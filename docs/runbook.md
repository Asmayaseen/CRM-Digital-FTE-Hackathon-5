# Runbook — CloudSync Pro Customer Success FTE

**Version**: 1.0
**Last Updated**: 2026-02-24
**On-call contact**: engineering@cloudsyncpro.com

---

## Table of Contents
1. [Service Overview](#service-overview)
2. [Health Checks](#health-checks)
3. [Common Incidents](#common-incidents)
4. [Escalation Procedures](#escalation-procedures)
5. [Deployment & Rollback](#deployment--rollback)
6. [Database Operations](#database-operations)
7. [Channel-Specific Troubleshooting](#channel-specific-troubleshooting)
8. [Monitoring & Alerts](#monitoring--alerts)

---

## Service Overview

| Component | Technology | Port | Health Check |
|-----------|-----------|------|-------------|
| API Server | FastAPI + Uvicorn | 8000 | `GET /health` |
| Frontend | Next.js | 3000 | `GET /` |
| Database | PostgreSQL 15 + pgvector | 5432 | `SELECT 1` |
| Message Queue | Apache Kafka | 9092 | `kafka-topics.sh --list` |
| AI Agent | Groq API (LLaMA 4) | external | Groq console |

---

## Health Checks

### Quick System Status
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","channels":{"email":"active","whatsapp":"active","web_form":"active"},"database":"active"}
```

### Check All Services
```bash
# API
curl -s http://localhost:8000/health | python3 -m json.tool

# Database
psql -U fte_user -d fte_db -c "SELECT COUNT(*) FROM tickets;"

# Kafka (if running)
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

---

## Common Incidents

### INC-001: API Not Responding

**Symptoms**: `curl http://localhost:8000/health` times out or connection refused

**Steps**:
```bash
# 1. Check if process is running
ps aux | grep uvicorn

# 2. Check what's on port 8000
lsof -i :8000

# 3. Kill stale processes if multiple
pkill -f uvicorn

# 4. Restart
cd /path/to/project
python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 &

# 5. Verify
curl http://localhost:8000/health
```

---

### INC-002: Database Connection Failed

**Symptoms**: Health check shows `"database":"inactive"` or DB errors in logs

**Steps**:
```bash
# 1. Check PostgreSQL is running
pg_isready -h localhost -p 5432

# 2. If not running, start it
sudo service postgresql start
# or
docker start postgres-container

# 3. Verify credentials
psql -U fte_user -d fte_db -h localhost -c "SELECT 1;"

# 4. Check connection pool settings in .env
grep POSTGRES .env

# 5. Restart API to reset pool
pkill -f uvicorn && python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 &
```

---

### INC-003: AI Agent Not Responding (Groq API Failure)

**Symptoms**: Tickets created but status stays `open` with no agent reply after 5+ minutes

**Steps**:
```bash
# 1. Test Groq API directly
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"

# 2. Check rate limits (Groq console)
# https://console.groq.com/usage

# 3. Check .env model name
grep AGENT_MODEL .env
# Should be: meta-llama/llama-4-scout-17b-16e-instruct

# 4. Verify API key
grep GROK_API_KEY .env

# 5. If rate limited: wait 1 minute, resubmit ticket manually
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","subject":"Test","message":"API test after rate limit"}'
```

---

### INC-004: Kafka Unavailable

**Symptoms**: Log shows `WARNING: Kafka unavailable — running without message queue`

**Impact**: System continues working via direct processor fallback. **Not critical.**

**Steps**:
```bash
# 1. This is expected in dev — no action needed
# 2. In production, restart Kafka:
docker-compose restart kafka zookeeper

# 3. Restart API to reconnect
pkill -f uvicorn && python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 &

# 4. Verify messages flowing
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group fte-workers
```

---

### INC-005: Gmail Channel Inactive

**Symptoms**: Health check shows `"email":"inactive"`

**Steps**:
```bash
# 1. Check credentials file exists
ls -la credentials/gmail-credentials.json

# 2. Test credentials
python3 -c "
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file('credentials/gmail-credentials.json')
service = build('gmail', 'v1', credentials=creds)
print(service.users().getProfile(userId='me').execute())
"

# 3. If token expired, regenerate:
python credentials/generate_gmail_token.py

# 4. Check GMAIL_CREDENTIALS_PATH in .env
grep GMAIL .env

# 5. Restart API
pkill -f uvicorn && python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 &
```

---

### INC-006: WhatsApp Messages Not Received

**Symptoms**: WhatsApp messages sent but no ticket created

**Steps**:
```bash
# 1. Check ngrok tunnel is running
curl http://localhost:4040/api/tunnels | python3 -m json.tool

# 2. If ngrok down, restart
/tmp/ngrok http 8000 &
sleep 3
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")
echo "New URL: $NGROK_URL/whatsapp/webhook"

# 3. Update Twilio webhook URL
# Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/sandbox
# Update "When a message comes in" URL to new ngrok URL

# 4. Test webhook manually
curl -X POST http://localhost:8000/whatsapp/webhook \
  -d "From=whatsapp:+1234567890&Body=Test+message&MessageSid=TEST123"
```

---

### INC-007: Web Form Submissions Hanging

**Symptoms**: POST /support/submit never returns (curl exit 28)

**Root cause history**:
1. `email-validator` DNS MX lookup blocking event loop → Fixed: `check_deliverability=False`
2. Kafka partial-init: `_producer` set but not started → Fixed: `_producer = None` after timeout
3. `publish()` blocking forever → Fixed: `asyncio.wait_for(..., timeout=5.0)`

**Steps**:
```bash
# 1. Quick test
curl -m 10 -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"t@t.com","subject":"Test","message":"Test message here"}'

# 2. If hanging, check for stale processes
ps aux | grep uvicorn | awk '{print $2}' | xargs -r kill
python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 &

# 3. Check Kafka producer state in logs
grep "Kafka" /tmp/fte.log | tail -10
```

---

### INC-008: High Memory Usage

**Symptoms**: OOMKilled in Kubernetes, or system slow

**Steps**:
```bash
# 1. Check memory usage
ps aux --sort=-%mem | head -10

# 2. Common cause: fastembed model loaded multiple times
# Verify singleton in production/agent/tools.py:
grep "_embedding_model" production/agent/tools.py

# 3. Force restart API
pkill -f uvicorn
python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --workers 2 &

# 4. In Kubernetes, trigger rolling restart
kubectl rollout restart deployment/fte-api -n fte-production
```

---

## Escalation Procedures

### Tier 1 — Automated (AI Agent)
- Resolvable queries: KB match above 0.70 cosine similarity
- Response time: < 15 seconds

### Tier 2 — Human Support Agent
Triggered when AI escalates (check tickets with `status = 'escalated'`):
```bash
# Find escalated tickets
psql -U fte_user -d fte_db -c "
  SELECT id, subject, priority, created_at
  FROM tickets WHERE status = 'escalated'
  ORDER BY created_at DESC LIMIT 20;"
```

### Tier 3 — Engineering On-Call
- Email: engineering@cloudsyncpro.com
- Trigger: API down > 5 min, data loss, security incident

### Tier 4 — Legal / Compliance
- Email: legal@cloudsyncpro.com
- Trigger: Any ticket with `escalation_reason = 'legal_language'`

---

## Deployment & Rollback

### Deploy New Version
```bash
# 1. Pull latest
git pull origin main

# 2. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 3. Run migration if schema changed
psql -U fte_user -d fte_db -f production/database/migrations/latest.sql

# 4. Run transition gate (MUST PASS)
pytest production/tests/test_transition.py -v
# If any test fails — DO NOT deploy

# 5. Restart API
pkill -f uvicorn
python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --workers 2 &

# 6. Restart frontend
cd frontend && npm run build && npm start &
```

### Rollback
```bash
# 1. Identify last good commit
git log --oneline -10

# 2. Rollback
git checkout <commit-hash>

# 3. Restart services
pkill -f uvicorn
python -m uvicorn production.api.main:app --host 0.0.0.0 --port 8000 &
```

### Kubernetes Rollback
```bash
kubectl rollout undo deployment/fte-api -n fte-production
kubectl rollout status deployment/fte-api -n fte-production
```

---

## Database Operations

### Backup
```bash
pg_dump -U fte_user -d fte_db -F c -f backups/fte_$(date +%Y%m%d).dump
```

### Restore
```bash
pg_restore -U fte_user -d fte_db -F c backups/fte_20260224.dump
```

### Common Queries
```sql
-- Active open tickets
SELECT id, subject, channel, priority, created_at
FROM tickets WHERE status = 'open'
ORDER BY priority DESC, created_at ASC;

-- Tickets by channel today
SELECT channel, COUNT(*) as count
FROM tickets WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY channel;

-- Average resolution time
SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/60) as avg_minutes
FROM tickets WHERE status = 'resolved' AND resolved_at IS NOT NULL;

-- Escalation rate
SELECT
  COUNT(*) FILTER (WHERE status = 'escalated') * 100.0 / COUNT(*) as escalation_pct
FROM tickets WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## Channel-Specific Troubleshooting

### Gmail Watch Expiry
Gmail Pub/Sub watch expires every 7 days. Renew:
```bash
curl -X POST http://localhost:8000/gmail/setup-watch
```
Set a cron job: `0 0 */6 * * curl -X POST http://localhost:8000/gmail/setup-watch`

### Twilio Sandbox Reset
If Twilio sandbox resets (monthly):
1. Go to https://console.twilio.com/us1/develop/phone-numbers/manage/sandbox
2. Re-join sandbox: WhatsApp `join <your-word>`
3. Update webhook URL if ngrok URL changed

---

## Monitoring & Alerts

### Key Metrics to Watch
| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| API response time (p95) | > 500ms | > 2000ms | Scale up workers |
| Ticket backlog (open) | > 50 | > 200 | Check agent health |
| Escalation rate | > 30% | > 60% | Check KB quality |
| DB connection errors | > 5/min | > 20/min | Restart API + check PG |
| Groq API errors | > 3/min | > 10/min | Check API key + rate limits |

### Log Locations
```bash
# API logs (if started with redirect)
tail -f /tmp/fte.log

# System logs
journalctl -u fte-api -f

# Kubernetes logs
kubectl logs -f deployment/fte-api -n fte-production
```
