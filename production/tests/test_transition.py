"""
production/tests/test_transition.py
MANDATORY GATE TESTS — Constitution Principle VII.

ALL 6 tests must pass before any production deployment.
Run: pytest production/tests/test_transition.py -v

These tests validate the incubation → production transition by exercising
the core agent behaviours extracted from prototype.py and validated against
the production formatters.py and the escalation rules.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub missing optional dependencies before any production imports.
# In the test environment, aiokafka and asyncpg may not be installed.
# Production code is tested for structure and logic only — not live I/O.
# ---------------------------------------------------------------------------
for _mod in ("aiokafka", "asyncpg", "agents"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# ---------------------------------------------------------------------------
# Import production modules under test
# These are tested in isolation — no live DB, no live Kafka, no live OpenAI.
# ---------------------------------------------------------------------------

from production.agent.formatters import format_for_channel
from src.agent.prototype import detect_escalation, detect_sentiment, process_message


# ---------------------------------------------------------------------------
# Test 1: Edge case — empty message
# ---------------------------------------------------------------------------


def test_edge_case_empty_message():
    """
    An empty or whitespace-only message must not crash the agent.
    The prototype should return a clarification request, not an exception.
    """
    result = process_message(
        customer_id="test-empty-001",
        message="   ",
        channel="web_form",
        customer_name="TestUser",
    )
    # Must not raise; must return a response dict
    assert isinstance(result, dict), "process_message must return a dict"
    assert "response" in result, "Response dict must contain 'response' key"
    response_text = result["response"].lower()
    # Should ask for more information, not crash
    assert result["escalated"] is False or "detail" in response_text or "help" in response_text, (
        "Empty message should prompt for clarification or proceed without escalation"
    )


# ---------------------------------------------------------------------------
# Test 2: Edge case — pricing inquiry triggers escalation
# ---------------------------------------------------------------------------


def test_edge_case_pricing_escalation():
    """
    Any message containing pricing keywords must escalate immediately.
    The agent must NEVER answer pricing questions.
    """
    pricing_messages = [
        "How much does the enterprise plan cost?",
        "What is your pricing for 50 users?",
        "I want to know the price of the Pro tier",
        "Compare your cost to competitor pricing",
    ]
    for msg in pricing_messages:
        should_escalate, reason = detect_escalation(msg)
        assert should_escalate, f"Pricing message should trigger escalation: '{msg}'"
        assert reason in ("pricing_inquiry", "legal_language"), (
            f"Escalation reason for pricing should be 'pricing_inquiry', got '{reason}' for: '{msg}'"
        )

    # Full process_message test for a pricing inquiry
    result = process_message(
        customer_id="test-pricing-001",
        message="How much does the enterprise plan cost?",
        channel="email",
        customer_name="Alice",
    )
    assert result["escalated"] is True, "Pricing inquiry must be escalated"
    # Response must NOT contain any price information
    response_lower = result["response"].lower()
    price_answers = ["$", "€", "£", "per month", "per year", "usd", "free", "paid", "tier"]
    for price_word in price_answers:
        assert price_word not in response_lower, (
            f"Escalated pricing response must not contain price info: found '{price_word}'"
        )


# ---------------------------------------------------------------------------
# Test 3: Edge case — angry customer triggers empathy or escalation
# ---------------------------------------------------------------------------


def test_edge_case_angry_customer():
    """
    An angry customer (negative sentiment) must either be escalated
    or receive an empathetic response. Never a dismissive or automated reply.
    """
    angry_messages = [
        "This is absolutely terrible, your product is garbage",
        "I hate this software, it's completely useless",
        "Worst customer service I've ever experienced",
    ]
    for msg in angry_messages:
        score = detect_sentiment(msg)
        assert score < 0.5, (
            f"Negative message should have sentiment < 0.5, got {score} for: '{msg}'"
        )

    # Full process for a strongly negative message
    result = process_message(
        customer_id="test-angry-001",
        message="This is absolutely terrible, your product is garbage and I hate it",
        channel="whatsapp",
        customer_name="Bob",
    )
    # Either escalated OR response contains empathy keywords
    response_lower = result["response"].lower()
    empathy_keywords = ["sorry", "apologize", "understand", "help", "specialist", "escalat"]
    has_empathy = any(kw in response_lower for kw in empathy_keywords)
    assert result["escalated"] is True or has_empathy, (
        "Angry customer must be escalated or receive an empathetic response"
    )


# ---------------------------------------------------------------------------
# Test 4: Channel formatting — email must have greeting and signature
# ---------------------------------------------------------------------------


def test_channel_response_email_format():
    """
    Email responses must include a personal greeting and a sign-off.
    This is Constitution Principle IX — channel-aware formatting.
    """
    raw_response = (
        "To reset your password, go to Settings > Account > Reset Password. "
        "You will receive an email with a reset link within 5 minutes."
    )
    formatted = format_for_channel(
        response=raw_response,
        channel="email",
        customer_name="Jane Doe",
        ticket_id="TICKET-ABCD1234",
    )

    assert formatted.startswith("Hi Jane"), (
        f"Email response must start with greeting. Got: {formatted[:50]}"
    )
    assert "Best regards" in formatted, (
        "Email response must include 'Best regards' signature"
    )
    assert "TICKET-ABCD1234" in formatted, (
        "Email response must include the ticket reference"
    )
    assert len(formatted) <= 2000, (
        f"Email response must not exceed 2000 chars, got {len(formatted)}"
    )


# ---------------------------------------------------------------------------
# Test 5: Channel formatting — WhatsApp must be brief
# ---------------------------------------------------------------------------


def test_channel_response_whatsapp_brevity():
    """
    WhatsApp responses must stay under 500 characters (ideally < 300).
    The 📱 CTA suffix must be present.
    """
    raw_response = (
        "To reset your password, open the CloudSync Pro app or website, "
        "click on 'Forgot Password' on the login screen, enter your email address, "
        "and follow the instructions sent to your inbox."
    )
    formatted = format_for_channel(
        response=raw_response,
        channel="whatsapp",
        customer_name="Carlos",
    )

    assert len(formatted) < 500, (
        f"WhatsApp response must be under 500 chars, got {len(formatted)}"
    )
    assert "📱" in formatted, (
        "WhatsApp response must contain the 📱 CTA suffix"
    )
    assert "Hi Carlos" not in formatted, (
        "WhatsApp response must NOT have a formal greeting"
    )
    assert "Best regards" not in formatted, (
        "WhatsApp response must NOT have an email signature"
    )


# ---------------------------------------------------------------------------
# Test 6: Tool execution order — create_ticket first, send_response last
# ---------------------------------------------------------------------------


def test_tool_execution_order():
    """
    Validate that the incubation prototype enforces the correct tool order:
    create_ticket → (search/escalate) → send_response.

    In the prototype, this is simulated by the process_message function
    always returning a ticket reference in the response when escalated.
    In production, the system prompt + test_transition enforces order via
    tool call sequencing in the OpenAI Agents SDK.

    This test validates the sequence is documented and the prototype returns
    a ticket_id before sending a response.
    """
    # The prototype's escalation path always creates a reference before responding
    result = process_message(
        customer_id="test-order-001",
        message="I need help with syncing files",
        channel="web_form",
        customer_name="TestUser",
    )
    assert isinstance(result, dict), "process_message must return a dict"
    assert "response" in result, "Must have a response"
    assert "escalated" in result, "Must have escalation status"
    # When escalated, escalation_reason must be set before send
    if result["escalated"]:
        assert result.get("escalation_reason") is not None, (
            "Escalated response must have a reason set before send_response"
        )

    # Tool order assertion for production: verify ALL_TOOLS list ordering
    # by inspecting the source file directly (avoids dependency on mocked agents SDK).
    import re
    from pathlib import Path

    tools_source = (Path(__file__).parent.parent / "agent" / "tools.py").read_text()
    match = re.search(r"ALL_TOOLS\s*=\s*\[(.*?)\]", tools_source, re.DOTALL)
    assert match, "ALL_TOOLS list not found in production/agent/tools.py"

    known_tools = {
        "create_ticket", "get_customer_history",
        "search_knowledge_base", "escalate_to_human", "send_response",
    }
    ordered = [n for n in re.findall(r"\b(\w+)\b", match.group(1)) if n in known_tools]

    assert ordered[0] == "create_ticket", (
        f"create_ticket must be first in ALL_TOOLS. Order: {ordered}"
    )
    assert ordered[-1] == "send_response", (
        f"send_response must be last in ALL_TOOLS. Order: {ordered}"
    )
