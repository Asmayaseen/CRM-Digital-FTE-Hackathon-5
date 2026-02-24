# Tasks: Customer Success Digital FTE

**Input**: Design documents from `/specs/1-customer-success-fte/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅
**Branch**: `1-customer-success-fte`
**Date**: 2026-02-22

**Tests**: Transition gate tests (test_transition.py) are MANDATORY — they gate
production deployment. Additional tests in polish phase are optional but recommended.

**Organization**: Tasks grouped by user story for independent implementation and testing.
Incubation (src/) tasks appear in US2 phase per the Agent Maturity Model (Principle II).

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Runs in parallel (different files, no in-phase dependency)
- **[Story]**: US1 → US5 maps to spec.md user stories

---

## Phase 1: Setup

**Purpose**: Project initialization and environment configuration.

- [x] T001 Create full project directory structure: `context/`, `src/channels/`, `src/agent/`, `production/agent/`, `production/channels/`, `production/workers/`, `production/api/`, `production/database/migrations/`, `production/tests/`, `k8s/`, `web-form/`
- [x] T002 Create `production/requirements.txt` with pinned versions: `openai-agents`, `fastapi`, `uvicorn[standard]`, `asyncpg`, `aiokafka`, `google-api-python-client`, `google-auth-oauthlib`, `twilio`, `pydantic>=2`, `pgvector`, `pytest`, `pytest-asyncio`, `httpx`, `python-dotenv`
- [x] T003 [P] Create `docker-compose.yml` with services: `postgres` (ankane/pgvector image), `zookeeper`, `kafka`; include healthchecks and volume mounts
- [x] T004 [P] Create `.env.example` with all required variables: `OPENAI_API_KEY`, `POSTGRES_*`, `KAFKA_BOOTSTRAP_SERVERS`, `GMAIL_CREDENTIALS_PATH`, `GMAIL_PUBSUB_TOPIC`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`, `ENVIRONMENT`, `LOG_LEVEL`
- [x] T005 [P] Create `Dockerfile` with multi-stage build: Python 3.11-slim base; install requirements; set `CMD` to uvicorn (role determined by k8s command override)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 Create `context/company-profile.md`: fictional SaaS company name, product summary (3–4 features), target market, support contact details, and escalation team contact
- [x] T007 [P] Create `context/product-docs.md`: 8–10 sections covering product features, how-to guides (password reset, data export, API keys, integrations, billing, account settings, user management, troubleshooting); content used to seed knowledge base
- [x] T008 [P] Create `context/sample-tickets.json`: 50+ sample customer inquiries across all three channels; include channel, customer_email/phone, subject, content, expected_action (resolve/escalate); cover all escalation trigger types
- [x] T009 [P] Create `context/escalation-rules.md`: finalized list of all escalation triggers (pricing, refund, legal language, sentiment < 0.3, explicit human request, 2 failed searches); include example phrases for each trigger
- [x] T010 [P] Create `context/brand-voice.md`: tone guidelines per channel (email: formal, WhatsApp: conversational, web: semi-formal); prohibited topics; empathy phrases; signature template
- [x] T011 Create `production/database/schema.sql`: full PostgreSQL schema for all 8 tables (`customers`, `customer_identifiers`, `conversations`, `messages`, `tickets`, `knowledge_base`, `channel_configs`, `agent_metrics`) including pgvector extension, all indexes, and constraints from `data-model.md`
- [x] T012 [P] Create `production/database/migrations/001_initial_schema.sql`: copy of schema.sql with idempotent `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` guards
- [x] T013 [P] Create `production/database/migrations/002_seed_channel_configs.sql`: INSERT rows for email, whatsapp, web_form into `channel_configs` with max_response_length values (2000, 1600, 1000)
- [x] T014 Create `production/database/queries.py`: all typed async query functions using asyncpg — `get_or_create_customer()`, `get_customer_by_identifier()`, `create_customer_identifier()`, `create_conversation()`, `get_active_conversation()`, `create_message()`, `update_message_delivery_status()`, `create_ticket()`, `update_ticket_status()`, `get_ticket_by_id()`, `get_customer_history()`, `search_knowledge_base()`, `insert_knowledge_entry()`, `record_metric()`; include `get_db_pool()` singleton
- [x] T015 [P] Create `production/kafka_client.py`: `TOPICS` dict with all 8 topics, `FTEKafkaProducer` (start/stop/publish), `FTEKafkaConsumer` (start/stop/consume) using aiokafka; JSON serialization; `timestamp` field auto-added on publish
- [x] T016 [P] Create `production/agent/prompts.py`: `CUSTOMER_SUCCESS_SYSTEM_PROMPT` constant with channel awareness section, required workflow order (create_ticket → get_customer_history → search_knowledge_base → send_response), hard constraints (NEVER list), escalation triggers list, response quality standards, and context variable placeholders

