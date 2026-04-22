import { useCallback, useEffect, useState } from 'react';
import { apiDelete, apiPost } from '@/lib/v2/apiClient';

/**
 * VAPID public key (base64url) for the push service. Kept optional : if
 * missing, `subscribe()` still works on browsers that allow "no key" push,
 * but most browsers require it. The fallback value is only meant for
 * local/dev — production must inject `VITE_VAPID_PUBLIC_KEY`.
 */
const VAPID_PUBLIC_KEY = (
  import.meta.env.VITE_VAPID_PUBLIC_KEY as string | undefined
) ?? '';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

/**
 * Shape returned by `PushSubscription.toJSON()` — only the fields the
 * backend cares about.
 */
export interface PushSubscriptionPayload {
  endpoint: string;
  keys?: {
    p256dh?: string;
    auth?: string;
  };
  expirationTime?: number | null;
}

export interface UseEnablePushResult {
  /** 'default' | 'granted' | 'denied' (falls back to 'default' on unsupported). */
  permission: NotificationPermission;
  /** Whether `Notification` + `navigator.serviceWorker` are available. */
  isSupported: boolean;
  /** Ask permission, register SW, subscribe, POST to backend. Throws on denial. */
  enable: () => Promise<void>;
  /** Unsubscribe locally + DELETE the server-side record. */
  disable: () => Promise<void>;
}

function detectSupport(): boolean {
  if (typeof window === 'undefined') return false;
  if (typeof Notification === 'undefined') return false;
  if (typeof navigator === 'undefined') return false;
  return 'serviceWorker' in navigator;
}

/**
 * Hook orchestrating the browser push subscription flow.
 *
 * Rationale:
 *  - `useMutation` is overkill here — we expose a thin imperative API so
 *    callers can `await enable()` / `await disable()` directly from a
 *    button handler, and keep the local `permission` snapshot reactive.
 *  - jsdom doesn't ship `Notification` or `navigator.serviceWorker`, so
 *    we return `isSupported: false` and make `enable()` throw early.
 */
export function useEnablePush(): UseEnablePushResult {
  const isSupported = detectSupport();
  const [permission, setPermission] = useState<NotificationPermission>(
    isSupported ? Notification.permission : 'default',
  );

  // Keep local state in sync with the global on re-renders (e.g. after
  // the browser surface flipped the permission from another tab).
  useEffect(() => {
    if (!isSupported) return;
    setPermission(Notification.permission);
  }, [isSupported]);

  const enable = useCallback(async () => {
    if (!isSupported) {
      throw new Error('Push notifications not supported in this environment');
    }

    const result = await Notification.requestPermission();
    setPermission(result);
    if (result !== 'granted') {
      throw new Error(`Permission ${result}`);
    }

    const registration = await navigator.serviceWorker.register('/sw-push.js');
    const pushManager = (registration as unknown as { pushManager: PushManager }).pushManager;

    const existing = typeof pushManager.getSubscription === 'function'
      ? await pushManager.getSubscription()
      : null;

    const subscription = existing ?? (await pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: VAPID_PUBLIC_KEY
        ? urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
        : undefined,
    }));

    const payload: PushSubscriptionPayload =
      typeof (subscription as unknown as { toJSON?: () => PushSubscriptionPayload }).toJSON === 'function'
        ? ((subscription as unknown as { toJSON: () => PushSubscriptionPayload }).toJSON())
        : {
            endpoint: (subscription as unknown as { endpoint: string }).endpoint,
          };

    await apiPost<PushSubscriptionPayload, { ok: boolean }>(
      '/api/user/notifications/push/subscribe',
      payload,
    );
  }, [isSupported]);

  const disable = useCallback(async () => {
    if (!isSupported) return;
    const registration = await navigator.serviceWorker.register('/sw-push.js');
    const pushManager = (registration as unknown as { pushManager: PushManager }).pushManager;
    const subscription = typeof pushManager.getSubscription === 'function'
      ? await pushManager.getSubscription()
      : null;

    if (subscription && typeof (subscription as unknown as { unsubscribe?: () => Promise<boolean> }).unsubscribe === 'function') {
      await (subscription as unknown as { unsubscribe: () => Promise<boolean> }).unsubscribe();
    }

    await apiDelete('/api/user/notifications/push/unsubscribe');
  }, [isSupported]);

  return { permission, isSupported, enable, disable };
}
