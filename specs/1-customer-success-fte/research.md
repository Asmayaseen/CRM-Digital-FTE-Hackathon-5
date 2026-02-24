# Research: Customer Success Digital FTE

**Feature**: 1-customer-success-fte
**Date**: 2026-02-22
**Phase**: Phase 0 — Technology Decisions

All NEEDS CLARIFICATION items from Technical Context have been resolved below.

---

## Decision 1: Agent Orchestration Framework

**Decision**: OpenAI Agents SDK (`openai-agents`) with `@function_tool` decorators

**Rationale**:
- Provides deterministic tool call orchestration — agent MUST call tools in order
- `@function_tool` auto-generates JSON schema from Pydantic `BaseModel` input classes
- `Runner` class handles the agent loop, token management, and tool dispatch
- Used in hackathon-5.md as the mandated production framework

**Alternatives Considered**:
- LangChain — heavy abstractions, harder to enforce strict tool ordering
- Raw OpenAI function calling — requires manual loop; more error-prone
- Anthropic Claude API directly — viable but hackathon mandates OpenAI Agents SDK

**Resolution**: Use `openai-agents` with `gpt-4o` as model.

---

## Decision 2: Vector Search Strategy

**Decision**: `pgvector` extension in PostgreSQL; `text-embedding-3-small` (1536 dims);
`ivfflat` index with cosine distance

**Rationale**:
- Keeps all state in a single PostgreSQL database (Principle IV — no external vector DB)
- `text-embedding-3-small` costs $0.02/1M tokens; embedding the full knowledge base
  (~500 articles × ~500 tokens) costs < $1 total — well within $1,000/year budget
- `ivfflat` index provides good query speed for < 100,000 vectors without HNSW overhead
- `1 - (embedding <=> query_embedding)` gives cosine similarity in [0,1] range

**Alternatives Considered**:
- Pinecone — managed service but adds ~$70/month; violates Principle IV (external state)
- Weaviate — powerful but requires additional infrastructure pod; cost and complexity
- HNSW index in pgvector — faster recall but slower inserts; knowledge base is mostly
  static so ivfflat insert overhead is acceptable

**Resolution**: pgvector ivfflat, `VECTOR(1536)`, cosine ops.

---

## Decision 3: Async Message Queue

**Decision**: Apache Kafka via `aiokafka` library; topics defined in `kafka_client.py`

**Rationale**:
- Kafka provides guaranteed delivery and consumer group-based load distribution
  across multiple worker pods (Kubernetes HPA)
- `aiokafka` is pure-asyncio, matching the async-first codebase (Principle III)
- Topic-per-channel isolation (`fte.channels.email.*`) gives per-channel audit trail
- Dead-letter queue (`fte.dlq`) enables graceful error recovery without infinite retries

**Alternatives Considered**:
- RabbitMQ — good for task queues but lacks topic-based partitioning for per-channel audit
- Redis Streams — lighter but adds another stateful service; less mature replay/retry
- Direct database polling — couples API and worker; misses events under load; not
  event-driven architecture

**Resolution**: Kafka with `aiokafka`; 8 topics as defined in `kafka_client.py`.

---

## Decision 4: Email Channel Integration

**Decision**: Gmail API with Google Cloud Pub/Sub push notifications; no polling

**Rationale**:
- Pub/Sub push delivers new emails to the webhook within < 2 seconds of receipt
  (no 30-second polling delay)
- `watch()` API + `labelIds: ['INBOX']` filters only incoming customer emails
- `google-api-python-client` handles OAuth token refresh automatically
- Thread ID preservation enables proper email reply threading

**Alternatives Considered**:
- IMAP polling — simple but introduces latency; hits rate limits under load
- Gmail polling via periodic API calls — same latency issue; wastes API quota
- SendGrid Inbound Parse — handles incoming email but loses Gmail thread context

**Resolution**: Gmail API with Pub/Sub push; `setup_push_notifications()` called on startup.

---

## Decision 5: WhatsApp Channel Integration

**Decision**: Twilio WhatsApp Business API; webhook with X-Twilio-Signature validation

**Rationale**:
- Twilio provides a stable, official path to WhatsApp Business without Meta approval wait
- `RequestValidator.validate()` ensures only genuine Twilio requests are processed
- `twilio.rest.Client` handles message delivery with SID-based status tracking
- WhatsApp message limit is 1600 characters; `format_response()` splits long messages

