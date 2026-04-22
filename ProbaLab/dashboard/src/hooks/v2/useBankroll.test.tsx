import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useBankroll } from './useBankroll';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useBankroll', () => {
  it('fetches the bankroll summary', async () => {
    const { result } = renderHook(() => useBankroll(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.current_balance).toBe(1284);
    expect(result.current.data?.initial_balance).toBe(1000);
    expect(result.current.data?.roi_30d).toBe(12.4);
    expect(result.current.data?.roi_90d).toBe(9.8);
    expect(result.current.data?.win_rate).toBe(58.7);
    expect(result.current.data?.drawdown_max_pct).toBe(-4.2);
    expect(result.current.data?.kelly_fraction_active).toBe(0.25);
    expect(result.current.data?.total_bets).toBeGreaterThan(0);
  });

  it('surfaces errors when the backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/bankroll`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useBankroll(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
