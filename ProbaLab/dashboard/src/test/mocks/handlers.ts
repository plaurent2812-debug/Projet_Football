import { http, HttpResponse } from 'msw';
import type { Sport } from '@/types/v2/matches';
import type { AddBetRequest, AddBetResponse } from '@/types/v2/match-detail';
import type { ProfileData, UpdateProfileInput, ChangePasswordInput } from '@/hooks/v2/useProfile';
import type { BankrollSettings } from '@/lib/v2/schemas';
import type {
  AddBetPayload,
  BetRow,
  UpdateBetPayload,
} from '@/hooks/v2/useBankrollBets';
import type { NotificationRule } from '@/lib/v2/schemas/rules';
import type { CreateRuleInput } from '@/hooks/v2/useNotificationRules';
import {
  mockMatchesBackendResponse,
  mockPerformance,
  mockSafePickResponse,
  mockSafePickEmptyResponse,
  mockMatchDetailById,
  mockAnalysisById,
  mockTrackRecordLive,
  mockProfile,
  mockSubscription,
  mockInvoices,
  mockBankroll,
  mockBets,
  mockROIByMarket,
  mockBankrollSettings,
  mockNotificationChannels,
  mockNotificationRules,
} from './fixtures';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const handlers = [
  http.get(`${API}/api/safe-pick`, ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get('date') === '2026-04-22-empty') {
      return HttpResponse.json(mockSafePickEmptyResponse);
    }
    return HttpResponse.json(mockSafePickResponse);
  }),

  // Returns the real backend shape (grouped by league, snake_case) — the
  // `useMatchesOfDay` hook owns the flattening + camelCase adaptation.
  http.get(`${API}/api/matches`, ({ request }) => {
    const url = new URL(request.url);
    const sports = url.searchParams.get('sports')?.split(',').filter(Boolean);
    const valueOnly = url.searchParams.get('value_only') === 'true';

    // Apply filters at the group level. Each group may or may not match
    // the requested sports / value-only filter; empty groups are dropped.
    const filteredGroups = mockMatchesBackendResponse.groups
      .map((g) => {
        let matches = g.matches;
        if (sports && sports.length) {
          const allowed = new Set<Sport>(sports as Sport[]);
          matches = matches.filter((m) => allowed.has(m.sport));
        }
        if (valueOnly) {
          matches = matches.filter((m) => (m.signals ?? []).includes('value'));
        }
        return { ...g, matches };
      })
      .filter((g) => g.matches.length > 0);

    const total = filteredGroups.reduce((acc, g) => acc + g.matches.length, 0);

    return HttpResponse.json({
      date: url.searchParams.get('date') ?? mockMatchesBackendResponse.date,
      total,
      groups: filteredGroups,
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

  // Lot 5 — Public live track record (no auth)
  http.get(`${API}/api/public/track-record/live`, () =>
    HttpResponse.json(mockTrackRecordLive),
  ),

  // Lot 5 Bloc B — Account profile
  http.get(`${API}/api/user/profile`, () => HttpResponse.json(mockProfile)),

  http.patch(`${API}/api/user/profile`, async ({ request }) => {
    const body = (await request.json()) as UpdateProfileInput;
    const updated: ProfileData = {
      ...mockProfile,
      ...(body.pseudo !== undefined ? { pseudo: body.pseudo } : {}),
      ...(body.avatarUrl !== undefined ? { avatarUrl: body.avatarUrl } : {}),
      ...(body.email !== undefined ? { email: body.email } : {}),
    };
    return HttpResponse.json(updated);
  }),

  http.post(`${API}/api/user/profile/password`, async ({ request }) => {
    const body = (await request.json()) as ChangePasswordInput;
    if (!body?.current || !body?.next || body.next.length < 8) {
      return HttpResponse.json({ error: 'invalid_payload' }, { status: 400 });
    }
    return HttpResponse.json({ ok: true });
  }),

  http.delete(`${API}/api/user/profile`, () => new HttpResponse(null, { status: 204 })),

  // Lot 5 Bloc B — Account subscription + invoices
  http.get(`${API}/api/user/subscription`, () => HttpResponse.json(mockSubscription)),

  http.get(`${API}/api/user/invoices`, () => HttpResponse.json(mockInvoices)),

  // Add a bet to the user bankroll. Accepts two shapes:
  //   - Lot 4 legacy: `{ fixture_id, market_key, odds, stake }` (predictions CTA)
  //   - Lot 5 Bloc C: `{ fixture_id, match_title, market, selection, odds, stake, placed_at }` (bankroll page)
  http.post(`${API}/api/user/bets`, async ({ request }) => {
    const body = (await request.json()) as Partial<AddBetRequest & AddBetPayload>;
    if (!body || typeof body.stake !== 'number' || body.stake <= 0) {
      return HttpResponse.json({ error: 'invalid_stake' }, { status: 400 });
    }
    if (!body.fixture_id || typeof body.odds !== 'number') {
      return HttpResponse.json({ error: 'invalid_payload' }, { status: 400 });
    }
    // Lot 5 Bloc C shape — richer payload.
    if (typeof body.market === 'string' && typeof body.selection === 'string') {
      const response: BetRow = {
        id: `bet-new-${body.fixture_id}`,
        fixture_id: body.fixture_id,
        match_title: body.match_title ?? '',
        market: body.market,
        selection: body.selection,
        odds: body.odds,
        stake: body.stake,
        result: 'PENDING',
        placed_at: body.placed_at ?? '2026-04-22T10:00:00Z',
        resolved_at: null,
      };
      return HttpResponse.json(response, { status: 201 });
    }
    // Lot 4 legacy shape.
    if (typeof body.market_key !== 'string') {
      return HttpResponse.json({ error: 'invalid_payload' }, { status: 400 });
    }
    const legacy: AddBetResponse = {
      id: `bet_${body.fixture_id}_${body.market_key}`,
      fixture_id: body.fixture_id,
      market_key: body.market_key,
      odds: body.odds,
      stake: body.stake,
      placed_at: '2026-04-22T10:00:00Z',
    };
    return HttpResponse.json(legacy, { status: 201 });
  }),

  // Lot 5 Bloc C — Bankroll summary / bets / ROI by market / settings
  http.get(`${API}/api/user/bankroll`, () => HttpResponse.json(mockBankroll)),

  http.get(`${API}/api/user/bets`, ({ request }) => {
    const url = new URL(request.url);
    const filter = url.searchParams.get('filter') ?? 'all';
    let rows: BetRow[] = mockBets;
    if (filter === 'won') rows = mockBets.filter((b) => b.result === 'WIN');
    else if (filter === 'lost') rows = mockBets.filter((b) => b.result === 'LOSS');
    else if (filter === 'pending') rows = mockBets.filter((b) => b.result === 'PENDING');
    return HttpResponse.json(rows);
  }),

  http.patch(`${API}/api/user/bets/:id`, async ({ params, request }) => {
    const id = String(params.id);
    const body = (await request.json()) as UpdateBetPayload;
    const existing = mockBets.find((b) => b.id === id);
    if (!existing) {
      // Keep a sensible echo so tests can assert the merged shape.
      return HttpResponse.json({
        id,
        fixture_id: 'fx-unknown',
        match_title: '',
        market: '',
        selection: '',
        odds: 0,
        stake: 0,
        result: body.result,
        placed_at: '2026-04-22T10:00:00Z',
        resolved_at: body.resolved_at ?? null,
      } satisfies BetRow);
    }
    return HttpResponse.json({
      ...existing,
      result: body.result,
      resolved_at: body.resolved_at ?? existing.resolved_at,
    } satisfies BetRow);
  }),

  http.delete(`${API}/api/user/bets/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/api/user/bankroll/roi-by-market`, () =>
    HttpResponse.json(mockROIByMarket),
  ),

  http.get(`${API}/api/user/bankroll/settings`, () =>
    HttpResponse.json(mockBankrollSettings),
  ),

  http.put(`${API}/api/user/bankroll/settings`, async ({ request }) => {
    const body = (await request.json()) as BankrollSettings;
    if (![0.1, 0.25, 0.5].includes(body.kellyFraction)) {
      return HttpResponse.json({ error: 'invalid_fraction' }, { status: 400 });
    }
    if (body.stakeCapPct < 0.5 || body.stakeCapPct > 25) {
      return HttpResponse.json({ error: 'invalid_cap' }, { status: 400 });
    }
    if (body.initialStake <= 0) {
      return HttpResponse.json({ error: 'invalid_stake' }, { status: 400 });
    }
    return HttpResponse.json(body);
  }),

  // Lot 5 Bloc E — Notification channels + push subscription.
  http.post(`${API}/api/user/notifications/push/subscribe`, () =>
    HttpResponse.json({ ok: true }),
  ),

  http.delete(`${API}/api/user/notifications/push/unsubscribe`, () =>
    new HttpResponse(null, { status: 204 }),
  ),

  // Channels status (telegram / email / push)
  http.get(`${API}/api/user/notifications/channels`, () =>
    HttpResponse.json(mockNotificationChannels),
  ),

  // Rules CRUD
  http.get(`${API}/api/user/notifications/rules`, () =>
    HttpResponse.json(mockNotificationRules),
  ),

  http.post(`${API}/api/user/notifications/rules`, async ({ request }) => {
    const body = (await request.json()) as CreateRuleInput;
    if (!body?.name || body.name.trim().length === 0) {
      return HttpResponse.json({ error: 'invalid_name' }, { status: 400 });
    }
    const created: NotificationRule = {
      ...body,
      id: `rule-${Math.random().toString(36).slice(2, 8)}`,
    };
    return HttpResponse.json(created, { status: 201 });
  }),

  http.put(
    `${API}/api/user/notifications/rules/:id`,
    async ({ request, params }) => {
      const body = (await request.json()) as NotificationRule;
      const updated: NotificationRule = {
        ...body,
        id: String(params.id),
      };
      return HttpResponse.json(updated);
    },
  ),

  http.patch(
    `${API}/api/user/notifications/rules/:id`,
    async ({ request, params }) => {
      const body = (await request.json()) as Partial<NotificationRule>;
      const existing = mockNotificationRules.find(
        (r) => r.id === String(params.id),
      );
      const base: NotificationRule = existing ?? {
        id: String(params.id),
        name: 'unknown',
        conditions: [{ type: 'edge_min', value: 5 }],
        logic: 'AND',
        channels: ['email'],
        action: { notify: true, pauseSuggestion: false },
        enabled: true,
      };
      return HttpResponse.json({
        ...base,
        ...body,
        id: String(params.id),
      } satisfies NotificationRule);
    },
  ),

  http.delete(`${API}/api/user/notifications/rules/:id`, () =>
    new HttpResponse(null, { status: 204 }),
  ),

  // Telegram connect flow
  http.post(`${API}/api/user/notifications/telegram/connect-start`, () => {
    const token = Math.random().toString(36).slice(2, 12).toUpperCase();
    return HttpResponse.json({
      token,
      bot_url: `https://t.me/probalab_bot?start=${token}`,
    });
  }),

  http.delete(`${API}/api/user/notifications/telegram`, () =>
    new HttpResponse(null, { status: 204 }),
  ),
];
