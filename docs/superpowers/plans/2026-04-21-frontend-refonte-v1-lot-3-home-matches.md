# Frontend Refonte V1 — Lot 3 · Accueil + Matchs

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` strictly. Chaque Task commence par un test failing, puis l'implémentation, puis le commit. Steps utilisent la syntaxe checkbox (`- [ ]`).

**Goal:** Livrer les pages `/` (mode landing visiteur + mode dashboard connecté) et `/matchs` (mobile + desktop avec sidebar filtres), en remplaçant les stubs `HomeV2` / `MatchesV2` produits au Lot 1. Toute la couche data utilise TanStack Query 5 contre les endpoints Lot 2 (`/api/safe-pick`, `/api/matches`, `/api/performance/summary`, `/api/best-bets`). MSW mocke ces endpoints en dev/test tant que Lot 2 n'est pas mergé.

**Spec source:** [docs/superpowers/specs/2026-04-21-frontend-refonte-v1-design.md](../specs/2026-04-21-frontend-refonte-v1-design.md) sections 6 (Accueil) et 7 (Matchs).

**Prerequisites:**
- Lot 1 mergé : tokens CSS, `StatTile`, `ProbBar`, `ValueBadge`, `OddsChip`, `LockOverlay`, `TrialBanner`, `HeaderV2`, `BottomNavV2`, `LayoutShell`, routing V2 avec stubs `HomeV2` / `MatchesV2`, `AppV2` monté sur `VITE_FRONTEND_V2=true`.
- Lot 2 : soit mergé (endpoints réels), soit accessible via MSW (mocks livrés dans ce lot).
- `msw` et `@testing-library/react-hooks` installés au pré-requis master P1.
- `date-fns` et `date-fns-tz` disponibles (sinon installer au début de ce lot).

**Working directory:** toutes les commandes `npm` depuis `ProbaLab/dashboard/`. Tous les chemins d'import relatifs côté `src/`, chemins absolus dans ce document : `/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/dashboard/...`.

**Branch:** `feat/frontend-refonte-v1-lot-3` basée sur `feat/frontend-refonte-v1` (ou directement sur cette branche si parallélisation pas nécessaire).

**Commit convention:** `feat(v2/home): ...`, `feat(v2/matches): ...`, `test(v2/home): ...`, `test(v2/matches): ...`, `chore(v2): ...`. Co-Authored-By Claude Sonnet 4.6 sur chaque commit. Jamais `--no-verify`.

---

## Invariants

- **TypeScript strict.** `any` interdit. Types partagés dans `src/types/v2/`.
- **Mobile-first.** Chaque composant testé à 375px et 1280px via `window.innerWidth` + `resize` event (helper `setViewportWidth` dans `test/utils.ts`).
- **TDD strict.** Test failing d'abord, implem ensuite, pass, commit. Un commit par cycle.
- **Snapshots interdits** sauf justification explicite en commentaire dans le test. Les tests assertent du comportement (rôles ARIA, texte, interactions), jamais la forme du DOM.
- **Accessibility.** Chaque composant expose ses états à la techno d'assistance : rôles ARIA, `aria-label` sur les barres de probas (`"PSG 58%, Nul 24%, Lens 18%"`), focus visible testé via `:focus-visible`, ordre tab cohérent. Chaque Task inclut un test `jest-axe` (`expect(await axe(container)).toHaveNoViolations()`).
- **Gating.** Le hook `useAuthState()` (fourni Lot 1) retourne `{ status: 'visitor' | 'free' | 'trial' | 'premium', trialDaysLeft?: number }`. Les composants consomment ce hook — pas de prop drilling du statut.
- **Perf.** `MatchesList` / `MatchesTableDesktop` rendent <50 lignes en rendu simple (YAGNI). Si >50 lignes détectées, on bascule sur `react-window` (hors scope de ce lot, log d'avertissement uniquement).
- **Pas de TODO/FIXME/XXX** dans le code livré.
- **Fichiers ≤ 300 lignes.** Au-delà, split.

---

## Types partagés (créés dans Task 1)

Tous les types produits par les endpoints Lot 2 vivent dans `src/types/v2/matches.ts` et sont importés par les hooks, composants et mocks MSW. Une seule source de vérité.

---

## Task 1 · Types & MSW handlers (fondations data)

**Files:**
- `src/types/v2/matches.ts` (nouveau)
- `src/types/v2/performance.ts` (nouveau)
- `src/test/mocks/handlers.ts` (nouveau)
- `src/test/mocks/server.ts` (nouveau)
- `src/test/mocks/fixtures.ts` (nouveau)
- `src/test/setup.ts` (modifié : démarrer MSW server)

**Steps:**

- [ ] Écrire `src/types/v2/matches.ts` :

```ts
// src/types/v2/matches.ts
export type FixtureId = string;
export type Sport = 'football' | 'nhl';
export type SignalKind = 'safe' | 'value' | 'high_confidence';

export interface TeamRef {
  id: string;
  name: string;
  short: string;
  logoUrl?: string;
}

export interface LeagueRef {
  id: string;
  name: string;
  country: string;
  color: string; // hex token spec section 7
}

export interface Prob1x2 {
  home: number; // 0..1
  draw: number; // 0..1 (absent NHL)
  away: number;
}

export interface ValueBet {
  market: string;          // ex: "BTTS Oui"
  edgePct: number;         // ex: 7.2
  bestOdd: number;         // ex: 1.92
  bestBook: string;        // ex: "Pinnacle"
  kellyPct: number;        // ex: 2.4
}

export interface MatchRowData {
  fixtureId: FixtureId;
  sport: Sport;
  league: LeagueRef;
  kickoffUtc: string;      // ISO 8601
  home: TeamRef;
  away: TeamRef;
  prob1x2: Prob1x2;
  signals: SignalKind[];
  topValueBet?: ValueBet;  // le plus edgé si présent
}

export interface SafePick {
  fixtureId: FixtureId;
  league: LeagueRef;
  kickoffUtc: string;
  home: TeamRef;
  away: TeamRef;
  betLabel: string;        // "PSG gagne vs Lens"
  odd: number;             // 1.92
  probability: number;     // 0..1
  justification: string;   // 2-3 lignes
}

export interface MatchesFilters {
  date: string;            // YYYY-MM-DD (UTC)
  sports?: Sport[];
  leagues?: string[];
  signals?: SignalKind[];
  valueOnly?: boolean;
  sort?: 'kickoff' | 'edge' | 'confidence' | 'league';
}

export interface MatchesResponse {
  date: string;
  matches: MatchRowData[];
  counts: {
    total: number;
    bySport: Record<Sport, number>;
    byLeague: Record<string, number>;
  };
}
```

- [ ] Écrire `src/types/v2/performance.ts` :

```ts
// src/types/v2/performance.ts
export interface PerformanceSummary {
  roi30d: { value: number; deltaVs7d: number };         // en %
  accuracy: { value: number; deltaVs7d: number };       // en %
  brier7d: { value: number; deltaVs7d: number };        // brier score
  bankroll: { value: number; currency: 'EUR' };         // montant
}
```

- [ ] Écrire `src/test/mocks/fixtures.ts` (3-5 matchs exemples, pas plus) :

```ts
// src/test/mocks/fixtures.ts
import type { MatchRowData, SafePick, PerformanceSummary } from '@/types/v2/matches';
import type { PerformanceSummary as Perf } from '@/types/v2/performance';

export const leagueL1 = {
  id: 'fr-l1', name: 'Ligue 1', country: 'FR', color: '#2563eb',
};
export const leaguePL = {
  id: 'en-pl', name: 'Premier League', country: 'EN', color: '#7c3aed',
};

