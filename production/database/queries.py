"""
Typed async database query functions — production/database/queries.py
All queries use asyncpg directly (no ORM).
"""
from __future__ import annotations

import asyncpg
import os
import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Neon / cloud DB — use full URL with SSL
            _pool = await asyncpg.create_pool(
                database_url,
                ssl="require",
                min_size=1,
                max_size=5,
                timeout=10.0,
                command_timeout=15.0,
            )
        else:
            ssl_mode = os.getenv("POSTGRES_SSL", "disable")
            _pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "fte_db"),
                user=os.getenv("POSTGRES_USER", "fte_user"),
                password=os.getenv("POSTGRES_PASSWORD", "changeme"),
                ssl=ssl_mode if ssl_mode != "disable" else None,
                min_size=2,
                max_size=10,
                timeout=5.0,
                command_timeout=10.0,
            )
    return _pool


# ---------------------------------------------------------------------------
# Customer queries
# ---------------------------------------------------------------------------

async def get_or_create_customer(email: Optional[str] = None,
                                  phone: Optional[str] = None,
                                  name: Optional[str] = None) -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if email:
            row = await conn.fetchrow(
                "SELECT id FROM customers WHERE email = $1", email
            )
            if row:
                return str(row["id"])
            cid = await conn.fetchval(
                "INSERT INTO customers (email, name) VALUES ($1, $2) RETURNING id",
                email, name or ""
            )
        elif phone:
            row = await conn.fetchrow(
                "SELECT customer_id FROM customer_identifiers "
                "WHERE identifier_type = 'whatsapp' AND identifier_value = $1",
                phone
            )
            if row:
                return str(row["customer_id"])
            cid = await conn.fetchval(
                "INSERT INTO customers (phone) VALUES ($1) RETURNING id", phone
            )
            await conn.execute(
                "INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value) "
                "VALUES ($1, 'whatsapp', $2) ON CONFLICT DO NOTHING",
                cid, phone
            )
        else:
            raise ValueError("Must provide email or phone")
        return str(cid)


async def get_customer_by_email(email: str) -> Optional[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, phone, name, created_at FROM customers WHERE email = $1",
            email
        )
        return dict(row) if row else None


async def get_customer_by_phone(phone: str) -> Optional[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT c.id, c.email, c.phone, c.name, c.created_at
               FROM customers c
               JOIN customer_identifiers ci ON ci.customer_id = c.id
               WHERE ci.identifier_type = 'whatsapp' AND ci.identifier_value = $1""",
            phone
        )
        return dict(row) if row else None


async def create_customer_identifier(customer_id: str,
                                      identifier_type: str,
                                      identifier_value: str) -> None:
    """Alias for link_customer_identifier — used by message_processor."""
    return await link_customer_identifier(customer_id, identifier_type, identifier_value)


async def link_customer_identifier(customer_id: str,
                                    identifier_type: str,
                                    identifier_value: str) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO customer_identifiers
               (customer_id, identifier_type, identifier_value)
               VALUES ($1, $2, $3)
               ON CONFLICT (identifier_type, identifier_value) DO NOTHING""",
            UUID(customer_id), identifier_type, identifier_value
        )


# ---------------------------------------------------------------------------
# Conversation queries
# ---------------------------------------------------------------------------

async def get_active_conversation(customer_id: str) -> Optional[str]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id FROM conversations
               WHERE customer_id = $1
                 AND status = 'active'
                 AND started_at > NOW() - INTERVAL '24 hours'
               ORDER BY started_at DESC
               LIMIT 1""",
            UUID(customer_id)
        )
        return str(row["id"]) if row else None


async def create_conversation(customer_id: str, channel: str) -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        cid = await conn.fetchval(
            """INSERT INTO conversations (customer_id, initial_channel, status)
               VALUES ($1, $2, 'active')
               RETURNING id""",
            UUID(customer_id), channel
        )
        return str(cid)


async def update_conversation_status(conversation_id: str,
                                      status: str,
                                      resolution_type: Optional[str] = None,
                                      escalated_to: Optional[str] = None) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE conversations
               SET status = $1, resolution_type = $2, escalated_to = $3,
                   ended_at = CASE WHEN $1 != 'active' THEN NOW() ELSE ended_at END
               WHERE id = $4""",
            status, resolution_type, escalated_to, UUID(conversation_id)
        )


async def update_conversation_sentiment(conversation_id: str,
                                         score: float) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE conversations SET sentiment_score = $1 WHERE id = $2",
            score, UUID(conversation_id)
        )


# ---------------------------------------------------------------------------
# Message queries
# ---------------------------------------------------------------------------

