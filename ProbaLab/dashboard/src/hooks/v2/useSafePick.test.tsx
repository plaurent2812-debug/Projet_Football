import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSafePick } from './useSafePick';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useSafePick', () => {
  it('unwraps the backend response into a flat SafePick', async () => {
    const { result } = renderHook(() => useSafePick('2026-04-21'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.fixtureId).toBe('fx-1');
    expect(result.current.data?.odd).toBe(1.85);
    expect(result.current.data?.probability).toBeCloseTo(0.58, 2);
    expect(result.current.data?.betLabel).toBe('PSG gagne vs Lens');
  });

  it('returns null when the backend has no safe pick', async () => {
    const { result } = renderHook(() => useSafePick('2026-04-22-empty'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it('returns null for combo payloads until the card supports combo rendering', async () => {
    server.use(
      http.get(`${API}/api/safe-pick`, () =>
        HttpResponse.json({
          date: '2026-04-23',
          safe_pick: { type: 'combo', legs: [{ fixture_id: 'a' }, { fixture_id: 'b' }] },
          fallback_message: null,
        }),
      ),
    );

    const { result } = renderHook(() => useSafePick('2026-04-23'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });
});
