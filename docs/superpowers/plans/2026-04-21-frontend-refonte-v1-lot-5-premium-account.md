# Plan d'implémentation — Lot 5 : Premium + Compte (Frontend Refonte V1)

## Header

- **Date** : 2026-04-21
- **Auteur** : Claude Sonnet 4.6
- **Projet** : ProbaLab — Refonte Frontend V1
- **Lot** : 5 / 7 — Premium + Compte (Profil / Abonnement / Bankroll / Notifications)
- **Branche cible** : `feat/frontend-v1-lot-5-premium-account`
- **Base** : `main` (après merge des Lots 1 et 2)
- **Spec source** : `docs/superpowers/specs/2026-04-21-frontend-refonte-v1-design.md` (sections 9 à 12)
- **Master plan** : `docs/superpowers/plans/2026-04-21-frontend-refonte-v1-MASTER.md`
- **Stack** : React 19, Vite 7, Tailwind CSS 4, TanStack Query 5, Recharts 3, react-router-dom 7, react-hook-form 7, zod 3, Vitest, Testing Library
- **Méthodologie** : TDD strict (Red → Green → Refactor). Un commit par cycle.
- **Co-author** : `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- **Prérequis validés** :
  - Lot 1 mergé (stubs `PremiumV2`, `AccountV2`, layout V2, routing `/v2/*`)
  - Lot 2 mergé (tokens design, primitives Tailwind, `StatTile`, `Card`, `Button`, `Chip`, `Modal`, `Tabs`)
  - Backend endpoints existants : `/api/public/track-record/live`, `/api/user/bankroll`, `/api/user/bankroll/bets`, `/api/user/bankroll/roi-by-market`, `/api/user/bankroll/settings`, `/api/user/profile`, `/api/user/subscription`, `/api/user/invoices`, `/api/billing/portal`, `/api/user/notifications/channels`, `/api/user/notifications/rules`, `/api/user/notifications/telegram/token`, `/api/user/notifications/push/subscribe`
- **Scope** : 2 pages (`/premium`, `/compte`) + 4 onglets compte + rules builder composable. ~28 composants, ~12 hooks, 6 schemas zod.

## Objectifs

1. Livrer `/premium` en landing V1 avec proof LIVE (StatTiles + courbe ROI 90j).
2. Livrer `/compte` avec 4 onglets navigables via `react-router` nested routes.
3. Rules builder composable (geste différenciant) avec validation zod composable.
4. Flux Stripe portal, Telegram deep-link, Push Service Worker.
5. 100% tests verts, couverture ≥ 90% sur composants et hooks.

## Architecture cible

```
dashboard/src/
├── pages/v2/
│   ├── PremiumV2.tsx                       (remplace stub Lot 1)
│   ├── AccountV2.tsx                       (wrapper tabs + Outlet)
│   └── account/
│       ├── ProfileTab.tsx
│       ├── SubscriptionTab.tsx
│       ├── BankrollTab.tsx
│       └── NotificationsTab.tsx
├── components/v2/
│   ├── premium/
│   │   ├── PremiumHero.tsx
│   │   ├── LiveTrackRecord.tsx
│   │   ├── PricingCards.tsx
│   │   ├── TransparencyGuarantee.tsx
│   │   └── FAQShort.tsx
│   └── account/
│       ├── profile/
│       │   └── ProfileForm.tsx
│       ├── subscription/
│       │   ├── SubscriptionStatus.tsx
│       │   └── InvoicesList.tsx
│       ├── bankroll/
│       │   ├── BankrollHeader.tsx
│       │   ├── KPIStrip5.tsx
│       │   ├── BankrollChart.tsx
│       │   ├── ROIByMarketChart.tsx
│       │   ├── BetsTable.tsx
│       │   ├── AddBetModal.tsx
│       │   └── BankrollSettingsModal.tsx
│       └── notifications/
│           ├── ChannelsCard.tsx
│           ├── TelegramConnectFlow.tsx
│           ├── PushPermissionButton.tsx
│           ├── RulesList.tsx
│           ├── RuleRow.tsx
│           ├── RuleBuilderModal.tsx
│           └── DeleteRuleConfirm.tsx
├── hooks/v2/
│   ├── useTrackRecordLive.ts
│   ├── useProfile.ts
│   ├── useSubscription.ts
│   ├── useInvoices.ts
│   ├── useBankroll.ts
│   ├── useBankrollBets.ts
│   ├── useROIByMarket.ts
│   ├── useBankrollSettings.ts
│   ├── useNotificationChannels.ts
│   ├── useNotificationRules.ts
│   ├── useConnectTelegram.ts
│   └── useEnablePush.ts
├── lib/v2/
│   ├── schemas/
│   │   ├── profile.ts          (profileSchema, passwordChangeSchema)
│   │   ├── bets.ts             (betSchema, bankrollSettingsSchema)
│   │   └── rules.ts            (conditionSchema, ruleSchema, channelSchema)
│   └── push/
│       └── sw-register.ts
└── public/
    └── sw.js
```

## Règles globales

- **TDD strict** : test en rouge avant code. Jamais de composant sans test.
- **Un commit par cycle Red-Green-Refactor** (format `feat(v2/<zone>): <objet>` ou `test(v2/<zone>): ...`).
- **Pas de TODO / FIXME / placeholder** dans le code livré.
- **Zod schemas** définis une seule fois dans `src/lib/v2/schemas/` et importés partout.
- **Hooks** définis une seule fois dans `src/hooks/v2/`.
- **Recharts lazy-loaded** via `React.lazy` + `Suspense` (fallback = skeleton card).
- **Tests** : colocation `.test.tsx` à côté du fichier source.
- **Accessibilité** : `aria-label` sur tous les boutons icônes, `role` + `aria-selected` sur tabs.
- **TypeScript strict** : pas de `any`, pas de `@ts-ignore`.

---

## Task 0 — Setup zod schemas partagés

**Objectif** : créer les schemas zod réutilisés dans tout le lot avant d'écrire un seul composant.

### Red

**Fichier** : `dashboard/src/lib/v2/schemas/profile.test.ts`

```ts
import { describe, it, expect } from 'vitest';
import { profileSchema, passwordChangeSchema } from './profile';

describe('profileSchema', () => {
  it('accepts valid pseudo', () => {
    const r = profileSchema.safeParse({ pseudo: 'JohnDoe' });
    expect(r.success).toBe(true);
  });
  it('rejects pseudo under 3 chars', () => {
    const r = profileSchema.safeParse({ pseudo: 'ab' });
    expect(r.success).toBe(false);
  });
  it('rejects pseudo over 24 chars', () => {
    const r = profileSchema.safeParse({ pseudo: 'x'.repeat(25) });
    expect(r.success).toBe(false);
  });
  it('rejects pseudo with spaces', () => {
    const r = profileSchema.safeParse({ pseudo: 'john doe' });
    expect(r.success).toBe(false);
  });
});

describe('passwordChangeSchema', () => {
  it('requires current + new (min 8) + confirm matching', () => {
    const ok = passwordChangeSchema.safeParse({
      current: 'oldpass123',
      next: 'newpass123',
      confirm: 'newpass123',
    });
    expect(ok.success).toBe(true);
  });
  it('rejects mismatch', () => {
    const r = passwordChangeSchema.safeParse({
      current: 'oldpass123',
      next: 'newpass123',
      confirm: 'other',
    });
    expect(r.success).toBe(false);
  });
  it('rejects short new password', () => {
    const r = passwordChangeSchema.safeParse({
      current: 'oldpass123',
      next: 'short',
      confirm: 'short',
    });
    expect(r.success).toBe(false);
  });
});
```

**Fichier** : `dashboard/src/lib/v2/schemas/bets.test.ts`

```ts
import { describe, it, expect } from 'vitest';
import { betSchema, bankrollSettingsSchema } from './bets';

describe('betSchema', () => {
  const base = {
    fixtureLabel: 'PSG - OM',
    market: '1X2',
    pick: 'Home',
    odds: 1.85,
    stake: 25,
    status: 'PENDING' as const,
    placedAt: '2026-04-21T10:00:00Z',
  };
  it('accepts valid bet', () => {
    expect(betSchema.safeParse(base).success).toBe(true);
  });
  it('rejects odds < 1.01', () => {
    expect(betSchema.safeParse({ ...base, odds: 1 }).success).toBe(false);
  });
  it('rejects negative stake', () => {
    expect(betSchema.safeParse({ ...base, stake: -1 }).success).toBe(false);
  });
  it('rejects invalid status', () => {
    expect(betSchema.safeParse({ ...base, status: 'FOO' }).success).toBe(false);
  });
});

describe('bankrollSettingsSchema', () => {
  it('accepts valid settings', () => {
    const r = bankrollSettingsSchema.safeParse({
      initialStake: 1000,
      kellyFraction: 0.25,
      stakeCapPct: 5,
    });
    expect(r.success).toBe(true);
  });
  it('rejects kelly not in allowed values', () => {
    const r = bankrollSettingsSchema.safeParse({
      initialStake: 1000,
      kellyFraction: 0.33,
      stakeCapPct: 5,
    });
    expect(r.success).toBe(false);
  });
  it('rejects stakeCapPct > 25', () => {
    const r = bankrollSettingsSchema.safeParse({
      initialStake: 1000,
      kellyFraction: 0.25,
      stakeCapPct: 30,
    });
    expect(r.success).toBe(false);
  });
});
```

**Fichier** : `dashboard/src/lib/v2/schemas/rules.test.ts`

```ts
import { describe, it, expect } from 'vitest';
import { conditionSchema, ruleSchema } from './rules';

describe('conditionSchema', () => {
  it('accepts edge_min with number', () => {
    const r = conditionSchema.safeParse({ type: 'edge_min', value: 5 });
    expect(r.success).toBe(true);
  });
  it('accepts league_in with string array', () => {
    const r = conditionSchema.safeParse({ type: 'league_in', value: ['L1', 'PL'] });
    expect(r.success).toBe(true);
  });
  it('rejects edge_min with string value', () => {
    const r = conditionSchema.safeParse({ type: 'edge_min', value: 'foo' });
    expect(r.success).toBe(false);
  });
  it('rejects unknown type', () => {
    const r = conditionSchema.safeParse({ type: 'xyz', value: 1 });
    expect(r.success).toBe(false);
  });
});

describe('ruleSchema', () => {
  const base = {
    name: 'Value bets L1',
    conditions: [{ type: 'edge_min' as const, value: 5 }],
    logic: 'AND' as const,
    channels: ['email' as const],
    pauseSuggestion: false,
    enabled: true,
  };
  it('accepts minimal valid rule', () => {
    expect(ruleSchema.safeParse(base).success).toBe(true);
  });
  it('rejects empty name', () => {
    expect(ruleSchema.safeParse({ ...base, name: '' }).success).toBe(false);
  });
  it('rejects 0 conditions', () => {
    expect(ruleSchema.safeParse({ ...base, conditions: [] }).success).toBe(false);
  });
  it('rejects more than 3 conditions', () => {
    const many = Array(4).fill({ type: 'edge_min', value: 5 });
    expect(ruleSchema.safeParse({ ...base, conditions: many }).success).toBe(false);
  });
  it('rejects 0 channels', () => {
    expect(ruleSchema.safeParse({ ...base, channels: [] }).success).toBe(false);
  });
});
```

### Green

**Fichier** : `dashboard/src/lib/v2/schemas/profile.ts`

```ts
import { z } from 'zod';

export const profileSchema = z.object({
  pseudo: z
    .string()
    .min(3, 'Pseudo trop court (min 3)')
    .max(24, 'Pseudo trop long (max 24)')
    .regex(/^[A-Za-z0-9_-]+$/, 'Caractères autorisés : A-Z, a-z, 0-9, _ -'),
});
export type ProfileInput = z.infer<typeof profileSchema>;

export const passwordChangeSchema = z
  .object({
    current: z.string().min(8, 'Min 8 caractères'),
    next: z.string().min(8, 'Min 8 caractères'),
    confirm: z.string().min(8, 'Min 8 caractères'),
  })
  .refine((d) => d.next === d.confirm, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirm'],
  });
export type PasswordChangeInput = z.infer<typeof passwordChangeSchema>;
```

**Fichier** : `dashboard/src/lib/v2/schemas/bets.ts`

```ts
import { z } from 'zod';

export const betStatusEnum = z.enum(['WIN', 'LOSS', 'PENDING', 'VOID']);
export type BetStatus = z.infer<typeof betStatusEnum>;

export const betSchema = z.object({
  fixtureLabel: z.string().min(1),
  market: z.string().min(1),
  pick: z.string().min(1),
  odds: z.number().min(1.01).max(1000),
  stake: z.number().positive(),
  status: betStatusEnum,
  placedAt: z.string().datetime(),
});
export type BetInput = z.infer<typeof betSchema>;

export const bankrollSettingsSchema = z.object({
  initialStake: z.number().positive(),
  kellyFraction: z.union([z.literal(0.1), z.literal(0.25), z.literal(0.5)]),
  stakeCapPct: z.number().min(0.5).max(25),
});
export type BankrollSettingsInput = z.infer<typeof bankrollSettingsSchema>;
```

**Fichier** : `dashboard/src/lib/v2/schemas/rules.ts`

```ts
import { z } from 'zod';

export const conditionTypeEnum = z.enum([
  'edge_min',
  'league_in',
  'sport',
  'confidence',
  'kickoff_within',
  'bankroll_drawdown',
]);
export type ConditionType = z.infer<typeof conditionTypeEnum>;

export const conditionSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('edge_min'), value: z.number().min(0).max(100) }),
  z.object({ type: z.literal('league_in'), value: z.array(z.string()).min(1) }),
  z.object({ type: z.literal('sport'), value: z.enum(['football', 'nhl']) }),
  z.object({ type: z.literal('confidence'), value: z.enum(['LOW', 'MED', 'HIGH']) }),
  z.object({ type: z.literal('kickoff_within'), value: z.number().int().min(1).max(168) }),
  z.object({ type: z.literal('bankroll_drawdown'), value: z.number().min(0).max(100) }),
]);
export type ConditionInput = z.infer<typeof conditionSchema>;

export const channelEnum = z.enum(['email', 'telegram', 'push']);
export type Channel = z.infer<typeof channelEnum>;

export const ruleSchema = z.object({
  id: z.string().optional(),
  name: z.string().min(1).max(60),
  conditions: z.array(conditionSchema).min(1).max(3),
  logic: z.enum(['AND', 'OR']),
  channels: z.array(channelEnum).min(1),
  pauseSuggestion: z.boolean(),
  enabled: z.boolean(),
});
export type RuleInput = z.infer<typeof ruleSchema>;
```

### Verify

- `pnpm --filter dashboard test src/lib/v2/schemas` → vert.
- Commit : `test(v2/schemas): add zod schemas for profile, bets, rules (Lot 5)`

---

## Task 1 — Hook `useTrackRecordLive`

### Red

**Fichier** : `dashboard/src/hooks/v2/useTrackRecordLive.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTrackRecordLive } from './useTrackRecordLive';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useTrackRecordLive', () => {
  beforeEach(() => mockFetch.mockReset());

  it('fetches track record and returns data', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        clv30d: 3.2,
        roi90d: 12.5,
        brier30d: 0.21,
        safe90d: 8.1,
        roiCurve: [{ date: '2026-01-01', roi: 1.1 }],
      }),
    });
    const { result } = renderHook(() => useTrackRecordLive(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.clv30d).toBe(3.2);
    expect(mockFetch).toHaveBeenCalledWith('/api/public/track-record/live');
  });

  it('exposes error on failure', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    const { result } = renderHook(() => useTrackRecordLive(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
```

### Green

**Fichier** : `dashboard/src/hooks/v2/useTrackRecordLive.ts`

```ts
import { useQuery } from '@tanstack/react-query';

export interface TrackRecordLive {
  clv30d: number;
  roi90d: number;
  brier30d: number;
  safe90d: number;
  roiCurve: Array<{ date: string; roi: number }>;
}

async function fetchTrackRecord(): Promise<TrackRecordLive> {
  const res = await fetch('/api/public/track-record/live');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function useTrackRecordLive() {
  return useQuery({
    queryKey: ['v2', 'public', 'track-record-live'],
    queryFn: fetchTrackRecord,
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}
```

### Verify

- Commit : `feat(v2/premium): add useTrackRecordLive hook (cache 5min)`

---

## Task 2 — Composant `PremiumHero`

### Red

**Fichier** : `dashboard/src/components/v2/premium/PremiumHero.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PremiumHero } from './PremiumHero';

describe('PremiumHero', () => {
  it('renders title, subtitle and CTAs', () => {
    render(<PremiumHero onPrimary={() => {}} onSecondary={() => {}} />);
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/CLV/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /passer premium/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /voir track record/i })).toBeInTheDocument();
  });

  it('fires callbacks on CTA clicks', async () => {
    const onPrimary = vi.fn();
    const onSecondary = vi.fn();
    const user = userEvent.setup();
    render(<PremiumHero onPrimary={onPrimary} onSecondary={onSecondary} />);
    await user.click(screen.getByRole('button', { name: /passer premium/i }));
    await user.click(screen.getByRole('button', { name: /voir track record/i }));
    expect(onPrimary).toHaveBeenCalledOnce();
    expect(onSecondary).toHaveBeenCalledOnce();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/premium/PremiumHero.tsx`

```tsx
import { Button } from '@/components/v2/primitives/Button';

interface Props {
  onPrimary: () => void;
  onSecondary: () => void;
}

export function PremiumHero({ onPrimary, onSecondary }: Props) {
  return (
    <section className="py-16 text-center">
      <h1 className="text-[44px] font-bold leading-tight tracking-tight text-slate-900 dark:text-white">
        Des prédictions que vous pouvez <span className="text-emerald-500">vérifier</span>
      </h1>
      <p className="mt-4 text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
        Chaque pari est mesuré en CLV (closing line value). Pas de promesse — des chiffres LIVE.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Button variant="primary" size="lg" onClick={onPrimary}>
          Passer Premium
        </Button>
        <Button variant="secondary" size="lg" onClick={onSecondary}>
          Voir track record
        </Button>
      </div>
    </section>
  );
}
```

### Verify

- Commit : `feat(v2/premium): add PremiumHero component`

---

## Task 3 — Composant `LiveTrackRecord`

### Red

**Fichier** : `dashboard/src/components/v2/premium/LiveTrackRecord.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LiveTrackRecord } from './LiveTrackRecord';

vi.mock('@/hooks/v2/useTrackRecordLive', () => ({
  useTrackRecordLive: vi.fn(),
}));
import { useTrackRecordLive } from '@/hooks/v2/useTrackRecordLive';

const wrap = (ui: React.ReactNode) => {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
};

describe('LiveTrackRecord', () => {
  it('shows skeleton while loading', () => {
    (useTrackRecordLive as unknown as vi.Mock).mockReturnValue({ isLoading: true, data: undefined });
    render(wrap(<LiveTrackRecord />));
    expect(screen.getByTestId('tracker-skeleton')).toBeInTheDocument();
  });

  it('renders 4 stat tiles when loaded', async () => {
    (useTrackRecordLive as unknown as vi.Mock).mockReturnValue({
      isLoading: false,
      data: {
        clv30d: 3.2,
        roi90d: 12.5,
        brier30d: 0.21,
        safe90d: 8.1,
        roiCurve: [{ date: '2026-01-01', roi: 1 }],
      },
    });
    render(wrap(<LiveTrackRecord />));
    await waitFor(() => {
      expect(screen.getByText(/CLV 30j/i)).toBeInTheDocument();
      expect(screen.getByText(/ROI 90j/i)).toBeInTheDocument();
      expect(screen.getByText(/Brier 30j/i)).toBeInTheDocument();
      expect(screen.getByText(/Safe 90j/i)).toBeInTheDocument();
    });
  });

  it('renders chart container', async () => {
    (useTrackRecordLive as unknown as vi.Mock).mockReturnValue({
      isLoading: false,
      data: {
        clv30d: 3.2, roi90d: 12.5, brier30d: 0.21, safe90d: 8.1,
        roiCurve: [{ date: '2026-01-01', roi: 1 }],
      },
    });
    render(wrap(<LiveTrackRecord />));
    await waitFor(() => expect(screen.getByTestId('roi-chart-container')).toBeInTheDocument());
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/premium/LiveTrackRecord.tsx`

```tsx
import { lazy, Suspense } from 'react';
import { useTrackRecordLive } from '@/hooks/v2/useTrackRecordLive';
import { StatTile } from '@/components/v2/primitives/StatTile';
import { Card } from '@/components/v2/primitives/Card';

const ROIChart = lazy(() => import('./ROIChart').then((m) => ({ default: m.ROIChart })));

export function LiveTrackRecord() {
  const { data, isLoading } = useTrackRecordLive();

  if (isLoading || !data) {
    return (
      <div data-testid="tracker-skeleton" className="grid animate-pulse gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-2xl bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex items-center gap-2">
        <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-600">LIVE</h2>
        <p className="text-sm text-slate-500">Mis à jour toutes les 5 minutes</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="CLV 30j" value={`${data.clv30d.toFixed(2)}%`} tone="emerald" />
        <StatTile label="ROI 90j" value={`${data.roi90d.toFixed(1)}%`} tone="emerald" />
        <StatTile label="Brier 30j" value={data.brier30d.toFixed(3)} tone="slate" />
        <StatTile label="Safe 90j" value={`${data.safe90d.toFixed(1)}%`} tone="emerald" />
      </div>

      <Card data-testid="roi-chart-container" className="p-6">
        <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />}>
          <ROIChart data={data.roiCurve} />
        </Suspense>
      </Card>
    </section>
  );
}
```

**Fichier** : `dashboard/src/components/v2/premium/ROIChart.tsx`

```tsx
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface Props {
  data: Array<{ date: string; roi: number }>;
}

export function ROIChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={256}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="roiGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
        <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip />
        <Area type="monotone" dataKey="roi" stroke="#10b981" strokeWidth={2} fill="url(#roiGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

### Verify

- Commit : `feat(v2/premium): add LiveTrackRecord with 4 stat tiles + lazy ROI chart`

---

## Task 4 — Composant `PricingCards`

### Red

**Fichier** : `dashboard/src/components/v2/premium/PricingCards.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PricingCards } from './PricingCards';

describe('PricingCards', () => {
  it('renders Free and Premium cards with prices', () => {
    render(<PricingCards onUpgrade={() => {}} />);
    expect(screen.getByText(/Free/i)).toBeInTheDocument();
    expect(screen.getByText(/Premium/i)).toBeInTheDocument();
    expect(screen.getByText(/0\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/14[,.]99\s*€/)).toBeInTheDocument();
  });

  it('highlights Premium with RECOMMANDÉ badge', () => {
    render(<PricingCards onUpgrade={() => {}} />);
    expect(screen.getByText(/recommandé/i)).toBeInTheDocument();
  });

  it('triggers onUpgrade when Premium CTA clicked', async () => {
    const onUpgrade = vi.fn();
    const user = userEvent.setup();
    render(<PricingCards onUpgrade={onUpgrade} />);
    await user.click(screen.getByRole('button', { name: /commencer premium/i }));
    expect(onUpgrade).toHaveBeenCalledOnce();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/premium/PricingCards.tsx`

```tsx
import { Card } from '@/components/v2/primitives/Card';
import { Button } from '@/components/v2/primitives/Button';

interface Props {
  onUpgrade: () => void;
}

const FREE_FEATURES = [
  '3 prédictions par jour',
  'Marchés 1X2 uniquement',
  'Track record public en lecture',
];
const PREMIUM_FEATURES = [
  'Prédictions illimitées + value bets',
  'Tous marchés (BTTS, O/U, Handicaps, Score)',
  'Bankroll + Kelly + ROI par marché',
  'Notifications Telegram / Push / Email',
  'Combos Safe / Fun / Jackpot',
  'Analyses narratives Gemini',
];

export function PricingCards({ onUpgrade }: Props) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="p-8">
        <h3 className="text-xl font-semibold">Free</h3>
        <p className="mt-1 text-sm text-slate-500">Pour découvrir</p>
        <div className="mt-6 flex items-baseline gap-1">
          <span className="text-4xl font-bold">0 €</span>
          <span className="text-sm text-slate-500">/ mois</span>
        </div>
        <ul className="mt-6 space-y-2 text-sm">
          {FREE_FEATURES.map((f) => (
            <li key={f} className="flex items-start gap-2">
              <span className="text-emerald-500">✓</span>
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="relative border-2 border-emerald-500 bg-emerald-50/30 p-8 dark:bg-emerald-950/20">
        <span className="absolute -top-3 right-6 rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-white">
          RECOMMANDÉ
        </span>
        <h3 className="text-xl font-semibold">Premium</h3>
        <p className="mt-1 text-sm text-slate-500">Tout ProbaLab</p>
        <div className="mt-6 flex items-baseline gap-1">
          <span className="text-4xl font-bold">14,99 €</span>
          <span className="text-sm text-slate-500">/ mois</span>
        </div>
        <ul className="mt-6 space-y-2 text-sm">
          {PREMIUM_FEATURES.map((f) => (
            <li key={f} className="flex items-start gap-2">
              <span className="text-emerald-500">✓</span>
              <span>{f}</span>
            </li>
          ))}
        </ul>
        <Button variant="primary" size="lg" className="mt-8 w-full" onClick={onUpgrade}>
          Commencer Premium
        </Button>
      </Card>
    </div>
  );
}
```

### Verify

- Commit : `feat(v2/premium): add PricingCards (Free vs Premium, highlight emerald)`

---

## Task 5 — `TransparencyGuarantee` + `FAQShort`

### Red

**Fichier** : `dashboard/src/components/v2/premium/TransparencyGuarantee.test.tsx`

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TransparencyGuarantee } from './TransparencyGuarantee';

describe('TransparencyGuarantee', () => {
  it('renders guarantee banner with mois offert message', () => {
    render(<TransparencyGuarantee />);
    expect(screen.getByText(/mois offert/i)).toBeInTheDocument();
    expect(screen.getByText(/transparence/i)).toBeInTheDocument();
  });
});
```

**Fichier** : `dashboard/src/components/v2/premium/FAQShort.test.tsx`

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FAQShort } from './FAQShort';

describe('FAQShort', () => {
  it('renders exactly 3 FAQ cards', () => {
    render(<FAQShort />);
    const items = screen.getAllByRole('article');
    expect(items).toHaveLength(3);
  });

  it('mentions CLV in at least one question', () => {
    render(<FAQShort />);
    expect(screen.getByText(/CLV/i)).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/premium/TransparencyGuarantee.tsx`

```tsx
export function TransparencyGuarantee() {
  return (
    <section className="rounded-2xl border border-emerald-500/20 bg-emerald-50/50 p-8 text-center dark:bg-emerald-950/20">
      <h3 className="text-lg font-semibold text-emerald-700 dark:text-emerald-300">
        Notre garantie transparence
      </h3>
      <p className="mx-auto mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
        Si le CLV 30 jours devient négatif, vous recevez automatiquement un{' '}
        <strong>mois offert</strong>. Nos chiffres sont publics, vérifiables, mis à jour toutes les 5 minutes.
      </p>
    </section>
  );
}
```

**Fichier** : `dashboard/src/components/v2/premium/FAQShort.tsx`

```tsx
import { Card } from '@/components/v2/primitives/Card';

const FAQ = [
  {
    q: "Qu'est-ce que le CLV ?",
    a: "Closing Line Value : mesure si nos cotes battent le marché à la fermeture. Un CLV > 0 indique un edge réel, vérifiable sur le long terme.",
  },
  {
    q: 'Pourquoi c’est plus fiable que les tipsters ?',
    a: "Les tipsters vendent du ROI court terme, souvent biaisé. ProbaLab publie Brier + CLV + ROI 90j en temps réel — pas de cherry-picking.",
  },
  {
    q: 'Puis-je annuler à tout moment ?',
    a: "Oui. L'abonnement se résilie en un clic via le portail Stripe, sans pénalité ni engagement.",
  },
];

export function FAQShort() {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {FAQ.map((f) => (
        <Card key={f.q} as="article" className="p-6">
          <h4 className="text-sm font-semibold">{f.q}</h4>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{f.a}</p>
        </Card>
      ))}
    </section>
  );
}
```

### Verify

- Commit : `feat(v2/premium): add TransparencyGuarantee banner + 3-card FAQShort`

---

## Task 6 — Page `PremiumV2` (wire up)

### Red

**Fichier** : `dashboard/src/pages/v2/PremiumV2.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumV2 } from './PremiumV2';

vi.mock('@/hooks/v2/useTrackRecordLive', () => ({
  useTrackRecordLive: () => ({
    isLoading: false,
    data: { clv30d: 3, roi90d: 10, brier30d: 0.2, safe90d: 7, roiCurve: [] },
  }),
}));

const render_ = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <PremiumV2 />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe('PremiumV2', () => {
  it('composes hero + live track + pricing + guarantee + FAQ', () => {
    render_();
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/LIVE/i)).toBeInTheDocument();
    expect(screen.getByText(/Premium/i)).toBeInTheDocument();
    expect(screen.getByText(/mois offert/i)).toBeInTheDocument();
    expect(screen.getAllByRole('article').length).toBeGreaterThanOrEqual(3);
  });
});
```

### Green

**Fichier** : `dashboard/src/pages/v2/PremiumV2.tsx`

```tsx
import { useNavigate } from 'react-router-dom';
import { PremiumHero } from '@/components/v2/premium/PremiumHero';
import { LiveTrackRecord } from '@/components/v2/premium/LiveTrackRecord';
import { PricingCards } from '@/components/v2/premium/PricingCards';
import { TransparencyGuarantee } from '@/components/v2/premium/TransparencyGuarantee';
import { FAQShort } from '@/components/v2/premium/FAQShort';

export function PremiumV2() {
  const nav = useNavigate();
  const upgrade = () => {
    window.location.href = '/api/billing/portal?intent=subscribe';
  };
  return (
    <div className="mx-auto max-w-6xl space-y-20 px-4 py-12">
      <PremiumHero onPrimary={upgrade} onSecondary={() => nav('/track-record')} />
      <LiveTrackRecord />
      <PricingCards onUpgrade={upgrade} />
      <TransparencyGuarantee />
      <FAQShort />
    </div>
  );
}

export default PremiumV2;
```

### Verify

- Commit : `feat(v2/premium): wire PremiumV2 page (hero + proof + pricing + FAQ)`

---

## Task 7 — `AccountV2` wrapper avec 4 tabs (nested routing)

### Red

**Fichier** : `dashboard/src/pages/v2/AccountV2.test.tsx`

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AccountV2 } from './AccountV2';

function Harness({ initial = '/compte/profil' }: { initial?: string }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/compte/*" element={<AccountV2 />}>
            <Route path="profil" element={<div data-testid="tab-profile">PROFIL</div>} />
            <Route path="abonnement" element={<div data-testid="tab-sub">ABO</div>} />
            <Route path="bankroll" element={<div data-testid="tab-bk">BK</div>} />
            <Route path="notifications" element={<div data-testid="tab-notif">NOTIF</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('AccountV2', () => {
  it('renders 4 tab links', () => {
    render(<Harness />);
    expect(screen.getByRole('link', { name: /profil/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /abonnement/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /bankroll/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /notifications/i })).toBeInTheDocument();
  });

  it('renders outlet content for current route', () => {
    render(<Harness initial="/compte/bankroll" />);
    expect(screen.getByTestId('tab-bk')).toBeInTheDocument();
  });

  it('navigates between tabs', async () => {
    const user = userEvent.setup();
    render(<Harness initial="/compte/profil" />);
    expect(screen.getByTestId('tab-profile')).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /notifications/i }));
    expect(screen.getByTestId('tab-notif')).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/pages/v2/AccountV2.tsx`

```tsx
import { NavLink, Outlet } from 'react-router-dom';
import { clsx } from 'clsx';

const TABS = [
  { to: 'profil', label: 'Profil' },
  { to: 'abonnement', label: 'Abonnement' },
  { to: 'bankroll', label: 'Bankroll' },
  { to: 'notifications', label: 'Notifications' },
] as const;

export function AccountV2() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-3xl font-bold">Mon compte</h1>
      <nav className="mt-6 border-b border-slate-200 dark:border-slate-800" role="tablist">
        <ul className="flex gap-1">
          {TABS.map((t) => (
            <li key={t.to}>
              <NavLink
                to={t.to}
                role="tab"
                className={({ isActive }) =>
                  clsx(
                    'inline-block rounded-t-lg px-4 py-2 text-sm font-medium transition',
                    isActive
                      ? 'border-b-2 border-emerald-500 text-emerald-600'
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
                  )
                }
              >
                {t.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="mt-8">
        <Outlet />
      </div>
    </div>
  );
}

export default AccountV2;
```

### Verify

- Ajouter les routes nested dans le router principal :
  ```tsx
  <Route path="/compte" element={<AccountV2 />}>
    <Route index element={<Navigate to="profil" replace />} />
    <Route path="profil" element={<ProfileTab />} />
    <Route path="abonnement" element={<SubscriptionTab />} />
    <Route path="bankroll" element={<BankrollTab />} />
    <Route path="notifications" element={<NotificationsTab />} />
  </Route>
  ```
- Commit : `feat(v2/account): add AccountV2 wrapper with 4 nested tabs`

---

## Task 8 — Hooks compte (`useProfile`, `useSubscription`, `useInvoices`)

### Red

**Fichier** : `dashboard/src/hooks/v2/useProfile.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useProfile, useUpdateProfile } from './useProfile';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useProfile', () => {
  beforeEach(() => mockFetch.mockReset());

  it('fetches profile', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ email: 'a@b.com', pseudo: 'john' }) });
    const { result } = renderHook(() => useProfile(), { wrapper });
    await waitFor(() => expect(result.current.data?.pseudo).toBe('john'));
  });
});

describe('useUpdateProfile', () => {
  beforeEach(() => mockFetch.mockReset());

  it('PATCHes profile pseudo', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ email: 'a@b.com', pseudo: 'new' }) });
    const { result } = renderHook(() => useUpdateProfile(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ pseudo: 'new' });
    });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/user/profile',
      expect.objectContaining({ method: 'PATCH' }),
    );
  });
});
```

### Green

**Fichier** : `dashboard/src/hooks/v2/useProfile.ts`

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ProfileInput } from '@/lib/v2/schemas/profile';

export interface ProfileData {
  email: string;
  pseudo: string;
  avatarUrl?: string;
}

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export function useProfile() {
  return useQuery({
    queryKey: ['v2', 'user', 'profile'],
    queryFn: () => getJSON<ProfileData>('/api/user/profile'),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: ProfileInput) => {
      const r = await fetch('/api/user/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json() as Promise<ProfileData>;
    },
    onSuccess: (data) => {
      qc.setQueryData(['v2', 'user', 'profile'], data);
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (payload: { current: string; next: string }) => {
      const r = await fetch('/api/user/profile/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/user/profile', { method: 'DELETE' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    },
  });
}
```

**Fichier** : `dashboard/src/hooks/v2/useSubscription.ts`

```ts
import { useQuery } from '@tanstack/react-query';

export interface SubscriptionData {
  plan: 'FREE' | 'TRIAL' | 'PREMIUM';
  renewsAt?: string;
  cancelAtPeriodEnd?: boolean;
}

export function useSubscription() {
  return useQuery({
    queryKey: ['v2', 'user', 'subscription'],
    queryFn: async () => {
      const r = await fetch('/api/user/subscription');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as SubscriptionData;
    },
  });
}
```

**Fichier** : `dashboard/src/hooks/v2/useInvoices.ts`

```ts
import { useQuery } from '@tanstack/react-query';

export interface Invoice {
  id: string;
  number: string;
  amountCents: number;
  currency: string;
  status: 'paid' | 'open' | 'void';
  issuedAt: string;
  pdfUrl: string;
}

export function useInvoices() {
  return useQuery({
    queryKey: ['v2', 'user', 'invoices'],
    queryFn: async () => {
      const r = await fetch('/api/user/invoices');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as Invoice[];
    },
  });
}
```

### Verify

- Commit : `feat(v2/account): add hooks useProfile, useSubscription, useInvoices`

---

## Task 9 — `ProfileForm` (onglet Profil)

### Red

**Fichier** : `dashboard/src/components/v2/account/profile/ProfileForm.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileForm } from './ProfileForm';

const updateMock = vi.fn().mockResolvedValue({ email: 'a@b.com', pseudo: 'new' });
const deleteMock = vi.fn().mockResolvedValue(undefined);
const passwordMock = vi.fn().mockResolvedValue({});

vi.mock('@/hooks/v2/useProfile', () => ({
  useProfile: () => ({ data: { email: 'a@b.com', pseudo: 'john' }, isLoading: false }),
  useUpdateProfile: () => ({ mutateAsync: updateMock, isPending: false }),
  useChangePassword: () => ({ mutateAsync: passwordMock, isPending: false }),
  useDeleteAccount: () => ({ mutateAsync: deleteMock, isPending: false }),
}));

const wrap = (ui: React.ReactNode) => (
  <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
);

describe('ProfileForm', () => {
  it('shows email as readonly', () => {
    render(wrap(<ProfileForm />));
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    expect(email.readOnly).toBe(true);
    expect(email.value).toBe('a@b.com');
  });

  it('submits pseudo update when valid', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    const pseudo = screen.getByLabelText(/pseudo/i);
    await user.clear(pseudo);
    await user.type(pseudo, 'new_name');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    await waitFor(() => expect(updateMock).toHaveBeenCalledWith({ pseudo: 'new_name' }));
  });

  it('shows zod error when pseudo too short', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    const pseudo = screen.getByLabelText(/pseudo/i);
    await user.clear(pseudo);
    await user.type(pseudo, 'ab');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    expect(await screen.findByText(/trop court/i)).toBeInTheDocument();
    expect(updateMock).not.toHaveBeenCalled();
  });

  it('opens and confirms delete flow (RGPD)', async () => {
    const user = userEvent.setup();
    render(wrap(<ProfileForm />));
    await user.click(screen.getByRole('button', { name: /supprimer mon compte/i }));
    await user.type(screen.getByLabelText(/tapez SUPPRIMER/i), 'SUPPRIMER');
    await user.click(screen.getByRole('button', { name: /confirmer la suppression/i }));
    await waitFor(() => expect(deleteMock).toHaveBeenCalled());
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/profile/ProfileForm.tsx`

```tsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useProfile, useUpdateProfile, useChangePassword, useDeleteAccount } from '@/hooks/v2/useProfile';
import { profileSchema, passwordChangeSchema, type ProfileInput, type PasswordChangeInput } from '@/lib/v2/schemas/profile';
import { Button } from '@/components/v2/primitives/Button';
import { Card } from '@/components/v2/primitives/Card';

export function ProfileForm() {
  const { data, isLoading } = useProfile();
  const update = useUpdateProfile();
  const changePw = useChangePassword();
  const del = useDeleteAccount();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  const form = useForm<ProfileInput>({
    resolver: zodResolver(profileSchema),
    values: { pseudo: data?.pseudo ?? '' },
  });

  const pwForm = useForm<PasswordChangeInput>({
    resolver: zodResolver(passwordChangeSchema),
    defaultValues: { current: '', next: '', confirm: '' },
  });

  if (isLoading || !data) return <div className="h-24 animate-pulse rounded-xl bg-slate-100" />;

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-semibold">Informations</h2>
        <form onSubmit={form.handleSubmit((v) => update.mutateAsync(v))} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium" htmlFor="email">Email</label>
            <input id="email" type="email" value={data.email} readOnly
              className="mt-1 w-full rounded-lg border bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900" />
          </div>
          <div>
            <label className="block text-sm font-medium" htmlFor="pseudo">Pseudo</label>
            <input id="pseudo" {...form.register('pseudo')}
              className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            {form.formState.errors.pseudo && (
              <p className="mt-1 text-xs text-rose-500">{form.formState.errors.pseudo.message}</p>
            )}
          </div>
          <Button type="submit" variant="primary" disabled={update.isPending}>
            {update.isPending ? 'Enregistrement…' : 'Enregistrer'}
          </Button>
        </form>
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-semibold">Mot de passe</h2>
        <form onSubmit={pwForm.handleSubmit((v) => changePw.mutateAsync({ current: v.current, next: v.next }))} className="mt-4 space-y-4">
          <Field label="Actuel" type="password" {...pwForm.register('current')} error={pwForm.formState.errors.current?.message} />
          <Field label="Nouveau" type="password" {...pwForm.register('next')} error={pwForm.formState.errors.next?.message} />
          <Field label="Confirmer" type="password" {...pwForm.register('confirm')} error={pwForm.formState.errors.confirm?.message} />
          <Button type="submit" variant="secondary" disabled={changePw.isPending}>
            Mettre à jour le mot de passe
          </Button>
        </form>
      </Card>

      <Card className="border-rose-200 p-6 dark:border-rose-900">
        <h2 className="text-lg font-semibold text-rose-600">Zone dangereuse</h2>
        <p className="mt-1 text-sm text-slate-500">Suppression définitive du compte (RGPD).</p>
        {!confirmOpen ? (
          <Button variant="danger" className="mt-4" onClick={() => setConfirmOpen(true)}>
            Supprimer mon compte
          </Button>
        ) : (
          <div className="mt-4 space-y-3">
            <label className="block text-sm" htmlFor="confirm-del">Tapez SUPPRIMER pour confirmer</label>
            <input id="confirm-del" value={confirmText} onChange={(e) => setConfirmText(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm" />
            <div className="flex gap-2">
              <Button variant="danger" disabled={confirmText !== 'SUPPRIMER' || del.isPending}
                onClick={() => del.mutateAsync()}>
                Confirmer la suppression
              </Button>
              <Button variant="ghost" onClick={() => { setConfirmOpen(false); setConfirmText(''); }}>
                Annuler
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

const Field = ({ label, error, ...rest }: any) => (
  <div>
    <label className="block text-sm font-medium">{label}</label>
    <input {...rest} className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
    {error && <p className="mt-1 text-xs text-rose-500">{error}</p>}
  </div>
);
```

### Verify

- Commit : `feat(v2/account): add ProfileForm with pseudo/password/delete RGPD`

---

## Task 10 — `ProfileTab` (page wrapper)

### Red + Green

**Fichier** : `dashboard/src/pages/v2/account/ProfileTab.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileTab } from './ProfileTab';

vi.mock('@/hooks/v2/useProfile', () => ({
  useProfile: () => ({ data: { email: 'a@b.com', pseudo: 'john' }, isLoading: false }),
  useUpdateProfile: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useChangePassword: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteAccount: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('ProfileTab', () => {
  it('renders ProfileForm heading', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ProfileTab />
      </QueryClientProvider>,
    );
    expect(screen.getByText(/informations/i)).toBeInTheDocument();
  });
});
```

**Fichier** : `dashboard/src/pages/v2/account/ProfileTab.tsx`

```tsx
import { ProfileForm } from '@/components/v2/account/profile/ProfileForm';

export function ProfileTab() {
  return <ProfileForm />;
}

export default ProfileTab;
```

### Verify

- Commit : `feat(v2/account): wire ProfileTab page`

---

## Task 11 — `SubscriptionStatus` + `InvoicesList` + `SubscriptionTab`

### Red

**Fichier** : `dashboard/src/components/v2/account/subscription/SubscriptionStatus.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SubscriptionStatus } from './SubscriptionStatus';

vi.mock('@/hooks/v2/useSubscription', () => ({
  useSubscription: () => ({
    data: { plan: 'PREMIUM', renewsAt: '2026-05-21T00:00:00Z', cancelAtPeriodEnd: false },
    isLoading: false,
  }),
}));

describe('SubscriptionStatus', () => {
  it('renders PREMIUM badge and renew date', () => {
    render(<SubscriptionStatus />);
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
    expect(screen.getByText(/21\/05\/2026/)).toBeInTheDocument();
  });
  it('has Stripe portal button', () => {
    render(<SubscriptionStatus />);
    const a = screen.getByRole('link', { name: /gérer l'abonnement/i }) as HTMLAnchorElement;
    expect(a.getAttribute('href')).toBe('/api/billing/portal');
  });
});
```

**Fichier** : `dashboard/src/components/v2/account/subscription/InvoicesList.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InvoicesList } from './InvoicesList';

vi.mock('@/hooks/v2/useInvoices', () => ({
  useInvoices: () => ({
    data: [
      { id: 'i1', number: 'F-001', amountCents: 1499, currency: 'EUR', status: 'paid', issuedAt: '2026-04-01T00:00:00Z', pdfUrl: '/x.pdf' },
      { id: 'i2', number: 'F-002', amountCents: 1499, currency: 'EUR', status: 'paid', issuedAt: '2026-03-01T00:00:00Z', pdfUrl: '/y.pdf' },
    ],
    isLoading: false,
  }),
}));

describe('InvoicesList', () => {
  it('renders rows with amount formatted in euros', () => {
    render(<InvoicesList />);
    expect(screen.getAllByRole('row')).toHaveLength(3); // header + 2 rows
    expect(screen.getAllByText(/14,99/).length).toBeGreaterThan(0);
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/subscription/SubscriptionStatus.tsx`

```tsx
import { useSubscription } from '@/hooks/v2/useSubscription';
import { Card } from '@/components/v2/primitives/Card';
import { Chip } from '@/components/v2/primitives/Chip';

const PLAN_TONES = { FREE: 'slate', TRIAL: 'amber', PREMIUM: 'emerald' } as const;

export function SubscriptionStatus() {
  const { data, isLoading } = useSubscription();
  if (isLoading || !data) return <div className="h-24 animate-pulse rounded-xl bg-slate-100" />;

  const renew = data.renewsAt ? new Date(data.renewsAt).toLocaleDateString('fr-FR') : null;
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Statut</h2>
          <div className="mt-2 flex items-center gap-2">
            <Chip tone={PLAN_TONES[data.plan]}>{data.plan}</Chip>
            {renew && (
              <span className="text-sm text-slate-500">
                {data.cancelAtPeriodEnd ? 'Se termine le' : 'Renouvellement le'} {renew}
              </span>
            )}
          </div>
        </div>
        <a
          href="/api/billing/portal"
          className="inline-flex items-center rounded-lg border px-4 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          Gérer l'abonnement
        </a>
      </div>
    </Card>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/subscription/InvoicesList.tsx`

```tsx
import { useInvoices } from '@/hooks/v2/useInvoices';
import { Card } from '@/components/v2/primitives/Card';

const fmt = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' });

export function InvoicesList() {
  const { data, isLoading } = useInvoices();
  if (isLoading || !data) return <div className="h-24 animate-pulse rounded-xl bg-slate-100" />;

  if (data.length === 0) {
    return (
      <Card className="p-6 text-sm text-slate-500">Aucune facture pour le moment.</Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr>
            <th className="p-3 text-left">N°</th>
            <th className="p-3 text-left">Date</th>
            <th className="p-3 text-right">Montant</th>
            <th className="p-3 text-center">Statut</th>
            <th className="p-3 text-right">PDF</th>
          </tr>
        </thead>
        <tbody>
          {data.map((i) => (
            <tr key={i.id} className="border-t border-slate-200 dark:border-slate-800">
              <td className="p-3">{i.number}</td>
              <td className="p-3">{new Date(i.issuedAt).toLocaleDateString('fr-FR')}</td>
              <td className="p-3 text-right">{fmt.format(i.amountCents / 100)}</td>
              <td className="p-3 text-center">{i.status}</td>
              <td className="p-3 text-right">
                <a href={i.pdfUrl} className="text-emerald-600 hover:underline">Télécharger</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
```

**Fichier** : `dashboard/src/pages/v2/account/SubscriptionTab.tsx`

```tsx
import { SubscriptionStatus } from '@/components/v2/account/subscription/SubscriptionStatus';
import { InvoicesList } from '@/components/v2/account/subscription/InvoicesList';

export function SubscriptionTab() {
  return (
    <div className="space-y-6">
      <SubscriptionStatus />
      <section>
        <h2 className="mb-3 text-lg font-semibold">Factures</h2>
        <InvoicesList />
      </section>
    </div>
  );
}

export default SubscriptionTab;
```

### Verify

- Commit : `feat(v2/account): add SubscriptionStatus + InvoicesList + tab`

---

## Task 12 — Hooks bankroll (`useBankroll`, `useBankrollBets`, `useROIByMarket`, `useBankrollSettings`)

### Red

**Fichier** : `dashboard/src/hooks/v2/useBankroll.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useBankroll, useBankrollBets, useAddBet, useUpdateBet, useDeleteBet } from './useBankroll';
import { useROIByMarket } from './useROIByMarket';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;
const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('bankroll hooks', () => {
  beforeEach(() => mockFetch.mockReset());

  it('useBankroll fetches KPIs + curve', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({
      bankroll: 1200, roiPct: 10, winRate: 0.55, drawdownPct: 5, kellySuggested: 0.25,
      curve: [{ date: '2026-01-01', value: 1000 }],
    }) });
    const { result } = renderHook(() => useBankroll(), { wrapper });
    await waitFor(() => expect(result.current.data?.bankroll).toBe(1200));
  });

  it('useBankrollBets paginates', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ items: [], total: 0 }) });
    const { result } = renderHook(() => useBankrollBets({ page: 1, pageSize: 20 }), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('page=1'));
  });

  it('useROIByMarket fetches with window', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [{ market: '1X2', roiPct: 5 }] });
    const { result } = renderHook(() => useROIByMarket(90), { wrapper });
    await waitFor(() => expect(result.current.data?.[0].market).toBe('1X2'));
    expect(mockFetch).toHaveBeenCalledWith('/api/user/bankroll/roi-by-market?window=90');
  });

  it('useAddBet POSTs bet', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'b1' }) });
    const { result } = renderHook(() => useAddBet(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        fixtureLabel: 'PSG - OM', market: '1X2', pick: 'Home',
        odds: 1.85, stake: 25, status: 'PENDING', placedAt: '2026-04-21T10:00:00Z',
      });
    });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/bankroll/bets', expect.objectContaining({ method: 'POST' }));
  });

  it('useUpdateBet PATCHes bet', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    const { result } = renderHook(() => useUpdateBet(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ id: 'b1', status: 'WIN' });
    });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/bankroll/bets/b1', expect.objectContaining({ method: 'PATCH' }));
  });

  it('useDeleteBet DELETEs bet', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });
    const { result } = renderHook(() => useDeleteBet(), { wrapper });
    await act(async () => { await result.current.mutateAsync('b1'); });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/bankroll/bets/b1', expect.objectContaining({ method: 'DELETE' }));
  });
});
```

### Green

**Fichier** : `dashboard/src/hooks/v2/useBankroll.ts`

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { BetInput, BetStatus } from '@/lib/v2/schemas/bets';

export interface BankrollData {
  bankroll: number;
  roiPct: number;
  winRate: number;
  drawdownPct: number;
  kellySuggested: number;
  curve: Array<{ date: string; value: number }>;
}

export interface Bet extends BetInput {
  id: string;
}

export function useBankroll() {
  return useQuery({
    queryKey: ['v2', 'user', 'bankroll'],
    queryFn: async () => {
      const r = await fetch('/api/user/bankroll');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as BankrollData;
    },
  });
}

export function useBankrollBets({ page, pageSize, status }: { page: number; pageSize: number; status?: BetStatus }) {
  return useQuery({
    queryKey: ['v2', 'user', 'bankroll', 'bets', page, pageSize, status],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
      if (status) params.set('status', status);
      const r = await fetch(`/api/user/bankroll/bets?${params}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as { items: Bet[]; total: number };
    },
  });
}

function invalidateBankroll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['v2', 'user', 'bankroll'] });
}

export function useAddBet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (bet: BetInput) => {
      const r = await fetch('/api/user/bankroll/bets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bet),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json() as Promise<Bet>;
    },
    onSuccess: () => invalidateBankroll(qc),
  });
}

export function useUpdateBet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (p: { id: string } & Partial<BetInput>) => {
      const { id, ...patch } = p;
      const r = await fetch(`/api/user/bankroll/bets/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
    onSuccess: () => invalidateBankroll(qc),
  });
}

export function useDeleteBet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const r = await fetch(`/api/user/bankroll/bets/${id}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    },
    onSuccess: () => invalidateBankroll(qc),
  });
}
```

**Fichier** : `dashboard/src/hooks/v2/useROIByMarket.ts`

```ts
import { useQuery } from '@tanstack/react-query';

export interface ROIByMarket {
  market: string;
  roiPct: number;
  bets: number;
}

export function useROIByMarket(windowDays: 7 | 30 | 90 | 0) {
  return useQuery({
    queryKey: ['v2', 'user', 'bankroll', 'roi-by-market', windowDays],
    queryFn: async () => {
      const r = await fetch(`/api/user/bankroll/roi-by-market?window=${windowDays}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as ROIByMarket[];
    },
  });
}
```

**Fichier** : `dashboard/src/hooks/v2/useBankrollSettings.ts`

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { BankrollSettingsInput } from '@/lib/v2/schemas/bets';

export function useBankrollSettings() {
  return useQuery({
    queryKey: ['v2', 'user', 'bankroll', 'settings'],
    queryFn: async () => {
      const r = await fetch('/api/user/bankroll/settings');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as BankrollSettingsInput;
    },
  });
}

export function useUpdateBankrollSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (s: BankrollSettingsInput) => {
      const r = await fetch('/api/user/bankroll/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(s),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['v2', 'user', 'bankroll'] }),
  });
}
```

### Verify

- Commit : `feat(v2/account): add bankroll hooks (data, bets CRUD, ROI by market, settings)`

---

## Task 13 — `KPIStrip5`

### Red

**Fichier** : `dashboard/src/components/v2/account/bankroll/KPIStrip5.test.tsx`

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KPIStrip5 } from './KPIStrip5';

describe('KPIStrip5', () => {
  it('renders 5 tiles with labels', () => {
    render(<KPIStrip5 data={{ bankroll: 1200, roiPct: 10, winRate: 0.55, drawdownPct: 5, kellySuggested: 0.25 }} />);
    expect(screen.getByText(/Bankroll/i)).toBeInTheDocument();
    expect(screen.getByText(/ROI/i)).toBeInTheDocument();
    expect(screen.getByText(/Win rate/i)).toBeInTheDocument();
    expect(screen.getByText(/Drawdown/i)).toBeInTheDocument();
    expect(screen.getByText(/Kelly/i)).toBeInTheDocument();
  });

  it('formats bankroll as euros', () => {
    render(<KPIStrip5 data={{ bankroll: 1234.5, roiPct: 10, winRate: 0.55, drawdownPct: 5, kellySuggested: 0.25 }} />);
    expect(screen.getByText(/1\s?234[,.]50\s*€/)).toBeInTheDocument();
  });

  it('colors negative ROI red', () => {
    render(<KPIStrip5 data={{ bankroll: 800, roiPct: -10, winRate: 0.4, drawdownPct: 20, kellySuggested: 0.1 }} />);
    expect(screen.getByTestId('tile-roi')).toHaveAttribute('data-tone', 'rose');
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/bankroll/KPIStrip5.tsx`

```tsx
import { StatTile } from '@/components/v2/primitives/StatTile';

const euro = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' });

interface Props {
  data: {
    bankroll: number;
    roiPct: number;
    winRate: number;
    drawdownPct: number;
    kellySuggested: number;
  };
}

export function KPIStrip5({ data }: Props) {
  const roiTone = data.roiPct >= 0 ? 'emerald' : 'rose';
  const ddTone = data.drawdownPct >= 15 ? 'rose' : 'slate';
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <StatTile label="Bankroll" value={euro.format(data.bankroll)} tone="slate" />
      <StatTile data-testid="tile-roi" label="ROI" value={`${data.roiPct.toFixed(1)}%`} tone={roiTone} />
      <StatTile label="Win rate" value={`${(data.winRate * 100).toFixed(0)}%`} tone="slate" />
      <StatTile label="Drawdown" value={`${data.drawdownPct.toFixed(1)}%`} tone={ddTone} />
      <StatTile label="Kelly suggéré" value={data.kellySuggested.toFixed(2)} tone="emerald" />
    </div>
  );
}
```

### Verify

- Commit : `feat(v2/account): add KPIStrip5 component`

---

## Task 14 — `BankrollChart` (courbe avec toggle 7/30/90/All)

### Red

**Fichier** : `dashboard/src/components/v2/account/bankroll/BankrollChart.test.tsx`

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BankrollChart } from './BankrollChart';

const data = Array.from({ length: 120 }, (_, i) => ({
  date: new Date(2026, 0, i + 1).toISOString(),
  value: 1000 + i * 2,
}));

describe('BankrollChart', () => {
  it('renders 4 range toggles', () => {
    render(<BankrollChart data={data} />);
    ['7j', '30j', '90j', 'Tout'].forEach((l) => {
      expect(screen.getByRole('button', { name: l })).toBeInTheDocument();
    });
  });

  it('defaults to 90j active', () => {
    render(<BankrollChart data={data} />);
    expect(screen.getByRole('button', { name: '90j', pressed: true })).toBeInTheDocument();
  });

  it('changes range when clicking 30j', async () => {
    const user = userEvent.setup();
    render(<BankrollChart data={data} />);
    await user.click(screen.getByRole('button', { name: '30j' }));
    expect(screen.getByRole('button', { name: '30j', pressed: true })).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/bankroll/BankrollChart.tsx`

```tsx
import { lazy, Suspense, useMemo, useState } from 'react';
import { Card } from '@/components/v2/primitives/Card';

const Chart = lazy(() => import('./BankrollChartInner').then((m) => ({ default: m.BankrollChartInner })));

type Range = '7' | '30' | '90' | 'all';
const RANGES: Array<{ value: Range; label: string }> = [
  { value: '7', label: '7j' },
  { value: '30', label: '30j' },
  { value: '90', label: '90j' },
  { value: 'all', label: 'Tout' },
];

interface Props {
  data: Array<{ date: string; value: number }>;
}

export function BankrollChart({ data }: Props) {
  const [range, setRange] = useState<Range>('90');
  const sliced = useMemo(() => {
    if (range === 'all') return data;
    const days = Number(range);
    const cutoff = Date.now() - days * 86400000;
    return data.filter((d) => new Date(d.date).getTime() >= cutoff);
  }, [data, range]);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Évolution bankroll</h3>
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
          {RANGES.map((r) => (
            <button
              key={r.value}
              type="button"
              aria-pressed={range === r.value}
              onClick={() => setRange(r.value)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                range === r.value ? 'bg-white shadow dark:bg-slate-700' : 'text-slate-500'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-4 h-64">
        <Suspense fallback={<div className="h-full animate-pulse rounded-xl bg-slate-100" />}>
          <Chart data={sliced} />
        </Suspense>
      </div>
    </Card>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/bankroll/BankrollChartInner.tsx`

```tsx
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface Props {
  data: Array<{ date: string; value: number }>;
}

export function BankrollChartInner({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
        <defs>
          <linearGradient id="bkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
        <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip />
        <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} fill="url(#bkGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

### Verify

- Commit : `feat(v2/account): add BankrollChart with 7/30/90/All toggle (lazy recharts)`

---

## Task 15 — `ROIByMarketChart`

### Red

**Fichier** : `dashboard/src/components/v2/account/bankroll/ROIByMarketChart.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ROIByMarketChart } from './ROIByMarketChart';

vi.mock('@/hooks/v2/useROIByMarket', () => ({
  useROIByMarket: () => ({
    isLoading: false,
    data: [
      { market: '1X2', roiPct: 8.5, bets: 120 },
      { market: 'O/U', roiPct: -2.3, bets: 80 },
      { market: 'BTTS', roiPct: 4.1, bets: 50 },
    ],
  }),
}));

describe('ROIByMarketChart', () => {
  it('renders one bar per market', () => {
    render(<ROIByMarketChart window={90} />);
    expect(screen.getByText('1X2')).toBeInTheDocument();
    expect(screen.getByText('O/U')).toBeInTheDocument();
    expect(screen.getByText('BTTS')).toBeInTheDocument();
  });

  it('shows percentage labels', () => {
    render(<ROIByMarketChart window={90} />);
    expect(screen.getByText(/8\.5%/)).toBeInTheDocument();
    expect(screen.getByText(/-2\.3%/)).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/bankroll/ROIByMarketChart.tsx`

```tsx
import { useROIByMarket } from '@/hooks/v2/useROIByMarket';
import { Card } from '@/components/v2/primitives/Card';

interface Props {
  window: 7 | 30 | 90 | 0;
}

export function ROIByMarketChart({ window }: Props) {
  const { data, isLoading } = useROIByMarket(window);
  if (isLoading || !data) return <div className="h-40 animate-pulse rounded-xl bg-slate-100" />;

  const max = Math.max(10, ...data.map((d) => Math.abs(d.roiPct)));
  return (
    <Card className="p-6">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">ROI par marché</h3>
      <div className="mt-4 space-y-2">
        {data.map((row) => {
          const pos = row.roiPct >= 0;
          const width = (Math.abs(row.roiPct) / max) * 50;
          return (
            <div key={row.market} className="grid grid-cols-[6rem_1fr_4rem] items-center gap-3 text-sm">
              <span className="truncate">{row.market}</span>
              <div className="relative h-5 rounded-md bg-slate-100 dark:bg-slate-800">
                <div className="absolute left-1/2 top-0 h-5 w-px bg-slate-400" />
                <div
                  className={`absolute top-0 h-5 rounded-md ${pos ? 'bg-emerald-500' : 'bg-rose-500'}`}
                  style={{ left: pos ? '50%' : `${50 - width}%`, width: `${width}%` }}
                />
              </div>
              <span className={`text-right tabular-nums ${pos ? 'text-emerald-600' : 'text-rose-600'}`}>
                {row.roiPct.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
```

### Verify

- Commit : `feat(v2/account): add ROIByMarketChart (horizontal bars pos/neg)`

---

## Task 16 — `BetsTable` + `AddBetModal`

### Red

**Fichier** : `dashboard/src/components/v2/account/bankroll/BetsTable.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BetsTable } from './BetsTable';

const mockBets = [
  { id: 'b1', fixtureLabel: 'PSG-OM', market: '1X2', pick: 'Home', odds: 1.85, stake: 25, status: 'WIN', placedAt: '2026-04-20T10:00:00Z' },
  { id: 'b2', fixtureLabel: 'OL-RCL', market: 'BTTS', pick: 'Yes', odds: 1.7, stake: 20, status: 'PENDING', placedAt: '2026-04-21T10:00:00Z' },
];

vi.mock('@/hooks/v2/useBankroll', () => ({
  useBankrollBets: () => ({ data: { items: mockBets, total: 2 }, isLoading: false }),
  useUpdateBet: () => ({ mutateAsync: vi.fn() }),
  useDeleteBet: () => ({ mutateAsync: vi.fn() }),
}));

const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('BetsTable', () => {
  it('renders bets rows with status chips', () => {
    render(wrap(<BetsTable />));
    expect(screen.getByText('PSG-OM')).toBeInTheDocument();
    expect(screen.getByText('WIN')).toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('filters by status', async () => {
    const user = userEvent.setup();
    render(wrap(<BetsTable />));
    await user.selectOptions(screen.getByLabelText(/filtrer/i), 'WIN');
    // re-render triggered; test mocks independent of filter for this unit test
    expect((screen.getByLabelText(/filtrer/i) as HTMLSelectElement).value).toBe('WIN');
  });
});
```

**Fichier** : `dashboard/src/components/v2/account/bankroll/AddBetModal.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AddBetModal } from './AddBetModal';

const addMock = vi.fn().mockResolvedValue({ id: 'new' });
vi.mock('@/hooks/v2/useBankroll', () => ({
  useAddBet: () => ({ mutateAsync: addMock, isPending: false }),
}));

const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('AddBetModal', () => {
  it('submits valid form', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(wrap(<AddBetModal open={true} onClose={onClose} />));
    await user.type(screen.getByLabelText(/match/i), 'PSG - OM');
    await user.type(screen.getByLabelText(/marché/i), '1X2');
    await user.type(screen.getByLabelText(/pick/i), 'Home');
    await user.type(screen.getByLabelText(/cote/i), '1.85');
    await user.type(screen.getByLabelText(/mise/i), '25');
    await user.click(screen.getByRole('button', { name: /ajouter/i }));
    await waitFor(() => expect(addMock).toHaveBeenCalled());
    expect(addMock.mock.calls[0][0].fixtureLabel).toBe('PSG - OM');
    expect(addMock.mock.calls[0][0].odds).toBe(1.85);
  });

  it('shows validation error on odds < 1.01', async () => {
    const user = userEvent.setup();
    render(wrap(<AddBetModal open={true} onClose={vi.fn()} />));
    await user.type(screen.getByLabelText(/match/i), 'A');
    await user.type(screen.getByLabelText(/marché/i), '1X2');
    await user.type(screen.getByLabelText(/pick/i), 'H');
    await user.type(screen.getByLabelText(/cote/i), '1.00');
    await user.type(screen.getByLabelText(/mise/i), '25');
    await user.click(screen.getByRole('button', { name: /ajouter/i }));
    expect(await screen.findByText(/cote invalide/i)).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/bankroll/BetsTable.tsx`

```tsx
import { useState } from 'react';
import { useBankrollBets, useDeleteBet, useUpdateBet } from '@/hooks/v2/useBankroll';
import { Card } from '@/components/v2/primitives/Card';
import { Chip } from '@/components/v2/primitives/Chip';
import { Button } from '@/components/v2/primitives/Button';
import type { BetStatus } from '@/lib/v2/schemas/bets';

const STATUS_TONES: Record<BetStatus, 'emerald' | 'rose' | 'slate' | 'amber'> = {
  WIN: 'emerald',
  LOSS: 'rose',
  PENDING: 'amber',
  VOID: 'slate',
};

export function BetsTable() {
  const [status, setStatus] = useState<BetStatus | ''>('');
  const [page, setPage] = useState(1);
  const { data, isLoading } = useBankrollBets({
    page,
    pageSize: 20,
    status: status || undefined,
  });
  const update = useUpdateBet();
  const del = useDeleteBet();

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Paris récents</h3>
        <label className="flex items-center gap-2 text-sm">
          Filtrer
          <select value={status} onChange={(e) => { setStatus(e.target.value as BetStatus | ''); setPage(1); }}
            className="rounded-md border px-2 py-1 text-sm">
            <option value="">Tous</option>
            <option value="WIN">WIN</option>
            <option value="LOSS">LOSS</option>
            <option value="PENDING">PENDING</option>
            <option value="VOID">VOID</option>
          </select>
        </label>
      </div>
      <div className="mt-4 overflow-x-auto">
        {isLoading || !data ? (
          <div className="h-24 animate-pulse rounded-xl bg-slate-100" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-2">Match</th>
                <th>Marché</th>
                <th>Pick</th>
                <th className="text-right">Cote</th>
                <th className="text-right">Mise</th>
                <th className="text-center">Statut</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((b) => (
                <tr key={b.id} className="border-t border-slate-200 dark:border-slate-800">
                  <td className="py-2">{b.fixtureLabel}</td>
                  <td>{b.market}</td>
                  <td>{b.pick}</td>
                  <td className="text-right tabular-nums">{b.odds.toFixed(2)}</td>
                  <td className="text-right tabular-nums">{b.stake}</td>
                  <td className="text-center">
                    <Chip tone={STATUS_TONES[b.status]}>{b.status}</Chip>
                  </td>
                  <td className="text-right">
                    {b.status === 'PENDING' && (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => update.mutateAsync({ id: b.id, status: 'WIN' })}>W</Button>
                        <Button size="sm" variant="ghost" onClick={() => update.mutateAsync({ id: b.id, status: 'LOSS' })}>L</Button>
                      </>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => del.mutateAsync(b.id)} aria-label="Supprimer">✕</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/bankroll/AddBetModal.tsx`

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Modal } from '@/components/v2/primitives/Modal';
import { Button } from '@/components/v2/primitives/Button';
import { useAddBet } from '@/hooks/v2/useBankroll';
import { betSchema, type BetInput } from '@/lib/v2/schemas/bets';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function AddBetModal({ open, onClose }: Props) {
  const add = useAddBet();
  const form = useForm<BetInput>({
    resolver: zodResolver(betSchema),
    defaultValues: {
      fixtureLabel: '',
      market: '',
      pick: '',
      odds: 2,
      stake: 10,
      status: 'PENDING',
      placedAt: new Date().toISOString(),
    },
  });

  const submit = form.handleSubmit(async (v) => {
    await add.mutateAsync(v);
    form.reset();
    onClose();
  });

  return (
    <Modal open={open} onClose={onClose} title="Ajouter un pari">
      <form onSubmit={submit} className="space-y-3">
        <Field label="Match" error={form.formState.errors.fixtureLabel?.message} {...form.register('fixtureLabel')} />
        <Field label="Marché" error={form.formState.errors.market?.message} {...form.register('market')} />
        <Field label="Pick" error={form.formState.errors.pick?.message} {...form.register('pick')} />
        <Field
          label="Cote"
          type="number"
          step="0.01"
          error={form.formState.errors.odds?.message ? 'Cote invalide' : undefined}
          {...form.register('odds', { valueAsNumber: true })}
        />
        <Field
          label="Mise"
          type="number"
          step="1"
          error={form.formState.errors.stake?.message}
          {...form.register('stake', { valueAsNumber: true })}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>Annuler</Button>
          <Button type="submit" variant="primary" disabled={add.isPending}>Ajouter</Button>
        </div>
      </form>
    </Modal>
  );
}

const Field = ({ label, error, ...rest }: any) => (
  <div>
    <label className="block text-sm font-medium">{label}</label>
    <input {...rest} className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
    {error && <p className="mt-1 text-xs text-rose-500">{error}</p>}
  </div>
);
```

### Verify

- Commit : `feat(v2/account): add BetsTable + AddBetModal with zod validation`

---

## Task 17 — `BankrollSettingsModal` + `BankrollHeader`

### Red

**Fichier** : `dashboard/src/components/v2/account/bankroll/BankrollSettingsModal.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BankrollSettingsModal } from './BankrollSettingsModal';

const saveMock = vi.fn().mockResolvedValue({});
vi.mock('@/hooks/v2/useBankrollSettings', () => ({
  useBankrollSettings: () => ({ data: { initialStake: 1000, kellyFraction: 0.25, stakeCapPct: 5 }, isLoading: false }),
  useUpdateBankrollSettings: () => ({ mutateAsync: saveMock, isPending: false }),
}));
const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('BankrollSettingsModal', () => {
  it('submits with selected Kelly fraction', async () => {
    const user = userEvent.setup();
    render(wrap(<BankrollSettingsModal open onClose={vi.fn()} />));
    await user.selectOptions(screen.getByLabelText(/kelly/i), '0.5');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    await waitFor(() => expect(saveMock).toHaveBeenCalledWith(expect.objectContaining({ kellyFraction: 0.5 })));
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/bankroll/BankrollSettingsModal.tsx`

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Modal } from '@/components/v2/primitives/Modal';
import { Button } from '@/components/v2/primitives/Button';
import { useBankrollSettings, useUpdateBankrollSettings } from '@/hooks/v2/useBankrollSettings';
import { bankrollSettingsSchema, type BankrollSettingsInput } from '@/lib/v2/schemas/bets';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function BankrollSettingsModal({ open, onClose }: Props) {
  const { data } = useBankrollSettings();
  const save = useUpdateBankrollSettings();
  const form = useForm<BankrollSettingsInput>({
    resolver: zodResolver(bankrollSettingsSchema),
    values: data ?? { initialStake: 1000, kellyFraction: 0.25, stakeCapPct: 5 },
  });

  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync(v);
    onClose();
  });

  return (
    <Modal open={open} onClose={onClose} title="Paramètres bankroll">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium" htmlFor="initialStake">Stake initial (€)</label>
          <input id="initialStake" type="number" step="1"
            {...form.register('initialStake', { valueAsNumber: true })}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium" htmlFor="kellyFraction">Kelly fraction</label>
          <select
            id="kellyFraction"
            {...form.register('kellyFraction', { valueAsNumber: true })}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
          >
            <option value={0.1}>0.10 (conservateur)</option>
            <option value={0.25}>0.25 (équilibré)</option>
            <option value={0.5}>0.50 (agressif)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium" htmlFor="stakeCapPct">Stake cap (%)</label>
          <input id="stakeCapPct" type="number" step="0.5"
            {...form.register('stakeCapPct', { valueAsNumber: true })}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>Annuler</Button>
          <Button type="submit" variant="primary" disabled={save.isPending}>Enregistrer</Button>
        </div>
      </form>
    </Modal>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/bankroll/BankrollHeader.tsx`

```tsx
import { Button } from '@/components/v2/primitives/Button';

interface Props {
  onSettings: () => void;
  onAddBet: () => void;
}

export function BankrollHeader({ onSettings, onAddBet }: Props) {
  return (
    <header className="flex items-center justify-between">
      <h2 className="text-2xl font-bold">Bankroll</h2>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={onSettings}>Paramètres</Button>
        <Button variant="primary" onClick={onAddBet}>Ajouter un pari</Button>
      </div>
    </header>
  );
}
```

### Verify

- Commit : `feat(v2/account): add BankrollSettingsModal + BankrollHeader`

---

## Task 18 — `BankrollTab` (compose tout)

### Red

**Fichier** : `dashboard/src/pages/v2/account/BankrollTab.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BankrollTab } from './BankrollTab';

vi.mock('@/hooks/v2/useBankroll', () => ({
  useBankroll: () => ({
    data: { bankroll: 1200, roiPct: 10, winRate: 0.55, drawdownPct: 5, kellySuggested: 0.25,
      curve: [{ date: '2026-01-01', value: 1000 }] },
    isLoading: false,
  }),
  useBankrollBets: () => ({ data: { items: [], total: 0 }, isLoading: false }),
  useAddBet: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateBet: () => ({ mutateAsync: vi.fn() }),
  useDeleteBet: () => ({ mutateAsync: vi.fn() }),
}));
vi.mock('@/hooks/v2/useROIByMarket', () => ({
  useROIByMarket: () => ({ data: [], isLoading: false }),
}));
vi.mock('@/hooks/v2/useBankrollSettings', () => ({
  useBankrollSettings: () => ({ data: { initialStake: 1000, kellyFraction: 0.25, stakeCapPct: 5 }, isLoading: false }),
  useUpdateBankrollSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('BankrollTab', () => {
  it('renders header, KPIs, chart, ROI by market, bets table', () => {
    render(wrap(<BankrollTab />));
    expect(screen.getByRole('heading', { name: /bankroll/i })).toBeInTheDocument();
    expect(screen.getByText(/Kelly/i)).toBeInTheDocument();
    expect(screen.getByText(/ROI par marché/i)).toBeInTheDocument();
    expect(screen.getByText(/Paris récents/i)).toBeInTheDocument();
  });

  it('opens AddBetModal when button clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<BankrollTab />));
    await user.click(screen.getByRole('button', { name: /ajouter un pari/i }));
    expect(screen.getByRole('dialog', { name: /ajouter un pari/i })).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/pages/v2/account/BankrollTab.tsx`

```tsx
import { useState } from 'react';
import { useBankroll } from '@/hooks/v2/useBankroll';
import { BankrollHeader } from '@/components/v2/account/bankroll/BankrollHeader';
import { KPIStrip5 } from '@/components/v2/account/bankroll/KPIStrip5';
import { BankrollChart } from '@/components/v2/account/bankroll/BankrollChart';
import { ROIByMarketChart } from '@/components/v2/account/bankroll/ROIByMarketChart';
import { BetsTable } from '@/components/v2/account/bankroll/BetsTable';
import { AddBetModal } from '@/components/v2/account/bankroll/AddBetModal';
import { BankrollSettingsModal } from '@/components/v2/account/bankroll/BankrollSettingsModal';

export function BankrollTab() {
  const { data, isLoading } = useBankroll();
  const [addOpen, setAddOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  if (isLoading || !data) return <div className="h-24 animate-pulse rounded-xl bg-slate-100" />;

  return (
    <div className="space-y-6">
      <BankrollHeader onSettings={() => setSettingsOpen(true)} onAddBet={() => setAddOpen(true)} />
      <KPIStrip5 data={data} />
      <BankrollChart data={data.curve} />
      <ROIByMarketChart window={90} />
      <BetsTable />
      <AddBetModal open={addOpen} onClose={() => setAddOpen(false)} />
      <BankrollSettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default BankrollTab;
```

### Verify

- Commit : `feat(v2/account): wire BankrollTab (header + KPIs + charts + table + modals)`

---

## Task 19 — Service Worker + hook `useEnablePush`

### Red

**Fichier** : `dashboard/src/lib/v2/push/sw-register.test.ts`

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { registerSWAndSubscribe } from './sw-register';

describe('registerSWAndSubscribe', () => {
  beforeEach(() => {
    vi.stubGlobal('Notification', class {
      static permission = 'default';
      static requestPermission = vi.fn().mockResolvedValue('granted');
    });
    vi.stubGlobal('navigator', {
      ...navigator,
      serviceWorker: {
        register: vi.fn().mockResolvedValue({
          pushManager: {
            subscribe: vi.fn().mockResolvedValue({
              endpoint: 'https://push.example/abc',
              toJSON: () => ({ endpoint: 'https://push.example/abc', keys: { p256dh: 'x', auth: 'y' } }),
            }),
          },
        }),
      },
    });
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }) as any;
  });

  it('requests permission, registers SW, subscribes, POSTs subscription', async () => {
    await registerSWAndSubscribe('VAPID_KEY');
    expect(Notification.requestPermission).toHaveBeenCalled();
    expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js');
    expect(fetch).toHaveBeenCalledWith(
      '/api/user/notifications/push/subscribe',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('throws when permission denied', async () => {
    (Notification.requestPermission as any) = vi.fn().mockResolvedValue('denied');
    await expect(registerSWAndSubscribe('KEY')).rejects.toThrow(/permission/i);
  });
});
```

### Green

**Fichier** : `dashboard/public/sw.js`

```js
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { /* ignore */ }
  const title = data.title || 'ProbaLab';
  const options = {
    body: data.body || '',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    data: data.url ? { url: data.url } : undefined,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(clients.openWindow(url));
});
```

**Fichier** : `dashboard/src/lib/v2/push/sw-register.ts`

```ts
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) output[i] = raw.charCodeAt(i);
  return output;
}

