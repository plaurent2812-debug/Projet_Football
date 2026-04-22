import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useROIByMarket } from './useROIByMarket';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useROIByMarket', () => {
  it('fetches ROI per market with default window=30', async () => {
    const { result } = renderHook(() => useROIByMarket(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
    const first = result.current.data?.[0];
    expect(typeof first?.market).toBe('string');
    expect(typeof first?.roi_pct).toBe('number');
    expect(typeof first?.n).toBe('number');
  });

  it('honours the window parameter', async () => {
    let seenWindow: string | null = null;
    server.use(
      http.get(`${API}/api/user/bankroll/roi-by-market`, ({ request }) => {
        const url = new URL(request.url);
        seenWindow = url.searchParams.get('window');
        return HttpResponse.json([
          { market: '1X2', roi_pct: 5, n: 10, wins: 5, losses: 5, voids: 0 },
        ]);
      }),
    );
    const { result } = renderHook(() => useROIByMarket(90), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(seenWindow).toBe('90');
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/bankroll/roi-by-market`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useROIByMarket(30), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
