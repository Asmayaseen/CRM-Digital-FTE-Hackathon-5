# Agent Skills Manifest — Customer Success Digital FTE

**Version**: 1.0
**Agent**: Customer Success FTE (OpenAI Agents SDK)
**Model**: gpt-4o
**Date**: 2026-02-22

---

## Overview

Five core skills map directly to the five `@function_tool` functions in
`production/agent/tools.py`. Each skill has a defined trigger condition,
required inputs, expected outputs, and test cases that are exercised in
`production/tests/test_transition.py`.

---

## Skill 1: Knowledge Retrieval

**Tool**: `search_knowledge_base(query: str, max_results: int = 5)`

**When to use**:
- Customer asks a question about product features, how-to guides, or account settings
- After `create_ticket` and `get_customer_history` have been called
- Only if no escalation trigger has been detected
- Maximum 2 attempts before escalating with reason `"knowledge_not_found"`

**Inputs**:
- `query`: Reformulated search query (not the raw customer message)
  - Strip filler words, focus on noun phrases
  - Example: "how to reset password" → "password reset steps"
- `max_results`: Default 5; reduce to 3 for WhatsApp (response length constraint)

**Outputs**:
- Up to 5 matching knowledge base entries ranked by cosine similarity
- Each entry: `title`, `content` (truncated to 500 chars), `similarity_score`
- Empty list if no entries exceed similarity threshold (0.7)

**Test Cases**:
```
Input: "how do I reset my password"
Expected: results[0].title contains "Password" OR "Account Settings"
Expected: similarity_score > 0.7

Input: "pricing enterprise plan"
Expected: should NOT be called (escalation detected first)
Expected: escalation reason = "pricing_inquiry"

Input: "qwerty nonsense xyz"
Expected: empty results
Expected: agent escalates after 2 failed searches
```

---

## Skill 2: Sentiment Analysis

**Tool**: Integrated into `process_message()` in `production/workers/message_processor.py`
(not a separate `@function_tool` — computed before agent invocation)

**When to use**:
- Every message is scored before agent processing begins
- Sentiment score stored in `messages.sentiment_score` column
- Score < 0.3 triggers escalation regardless of message content

**Inputs**:
- `message_content`: Raw customer message text

**Outputs**:
- `sentiment_score`: float 0.0–1.0
  - 0.0–0.29: Negative → escalate with reason `"negative_sentiment"`
  - 0.30–0.69: Neutral → proceed with agent
  - 0.70–1.0: Positive → proceed with agent

**Test Cases**:
```
Input: "This product is absolute garbage, I want my money back!!!"
Expected: score < 0.3
Expected: escalation triggered, reason = "negative_sentiment"

Input: "How do I add a new team member?"
Expected: 0.3 <= score <= 1.0
Expected: no sentiment-based escalation

Input: "I'm so frustrated and angry, nothing works"
Expected: score < 0.3
Expected: escalation triggered
```

---

## Skill 3: Escalation Decision

**Tool**: `escalate_to_human(ticket_id: str, reason: str, urgency: str = "normal")`

**When to use**:
Escalate IMMEDIATELY (do not search KB) when ANY of these conditions are met:
1. `pricing_inquiry`: message contains pricing/cost/price/plan comparison keywords
2. `refund_request`: message contains refund/money back/charge dispute keywords
3. `legal_language`: message contains lawyer/sue/legal/attorney/lawsuit keywords
4. `negative_sentiment`: sentiment_score < 0.3 (computed pre-agent)
5. `explicit_human_request`: message contains human/agent/real person/representative
6. `knowledge_not_found`: 2 consecutive `search_knowledge_base` calls returned empty

**Inputs**:
- `ticket_id`: From `create_ticket` (always called first)
- `reason`: One of the 6 reason codes above
- `urgency`: `"urgent"` for legal/refund/very negative; `"normal"` otherwise

