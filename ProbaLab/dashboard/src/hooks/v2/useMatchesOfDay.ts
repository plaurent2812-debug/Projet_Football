import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type {
  LeagueRef,
  MatchRowData,
  MatchesFilters,
  MatchesResponse,
  Prob1x2,
  SignalKind,
  Sport,
  TeamRef,
  ValueBet,
} from '@/types/v2/matches';

/**
 * Raw backend shape returned by `GET /api/matches`.
 * See `ProbaLab/api/routers/v2/matches_v2.py::MatchesV2Response`.
 */
interface BackendMatchRow {
  fixture_id: string;
  sport: 'football' | 'nhl';
  league_id: number | string;
  league_name: string;
  home_team: string;
  away_team: string;
  home_logo?: string | null;
  away_logo?: string | null;
  status?: string | null;
  home_goals?: number | null;
  away_goals?: number | null;
  kickoff_utc: string;
  prediction?: {
    proba_home?: number | null;
    proba_draw?: number | null;
    proba_away?: number | null;
    confidence_score?: number;
  } | null;
  confidence?: number;
  edge_pct?: number;
  signals?: string[];
}

interface BackendMatchesV2Response {
  date: string;
  total: number;
  groups: Array<{
    league_id: number | string;
    league_name: string;
    matches: BackendMatchRow[];
  }>;
}

// League id → hex color token (spec section 7).
const LEAGUE_COLORS: Record<string, string> = {
  '61': '#1e40af', // Ligue 1
  '62': '#3b82f6', // Ligue 2
  '39': '#7c3aed', // Premier League
  '140': '#ea580c', // La Liga
  '135': '#059669', // Serie A
  '78': '#dc2626', // Bundesliga
  '2': '#60a5fa', // UCL
  '3': '#f59e0b', // UEL
  NHL: '#64748b',
};

const LEAGUE_COUNTRIES: Record<string, string> = {
  '61': 'France',
  '62': 'France',
  '39': 'Angleterre',
  '140': 'Espagne',
  '135': 'Italie',
  '78': 'Allemagne',
  '2': 'Europe',
  '3': 'Europe',
  NHL: 'Amérique du Nord',
};

function shortName(name: string): string {
  if (!name) return '';
  const words = name.split(/\s+/).filter(Boolean);
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
  return words
    .map((w) => w[0])
    .join('')
    .slice(0, 3)
    .toUpperCase();
}

function buildTeam(name: string | undefined, logo: string | null | undefined): TeamRef {
  const safeName = name ?? 'Unknown';
  return {
    id: safeName,
    name: safeName,
    short: shortName(safeName),
    logoUrl: logo ?? undefined,
  };
}

function buildLeague(
  leagueId: number | string | null | undefined,
  leagueName: string | undefined,
): LeagueRef {
  const id = String(leagueId ?? 'unknown');
  return {
    id,
    name: leagueName || 'Ligue',
    country: LEAGUE_COUNTRIES[id] ?? '',
    color: LEAGUE_COLORS[id] ?? '#64748b',
  };
}

function buildProb1x2(row: BackendMatchRow): Prob1x2 {
  const pred = row.prediction ?? {};
  const toUnit = (value: number | null | undefined): number | null =>
    typeof value === 'number' && Number.isFinite(value) ? value / 100 : null;
  const home = toUnit(pred.proba_home);
  const draw = toUnit(pred.proba_draw);
  const away = toUnit(pred.proba_away);
  return { home, draw, away };
}

function buildSignals(raw: string[] | undefined): SignalKind[] {
  if (!raw) return [];
  return raw
    .map((s) => {
      if (s === 'value' || s === 'safe') return s;
      if (s === 'confidence') return 'high_confidence' as SignalKind;
      return null;
    })
    .filter((s): s is SignalKind => s !== null);
}

function buildTopValueBet(row: BackendMatchRow): ValueBet | undefined {
  if (!row.edge_pct || row.edge_pct <= 0) return undefined;
  return {
    market: '1X2',
    edgePct: row.edge_pct,
    bestOdd: 0,
    bestBook: 'Betclic',
    kellyPct: 0,
  };
}

function adaptRow(row: BackendMatchRow, fallbackLeague: { id: number | string; name: string }): MatchRowData {
  return {
    fixtureId: row.fixture_id,
    sport: row.sport,
    league: buildLeague(row.league_id ?? fallbackLeague.id, row.league_name || fallbackLeague.name),
    kickoffUtc: row.kickoff_utc,
    home: buildTeam(row.home_team, row.home_logo),
    away: buildTeam(row.away_team, row.away_logo),
    status: row.status ?? null,
    score: {
      home: row.home_goals ?? null,
      away: row.away_goals ?? null,
    },
    prob1x2: buildProb1x2(row),
    signals: buildSignals(row.signals),
    topValueBet: buildTopValueBet(row),
  };
}

/**
 * Flatten the backend response (grouped-by-league + snake_case) into the
 * frontend shape (flat matches + camelCase + nested refs).
 */
function adaptResponse(raw: BackendMatchesV2Response): MatchesResponse {
  const matches: MatchRowData[] = [];
  const bySport: Record<Sport, number> = { football: 0, nhl: 0 };
  const byLeague: Record<string, number> = {};

  for (const group of raw.groups ?? []) {
    const leagueKey = String(group.league_id);
    byLeague[leagueKey] = (byLeague[leagueKey] ?? 0) + (group.matches?.length ?? 0);
    for (const m of group.matches ?? []) {
      const sport = (m.sport ?? 'football') as Sport;
      bySport[sport] = (bySport[sport] ?? 0) + 1;
      matches.push(adaptRow(m, { id: group.league_id, name: group.league_name }));
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