async def create_message(conversation_id: str,
                          channel: str,
                          direction: str,
                          role: str,
                          content: str,
                          tokens_used: Optional[int] = None,
                          latency_ms: Optional[int] = None,
                          tool_calls: Optional[list] = None,
                          channel_message_id: Optional[str] = None,
                          delivery_status: str = "pending") -> str:
    pool = await get_db_pool()
    import json
    async with pool.acquire() as conn:
        mid = await conn.fetchval(
            """INSERT INTO messages
               (conversation_id, channel, direction, role, content,
                tokens_used, latency_ms, tool_calls, channel_message_id, delivery_status)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               RETURNING id""",
            UUID(conversation_id), channel, direction, role, content,
            tokens_used, latency_ms,
            json.dumps(tool_calls or []),
            channel_message_id, delivery_status
        )
        return str(mid)


async def update_message_delivery_status(channel_message_id: str,
                                          status: str) -> None:
    """Update delivery status — accepts either a channel_message_id string or a UUID (message.id)."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Try UUID match (message primary key) first, then channel_message_id string
        try:
            parsed_uuid = UUID(channel_message_id)
            await conn.execute(
                "UPDATE messages SET delivery_status = $1 WHERE id = $2",
                status, parsed_uuid
            )
        except (ValueError, Exception):
            await conn.execute(
                "UPDATE messages SET delivery_status = $1 WHERE channel_message_id = $2",
                status, channel_message_id
            )


async def get_last_agent_message(conversation_id: str) -> Optional[dict]:
    """Return the most recent agent outbound message for a conversation."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, content, delivery_status, channel_message_id
               FROM messages
               WHERE conversation_id = $1
                 AND role = 'agent'
                 AND direction = 'outbound'
               ORDER BY created_at DESC
               LIMIT 1""",
            UUID(conversation_id)
        )
        if not row:
            return None
        return {"id": row["id"], "content": row["content"],
                "delivery_status": row["delivery_status"],
                "channel_message_id": row["channel_message_id"]}


async def load_conversation_history(conversation_id: str) -> list[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT role, content, channel, created_at
               FROM messages
               WHERE conversation_id = $1
               ORDER BY created_at ASC""",
            UUID(conversation_id)
        )
        return [{"role": r["role"], "content": r["content"],
                 "channel": r["channel"]} for r in rows]


async def get_customer_history_query(customer_id: str) -> list[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT c.initial_channel, c.started_at, c.status,
                      m.content, m.role, m.channel, m.created_at
               FROM conversations c
               JOIN messages m ON m.conversation_id = c.id
               WHERE c.customer_id = $1
               ORDER BY m.created_at DESC
               LIMIT 20""",
            UUID(customer_id)
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Ticket queries
# ---------------------------------------------------------------------------

async def create_ticket(customer_id: str,
                         conversation_id: str,
                         source_channel: str,
                         category: Optional[str] = None,
                         priority: str = "medium") -> str:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        tid = await conn.fetchval(
            """INSERT INTO tickets
               (customer_id, conversation_id, source_channel, category, priority, status)
               VALUES ($1, $2, $3, $4, $5, 'open')
               RETURNING id""",
            UUID(customer_id), UUID(conversation_id), source_channel, category, priority
        )
        return str(tid)


async def update_ticket_status(ticket_id: str,
                                status: str,
                                resolution_notes: Optional[str] = None) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE tickets
               SET status = $1::varchar,
                   resolution_notes = COALESCE($2, resolution_notes),
                   resolved_at = CASE WHEN $1::varchar IN ('resolved','closed') THEN NOW() ELSE resolved_at END
               WHERE id = $3""",
            status, resolution_notes, UUID(ticket_id)
        )


async def get_ticket_by_id(ticket_id: str) -> Optional[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT t.*, c.email as customer_email, c.phone as customer_phone
               FROM tickets t
               JOIN customers c ON c.id = t.customer_id
               WHERE t.id = $1""",
            UUID(ticket_id)
        )
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Knowledge base queries
# ---------------------------------------------------------------------------

async def search_knowledge_base(embedding: list[float],
                                  category: Optional[str],
                                  max_results: int = 5) -> list[dict]:
    # asyncpg requires pgvector as a formatted string, not a Python list
    embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT title, content, category,
                      1 - (embedding <=> $1::vector) AS similarity
               FROM knowledge_base
               WHERE ($2::text IS NULL OR category = $2)
               ORDER BY embedding <=> $1::vector
               LIMIT $3""",
            embedding_str, category, max_results
        )
        return [dict(r) for r in rows]


