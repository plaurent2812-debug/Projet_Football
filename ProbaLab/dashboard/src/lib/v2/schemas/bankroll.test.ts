import { describe, it, expect } from 'vitest';
import { bankrollSettingsSchema } from './bankroll';

describe('bankrollSettingsSchema', () => {
  const base = {
    initialStake: 1000,
    kellyFraction: 0.25,
    stakeCapPct: 5,
  } as const;

  it('accepts 0.1 / 0.25 / 0.5 kelly fractions', () => {
    expect(
      bankrollSettingsSchema.safeParse({ ...base, kellyFraction: 0.1 }).success,
    ).toBe(true);
    expect(
      bankrollSettingsSchema.safeParse({ ...base, kellyFraction: 0.25 }).success,
    ).toBe(true);
    expect(
      bankrollSettingsSchema.safeParse({ ...base, kellyFraction: 0.5 }).success,
    ).toBe(true);
  });

  it('rejects kelly not in allowed values', () => {
    expect(
      bankrollSettingsSchema.safeParse({ ...base, kellyFraction: 0.33 }).success,
    ).toBe(false);
  });

  it('rejects stakeCapPct above 25', () => {
    expect(
      bankrollSettingsSchema.safeParse({ ...base, stakeCapPct: 30 }).success,
    ).toBe(false);
  });

  it('rejects stakeCapPct below 0.5', () => {
    expect(
      bankrollSettingsSchema.safeParse({ ...base, stakeCapPct: 0.1 }).success,
    ).toBe(false);
  });

  it('rejects negative initial stake', () => {
    expect(
      bankrollSettingsSchema.safeParse({ ...base, initialStake: -100 }).success,
    ).toBe(false);
  });

  it('rejects zero initial stake', () => {
    expect(
      bankrollSettingsSchema.safeParse({ ...base, initialStake: 0 }).success,
    ).toBe(false);
  });
});
