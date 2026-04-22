import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { SubscriptionStatus } from '@/types/v2/common';

/**
 * Subscription payload — returned by `GET /api/user/subscription`.
 *
 * `plan` is the marketing label ; `status` is the Stripe lifecycle status
 * (re-exported from `types/v2/common` to keep one source of truth).
 */
export interface SubscriptionData {
  plan: 'FREE' | 'TRIAL' | 'PREMIUM';
  status: SubscriptionStatus;
  renewsAt?: string;
  cancelAtPeriodEnd?: boolean;
  planName?: string;
  cancellationUrl?: string;
}

export function useSubscription() {
  return useQuery({
    queryKey: ['v2', 'user', 'subscription'],
    queryFn: () => apiGet<SubscriptionData>('/api/user/subscription'),
    staleTime: 60 * 1000,
  });
}
