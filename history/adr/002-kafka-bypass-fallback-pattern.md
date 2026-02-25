# ADR-002: Kafka Bypass Fallback Pattern

- **Status:** Accepted
- **Date:** 2026-02-25
- **Feature:** 1-customer-success-fte
- **Context:** Constitution Principle V mandates "All inter-service communication and
  channel intake MUST flow through Kafka topics." In production, the Kafka broker
  may be unavailable at pod startup (cloud cold start, Kubernetes pod ordering race,
  local development without Docker Compose running). Without a fallback, the entire
  API would refuse all requests when Kafka is temporarily unreachable — reducing
  availability below the 99.9% SC-007 target. A 5-second connection timeout was
  implemented at startup; if Kafka fails to connect, `kafka_producer._producer` is
  set to `None` and the system continues in degraded mode.

<!-- Significance checklist
     1) Impact: Affects system availability, data integrity, and constitution compliance ✅
     2) Alternatives: Hard failure vs retry vs circuit breaker vs in-memory queue ✅
     3) Scope: Cross-cutting — affects all three channel handlers and message processor ✅ -->

## Decision

- **Behaviour**: 5-second Kafka connection timeout at FastAPI startup
- **Degraded mode**: If timeout expires, `kafka_producer._producer = None`; API continues serving requests
- **Message processing**: Agent processes messages synchronously (no Kafka publish)
- **Metrics events**: Dropped silently when Kafka unavailable (not queued for retry)
- **DLQ**: Bypassed — errors logged to structured logger only
- **Location**: `production/api/main.py` startup handler, `production/kafka_client.py` `publish()` with `asyncio.wait_for(timeout=5.0)`
- **Constitution deviation**: This pattern deviates from Principle V and requires a formal constitution amendment noting "degraded mode is permitted when Kafka is transiently unavailable, provided it is monitored and alerted"

## Consequences

### Positive

- **High availability**: API and agent remain functional during Kafka outages; supports SC-007 (99.9% uptime)
- **Local development**: System works without running full Docker Compose (Kafka + Zookeeper); reduces developer setup friction
- **Graceful degradation**: Customers can still submit tickets and receive AI responses during infrastructure issues
- **Fast startup**: API pod ready in < 5 seconds regardless of Kafka broker state
- **No infinite hangs**: `asyncio.wait_for(timeout=5.0)` in `kafka_client.py` prevents `send_and_wait()` from blocking indefinitely

### Negative

- **Constitution violation**: Principle V is violated when bypass is active; requires amendment
- **Silent metric loss**: `fte.metrics` events are dropped during bypass — `agent_metrics` table will have gaps, affecting daily report accuracy (SC-008 impact)
- **No Kafka audit trail**: `fte.channels.*.inbound` topic events not published during bypass — compliance and debugging harder
- **Escalation events lost**: `fte.escalations` topic not published during bypass — human escalation team may not be notified of critical escalations
- **No recovery signalling**: System does not attempt to reconnect to Kafka after startup; bypass persists until pod restart
- **Observable gap**: `GET /health` must report Kafka status explicitly; without this, ops teams have no visibility into degraded mode

## Alternatives Considered

| Alternative | Behaviour | Why Rejected |
|-------------|-----------|--------------|
| **Hard failure** | Refuse all requests when Kafka unavailable | Violates SC-007 (99.9% availability); customer-facing downtime during infra issues |
| **Startup retry loop** | Retry Kafka connection every 30s before API starts accepting traffic | Delays pod readiness by up to minutes; Kubernetes readiness probes would fail repeatedly |
| **Background reconnect** | Mark Kafka as unavailable, retry in background thread every 60s | Most robust option; adds complexity; chosen for future improvement — see Next Steps |
| **In-memory queue fallback** | Buffer Kafka events in memory during outage, flush on reconnect | Risk of data loss on pod restart; violates Principle IV (state must survive pod restart) |
| **DLQ-first pattern** | All messages go to `fte.dlq` when main topics unavailable | DLQ consumer would need to replay in correct order; adds complexity; may violate topic semantics |

## Next Steps (Recommended)

1. Implement background Kafka reconnect in `kafka_client.py` — attempt reconnect every 60 seconds when `_producer is None`
2. Update `GET /health` to explicitly report `kafka: "degraded"` when bypass is active
3. Add Prometheus metric `kafka_bypass_active{channel="all"}` for alerting
4. Create constitution amendment: add §V exception clause for transient unavailability with monitoring requirement
5. Buffer `fte.escalations` events to PostgreSQL when Kafka unavailable — escalations are too critical to drop

## References

- Feature Spec: `specs/1-customer-success-fte/spec.md` §SC-007 (99.9% availability)
- Implementation Plan: `specs/1-customer-success-fte/plan.md` §Phase 1 Kafka Topics
- Constitution: `.specify/memory/constitution.md` §V Event-Driven via Kafka
- Related ADRs: ADR-001 (Groq/LLaMA Model Substitution)
- PHR Evidence: `history/prompts/1-customer-success-fte/005-web-form-channel-debug-fix.green.prompt.md`
- sp.analyze Finding: C2 (CRITICAL — constitution violation surfaced 2026-02-25)
