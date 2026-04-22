import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { MatchRowData, MatchesFilters, MatchesResponse, Sport } from '@/types/v2/matches';

/**
 * Raw backend shape returned by `GET /api/matches`.
 * See `ProbaLab/api/routers/v2/matches_v2.py::MatchesV2Response`.
 */
interface BackendMatchesV2Response {
  date: string;
  total: number;
  groups: Array<{
    league_id: number | string;
    league_name: string;
    matches: Array<Record<string, unknown>>;
  }>;
}

/**
 * Flatten the backend response (grouped-by-league) into the frontend shape
 * (flat matches + counts), so consumers don't need to worry about grouping.
 */
function adaptResponse(raw: BackendMatchesV2Response): MatchesResponse {
  const matches: MatchRowData[] = [];
  const bySport: Record<Sport, number> = { football: 0, nhl: 0 };
  const byLeague: Record<string, number> = {};

  for (const group of raw.groups ?? []) {
    const leagueKey = String(group.league_id);
    byLeague[leagueKey] = (byLeague[leagueKey] ?? 0) + (group.matches?.length ?? 0);
    for (const m of group.matches ?? []) {
      const sport = (m.sport as Sport) ?? 'football';
      bySport[sport] = (bySport[sport] ?? 0) + 1;
      matches.push({
        ...(m as Record<string, unknown>),
        league_id: m.league_id ?? group.league_id,
        league_name: (m.league_name as string) || group.league_name,
      } as unknown as MatchRowData);
    }
  }

  return {
    date: raw.date,
    matches,
    counts: {
      total: raw.total ?? matches.length,
      bySport,
      byLeague,
    },
  };
}

export function useMatchesOfDay(filters: MatchesFilters) {
  return useQuery({
    queryKey: ['v2', 'matches', filters],
    queryFn: async () => {
      const raw = await apiGet<BackendMatchesV2Response>('/api/matches', {
        date: filters.date,
        sports: filters.sports?.join(','),
        leagues: filters.leagues?.join(','),
        signals: filters.signals?.join(','),
        value_only: filters.valueOnly ? 'true' : undefined,
        sort: filters.sort,
      });
      return adaptResponse(raw);
    },
    staleTime: 5 * 60 * 1000,
  });
}
