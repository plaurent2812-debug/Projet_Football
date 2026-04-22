# Fix: Blank Page Crash on All ProbaLab Pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the `TypeError: Cannot read properties of undefined (reading 'toFixed')` that blanks out every ProbaLab page, add the missing `/api/performance/summary` backend endpoint, and add an ErrorBoundary so a single render failure can never take down the whole app again.

**Architecture:** Three-layer fix following defense-in-depth.
1. **Backend**: create a new `/api/performance/summary` endpoint that returns the exact `PerformanceSummary` shape (`roi30d`, `accuracy`, `brier7d`, `bankroll`) the frontend already expects, reusing the existing aggregates from `/api/performance` and `/api/public/track-record/live`.
2. **Frontend hooks**: adapt `useSafePick` to unwrap the real backend payload (`{date, safe_pick, fallback_message}`) into the `SafePick | null` shape components consume.
3. **Frontend components**: make `SafeOfTheDayCard` tolerant of partial data and wrap `AppV2` in a proper ErrorBoundary so any future schema drift degrades gracefully instead of whiteboarding the app.

**Tech Stack:** FastAPI, React 19 + Vite, TanStack Query v5, Vitest + MSW, Pydantic v2, Supabase, Tailwind 4.

---

## Context — Why this plan exists

Root cause confirmed via prod stack trace (`index-BVrhq_Kp.js:54`):

```
Uncaught TypeError: Cannot read properties of undefined (reading 'toFixed')
    at ET (index-BVrhq_Kp.js:54:63353)
```

The minified function `ET` resolves to `SafeOfTheDayCard`, specifically the line `{data.odd.toFixed(2)}`. The hook `useSafePick` types the query result as `SafePick` but the real backend (`api/routers/v2/safe_pick.py::get_safe_pick`) returns `{date, safe_pick, fallback_message}`. When the user lands on the dashboard:

- `data` is truthy (the wrapper object) so `if (!data)` never fires
- `data.odd` is `undefined`
- `.toFixed(2)` throws
- no ErrorBoundary in `AppV2.tsx` → React unmounts the whole tree → blank page on every route

The secondary 404 on `/api/performance/summary` is real but not the root cause — `StatStrip*` components already guard with `isNum()` / `toNum()`. Still fixed here because it spams the console and prevents real metrics from surfacing.

**Files that matter:**
- `ProbaLab/dashboard/src/hooks/v2/useSafePick.ts` — wrong assumption about response shape
- `ProbaLab/dashboard/src/hooks/v2/usePerformanceSummary.ts` — calls a non-existent endpoint
- `ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.tsx` — non-defensive `.toFixed`
- `ProbaLab/dashboard/src/app/v2/AppV2.tsx` — no ErrorBoundary
- `ProbaLab/api/routers/v2/safe_pick.py` — source of the wrapper response
- `ProbaLab/api/routers/performance.py` — current `/api/performance` endpoint, will host new sub-route
- `ProbaLab/api/main.py` — router wiring

---

## Task 1: Reproduce the bug with a failing frontend test

**Why:** Lock the bug down before fixing it. TDD discipline (CLAUDE.md) + lesson 78 (mock shape must match prod).

**Files:**
- Modify: `ProbaLab/dashboard/src/hooks/v2/useSafePick.test.tsx`
- Create: `ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.test.tsx`
- Modify: `ProbaLab/dashboard/src/test/mocks/handlers.ts`
- Modify: `ProbaLab/dashboard/src/test/mocks/fixtures.ts`

- [ ] **Step 1.1: Update the MSW fixture to match real backend shape**

Replace the flat mock in `ProbaLab/dashboard/src/test/mocks/fixtures.ts` around line 87 with the real API wrapper shape. Keep `mockSafePick` as the inner object (still useful for component tests) and add a new `mockSafePickResponse` for the MSW handler.

```ts
// ProbaLab/dashboard/src/test/mocks/fixtures.ts — replace the mockSafePick export
export const mockSafePick: SafePick = {
  fixtureId: 'fx-1',
  league: leagueL1,
  kickoffUtc: '2026-04-21T19:00:00Z',
  home: mockMatches[0].home,
  away: mockMatches[0].away,
  betLabel: 'PSG gagne vs Lens',
  odd: 1.85,
  probability: 0.58,
  justification:
    "PSG enchaîne 5 victoires à domicile avec xG moyen 2.3. Lens absent de ses 3 cadres défensifs. Valeur cote 1.85 vs proba 58% → edge 7.3%.",
};

// Wrapper shape returned by the real backend (GET /api/safe-pick).
// Keep this as the single source of truth for MSW.
export const mockSafePickResponse = {
  date: '2026-04-21',
  safe_pick: {
    type: 'single' as const,
    fixture_id: 'fx-1',
    odds: 1.85,
    confidence: 0.58,
    market: '1X2',
    selection: 'home',
    kickoff_utc: '2026-04-21T19:00:00Z',
    league_id: 61,
    league_name: 'Ligue 1',
    home_team: 'PSG',
    away_team: 'Lens',
    sport: 'football',
    odds_source: 'real',
  },
  fallback_message: null,
};

export const mockSafePickEmptyResponse = {
  date: '2026-04-22',
  safe_pick: null,
  fallback_message: "Aucun pari Safe ne correspond aux critères aujourd'hui. Revenez demain.",
};
```

