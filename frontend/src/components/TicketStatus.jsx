'use client';

import { useState } from 'react';
import { getTicketStatus, replyToTicket } from '@/lib/apiClient';

const STATUS_CONFIG = {
  open:        { label: 'Open',        bg: 'bg-blue-100 dark:bg-blue-900/40',     text: 'text-blue-700 dark:text-blue-300',     dot: 'bg-blue-500' },
  in_progress: { label: 'In Progress', bg: 'bg-yellow-100 dark:bg-yellow-900/40', text: 'text-yellow-700 dark:text-yellow-300', dot: 'bg-yellow-500' },
  resolved:    { label: 'Resolved',    bg: 'bg-green-100 dark:bg-green-900/40',   text: 'text-green-700 dark:text-green-300',   dot: 'bg-green-500' },
  closed:      { label: 'Closed',      bg: 'bg-gray-100 dark:bg-slate-700',       text: 'text-gray-600 dark:text-gray-400',     dot: 'bg-gray-400' },
  escalated:   { label: 'Escalated',   bg: 'bg-red-100 dark:bg-red-900/40',       text: 'text-red-700 dark:text-red-300',       dot: 'bg-red-500' },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function MessageBubble({ msg }) {
  const isAgent = msg.role === 'agent' || msg.direction === 'outbound';
  return (
    <div className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
        isAgent
          ? 'bg-blue-50 dark:bg-blue-900/30 text-gray-800 dark:text-gray-200 rounded-tl-sm border border-blue-100 dark:border-blue-800/40'
          : 'bg-blue-600 text-white rounded-tr-sm'
      }`}>
        <p className={`text-xs font-semibold mb-1 ${isAgent ? 'text-blue-600 dark:text-blue-400' : 'text-blue-100'}`}>
          {isAgent ? 'AI Support Agent' : 'You'}
        </p>
        <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        {msg.created_at && (
          <p className={`text-xs mt-2 ${isAgent ? 'text-gray-400 dark:text-gray-500' : 'text-blue-200'}`}>
            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  );
}

export default function TicketStatus() {
  const [ticketId, setTicketId] = useState('');
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [replyText, setReplyText] = useState('');
  const [replyLoading, setReplyLoading] = useState(false);
  const [replySent, setReplySent] = useState(false);

  async function handleLookup(e) {
    e.preventDefault();
    const id = ticketId.trim();
    if (!id) { setError('Please enter a ticket ID'); return; }
    setLoading(true); setError(''); setTicket(null); setReplySent(false); setReplyText('');
    try {
      setTicket(await getTicketStatus(id));
    } catch (err) {
      setError(err.message || 'Failed to fetch ticket. Please check the ID and try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleReply(e) {
    e.preventDefault();
    const text = replyText.trim();
    if (!text) return;
    setReplyLoading(true);
    try {
      await replyToTicket(ticket.ticket_id, text, ticket.customer_name || 'Customer');
      setReplyText('');
      setReplySent(true);
      setTimeout(async () => {
        try {
          setTicket(await getTicketStatus(ticket.ticket_id));
        } catch (_) {}
        setReplySent(false);
      }, 15000);
    } catch (err) {
      setError(err.message || 'Failed to send reply. Please try again.');
    } finally {
      setReplyLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Search */}
      <form onSubmit={handleLookup} className="flex gap-3">
        <input
          type="text" value={ticketId}
          onChange={e => { setTicketId(e.target.value); setError(''); }}
          placeholder="Enter your Ticket ID…"
          className="input-field flex-1"
        />
        <button type="submit" disabled={loading} className="btn-primary px-5 whitespace-nowrap">
          {loading ? (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
          Look Up
        </button>
      </form>

      {error && (
        <div className="rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 px-4 py-3 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {ticket && (
        <div className="space-y-5">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <p className="text-xs text-gray-400 font-mono mb-1">Ticket #{ticket.ticket_id?.slice(0, 8)}…</p>
              <h3 className="font-semibold text-gray-900 dark:text-white">{ticket.subject || 'Support Request'}</h3>
            </div>
            <StatusBadge status={ticket.status} />
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              { label: 'Customer', value: ticket.customer_name },
              { label: 'Priority',  value: ticket.priority },
              { label: 'Category',  value: ticket.category?.replace('_', ' ') },
              { label: 'Created',   value: ticket.created_at && new Date(ticket.created_at).toLocaleDateString() },
            ].filter(r => r.value).map(row => (
              <div key={row.label} className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">{row.label}</p>
                <p className="font-medium text-gray-800 dark:text-gray-200 capitalize">{row.value}</p>
              </div>
            ))}
          </div>

          {ticket.messages?.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Conversation</p>
              <div className="space-y-3 bg-gray-50 dark:bg-slate-700/30 rounded-xl p-4 border border-gray-100 dark:border-slate-600/30 max-h-80 overflow-y-auto">
                {ticket.messages.map((msg, i) => <MessageBubble key={msg.id || i} msg={msg} />)}
              </div>
            </div>
          )}

          {(ticket.status === 'open' || ticket.status === 'in_progress' || ticket.status === 'escalated') && (
            <div className="space-y-3">
              {replySent && (
                <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 px-4 py-3 text-sm text-blue-700 dark:text-blue-300">
                  Reply sent — refreshing in 15 s…
                </div>
              )}
              <form onSubmit={handleReply} className="space-y-2">
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">Send a Follow-up</p>
                <textarea
                  value={replyText}
                  onChange={e => setReplyText(e.target.value)}
                  placeholder="Type your follow-up message…"
                  rows={3}
                  disabled={replyLoading || replySent}
                  className="w-full rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={replyLoading || replySent || replyText.trim().length < 2}
                    className="btn-primary px-5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {replyLoading ? (
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : 'Send Reply'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {ticket.resolution_notes && (
            <div className="rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/40 px-4 py-3">
              <p className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1">Resolution Note</p>
              <p className="text-sm text-green-800 dark:text-green-300">{ticket.resolution_notes}</p>
            </div>
          )}

          <button onClick={() => { setTicket(null); setTicketId(''); setReplyText(''); setReplySent(false); setError(''); }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">
            ← Search another ticket
          </button>
        </div>
      )}

      {!ticket && !error && (
        <div className="text-center py-8 text-gray-300 dark:text-slate-600">
          <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-sm text-gray-400 dark:text-slate-500">Enter your ticket ID to check the status of your request</p>
        </div>
      )}
    </div>
  );
}
