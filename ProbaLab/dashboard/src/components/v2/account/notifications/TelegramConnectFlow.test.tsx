import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { TelegramConnectFlow } from './TelegramConnectFlow';
import type { NotificationChannelsStatus } from '@/hooks/v2/useNotificationChannels';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

const disconnected: NotificationChannelsStatus['telegram'] = { connected: false };
const connected: NotificationChannelsStatus['telegram'] = {
  connected: true,
  username: 'johndoe',
};

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('TelegramConnectFlow', () => {
  it('shows the "Connecter Telegram" CTA when disconnected', () => {
    render(wrap(<TelegramConnectFlow telegram={disconnected} />));
    expect(
      screen.getByRole('button', { name: /connecter telegram/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/non connecté/i)).toBeInTheDocument();
  });

  it('opens the bot_url in a new tab and surfaces the waiting hint on click', async () => {
    const user = userEvent.setup();
    const openSpy = vi.fn().mockReturnValue(null);
    vi.stubGlobal('open', openSpy);
    server.use(
      http.post(
        `${API}/api/user/notifications/telegram/connect-start`,
        () =>
          HttpResponse.json({
            token: 'TOKEN123',
            bot_url: 'https://t.me/probalab_bot?start=TOKEN123',
          }),
      ),
    );

    render(wrap(<TelegramConnectFlow telegram={disconnected} />));
    await user.click(
      screen.getByRole('button', { name: /connecter telegram/i }),
    );

    await screen.findByText(/en attente/i);
    expect(openSpy).toHaveBeenCalledWith(
      'https://t.me/probalab_bot?start=TOKEN123',
      '_blank',
      'noopener,noreferrer',
    );
  });

  it('shows connected state with @username + a Déconnecter button', async () => {
    render(wrap(<TelegramConnectFlow telegram={connected} />));
    expect(screen.getByText(/@johndoe/i)).toBeInTheDocument();
    expect(screen.getByText(/connecté/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /déconnecter/i }),
    ).toBeInTheDocument();
  });

  it('calls DELETE when the user clicks Déconnecter', async () => {
    const user = userEvent.setup();
    let deleted = false;
    server.use(
      http.delete(`${API}/api/user/notifications/telegram`, () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    render(wrap(<TelegramConnectFlow telegram={connected} />));
    await user.click(screen.getByRole('button', { name: /déconnecter/i }));
    await vi.waitFor(() => expect(deleted).toBe(true));
  });

  it('surfaces a friendly message on API error', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        `${API}/api/user/notifications/telegram/connect-start`,
        () => HttpResponse.json({ error: 'nope' }, { status: 500 }),
      ),
    );
    render(wrap(<TelegramConnectFlow telegram={disconnected} />));
    await user.click(
      screen.getByRole('button', { name: /connecter telegram/i }),
    );
    await screen.findByRole('alert');
    expect(screen.getByRole('alert').textContent).toMatch(/erreur/i);
  });

  it('exposes a data-testid on the root', () => {
    render(
      wrap(
        <TelegramConnectFlow
          telegram={disconnected}
          data-testid="custom-tg"
        />,
      ),
    );
    expect(screen.getByTestId('custom-tg')).toBeInTheDocument();
  });

  it('has no axe violations in disconnected state', async () => {
    const { container } = render(
      wrap(<TelegramConnectFlow telegram={disconnected} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no axe violations in connected state', async () => {
    const { container } = render(
      wrap(<TelegramConnectFlow telegram={connected} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
