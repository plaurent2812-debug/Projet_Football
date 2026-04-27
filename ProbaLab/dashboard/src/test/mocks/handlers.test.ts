import { describe, it, expect } from 'vitest';
import type { PerformanceSummary } from '@/types/v2/performance';

// Backend shape for /api/matches — grouped by league, snake_case. Inline here
// to keep the test self-documenting (the real type lives inside useMatchesOfDay).
interface BackendMatchRow {
  fixture_id: string;
  sport: 'football' | 'nhl';
  signals?: string[];
}
interface BackendMatchesResponse {
  date: string;
  total: number;
  groups: Array<{ league_id: number | string; league_name: string; matches: BackendMatchRow[] }>;
}

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

describe('MSW handlers', () => {
  it('GET /api/safe-pick returns the backend wrapper shape', async () => {
    const res = await fetch(`${API}/api/safe-pick?date=2026-04-21`);
    expect(res.status).toBe(200);
    // Handler now returns the real backend wrapper shape {date, safe_pick, fallback_message}.
    const data = await res.json() as { date: string; safe_pick: { odds: number; confidence: number } | null; fallback_message: string | null };
    expect(data.date).toBe('2026-04-21');
    expect(data.safe_pick).not.toBeNull();
    expect(data.safe_pick!.odds).toBeGreaterThan(1);
    expect(data.safe_pick!.confidence).toBeGreaterThan(0);
    expect(data.safe_pick!.confidence).toBeLessThanOrEqual(1);
  });

  it('GET /api/matches returns backend-shaped groups + total', async () => {
    const res = await fetch(`${API}/api/matches?date=2026-04-21`);
    const data = (await res.json()) as BackendMatchesResponse;
    expect(data.total).toBe(3);
    const flat = data.groups.flatMap((g) => g.matches);
    expect(flat).toHaveLength(3);
    expect(flat.every((m) => m.sport === 'football')).toBe(true);
  });

  it('GET /api/matches?value_only=true filters to value signals', async () => {
    const res = await fetch(`${API}/api/matches?date=2026-04-21&value_only=true`);
    const data = (await res.json()) as BackendMatchesResponse;
    const flat = data.groups.flatMap((g) => g.matches);
    expect(flat.length).toBeGreaterThan(0);
    expect(flat.every((m) => (m.signals ?? []).includes('value'))).toBe(true);
  });

  it('GET /api/performance/summary returns KPIs', async () => {
    const res = await fetch(`${API}/api/performance/summary?window=30`);
    const data = (await res.json()) as PerformanceSummary;
    expect(data.roi30d.value).toBeCloseTo(12.4);
    expect(data.bankroll.currency).toBe('EUR');
  });
});
