'use client';

import { useEffect, useState, useCallback } from 'react';
import { getSummaryMetrics, getChannelMetrics, getHealth } from '@/lib/apiClient';

const REFRESH_INTERVAL = 30;

function SkeletonBar({ className = '' }) {
  return (
    <div className={`animate-pulse bg-gray-200 dark:bg-slate-700 rounded ${className}`} />
  );
}

function KpiCard({ label, value, sub, loading }) {
  return (
    <div className="card p-5 flex flex-col gap-1">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
      {loading ? (
        <SkeletonBar className="h-8 w-24 mt-1" />
      ) : (
        <p className="text-3xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</p>
      )}
      {sub && !loading && (
        <p className="text-xs text-gray-400 dark:text-gray-500">{sub}</p>
      )}
    </div>
  );
}

function StatusDot({ ok }) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`}
    />
  );
}

function ProgressBar({ value, max, color = 'bg-blue-500' }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 dark:bg-slate-700 rounded-full h-3 overflow-hidden">
        <div
          className={`h-3 rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">{value}</span>
    </div>
  );
}

const STATUS_COLORS = {
  open: 'bg-blue-500',
  in_progress: 'bg-yellow-500',
  resolved: 'bg-green-500',
  closed: 'bg-gray-400',
  escalated: 'bg-red-500',
};

const CHANNEL_LABELS = {
  gmail: 'Gmail',
  whatsapp: 'WhatsApp',
  web_form: 'Web Form',
};

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [channels, setChannels] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c, h] = await Promise.all([
        getSummaryMetrics(),
        getChannelMetrics(),
        getHealth(),
      ]);
      setSummary(s);
      setChannels(c);
      setHealth(h);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setCountdown(REFRESH_INTERVAL);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Auto-refresh timer
  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          fetchAll();
          return REFRESH_INTERVAL;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const statusMax = summary
    ? Math.max(...Object.values(summary.ticket_status), 1)
    : 1;

  const channelMax = summary
    ? Math.max(...Object.values(summary.ticket_by_channel), 1)
    : 1;

  const dbOk = health?.database === 'connected';
  const channelHealth = health?.channels ?? {};

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white gradient-text">
            System Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Live metrics · 24-hour window
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!loading && (
            <span className="text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-slate-800 rounded-full px-3 py-1">
              Refreshing in {countdown}s
            </span>
          )}
          <button
            onClick={fetchAll}
            disabled={loading}
            className="btn-primary text-sm py-2 px-4 disabled:opacity-60"
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-5 py-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* System Health Row */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 uppercase tracking-wide">
          System Health
        </h2>
        {loading ? (
          <div className="flex gap-6">
            {[...Array(4)].map((_, i) => <SkeletonBar key={i} className="h-5 w-28" />)}
          </div>
        ) : (
          <div className="flex flex-wrap gap-6 items-center">
            <div className="flex items-center gap-2">
              <StatusDot ok={dbOk} />
              <span className="text-sm text-gray-700 dark:text-gray-300">Database</span>
            </div>
            {Object.entries(CHANNEL_LABELS).map(([key, label]) => (
              <div key={key} className="flex items-center gap-2">
                <StatusDot ok={channelHealth[key] !== 'error'} />
                <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          label="Tickets (24h)"
          value={summary?.tickets_24h?.toLocaleString()}
          sub={`${summary?.tickets_total?.toLocaleString() ?? '—'} total`}
          loading={loading}
        />
        <KpiCard
          label="Customers"
          value={summary?.customers_total?.toLocaleString()}
          loading={loading}
        />
        <KpiCard
          label="Conversations (24h)"
          value={summary?.conversations_24h?.toLocaleString()}
          loading={loading}
        />
        <KpiCard
          label="Messages (24h)"
          value={summary?.messages_24h?.toLocaleString()}
          loading={loading}
        />
        <KpiCard
          label="Avg Latency"
          value={summary?.avg_latency_ms != null ? `${summary.avg_latency_ms} ms` : '—'}
          loading={loading}
        />
        <KpiCard
          label="Escalation Rate"
          value={summary?.escalation_rate_pct != null ? `${summary.escalation_rate_pct}%` : '—'}
          sub={`${summary?.escalations_24h ?? 0} escalations`}
          loading={loading}
        />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Ticket Status Bars */}
        <div className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Ticket Status Distribution
          </h2>
          {loading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => <SkeletonBar key={i} className="h-4 w-full" />)}
            </div>
          ) : (
            <div className="space-y-3">
              {Object.entries(STATUS_COLORS).map(([status, color]) => (
                <div key={status}>
                  <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                    <span className="capitalize">{status.replace('_', ' ')}</span>
                  </div>
                  <ProgressBar
                    value={summary?.ticket_status?.[status] ?? 0}
                    max={statusMax}
                    color={color}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Ticket by Channel Bars */}
        <div className="card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Conversations by Channel (24h)
          </h2>
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => <SkeletonBar key={i} className="h-4 w-full" />)}
            </div>
          ) : (
            <div className="space-y-3">
              {Object.entries(CHANNEL_LABELS).map(([key, label]) => (
                <div key={key}>
                  <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                    <span>{label}</span>
                  </div>
                  <ProgressBar
                    value={summary?.ticket_by_channel?.[key] ?? 0}
                    max={channelMax}
                    color="bg-blue-500"
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Channel Breakdown Table */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-4">
          Channel Breakdown (24h)
        </h2>
        {loading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => <SkeletonBar key={i} className="h-6 w-full" />)}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide border-b border-gray-100 dark:border-slate-700">
                  <th className="pb-3 pr-6 font-medium">Channel</th>
                  <th className="pb-3 pr-6 font-medium">Conversations</th>
                  <th className="pb-3 pr-6 font-medium">Escalations</th>
                  <th className="pb-3 pr-6 font-medium">Avg Latency</th>
                  <th className="pb-3 font-medium">Avg Sentiment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-slate-700/50">
                {Object.entries(CHANNEL_LABELS).map(([key, label]) => {
                  const row = channels?.[key];
                  return (
                    <tr key={key} className="text-gray-700 dark:text-gray-300">
                      <td className="py-3 pr-6 font-medium">{label}</td>
                      <td className="py-3 pr-6">
                        {row ? Number(row.total_conversations).toLocaleString() : '—'}
                      </td>
                      <td className="py-3 pr-6">
                        {row ? Number(row.escalations).toLocaleString() : '—'}
                      </td>
                      <td className="py-3 pr-6">
                        {row?.avg_latency_ms != null
                          ? `${Math.round(row.avg_latency_ms)} ms`
                          : '—'}
                      </td>
                      <td className="py-3">
                        {row?.avg_sentiment != null
                          ? Number(row.avg_sentiment).toFixed(2)
                          : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
