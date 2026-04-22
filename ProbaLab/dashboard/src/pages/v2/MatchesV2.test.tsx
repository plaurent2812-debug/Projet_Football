import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import type { ReactElement } from 'react';
import MatchesV2 from './MatchesV2';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    value: width,
    configurable: true,
    writable: true,
  });
  window.dispatchEvent(new Event('resize'));
}

function renderAt(ui: ReactElement, initialEntries: string[] = ['/matchs']) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/matchs" element={ui} />
          <Route path="/matchs/:fixtureId" element={<div data-testid="match-detail-route" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('MatchesV2', () => {
  beforeEach(() => {
    setViewportWidth(1280);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders root wrapper with data-testid', async () => {
    renderAt(<MatchesV2 />);
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('loads matches for the current day by default (desktop)', async () => {
    renderAt(<MatchesV2 />);
    await waitFor(() => {
      expect(screen.getByTestId('matches-table-desktop')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('match-row-desktop').length).toBeGreaterThan(0);
  });

  it('renders mobile layout under md breakpoint', async () => {
    setViewportWidth(375);
    renderAt(<MatchesV2 />);
    await waitFor(() => {
      expect(screen.getByTestId('matches-list-mobile')).toBeInTheDocument();
    });
  });

  it('reads initial date from ?date= query param', async () => {
    renderAt(<MatchesV2 />, ['/matchs?date=2026-04-22']);
    await waitFor(() => {
      expect(screen.getByTestId('matches-v2-page')).toHaveAttribute('data-date', '2026-04-22');
    });
  });

  it('updates URL when a date is selected in DateScroller', async () => {
    const user = userEvent.setup();
    renderAt(<MatchesV2 />);
    const scroller = await screen.findByTestId('date-scroller');
    const buttons = within(scroller).getAllByRole('button');
    const dayButton = buttons.find((b) => b.getAttribute('data-iso') && b.getAttribute('aria-pressed') === 'false');
    expect(dayButton).toBeDefined();
    const iso = dayButton!.getAttribute('data-iso');
    await user.click(dayButton!);
    await waitFor(() => {
      expect(screen.getByTestId('matches-v2-page')).toHaveAttribute('data-date', iso);
    });
  });

  it('toggles sport via SportChips and reflects in URL', async () => {
    const user = userEvent.setup();
    renderAt(<MatchesV2 />);
    const chips = await screen.findByTestId('sport-chips');
    const football = within(chips).getByRole('button', { name: /football/i });
    await user.click(football);
    await waitFor(() => {
      expect(screen.getByTestId('matches-v2-page')).toHaveAttribute('data-sport', 'football');
    });
  });

  it('filters via FilterSidebar on desktop (league checkbox)', async () => {
    const user = userEvent.setup();
    renderAt(<MatchesV2 />);
    const sidebar = await screen.findByTestId('filter-sidebar');
    const l1 = within(sidebar).getByRole('checkbox', { name: /ligue 1/i });
    await user.click(l1);
    await waitFor(() => {
      expect(screen.getByTestId('matches-v2-page')).toHaveAttribute('data-leagues', 'L1');
    });
  });

  it('shows empty state when no matches', async () => {
    server.use(
      http.get(`${API}/api/matches`, () =>
        HttpResponse.json({
          date: '2026-04-21',
          matches: [],
          counts: { total: 0, bySport: { football: 0, nhl: 0 }, byLeague: {} },
        }),
      ),
    );
    renderAt(<MatchesV2 />);
    expect(await screen.findByTestId('matches-empty')).toBeInTheDocument();
  });

  it('navigates to match detail when clicking a desktop row detail button', async () => {
    const user = userEvent.setup();
    renderAt(<MatchesV2 />);
    await waitFor(() => {
      expect(screen.getByTestId('matches-table-desktop')).toBeInTheDocument();
    });
    const links = screen.getAllByRole('link', { name: /voir le détail/i });
    await user.click(links[0]);
    await waitFor(() => {
      expect(screen.getByTestId('match-detail-route')).toBeInTheDocument();
    });
  });

  it('shows error state on fetch error', async () => {
    server.use(
      http.get(`${API}/api/matches`, () => HttpResponse.json({ error: 'boom' }, { status: 500 })),
    );
    renderAt(<MatchesV2 />);
    expect(await screen.findByTestId('matches-error')).toBeInTheDocument();
  });
});
