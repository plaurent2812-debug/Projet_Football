import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { PerformanceSummary } from '@/types/v2/performance';

export function usePerformanceSummary(window: 7 | 30 | 90 = 30) {
  return useQuery({
    queryKey: ['v2', 'performance', 'summary', window],
    queryFn: () =>
      apiGet<PerformanceSummary>('/api/performance/summary', { window: String(window) }),
    staleTime: 5 * 60 * 1000,
  });
}
