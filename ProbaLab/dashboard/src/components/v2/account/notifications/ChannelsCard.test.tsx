import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ChannelsCard } from './ChannelsCard';
import { server } from '@/test/mocks/server';
import { mockNotificationChannels } from '@/test/mocks/fixtures';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// Stub the children that hit the push + telegram hooks — we only want
// to assert composition at this level.
vi.mock('./TelegramConnectFlow', () => ({
  TelegramConnectFlow: ({ telegram }: { telegram: { connected: boolean } }) => (
    <div data-testid="mock-tg">
      tg-connected={telegram.connected ? 'yes' : 'no'}
    </div>
  ),
}));
vi.mock('./PushPermissionButton', () => ({
  PushPermissionButton: ({ push }: { push: { subscribed: boolean } }) => (
    <div data-testid="mock-push">
      push-sub={push.subscribed ? 'yes' : 'no'}
    </div>
  ),
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  server.resetHandlers();
});

describe('ChannelsCard', () => {
  it('renders a skeleton while loading', () => {
    server.use(
      http.get(`${API}/api/user/notifications/channels`, async () => {
        // Keep the promise pending to stay in loading state.
        await new Promise((r) => setTimeout(r, 500));
        return HttpResponse.json(mockNotificationChannels);
      }),
    );
    render(wrap(<ChannelsCard />));
    expect(screen.getByTestId('channels-card-skeleton')).toBeInTheDocument();
  });

  it('renders the three channel rows with the expected composition', async () => {
    render(wrap(<ChannelsCard />));
    // Email stays inline in the card — Telegram + Push are stubbed but
    // still rendered via their testids.
    await screen.findByText(/^Email$/i);
    expect(screen.getByTestId('mock-tg')).toBeInTheDocument();
    expect(screen.getByTestId('mock-push')).toBeInTheDocument();
  });

  it('passes the telegram status to TelegramConnectFlow', async () => {
    render(wrap(<ChannelsCard />));
    const tg = await screen.findByTestId('mock-tg');
    expect(tg.textContent).toMatch(/tg-connected=no/);
  });

  it('passes the push status to PushPermissionButton', async () => {
    render(wrap(<ChannelsCard />));
    const push = await screen.findByTestId('mock-push');
    expect(push.textContent).toMatch(/push-sub=no/);
  });

  it('renders a verified chip for the email address', async () => {
    render(wrap(<ChannelsCard />));
    await screen.findByText(/^Email$/i);
    expect(screen.getByText(/vérifié/i)).toBeInTheDocument();
    expect(screen.getByText(/demo@probalab\.net/i)).toBeInTheDocument();
  });

  it('renders an error state when the backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/notifications/channels`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    render(wrap(<ChannelsCard />));
    await screen.findByRole('alert');
    expect(screen.getByRole('alert').textContent).toMatch(/erreur/i);
  });

  it('exposes a data-testid on the root', async () => {
    render(wrap(<ChannelsCard data-testid="custom-channels" />));
    await screen.findByTestId('custom-channels');
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<ChannelsCard />));
    await screen.findByText(/^Email$/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