**Alternatives Considered**:
- Direct Meta WhatsApp Cloud API — requires business verification; slower approval
- 360dialog — reseller layer; adds cost and dependency
- WhatsApp via Vonage — viable alternative; Twilio chosen for SDK maturity

**Resolution**: Twilio `whatsapp:` prefix format; validate every webhook request.

---

## Decision 6: Async Database Driver

**Decision**: `asyncpg` directly; no ORM (SQLAlchemy, Tortoise, etc.)

**Rationale**:
- asyncpg is 3–10x faster than SQLAlchemy async on raw queries
- No ORM overhead aligns with Principle III (production grade, no abstractions for abstraction's sake)
- Full SQL control is required for: pgvector cosine queries, JSONB operations,
  `INSERT ... RETURNING`, window functions for metrics
- Connection pool managed once via `asyncpg.create_pool()`; shared across all handlers

**Alternatives Considered**:
- SQLAlchemy 2.0 async — familiar but adds 200–400ms overhead per query at scale;
  ORM mapping of VECTOR type is awkward
- Tortoise ORM — asyncio-native but poor pgvector support
- Databases (encode) — lightweight but incomplete feature set for complex queries

**Resolution**: asyncpg connection pool; all queries in `database/queries.py` as typed functions.

---

## Decision 7: Web Form Frontend

**Decision**: Standalone React JSX component (`SupportForm.jsx`); no full Next.js app

**Rationale**:
- Hackathon requirement: "standalone, embeddable component" — not an entire website
- Pure React JSX can be bundled and dropped into any HTML page
- No server-side rendering needed for a support form
- Form validation in React (no external library needed for basic field checks)

**Alternatives Considered**:
- Next.js full app — over-engineered for a single embeddable form
- Plain HTML/JS — less maintainable; no component reuse
- Vue.js — React chosen for wider familiarity; hackathon examples use React

**Resolution**: Single `SupportForm.jsx` component with internal state management.

---

## Decision 8: Kubernetes Deployment Strategy

**Decision**: Two separate Deployments (`fte-api` and `fte-message-processor`);
HPA on CPU 70% target; single Docker image with command-based role selection

**Rationale**:
- API pods scale on HTTP traffic; worker pods scale on Kafka consumer lag
- Single image simplifies CI/CD; `command` field in k8s determines the role
- HPA `minReplicas: 3` ensures HA; `maxReplicas: 20/30` controls cost ceiling
- Namespace `customer-success-fte` isolates all resources for easy teardown

**Alternatives Considered**:
- Separate Docker images per component — increases build complexity; no benefit
  when codebase is a monorepo
- KEDA (Kafka-based autoscaling) — ideal but adds operational complexity; CPU-based
  HPA is sufficient for hackathon scope
- Serverless (AWS Lambda, Cloud Run) — cold starts incompatible with < 3s processing
  requirement; harder to estimate cost

**Resolution**: Single image; two Deployments; CPU-based HPA; namespace isolation.

---

## Decision 9: System Prompt Strategy

**Decision**: Explicit constraint-first system prompt in `prompts.py`;
extracted verbatim from incubation prototype after testing

**Rationale**:
- Principle II (Agent Maturity Model) requires prompts extracted from working incubation
- Constraint-first format (NEVER do X before describing context) produces more
  reliable constraint adherence than conversational prompts
- Required workflow section enforces tool call ordering: create_ticket → get_history
  → search_kb → send_response
- Channel awareness section adapts tone without requiring separate agents per channel

**Alternatives Considered**:
- Separate agent per channel — 3x token cost; harder to maintain; cross-channel
  history retrieval requires shared agent anyway
- Dynamic prompt assembly — adds complexity; static prompt is more predictable
  and easier to audit

**Resolution**: Single `CUSTOMER_SUCCESS_SYSTEM_PROMPT` constant in `prompts.py`.

---

## Decision 10: Incubation MCP Server Design

**Decision**: 5 MCP tools mirroring the 5 production `@function_tool` functions;
MCP server runs via `stdio` transport for Claude Code integration

**Rationale**:
- 1:1 mapping between MCP tools and production tools ensures smooth transition
  (Principle II, Step 3)
- Testing MCP tools via Claude Code validates agent behaviour before production
- `Channel(str, Enum)` enum shared between MCP and production definitions

**Alternatives Considered**:
- HTTP-based MCP transport — adds networking complexity for local incubation
- Separate tool set for incubation — divergence makes transition harder; defeats
  the purpose of Principle II

**Resolution**: 5 MCP tools: `search_knowledge_base`, `create_ticket`,
`get_customer_history`, `escalate_to_human`, `send_response`.
