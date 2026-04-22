import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';

/**
 * A single point on the 90-day cumulative ROI curve exposed
 * by the public track-record endpoint.
 */
export interface TrackRecordPoint {
  date: string;
  roi: number;
}

/**
 * Shape returned by `GET /api/public/track-record/live`.
 * All figures are computed on the integrality of placed bets — no cherry picking.
 */
export interface TrackRecordLive {
  clv30d: number;
  roi90d: number;
  brier30d: number;
  safeRate90d: number;
  roiCurve90d: TrackRecordPoint[];
  lastUpdatedAt: string;
}

/**
 * Live track-record hook.
 *
 * Polls the public endpoint every 5 minutes (stale-while-revalidate).
 * Publicly cacheable data — no auth required — which is why we
 * prefer a 5-minute stale time over the default 0.
 */
export function useTrackRecordLive() {
  return useQuery({
    queryKey: ['v2', 'public', 'track-record-live'],
    queryFn: () => apiGet<TrackRecordLive>('/api/public/track-record/live'),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}
