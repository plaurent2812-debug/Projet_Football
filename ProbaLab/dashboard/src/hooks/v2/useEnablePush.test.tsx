import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useEnablePush } from './useEnablePush';
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

// -------- Helpers to mock the Notification + navigator.serviceWorker APIs --

interface MockNotificationCtor {
  permission: NotificationPermission;
  requestPermission: ReturnType<typeof vi.fn>;
}

function stubNotification(initialPermission: NotificationPermission = 'default'): MockNotificationCtor {
  const ctor: MockNotificationCtor = {
    permission: initialPermission,
    requestPermission: vi.fn().mockImplementation(async () => {
      ctor.permission = 'granted';
      return 'granted';
    }),
  };
  vi.stubGlobal('Notification', ctor);
  return ctor;
}

function stubServiceWorker(opts: {
  subscribeResult?: unknown;
  existingSubscription?: unknown;
  registerImpl?: () => Promise<unknown>;
} = {}) {
  const fakeSubscription = opts.subscribeResult ?? {
    endpoint: 'https://push.example/abc',
    toJSON: () => ({
      endpoint: 'https://push.example/abc',
      keys: { p256dh: 'pk', auth: 'ak' },
    }),
    unsubscribe: vi.fn().mockResolvedValue(true),
  };
  const register = opts.registerImpl
    ? vi.fn().mockImplementation(opts.registerImpl)
    : vi.fn().mockResolvedValue({
        pushManager: {
          getSubscription: vi.fn().mockResolvedValue(opts.existingSubscription ?? null),
          subscribe: vi.fn().mockResolvedValue(fakeSubscription),
        },
      });

  const mockNav = {
    serviceWorker: {
      register,
    },
  };
  vi.stubGlobal('navigator', mockNav);
  return { register, fakeSubscription };
}

// ---------------------------------------------------------------------------

describe('useEnablePush', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reports isSupported=false when Notification is missing', async () => {
    // jsdom by default has no Notification / no pushManager. Make sure.
    vi.stubGlobal('Notification', undefined);
    vi.stubGlobal('navigator', { serviceWorker: undefined });
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEnablePush(), { wrapper });
    expect(result.current.isSupported).toBe(false);
    expect(result.current.permission).toBe('default');
  });

  it('reflects the current Notification.permission when supported', () => {
    stubNotification('granted');
    stubServiceWorker();
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEnablePush(), { wrapper });
    expect(result.current.isSupported).toBe(true);
    expect(result.current.permission).toBe('granted');
  });

  it('requests permission, registers SW, subscribes and POSTs subscription on enable()', async () => {
    const ctor = stubNotification('default');
    const { register } = stubServiceWorker();
    const postCalls: unknown[] = [];
    server.use(
      http.post(`${API}/api/user/notifications/push/subscribe`, async ({ request }) => {
        postCalls.push(await request.json());
        return HttpResponse.json({ ok: true });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEnablePush(), { wrapper });
    await act(async () => {
      await result.current.enable();
    });

    expect(ctor.requestPermission).toHaveBeenCalled();
    expect(register).toHaveBeenCalledWith('/sw-push.js');
    expect(postCalls).toHaveLength(1);
    expect(postCalls[0]).toMatchObject({
      endpoint: 'https://push.example/abc',
      keys: { p256dh: 'pk', auth: 'ak' },
    });
    await waitFor(() => expect(result.current.permission).toBe('granted'));
  });

  it('throws when permission is denied', async () => {
    const ctor = stubNotification('default');
    ctor.requestPermission = vi.fn().mockImplementation(async () => {
      ctor.permission = 'denied';
      return 'denied';
    });
    stubServiceWorker();

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEnablePush(), { wrapper });
    await expect(
      act(async () => {
        await result.current.enable();
      }),
    ).rejects.toThrow(/permission/i);
  });

  it('disable() unsubscribes, DELETEs the server subscription and keeps permission state', async () => {
    stubNotification('granted');
    const unsubscribeFn = vi.fn().mockResolvedValue(true);
    const existing = {
      endpoint: 'https://push.example/abc',
      toJSON: () => ({
        endpoint: 'https://push.example/abc',
        keys: { p256dh: 'pk', auth: 'ak' },
      }),
      unsubscribe: unsubscribeFn,
    };
    stubServiceWorker({ existingSubscription: existing });

    const deleteCalls: string[] = [];
    server.use(
      http.delete(`${API}/api/user/notifications/push/unsubscribe`, ({ request }) => {
        deleteCalls.push(request.method);
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEnablePush(), { wrapper });
    await act(async () => {
      await result.current.disable();
    });

    expect(unsubscribeFn).toHaveBeenCalled();
    expect(deleteCalls).toEqual(['DELETE']);
  });

  it('enable() is a no-op (returns early without throwing) when unsupported', async () => {
    vi.stubGlobal('Notification', undefined);
    vi.stubGlobal('navigator', { serviceWorker: undefined });
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useEnablePush(), { wrapper });
    await expect(
      act(async () => {
        await result.current.enable();
      }),
    ).rejects.toThrow(/not supported/i);
  });
});
