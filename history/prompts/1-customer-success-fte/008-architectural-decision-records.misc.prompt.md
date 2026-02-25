---
id: "008"
title: Architectural Decision Records Creation
stage: misc
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 1-customer-success-fte
branch: main
user: asmayaseen
command: /sp.adr groq-llama-model-substitution
labels: ["adr","architecture","model-selection","kafka","groq","llama","decision"]
links:
  spec: specs/1-customer-success-fte/spec.md
  ticket: null
  adr: history/adr/001-groq-llama-model-substitution.md
  pr: null
files:
  - history/adr/001-groq-llama-model-substitution.md (created)
  - history/adr/002-kafka-bypass-fallback-pattern.md (created)
tests:
  - none
---

## Prompt

Run sp.adr groq-llama-model-substitution — document the Groq/LLaMA model substitution
as an Architecture Decision Record. Also document the Kafka bypass fallback pattern
(second CRITICAL finding from sp.analyze C2).

## Response snapshot

Created 2 ADRs documenting CRITICAL architectural deviations identified in sp.analyze:

**ADR-001: Groq/LLaMA Model Substitution**
- Status: Accepted
- Decision: Use meta-llama/llama-4-scout-17b-16e-instruct via Groq instead of GPT-4o
- Rationale: 45× cheaper ($0.11 vs $5/1M tokens), 5–10× lower latency, open-weight
- Tradeoffs: Constitution §X violation requires amendment; parallel_tool_calls=False
  reduces throughput; Groq API availability dependency
- Alternatives considered: GPT-4o (budget risk), GPT-4o-mini (less capable),
  LLaMA 3.3 (broken function calling), Claude Haiku (SDK switch needed), Mistral

**ADR-002: Kafka Bypass Fallback Pattern**
- Status: Accepted
- Decision: 5-second startup timeout; if Kafka unavailable, kafka_producer._producer=None;
  API continues in degraded mode (no Kafka publish)
- Rationale: Supports SC-007 99.9% availability; enables local dev without Docker Compose
- Tradeoffs: Constitution §V violation; metrics events dropped; escalation events lost;
  no reconnect logic
- Next Steps: Background reconnect, /health Kafka status, buffer escalations to PostgreSQL

## Outcome

- ✅ Impact: 2 ADRs created documenting both CRITICAL constitution deviations from sp.analyze;
  each ADR includes significance justification, full alternatives table, positive/negative
  consequences, and next steps; both reference PHR evidence from implementation sessions
- 🧪 Tests: none (documentation artifacts)
- 📁 Files: history/adr/001-groq-llama-model-substitution.md (created),
  history/adr/002-kafka-bypass-fallback-pattern.md (created)
- 🔁 Next prompts: Update constitution §X and §V with amendment procedure;
  implement background Kafka reconnect; add kafka status to /health endpoint
- 🧠 Reflection: Both ADRs address pragmatic deviations made during implementation to
  solve real constraints (model XML errors, infrastructure availability); documenting
  them formally closes the gap between constitution and production reality

## Evaluation notes (flywheel)

- Failure modes observed: none — all placeholders resolved; both files created successfully
- Graders run and results (PASS/FAIL): significance test PASS for both (impact ✅, alternatives ✅, cross-cutting ✅)
- Prompt variant (if applicable): user specified groq-llama-model-substitution; kafka-bypass added from sp.analyze C2
- Next experiment (smallest change to try): implement ADR-002 §Next Steps item 1 (background Kafka reconnect)
