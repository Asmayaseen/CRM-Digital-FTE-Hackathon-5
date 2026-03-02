"""
Gmail channel handler — production/channels/gmail_handler.py
Handles Gmail Pub/Sub push notifications and outbound email replies.
"""
from __future__ import annotations

import base64
import email as email_lib
import json
import logging
import os
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailHandler:
    def __init__(self, credentials_path: str | None = None) -> None:
        path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH", "")
        try:
            self.credentials = Credentials.from_authorized_user_file(path)
            self.service = build("gmail", "v1", credentials=self.credentials)
        except Exception as exc:
            logger.warning("Gmail credentials not loaded: %s", exc)
            self.service = None

    async def setup_push_notifications(self, topic_name: str) -> dict:
        """Register Gmail push notifications via Google Cloud Pub/Sub."""
        if not self.service:
            raise RuntimeError("Gmail service not initialised")
        request = {
            "labelIds": ["INBOX"],
            "topicName": topic_name,
            "labelFilterAction": "include",
        }
        return self.service.users().watch(userId="me", body=request).execute()

    async def process_notification(self, pubsub_message: dict) -> list[dict]:
        """Process a Pub/Sub push notification; return list of normalised messages."""
        if not self.service:
            logger.error("Gmail service not initialised — skipping notification")
            return []

        try:
            # Decode the Pub/Sub message
            data_b64 = pubsub_message.get("message", {}).get("data", "")
            data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
            history_id = data.get("historyId")

            history = (
                self.service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=history_id,
                    historyTypes=["messageAdded"],
                )
                .execute()
            )

            messages = []
            for record in history.get("history", []):
                for msg_added in record.get("messagesAdded", []):
                    msg_id = msg_added["message"]["id"]
                    message = await self.get_message(msg_id)
                    if message:
                        messages.append(message)
            return messages

        except Exception as exc:
            logger.error("Failed to process Gmail notification: %s", exc)
            return []

    async def get_message(self, message_id: str) -> dict | None:
        """Fetch and normalise a single Gmail message."""
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            # Case-insensitive header lookup (Gmail API returns inconsistent casing)
            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
            body = self._extract_body(msg["payload"])

            return {
                "channel": "email",
                "channel_message_id": message_id,
                "customer_email": self._extract_email(headers.get("from", "")),
                "customer_name": self._extract_name(headers.get("from", "")),
                "subject": headers.get("subject", "Support Request"),
                "content": body,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "thread_id": msg.get("threadId"),
                "metadata": {
                    "headers": {
                        k: v for k, v in headers.items()
                        if k in ("from", "to", "subject", "date", "message-id")
                    },
                    "labels": msg.get("labelIds", []),
                },
            }
        except Exception as exc:
            logger.error("Failed to fetch Gmail message %s: %s", message_id, exc)
            return None

    async def send_reply(self, to_email: str, subject: str, body: str,
                          thread_id: str | None = None) -> dict:
        """Send an email reply via Gmail API."""
        if not self.service:
            logger.error("Gmail service not initialised — cannot send reply")
            return {"delivery_status": "failed", "channel_message_id": None}

        try:
            message = MIMEText(body)
            message["to"] = to_email
            message["subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            send_request: dict = {"raw": raw}
            if thread_id:
                send_request["threadId"] = thread_id

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body=send_request)
                .execute()
            )
            return {"channel_message_id": result["id"], "delivery_status": "sent"}
        except Exception as exc:
            logger.error("Failed to send Gmail reply to %s: %s", to_email, exc)
            return {"delivery_status": "failed", "channel_message_id": None}

    def _extract_body(self, payload: dict) -> str:
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part["body"].get("data"):
                    return base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8")
        return ""

    def _extract_email(self, from_header: str) -> str:
        match = re.search(r"<(.+?)>", from_header)
        return match.group(1) if match else from_header.strip()

    def _extract_name(self, from_header: str) -> str:
        match = re.match(r"^(.+?)\s*<", from_header)
        return match.group(1).strip().strip('"') if match else ""
