import type { LeagueRef, MatchRowData, SafePick } from '@/types/v2/matches';
import type { PerformanceSummary } from '@/types/v2/performance';
import type {
  AnalysisPayload,
  MatchDetailPayload,
} from '@/types/v2/match-detail';
import type { TrackRecordLive } from '@/hooks/v2/useTrackRecordLive';
import type { ProfileData } from '@/hooks/v2/useProfile';
import type { SubscriptionData } from '@/hooks/v2/useSubscription';
import type { Invoice } from '@/hooks/v2/useInvoices';
import type { BankrollSummary } from '@/hooks/v2/useBankroll';
import type { BetRow } from '@/hooks/v2/useBankrollBets';
import type { ROIByMarketItem } from '@/hooks/v2/useROIByMarket';
import type { BankrollSettings } from '@/lib/v2/schemas';
import type { NotificationRule } from '@/lib/v2/schemas/rules';
import type { NotificationChannelsStatus } from '@/hooks/v2/useNotificationChannels';

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
      bestBook: 'Betclic',
      kellyPct: 2.4,
    },
  },
];

// ---------------------------------------------------------------------------
// Backend-shaped matches response (GET /api/matches) — grouped by league,
// snake_case, probabilities in 0-100 range (useMatchesOfDay divides by 100).
// Keep in sync with BackendMatchesV2Response in useMatchesOfDay.ts.
// ---------------------------------------------------------------------------
export const mockMatchesBackendResponse = {
  date: '2026-04-21',
  total: 3,
  groups: [
    {
      league_id: 61,
      league_name: 'Ligue 1',
      matches: [
        {
          fixture_id: 'fx-1',
          sport: 'football' as const,
          league_id: 61,
          league_name: 'Ligue 1',
          home_team: 'Paris Saint-Germain',
          away_team: 'RC Lens',
          kickoff_utc: '2026-04-21T19:00:00Z',
          prediction: { proba_home: 58, proba_draw: 24, proba_away: 18 },
          signals: ['safe'],
          edge_pct: 0,
        },
      ],
    },
    {
      league_id: 39,
      league_name: 'Premier League',
      matches: [
        {
          fixture_id: 'fx-2',
          sport: 'football' as const,
          league_id: 39,
          league_name: 'Premier League',
          home_team: 'Arsenal',
          away_team: 'Chelsea',
          kickoff_utc: '2026-04-21T18:30:00Z',
          prediction: { proba_home: 51, proba_draw: 26, proba_away: 23 },
          signals: ['value', 'confidence'],
          edge_pct: 5.4,
        },
      ],
    },
    {
      league_id: 135,
      league_name: 'Serie A',
      matches: [
        {
          fixture_id: 'fx-3',
          sport: 'football' as const,
          league_id: 135,
          league_name: 'Serie A',
          home_team: 'Inter Milan',
          away_team: 'AC Milan',
          kickoff_utc: '2026-04-21T20:45:00Z',
          prediction: { proba_home: 42, proba_draw: 27, proba_away: 31 },
          signals: ['value'],
          edge_pct: 7.2,
        },
      ],
    },
  ],
};

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
    "PSG enchaîne 5 victoires à domicile avec xG moyen 2.3. Lens absent de ses 3 cadres défensifs. La cote 1.85 reste intéressante face à notre probabilité de 58% : signal modèle +7.3%.",
};

// Wrapper shape returned by the real backend (GET /api/safe-pick).
// Keep this as the single source of truth for MSW.
export const mockSafePickResponse = {
  date: '2026-04-21',
  safe_pick: {
    type: 'single' as const,
    fixture_id: 'fx-1',
    odds: 1.85,
    confidence: 0.58,
    market: '1X2',
    selection: 'home',
    kickoff_utc: '2026-04-21T19:00:00Z',
    league_id: 61,
    league_name: 'Ligue 1',
    home_team: 'PSG',
    away_team: 'Lens',
    sport: 'football',
    odds_source: 'real',
  },
  fallback_message: null,
};

export const mockSafePickEmptyResponse = {
  date: '2026-04-22',
  safe_pick: null,
  fallback_message: "Aucun pari Safe ne correspond aux critères aujourd'hui. Revenez demain.",
};

