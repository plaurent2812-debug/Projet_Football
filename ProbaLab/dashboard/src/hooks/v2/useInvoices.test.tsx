import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useInvoices } from './useInvoices';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useInvoices', () => {
  it('fetches the invoices list', async () => {
    const { result } = renderHook(() => useInvoices(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
    const first = result.current.data?.[0];
    expect(typeof first?.id).toBe('string');
    expect(typeof first?.amountCents).toBe('number');
    expect(first?.currency).toBe('EUR');
  });

  it('handles empty invoice list', async () => {
    server.use(
      http.get(`${API}/api/user/invoices`, () => HttpResponse.json([])),
    );
    const { result } = renderHook(() => useInvoices(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });

  it('surfaces an error when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/invoices`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useInvoices(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
