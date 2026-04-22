import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiDelete, apiPost } from '@/lib/v2/apiClient';
import { NOTIF_CHANNELS_KEY } from './useNotificationChannels';

/**
 * Payload returned by `POST /api/user/notifications/telegram/connect-start`.
 * `bot_url` is a deep link to the Telegram bot with the single-use token
 * — the client just needs to open it in a new tab.
 */
export interface TelegramConnectStart {
  token: string;
  bot_url: string;
}

export function useConnectTelegram() {
  const qc = useQueryClient();
  return useMutation<TelegramConnectStart, Error, void>({
    mutationFn: () =>
      apiPost<Record<string, never>, TelegramConnectStart>(
        '/api/user/notifications/telegram/connect-start',
        {},
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NOTIF_CHANNELS_KEY });
    },
  });
}

export function useDisconnectTelegram() {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiDelete('/api/user/notifications/telegram'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NOTIF_CHANNELS_KEY });
    },
  });
}
