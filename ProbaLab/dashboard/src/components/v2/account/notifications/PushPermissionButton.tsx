import { useState } from 'react';
import { AlertCircle, Bell, BellOff, CheckCircle2, Monitor } from 'lucide-react';
import { useEnablePush } from '@/hooks/v2/useEnablePush';
import type { NotificationChannelsStatus } from '@/hooks/v2/useNotificationChannels';

export interface PushPermissionButtonProps {
  push: NotificationChannelsStatus['push'];
  'data-testid'?: string;
}

/**
 * Browser push row. Four distinct surface states :
 *  - `!isSupported` → "Non disponible sur ce navigateur"
 *  - `permission === 'default'` → "Activer les notifications push"
 *  - `permission === 'granted'` → "Activé · N appareil(s)" + Désactiver
 *  - `permission === 'denied'` → "Bloqué par le navigateur…"
 *
 * The `useEnablePush` hook wraps the Notification + serviceWorker APIs
 * so we can unit-test this component purely via React Testing Library
 * with a mocked hook implementation.
 */
export function PushPermissionButton({
  push,
  'data-testid': dataTestId = 'push-permission-button',
}: PushPermissionButtonProps) {
  const { permission, isSupported, enable, disable } = useEnablePush();
  const [pending, setPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const onEnable = async () => {
    setErrorMsg(null);
    setPending(true);
    try {
      await enable();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erreur d’activation push';
      setErrorMsg(`Erreur : ${message}`);
    } finally {
      setPending(false);
    }
  };

  const onDisable = async () => {
    setErrorMsg(null);
    setPending(true);
    try {
      await disable();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erreur de désactivation push';
      setErrorMsg(`Erreur : ${message}`);
    } finally {
      setPending(false);
    }
  };

  let status: JSX.Element;
  let action: JSX.Element | null;

  if (!isSupported) {
    status = (
      <span
        className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
        role="status"
      >
        Non disponible sur ce navigateur
      </span>
    );
    action = null;
  } else if (permission === 'denied') {
    status = (
      <span
        className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700 dark:bg-rose-950 dark:text-rose-400"
        role="status"
      >
        <BellOff className="h-3 w-3" aria-hidden="true" />
        Bloqué par le navigateur. Réactiver dans les paramètres.
      </span>
    );
    action = null;
  } else if (permission === 'granted' && push.subscribed) {
    status = (
      <span
        className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
        role="status"
      >
        <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
        Activé · {push.devices} appareil{push.devices > 1 ? 's' : ''}
      </span>
    );
    action = (
      <button
        type="button"
        onClick={onDisable}
        disabled={pending}
        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
      >
        <BellOff className="h-4 w-4" aria-hidden="true" />
        {pending ? 'Désactivation…' : 'Désactiver'}
      </button>
    );
  } else {
    status = (
      <span
        className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
        role="status"
      >
        Inactif
      </span>
    );
    action = (
      <button
        type="button"
        onClick={onEnable}
        disabled={pending}
        className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        {pending ? 'Activation…' : 'Activer les notifications push'}
      </button>
    );
  }

  return (
    <div data-testid={dataTestId} className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <Monitor className="h-5 w-5 text-slate-500" aria-hidden="true" />
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-slate-900 dark:text-white">
              Push (navigateur)
            </span>
            {status}
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Notifications système sur cet appareil.
          </p>
        </div>
        {action}
      </div>

      {errorMsg && (
        <div
          role="alert"
          className="ml-8 flex items-center gap-2 text-sm text-rose-600"
        >
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
          {errorMsg}
        </div>
      )}
    </div>
  );
}

export default PushPermissionButton;
