import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { SafePick } from '@/types/v2/matches';

// Real backend shape (see api/routers/v2/safe_pick.py::SafePickResponse).
// `safe_pick` is either a single bet, a 2-leg combo or null.
interface BackendSingleLeg {
  type: 'single';
  fixture_id: string;
  odds: number;
  confidence: number; // 0..1
  market?: string;
  selection?: string;
  kickoff_utc?: string;
  league_id?: number | string;
  league_name?: string;
  home_team?: string;
  away_team?: string;
  sport?: 'football' | 'nhl';
  odds_source?: 'real' | 'implied';
}

interface BackendSafePickResponse {
  date: string;
  safe_pick: BackendSingleLeg | { type: 'combo'; [k: string]: unknown } | null;
  fallback_message: string | null;
}

// Map the backend single-leg payload into the frontend SafePick shape.
// Combos are intentionally collapsed to `null` for now: the landing card
// only knows how to render a single bet. When combo rendering is added,
// this adapter is the single place to extend.
function adaptSafePick(raw: BackendSafePickResponse): SafePick | null {
  const leg = raw.safe_pick;
  if (!leg || leg.type !== 'single') return null;
  if (typeof leg.odds !== 'number' || typeof leg.confidence !== 'number') return null;

  const label = [leg.home_team, leg.away_team].filter(Boolean).join(' vs ') || 'Pronostic Safe';
  const betLabel =
    leg.selection && leg.market
      ? `${leg.selection.toUpperCase()} · ${leg.market} (${label})`
      : label;

  return {
    fixtureId: String(leg.fixture_id),
    league: {
      id: String(leg.league_id ?? 'unknown'),
      name: leg.league_name ?? '',
      country: '',
      color: '#64748b',
    },
    kickoffUtc: leg.kickoff_utc ?? '',
    home: { id: '', name: leg.home_team ?? '', short: leg.home_team ?? '' },
    away: { id: '', name: leg.away_team ?? '', short: leg.away_team ?? '' },
    betLabel,
    odd: leg.odds,
    probability: leg.confidence,
    justification: '',
  };
}

export function useSafePick(date: string) {
  return useQuery<BackendSafePickResponse, Error, SafePick | null>({
    queryKey: ['v2', 'safe-pick', date],
    queryFn: () => apiGet<BackendSafePickResponse>('/api/safe-pick', { date }),
    select: adaptSafePick,
    staleTime: 5 * 60 * 1000,
  });
}
