/**
 * Types partagés V2.
 * Source de vérité pour tous les composants V2.
 */

/**
 * fixture_id est TEXT côté DB (lesson 48).
 * Jamais typé en `number` côté frontend.
 */
export type FixtureId = string;

export type UserRole = 'visitor' | 'free' | 'trial' | 'premium' | 'admin';

export type Sport = 'football' | 'nhl';

export type SubscriptionStatus =
  | 'active'
  | 'trialing'
  | 'past_due'
  | 'canceled'
  | 'incomplete'
  | 'none';

export type League =
  | 'L1'
  | 'L2'
  | 'PL'
  | 'LaLiga'
  | 'SerieA'
  | 'Bundesliga'
  | 'UCL'
  | 'UEL'
  | 'NHL';

export interface ProbTriplet {
  home: number;
  draw: number;
  away: number;
}

export interface Bookmaker {
  name: string;
  odds: number;
  url?: string;
}

export interface MoneyAmount {
  amount: number;
  currency: 'EUR';
}
