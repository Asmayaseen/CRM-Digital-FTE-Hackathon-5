"""
production/workers/metrics_collector.py
MetricsConsumer — batches Kafka metrics events into PostgreSQL agent_metrics table.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

from production.database.queries import record_metric
from production.kafka_client import FTEKafkaConsumer, TOPICS

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

BATCH_SIZE = 50
BATCH_INTERVAL_SECONDS = 10


class MetricsConsumer:
    """
    Consumes from `fte.metrics` topic and batch-inserts into agent_metrics.

    Supported event types:
    - message_processed: dimensions must contain latency_ms, channel, sentiment_score
    - escalation: dimensions must contain channel, reason
    - error: dimensions must contain channel, error_type
    """

    def __init__(self) -> None:
        self._consumer = FTEKafkaConsumer(
            topics=[TOPICS["metrics"]],
            group_id="fte-metrics-collector",
        )
        self._buffer: list[dict] = []
        self._running = False

    async def start(self) -> None:
        await self._consumer.start()
        self._running = True
        logger.info("MetricsConsumer started")
        await asyncio.gather(
            self._consume_loop(),
            self._flush_loop(),
        )

    async def stop(self) -> None:
        self._running = False
        if self._buffer:
            await self._flush()
        await self._consumer.stop()
        logger.info("MetricsConsumer stopped")

    async def _consume_loop(self) -> None:
        async for event in self._consumer.consume():
            if not self._running:
                break
            self._buffer.append(event)
            if len(self._buffer) >= BATCH_SIZE:
                await self._flush()

    async def _flush_loop(self) -> None:
        """Periodic flush every BATCH_INTERVAL_SECONDS."""
        while self._running:
            await asyncio.sleep(BATCH_INTERVAL_SECONDS)
            if self._buffer:
                await self._flush()

    async def _flush(self) -> None:
        batch = self._buffer[:]
        self._buffer.clear()
        for event in batch:
            try:
                await self._process_event(event)
            except Exception as exc:
                logger.error("Failed to record metric event: %s | event=%s", exc, event)

    async def _process_event(self, event: dict) -> None:
        event_type = event.get("event_type", "unknown")
        channel = event.get("channel")
        dimensions = {k: v for k, v in event.items()
                      if k not in ("event_type", "channel", "timestamp")}

        if event_type == "message_processed":
            latency_ms = event.get("latency_ms")
            sentiment_score = event.get("sentiment_score")
            if latency_ms is not None:
                await record_metric(
                    metric_name="latency_ms",
                    metric_value=float(latency_ms),
                    channel=channel,
                    dimensions=dimensions,
                )
            if sentiment_score is not None:
                await record_metric(
                    metric_name="sentiment_score",
                    metric_value=float(sentiment_score),
                    channel=channel,
                    dimensions=dimensions,
                )
        elif event_type == "escalation":
            await record_metric(
                metric_name="escalation_count",
                metric_value=1.0,
                channel=channel,
                dimensions=dimensions,
            )
        elif event_type == "error":
            await record_metric(
                metric_name="error_count",
                metric_value=1.0,
                channel=channel,
                dimensions=dimensions,
            )
        else:
            logger.debug("Unknown event_type '%s' — stored as-is", event_type)
            await record_metric(
                metric_name=event_type,
                metric_value=1.0,
                channel=channel,
                dimensions=dimensions,
            )


async def _main() -> None:
    consumer = MetricsConsumer()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(consumer.stop()))
    await consumer.start()


if __name__ == "__main__":
    asyncio.run(_main())
