import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import type { ReactElement } from 'react';
import MatchDetailV2 from './MatchDetailV2';
import * as v2User from '@/hooks/v2/useV2User';
import type { V2User } from '@/hooks/v2/useV2User';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function mockUser(u: V2User) {
  vi.spyOn(v2User, 'useV2User').mockReturnValue(u);
}

function renderAt(
  ui: ReactElement,
  initialEntries: string[] = ['/matchs/fx-1'],
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/matchs" element={<div data-testid="matches-route" />} />
          <Route path="/matchs/:fixtureId" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('MatchDetailV2', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('loading', () => {
    it('renders skeleton while data is loading', async () => {
      mockUser({ role: 'premium', isVisitor: false });
      // Delay response so the loading state is observable.
      server.use(
        http.get(`${API}/api/predictions/:fixtureId`, async () => {
          await new Promise((r) => setTimeout(r, 50));
          return HttpResponse.json({ error: 'late' }, { status: 500 });
        }),
      );
      renderAt(<MatchDetailV2 />);
      expect(
        await screen.findByTestId('match-detail-loading'),
      ).toBeInTheDocument();
    });
  });

  describe('error', () => {
    it('shows error state and "Retour aux matchs" link', async () => {
      mockUser({ role: 'premium', isVisitor: false });
      server.use(
        http.get(`${API}/api/predictions/:fixtureId`, () =>
          HttpResponse.json({ error: 'boom' }, { status: 500 }),
        ),
      );
      renderAt(<MatchDetailV2 />);
      expect(await screen.findByTestId('match-detail-error')).toBeInTheDocument();
      const backLink = screen.getByRole('link', { name: /retour/i });
      expect(backLink).toHaveAttribute('href', '/matchs');
    });
  });

  describe('premium', () => {
    beforeEach(() => {
      mockUser({ role: 'premium', isVisitor: false });
    });

    it('renders root wrapper with data-testid and fixture id', async () => {
      renderAt(<MatchDetailV2 />);
      const wrapper = await screen.findByTestId('match-detail-v2');
      expect(wrapper).toBeInTheDocument();
      expect(wrapper).toHaveAttribute('data-fixture-id', 'fx-1');
    });

    it('renders hero + reco + prob bar with full data', async () => {
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      expect(screen.getAllByText(/Paris Saint-Germain/).length).toBeGreaterThan(0);
      expect(screen.getByTestId('reco-card')).toBeInTheDocument();
      expect(screen.getByTestId('prob-bar')).toBeInTheDocument();
    });

    it('propagates the desktop right column with sticky layout', async () => {
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      const right = screen.getByTestId('match-detail-right-col');
      expect(right.className).toMatch(/sticky/);
      expect(right.className).toMatch(/top-5/);
    });

    it('does not render any LockOverlay', async () => {
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
    });

    it('renders breadcrumb with link back to /matchs', async () => {
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      const nav = screen.getByTestId('match-detail-breadcrumb');
      const link = within(nav).getByRole('link', { name: /matchs/i });
      expect(link).toHaveAttribute('href', '/matchs');
    });

    it('navigates back to /matchs when breadcrumb is clicked', async () => {
      const user = userEvent.setup();
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      const nav = screen.getByTestId('match-detail-breadcrumb');
      const link = within(nav).getByRole('link', { name: /matchs/i });
      await user.click(link);
      await waitFor(() => {
        expect(screen.getByTestId('matches-route')).toBeInTheDocument();
      });
    });
  });

  describe('free gating', () => {
    beforeEach(() => {
      mockUser({ role: 'free', isVisitor: false });
    });

    it('renders the page and shows at least one LockOverlay with "premium"', async () => {
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      const locks = await screen.findAllByTestId('lock-overlay');
      expect(locks.length).toBeGreaterThan(0);
      const texts = locks.map((l) => l.textContent ?? '').join(' ');
      expect(texts).toMatch(/premium/i);
    });
  });

  describe('visitor gating', () => {
    beforeEach(() => {
      mockUser({ role: 'visitor', isVisitor: true });
    });

    it('renders LockOverlay with "compte" CTA for visitors', async () => {
      renderAt(<MatchDetailV2 />);
      await screen.findByTestId('match-detail-v2');
      const locks = await screen.findAllByTestId('lock-overlay');
      expect(locks.length).toBeGreaterThan(0);
      const texts = locks.map((l) => l.textContent ?? '').join(' ');
      expect(texts).toMatch(/compte/i);
    });
  });
});
