import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useBankrollBets,
  useAddBet,
  useUpdateBet,
  useDeleteBet,
} from './useBankrollBets';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { wrapper, client };
}

describe('useBankrollBets', () => {
  it('fetches the bets list with default filter=all', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useBankrollBets(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
    const first = result.current.data?.[0];
    expect(typeof first?.id).toBe('string');
    expect(typeof first?.fixture_id).toBe('string');
    expect(typeof first?.match_title).toBe('string');
    expect(typeof first?.odds).toBe('number');
    expect(typeof first?.stake).toBe('number');
  });

  it('filters bets by status', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useBankrollBets('won'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.every((b) => b.result === 'WIN')).toBe(true);
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/bets`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useBankrollBets(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useAddBet', () => {
  it('POSTs a bet and invalidates bankroll + bets caches on success', async () => {
    const { wrapper, client } = createWrapper();
    const { result } = renderHook(() => useAddBet(), { wrapper });
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');
    result.current.mutate({
      fixture_id: 'fx-99',
      match_title: 'PSG - OM',
      market: '1X2',
      selection: 'Home',
      odds: 1.85,
      stake: 25,
      placed_at: '2026-04-22T10:00:00Z',
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: expect.arrayContaining(['bankroll']) }),
    );
  });

  it('surfaces backend validation errors (400)', async () => {
    server.use(
      http.post(`${API}/api/user/bets`, () =>
        HttpResponse.json({ error: 'invalid_stake' }, { status: 400 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAddBet(), { wrapper });
    result.current.mutate({
      fixture_id: 'fx-99',
      match_title: 'PSG - OM',
      market: '1X2',
      selection: 'Home',
      odds: 1.85,
      stake: 0,
      placed_at: '2026-04-22T10:00:00Z',
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useUpdateBet', () => {
  it('PATCHes a bet with result + resolved_at', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateBet('bet-001'), { wrapper });
    result.current.mutate({
      result: 'WIN',
      resolved_at: '2026-04-22T20:00:00Z',
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.patch(`${API}/api/user/bets/:id`, () =>
        HttpResponse.json({ error: 'not_found' }, { status: 404 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateBet('missing'), { wrapper });
    result.current.mutate({ result: 'WIN' });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useDeleteBet', () => {
  it('DELETEs a bet by id', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDeleteBet('bet-001'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.delete(`${API}/api/user/bets/:id`, () =>
        HttpResponse.json({ error: 'cannot_delete' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDeleteBet('bet-001'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