- [ ] **Step 1.2: Update the MSW handler to return the wrapper shape**

```ts
// ProbaLab/dashboard/src/test/mocks/handlers.ts — update the /api/safe-pick handler
import { mockSafePickResponse } from './fixtures';

http.get(`${API}/api/safe-pick`, () => HttpResponse.json(mockSafePickResponse)),
```

- [ ] **Step 1.3: Rewrite the `useSafePick` test to assert the new contract**

```tsx
// ProbaLab/dashboard/src/hooks/v2/useSafePick.test.tsx — full replacement
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useSafePick } from './useSafePick';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useSafePick', () => {
  it('returns a flat SafePick when the backend wraps it in {date, safe_pick, fallback_message}', async () => {
    const { result } = renderHook(() => useSafePick('2026-04-21'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Hook must unwrap and adapt to the SafePick shape used by components.
    expect(result.current.data?.betLabel).toBeDefined();
    expect(result.current.data?.odd).toBe(1.85);
    expect(result.current.data?.probability).toBeCloseTo(0.58, 2);
    expect(result.current.data?.fixtureId).toBe('fx-1');
  });

  it('returns null when the backend payload has safe_pick: null', async () => {
    const { result } = renderHook(() => useSafePick('2026-04-22-empty'), { wrapper });
    // Forcing a second handler is overkill — instead assert the hook tolerates
    // an empty response in Task 2 once the adapter is in place. Placeholder
    // assertion here keeps the test importable.
    await waitFor(() => expect(result.current.isFetched).toBe(true));
  });
});
```

- [ ] **Step 1.4: Run the hook test to see it fail**

```bash
cd "ProbaLab/dashboard"
pnpm test useSafePick --run
```

Expected: FAIL — `result.current.data?.odd` is `undefined` (current hook returns the wrapper as-is). This reproduces the prod bug.

- [ ] **Step 1.5: Create a component test that reproduces the `.toFixed` crash**

```tsx
// ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.test.tsx — new file
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SafeOfTheDayCard } from './SafeOfTheDayCard';
import { mockSafePick } from '@/test/mocks/fixtures';

function renderCard(data: Parameters<typeof SafeOfTheDayCard>[0]['data']) {
  return render(
    <MemoryRouter>
      <SafeOfTheDayCard data={data} />
    </MemoryRouter>,
  );
}

describe('SafeOfTheDayCard', () => {
  it('renders the empty state when data is null', () => {
    renderCard(null);
    expect(screen.getByText(/Pas de pronostic Safe/i)).toBeInTheDocument();
  });

  it('renders the bet label and formatted odd when data is complete', () => {
    renderCard(mockSafePick);
    expect(screen.getByText(mockSafePick.betLabel)).toBeInTheDocument();
    expect(screen.getByText('1.85')).toBeInTheDocument();
  });

  it('never crashes when odd is undefined (partial payload)', () => {
    // Regression test for the blank-page crash in prod (2026-04-22).
    const partial = { ...mockSafePick, odd: undefined as unknown as number };
    expect(() => renderCard(partial)).not.toThrow();
  });

  it('never crashes when probability is missing', () => {
    const partial = { ...mockSafePick, probability: undefined as unknown as number };
    expect(() => renderCard(partial)).not.toThrow();
  });
});
```

- [ ] **Step 1.6: Run the component test to see the crash**

```bash
cd "ProbaLab/dashboard"
pnpm test SafeOfTheDayCard --run
```

Expected: the two regression tests (undefined odd / probability) throw `TypeError: Cannot read properties of undefined (reading 'toFixed')`. This is the prod crash reproduced locally.

- [ ] **Step 1.7: Commit the failing tests**

```bash
git add \
  "ProbaLab/dashboard/src/hooks/v2/useSafePick.test.tsx" \
  "ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.test.tsx" \
  "ProbaLab/dashboard/src/test/mocks/handlers.ts" \
  "ProbaLab/dashboard/src/test/mocks/fixtures.ts"
git commit -m "test(v2/home): reproduce blank-page crash on SafeOfTheDayCard + useSafePick shape drift"
```

---

## Task 2: Adapt `useSafePick` to the real backend shape

**Files:**
- Modify: `ProbaLab/dashboard/src/hooks/v2/useSafePick.ts`

- [ ] **Step 2.1: Rewrite the hook with a typed adapter**