export async function registerSWAndSubscribe(vapidPublicKey: string): Promise<PushSubscription> {
  const perm = await Notification.requestPermission();
  if (perm !== 'granted') throw new Error('Permission notifications refusée');

  const reg = await navigator.serviceWorker.register('/sw.js');
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });

  const body = typeof sub.toJSON === 'function' ? sub.toJSON() : sub;
  const res = await fetch('/api/user/notifications/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return sub as PushSubscription;
}
```

**Fichier** : `dashboard/src/hooks/v2/useEnablePush.ts`

```ts
import { useMutation } from '@tanstack/react-query';
import { registerSWAndSubscribe } from '@/lib/v2/push/sw-register';

export function useEnablePush() {
  return useMutation({
    mutationFn: async () => {
      const vapid = import.meta.env.VITE_VAPID_PUBLIC_KEY as string;
      if (!vapid) throw new Error('VITE_VAPID_PUBLIC_KEY manquante');
      return registerSWAndSubscribe(vapid);
    },
  });
}
```

### Verify

- Commit : `feat(v2/notifications): add service worker + push subscribe flow`

---

## Task 20 — Hooks notifications (`useNotificationChannels`, `useNotificationRules`, `useConnectTelegram`)

### Red

**Fichier** : `dashboard/src/hooks/v2/useNotifications.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useNotificationChannels,
  useNotificationRules,
  useUpsertRule,
  useDeleteRule,
  useToggleRule,
} from './useNotificationRules';
import { useConnectTelegram } from './useConnectTelegram';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch as unknown as typeof fetch;
const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('notification hooks', () => {
  beforeEach(() => mockFetch.mockReset());

  it('useNotificationChannels fetches statuses', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({
      email: { enabled: true, verified: true },
      telegram: { enabled: false },
      push: { enabled: false },
    }) });
    const { result } = renderHook(() => useNotificationChannels(), { wrapper });
    await waitFor(() => expect(result.current.data?.email.verified).toBe(true));
  });

  it('useNotificationRules lists rules', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
    const { result } = renderHook(() => useNotificationRules(), { wrapper });
    await waitFor(() => expect(result.current.data).toEqual([]));
  });

  it('useUpsertRule POSTs new rule', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'r1' }) });
    const { result } = renderHook(() => useUpsertRule(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        name: 'Test', conditions: [{ type: 'edge_min', value: 5 }],
        logic: 'AND', channels: ['email'], pauseSuggestion: false, enabled: true,
      });
    });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/notifications/rules', expect.objectContaining({ method: 'POST' }));
  });

  it('useUpsertRule PUTs existing rule (id present)', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    const { result } = renderHook(() => useUpsertRule(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        id: 'r1', name: 'Test', conditions: [{ type: 'edge_min', value: 5 }],
        logic: 'AND', channels: ['email'], pauseSuggestion: false, enabled: true,
      });
    });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/notifications/rules/r1', expect.objectContaining({ method: 'PUT' }));
  });

  it('useDeleteRule DELETEs', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });
    const { result } = renderHook(() => useDeleteRule(), { wrapper });
    await act(async () => { await result.current.mutateAsync('r1'); });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/notifications/rules/r1', expect.objectContaining({ method: 'DELETE' }));
  });

  it('useToggleRule PATCHes enabled', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    const { result } = renderHook(() => useToggleRule(), { wrapper });
    await act(async () => { await result.current.mutateAsync({ id: 'r1', enabled: false }); });
    expect(mockFetch).toHaveBeenCalledWith('/api/user/notifications/rules/r1', expect.objectContaining({ method: 'PATCH' }));
  });

  it('useConnectTelegram fetches token + builds deep link', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ token: 'ABC123' }) });
    const { result } = renderHook(() => useConnectTelegram(), { wrapper });
    let link = '';
    await act(async () => { link = await result.current.mutateAsync(); });
    expect(link).toBe('https://t.me/probalab_bot?start=ABC123');
  });
});
```

### Green

**Fichier** : `dashboard/src/hooks/v2/useNotificationRules.ts`

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { RuleInput } from '@/lib/v2/schemas/rules';

export interface ChannelsStatus {
  email: { enabled: boolean; verified: boolean };
  telegram: { enabled: boolean; chatId?: string };
  push: { enabled: boolean };
}

export interface Rule extends RuleInput {
  id: string;
  createdAt: string;
}

const RULES_KEY = ['v2', 'user', 'notifications', 'rules'] as const;
const CHANNELS_KEY = ['v2', 'user', 'notifications', 'channels'] as const;

export function useNotificationChannels() {
  return useQuery({
    queryKey: CHANNELS_KEY,
    queryFn: async () => {
      const r = await fetch('/api/user/notifications/channels');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as ChannelsStatus;
    },
  });
}

export function useNotificationRules() {
  return useQuery({
    queryKey: RULES_KEY,
    queryFn: async () => {
      const r = await fetch('/api/user/notifications/rules');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return (await r.json()) as Rule[];
    },
  });
}

export function useUpsertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rule: RuleInput) => {
      const isUpdate = !!rule.id;
      const url = isUpdate
        ? `/api/user/notifications/rules/${rule.id}`
        : '/api/user/notifications/rules';
      const method = isUpdate ? 'PUT' : 'POST';
      const r = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: RULES_KEY }),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const r = await fetch(`/api/user/notifications/rules/${id}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: RULES_KEY }),
  });
}

