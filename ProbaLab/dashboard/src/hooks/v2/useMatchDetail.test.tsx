import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useMatchDetail } from './useMatchDetail';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useMatchDetail', () => {
  it('fetches /api/predictions/:fixtureId and exposes header + probs', async () => {
    const { result } = renderHook(() => useMatchDetail('fx-1'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.header.fixture_id).toBe('fx-1');
    expect(result.current.data?.header.league_name).toBe('Ligue 1');
    expect(result.current.data?.probs_1x2.home).toBeCloseTo(0.58);
  });

  it('exposes stats, h2h, compositions, all_markets, recommendation, value_bets', async () => {
    const { result } = renderHook(() => useMatchDetail('fx-1'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const data = result.current.data;
    expect(Array.isArray(data?.stats)).toBe(true);
    expect(data?.stats.length).toBeGreaterThan(0);
    expect(data?.h2h.home_wins).toBeGreaterThanOrEqual(0);
    expect(data?.compositions.status).toMatch(/confirmed|probable|unavailable/);
    expect(Array.isArray(data?.all_markets)).toBe(true);
    expect(Array.isArray(data?.value_bets)).toBe(true);
    expect(data?.recommendation).not.toBeUndefined();
  });

  it('does not fire when fixtureId is null', () => {
    const { result } = renderHook(() => useMatchDetail(null), { wrapper });
    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
  });

  it('surfaces errors when the request fails', async () => {
    const { result } = renderHook(() => useMatchDetail('fx-missing'), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });
});
