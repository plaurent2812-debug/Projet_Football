import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '@/lib/v2/apiClient';
import type {
  AddBetRequest,
  AddBetResponse,
} from '@/types/v2/match-detail';

/**
 * Hook : ajoute un pari à la bankroll de l'utilisateur (action depuis la
 * RecoCard / ValueBetsList / AllMarketsGrid).
 *
 * Endpoint : `POST /api/user/bets`.
 *
 * Effet secondaire : invalide `['bankroll']` pour déclencher un refetch du
 * dashboard P&L dans les composants qui l'utilisent (`useBankroll` ailleurs).
 *
 * Optimistic update : on ne mute pas le cache local ici ; l'invalidation au
 * succès suffit côté Lot 4 (la balance bankroll ne peut pas être dérivée
 * côté client sans voir la réponse backend, qui peut inclure un rejet
 * silencieux si Kelly cap dépassé).
 */
export function useAddToBankroll() {
  const qc = useQueryClient();
  return useMutation<AddBetResponse, Error, AddBetRequest>({
    mutationFn: (input) => apiPost<AddBetRequest, AddBetResponse>('/api/user/bets', input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bankroll'] });
    },
  });
}
