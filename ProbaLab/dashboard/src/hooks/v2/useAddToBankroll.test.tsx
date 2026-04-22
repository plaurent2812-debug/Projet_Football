import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useAddToBankroll } from './useAddToBankroll';
import type { AddBetRequest } from '@/types/v2/match-detail';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { wrapper, client };
}

describe('useAddToBankroll', () => {
  it('POSTs /api/user/bets with the payload and returns the created bet', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAddToBankroll(), { wrapper });
    const input: AddBetRequest = {
      fixture_id: 'fx-1',
      market_key: '1x2.home',
      odds: 1.85,
      stake: 10,
    };
    result.current.mutate(input);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.fixture_id).toBe('fx-1');
    expect(result.current.data?.market_key).toBe('1x2.home');
    expect(result.current.data?.odds).toBeCloseTo(1.85);
    expect(result.current.data?.stake).toBeCloseTo(10);
    expect(typeof result.current.data?.id).toBe('string');
    expect(result.current.data?.placed_at).toMatch(/\d{4}-\d{2}-\d{2}T/);
  });

  it('invalidates the bankroll query on success', async () => {
    const { wrapper, client } = createWrapper();
    // Prime the bankroll query so invalidation has a target.
    await client.fetchQuery({
      queryKey: ['bankroll'],
      queryFn: async () => ({ balance: 1240 }),
    });
    const before = client.getQueryState(['bankroll']);
    const { result } = renderHook(() => useAddToBankroll(), { wrapper });
    result.current.mutate({
      fixture_id: 'fx-1',
      market_key: '1x2.home',
      odds: 1.85,
      stake: 10,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const after = client.getQueryState(['bankroll']);
    expect(after?.isInvalidated).toBe(true);
    // Sanity: we did not just read the pristine state back.
    expect(before?.isInvalidated).toBe(false);
  });

  it('surfaces backend errors (validation 400) without retrying', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAddToBankroll(), { wrapper });
    result.current.mutate({
      fixture_id: 'fx-1',
      market_key: '1x2.home',
      odds: 1.85,
      stake: -5, // invalid stake triggers 400
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });
});
