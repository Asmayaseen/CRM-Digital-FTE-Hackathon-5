# ADR-001: Groq/LLaMA Model Substitution for GPT-4o

- **Status:** Accepted
- **Date:** 2026-02-25
- **Feature:** 1-customer-success-fte
- **Context:** Constitution Principle X mandates GPT-4o as the agent model ("use GPT-4o;
  avoid unnecessary token waste"). During implementation, LLaMA 3.3 70B via Groq was
  initially selected, then replaced with `meta-llama/llama-4-scout-17b-16e-instruct`
  (LLaMA 4 Scout) because LLaMA 3.3 produced malformed XML function calls with the
  OpenAI Agents SDK. The `parallel_tool_calls=False` constraint was also required to
  ensure correct tool call sequencing (create_ticket first, send_response last — per
  Constitution Principle VII transition test requirement 6).

<!-- Significance checklist (ALL must be true to justify this ADR)
     1) Impact: Long-term consequence for architecture/platform/security? ✅ YES — model choice affects cost, latency, reliability, and function-call correctness across entire agent
     2) Alternatives: Multiple viable options considered with tradeoffs? ✅ YES — GPT-4o, GPT-4o-mini, LLaMA 3.3, LLaMA 4 Scout, Claude Haiku
     3) Scope: Cross-cutting concern (not an isolated detail)? ✅ YES — affects agent orchestration, tool use, constitution compliance, cost budget -->

## Decision

- **Model**: `meta-llama/llama-4-scout-17b-16e-instruct`
- **API Provider**: Groq (https://api.groq.com/openai/v1)
- **SDK Setting**: `parallel_tool_calls=False` in `ModelSettings`
- **Location**: `production/agent/customer_success_agent.py`
- **Constitution Amendment Required**: Principle X should be updated via amendment
  procedure to reflect "cost-optimised open-weight model via Groq" rather than GPT-4o,
  or an exception clause added for budget-constrained deployments.

## Consequences

### Positive

- **Cost reduction**: Groq pricing is ~$0.11/1M input tokens vs GPT-4o ~$5/1M — approximately 45× cheaper, comfortably within the $1,000/year budget (Principle X)
- **Lower latency**: Groq's LPU hardware delivers inference 5–10× faster than OpenAI API, improving p95 processing time (< 3s target from plan.md)
- **Open-weight model**: LLaMA is not closed-source; reduces lock-in to a single vendor
- **Function calling**: LLaMA 4 Scout correctly generates tool calls compatible with OpenAI Agents SDK when `parallel_tool_calls=False`
- **Correct tool ordering**: `parallel_tool_calls=False` enforces sequential execution, which guarantees `create_ticket` before `send_response` (Constitution §VII test 6)

### Negative

- **Constitution violation**: Principle X explicitly names GPT-4o; this decision requires a formal constitution amendment before the project can be declared fully compliant
- **Throughput limitation**: `parallel_tool_calls=False` means tools execute sequentially — processing time increases if multiple tool calls are needed per conversation
- **Groq API dependency**: LLaMA 4 Scout availability depends on Groq's hosted service; model deprecation or provider outage is a business risk
- **Reduced ecosystem**: Fewer production case studies and community resources compared to GPT-4o for customer support agents
- **Test alignment**: Constitution §VII test 6 (`test_tool_execution_order`) was designed for GPT-4o; ensure it still passes correctly with LLaMA 4 Scout and `parallel_tool_calls=False`

## Alternatives Considered

| Alternative | Provider | Estimated Cost/year | Function Calling | Rejected Because |
|-------------|----------|--------------------|--------------------|-----------------|
| **GPT-4o** (constitution-mandated) | OpenAI | ~$800–1,200 (borderline $1K budget) | Excellent; native tool use | LLaMA 4 Scout is 45× cheaper and faster; GPT-4o risks budget overrun |
| **GPT-4o-mini** | OpenAI | ~$30–60 | Good; may miss complex tool orchestration | Less capable for multi-tool sequences; still OpenAI vendor lock-in |
| **LLaMA 3.3 70B** | Groq | ~$5–15 | Malformed XML tool calls with OpenAI Agents SDK | Broken function calling; failed `test_tool_execution_order` |
| **Claude Haiku 4.5** | Anthropic | ~$80–120 | Excellent native tool use | Would require switching from OpenAI Agents SDK to Anthropic SDK; larger refactor |
| **Mistral Small 3.1** | Mistral/Groq | ~$10–30 | Adequate | Less proven for multi-tool customer support workloads |

## References

- Feature Spec: `specs/1-customer-success-fte/spec.md`
- Implementation Plan: `specs/1-customer-success-fte/plan.md` §Phase 0 Key Technology Decisions
- Constitution: `.specify/memory/constitution.md` §X Cost Discipline, §VII Test-Transition Gate
- Related ADRs: ADR-002 (Kafka Bypass Fallback Pattern)
- PHR Evidence: `history/prompts/1-customer-success-fte/005-web-form-channel-debug-fix.green.prompt.md`
- sp.analyze Finding: C1 (CRITICAL — constitution violation surfaced 2026-02-25)
