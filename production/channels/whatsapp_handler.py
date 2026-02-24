"""
WhatsApp channel handler — production/channels/whatsapp_handler.py
Handles Twilio WhatsApp webhooks and outbound messages.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import Request
from twilio.request_validator import RequestValidator
from twilio.rest import Client

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.whatsapp_number = os.getenv(
            "TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"
        )
        self._client: Client | None = None
        self._validator = RequestValidator(self.auth_token)

    @property
    def client(self) -> Client:
        if not self._client:
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    async def validate_webhook(self, request: Request) -> bool:
        """Validate incoming Twilio webhook using X-Twilio-Signature header."""
        try:
            signature = request.headers.get("X-Twilio-Signature", "")
            url = str(request.url)
            form_data = await request.form()
            params = dict(form_data)
            return self._validator.validate(url, params, signature)
        except Exception as exc:
            logger.error("Twilio signature validation error: %s", exc)
            return False

    async def process_webhook(self, form_data: dict) -> dict:
        """Parse Twilio form payload into a normalised message dict."""
        raw_from = form_data.get("From", "")
        phone = raw_from.replace("whatsapp:", "").strip()

        return {
            "channel": "whatsapp",
            "channel_message_id": form_data.get("MessageSid"),
            "customer_phone": phone,
            "content": form_data.get("Body", "").strip(),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "num_media": form_data.get("NumMedia", "0"),
                "profile_name": form_data.get("ProfileName", ""),
                "wa_id": form_data.get("WaId", ""),
                "status": form_data.get("SmsStatus", ""),
            },
        }

    async def send_message(self, to_phone: str, body: str) -> dict:
        """Send a WhatsApp message via Twilio."""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"

        try:
            message = self.client.messages.create(
                body=body,
                from_=self.whatsapp_number,
                to=to_phone,
            )
            return {
                "channel_message_id": message.sid,
                "delivery_status": message.status,
            }
        except Exception as exc:
            logger.error("Failed to send WhatsApp message to %s: %s", to_phone, exc)
            return {"channel_message_id": None, "delivery_status": "failed"}

    def format_response(self, response: str, max_length: int = 1600) -> list[str]:
        """Split a long response into WhatsApp-sized chunks (max 1600 chars each)."""
        if len(response) <= max_length:
            return [response]

        parts: list[str] = []
        remaining = response
        while remaining:
            if len(remaining) <= max_length:
                parts.append(remaining)
                break
            break_point = remaining.rfind(". ", 0, max_length)
            if break_point == -1:
                break_point = remaining.rfind(" ", 0, max_length)
            if break_point == -1:
                break_point = max_length
            parts.append(remaining[: break_point + 1].strip())
            remaining = remaining[break_point + 1 :].strip()
        return parts
