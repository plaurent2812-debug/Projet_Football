import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';

/**
 * Connected status for each notification channel.
 * `push.devices` counts the number of active push subscriptions for the
 * user (mobile + desktop + tablet can cohabit).
 */
export interface NotificationChannelsStatus {
  telegram: {
    connected: boolean;
    username?: string;
  };
  email: {
    verified: boolean;
    address: string;
  };
  push: {
    subscribed: boolean;
    devices: number;
  };
}

export const NOTIF_CHANNELS_KEY = [
  'v2',
  'user',
  'notifications',
  'channels',
] as const;

export function useNotificationChannels() {
  return useQuery({
    queryKey: NOTIF_CHANNELS_KEY,
    queryFn: () =>
      apiGet<NotificationChannelsStatus>('/api/user/notifications/channels'),
    staleTime: 60 * 1000,
  });
}