**Checkpoint**: Foundation ready → all user story phases may begin in parallel.

---

## Phase 3: User Story 1 — Multi-Channel Intake (Priority: P1) 🎯 MVP

**Goal**: Accept customer support inquiries from all three channels; create a
tracked ticket for each; return confirmation to the customer.

**Independent Test**: Submit a test inquiry via web form `POST /support/submit` and
confirm: ticket created in DB, Kafka event published to `fte.tickets.incoming`,
`SupportFormResponse` returned with ticket_id. Repeat for WhatsApp and Gmail webhooks.

- [x] T017 [US1] Create `production/channels/gmail_handler.py`: `GmailHandler` class with `setup_push_notifications()`, `process_notification()`, `get_message()`, `_extract_body()`, `_extract_email()`, `send_reply()`; return normalized message dict with `channel: 'email'`, `channel_message_id`, `customer_email`, `content`, `thread_id`, `metadata`
- [x] T018 [P] [US1] Create `production/channels/whatsapp_handler.py`: `WhatsAppHandler` class with `validate_webhook()` (X-Twilio-Signature), `process_webhook()`, `send_message()`, `format_response()` (split at 1600 chars); return normalized message dict with `channel: 'whatsapp'`, `customer_phone`
- [x] T019 [P] [US1] Create `production/channels/web_form_handler.py`: FastAPI `APIRouter` with `POST /support/submit` (SupportFormSubmission model with validators, publishes to Kafka, returns SupportFormResponse), `GET /support/ticket/{ticket_id}` (returns status and messages); all validators per contracts/support-form-api.yaml
- [x] T020 [US1] Create `production/api/main.py`: FastAPI app with title/version; CORS middleware; startup/shutdown event handlers for Kafka; include `web_form_router`; `POST /webhooks/gmail` handler; `POST /webhooks/whatsapp` handler (validates Twilio signature, returns TwiML); `POST /webhooks/whatsapp/status` handler; initialize GmailHandler and WhatsAppHandler
- [x] T021 [US1] Create `web-form/SupportForm.jsx`: standalone React component per contracts/support-form-api.yaml; fields: name, email, subject, category (dropdown), priority (dropdown), message (textarea with char count); client-side validation; loading/success/error states; success state displays ticket_id
- [x] T022 [P] [US1] Create `web-form/package.json` with React, testing-library dependencies; create `web-form/SupportForm.test.jsx` with render test and form submission mock
- [x] T023 [US1] Create `src/channels/` incubation prototypes: `gmail_intake.py` (basic Gmail API polling), `whatsapp_intake.py` (Twilio webhook parse), `web_form_intake.py` (simple FastAPI form endpoint); no production error handling required; document learnings in `specs/1-customer-success-fte/discovery-log.md`

**Checkpoint**: US1 independently functional — all three channels accept messages and
create Kafka events. Test with `curl POST /support/submit` before proceeding.

---

## Phase 4: User Story 2 — Autonomous AI Resolution (Priority: P2)

**Goal**: AI agent processes tickets from all channels, searches knowledge base,
generates channel-appropriate responses, and delivers them without human involvement.

**Independent Test**: Submit web form with "How do I reset my password?" — verify agent
creates ticket, searches KB, generates response, sends formatted reply via web form
channel, all within 30 seconds. Run `pytest production/tests/test_transition.py` — ALL
6 tests must pass before this story is complete.

### Incubation Phase (src/ — must complete first per Principle II)

