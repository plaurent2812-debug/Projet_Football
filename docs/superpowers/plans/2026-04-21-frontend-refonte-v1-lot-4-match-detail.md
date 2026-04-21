# Plan d'implémentation — Lot 4 : Fiche match (Frontend Refonte V1)

**Auteur** : Claude (plan rédigé pour p.laurent2812@gmail.com)
**Date** : 2026-04-21
**Méthode** : TDD strict (RED → GREEN → REFACTOR), 1 commit par cycle
**Spec source** : `docs/superpowers/specs/2026-04-21-frontend-refonte-v1-design.md` §8
**Master plan** : `docs/superpowers/plans/2026-04-21-frontend-refonte-v1-MASTER.md`
**Prérequis** : Lots 1 (design system, `LockOverlay`, `ProbBar`, `BookOddsRow`, stub `MatchDetailV2`) et 2 (`useOddsComparison` + endpoints `/api/odds/:id/comparison`) mergés. Lot 3 peut être en cours.

---

## Objectif

Livrer la page `/matchs/:fixtureId` de la refonte V1 : layout responsive (mobile single-column, desktop 2-col avec colonne droite sticky), gating différencié visiteur / free / trial / premium, tous les blocs du produit (reco, odds compare, stats, H2H, IA, compositions, 14 marchés, value bets, sticky actions). Remplace le stub `MatchDetailV2` posé au Lot 1.

## Périmètre non fonctionnel

- Mobile-first (375px) → desktop (≥ 1024px) via breakpoint Tailwind `lg:`.
- Sticky colonne droite via `position: sticky; top: 20px` en CSS natif (pas de JS).
- Blur premium via Tailwind `blur-sm` + overlay `<LockOverlay>` (fourni Lot 1).
- Accessibilité : `aria-label` sur toutes les barres, `aria-label="Forme récente : V V N V V"` sur le form component, `aria-live="polite"` pour les mises à jour de cote.
- TypeScript strict. Pas de `any` implicite. Tout texte IA est rendu via React children (le moteur React escape automatiquement) — jamais d'injection HTML brute.
- 1 commit par cycle : `feat(v2/match-detail): <sujet>` — Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>.

## Arborescence livrée

```
dashboard/
  src/
    components/v2/match-detail/
      MatchHero.tsx
      MatchHero.test.tsx
      MatchHeroCompact.tsx
      MatchHeroCompact.test.tsx
      FormBadge.tsx
      FormBadge.test.tsx
      StatsComparative.tsx
      StatsComparative.test.tsx
      H2HSection.tsx
      H2HSection.test.tsx
      AIAnalysis.tsx
      AIAnalysis.test.tsx
      CompositionsSection.tsx
      CompositionsSection.test.tsx
      AllMarketsGrid.tsx
      AllMarketsGrid.test.tsx
      RecoCard.tsx
      RecoCard.test.tsx
      BookOddsList.tsx
      BookOddsList.test.tsx
      ValueBetsList.tsx
      ValueBetsList.test.tsx
      StickyActions.tsx
      StickyActions.test.tsx
      index.ts
    hooks/v2/
      useMatchDetail.ts
      useMatchDetail.test.ts
      useOddsComparison.ts          (déjà existant — Lot 2)
      useAnalysis.ts
      useAnalysis.test.ts
      useAddToBankroll.ts
      useAddToBankroll.test.ts
    pages/v2/
      MatchDetailV2.tsx              (remplace le stub)
      MatchDetailV2.test.tsx
    types/v2/
      match-detail.ts
```

## Types partagés (base contrat)

Fichier `dashboard/src/types/v2/match-detail.ts` — créé dans la Task 1. Toutes les tasks s'appuient sur ce fichier. Les noms de champs suivent la convention Supabase du backend (`fixture_id`, `home_team`, `away_team`, `kickoff_utc`).

```ts
export type UserRole = "visitor" | "free" | "trial" | "premium";

export type Outcome = "W" | "D" | "L";

export interface TeamInfo {
  id: number;
  name: string;
  logo_url: string;
  rank: number | null;
  form: Outcome[]; // 5 derniers, plus ancien -> plus récent
}

export interface MatchHeader {
  fixture_id: number;
  kickoff_utc: string; // ISO-8601
  stadium: string | null;
  league_name: string;
  home: TeamInfo;
  away: TeamInfo;
}

export interface ComparativeStat {
  label: string; // ex: "xG 5 derniers"
  home_value: number;
  away_value: number;
  unit?: string; // "%" ou null
}

export interface H2HSummary {
  home_wins: number;
  draws: number;
  away_wins: number;
  last_matches: Array<{
    date_utc: string;
    home_team: string;
    away_team: string;
    score: string;
  }>;
}

export interface AnalysisPayload {
  paragraphs: string[]; // Gemini, rendu en text nodes React uniquement
  generated_at: string;
}

export interface Lineup {
  formation: string; // "4-3-3"
  starters: Array<{ number: number; name: string; position: string }>;
}

export interface CompositionsPayload {
  home: Lineup | null;
  away: Lineup | null;
  status: "confirmed" | "probable" | "unavailable";
}

export interface MarketProb {
  market_key: string; // ex: "1x2.home", "btts.yes"
  label: string; // ex: "Victoire Nice"
  probability: number; // 0..1
  fair_odds: number;
  best_book_odds: number | null;
  is_value: boolean;
  edge: number | null; // 0..1
}

export interface BookOdd {
  bookmaker: string;
  odds: number;
  is_best: boolean;
  updated_at: string;
}

export interface Recommendation {
  market_key: string;
  market_label: string;
  odds: number;
  confidence: number; // 0..1
  kelly_fraction: number; // 0..1
  edge: number; // 0..1
  book_name: string;
}

export interface ValueBet {
  market_key: string;
  label: string;
  probability: number;
  best_odds: number;
  edge: number;
}

export interface MatchDetailPayload {
  header: MatchHeader;
  probs_1x2: { home: number; draw: number; away: number };
  stats: ComparativeStat[];
  h2h: H2HSummary;
  compositions: CompositionsPayload;
  all_markets: MarketProb[];
  recommendation: Recommendation | null;
  value_bets: ValueBet[];
}
```

## Matrice de gating (référence pour toutes les tasks)

| Bloc                 | visitor       | free          | trial | premium |
|----------------------|---------------|---------------|-------|---------|
| MatchHero            | visible       | visible       | vis.  | vis.    |
| ProbBar 1X2          | visible       | visible       | vis.  | vis.    |
| StatsComparative     | visible (basique) | visible   | vis.  | vis.    |
| RecoCard             | lock          | lock          | vis.  | vis.    |
| BookOddsList         | lock          | lock          | vis.  | vis.    |
| ValueBetsList        | lock          | 1 aperçu + lock autres | vis. | vis. |
| H2HSection           | lock          | visible       | vis.  | vis.    |
| AIAnalysis           | lock          | 1er § + blur | vis.  | vis.    |
| CompositionsSection  | lock          | visible       | vis.  | vis.    |
| AllMarketsGrid       | lock          | lock          | vis.  | vis.    |
| StickyActions        | hidden (CTA signup) | hidden (CTA upgrade) | vis. | vis. |

Le composant `<LockOverlay>` (Lot 1) prend la variante `variant: "signup" | "upgrade"` et un CTA href. Il est superposé en absolute sur un wrapper `relative blur-sm pointer-events-none`.

---

# Tasks

## Task 1 — Types + hook `useMatchDetail`

### Files
- `dashboard/src/types/v2/match-detail.ts` (nouveau)
- `dashboard/src/hooks/v2/useMatchDetail.ts` (nouveau)
- `dashboard/src/hooks/v2/useMatchDetail.test.ts` (nouveau)

### Steps
1. RED — écrire le test du hook : rend avec `QueryClientProvider`, mock `fetch`, attend `data.header.fixture_id === 42`.
2. GREEN — créer les types puis le hook.
3. Commit `feat(v2/match-detail): add types and useMatchDetail hook`.

