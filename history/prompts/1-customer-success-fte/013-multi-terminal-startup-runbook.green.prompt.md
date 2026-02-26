---
id: "013"
title: Multi-Terminal Startup Runbook for Demo
stage: green
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 1-customer-success-fte
branch: main
user: asmayaseen
command: Add multi-terminal startup runbook (ji — yes, do it)
labels: ["runbook","demo","startup","multi-terminal","docs"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - docs/runbook.md
tests:
  - Manual: follow Terminal 1-4 steps, verify all services start
---

## Prompt

ji

(Context: user approved adding multi-terminal startup runbook to bring project to parity with Ashna's project on the "clearly documented for demos" front)

## Response snapshot

Added a prominent **"Demo Quick Start (Multi-Terminal)"** section to the top of `docs/runbook.md` (v1.0 → v1.1). Updated Table of Contents to include new section as item #1.

Section covers:
- Prerequisites checklist (DB, .env, deps, knowledge base seed)
- Terminal 1: Backend API (uvicorn with --reload, Kafka bypass note)
- Terminal 2: Frontend (Next.js npm run dev)
- Terminal 3: API logs (live tail via tee /tmp/fte.log)
- Terminal 4: Load test (Locust headless + web UI options)
- End-to-end demo flow (submit → status → reply → metrics → dashboard)
- Clean shutdown commands

## Outcome

- ✅ Impact: Project now has clear multi-terminal demo startup runbook — matches Ashna's project on this front
- 🧪 Tests: Manual walkthrough of all 4 terminal commands
- 📁 Files: 1 modified (docs/runbook.md)
- 🔁 Next prompts: git commit + PR to capture all 3 parity features (dashboard, locust, runbook)
- 🧠 Reflection: Added to existing runbook rather than creating new file — keeps docs consolidated

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): manual review PASS
- Prompt variant (if applicable): green (docs/implementation)
- Next experiment: add a one-liner bootstrap script (start.sh) that opens tmux panes automatically
