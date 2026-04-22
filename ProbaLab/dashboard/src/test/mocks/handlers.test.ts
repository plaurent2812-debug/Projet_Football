import { describe, it, expect } from 'vitest';
import type { MatchesResponse, SafePick } from '@/types/v2/matches';
import type { PerformanceSummary } from '@/types/v2/performance';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

describe('MSW handlers', () => {
  it('GET /api/safe-pick returns a SafePick shape', async () => {
    const res = await fetch(`${API}/api/safe-pick?date=2026-04-21`);
    expect(res.status).toBe(200);
    const data = (await res.json()) as SafePick;
    expect(data.betLabel).toBe('PSG gagne vs Lens');
    expect(data.odd).toBeGreaterThan(1);
    expect(data.probability).toBeGreaterThan(0);
    expect(data.probability).toBeLessThanOrEqual(1);
  });

  it('GET /api/matches returns matches + counts', async () => {
    const res = await fetch(`${API}/api/matches?date=2026-04-21`);
    const data = (await res.json()) as MatchesResponse;
    expect(data.matches).toHaveLength(3);
    expect(data.counts.total).toBe(3);
    expect(data.counts.bySport.football).toBe(3);
  });

  it('GET /api/matches?value_only=true filters to value signals', async () => {
    const res = await fetch(`${API}/api/matches?date=2026-04-21&value_only=true`);
    const data = (await res.json()) as MatchesResponse;
    expect(data.matches.length).toBeGreaterThan(0);
    expect(data.matches.every((m) => m.signals.includes('value'))).toBe(true);
  });

  it('GET /api/performance/summary returns KPIs', async () => {
    const res = await fetch(`${API}/api/performance/summary?window=30`);
    const data = (await res.json()) as PerformanceSummary;
    expect(data.roi30d.value).toBeCloseTo(12.4);
    expect(data.bankroll.currency).toBe('EUR');
  });
});
