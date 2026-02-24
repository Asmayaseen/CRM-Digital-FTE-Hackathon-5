"""
MCP Server — src/mcp_server.py
Stage 1 incubation: 5 tools mirroring production @function_tool signatures.
Run with Claude Code via stdio transport.
"""
from __future__ import annotations

from enum import Enum

from mcp.server import Server
from mcp.types import TextContent, Tool

from src.agent.prototype import (
    _conversations,
    detect_escalation,
    process_message,
    search_docs,
)

server = Server("customer-success-fte")


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# ---------------------------------------------------------------------------
# Tools — 1:1 mapping to production @function_tool functions
# ---------------------------------------------------------------------------

@server.tool("search_knowledge_base")
async def search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search CloudSync Pro product documentation for relevant information.

    Use this when the customer asks questions about product features,
    how to use something, or needs technical information.
    """
    results = search_docs(query)
    return results if results else "No relevant documentation found."


@server.tool("create_ticket")
async def create_ticket(customer_id: str, issue: str,
                         priority: str = "medium", channel: str = "web_form") -> str:
    """Create a support ticket for tracking. ALWAYS call this first."""
    import uuid
    ticket_id = f"TICKET-{str(uuid.uuid4())[:8].upper()}"
    _conversations.setdefault(customer_id, {
        "messages": [], "sentiment_scores": [], "status": "open",
        "original_channel": channel, "topics": [],
    })
    _conversations[customer_id]["ticket_id"] = ticket_id
    return f"Ticket created: {ticket_id} | Channel: {channel} | Priority: {priority}"


@server.tool("get_customer_history")
async def get_customer_history(customer_id: str) -> str:
    """Get customer interaction history across ALL channels."""
    conv = _conversations.get(customer_id)
    if not conv:
        return "No prior interaction history found for this customer."
    messages = conv.get("messages", [])
    if not messages:
        return "No messages in history."
    summary = [f"[{m['channel']}] {m['role']}: {m['content'][:100]}" for m in messages[-10:]]
    return "\n".join(summary)


@server.tool("escalate_to_human")
async def escalate_to_human(ticket_id: str, reason: str, urgency: str = "normal") -> str:
    """Escalate conversation to human support.

    Use when: pricing/refund inquiry, legal language, negative sentiment,
    explicit human request, or knowledge not found after 2 searches.
    """
    return f"Escalated {ticket_id} to human support. Reason: {reason} | Urgency: {urgency}"


@server.tool("send_response")
async def send_response(ticket_id: str, message: str, channel: str) -> str:
    """Send formatted response to customer via their channel.

    Always call this LAST. Response will be formatted for the channel.
    """
    # In incubation, just return confirmation
    return f"Response sent via {channel} | Ticket: {ticket_id} | Status: delivered"


if __name__ == "__main__":
    server.run()
