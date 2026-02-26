"""
Web form channel handler — production/channels/web_form_handler.py
FastAPI router for the support form channel.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, field_validator
from email_validator import validate_email as _validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["support-form"])


class SupportFormSubmission(BaseModel):
    name: str
    email: str
    subject: str
    category: str
    message: str
    priority: Optional[str] = "medium"
    attachments: Optional[list[str]] = []

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        try:
            info = _validate_email(v, check_deliverability=False)
            return info.normalized
        except EmailNotValidError as exc:
            raise ValueError(str(exc))

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("subject")
    @classmethod
    def subject_must_not_be_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("Subject must be at least 5 characters")
        return v.strip()

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("Message must be at least 10 characters")
        return v.strip()

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, v: str) -> str:
        valid = {"general", "technical", "billing", "feedback", "bug_report"}
        if v not in valid:
            raise ValueError(f"Category must be one of: {sorted(valid)}")
        return v

    @field_validator("priority")
    @classmethod
    def priority_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in {"low", "medium", "high"}:
            raise ValueError("Priority must be low, medium, or high")
        return v


class SupportFormResponse(BaseModel):
    ticket_id: str
    message: str
    estimated_response_time: str


class ReplyRequest(BaseModel):
    message: str
    customer_name: str = "Customer"

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("Message must be at least 2 characters")
        return v.strip()


# These are set by api/main.py after startup
_kafka_producer = None
_create_ticket_record = None
_message_processor = None


def set_dependencies(kafka_producer, create_ticket_fn, message_processor=None):
    global _kafka_producer, _create_ticket_record, _message_processor
    _kafka_producer = kafka_producer
    _create_ticket_record = create_ticket_fn
    _message_processor = message_processor


@router.post("/submit", response_model=SupportFormResponse)
async def submit_support_form(submission: SupportFormSubmission, background_tasks: BackgroundTasks):
    """
    Accept a support form submission, create a ticket, publish to Kafka,
    and return confirmation to the customer.
    """
    ticket_id = str(uuid.uuid4())

    message_data = {
        "channel": "web_form",
        "channel_message_id": ticket_id,
        "customer_email": str(submission.email),
        "customer_name": submission.name,
        "subject": submission.subject,
        "content": submission.message,
        "category": submission.category,
        "priority": submission.priority or "medium",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "form_version": "1.0",
            "attachments": submission.attachments or [],
        },
    }

    try:
        if _message_processor:
            # Always process directly — guarantees ticket is created and AI responds
            background_tasks.add_task(_message_processor, message_data)
        else:
            logger.warning("No message processor available — ticket %s not processed", ticket_id)
    except Exception as exc:
        logger.error("Failed to process web form ticket: %s", exc)

    return SupportFormResponse(
        ticket_id=ticket_id,
        message="Thank you for contacting us! Our AI assistant will respond shortly.",
        estimated_response_time="Usually within 5 minutes",
    )


@router.get("/ticket/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    """Return ticket status and conversation history."""
    from production.database.queries import get_ticket_by_id, load_conversation_history, get_db_pool

    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        # Fallback: look up by channel_message_id (form submission ID stored in messages)
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT t.*, cust.email as customer_email, cust.name as customer_name
                       FROM tickets t
                       JOIN conversations conv ON conv.id = t.conversation_id
                       JOIN customers cust ON cust.id = t.customer_id
                       WHERE EXISTS (
                           SELECT 1 FROM messages m
                           WHERE m.conversation_id = conv.id
                           AND m.channel_message_id = $1
                       )
                       ORDER BY t.created_at DESC LIMIT 1""",
                    ticket_id
                )
                if row:
                    ticket = dict(row)
        except Exception:
            pass
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    messages = []
    if ticket.get("conversation_id"):
        messages = await load_conversation_history(str(ticket["conversation_id"]))

    return {
        "ticket_id": ticket_id,
        "status": ticket["status"],
        "customer_name": ticket.get("customer_name"),
        "messages": messages,
        "created_at": ticket["created_at"].isoformat() if ticket.get("created_at") else None,
        "last_updated": ticket["resolved_at"].isoformat() if ticket.get("resolved_at") else None,
    }


@router.post("/ticket/{ticket_id}/reply")
async def reply_to_ticket(ticket_id: str, body: ReplyRequest, background_tasks: BackgroundTasks):
    """Accept a follow-up message on an existing ticket and queue it for agent processing."""
    from production.database.queries import get_ticket_by_id, get_db_pool

    ticket = None
    try:
        ticket = await get_ticket_by_id(ticket_id)
    except Exception:
        pass

    if not ticket:
        # Fallback: look up by channel_message_id (form submission UUID stored in messages)
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT t.*, cust.email as customer_email, cust.name as customer_name
                       FROM tickets t
                       JOIN conversations conv ON conv.id = t.conversation_id
                       JOIN customers cust ON cust.id = t.customer_id
                       WHERE EXISTS (
                           SELECT 1 FROM messages m
                           WHERE m.conversation_id = conv.id
                           AND m.channel_message_id = $1
                       )
                       ORDER BY t.created_at DESC LIMIT 1""",
                    ticket_id
                )
                if row:
                    ticket = dict(row)
        except Exception:
            pass

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.get("status") in ("closed", "resolved"):
        raise HTTPException(status_code=422, detail="Cannot reply to a closed or resolved ticket")

    customer_email = ticket.get("customer_email", "")
    customer_name = body.customer_name if body.customer_name != "Customer" else (ticket.get("customer_name") or "Customer")

    message_data = {
        "channel": "web_form",
        "channel_message_id": ticket_id,  # same as original → keeps same conversation thread
        "customer_email": customer_email,
        "customer_name": customer_name,
        "subject": f"Re: {ticket.get('subject', 'Support Request')}",
        "content": body.message,
        "category": ticket.get("category", "general"),
        "priority": ticket.get("priority", "medium"),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "form_version": "1.0",
            "attachments": [],
            "is_reply": True,
        },
    }

    if _message_processor:
        # Always process directly — guarantees AI responds to follow-up
        background_tasks.add_task(_message_processor, message_data)
    else:
        logger.warning("No message processor — reply for ticket %s not processed", ticket_id)

    return {"status": "received", "ticket_id": ticket_id}
