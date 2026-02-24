"""
Incubation prototype — src/channels/web_form_intake.py
Stage 1: Simple FastAPI form endpoint. NOT production code.

Learning goals:
- Validate required fields before agent processing
- Understand category/priority taxonomy
- Test React form ↔ FastAPI contract alignment
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VALID_CATEGORIES = {"general", "technical", "billing", "bug_report", "feedback"}
VALID_PRIORITIES = {"low", "medium", "high"}


@dataclass
class WebFormSubmission:
    name: str
    email: str
    subject: str
    category: str
    priority: str
    message: str


def validate_submission(data: dict) -> tuple[bool, str]:
    """
    Validate a web form submission dict.

    Discovery: Email regex in prototype matches React component's regex.
    This ensures frontend + backend validation are consistent.
    """
    import re

    if not data.get("name") or len(data["name"].strip()) < 2:
        return False, "Name must be at least 2 characters"
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", data.get("email", "")):
        return False, "Invalid email address"
    if not data.get("subject") or len(data["subject"].strip()) < 5:
        return False, "Subject must be at least 5 characters"
    if not data.get("message") or len(data["message"].strip()) < 10:
        return False, "Message must be at least 10 characters"
    if data.get("category") not in VALID_CATEGORIES:
        return False, f"Category must be one of: {', '.join(VALID_CATEGORIES)}"
    if data.get("priority") not in VALID_PRIORITIES:
        return False, f"Priority must be one of: {', '.join(VALID_PRIORITIES)}"
    return True, ""


def normalize_submission(data: dict) -> dict:
    """
    Convert web form dict to normalized message format.

    Discovery: Web form provides richer metadata (category, priority) than
    other channels. Use these to pre-classify before agent processing.
    """
    return {
        "channel": "web_form",
        "channel_message_id": None,  # Assigned after ticket creation
        "customer_email": data["email"],
        "customer_name": data["name"],
        "subject": data["subject"],
        "content": data["message"],
        "metadata": {
            "category": data.get("category", "general"),
            "priority": data.get("priority", "medium"),
        },
    }


def stub_form_submission() -> dict:
    """Realistic web form payload for incubation testing."""
    return {
        "name": "Carol Davies",
        "email": "carol@techcorp.io",
        "subject": "API key not working after reset",
        "category": "technical",
        "priority": "high",
        "message": (
            "I reset my API key yesterday but now all my integrations are broken. "
            "The new key returns 401 Unauthorized on every request. "
            "Please help urgently."
        ),
    }


if __name__ == "__main__":
    # Incubation smoke test
    raw = stub_form_submission()
    valid, err = validate_submission(raw)
    if not valid:
        print(f"Validation failed: {err}")
    else:
        normalized = normalize_submission(raw)
        print(f"Channel: {normalized['channel']}")
        print(f"Email: {normalized['customer_email']}")
        print(f"Category: {normalized['metadata']['category']}")
        print(f"Priority: {normalized['metadata']['priority']}")
        print(f"Content preview: {normalized['content'][:60]}...")
