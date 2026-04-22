import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSafePick } from './useSafePick';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useSafePick', () => {
  it('fetches the safe pick for a given date', async () => {
    const { result } = renderHook(() => useSafePick('2026-04-21'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.betLabel).toBe('PSG gagne vs Lens');
    expect(result.current.data?.odd).toBe(1.85);
  });
});