export const mockMatches: MatchRowData[] = [
  {
    fixtureId: 'fx-1',
    sport: 'football',
    league: leagueL1,
    kickoffUtc: '2026-04-21T19:00:00Z',
    home: { id: 't-psg', name: 'Paris Saint-Germain', short: 'PSG' },
    away: { id: 't-len', name: 'RC Lens', short: 'LEN' },
    prob1x2: { home: 0.58, draw: 0.24, away: 0.18 },
    signals: ['safe'],
    topValueBet: undefined,
  },
  {
    fixtureId: 'fx-2',
    sport: 'football',
    league: leagueL1,
    kickoffUtc: '2026-04-21T21:00:00Z',
    home: { id: 't-om', name: 'Olympique de Marseille', short: 'OM' },
    away: { id: 't-lyo', name: 'Olympique Lyonnais', short: 'OL' },
    prob1x2: { home: 0.42, draw: 0.27, away: 0.31 },
    signals: ['value'],
    topValueBet: {
      market: 'BTTS Oui', edgePct: 7.2, bestOdd: 1.92, bestBook: 'Pinnacle', kellyPct: 2.4,
    },
  },
  {
    fixtureId: 'fx-3',
    sport: 'football',
    league: leaguePL,
    kickoffUtc: '2026-04-21T18:30:00Z',
    home: { id: 't-ars', name: 'Arsenal', short: 'ARS' },
    away: { id: 't-che', name: 'Chelsea', short: 'CHE' },
    prob1x2: { home: 0.51, draw: 0.26, away: 0.23 },
    signals: ['value', 'high_confidence'],
    topValueBet: {
      market: 'Over 2.5', edgePct: 5.4, bestOdd: 1.85, bestBook: 'Unibet', kellyPct: 1.7,
    },
  },
];

export const mockSafePick: SafePick = {
  fixtureId: 'fx-1',
  league: leagueL1,
  kickoffUtc: '2026-04-21T19:00:00Z',
  home: mockMatches[0].home,
  away: mockMatches[0].away,
  betLabel: 'PSG gagne vs Lens',
  odd: 1.92,
  probability: 0.58,
  justification: "PSG enchaîne 5 victoires à domicile avec xG moyen 2.3. Lens absent de ses 3 cadres défensifs. Valeur cote 1.92 vs proba 58% → edge 4.9%.",
};

export const mockPerformance: Perf = {
  roi30d: { value: 12.4, deltaVs7d: 0.8 },
  accuracy: { value: 54.2, deltaVs7d: -0.3 },
  brier7d: { value: 0.189, deltaVs7d: -0.004 },
  bankroll: { value: 1240, currency: 'EUR' },
};
```

- [ ] Écrire `src/test/mocks/handlers.ts` :

```ts
// src/test/mocks/handlers.ts
import { http, HttpResponse } from 'msw';
import { mockMatches, mockSafePick, mockPerformance } from './fixtures';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const handlers = [
  http.get(`${API}/api/safe-pick`, () => HttpResponse.json(mockSafePick)),
  http.get(`${API}/api/matches`, ({ request }) => {
    const url = new URL(request.url);
    const sports = url.searchParams.get('sports')?.split(',');
    const valueOnly = url.searchParams.get('value_only') === 'true';
    let matches = mockMatches;
    if (sports && sports.length) {
      matches = matches.filter((m) => sports.includes(m.sport));
    }
    if (valueOnly) {
      matches = matches.filter((m) => m.signals.includes('value'));
    }
    const counts = {
      total: matches.length,
      bySport: { football: matches.filter((m) => m.sport === 'football').length, nhl: matches.filter((m) => m.sport === 'nhl').length },
      byLeague: matches.reduce<Record<string, number>>((acc, m) => {
        acc[m.league.id] = (acc[m.league.id] ?? 0) + 1;
        return acc;
      }, {}),
    };
    return HttpResponse.json({ date: url.searchParams.get('date') ?? '2026-04-21', matches, counts });
  }),
  http.get(`${API}/api/performance/summary`, () => HttpResponse.json(mockPerformance)),
];
```

- [ ] Écrire `src/test/mocks/server.ts` :

```ts
// src/test/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

- [ ] Modifier `src/test/setup.ts` pour ajouter le cycle MSW :

```ts
import { server } from './mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] Lancer `npm run test:ci` — tous les tests existants doivent rester verts (MSW actif mais handlers non sollicités).

- [ ] Commit : `chore(v2): add shared match/performance types and MSW handlers`.

---

## Task 2 · Hooks data : useSafePick, useMatchesOfDay, usePerformanceSummary

**Files:**
- `src/lib/v2/apiClient.ts` (nouveau — fetcher typé minimal)
- `src/hooks/v2/useSafePick.ts` (nouveau)
- `src/hooks/v2/useMatchesOfDay.ts` (nouveau)
- `src/hooks/v2/usePerformanceSummary.ts` (nouveau)
- `src/hooks/v2/useSafePick.test.ts` (nouveau)
- `src/hooks/v2/useMatchesOfDay.test.ts` (nouveau)
- `src/hooks/v2/usePerformanceSummary.test.ts` (nouveau)
- `src/test/utils.tsx` (nouveau — helper `renderWithQuery`)

**Règle de non-duplication :** ces hooks sont définis UNE SEULE FOIS ici et importés partout (Home, Matches). Aucune autre Task ne les redéfinit.

**Steps:**

- [ ] Écrire `src/lib/v2/apiClient.ts` :

```ts
// src/lib/v2/apiClient.ts
const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function apiGet<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), { credentials: 'include' });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}
```

- [ ] Écrire `src/test/utils.tsx` :

```tsx
// src/test/utils.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
}

export function renderWithQuery(ui: ReactElement, options?: RenderOptions) {
  const client = makeQueryClient();
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { ...render(ui, { wrapper: Wrapper, ...options }), client };
}

export function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', { value: width, configurable: true });
  window.dispatchEvent(new Event('resize'));
}
```

- [ ] **TDD** : écrire `src/hooks/v2/useSafePick.test.ts` (failing) :

```ts
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useSafePick } from './useSafePick';

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useSafePick', () => {
  it('fetches the safe pick for a given date', async () => {
    const { result } = renderHook(() => useSafePick('2026-04-21'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.betLabel).toBe('PSG gagne vs Lens');
    expect(result.current.data?.odd).toBe(1.92);
  });
});
```

- [ ] Implémenter `src/hooks/v2/useSafePick.ts` :

```ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { SafePick } from '@/types/v2/matches';

