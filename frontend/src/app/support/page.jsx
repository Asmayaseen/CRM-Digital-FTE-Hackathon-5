'use client';

import { useState } from 'react';
import SupportForm from '@/components/SupportForm';
import TicketStatus from '@/components/TicketStatus';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <button
      onClick={handleCopy}
      className="ml-2 inline-flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
      title="Copy ticket ID"
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-green-500">Copied!</span>
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Copy
        </>
      )}
    </button>
  );
}

const TABS = [
  {
    id: 'submit',
    label: 'Submit a Request',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
    ),
  },
  {
    id: 'status',
    label: 'Check Status',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
];

function SuccessBanner({ result, onReset }) {
  return (
    <div className="text-center py-8 space-y-5">
      <div className="flex justify-center">
        <div className="w-16 h-16 bg-green-100 dark:bg-green-900/40 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>
      <div>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-1">Request Submitted!</h3>
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          {result.message || 'Our AI agent will respond to your request shortly.'}
        </p>
      </div>
      <div className="inline-block bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-2xl px-6 py-4">
        <div className="flex items-center justify-center gap-1 mb-1">
          <p className="text-xs text-blue-500 dark:text-blue-400 font-medium">Your Ticket ID</p>
          <CopyButton text={result.ticket_id} />
        </div>
        <p className="font-mono font-bold text-blue-800 dark:text-blue-300 text-lg tracking-wide break-all">
          {result.ticket_id}
        </p>
      </div>
      {result.estimated_response_time && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Estimated response: <span className="font-semibold text-gray-700 dark:text-gray-200">{result.estimated_response_time}</span>
        </p>
      )}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40 rounded-xl px-4 py-3 text-sm text-amber-800 dark:text-amber-300 text-left">
        <p className="font-semibold mb-1">Save your Ticket ID</p>
        <p>Use the <strong>Check Status</strong> tab to view your AI agent&apos;s response anytime.</p>
      </div>
      <button onClick={onReset} className="btn-primary">
        Submit Another Request
      </button>
    </div>
  );
}

export default function SupportPage() {
  const [activeTab, setActiveTab] = useState('submit');
  const [submitResult, setSubmitResult] = useState(null);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12 space-y-8">

      {/* Page Header */}
      <div className="text-center space-y-3">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">How can we help you?</h2>
        <p className="text-gray-500 dark:text-gray-400">
          Our AI support agent responds in seconds — available 24/7.
        </p>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap justify-center gap-3">
        {[
          { icon: '⚡', label: 'Instant AI responses' },
          { icon: '🔒', label: 'Secure & private' },
          { icon: '🕐', label: '24/7 availability' },
        ].map(f => (
          <span key={f.label}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800
                       border border-gray-200 dark:border-slate-700 rounded-full text-sm
                       text-gray-600 dark:text-gray-300 shadow-sm">
            <span>{f.icon}</span> {f.label}
          </span>
        ))}
      </div>

      {/* Card */}
      <div className="card">
        {/* Tab Bar */}
        <div className="flex gap-1 bg-gray-100 dark:bg-slate-700/50 rounded-xl p-1 mb-6">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); if (tab.id === 'submit') setSubmitResult(null); }}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'submit' && (
          submitResult
            ? <SuccessBanner result={submitResult} onReset={() => setSubmitResult(null)} />
            : <SupportForm onSuccess={setSubmitResult} />
        )}
        {activeTab === 'status' && <TicketStatus />}
      </div>
    </div>
  );
}
