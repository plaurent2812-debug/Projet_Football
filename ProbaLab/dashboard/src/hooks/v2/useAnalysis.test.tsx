import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useAnalysis } from './useAnalysis';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useAnalysis', () => {
  it('fetches /api/analysis/:fixtureId and exposes paragraphs + generated_at', async () => {
    const { result } = renderHook(() => useAnalysis('fx-1'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.paragraphs.length).toBeGreaterThan(0);
    expect(result.current.data?.generated_at).toMatch(/\d{4}-\d{2}-\d{2}T/);
  });

  it('supports teaser shape for free users (is_teaser=true, 1 paragraph)', async () => {
    const { result } = renderHook(() => useAnalysis('fx-teaser'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.is_teaser).toBe(true);
    expect(result.current.data?.paragraphs).toHaveLength(1);
  });

  it('does not fire when fixtureId is null', () => {
    const { result } = renderHook(() => useAnalysis(null), { wrapper });
    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
  });

  it('surfaces errors for missing fixtureId', async () => {
    const { result } = renderHook(() => useAnalysis('fx-missing'), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });
});
