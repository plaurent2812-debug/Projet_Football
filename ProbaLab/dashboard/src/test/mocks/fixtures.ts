import type { LeagueRef, MatchRowData, SafePick } from '@/types/v2/matches';
import type { PerformanceSummary } from '@/types/v2/performance';
import type {
  AnalysisPayload,
  MatchDetailPayload,
} from '@/types/v2/match-detail';

export const leagueL1: LeagueRef = {
  id: 'fr-l1',
  name: 'Ligue 1',
  country: 'FR',
  color: '#2563eb',
};

export const leaguePL: LeagueRef = {
  id: 'en-pl',
  name: 'Premier League',
  country: 'EN',
  color: '#7c3aed',
};

export const leagueSA: LeagueRef = {
  id: 'it-sa',
  name: 'Serie A',
  country: 'IT',
  color: '#0ea5e9',
};

export const mockMatches: MatchRowData[] = [
  {
    fixtureId: 'fx-1',
    sport: 'football',
    league: leagueL1,
    kickoffUtc: '2026-04-21T19:00:00Z',
    home: { id: 't-psg', name: 'Paris Saint-Germain', short: 'PSG' },
    away: { id: 't-len', name: 'RC Lens', short: 'LEN' },
    prob1x2: { home: 0.58, draw: 0.24, away: 0.18 },
    signals: ['safe'],
    topValueBet: undefined,
  },
  {
    fixtureId: 'fx-2',
    sport: 'football',
    league: leaguePL,
    kickoffUtc: '2026-04-21T18:30:00Z',
    home: { id: 't-ars', name: 'Arsenal', short: 'ARS' },
    away: { id: 't-che', name: 'Chelsea', short: 'CHE' },
    prob1x2: { home: 0.51, draw: 0.26, away: 0.23 },
    signals: ['value', 'high_confidence'],
    topValueBet: {
      market: 'Over 2.5',
      edgePct: 5.4,
      bestOdd: 1.85,
      bestBook: 'Unibet',
      kellyPct: 1.7,
    },
  },
  {
    fixtureId: 'fx-3',
    sport: 'football',
    league: leagueSA,
    kickoffUtc: '2026-04-21T20:45:00Z',
    home: { id: 't-int', name: 'Inter Milan', short: 'INT' },
    away: { id: 't-mil', name: 'AC Milan', short: 'MIL' },
    prob1x2: { home: 0.42, draw: 0.27, away: 0.31 },
    signals: ['value'],
    topValueBet: {
      market: 'Over 2.5',
      edgePct: 7.2,
      bestOdd: 1.92,
      bestBook: 'Pinnacle',
      kellyPct: 2.4,
    },
  },
];

export const mockSafePick: SafePick = {
  fixtureId: 'fx-1',
  league: leagueL1,
  kickoffUtc: '2026-04-21T19:00:00Z',
  home: mockMatches[0].home,
  away: mockMatches[0].away,
  betLabel: 'PSG gagne vs Lens',
  odd: 1.85,
  probability: 0.58,
  justification:
    "PSG enchaîne 5 victoires à domicile avec xG moyen 2.3. Lens absent de ses 3 cadres défensifs. Valeur cote 1.85 vs proba 58% → edge 7.3%.",
};

export const mockPerformance: PerformanceSummary = {
  roi30d: { value: 12.4, deltaVs7d: 0.8 },
  accuracy: { value: 54.2, deltaVs7d: -0.3 },
  brier7d: { value: 0.189, deltaVs7d: -0.004 },
  bankroll: { value: 1240, currency: 'EUR' },
};

// ---------------------------------------------------------------------------
// Lot 4 — Match Detail fixtures (PSG vs Lens)
// ---------------------------------------------------------------------------

