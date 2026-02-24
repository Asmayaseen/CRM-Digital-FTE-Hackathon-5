# Implementation Plan: Customer Success Digital FTE

**Branch**: `1-customer-success-fte` | **Date**: 2026-02-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/1-customer-success-fte/spec.md`

---

## Summary

Build a 24/7 AI-powered Customer Success employee (Digital FTE) that autonomously
handles customer support inquiries across three channels — Email (Gmail),
WhatsApp (Twilio), and a Web Support Form — backed by a PostgreSQL CRM, Kafka
event streaming, and deployed on Kubernetes. The system evolves through two
phases: Incubation (Claude Code prototype + MCP server) then Specialization
(production Custom Agent using OpenAI Agents SDK).

---

## Technical Context

**Language/Version**: Python 3.11+ (async-first throughout)
**Primary Dependencies**:
- `openai-agents` (OpenAI Agents SDK) — agent orchestration
- `fastapi` + `uvicorn` — API layer and webhooks
- `asyncpg` — async PostgreSQL driver (no ORM)
- `aiokafka` — async Kafka producer/consumer
- `google-api-python-client` + `google-auth` — Gmail API
- `twilio` — WhatsApp channel
- `pydantic` v2 — input validation for all tools and endpoints
- `pgvector` — vector similarity search in PostgreSQL
- `pytest` + `pytest-asyncio` + `httpx` — test suite

**Storage**: PostgreSQL 15+ with `pgvector` extension (unified CRM + vector KB)
**Testing**: `pytest` with `pytest-asyncio`; contract tests + integration tests + E2E
**Target Platform**: Kubernetes cluster (Linux containers); local dev via `docker-compose`
**Project Type**: Web application — `production/` backend + `web-form/` frontend
**Performance Goals**:
- Message processing: < 3 seconds p95
- End-to-end delivery: < 30 seconds p95
- Knowledge search: < 500ms p95
**Constraints**:
- Annual operating cost < $1,000 USD
- Memory per pod: < 1 GB
- No hardcoded secrets anywhere
- Escalation rate < 20%

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate Requirement | Status |
|-----------|-----------------|--------|
| I. Multi-Channel First | All three channels (Email/WhatsApp/Web) have handlers, tests, and channel field in every entity | ✅ PASS — channels/ has three handlers; channel tracked in all DB tables |
| II. Agent Maturity Model | Incubation prototype exists before production agent; context/ docs prepared first | ✅ PASS — src/ incubation precedes production/; hackathon-5.md defines exercises |
| III. Production Grade Only | All `production/` tools use Pydantic BaseModel; try/except on every tool; no print() | ✅ PASS — enforced via code review gate; transition tests validate |
| IV. PostgreSQL as CRM | Schema covers customers, conversations, messages, tickets, knowledge_base, metrics | ✅ PASS — full schema in data-model.md |
| V. Event-Driven via Kafka | All inter-service communication via defined Kafka topics; no direct service-to-service calls | ✅ PASS — kafka_client.py TOPICS dict is authoritative; all handlers publish only |
| VI. Escalation Governance | Hard rules enforced in system prompt and via escalate_to_human tool | ✅ PASS — NEVER clauses in CUSTOMER_SUCCESS_SYSTEM_PROMPT; FR-008 enforces escalation |
| VII. Test-Transition Gate | `tests/test_transition.py` suite must pass before any production/ code is merged | ✅ PASS — test suite specified; 6 mandatory test cases defined |
| VIII. Observability First | latency_ms + tokens_used in messages table; metrics event published per message | ✅ PASS — data model and metrics_collector.py enforce this |
| IX. Channel-Aware Formatting | Single `format_for_channel()` function; all responses route through it | ✅ PASS — production/agent/formatters.py is the sole formatter |
| X. Cost Discipline | GPT-4o model; max 5 KB results; HPA scales down; response length limits enforced | ✅ PASS — channel config max lengths enforced; HPA minReplicas=3 |

**Gate Result**: ALL PASS — proceed to Phase 0.

---

## Project Structure

### Documentation (this feature)

```text
specs/1-customer-success-fte/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — PostgreSQL schema + entities
├── quickstart.md        # Phase 1 output — local dev setup
├── contracts/           # Phase 1 output — API contracts (OpenAPI YAML)
│   ├── webhook-api.yaml
│   ├── support-form-api.yaml
│   └── management-api.yaml
└── tasks.md             # Phase 2 output — /sp.tasks command
```

### Source Code (repository root)

```text
context/                             # Agent dossier (prepare first)
├── company-profile.md               # SaaS company identity + product overview
├── product-docs.md                  # Knowledge base source content
├── sample-tickets.json              # 50+ multi-channel sample inquiries
├── escalation-rules.md              # Finalized escalation triggers
└── brand-voice.md                   # Communication tone and style guide