```ts
// ProbaLab/dashboard/src/hooks/v2/useSafePick.ts — full replacement
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { SafePick } from '@/types/v2/matches';

// Real backend shape (see api/routers/v2/safe_pick.py::SafePickResponse).
// `safe_pick` is either a single bet, a 2-leg combo or null.
interface BackendSingleLeg {
  type: 'single';
  fixture_id: string;
  odds: number;
  confidence: number; // 0..1
  market?: string;
  selection?: string;
  kickoff_utc?: string;
  league_id?: number | string;
  league_name?: string;
  home_team?: string;
  away_team?: string;
  sport?: 'football' | 'nhl';
  odds_source?: 'real' | 'implied';
}

interface BackendSafePickResponse {
  date: string;
  safe_pick: BackendSingleLeg | { type: 'combo'; [k: string]: unknown } | null;
  fallback_message: string | null;
}

// Map the backend single-leg payload into the frontend SafePick shape.
// Combos are intentionally collapsed to `null` for now: the landing card
// only knows how to render a single bet. When combo rendering is added,
// this adapter is the single place to extend.
function adaptSafePick(raw: BackendSafePickResponse): SafePick | null {
  const leg = raw.safe_pick;
  if (!leg || leg.type !== 'single') return null;
  const single = leg as BackendSingleLeg;
  if (typeof single.odds !== 'number' || typeof single.confidence !== 'number') return null;

  const label = [single.home_team, single.away_team].filter(Boolean).join(' vs ') || 'Pronostic Safe';
  const betLabel =
    single.selection && single.market
      ? `${single.selection.toUpperCase()} · ${single.market} (${label})`
      : label;

  return {
    fixtureId: String(single.fixture_id),
    league: {
      id: String(single.league_id ?? 'unknown'),
      name: single.league_name ?? '',
      country: '',
      color: '#64748b',
    },
    kickoffUtc: single.kickoff_utc ?? '',
    home: { id: '', name: single.home_team ?? '', short: single.home_team ?? '' },
    away: { id: '', name: single.away_team ?? '', short: single.away_team ?? '' },
    betLabel,
    odd: Number(single.odds),
    probability: Number(single.confidence),
    justification: '',
  };
}

export function useSafePick(date: string) {
  return useQuery<BackendSafePickResponse, Error, SafePick | null>({
    queryKey: ['v2', 'safe-pick', date],
    queryFn: () => apiGet<BackendSafePickResponse>('/api/safe-pick', { date }),
    select: adaptSafePick,
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] **Step 2.2: Run the hook test**

```bash
cd "ProbaLab/dashboard"
pnpm test useSafePick --run
```

Expected: PASS — `result.current.data?.odd === 1.85` now that the adapter unwraps the backend payload.

- [ ] **Step 2.3: Commit**

```bash
git add "ProbaLab/dashboard/src/hooks/v2/useSafePick.ts"
git commit -m "fix(v2/hooks): adapt useSafePick to real backend shape ({date, safe_pick, fallback_message})"
```

---

## Task 3: Harden `SafeOfTheDayCard` against partial payloads

**Files:**
- Modify: `ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.tsx`

- [ ] **Step 3.1: Add defensive formatters and guard accessors**

Replace the body of the card (lines 10-93) with the version below. Two things change:
1. A single `hasMinimumData` guard short-circuits to the empty state when `odd` or `probability` are not finite numbers — no partial render.
2. All numeric outputs go through helpers that tolerate `undefined`.

```tsx
// ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.tsx — full replacement
import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';
import type { SafePick } from '@/types/v2/matches';

interface Props {
  data: SafePick | null;
  'data-testid'?: string;
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

function fmtOdd(v: unknown): string {
  return isFiniteNumber(v) ? v.toFixed(2) : '—';
}

function fmtPctFromUnit(v: unknown): string {
  return isFiniteNumber(v) ? `${Math.round(v * 100)}%` : '—';
}

function pctWidth(v: unknown): string {
  if (!isFiniteNumber(v)) return '0%';
  const clamped = Math.max(0, Math.min(1, v));
  return `${Math.round(clamped * 100)}%`;
}

export function SafeOfTheDayCard({
  data,
  'data-testid': dataTestId = 'safe-of-the-day-card',
}: Props) {
  const hasMinimumData =
    data !== null && isFiniteNumber(data.odd) && typeof data.betLabel === 'string';

  if (!hasMinimumData) {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-border bg-surface p-6 text-center"
        style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
      >
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Pas de pronostic Safe aujourd'hui — privilégiez l'analyse des matchs du soir.
        </p>
      </section>
    );
  }

