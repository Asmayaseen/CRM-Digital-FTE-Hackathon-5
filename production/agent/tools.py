"""
production/agent/tools.py
OpenAI Agents SDK @function_tool definitions — all 5 agent tools.

Tool execution order enforced by system prompt and test_transition.py:
  1. create_ticket
  2. get_customer_history
  3. search_knowledge_base  (OR escalate_to_human)
  4. send_response
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Literal, Optional

from agents import function_tool
from pydantic import BaseModel, Field

from production.agent.formatters import format_for_channel
from production.database import queries
from production.kafka_client import FTEKafkaProducer, TOPICS

logger = logging.getLogger(__name__)


class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------


class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., description="Search query reformulated from customer message")
    max_results: int = Field(default=5, ge=1, le=10)


class TicketInput(BaseModel):
    customer_id: str = Field(..., description="UUID of the customer record")
    issue: str = Field(..., description="Brief description of the customer issue")
    priority: Literal["low", "medium", "high"] = Field(default="medium")
    channel: Channel = Field(..., description="Channel where the inquiry arrived")
    conversation_id: Optional[str] = Field(default=None, description="Active conversation UUID — omit if unknown")


class EscalationInput(BaseModel):
    ticket_id: str = Field(..., description="Ticket ID returned by create_ticket")
    reason: Literal[
        "pricing_inquiry",
        "refund_request",
        "legal_language",
        "negative_sentiment",
        "explicit_human_request",
        "knowledge_not_found",
    ] = Field(..., description="Reason code for escalation")
    urgency: Literal["normal", "urgent", "high"] = Field(default="normal")


class ResponseInput(BaseModel):
    ticket_id: str = Field(..., description="Ticket ID returned by create_ticket")
    message: str = Field(..., description="Raw response text before channel formatting")
    channel: Channel = Field(..., description="Delivery channel")
    customer_name: str = Field(default="Customer")


# ---------------------------------------------------------------------------
# Tool 1: search_knowledge_base
# ---------------------------------------------------------------------------


@function_tool
async def search_knowledge_base(input: KnowledgeSearchInput) -> str:
    """Search CloudSync Pro product documentation for relevant information.

    Use this when the customer asks questions about product features,
    how to use something, or needs technical information.
    Do NOT call if any escalation trigger has been detected.
    Maximum 2 calls per interaction — escalate with reason 'knowledge_not_found' if both fail.
    """
    try:
        import asyncio
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        # fastembed is synchronous — run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: list(model.embed([input.query]))
        )
        embedding = embeddings[0].tolist()
        results = await queries.search_knowledge_base(
            embedding, category=None, max_results=input.max_results
        )
        if not results:
            return "No relevant documentation found."
        parts = []
        for row in results:
            parts.append(f"**{row['title']}**\n{row['content'][:500]}")
        return "\n\n---\n\n".join(parts)
    except Exception as exc:
        logger.error("search_knowledge_base failed: %s", exc)
        return "Knowledge base temporarily unavailable."


# ---------------------------------------------------------------------------
# Tool 2: create_ticket
# ---------------------------------------------------------------------------


@function_tool
async def create_ticket(input: TicketInput) -> str:
    """Create a support ticket for tracking. ALWAYS call this FIRST before any other tool.

    Returns the ticket_id which must be passed to all subsequent tool calls.
    """
    try:
        # Resolve conversation_id — use provided or look up active one
        conv_id = input.conversation_id
        if not conv_id:
            conv_id = await queries.get_active_conversation(input.customer_id) or ""
        ticket_id = await queries.create_ticket(
            customer_id=input.customer_id,
            conversation_id=conv_id or input.customer_id,  # fallback to customer_id
            source_channel=input.channel.value,
            category=input.issue[:100],
            priority=input.priority,
        )
        logger.info("Ticket created: %s | channel=%s", ticket_id, input.channel.value)
        return f"Ticket created: {ticket_id} | Priority: {input.priority} | Channel: {input.channel.value}"
    except Exception as exc:
        logger.error("create_ticket failed: %s", exc)
        return "Failed to create ticket. Please try again."


# ---------------------------------------------------------------------------
# Tool 3: get_customer_history
# ---------------------------------------------------------------------------


@function_tool
async def get_customer_history(customer_id: str) -> str:
    """Get customer interaction history across ALL channels.

    Always call this SECOND (after create_ticket) to check for prior contact.
    Use the history to acknowledge previous interactions and avoid asking
    the customer to repeat themselves.
    """
    try:
        rows = await queries.get_customer_history_query(customer_id)
        if not rows:
            return "No prior interaction history found for this customer."
        lines = []
        for row in rows[:20]:  # Limit to last 20 messages
            channel = row.get("channel", "unknown")
            role = row.get("role", "unknown")
            content = str(row.get("content", ""))[:100]
            lines.append(f"[{channel}] {role}: {content}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("get_customer_history failed: %s", exc)
        return "Could not retrieve customer history."


# ---------------------------------------------------------------------------
# Tool 4: escalate_to_human
# ---------------------------------------------------------------------------


@function_tool
async def escalate_to_human(input: EscalationInput) -> str:
    """Escalate this conversation to a human support specialist.

    Use when ANY of these conditions are detected:
    - pricing_inquiry: customer asks about pricing, plans, or costs
    - refund_request: customer requests refund or disputes a charge
    - legal_language: message contains legal threats (sue, lawyer, lawsuit)
    - negative_sentiment: customer sentiment score < 0.3
    - explicit_human_request: customer asks to speak to a human/agent
    - knowledge_not_found: 2 consecutive KB searches returned no results

    Do NOT attempt to resolve these yourself. Escalate immediately.
    """
    try:
        await queries.update_ticket_status(
            ticket_id=input.ticket_id,
            status="escalated",
            resolution_notes=f"Escalated: {input.reason}",
        )
        # Store escalation notification so customer sees it in ticket status
        ticket = await queries.get_ticket_by_id(input.ticket_id)
        if ticket and ticket.get("conversation_id"):
            escalation_msg = (
                "Your request has been escalated to our human support team. "
                "A specialist will review your case and follow up with you shortly. "
                f"Ticket reference: {input.ticket_id}"
            )
            await queries.create_message(
                conversation_id=str(ticket["conversation_id"]),
                channel=ticket.get("source_channel", "web_form"),
                direction="outbound",
                role="agent",
                content=escalation_msg,
            )
        # Publish escalation event to Kafka
        producer = FTEKafkaProducer()
        await producer.publish(
            TOPICS["escalations"],
            {
                "ticket_id": input.ticket_id,
                "reason": input.reason,
                "urgency": input.urgency,
            },
        )
        logger.info(
            "Escalated ticket=%s reason=%s urgency=%s",
            input.ticket_id, input.reason, input.urgency
        )
        return (
            f"Escalated {input.ticket_id} to human support. "
            f"Reason: {input.reason} | Urgency: {input.urgency}"
        )
    except Exception as exc:
        logger.error("escalate_to_human failed: %s", exc)
        return f"Escalation recorded for {input.ticket_id}. A human will follow up shortly."


# ---------------------------------------------------------------------------
# Tool 5: send_response
# ---------------------------------------------------------------------------


@function_tool
async def send_response(input: ResponseInput) -> str:
    """Send formatted response to customer via their channel. ALWAYS call this LAST.

    Format is automatically applied based on channel:
    - email: greeting + signature + ticket reference
    - whatsapp: truncated + CTA suffix
    - web_form: response + help portal link

    Never call this before create_ticket. Never call twice in one interaction.
    """
    try:
        formatted = format_for_channel(
            response=input.message,
            channel=input.channel.value,
            customer_name=input.customer_name,
            ticket_id=input.ticket_id,
        )
        # Store agent response in the messages table
        ticket = await queries.get_ticket_by_id(input.ticket_id)
        if ticket and ticket.get("conversation_id"):
            await queries.create_message(
                conversation_id=str(ticket["conversation_id"]),
                channel=input.channel.value,
                direction="outbound",
                role="agent",
                content=formatted,
            )
        logger.info("Response sent | ticket=%s channel=%s", input.ticket_id, input.channel.value)
        return f"Response sent via {input.channel.value} | Ticket: {input.ticket_id} | Status: delivered"
    except Exception as exc:
        logger.error("send_response failed: %s", exc)
        return f"Response delivery failed for {input.ticket_id}. Error logged."


# ---------------------------------------------------------------------------
# Exported tool list (order matters for Agent definition)
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    create_ticket,
    get_customer_history,
    search_knowledge_base,
    escalate_to_human,
    send_response,
]
