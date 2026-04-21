import { http, HttpResponse } from 'msw';
import type { Sport } from '@/types/v2/matches';
import type { AddBetRequest, AddBetResponse } from '@/types/v2/match-detail';
import {
  mockMatches,
  mockPerformance,
  mockSafePick,
  mockMatchDetailById,
  mockAnalysisById,
} from './fixtures';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const handlers = [
  http.get(`${API}/api/safe-pick`, () => HttpResponse.json(mockSafePick)),

  http.get(`${API}/api/matches`, ({ request }) => {
    const url = new URL(request.url);
    const sports = url.searchParams.get('sports')?.split(',').filter(Boolean);
    const valueOnly = url.searchParams.get('value_only') === 'true';

    let matches = mockMatches;
    if (sports && sports.length) {
      const allowed = new Set<Sport>(sports as Sport[]);
      matches = matches.filter((m) => allowed.has(m.sport));
    }
    if (valueOnly) {
      matches = matches.filter((m) => m.signals.includes('value'));
    }

    const bySport: Record<Sport, number> = {
      football: matches.filter((m) => m.sport === 'football').length,
      nhl: matches.filter((m) => m.sport === 'nhl').length,
    };

    const byLeague = matches.reduce<Record<string, number>>((acc, m) => {
      acc[m.league.id] = (acc[m.league.id] ?? 0) + 1;
      return acc;
    }, {});

    return HttpResponse.json({
      date: url.searchParams.get('date') ?? '2026-04-21',
      matches,
      counts: {
        total: matches.length,
        bySport,
        byLeague,
      },
    });
  }),

  http.get(`${API}/api/performance/summary`, () => HttpResponse.json(mockPerformance)),

  // Lot 4 — Match detail (predictions)
  http.get(`${API}/api/predictions/:fixtureId`, ({ params }) => {
    const fixtureId = String(params.fixtureId);
    const payload = mockMatchDetailById[fixtureId];
    if (!payload) {
      return HttpResponse.json({ error: 'fixture_not_found' }, { status: 404 });
    }
    return HttpResponse.json(payload);
  }),

  // Lot 4 — IA analysis (Gemini paragraphs)
  http.get(`${API}/api/analysis/:fixtureId`, ({ params }) => {
    const fixtureId = String(params.fixtureId);
    const payload = mockAnalysisById[fixtureId];
    if (!payload) {
      return HttpResponse.json({ error: 'analysis_not_found' }, { status: 404 });
    }
    return HttpResponse.json(payload);
  }),

  // Lot 4 — Add a bet to the user bankroll
  http.post(`${API}/api/user/bets`, async ({ request }) => {
    const body = (await request.json()) as AddBetRequest;
    if (!body || typeof body.stake !== 'number' || body.stake <= 0) {
      return HttpResponse.json({ error: 'invalid_stake' }, { status: 400 });
    }
    if (!body.fixture_id || !body.market_key || typeof body.odds !== 'number') {
      return HttpResponse.json({ error: 'invalid_payload' }, { status: 400 });
    }
    const response: AddBetResponse = {
      id: `bet_${body.fixture_id}_${body.market_key}`,
      fixture_id: body.fixture_id,
      market_key: body.market_key,
      odds: body.odds,
      stake: body.stake,
      placed_at: '2026-04-22T10:00:00Z',
    };
    return HttpResponse.json(response, { status: 201 });
  }),
];
