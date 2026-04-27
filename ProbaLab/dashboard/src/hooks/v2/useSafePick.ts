import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { SafePick } from '@/types/v2/matches';

// Real backend shape (see api/routers/v2/safe_pick.py::SafePickResponse).
// `safe_pick` is either a single bet, a 2-leg combo or null.
interface BackendSingleLeg {
  type: 'single';
  fixture_id: string | number;
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

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

// Map the backend single-leg payload into the frontend SafePick shape.
// Combos are intentionally collapsed to `null` for now: the landing card
// only knows how to render a single bet. When combo rendering is added,
// this adapter is the single place to extend.
function adaptSafePick(raw: BackendSafePickResponse): SafePick | null {
  const leg = raw.safe_pick;
  if (!leg || leg.type !== 'single') return null;
  if (!isFiniteNumber(leg.odds) || !isFiniteNumber(leg.confidence)) return null;

  const homeName = leg.home_team ?? '';
  const awayName = leg.away_team ?? '';
  const matchup = [homeName, awayName].filter(Boolean).join(' vs ');
  const selection = leg.selection ? leg.selection.toUpperCase() : '';
  const market = leg.market ?? '';
  const betLabel =
    market === '1X2' && leg.selection === 'home' && homeName && awayName
      ? `${homeName} gagne vs ${awayName}`
      : market === '1X2' && leg.selection === 'away' && homeName && awayName
        ? `${awayName} gagne vs ${homeName}`
        : market === '1X2' && leg.selection === 'draw' && matchup
          ? `Match nul ${matchup}`
          : [selection, market].filter(Boolean).join(' · ') || matchup || 'Pronostic Safe';

  return {
    fixtureId: String(leg.fixture_id),
    league: {
      id: String(leg.league_id ?? 'unknown'),
      name: leg.league_name ?? '',
      country: '',
      color: '#10b981',
    },
    kickoffUtc: leg.kickoff_utc ?? '',
    home: { id: '', name: homeName, short: homeName },
    away: { id: '', name: awayName, short: awayName },
    betLabel,
    odd: leg.odds,
    probability: leg.confidence,
    justification: raw.fallback_message ?? '',
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
