"""
Incubation prototype — src/agent/prototype.py
Stage 1: Claude Code-driven exploration. NOT production code.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

CHANNEL_STYLES = {
    "email":     {"max_len": 2000, "greeting": True, "signature": True},
    "whatsapp":  {"max_len": 300,  "greeting": False, "signature": False},
    "web_form":  {"max_len": 1000, "greeting": False, "signature": False},
}

ESCALATION_KEYWORDS = [
    "pricing", "price", "cost", "refund", "lawyer", "sue", "legal",
    "attorney", "lawsuit", "cancel subscription", "money back",
]

HUMAN_REQUEST_KEYWORDS = [
    "human", "agent", "real person", "speak to someone", "representative",
    "put me through", "connect me", "talk to someone", "speak with someone",
]

# In-memory state — replaced by PostgreSQL in production
_conversations: dict[str, dict] = {}


def _load_product_docs() -> str:
    docs_path = Path(__file__).parent.parent.parent / "context" / "product-docs.md"
    if docs_path.exists():
        return docs_path.read_text()
    return ""


PRODUCT_DOCS = _load_product_docs()


def search_docs(query: str) -> str:
    """Simple keyword-based search (replaced by pgvector in production)."""
    query_lower = query.lower()
    results = []
    for section in PRODUCT_DOCS.split("##"):
        if any(word in section.lower() for word in query_lower.split()):
            results.append(section.strip()[:500])
            if len(results) >= 3:
                break
    return "\n\n---\n\n".join(results) if results else ""


def detect_escalation(message: str) -> tuple[bool, str]:
    """Return (should_escalate, reason)."""
    msg_lower = message.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in msg_lower:
            if any(k in kw for k in ("pric", "cost", "cancel")):
                return True, "pricing_inquiry"
            if "refund" in kw or "money back" in kw:
                return True, "refund_request"
            return True, "legal_language"
    for kw in HUMAN_REQUEST_KEYWORDS:
        if kw in msg_lower:
            return True, "explicit_human_request"
    return False, ""


def detect_sentiment(message: str) -> float:
    """Naive sentiment — replaced by LLM in production."""
    negative_words = ["ridiculous", "broken", "useless", "terrible", "worst",
                      "hate", "scam", "awful", "garbage", "stupid"]
    score = 0.7  # default neutral-positive
    for word in negative_words:
        if word in message.lower():
            score -= 0.2
    return max(0.0, min(1.0, score))


def format_response(response: str, channel: str, customer_name: str = "Customer") -> str:
    style = CHANNEL_STYLES.get(channel, CHANNEL_STYLES["web_form"])
    if style["greeting"]:
        response = f"Hi {customer_name},\n\n{response}"
    if style["signature"]:
        response += "\n\nBest regards,\nCloudSync Pro Support Team"
    if len(response) > style["max_len"]:
        response = response[:style["max_len"] - 3] + "..."
    return response


def process_message(customer_id: str, message: str, channel: str,
                     customer_name: str = "Customer") -> dict:
    """Core interaction loop — returns response dict with escalation info."""
    # Memory
    if customer_id not in _conversations:
        _conversations[customer_id] = {
            "messages": [], "sentiment_scores": [], "topics": [],
            "original_channel": channel, "status": "active",
        }
    conv = _conversations[customer_id]
    conv["messages"].append({"role": "customer", "content": message, "channel": channel})

    sentiment = detect_sentiment(message)
    conv["sentiment_scores"].append(sentiment)

    should_escalate, reason = detect_escalation(message)
    if not should_escalate and sentiment < 0.3:
        should_escalate, reason = True, "negative_sentiment"

    if should_escalate:
        conv["status"] = "escalated"
        reply = f"I've escalated your case to our specialist team. Reference: TICKET-{len(_conversations):04d}"
        return {
            "response": format_response(reply, channel, customer_name),
            "escalated": True,
            "escalation_reason": reason,
            "sentiment": sentiment,
        }

    docs = search_docs(message)
    if docs:
        reply = f"Here's what I found:\n\n{docs[:500]}\n\nDoes that help?"
    else:
        reply = "I couldn't find specific information on that. Could you provide more detail?"

    conv["messages"].append({"role": "agent", "content": reply})
    return {
        "response": format_response(reply, channel, customer_name),
        "escalated": False,
        "escalation_reason": None,
        "sentiment": sentiment,
    }
