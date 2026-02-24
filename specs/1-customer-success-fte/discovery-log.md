# Discovery Log — Customer Success Digital FTE

**Purpose**: Document incubation learnings that inform production architecture decisions.
**Branch**: `1-customer-success-fte`
**Stage**: Incubation → Specialization transition

---

## Channel Intake Discoveries (T023)

### Gmail Intake (`src/channels/gmail_intake.py`)

**Learning 1: Polling vs Pub/Sub latency**
- Polling Gmail API introduces 30–60 second latency
- Pub/Sub push notifications are near-real-time (< 2s)
- **Decision**: Use Gmail Pub/Sub in production (research.md Decision 4)

**Learning 2: Email address extraction**
- `From` header format: `"Name" <email>` or bare `email@domain`
- Must handle both; strip quotes from name
- Reply-To can differ from From; use From for customer identity

**Learning 3: Thread vs Message**
- Gmail threads group multiple messages
- Track `threadId` for conversation continuity across email replies
- Production: query active conversation by `threadId` before creating new one

**Learning 4: Body parsing**
- Plain-text in `payload.body.data` (base64url encoded)
- Multipart: search `payload.parts[]` for `mimeType: text/plain`
- HTML-only emails: will need html2text in production

---

### WhatsApp Intake (`src/channels/whatsapp_intake.py`)

**Learning 1: Twilio payload is form-encoded, not JSON**
- FastAPI must use `request.form()`, not `request.json()`
- `Content-Type: application/x-www-form-urlencoded`

**Learning 2: Phone number format**
- `From` field includes `whatsapp:` prefix → must strip
- `WaId` is numeric phone without prefix
- Normalise to E.164 format (+1XXXXXXXXXX) for CRM identity

**Learning 3: Signature validation is mandatory**
- X-Twilio-Signature header = HMAC-SHA1(auth_token, url + sorted_params)
- Must validate BEFORE any processing (403 if invalid)
- Production: use `twilio.request_validator.RequestValidator`

**Learning 4: Media messages**
- `NumMedia > 0` signals image/audio/video attachments
- `MediaUrl0` contains temporary Twilio-hosted URL
- v1 scope: skip media, reply with "Please describe your issue in text"

---

### Web Form Intake (`src/channels/web_form_intake.py`)

**Learning 1: Validation parity with React component**
- Frontend regex `/^[^\s@]+@[^\s@]+\.[^\s@]+$/` must match backend
- Same minimum lengths (name ≥ 2, subject ≥ 5, message ≥ 10)
- Prevents users bypassing client-side validation via direct API calls

**Learning 2: Category pre-classification**
- Web form provides `category` and `priority` not available in other channels
- Use `category: billing` as a soft escalation hint (combined with keyword detection)
- Store in ticket metadata for human agents reviewing escalations

---

## Agent Prototype Discoveries (T024–T025)

### Core Interaction Loop (`src/agent/prototype.py`)

**Learning 1: Keyword search is brittle**
- Section-splitting by `##` misses content in subsections (`###`)
- Matching any query word against section text creates too many false positives
- **Production decision**: Replace with pgvector cosine similarity search

**Learning 2: Escalation detection must run before search**
- Running knowledge search before escalation check wastes tokens on doomed requests
- Order: check escalation triggers → if clean, search KB → generate response
- Mirrors the system prompt's required workflow order

**Learning 3: Sentiment thresholds**
- Naïve word-list sentiment gives score of 0.0 for extreme negative messages
- Combined condition: `sentiment < 0.3 OR escalation keyword detected`
- Production: replace naïve scorer with LLM sentiment analysis (single-sentence prompt)

**Learning 4: Conversation memory structure**
```python
{
    "messages": [{"role": "customer"|"agent", "content": str, "channel": str}],
    "sentiment_scores": [float],  # history for trend detection
    "topics": [str],              # extracted topics for continuity
    "original_channel": str,
    "status": "active"|"escalated"|"resolved",
    "ticket_id": str,
}
```
- Key: `customer_id` (email in incubation; UUID in production)
- In production: persisted in PostgreSQL `conversations` + `messages` tables

---

## MCP Server Discoveries (T026)

**Learning 1: 1:1 tool signature mapping is essential**
- MCP tool signatures match production `@function_tool` signatures exactly
- Allows incubation testing with Claude Code before switching to OpenAI Agents SDK
- Deviation here would break the incubation → production transition

**Learning 2: Channel enum in both layers**
- `Channel(str, Enum)` with EMAIL/WHATSAPP/WEB_FORM defined in both `src/` and `production/`
- Production version shared across tools, formatters, and message_processor
- String values ("email", "whatsapp", "web_form") match database `channel` column values

**Learning 3: Tool ordering discipline**
- `create_ticket` must be called FIRST (creates the reference ID)
- `send_response` must be called LAST (delivery is irreversible)
- System prompt enforces this; test_transition.py (T032) gates it

---

## Key Decisions for Production Transition

| Incubation Pattern | Production Replacement | Rationale |
|---|---|---|
| In-memory `_conversations` dict | PostgreSQL `conversations` + `messages` tables | Durability, cross-instance state |
| Keyword search in product-docs.md | pgvector cosine similarity on `knowledge_base` | Semantic accuracy |
| Naïve word-list sentiment | LLM single-sentence sentiment prompt | Accuracy for edge cases |
| Gmail API polling | Gmail Pub/Sub push webhook | Latency (< 2s vs 30–60s) |
| `print()` debug output | Structured logging with `logging.getLogger` | Observability, no stdout in k8s |
| Synchronous function calls | `async def` with `asyncpg` | Non-blocking under load |