- [x] T024 [US2] Create `src/agent/prototype.py`: core interaction loop — takes customer message + channel metadata, searches product docs (string matching), generates response, formats for channel, decides escalation; test with `context/sample-tickets.json`; document patterns in `specs/1-customer-success-fte/discovery-log.md`
- [x] T025 [US2] Extend `src/agent/prototype.py` with conversation memory: in-memory dict keyed by customer email; track sentiment (positive/neutral/negative), topics discussed, resolution status, original channel; test cross-channel context persistence
- [x] T026 [US2] Create `src/mcp_server.py`: MCP `Server("customer-success-fte")` with 5 tools matching production tool signatures — `search_knowledge_base(query)`, `create_ticket(customer_id, issue, priority, channel)`, `get_customer_history(customer_id)`, `escalate_to_human(ticket_id, reason)`, `send_response(ticket_id, message, channel)`; use `Channel(str, Enum)` with EMAIL/WHATSAPP/WEB_FORM values
- [x] T027 [P] [US2] Create `specs/1-customer-success-fte/agent-skills.md`: skills manifest for 5 agent skills — Knowledge Retrieval, Sentiment Analysis, Escalation Decision, Channel Adaptation, Customer Identification; each skill: when_to_use, inputs, outputs, test_cases

### Transition to Production (extract from incubation)

- [x] T028 [US2] Create `production/agent/formatters.py`: `format_for_channel(response, channel)` — email: prepend greeting + append signature + ticket reference; whatsapp: truncate to 297 chars if > 300, append `📱 Reply for more help or type 'human' for live support.`; web_form: append help portal link; this is the ONLY place response formatting occurs
- [x] T029 [US2] Create `production/agent/tools.py`: 5 `@function_tool` decorated async functions with Pydantic input schemas — `search_knowledge_base(KnowledgeSearchInput)`, `create_ticket(TicketInput)`, `get_customer_history(str)`, `escalate_to_human(EscalationInput)`, `send_response(ResponseInput)`; all use `database/queries.py`; all have try/except with graceful fallback; no print() statements; Channel enum shared
- [x] T030 [US2] Create `production/agent/customer_success_agent.py`: `Agent` with `name="Customer Success FTE"`, `model="gpt-4o"`, `instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT`, `tools=[all 5 tools]`; `format_for_channel()` called inside `send_response` tool; channel-aware response dispatch (Gmail API / Twilio / store + email notify)
- [x] T031 [US2] Create `production/workers/message_processor.py`: `UnifiedMessageProcessor` class — `start()` launches Kafka consumer on `fte.tickets.incoming`; `process_message()` resolves customer, gets/creates conversation, stores inbound message, loads history, runs agent, stores outbound message, publishes metrics event; `handle_error()` sends apology and publishes to DLQ
- [x] T032 [US2] Create `production/tests/test_transition.py`: 6 **mandatory gate tests** (all must PASS before any production deployment):
  1. `test_edge_case_empty_message` — no crash, asks for clarification
  2. `test_edge_case_pricing_escalation` — escalates, never answers price
  3. `test_edge_case_angry_customer` — escalates or shows empathy
  4. `test_channel_response_email_format` — greeting + signature present
  5. `test_channel_response_whatsapp_brevity` — len(output) < 500
  6. `test_tool_execution_order` — create_ticket first, send_response last

**Checkpoint**: `pytest production/tests/test_transition.py` ALL PASS before merging
Phase 4 to main. This is Constitution Principle VII — non-negotiable gate.

---

## Phase 5: User Story 3 — Cross-Channel Conversation Continuity (Priority: P3)

**Goal**: Identify the same customer across channels; load unified interaction history;
acknowledge prior contact in responses; link follow-up messages to active conversations.

**Independent Test**: Create a customer via email, then submit a WhatsApp message with
the same customer's email in metadata. Verify `resolve_customer()` returns the same
customer_id and `get_customer_history()` returns messages from both channels.

