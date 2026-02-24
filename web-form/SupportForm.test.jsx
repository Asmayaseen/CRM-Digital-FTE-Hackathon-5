import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import SupportForm from './SupportForm';

// ---------------------------------------------------------------------------
// Mock fetch globally
// ---------------------------------------------------------------------------
global.fetch = jest.fn();

const fillValidForm = async (user) => {
  await user.type(screen.getByLabelText(/your name/i), 'Jane Smith');
  await user.type(screen.getByLabelText(/email address/i), 'jane@example.com');
  await user.type(screen.getByLabelText(/subject/i), 'Cannot sync files');
  await user.type(
    screen.getByLabelText(/how can we help/i),
    'My files are not syncing to the cloud drive. I have tried restarting.'
  );
};

beforeEach(() => {
  fetch.mockClear();
});

// ---------------------------------------------------------------------------
// Test 1: Component renders
// ---------------------------------------------------------------------------

test('renders the support form with all required fields', () => {
  render(<SupportForm />);

  expect(screen.getByLabelText(/your name/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/subject/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/how can we help/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /submit support request/i })).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// Test 2: Validation — empty form
// ---------------------------------------------------------------------------

test('shows validation error when name is too short', async () => {
  const user = userEvent.setup();
  render(<SupportForm />);

  await user.type(screen.getByLabelText(/your name/i), 'J');
  fireEvent.click(screen.getByRole('button', { name: /submit support request/i }));

  await waitFor(() => {
    expect(screen.getByText(/at least 2 characters/i)).toBeInTheDocument();
  });
});

test('shows validation error for invalid email', async () => {
  const user = userEvent.setup();
  render(<SupportForm />);

  await user.type(screen.getByLabelText(/your name/i), 'Jane Smith');
  await user.type(screen.getByLabelText(/email address/i), 'not-an-email');
  fireEvent.click(screen.getByRole('button', { name: /submit support request/i }));

  await waitFor(() => {
    expect(screen.getByText(/valid email/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 3: Successful submission — displays ticketId
// ---------------------------------------------------------------------------

test('displays ticket ID after successful submission', async () => {
  const user = userEvent.setup();
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ticket_id: 'TICKET-ABCD1234', status: 'open' }),
  });

  render(<SupportForm />);
  await fillValidForm(user);
  fireEvent.click(screen.getByRole('button', { name: /submit support request/i }));

  await waitFor(() => {
    expect(screen.getByText('TICKET-ABCD1234')).toBeInTheDocument();
    expect(screen.getByText(/thank you/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 4: Error state — network failure
// ---------------------------------------------------------------------------

test('shows error message on network failure', async () => {
  const user = userEvent.setup();
  fetch.mockRejectedValueOnce(new Error('Network error'));

  render(<SupportForm />);
  await fillValidForm(user);
  fireEvent.click(screen.getByRole('button', { name: /submit support request/i }));

  await waitFor(() => {
    expect(screen.getByText(/network error/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 5: Error state — API 422
// ---------------------------------------------------------------------------

test('shows error message on API 422 response', async () => {
  const user = userEvent.setup();
  fetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: 'Invalid email address format' }),
  });

  render(<SupportForm />);
  await fillValidForm(user);
  fireEvent.click(screen.getByRole('button', { name: /submit support request/i }));

  await waitFor(() => {
    expect(screen.getByText(/invalid email address format/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 6: Submit another request resets form
// ---------------------------------------------------------------------------

test('submit another request button resets the form', async () => {
  const user = userEvent.setup();
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ticket_id: 'TICKET-XYZ', status: 'open' }),
  });

  render(<SupportForm />);
  await fillValidForm(user);
  fireEvent.click(screen.getByRole('button', { name: /submit support request/i }));

  await waitFor(() => {
    expect(screen.getByText('TICKET-XYZ')).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole('button', { name: /submit another request/i }));

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /submit support request/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/your name/i)).toHaveValue('');
  });
});

// ---------------------------------------------------------------------------
// Test 7: Character counter updates
// ---------------------------------------------------------------------------

test('character counter updates as user types in message field', async () => {
  const user = userEvent.setup();
  render(<SupportForm />);

  const textarea = screen.getByLabelText(/how can we help/i);
  await user.type(textarea, 'Hello world');

  expect(screen.getByText(/11\/1000 characters/i)).toBeInTheDocument();
});
