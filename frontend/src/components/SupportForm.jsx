'use client';

import { useState } from 'react';
import { submitSupportForm } from '@/lib/apiClient';

const CATEGORIES = [
  { value: 'billing', label: 'Billing & Payments' },
  { value: 'technical', label: 'Technical Issue' },
  { value: 'account', label: 'Account Management' },
  { value: 'feature_request', label: 'Feature Request' },
  { value: 'other', label: 'Other' },
];

const PRIORITIES = [
  { value: 'low', label: 'Low', color: 'text-green-600' },
  { value: 'medium', label: 'Medium', color: 'text-yellow-600' },
  { value: 'high', label: 'High', color: 'text-orange-600' },
  { value: 'urgent', label: 'Urgent', color: 'text-red-600' },
];

export default function SupportForm({ onSuccess }) {
  const [form, setForm] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
    category: 'technical',
    priority: 'medium',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = 'Name is required';
    if (!form.email.trim()) {
      e.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      e.email = 'Enter a valid email address';
    }
    if (!form.subject.trim()) e.subject = 'Subject is required';
    if (!form.message.trim()) {
      e.message = 'Message is required';
    } else if (form.message.trim().length < 10) {
      e.message = 'Message must be at least 10 characters';
    }
    return e;
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
    if (apiError) setApiError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);
    setApiError('');
    try {
      const result = await submitSupportForm(form);
      onSuccess(result);
    } catch (err) {
      setApiError(err.message || 'Failed to submit. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Full Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          name="name"
          value={form.name}
          onChange={handleChange}
          placeholder="John Smith"
          className={`input-field ${errors.name ? 'border-red-400 focus:ring-red-400' : ''}`}
        />
        {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name}</p>}
      </div>

      {/* Email */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Email Address <span className="text-red-500">*</span>
        </label>
        <input
          type="email"
          name="email"
          value={form.email}
          onChange={handleChange}
          placeholder="john@example.com"
          className={`input-field ${errors.email ? 'border-red-400 focus:ring-red-400' : ''}`}
        />
        {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email}</p>}
      </div>

      {/* Category + Priority */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Category</label>
          <select
            name="category"
            value={form.category}
            onChange={handleChange}
            className="input-field"
          >
            {CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
          <select
            name="priority"
            value={form.priority}
            onChange={handleChange}
            className="input-field"
          >
            {PRIORITIES.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Subject */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Subject <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          name="subject"
          value={form.subject}
          onChange={handleChange}
          placeholder="Brief description of your issue"
          className={`input-field ${errors.subject ? 'border-red-400 focus:ring-red-400' : ''}`}
        />
        {errors.subject && <p className="mt-1 text-xs text-red-500">{errors.subject}</p>}
      </div>

      {/* Message */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Message <span className="text-red-500">*</span>
        </label>
        <textarea
          name="message"
          value={form.message}
          onChange={handleChange}
          rows={5}
          maxLength={1000}
          placeholder="Please describe your issue in detail..."
          className={`input-field resize-none ${errors.message ? 'border-red-400 focus:ring-red-400' : ''}`}
        />
        <div className="flex justify-between items-center mt-1">
          {errors.message
            ? <p className="text-xs text-red-500">{errors.message}</p>
            : <span />}
          <span className={`text-xs font-medium ${
            form.message.length > 900 ? 'text-red-500' :
            form.message.length > 700 ? 'text-yellow-500' :
            'text-gray-400 dark:text-gray-500'
          }`}>
            {form.message.length} / 1000
          </span>
        </div>
      </div>

      {/* API Error */}
      {apiError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {apiError}
        </div>
      )}

      {/* Submit */}
      <button type="submit" disabled={loading} className="btn-primary w-full">
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Submitting…
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            Submit Support Request
          </>
        )}
      </button>
    </form>
  );
}
