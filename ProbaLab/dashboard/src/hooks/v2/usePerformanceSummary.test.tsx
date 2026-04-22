import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { usePerformanceSummary } from './usePerformanceSummary';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('usePerformanceSummary', () => {
  it('fetches KPIs for the stat strip with default window 30', async () => {
    const { result } = renderHook(() => usePerformanceSummary(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.roi30d.value).toBeCloseTo(12.4);
    expect(result.current.data?.bankroll.currency).toBe('EUR');
  });

  it('honors a custom window in the queryKey', async () => {
    const { result } = renderHook(() => usePerformanceSummary(7), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.accuracy.value).toBeCloseTo(54.2);
  });
});
