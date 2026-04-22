/**
 * Types pour la page Match Detail V2 (Lot 4).
 *
 * Ce fichier est partagé entre le Bloc A (types + hooks) et le Bloc B
 * (composants visuels) du Lot 4. Le Bloc B ajoute uniquement les types
 * strictement nécessaires à ses 5 composants ; le Bloc A complétera
 * ensuite avec les types restants (predictions, books, AI, etc.).
 */

import type { FixtureId } from './common';

/**
 * Résultat d'un match passé pour la forme récente d'une équipe.
 * W = Win, D = Draw, L = Loss.
 */
export type Outcome = 'W' | 'D' | 'L';

/**
 * Info d'une équipe dans le hero du match.
 */
export interface MatchHeaderTeam {
  id: number;
  name: string;
  logo_url: string;
  rank?: number;
  form: Outcome[];
}

/**
 * Header d'un match : infos factuelles (équipes, coup d'envoi, stade).
 */
export interface MatchHeader {
  fixture_id: FixtureId | number;
  kickoff_utc: string;
  stadium?: string;
  referee?: string;
  league_name: string;
  home: MatchHeaderTeam;
  away: MatchHeaderTeam;
}

/**
 * Stat comparative domicile vs extérieur sur les 5 derniers matchs.
 */
export interface ComparativeStat {
  label: string;
  home_value: number;
  away_value: number;
  unit?: string;
}

/**
 * Match passé dans l'historique H2H.
 */
export interface H2HPastMatch {
  date_utc: string;
  home_team: string;
  away_team: string;
  score: string;
  competition?: string;
}

/**
 * Résumé H2H (face-à-face) agrégé + 3 derniers matchs.
 */
export interface H2HSummary {
  home_wins: number;
  draws: number;
  away_wins: number;
  last_matches: H2HPastMatch[];
}

/**
 * Statut des compositions d'équipes avant le match.
 * - confirmed : compos officielles publiées (J-1 à J-60min)
 * - probable : compos prédites par l'algo, non officielles
 * - unavailable : aucune donnée disponible
 */
export type CompositionsStatus = 'confirmed' | 'probable' | 'unavailable';

/**
 * Joueur titulaire d'une compo de départ.
 */
export interface LineupPlayer {
  number: number;
  name: string;
  position: string;
}

/**
 * Composition d'une équipe (formation + onze de départ).
 */
export interface Lineup {
  formation: string; // ex: "4-3-3"
  starters: LineupPlayer[];
}

/**
 * Données de compositions pour les deux équipes.
 */
export interface CompositionsPayload {
  home: Lineup | null;
  away: Lineup | null;
  status: CompositionsStatus;
}

/**
 * Probabilité + value info sur un marché unique (1x2.home, btts.yes, etc.).
 */
export interface MarketProb {
  market_key: string;
  label: string;
  probability: number; // 0..1
  fair_odds: number;
  best_book_odds: number | null;
  is_value: boolean;
  edge: number | null; // 0..1
}

/**
 * Cote d'un bookmaker pour un marché donné.
 */
export interface BookOdd {
  bookmaker: string;
  odds: number;
  is_best: boolean;
  updated_at: string; // ISO 8601 UTC
}

/**
 * Recommandation principale (top value bet) servie dans la RecoCard.
 */
export interface Recommendation {
  market_key: string;
  market_label: string;
  odds: number;
  confidence: number; // 0..1
  kelly_fraction: number; // 0..1
  edge: number; // 0..1
  book_name: string;
}

/**
 * Ligne d'une value bet secondaire.
 */
export interface ValueBet {
  market_key: string;
  label: string;
  probability: number;
  best_odds: number;
  edge: number;
}

/**
 * Payload complet retourné par `GET /api/predictions/:fixture_id`.
 * Source unique consommée par la page MatchDetailV2.
 */
export interface MatchDetailPayload {
  header: MatchHeader;
  probs_1x2: { home: number; draw: number; away: number };
  stats: ComparativeStat[];
  h2h: H2HSummary;
  compositions: CompositionsPayload;
  all_markets: MarketProb[];
  recommendation: Recommendation | null;
  value_bets: ValueBet[];
}

/**
 * Payload retourné par `GET /api/analysis/:fixture_id` (analyse IA Gemini).
 * `is_teaser = true` quand l'utilisateur free post-trial ne voit qu'un paragraphe.
 */
export interface AnalysisPayload {
  paragraphs: string[];
  generated_at: string; // ISO 8601 UTC
  is_teaser?: boolean;
}

/**
 * Entrée d'un bookmaker dans la comparaison de cotes.
 */
export interface OddsComparisonEntry {
  bookmaker: string;
  odds: number;
  is_best: boolean;
  updated_at: string; // ISO 8601 UTC
}

/**
 * Payload retourné par `GET /api/odds/:fixture_id/comparison`.
 */
export interface OddsComparisonResponse {
  fixture_id: FixtureId;
  market_key: string;
  books: OddsComparisonEntry[];
}

/**
 * Payload retourné par `GET /api/markets/:fixture_id`.
 */
export interface AllMarketsResponse {
  fixture_id: FixtureId;
  markets: MarketProb[];
}

/**
 * Requête `POST /api/user/bets` (ajout à la bankroll).
 */
export interface AddBetRequest {
  fixture_id: FixtureId;
  market_key: string;
  odds: number;
  stake: number;
}

/**
 * Réponse `POST /api/user/bets` (pari confirmé).
 */
export interface AddBetResponse {
  id: string;
  fixture_id: FixtureId;
  market_key: string;
  odds: number;
  stake: number;
  placed_at: string; // ISO 8601 UTC
}
