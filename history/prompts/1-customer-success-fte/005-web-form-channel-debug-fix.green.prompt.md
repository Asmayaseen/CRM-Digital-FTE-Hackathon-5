---
id: "005"
title: Web Form Channel Debug and Fix
stage: green
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: 1-customer-success-fte
branch: master
user: asmayaseen
command: debug session (continued from context)
labels: ["bugfix","web-form","kafka","asyncio","pgvector","email-validator","groq","llama4"]
links:
  spec: specs/1-customer-success-fte/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - production/channels/web_form_handler.py
  - production/api/main.py
  - production/kafka_client.py
  - production/database/queries.py
  - production/agent/tools.py
  - production/agent/customer_success_agent.py
  - .env
tests:
  - Manual: POST /support/submit → 200 OK with ticket_id
  - Manual: GET /support/ticket/{id} → status + messages
  - Manual: GET /health → healthy
---

## PROMPT_TEXT

(Continuation from compacted session — web form POST was hanging with curl exit 28 / ReadTimeout. Last confirmed state: POST /support/submit times out with valid body; empty body {} returns 422 instantly. Task: diagnose and fix the hanging issue.)

## RESPONSE_TEXT

Diagnosed and fixed 8 bugs blocking the web form channel:

### Root Cause Chain

1. **EmailStr DNS hang** — pydantic `EmailStr` uses `email-validator` v2.3.0 with `dnspython` installed, defaulting to `check_deliverability=True` (blocking DNS MX lookup). Fixed: replaced with `str` field + `validate_email(v, check_deliverability=False)`.

2. **Kafka partial-init hang (primary)** — When `asyncio.wait_for(kafka_producer.start(), timeout=5.0)` times out, the `AIOKafkaProducer` object is assigned to `_producer` but `.start()` was cancelled. The web_form_handler then calls `_kafka_producer.publish()` on this broken producer, which blocks in `send_and_wait()` forever. Fixed: `kafka_producer._producer = None` in the startup except clause + `asyncio.wait_for(..., timeout=5.0)` in `publish()`.

3. **pgvector embedding format** — `search_knowledge_base()` passed a Python `list[float]` to asyncpg but `$1::vector` requires a formatted string `"[x,y,z]"`. Fixed in `queries.py`.

4. **search_knowledge_base tool args** — Tool called `queries.search_knowledge_base(input.query, limit=...)` but function expects `(embedding: list[float], category, max_results)`. Fixed: generate fastembed embedding in executor, pass correct args.

5. **update_ticket_status SQL type conflict** — `$1` used twice in same query (SET + CASE WHEN) causes PostgreSQL to infer conflicting types (text vs varchar). Fixed: `$1::varchar` cast.

6. **send_response not persisting** — Tool formatted response but didn't save to DB. Fixed: added `create_message(role="agent", direction="outbound")` call.

7. **ticket status lookup mismatch** — Form returns a submission UUID but agent creates a different DB ticket UUID. Fixed: fallback query by `channel_message_id` in `get_ticket_status`.

8. **Groq model malformed XML** — `llama-3.3-70b-versatile` generates `<function=name[]{"input":{}}` format that Groq rejects (400). Fixed: switched to `meta-llama/llama-4-scout-17b-16e-instruct` + `ModelSettings(parallel_tool_calls=False)`.

### Final Working Flow

```
POST /support/submit → 200 OK with ticket_id (immediate, < 4s)
  ↓ background task
Agent: create_ticket → get_customer_history → search_knowledge_base → send_response
  ↓ DB persisted
GET /support/ticket/{submission_id} → {status: open|escalated, messages: [customer, agent]}
```