- [x] T033 [US3] Implement `resolve_customer()` in `production/workers/message_processor.py`: check `customers.email` first; if not found, check `customer_identifiers` table for phone/whatsapp type; create new customer if no match; create `customer_identifiers` row for new WhatsApp contacts; return unified customer_id
- [x] T034 [US3] Implement `get_or_create_conversation()` in `production/workers/message_processor.py`: query `conversations` for active record within 24 hours for same customer_id; create new conversation if none found; store `initial_channel` on creation; return conversation_id
- [x] T035 [P] [US3] Add `get_customer_by_email()`, `get_customer_by_phone()`, `link_customer_identifier()` to `production/database/queries.py` supporting the cross-channel lookup pattern
- [x] T036 [US3] Verify `get_customer_history` `@function_tool` in `production/agent/tools.py` uses the cross-channel JOIN query from `data-model.md` (joins `conversations` + `messages`, orders by `created_at DESC`, limits to 20 rows); tool docstring explicitly states "across ALL channels"
- [x] T037 [US3] Update `production/agent/prompts.py` — add Cross-Channel Continuity section: "If customer has prior contact on any channel, acknowledge it: 'I see you contacted us previously about X. Let me help you further...'"

**Checkpoint**: US3 independently testable — same customer recognised across email
and WhatsApp; prior interaction acknowledged in response.

---

## Phase 6: User Story 4 — Human Escalation and Handoff (Priority: P4)

**Goal**: Detect all escalation triggers; hand off to human without attempting resolution;
notify customer via correct channel; publish escalation event to Kafka.

**Independent Test**: Submit message containing "I want to sue you" via web form — verify
ticket status = 'escalated', `fte.escalations` Kafka event published with `reason='legal_language'`,
customer receives notification message (not an answer).

- [x] T038 [US4] Implement `escalate_to_human` `@function_tool` in `production/agent/tools.py`: UPDATE tickets status to 'escalated', set resolution_notes to escalation reason; publish event to `fte.escalations` Kafka topic with ticket_id, reason, urgency, customer_id, channel; return confirmation string
- [x] T039 [US4] Add escalation notification logic in `send_response` tool (or `production/agent/formatters.py`): when channel = EMAIL send "A specialist will follow up within 24 hours"; when channel = WHATSAPP send concise "We've connected you with our team"; when channel = WEB_FORM store escalation message against ticket
- [x] T040 [P] [US4] Create `production/tests/test_agent.py`: unit tests for all 6 escalation triggers — pricing_inquiry, refund_request, legal_language, negative_sentiment, explicit_human_request, whatsapp_human_keyword; each test verifies `escalated == True` and correct reason code
- [x] T041 [US4] Implement `handle_error()` in `production/workers/message_processor.py`: catch all exceptions from agent processing; send apology message via originating channel; publish error event to `fte.dlq` topic with original_message, error string, requires_human=True; log structured error with conversation_id and channel
- [x] T042 [US4] Add `update_ticket_status(ticket_id, status, resolution_notes)` to `production/database/queries.py`; ensure escalation reason stored in `resolution_notes`; update `conversations.status` to 'escalated' and set `escalated_to` field

**Checkpoint**: US4 independently testable — all 6 trigger types escalate correctly;
customer notification sent; Kafka event published.

---

## Phase 7: User Story 5 — Management Reporting and Insights (Priority: P5)

**Goal**: Collect per-interaction metrics; expose 24-hour channel performance report;
health endpoint reports per-channel status.

**Independent Test**: Process 5 tickets via web form, call `GET /metrics/channels` —
verify response contains `web_form` key with `total_conversations >= 5`,
`avg_sentiment` value, `escalations` count, `avg_latency_ms` value.

- [x] T043 [US5] Create `production/workers/metrics_collector.py`: `MetricsConsumer` class — Kafka consumer on `fte.metrics` topic; batch-inserts metric events into `agent_metrics` table every 10 seconds; handles `message_processed`, `escalation`, `error` event types; extracts channel, latency_ms, sentiment_score from event dimensions
- [x] T044 [US5] Implement `GET /metrics/channels` in `production/api/main.py`: runs daily report query from `data-model.md` aggregating `agent_metrics` by channel for last 24 hours; returns `ChannelMetricsResponse` per `contracts/management-api.yaml`
- [x] T045 [P] [US5] Implement `GET /health` in `production/api/main.py`: check PostgreSQL connectivity (simple SELECT 1), Kafka producer is started, all three channel handlers initialised; return per-channel status dict; used by Kubernetes liveness/readiness probes
- [x] T046 [P] [US5] Implement `GET /conversations/{conversation_id}` in `production/api/main.py`: query conversations + messages JOIN; 404 if not found; return `ConversationDetail` per `contracts/management-api.yaml`
- [x] T047 [P] [US5] Implement `GET /customers/lookup` in `production/api/main.py`: accept `email` or `phone` query param (400 if neither); call `queries.get_customer_by_email()` or `get_customer_by_phone()`; return `CustomerProfile` with identifiers array and conversation_count
- [x] T048 [US5] Create `production/database/seed_knowledge_base.py`: CLI script — reads `context/product-docs.md`, splits into sections by H2 headings, generates `text-embedding-3-small` embeddings via OpenAI API, bulk-inserts into `knowledge_base` table; print progress; idempotent (check title before insert)

