"""
production/workers/message_processor.py
UnifiedMessageProcessor — Kafka consumer that drives the agent for every
inbound ticket across all three channels.

Entry point for the fte-message-processor Kubernetes Deployment.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any

from agents import Runner

from production.agent.customer_success_agent import customer_success_agent
from production.agent.formatters import format_for_channel
from production.database import queries
from production.kafka_client import FTEKafkaConsumer, FTEKafkaProducer, TOPICS

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


class UnifiedMessageProcessor:
    """
    Consumes messages from the `fte.tickets.incoming` Kafka topic and
    orchestrates the full agent processing pipeline per message.

    Pipeline per message:
      1. Resolve customer identity (email or phone → UUID)
      2. Get or create active conversation
      3. Store inbound message
      4. Build context string (history + metadata)
      5. Run agent with Runner.run()
      6. Store outbound message (agent writes via send_response tool)
      7. Publish metrics event
    """

    def __init__(self) -> None:
        self._consumer = FTEKafkaConsumer(
            topics=[TOPICS["tickets_incoming"]],
            group_id="fte-message-processor",
        )
        self._producer = FTEKafkaProducer()
        self._running = False

    async def start(self) -> None:
        await self._consumer.start()
        await self._producer.start()
        self._running = True
        logger.info("UnifiedMessageProcessor started — consuming %s", TOPICS["tickets_incoming"])
        try:
            await self._consume_loop()
        finally:
            await self.stop()

    async def stop(self) -> None:
        self._running = False
        await self._consumer.stop()
        await self._producer.stop()
        logger.info("UnifiedMessageProcessor stopped")

    async def _consume_loop(self) -> None:
        async for message in self._consumer.consume():
            if not self._running:
                break
            try:
                await self.process_message(message)
            except Exception as exc:
                logger.exception("Unhandled error processing message: %s", exc)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    async def process_message(self, raw_message: dict) -> None:
        """Full processing pipeline for a single inbound ticket message."""
        channel = raw_message.get("channel", "web_form")
        customer_email = raw_message.get("customer_email")
        customer_phone = raw_message.get("customer_phone")
        customer_name = raw_message.get("customer_name", "Customer")
        content = raw_message.get("content", "")

        if not content.strip():
            logger.warning("Empty message received, skipping")
            return

        import time
        start_time = time.monotonic()

        try:
            # Step 1: Resolve customer
            customer_id = await self._resolve_customer(
                email=customer_email,
                phone=customer_phone,
                name=customer_name,
                channel=channel,
            )

            # Step 2: Get or create conversation
            conversation_id = await self._get_or_create_conversation(
                customer_id=customer_id,
                channel=channel,
            )

            # Step 3: Store inbound message
            await queries.create_message(
                conversation_id=conversation_id,
                role="customer",
                direction="inbound",
                content=content,
                channel=channel,
                channel_message_id=raw_message.get("channel_message_id"),
            )

            # Step 4: Build agent context prompt
            agent_input = self._build_agent_input(
                content=content,
                channel=channel,
                customer_id=customer_id,
                customer_name=customer_name,
                conversation_id=conversation_id,
            )

            # Step 5: Run agent
            result = await Runner.run(customer_success_agent, agent_input)
            logger.info(
                "Agent completed | customer=%s channel=%s",
                customer_id, channel
            )

            # Step 5b: Deliver agent response via channel
            await self._deliver_response(
                conversation_id=conversation_id,
                channel=channel,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_name=customer_name,
                raw_message=raw_message,
            )

            # Step 6: Publish metrics
            latency_ms = int((time.monotonic() - start_time) * 1000)
            await self._producer.publish(
                TOPICS["metrics"],
                {
                    "event_type": "message_processed",
                    "customer_id": customer_id,
                    "conversation_id": str(conversation_id),
                    "channel": channel,
                    "latency_ms": latency_ms,
                },
            )

        except Exception as exc:
            logger.exception(
                "Processing failed for channel=%s customer_email=%s: %s",
                channel, customer_email, exc
            )
            await self.handle_error(
                channel=channel,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_name=customer_name,
                original_message=raw_message,
                error=exc,
            )

    # ------------------------------------------------------------------
    # Customer resolution
    # ------------------------------------------------------------------

    async def _resolve_customer(
        self,
        email: str | None,
        phone: str | None,
        name: str,
        channel: str,
    ) -> str:
        """
        Resolve to a unified customer_id.

        Lookup order:
        1. email in customers table (primary)
        2. phone in customer_identifiers table (WhatsApp)
        3. Create new customer record
        """
        customer_id = await queries.get_or_create_customer(
            email=email,
            phone=phone,
            name=name,
        )
        # Link phone as identifier if both email and phone are present
        if email and phone and channel == "whatsapp":
            try:
                await queries.create_customer_identifier(
                    customer_id=customer_id,
                    identifier_type="whatsapp",
                    identifier_value=phone,
                )
            except Exception:
                pass  # Already linked; ignore duplicate
        return customer_id

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------
    # Channel delivery
    # ------------------------------------------------------------------

    async def _deliver_response(
        self,
        conversation_id: str,
        channel: str,
        customer_email: str | None,
        customer_phone: str | None,
        customer_name: str,
        raw_message: dict,
    ) -> None:
        """Send the agent's last outbound message via the actual channel (Gmail/Twilio)."""
        try:
            # Fetch the most recent agent outbound message for this conversation
            rows = await queries.get_last_agent_message(conversation_id)
            if not rows:
                logger.warning("No agent message found to deliver for conv=%s", conversation_id)
                return

            message_id = rows["id"]
            content = rows["content"]
            subject = raw_message.get("subject", "Re: Support Request")
            thread_id = raw_message.get("thread_id")

            if channel == "email" and customer_email:
                from production.channels.gmail_handler import GmailHandler
                handler = GmailHandler()
                result = await handler.send_reply(
                    to_email=customer_email,
                    subject=subject if subject.startswith("Re:") else f"Re: {subject}",
                    body=content,
                    thread_id=thread_id,
                )
                delivery_status = result.get("delivery_status", "failed")
                sent_id = result.get("channel_message_id")
                await queries.update_message_delivery_status(
                    channel_message_id=str(message_id),
                    status=delivery_status,
                )
                logger.info(
                    "Gmail reply sent to %s | status=%s | sent_id=%s",
                    customer_email, delivery_status, sent_id
                )

            elif channel == "whatsapp" and customer_phone:
                from production.channels.whatsapp_handler import WhatsAppHandler
                handler = WhatsAppHandler()
                result = await handler.send_message(customer_phone, content)
                delivery_status = result.get("delivery_status", "failed")
                await queries.update_message_delivery_status(
                    channel_message_id=str(message_id),
                    status=delivery_status,
                )
                logger.info(
                    "WhatsApp reply sent to %s | status=%s",
                    customer_phone, delivery_status
                )

        except Exception as exc:
            logger.error("_deliver_response failed for conv=%s: %s", conversation_id, exc)

    # ------------------------------------------------------------------

    async def _get_or_create_conversation(
        self,
        customer_id: str,
        channel: str,
    ) -> str:
        """Return active conversation_id or create a new one."""
        existing = await queries.get_active_conversation(customer_id)
        if existing:
            return str(existing)
        return await queries.create_conversation(
            customer_id=customer_id,
            channel=channel,
        )

    # ------------------------------------------------------------------
    # Agent input construction
    # ------------------------------------------------------------------

    def _build_agent_input(
        self,
        content: str,
        channel: str,
        customer_id: str,
        customer_name: str,
        conversation_id: str,
    ) -> str:
        """
        Build the user-turn message passed to the agent.
        Provides channel + customer context so the agent can call tools correctly.
        """
        return (
            f"[CONTEXT]\n"
            f"channel: {channel}\n"
            f"customer_id: {customer_id}\n"
            f"customer_name: {customer_name}\n"
            f"conversation_id: {conversation_id}\n\n"
            f"[CUSTOMER MESSAGE]\n{content}"
        )

    # ------------------------------------------------------------------
    # Error handling (DLQ)
    # ------------------------------------------------------------------

    async def handle_error(
        self,
        channel: str,
        customer_email: str | None,
        customer_phone: str | None,
        customer_name: str,
        original_message: dict,
        error: Exception,
    ) -> None:
        """
        Send an apology message and publish to the dead-letter queue.
        Never raises — this is a last-resort error path.
        """
        apology = format_for_channel(
            response=(
                "We're sorry, we encountered an issue processing your request. "
                "A member of our team will follow up with you shortly."
            ),
            channel=channel,
            customer_name=customer_name,
        )

        # Best-effort delivery of apology
        try:
            if channel == "email" and customer_email:
                from production.channels.gmail_handler import GmailHandler
                handler = GmailHandler()
                # Simplified — in production: get thread_id from original_message
                logger.info("Would send email apology to %s", customer_email)
            elif channel == "whatsapp" and customer_phone:
                from production.channels.whatsapp_handler import WhatsAppHandler
                handler = WhatsAppHandler()
                await handler.send_message(customer_phone, apology)
        except Exception as delivery_err:
            logger.error("Apology delivery also failed: %s", delivery_err)

        # Always publish to DLQ
        try:
            await self._producer.publish(
                TOPICS["dlq"],
                {
                    "original_message": original_message,
                    "error": str(error),
                    "channel": channel,
                    "requires_human": True,
                },
            )
        except Exception as dlq_err:
            logger.critical("DLQ publish failed: %s", dlq_err)


# ---------------------------------------------------------------------------
# Entry point for Kubernetes fte-message-processor deployment
# ---------------------------------------------------------------------------

async def _main() -> None:
    processor = UnifiedMessageProcessor()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(processor.stop()))

    await processor.start()


if __name__ == "__main__":
    asyncio.run(_main())