export const mockPerformance: PerformanceSummary = {
  roi30d: { value: 12.4, deltaVs7d: 0.8 },
  accuracy: { value: 54.2, deltaVs7d: -0.3 },
  brier7d: { value: 0.214, deltaVs7d: -0.002 },
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
    book_name: 'Betclic',
  },
  value_bets: [
    {
      market_key: '1x2.home',
      label: 'Victoire PSG @ Betclic',
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
    "Statistiquement, le scénario attendu est un PSG dominant la possession (~62%) avec un score probable 2-1 ou 3-1. La cote 1,85 sur la victoire domicile ressort avec un signal modèle de +7,6% face à notre probabilité de 58%.",
  ],
  generated_at: '2026-04-21T10:00:00Z',
  is_teaser: false,
};

export const mockAnalysisTeaser: AnalysisPayload = {
  paragraphs: [
    "Paris Saint-Germain reste sur 4 victoires consécutives à domicile avec un xG moyen de 2,3 et une défense solide (3 clean sheets sur les 5 derniers).",
  ],
  generated_at: '2026-04-21T10:00:00Z',
  is_teaser: true,
};

export const mockAnalysisById: Record<string, AnalysisPayload> = {
  'fx-1': mockAnalysisPsgLens,
  'fx-teaser': mockAnalysisTeaser,
};

// ---------------------------------------------------------------------------
// Lot 5 — public live track record.
// 90 synthetic points, ~+12.4% final ROI, gentle drawdown mid-window.
// ---------------------------------------------------------------------------
function buildRoiCurve(): Array<{ date: string; roi: number }> {
  const points: Array<{ date: string; roi: number }> = [];
  const start = Date.UTC(2026, 0, 22); // 2026-01-22
  for (let i = 0; i < 90; i += 1) {
    const t = start + i * 24 * 3600 * 1000;
    const date = new Date(t).toISOString().slice(0, 10);
    // Gentle logistic growth with a ~day 40 drawdown, final ~12.4%.
    const phase = (i - 40) / 22;
    const roi = 12.4 / (1 + Math.exp(-phase)) - (i > 35 && i < 50 ? 1.6 : 0);
    points.push({ date, roi: Number(roi.toFixed(2)) });
  }
  return points;
}

export const mockTrackRecordLive: TrackRecordLive = {
  clv30d: 2.1,
  roi90d: 12.4,
  brier30d: 0.208,
  safeRate90d: 71.8,
  roiCurve90d: buildRoiCurve(),
  lastUpdatedAt: '2026-04-22T09:30:00Z',
};

// -------------- Lot 5 Bloc B — Account (profile / subscription / invoices)

export const mockProfile: ProfileData = {
  email: 'demo@probalab.net',
  pseudo: 'demo',
  avatarUrl: undefined,
  role: 'premium',
  trialEnd: undefined,
};

export const mockSubscription: SubscriptionData = {
  plan: 'PREMIUM',
  status: 'active',
  renewsAt: '2026-05-21T00:00:00Z',
  cancelAtPeriodEnd: false,
  planName: 'Premium mensuel',
};

export const mockInvoices: Invoice[] = [
  {
    id: 'in_001',
    number: 'F-001',
    amountCents: 1499,
    currency: 'EUR',
    status: 'paid',
    issuedAt: '2026-04-01T00:00:00Z',
    pdfUrl: 'https://invoices.probalab.net/in_001.pdf',
  },
  {
    id: 'in_002',
    number: 'F-002',
    amountCents: 1499,
    currency: 'EUR',
    status: 'paid',
    issuedAt: '2026-03-01T00:00:00Z',
    pdfUrl: 'https://invoices.probalab.net/in_002.pdf',
  },
];

// ---------------------------------------------------------------------------
// Lot 5 Bloc C — Bankroll (summary, bets, ROI by market, settings)
// ---------------------------------------------------------------------------

export const mockBankroll: BankrollSummary = {
  current_balance: 1284,
  initial_balance: 1000,
  roi_30d: 12.4,
  roi_90d: 9.8,
  win_rate: 58.7,
  drawdown_max_pct: -4.2,
  kelly_fraction_active: 0.25,
  total_bets: 48,
  wins: 26,
  losses: 19,
  voids: 3,
};

