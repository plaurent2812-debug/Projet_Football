import { useState } from 'react';
import { AlertCircle, CheckCircle2, Link as LinkIcon, Send, Unlink } from 'lucide-react';
import {
  useConnectTelegram,
  useDisconnectTelegram,
} from '@/hooks/v2/useConnectTelegram';
import type { NotificationChannelsStatus } from '@/hooks/v2/useNotificationChannels';

export interface TelegramConnectFlowProps {
  telegram: NotificationChannelsStatus['telegram'];
  'data-testid'?: string;
}

/**
 * Telegram row for the notifications card.
 *
 * Two surfaces :
 *  - disconnected → "Connecter Telegram" button. Clicking fetches a
 *    one-shot token from the backend, opens the bot deep link in a new
 *    tab, then displays a "En attente…" hint until the channels query
 *    is invalidated (webhook → GET channels → re-render connected).
 *  - connected → "@username · Connecté" + "Déconnecter" button.
 *
 * All copy is in French to match the rest of the dashboard. We use
 * `role="alert"` for the error path so screen readers announce it.
 */
export function TelegramConnectFlow({
  telegram,
  'data-testid': dataTestId = 'telegram-connect-flow',
}: TelegramConnectFlowProps) {
  const connect = useConnectTelegram();
  const disconnect = useDisconnectTelegram();
  const [waiting, setWaiting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const onConnect = async () => {
    setErrorMsg(null);
    try {
      const { bot_url } = await connect.mutateAsync();
      setWaiting(true);
      if (typeof window !== 'undefined' && typeof window.open === 'function') {
        window.open(bot_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erreur de connexion à Telegram';
      setErrorMsg(`Erreur : ${message}`);
      setWaiting(false);
    }
  };

  const onDisconnect = async () => {
    setErrorMsg(null);
    try {
      await disconnect.mutateAsync();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erreur de déconnexion Telegram';
      setErrorMsg(`Erreur : ${message}`);
    }
  };

  const isConnected = telegram.connected;
  const isDisconnecting = disconnect.isPending;

  return (
    <div
      data-testid={dataTestId}
      className="flex flex-col gap-2"
    >
      <div className="flex items-center gap-3">
        <Send className="h-5 w-5 text-sky-500" aria-hidden="true" />
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-slate-900 dark:text-white">
              Telegram
            </span>
            {isConnected ? (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                role="status"
              >
                <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                Connecté
              </span>
            ) : (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                role="status"
              >
                Non connecté
              </span>
            )}
          </div>
          {isConnected && telegram.username && (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              @{telegram.username}
            </p>
          )}
        </div>
        {isConnected ? (
          <button
            type="button"
            onClick={onDisconnect}
            disabled={isDisconnecting}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <Unlink className="h-4 w-4" aria-hidden="true" />
            {isDisconnecting ? 'Déconnexion…' : 'Déconnecter'}
          </button>
        ) : (
          <button
            type="button"
            onClick={onConnect}
            disabled={connect.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-sm font-medium text-white hover:bg-sky-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LinkIcon className="h-4 w-4" aria-hidden="true" />
            {connect.isPending ? 'Connexion…' : 'Connecter Telegram'}
          </button>
        )}
      </div>

      {waiting && !isConnected && !errorMsg && (
        <p
          className="ml-8 text-sm text-slate-500 dark:text-slate-400"
          role="status"
        >
          En attente… (lien envoyé sur Telegram)
        </p>
      )}

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

export default TelegramConnectFlow;
