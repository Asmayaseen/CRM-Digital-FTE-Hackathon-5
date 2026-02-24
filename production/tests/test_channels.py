"""
production/tests/test_channels.py
Unit tests for channel handlers.
Run: pytest production/tests/test_channels.py -v
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import unittest

import pytest

from production.agent.formatters import format_for_channel


# ---------------------------------------------------------------------------
# Gmail handler tests (no live Google API — test parsing logic only)
# ---------------------------------------------------------------------------


class TestGmailBodyExtraction:
    """Test _decode_body logic via src/channels/gmail_intake.py."""

    def test_extracts_plain_text_body(self):
        from src.channels.gmail_intake import _decode_body

        raw_text = "Hello, I need help with syncing."
        encoded = base64.urlsafe_b64encode(raw_text.encode()).decode()
        payload = {"body": {"data": encoded}}
        result = _decode_body(payload)
        assert result == raw_text

    def test_extracts_body_from_parts(self):
        from src.channels.gmail_intake import _decode_body

        raw_text = "Multipart message body."
        encoded = base64.urlsafe_b64encode(raw_text.encode()).decode()
        payload = {
            "parts": [
                {"mimeType": "text/html", "body": {"data": "PGh0bWw+"}},
                {"mimeType": "text/plain", "body": {"data": encoded}},
            ]
        }
        result = _decode_body(payload)
        assert result == raw_text

    def test_returns_empty_for_missing_body(self):
        from src.channels.gmail_intake import _decode_body

        payload = {"body": {}}
        result = _decode_body(payload)
        assert result == ""

    def test_extracts_email_from_angle_bracket_format(self):
        from src.channels.gmail_intake import parse_gmail_message

        msg = {
            "id": "msg-001",
            "threadId": "thread-001",
            "payload": {
                "headers": [
                    {"name": "From", "value": '"Alice Wong" <alice@example.com>'},
                    {"name": "Subject", "value": "Test subject"},
                ],
                "body": {},
            },
        }
        parsed = parse_gmail_message(msg)
        assert parsed["customer_email"] == "alice@example.com"
        assert parsed["customer_name"] == "Alice Wong"
        assert parsed["channel"] == "email"
        assert parsed["thread_id"] == "thread-001"

    def test_extracts_bare_email(self):
        from src.channels.gmail_intake import parse_gmail_message

        msg = {
            "id": "msg-002",
            "threadId": "thread-002",
            "payload": {
                "headers": [
                    {"name": "From", "value": "bob@example.com"},
                    {"name": "Subject", "value": "Question"},
                ],
                "body": {},
            },
        }
        parsed = parse_gmail_message(msg)
        assert parsed["customer_email"] == "bob@example.com"


# ---------------------------------------------------------------------------
# WhatsApp handler tests
# ---------------------------------------------------------------------------


class TestWhatsAppHandler:
    """Test WhatsApp payload parsing from src/channels/whatsapp_intake.py."""

    def test_strips_whatsapp_prefix_from_phone(self):
        from src.channels.whatsapp_intake import parse_twilio_form

        payload = {
            "From": "whatsapp:+14155238886",
            "Body": "Hello",
            "MessageSid": "SM001",
            "ProfileName": "Bob",
            "WaId": "14155238886",
            "To": "whatsapp:+14155551234",
            "NumMedia": "0",
        }
        parsed = parse_twilio_form(payload)
        assert parsed["customer_phone"] == "+14155238886"
        assert parsed["channel"] == "whatsapp"

    def test_parses_profile_name(self):
        from src.channels.whatsapp_intake import parse_twilio_form

        payload = {
            "From": "whatsapp:+12025551234",
            "Body": "test",
            "MessageSid": "SM002",
            "ProfileName": "Carol Davies",
            "WaId": "2025551234",
            "NumMedia": "0",
        }
        parsed = parse_twilio_form(payload)
        assert parsed["customer_name"] == "Carol Davies"

    def test_format_response_under_300_chars(self):
        """WhatsApp formatter must keep output under 300 chars for normal responses."""
        short_response = "Here are the steps to reset your password: go to Settings."
        formatted = format_for_channel(short_response, "whatsapp")
        assert len(formatted) < 500, "WhatsApp response exceeds 500 char limit"
        assert "📱" in formatted, "Missing WhatsApp CTA suffix"

    def test_format_response_truncates_long_text(self):
        """Long WhatsApp responses must be truncated with suffix preserved."""
        long_response = "A" * 500
        formatted = format_for_channel(long_response, "whatsapp")
        assert len(formatted) <= 300 + len("📱 Reply for more help or type 'human' for live support.") + 5
        assert "📱" in formatted, "Suffix must be preserved after truncation"


# ---------------------------------------------------------------------------
# Web form handler tests
# ---------------------------------------------------------------------------


class TestWebFormValidators:
    """Test validation in src/channels/web_form_intake.py."""

    def _valid_payload(self) -> dict:
        return {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "subject": "Cannot sync files",
            "category": "technical",
            "priority": "high",
            "message": "My files are not syncing properly. Please help.",
        }

    def test_valid_submission_passes(self):
        from src.channels.web_form_intake import validate_submission

        valid, err = validate_submission(self._valid_payload())
        assert valid is True
        assert err == ""

    def test_empty_name_fails(self):
        from src.channels.web_form_intake import validate_submission

        data = self._valid_payload()
        data["name"] = ""
        valid, err = validate_submission(data)
        assert valid is False
        assert "name" in err.lower()

    def test_short_name_fails(self):
        from src.channels.web_form_intake import validate_submission

        data = self._valid_payload()
        data["name"] = "J"
        valid, err = validate_submission(data)
        assert valid is False

    def test_invalid_email_fails(self):
        from src.channels.web_form_intake import validate_submission

        for bad_email in ["notanemail", "missing@", "@nodomain.com", "no at sign"]:
            data = self._valid_payload()
            data["email"] = bad_email
            valid, err = validate_submission(data)
            assert valid is False, f"Expected failure for email: {bad_email}"
            assert "email" in err.lower()

    def test_short_message_fails(self):
        from src.channels.web_form_intake import validate_submission

        data = self._valid_payload()
        data["message"] = "short"
        valid, err = validate_submission(data)
        assert valid is False
        assert "detail" in err.lower() or "character" in err.lower()

    def test_invalid_category_fails(self):
        from src.channels.web_form_intake import validate_submission

        data = self._valid_payload()
        data["category"] = "unknown_category"
        valid, err = validate_submission(data)
        assert valid is False
        assert "category" in err.lower()
