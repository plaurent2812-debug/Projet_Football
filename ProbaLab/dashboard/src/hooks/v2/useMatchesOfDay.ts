import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { MatchesFilters, MatchesResponse } from '@/types/v2/matches';

export function useMatchesOfDay(filters: MatchesFilters) {
  return useQuery({
    queryKey: ['v2', 'matches', filters],
    queryFn: () =>
      apiGet<MatchesResponse>('/api/matches', {
        date: filters.date,
        sports: filters.sports?.join(','),
        leagues: filters.leagues?.join(','),
        signals: filters.signals?.join(','),
        value_only: filters.valueOnly ? 'true' : undefined,
        sort: filters.sort,
      }),
    staleTime: 5 * 60 * 1000,
  });
}