src/                                 # Stage 1: Incubation prototype
├── channels/                        # Channel-specific intake parsers
├── agent/                           # Core agent loop (prototype)
├── mcp_server.py                    # MCP server with 5+ tools
└── web-form/                        # Support form (prototype HTML)

production/                          # Stage 2: Specialization (production)
├── agent/
│   ├── __init__.py
│   ├── customer_success_agent.py    # Agent definition + Runner
│   ├── tools.py                     # All @function_tool definitions (Pydantic)
│   ├── prompts.py                   # System prompt constants
│   └── formatters.py                # format_for_channel() — sole formatter
├── channels/
│   ├── __init__.py
│   ├── gmail_handler.py             # Gmail API + Pub/Sub intake
│   ├── whatsapp_handler.py          # Twilio webhook intake + sending
│   └── web_form_handler.py          # FastAPI router for web form
├── workers/
│   ├── __init__.py
│   ├── message_processor.py         # Kafka consumer + agent runner
│   └── metrics_collector.py         # Background metrics aggregation
├── api/
│   ├── __init__.py
│   └── main.py                      # FastAPI app; includes all routers
├── database/
│   ├── schema.sql                   # Full PostgreSQL schema (see data-model.md)
│   ├── migrations/                  # Numbered migration scripts
│   └── queries.py                   # Typed async query functions
├── tests/
│   ├── test_agent.py                # Unit tests for agent tools
│   ├── test_channels.py             # Unit tests for channel handlers
│   ├── test_transition.py           # GATE: transition suite (MUST pass)
│   └── test_e2e.py                  # End-to-end multi-channel tests
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployment-api.yaml
│   ├── deployment-worker.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
├── Dockerfile
├── docker-compose.yml               # Local development environment
└── requirements.txt