export function useToggleRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const r = await fetch(`/api/user/notifications/rules/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: RULES_KEY }),
  });
}
```

**Fichier** : `dashboard/src/hooks/v2/useConnectTelegram.ts`

```ts
import { useMutation } from '@tanstack/react-query';

export function useConnectTelegram() {
  return useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/user/notifications/telegram/token', { method: 'POST' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const { token } = (await r.json()) as { token: string };
      return `https://t.me/probalab_bot?start=${token}`;
    },
  });
}
```

### Verify

- Commit : `feat(v2/notifications): add channels + rules CRUD + telegram deep-link hooks`

---

## Task 21 — `ChannelsCard` + `TelegramConnectFlow` + `PushPermissionButton`

### Red

**Fichier** : `dashboard/src/components/v2/account/notifications/ChannelsCard.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChannelsCard } from './ChannelsCard';

const connectMock = vi.fn().mockResolvedValue('https://t.me/probalab_bot?start=ABC');
const enablePushMock = vi.fn().mockResolvedValue({ endpoint: 'x' });
vi.mock('@/hooks/v2/useNotificationRules', () => ({
  useNotificationChannels: () => ({ data: {
    email: { enabled: true, verified: false },
    telegram: { enabled: false },
    push: { enabled: false },
  }, isLoading: false }),
}));
vi.mock('@/hooks/v2/useConnectTelegram', () => ({ useConnectTelegram: () => ({ mutateAsync: connectMock }) }));
vi.mock('@/hooks/v2/useEnablePush', () => ({ useEnablePush: () => ({ mutateAsync: enablePushMock }) }));

