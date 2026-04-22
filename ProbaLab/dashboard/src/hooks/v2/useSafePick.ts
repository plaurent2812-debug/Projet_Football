import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { SafePick } from '@/types/v2/matches';

export function useSafePick(date: string) {
  return useQuery({
    queryKey: ['v2', 'safe-pick', date],
    queryFn: () => apiGet<SafePick>('/api/safe-pick', { date }),
    staleTime: 5 * 60 * 1000,
  });
}
