import { z } from 'zod';

export const betStatusEnum = z.enum(['WIN', 'LOSS', 'PENDING', 'VOID']);
export type BetStatus = z.infer<typeof betStatusEnum>;

/**
 * Payload used when adding a bet to the user bankroll.
 *
 * Odds and stake boundaries mirror the backend validators.
 */
export const addBetSchema = z.object({
  fixtureLabel: z.string().min(1, 'Match requis'),
  market: z.string().min(1, 'Marché requis'),
  pick: z.string().min(1, 'Sélection requise'),
  odds: z.number().min(1.01, 'Cote minimale 1.01').max(1000, 'Cote maximale 1000'),
  stake: z.number().positive('Mise strictement positive'),
  placedAt: z.string().datetime('Date ISO UTC attendue'),
});
export type AddBet = z.infer<typeof addBetSchema>;

/**
 * Update payload for an existing bet. Only status + settlement timestamp
 * can be changed client-side. `settledAt` is required only when the
 * status transitions to WIN / LOSS / VOID — we leave that enforcement
 * to the backend to keep this schema composable on partial updates.
 */
export const updateBetSchema = z.object({
  status: betStatusEnum,
  settledAt: z.string().datetime('Date ISO UTC attendue').optional(),
});
export type UpdateBet = z.infer<typeof updateBetSchema>;