const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('ChannelsCard', () => {
  it('renders 3 channels rows', () => {
    render(wrap(<ChannelsCard />));
    expect(screen.getByText(/Telegram/i)).toBeInTheDocument();
    expect(screen.getByText(/Email/i)).toBeInTheDocument();
    expect(screen.getByText(/Push/i)).toBeInTheDocument();
  });

  it('shows "non vérifié" chip for email', () => {
    render(wrap(<ChannelsCard />));
    expect(screen.getByText(/non vérifié/i)).toBeInTheDocument();
  });

  it('connect telegram opens deep link in new tab', async () => {
    const user = userEvent.setup();
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    render(wrap(<ChannelsCard />));
    await user.click(screen.getByRole('button', { name: /connecter telegram/i }));
    await vi.waitFor(() => {
      expect(openSpy).toHaveBeenCalledWith('https://t.me/probalab_bot?start=ABC', '_blank', 'noopener');
    });
    openSpy.mockRestore();
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/notifications/TelegramConnectFlow.tsx`

```tsx
import { Button } from '@/components/v2/primitives/Button';
import { useConnectTelegram } from '@/hooks/v2/useConnectTelegram';

export function TelegramConnectFlow() {
  const connect = useConnectTelegram();
  const onClick = async () => {
    const url = await connect.mutateAsync();
    window.open(url, '_blank', 'noopener');
  };
  return (
    <Button variant="secondary" onClick={onClick} disabled={connect.isPending}>
      Connecter Telegram
    </Button>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/notifications/PushPermissionButton.tsx`

```tsx
import { Button } from '@/components/v2/primitives/Button';
import { useEnablePush } from '@/hooks/v2/useEnablePush';

export function PushPermissionButton() {
  const enable = useEnablePush();
  return (
    <Button variant="secondary" onClick={() => enable.mutateAsync().catch(() => {})} disabled={enable.isPending}>
      Activer notifications push
    </Button>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/notifications/ChannelsCard.tsx`

```tsx
import { Card } from '@/components/v2/primitives/Card';
import { Chip } from '@/components/v2/primitives/Chip';
import { useNotificationChannels } from '@/hooks/v2/useNotificationRules';
import { TelegramConnectFlow } from './TelegramConnectFlow';
import { PushPermissionButton } from './PushPermissionButton';

export function ChannelsCard() {
  const { data, isLoading } = useNotificationChannels();
  if (isLoading || !data) return <div className="h-24 animate-pulse rounded-xl bg-slate-100" />;

  return (
    <Card className="divide-y divide-slate-200 dark:divide-slate-800">
      <Row
        title="Telegram"
        desc="Receive alerts instantly on your phone"
        status={data.telegram.enabled
          ? <Chip tone="emerald">Connecté</Chip>
          : <Chip tone="slate">Non connecté</Chip>}
        action={<TelegramConnectFlow />}
      />
      <Row
        title="Email"
        desc="Daily digest + instant alerts"
        status={data.email.verified
          ? <Chip tone="emerald">Vérifié</Chip>
          : <Chip tone="amber">Non vérifié</Chip>}
      />
      <Row
        title="Push (navigateur)"
        desc="Browser notifications"
        status={data.push.enabled
          ? <Chip tone="emerald">Actif</Chip>
          : <Chip tone="slate">Inactif</Chip>}
        action={!data.push.enabled && <PushPermissionButton />}
      />
    </Card>
  );
}

function Row({ title, desc, status, action }: {
  title: string; desc: string;
  status: React.ReactNode; action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 p-4">
      <div>
        <div className="flex items-center gap-2">
          <h4 className="font-medium">{title}</h4>
          {status}
        </div>
        <p className="text-sm text-slate-500">{desc}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
```

### Verify

- Commit : `feat(v2/notifications): add ChannelsCard + Telegram deep-link + Push activation`

---

## Task 22 — `RuleBuilderModal` (rules builder composable) — cœur du lot

### Red

**Fichier** : `dashboard/src/components/v2/account/notifications/RuleBuilderModal.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RuleBuilderModal } from './RuleBuilderModal';

const upsertMock = vi.fn().mockResolvedValue({});
vi.mock('@/hooks/v2/useNotificationRules', () => ({
  useUpsertRule: () => ({ mutateAsync: upsertMock, isPending: false }),
  useNotificationChannels: () => ({ data: { email: { enabled: true, verified: true }, telegram: { enabled: true }, push: { enabled: true } } }),
}));
const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('RuleBuilderModal', () => {
  it('starts with 1 condition row', () => {
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    expect(screen.getAllByTestId('condition-row')).toHaveLength(1);
  });

  it('adds conditions up to 3 then hides add button', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    await user.click(screen.getByRole('button', { name: /ajouter une condition/i }));
    await user.click(screen.getByRole('button', { name: /ajouter une condition/i }));
    expect(screen.getAllByTestId('condition-row')).toHaveLength(3);
    expect(screen.queryByRole('button', { name: /ajouter une condition/i })).not.toBeInTheDocument();
  });

  it('removes a condition', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    await user.click(screen.getByRole('button', { name: /ajouter une condition/i }));
    expect(screen.getAllByTestId('condition-row')).toHaveLength(2);
    await user.click(screen.getAllByRole('button', { name: /supprimer condition/i })[0]);
    expect(screen.getAllByTestId('condition-row')).toHaveLength(1);
  });

  it('toggles AND/OR logic', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    await user.click(screen.getByRole('button', { name: /ajouter une condition/i }));
    const or = screen.getByRole('button', { name: 'OR' });
    await user.click(or);
    expect(or).toHaveAttribute('aria-pressed', 'true');
  });

  it('submits valid rule with AND edge_min + email channel', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(wrap(<RuleBuilderModal open onClose={onClose} />));
    await user.type(screen.getByLabelText(/nom/i), 'Value L1');
    // default condition row: select edge_min and value 5
    await user.selectOptions(screen.getByLabelText(/type condition 1/i), 'edge_min');
    await user.clear(screen.getByLabelText(/valeur condition 1/i));
    await user.type(screen.getByLabelText(/valeur condition 1/i), '5');
    await user.click(screen.getByLabelText(/email/i));
    await user.click(screen.getByRole('button', { name: /enregistrer la règle/i }));
    await waitFor(() => expect(upsertMock).toHaveBeenCalled());
    const arg = upsertMock.mock.calls[0][0];
    expect(arg.name).toBe('Value L1');
    expect(arg.conditions).toEqual([{ type: 'edge_min', value: 5 }]);
    expect(arg.channels).toContain('email');
    expect(onClose).toHaveBeenCalled();
  });

  it('rejects submit when name empty', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    await user.click(screen.getByRole('button', { name: /enregistrer la règle/i }));
    expect(await screen.findByText(/nom.*obligatoire|requis/i)).toBeInTheDocument();
  });

  it('rejects submit when no channel selected', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    await user.type(screen.getByLabelText(/nom/i), 'X');
    await user.click(screen.getByRole('button', { name: /enregistrer la règle/i }));
    expect(await screen.findByText(/au moins un canal/i)).toBeInTheDocument();
  });

  it('includes pauseSuggestion when box checked', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onClose={vi.fn()} />));
    await user.type(screen.getByLabelText(/nom/i), 'R');
    await user.click(screen.getByLabelText(/email/i));
    await user.click(screen.getByLabelText(/pause paris suggérée/i));
    await user.click(screen.getByRole('button', { name: /enregistrer la règle/i }));
    await waitFor(() => expect(upsertMock.mock.calls.at(-1)[0].pauseSuggestion).toBe(true));
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/notifications/RuleBuilderModal.tsx`

```tsx
import { useMemo, useState } from 'react';
import { Modal } from '@/components/v2/primitives/Modal';
import { Button } from '@/components/v2/primitives/Button';
import { ruleSchema, type RuleInput, type ConditionInput, type Channel } from '@/lib/v2/schemas/rules';
import { useUpsertRule } from '@/hooks/v2/useNotificationRules';

interface Props {
  open: boolean;
  onClose: () => void;
  initial?: RuleInput;
}

const EMPTY_CONDITION: ConditionInput = { type: 'edge_min', value: 5 };

const CONDITION_DEFS = [
  { type: 'edge_min', label: 'Edge min (%)', inputType: 'number' as const },
  { type: 'league_in', label: 'Ligues (CSV)', inputType: 'csv' as const },
  { type: 'sport', label: 'Sport', inputType: 'select' as const, options: ['football', 'nhl'] },
  { type: 'confidence', label: 'Confiance', inputType: 'select' as const, options: ['LOW', 'MED', 'HIGH'] },
  { type: 'kickoff_within', label: 'Coup d\'envoi dans (h)', inputType: 'number' as const },
  { type: 'bankroll_drawdown', label: 'Drawdown bankroll (%)', inputType: 'number' as const },
] as const;

export function RuleBuilderModal({ open, onClose, initial }: Props) {
  const upsert = useUpsertRule();
  const [name, setName] = useState(initial?.name ?? '');
  const [conditions, setConditions] = useState<ConditionInput[]>(initial?.conditions ?? [EMPTY_CONDITION]);
  const [logic, setLogic] = useState<'AND' | 'OR'>(initial?.logic ?? 'AND');
  const [channels, setChannels] = useState<Channel[]>(initial?.channels ?? []);
  const [pauseSuggestion, setPauseSuggestion] = useState(initial?.pauseSuggestion ?? false);
  const [formError, setFormError] = useState<string | null>(null);

  const canAdd = conditions.length < 3;

  const toggleChannel = (c: Channel) => {
    setChannels((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));
  };

  const updateCondition = (idx: number, patch: Partial<ConditionInput>) => {
    setConditions((prev) => prev.map((c, i) => (i === idx ? ({ ...c, ...patch } as ConditionInput) : c)));
  };

  const changeType = (idx: number, type: ConditionInput['type']) => {
    const def = CONDITION_DEFS.find((d) => d.type === type)!;
    let value: ConditionInput['value'];
    if (def.inputType === 'csv') value = [];
    else if (def.inputType === 'select') value = def.options[0] as any;
    else value = 5;
    setConditions((prev) => prev.map((c, i) => (i === idx ? ({ type, value } as ConditionInput) : c)));
  };

  const submit = async () => {
    setFormError(null);
    const payload: RuleInput = {
      ...(initial?.id ? { id: initial.id } : {}),
      name,
      conditions,
      logic,
      channels,
      pauseSuggestion,
      enabled: initial?.enabled ?? true,
    };
    const parsed = ruleSchema.safeParse(payload);
    if (!parsed.success) {
      const issues = parsed.error.issues;
      const nameMissing = issues.find((i) => i.path[0] === 'name');
      const channelsMissing = issues.find((i) => i.path[0] === 'channels');
      if (nameMissing) setFormError('Nom obligatoire');
      else if (channelsMissing) setFormError('Sélectionne au moins un canal');
      else setFormError(issues[0]?.message ?? 'Formulaire invalide');
      return;
    }
    await upsert.mutateAsync(parsed.data);
    onClose();
  };

  const title = useMemo(() => (initial?.id ? 'Modifier la règle' : 'Nouvelle règle'), [initial?.id]);

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-4">
        <div>
          <label htmlFor="rule-name" className="block text-sm font-medium">Nom de la règle</label>
          <input id="rule-name" value={name} onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
        </div>

        <div>
          <h4 className="text-sm font-semibold">Quand…</h4>
          <div className="mt-2 space-y-2">
            {conditions.map((c, i) => (
              <ConditionRow
                key={i}
                index={i}
                value={c}
                onTypeChange={(t) => changeType(i, t)}
                onValueChange={(v) => updateCondition(i, { value: v } as any)}
                onRemove={conditions.length > 1 ? () => setConditions((prev) => prev.filter((_, idx) => idx !== i)) : undefined}
              />
            ))}
          </div>
          {canAdd && (
            <Button type="button" variant="ghost" size="sm" className="mt-2"
              onClick={() => setConditions((prev) => [...prev, EMPTY_CONDITION])}>
              + Ajouter une condition
            </Button>
          )}
        </div>

        {conditions.length > 1 && (
          <div>
            <h4 className="text-sm font-semibold">Relier avec…</h4>
            <div className="mt-2 inline-flex overflow-hidden rounded-lg border">
              {(['AND', 'OR'] as const).map((l) => (
                <button
                  key={l}
                  type="button"
                  aria-pressed={logic === l}
                  onClick={() => setLogic(l)}
                  className={`px-3 py-1 text-xs ${logic === l ? 'bg-emerald-500 text-white' : 'text-slate-500'}`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <h4 className="text-sm font-semibold">Notifier sur…</h4>
          <div className="mt-2 flex gap-2">
            {(['email', 'telegram', 'push'] as const).map((c) => (
              <label key={c} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={channels.includes(c)} onChange={() => toggleChannel(c)} />
                <span className="capitalize">{c}</span>
              </label>
            ))}
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={pauseSuggestion} onChange={(e) => setPauseSuggestion(e.target.checked)} />
          + pause paris suggérée
        </label>

        {formError && <p className="text-xs text-rose-500">{formError}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>Annuler</Button>
          <Button type="button" variant="primary" onClick={submit} disabled={upsert.isPending}>
            Enregistrer la règle
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function ConditionRow({
  index, value, onTypeChange, onValueChange, onRemove,
}: {
  index: number;
  value: ConditionInput;
  onTypeChange: (t: ConditionInput['type']) => void;
  onValueChange: (v: ConditionInput['value']) => void;
  onRemove?: () => void;
}) {
  const def = CONDITION_DEFS.find((d) => d.type === value.type)!;
  return (
    <div data-testid="condition-row" className="flex items-center gap-2">
      <label className="sr-only" htmlFor={`cond-type-${index}`}>Type condition {index + 1}</label>
      <select
        id={`cond-type-${index}`}
        value={value.type}
        onChange={(e) => onTypeChange(e.target.value as ConditionInput['type'])}
        className="rounded-md border px-2 py-1 text-sm"
      >
        {CONDITION_DEFS.map((d) => (
          <option key={d.type} value={d.type}>{d.label}</option>
        ))}
      </select>
      <label className="sr-only" htmlFor={`cond-val-${index}`}>Valeur condition {index + 1}</label>
      {def.inputType === 'number' && (
        <input
          id={`cond-val-${index}`}
          type="number"
          value={value.value as number}
          onChange={(e) => onValueChange(Number(e.target.value))}
          className="w-28 rounded-md border px-2 py-1 text-sm"
        />
      )}
      {def.inputType === 'select' && (
        <select
          id={`cond-val-${index}`}
          value={value.value as string}
          onChange={(e) => onValueChange(e.target.value as any)}
          className="rounded-md border px-2 py-1 text-sm"
        >
          {def.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      )}
      {def.inputType === 'csv' && (
        <input
          id={`cond-val-${index}`}
          type="text"
          value={(value.value as string[]).join(',')}
          onChange={(e) => onValueChange(e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
          placeholder="L1,PL,LaLiga"
          className="w-48 rounded-md border px-2 py-1 text-sm"
        />
      )}
      {onRemove && (
        <button type="button" onClick={onRemove} aria-label="Supprimer condition"
          className="rounded p-1 text-slate-400 hover:text-rose-500">✕</button>
      )}
    </div>
  );
}
```

### Verify

- Commit : `feat(v2/notifications): add composable RuleBuilderModal (max 3 conditions, AND/OR, channels)`

---

## Task 23 — `RuleRow` + `RulesList` + `DeleteRuleConfirm`

### Red

**Fichier** : `dashboard/src/components/v2/account/notifications/RulesList.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RulesList } from './RulesList';

const toggleMock = vi.fn().mockResolvedValue({});
const deleteMock = vi.fn().mockResolvedValue({});

vi.mock('@/hooks/v2/useNotificationRules', () => ({
  useNotificationRules: () => ({ data: [
    { id: 'r1', name: 'Value L1', conditions: [{ type: 'edge_min', value: 5 }], logic: 'AND', channels: ['email'], pauseSuggestion: false, enabled: true, createdAt: '2026-04-01T00:00:00Z' },
  ], isLoading: false }),
  useToggleRule: () => ({ mutateAsync: toggleMock }),
  useDeleteRule: () => ({ mutateAsync: deleteMock }),
  useUpsertRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useNotificationChannels: () => ({ data: { email: { enabled: true, verified: true }, telegram: { enabled: false }, push: { enabled: false } } }),
}));
const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('RulesList', () => {
  it('renders rule rows', () => {
    render(wrap(<RulesList />));
    expect(screen.getByText('Value L1')).toBeInTheDocument();
  });

  it('toggles a rule', async () => {
    const user = userEvent.setup();
    render(wrap(<RulesList />));
    await user.click(screen.getByRole('switch', { name: /activer value l1/i }));
    expect(toggleMock).toHaveBeenCalledWith({ id: 'r1', enabled: false });
  });

  it('opens delete confirm and deletes on confirm', async () => {
    const user = userEvent.setup();
    render(wrap(<RulesList />));
    await user.click(screen.getByRole('button', { name: /menu value l1/i }));
    await user.click(screen.getByRole('menuitem', { name: /supprimer/i }));
    await user.click(screen.getByRole('button', { name: /confirmer/i }));
    expect(deleteMock).toHaveBeenCalledWith('r1');
  });
});
```

### Green

**Fichier** : `dashboard/src/components/v2/account/notifications/RuleRow.tsx`

```tsx
import { useState } from 'react';
import { Chip } from '@/components/v2/primitives/Chip';
import type { Rule } from '@/hooks/v2/useNotificationRules';

interface Props {
  rule: Rule;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function RuleRow({ rule, onToggle, onEdit, onDelete }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="flex items-center justify-between gap-4 p-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="truncate font-medium">{rule.name}</h4>
          {rule.pauseSuggestion && <Chip tone="amber">pause</Chip>}
        </div>
        <div className="mt-1 flex flex-wrap gap-1 text-xs text-slate-500">
          {rule.conditions.map((c, i) => (
            <span key={i} className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
              {c.type}: {Array.isArray(c.value) ? c.value.join(',') : String(c.value)}
            </span>
          ))}
          <span className="px-1">· {rule.logic} ·</span>
          {rule.channels.map((c) => <Chip key={c} tone="emerald">{c}</Chip>)}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          role="switch"
          aria-checked={rule.enabled}
          aria-label={`Activer ${rule.name}`}
          onClick={onToggle}
          className={`h-5 w-9 rounded-full transition ${rule.enabled ? 'bg-emerald-500' : 'bg-slate-300'}`}
        >
          <span className={`block h-4 w-4 rounded-full bg-white transition-transform ${rule.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
        </button>
        <div className="relative">
          <button type="button" aria-label={`Menu ${rule.name}`} aria-haspopup="menu"
            onClick={() => setMenuOpen((v) => !v)}
            className="rounded p-1 text-slate-500 hover:bg-slate-100">⋯</button>
          {menuOpen && (
            <div role="menu" className="absolute right-0 top-8 z-10 w-32 rounded-lg border bg-white py-1 shadow dark:bg-slate-900">
              <button role="menuitem" onClick={() => { setMenuOpen(false); onEdit(); }}
                className="block w-full px-3 py-1 text-left text-sm hover:bg-slate-100">Modifier</button>
              <button role="menuitem" onClick={() => { setMenuOpen(false); onDelete(); }}
                className="block w-full px-3 py-1 text-left text-sm text-rose-600 hover:bg-rose-50">Supprimer</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/notifications/DeleteRuleConfirm.tsx`

```tsx
import { Modal } from '@/components/v2/primitives/Modal';
import { Button } from '@/components/v2/primitives/Button';

interface Props {
  open: boolean;
  ruleName: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteRuleConfirm({ open, ruleName, onCancel, onConfirm }: Props) {
  return (
    <Modal open={open} onClose={onCancel} title="Supprimer la règle">
      <p className="text-sm">
        Supprimer la règle « <strong>{ruleName}</strong> » ? Action irréversible.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>Annuler</Button>
        <Button variant="danger" onClick={onConfirm}>Confirmer</Button>
      </div>
    </Modal>
  );
}
```

**Fichier** : `dashboard/src/components/v2/account/notifications/RulesList.tsx`

```tsx
import { useState } from 'react';
import { Card } from '@/components/v2/primitives/Card';
import { Button } from '@/components/v2/primitives/Button';
import { useNotificationRules, useToggleRule, useDeleteRule, type Rule } from '@/hooks/v2/useNotificationRules';
import { RuleRow } from './RuleRow';
import { RuleBuilderModal } from './RuleBuilderModal';
import { DeleteRuleConfirm } from './DeleteRuleConfirm';

export function RulesList() {
  const { data, isLoading } = useNotificationRules();
  const toggle = useToggleRule();
  const del = useDeleteRule();
  const [editing, setEditing] = useState<Rule | null>(null);
  const [creating, setCreating] = useState(false);
  const [toDelete, setToDelete] = useState<Rule | null>(null);

  if (isLoading || !data) return <div className="h-24 animate-pulse rounded-xl bg-slate-100" />;

  return (
    <section>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Règles</h3>
        <Button variant="primary" onClick={() => setCreating(true)}>Nouvelle règle</Button>
      </div>
      <Card className="mt-3 divide-y divide-slate-200 dark:divide-slate-800">
        {data.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">Aucune règle. Créez-en une pour recevoir des alertes ciblées.</p>
        ) : (
          data.map((r) => (
            <RuleRow
              key={r.id}
              rule={r}
              onToggle={() => toggle.mutateAsync({ id: r.id, enabled: !r.enabled })}
              onEdit={() => setEditing(r)}
              onDelete={() => setToDelete(r)}
            />
          ))
        )}
      </Card>

      {creating && <RuleBuilderModal open onClose={() => setCreating(false)} />}
      {editing && <RuleBuilderModal open initial={editing} onClose={() => setEditing(null)} />}
      {toDelete && (
        <DeleteRuleConfirm
          open
          ruleName={toDelete.name}
          onCancel={() => setToDelete(null)}
          onConfirm={async () => { await del.mutateAsync(toDelete.id); setToDelete(null); }}
        />
      )}
    </section>
  );
}
```

### Verify

- Commit : `feat(v2/notifications): add RuleRow + RulesList + DeleteRuleConfirm`

---

## Task 24 — `NotificationsTab` (page wrapper)

### Red + Green

**Fichier** : `dashboard/src/pages/v2/account/NotificationsTab.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotificationsTab } from './NotificationsTab';

vi.mock('@/hooks/v2/useNotificationRules', () => ({
  useNotificationRules: () => ({ data: [], isLoading: false }),
  useNotificationChannels: () => ({ data: {
    email: { enabled: true, verified: true },
    telegram: { enabled: false }, push: { enabled: false },
  }, isLoading: false }),
  useToggleRule: () => ({ mutateAsync: vi.fn() }),
  useDeleteRule: () => ({ mutateAsync: vi.fn() }),
  useUpsertRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/hooks/v2/useConnectTelegram', () => ({ useConnectTelegram: () => ({ mutateAsync: vi.fn() }) }));
vi.mock('@/hooks/v2/useEnablePush', () => ({ useEnablePush: () => ({ mutateAsync: vi.fn() }) }));

const wrap = (ui: React.ReactNode) => <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;

describe('NotificationsTab', () => {
  it('renders channels section and rules section', () => {
    render(wrap(<NotificationsTab />));
    expect(screen.getByText(/Canaux/i)).toBeInTheDocument();
    expect(screen.getByText(/Règles/i)).toBeInTheDocument();
  });
});
```

**Fichier** : `dashboard/src/pages/v2/account/NotificationsTab.tsx`

```tsx
import { ChannelsCard } from '@/components/v2/account/notifications/ChannelsCard';
import { RulesList } from '@/components/v2/account/notifications/RulesList';

export function NotificationsTab() {
  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-lg font-semibold">Canaux</h2>
        <ChannelsCard />
      </section>
      <RulesList />
    </div>
  );
}

export default NotificationsTab;
```

### Verify

- Commit : `feat(v2/account): wire NotificationsTab (channels + rules)`

---

## Task 25 — Router integration + navigation globale

### Red

**Fichier** : `dashboard/src/App.v2.test.tsx`

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppV2Routes } from './App.v2';

vi.mock('@/hooks/v2/useTrackRecordLive', () => ({
  useTrackRecordLive: () => ({ isLoading: false, data: { clv30d: 3, roi90d: 10, brier30d: 0.2, safe90d: 7, roiCurve: [] } }),
}));
vi.mock('@/hooks/v2/useProfile', () => ({
  useProfile: () => ({ data: { email: 'a@b.com', pseudo: 'john' }, isLoading: false }),
  useUpdateProfile: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useChangePassword: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteAccount: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

const wrap = (initial: string) => (
  <QueryClientProvider client={new QueryClient()}>
    <MemoryRouter initialEntries={[initial]}>
      <AppV2Routes />
    </MemoryRouter>
  </QueryClientProvider>
);

describe('AppV2Routes', () => {
  it('renders /premium page', () => {
    render(wrap('/premium'));
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('redirects /compte → /compte/profil', () => {
    render(wrap('/compte'));
    expect(screen.getByText(/informations/i)).toBeInTheDocument();
  });
});
```

### Green

**Fichier** : `dashboard/src/App.v2.tsx` (à modifier — ajouter les routes Lot 5)

```tsx
import { Navigate, Route, Routes } from 'react-router-dom';
import { PremiumV2 } from '@/pages/v2/PremiumV2';
import { AccountV2 } from '@/pages/v2/AccountV2';
import { ProfileTab } from '@/pages/v2/account/ProfileTab';
import { SubscriptionTab } from '@/pages/v2/account/SubscriptionTab';
import { BankrollTab } from '@/pages/v2/account/BankrollTab';
import { NotificationsTab } from '@/pages/v2/account/NotificationsTab';

export function AppV2Routes() {
  return (
    <Routes>
      <Route path="/premium" element={<PremiumV2 />} />
      <Route path="/compte" element={<AccountV2 />}>
        <Route index element={<Navigate to="profil" replace />} />
        <Route path="profil" element={<ProfileTab />} />
        <Route path="abonnement" element={<SubscriptionTab />} />
        <Route path="bankroll" element={<BankrollTab />} />
        <Route path="notifications" element={<NotificationsTab />} />
      </Route>
    </Routes>
  );
}
```

### Verify

- Commit : `feat(v2): wire routes /premium + /compte/{profil,abonnement,bankroll,notifications}`

---

## Task 26 — Vérification finale + checklist mergeable

### Actions

1. Lancer la suite complète :
   - `pnpm --filter dashboard lint`
   - `pnpm --filter dashboard typecheck`
   - `pnpm --filter dashboard test -- --run`
   - `pnpm --filter dashboard build`
2. Vérifier la couverture : `pnpm --filter dashboard test -- --coverage` — attendu ≥ 90 % sur `src/components/v2/{premium,account}` et `src/hooks/v2`.
3. Smoke test manuel en dev (`pnpm --filter dashboard dev`) :
   - `/premium` : hero + LIVE tiles + courbe + pricing + garantie + 3 FAQ
   - `/compte/profil` : submit pseudo + flux delete
   - `/compte/abonnement` : badge plan + Stripe portal link pointe `/api/billing/portal`
   - `/compte/bankroll` : KPIs + chart + ROI par marché + table + add/settings modals
   - `/compte/notifications` : 3 canaux + creation règle 2 conditions AND + toggle/delete
4. Vérifier inline :
   - Aucun `TODO`, `FIXME`, `placeholder`, `any`
   - Tous les hooks importés depuis `@/hooks/v2/*` (pas de redéfinition)
   - Tous les schemas importés depuis `@/lib/v2/schemas/*` (pas de redéfinition)
   - `public/sw.js` présent
   - `VITE_VAPID_PUBLIC_KEY` documentée dans `.env.example`
5. Ouvrir PR : `feat(v2): Lot 5 — Premium + Compte (profil, abonnement, bankroll, notifications)`

### Commit final

- Commit : `chore(v2/lot5): verify lint/typecheck/tests green, update .env.example with VAPID key`

---

## Dépendances npm à vérifier dans `dashboard/package.json`

Aucune nouvelle dépendance — toutes présentes dans Lot 1 / 2 :
- `react-hook-form` + `@hookform/resolvers`
- `zod`
- `@tanstack/react-query`
- `recharts`
- `react-router-dom`
- `clsx`

Si manquant : `pnpm --filter dashboard add <pkg>` avant Task 0.

## Variables d'environnement

Ajouter dans `dashboard/.env.example` :
```
VITE_VAPID_PUBLIC_KEY=
```

## Critères d'acceptation (PR)

- [ ] 26 tasks mergées avec commits conventionnels
- [ ] Tous tests verts (`test -- --run`)
- [ ] `typecheck` et `lint` verts
- [ ] Build Vite produit sans warnings bloquants
- [ ] Pages `/premium` et `/compte/*` navigables et fonctionnelles
- [ ] Aucun `TODO` / `any` / placeholder dans le diff
- [ ] Couverture ≥ 90 % sur `src/components/v2/{premium,account}` et `src/hooks/v2`
- [ ] Rules builder : max 3 conditions vérifié, AND/OR fonctionnel, validation zod active
- [ ] Stripe portal, Telegram deep-link et push SW testés manuellement en dev

## Notes

- Les primitives `Button`, `Card`, `Chip`, `Modal`, `StatTile` sont supposées livrées par le Lot 2 dans `src/components/v2/primitives/`. Si une prop de `StatTile` manque (`tone`, `data-testid`, etc.), étendre la primitive dans un mini-commit prefixé `chore(v2/primitives): ...` avant le composant consommateur.
- Les endpoints backend listés en prérequis sont supposés existants ou livrés par un lot backend parallèle ; les tests mockent `fetch` et n'exécutent aucun appel réseau réel.
- Le Service Worker `public/sw.js` minimal n'interfère pas avec le dev HMR Vite (registered uniquement on demand via bouton).
