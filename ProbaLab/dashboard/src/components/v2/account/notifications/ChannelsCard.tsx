import { AlertCircle, CheckCircle2, Mail } from 'lucide-react';
import { useNotificationChannels } from '@/hooks/v2/useNotificationChannels';
import { TelegramConnectFlow } from './TelegramConnectFlow';
import { PushPermissionButton } from './PushPermissionButton';

export interface ChannelsCardProps {
  'data-testid'?: string;
}

/**
 * "Canaux de notification" card for the Account settings page.
 *
 * Composes three channel rows — Telegram, Email and Push — each with
 * its own status chip + action. The card itself is responsible for
 * fetching the aggregated channels status (via `useNotificationChannels`)
 * and dispatching the slice each child needs.
 *
 * Loading → neutral skeleton. Error → `role="alert"` red banner.
 */
export function ChannelsCard({
  'data-testid': dataTestId = 'channels-card',
}: ChannelsCardProps = {}) {
  const { data, isLoading, isError, error } = useNotificationChannels();

  if (isLoading || (!data && !isError)) {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div
          data-testid="channels-card-skeleton"
          aria-busy="true"
          aria-label="Chargement des canaux"
          className="space-y-3"
        >
          <div className="h-5 w-40 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
          <div className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
          <div className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
          <div className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
        </div>
      </section>
    );
  }

  if (isError || !data) {
    const message =
      error instanceof Error ? error.message : 'Canaux indisponibles';
    return (
      <section
        data-testid={dataTestId}
        className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
      >
        <div role="alert" className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
          Erreur de chargement des canaux : {message}
        </div>
      </section>
    );
  }

  return (
    <section
      data-testid={dataTestId}
      aria-label="Canaux de notification"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
        Canaux de notification
      </h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Choisis où ProbaLab t’envoie tes alertes.
      </p>

      <ul className="mt-4 divide-y divide-slate-200 dark:divide-slate-800">
        <li className="py-4">
          <TelegramConnectFlow telegram={data.telegram} />
        </li>
        <li className="py-4">
          <EmailRow email={data.email} />
        </li>
        <li className="py-4">
          <PushPermissionButton push={data.push} />
        </li>
      </ul>
    </section>
  );
}

function EmailRow({
  email,
}: {
  email: { verified: boolean; address: string };
}) {
  return (
    <div className="flex items-center gap-3">
      <Mail className="h-5 w-5 text-emerald-500" aria-hidden="true" />
      <div className="flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-slate-900 dark:text-white">
            Email
          </span>
          {email.verified ? (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
              role="status"
            >
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
              Vérifié
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950 dark:text-amber-400"
              role="status"
            >
              Non vérifié
            </span>
          )}
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {email.address}
        </p>
      </div>
    </div>
  );
}

export default ChannelsCard;
