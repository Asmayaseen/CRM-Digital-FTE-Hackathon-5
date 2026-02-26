---
id: "011"
title: Ticket Reply Conversation Continuity
stage: green
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 1-customer-success-fte
branch: main
user: asmayaseen
command: implement ticket reply / conversation continuity plan
labels: ["reply","conversation","web-form","fastapi","react","continuity"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - production/channels/web_form_handler.py
  - frontend/src/lib/apiClient.js
  - frontend/src/components/TicketStatus.jsx
tests:
  - manual: POST /support/ticket/{id}/reply returns 200 with same ticket_id
  - manual: GET /support/ticket/{id} shows follow-up messages after agent processes reply
  - manual: reply UI renders textarea + Send Reply button for open/in_progress tickets
  - manual: replySent banner appears and auto-refreshes after 15s
---

## Prompt

Implement the following plan:

# Plan: Ticket Reply / Conversation Continuity

## Context
Currently a user can submit one message via the web form and see the AI's response, but there is no way to send a follow-up. The user wants to continue chatting on the same ticket — asking follow-up questions and getting AI responses without creating a new ticket.

[...full plan with ReplyRequest model, reply endpoint, apiClient update, TicketStatus UI changes]

## Response snapshot

Implemented all three layers of the conversation continuity feature:

**Backend (`production/channels/web_form_handler.py`)**:
- Added `ReplyRequest` Pydantic model (message min 2 chars, customer_name default "Customer")
- Fixed `get_ticket_status` fallback SELECT to JOIN customers → returns `customer_email`, `customer_name`
- Added `customer_name` to the GET /ticket/{id} response body
- Added `POST /support/ticket/{ticket_id}/reply` endpoint:
  - Dual lookup: `get_ticket_by_id` → fallback channel_message_id JOIN with customers
  - 404 if not found, 422 if ticket is closed/resolved
  - Builds `message_data` with `channel_message_id = ticket_id` (preserves conversation thread)
  - Queues via `background_tasks.add_task(_message_processor, message_data)`
  - Returns `{"status": "received", "ticket_id": ticket_id}`

**Frontend apiClient (`frontend/src/lib/apiClient.js`)**:
- Added `replyToTicket(ticketId, message, customerName)` — POST to `/support/ticket/{id}/reply`

**Frontend UI (`frontend/src/components/TicketStatus.jsx`)**:
- Added state: `replyText`, `replyLoading`, `replySent`
- Added `handleReply()` async function with error handling and 15s auto-refresh
- Reply UI (textarea + Send Reply button) renders only when status is `open` or `in_progress`
- "Reply sent — refreshing in 15 s…" banner shown after successful send
- Button disabled when loading, replySent, or message < 2 chars

## Outcome

- ✅ Impact: Users can now have multi-turn conversations on a ticket without creating new tickets; same channel_message_id ensures the same conversation thread is reused by get_active_conversation(customer_id)
- 🧪 Tests: Manual E2E verification steps defined in plan
- 📁 Files: 3 files modified (web_form_handler.py, apiClient.js, TicketStatus.jsx)
- 🔁 Next prompts: Add read receipts / typing indicator; consider polling interval config
- 🧠 Reflection: The channel_message_id=ticket_id approach elegantly reuses the existing 24h active conversation lookup — no schema changes needed

## Evaluation notes (flywheel)

- Failure modes observed: none during implementation
- Graders run and results (PASS/FAIL): manual review only
- Prompt variant (if applicable): plan-mode → implement
- Next experiment (smallest change to try): reduce auto-refresh to 10s or add manual refresh button
