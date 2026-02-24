"""
Incubation prototype — src/channels/gmail_intake.py
Stage 1: Basic Gmail API polling. NOT production code.

Learning goals:
- Understand Gmail API authentication flow
- Parse email thread structure
- Extract sender metadata for cross-channel identity
"""
from __future__ import annotations

import base64
import os
from typing import Any

# In production: google-api-python-client + google-auth-oauthlib
# For incubation: stub returning realistic test data


def _decode_body(payload: dict) -> str:
    """Extract plain-text body from Gmail message payload."""
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")
    return ""


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def parse_gmail_message(raw_message: dict) -> dict:
    """
    Parse a raw Gmail API message into a normalized dict.

    Discovery notes:
    - Gmail wraps multipart in payload.parts[]
    - Reply-To may differ from From — use From for identity
    - Thread ID is critical for conversation continuity
    """
    payload = raw_message.get("payload", {})
    headers = payload.get("headers", [])

    from_header = _get_header(headers, "From")
    # Extract email from "Name <email@domain>" format
    if "<" in from_header and ">" in from_header:
        customer_email = from_header.split("<")[1].rstrip(">")
        customer_name = from_header.split("<")[0].strip().strip('"')
    else:
        customer_email = from_header.strip()
        customer_name = customer_email.split("@")[0]

    return {
        "channel": "email",
        "channel_message_id": raw_message.get("id", ""),
        "thread_id": raw_message.get("threadId", ""),
        "customer_email": customer_email,
        "customer_name": customer_name,
        "subject": _get_header(headers, "Subject"),
        "content": _decode_body(payload),
        "metadata": {
            "date": _get_header(headers, "Date"),
            "message_id": _get_header(headers, "Message-ID"),
            "in_reply_to": _get_header(headers, "In-Reply-To"),
        },
    }


def stub_poll_inbox() -> list[dict]:
    """
    Stub Gmail poller for incubation testing.
    In production: replaced by Pub/Sub push webhook.

    Discovery: Polling has 30-second latency; Pub/Sub is near-real-time.
    Decision: Use Pub/Sub in production (see research.md Decision 4).
    """
    return [
        {
            "id": "stub-001",
            "threadId": "thread-abc",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice Wong <alice@example.com>"},
                    {"name": "Subject", "value": "Cannot sync my files"},
                    {"name": "Date", "value": "2026-02-22T10:00:00Z"},
                    {"name": "Message-ID", "value": "<msg-001@gmail.com>"},
                ],
                "body": {
                    "data": "SSBjYW5ub3Qgc3luYyBteSBmaWxlcyB0byB0aGUgY2xvdWQuIFBsZWFzZSBoZWxwIQ==",
                    # Decoded: "I cannot sync my files to the cloud. Please help!"
                },
            },
        }
    ]


if __name__ == "__main__":
    # Incubation smoke test
    for raw in stub_poll_inbox():
        parsed = parse_gmail_message(raw)
        print(f"Channel: {parsed['channel']}")
        print(f"From: {parsed['customer_email']} ({parsed['customer_name']})")
        print(f"Subject: {parsed['subject']}")
        print(f"Thread: {parsed['thread_id']}")
        print()