**Checkpoint**: US5 independently testable — `/metrics/channels` returns real data;
`/health` used by Kubernetes probes.

---

## Phase 8: Kubernetes Deployment

**Purpose**: Package and deploy to Kubernetes cluster.

- [x] T049 Create `k8s/namespace.yaml` (namespace: customer-success-fte) and `k8s/configmap.yaml` (ENVIRONMENT, LOG_LEVEL, KAFKA_BOOTSTRAP_SERVERS, POSTGRES_HOST/DB, GMAIL_ENABLED, WHATSAPP_ENABLED, WEBFORM_ENABLED, MAX_*_LENGTH values)
- [x] T050 [P] Create `k8s/secrets.yaml`: template with `${VAR}` placeholders for OPENAI_API_KEY, POSTGRES_PASSWORD, GMAIL_CREDENTIALS, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER; add `k8s/secrets.yaml` to `.gitignore`
- [x] T051 [P] Create `k8s/deployment-api.yaml`: Deployment `fte-api`; 3 replicas; container command `uvicorn production.api.main:app --host 0.0.0.0 --port 8000`; envFrom configmap + secret; resources 250m/500m CPU, 512Mi/1Gi memory; livenessProbe + readinessProbe on `/health:8000`
- [x] T052 [P] Create `k8s/deployment-worker.yaml`: Deployment `fte-message-processor`; 3 replicas; command `python production/workers/message_processor.py`; envFrom configmap + secret; same resource limits as API
- [x] T053 [P] Create `k8s/service.yaml` (ClusterIP, port 80 → 8000) and `k8s/ingress.yaml` (nginx ingress, TLS via cert-manager, host: support-api.yourdomain.com)
- [x] T054 [P] Create `k8s/hpa.yaml`: two HPA resources — `fte-api-hpa` (min 3, max 20, CPU 70%) and `fte-worker-hpa` (min 3, max 30, CPU 70%)

---

## Phase N: Polish and Cross-Cutting Concerns

**Purpose**: Quality, security, and validation across all stories.

- [x] T055 Create `production/tests/test_channels.py`: unit tests for `GmailHandler._extract_body()`, `_extract_email()`, `WhatsAppHandler.validate_webhook()`, `format_response()` (split at 1600), `web_form_handler` validators (empty name, invalid email, short message, invalid category)
- [x] T056 [P] Create `production/tests/test_e2e.py`: multi-channel E2E test suite — web form full flow (submit → Kafka → agent → response stored), channel format assertions per channel type, cross-channel customer identity test, escalation flow test
- [x] T057 [P] Create `web-form/SupportForm.test.jsx`: component render test, field validation test, successful submission mock (verify ticketId displayed), error state test (network failure)
- [x] T058 Validate `specs/1-customer-success-fte/quickstart.md` end-to-end: follow every step from Docker Compose startup through web form test curl; fix any discrepancies found
- [x] T059 [P] Security hardening: update CORS in `api/main.py` to restrict origins from `*` to configured allowed list; verify Twilio signature validation is tested; confirm no secrets appear in logs; audit `requirements.txt` for known CVEs
- [x] T060 Performance validation: run `production/tests/test_e2e.py` with timing assertions — verify p95 processing < 3000ms; verify all tool calls logged with latency_ms in messages.tool_calls JSONB

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational — can start after Phase 2 completes
- **US2 (Phase 4)**: Depends on Foundational; incubation (T024-T027) can run in parallel with US1
- **US3 (Phase 5)**: Depends on US2 (needs agent + message_processor running)
- **US4 (Phase 6)**: Depends on US2 (needs agent tools and Kafka topics)
- **US5 (Phase 7)**: Depends on US1 + US2 (needs messages flowing and metrics published)
- **Kubernetes (Phase 8)**: Depends on all user stories being implemented
- **Polish (Phase N)**: Depends on all phases above

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational — no story dependencies
- **US2 (P2)**: Depends only on Foundational — incubation runs with US1; production after US1 channels exist
- **US3 (P3)**: Depends on US2 — requires message_processor and agent running
- **US4 (P4)**: Depends on US2 — requires agent tools (escalate_to_human); can run with US3
- **US5 (P5)**: Depends on US1 + US2 — requires tickets being created and metrics events published

