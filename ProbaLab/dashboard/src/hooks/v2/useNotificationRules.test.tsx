import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useNotificationRules,
  useCreateRule,
  useUpdateRule,
  useDeleteRule,
  useToggleRule,
  NOTIF_RULES_KEY,
} from './useNotificationRules';
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

describe('useNotificationRules', () => {
  it('exposes a stable query key', () => {
    expect(NOTIF_RULES_KEY).toEqual(['v2', 'user', 'notifications', 'rules']);
  });

  it('fetches the rules list', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useNotificationRules(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThanOrEqual(3);
    const first = result.current.data?.[0];
    expect(typeof first?.id).toBe('string');
    expect(typeof first?.name).toBe('string');
    expect(Array.isArray(first?.conditions)).toBe(true);
    expect(Array.isArray(first?.channels)).toBe(true);
  });

  it('surfaces errors when backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/notifications/rules`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useNotificationRules(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useCreateRule', () => {
  it('POSTs a new rule and invalidates the list', async () => {
    const { wrapper, client } = createWrapper();
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');
    const { result } = renderHook(() => useCreateRule(), { wrapper });
    result.current.mutate({
      name: 'Top edge',
      conditions: [{ type: 'edge_min', value: 8 }],
      logic: 'AND',
      channels: ['email', 'telegram'],
      action: { notify: true, pauseSuggestion: false },
      enabled: true,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBeDefined();
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: NOTIF_RULES_KEY }),
    );
  });

  it('surfaces validation errors (400)', async () => {
    server.use(
      http.post(`${API}/api/user/notifications/rules`, () =>
        HttpResponse.json({ error: 'invalid_rule' }, { status: 400 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useCreateRule(), { wrapper });
    result.current.mutate({
      name: '',
      conditions: [{ type: 'edge_min', value: 8 }],
      logic: 'AND',
      channels: ['email'],
      action: { notify: true, pauseSuggestion: false },
      enabled: true,
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useUpdateRule', () => {
  it('PUTs a rule by id', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateRule('rule-001'), { wrapper });
    result.current.mutate({
      id: 'rule-001',
      name: 'Updated',
      conditions: [{ type: 'edge_min', value: 10 }],
      logic: 'AND',
      channels: ['telegram'],
      action: { notify: true, pauseSuggestion: false },
      enabled: true,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.name).toBe('Updated');
  });
});

describe('useDeleteRule', () => {
  it('DELETEs a rule by id', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDeleteRule('rule-001'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('surfaces errors when delete fails', async () => {
    server.use(
      http.delete(`${API}/api/user/notifications/rules/:id`, () =>
        HttpResponse.json({ error: 'nope' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDeleteRule('rule-001'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useToggleRule', () => {
  it('PATCHes the enabled flag', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useToggleRule('rule-001'), { wrapper });
    result.current.mutate(false);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.enabled).toBe(false);
  });
});
