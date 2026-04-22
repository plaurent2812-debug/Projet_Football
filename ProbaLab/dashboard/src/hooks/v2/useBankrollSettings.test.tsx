import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useBankrollSettings,
  useUpdateBankrollSettings,
} from './useBankrollSettings';
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

describe('useBankrollSettings', () => {
  it('fetches the bankroll settings', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useBankrollSettings(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(typeof result.current.data?.initialStake).toBe('number');
    expect([0.1, 0.25, 0.5]).toContain(result.current.data?.kellyFraction);
    expect(typeof result.current.data?.stakeCapPct).toBe('number');
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/bankroll/settings`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useBankrollSettings(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useUpdateBankrollSettings', () => {
  it('PUTs valid settings and mirrors the server response in cache', async () => {
    const { wrapper, client } = createWrapper();
    const { result } = renderHook(() => useUpdateBankrollSettings(), { wrapper });
    result.current.mutate({
      initialStake: 1000,
      kellyFraction: 0.5,
      stakeCapPct: 5,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.kellyFraction).toBe(0.5);
    expect(
      client.getQueryData(['v2', 'user', 'bankroll', 'settings']),
    ).toEqual(expect.objectContaining({ kellyFraction: 0.5 }));
  });

  it('surfaces backend validation errors (400)', async () => {
    server.use(
      http.put(`${API}/api/user/bankroll/settings`, () =>
        HttpResponse.json({ error: 'invalid_fraction' }, { status: 400 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateBankrollSettings(), { wrapper });
    result.current.mutate({
      initialStake: 1000,
      kellyFraction: 0.25,
      stakeCapPct: 5,
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
