import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { RulesList } from './RulesList';
import { server } from '@/test/mocks/server';
import { mockNotificationRules } from '@/test/mocks/fixtures';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  server.resetHandlers();
});

describe('RulesList', () => {
  it('renders a skeleton while loading', () => {
    server.use(
      http.get(`${API}/api/user/notifications/rules`, async () => {
        await new Promise((r) => setTimeout(r, 500));
        return HttpResponse.json(mockNotificationRules);
      }),
    );
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    expect(screen.getByTestId('rules-list-skeleton')).toBeInTheDocument();
  });

  it('renders the header with title and create button', async () => {
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await screen.findByText(/règles actives/i);
    expect(
      screen.getByRole('button', { name: /\+?\s*nouvelle règle/i }),
    ).toBeInTheDocument();
  });

  it('renders each rule from the API', async () => {
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    // Each fixture rule should appear.
    await screen.findByText(/value bets haut edge/i);
    expect(screen.getByText(/safe du jour kick-off/i)).toBeInTheDocument();
    expect(screen.getByText(/drawdown critique/i)).toBeInTheDocument();
  });

  it('renders an empty state when no rules are returned', async () => {
    server.use(
      http.get(`${API}/api/user/notifications/rules`, () =>
        HttpResponse.json([]),
      ),
    );
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await screen.findByText(/aucune règle configurée/i);
  });

  it('calls onCreate when the "Nouvelle règle" button is clicked', async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();
    render(
      wrap(
        <RulesList
          onCreate={onCreate}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await screen.findByText(/value bets haut edge/i);
    await user.click(
      screen.getByRole('button', { name: /\+?\s*nouvelle règle/i }),
    );
    expect(onCreate).toHaveBeenCalledTimes(1);
  });

  it('forwards onEdit from a rule row', async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={onEdit}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await screen.findByText(/value bets haut edge/i);
    await user.click(
      screen.getByRole('button', { name: /menu value bets haut edge/i }),
    );
    await user.click(screen.getByRole('menuitem', { name: /modifier/i }));
    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit.mock.calls[0][0].id).toBe('rule-001');
  });

  it('forwards onDeleteRequest from a rule row', async () => {
    const user = userEvent.setup();
    const onDeleteRequest = vi.fn();
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={onDeleteRequest}
        />,
      ),
    );
    await screen.findByText(/drawdown critique/i);
    await user.click(
      screen.getByRole('button', { name: /menu drawdown critique/i }),
    );
    await user.click(screen.getByRole('menuitem', { name: /supprimer/i }));
    expect(onDeleteRequest).toHaveBeenCalledTimes(1);
    expect(onDeleteRequest.mock.calls[0][0].id).toBe('rule-003');
  });

  it('renders an error state when the API fails', async () => {
    server.use(
      http.get(`${API}/api/user/notifications/rules`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await screen.findByRole('alert');
    expect(screen.getByRole('alert').textContent).toMatch(/erreur/i);
  });

  it('exposes a data-testid on the root', async () => {
    render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
          data-testid="my-rules-list"
        />,
      ),
    );
    await waitFor(() => {
      expect(screen.getByTestId('my-rules-list')).toBeInTheDocument();
    });
  });

  it('has no axe violations', async () => {
    const { container } = render(
      wrap(
        <RulesList
          onCreate={vi.fn()}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await screen.findByText(/value bets haut edge/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