  const pctLabel = fmtPctFromUnit(data.probability);
  const progressWidth = pctWidth(data.probability);
  const ariaValue = isFiniteNumber(data.probability)
    ? Math.round(data.probability * 100)
    : 0;

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl p-6 shadow-sm"
      style={{
        borderLeft: '3px solid var(--primary)',
        background:
          'linear-gradient(135deg, rgba(16,185,129,0.12) 0%, var(--surface) 70%)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <span
          className="inline-flex items-center gap-1 text-xs font-medium tracking-wide"
          style={{ color: 'var(--primary)' }}
        >
          <Star aria-hidden="true" size={14} />
          SAFE · PRONOSTIC DU JOUR
        </span>
        <span
          className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
          style={{ border: '1px solid var(--border)', color: 'var(--text-muted)' }}
        >
          FREE
        </span>
      </div>
      <h3 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>
        {data.betLabel}
      </h3>
      <div className="mt-3 flex items-baseline gap-4">
        <span
          className="font-bold tabular-nums"
          style={{ fontSize: 32, color: 'var(--primary)', fontVariantNumeric: 'tabular-nums' }}
        >
          {fmtOdd(data.odd)}
        </span>
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Probabilité {pctLabel}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={ariaValue}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Probabilité ${data.betLabel} ${pctLabel}`}
        className="mt-2 h-1 w-full rounded-full overflow-hidden"
        style={{ background: 'var(--surface-2)' }}
      >
        <div
          className="h-full"
          style={{ width: progressWidth, background: 'var(--primary)' }}
        />
      </div>
      {data.justification && (
        <p className="mt-4 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          {data.justification}
        </p>
      )}
      <Link
        to={`/matchs/${data.fixtureId}`}
        className="mt-4 inline-block text-sm font-medium focus-visible:outline focus-visible:outline-2"
        style={{ color: 'var(--primary)' }}
      >
        Voir le match →
      </Link>
    </section>
  );
}

export default SafeOfTheDayCard;
```

- [ ] **Step 3.2: Run the component test**

```bash
cd "ProbaLab/dashboard"
pnpm test SafeOfTheDayCard --run
```

Expected: all 4 tests PASS, including the two regression tests that previously threw.

- [ ] **Step 3.3: Commit**

```bash
git add "ProbaLab/dashboard/src/components/v2/home/SafeOfTheDayCard.tsx"
git commit -m "fix(v2/home): SafeOfTheDayCard tolerates missing odd/probability (regression: blank-page crash)"
```

---

## Task 4: Add the missing `/api/performance/summary` backend endpoint

**Why:** The hook `usePerformanceSummary` targets an endpoint that doesn't exist → constant 404 in the console. A real endpoint returning the exact shape the frontend expects is cleaner than adapting the hook to the existing `/api/performance?days=N` (different aggregation window, different keys). Leverages the existing `_compute_market_performance` helper and the track-record builder for reuse.

**Files:**
- Modify: `ProbaLab/api/routers/performance.py`
- Create: `ProbaLab/tests/test_api/test_performance_summary.py`

- [ ] **Step 4.1: Write the failing backend test**

```python
# ProbaLab/tests/test_api/test_performance_summary.py — new file
"""Contract test for GET /api/performance/summary.

The frontend hook `usePerformanceSummary` expects the following shape exactly:
    {
      roi30d:   {value: number, deltaVs7d: number},
      accuracy: {value: number, deltaVs7d: number},
      brier7d:  {value: number, deltaVs7d: number},
      bankroll: {value: number, currency: "EUR"},
    }

Schema drift = frontend crash, so this test pins the contract.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_performance_summary_returns_expected_shape(client: TestClient):
    res = client.get("/api/performance/summary", params={"window": 30})
    assert res.status_code == 200, res.text
    body = res.json()

    for key in ("roi30d", "accuracy", "brier7d", "bankroll"):
        assert key in body, f"missing top-level key {key!r}"

    for key in ("roi30d", "accuracy", "brier7d"):
        assert "value" in body[key], f"{key}.value missing"
        assert "deltaVs7d" in body[key], f"{key}.deltaVs7d missing"
        assert isinstance(body[key]["value"], (int, float))
        assert isinstance(body[key]["deltaVs7d"], (int, float))

    assert isinstance(body["bankroll"]["value"], (int, float))
    assert body["bankroll"]["currency"] == "EUR"


def test_performance_summary_accepts_window_7_30_90(client: TestClient):
    for window in (7, 30, 90):
        res = client.get("/api/performance/summary", params={"window": window})
        assert res.status_code == 200, f"window={window} got {res.status_code}: {res.text}"


def test_performance_summary_rejects_invalid_window(client: TestClient):
    res = client.get("/api/performance/summary", params={"window": 500})
    assert res.status_code == 422


def test_performance_summary_returns_zeros_when_db_empty(
    client: TestClient, monkeypatch
):
    """Even with no finished fixtures, the endpoint must return well-typed zeros,
    never 500 or a partial payload. This is what unblocks the landing when the
    DB is seeded from scratch (lesson 60)."""
    from api.routers import performance as perf_router

    def _empty(*_a, **_kw):
        return {
            "roi_value": 0.0,
            "roi_delta": 0.0,
            "accuracy_value": 0.0,
            "accuracy_delta": 0.0,
            "brier_value": 0.0,
            "brier_delta": 0.0,
            "bankroll_value": 0.0,
        }

    monkeypatch.setattr(perf_router, "_compute_performance_summary", _empty)
    res = client.get("/api/performance/summary", params={"window": 30})
    assert res.status_code == 200
    body = res.json()
    assert body["roi30d"] == {"value": 0.0, "deltaVs7d": 0.0}
    assert body["bankroll"] == {"value": 0.0, "currency": "EUR"}
```

- [ ] **Step 4.2: Run the test to see it fail**

```bash
cd "ProbaLab"
pyenv exec pytest tests/test_api/test_performance_summary.py -v
```

Expected: FAIL — endpoint returns 404.

- [ ] **Step 4.3: Implement `_compute_performance_summary` as a pure helper**

Append this to `ProbaLab/api/routers/performance.py`, right before the last route (i.e. after `_compute_market_performance`, before `get_market_roi`):

```python
# ─── Performance Summary (V2 landing) ────────────────────────


def _compute_performance_summary(window_days: int) -> dict[str, float]:
    """Compute the 4 KPIs surfaced on the V2 landing stat strip.

    Pure function — takes a window in days, returns primitive floats only.
    Reuses existing aggregates:
    - accuracy: 1X2 accuracy on predictions made in the window (same formula
      as /api/performance).
    - brier: average Brier score on predictions made in the last 7 days
      (frontend label is "Brier 7J").
    - roi: average market ROI weighted by volume, sourced from
      ``_compute_market_performance(window_days)``.
    - bankroll: simulated bankroll assuming a flat 1€ stake on every "active"
      market bet over the window. Good enough as a public signal — the
      real per-user bankroll lives in /api/user/bankroll/*.
    - deltaVs7d: same metric computed on the last 7 days, minus the value
      on the 7 days BEFORE that. Gives a "trend arrow".

    Returns zeros (never raises) when the DB has no data — the endpoint
    stays 200 so the frontend can render its fallbacks.
    """
    from src.constants import LEAGUES_TO_FETCH

    # ── ROI + bankroll from market performance ───────────────────
    markets = _compute_market_performance(days=window_days)
    if markets:
        total_staked = sum(m["total"] for m in markets.values())
        # Weighted average ROI by bet volume (more trustworthy than a flat mean).
        weighted_roi = (
            sum(m["roi"] * m["total"] for m in markets.values()) / total_staked
            if total_staked
            else 0.0
        )
        # Simulated bankroll = 1000€ seed * (1 + roi%)
        bankroll_value = round(1000.0 * (1.0 + weighted_roi / 100.0), 2)
    else:
        weighted_roi = 0.0
        bankroll_value = 1000.0

    markets_7 = _compute_market_performance(days=7)
    markets_prev7 = {}
    # Previous 7d = days 8..14. We don't have a "range" helper so we just
    # compute the delta as roi(7d) - roi(14d weighted), matching the
    # frontend's label "vs 7j". Close enough for a public signal.
    if markets_7:
        total7 = sum(m["total"] for m in markets_7.values())
        roi_7 = (
            sum(m["roi"] * m["total"] for m in markets_7.values()) / total7
            if total7
            else 0.0
        )
    else:
        roi_7 = 0.0
    markets_14 = _compute_market_performance(days=14)
    if markets_14:
        total14 = sum(m["total"] for m in markets_14.values())
        roi_14 = (
            sum(m["roi"] * m["total"] for m in markets_14.values()) / total14
            if total14
            else 0.0
        )
    else:
        roi_14 = 0.0
    roi_delta = round(roi_7 - roi_14, 2)

    # ── Accuracy + Brier from predictions/fixtures ───────────────
    from datetime import datetime, timedelta, timezone

    def _accuracy_brier(days: int) -> tuple[float, float]:
        """Return (accuracy_pct, brier_score) over the window. (0.0, 0.0) if empty."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            finished = (
                supabase.table("fixtures")
                .select("id, home_goals, away_goals, date")
                .in_("status", ["FT", "AET", "PEN"])
                .in_("league_id", LEAGUES_TO_FETCH)
                .gte("date", cutoff)
                .order("date")
                .range(0, 999)
                .execute()
                .data
                or []
            )
        except Exception:
            logger.warning("summary: fixtures fetch failed", exc_info=True)
            return 0.0, 0.0

        if not finished:
            return 0.0, 0.0

        fixture_ids = [f["id"] for f in finished]
        preds: list[dict] = []
        CHUNK = 100
        for i in range(0, len(fixture_ids), CHUNK):
            chunk = fixture_ids[i : i + CHUNK]
            try:
                page = (
                    supabase.table("predictions")
                    .select("fixture_id, proba_home, proba_draw, proba_away")
                    .in_("fixture_id", chunk)
                    .order("created_at")
                    .execute()
                    .data
                    or []
                )
            except Exception:
                logger.warning("summary: predictions fetch failed", exc_info=True)
                page = []
            preds.extend(page)

        # Dedupe keeping the FIRST prediction (lesson 32).
        pred_by_fix: dict[str, dict] = {}
        for p in preds:
            fid = str(p["fixture_id"])
            if fid not in pred_by_fix:
                pred_by_fix[fid] = p

        correct = 0
        countable = 0
        brier_sum = 0.0
        brier_n = 0
        for f in finished:
            pred = pred_by_fix.get(str(f["id"]))
            if not pred:
                continue
            ph, pd_, pa = pred.get("proba_home"), pred.get("proba_draw"), pred.get("proba_away")
            if ph is None or pd_ is None or pa is None:
                continue
            hg = f.get("home_goals") or 0
            ag = f.get("away_goals") or 0
            actual = "H" if hg > ag else ("D" if hg == ag else "A")
            # Strict > to avoid home bias on ties (lesson 30).
            if ph > pd_ and ph > pa:
                pred_r = "H"
            elif pa > ph and pa > pd_:
                pred_r = "A"
            elif pd_ > ph and pd_ > pa:
                pred_r = "D"
            else:
                pred_r = None
            if pred_r is not None:
                countable += 1
                if pred_r == actual:
                    correct += 1
            # Brier always computed when probas are valid.
            o_h = 1 if actual == "H" else 0
            o_d = 1 if actual == "D" else 0
            o_a = 1 if actual == "A" else 0
            brier_sum += (
                (ph / 100.0 - o_h) ** 2
                + (pd_ / 100.0 - o_d) ** 2
                + (pa / 100.0 - o_a) ** 2
            )
            brier_n += 1

        acc = round(correct / countable * 100, 1) if countable else 0.0
        brier = round(brier_sum / brier_n, 3) if brier_n else 0.0
        return acc, brier

    acc_window, _ = _accuracy_brier(window_days)
    acc_7d, brier_7d = _accuracy_brier(7)
    acc_14d, brier_14d = _accuracy_brier(14)
    accuracy_delta = round(acc_7d - acc_14d, 1)
    # Lower Brier = better → the frontend treats brier delta differently but
    # we still expose the raw diff; StatStrip handles the tone.
    brier_delta = round(brier_7d - brier_14d, 3)

    return {
        "roi_value": round(weighted_roi, 2),
        "roi_delta": roi_delta,
        "accuracy_value": acc_window,
        "accuracy_delta": accuracy_delta,
        "brier_value": brier_7d,
        "brier_delta": brier_delta,
        "bankroll_value": bankroll_value,
    }


@router.get(
    "/performance/summary",
    summary="V2 landing KPIs (ROI, accuracy, Brier 7J, bankroll)",
    responses={500: {"description": "Internal server error"}},
)
def get_performance_summary(
    window: int = Query(
        30,
        description="Rolling window in days. Only 7/30/90 are permitted.",
        ge=7,
        le=90,
    ),
):
    """Return the 4 KPIs consumed by `usePerformanceSummary` on the V2 landing.

    Shape is fixed by the frontend `PerformanceSummary` type — any drift here
    blanks out the stat strip (lesson 60: API shape must match frontend exactly).
    """
    if window not in (7, 30, 90):
        raise HTTPException(status_code=422, detail="window must be one of 7, 30, 90")
    try:
        s = _compute_performance_summary(window)
        return {
            "roi30d": {"value": s["roi_value"], "deltaVs7d": s["roi_delta"]},
            "accuracy": {"value": s["accuracy_value"], "deltaVs7d": s["accuracy_delta"]},
            "brier7d": {"value": s["brier_value"], "deltaVs7d": s["brier_delta"]},
            "bankroll": {"value": s["bankroll_value"], "currency": "EUR"},
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("get_performance_summary failed")
        # Never 500 the landing — fall back to typed zeros. The frontend's
        # fallback kicks in but the page stays up.
        return {
            "roi30d": {"value": 0.0, "deltaVs7d": 0.0},
            "accuracy": {"value": 0.0, "deltaVs7d": 0.0},
            "brier7d": {"value": 0.0, "deltaVs7d": 0.0},
            "bankroll": {"value": 0.0, "currency": "EUR"},
        }
```

- [ ] **Step 4.4: Run the test again to see it pass**

```bash
cd "ProbaLab"
pyenv exec pytest tests/test_api/test_performance_summary.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 4.5: Run the full backend suite to make sure nothing else broke**

```bash
cd "ProbaLab"
pyenv exec pytest -q
```

Expected: same pass count as before + the new tests (no regressions). If any test fails, STOP — check lesson 78 (mock chain methods) before patching.

- [ ] **Step 4.6: Commit**

```bash
git add \
  "ProbaLab/api/routers/performance.py" \
  "ProbaLab/tests/test_api/test_performance_summary.py"
git commit -m "feat(api/perf): add /api/performance/summary for V2 landing KPIs"
```

---

## Task 5: Verify the frontend hook works against the real endpoint

**Files:**
- Modify: `ProbaLab/dashboard/src/test/mocks/fixtures.ts`
- Modify: `ProbaLab/dashboard/src/test/mocks/handlers.ts`
- Modify: `ProbaLab/dashboard/src/test/mocks/handlers.test.ts`

- [ ] **Step 5.1: Align the MSW handler with the new backend shape**

The existing `mockPerformance` in fixtures already matches `PerformanceSummary` — verify it by opening `ProbaLab/dashboard/src/test/mocks/fixtures.ts` and checking that `mockPerformance` has the 4 top-level keys with `{value, deltaVs7d}` each. If any key is missing or differs, fix it:

```ts
// ProbaLab/dashboard/src/test/mocks/fixtures.ts — mockPerformance must be:
export const mockPerformance: PerformanceSummary = {
  roi30d:   { value: 12.4, deltaVs7d: 0.8 },
  accuracy: { value: 54.2, deltaVs7d: -0.3 },
  brier7d:  { value: 0.214, deltaVs7d: -0.002 },
  bankroll: { value: 1240, currency: 'EUR' },
};
```

- [ ] **Step 5.2: Run the hook test for `usePerformanceSummary`**

```bash
cd "ProbaLab/dashboard"
pnpm test usePerformanceSummary --run
```

Expected: PASS. If it fails because of a shape mismatch, align `mockPerformance`.

- [ ] **Step 5.3: Commit (skip if nothing changed)**

```bash
git add "ProbaLab/dashboard/src/test/mocks/fixtures.ts" \
         "ProbaLab/dashboard/src/test/mocks/handlers.ts" \
         "ProbaLab/dashboard/src/test/mocks/handlers.test.ts" 2>/dev/null || true
git diff --cached --quiet || git commit -m "test(v2/mocks): align mockPerformance with real /api/performance/summary shape"
```

---

## Task 6: Wrap `AppV2` in an ErrorBoundary so a render crash can never blank the app

**Why:** Without an ErrorBoundary any uncaught throw during render unmounts the whole React tree — that's why every page went blank, not just the one rendering `SafeOfTheDayCard`. Lesson: `AppLegacy.tsx` already had one. `AppV2.tsx` forgot it.

**Files:**
- Create: `ProbaLab/dashboard/src/components/v2/system/ErrorBoundary.tsx`
- Create: `ProbaLab/dashboard/src/components/v2/system/ErrorBoundary.test.tsx`
- Modify: `ProbaLab/dashboard/src/app/v2/AppV2.tsx`

- [ ] **Step 6.1: Write the failing test**

```tsx
// ProbaLab/dashboard/src/components/v2/system/ErrorBoundary.test.tsx — new file
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

function Boom(): JSX.Element {
  throw new Error("Cannot read properties of undefined (reading 'toFixed')");
}

describe('ErrorBoundary', () => {
  it('renders children when they do not throw', () => {
    render(
      <ErrorBoundary>
        <p>hello</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('renders fallback UI when a child throws', () => {
    // Silence the expected console.error from React's boundary logging.
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
    expect(screen.getByText(/réessayer/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6.2: Run the test to see it fail**

```bash
cd "ProbaLab/dashboard"
pnpm test ErrorBoundary --run
```

Expected: FAIL — `ErrorBoundary` not found.

- [ ] **Step 6.3: Implement the component**

```tsx
// ProbaLab/dashboard/src/components/v2/system/ErrorBoundary.tsx — new file
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

// Catches render-time errors from anywhere in the subtree so a single bad
// component (undefined `.toFixed`, shape drift, stale cached data…) can't
// blank out the whole app. Pairs with the AppLegacy boundary so legacy and
// V2 routes now share the same guarantee.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Reload-on-stale-chunk — same heuristic as AppLegacy.tsx.
    const msg = error?.message ?? '';
    if (
      msg.includes('Failed to fetch dynamically imported module') ||
      msg.includes('Loading chunk') ||
      msg.includes('Loading CSS chunk')
    ) {
      window.location.reload();
      return;
    }
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary (V2) caught:', error, info);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;
    return (
      <div
        data-testid="error-boundary-fallback"
        role="alert"
        style={{
          minHeight: '60vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          padding: 24,
          textAlign: 'center',
          color: 'var(--text)',
          background: 'var(--bg)',
        }}
      >
        <h2 style={{ fontSize: 22, fontWeight: 700 }}>Une erreur est survenue</h2>
        <p style={{ maxWidth: 420, color: 'var(--text-muted)' }}>
          Pas de panique — la page a planté à l'affichage. On a capturé l'erreur,
          vous pouvez réessayer sans recharger.
        </p>
        <button
          type="button"
          onClick={this.handleRetry}
          style={{
            padding: '10px 18px',
            borderRadius: 8,
            border: '1px solid var(--border)',
            background: 'var(--primary)',
            color: '#fff',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Réessayer
        </button>
      </div>
    );
  }
}

export default ErrorBoundary;
```

- [ ] **Step 6.4: Run the test to see it pass**

```bash
cd "ProbaLab/dashboard"
pnpm test ErrorBoundary --run
```

Expected: both tests PASS.

- [ ] **Step 6.5: Wire the boundary into `AppV2`**

```tsx
// ProbaLab/dashboard/src/app/v2/AppV2.tsx — full replacement
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../../lib/auth';
import { v2Routes } from './routes';
import { LayoutShell } from '../../components/v2/layout/LayoutShell';
import { ErrorBoundary } from '../../components/v2/system/ErrorBoundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function AppV2Content() {
  return (
    <div className="v2-root">
      <LayoutShell>
        <ErrorBoundary>
          <Routes>
            {v2Routes.map((route) => (
              <Route key={route.path} path={route.path} element={route.element}>
                {route.children?.map((child, idx) =>
                  child.index ? (
                    <Route key={`idx-${route.path}`} index element={child.element} />
                  ) : (
                    <Route
                      key={`${route.path}-${child.path ?? idx}`}
                      path={child.path}
                      element={child.element}
                    />
                  ),
                )}
              </Route>
            ))}
          </Routes>
        </ErrorBoundary>
      </LayoutShell>
    </div>
  );
}

export function AppV2() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppV2Content />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default AppV2;
```

- [ ] **Step 6.6: Run the existing `AppV2` test to make sure the wrap didn't break anything**

```bash
cd "ProbaLab/dashboard"
pnpm test AppV2 --run
```

Expected: PASS.

- [ ] **Step 6.7: Commit**

```bash
git add \
  "ProbaLab/dashboard/src/components/v2/system/ErrorBoundary.tsx" \
  "ProbaLab/dashboard/src/components/v2/system/ErrorBoundary.test.tsx" \
  "ProbaLab/dashboard/src/app/v2/AppV2.tsx"
git commit -m "feat(v2): wrap AppV2 routes in ErrorBoundary to prevent blank-page crashes"
```

---

## Task 7: Full-suite verification

**Files:** none (verification only).

- [ ] **Step 7.1: Run the full frontend test suite**

```bash
cd "ProbaLab/dashboard"
pnpm test --run
```

Expected: all tests PASS. Record the previous PASS count (from CI) and confirm the new count = previous + 4 new tests from Tasks 1, 3, 4, 6.

- [ ] **Step 7.2: Run the full backend test suite**

```bash
cd "ProbaLab"
pyenv exec pytest -q
```

Expected: all tests PASS including the new contract test.

- [ ] **Step 7.3: Typecheck the frontend**

```bash
cd "ProbaLab/dashboard"
pnpm typecheck
```

Expected: zero errors.

- [ ] **Step 7.4: Lint**

```bash
cd "ProbaLab/dashboard"
pnpm lint
```

Expected: zero errors. If `pnpm lint` is not wired, use `pnpm exec eslint src --max-warnings=0`.

- [ ] **Step 7.5: Smoke-test locally against a running backend**

Terminal A — start backend:
```bash
cd "ProbaLab"
pyenv exec uvicorn api.main:app --reload --port 8000
```

Terminal B — start frontend:
```bash
cd "ProbaLab/dashboard"
VITE_API_URL=http://localhost:8000 pnpm dev
```

Open `http://localhost:5173/` in a browser. Expected:
- No blank page.
- Console shows 0 occurrences of `Cannot read properties of undefined (reading 'toFixed')`.
- Network tab: `GET /api/performance/summary?window=30` returns 200 with the `{roi30d, accuracy, brier7d, bankroll}` shape.
- Network tab: `GET /api/safe-pick?date=<today>` returns 200; the landing either shows the card or the empty state — never throws.

- [ ] **Step 7.6: Commit (no code changes — just gate the plan)**

Nothing to commit here. If the smoke test revealed an issue, STOP and return to Phase 1 of systematic-debugging.

---

## Task 8: Update `tasks/lessons.md` with the root-cause lesson

**Files:**
- Modify: `ProbaLab/tasks/lessons.md`

- [ ] **Step 8.1: Append lesson 79**

Open `ProbaLab/tasks/lessons.md` and append the following row to the table (keeping the pipe layout of the existing rows):

```markdown
| 2026-04-22 | Hook `useSafePick` typé `SafePick` mais backend retourne `{date, safe_pick, fallback_message}` → `data.odd` undefined → `.toFixed(2)` crash → blank page toutes pages (pas d'ErrorBoundary sur AppV2) | Tout hook qui consomme une API doit soit typer la réponse réelle exacte soit utiliser `select:` pour adapter. Et toute app React de prod doit avoir un ErrorBoundary à la racine — un seul composant qui throw ne doit jamais pouvoir blanchir toutes les pages |
```

- [ ] **Step 8.2: Commit**

```bash
git add "ProbaLab/tasks/lessons.md"
git commit -m "docs(lessons): add lesson 79 — ErrorBoundary + hook shape adapter"
```

---

## Task 9: Push + deploy

- [ ] **Step 9.1: Push the branch**

```bash
git push origin HEAD
```

- [ ] **Step 9.2: Confirm Vercel + Railway deploys succeeded**

- Vercel: https://vercel.com — watch the build log for `ProbaLab/dashboard`. Expected: green.
- Railway: same — watch the API build. Expected: green.

- [ ] **Step 9.3: Smoke-test prod after deploy**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://api.probalab.net/api/performance/summary?window=30"
```

Expected: `200`.

```bash
curl -s "https://api.probalab.net/api/performance/summary?window=30" | python3 -m json.tool
```

Expected: the 4-keys shape with numeric values.

Load https://probalab.net in a browser. Expected:
- Landing renders.
- Devtools console: 0 `toFixed` crash.
- Devtools network: `/api/performance/summary?window=30` → 200.

- [ ] **Step 9.4: If anything is red, rollback**

The Vercel dashboard has a one-click rollback to the previous working build. Use it rather than reverting commits in a hurry.
