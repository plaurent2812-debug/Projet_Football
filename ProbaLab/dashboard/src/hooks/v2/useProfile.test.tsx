import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useProfile,
  useUpdateProfile,
  useChangePassword,
  useDeleteAccount,
} from './useProfile';
import { server } from '@/test/mocks/server';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { wrapper, client };
}

describe('useProfile', () => {
  it('fetches the user profile', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useProfile(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.email).toBe('demo@probalab.net');
    expect(result.current.data?.pseudo).toBe('demo');
  });

  it('surfaces an error when the backend fails', async () => {
    server.use(
      http.get(`${API}/api/user/profile`, () =>
        HttpResponse.json({ error: 'boom' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useProfile(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useUpdateProfile', () => {
  it('PATCHes /api/user/profile and mirrors the server response in cache', async () => {
    const { wrapper, client } = createWrapper();
    const { result } = renderHook(() => useUpdateProfile(), { wrapper });
    result.current.mutate({ pseudo: 'john2' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.pseudo).toBe('john2');
    expect(client.getQueryData(['v2', 'user', 'profile'])).toEqual(
      expect.objectContaining({ pseudo: 'john2' }),
    );
  });

  it('surfaces backend validation errors (400)', async () => {
    server.use(
      http.patch(`${API}/api/user/profile`, () =>
        HttpResponse.json({ error: 'pseudo_taken' }, { status: 400 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateProfile(), { wrapper });
    result.current.mutate({ pseudo: 'clash' });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useChangePassword', () => {
  it('POSTs /api/user/profile/password with current + next', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useChangePassword(), { wrapper });
    result.current.mutate({ current: 'old12345', next: 'new12345' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('rejects wrong current password (400)', async () => {
    server.use(
      http.post(`${API}/api/user/profile/password`, () =>
        HttpResponse.json({ error: 'wrong_current' }, { status: 400 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useChangePassword(), { wrapper });
    result.current.mutate({ current: 'bad', next: 'new12345' });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useDeleteAccount', () => {
  it('DELETEs the profile and returns void on success', async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDeleteAccount(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('surfaces backend errors when deletion fails', async () => {
    server.use(
      http.delete(`${API}/api/user/profile`, () =>
        HttpResponse.json({ error: 'cannot_delete' }, { status: 500 }),
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useDeleteAccount(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
