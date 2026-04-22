import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useConnectTelegram,
  useDisconnectTelegram,
} from './useConnectTelegram';
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

describe('useConnectTelegram', () => {
  it('POSTs the connect-start endpoint and returns { token, bot_url }', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useConnectTelegram(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const data = result.current.data;
    expect(typeof data?.token).toBe('string');
    expect(data?.bot_url).toMatch(/^https:\/\/t\.me\/probalab_bot\?start=/);
    expect(data?.bot_url.endsWith(data?.token ?? '')).toBe(true);
  });

  it('invalidates the channels cache on success', async () => {
    const { wrapper, client } = createWrapper();
    const spy = vi.spyOn(client, 'invalidateQueries');
    const { result } = renderHook(() => useConnectTelegram(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: expect.arrayContaining(['channels']),
      }),
    );
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.post(
        `${API}/api/user/notifications/telegram/connect-start`,
        () => HttpResponse.json({ error: 'nope' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useConnectTelegram(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useDisconnectTelegram', () => {
  it('DELETEs and returns success', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDisconnectTelegram(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('surfaces errors when disconnect fails', async () => {
    server.use(
      http.delete(`${API}/api/user/notifications/telegram`, () =>
        HttpResponse.json({ error: 'nope' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDisconnectTelegram(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
