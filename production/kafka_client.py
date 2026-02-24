"""
Kafka client — production/kafka_client.py
FTEKafkaProducer and FTEKafkaConsumer with all defined topics.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Awaitable, Callable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Authoritative topic registry — all inter-service communication uses these
TOPICS = {
    "tickets_incoming":   "fte.tickets.incoming",
    "email_inbound":      "fte.channels.email.inbound",
    "whatsapp_inbound":   "fte.channels.whatsapp.inbound",
    "webform_inbound":    "fte.channels.webform.inbound",
    "email_outbound":     "fte.channels.email.outbound",
    "whatsapp_outbound":  "fte.channels.whatsapp.outbound",
    "escalations":        "fte.escalations",
    "metrics":            "fte.metrics",
    "dlq":                "fte.dlq",
}


class FTEKafkaProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, topic: str, event: dict) -> None:
        if not self._producer:
            logger.warning("Kafka unavailable — dropping event to %s: %s", topic, event.get("event_type", "unknown"))
            return
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        try:
            await asyncio.wait_for(self._producer.send_and_wait(topic, event), timeout=5.0)
            logger.debug("Published to %s: %s", topic, event.get("event_type", "unknown"))
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("Kafka publish failed for %s: %s", topic, exc)


class FTEKafkaConsumer:
    def __init__(self, topics: list[str], group_id: str) -> None:
        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )

    async def start(self) -> None:
        await self._consumer.start()
        logger.info("Kafka consumer started (group=%s)", self._consumer._group_id)

    async def stop(self) -> None:
        await self._consumer.stop()
        logger.info("Kafka consumer stopped")

    async def consume(
        self, handler: Callable[[str, dict], Awaitable[None]]
    ) -> None:
        async for msg in self._consumer:
            try:
                await handler(msg.topic, msg.value)
            except Exception as exc:
                logger.error(
                    "Consumer handler failed on topic %s: %s", msg.topic, exc
                )
