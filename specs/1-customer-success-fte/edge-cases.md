# Edge Cases — CloudSync Pro Customer Success FTE

## Overview
This document catalogs edge cases discovered during incubation testing across all three channels (email, WhatsApp, web_form) and defines the handling strategy for each.

---

## Channel: Email (Gmail)

| # | Edge Case | Trigger | Handling Strategy |
|---|-----------|---------|-------------------|
| E1 | Empty email body | Body = "" or whitespace | Return 400; do not create ticket |
| E2 | Attachment-only email | No text body, has attachment | Extract subject only; reply requesting description |
| E3 | Email thread reply | In-Reply-To header present | Link to existing ticket via thread_id; skip create_ticket |
| E4 | Auto-reply / OOO | X-Autoreply or Auto-Submitted header | Detect and discard; never respond to auto-replies |
| E5 | Malformed From header | `From: <>` or no email address | Log warning; skip processing |
| E6 | Non-English email | Detected via langdetect | Respond in English; note language limitation |
| E7 | Forwarded email chain | "---------- Forwarded message" | Extract only latest message above fold |
| E8 | HTML-only email | No plain text part | Strip HTML tags; use text/html MIME part |
| E9 | Duplicate email (retry) | Same Message-ID received twice | Idempotency: skip if channel_message_id already exists |
| E10 | Email >10KB body | Long message | Truncate to first 2000 chars; append "[truncated]" note |

---

## Channel: WhatsApp (Twilio)

| # | Edge Case | Trigger | Handling Strategy |
|---|-----------|---------|-------------------|
| W1 | Media message (image/audio) | MediaUrl present in payload | Acknowledge receipt; ask customer to describe in text |
| W2 | Location share | Latitude/Longitude in payload | Ignore coordinates; ask for text description |
| W3 | Very short message | Body < 3 characters (e.g., "hi", "?") | Reply with greeting + "How can I help you today?" |
| W4 | Emoji-only message | e.g., "😡😡😡" | Sentiment = negative (<0.3); escalate to human |
| W5 | Phone number not in E.164 | Missing +country code | Normalize: prepend + if missing; log warning |
| W6 | Invalid Twilio signature | X-Twilio-Signature mismatch | Return 403; log security warning |
| W7 | Duplicate webhook | Same MessageSid received twice | Idempotency check on channel_message_id; skip |
| W8 | Message >300 chars | Customer sends long message | Accept full message; agent response still capped at 300 |
| W9 | "STOP" / opt-out keyword | Twilio opt-out message | Do NOT respond (Twilio handles); log as opt-out |
| W10 | Rapid repeat messages | >3 messages in 60 seconds | Rate-limit: queue messages; process sequentially |

---

## Channel: Web Form

| # | Edge Case | Trigger | Handling Strategy |
|---|-----------|---------|-------------------|
| F1 | Invalid email format | regex fails | Return 422 with field-level error |
| F2 | DNS-blocked email validation | email-validator with check_deliverability=True | Use check_deliverability=False to avoid DNS hang |
| F3 | Message < 10 characters | e.g., "help" | Return 422: "Message must be at least 10 characters" |
| F4 | XSS in subject/message | `<script>` tags | HTML-escape all inputs at storage; never render raw HTML |
| F5 | SQL injection attempt | `'; DROP TABLE tickets;` | Parameterized queries via asyncpg; input never interpolated |
| F6 | Rapid duplicate submissions | Same content, same email, < 5 min | Return existing ticket_id; do not create duplicate |
| F7 | Missing optional fields | name/category/priority empty | Use defaults: name="Anonymous", category="other", priority="medium" |
| F8 | Kafka unavailable at submit | Connection refused | Bypass Kafka; use direct message_processor call (background task) |
| F9 | Large message (>5000 chars) | User pastes wall of text | Accept; truncate to 2000 chars for KB search; store full text |
| F10 | Concurrent submissions | Same user, multiple tabs | Each gets unique ticket_id; handled independently |

---

## Agent Behaviour Edge Cases

| # | Edge Case | Trigger | Handling Strategy |
|---|-----------|---------|-------------------|
| A1 | KB returns 0 results | No vector match above threshold | Escalate after 2 failed searches; never hallucinate |
| A2 | Customer asks for pricing | Any price/cost/plan mention | Hard escalate immediately; never quote prices |
| A3 | Legal threat ("I'll sue") | Legal language detected | Do NOT respond; escalate to legal team instantly |
| A4 | Refund request | "refund", "money back", "charge" | Hard escalate to billing@cloudsyncpro.com |
| A5 | Profanity / abusive language | Profanity detected | Respond with empathy once; escalate if continues |
| A6 | Prior escalated ticket | get_customer_history shows escalated | Do NOT re-attempt; re-escalate immediately |
| A7 | Tool execution timeout | Tool call > 10 seconds | Retry once; if fails, escalate with timeout reason |
| A8 | Parallel tool calls | LLM tries concurrent calls | ModelSettings(parallel_tool_calls=False) enforced |
| A9 | Missing customer record | get_customer_history returns empty | Create new customer record; proceed without history |
| A10 | Cross-channel prior contact | Email ticket, now WhatsApp | Acknowledge prior contact; do NOT ask to repeat issue |

---

## Performance Edge Cases

| # | Edge Case | Trigger | Handling Strategy |
|---|-----------|---------|-------------------|
| P1 | pgvector slow search | >500ms embedding lookup | Index: `CREATE INDEX USING ivfflat`; max_results=5 |
| P2 | DB connection pool exhausted | >20 concurrent requests | Pool size=20, max_inactive=30s; queue excess |
| P3 | Groq API rate limit | 429 from Groq | Exponential backoff: 1s, 2s, 4s; max 3 retries |
| P4 | FastAPI event loop blocked | Sync code in async handler | All DB/AI calls use await; sync ops use run_in_executor |
| P5 | Memory leak in embeddings | fastembed model reloaded per request | Singleton model instance at module level |