export function useSafePick(date: string) {
  return useQuery({
    queryKey: ['v2', 'safe-pick', date],
    queryFn: () => apiGet<SafePick>('/api/safe-pick', { date }),
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] Lancer `npm run test:ci -- useSafePick`. Vert. Commit : `feat(v2/hooks): add useSafePick with TanStack Query`.

- [ ] **TDD** : `src/hooks/v2/useMatchesOfDay.test.ts` :

```ts
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMatchesOfDay } from './useMatchesOfDay';

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useMatchesOfDay', () => {
  it('fetches all matches for a date', async () => {
    const { result } = renderHook(() => useMatchesOfDay({ date: '2026-04-21' }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.matches).toHaveLength(3);
    expect(result.current.data?.counts.total).toBe(3);
  });

  it('applies valueOnly filter to query params', async () => {
    const { result } = renderHook(
      () => useMatchesOfDay({ date: '2026-04-21', valueOnly: true }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.matches.every((m) => m.signals.includes('value'))).toBe(true);
  });

  it('applies sports filter', async () => {
    const { result } = renderHook(
      () => useMatchesOfDay({ date: '2026-04-21', sports: ['football'] }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.matches.every((m) => m.sport === 'football')).toBe(true);
  });
});
```

- [ ] Implémenter `src/hooks/v2/useMatchesOfDay.ts` :

```ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { MatchesFilters, MatchesResponse } from '@/types/v2/matches';

export function useMatchesOfDay(filters: MatchesFilters) {
  return useQuery({
    queryKey: ['v2', 'matches', filters],
    queryFn: () => apiGet<MatchesResponse>('/api/matches', {
      date: filters.date,
      sports: filters.sports?.join(','),
      leagues: filters.leagues?.join(','),
      signals: filters.signals?.join(','),
      value_only: filters.valueOnly ? 'true' : undefined,
      sort: filters.sort,
    }),
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] Vert. Commit : `feat(v2/hooks): add useMatchesOfDay with filters`.

- [ ] **TDD** : `src/hooks/v2/usePerformanceSummary.test.ts` :

```ts
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePerformanceSummary } from './usePerformanceSummary';

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('usePerformanceSummary', () => {
  it('fetches KPIs for the stat strip', async () => {
    const { result } = renderHook(() => usePerformanceSummary(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.roi30d.value).toBeCloseTo(12.4);
    expect(result.current.data?.bankroll.currency).toBe('EUR');
  });
});
```

- [ ] Implémenter `src/hooks/v2/usePerformanceSummary.ts` :

```ts
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';
import type { PerformanceSummary } from '@/types/v2/performance';

export function usePerformanceSummary() {
  return useQuery({
    queryKey: ['v2', 'performance', 'summary'],
    queryFn: () => apiGet<PerformanceSummary>('/api/performance/summary', { window: '30' }),
    staleTime: 5 * 60 * 1000,
  });
}
```

- [ ] Vert. Commit : `feat(v2/hooks): add usePerformanceSummary for stat strip`.

---

## Task 3 · `StatStrip` (composant dashboard Accueil)

**Files:**
- `src/components/v2/home/StatStrip.tsx` (nouveau)
- `src/components/v2/home/StatStrip.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** : `StatStrip.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { StatStrip } from './StatStrip';
import type { PerformanceSummary } from '@/types/v2/performance';

expect.extend(toHaveNoViolations);

const data: PerformanceSummary = {
  roi30d: { value: 12.4, deltaVs7d: 0.8 },
  accuracy: { value: 54.2, deltaVs7d: -0.3 },
  brier7d: { value: 0.189, deltaVs7d: -0.004 },
  bankroll: { value: 1240, currency: 'EUR' },
};

describe('StatStrip', () => {
  it('renders 4 stat tiles with labels and values', () => {
    render(<StatStrip data={data} />);
    expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument();
    expect(screen.getByText(/12\.4%/)).toBeInTheDocument();
    expect(screen.getByText(/Accuracy/i)).toBeInTheDocument();
    expect(screen.getByText(/54\.2%/)).toBeInTheDocument();
    expect(screen.getByText(/Brier 7J/i)).toBeInTheDocument();
    expect(screen.getByText(/Bankroll/i)).toBeInTheDocument();
    expect(screen.getByText(/1\s?240/)).toBeInTheDocument();
  });

  it('shows a skeleton when loading', () => {
    render(<StatStrip loading />);
    expect(screen.getAllByTestId('stat-tile-skeleton')).toHaveLength(4);
  });

  it('has no axe violations', async () => {
    const { container } = render(<StatStrip data={data} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `StatStrip.tsx` (réutilise `StatTile` du Lot 1) :

```tsx
import { StatTile } from '@/components/v2/system/StatTile';
import type { PerformanceSummary } from '@/types/v2/performance';

interface Props {
  data?: PerformanceSummary;
  loading?: boolean;
}

function formatDelta(v: number, suffix = '%'): string {
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(1)}${suffix} vs 7j`;
}

export function StatStrip({ data, loading }: Props) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} data-testid="stat-tile-skeleton" className="h-20 rounded-lg bg-surface-2 animate-pulse" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <StatTile label="ROI 30J" value={`${data.roi30d.value.toFixed(1)}%`} delta={formatDelta(data.roi30d.deltaVs7d)} tone={data.roi30d.value >= 0 ? 'positive' : 'negative'} />
      <StatTile label="Accuracy" value={`${data.accuracy.value.toFixed(1)}%`} delta={formatDelta(data.accuracy.deltaVs7d)} />
      <StatTile label="Brier 7J" value={data.brier7d.value.toFixed(3)} delta={formatDelta(data.brier7d.deltaVs7d, '')} tone={data.brier7d.deltaVs7d <= 0 ? 'positive' : 'negative'} />
      <StatTile label="Bankroll" value={`${data.bankroll.value.toLocaleString('fr-FR')} €`} />
    </div>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add StatStrip KPI grid`.

---

## Task 4 · `SafeOfTheDayCard`

**Files:**
- `src/components/v2/home/SafeOfTheDayCard.tsx` (nouveau)
- `src/components/v2/home/SafeOfTheDayCard.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** : test rendu + a11y + interaction lien :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { SafeOfTheDayCard } from './SafeOfTheDayCard';
import { mockSafePick } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function renderCard(props = {}) {
  return render(
    <MemoryRouter>
      <SafeOfTheDayCard data={mockSafePick} {...props} />
    </MemoryRouter>,
  );
}

describe('SafeOfTheDayCard', () => {
  it('displays the bet label, odd and justification', () => {
    renderCard();
    expect(screen.getByText('PSG gagne vs Lens')).toBeInTheDocument();
    expect(screen.getByText('1.92')).toBeInTheDocument();
    expect(screen.getByText(/xG moyen 2\.3/)).toBeInTheDocument();
  });

  it('shows probability as aria-labelled progress', () => {
    renderCard();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '58');
    expect(bar).toHaveAttribute('aria-label', expect.stringContaining('58%'));
  });

  it('links to match detail page when clicked', async () => {
    const user = userEvent.setup();
    renderCard();
    const link = screen.getByRole('link', { name: /voir le match/i });
    expect(link).toHaveAttribute('href', '/matchs/fx-1');
    await user.click(link);
  });

  it('renders a FREE chip', () => {
    renderCard();
    expect(screen.getByText(/FREE/)).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders an empty state when data is null', () => {
    render(<SafeOfTheDayCard data={null} />);
    expect(screen.getByText(/pas de pronostic safe/i)).toBeInTheDocument();
  });
});
```

- [ ] Implémenter `SafeOfTheDayCard.tsx` :

```tsx
import { Link } from 'react-router-dom';
import type { SafePick } from '@/types/v2/matches';

interface Props {
  data: SafePick | null;
}

export function SafeOfTheDayCard({ data }: Props) {
  if (!data) {
    return (
      <section className="rounded-xl border border-border bg-surface p-6 text-center">
        <p className="text-text-muted text-sm">Pas de pronostic Safe aujourd'hui — privilégiez l'analyse des matchs du soir.</p>
      </section>
    );
  }
  const pct = Math.round(data.probability * 100);
  return (
    <section
      className="rounded-xl border-l-4 border-l-primary p-6 shadow-sm"
      style={{ background: 'linear-gradient(135deg, var(--primary-soft) 0%, var(--surface) 70%)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium tracking-wide text-primary">★ SAFE · PRONOSTIC DU JOUR</span>
        <span className="rounded-full border border-border px-2 py-0.5 text-[11px] font-semibold text-text-muted">FREE</span>
      </div>
      <h3 className="text-lg font-semibold text-text">{data.betLabel}</h3>
      <div className="mt-3 flex items-baseline gap-4">
        <span className="text-[32px] font-bold tabular-nums text-primary">{data.odd.toFixed(2)}</span>
        <span className="text-sm text-text-muted">Probabilité {pct}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Probabilité ${data.betLabel} ${pct}%`}
        className="mt-2 h-1 w-full rounded-full bg-surface-2 overflow-hidden"
      >
        <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-4 text-sm text-text-muted leading-relaxed">{data.justification}</p>
      <Link
        to={`/matchs/${data.fixtureId}`}
        className="mt-4 inline-block text-sm font-medium text-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
      >
        Voir le match →
      </Link>
    </section>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add SafeOfTheDayCard with gradient hero`.

---

## Task 5 · `MatchRow` (composant partagé Home + Matches)

**Files:**
- `src/components/v2/home/MatchRow.tsx` (nouveau)
- `src/components/v2/home/MatchRow.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchRow } from './MatchRow';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function renderRow(match = mockMatches[0]) {
  return render(
    <MemoryRouter>
      <MatchRow match={match} />
    </MemoryRouter>,
  );
}

