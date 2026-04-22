import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useMatchesOfDay } from './useMatchesOfDay';

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
});
