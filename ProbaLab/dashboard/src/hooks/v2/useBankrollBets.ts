import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPatch, apiDelete } from '@/lib/v2/apiClient';

export type BetResult = 'WIN' | 'LOSS' | 'VOID' | 'PENDING';

/**
 * Bet row — returned by `GET /api/user/bets`.
 *
 * `resolved_at` is `null` as long as the bet is PENDING. All timestamps
 * are ISO UTC — callers format at render time.
 */
export interface BetRow {
  id: string;
  fixture_id: string;
  match_title: string;
  market: string;
  selection: string;
  odds: number;
  stake: number;
  result: BetResult;
  placed_at: string;
  resolved_at: string | null;
}

export type BetsFilter = 'all' | 'pending' | 'won' | 'lost';

/**
 * Payload for `POST /api/user/bets`. Mirrors the backend validator —
 * the form layer validates with `addBetSchema` before calling.
 */
export interface AddBetPayload {
  fixture_id: string;
  match_title: string;
  market: string;
  selection: string;
  odds: number;
  stake: number;
  placed_at: string;
}

/**
 * Partial payload for `PATCH /api/user/bets/:id`. Only the outcome
 * can be changed client-side.
 */
export interface UpdateBetPayload {
  result: BetResult;
  resolved_at?: string;
}

export const BETS_KEY = ['v2', 'user', 'bankroll', 'bets'] as const;

export function useBankrollBets(filter: BetsFilter = 'all') {
  return useQuery({
    queryKey: [...BETS_KEY, filter],
    queryFn: () =>
      apiGet<BetRow[]>('/api/user/bets', filter === 'all' ? undefined : { filter }),
    staleTime: 30 * 1000,
  });
}

function invalidateBankroll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['v2', 'user', 'bankroll'] });
}

export function useAddBet() {
  const qc = useQueryClient();
  return useMutation<BetRow, Error, AddBetPayload>({
    mutationFn: (input) => apiPost<AddBetPayload, BetRow>('/api/user/bets', input),
    onSuccess: () => invalidateBankroll(qc),
  });
}

export function useUpdateBet(id: string) {
  const qc = useQueryClient();
  return useMutation<BetRow, Error, UpdateBetPayload>({
    mutationFn: (patch) =>
      apiPatch<UpdateBetPayload, BetRow>(`/api/user/bets/${id}`, patch),
    onSuccess: () => invalidateBankroll(qc),
  });
}

export function useDeleteBet(id: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiDelete(`/api/user/bets/${id}`),
    onSuccess: () => invalidateBankroll(qc),
  });
}
