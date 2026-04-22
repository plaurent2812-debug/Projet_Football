import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { AppV2Content } from './AppV2';
import * as v2User from '@/hooks/v2/useV2User';

function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('AppV2', () => {
  it('renders HomeV2 at /', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'visitor', isVisitor: true });
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      /vraie probabilité/i,
    );
  });

  it('renders MatchesV2 at /matchs', async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/matchs']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('renders MatchDetailV2 at /matchs/:fixtureId', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'premium', isVisitor: false });
    renderWithProviders(
      <MemoryRouter initialEntries={['/matchs/fx-1']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByTestId('match-detail-v2')).toHaveAttribute(
      'data-fixture-id',
      'fx-1',
    );
  });

  it('renders PremiumV2 at /premium', () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/premium']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByTestId('premium-v2-page')).toBeInTheDocument();
  });

  it('renders AccountV2 with ProfileTab at /compte (index redirect)', () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({
      role: 'premium',
      isVisitor: false,
    });
    renderWithProviders(
      <MemoryRouter initialEntries={['/compte']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(
      screen.getByRole('heading', { level: 1, name: /mon compte/i }),
    ).toBeInTheDocument();
  });

  it('renders the NotificationsTab at /compte/notifications (not the stub)', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({
      role: 'premium',
      isVisitor: false,
    });
    renderWithProviders(
      <MemoryRouter initialEntries={['/compte/notifications']}>
        <AppV2Content />
      </MemoryRouter>,
    );
    // The full page exposes its own h1 — the stub only rendered a
    // dashed WIP block with no heading.
    expect(
      await screen.findByRole('heading', { level: 1, name: /^notifications$/i }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('tab-notifications-stub')).not.toBeInTheDocument();
  });

  it('renders LoginV2 at /login', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/LoginV2 WIP/i)).toBeInTheDocument();
  });

  it('renders RegisterV2 at /register', () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/RegisterV2 WIP/i)).toBeInTheDocument();
  });
});
