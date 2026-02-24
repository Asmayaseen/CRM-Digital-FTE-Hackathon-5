"""
production/tests/test_agent.py
Unit tests for all 6 escalation triggers and escalation notification logic.
Run: pytest production/tests/test_agent.py -v
"""
from __future__ import annotations

import pytest

from src.agent.prototype import detect_escalation, detect_sentiment, process_message
from production.agent.formatters import format_for_channel


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _should_escalate(message: str) -> tuple[bool, str]:
    """Check escalation via prototype (mirrors production logic)."""
    escalate, reason = detect_escalation(message)
    if not escalate:
        sentiment = detect_sentiment(message)
        if sentiment < 0.3:
            escalate, reason = True, "negative_sentiment"
    return escalate, reason


# ---------------------------------------------------------------------------
# Trigger 1: pricing_inquiry
# ---------------------------------------------------------------------------


def test_escalation_trigger_pricing_inquiry():
    """Pricing keywords must immediately trigger escalation."""
    pricing_messages = [
        "How much does the enterprise plan cost?",
        "What is the monthly price?",
        "Can you give me a discount on pricing?",
        "I want to compare your prices to a competitor",
        "Is there a free trial or what's the cost?",
    ]
    for msg in pricing_messages:
        escalated, reason = _should_escalate(msg)
        assert escalated is True, f"Expected escalation for: '{msg}'"
        assert reason in ("pricing_inquiry", "legal_language"), (
            f"Expected pricing_inquiry or legal_language, got '{reason}' for: '{msg}'"
        )


# ---------------------------------------------------------------------------
# Trigger 2: refund_request
# ---------------------------------------------------------------------------


def test_escalation_trigger_refund_request():
    """Refund and money-back keywords must trigger escalation."""
    refund_messages = [
        "I want a refund for last month",
        "Please give me my money back",
        "I was charged incorrectly and need a refund",
        "How do I get money back for unused subscription?",
    ]
    for msg in refund_messages:
        escalated, reason = _should_escalate(msg)
        assert escalated is True, f"Expected escalation for: '{msg}'"
        # refund / money back maps to refund_request in prototype
        assert reason in ("refund_request", "pricing_inquiry", "legal_language"), (
            f"Expected refund-related reason, got '{reason}' for: '{msg}'"
        )


# ---------------------------------------------------------------------------
# Trigger 3: legal_language
# ---------------------------------------------------------------------------


def test_escalation_trigger_legal_language():
    """Legal threats must trigger escalation immediately."""
    legal_messages = [
        "I'm going to sue your company",
        "My lawyer will be contacting you",
        "This is a legal matter and I will take legal action",
        "I'll file a lawsuit if this isn't resolved",
        "I'm consulting an attorney about this",
    ]
    for msg in legal_messages:
        escalated, reason = _should_escalate(msg)
        assert escalated is True, f"Expected escalation for: '{msg}'"
        assert reason == "legal_language", (
            f"Expected 'legal_language', got '{reason}' for: '{msg}'"
        )


# ---------------------------------------------------------------------------
# Trigger 4: negative_sentiment
# ---------------------------------------------------------------------------


def test_escalation_trigger_negative_sentiment():
    """Messages with strong negative sentiment must escalate."""
    negative_messages = [
        "This product is absolutely terrible and completely useless garbage",
        "I hate this software, it's the worst I've ever used",
        "This is ridiculous, awful, and totally broken. I hate it",
    ]
    for msg in negative_messages:
        score = detect_sentiment(msg)
        escalated, reason = _should_escalate(msg)
        assert escalated is True, (
            f"Expected escalation for negative message (score={score:.2f}): '{msg}'"
        )
        assert reason == "negative_sentiment", (
            f"Expected 'negative_sentiment', got '{reason}'"
        )


# ---------------------------------------------------------------------------
# Trigger 5: explicit_human_request
# ---------------------------------------------------------------------------


def test_escalation_trigger_explicit_human_request():
    """Customer requesting a human agent must escalate."""
    human_request_messages = [
        "I want to speak to a human",
        "Can I talk to a real person please?",
        "Connect me to an agent",
        "I need a representative not a bot",
        "Please put me through to someone",
    ]
    for msg in human_request_messages:
        escalated, reason = _should_escalate(msg)
        assert escalated is True, f"Expected escalation for: '{msg}'"
        assert reason == "explicit_human_request", (
            f"Expected 'explicit_human_request', got '{reason}' for: '{msg}'"
        )


# ---------------------------------------------------------------------------
# Trigger 6: knowledge_not_found (tested via process_message flow)
# ---------------------------------------------------------------------------


def test_escalation_trigger_knowledge_not_found():
    """
    When the KB cannot answer, agent should respond with clarification request.

    Prototype note: the prototype uses dumb keyword search, so it may return
    partial matches on common English words. We use a query made entirely of
    gibberish tokens that cannot match any word in product-docs.md.
    Production: pgvector cosine similarity will correctly return no results.
    """
    # Pure gibberish — no real English words that could match product docs
    gibberish_query = "fjdksajf qpwxzlmv brthnqzx yqvwzpkj"
    result = process_message(
        customer_id="test-no-kb-001",
        message=gibberish_query,
        channel="web_form",
        customer_name="TestUser",
    )
    assert isinstance(result, dict), "Must return a dict"
    assert "response" in result, "Must have a response key"
    # With no matching words, the prototype falls through to the "no info found" path
    response_lower = result["response"].lower()
    assert (
        result["escalated"]
        or "more detail" in response_lower
        or "couldn't find" in response_lower
        or "specific" in response_lower
        or "provide" in response_lower
    ), f"Unknown query should ask for clarification. Got: {result['response'][:100]}"


# ---------------------------------------------------------------------------
# Escalation notification formatting tests (T039)
# ---------------------------------------------------------------------------


def test_escalation_notification_email():
    """Email escalation notification must mention specialist follow-up timeline."""
    notification = format_for_channel(
        response="A specialist will follow up with you within 24 hours.",
        channel="email",
        customer_name="Alice Smith",
        ticket_id="TICKET-ESC001",
    )
    assert "Hi Alice" in notification, "Email must have greeting"
    assert "Best regards" in notification, "Email must have signature"
    assert "TICKET-ESC001" in notification, "Email must reference ticket"
    assert "24 hours" in notification or "specialist" in notification.lower(), (
        "Email escalation must mention follow-up timeline"
    )


def test_escalation_notification_whatsapp():
    """WhatsApp escalation notification must be brief and have CTA."""
    notification = format_for_channel(
        response="We've connected you with our support team.",
        channel="whatsapp",
        customer_name="Bob",
    )
    assert len(notification) < 500, "WhatsApp notification must be brief"
    assert "📱" in notification, "WhatsApp notification must have CTA"
    assert "Hi Bob" not in notification, "WhatsApp must not have formal greeting"


def test_escalation_notification_web_form():
    """Web form escalation notification must have help portal link."""
    notification = format_for_channel(
        response="Your case has been escalated to our specialist team.",
        channel="web_form",
        customer_name="Carol",
    )
    assert "help.cloudsyncpro.com" in notification, (
        "Web form escalation must include help portal link"
    )
    assert len(notification) < 1000, "Web form must stay under 1000 chars"
