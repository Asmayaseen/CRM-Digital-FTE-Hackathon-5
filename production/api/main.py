"""
FastAPI application — production/api/main.py
All channel webhooks, web form router, and management endpoints.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from production.channels.gmail_handler import GmailHandler
from production.channels.web_form_handler import router as web_form_router, set_dependencies
from production.channels.whatsapp_handler import WhatsAppHandler
from production.database.queries import (
    get_channel_metrics_24h,
    get_customer_by_email,
    get_customer_by_phone,
    get_customer_history_query,
    load_conversation_history,
    update_message_delivery_status,
)
from production.kafka_client import FTEKafkaProducer, TOPICS

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Customer Success FTE API",
    description="24/7 AI-powered customer support — Email, WhatsApp, Web Form",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_form_router)

gmail_handler = GmailHandler()
whatsapp_handler = WhatsAppHandler()
kafka_producer = FTEKafkaProducer()
_IS_DEV = os.getenv("ENVIRONMENT", "development") == "development"


async def _process_message_direct(raw_message: dict) -> None:
    """Direct agent processing without Kafka — used when Kafka is unavailable."""
    from production.workers.message_processor import UnifiedMessageProcessor
    processor = UnifiedMessageProcessor()
    await processor.process_message(raw_message)


@app.on_event("startup")
async def startup() -> None:
    try:
        await asyncio.wait_for(kafka_producer.start(), timeout=5.0)
        logger.info("Kafka producer connected")
    except Exception as exc:
        logger.warning("Kafka unavailable — running without message queue: %s", exc)
        kafka_producer._producer = None  # ensure broken partial-init is cleared
    set_dependencies(kafka_producer, None, _process_message_direct)
    logger.info("FTE API started — all channels active")


@app.on_event("shutdown")
async def shutdown() -> None:
    try:
        await kafka_producer.stop()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    from production.database.queries import get_db_pool
    db_status = "active"
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "degraded"

    return {
        "status": "healthy" if db_status == "active" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channels": {
            "email": "active" if gmail_handler.service else "inactive",
            "whatsapp": "active" if whatsapp_handler.account_sid else "inactive",
            "web_form": "active",
        },
        "database": db_status,
    }


# ---------------------------------------------------------------------------
# Gmail webhook
# ---------------------------------------------------------------------------

@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Gmail Pub/Sub push notifications."""
    try:
        body = await request.json()
        messages = await gmail_handler.process_notification(body)
        for message in messages:
            logger.info("Gmail message received from %s: %s",
                        message.get("customer_email"), message.get("subject", "")[:50])
            # Process directly — guarantees AI responds even when Kafka is unavailable
            background_tasks.add_task(_process_message_direct, message)
        return {"status": "processed", "count": len(messages)}
    except Exception as exc:
        logger.error("Gmail webhook error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# WhatsApp webhooks
# ---------------------------------------------------------------------------

@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp messages via Twilio."""
    # Skip signature validation in development (ngrok URL mismatch)
    if not _IS_DEV:
        if not await whatsapp_handler.validate_webhook(request):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    form_data = await request.form()
    message = await whatsapp_handler.process_webhook(dict(form_data))
    logger.info("WhatsApp message received from %s: %s",
                message.get("customer_phone"), message.get("content", "")[:50])

    # Process directly (Kafka not available in dev)
    background_tasks.add_task(_process_message_direct, message)

    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )


@app.post("/webhooks/whatsapp/status")
async def whatsapp_status_webhook(request: Request):
    """Handle Twilio delivery status callbacks."""
    try:
        form_data = await request.form()
        await update_message_delivery_status(
            channel_message_id=form_data.get("MessageSid", ""),
            status=form_data.get("MessageStatus", "unknown"),
        )
    except Exception as exc:
        logger.warning("WhatsApp status update failed: %s", exc)
    return {"status": "received"}


# ---------------------------------------------------------------------------
# Management endpoints
# ---------------------------------------------------------------------------

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    messages = await load_conversation_history(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "messages": messages}


@app.get("/customers/lookup")
async def lookup_customer(email: str | None = None, phone: str | None = None):
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Provide email or phone")

    customer = None
    if email:
        customer = await get_customer_by_email(email)
    elif phone:
        customer = await get_customer_by_phone(phone)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Enrich with history
    history = await get_customer_history_query(str(customer["id"]))
    customer["conversation_count"] = len({r["started_at"] for r in history})
    customer["last_contact"] = history[0]["created_at"].isoformat() if history else None
    return customer


@app.get("/metrics/channels")
async def get_channel_metrics():
    """24-hour performance metrics per channel."""
    rows = await get_channel_metrics_24h()
    return {row["channel"]: row for row in rows}


@app.get("/metrics/summary")
async def get_metrics_summary():
    """Overall system metrics: totals, rates, distributions."""
    from production.database.queries import get_summary_metrics
    return await get_summary_metrics()
