"""
Incubation prototype — src/channels/whatsapp_intake.py
Stage 1: Twilio webhook parse. NOT production code.

Learning goals:
- Understand Twilio webhook payload structure
- Extract phone number for cross-channel identity
- Learn X-Twilio-Signature validation requirements
"""
from __future__ import annotations

import hashlib
import hmac
import os


def parse_twilio_form(form_data: dict) -> dict:
    """
    Parse a Twilio WhatsApp webhook form payload into a normalized dict.

    Twilio sends application/x-www-form-urlencoded, NOT JSON.
    Key fields: From, Body, MessageSid, ProfileName, WaId

    Discovery notes:
    - From field includes "whatsapp:" prefix — must strip
    - WaId is the raw phone number without country code prefix
    - ProfileName is WhatsApp display name (may differ from CRM name)
    - MediaUrl0..N present for media messages — skip in v1
    """
    raw_from = form_data.get("From", "")
    customer_phone = raw_from.replace("whatsapp:", "").strip()

    return {
        "channel": "whatsapp",
        "channel_message_id": form_data.get("MessageSid", ""),
        "customer_phone": customer_phone,
        "customer_name": form_data.get("ProfileName", ""),
        "wa_id": form_data.get("WaId", ""),
        "content": form_data.get("Body", ""),
        "to_number": form_data.get("To", "").replace("whatsapp:", ""),
        "num_media": int(form_data.get("NumMedia", "0")),
        "metadata": {
            "account_sid": form_data.get("AccountSid", ""),
            "messaging_service_sid": form_data.get("MessagingServiceSid", ""),
        },
    }


def validate_signature_stub(
    auth_token: str, url: str, params: dict, signature: str
) -> bool:
    """
    Twilio signature validation.
    Discovery: HMAC-SHA1 of URL + sorted params using auth token as key.
    Production: Use twilio.request_validator.RequestValidator.
    """
    # Sort params alphabetically and concatenate key+value pairs
    s = url
    for key in sorted(params.keys()):
        s += key + params[key]

    computed = hmac.new(
        auth_token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1
    ).digest()
    import base64

    computed_b64 = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(computed_b64, signature)


def stub_webhook_payload() -> dict:
    """Realistic Twilio WhatsApp webhook payload for incubation testing."""
    return {
        "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "SmsSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "MessagingServiceSid": "",
        "From": "whatsapp:+14155238886",
        "To": "whatsapp:+14155551234",
        "Body": "Hi, I forgot my password. How do I reset it?",
        "NumMedia": "0",
        "ProfileName": "Bob Smith",
        "WaId": "14155238886",
    }


if __name__ == "__main__":
    # Incubation smoke test
    payload = stub_webhook_payload()
    parsed = parse_twilio_form(payload)
    print(f"Channel: {parsed['channel']}")
    print(f"Phone: {parsed['customer_phone']}")
    print(f"Name: {parsed['customer_name']}")
    print(f"Message: {parsed['content']}")
