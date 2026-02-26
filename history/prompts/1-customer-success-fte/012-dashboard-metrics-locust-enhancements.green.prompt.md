---
id: "012"
title: Dashboard Metrics Page + Locust Load Test Enhancements
stage: green
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 1-customer-success-fte
branch: main
user: asmayaseen
command: Implement the plan (Dashboard Metrics Page + Locust Load Test Enhancements)
labels: ["dashboard","metrics","frontend","load-test","locust","api"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - production/database/queries.py
  - production/api/main.py
  - frontend/src/lib/apiClient.js
  - frontend/src/app/dashboard/page.jsx
  - frontend/src/app/layout.jsx
  - tests/load_test.py
tests:
  - curl http://localhost:8000/metrics/summary
  - curl http://localhost:8000/metrics/channels
  - locust -f tests/load_test.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 1m --headless
---

## Prompt

Implement the following plan:

# Plan: Dashboard Metrics Page + Locust Load Test Enhancements

## Context
The referenced repo (Syedaashnaghazanfar/Customer-Support-FTE) has two features we lack:
1. A `/dashboard` page showing live metrics (ticket counts, channel breakdown, latency, escalation rate, system health)
2. Locust load tests covering the new `/reply` endpoint and metrics endpoints

The existing `tests/load_test.py` only covers submit + status + health. It needs the reply + metrics tasks added.
No chart library is installed (recharts/chart.js absent) — all charts will use pure Tailwind CSS.

Changes required across 6 files: queries.py, main.py, apiClient.js, dashboard/page.jsx (new), layout.jsx, load_test.py.

## Response snapshot

Implemented all 6 changes:

1. **`production/database/queries.py`** — Added `get_summary_metrics()` after line 381. Runs 6 scalar COUNT queries + escalation_rate calc + AVG latency + ticket_status GROUP BY + ticket_by_channel GROUP BY, all in a single connection. Returns typed dict.

2. **`production/api/main.py`** — Added `GET /metrics/summary` endpoint after `/metrics/channels` (line 208). Uses local import of `get_summary_metrics`.

3. **`frontend/src/lib/apiClient.js`** — Added `getChannelMetrics()` (GET `/metrics/channels`) and `getSummaryMetrics()` (GET `/metrics/summary`) exports.

4. **`frontend/src/app/dashboard/page.jsx`** — Created new `'use client'` React page with:
   - Auto-refresh every 30s with countdown pill
   - System health row (DB dot + Gmail/WhatsApp/Web Form dots)
   - 6 KPI cards (Tickets 24h, Customers, Conversations, Messages, Avg Latency, Escalation Rate)
   - Ticket status distribution (5 CSS progress bars per status)
   - Conversations by channel (3 CSS bars relative to max)
   - Channel breakdown table (Conversations, Escalations, Avg Latency, Avg Sentiment)
   - Skeleton loading state (animate-pulse) while fetching
   - `Promise.all([getSummaryMetrics(), getChannelMetrics(), getHealth()])` on load/refresh

5. **`frontend/src/app/layout.jsx`** — Added `<Link href="/dashboard">Dashboard</Link>` nav link after Channels.

6. **`tests/load_test.py`** — Added `send_reply()` @task(3) to SupportAPIUser; added `check_channel_metrics()` @task(2) and `check_summary_metrics()` @task(1) to AdminAPIUser; updated module docstring with full endpoint list.

## Outcome

- ✅ Impact: Full dashboard metrics page live at /dashboard; backend /metrics/summary endpoint added; load tests cover /reply and metrics endpoints
- 🧪 Tests: Manual curl verification; Locust headless run with 50 users
- 📁 Files: 5 modified + 1 created (frontend/src/app/dashboard/page.jsx)
- 🔁 Next prompts: verify dashboard renders with live DB data; consider adding /metrics/summary to health checks
- 🧠 Reflection: Pure Tailwind CSS progress bars avoid any chart library dependency. Promise.all keeps load fast. Skeleton state gives good UX on first load.

## Evaluation notes (flywheel)

- Failure modes observed: none — additive changes only, no existing behavior modified
- Graders run and results (PASS/FAIL): manual code review PASS
- Prompt variant (if applicable): green (implementation)
- Next experiment: add E2E Playwright test for /dashboard page render
