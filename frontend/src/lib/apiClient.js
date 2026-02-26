const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Submit a support form ticket
 * @param {Object} formData
 * @returns {Promise<{ticket_id: string, message: string, estimated_response_time: string}>}
 */
export async function submitSupportForm(formData) {
  const res = await fetch(`${API_BASE}/support/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Get ticket status and conversation history
 * @param {string} ticketId
 * @returns {Promise<{ticket_id: string, status: string, messages: Array}>}
 */
export async function getTicketStatus(ticketId) {
  const res = await fetch(`${API_BASE}/support/ticket/${ticketId}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Ticket not found. Please check your ticket ID.');
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Send a follow-up reply on an existing ticket
 * @param {string} ticketId
 * @param {string} message
 * @param {string} customerName
 * @returns {Promise<{status: string, ticket_id: string}>}
 */
export async function replyToTicket(ticketId, message, customerName) {
  const res = await fetch(`${API_BASE}/support/ticket/${ticketId}/reply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, customer_name: customerName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Get system health
 * @returns {Promise<Object>}
 */
export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

/**
 * Get 24-hour performance metrics per channel
 * @returns {Promise<Object>}
 */
export async function getChannelMetrics() {
  const res = await fetch(`${API_BASE}/metrics/channels`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

/**
 * Get overall system metrics: totals, rates, distributions
 * @returns {Promise<Object>}
 */
export async function getSummaryMetrics() {
  const res = await fetch(`${API_BASE}/metrics/summary`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}