**Outputs**:
- Confirmation string: `"Escalated TICKET-XXX to human support. Reason: ... | Urgency: ..."`
- Side effect: ticket status → `"escalated"`, Kafka event published to `fte.escalations`

**Test Cases**:
```
Input: "I want to sue your company for this"
Expected: escalate called with reason="legal_language", urgency="urgent"
Expected: NO attempt to search KB

Input: "How much does the enterprise plan cost?"
Expected: escalate called with reason="pricing_inquiry"
Expected: NO price information in response

Input: "Can I speak to a real person please?"
Expected: escalate called with reason="explicit_human_request"
```

---

## Skill 4: Channel Adaptation

**Tool**: `send_response(ticket_id: str, message: str, channel: str)`
(formatting applied inside tool via `format_for_channel()`)

**When to use**:
- ALWAYS called last in the tool sequence
- Never call before `create_ticket` has been called
- Called once per interaction (do not double-send)

**Inputs**:
- `ticket_id`: From `create_ticket`
- `message`: Raw response text (before channel formatting)
- `channel`: `"email"` | `"whatsapp"` | `"web_form"`

**Channel Formatting Rules** (applied by `production/agent/formatters.py`):

| Channel | Max Length | Greeting | Signature | Append |
|---------|-----------|----------|-----------|--------|
| email | 2000 chars | "Hi {name}," | "Best regards, CloudSync Pro Support" + ticket ref | — |
| whatsapp | 300 chars | None | None | "📱 Reply for more help or type 'human' for live support." |
| web_form | 1000 chars | None | None | Help portal link |

**Test Cases**:
```
Channel: email
Expected: response starts with "Hi " (greeting)
Expected: response ends with "Best regards"
Expected: ticket ID present in response

Channel: whatsapp
Expected: len(response) < 500 (ideally < 300)
Expected: no formal greeting
Expected: ends with 📱 emoji line

Channel: web_form
Expected: len(response) < 1000
Expected: help portal link present
```

---

## Skill 5: Customer Identification

**Tool**: `get_customer_history(customer_id: str)`

**When to use**:
- Always called SECOND (after `create_ticket`, before `search_knowledge_base`)
- Provides context to avoid asking customer to repeat themselves
- Result informs acknowledgment of prior contact

**Inputs**:
- `customer_id`: UUID from `get_or_create_customer()` in `message_processor.py`
  (the agent receives this via the system prompt context, NOT from a tool call)

**Outputs**:
- Last 20 messages across ALL channels, ordered by `created_at DESC`
- Format: `"[email] customer: message content..."` (truncated)
- Empty string if first-time customer

**Cross-Channel Continuity Response Pattern**:
```
If history contains prior messages:
  "I can see you've contacted us before about {topic}. Let me help you further..."
If history is empty:
  Proceed without acknowledgment preamble
```

**Test Cases**:
```
Customer with prior email history, now on WhatsApp:
Expected: history returned includes email messages
Expected: response acknowledges prior contact

New customer (no history):
Expected: empty string returned
Expected: no "I see you contacted us before" in response
```

---

## Tool Execution Order (Constitution Principle — ENFORCED)

```
1. create_ticket          ← ALWAYS FIRST
2. get_customer_history   ← ALWAYS SECOND
3. search_knowledge_base  ← IF no escalation (max 2 calls)
   OR
3. escalate_to_human      ← IF any escalation trigger detected
4. send_response          ← ALWAYS LAST
```

This order is enforced by:
- System prompt in `production/agent/prompts.py`
- `test_tool_execution_order` test in `production/tests/test_transition.py` (T032)

---

## Skill Coverage Matrix

| User Story | Skills Used |
|---|---|
| US1: Multi-Channel Intake | Customer Identification (initial) |
| US2: Autonomous Resolution | All 5 skills |
| US3: Cross-Channel Continuity | Customer Identification (cross-channel JOIN) |
| US4: Human Escalation | Escalation Decision, Channel Adaptation (notification) |
| US5: Reporting | Sentiment Analysis (score stored per message) |
