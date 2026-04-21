import { http, HttpResponse } from 'msw';
import type { Sport } from '@/types/v2/matches';
import {
  mockMatches,
  mockPerformance,
  mockSafePick,
  mockMatchDetailById,
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
];
