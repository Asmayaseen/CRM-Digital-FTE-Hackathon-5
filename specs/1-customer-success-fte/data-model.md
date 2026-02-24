# Data Model: Customer Success Digital FTE

**Feature**: 1-customer-success-fte
**Date**: 2026-02-22
**Storage**: PostgreSQL 15+ with `pgvector` extension

---

## Entity Relationship Overview

```text
customers
  │─── customer_identifiers  (one customer → many channel identifiers)
  │─── conversations          (one customer → many conversations)
        │─── messages         (one conversation → many messages)
        │─── tickets          (one conversation → one or more tickets)

knowledge_base                (standalone; indexed by embedding vector)
channel_configs               (one row per channel; configuration store)
agent_metrics                 (append-only time-series; one row per event)
```

---

## Table Definitions

### `customers`

Unified customer identity across all channels.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Internal identifier |
| `email` | VARCHAR(255) | UNIQUE, nullable | Primary cross-channel key |
| `phone` | VARCHAR(50) | nullable | Used when email unknown (WhatsApp) |
| `name` | VARCHAR(255) | nullable | Display name from any channel |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | First contact timestamp |
| `metadata` | JSONB | DEFAULT '{}' | Extensible; channel-specific extras |

**Index**: `idx_customers_email ON customers(email)`

**State transitions**: customers are created on first contact; never deleted
(soft archive via metadata flag if needed).

---

### `customer_identifiers`

Maps channel-specific contact points (email, phone, whatsapp ID) to a unified
customer record. Enables cross-channel identity resolution.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `customer_id` | UUID | FK → customers(id) | |
| `identifier_type` | VARCHAR(50) | NOT NULL | `'email'`, `'phone'`, `'whatsapp'` |
| `identifier_value` | VARCHAR(255) | NOT NULL | The actual email/phone/WA ID |
| `verified` | BOOLEAN | DEFAULT FALSE | Verified via channel confirmation |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Unique constraint**: `(identifier_type, identifier_value)`
**Index**: `idx_customer_identifiers_value ON customer_identifiers(identifier_value)`

**Lookup pattern**:
```sql
SELECT customer_id FROM customer_identifiers
WHERE identifier_type = 'whatsapp' AND identifier_value = '+1234567890';
```

---

### `conversations`

A conversation thread; may span multiple channels and multiple tickets.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `customer_id` | UUID | FK → customers(id) | |
| `initial_channel` | VARCHAR(50) | NOT NULL | Channel that started the conversation |
| `started_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `ended_at` | TIMESTAMPTZ | nullable | Set when resolved or escalated |
| `status` | VARCHAR(50) | DEFAULT 'active' | `active`, `resolved`, `escalated`, `closed` |
| `sentiment_score` | DECIMAL(3,2) | nullable | Latest computed score [0.0, 1.0] |
| `resolution_type` | VARCHAR(50) | nullable | `'ai_resolved'`, `'human_escalated'`, `'abandoned'` |
| `escalated_to` | VARCHAR(255) | nullable | Human agent ID or queue name |
| `metadata` | JSONB | DEFAULT '{}' | Channel switches, tags, custom data |

**Indexes**:
- `idx_conversations_customer ON conversations(customer_id)`
- `idx_conversations_status ON conversations(status)`
- `idx_conversations_channel ON conversations(initial_channel)`

**Active conversation lookup** (within 24 hours):
```sql
SELECT id FROM conversations
WHERE customer_id = $1
  AND status = 'active'
  AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC
LIMIT 1;
```

**State transitions**:
```text
active → resolved     (AI resolved all issues)
active → escalated    (escalation trigger fired)
active → closed       (timed out, no customer response)
escalated → resolved  (human agent resolved)
```

---

### `messages`

Every individual communication unit — inbound from customers and outbound from
agent — with full channel and delivery tracking.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `conversation_id` | UUID | FK → conversations(id) | |
| `channel` | VARCHAR(50) | NOT NULL | `'email'`, `'whatsapp'`, `'web_form'` |
| `direction` | VARCHAR(20) | NOT NULL | `'inbound'`, `'outbound'` |
| `role` | VARCHAR(20) | NOT NULL | `'customer'`, `'agent'`, `'system'` |
| `content` | TEXT | NOT NULL | Full message text |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `tokens_used` | INTEGER | nullable | LLM tokens consumed generating this response |
| `latency_ms` | INTEGER | nullable | Processing time (outbound messages only) |
| `tool_calls` | JSONB | DEFAULT '[]' | Array of tool call records for audit |
| `channel_message_id` | VARCHAR(255) | nullable | External ID (Gmail msg ID, Twilio SID) |
| `delivery_status` | VARCHAR(50) | DEFAULT 'pending' | `'pending'`, `'sent'`, `'delivered'`, `'failed'` |

**Indexes**:
- `idx_messages_conversation ON messages(conversation_id)`
- `idx_messages_channel ON messages(channel)`

**Tool call audit schema** (stored in `tool_calls` JSONB array):
```json
[
  {
    "tool_name": "create_ticket",
    "input": {"customer_id": "...", "channel": "email"},
    "output": "Ticket created: uuid",
    "duration_ms": 45
  }
]
```

**History query** (for `get_customer_history` tool):
```sql
SELECT c.initial_channel, c.started_at, c.status,
       m.content, m.role, m.channel, m.created_at
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
WHERE c.customer_id = $1
ORDER BY m.created_at DESC
LIMIT 20;
```

---

### `tickets`

A discrete support issue; created at the start of every agent interaction.
One conversation may have multiple tickets (re-opened issues).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | Returned to customer as ticket reference |
| `conversation_id` | UUID | FK → conversations(id) | |
| `customer_id` | UUID | FK → customers(id) | Denormalized for fast lookup |
| `source_channel` | VARCHAR(50) | NOT NULL | Channel this ticket originated from |
| `category` | VARCHAR(100) | nullable | `'general'`, `'technical'`, `'billing'`, `'feedback'`, `'bug_report'` |
| `priority` | VARCHAR(20) | DEFAULT 'medium' | `'low'`, `'medium'`, `'high'` |
| `status` | VARCHAR(50) | DEFAULT 'open' | `'open'`, `'in_progress'`, `'escalated'`, `'resolved'`, `'closed'` |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `resolved_at` | TIMESTAMPTZ | nullable | |
| `resolution_notes` | TEXT | nullable | Agent summary or escalation reason |

**Indexes**:
- `idx_tickets_status ON tickets(status)`
- `idx_tickets_channel ON tickets(source_channel)`

**State transitions**:
```text
open → in_progress  (agent processing)
in_progress → resolved   (AI resolved)
in_progress → escalated  (trigger fired)
escalated → resolved     (human resolved)
```

---

### `knowledge_base`

Curated product documentation entries; searched semantically via pgvector.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `title` | VARCHAR(500) | NOT NULL | Article/section title |
| `content` | TEXT | NOT NULL | Full documentation text |
| `category` | VARCHAR(100) | nullable | Docs category for filtering |
| `embedding` | VECTOR(1536) | nullable | `text-embedding-3-small` output |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Index**: `idx_knowledge_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops)`

**Semantic search query**:
```sql
SELECT title, content, category,
       1 - (embedding <=> $1::vector) AS similarity
FROM knowledge_base
WHERE ($2::text IS NULL OR category = $2)
ORDER BY embedding <=> $1::vector
LIMIT $3;
```

**Embedding generation**: `text-embedding-3-small` via OpenAI Embeddings API;
run once on knowledge base load; re-run only when content updates.

---

### `channel_configs`

Runtime configuration for each channel — enables toggling channels without
redeployment.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `channel` | VARCHAR(50) | UNIQUE NOT NULL | `'email'`, `'whatsapp'`, `'web_form'` |
| `enabled` | BOOLEAN | DEFAULT TRUE | Toggle channel on/off |
| `config` | JSONB | NOT NULL | Channel-specific settings (no secrets) |
| `response_template` | TEXT | nullable | Override template for this channel |
| `max_response_length` | INTEGER | nullable | Enforced by formatters.py |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Channel config defaults** (seed data):
```json
{"channel": "email",     "max_response_length": 2000, "enabled": true}
{"channel": "whatsapp",  "max_response_length": 1600, "enabled": true}
{"channel": "web_form",  "max_response_length": 1000, "enabled": true}
```

---

### `agent_metrics`

Append-only time-series for performance tracking and daily report generation.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `metric_name` | VARCHAR(100) | NOT NULL | e.g. `'message_processed'`, `'escalation'` |
| `metric_value` | DECIMAL(10,4) | NOT NULL | Numeric value (latency, score, count) |
| `channel` | VARCHAR(50) | nullable | Channel-specific metric |
| `dimensions` | JSONB | DEFAULT '{}' | Additional dimensions (escalation_reason, etc.) |
| `recorded_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Daily report query**:
```sql
SELECT
    channel,
    COUNT(*) AS total_conversations,
    AVG(CASE WHEN metric_name = 'sentiment_score' THEN metric_value END) AS avg_sentiment,
    COUNT(*) FILTER (WHERE metric_name = 'escalation') AS escalations,
    AVG(CASE WHEN metric_name = 'latency_ms' THEN metric_value END) AS avg_latency_ms
FROM agent_metrics
WHERE recorded_at > NOW() - INTERVAL '24 hours'
GROUP BY channel;
```

---

## Required PostgreSQL Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";     -- pgvector
```

---

## Migration Strategy

- Migrations in `database/migrations/` numbered `001_initial_schema.sql`,
  `002_seed_channel_configs.sql`, etc.
- Apply sequentially via `psql` in docker-compose startup or k8s init container.
- No down migrations in initial version; add as needed for rollback.
- `knowledge_base` embeddings populated by a one-time seed script after schema init.