export const mockBets: BetRow[] = [
  {
    id: 'bet-001',
    fixture_id: 'fx-1',
    match_title: 'PSG - Lens',
    market: '1X2',
    selection: 'Home',
    odds: 1.85,
    stake: 25,
    result: 'WIN',
    placed_at: '2026-04-19T10:00:00Z',
    resolved_at: '2026-04-19T21:00:00Z',
  },
  {
    id: 'bet-002',
    fixture_id: 'fx-2',
    match_title: 'Arsenal - Chelsea',
    market: 'O/U',
    selection: 'Over 2.5',
    odds: 1.92,
    stake: 30,
    result: 'WIN',
    placed_at: '2026-04-20T11:00:00Z',
    resolved_at: '2026-04-20T20:30:00Z',
  },
  {
    id: 'bet-003',
    fixture_id: 'fx-3',
    match_title: 'Inter - Milan',
    market: 'BTTS',
    selection: 'Yes',
    odds: 1.7,
    stake: 20,
    result: 'LOSS',
    placed_at: '2026-04-20T12:00:00Z',
    resolved_at: '2026-04-20T22:45:00Z',
  },
  {
    id: 'bet-004',
    fixture_id: 'fx-4',
    match_title: 'Bayern - Dortmund',
    market: '1X2',
    selection: 'Draw',
    odds: 3.4,
    stake: 15,
    result: 'LOSS',
    placed_at: '2026-04-21T09:00:00Z',
    resolved_at: '2026-04-21T20:30:00Z',
  },
  {
    id: 'bet-005',
    fixture_id: 'fx-5',
    match_title: 'OL - Rennes',
    market: 'DC',
    selection: '1X',
    odds: 1.4,
    stake: 40,
    result: 'PENDING',
    placed_at: '2026-04-22T08:00:00Z',
    resolved_at: null,
  },
  {
    id: 'bet-006',
    fixture_id: 'fx-6',
    match_title: 'Man City - Liverpool',
    market: 'Score',
    selection: '2-1',
    odds: 9.5,
    stake: 10,
    result: 'PENDING',
    placed_at: '2026-04-22T09:00:00Z',
    resolved_at: null,
  },
];

export const mockROIByMarket: ROIByMarketItem[] = [
  { market: '1X2', roi_pct: 14.2, n: 18, wins: 11, losses: 6, voids: 1 },
  { market: 'O/U', roi_pct: 8.5, n: 12, wins: 7, losses: 5, voids: 0 },
  { market: 'BTTS', roi_pct: 4.1, n: 8, wins: 4, losses: 4, voids: 0 },
  { market: 'DC', roi_pct: -1.8, n: 6, wins: 3, losses: 3, voids: 0 },
  { market: 'Score', roi_pct: -12.3, n: 4, wins: 1, losses: 3, voids: 0 },
];

export const mockBankrollSettings: BankrollSettings = {
  initialStake: 1000,
  kellyFraction: 0.25,
  stakeCapPct: 5,
};

// ---------------------------------------------------------------------------
// Lot 5 Bloc E — Notification channels + rules
// ---------------------------------------------------------------------------

export const mockNotificationChannels: NotificationChannelsStatus = {
  telegram: { connected: false },
  email: { verified: true, address: 'demo@probalab.net' },
  push: { subscribed: false, devices: 0 },
};

/**
 * Three exemplary rules covering the three main user intents :
 *  1. catch strong model signals (email + telegram).
 *  2. remind the user of the kick-off of today's Safe pick.
 *  3. surface a capital loss alert with a pause suggestion.
 */
export const mockNotificationRules: NotificationRule[] = [
  {
    id: 'rule-001',
    name: 'Signaux forts',
    conditions: [{ type: 'edge_min', value: 8 }],
    logic: 'AND',
    channels: ['email', 'telegram'],
    action: { notify: true, pauseSuggestion: false },
    enabled: true,
  },
  {
    id: 'rule-002',
    name: 'Safe du jour kick-off',
    conditions: [{ type: 'kickoff_within', value: 2 }],
    logic: 'AND',
    channels: ['push'],
    action: { notify: true, pauseSuggestion: false },
    enabled: true,
  },
  {
    id: 'rule-003',
    name: 'Baisse max critique',
    conditions: [{ type: 'bankroll_drawdown', value: 10 }],
    logic: 'AND',
    channels: ['email', 'telegram', 'push'],
    action: { notify: true, pauseSuggestion: true },
    enabled: false,
  },
];
