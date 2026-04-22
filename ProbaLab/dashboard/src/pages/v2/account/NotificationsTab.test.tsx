import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { NotificationsTab } from './NotificationsTab';
import { server } from '@/test/mocks/server';
import {
  mockNotificationChannels,
  mockNotificationRules,
} from '@/test/mocks/fixtures';

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

describe('NotificationsTab', () => {
  it('renders the page title', async () => {
    render(wrap(<NotificationsTab />));
    expect(
      screen.getByRole('heading', { level: 1, name: /notifications/i }),
    ).toBeInTheDocument();
  });

  it('renders both the channels card and the rules list', async () => {
    render(wrap(<NotificationsTab />));
    await screen.findByText(/canaux de notification/i);
    await screen.findByText(/règles actives/i);
  });

  it('renders rules from the API', async () => {
    render(wrap(<NotificationsTab />));
    await screen.findByText(/value bets haut edge/i);
    expect(screen.getByText(/safe du jour kick-off/i)).toBeInTheDocument();
  });

  it('opens the RuleBuilderModal when "Nouvelle règle" is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<NotificationsTab />));
    await screen.findByText(/value bets haut edge/i);
    await user.click(
      screen.getByRole('button', { name: /\+?\s*nouvelle règle/i }),
    );
    expect(
      screen.getByRole('heading', { level: 2, name: /nouvelle règle/i }),
    ).toBeInTheDocument();
  });

  it('opens the RuleBuilderModal in edit mode when Modifier is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<NotificationsTab />));
    await screen.findByText(/value bets haut edge/i);
    await user.click(
      screen.getByRole('button', { name: /menu value bets haut edge/i }),
    );
    await user.click(screen.getByRole('menuitem', { name: /modifier/i }));
    expect(
      screen.getByRole('heading', { level: 2, name: /modifier la règle/i }),
    ).toBeInTheDocument();
  });

  it('opens the DeleteRuleConfirm when Supprimer is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<NotificationsTab />));
    await screen.findByText(/drawdown critique/i);
    await user.click(
      screen.getByRole('button', { name: /menu drawdown critique/i }),
    );
    await user.click(screen.getByRole('menuitem', { name: /supprimer/i }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /supprimer la règle/i }),
    ).toBeInTheDocument();
    // The rule name shows inside the dialog as well as in the list below.
    expect(dialog.textContent).toMatch(/drawdown critique/i);
  });

  it('renders a skeleton while channels and rules are loading', () => {
    server.use(
      http.get(`${API}/api/user/notifications/channels`, async () => {
        await new Promise((r) => setTimeout(r, 500));
        return HttpResponse.json(mockNotificationChannels);
      }),
      http.get(`${API}/api/user/notifications/rules`, async () => {
        await new Promise((r) => setTimeout(r, 500));
        return HttpResponse.json(mockNotificationRules);
      }),
    );
    render(wrap(<NotificationsTab />));
    expect(screen.getByTestId('channels-card-skeleton')).toBeInTheDocument();
    expect(screen.getByTestId('rules-list-skeleton')).toBeInTheDocument();
  });

  it('exposes a data-testid on the root', async () => {
    render(wrap(<NotificationsTab data-testid="my-notif-tab" />));
    await waitFor(() => {
      expect(screen.getByTestId('my-notif-tab')).toBeInTheDocument();
    });
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<NotificationsTab />));
    await screen.findByText(/value bets haut edge/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
