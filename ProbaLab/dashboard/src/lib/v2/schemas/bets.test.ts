import { describe, it, expect } from 'vitest';
import { addBetSchema, updateBetSchema, betStatusEnum } from './bets';

describe('betStatusEnum', () => {
  it('accepts WIN / LOSS / PENDING / VOID', () => {
    expect(betStatusEnum.safeParse('WIN').success).toBe(true);
    expect(betStatusEnum.safeParse('LOSS').success).toBe(true);
    expect(betStatusEnum.safeParse('PENDING').success).toBe(true);
    expect(betStatusEnum.safeParse('VOID').success).toBe(true);
  });

  it('rejects unknown status', () => {
    expect(betStatusEnum.safeParse('DRAW').success).toBe(false);
  });
});

describe('addBetSchema', () => {
  const base = {
    fixtureLabel: 'PSG - OM',
    market: '1X2',
    pick: 'Home',
    odds: 1.85,
    stake: 25,
    placedAt: '2026-04-21T10:00:00Z',
  };

  it('accepts a valid bet', () => {
    expect(addBetSchema.safeParse(base).success).toBe(true);
  });

  it('rejects odds strictly lower than 1.01', () => {
    expect(addBetSchema.safeParse({ ...base, odds: 1.0 }).success).toBe(false);
  });

  it('rejects odds above 1000', () => {
    expect(addBetSchema.safeParse({ ...base, odds: 1001 }).success).toBe(false);
  });

  it('rejects zero or negative stake', () => {
    expect(addBetSchema.safeParse({ ...base, stake: 0 }).success).toBe(false);
    expect(addBetSchema.safeParse({ ...base, stake: -5 }).success).toBe(false);
  });

  it('rejects empty fixtureLabel / market / pick', () => {
    expect(addBetSchema.safeParse({ ...base, fixtureLabel: '' }).success).toBe(false);
    expect(addBetSchema.safeParse({ ...base, market: '' }).success).toBe(false);
    expect(addBetSchema.safeParse({ ...base, pick: '' }).success).toBe(false);
  });

  it('rejects invalid ISO datetime', () => {
    expect(addBetSchema.safeParse({ ...base, placedAt: '2026/04/21' }).success).toBe(false);
  });
});

describe('updateBetSchema', () => {
  it('accepts status-only payload', () => {
    const res = updateBetSchema.safeParse({ status: 'WIN' });
    expect(res.success).toBe(true);
  });

  it('accepts status + settledAt', () => {
    const res = updateBetSchema.safeParse({
      status: 'LOSS',
      settledAt: '2026-04-22T15:00:00Z',
    });
    expect(res.success).toBe(true);
  });

  it('rejects invalid status', () => {
    expect(updateBetSchema.safeParse({ status: 'MAYBE' }).success).toBe(false);
  });
});
