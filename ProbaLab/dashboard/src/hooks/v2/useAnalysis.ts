import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { FixtureId } from '@/types/v2/common';
import type { AnalysisPayload } from '@/types/v2/match-detail';

/**
 * Hook : récupère l'analyse IA Gemini d'un match (3 paragraphes narratifs +
 * reco rationnelle).
 *
 * Endpoint : `GET /api/analysis/:fixtureId`.
 *
 * État "teaser" : le backend renvoie `is_teaser: true` + un seul paragraphe
 * pour les utilisateurs free post-trial, laissant la décision de masquer le
 * reste à l'UI (blur + LockOverlay).
 *
 * Les paragraphes sont toujours rendus via React children (text nodes) —
 * jamais en HTML brut — pour éviter toute injection depuis le LLM.
 */
export function useAnalysis(fixtureId: FixtureId | null) {
  return useQuery<AnalysisPayload>({
    queryKey: ['v2', 'analysis', fixtureId],
    queryFn: () => apiGet<AnalysisPayload>(`/api/analysis/${fixtureId}`),
    enabled: fixtureId != null,
    staleTime: 60_000,
  });
}
