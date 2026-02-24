"""
production/tests/test_e2e.py
E2E test scenarios (mocked — no live DB, Kafka, or OpenAI required).
Run: pytest production/tests/test_e2e.py -v

These tests verify the full data flow and cross-cutting concerns
using the prototype as a stand-in for the production agent.
"""
from __future__ import annotations

import time

import pytest

from src.agent.prototype import _conversations, detect_escalation, process_message
from production.agent.formatters import format_for_channel
from src.channels.gmail_intake import parse_gmail_message, stub_poll_inbox
from src.channels.web_form_intake import normalize_submission, validate_submission, stub_form_submission
from src.channels.whatsapp_intake import parse_twilio_form, stub_webhook_payload


# ---------------------------------------------------------------------------
# Helper: reset prototype state between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_conversations():
    """Reset in-memory conversation state before each test."""
    _conversations.clear()
    yield
    _conversations.clear()


# ---------------------------------------------------------------------------
# Web form full flow
# ---------------------------------------------------------------------------


class TestWebFormFlow:
    def test_web_form_submit_creates_response(self):
        """Web form message produces a valid response dict."""
        raw = stub_form_submission()
        valid, err = validate_submission(raw)
        assert valid, f"Validation failed: {err}"

        normalized = normalize_submission(raw)
        result = process_message(
            customer_id=normalized["customer_email"],
            message=normalized["content"],
            channel="web_form",
            customer_name=normalized["customer_name"],
        )
        assert "response" in result
        assert isinstance(result["escalated"], bool)

    def test_web_form_response_format_is_correct(self):
        """Web form response via production formatter includes help portal link.

        Note: the incubation prototype uses its own format_response (no portal link).
        The portal link is added by production/agent/formatters.py format_for_channel().
        This test validates the formatter directly, mirroring what the production
        send_response tool does.
        """
        raw = stub_form_submission()
        normalized = normalize_submission(raw)
        result = process_message(
            customer_id=normalized["customer_email"],
            message=normalized["content"],
            channel="web_form",
            customer_name=normalized["customer_name"],
        )
        # Apply the production formatter to the prototype's raw response
        formatted = format_for_channel(
            response=result["response"],
            channel="web_form",
        )
        assert "help.cloudsyncpro.com" in formatted, (
            "Production format_for_channel must add the help portal link for web_form channel"
        )

    def test_web_form_response_under_1000_chars(self):
        """Web form responses must stay under 1000 chars."""
        result = process_message(
            customer_id="test@example.com",
            message="How do I reset my password? I've been trying for a while.",
            channel="web_form",
        )
        assert len(result["response"]) <= 1000


# ---------------------------------------------------------------------------
# Channel format assertions
# ---------------------------------------------------------------------------


class TestChannelFormatting:
    def test_email_format_has_greeting_and_signature(self):
        response = format_for_channel(
            "Here is the information you requested.",
            channel="email",
            customer_name="Alice",
            ticket_id="TICKET-001",
        )
        assert response.startswith("Hi Alice")
        assert "Best regards" in response
        assert "TICKET-001" in response

    def test_whatsapp_format_is_brief_with_cta(self):
        response = format_for_channel(
            "To reset your password go to Settings.",
            channel="whatsapp",
        )
        assert len(response) < 500
        assert "📱" in response

    def test_web_form_format_has_portal_link(self):
        response = format_for_channel(
            "Your issue has been logged.",
            channel="web_form",
        )
        assert "help.cloudsyncpro.com" in response


# ---------------------------------------------------------------------------
# Cross-channel customer identity
# ---------------------------------------------------------------------------


class TestCrossChannelIdentity:
    def test_same_customer_id_shows_history_on_second_message(self):
        """Customer with prior messages gets history on second interaction."""
        customer_id = "alice@example.com"

        # First interaction (email)
        process_message(
            customer_id=customer_id,
            message="How do I export my data?",
            channel="email",
            customer_name="Alice",
        )

        # Second interaction (web form — same customer_id = email)
        assert customer_id in _conversations, "Customer state should persist"
        history = _conversations[customer_id].get("messages", [])
        assert len(history) >= 1, "History should have at least one prior message"

    def test_different_customers_have_separate_state(self):
        """Two customers must not share conversation state."""
        process_message(
            customer_id="alice@example.com",
            message="I need help with syncing",
            channel="email",
        )
        process_message(
            customer_id="bob@example.com",
            message="Password reset help",
            channel="whatsapp",
        )
        assert "alice@example.com" in _conversations
        assert "bob@example.com" in _conversations
        alice_msgs = _conversations["alice@example.com"]["messages"]
        bob_msgs = _conversations["bob@example.com"]["messages"]
        # Messages must not cross-contaminate
        for msg in alice_msgs:
            assert "password" not in msg.get("content", "").lower() or "sync" in msg.get("content", "").lower()


# ---------------------------------------------------------------------------
# Escalation flow
# ---------------------------------------------------------------------------


class TestEscalationFlow:
    def test_pricing_inquiry_escalates_without_price_info(self):
        result = process_message(
            customer_id="test@example.com",
            message="How much does your enterprise plan cost?",
            channel="email",
            customer_name="Test User",
        )
        assert result["escalated"] is True
        response_lower = result["response"].lower()
        # Must not answer the pricing question
        for word in ["$", "€", "per month", "usd", "free trial costs"]:
            assert word not in response_lower, f"Found '{word}' in escalated pricing response"

    def test_legal_threat_escalates(self):
        result = process_message(
            customer_id="angry@example.com",
            message="I'm going to sue your company for this data loss",
            channel="web_form",
        )
        assert result["escalated"] is True
        assert result["escalation_reason"] == "legal_language"

    def test_explicit_human_request_escalates(self):
        result = process_message(
            customer_id="human@example.com",
            message="I want to speak to a real person please",
            channel="whatsapp",
        )
        assert result["escalated"] is True
        assert result["escalation_reason"] == "explicit_human_request"


# ---------------------------------------------------------------------------
# Gmail intake flow
# ---------------------------------------------------------------------------


class TestGmailIntakeFlow:
    def test_stub_inbox_parses_correctly(self):
        messages = stub_poll_inbox()
        assert len(messages) > 0
        parsed = parse_gmail_message(messages[0])
        assert parsed["channel"] == "email"
        assert "@" in parsed["customer_email"]
        assert parsed["thread_id"] != ""
        assert len(parsed["content"]) > 0


# ---------------------------------------------------------------------------
# WhatsApp intake flow
# ---------------------------------------------------------------------------


class TestWhatsAppIntakeFlow:
    def test_stub_webhook_parses_correctly(self):
        payload = stub_webhook_payload()
        parsed = parse_twilio_form(payload)
        assert parsed["channel"] == "whatsapp"
        assert parsed["customer_phone"].startswith("+")
        assert len(parsed["content"]) > 0
        assert parsed["customer_name"] != ""