async def insert_knowledge_entry(title: str,
                                   content: str,
                                   category: Optional[str],
                                   embedding: list[float]) -> str:
    # pgvector expects a string like '[0.1, 0.2, ...]' via asyncpg
    embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        kid = await conn.fetchval(
            """INSERT INTO knowledge_base (title, content, category, embedding)
               VALUES ($1, $2, $3, $4::vector)
               ON CONFLICT DO NOTHING
               RETURNING id""",
            title, content, category, embedding_str
        )
        return str(kid)


# ---------------------------------------------------------------------------
# Metrics queries
# ---------------------------------------------------------------------------

async def record_metric(metric_name: str,
                         metric_value: float,
                         channel: Optional[str] = None,
                         dimensions: Optional[dict] = None) -> None:
    pool = await get_db_pool()
    import json
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO agent_metrics (metric_name, metric_value, channel, dimensions)
               VALUES ($1, $2, $3, $4)""",
            metric_name, metric_value, channel, json.dumps(dimensions or {})
        )


async def get_channel_metrics_24h() -> list[dict]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT
                   initial_channel AS channel,
                   COUNT(*) AS total_conversations,
                   AVG(sentiment_score) AS avg_sentiment,
                   COUNT(*) FILTER (WHERE status = 'escalated') AS escalations
               FROM conversations
               WHERE started_at > NOW() - INTERVAL '24 hours'
               GROUP BY initial_channel""",
        )
        metrics = [dict(r) for r in rows]

        # Enrich with latency from agent_metrics
        for m in metrics:
            lat_row = await conn.fetchrow(
                """SELECT AVG(metric_value) AS avg_latency_ms
                   FROM agent_metrics
                   WHERE metric_name = 'latency_ms'
                     AND channel = $1
                     AND recorded_at > NOW() - INTERVAL '24 hours'""",
                m["channel"]
            )
            m["avg_latency_ms"] = float(lat_row["avg_latency_ms"]) if lat_row["avg_latency_ms"] else None
        return metrics


async def get_summary_metrics() -> dict:
    """Aggregate system-wide metrics: totals, rates, and distributions."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Scalar counts
        tickets_24h = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
        tickets_total = await conn.fetchval("SELECT COUNT(*) FROM tickets")
        customers_total = await conn.fetchval("SELECT COUNT(*) FROM customers")
        messages_24h = await conn.fetchval(
            "SELECT COUNT(*) FROM messages WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
        conversations_24h = await conn.fetchval(
            "SELECT COUNT(*) FROM conversations WHERE started_at > NOW() - INTERVAL '24 hours'"
        )
        escalations_24h = await conn.fetchval(
            "SELECT COUNT(*) FROM conversations WHERE status = 'escalated' AND started_at > NOW() - INTERVAL '24 hours'"
        )

        # Escalation rate (%)
        escalation_rate = (
            round(float(escalations_24h) / float(conversations_24h) * 100, 1)
            if conversations_24h
            else 0.0
        )

        # Average latency from agent_metrics
        lat_row = await conn.fetchrow(
            """SELECT AVG(metric_value) AS avg_latency_ms
               FROM agent_metrics
               WHERE metric_name = 'latency_ms'
                 AND recorded_at > NOW() - INTERVAL '24 hours'"""
        )
        avg_latency_ms = (
            round(float(lat_row["avg_latency_ms"]), 1) if lat_row["avg_latency_ms"] else None
        )

        # Ticket status distribution
        status_rows = await conn.fetch(
            "SELECT status, COUNT(*) AS cnt FROM tickets GROUP BY status"
        )
        ticket_status = {r["status"]: int(r["cnt"]) for r in status_rows}
        for s in ("open", "in_progress", "resolved", "closed", "escalated"):
            ticket_status.setdefault(s, 0)

        # Ticket count by channel (from conversations)
        channel_rows = await conn.fetch(
            """SELECT initial_channel AS channel, COUNT(*) AS cnt
               FROM conversations
               WHERE started_at > NOW() - INTERVAL '24 hours'
               GROUP BY initial_channel"""
        )
        ticket_by_channel = {r["channel"]: int(r["cnt"]) for r in channel_rows}
        for ch in ("gmail", "whatsapp", "web_form"):
            ticket_by_channel.setdefault(ch, 0)

    return {
        "tickets_24h": int(tickets_24h),
        "tickets_total": int(tickets_total),
        "customers_total": int(customers_total),
        "messages_24h": int(messages_24h),
        "conversations_24h": int(conversations_24h),
        "escalations_24h": int(escalations_24h),
        "escalation_rate_pct": escalation_rate,
        "avg_latency_ms": avg_latency_ms,
        "ticket_status": ticket_status,
        "ticket_by_channel": ticket_by_channel,
    }
