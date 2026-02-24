<!--
  SYNC IMPACT REPORT
  ==================
  Version change: (none) → 1.0.0
  Added sections:
    - Core Principles (I–X)
    - Technology Stack
    - Development Workflow
    - Governance
  Modified principles: N/A (initial creation)
  Removed sections: N/A
  Templates requiring updates:
    - ✅ .specify/templates/plan-template.md  — Constitution Check gates align
    - ✅ .specify/templates/spec-template.md  — Channel + escalation constraints noted
    - ✅ .specify/templates/tasks-template.md — Task categories reflect principles
  Deferred TODOs: none
-->

# Customer Success Digital FTE — Project Constitution

## Core Principles

### I. Multi-Channel First

Every feature, tool, response, and data model MUST explicitly account for all
three supported intake channels: **Email (Gmail)**, **WhatsApp (Twilio)**, and
**Web Form**. Channel identity MUST be stored in every ticket, message, and
conversation record.

- Response formatting MUST adapt to channel constraints:
  - Email: formal, full-length (≤ 500 words), greeting + signature required
  - WhatsApp: conversational, concise (≤ 300 characters preferred, ≤ 1600 hard)
  - Web Form: semi-formal (≤ 300 words)
- A feature that works for only one channel is considered incomplete.
- Channel switching by the same customer MUST be detected and cross-linked via
  `customer_identifiers` table.

### II. Agent Maturity Model — Incubation before Specialization

Development MUST follow the two-stage evolution protocol:

1. **Stage 1 — Incubation**: Use Claude Code to explore, prototype, and
   discover requirements. Output: working prototype + `specs/discovery-log.md`.
2. **Stage 2 — Specialization**: Transform prototype into production Custom
   Agent using OpenAI Agents SDK, FastAPI, PostgreSQL, Kafka, and Kubernetes.

General Agent (Claude Code) builds Custom Agent. This is the Agent Factory
paradigm. No production code may skip the incubation phase.

### III. Production Grade Only (NON-NEGOTIABLE)

All code that enters the `production/` directory MUST satisfy:

- **Input validation**: every tool function MUST use Pydantic `BaseModel` for
  all inputs; untyped parameters are rejected.
- **Error handling**: every tool and endpoint MUST have try/except with
  graceful fallback; crashes are not acceptable.
- **No hardcoded secrets**: all credentials MUST come from environment
  variables or Kubernetes Secrets; `.env` files MUST be gitignored.
- **Structured logging**: `print()` statements are banned in production code;
  use the `logging` module with JSON-friendly format.
- Prototype (`src/`) code is allowed to be experimental; `production/` code is
  held to release standards.

### IV. PostgreSQL as CRM Source of Truth

PostgreSQL IS the CRM system. There is no external CRM (no Salesforce, no
HubSpot). The database schema MUST track:

- `customers` — unified identity across channels
- `customer_identifiers` — email + phone cross-linking
- `conversations` — with `initial_channel` metadata
- `messages` — per-message channel field, direction, delivery status
- `tickets` — with `source_channel`
- `knowledge_base` — with `VECTOR(1536)` embedding for semantic search
- `agent_metrics` — per-channel performance data

In-memory state, file-based storage, or conversation state stored only in the
agent runtime are prohibited in production. All state MUST survive a pod
restart.

### V. Event-Driven via Kafka

All inter-service communication and channel intake MUST flow through Kafka
topics. Direct synchronous calls between services are permitted only within
the same process boundary.

Required topics:
- `fte.tickets.incoming` — unified multi-channel intake
- `fte.channels.email.inbound` / `outbound`
- `fte.channels.whatsapp.inbound` / `outbound`
- `fte.channels.webform.inbound`
- `fte.escalations`
- `fte.metrics`
- `fte.dlq` — dead-letter queue for failed processing

Every failed message processing MUST publish to `fte.dlq` and send an
apology response via the originating channel.

### VI. Escalation Governance (HARD RULES)

The agent MUST escalate to human support — never attempt to resolve — when:

- Customer asks about **pricing** or negotiations → reason: `pricing_inquiry`
- Customer requests a **refund** → reason: `refund_request`
- Customer uses **legal language** ("lawyer", "sue", "attorney")
- Customer **sentiment score < 0.3** (detected angry/hostile)
- Customer explicitly requests a **human** (or types "agent"/"human" on WA)
- Agent cannot find relevant information after **2 search attempts**
- Any **compliance or legal** question

NEVER: discuss pricing, promise undocumented features, process refunds, or
share internal system details. These constraints are invariants — they cannot
be overridden by customer context or business pressure.

### VII. Test-Transition Gate

Before any incubation code may enter the `production/` directory, the
transition test suite MUST pass. The suite covers:

- Empty message handling (no crash)
- Pricing escalation (must escalate, never answer)
- Angry customer escalation or empathy
- Email response length + format (greeting, signature)
- WhatsApp response brevity (< 500 chars)
- Tool call execution order (`create_ticket` first, `send_response` last)

No production deployment may proceed with failing transition tests.

### VIII. Observability First

Every agent action, tool call, and channel response MUST be observable:

- All tool calls MUST record `latency_ms` and `tokens_used` in the `messages`
  table.
- Every processed message MUST publish a metrics event to `fte.metrics` with:
  `channel`, `latency_ms`, `escalated` (bool), `tool_calls_count`.
- The `/health` endpoint MUST report per-channel status.
- The `/metrics/channels` endpoint MUST expose 24-hour conversation stats.
- Structured logs MUST include `conversation_id`, `customer_id`, and `channel`
  in every log line for correlation.