web-form/                            # Standalone embeddable React component
├── SupportForm.jsx                  # Required deliverable
├── SupportForm.test.jsx
└── package.json
```

**Structure Decision**: Web application variant — `production/` backend and
`web-form/` frontend are separate concerns. `src/` holds the incubation
prototype and is intentionally kept separate from production code.

---

## Phase 0: Research Summary

See [research.md](research.md) for full decision rationale.

### Key Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | OpenAI Agents SDK | Deterministic tool orchestration; `@function_tool` aligns with Pydantic; production-tested |
| Vector search | pgvector in PostgreSQL | Keeps all state in one DB (Principle IV); avoids Pinecone/Weaviate cost |
| Message queue | Apache Kafka (aiokafka) | Guaranteed delivery; topic-per-channel isolation; Principle V |
| Email channel | Gmail API + Google Pub/Sub | Push notifications; no polling latency; sub-second delivery |
| WhatsApp | Twilio API | Fastest path to WhatsApp Business; official webhook validation |
| Async DB driver | asyncpg (no ORM) | Zero ORM overhead; full SQL control; asyncio-native |
| Embedding model | `text-embedding-3-small` | 1536 dims; $0.02/1M tokens; fits < $1,000/year budget |
| Kubernetes autoscaler | HPA (CPU-based) | Scales workers independently from API pods |
| Web form | React standalone JSX | Embeddable without full Next.js; Principle I web channel requirement |

---

## Phase 1: Design Artifacts

### Data Model

See [data-model.md](data-model.md) for full schema.

**Core tables**: `customers`, `customer_identifiers`, `conversations`, `messages`,
`tickets`, `knowledge_base`, `channel_configs`, `agent_metrics`

**Key design decisions**:
- `customers.email` is the primary cross-channel identity key
- `customer_identifiers` handles WhatsApp phone → customer_id resolution
- `messages.channel` tracks per-message channel for cross-channel threads
- `knowledge_base.embedding VECTOR(1536)` with `ivfflat` index for cosine similarity
- `messages.tool_calls JSONB` stores full tool call audit trail per message

### API Contracts

See [contracts/](contracts/) for full OpenAPI specs.

**Webhook endpoints** (`/webhooks/`):
- `POST /webhooks/gmail` — Gmail Pub/Sub push notification handler
- `POST /webhooks/whatsapp` — Twilio WhatsApp inbound message
- `POST /webhooks/whatsapp/status` — Twilio delivery status callback

**Web Form endpoints** (`/support/`):
- `POST /support/submit` — Submit support form; returns ticket_id
- `GET /support/ticket/{ticket_id}` — Poll ticket status and responses

**Management endpoints**:
- `GET /health` — Per-channel health status
- `GET /conversations/{conversation_id}` — Full conversation history
- `GET /customers/lookup?email=&phone=` — Customer lookup
- `GET /metrics/channels` — 24-hour channel performance metrics

### Agent Tools (OpenAI Agents SDK)

| Tool | Input Schema | Purpose | When Called |
|------|-------------|---------|-------------|
| `search_knowledge_base` | `KnowledgeSearchInput(query, max_results=5)` | Vector search docs | Product questions |
| `create_ticket` | `TicketInput(customer_id, issue, priority, channel)` | Log all interactions | FIRST — every conversation |
| `get_customer_history` | `customer_id: str` | Cross-channel history | SECOND — every conversation |
| `escalate_to_human` | `EscalationInput(ticket_id, reason, urgency)` | Human handoff | Escalation triggers |
| `send_response` | `ResponseInput(ticket_id, message, channel)` | Channel-formatted reply | LAST — every conversation |

### Kafka Topics

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `fte.tickets.incoming` | All channel handlers | message_processor | Unified intake queue |
| `fte.channels.email.inbound` | gmail_handler | message_processor | Email-specific audit |
| `fte.channels.whatsapp.inbound` | whatsapp_handler | message_processor | WA-specific audit |
| `fte.channels.webform.inbound` | web_form_handler | message_processor | Form-specific audit |
| `fte.escalations` | message_processor | Human agent system | Escalation events |
| `fte.metrics` | message_processor | metrics_collector | Performance data |
| `fte.dlq` | message_processor | ops alerts | Failed processing |

### Kubernetes Resources

| Component | Kind | Replicas | CPU req/limit | Mem req/limit |
|-----------|------|----------|---------------|---------------|
| `fte-api` | Deployment | 3–20 (HPA) | 250m / 500m | 512Mi / 1Gi |
| `fte-message-processor` | Deployment | 3–30 (HPA) | 250m / 500m | 512Mi / 1Gi |
| Namespace | customer-success-fte | — | — | — |

---

## Phase 2: Task Generation

See [tasks.md](tasks.md) — generated by `/sp.tasks`.

### Implementation Sequence

```text
Phase 1: Setup
  → Git branch, docker-compose, requirements.txt, env template

Phase 2: Foundational (BLOCKS all user stories)
  → context/ documents
  → PostgreSQL schema + migrations
  → Kafka topics + kafka_client.py
  → database/queries.py (all query functions)
  → Dockerfile + docker-compose.yml

Phase 3: User Story 1 — Multi-Channel Intake (P1)
  → gmail_handler.py + webhook endpoint
  → whatsapp_handler.py + webhook endpoint
  → web_form_handler.py + router
  → Incubation src/ prototype

Phase 4: User Story 2 — Autonomous AI Resolution (P2)
  → Transition: extract prompts.py, formatters.py
  → agent/tools.py (all 5 @function_tool)
  → agent/customer_success_agent.py
  → workers/message_processor.py
  → tests/test_transition.py (GATE)

Phase 5: User Story 3 — Cross-Channel Continuity (P3)
  → customer identity resolution in message_processor
  → get_customer_history tool verified cross-channel
  → conversation threading logic

Phase 6: User Story 4 — Human Escalation (P4)
  → escalate_to_human tool + Kafka event
  → escalation notification per channel
  → tests/test_agent.py escalation cases

Phase 7: User Story 5 — Management Reporting (P5)
  → metrics_collector.py
  → /metrics/channels endpoint
  → daily report generation

Phase 8: Kubernetes + E2E
  → k8s/ manifests
  → web-form/SupportForm.jsx
  → tests/test_e2e.py
  → Deployment validation
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Three separate channel handlers | Each channel has unique auth, format, and SDK | Single handler would require excessive branching; unmaintainable |
| Kafka between API and workers | Decoupled intake; workers scale independently | Direct DB polling would miss messages under load; not event-driven |
| pgvector alongside relational tables | Knowledge base requires semantic search | Separate vector DB (Pinecone) would violate Principle IV and exceed budget |
| Two-stage incubation/production | Hackathon mandate + Principle II | Cannot skip; spec requires both stages as learning + production artifacts |
