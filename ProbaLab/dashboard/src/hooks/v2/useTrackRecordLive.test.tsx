import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTrackRecordLive } from './useTrackRecordLive';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useTrackRecordLive', () => {
  it('fetches the live track-record payload', async () => {
    const { result } = renderHook(() => useTrackRecordLive(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
    expect(typeof result.current.data?.clv30d).toBe('number');
    expect(typeof result.current.data?.roi90d).toBe('number');
    expect(typeof result.current.data?.brier30d).toBe('number');
    expect(typeof result.current.data?.safeRate90d).toBe('number');
    expect(Array.isArray(result.current.data?.roiCurve90d)).toBe(true);
    expect(result.current.data?.roiCurve90d?.length).toBeGreaterThan(0);
  });

  it('exposes an error when the backend fails', async () => {
    server.use(
      http.get(`${API}/api/public/track-record/live`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useTrackRecordLive(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
