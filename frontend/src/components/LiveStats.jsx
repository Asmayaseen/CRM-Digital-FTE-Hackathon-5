'use client';

import { useEffect, useState } from 'react';
import { getSummaryMetrics } from '@/lib/apiClient';

const FALLBACK = [
  { value: '< 5s',  label: 'Avg. Response Time' },
  { value: '24/7',  label: 'Availability' },
  { value: '3',     label: 'Support Channels' },
  { value: '99.9%', label: 'Uptime SLA' },
];

export default function LiveStats() {
  const [stats, setStats] = useState(FALLBACK);
  const [live, setLive] = useState(false);

  useEffect(() => {
    getSummaryMetrics()
      .then(data => {
        setStats([
          {
            value: data.avg_latency_ms ? `${data.avg_latency_ms} ms` : '< 5s',
            label: 'Avg. Response Time',
          },
          {
            value: data.tickets_total?.toLocaleString() ?? '0',
            label: 'Tickets Resolved',
          },
          {
            value: data.customers_total?.toLocaleString() ?? '0',
            label: 'Customers Helped',
          },
          {
            value: data.escalation_rate_pct != null
              ? `${(100 - data.escalation_rate_pct).toFixed(1)}%`
              : '99.9%',
            label: 'AI Resolution Rate',
          },
        ]);
        setLive(true);
      })
      .catch(() => {
        // silently fall back to static values
      });
  }, []);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto animate-fade-up">
      {stats.map(s => (
        <div key={s.label} className="glass-card px-4 py-5 text-center glow-blue relative">
          {live && (
            <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" title="Live data" />
          )}
          <p className="text-3xl font-extrabold gradient-text mb-1">{s.value}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">{s.label}</p>
        </div>
      ))}
    </div>
  );
}
