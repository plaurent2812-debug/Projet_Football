import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSubscription } from './useSubscription';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useSubscription', () => {
  it('fetches the current subscription with plan + renewsAt', async () => {
    const { result } = renderHook(() => useSubscription(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.plan).toBe('PREMIUM');
    expect(result.current.data?.status).toBe('active');
    expect(typeof result.current.data?.renewsAt).toBe('string');
    expect(result.current.data?.cancelAtPeriodEnd).toBe(false);
  });

  it('surfaces an error when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/subscription`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useSubscription(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
