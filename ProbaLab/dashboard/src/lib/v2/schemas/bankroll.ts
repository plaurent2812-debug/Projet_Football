import { z } from 'zod';

/**
 * Bankroll settings form schema.
 *
 * - `kellyFraction` : only the three sanctioned fractional-Kelly values are
 *   allowed. Fractional-Kelly beyond 0.5 is unsafe; below 0.1 is noise.
 * - `stakeCapPct`   : hard cap 25% per bet, floor 0.5%.
 */
export const bankrollSettingsSchema = z.object({
  initialStake: z.number().positive('Mise initiale strictement positive'),
  kellyFraction: z.union([z.literal(0.1), z.literal(0.25), z.literal(0.5)]),
  stakeCapPct: z
    .number()
    .min(0.5, 'Plancher 0,5%')
    .max(25, 'Plafond 25%'),
});
export type BankrollSettings = z.infer<typeof bankrollSettingsSchema>;