### Test `useMatchDetail.test.ts`
```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { useMatchDetail } from "./useMatchDetail";

const wrapper = ({ children }: { children: ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("useMatchDetail", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches /api/predictions/:id and exposes data", async () => {
    const payload = {
      header: {
        fixture_id: 42,
        kickoff_utc: "2026-04-22T18:45:00Z",
        stadium: "Allianz Riviera",
        league_name: "Ligue 1",
        home: { id: 1, name: "Nice", logo_url: "/n.png", rank: 4, form: ["W", "W", "D", "W", "W"] },
        away: { id: 2, name: "Lens", logo_url: "/l.png", rank: 7, form: ["L", "D", "W", "L", "D"] },
      },
      probs_1x2: { home: 0.52, draw: 0.26, away: 0.22 },
      stats: [],
      h2h: { home_wins: 7, draws: 2, away_wins: 1, last_matches: [] },
      compositions: { home: null, away: null, status: "unavailable" },
      all_markets: [],
      recommendation: null,
      value_bets: [],
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );
    const { result } = renderHook(() => useMatchDetail(42), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.header.fixture_id).toBe(42);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/predictions/42", expect.any(Object));
  });

  it("does not fire when fixtureId is null", () => {
    const spy = vi.spyOn(globalThis, "fetch");
    renderHook(() => useMatchDetail(null), { wrapper });
    expect(spy).not.toHaveBeenCalled();
  });
});
```

### Implémentation `useMatchDetail.ts`
```ts
import { useQuery } from "@tanstack/react-query";
import type { MatchDetailPayload } from "../../types/v2/match-detail";

async function fetchMatchDetail(id: number, signal: AbortSignal): Promise<MatchDetailPayload> {
  const res = await fetch(`/api/predictions/${id}`, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as MatchDetailPayload;
}

export function useMatchDetail(fixtureId: number | null) {
  return useQuery({
    queryKey: ["match-detail", fixtureId],
    queryFn: ({ signal }) => fetchMatchDetail(fixtureId as number, signal),
    enabled: fixtureId != null,
    staleTime: 30_000,
  });
}
```

---

## Task 2 — Hook `useAnalysis`

### Files
- `dashboard/src/hooks/v2/useAnalysis.ts`
- `dashboard/src/hooks/v2/useAnalysis.test.ts`

### Steps
1. RED — test : appelle `/api/analysis/:id`, expose `data.paragraphs`.
2. GREEN — hook simple identique à `useMatchDetail`.
3. Commit `feat(v2/match-detail): add useAnalysis hook`.

### Test
```tsx
import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { useAnalysis } from "./useAnalysis";

const wrapper = ({ children }: { children: ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("useAnalysis", () => {
  it("fetches /api/analysis/:id", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ paragraphs: ["Nice domine.", "Lens solide."], generated_at: "2026-04-21T10:00:00Z" }), { status: 200 }),
    );
    const { result } = renderHook(() => useAnalysis(42), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.paragraphs).toHaveLength(2);
  });
});
```

### Implémentation
```ts
import { useQuery } from "@tanstack/react-query";
import type { AnalysisPayload } from "../../types/v2/match-detail";

export function useAnalysis(fixtureId: number | null) {
  return useQuery({
    queryKey: ["analysis", fixtureId],
    queryFn: async ({ signal }) => {
      const res = await fetch(`/api/analysis/${fixtureId}`, { signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return (await res.json()) as AnalysisPayload;
    },
    enabled: fixtureId != null,
    staleTime: 60_000,
  });
}
```

---

## Task 3 — Hook `useAddToBankroll`

### Files
- `dashboard/src/hooks/v2/useAddToBankroll.ts`
- `dashboard/src/hooks/v2/useAddToBankroll.test.ts`

### Steps
1. RED — test : mutate avec payload, vérifie POST `/api/user/bets`.
2. GREEN.
3. Commit `feat(v2/match-detail): add useAddToBankroll mutation`.

### Test
```tsx
import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { useAddToBankroll } from "./useAddToBankroll";

const wrapper = ({ children }: { children: ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("useAddToBankroll", () => {
  it("POSTs /api/user/bets with payload", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "bet_1" }), { status: 201 }),
    );
    const { result } = renderHook(() => useAddToBankroll(), { wrapper });
    result.current.mutate({ fixture_id: 42, market_key: "1x2.home", odds: 2.1, stake: 10 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith(
      "/api/user/bets",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
```

### Implémentation
```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";

export interface AddBetInput {
  fixture_id: number;
  market_key: string;
  odds: number;
  stake: number;
}

export function useAddToBankroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: AddBetInput) => {
      const res = await fetch("/api/user/bets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return (await res.json()) as { id: string };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bankroll"] });
    },
  });
}
```

---

## Task 4 — `FormBadge`

Petit composant réutilisé par `MatchHero` et `MatchHeroCompact`.

### Files
- `dashboard/src/components/v2/match-detail/FormBadge.tsx`
- `dashboard/src/components/v2/match-detail/FormBadge.test.tsx`

### Steps
1. RED — test aria-label `"Forme récente : V V N V V"` et couleurs.
2. GREEN.
3. Commit `feat(v2/match-detail): add FormBadge component`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FormBadge } from "./FormBadge";

describe("FormBadge", () => {
  it("renders aria-label with VND mapping", () => {
    render(<FormBadge form={["W", "W", "D", "W", "W"]} />);
    const el = screen.getByLabelText("Forme récente : V V N V V");
    expect(el).toBeInTheDocument();
  });

  it("applies color class per outcome", () => {
    render(<FormBadge form={["W", "L", "D", "W", "L"]} />);
    const badges = screen.getAllByTestId("form-dot");
    expect(badges[0].className).toMatch(/bg-emerald/);
    expect(badges[1].className).toMatch(/bg-rose/);
    expect(badges[2].className).toMatch(/bg-slate/);
  });
});
```

### Implémentation
```tsx
import type { Outcome } from "../../../types/v2/match-detail";

const COLOR: Record<Outcome, string> = {
  W: "bg-emerald-500",
  D: "bg-slate-400",
  L: "bg-rose-500",
};

export interface FormBadgeProps {
  form: Outcome[];
}

export function FormBadge({ form }: FormBadgeProps) {
  const readable = form.map((o) => (o === "W" ? "V" : o === "D" ? "N" : "V")).join(" ");
  return (
    <div
      role="img"
      aria-label={`Forme récente : ${readable}`}
      className="flex items-center gap-1"
    >
      {form.map((o, i) => (
        <span
          key={i}
          data-testid="form-dot"
          className={`inline-block h-2.5 w-2.5 rounded-full ${COLOR[o]}`}
        />
      ))}
    </div>
  );
}
```

---

## Task 5 — `MatchHero` (desktop)

### Files
- `dashboard/src/components/v2/match-detail/MatchHero.tsx`
- `dashboard/src/components/v2/match-detail/MatchHero.test.tsx`

### Steps
1. RED — test : logos 64px, noms équipes, rang, form, kickoff formaté, stade.
2. GREEN.
3. Commit `feat(v2/match-detail): add MatchHero desktop component`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MatchHero } from "./MatchHero";
import type { MatchHeader } from "../../../types/v2/match-detail";

const header: MatchHeader = {
  fixture_id: 42,
  kickoff_utc: "2026-04-22T18:45:00Z",
  stadium: "Allianz Riviera",
  league_name: "Ligue 1",
  home: { id: 1, name: "Nice", logo_url: "/n.png", rank: 4, form: ["W", "W", "D", "W", "W"] },
  away: { id: 2, name: "Lens", logo_url: "/l.png", rank: 7, form: ["L", "D", "W", "L", "D"] },
};

describe("MatchHero", () => {
  it("renders team names and rank", () => {
    render(<MatchHero header={header} />);
    expect(screen.getByText("Nice")).toBeInTheDocument();
    expect(screen.getByText("Lens")).toBeInTheDocument();
    expect(screen.getByText(/#4/)).toBeInTheDocument();
    expect(screen.getByText(/#7/)).toBeInTheDocument();
  });

  it("renders logos at 64px", () => {
    render(<MatchHero header={header} />);
    const imgs = screen.getAllByRole("img", { name: /logo/i });
    expect(imgs[0]).toHaveAttribute("width", "64");
    expect(imgs[0]).toHaveAttribute("height", "64");
  });

  it("renders stadium when present", () => {
    render(<MatchHero header={header} />);
    expect(screen.getByText(/Allianz Riviera/)).toBeInTheDocument();
  });
});
```

