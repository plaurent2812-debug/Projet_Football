// Shared match types for the V2 frontend refonte.
// Single source of truth consumed by hooks, components and MSW handlers.

export type FixtureId = string;
export type Sport = 'football' | 'nhl';
export type SignalKind = 'safe' | 'value' | 'high_confidence';

export interface TeamRef {
  id: string;
  name: string;
  short: string;
  logoUrl?: string;
}

export interface LeagueRef {
  id: string;
  name: string;
  country: string;
  color: string; // hex token (spec section 7)
}

export interface Prob1x2 {
  home: number; // 0..1
  draw: number; // 0..1 (absent for NHL)
  away: number;
}

export interface ValueBet {
  market: string; // ex: "BTTS Oui"
  edgePct: number; // ex: 7.2
  bestOdd: number; // ex: 1.92
  bestBook: string; // ex: "Pinnacle"
  kellyPct: number; // ex: 2.4
}

export interface MatchRowData {
  fixtureId: FixtureId;
  sport: Sport;
  league: LeagueRef;
  kickoffUtc: string; // ISO 8601
  home: TeamRef;
  away: TeamRef;
  prob1x2: Prob1x2;
  signals: SignalKind[];
  topValueBet?: ValueBet; // best edge when present
}

export interface SafePick {
  fixtureId: FixtureId;
  league: LeagueRef;
  kickoffUtc: string;
  home: TeamRef;
  away: TeamRef;
  betLabel: string; // "PSG gagne vs Lens"
  odd: number; // 1.92
  probability: number; // 0..1
  justification: string; // 2-3 lines
}

export interface MatchesFilters {
  date: string; // YYYY-MM-DD (UTC)
  sports?: Sport[];
  leagues?: string[];
  signals?: SignalKind[];
  valueOnly?: boolean;
  sort?: 'kickoff' | 'edge' | 'confidence' | 'league';
}

export interface MatchesResponse {
  date: string;
  matches: MatchRowData[];
  counts: {
    total: number;
    bySport: Record<Sport, number>;
    byLeague: Record<string, number>;
  };
}