export const mockMatchDetailPsgLens: MatchDetailPayload = {
  header: {
    fixture_id: 'fx-1',
    kickoff_utc: '2026-04-21T19:00:00Z',
    stadium: 'Parc des Princes',
    league_name: 'Ligue 1',
    home: {
      id: 1,
      name: 'Paris Saint-Germain',
      logo_url: '/logos/psg.png',
      rank: 1,
      form: ['W', 'W', 'D', 'W', 'W'],
    },
    away: {
      id: 2,
      name: 'RC Lens',
      logo_url: '/logos/lens.png',
      rank: 7,
      form: ['L', 'D', 'W', 'L', 'D'],
    },
  },
  probs_1x2: { home: 0.58, draw: 0.24, away: 0.18 },
  stats: [
    { label: 'xG 5 derniers', home_value: 2.3, away_value: 1.1 },
    { label: 'Possession moyenne', home_value: 62, away_value: 47, unit: '%' },
    { label: 'Tirs cadrés / match', home_value: 6.2, away_value: 3.8 },
    { label: 'Clean sheets (5 derniers)', home_value: 3, away_value: 1 },
  ],
  h2h: {
    home_wins: 7,
    draws: 2,
    away_wins: 1,
    last_matches: [
      {
        date_utc: '2026-01-14T20:00:00Z',
        home_team: 'RC Lens',
        away_team: 'Paris Saint-Germain',
        score: '1-2',
      },
      {
        date_utc: '2025-08-25T19:00:00Z',
        home_team: 'Paris Saint-Germain',
        away_team: 'RC Lens',
        score: '3-0',
      },
      {
        date_utc: '2025-04-09T19:00:00Z',
        home_team: 'Paris Saint-Germain',
        away_team: 'RC Lens',
        score: '2-1',
      },
    ],
  },
  compositions: {
    home: {
      formation: '4-3-3',
      starters: [
        { number: 1, name: 'Donnarumma', position: 'GK' },
        { number: 4, name: 'Marquinhos', position: 'DC' },
        { number: 5, name: 'Pacho', position: 'DC' },
        { number: 26, name: 'Nuno Mendes', position: 'DG' },
        { number: 2, name: 'Hakimi', position: 'DD' },
        { number: 8, name: 'Fabian Ruiz', position: 'MC' },
        { number: 17, name: 'Vitinha', position: 'MC' },
        { number: 87, name: 'Joao Neves', position: 'MC' },
        { number: 10, name: 'Dembélé', position: 'AD' },
        { number: 9, name: 'Gonçalo Ramos', position: 'AT' },
        { number: 14, name: 'Doué', position: 'AG' },
      ],
    },
    away: {
      formation: '3-4-3',
      starters: [
        { number: 1, name: 'Samba', position: 'GK' },
        { number: 4, name: 'Danso', position: 'DC' },
        { number: 5, name: 'Medina', position: 'DC' },
        { number: 23, name: 'Gradit', position: 'DC' },
        { number: 25, name: 'Frankowski', position: 'PD' },
        { number: 8, name: 'Thomasson', position: 'MC' },
        { number: 18, name: 'Fofana', position: 'MC' },
        { number: 3, name: 'Machado', position: 'PG' },
        { number: 7, name: 'Sotoca', position: 'AT' },
        { number: 9, name: 'Wahi', position: 'AT' },
        { number: 10, name: 'Said', position: 'AT' },
      ],
    },
    status: 'probable',
  },
  all_markets: [
    {
      market_key: '1x2.home',
      label: 'Victoire PSG',
      probability: 0.58,
      fair_odds: 1.72,
      best_book_odds: 1.85,
      is_value: true,
      edge: 0.076,
    },
    {
      market_key: '1x2.draw',
      label: 'Match nul',
      probability: 0.24,
      fair_odds: 4.17,
      best_book_odds: 4.0,
      is_value: false,
      edge: null,
    },
    {
      market_key: '1x2.away',
      label: 'Victoire Lens',
      probability: 0.18,
      fair_odds: 5.56,
      best_book_odds: 5.2,
      is_value: false,
      edge: null,
    },
    {
      market_key: 'btts.yes',
      label: 'Les deux équipes marquent',
      probability: 0.52,
      fair_odds: 1.92,
      best_book_odds: 1.9,
      is_value: false,
      edge: null,
    },
    {
      market_key: 'ou_2_5.over',
      label: 'Plus de 2,5 buts',
      probability: 0.61,
      fair_odds: 1.64,
      best_book_odds: 1.72,
      is_value: true,
      edge: 0.049,
    },
  ],
  recommendation: {
    market_key: '1x2.home',
    market_label: 'Victoire PSG',
    odds: 1.85,
    confidence: 0.58,
    kelly_fraction: 0.042,
    edge: 0.076,
    book_name: 'Pinnacle',
  },
  value_bets: [
    {
      market_key: '1x2.home',
      label: 'Victoire PSG @ Pinnacle',
      probability: 0.58,
      best_odds: 1.85,
      edge: 0.076,
    },
    {
      market_key: 'ou_2_5.over',
      label: 'Plus de 2,5 buts @ Unibet',
      probability: 0.61,
      best_odds: 1.72,
      edge: 0.049,
    },
  ],
};

// Map fixtureId -> payload pour élargir la couverture MSW.
export const mockMatchDetailById: Record<string, MatchDetailPayload> = {
  'fx-1': mockMatchDetailPsgLens,
};

export const mockAnalysisPsgLens: AnalysisPayload = {
  paragraphs: [
    "Paris Saint-Germain reste sur 4 victoires consécutives à domicile avec un xG moyen de 2,3 et une défense solide (3 clean sheets sur les 5 derniers).",
    "Lens peine à l'extérieur (1 victoire sur 5) et devra faire sans Danso, suspendu pour accumulation de cartons, ce qui fragilise la charnière centrale.",
    "Statistiquement, le scénario attendu est un PSG dominant la possession (~62%) avec un score probable 2-1 ou 3-1. La cote 1,85 sur la victoire domicile offre un edge de 7,6% vs notre probabilité modèle de 58%.",
  ],
  generated_at: '2026-04-21T10:00:00Z',
  is_teaser: false,
};

export const mockAnalysisById: Record<string, AnalysisPayload> = {
  'fx-1': mockAnalysisPsgLens,
};