describe('MatchRow', () => {
  it('renders kickoff time, teams, and probabilities', () => {
    renderRow();
    expect(screen.getByText(/PSG/)).toBeInTheDocument();
    expect(screen.getByText(/LEN/)).toBeInTheDocument();
    expect(screen.getByText(/58%/)).toBeInTheDocument();
  });

  it('shows SAFE chip when signal present', () => {
    renderRow(mockMatches[0]);
    expect(screen.getByText(/SAFE/i)).toBeInTheDocument();
  });

  it('shows VALUE badge with edge when top value bet present', () => {
    renderRow(mockMatches[1]);
    expect(screen.getByText(/\+7\.2%/)).toBeInTheDocument();
  });

  it('exposes proba bar with comprehensive aria-label', () => {
    renderRow(mockMatches[0]);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-label', 'PSG 58%, Nul 24%, LEN 18%');
  });

  it('is a link to match detail', async () => {
    const user = userEvent.setup();
    renderRow();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/matchs/fx-1');
    await user.click(link);
  });

  it('has no axe violations', async () => {
    const { container } = renderRow();
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `MatchRow.tsx` :

```tsx
import { Link } from 'react-router-dom';
import { ProbBar } from '@/components/v2/system/ProbBar';
import { ValueBadge } from '@/components/v2/system/ValueBadge';
import type { MatchRowData } from '@/types/v2/matches';

interface Props {
  match: MatchRowData;
  variant?: 'mobile' | 'desktop';
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' });
}

export function MatchRow({ match, variant = 'mobile' }: Props) {
  const { prob1x2, home, away, signals, topValueBet } = match;
  const pct = {
    home: Math.round(prob1x2.home * 100),
    draw: Math.round(prob1x2.draw * 100),
    away: Math.round(prob1x2.away * 100),
  };
  const ariaLabel = `${home.short} ${pct.home}%, Nul ${pct.draw}%, ${away.short} ${pct.away}%`;

  return (
    <Link
      to={`/matchs/${match.fixtureId}`}
      className="flex items-center gap-3 rounded-lg px-3 py-3 hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary transition-colors"
      data-variant={variant}
    >
      <time className="w-12 shrink-0 text-xs tabular-nums text-text-muted">{fmtTime(match.kickoffUtc)}</time>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2 text-sm font-medium text-text">
          <span className="truncate">{home.short}</span>
          <span className="text-text-faint">vs</span>
          <span className="truncate text-right">{away.short}</span>
        </div>
        <ProbBar probs={prob1x2} ariaLabel={ariaLabel} className="mt-2" />
        <div className="mt-1 flex justify-between text-[11px] tabular-nums text-text-muted">
          <span>{pct.home}%</span>
          <span>{pct.draw}%</span>
          <span>{pct.away}%</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        {signals.includes('safe') && (
          <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-semibold text-primary">★ SAFE</span>
        )}
        {topValueBet && <ValueBadge edgePct={topValueBet.edgePct} />}
      </div>
    </Link>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add shared MatchRow component`.

---

## Task 6 · `MatchesList` (groupée par ligue)

**Files:**
- `src/components/v2/home/MatchesList.tsx` (nouveau)
- `src/components/v2/home/MatchesList.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchesList } from './MatchesList';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('MatchesList', () => {
  it('groups matches by league with colored header', () => {
    render(<MemoryRouter><MatchesList matches={mockMatches} /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: /Ligue 1/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Premier League/ })).toBeInTheDocument();
  });

  it('renders each match as a link', () => {
    render(<MemoryRouter><MatchesList matches={mockMatches} /></MemoryRouter>);
    expect(screen.getAllByRole('link')).toHaveLength(mockMatches.length);
  });

  it('shows empty state when list is empty', () => {
    render(<MemoryRouter><MatchesList matches={[]} /></MemoryRouter>);
    expect(screen.getByText(/Aucun match/i)).toBeInTheDocument();
  });

  it('warns (console) but still renders when >50 matches', () => {
    const big = Array.from({ length: 55 }, (_, i) => ({ ...mockMatches[0], fixtureId: `fx-big-${i}` }));
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(<MemoryRouter><MatchesList matches={big} /></MemoryRouter>);
    expect(spy).toHaveBeenCalledWith(expect.stringContaining('virtualization'));
    spy.mockRestore();
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><MatchesList matches={mockMatches} /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `MatchesList.tsx` :

```tsx
import { useEffect, useMemo } from 'react';
import { MatchRow } from './MatchRow';
import type { MatchRowData } from '@/types/v2/matches';

interface Props {
  matches: MatchRowData[];
}

export function MatchesList({ matches }: Props) {
  useEffect(() => {
    if (matches.length > 50) {
      console.warn(`[MatchesList] ${matches.length} rows rendered without virtualization — consider react-window`);
    }
  }, [matches.length]);

  const grouped = useMemo(() => {
    const map = new Map<string, { league: MatchRowData['league']; items: MatchRowData[] }>();
    for (const m of matches) {
      const g = map.get(m.league.id) ?? { league: m.league, items: [] };
      g.items.push(m);
      map.set(m.league.id, g);
    }
    return Array.from(map.values());
  }, [matches]);

  if (matches.length === 0) {
    return <p className="rounded-lg border border-border bg-surface p-6 text-center text-sm text-text-muted">Aucun match programmé.</p>;
  }

  return (
    <div className="space-y-4">
      {grouped.map(({ league, items }) => (
        <section key={league.id} className="rounded-xl border border-border bg-surface overflow-hidden">
          <h3
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
            style={{ backgroundColor: league.color }}
          >
            {league.name}
            <span className="ml-auto text-[11px] opacity-80">{items.length}</span>
          </h3>
          <ul className="divide-y divide-border">
            {items.map((m) => (
              <li key={m.fixtureId}><MatchRow match={m} /></li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add MatchesList grouped by league`.

---

## Task 7 · `ValueBetsTeaser` + `PremiumCTA`

**Files:**
- `src/components/v2/home/ValueBetsTeaser.tsx` (nouveau)
- `src/components/v2/home/ValueBetsTeaser.test.tsx` (nouveau)
- `src/components/v2/home/PremiumCTA.tsx` (nouveau)
- `src/components/v2/home/PremiumCTA.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** `ValueBetsTeaser.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ValueBetsTeaser } from './ValueBetsTeaser';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('ValueBetsTeaser', () => {
  it('renders up to 2 value bets with edge and Kelly', () => {
    render(<MemoryRouter><ValueBetsTeaser matches={mockMatches} /></MemoryRouter>);
    expect(screen.getAllByText(/Edge/)).toHaveLength(2);
  });

  it('blurs the second item for free users', () => {
    render(<MemoryRouter><ValueBetsTeaser matches={mockMatches} gating="free" /></MemoryRouter>);
    expect(screen.getByTestId('value-bet-locked')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><ValueBetsTeaser matches={mockMatches} /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `ValueBetsTeaser.tsx` :

```tsx
import { Link } from 'react-router-dom';
import { LockOverlay } from '@/components/v2/system/LockOverlay';
import type { MatchRowData } from '@/types/v2/matches';

interface Props {
  matches: MatchRowData[];
  gating?: 'free' | 'trial' | 'premium';
}

export function ValueBetsTeaser({ matches, gating = 'premium' }: Props) {
  const items = matches.filter((m) => m.topValueBet).slice(0, 2);
  if (items.length === 0) return null;
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold text-text mb-3">⚡ Value bets du jour</h3>
      <ul className="space-y-2">
        {items.map((m, idx) => {
          const vb = m.topValueBet!;
          const locked = gating === 'free' && idx > 0;
          const content = (
            <Link to={`/matchs/${m.fixtureId}`} className="flex items-center justify-between gap-2 text-sm">
              <span className="truncate">{m.home.short} vs {m.away.short} · {vb.market}</span>
              <span className="shrink-0 tabular-nums text-value">+{vb.edgePct.toFixed(1)}% · Kelly {vb.kellyPct.toFixed(1)}%</span>
            </Link>
          );
          return (
            <li key={m.fixtureId} data-testid={locked ? 'value-bet-locked' : undefined}>
              {locked ? <LockOverlay>{content}</LockOverlay> : content}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add ValueBetsTeaser sidebar widget`.

- [ ] **TDD** `PremiumCTA.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { PremiumCTA } from './PremiumCTA';

expect.extend(toHaveNoViolations);

describe('PremiumCTA', () => {
  it('renders heading and CTA link to /premium', () => {
    render(<MemoryRouter><PremiumCTA /></MemoryRouter>);
    const cta = screen.getByRole('link', { name: /Passer en Premium/i });
    expect(cta).toHaveAttribute('href', '/premium');
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><PremiumCTA /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `PremiumCTA.tsx` :

```tsx
import { Link } from 'react-router-dom';

export function PremiumCTA() {
  return (
    <section className="rounded-xl border border-value/40 bg-value/5 p-5">
      <h3 className="text-sm font-semibold text-value">Débloque tout avec Premium</h3>
      <p className="mt-1 text-xs text-text-muted">Value bets illimités, analyses IA, bankroll, alertes custom.</p>
      <Link
        to="/premium"
        className="mt-3 inline-flex items-center justify-center rounded-md bg-value px-4 py-2 text-sm font-semibold text-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-value"
      >
        Passer en Premium →
      </Link>
    </section>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add PremiumCTA amber card`.

---

## Task 8 · `PreviewBlurMatches` + `HeroLanding` (landing non-connecté)

**Files:**
- `src/components/v2/home/PreviewBlurMatches.tsx` (nouveau)
- `src/components/v2/home/PreviewBlurMatches.test.tsx` (nouveau)
- `src/components/v2/home/HeroLanding.tsx` (nouveau)
- `src/components/v2/home/HeroLanding.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** `PreviewBlurMatches.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { PreviewBlurMatches } from './PreviewBlurMatches';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('PreviewBlurMatches', () => {
  it('renders 3 blurred match rows with a create-account overlay', () => {
    render(<MemoryRouter><PreviewBlurMatches matches={mockMatches} /></MemoryRouter>);
    expect(screen.getAllByTestId('preview-blur-row')).toHaveLength(3);
    expect(screen.getByRole('link', { name: /Créer un compte/i })).toHaveAttribute('href', '/register');
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><PreviewBlurMatches matches={mockMatches} /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `PreviewBlurMatches.tsx` :

```tsx
import { Link } from 'react-router-dom';
import type { MatchRowData } from '@/types/v2/matches';

interface Props { matches: MatchRowData[]; }

export function PreviewBlurMatches({ matches }: Props) {
  const preview = matches.slice(0, 3);
  return (
    <section className="relative rounded-xl border border-border bg-surface p-4">
      <ul className="space-y-2" aria-hidden>
        {preview.map((m) => (
          <li key={m.fixtureId} data-testid="preview-blur-row" className="flex items-center gap-3 py-2 blur-sm">
            <span className="text-xs text-text-muted">{new Date(m.kickoffUtc).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
            <span className="text-sm">{m.home.short} vs {m.away.short}</span>
            <span className="ml-auto text-sm tabular-nums">{Math.round(m.prob1x2.home * 100)}% / {Math.round(m.prob1x2.draw * 100)}% / {Math.round(m.prob1x2.away * 100)}%</span>
          </li>
        ))}
      </ul>
      <div className="absolute inset-0 flex items-center justify-center">
        <Link
          to="/register"
          className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          Créer un compte pour voir
        </Link>
      </div>
    </section>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add PreviewBlurMatches for visitor landing`.

- [ ] **TDD** `HeroLanding.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { HeroLanding } from './HeroLanding';

expect.extend(toHaveNoViolations);

describe('HeroLanding', () => {
  it('renders the headline and a primary CTA to /register', () => {
    render(<MemoryRouter><HeroLanding /></MemoryRouter>);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/vraie probabilité/i);
    expect(screen.getByRole('link', { name: /Essai gratuit 30 jours/i })).toHaveAttribute('href', '/register');
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><HeroLanding /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `HeroLanding.tsx` :

```tsx
import { Link } from 'react-router-dom';

export function HeroLanding() {
  return (
    <section className="py-12 md:py-20 text-center">
      <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-text">
        Parier avec une vraie probabilité, pas un feeling.
      </h1>
      <p className="mt-4 max-w-xl mx-auto text-base text-text-muted">
        Le seul pronostiqueur français qui publie son CLV vs Pinnacle en temps réel.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link
          to="/register"
          className="rounded-md bg-primary px-5 py-3 text-sm font-semibold text-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          Essai gratuit 30 jours →
        </Link>
        <Link
          to="/premium"
          className="rounded-md border border-border px-5 py-3 text-sm font-semibold text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          Voir le track record
        </Link>
      </div>
      <p className="mt-4 text-xs text-text-faint">Sans engagement · Aucune carte bancaire requise</p>
    </section>
  );
}
```

- [ ] Vert. Commit : `feat(v2/home): add HeroLanding marketing block`.

---

## Task 9 · Page `HomeV2` (assemble tout)

**Files:**
- `src/pages/v2/HomeV2.tsx` (modifié : remplace le stub Lot 1)
- `src/pages/v2/HomeV2.test.tsx` (modifié ou créé)

**Steps:**

- [ ] **TDD** `HomeV2.test.tsx` couvre les deux modes :

```tsx
import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { renderWithQuery, setViewportWidth } from '@/test/utils';
import { HomeV2 } from './HomeV2';
import * as auth from '@/hooks/v2/useAuthState';

function withRouter(ui: React.ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe('HomeV2', () => {
  it('shows landing mode for visitors', async () => {
    vi.spyOn(auth, 'useAuthState').mockReturnValue({ status: 'visitor' });
    renderWithQuery(withRouter(<HomeV2 />));
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/vraie probabilité/i);
    expect(screen.queryByText(/ROI 30J/i)).not.toBeInTheDocument();
  });

  it('shows dashboard mode for connected users', async () => {
    vi.spyOn(auth, 'useAuthState').mockReturnValue({ status: 'trial', trialDaysLeft: 18 });
    renderWithQuery(withRouter(<HomeV2 />));
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(await screen.findByText('PSG gagne vs Lens')).toBeInTheDocument();
  });

  it('renders mobile layout at 375px', async () => {
    setViewportWidth(375);
    vi.spyOn(auth, 'useAuthState').mockReturnValue({ status: 'free' });
    renderWithQuery(withRouter(<HomeV2 />));
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    // right column is rendered inline, not sticky
    expect(screen.getByTestId('home-right-col')).toHaveAttribute('data-layout', 'inline');
  });

  it('renders desktop layout at 1280px', async () => {
    setViewportWidth(1280);
    vi.spyOn(auth, 'useAuthState').mockReturnValue({ status: 'premium' });
    renderWithQuery(withRouter(<HomeV2 />));
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(screen.getByTestId('home-right-col')).toHaveAttribute('data-layout', 'sticky');
  });
});
```

- [ ] Implémenter `HomeV2.tsx` :

```tsx
import { useAuthState } from '@/hooks/v2/useAuthState';
import { useSafePick } from '@/hooks/v2/useSafePick';
import { useMatchesOfDay } from '@/hooks/v2/useMatchesOfDay';
import { usePerformanceSummary } from '@/hooks/v2/usePerformanceSummary';
import { HeroLanding } from '@/components/v2/home/HeroLanding';
import { PreviewBlurMatches } from '@/components/v2/home/PreviewBlurMatches';
import { StatStrip } from '@/components/v2/home/StatStrip';
import { SafeOfTheDayCard } from '@/components/v2/home/SafeOfTheDayCard';
import { MatchesList } from '@/components/v2/home/MatchesList';
import { ValueBetsTeaser } from '@/components/v2/home/ValueBetsTeaser';
import { PremiumCTA } from '@/components/v2/home/PremiumCTA';
import { useEffect, useState } from 'react';

const DESKTOP_BREAKPOINT = 1024;

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(() => window.innerWidth >= DESKTOP_BREAKPOINT);
  useEffect(() => {
    const onResize = () => setIsDesktop(window.innerWidth >= DESKTOP_BREAKPOINT);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return isDesktop;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function HomeV2() {
  const auth = useAuthState();
  const date = todayIso();
  const safe = useSafePick(date);
  const matches = useMatchesOfDay({ date });
  const perf = usePerformanceSummary();
  const isDesktop = useIsDesktop();

  if (auth.status === 'visitor') {
    return (
      <main className="mx-auto max-w-5xl px-4 md:px-8">
        <HeroLanding />
        {matches.data && <PreviewBlurMatches matches={matches.data.matches} />}
      </main>
    );
  }

  const gating = auth.status === 'free' ? 'free' : 'premium';

  const rightCol = (
    <div
      data-testid="home-right-col"
      data-layout={isDesktop ? 'sticky' : 'inline'}
      className={isDesktop ? 'sticky top-6 space-y-4' : 'space-y-4'}
    >
      {safe.data && isDesktop && <SafeOfTheDayCard data={safe.data} />}
      {matches.data && <ValueBetsTeaser matches={matches.data.matches} gating={gating} />}
      {auth.status !== 'premium' && <PremiumCTA />}
    </div>
  );

  return (
    <main className="mx-auto max-w-7xl px-4 md:px-8 py-6 space-y-6">
      <StatStrip data={perf.data} loading={perf.isLoading} />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <SafeOfTheDayCard data={safe.data ?? null} />
          <section>
            <h2 className="mb-3 text-lg font-semibold text-text">Matchs du soir</h2>
            <MatchesList matches={matches.data?.matches ?? []} />
          </section>
        </div>
        <aside>{rightCol}</aside>
      </div>
    </main>
  );
}
```

Note : `SafeOfTheDayCard` apparaît deux fois (col gauche mobile + sticky droite desktop) — la duplication est intentionnelle comme demandé par la spec section 6. On cache la version droite en mobile (`isDesktop && ...`).

- [ ] Vert. Commit : `feat(v2/home): assemble HomeV2 landing + dashboard modes`.

---

## Task 10 · `SportChips` + `DateScroller` + `ValueOnlyToggle`

**Files:**
- `src/components/v2/matches/SportChips.tsx` / `.test.tsx`
- `src/components/v2/matches/DateScroller.tsx` / `.test.tsx`
- `src/components/v2/matches/ValueOnlyToggle.tsx` / `.test.tsx`

**Steps:**

- [ ] **TDD** `SportChips.test.tsx` :

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { SportChips } from './SportChips';

expect.extend(toHaveNoViolations);

describe('SportChips', () => {
  it('renders All / Football / NHL with counts', () => {
    render(<SportChips value={[]} counts={{ football: 8, nhl: 2 }} onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /Tous/ })).toHaveTextContent('10');
    expect(screen.getByRole('button', { name: /Foot/ })).toHaveTextContent('8');
    expect(screen.getByRole('button', { name: /NHL/ })).toHaveTextContent('2');
  });

  it('calls onChange with toggled sport', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SportChips value={[]} counts={{ football: 8, nhl: 2 }} onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /Foot/ }));
    expect(onChange).toHaveBeenCalledWith(['football']);
  });

  it('sets aria-pressed on active chips', () => {
    render(<SportChips value={['football']} counts={{ football: 8, nhl: 2 }} onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /Foot/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('has no axe violations', async () => {
    const { container } = render(<SportChips value={[]} counts={{ football: 0, nhl: 0 }} onChange={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `SportChips.tsx` :

```tsx
import type { Sport } from '@/types/v2/matches';

interface Props {
  value: Sport[];
  counts: Record<Sport, number>;
  onChange: (next: Sport[]) => void;
}

const OPTIONS: { id: Sport | 'all'; label: string }[] = [
  { id: 'all', label: 'Tous' },
  { id: 'football', label: '⚽ Foot' },
  { id: 'nhl', label: '🏒 NHL' },
];

export function SportChips({ value, counts, onChange }: Props) {
  const total = counts.football + counts.nhl;
  return (
    <div role="group" aria-label="Filtre sport" className="flex gap-2 overflow-x-auto">
      {OPTIONS.map((opt) => {
        const active = opt.id === 'all' ? value.length === 0 : value.includes(opt.id);
        const count = opt.id === 'all' ? total : counts[opt.id];
        return (
          <button
            key={opt.id}
            type="button"
            aria-pressed={active}
            onClick={() => {
              if (opt.id === 'all') return onChange([]);
              const next = value.includes(opt.id) ? value.filter((v) => v !== opt.id) : [...value, opt.id];
              onChange(next);
            }}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${active ? 'border-primary bg-primary-soft text-primary' : 'border-border text-text-muted hover:border-text-muted'}`}
          >
            {opt.label} <span className="ml-1 tabular-nums">{count}</span>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add SportChips filter`.

- [ ] **TDD** `DateScroller.test.tsx` :

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { DateScroller } from './DateScroller';

expect.extend(toHaveNoViolations);

describe('DateScroller', () => {
  it('renders a horizontal list from yesterday to +5 days', () => {
    render(<DateScroller value="2026-04-21" today="2026-04-21" onChange={() => {}} />);
    expect(screen.getAllByRole('button')).toHaveLength(7);
    expect(screen.getByRole('button', { name: /Aujourd'hui/i })).toHaveAttribute('aria-pressed', 'true');
  });

  it('calls onChange when another date is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DateScroller value="2026-04-21" today="2026-04-21" onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /Demain/i }));
    expect(onChange).toHaveBeenCalledWith('2026-04-22');
  });

  it('has no axe violations', async () => {
    const { container } = render(<DateScroller value="2026-04-21" today="2026-04-21" onChange={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `DateScroller.tsx` :

```tsx
interface Props {
  value: string;
  today: string;
  onChange: (iso: string) => void;
}

function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function label(iso: string, today: string): string {
  if (iso === today) return "Aujourd'hui";
  if (iso === addDays(today, -1)) return 'Hier';
  if (iso === addDays(today, 1)) return 'Demain';
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: 'short' });
}

export function DateScroller({ value, today, onChange }: Props) {
  const offsets = [-1, 0, 1, 2, 3, 4, 5];
  return (
    <div role="group" aria-label="Sélection de date" className="flex gap-2 overflow-x-auto py-2">
      {offsets.map((off) => {
        const iso = addDays(today, off);
        const active = iso === value;
        return (
          <button
            key={iso}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(iso)}
            className={`shrink-0 rounded-lg border px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${active ? 'border-primary bg-primary text-surface' : 'border-border text-text-muted'}`}
          >
            {label(iso, today)}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add DateScroller`.

- [ ] **TDD** `ValueOnlyToggle.test.tsx` :

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ValueOnlyToggle } from './ValueOnlyToggle';

expect.extend(toHaveNoViolations);

describe('ValueOnlyToggle', () => {
  it('is a toggle button reflecting value state', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ValueOnlyToggle value={false} onChange={onChange} />);
    const btn = screen.getByRole('switch', { name: /Value only/i });
    expect(btn).toHaveAttribute('aria-checked', 'false');
    await user.click(btn);
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('has no axe violations', async () => {
    const { container } = render(<ValueOnlyToggle value={false} onChange={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `ValueOnlyToggle.tsx` :

```tsx
interface Props { value: boolean; onChange: (v: boolean) => void; }

export function ValueOnlyToggle({ value, onChange }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={value}
      aria-label="Value only"
      onClick={() => onChange(!value)}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-value ${value ? 'border-value bg-value/10 text-value' : 'border-border text-text-muted'}`}
    >
      ⚡ Value only
    </button>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add ValueOnlyToggle`.

---

## Task 11 · `FilterSidebar` (desktop)

**Files:**
- `src/components/v2/matches/FilterSidebar.tsx` / `.test.tsx`

**Steps:**

- [ ] **TDD** :

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { FilterSidebar } from './FilterSidebar';

expect.extend(toHaveNoViolations);

const leagues = [
  { id: 'fr-l1', name: 'Ligue 1', country: 'FR', color: '#2563eb' },
  { id: 'en-pl', name: 'Premier League', country: 'EN', color: '#7c3aed' },
];

describe('FilterSidebar', () => {
  it('renders sport, league, signal sections and sort select', () => {
    render(<FilterSidebar leagues={leagues} filters={{ date: '2026-04-21' }} onChange={() => {}} />);
    expect(screen.getByRole('group', { name: /Sport/i })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: /Ligue/i })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: /Signaux/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /Tri/i })).toBeInTheDocument();
  });

  it('toggles a league checkbox and emits new filters', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterSidebar leagues={leagues} filters={{ date: '2026-04-21' }} onChange={onChange} />);
    await user.click(screen.getByRole('checkbox', { name: /Ligue 1/ }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ leagues: ['fr-l1'] }));
  });

  it('has no axe violations', async () => {
    const { container } = render(<FilterSidebar leagues={leagues} filters={{ date: '2026-04-21' }} onChange={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `FilterSidebar.tsx` :

```tsx
import type { LeagueRef, MatchesFilters, Sport, SignalKind } from '@/types/v2/matches';

interface Props {
  leagues: LeagueRef[];
  filters: MatchesFilters;
  onChange: (next: MatchesFilters) => void;
}

const SPORTS: { id: Sport; label: string }[] = [
  { id: 'football', label: '⚽ Football' },
  { id: 'nhl', label: '🏒 NHL' },
];

const SIGNALS: { id: SignalKind; label: string }[] = [
  { id: 'value', label: '⚡ Value ≥5%' },
  { id: 'safe', label: '★ Safe du jour' },
  { id: 'high_confidence', label: 'Confiance élevée' },
];

function toggle<T>(arr: T[] | undefined, v: T): T[] {
  const a = arr ?? [];
  return a.includes(v) ? a.filter((x) => x !== v) : [...a, v];
}

export function FilterSidebar({ leagues, filters, onChange }: Props) {
  return (
    <aside className="w-[220px] shrink-0 space-y-6">
      <fieldset>
        <legend className="mb-2 text-xs font-semibold uppercase text-text-faint">Sport</legend>
        <div role="group" aria-label="Sport" className="space-y-1">
          {SPORTS.map((s) => (
            <label key={s.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.sports?.includes(s.id) ?? false}
                onChange={() => onChange({ ...filters, sports: toggle(filters.sports, s.id) })}
              />
              {s.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-2 text-xs font-semibold uppercase text-text-faint">Ligue</legend>
        <div role="group" aria-label="Ligue" className="space-y-1">
          {leagues.map((l) => (
            <label key={l.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.leagues?.includes(l.id) ?? false}
                onChange={() => onChange({ ...filters, leagues: toggle(filters.leagues, l.id) })}
              />
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} />
              {l.name}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-2 text-xs font-semibold uppercase text-text-faint">Signaux</legend>
        <div role="group" aria-label="Signaux" className="space-y-1">
          {SIGNALS.map((s) => (
            <label key={s.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.signals?.includes(s.id) ?? false}
                onChange={() => onChange({ ...filters, signals: toggle(filters.signals, s.id) })}
              />
              {s.label}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="block text-sm">
        <span className="mb-1 block text-xs font-semibold uppercase text-text-faint">Tri</span>
        <select
          aria-label="Tri"
          value={filters.sort ?? 'kickoff'}
          onChange={(e) => onChange({ ...filters, sort: e.target.value as MatchesFilters['sort'] })}
          className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm"
        >
          <option value="kickoff">Heure</option>
          <option value="edge">Edge</option>
          <option value="confidence">Confiance</option>
          <option value="league">Ligue</option>
        </select>
      </label>
    </aside>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add desktop FilterSidebar`.

---

## Task 12 · `LeagueGroup` + `MatchesTableDesktop` + `MatchesListMobile`

**Files:**
- `src/components/v2/matches/LeagueGroup.tsx` / `.test.tsx`
- `src/components/v2/matches/MatchesTableDesktop.tsx` / `.test.tsx`
- `src/components/v2/matches/MatchesListMobile.tsx` / `.test.tsx`

**Steps:**

- [ ] **TDD** `LeagueGroup.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { LeagueGroup } from './LeagueGroup';
import { leagueL1 } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('LeagueGroup', () => {
  it('renders a coloured header with league name and count', () => {
    render(
      <LeagueGroup league={leagueL1} count={3}>
        <div>content</div>
      </LeagueGroup>,
    );
    const h = screen.getByRole('heading', { name: /Ligue 1/ });
    expect(h).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<LeagueGroup league={leagueL1} count={1}><div>x</div></LeagueGroup>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `LeagueGroup.tsx` :

```tsx
import type { ReactNode } from 'react';
import type { LeagueRef } from '@/types/v2/matches';

interface Props { league: LeagueRef; count: number; children: ReactNode; }

export function LeagueGroup({ league, count, children }: Props) {
  return (
    <section className="rounded-xl border border-border bg-surface overflow-hidden">
      <h3
        className="flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
        style={{ backgroundColor: league.color }}
      >
        {league.name}
        <span className="ml-auto text-[11px] tabular-nums opacity-80">{count}</span>
      </h3>
      {children}
    </section>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add LeagueGroup wrapper`.

- [ ] **TDD** `MatchesListMobile.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchesListMobile } from './MatchesListMobile';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('MatchesListMobile', () => {
  it('renders groups with their matches', () => {
    render(<MemoryRouter><MatchesListMobile matches={mockMatches} /></MemoryRouter>);
    expect(screen.getAllByRole('link')).toHaveLength(mockMatches.length);
    expect(screen.getByRole('heading', { name: /Ligue 1/ })).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<MemoryRouter><MatchesListMobile matches={[]} /></MemoryRouter>);
    expect(screen.getByText(/Aucun match/i)).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><MatchesListMobile matches={mockMatches} /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `MatchesListMobile.tsx` (réutilise `MatchRow` + `LeagueGroup`) :

```tsx
import { useMemo } from 'react';
import { LeagueGroup } from './LeagueGroup';
import { MatchRow } from '@/components/v2/home/MatchRow';
import type { MatchRowData } from '@/types/v2/matches';

interface Props { matches: MatchRowData[]; }

export function MatchesListMobile({ matches }: Props) {
  const grouped = useMemo(() => {
    const map = new Map<string, { league: MatchRowData['league']; items: MatchRowData[] }>();
    for (const m of matches) {
      const g = map.get(m.league.id) ?? { league: m.league, items: [] };
      g.items.push(m);
      map.set(m.league.id, g);
    }
    return Array.from(map.values());
  }, [matches]);

  if (matches.length === 0) {
    return <p className="rounded-lg border border-border bg-surface p-6 text-center text-sm text-text-muted">Aucun match pour cette date.</p>;
  }

  return (
    <div className="space-y-4">
      {grouped.map(({ league, items }) => (
        <LeagueGroup key={league.id} league={league} count={items.length}>
          <ul className="divide-y divide-border">
            {items.map((m) => <li key={m.fixtureId}><MatchRow match={m} variant="mobile" /></li>)}
          </ul>
        </LeagueGroup>
      ))}
    </div>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add MatchesListMobile`.

- [ ] **TDD** `MatchesTableDesktop.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchesTableDesktop } from './MatchesTableDesktop';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('MatchesTableDesktop', () => {
  it('renders a table with expected headers per league group', () => {
    render(<MemoryRouter><MatchesTableDesktop matches={mockMatches} /></MemoryRouter>);
    expect(screen.getAllByRole('table')).toHaveLength(2); // L1 + PL
    expect(screen.getAllByRole('columnheader', { name: /Heure/i }).length).toBeGreaterThan(0);
  });

  it('highlights value-bet rows with amber accent class', () => {
    render(<MemoryRouter><MatchesTableDesktop matches={mockMatches} /></MemoryRouter>);
    const highlighted = screen.getAllByTestId('match-row-value');
    expect(highlighted.length).toBeGreaterThanOrEqual(1);
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><MatchesTableDesktop matches={mockMatches} /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] Implémenter `MatchesTableDesktop.tsx` :

```tsx
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { LeagueGroup } from './LeagueGroup';
import { ProbBar } from '@/components/v2/system/ProbBar';
import { ValueBadge } from '@/components/v2/system/ValueBadge';
import type { MatchRowData } from '@/types/v2/matches';

interface Props { matches: MatchRowData[]; }

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' });
}

export function MatchesTableDesktop({ matches }: Props) {
  const grouped = useMemo(() => {
    const map = new Map<string, { league: MatchRowData['league']; items: MatchRowData[] }>();
    for (const m of matches) {
      const g = map.get(m.league.id) ?? { league: m.league, items: [] };
      g.items.push(m);
      map.set(m.league.id, g);
    }
    return Array.from(map.values());
  }, [matches]);

  if (matches.length === 0) {
    return <p className="rounded-lg border border-border bg-surface p-6 text-center text-sm text-text-muted">Aucun match pour cette date.</p>;
  }

  return (
    <div className="space-y-4">
      {grouped.map(({ league, items }) => (
        <LeagueGroup key={league.id} league={league} count={items.length}>
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-[11px] uppercase text-text-faint">
              <tr>
                <th scope="col" className="px-4 py-2 w-16">Heure</th>
                <th scope="col" className="px-4 py-2">Match</th>
                <th scope="col" className="px-4 py-2 w-64">Probabilités</th>
                <th scope="col" className="px-4 py-2 w-32">Signal</th>
                <th scope="col" className="px-4 py-2 w-40">Meilleure cote</th>
                <th scope="col" className="px-4 py-2 w-16 text-right">Détail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((m) => {
                const isValue = Boolean(m.topValueBet);
                const pct = {
                  h: Math.round(m.prob1x2.home * 100),
                  d: Math.round(m.prob1x2.draw * 100),
                  a: Math.round(m.prob1x2.away * 100),
                };
                const aria = `${m.home.short} ${pct.h}%, Nul ${pct.d}%, ${m.away.short} ${pct.a}%`;
                return (
                  <tr
                    key={m.fixtureId}
                    data-testid={isValue ? 'match-row-value' : undefined}
                    className={isValue ? 'bg-value/5' : ''}
                  >
                    <td className="px-4 py-2 tabular-nums text-text-muted">{fmtTime(m.kickoffUtc)}</td>
                    <td className="px-4 py-2 font-medium">{m.home.short} vs {m.away.short}</td>
                    <td className="px-4 py-2">
                      <ProbBar probs={m.prob1x2} ariaLabel={aria} />
                      <div className="mt-1 flex justify-between text-[11px] tabular-nums text-text-muted">
                        <span>{pct.h}%</span><span>{pct.d}%</span><span>{pct.a}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      {m.signals.includes('safe') && <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-semibold text-primary">★ SAFE</span>}
                      {m.topValueBet && <ValueBadge edgePct={m.topValueBet.edgePct} />}
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {m.topValueBet ? <span>{m.topValueBet.bestOdd.toFixed(2)} · {m.topValueBet.bestBook}</span> : <span className="text-text-faint">—</span>}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Link to={`/matchs/${m.fixtureId}`} className="text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">→</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </LeagueGroup>
      ))}
    </div>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): add MatchesTableDesktop dense view`.

---

## Task 13 · Page `MatchesV2` (assemble tout)

**Files:**
- `src/pages/v2/MatchesV2.tsx` (modifié : remplace le stub Lot 1)
- `src/pages/v2/MatchesV2.test.tsx` (nouveau)

**Steps:**

- [ ] **TDD** `MatchesV2.test.tsx` :

```tsx
import { describe, it, expect } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { renderWithQuery, setViewportWidth } from '@/test/utils';
import { MatchesV2 } from './MatchesV2';

function wrap(ui: React.ReactElement) { return <MemoryRouter>{ui}</MemoryRouter>; }

describe('MatchesV2', () => {
  it('renders mobile layout with SportChips, DateScroller and ValueOnlyToggle at 375px', async () => {
    setViewportWidth(375);
    renderWithQuery(wrap(<MatchesV2 />));
    await waitFor(() => expect(screen.getAllByRole('link').length).toBeGreaterThan(0));
    expect(screen.getByRole('switch', { name: /Value only/i })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: /^Ligue$/i })).not.toBeInTheDocument();
  });

  it('renders desktop layout with FilterSidebar at 1280px', async () => {
    setViewportWidth(1280);
    renderWithQuery(wrap(<MatchesV2 />));
    await waitFor(() => expect(screen.getAllByRole('table').length).toBeGreaterThan(0));
    expect(screen.getByRole('group', { name: /^Ligue$/i })).toBeInTheDocument();
  });

  it('filters by valueOnly via toggle', async () => {
    const user = userEvent.setup();
    setViewportWidth(375);
    renderWithQuery(wrap(<MatchesV2 />));
    await waitFor(() => expect(screen.getAllByRole('link').length).toBe(3));
    await user.click(screen.getByRole('switch', { name: /Value only/i }));
    await waitFor(() => expect(screen.getAllByRole('link').length).toBe(2));
  });
});
```

- [ ] Implémenter `MatchesV2.tsx` :

```tsx
import { useMemo, useState, useEffect } from 'react';
import { useMatchesOfDay } from '@/hooks/v2/useMatchesOfDay';
import { SportChips } from '@/components/v2/matches/SportChips';
import { DateScroller } from '@/components/v2/matches/DateScroller';
import { ValueOnlyToggle } from '@/components/v2/matches/ValueOnlyToggle';
import { FilterSidebar } from '@/components/v2/matches/FilterSidebar';
import { MatchesListMobile } from '@/components/v2/matches/MatchesListMobile';
import { MatchesTableDesktop } from '@/components/v2/matches/MatchesTableDesktop';
import type { MatchesFilters, LeagueRef } from '@/types/v2/matches';

const DESKTOP_BREAKPOINT = 1024;

function todayIso(): string { return new Date().toISOString().slice(0, 10); }

function useIsDesktop() {
  const [v, setV] = useState(() => window.innerWidth >= DESKTOP_BREAKPOINT);
  useEffect(() => {
    const onResize = () => setV(window.innerWidth >= DESKTOP_BREAKPOINT);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return v;
}

export function MatchesV2() {
  const today = todayIso();
  const [filters, setFilters] = useState<MatchesFilters>({ date: today });
  const { data } = useMatchesOfDay(filters);
  const isDesktop = useIsDesktop();

  const leagues: LeagueRef[] = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, LeagueRef>();
    for (const m of data.matches) map.set(m.league.id, m.league);
    return Array.from(map.values());
  }, [data]);

  const counts = data?.counts.bySport ?? { football: 0, nhl: 0 };

  return (
    <main className="mx-auto max-w-7xl px-4 md:px-8 py-6">
      <h1 className="mb-4 text-xl font-semibold text-text">Matchs</h1>

      <div className="mb-4 space-y-3">
        <SportChips
          value={filters.sports ?? []}
          counts={counts}
          onChange={(sports) => setFilters({ ...filters, sports: sports.length ? sports : undefined })}
        />
        <DateScroller value={filters.date} today={today} onChange={(d) => setFilters({ ...filters, date: d })} />
        {!isDesktop && (
          <ValueOnlyToggle
            value={Boolean(filters.valueOnly)}
            onChange={(v) => setFilters({ ...filters, valueOnly: v || undefined })}
          />
        )}
      </div>

      {isDesktop ? (
        <div className="flex gap-6">
          <FilterSidebar leagues={leagues} filters={filters} onChange={setFilters} />
          <div className="flex-1 min-w-0">
            <MatchesTableDesktop matches={data?.matches ?? []} />
          </div>
        </div>
      ) : (
        <MatchesListMobile matches={data?.matches ?? []} />
      )}
    </main>
  );
}
```

- [ ] Vert. Commit : `feat(v2/matches): assemble MatchesV2 with mobile + desktop layouts`.

---

## Task 14 · Vérifications finales du lot

**Files:** aucun nouveau — uniquement validation.

**Steps:**

- [ ] `cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/dashboard" && npm run test:ci` — tous les tests verts, MSW n'émet aucun warning `unhandled request`.
- [ ] `npm run lint` — 0 erreur.
- [ ] `npm run build` — bundle construit sans warning TypeScript. Vérifier que le chunk initial n'a pas grossi >50 Ko vs baseline Lot 1.
- [ ] Vérifier visuellement `npm run dev` :
  - [ ] `/` non-connecté (forcer `useAuthState` visitor en dev) : hero + preview blur + CTA register.
  - [ ] `/` connecté (trial) : TrialBanner Lot 1 visible + StatStrip + Safe + matchs groupés + sticky right col desktop.
  - [ ] `/matchs` mobile (devtools 375px) : chips sport + date scroller + toggle value only + liste mobile groupée.
  - [ ] `/matchs` desktop (1280px) : sidebar filtres + table dense, value rows en amber léger.
  - [ ] Lighthouse accessibility ≥ 95 sur `/` et `/matchs`.
- [ ] Supprimer les éventuelles console.warn résiduelles (hors virtualization warning volontaire).
- [ ] Ouvrir la PR Lot 3 sur base `feat/frontend-refonte-v1`.

---

## Critères d'acceptation Lot 3

- [ ] `HomeV2` rend les modes visitor/free/trial/premium conformément à la matrice section 3 du spec.
- [ ] `MatchesV2` bascule mobile/desktop à 1024px, sans layout shift notable.
- [ ] Tous les composants v2/home et v2/matches listés dans la section structure du Master sont livrés et testés (rendu + interactions + axe).
- [ ] Les hooks `useSafePick`, `useMatchesOfDay`, `usePerformanceSummary` sont déclarés une seule fois (Task 2) et réutilisés par les pages.
- [ ] MSW mocke les 3 endpoints backend pour tous les tests, sans requête réseau réelle en CI.
- [ ] `npm run test:ci`, `npm run lint`, `npm run build` verts.
- [ ] Zero console error/warn en prod (hors warning intentionnel >50 lignes).
- [ ] Matrice gating respectée : visitor voit preview flouté, free voit 1 value bet puis `LockOverlay`, trial/premium voient tout.
- [ ] Barres de probabilité ont un `aria-label` complet type `"PSG 58%, Nul 24%, LEN 18%"`.
- [ ] Aucun TODO/FIXME/XXX dans le code livré.

---

## Dépendances vers lots suivants

- Lot 4 (fiche match) réutilise `MatchRow`, `ValueBadge`, `ProbBar`, `useMatchesOfDay` (pour breadcrumb/navigation) et les types `MatchRowData`.
- Lot 5 (premium + compte) réutilise `StatTile` et pattern MSW mis en place ici.
- Lot 6 (migration) supprime les stubs legacy — `HomeV2` et `MatchesV2` deviennent les routes canoniques `/` et `/matchs`.
