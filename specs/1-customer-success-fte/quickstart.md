# Quickstart: Customer Success Digital FTE

**Feature**: 1-customer-success-fte
**Date**: 2026-02-22
**Target**: Local development environment via Docker Compose

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop / Docker Engine | 24+ | Container runtime |
| Docker Compose | v2 | Local orchestration |
| Python | 3.11+ | Development and testing |
| Node.js | 18+ | Web form development |
| Git | any | Version control |

---

## 1. Clone and Branch

```bash
git clone <repo-url>
cd <repo-root>
git checkout 1-customer-success-fte
```

---

## 2. Configure Environment

Copy the environment template and fill in required values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fte_db
POSTGRES_USER=fte_user
POSTGRES_PASSWORD=changeme

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Gmail (see Step 5 for setup)
GMAIL_CREDENTIALS_PATH=./credentials/gmail-credentials.json
GMAIL_PUBSUB_TOPIC=projects/<gcp-project>/topics/gmail-notifications

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## 3. Start Infrastructure

```bash
docker-compose up -d postgres kafka zookeeper
```

Wait for services to be healthy:

```bash
docker-compose ps
# All should show "healthy" or "running"
```

---

## 4. Initialize Database

```bash
# Apply all migrations in order
docker exec -i fte_postgres psql -U fte_user -d fte_db \
  < production/database/migrations/001_initial_schema.sql

docker exec -i fte_postgres psql -U fte_user -d fte_db \
  < production/database/migrations/002_seed_channel_configs.sql

# Verify tables created
docker exec -it fte_postgres psql -U fte_user -d fte_db \
  -c "\dt"
```

Expected output: 7 tables listed (`customers`, `customer_identifiers`,
`conversations`, `messages`, `tickets`, `knowledge_base`, `channel_configs`,
`agent_metrics`).

---

## 5. Seed Knowledge Base

```bash
# Install Python dependencies
pip install -r production/requirements.txt

# Seed knowledge base from context/product-docs.md
python production/database/seed_knowledge_base.py \
  --source context/product-docs.md
```

This generates embeddings for each documentation section and inserts them into
`knowledge_base`. Requires a valid `OPENAI_API_KEY`.

---

## 6. Gmail Setup (Email Channel)

> Skip this step if testing Email channel is not required locally.
> Use ngrok or equivalent for webhook delivery to localhost.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable: Gmail API, Cloud Pub/Sub API
3. Create a Service Account with `Gmail API > gmail.modify` scope
4. Download credentials JSON → save to `./credentials/gmail-credentials.json`
5. Create a Pub/Sub topic named `gmail-notifications`
6. Grant `serviceAccount:...@gserviceaccount.com` the `pubsub.publisher` role
7. Start ngrok: `ngrok http 8000`
8. Register Gmail watch (run once):
   ```bash
   python -c "
   from production.channels.gmail_handler import GmailHandler
   import asyncio
   h = GmailHandler()
   asyncio.run(h.setup_push_notifications('projects/<project>/topics/gmail-notifications'))
   "
   ```

---

## 7. Twilio WhatsApp Setup

> Skip this step if testing WhatsApp is not required locally.

1. Log in to [Twilio Console](https://console.twilio.com/)
2. Navigate to Messaging > Try it out > Send a WhatsApp message
3. Join the Twilio Sandbox: send `join <sandbox-code>` to the sandbox number
4. Set Webhook URL in Twilio console:
   - Incoming messages: `https://<ngrok-url>/webhooks/whatsapp`
   - Status callbacks: `https://<ngrok-url>/webhooks/whatsapp/status`
5. Update `.env` with your `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
   and `TWILIO_WHATSAPP_NUMBER`

---

## 8. Run the Application

### Start the API Server

```bash
uvicorn production.api.main:app --reload --port 8000
```

Verify health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-22T...",
  "channels": {
    "email": "active",
    "whatsapp": "active",
    "web_form": "active"
  }
}
```

### Start the Message Processor (Worker)

In a separate terminal:

```bash
python production/workers/message_processor.py
```

You should see:
```
INFO: Message processor started, listening for tickets...
```

---

## 9. Test Web Form (Quickest Test)

The web form channel requires no external credentials. Submit a test ticket:

```bash
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "How do I reset my password?",
    "category": "technical",
    "priority": "medium",
    "message": "I forgot my password and cannot log in. How do I reset it?"
  }'
```

Expected response:
```json
{
  "ticket_id": "...",
  "message": "Thank you for contacting us! Our AI assistant will respond shortly.",
  "estimated_response_time": "Usually within 5 minutes"
}
```

Check the message processor log — it should show the agent processing the ticket
and the response being stored.

Retrieve the ticket response:

```bash
curl http://localhost:8000/support/ticket/<ticket_id>
```

---

## 10. Run Tests

### Transition Gate Tests (REQUIRED before any production merge)

```bash
pytest production/tests/test_transition.py -v
```

All 6 tests must pass. If any fail, do NOT proceed to production deployment.

### All Tests

```bash
pytest production/tests/ -v
```

### Web Form Component Tests

```bash
cd web-form
npm install
npm test
```

---

## 11. Full Docker Compose Stack

To run all components together (API + worker + infrastructure):

```bash
docker-compose up
```

This starts: PostgreSQL, Kafka, Zookeeper, `fte-api`, `fte-message-processor`.

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `pgvector extension not found` | pgvector not installed in Postgres image | Use `ankane/pgvector` Docker image |
| `Kafka connection refused` | Kafka not ready | Wait 30s after `docker-compose up` |
| `OPENAI_API_KEY not set` | Missing env var | Check `.env` file is loaded |
| `Invalid Twilio signature` | Wrong auth token or URL mismatch | Verify `TWILIO_AUTH_TOKEN` and webhook URL |
| `Gmail watch expired` | Watch expires every 7 days | Re-run `setup_push_notifications()` |
| Transition tests failing | Agent tool order wrong | Check `prompts.py` workflow order |

---

## Environment Tear-Down

```bash
docker-compose down -v   # Removes containers AND volumes (data lost)
docker-compose down      # Removes containers only (data preserved)
```