### Implémentation
```tsx
import type { MatchHeader } from "../../../types/v2/match-detail";
import { FormBadge } from "./FormBadge";

function formatKickoff(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "full",
    timeStyle: "short",
    timeZone: "Europe/Paris",
  }).format(d);
}

export interface MatchHeroProps {
  header: MatchHeader;
}

export function MatchHero({ header }: MatchHeroProps) {
  const { home, away, kickoff_utc, stadium, league_name } = header;
  return (
    <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-500">{league_name}</div>
      <div className="mt-4 flex items-center justify-between gap-6">
        <TeamBlock team={home} align="right" />
        <div className="flex flex-col items-center text-center">
          <div className="text-sm font-medium text-slate-700">{formatKickoff(kickoff_utc)}</div>
          {stadium && <div className="text-xs text-slate-500">{stadium}</div>}
          <div className="mt-2 text-2xl font-bold text-slate-900">VS</div>
        </div>
        <TeamBlock team={away} align="left" />
      </div>
    </header>
  );
}

function TeamBlock({ team, align }: { team: MatchHeader["home"]; align: "left" | "right" }) {
  return (
    <div className={`flex flex-1 items-center gap-4 ${align === "right" ? "justify-end" : "justify-start"}`}>
      {align === "left" && <img src={team.logo_url} alt={`${team.name} logo`} width={64} height={64} />}
      <div className={align === "right" ? "text-right" : "text-left"}>
        <div className="text-lg font-semibold text-slate-900">{team.name}</div>
        {team.rank != null && <div className="text-xs text-slate-500">#{team.rank}</div>}
        <div className="mt-1"><FormBadge form={team.form} /></div>
      </div>
      {align === "right" && <img src={team.logo_url} alt={`${team.name} logo`} width={64} height={64} />}
    </div>
  );
}
```

---

## Task 6 — `MatchHeroCompact` (mobile)

### Files
- `dashboard/src/components/v2/match-detail/MatchHeroCompact.tsx`
- `dashboard/src/components/v2/match-detail/MatchHeroCompact.test.tsx`

### Steps
1. RED — test : logos 40px, layout vertical compact.
2. GREEN.
3. Commit `feat(v2/match-detail): add MatchHeroCompact mobile component`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MatchHeroCompact } from "./MatchHeroCompact";
import type { MatchHeader } from "../../../types/v2/match-detail";

const header: MatchHeader = {
  fixture_id: 42,
  kickoff_utc: "2026-04-22T18:45:00Z",
  stadium: "Allianz Riviera",
  league_name: "Ligue 1",
  home: { id: 1, name: "Nice", logo_url: "/n.png", rank: 4, form: ["W", "W", "D", "W", "W"] },
  away: { id: 2, name: "Lens", logo_url: "/l.png", rank: 7, form: ["L", "D", "W", "L", "D"] },
};

describe("MatchHeroCompact", () => {
  it("renders compact logos at 40px", () => {
    render(<MatchHeroCompact header={header} />);
    const imgs = screen.getAllByRole("img", { name: /logo/i });
    expect(imgs[0]).toHaveAttribute("width", "40");
  });
  it("shows both team names", () => {
    render(<MatchHeroCompact header={header} />);
    expect(screen.getByText("Nice")).toBeInTheDocument();
    expect(screen.getByText("Lens")).toBeInTheDocument();
  });
});
```

### Implémentation
```tsx
import type { MatchHeader } from "../../../types/v2/match-detail";
import { FormBadge } from "./FormBadge";

export interface MatchHeroCompactProps {
  header: MatchHeader;
}

export function MatchHeroCompact({ header }: MatchHeroCompactProps) {
  const { home, away, kickoff_utc, league_name } = header;
  const time = new Date(kickoff_utc).toLocaleString("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Paris",
  });
  return (
    <header className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{league_name}</div>
      <div className="mt-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src={home.logo_url} alt={`${home.name} logo`} width={40} height={40} />
          <div>
            <div className="text-sm font-semibold">{home.name}</div>
            <FormBadge form={home.form} />
          </div>
        </div>
        <div className="text-xs font-medium text-slate-600">{time}</div>
        <div className="flex items-center gap-2">
          <div className="text-right">
            <div className="text-sm font-semibold">{away.name}</div>
            <FormBadge form={away.form} />
          </div>
          <img src={away.logo_url} alt={`${away.name} logo`} width={40} height={40} />
        </div>
      </div>
    </header>
  );
}
```

---

## Task 7 — `StatsComparative`

Barres bicolores symétriques (valeur domicile à gauche, extérieur à droite).

### Files
- `dashboard/src/components/v2/match-detail/StatsComparative.tsx`
- `dashboard/src/components/v2/match-detail/StatsComparative.test.tsx`

### Steps
1. RED — test : chaque stat a un `aria-label` "xG 5 derniers : domicile 1.8 extérieur 1.2".
2. GREEN.
3. Commit `feat(v2/match-detail): add StatsComparative component`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatsComparative } from "./StatsComparative";
import type { ComparativeStat } from "../../../types/v2/match-detail";

const stats: ComparativeStat[] = [
  { label: "xG 5 derniers", home_value: 1.8, away_value: 1.2 },
  { label: "Possession", home_value: 58, away_value: 42, unit: "%" },
];

describe("StatsComparative", () => {
  it("renders one bar per stat with aria-label", () => {
    render(<StatsComparative stats={stats} />);
    expect(screen.getByLabelText("xG 5 derniers : domicile 1.8, extérieur 1.2")).toBeInTheDocument();
    expect(screen.getByLabelText("Possession : domicile 58%, extérieur 42%")).toBeInTheDocument();
  });

  it("renders nothing useful when stats empty", () => {
    const { container } = render(<StatsComparative stats={[]} />);
    expect(container.querySelectorAll("[data-testid='stat-row']").length).toBe(0);
  });
});
```

### Implémentation
```tsx
import type { ComparativeStat } from "../../../types/v2/match-detail";

export interface StatsComparativeProps {
  stats: ComparativeStat[];
}

export function StatsComparative({ stats }: StatsComparativeProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Stats comparatives (5 derniers matchs)</h3>
      <ul className="space-y-3">
        {stats.map((s) => {
          const total = s.home_value + s.away_value || 1;
          const homePct = (s.home_value / total) * 100;
          const unit = s.unit ?? "";
          return (
            <li
              key={s.label}
              data-testid="stat-row"
              aria-label={`${s.label} : domicile ${s.home_value}${unit}, extérieur ${s.away_value}${unit}`}
              className="flex items-center gap-3 text-xs"
            >
              <span className="w-10 text-right font-medium text-slate-700">{s.home_value}{unit}</span>
              <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div className="bg-emerald-500" style={{ width: `${homePct}%` }} />
                <div className="bg-sky-500" style={{ width: `${100 - homePct}%` }} />
              </div>
              <span className="w-10 font-medium text-slate-700">{s.away_value}{unit}</span>
              <span className="ml-2 min-w-[120px] text-slate-500">{s.label}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
```

---

## Task 8 — `H2HSection`

### Files
- `dashboard/src/components/v2/match-detail/H2HSection.tsx`
- `dashboard/src/components/v2/match-detail/H2HSection.test.tsx`