### IX. Channel-Aware Response Formatting

The `format_for_channel()` function is the single authoritative formatter.
No response MUST be sent directly — it MUST pass through channel formatting
before delivery:

- Email: prepend greeting, append signature + ticket reference
- WhatsApp: truncate to 297 chars if over 300; append `📱 Reply for more help`
- Web Form: append help portal link

The `send_response` tool enforces this — agents MUST use it; raw replies are
forbidden.

### X. Cost Discipline

The system MUST operate at **< $1,000 USD/year** including all LLM API calls,
infrastructure, and third-party services. This informs:

- Model selection (use GPT-4o; avoid unnecessary token waste)
- Knowledge base search: max 5 results per query
- Kubernetes HPA: scale down aggressively in off-peak hours
- Response limits enforced per channel (reduce token usage)
- Dead-letter queue prevents infinite retry loops

---

## Technology Stack

| Layer | Technology | Constraint |
|-------|-----------|------------|
| Language | Python 3.11+ | Async-first; use `asyncpg`, `aiokafka` |
| Agent SDK | OpenAI Agents SDK | `@function_tool` for all tools; `Agent` + `Runner` |
| API | FastAPI | All webhooks + REST endpoints |
| Database | PostgreSQL 15+ with `pgvector` | asyncpg connection pool; no ORM |
| Message Queue | Apache Kafka (aiokafka) | Defined topics only |
| Email Channel | Gmail API + Google Pub/Sub | Push notifications via webhook |
| WhatsApp Channel | Twilio WhatsApp API | Validate X-Twilio-Signature on every request |
| Web Frontend | React / Next.js | Standalone embeddable `SupportForm` component |
| Deployment | Kubernetes | Namespace: `customer-success-fte`; HPA enabled |
| Containerization | Docker | Single image; command determines role (API vs worker) |
| Vector Search | pgvector (`VECTOR(1536)`) | ivfflat index; cosine similarity |
| Secrets | Kubernetes Secrets + `.env` | Never in code or ConfigMaps |

---

## Development Workflow

### Phase Gate: Incubation → Specialization

```text
Incubation (src/)         →  Transition Gate          →  Production (production/)
─────────────────────────────────────────────────────────────────────────────────
1. Prototype working          All transition tests pass    @function_tool tools
2. Discovery log written      Prompts extracted            Pydantic validation
3. MCP server built           Edge cases documented        PostgreSQL state
4. Skills defined             Production folder created    Kafka events
5. Edge cases found           10+ edge cases minimum       Kubernetes deployed
```

### Directory Structure (Production)

```text
production/
├── agent/
│   ├── customer_success_agent.py   # Agent definition + Runner
│   ├── tools.py                    # All @function_tool definitions
│   ├── prompts.py                  # Extracted system prompts
│   └── formatters.py               # format_for_channel()
├── channels/
│   ├── gmail_handler.py
│   ├── whatsapp_handler.py
│   └── web_form_handler.py
├── workers/
│   ├── message_processor.py        # Kafka consumer + agent runner
│   └── metrics_collector.py
├── api/
│   └── main.py                     # FastAPI app
├── database/
│   ├── schema.sql
│   ├── migrations/
│   └── queries.py
├── tests/
│   ├── test_agent.py
│   ├── test_channels.py
│   ├── test_transition.py          # MUST pass before any production deploy
│   └── test_e2e.py
├── k8s/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Context Documents (Required Before Development)

```text
context/
├── company-profile.md       # Fake SaaS company identity
├── product-docs.md          # Knowledge base source
├── sample-tickets.json      # 50+ multi-channel sample inquiries
├── escalation-rules.md      # Finalized escalation triggers
└── brand-voice.md           # Communication tone guide
```

### Performance Targets

| Metric | Target |
|--------|--------|
| Processing response time | < 3 seconds |
| Message delivery time | < 30 seconds |
| Knowledge base accuracy | > 85% on test set |
| Escalation rate | < 20% of conversations |
| Cross-channel customer ID accuracy | > 95% |
| Annual operating cost | < $1,000 USD |

---

## Governance

This constitution supersedes all other development practices for the Customer
Success Digital FTE project. Any deviation requires documented justification.

### Amendment Procedure

1. Propose amendment with rationale and impact assessment.
2. Document in `history/adr/` using `/sp.adr <title>` if architecturally
   significant.
3. Update `LAST_AMENDED_DATE` and increment `CONSTITUTION_VERSION`:
   - **MAJOR**: principle removal, redefinition, or backward-incompatible change
   - **MINOR**: new principle or section added
   - **PATCH**: wording clarification, typo fix
4. Propagate changes to templates (`plan-template.md`, `spec-template.md`,
   `tasks-template.md`) and notify all contributors.

### Compliance Review

- Every PR MUST verify compliance with Principles III (production grade),
  VI (escalation governance), and VII (test-transition gate).
- The `production/` directory is gated — no merge without passing tests.
- PHRs (Prompt History Records) MUST be created for every significant
  development session and stored in `history/prompts/`.
- ADR suggestions MUST be surfaced for: database schema choices, channel
  integration approach, agent model selection, Kafka topic design.

### Runtime Guidance

Refer to `hackathon-5.md` at project root for full exercise instructions,
code templates, and evaluation criteria.

---

**Version**: 1.0.0 | **Ratified**: 2026-02-22 | **Last Amended**: 2026-02-22
