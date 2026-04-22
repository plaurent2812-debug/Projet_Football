import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';

export type ROIWindow = 7 | 30 | 90;

/**
 * One row of the `/api/user/bankroll/roi-by-market` response.
 *
 * `roi_pct` can be negative (losing market). Counts should reconcile:
 * `n === wins + losses + voids` modulo pending bets which are excluded
 * from the aggregation backend-side.
 */
export interface ROIByMarketItem {
  market: string;
  roi_pct: number;
  n: number;
  wins: number;
  losses: number;
  voids: number;
}

export const ROI_BY_MARKET_KEY = ['v2', 'user', 'bankroll', 'roi-by-market'] as const;

export function useROIByMarket(window: ROIWindow = 30) {
  return useQuery({
    queryKey: [...ROI_BY_MARKET_KEY, window],
    queryFn: () =>
      apiGet<ROIByMarketItem[]>('/api/user/bankroll/roi-by-market', {
        window: String(window),
      }),
    staleTime: 60 * 1000,
  });
}
