import { z } from 'zod';

/**
 * Allowed condition types for the notification rules builder.
 * Keep in sync with the backend validator.
 */
export const conditionTypeEnum = z.enum([
  'edge_min',
  'league_in',
  'sport',
  'confidence',
  'kickoff_within',
  'bankroll_drawdown',
]);
export type ConditionType = z.infer<typeof conditionTypeEnum>;

/**
 * Discriminated union — each condition type has its own `value` shape.
 * This gives us both compile-time type narrowing and precise runtime errors.
 */
export const ruleConditionSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('edge_min'), value: z.number().min(0).max(100) }),
  z.object({ type: z.literal('league_in'), value: z.array(z.string()).min(1) }),
  z.object({ type: z.literal('sport'), value: z.enum(['football', 'nhl']) }),
  z.object({ type: z.literal('confidence'), value: z.enum(['LOW', 'MED', 'HIGH']) }),
  z.object({ type: z.literal('kickoff_within'), value: z.number().int().min(1).max(168) }),
  z.object({ type: z.literal('bankroll_drawdown'), value: z.number().min(0).max(100) }),
]);
export type RuleCondition = z.infer<typeof ruleConditionSchema>;

export const ruleChannelSchema = z.enum(['email', 'telegram', 'push']);
export type RuleChannel = z.infer<typeof ruleChannelSchema>;

/**
 * Actions taken when a rule triggers. `pauseSuggestion` is surfaced to the
 * user as a suggestion — it never automatically pauses any subscription.
 */
export const ruleActionSchema = z.object({
  notify: z.boolean(),
  pauseSuggestion: z.boolean(),
});
export type RuleAction = z.infer<typeof ruleActionSchema>;

/**
 * Top-level rule schema consumed by the rules builder modal + list.
 * Minimum 1, maximum 3 conditions keep the UI composable and the backend
 * predicate evaluator bounded.
 */
export const notificationRuleSchema = z.object({
  id: z.string().optional(),
  name: z.string().min(1, 'Nom requis').max(60, 'Nom trop long (max 60)'),
  conditions: z.array(ruleConditionSchema).min(1, 'Au moins 1 condition').max(3, 'Max 3 conditions'),
  logic: z.enum(['AND', 'OR']),
  channels: z.array(ruleChannelSchema).min(1, 'Au moins 1 canal'),
  action: ruleActionSchema,
  enabled: z.boolean(),
});
export type NotificationRule = z.infer<typeof notificationRuleSchema>;