### Steps
1. RED — test : barre empilée avec 3 segments, liste des 3 derniers matchs.
2. GREEN.
3. Commit `feat(v2/match-detail): add H2HSection component`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { H2HSection } from "./H2HSection";
import type { H2HSummary } from "../../../types/v2/match-detail";

const h2h: H2HSummary = {
  home_wins: 7,
  draws: 2,
  away_wins: 1,
  last_matches: [
    { date_utc: "2025-11-04", home_team: "Nice", away_team: "Lens", score: "2-1" },
    { date_utc: "2025-04-18", home_team: "Lens", away_team: "Nice", score: "0-0" },
    { date_utc: "2024-12-02", home_team: "Nice", away_team: "Lens", score: "3-1" },
  ],
};

describe("H2HSection", () => {
  it("shows aggregated bar with aria-label", () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(
      screen.getByLabelText("Historique : Nice 7 victoires, 2 nuls, Lens 1 victoire"),
    ).toBeInTheDocument();
  });

  it("lists last 3 matches", () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(screen.getAllByTestId("h2h-row")).toHaveLength(3);
  });
});
```

### Implémentation
```tsx
import type { H2HSummary } from "../../../types/v2/match-detail";

export interface H2HSectionProps {
  h2h: H2HSummary;
  homeName: string;
  awayName: string;
}

