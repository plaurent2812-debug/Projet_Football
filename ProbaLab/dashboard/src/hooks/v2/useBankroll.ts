import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';

/**
 * Bankroll summary — returned by `GET /api/user/bankroll`.
 *
 * The backend exposes snake_case fields; we mirror them verbatim
 * so the client never has to guess the contract shape. Negative
 * values are expected for `drawdown_max_pct` (it measures a loss
 * peak-to-trough).
 */
export interface BankrollSummary {
  current_balance: number;
  initial_balance: number;
  roi_30d: number;
  roi_90d: number;
  win_rate: number;
  drawdown_max_pct: number;
  kelly_fraction_active: number;
  total_bets: number;
  wins: number;
  losses: number;
  voids: number;
}

export const BANKROLL_KEY = ['v2', 'user', 'bankroll'] as const;

export function useBankroll() {
  return useQuery({
    queryKey: BANKROLL_KEY,
    queryFn: () => apiGet<BankrollSummary>('/api/user/bankroll'),
    staleTime: 60 * 1000,
  });
}
