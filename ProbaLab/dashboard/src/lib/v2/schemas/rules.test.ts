import { describe, it, expect } from 'vitest';
import {
  ruleConditionSchema,
  ruleChannelSchema,
  notificationRuleSchema,
  ruleActionSchema,
} from './rules';

describe('ruleConditionSchema', () => {
  it('accepts edge_min with positive number', () => {
    expect(ruleConditionSchema.safeParse({ type: 'edge_min', value: 5 }).success).toBe(true);
  });

  it('accepts league_in with a non-empty string array', () => {
    const r = ruleConditionSchema.safeParse({
      type: 'league_in',
      value: ['L1', 'PL'],
    });
    expect(r.success).toBe(true);
  });

  it('accepts sport with football or nhl', () => {
    expect(ruleConditionSchema.safeParse({ type: 'sport', value: 'football' }).success).toBe(true);
    expect(ruleConditionSchema.safeParse({ type: 'sport', value: 'nhl' }).success).toBe(true);
  });

  it('accepts confidence with HIGH', () => {
    expect(
      ruleConditionSchema.safeParse({ type: 'confidence', value: 'HIGH' }).success,
    ).toBe(true);
  });

  it('rejects edge_min with string value', () => {
    expect(ruleConditionSchema.safeParse({ type: 'edge_min', value: 'foo' }).success).toBe(false);
  });

  it('rejects league_in with empty array', () => {
    expect(ruleConditionSchema.safeParse({ type: 'league_in', value: [] }).success).toBe(false);
  });

  it('rejects unknown type', () => {
    expect(ruleConditionSchema.safeParse({ type: 'xyz', value: 1 }).success).toBe(false);
  });

  it('rejects kickoff_within over 168h', () => {
    expect(
      ruleConditionSchema.safeParse({ type: 'kickoff_within', value: 200 }).success,
    ).toBe(false);
  });
});

describe('ruleChannelSchema', () => {
  it('accepts email / telegram / push', () => {
    expect(ruleChannelSchema.safeParse('email').success).toBe(true);
    expect(ruleChannelSchema.safeParse('telegram').success).toBe(true);
    expect(ruleChannelSchema.safeParse('push').success).toBe(true);
  });

  it('rejects unknown channel', () => {
    expect(ruleChannelSchema.safeParse('sms').success).toBe(false);
  });
});

describe('ruleActionSchema', () => {
  it('accepts notify + pause suggestion flags', () => {
    expect(ruleActionSchema.safeParse({ notify: true, pauseSuggestion: false }).success).toBe(
      true,
    );
  });

  it('rejects non-boolean fields', () => {
    expect(
      ruleActionSchema.safeParse({ notify: 'yes', pauseSuggestion: false }).success,
    ).toBe(false);
  });
});

describe('notificationRuleSchema', () => {
  const base = {
    name: 'Value bets L1',
    conditions: [{ type: 'edge_min' as const, value: 5 }],
    logic: 'AND' as const,
    channels: ['email' as const],
    action: { notify: true, pauseSuggestion: false },
    enabled: true,
  };

  it('accepts a minimal valid rule', () => {
    expect(notificationRuleSchema.safeParse(base).success).toBe(true);
  });

  it('accepts up to 3 conditions', () => {
    const r = notificationRuleSchema.safeParse({
      ...base,
      conditions: [
        { type: 'edge_min', value: 5 },
        { type: 'league_in', value: ['L1'] },
        { type: 'confidence', value: 'HIGH' },
      ],
    });
    expect(r.success).toBe(true);
  });

  it('rejects empty name', () => {
    expect(notificationRuleSchema.safeParse({ ...base, name: '' }).success).toBe(false);
  });

  it('rejects more than 60 chars name', () => {
    expect(
      notificationRuleSchema.safeParse({ ...base, name: 'x'.repeat(61) }).success,
    ).toBe(false);
  });

  it('rejects 0 conditions', () => {
    expect(notificationRuleSchema.safeParse({ ...base, conditions: [] }).success).toBe(false);
  });

  it('rejects more than 3 conditions', () => {
    const many = Array(4).fill({ type: 'edge_min' as const, value: 5 });
    expect(
      notificationRuleSchema.safeParse({ ...base, conditions: many }).success,
    ).toBe(false);
  });

  it('rejects empty channels array', () => {
    expect(notificationRuleSchema.safeParse({ ...base, channels: [] }).success).toBe(false);
  });

  it('rejects unknown logic', () => {
    expect(
      notificationRuleSchema.safeParse({ ...base, logic: 'XOR' }).success,
    ).toBe(false);
  });
});
