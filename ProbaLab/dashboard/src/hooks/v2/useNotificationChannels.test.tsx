import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useNotificationChannels,
  NOTIF_CHANNELS_KEY,
} from './useNotificationChannels';
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

describe('useNotificationChannels', () => {
  it('exposes a stable query key', () => {
    expect(NOTIF_CHANNELS_KEY).toEqual([
      'v2',
      'user',
      'notifications',
      'channels',
    ]);
  });

  it('fetches telegram / email / push statuses from the backend', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useNotificationChannels(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const data = result.current.data;
    expect(data?.telegram.connected).toBe(false);
    expect(data?.email.verified).toBe(true);
    expect(data?.email.address).toBe('demo@probalab.net');
    expect(data?.push.subscribed).toBe(false);
    expect(data?.push.devices).toBe(0);
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/notifications/channels`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useNotificationChannels(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