### Within Each Phase

- All `[P]`-marked tasks within a phase may run in parallel
- Non-`[P]` tasks run sequentially or depend on same-phase `[P]` tasks completing
- `test_transition.py` MUST pass before US2 is marked complete

---

## Parallel Opportunities

### Phase 2: Foundational (all P tasks run simultaneously)

```text
T006 company-profile.md   ← solo
T007 product-docs.md      ← parallel with T008, T009, T010
T008 sample-tickets.json  ← parallel
T009 escalation-rules.md  ← parallel
T010 brand-voice.md       ← parallel
T011 schema.sql           ← solo (others depend on it)
T012 migration 001        ← parallel with T013
T013 migration 002        ← parallel
T014 queries.py           ← solo (depends on T011 schema)
T015 kafka_client.py      ← parallel with T016
T016 prompts.py           ← parallel
```

### Phase 3: US1 (parallel channel handlers)

```text
T017 gmail_handler.py     ← solo (most complex)
T018 whatsapp_handler.py  ← parallel with T017
T019 web_form_handler.py  ← parallel with T017, T018
T020 api/main.py          ← after T017, T018, T019 complete
T021 SupportForm.jsx      ← parallel with T020
T022 web-form tests       ← parallel with T021
T023 src/ incubation      ← parallel with T020
```

### Phase 4: US2 (incubation then production)

```text
T024 src prototype         ← solo first
T025 src memory            ← after T024
T026 mcp_server.py         ← after T025
T027 agent-skills.md       ← parallel with T026
T028 formatters.py         ← parallel with T029 (after incubation complete)
T029 tools.py              ← parallel with T028
T030 customer_agent.py     ← after T028, T029
T031 message_processor.py  ← after T030
T032 test_transition.py    ← after T031 (GATE — run immediately)
```

---

## Implementation Strategy

### MVP First (US1 Only — fastest working demo)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**CRITICAL**)
3. Complete Phase 3: US1 (web form channel first)
4. **STOP AND VALIDATE**: `curl POST /support/submit` creates ticket ✅
5. Add Gmail and WhatsApp handlers
6. Demo: all 3 channels ingest messages

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 → channels accept messages (demo: 3-channel intake)
3. US2 + Transition Gate → AI responds autonomously (demo: web form Q&A)
4. US3 → cross-channel identity works (demo: email + WhatsApp same customer)
5. US4 → escalation fires correctly (demo: pricing inquiry escalated)
6. US5 → metrics visible (demo: `/metrics/channels` shows 24h data)
7. Kubernetes deployment → production-ready

### Agent Factory Parallel Strategy

Per Principle II — Claude Code builds the Custom Agent:

1. Developer uses Claude Code on `src/` incubation (T024–T027) while channels are built (US1)
2. Once incubation prototype validates, transition to production tools (T028–T032)
3. `test_transition.py` confirms nothing was lost in the transition

---

## Notes

- `[P]` = different files, no same-phase dependency — run in parallel
- `[US#]` label maps task to specific user story for independent delivery
- T032 (`test_transition.py`) is a **hard gate** — do not skip per Constitution Principle VII
- Always `pytest production/tests/test_transition.py` before declaring US2 complete
- Commit after each phase checkpoint or when a logical group completes
- `production/` code must meet Principle III standards (Pydantic, try/except, no print())
- `src/` incubation code may be exploratory; document learnings in `discovery-log.md`
- Total tasks: **60** across 9 phases
