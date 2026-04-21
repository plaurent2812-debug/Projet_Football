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
