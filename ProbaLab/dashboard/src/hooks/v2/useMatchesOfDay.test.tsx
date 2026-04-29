import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import type { ReactNode } from 'react';
import { useMatchesOfDay } from './useMatchesOfDay';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useMatchesOfDay', () => {
  it('fetches all matches for a date', async () => {
    const { result } = renderHook(() => useMatchesOfDay({ date: '2026-04-21' }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.matches).toHaveLength(3);
    expect(result.current.data?.counts.total).toBe(3);
  });

  it('applies valueOnly filter to query params', async () => {
    const { result } = renderHook(
      () => useMatchesOfDay({ date: '2026-04-21', valueOnly: true }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.matches.every((m) => m.signals.includes('value'))).toBe(true);
  });

  it('applies sports filter', async () => {
    const { result } = renderHook(
      () => useMatchesOfDay({ date: '2026-04-21', sports: ['football'] }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.matches.every((m) => m.sport === 'football')).toBe(true);
  });

  it('keeps NHL probabilities and score metadata from the backend listing', async () => {
    server.use(
      http.get(`${API}/api/matches`, () =>
        HttpResponse.json({
          date: '2026-04-30',
          total: 1,
          groups: [
            {
              league_id: 'NHL',
              league_name: 'NHL',
              matches: [
                {
                  fixture_id: 'nhl-1',
                  sport: 'nhl',
                  league_id: 'NHL',
                  league_name: 'NHL',
                  home_team: 'Dallas Stars',
                  away_team: 'Minnesota Wild',
                  status: 'LIVE',
                  home_goals: 2,
                  away_goals: 1,
                  kickoff_utc: '2026-04-30T02:00:00Z',
                  prediction: {
                    proba_home: 57.5,
                    proba_draw: null,
                    proba_away: 42.5,
                    confidence_score: 7,
                  },
                },
              ],
            },
          ],
        }),
      ),
    );

    const { result } = renderHook(() => useMatchesOfDay({ date: '2026-04-30' }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.matches[0]).toMatchObject({
      sport: 'nhl',
      prob1x2: { home: 0.575, draw: null, away: 0.425 },
      score: { home: 2, away: 1 },
      status: 'LIVE',
    });
  });
});
