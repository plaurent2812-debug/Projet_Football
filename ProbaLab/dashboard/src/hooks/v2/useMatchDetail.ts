import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { FixtureId } from '@/types/v2/common';
import type { MatchDetailPayload } from '@/types/v2/match-detail';

/**
 * Hook : prédiction complète d'un match (header, probas 1X2, stats comparatives,
 * H2H, compositions, tous les marchés, reco principale, value bets).
 *
 * Endpoint : `GET /api/predictions/:fixtureId`.
 * Ne part pas tant que `fixtureId` est `null` (cas route pas encore montée).
 */
export function useMatchDetail(fixtureId: FixtureId | null) {
  return useQuery<MatchDetailPayload>({
    queryKey: ['v2', 'match-detail', fixtureId],
    queryFn: () => apiGet<MatchDetailPayload>(`/api/predictions/${fixtureId}`),
    enabled: fixtureId != null,
    staleTime: 30_000,
  });
}