export function H2HSection({ h2h, homeName, awayName }: H2HSectionProps) {
  const total = h2h.home_wins + h2h.draws + h2h.away_wins || 1;
  const homePct = (h2h.home_wins / total) * 100;
  const drawPct = (h2h.draws / total) * 100;
  const awayPct = 100 - homePct - drawPct;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Face à face</h3>
      <div
        role="img"
        aria-label={`Historique : ${homeName} ${h2h.home_wins} victoires, ${h2h.draws} nuls, ${awayName} ${h2h.away_wins} victoire${h2h.away_wins > 1 ? "s" : ""}`}
        className="flex h-3 overflow-hidden rounded-full"
      >
        <div className="bg-emerald-500" style={{ width: `${homePct}%` }} />
        <div className="bg-slate-400" style={{ width: `${drawPct}%` }} />
        <div className="bg-sky-500" style={{ width: `${awayPct}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-600">
        <span>{homeName} {h2h.home_wins}V</span>
        <span>{h2h.draws}N</span>
        <span>{awayName} {h2h.away_wins}V</span>
      </div>
      <ul className="mt-4 space-y-2">
        {h2h.last_matches.map((m, i) => (
          <li key={i} data-testid="h2h-row" className="flex items-center justify-between text-xs text-slate-700">
            <span>{new Date(m.date_utc).toLocaleDateString("fr-FR")}</span>
            <span className="font-medium">{m.home_team} {m.score} {m.away_team}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

---

## Task 9 — `AIAnalysis` (avec gating teaser)

### Files
- `dashboard/src/components/v2/match-detail/AIAnalysis.tsx`
- `dashboard/src/components/v2/match-detail/AIAnalysis.test.tsx`

### Steps
1. RED — 3 cas : `premium` → tout visible, `free` → §1 visible + reste blurred + `LockOverlay`, `visitor` → totalement locké.
2. GREEN.
3. Commit `feat(v2/match-detail): add AIAnalysis with gating`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AIAnalysis } from "./AIAnalysis";

const paragraphs = [
  "Nice a remporté ses 4 derniers matchs à domicile.",
  "Lens peine en déplacement avec 2 buts encaissés en moyenne.",
  "Le xG de Nice explose cette saison.",
];

describe("AIAnalysis", () => {
  it("premium sees all paragraphs, no lock", () => {
    render(<AIAnalysis paragraphs={paragraphs} userRole="premium" />);
    paragraphs.forEach((p) => expect(screen.getByText(p)).toBeInTheDocument());
    expect(screen.queryByTestId("lock-overlay")).not.toBeInTheDocument();
  });

  it("free sees first paragraph and blurred rest with upgrade lock", () => {
    render(<AIAnalysis paragraphs={paragraphs} userRole="free" />);
    expect(screen.getByText(paragraphs[0])).toBeInTheDocument();
    const blurred = screen.getByTestId("ai-blurred");
    expect(blurred.className).toMatch(/blur-sm/);
    expect(screen.getByTestId("lock-overlay")).toHaveAttribute("data-variant", "upgrade");
  });

  it("visitor sees signup lock over all content", () => {
    render(<AIAnalysis paragraphs={paragraphs} userRole="visitor" />);
    expect(screen.getByTestId("lock-overlay")).toHaveAttribute("data-variant", "signup");
  });

  it("renders paragraphs as safe React text children", () => {
    const attempted = "<script>alert('x')</script>Nice gagne.";
    render(<AIAnalysis paragraphs={[attempted]} userRole="premium" />);
    // React échappe : la chaîne apparaît en texte brut, aucun élément <script> n'est créé
    expect(screen.getByText(attempted)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
});
```

### Implémentation
```tsx
import { LockOverlay } from "../system/LockOverlay"; // fourni Lot 1
import type { UserRole } from "../../../types/v2/match-detail";

export interface AIAnalysisProps {
  paragraphs: string[];
  userRole: UserRole;
}

export function AIAnalysis({ paragraphs, userRole }: AIAnalysisProps) {
  if (userRole === "visitor") {
    return (
      <section className="relative rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Analyse IA</h3>
        <div className="pointer-events-none select-none blur-sm" aria-hidden>
          {paragraphs.map((p, i) => (
            <p key={i} className="mb-2 text-sm text-slate-700">{p}</p>
          ))}
        </div>
        <LockOverlay variant="signup" ctaHref="/signup" />
      </section>
    );
  }

  const [first, ...rest] = paragraphs;
  const gated = userRole === "free" && rest.length > 0;

  return (
    <section className="relative rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Analyse IA</h3>
      {first && <p className="mb-2 text-sm text-slate-800">{first}</p>}
      {rest.length > 0 && (
        <div className="relative">
          <div
            data-testid="ai-blurred"
            className={gated ? "pointer-events-none select-none blur-sm" : ""}
            aria-hidden={gated}
          >
            {rest.map((p, i) => (
              <p key={i} className="mb-2 text-sm text-slate-700">{p}</p>
            ))}
          </div>
          {gated && <LockOverlay variant="upgrade" ctaHref="/pricing" />}
        </div>
      )}
    </section>
  );
}
```

> `LockOverlay` du Lot 1 doit exposer `data-testid="lock-overlay"` et `data-variant={variant}`. Si ce n'est pas le cas au moment de l'implémentation, ouvrir un mini-PR sur Lot 1 pour l'ajouter.

---

## Task 10 — `CompositionsSection`

### Files
- `dashboard/src/components/v2/match-detail/CompositionsSection.tsx`
- `dashboard/src/components/v2/match-detail/CompositionsSection.test.tsx`

### Steps
1. RED — test : affichage XI, status "probable" affiche badge, status "unavailable" affiche fallback.
2. GREEN.
3. Commit `feat(v2/match-detail): add CompositionsSection`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CompositionsSection } from "./CompositionsSection";
import type { CompositionsPayload } from "../../../types/v2/match-detail";

const comps: CompositionsPayload = {
  status: "probable",
  home: {
    formation: "4-3-3",
    starters: [
      { number: 1, name: "Bulka", position: "GK" },
      { number: 9, name: "Moffi", position: "ST" },
    ],
  },
  away: {
    formation: "4-2-3-1",
    starters: [{ number: 30, name: "Samba", position: "GK" }],
  },
};

describe("CompositionsSection", () => {
  it("renders formations and players", () => {
    render(<CompositionsSection compositions={comps} homeName="Nice" awayName="Lens" />);
    expect(screen.getByText("4-3-3")).toBeInTheDocument();
    expect(screen.getByText("Moffi")).toBeInTheDocument();
  });

  it("shows status badge", () => {
    render(<CompositionsSection compositions={comps} homeName="Nice" awayName="Lens" />);
    expect(screen.getByText(/probable/i)).toBeInTheDocument();
  });

  it("renders fallback when unavailable", () => {
    render(
      <CompositionsSection
        compositions={{ status: "unavailable", home: null, away: null }}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(screen.getByText(/compositions non communiquées/i)).toBeInTheDocument();
  });
});
```

### Implémentation
```tsx
import type { CompositionsPayload, Lineup } from "../../../types/v2/match-detail";

export interface CompositionsSectionProps {
  compositions: CompositionsPayload;
  homeName: string;
  awayName: string;
}

const STATUS_LABEL: Record<CompositionsPayload["status"], string> = {
  confirmed: "Confirmée",
  probable: "Probable",
  unavailable: "Indisponible",
};

export function CompositionsSection({ compositions, homeName, awayName }: CompositionsSectionProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Compositions</h3>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-600">
          {STATUS_LABEL[compositions.status]}
        </span>
      </div>
      {compositions.status === "unavailable" || (!compositions.home && !compositions.away) ? (
        <p className="text-xs text-slate-500">Compositions non communiquées.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {compositions.home && <TeamLineup name={homeName} lineup={compositions.home} />}
          {compositions.away && <TeamLineup name={awayName} lineup={compositions.away} />}
        </div>
      )}
    </section>
  );
}

function TeamLineup({ name, lineup }: { name: string; lineup: Lineup }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-800">{name}</span>
        <span className="text-xs text-slate-500">{lineup.formation}</span>
      </div>
      <ul className="space-y-1 text-xs text-slate-700">
        {lineup.starters.map((p) => (
          <li key={p.number} className="flex items-center gap-2">
            <span className="inline-block w-6 text-right tabular-nums text-slate-500">{p.number}</span>
            <span className="font-medium">{p.name}</span>
            <span className="text-slate-400">{p.position}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Task 11 — `AllMarketsGrid`

### Files
- `dashboard/src/components/v2/match-detail/AllMarketsGrid.tsx`
- `dashboard/src/components/v2/match-detail/AllMarketsGrid.test.tsx`

### Steps
1. RED — 14 markets, `is_value=true` highlight, grid 2 colonnes desktop.
2. GREEN.
3. Commit `feat(v2/match-detail): add AllMarketsGrid`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AllMarketsGrid } from "./AllMarketsGrid";
import type { MarketProb } from "../../../types/v2/match-detail";

const markets: MarketProb[] = [
  { market_key: "1x2.home", label: "Victoire Nice", probability: 0.52, fair_odds: 1.92, best_book_odds: 2.1, is_value: true, edge: 0.08 },
  { market_key: "1x2.draw", label: "Match nul", probability: 0.26, fair_odds: 3.85, best_book_odds: 3.5, is_value: false, edge: null },
];

describe("AllMarketsGrid", () => {
  it("renders one cell per market", () => {
    render(<AllMarketsGrid markets={markets} />);
    expect(screen.getAllByTestId("market-cell")).toHaveLength(2);
  });

  it("highlights value bets", () => {
    render(<AllMarketsGrid markets={markets} />);
    const cells = screen.getAllByTestId("market-cell");
    expect(cells[0].className).toMatch(/ring|border-emerald/);
    expect(cells[1].className).not.toMatch(/border-emerald/);
  });

  it("renders aria-label with probability", () => {
    render(<AllMarketsGrid markets={markets} />);
    expect(screen.getByLabelText(/Victoire Nice, probabilité 52%/)).toBeInTheDocument();
  });
});
```

### Implémentation
```tsx
import type { MarketProb } from "../../../types/v2/match-detail";

export interface AllMarketsGridProps {
  markets: MarketProb[];
}

export function AllMarketsGrid({ markets }: AllMarketsGridProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Tous les marchés</h3>
      <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
        {markets.map((m) => {
          const pct = Math.round(m.probability * 100);
          const valueCls = m.is_value
            ? "ring-2 ring-emerald-400 border-emerald-400 bg-emerald-50"
            : "border-slate-200 bg-white";
          return (
            <li
              key={m.market_key}
              data-testid="market-cell"
              aria-label={`${m.label}, probabilité ${pct}%`}
              className={`flex items-center justify-between rounded-lg border p-3 text-sm ${valueCls}`}
            >
              <span className="font-medium text-slate-800">{m.label}</span>
              <div className="flex items-center gap-3 tabular-nums">
                <span className="text-slate-600">{pct}%</span>
                <span className="font-semibold text-slate-900">
                  {m.best_book_odds?.toFixed(2) ?? m.fair_odds.toFixed(2)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
```

---

## Task 12 — `RecoCard`

Cote hero 34px, breakdown Confiance / Kelly / Edge.

### Files
- `dashboard/src/components/v2/match-detail/RecoCard.tsx`
- `dashboard/src/components/v2/match-detail/RecoCard.test.tsx`

### Steps
1. RED — test : cote affichée en 34px (classe `text-[34px]`), 3 métriques présentes.
2. GREEN.
3. Commit `feat(v2/match-detail): add RecoCard`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecoCard } from "./RecoCard";
import type { Recommendation } from "../../../types/v2/match-detail";

const reco: Recommendation = {
  market_key: "1x2.home",
  market_label: "Victoire Nice",
  odds: 2.1,
  confidence: 0.74,
  kelly_fraction: 0.035,
  edge: 0.08,
  book_name: "Unibet",
};

describe("RecoCard", () => {
  it("renders odds hero size", () => {
    render(<RecoCard reco={reco} />);
    const hero = screen.getByTestId("reco-odds");
    expect(hero.className).toMatch(/text-\[34px\]/);
    expect(hero).toHaveTextContent("2.10");
  });

  it("renders breakdown", () => {
    render(<RecoCard reco={reco} />);
    expect(screen.getByText(/74%/)).toBeInTheDocument();
    expect(screen.getByText(/3.5%/)).toBeInTheDocument();
    expect(screen.getByText(/8%/)).toBeInTheDocument();
  });

  it("returns null when reco is null", () => {
    const { container } = render(<RecoCard reco={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

### Implémentation
```tsx
import type { Recommendation } from "../../../types/v2/match-detail";

export interface RecoCardProps {
  reco: Recommendation | null;
}

export function RecoCard({ reco }: RecoCardProps) {
  if (!reco) return null;
  const conf = Math.round(reco.confidence * 100);
  const kelly = (reco.kelly_fraction * 100).toFixed(1);
  const edge = Math.round(reco.edge * 100);
  return (
    <section className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-5">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
        Recommandation
      </div>
      <div className="mt-1 text-base font-semibold text-slate-900">{reco.market_label}</div>
      <div
        data-testid="reco-odds"
        className="mt-2 text-[34px] font-bold leading-none text-emerald-700"
      >
        {reco.odds.toFixed(2)}
      </div>
      <div className="mt-1 text-xs text-slate-500">chez {reco.book_name}</div>
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <dt className="text-slate-500">Confiance</dt>
          <dd className="font-semibold text-slate-900">{conf}%</dd>
        </div>
        <div>
          <dt className="text-slate-500">Kelly</dt>
          <dd className="font-semibold text-slate-900">{kelly}%</dd>
        </div>
        <div>
          <dt className="text-slate-500">Edge</dt>
          <dd className="font-semibold text-emerald-700">+{edge}%</dd>
        </div>
      </dl>
    </section>
  );
}
```

---

## Task 13 — `BookOddsList`

Tableau de 5 books avec la meilleure cote highlight. Réutilise `BookOddsRow` du Lot 1.

### Files
- `dashboard/src/components/v2/match-detail/BookOddsList.tsx`
- `dashboard/src/components/v2/match-detail/BookOddsList.test.tsx`

### Steps
1. RED — 5 lignes, exactement 1 `is_best=true` → appliqué.
2. GREEN.
3. Commit `feat(v2/match-detail): add BookOddsList`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BookOddsList } from "./BookOddsList";
import type { BookOdd } from "../../../types/v2/match-detail";

const books: BookOdd[] = [
  { bookmaker: "Unibet", odds: 2.10, is_best: true, updated_at: "2026-04-21T10:00:00Z" },
  { bookmaker: "Winamax", odds: 2.05, is_best: false, updated_at: "2026-04-21T10:00:00Z" },
  { bookmaker: "Betclic", odds: 2.00, is_best: false, updated_at: "2026-04-21T10:00:00Z" },
  { bookmaker: "PMU", odds: 1.98, is_best: false, updated_at: "2026-04-21T10:00:00Z" },
  { bookmaker: "Pinnacle", odds: 2.08, is_best: false, updated_at: "2026-04-21T10:00:00Z" },
];

describe("BookOddsList", () => {
  it("renders one row per book", () => {
    render(<BookOddsList books={books} />);
    expect(screen.getAllByTestId("book-odds-row")).toHaveLength(5);
  });
  it("highlights the best book", () => {
    render(<BookOddsList books={books} />);
    const best = screen.getByTestId("book-odds-row-best");
    expect(best).toHaveTextContent("Unibet");
    expect(best).toHaveTextContent("2.10");
  });
});
```

### Implémentation
```tsx
import { BookOddsRow } from "../system/BookOddsRow"; // Lot 1
import type { BookOdd } from "../../../types/v2/match-detail";

export interface BookOddsListProps {
  books: BookOdd[];
}

export function BookOddsList({ books }: BookOddsListProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Cotes bookmakers</h3>
      <ul className="divide-y divide-slate-100">
        {books.map((b) => (
          <BookOddsRow
            key={b.bookmaker}
            bookmaker={b.bookmaker}
            odds={b.odds}
            isBest={b.is_best}
            updatedAt={b.updated_at}
            data-testid={b.is_best ? "book-odds-row-best" : "book-odds-row"}
          />
        ))}
      </ul>
    </section>
  );
}
```

> `BookOddsRow` Lot 1 doit accepter et propager le `data-testid` sur son élément racine (c'est le cas si fait via rest-props).

---

## Task 14 — `ValueBetsList`

### Files
- `dashboard/src/components/v2/match-detail/ValueBetsList.tsx`
- `dashboard/src/components/v2/match-detail/ValueBetsList.test.tsx`

### Steps
1. RED — test : premium voit tous les VB, free voit 1 aperçu + reste flouté + lock upgrade.
2. GREEN.
3. Commit `feat(v2/match-detail): add ValueBetsList with gating`.

### Test
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ValueBetsList } from "./ValueBetsList";
import type { ValueBet } from "../../../types/v2/match-detail";

const bets: ValueBet[] = [
  { market_key: "1x2.home", label: "Victoire Nice", probability: 0.52, best_odds: 2.1, edge: 0.08 },
  { market_key: "btts.yes", label: "Les deux équipes marquent", probability: 0.58, best_odds: 1.85, edge: 0.05 },
  { market_key: "over25", label: "Plus de 2.5 buts", probability: 0.55, best_odds: 1.95, edge: 0.04 },
];

describe("ValueBetsList", () => {
  it("premium sees all bets", () => {
    render(<ValueBetsList bets={bets} userRole="premium" />);
    expect(screen.getAllByTestId("value-bet-row")).toHaveLength(3);
    expect(screen.queryByTestId("lock-overlay")).not.toBeInTheDocument();
  });

  it("free sees one visible, rest blurred with upgrade lock", () => {
    render(<ValueBetsList bets={bets} userRole="free" />);
    expect(screen.getAllByTestId("value-bet-row")).toHaveLength(3);
    expect(screen.getByTestId("vb-blurred").className).toMatch(/blur-sm/);
    expect(screen.getByTestId("lock-overlay")).toHaveAttribute("data-variant", "upgrade");
  });

  it("visitor sees signup lock", () => {
    render(<ValueBetsList bets={bets} userRole="visitor" />);
    expect(screen.getByTestId("lock-overlay")).toHaveAttribute("data-variant", "signup");
  });
});
```

### Implémentation
```tsx
import { LockOverlay } from "../system/LockOverlay";
import type { UserRole, ValueBet } from "../../../types/v2/match-detail";

export interface ValueBetsListProps {
  bets: ValueBet[];
  userRole: UserRole;
}

function Row({ bet }: { bet: ValueBet }) {
  return (
    <li
      data-testid="value-bet-row"
      aria-label={`${bet.label}, edge ${(bet.edge * 100).toFixed(0)}%`}
      className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs"
    >
      <span className="font-medium text-slate-900">{bet.label}</span>
      <span className="font-semibold text-emerald-700">+{Math.round(bet.edge * 100)}% @ {bet.best_odds.toFixed(2)}</span>
    </li>
  );
}

export function ValueBetsList({ bets, userRole }: ValueBetsListProps) {
  if (userRole === "visitor") {
    return (
      <section className="relative rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Value bets</h3>
        <ul className="space-y-2 pointer-events-none blur-sm" aria-hidden>
          {bets.map((b) => <Row key={b.market_key} bet={b} />)}
        </ul>
        <LockOverlay variant="signup" ctaHref="/signup" />
      </section>
    );
  }

  if (userRole === "free") {
    const [first, ...rest] = bets;
    return (
      <section className="relative rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Value bets</h3>
        <ul className="space-y-2">
          {first && <Row bet={first} />}
          {rest.length > 0 && (
            <div className="relative">
              <div data-testid="vb-blurred" className="pointer-events-none blur-sm space-y-2" aria-hidden>
                {rest.map((b) => <Row key={b.market_key} bet={b} />)}
              </div>
              <LockOverlay variant="upgrade" ctaHref="/pricing" />
            </div>
          )}
        </ul>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Value bets</h3>
      <ul className="space-y-2">
        {bets.map((b) => <Row key={b.market_key} bet={b} />)}
      </ul>
    </section>
  );
}
```

---

## Task 15 — `StickyActions`

Deux boutons empilés : suivre bankroll + alerte kick-off.

### Files
- `dashboard/src/components/v2/match-detail/StickyActions.tsx`
- `dashboard/src/components/v2/match-detail/StickyActions.test.tsx`

### Steps
1. RED — clic sur "Suivre bankroll" appelle la mutation fournie, bouton désactivé pendant pending.
2. GREEN.
3. Commit `feat(v2/match-detail): add StickyActions`.

### Test
```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StickyActions } from "./StickyActions";

describe("StickyActions", () => {
  it("calls onAddToBankroll on click", () => {
    const onAdd = vi.fn();
    const onAlert = vi.fn();
    render(<StickyActions onAddToBankroll={onAdd} onAlertKickoff={onAlert} pending={false} />);
    fireEvent.click(screen.getByRole("button", { name: /suivre bankroll/i }));
    expect(onAdd).toHaveBeenCalledTimes(1);
  });

  it("disables when pending", () => {
    render(<StickyActions onAddToBankroll={vi.fn()} onAlertKickoff={vi.fn()} pending />);
    expect(screen.getByRole("button", { name: /suivre bankroll/i })).toBeDisabled();
  });
});
```

### Implémentation
```tsx
export interface StickyActionsProps {
  onAddToBankroll: () => void;
  onAlertKickoff: () => void;
  pending: boolean;
}

export function StickyActions({ onAddToBankroll, onAlertKickoff, pending }: StickyActionsProps) {
  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        disabled={pending}
        onClick={onAddToBankroll}
        className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
      >
        Suivre bankroll
      </button>
      <button
        type="button"
        onClick={onAlertKickoff}
        className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
      >
        Alerte kick-off
      </button>
    </div>
  );
}
```

---

## Task 16 — Barrel export

### Files
- `dashboard/src/components/v2/match-detail/index.ts`

### Steps
1. Écrire l'index.
2. Commit `feat(v2/match-detail): add barrel export`.

```ts
export { MatchHero } from "./MatchHero";
export { MatchHeroCompact } from "./MatchHeroCompact";
export { FormBadge } from "./FormBadge";
export { StatsComparative } from "./StatsComparative";
export { H2HSection } from "./H2HSection";
export { AIAnalysis } from "./AIAnalysis";
export { CompositionsSection } from "./CompositionsSection";
export { AllMarketsGrid } from "./AllMarketsGrid";
export { RecoCard } from "./RecoCard";
export { BookOddsList } from "./BookOddsList";
export { ValueBetsList } from "./ValueBetsList";
export { StickyActions } from "./StickyActions";
```

---

## Task 17 — Page `MatchDetailV2` (assemblage + sticky + gating)

Remplace le stub Lot 1. C'est la task la plus lourde et la plus testée.

### Files
- `dashboard/src/pages/v2/MatchDetailV2.tsx` (réécriture)
- `dashboard/src/pages/v2/MatchDetailV2.test.tsx` (réécriture)

### Steps
1. RED — tests :
   - Rend le loader puis le contenu après résolution des hooks.
   - Sticky : la colonne droite a la classe `sticky top-5` (vérification via DOM).
   - Gating par rôle : `userRole` propagé aux sous-composants (test par présence / absence de `LockOverlay`).
   - Mobile : `MatchHeroCompact` rendu, desktop `MatchHero`.
   - `aria-label` probas 1X2 présent via `ProbBar`.
2. GREEN.
3. Commit `feat(v2/match-detail): implement MatchDetailV2 page`.

### Test
```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MatchDetailV2 } from "./MatchDetailV2";

function renderWith(userRole: "visitor" | "free" | "trial" | "premium") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/matchs/42"]}>
        <Routes>
          <Route path="/matchs/:fixtureId" element={<MatchDetailV2 userRole={userRole} />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const matchPayload = {
  header: {
    fixture_id: 42,
    kickoff_utc: "2026-04-22T18:45:00Z",
    stadium: "Allianz Riviera",
    league_name: "Ligue 1",
    home: { id: 1, name: "Nice", logo_url: "/n.png", rank: 4, form: ["W", "W", "D", "W", "W"] },
    away: { id: 2, name: "Lens", logo_url: "/l.png", rank: 7, form: ["L", "D", "W", "L", "D"] },
  },
  probs_1x2: { home: 0.52, draw: 0.26, away: 0.22 },
  stats: [{ label: "xG 5 derniers", home_value: 1.8, away_value: 1.2 }],
  h2h: { home_wins: 7, draws: 2, away_wins: 1, last_matches: [] },
  compositions: { status: "unavailable", home: null, away: null },
  all_markets: [
    { market_key: "1x2.home", label: "Victoire Nice", probability: 0.52, fair_odds: 1.92, best_book_odds: 2.1, is_value: true, edge: 0.08 },
  ],
  recommendation: {
    market_key: "1x2.home", market_label: "Victoire Nice",
    odds: 2.1, confidence: 0.74, kelly_fraction: 0.035, edge: 0.08, book_name: "Unibet",
  },
  value_bets: [
    { market_key: "1x2.home", label: "Victoire Nice", probability: 0.52, best_odds: 2.1, edge: 0.08 },
    { market_key: "btts.yes", label: "BTTS Oui", probability: 0.58, best_odds: 1.85, edge: 0.05 },
  ],
};

const comparison = {
  books: [
    { bookmaker: "Unibet", odds: 2.10, is_best: true, updated_at: "2026-04-21T10:00:00Z" },
    { bookmaker: "Winamax", odds: 2.05, is_best: false, updated_at: "2026-04-21T10:00:00Z" },
  ],
};

const analysis = { paragraphs: ["Nice domine.", "Lens solide."], generated_at: "2026-04-21T10:00:00Z" };

function mockFetch() {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/api/predictions/")) return Promise.resolve(new Response(JSON.stringify(matchPayload), { status: 200 }));
    if (url.includes("/api/odds/")) return Promise.resolve(new Response(JSON.stringify(comparison), { status: 200 }));
    if (url.includes("/api/analysis/")) return Promise.resolve(new Response(JSON.stringify(analysis), { status: 200 }));
    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

describe("MatchDetailV2", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockFetch();
  });

  it("renders loading then content", async () => {
    renderWith("premium");
    await waitFor(() => expect(screen.getByText("Nice")).toBeInTheDocument());
    expect(screen.getByText("Victoire Nice")).toBeInTheDocument();
  });

  it("applies sticky class on right column (desktop)", async () => {
    renderWith("premium");
    await waitFor(() => expect(screen.getByText("Nice")).toBeInTheDocument());
    const sticky = screen.getByTestId("right-column");
    expect(sticky.className).toMatch(/sticky/);
    expect(sticky.className).toMatch(/top-5/);
  });

  it("visitor sees signup locks on reco, analysis, value bets", async () => {
    renderWith("visitor");
    await waitFor(() => expect(screen.getByText("Nice")).toBeInTheDocument());
    const locks = screen.getAllByTestId("lock-overlay");
    expect(locks.length).toBeGreaterThanOrEqual(2);
    locks.forEach((l) => expect(l).toHaveAttribute("data-variant", "signup"));
  });

  it("free sees upgrade lock on AI and value bets, H2H visible", async () => {
    renderWith("free");
    await waitFor(() => expect(screen.getByText("Nice")).toBeInTheDocument());
    const locks = screen.getAllByTestId("lock-overlay");
    expect(locks.some((l) => l.getAttribute("data-variant") === "upgrade")).toBe(true);
    expect(screen.getByText(/Face à face/i)).toBeInTheDocument();
  });

  it("premium: no lock overlays at all", async () => {
    renderWith("premium");
    await waitFor(() => expect(screen.getByText("Nice")).toBeInTheDocument());
    expect(screen.queryByTestId("lock-overlay")).not.toBeInTheDocument();
  });

  it("renders ProbBar with aria-label for 1X2 probabilities", async () => {
    renderWith("premium");
    await waitFor(() => expect(screen.getByText("Nice")).toBeInTheDocument());
    expect(screen.getByLabelText(/Probabilités 1X2/i)).toBeInTheDocument();
  });
});
```

### Implémentation `MatchDetailV2.tsx`
```tsx
import { useParams } from "react-router-dom";
import { useMatchDetail } from "../../hooks/v2/useMatchDetail";
import { useOddsComparison } from "../../hooks/v2/useOddsComparison"; // Lot 2
import { useAnalysis } from "../../hooks/v2/useAnalysis";
import { useAddToBankroll } from "../../hooks/v2/useAddToBankroll";
import {
  MatchHero,
  MatchHeroCompact,
  StatsComparative,
  H2HSection,
  AIAnalysis,
  CompositionsSection,
  AllMarketsGrid,
  RecoCard,
  BookOddsList,
  ValueBetsList,
  StickyActions,
} from "../../components/v2/match-detail";
import { ProbBar } from "../../components/v2/system/ProbBar"; // Lot 1
import { LockOverlay } from "../../components/v2/system/LockOverlay";
import type { UserRole } from "../../types/v2/match-detail";

export interface MatchDetailV2Props {
  userRole: UserRole;
}

export function MatchDetailV2({ userRole }: MatchDetailV2Props) {
  const { fixtureId: raw } = useParams<{ fixtureId: string }>();
  const fixtureId = raw ? Number(raw) : null;

  const match = useMatchDetail(fixtureId);
  const comparison = useOddsComparison(fixtureId);
  const analysis = useAnalysis(fixtureId);
  const addBet = useAddToBankroll();

  if (!fixtureId) return <p className="p-6 text-sm text-rose-600">Identifiant de match invalide.</p>;
  if (match.isLoading) return <p className="p-6 text-sm text-slate-500">Chargement…</p>;
  if (match.isError || !match.data) return <p className="p-6 text-sm text-rose-600">Erreur de chargement.</p>;

  const d = match.data;
  const canSeeReco = userRole === "trial" || userRole === "premium";
  const canSeeOdds = userRole === "trial" || userRole === "premium";
  const canSeeH2H = userRole !== "visitor";
  const canSeeCompositions = userRole !== "visitor";
  const canSeeAllMarkets = userRole === "trial" || userRole === "premium";

  const handleAddBankroll = () => {
    if (!d.recommendation) return;
    addBet.mutate({
      fixture_id: d.header.fixture_id,
      market_key: d.recommendation.market_key,
      odds: d.recommendation.odds,
      stake: 10,
    });
  };

  const handleAlertKickoff = () => {
    // Placeholder — impl détaillée Lot 6 notifications
  };

  return (
    <main className="mx-auto max-w-7xl p-4 lg:p-6">
      <nav aria-label="Fil d'Ariane" className="mb-3 text-xs text-slate-500">
        <a href="/matchs" className="hover:text-slate-800">← Matchs</a>
        <span className="mx-2">/</span>
        <span>{d.header.home.name} vs {d.header.away.name}</span>
      </nav>

      {/* Mobile header */}
      <div className="lg:hidden"><MatchHeroCompact header={d.header} /></div>
      {/* Desktop header */}
      <div className="hidden lg:block"><MatchHero header={d.header} /></div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-4">
          <ProbBar
            home={d.probs_1x2.home}
            draw={d.probs_1x2.draw}
            away={d.probs_1x2.away}
            aria-label={`Probabilités 1X2 — domicile ${Math.round(d.probs_1x2.home * 100)}%, nul ${Math.round(d.probs_1x2.draw * 100)}%, extérieur ${Math.round(d.probs_1x2.away * 100)}%`}
          />
          <StatsComparative stats={d.stats} />

          {canSeeH2H ? (
            <H2HSection h2h={d.h2h} homeName={d.header.home.name} awayName={d.header.away.name} />
          ) : (
            <LockedBlock title="Face à face" variant="signup" />
          )}

          <AIAnalysis
            paragraphs={analysis.data?.paragraphs ?? []}
            userRole={userRole}
          />

          {canSeeCompositions ? (
            <CompositionsSection
              compositions={d.compositions}
              homeName={d.header.home.name}
              awayName={d.header.away.name}
            />
          ) : (
            <LockedBlock title="Compositions" variant="signup" />
          )}

          {canSeeAllMarkets ? (
            <AllMarketsGrid markets={d.all_markets} />
          ) : (
            <LockedBlock title="Tous les marchés" variant={userRole === "visitor" ? "signup" : "upgrade"} />
          )}
        </div>

        {/* Right column — sticky on desktop only */}
        <aside
          data-testid="right-column"
          className="space-y-4 lg:sticky lg:top-5 lg:self-start"
        >
          {canSeeReco ? (
            <RecoCard reco={d.recommendation} />
          ) : (
            <LockedBlock title="Recommandation" variant={userRole === "visitor" ? "signup" : "upgrade"} />
          )}

          {canSeeOdds && comparison.data ? (
            <BookOddsList books={comparison.data.books} />
          ) : (
            <LockedBlock title="Cotes bookmakers" variant={userRole === "visitor" ? "signup" : "upgrade"} />
          )}

          <ValueBetsList bets={d.value_bets} userRole={userRole} />

          {(userRole === "trial" || userRole === "premium") && (
            <StickyActions
              onAddToBankroll={handleAddBankroll}
              onAlertKickoff={handleAlertKickoff}
              pending={addBet.isPending}
            />
          )}
        </aside>
      </div>
    </main>
  );
}

function LockedBlock({ title, variant }: { title: string; variant: "signup" | "upgrade" }) {
  const href = variant === "signup" ? "/signup" : "/pricing";
  return (
    <section className="relative rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">{title}</h3>
      <div className="h-24 pointer-events-none blur-sm bg-slate-100" aria-hidden />
      <LockOverlay variant={variant} ctaHref={href} />
    </section>
  );
}
```

> Dépendances Lot 1 attendues :
> - `ProbBar` accepte et propage `aria-label`.
> - `LockOverlay` expose `data-testid="lock-overlay"` et `data-variant`.
> Si absent, aligner via petit PR complémentaire avant merge.

---

## Task 18 — Routing & ajout au router

Le stub est déjà monté sur `/matchs/:fixtureId` au Lot 1. Cette task vérifie qu'on passe bien `userRole` (obtenu du contexte auth Lot 1).

### Files
- `dashboard/src/pages/v2/MatchDetailV2.tsx` (déjà modifié Task 17)
- `dashboard/src/app/router.tsx` (ou équivalent — modification minimale)

### Steps
1. RED — test d'intégration : monter le router, naviguer sur `/matchs/42`, vérifier rendu.
2. GREEN — si déjà câblé au Lot 1, juste passer `userRole={useAuth().role}`.
3. Commit `feat(v2/match-detail): wire userRole from auth context`.

> Pas de test TSX dédié nouveau si `router.tsx` a déjà sa suite de tests Lot 1 — ajouter un test `route.match-detail.test.tsx` si absent.

### Extrait router
```tsx
import { useAuth } from "../hooks/useAuth"; // contexte Lot 1

function MatchDetailRoute() {
  const { role } = useAuth();
  return <MatchDetailV2 userRole={role} />;
}

// dans les routes :
// <Route path="/matchs/:fixtureId" element={<MatchDetailRoute />} />
```

---

## Checklist de clôture (avant merge PR Lot 4)

- [ ] Tous les fichiers listés ci-dessus existent au chemin indiqué.
- [ ] `pnpm --filter dashboard test` vert (ou `npm test` selon workspace), 0 warning React.
- [ ] `pnpm --filter dashboard typecheck` vert (strict).
- [ ] `pnpm --filter dashboard lint` vert.
- [ ] Preview manuelle sur 375px et 1280px : sticky OK, blur OK pour `free` et `visitor`.
- [ ] Matrice gating vérifiée visuellement pour les 4 rôles sur un fixture de dev.
- [ ] Aucune injection HTML brute pour le texte IA (tout passe par React children).
- [ ] Aucun `any`, aucun `TODO` restant.
- [ ] Commits atomiques, chacun avec le trailer :
      `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- [ ] PR intitulée `feat(v2/match-detail): fiche match refonte V1 (Lot 4)` pointant vers ce plan.

---

## Risques & décisions prises

1. **`LockOverlay` / `ProbBar` / `BookOddsRow` doivent exposer `data-testid` et `data-variant`.** Si le Lot 1 ne les expose pas, ouvrir un mini-PR d'amendement avant la Task 9. Décision : on ne reconstruit pas ces composants dans Lot 4.
2. **Sticky** : CSS natif `lg:sticky lg:top-5 lg:self-start`. Aucun JS requis. Testé via `className`.
3. **Compositions indisponibles** : pas de gating additionnel — si `status==="unavailable"`, on rend un fallback texte, indépendamment du rôle.
4. **IA vide** : si `analysis.data.paragraphs` est vide, `AIAnalysis` ne rend que son titre et rien d'autre, aucun lock même en free (il n'y a rien à floutter). Volontaire.
5. **Convention noms** : les contrats TS respectent `snake_case` des payloads backend Supabase/FastAPI (cf. CLAUDE.md projet). Pas de transformation au vol.
6. **Endpoints** : `/api/predictions/:id` existe (legacy), on le réutilise — seul le shape renvoyé doit correspondre à `MatchDetailPayload`. Si ce n'est pas déjà le cas, une migration backend pourra être ajoutée en Lot parallèle ; le frontend reste stable.

Fin du plan Lot 4.
