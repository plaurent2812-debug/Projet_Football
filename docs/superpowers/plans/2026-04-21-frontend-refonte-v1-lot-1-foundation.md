# Frontend Refonte V1 — Lot 1 · Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking. TDD strict : chaque step = une action (2-5 min), test écrit et failing AVANT l'implémentation.

**Goal:** Livrer le socle technique V2 : feature flag `VITE_FRONTEND_V2`, tokens CSS fintech (dark + light), routing V2 parallèle à l'existant, layout shell (header + bottom nav + trial banner), et 9 composants système testables en isolation. En fin de lot, le flag dev active un shell fonctionnel avec pages stubs, et tous les composants système ont des tests verts (Vitest + Testing Library + jest-axe).

**Architecture:** Tout le code V2 vit sous `src/**/v2/`. L'ancien `App.tsx` est renommé `AppLegacy.tsx` et le nouvel `App.tsx` choisit entre `AppLegacy` et `AppV2` via `FRONTEND_V2_ENABLED`. Pas de modification de code legacy hors ce switch racine.

**Spec source:** [docs/superpowers/specs/2026-04-21-frontend-refonte-v1-design.md](../specs/2026-04-21-frontend-refonte-v1-design.md) — sections 4 (routing) et 5 (design system).

**Master plan:** [2026-04-21-frontend-refonte-v1-MASTER.md](./2026-04-21-frontend-refonte-v1-MASTER.md)

---

## Pré-requis

Tous les pré-requis globaux P1–P4 du master plan doivent être exécutés avant de démarrer ce lot. Vérifications supplémentaires propres au lot 1 :

### PR1 · Vérifier présence de Vitest, Testing Library, jest-dom

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
grep -E '"(vitest|@testing-library/react|@testing-library/jest-dom)"' package.json
```

**Expected:** les 3 dépendances sont listées. Si absentes : `npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom`.

### PR2 · Installer jest-axe pour tests d'accessibilité

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
npm install --save-dev jest-axe @types/jest-axe
```

**Expected:** installation propre.

### PR3 · Vérifier que `src/test/setup.ts` existe

```bash
ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard/src/test/setup.ts"
```

**Expected:** le fichier existe et importe `@testing-library/jest-dom`. Sinon le créer :

```ts
import '@testing-library/jest-dom';
import { expect } from 'vitest';
import { toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);
```

### PR4 · Vérifier baseline tests verts

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
npm run test:ci
```

**Expected:** tous les tests existants passent. Ne jamais démarrer un lot sur un baseline rouge.

---

## Task 1 · Feature flag V2

**Files**
- Create : `dashboard/src/lib/v2/featureFlag.ts`
- Create : `dashboard/src/lib/v2/featureFlag.test.ts`

**Steps**

- [ ] **1.1** Écrire le test qui échoue : le helper lit `import.meta.env.VITE_FRONTEND_V2` et retourne un booléen, default false.

  Créer `dashboard/src/lib/v2/featureFlag.test.ts` :

  ```ts
  import { describe, it, expect, vi, beforeEach } from 'vitest';

  describe('isFrontendV2Enabled', () => {
    beforeEach(() => {
      vi.resetModules();
    });

    it('returns false when VITE_FRONTEND_V2 is undefined', async () => {
      vi.stubEnv('VITE_FRONTEND_V2', '');
      const { isFrontendV2Enabled } = await import('./featureFlag');
      expect(isFrontendV2Enabled()).toBe(false);
    });

    it('returns true when VITE_FRONTEND_V2 is "true"', async () => {
      vi.stubEnv('VITE_FRONTEND_V2', 'true');
      const { isFrontendV2Enabled } = await import('./featureFlag');
      expect(isFrontendV2Enabled()).toBe(true);
    });

    it('returns false when VITE_FRONTEND_V2 is "false"', async () => {
      vi.stubEnv('VITE_FRONTEND_V2', 'false');
      const { isFrontendV2Enabled } = await import('./featureFlag');
      expect(isFrontendV2Enabled()).toBe(false);
    });

    it('returns false for any other value', async () => {
      vi.stubEnv('VITE_FRONTEND_V2', 'yes');
      const { isFrontendV2Enabled } = await import('./featureFlag');
      expect(isFrontendV2Enabled()).toBe(false);
    });
  });
  ```

  Lancer :
  ```bash
  cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
  npx vitest run src/lib/v2/featureFlag.test.ts
  ```
  **Expected:** 4 tests fail (module introuvable).

- [ ] **1.2** Implémenter le helper pour faire passer les tests.

  Créer `dashboard/src/lib/v2/featureFlag.ts` :

  ```ts
  /**
   * Feature flag pour la refonte frontend V2.
   * Lu depuis la variable Vite `VITE_FRONTEND_V2`.
   * Default : false (ancien frontend servi).
   */
  export function isFrontendV2Enabled(): boolean {
    const raw = import.meta.env.VITE_FRONTEND_V2;
    return raw === 'true';
  }

  export const FRONTEND_V2_ENABLED: boolean = isFrontendV2Enabled();
  ```

  Relancer :
  ```bash
  npx vitest run src/lib/v2/featureFlag.test.ts
  ```
  **Expected:** 4 tests pass.

- [ ] **1.3** Commit TDD cycle.

  ```bash
  cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
  git add dashboard/src/lib/v2/featureFlag.ts dashboard/src/lib/v2/featureFlag.test.ts
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add VITE_FRONTEND_V2 feature flag helper

  Centralise la lecture de la variable d'env pour basculer entre frontend
  legacy et V2. Default false pour sécurité en prod.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

---

## Task 2 · Types partagés V2

**Files**
- Create : `dashboard/src/types/v2/common.ts`
- Create : `dashboard/src/types/v2/common.test-d.ts`

**Steps**

- [ ] **2.1** Écrire un type-test qui échoue.

  Créer `dashboard/src/types/v2/common.test-d.ts` :

  ```ts
  import { describe, it, expectTypeOf } from 'vitest';
  import type { FixtureId, UserRole, Sport, SubscriptionStatus, League } from './common';

  describe('types/v2/common', () => {
    it('FixtureId is a string brand', () => {
      expectTypeOf<FixtureId>().toMatchTypeOf<string>();
    });

    it('UserRole has the 4 known roles', () => {
      expectTypeOf<UserRole>().toEqualTypeOf<'visitor' | 'free' | 'trial' | 'premium' | 'admin'>();
    });

    it('Sport is football or nhl', () => {
      expectTypeOf<Sport>().toEqualTypeOf<'football' | 'nhl'>();
    });

    it('SubscriptionStatus is one of the Stripe statuses', () => {
      expectTypeOf<SubscriptionStatus>().toEqualTypeOf<
        'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete' | 'none'
      >();
    });

    it('League is a string literal union of supported leagues', () => {
      expectTypeOf<League>().toMatchTypeOf<string>();
    });
  });
  ```

  Lancer :
  ```bash
  npx vitest run src/types/v2/common.test-d.ts
  ```
  **Expected:** fail (module introuvable).

- [ ] **2.2** Implémenter les types.

  Créer `dashboard/src/types/v2/common.ts` :

  ```ts
  /**
   * Types partagés V2.
   * Source de vérité pour tous les composants V2.
   */

  /**
   * fixture_id est TEXT côté DB (lesson 48).
   * Jamais typé en `number` côté frontend.
   */
  export type FixtureId = string;

  export type UserRole = 'visitor' | 'free' | 'trial' | 'premium' | 'admin';

  export type Sport = 'football' | 'nhl';

  export type SubscriptionStatus =
    | 'active'
    | 'trialing'
    | 'past_due'
    | 'canceled'
    | 'incomplete'
    | 'none';

  export type League =
    | 'L1'
    | 'L2'
    | 'PL'
    | 'LaLiga'
    | 'SerieA'
    | 'Bundesliga'
    | 'UCL'
    | 'UEL'
    | 'NHL';

  export interface ProbTriplet {
    home: number;
    draw: number;
    away: number;
  }

  export interface Bookmaker {
    name: string;
    odds: number;
    url?: string;
  }

  export interface MoneyAmount {
    amount: number;
    currency: 'EUR';
  }
  ```

  Relancer :
  ```bash
  npx vitest run src/types/v2/common.test-d.ts
  ```
  **Expected:** 5 tests pass.

- [ ] **2.3** Commit.

  ```bash
  git add dashboard/src/types/v2/common.ts dashboard/src/types/v2/common.test-d.ts
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add shared V2 types (FixtureId, UserRole, Sport, League)

  FixtureId est string strict (lesson 48). Types partagés pour tous les
  composants et hooks V2.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

---

## Task 3 · Tokens CSS fintech

**Files**
- Create : `dashboard/src/styles/v2/tokens.css`
- Modify : `dashboard/src/main.tsx` (import tokens.css)
- Create : `dashboard/src/styles/v2/tokens.test.ts`

**Steps**

- [ ] **3.1** Écrire le test qui vérifie la présence des CSS vars en mode dark.

  Créer `dashboard/src/styles/v2/tokens.test.ts` :

  ```ts
  import { describe, it, expect, beforeAll } from 'vitest';
  import fs from 'node:fs';
  import path from 'node:path';

  describe('tokens.css', () => {
    let css = '';

    beforeAll(() => {
      css = fs.readFileSync(
        path.resolve(__dirname, './tokens.css'),
        'utf-8'
      );
    });

    it('defines :root dark palette', () => {
      expect(css).toMatch(/:root\s*{[^}]*--bg:\s*#0a0e1a/);
      expect(css).toMatch(/--surface:\s*#111827/);
      expect(css).toMatch(/--primary:\s*#10b981/);
      expect(css).toMatch(/--value:\s*#fbbf24/);
      expect(css).toMatch(/--danger:\s*#ef4444/);
    });

    it('defines [data-theme="light"] palette', () => {
      expect(css).toMatch(/\[data-theme="light"\]\s*{[^}]*--bg:\s*#fafaf8/);
      expect(css).toMatch(/--primary:\s*#059669/);
    });

    it('defines spacing scale on 4px grid', () => {
      expect(css).toMatch(/--space-1:\s*4px/);
      expect(css).toMatch(/--space-2:\s*8px/);
      expect(css).toMatch(/--space-4:\s*16px/);
    });

    it('defines focus ring using primary', () => {
      expect(css).toMatch(/--focus-ring:\s*2px solid var\(--primary\)/);
    });
  });
  ```

  Lancer :
  ```bash
  npx vitest run src/styles/v2/tokens.test.ts
  ```
  **Expected:** fail (fichier introuvable).

- [ ] **3.2** Créer `dashboard/src/styles/v2/tokens.css`.

  ```css
  /*
   * ProbaLab V2 design tokens — palette fintech/trading.
   * Dark par défaut, light activable via `data-theme="light"` sur <html>.
   * Grille 4px stricte.
   */

  :root {
    /* Palette — dark default */
    --bg: #0a0e1a;
    --surface: #111827;
    --surface-2: #1f2937;
    --border: #1f2937;
    --text: #e5e7eb;
    --text-muted: #94a3b8;
    --text-faint: #64748b;
    --primary: #10b981;
    --primary-soft: #064e3b;
    --value: #fbbf24;
    --danger: #ef4444;
    --info: #60a5fa;

    /* Typography */
    --font-sans: 'Inter', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', ui-monospace, monospace;

    /* Spacing — 4px grid */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-8: 32px;
    --space-10: 40px;
    --space-12: 48px;

    /* Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;

    /* Focus & transitions */
    --focus-ring: 2px solid var(--primary);
    --transition-fast: 150ms ease-out;

    /* Layout */
    --container-max: 1200px;
    --breakpoint-mobile: 375px;
  }

  [data-theme="light"] {
    --bg: #fafaf8;
    --surface: #ffffff;
    --surface-2: #f4f4f1;
    --border: #e5e5e0;
    --text: #0a0a0a;
    --text-muted: #6b7280;
    --text-faint: #9ca3af;
    --primary: #059669;
    --primary-soft: #d1fae5;
    --value: #d97706;
    --danger: #dc2626;
    --info: #2563eb;
  }

  /* Base V2 — applied to body when V2 enabled via .v2-root class */
  .v2-root {
    background-color: var(--bg);
    color: var(--text);
    font-family: var(--font-sans);
    font-variant-numeric: tabular-nums;
  }

  .v2-root *:focus-visible {
    outline: var(--focus-ring);
    outline-offset: 2px;
  }
  ```

  Relancer :
  ```bash
  npx vitest run src/styles/v2/tokens.test.ts
  ```
  **Expected:** 4 tests pass.

- [ ] **3.3** Importer les tokens depuis `main.tsx`.

  Localiser le fichier :
  ```bash
  cat "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard/src/main.tsx"
  ```

  Ajouter l'import en tête (après les imports React mais avant `index.css`) :

  ```ts
  import './styles/v2/tokens.css';
  ```

  Vérifier que le build fonctionne :
  ```bash
  cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
  npm run build
  ```
  **Expected:** build succeeds, `tokens.css` inclus dans le bundle.

- [ ] **3.4** Commit.

  ```bash
  git add dashboard/src/styles/v2/tokens.css dashboard/src/styles/v2/tokens.test.ts dashboard/src/main.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add fintech design tokens (dark default + light)

  Palette émeraude sur fond nuit, grille 4px, typo Inter tabulaire. Import
  dans main.tsx pour que tout usage de var(--*) soit résolu.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

---

## Task 4 · Routing V2 parallèle

Renommer l'ancien `App.tsx` en `AppLegacy.tsx`, créer `AppV2.tsx` + table de routes, et faire choisir `App.tsx` entre les deux via le flag.

**Files**
- Modify : `dashboard/src/App.tsx` (devient le switcher)
- Create : `dashboard/src/AppLegacy.tsx` (copie de l'ancien App)
- Create : `dashboard/src/app/v2/AppV2.tsx`
- Create : `dashboard/src/app/v2/AppV2.test.tsx`
- Create : `dashboard/src/app/v2/routes.tsx`
- Create : `dashboard/src/pages/v2/HomeV2.tsx`
- Create : `dashboard/src/pages/v2/MatchesV2.tsx`
- Create : `dashboard/src/pages/v2/MatchDetailV2.tsx`
- Create : `dashboard/src/pages/v2/PremiumV2.tsx`
- Create : `dashboard/src/pages/v2/AccountV2.tsx`
- Create : `dashboard/src/pages/v2/LoginV2.tsx`
- Create : `dashboard/src/pages/v2/RegisterV2.tsx`

**Steps**

- [ ] **4.1** Écrire le test qui valide que `AppV2` rend la home V2 par défaut.

  Créer `dashboard/src/app/v2/AppV2.test.tsx` :

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { MemoryRouter } from 'react-router-dom';
  import { AppV2 } from './AppV2';

  describe('AppV2', () => {
    it('renders HomeV2 at /', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/HomeV2 WIP/i)).toBeInTheDocument();
    });

    it('renders MatchesV2 at /matchs', () => {
      render(
        <MemoryRouter initialEntries={['/matchs']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/MatchesV2 WIP/i)).toBeInTheDocument();
    });

    it('renders MatchDetailV2 at /matchs/:fixtureId', () => {
      render(
        <MemoryRouter initialEntries={['/matchs/abc-123']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/MatchDetailV2 WIP/i)).toBeInTheDocument();
    });

    it('renders PremiumV2 at /premium', () => {
      render(
        <MemoryRouter initialEntries={['/premium']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/PremiumV2 WIP/i)).toBeInTheDocument();
    });

    it('renders AccountV2 at /compte', () => {
      render(
        <MemoryRouter initialEntries={['/compte']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/AccountV2 WIP/i)).toBeInTheDocument();
    });

    it('renders LoginV2 at /login', () => {
      render(
        <MemoryRouter initialEntries={['/login']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/LoginV2 WIP/i)).toBeInTheDocument();
    });

    it('renders RegisterV2 at /register', () => {
      render(
        <MemoryRouter initialEntries={['/register']}>
          <AppV2 />
        </MemoryRouter>
      );
      expect(screen.getByText(/RegisterV2 WIP/i)).toBeInTheDocument();
    });
  });
  ```

  Lancer :
  ```bash
  npx vitest run src/app/v2/AppV2.test.tsx
  ```
  **Expected:** fail (modules introuvables).

- [ ] **4.2** Créer les 7 pages stubs.

  `dashboard/src/pages/v2/HomeV2.tsx` :

  ```tsx
  export default function HomeV2() {
    return (
      <main aria-label="Home V2">
        <h1>HomeV2 WIP</h1>
      </main>
    );
  }
  ```

  `dashboard/src/pages/v2/MatchesV2.tsx` :

  ```tsx
  export default function MatchesV2() {
    return (
      <main aria-label="Matches V2">
        <h1>MatchesV2 WIP</h1>
      </main>
    );
  }
  ```

  `dashboard/src/pages/v2/MatchDetailV2.tsx` :

  ```tsx
  import { useParams } from 'react-router-dom';
  import type { FixtureId } from '../../types/v2/common';

  export default function MatchDetailV2() {
    const { fixtureId } = useParams<{ fixtureId: FixtureId }>();
    return (
      <main aria-label="Match detail V2">
        <h1>MatchDetailV2 WIP</h1>
        <p>fixture: {fixtureId}</p>
      </main>
    );
  }
  ```

  `dashboard/src/pages/v2/PremiumV2.tsx` :

  ```tsx
  export default function PremiumV2() {
    return (
      <main aria-label="Premium V2">
        <h1>PremiumV2 WIP</h1>
      </main>
    );
  }
  ```

  `dashboard/src/pages/v2/AccountV2.tsx` :

  ```tsx
  export default function AccountV2() {
    return (
      <main aria-label="Account V2">
        <h1>AccountV2 WIP</h1>
      </main>
    );
  }
  ```

  `dashboard/src/pages/v2/LoginV2.tsx` :

  ```tsx
  export default function LoginV2() {
    return (
      <main aria-label="Login V2">
        <h1>LoginV2 WIP</h1>
      </main>
    );
  }
  ```

  `dashboard/src/pages/v2/RegisterV2.tsx` :

  ```tsx
  export default function RegisterV2() {
    return (
      <main aria-label="Register V2">
        <h1>RegisterV2 WIP</h1>
      </main>
    );
  }
  ```

- [ ] **4.3** Créer la table des routes.

  `dashboard/src/app/v2/routes.tsx` :

  ```tsx
  import type { ReactElement } from 'react';
  import HomeV2 from '../../pages/v2/HomeV2';
  import MatchesV2 from '../../pages/v2/MatchesV2';
  import MatchDetailV2 from '../../pages/v2/MatchDetailV2';
  import PremiumV2 from '../../pages/v2/PremiumV2';
  import AccountV2 from '../../pages/v2/AccountV2';
  import LoginV2 from '../../pages/v2/LoginV2';
  import RegisterV2 from '../../pages/v2/RegisterV2';

  export interface V2Route {
    path: string;
    element: ReactElement;
    isPublic: boolean;
  }

  export const v2Routes: readonly V2Route[] = [
    { path: '/', element: <HomeV2 />, isPublic: true },
    { path: '/matchs', element: <MatchesV2 />, isPublic: true },
    { path: '/matchs/:fixtureId', element: <MatchDetailV2 />, isPublic: true },
    { path: '/premium', element: <PremiumV2 />, isPublic: true },
    { path: '/compte', element: <AccountV2 />, isPublic: false },
    { path: '/login', element: <LoginV2 />, isPublic: true },
    { path: '/register', element: <RegisterV2 />, isPublic: true },
  ] as const;
  ```

- [ ] **4.4** Créer `AppV2.tsx`.

  `dashboard/src/app/v2/AppV2.tsx` :

  ```tsx
  import { Routes, Route } from 'react-router-dom';
  import { v2Routes } from './routes';
  import { LayoutShell } from '../../components/v2/layout/LayoutShell';

  export function AppV2() {
    return (
      <div className="v2-root">
        <LayoutShell>
          <Routes>
            {v2Routes.map((route) => (
              <Route key={route.path} path={route.path} element={route.element} />
            ))}
          </Routes>
        </LayoutShell>
      </div>
    );
  }

  export default AppV2;
  ```

  Note : `LayoutShell` sera créé en Task 5. Le test va d'abord échouer pour cette raison, puis passer après Task 5.

- [ ] **4.5** Créer un `LayoutShell` minimal stub pour débloquer les tests du routing.

  `dashboard/src/components/v2/layout/LayoutShell.tsx` (version minimale, sera étoffée Task 5) :

  ```tsx
  import type { ReactNode } from 'react';

  export interface LayoutShellProps {
    children: ReactNode;
  }

  export function LayoutShell({ children }: LayoutShellProps) {
    return <div data-testid="layout-shell">{children}</div>;
  }
  ```

  Relancer :
  ```bash
  npx vitest run src/app/v2/AppV2.test.tsx
  ```
  **Expected:** 7 tests pass.

- [ ] **4.6** Renommer l'ancien App et câbler le switcher.

  Vérifier le contenu actuel :
  ```bash
  ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard/src/App.tsx"
  ```

  Copier l'ancien vers `AppLegacy.tsx` :
  ```bash
  cp "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard/src/App.tsx" \
     "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard/src/AppLegacy.tsx"
  ```

  Dans `AppLegacy.tsx`, remplacer l'export `export default function App` par `export default function AppLegacy` (si présent) et ajuster l'export nommé si nécessaire. Si l'export est `export default App`, renommer la fonction `App` en `AppLegacy`.

  Réécrire `dashboard/src/App.tsx` :

  ```tsx
  import { FRONTEND_V2_ENABLED } from './lib/v2/featureFlag';
  import AppLegacy from './AppLegacy';
  import { AppV2 } from './app/v2/AppV2';

  export default function App() {
    return FRONTEND_V2_ENABLED ? <AppV2 /> : <AppLegacy />;
  }
  ```

  Vérifier le build :
  ```bash
  npm run build
  ```
  **Expected:** build succeeds. Si erreur d'import sur `AppLegacy`, ajuster l'export par défaut de `AppLegacy.tsx`.

- [ ] **4.7** Lancer toute la suite de tests.

  ```bash
  npm run test:ci
  ```
  **Expected:** tous les tests verts (legacy + nouveaux V2).

- [ ] **4.8** Commit.

  ```bash
  git add dashboard/src/App.tsx dashboard/src/AppLegacy.tsx dashboard/src/app/v2 dashboard/src/pages/v2 dashboard/src/components/v2/layout/LayoutShell.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add AppV2 routing parallel to legacy with feature flag switch

  App.tsx bascule entre AppLegacy (ancien code) et AppV2 (nouveau routing
  7 routes stubs) selon VITE_FRONTEND_V2. Code legacy intouché.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

---

## Task 5 · Layout shell (Header + BottomNav + TrialBanner container)

**Files**
- Create : `dashboard/src/components/v2/layout/HeaderV2.tsx`
- Create : `dashboard/src/components/v2/layout/HeaderV2.test.tsx`
- Create : `dashboard/src/components/v2/layout/BottomNavV2.tsx`
- Create : `dashboard/src/components/v2/layout/BottomNavV2.test.tsx`
- Create : `dashboard/src/components/v2/layout/TrialBannerContainer.tsx`
- Create : `dashboard/src/components/v2/layout/TrialBannerContainer.test.tsx`
- Modify : `dashboard/src/components/v2/layout/LayoutShell.tsx`
- Create : `dashboard/src/components/v2/layout/LayoutShell.test.tsx`

### 5a · HeaderV2

- [ ] **5.1** Écrire le test.

  `dashboard/src/components/v2/layout/HeaderV2.test.tsx` :

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { MemoryRouter } from 'react-router-dom';
  import { axe } from 'jest-axe';
  import { HeaderV2 } from './HeaderV2';

  describe('HeaderV2', () => {
    it('renders logo and nav links on desktop', () => {
      render(
        <MemoryRouter>
          <HeaderV2 userRole="free" />
        </MemoryRouter>
      );
      expect(screen.getByRole('link', { name: /probalab/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /accueil/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /matchs/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /compte/i })).toBeInTheDocument();
    });

    it('shows Free badge when userRole is free', () => {
      render(
        <MemoryRouter>
          <HeaderV2 userRole="free" />
        </MemoryRouter>
      );
      expect(screen.getByText('Free')).toBeInTheDocument();
    });

    it('shows Trial J-X badge when userRole is trial', () => {
      render(
        <MemoryRouter>
          <HeaderV2 userRole="trial" trialDaysLeft={12} />
        </MemoryRouter>
      );
      expect(screen.getByText(/trial j-12/i)).toBeInTheDocument();
    });

    it('shows Premium badge when userRole is premium', () => {
      render(
        <MemoryRouter>
          <HeaderV2 userRole="premium" />
        </MemoryRouter>
      );
      expect(screen.getByText('Premium')).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(
        <MemoryRouter>
          <HeaderV2 userRole="free" />
        </MemoryRouter>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
  ```

  Lancer :
  ```bash
  npx vitest run src/components/v2/layout/HeaderV2.test.tsx
  ```
  **Expected:** fail.

- [ ] **5.2** Implémenter HeaderV2.

  `dashboard/src/components/v2/layout/HeaderV2.tsx` :

  ```tsx
  import { Link } from 'react-router-dom';
  import type { UserRole } from '../../../types/v2/common';

  export interface HeaderV2Props {
    userRole: UserRole;
    trialDaysLeft?: number;
  }

  function roleBadge(role: UserRole, trialDaysLeft?: number): string {
    if (role === 'trial' && typeof trialDaysLeft === 'number') {
      return `Trial J-${trialDaysLeft}`;
    }
    if (role === 'premium') return 'Premium';
    if (role === 'free') return 'Free';
    if (role === 'admin') return 'Admin';
    return '';
  }

  export function HeaderV2({ userRole, trialDaysLeft }: HeaderV2Props) {
    const badge = roleBadge(userRole, trialDaysLeft);
    return (
      <header
        aria-label="Navigation principale"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-3) var(--space-4)',
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <Link to="/" aria-label="ProbaLab — accueil" style={{ color: 'var(--primary)', fontWeight: 700 }}>
          ProbaLab
        </Link>
        <nav aria-label="Navigation" style={{ display: 'flex', gap: 'var(--space-4)' }}>
          <Link to="/" aria-label="Accueil">Accueil</Link>
          <Link to="/matchs" aria-label="Matchs">Matchs</Link>
          <Link to="/compte" aria-label="Compte">Compte</Link>
        </nav>
        {badge && (
          <span
            aria-label={`Statut : ${badge}`}
            style={{
              fontSize: 12,
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--surface-2)',
              color: 'var(--text-muted)',
            }}
          >
            {badge}
          </span>
        )}
      </header>
    );
  }

  export default HeaderV2;
  ```

  Relancer test → **Expected:** 5 tests pass.

- [ ] **5.3** Commit.

  ```bash
  git add dashboard/src/components/v2/layout/HeaderV2.tsx dashboard/src/components/v2/layout/HeaderV2.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add HeaderV2 with sticky nav and role badge

  Header desktop sticky avec logo, 3 liens et badge d'état (Free/Trial J-X/
  Premium). Accessible (aria-labels, contrastes WCAG AA).

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 5b · BottomNavV2

- [ ] **5.4** Écrire le test.

  `dashboard/src/components/v2/layout/BottomNavV2.test.tsx` :

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { MemoryRouter } from 'react-router-dom';
  import { axe } from 'jest-axe';
  import { BottomNavV2 } from './BottomNavV2';

  describe('BottomNavV2', () => {
    it('renders 3 nav items', () => {
      render(
        <MemoryRouter>
          <BottomNavV2 />
        </MemoryRouter>
      );
      expect(screen.getByRole('link', { name: /accueil/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /matchs/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /compte/i })).toBeInTheDocument();
    });

    it('is labeled as navigation landmark', () => {
      render(
        <MemoryRouter>
          <BottomNavV2 />
        </MemoryRouter>
      );
      expect(screen.getByRole('navigation', { name: /navigation mobile/i })).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(
        <MemoryRouter>
          <BottomNavV2 />
        </MemoryRouter>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
  ```

  Lancer → fail.

- [ ] **5.5** Implémenter.

  `dashboard/src/components/v2/layout/BottomNavV2.tsx` :

  ```tsx
  import { Link } from 'react-router-dom';
  import { Home, List, User } from 'lucide-react';

  export function BottomNavV2() {
    return (
      <nav
        aria-label="Navigation mobile"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 40,
          display: 'flex',
          justifyContent: 'space-around',
          alignItems: 'center',
          padding: 'var(--space-2) 0',
          background: 'var(--surface)',
          borderTop: '1px solid var(--border)',
        }}
      >
        <Link to="/" aria-label="Accueil" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, color: 'var(--text)' }}>
          <Home size={20} aria-hidden="true" />
          <span style={{ fontSize: 12 }}>Accueil</span>
        </Link>
        <Link to="/matchs" aria-label="Matchs" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, color: 'var(--text)' }}>
          <List size={20} aria-hidden="true" />
          <span style={{ fontSize: 12 }}>Matchs</span>
        </Link>
        <Link to="/compte" aria-label="Compte" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, color: 'var(--text)' }}>
          <User size={20} aria-hidden="true" />
          <span style={{ fontSize: 12 }}>Compte</span>
        </Link>
      </nav>
    );
  }

  export default BottomNavV2;
  ```

  Relancer → pass.

- [ ] **5.6** Commit.

  ```bash
  git add dashboard/src/components/v2/layout/BottomNavV2.tsx dashboard/src/components/v2/layout/BottomNavV2.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add BottomNavV2 with 3 icons for mobile sticky nav

  Navigation fixed bottom mobile-first avec Lucide icons et aria-labels.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 5c · TrialBannerContainer

- [ ] **5.7** Écrire le test.

  `dashboard/src/components/v2/layout/TrialBannerContainer.test.tsx` :

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { TrialBannerContainer } from './TrialBannerContainer';

  describe('TrialBannerContainer', () => {
    it('renders the banner when role is trial and daysLeft is defined', () => {
      render(<TrialBannerContainer userRole="trial" trialDaysLeft={12} trialEndDate="2026-05-21" />);
      expect(screen.getByRole('region', { name: /trial/i })).toBeInTheDocument();
      expect(screen.getByText(/j-12/i)).toBeInTheDocument();
    });

    it('renders nothing when role is not trial', () => {
      const { container } = render(<TrialBannerContainer userRole="free" />);
      expect(container).toBeEmptyDOMElement();
    });

    it('renders nothing when daysLeft is missing on trial', () => {
      const { container } = render(<TrialBannerContainer userRole="trial" />);
      expect(container).toBeEmptyDOMElement();
    });
  });
  ```

  Lancer → fail.

- [ ] **5.8** Implémenter.

  `dashboard/src/components/v2/layout/TrialBannerContainer.tsx` :

  ```tsx
  import type { UserRole } from '../../../types/v2/common';
  import { TrialBanner } from '../system/TrialBanner';

  export interface TrialBannerContainerProps {
    userRole: UserRole;
    trialDaysLeft?: number;
    trialEndDate?: string;
  }

  export function TrialBannerContainer({ userRole, trialDaysLeft, trialEndDate }: TrialBannerContainerProps) {
    if (userRole !== 'trial' || typeof trialDaysLeft !== 'number') {
      return null;
    }
    return <TrialBanner daysLeft={trialDaysLeft} endDate={trialEndDate} />;
  }

  export default TrialBannerContainer;
  ```

  Note : `TrialBanner` sera créé Task 6 (system). Créer un stub minimal maintenant pour débloquer le test.

  `dashboard/src/components/v2/system/TrialBanner.tsx` (stub minimal, version complète Task 6g) :

  ```tsx
  export interface TrialBannerProps {
    daysLeft: number;
    endDate?: string;
  }

  export function TrialBanner({ daysLeft, endDate }: TrialBannerProps) {
    return (
      <div role="region" aria-label="Trial banner">
        <span>Trial premium · J-{daysLeft}</span>
        {endDate && <span> · jusqu'au {endDate}</span>}
      </div>
    );
  }

  export default TrialBanner;
  ```

  Relancer → pass.

- [ ] **5.9** Commit.

  ```bash
  git add dashboard/src/components/v2/layout/TrialBannerContainer.tsx dashboard/src/components/v2/layout/TrialBannerContainer.test.tsx dashboard/src/components/v2/system/TrialBanner.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add TrialBannerContainer gating logic + TrialBanner stub

  Container affiche TrialBanner uniquement si userRole=trial et daysLeft
  défini. Stub minimal pour TrialBanner (version stylée Task 6).

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 5d · LayoutShell complet

- [ ] **5.10** Écrire le test.

  `dashboard/src/components/v2/layout/LayoutShell.test.tsx` :

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { MemoryRouter } from 'react-router-dom';
  import { LayoutShell } from './LayoutShell';

  describe('LayoutShell', () => {
    it('wraps children with header and bottom nav', () => {
      render(
        <MemoryRouter>
          <LayoutShell userRole="free">
            <p>page content</p>
          </LayoutShell>
        </MemoryRouter>
      );
      expect(screen.getByRole('banner')).toBeInTheDocument();
      expect(screen.getByRole('navigation', { name: /navigation mobile/i })).toBeInTheDocument();
      expect(screen.getByText('page content')).toBeInTheDocument();
    });

    it('renders trial banner when role is trial', () => {
      render(
        <MemoryRouter>
          <LayoutShell userRole="trial" trialDaysLeft={5} trialEndDate="2026-04-26">
            <p>content</p>
          </LayoutShell>
        </MemoryRouter>
      );
      expect(screen.getByRole('region', { name: /trial/i })).toBeInTheDocument();
    });

    it('does not render trial banner when role is free', () => {
      render(
        <MemoryRouter>
          <LayoutShell userRole="free">
            <p>content</p>
          </LayoutShell>
        </MemoryRouter>
      );
      expect(screen.queryByRole('region', { name: /trial/i })).not.toBeInTheDocument();
    });

    it('defaults userRole to visitor when not provided', () => {
      render(
        <MemoryRouter>
          <LayoutShell>
            <p>content</p>
          </LayoutShell>
        </MemoryRouter>
      );
      expect(screen.getByText('content')).toBeInTheDocument();
    });
  });
  ```

  Lancer → fail (LayoutShell actuel est un stub).

- [ ] **5.11** Réécrire LayoutShell complet.

  `dashboard/src/components/v2/layout/LayoutShell.tsx` :

  ```tsx
  import type { ReactNode } from 'react';
  import type { UserRole } from '../../../types/v2/common';
  import { HeaderV2 } from './HeaderV2';
  import { BottomNavV2 } from './BottomNavV2';
  import { TrialBannerContainer } from './TrialBannerContainer';

  export interface LayoutShellProps {
    children: ReactNode;
    userRole?: UserRole;
    trialDaysLeft?: number;
    trialEndDate?: string;
  }

  export function LayoutShell({
    children,
    userRole = 'visitor',
    trialDaysLeft,
    trialEndDate,
  }: LayoutShellProps) {
    return (
      <div
        data-testid="layout-shell"
        style={{
          minHeight: '100vh',
          background: 'var(--bg)',
          color: 'var(--text)',
          paddingBottom: 72,
        }}
      >
        <TrialBannerContainer
          userRole={userRole}
          trialDaysLeft={trialDaysLeft}
          trialEndDate={trialEndDate}
        />
        <HeaderV2 userRole={userRole} trialDaysLeft={trialDaysLeft} />
        <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: 'var(--space-4)' }}>
          {children}
        </div>
        <BottomNavV2 />
      </div>
    );
  }

  export default LayoutShell;
  ```

  Relancer tout :
  ```bash
  npm run test:ci
  ```
  **Expected:** tous les tests verts (y compris AppV2.test.tsx qui utilise LayoutShell).

- [ ] **5.12** Commit.

  ```bash
  git add dashboard/src/components/v2/layout/LayoutShell.tsx dashboard/src/components/v2/layout/LayoutShell.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): wire full LayoutShell with header, bottom nav, trial banner

  Shell composable : accepte userRole + trialDaysLeft + trialEndDate. Trial
  banner conditionnel. Container max 1200px centré.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

---

## Task 6 · Composants système

9 composants dans `dashboard/src/components/v2/system/`. Chacun suit le cycle TDD : test fail → implem → pass → commit.

### 6a · StatTile

**Files**
- Create : `dashboard/src/components/v2/system/StatTile.tsx`
- Create : `dashboard/src/components/v2/system/StatTile.test.tsx`

- [ ] **6.1** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { StatTile } from './StatTile';

  describe('StatTile', () => {
    it('renders label and value', () => {
      render(<StatTile label="ROI 30J" value="+12.4%" />);
      expect(screen.getByText('ROI 30J')).toBeInTheDocument();
      expect(screen.getByText('+12.4%')).toBeInTheDocument();
    });

    it('renders delta when provided with positive tone', () => {
      render(<StatTile label="ROI" value="+12%" delta="+0.8 vs 7j" tone="positive" />);
      const delta = screen.getByText('+0.8 vs 7j');
      expect(delta).toBeInTheDocument();
      expect(delta).toHaveAttribute('data-tone', 'positive');
    });

    it('applies negative tone when specified', () => {
      render(<StatTile label="Drawdown" value="-4.2%" delta="-1.1 vs 7j" tone="negative" />);
      expect(screen.getByText('-1.1 vs 7j')).toHaveAttribute('data-tone', 'negative');
    });

    it('has no accessibility violations', async () => {
      const { container } = render(<StatTile label="ROI" value="+12%" />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
  ```

  Lancer → fail.

- [ ] **6.2** Implem.

  ```tsx
  import type { ReactNode } from 'react';

  export type StatTone = 'neutral' | 'positive' | 'negative';

  export interface StatTileProps {
    label: string;
    value: ReactNode;
    delta?: string;
    tone?: StatTone;
  }

  function toneColor(tone: StatTone): string {
    if (tone === 'positive') return 'var(--primary)';
    if (tone === 'negative') return 'var(--danger)';
    return 'var(--text-muted)';
  }

  export function StatTile({ label, value, delta, tone = 'neutral' }: StatTileProps) {
    return (
      <div
        role="group"
        aria-label={`${label}: ${typeof value === 'string' ? value : ''}`}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-1)',
          padding: 'var(--space-3)',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: 0.4 }}>
          {label}
        </span>
        <span style={{ fontSize: 24, fontWeight: 700, color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
          {value}
        </span>
        {delta && (
          <span
            data-tone={tone}
            style={{ fontSize: 12, color: toneColor(tone), fontVariantNumeric: 'tabular-nums' }}
          >
            {delta}
          </span>
        )}
      </div>
    );
  }

  export default StatTile;
  ```

  Test pass.

- [ ] **6.3** Commit.

  ```bash
  git add dashboard/src/components/v2/system/StatTile.tsx dashboard/src/components/v2/system/StatTile.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add StatTile with label/value/delta and tone variants

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6b · ProbBar

**Files**
- Create : `dashboard/src/components/v2/system/ProbBar.tsx`
- Create : `dashboard/src/components/v2/system/ProbBar.test.tsx`

- [ ] **6.4** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { ProbBar } from './ProbBar';

  describe('ProbBar', () => {
    it('renders 3 segments', () => {
      render(<ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />);
      const bar = screen.getByRole('img', { name: /psg 58%/i });
      expect(bar).toBeInTheDocument();
      expect(bar.querySelectorAll('[data-segment]')).toHaveLength(3);
    });

    it('builds a complete aria-label', () => {
      render(<ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />);
      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        expect.stringMatching(/PSG 58%.*Nul 24%.*Lens 18%/i)
      );
    });

    it('highlights the dominant segment', () => {
      render(<ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />);
      const dominant = screen.getByTestId('segment-home');
      expect(dominant).toHaveAttribute('data-dominant', 'true');
    });

    it('throws on probabilities not summing to ~1', () => {
      expect(() =>
        render(<ProbBar home={0.5} draw={0.2} away={0.1} homeLabel="A" awayLabel="B" />)
      ).toThrow(/sum/i);
    });

    it('has no accessibility violations', async () => {
      const { container } = render(
        <ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
  ```

  Lancer → fail.

- [ ] **6.5** Implem.

  ```tsx
  export interface ProbBarProps {
    home: number;
    draw: number;
    away: number;
    homeLabel: string;
    awayLabel: string;
  }

  function pct(n: number): number {
    return Math.round(n * 100);
  }

  export function ProbBar({ home, draw, away, homeLabel, awayLabel }: ProbBarProps) {
    const sum = home + draw + away;
    if (Math.abs(sum - 1) > 0.01) {
      throw new Error(`ProbBar: probabilities must sum to 1, got ${sum}`);
    }
    const max = Math.max(home, draw, away);
    const dominant = home === max ? 'home' : draw === max ? 'draw' : 'away';
    const label = `${homeLabel} ${pct(home)}%, Nul ${pct(draw)}%, ${awayLabel} ${pct(away)}%`;

    const bg = (isDom: boolean, muted: boolean): string => {
      if (isDom) return 'var(--primary)';
      return muted ? 'var(--surface-2)' : '#334155';
    };

    return (
      <div
        role="img"
        aria-label={label}
        style={{
          display: 'flex',
          width: '100%',
          height: 8,
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
          background: 'var(--surface-2)',
        }}
      >
        <span
          data-segment="home"
          data-testid="segment-home"
          data-dominant={dominant === 'home'}
          style={{ width: `${pct(home)}%`, background: bg(dominant === 'home', false) }}
        />
        <span
          data-segment="draw"
          data-testid="segment-draw"
          data-dominant={dominant === 'draw'}
          style={{ width: `${pct(draw)}%`, background: bg(dominant === 'draw', true) }}
        />
        <span
          data-segment="away"
          data-testid="segment-away"
          data-dominant={dominant === 'away'}
          style={{ width: `${pct(away)}%`, background: bg(dominant === 'away', false) }}
        />
      </div>
    );
  }

  export default ProbBar;
  ```

  Test pass.

- [ ] **6.6** Commit.

  ```bash
  git add dashboard/src/components/v2/system/ProbBar.tsx dashboard/src/components/v2/system/ProbBar.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add ProbBar with 3 segments and full aria-label

  Barre H/D/A colorée (primary sur dominant), aria-label complet lu par
  screen readers. Throw si probas ne somment pas à 1.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6c · ValueBadge

**Files**
- Create : `dashboard/src/components/v2/system/ValueBadge.tsx`
- Create : `dashboard/src/components/v2/system/ValueBadge.test.tsx`

- [ ] **6.7** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { ValueBadge } from './ValueBadge';

  describe('ValueBadge', () => {
    it('formats edge as percentage with one decimal', () => {
      render(<ValueBadge edge={0.072} />);
      expect(screen.getByText(/\+7\.2%/)).toBeInTheDocument();
    });

    it('uses aria-label with VALUE prefix', () => {
      render(<ValueBadge edge={0.072} />);
      expect(screen.getByLabelText(/value bet \+7\.2%/i)).toBeInTheDocument();
    });

    it('rounds to one decimal', () => {
      render(<ValueBadge edge={0.05678} />);
      expect(screen.getByText(/\+5\.7%/)).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(<ValueBadge edge={0.072} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **6.8** Implem.

  ```tsx
  export interface ValueBadgeProps {
    edge: number;
  }

  export function ValueBadge({ edge }: ValueBadgeProps) {
    const pct = (edge * 100).toFixed(1);
    const label = `Value bet +${pct}%`;
    return (
      <span
        aria-label={label}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--space-1)',
          padding: '2px 8px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--value)',
          color: '#111827',
          fontSize: 12,
          fontWeight: 600,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        ⚡ +{pct}%
      </span>
    );
  }

  export default ValueBadge;
  ```

- [ ] **6.9** Commit.

  ```bash
  git add dashboard/src/components/v2/system/ValueBadge.tsx dashboard/src/components/v2/system/ValueBadge.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add ValueBadge amber chip with edge percentage

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6d · OddsChip

**Files**
- Create : `dashboard/src/components/v2/system/OddsChip.tsx`
- Create : `dashboard/src/components/v2/system/OddsChip.test.tsx`

- [ ] **6.10** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { OddsChip } from './OddsChip';

  describe('OddsChip', () => {
    it('renders odds with @ prefix and 2 decimals', () => {
      render(<OddsChip value={1.92} />);
      expect(screen.getByText('@1.92')).toBeInTheDocument();
    });

    it('pads to 2 decimals', () => {
      render(<OddsChip value={2} />);
      expect(screen.getByText('@2.00')).toBeInTheDocument();
    });

    it('applies highlight style when highlighted', () => {
      render(<OddsChip value={1.92} highlight />);
      expect(screen.getByText('@1.92')).toHaveAttribute('data-highlight', 'true');
    });

    it('uses aria-label with cote prefix', () => {
      render(<OddsChip value={1.92} />);
      expect(screen.getByLabelText(/cote 1\.92/i)).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(<OddsChip value={1.92} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **6.11** Implem.

  ```tsx
  export interface OddsChipProps {
    value: number;
    highlight?: boolean;
  }

  export function OddsChip({ value, highlight = false }: OddsChipProps) {
    const formatted = value.toFixed(2);
    return (
      <span
        aria-label={`Cote ${formatted}`}
        data-highlight={highlight}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '2px 8px',
          borderRadius: 'var(--radius-sm)',
          background: highlight ? 'var(--primary-soft)' : 'var(--surface-2)',
          color: highlight ? 'var(--primary)' : 'var(--text)',
          border: `1px solid ${highlight ? 'var(--primary)' : 'var(--border)'}`,
          fontFamily: 'var(--font-mono)',
          fontSize: 14,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        @{formatted}
      </span>
    );
  }

  export default OddsChip;
  ```

- [ ] **6.12** Commit.

  ```bash
  git add dashboard/src/components/v2/system/OddsChip.tsx dashboard/src/components/v2/system/OddsChip.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add OddsChip mono tabular chip with highlight variant

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6e · BookOddsRow

**Files**
- Create : `dashboard/src/components/v2/system/BookOddsRow.tsx`
- Create : `dashboard/src/components/v2/system/BookOddsRow.test.tsx`

- [ ] **6.13** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { BookOddsRow } from './BookOddsRow';

  describe('BookOddsRow', () => {
    const books = [
      { name: 'Pinnacle', odds: 1.92 },
      { name: 'Bet365', odds: 1.95 },
      { name: 'Unibet', odds: 1.90 },
    ];

    it('renders one row per bookmaker', () => {
      render(<BookOddsRow bookmakers={books} />);
      expect(screen.getByText('Pinnacle')).toBeInTheDocument();
      expect(screen.getByText('Bet365')).toBeInTheDocument();
      expect(screen.getByText('Unibet')).toBeInTheDocument();
    });

    it('highlights the bookmaker with the best price', () => {
      render(<BookOddsRow bookmakers={books} />);
      const best = screen.getByTestId('book-row-Bet365');
      expect(best).toHaveAttribute('data-best', 'true');
    });

    it('renders a link when url is provided', () => {
      render(
        <BookOddsRow
          bookmakers={[{ name: 'Bet365', odds: 1.95, url: 'https://bet365.com' }]}
        />
      );
      const link = screen.getByRole('link', { name: /bet365/i });
      expect(link).toHaveAttribute('href', 'https://bet365.com');
      expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
    });

    it('has no accessibility violations', async () => {
      const { container } = render(<BookOddsRow bookmakers={books} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **6.14** Implem.

  ```tsx
  import type { Bookmaker } from '../../../types/v2/common';
  import { OddsChip } from './OddsChip';

  export interface BookOddsRowProps {
    bookmakers: readonly Bookmaker[];
  }

  export function BookOddsRow({ bookmakers }: BookOddsRowProps) {
    if (bookmakers.length === 0) return null;
    const bestOdds = Math.max(...bookmakers.map((b) => b.odds));
    return (
      <ul
        aria-label="Comparateur de cotes par bookmaker"
        style={{
          listStyle: 'none',
          padding: 0,
          margin: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-2)',
        }}
      >
        {bookmakers.map((b) => {
          const isBest = b.odds === bestOdds;
          const content = (
            <>
              <span style={{ flex: 1, fontWeight: isBest ? 600 : 400, color: 'var(--text)' }}>{b.name}</span>
              <OddsChip value={b.odds} highlight={isBest} />
            </>
          );
          return (
            <li
              key={b.name}
              data-testid={`book-row-${b.name}`}
              data-best={isBest}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-2) var(--space-3)',
                background: isBest ? 'var(--primary-soft)' : 'var(--surface)',
                border: `1px solid ${isBest ? 'var(--primary)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-md)',
              }}
            >
              {b.url ? (
                <a
                  href={b.url}
                  rel="noopener noreferrer"
                  target="_blank"
                  aria-label={`Voir ${b.name}, cote ${b.odds.toFixed(2)}`}
                  style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flex: 1, color: 'inherit' }}
                >
                  {content}
                </a>
              ) : (
                content
              )}
            </li>
          );
        })}
      </ul>
    );
  }

  export default BookOddsRow;
  ```

- [ ] **6.15** Commit.

  ```bash
  git add dashboard/src/components/v2/system/BookOddsRow.tsx dashboard/src/components/v2/system/BookOddsRow.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add BookOddsRow listing bookmakers with best price highlight

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6f · LockOverlay

**Files**
- Create : `dashboard/src/components/v2/system/LockOverlay.tsx`
- Create : `dashboard/src/components/v2/system/LockOverlay.test.tsx`

- [ ] **6.16** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { LockOverlay } from './LockOverlay';

  describe('LockOverlay', () => {
    it('renders the message', () => {
      render(
        <LockOverlay message="Débloque avec Premium">
          <p>hidden content</p>
        </LockOverlay>
      );
      expect(screen.getByText('Débloque avec Premium')).toBeInTheDocument();
    });

    it('keeps children visible but blurred', () => {
      render(
        <LockOverlay message="locked">
          <p data-testid="child">hidden content</p>
        </LockOverlay>
      );
      expect(screen.getByTestId('child')).toBeInTheDocument();
      expect(screen.getByTestId('lock-children')).toHaveAttribute('aria-hidden', 'true');
    });

    it('exposes a descriptive role and aria-label', () => {
      render(
        <LockOverlay message="Débloque avec Premium">
          <p>x</p>
        </LockOverlay>
      );
      expect(screen.getByRole('region', { name: /contenu verrouillé/i })).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(
        <LockOverlay message="locked">
          <p>content</p>
        </LockOverlay>
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **6.17** Implem.

  ```tsx
  import type { ReactNode } from 'react';
  import { Lock } from 'lucide-react';

  export interface LockOverlayProps {
    children: ReactNode;
    message: string;
  }

  export function LockOverlay({ children, message }: LockOverlayProps) {
    return (
      <div
        role="region"
        aria-label="Contenu verrouillé"
        style={{ position: 'relative' }}
      >
        <div
          data-testid="lock-children"
          aria-hidden="true"
          style={{ filter: 'blur(4px)', pointerEvents: 'none', userSelect: 'none' }}
        >
          {children}
        </div>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-2)',
            background: 'rgba(10, 14, 26, 0.5)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <Lock size={24} aria-hidden="true" color="var(--primary)" />
          <p style={{ margin: 0, color: 'var(--text)', fontSize: 14, fontWeight: 500, textAlign: 'center' }}>
            {message}
          </p>
        </div>
      </div>
    );
  }

  export default LockOverlay;
  ```

- [ ] **6.18** Commit.

  ```bash
  git add dashboard/src/components/v2/system/LockOverlay.tsx dashboard/src/components/v2/system/LockOverlay.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add LockOverlay with blur-4 and lock icon for gating

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6g · TrialBanner (version complète)

**Files**
- Modify : `dashboard/src/components/v2/system/TrialBanner.tsx` (stub existant depuis Task 5c)
- Create : `dashboard/src/components/v2/system/TrialBanner.test.tsx`

- [ ] **6.19** Test complet.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { MemoryRouter } from 'react-router-dom';
  import { axe } from 'jest-axe';
  import { TrialBanner } from './TrialBanner';

  describe('TrialBanner', () => {
    it('renders daysLeft and end date', () => {
      render(
        <MemoryRouter>
          <TrialBanner daysLeft={12} endDate="2026-05-21" />
        </MemoryRouter>
      );
      expect(screen.getByText(/j-12/i)).toBeInTheDocument();
      expect(screen.getByText(/2026-05-21/)).toBeInTheDocument();
    });

    it('renders without end date', () => {
      render(
        <MemoryRouter>
          <TrialBanner daysLeft={5} />
        </MemoryRouter>
      );
      expect(screen.getByText(/j-5/i)).toBeInTheDocument();
    });

    it('includes a link to activate subscription', () => {
      render(
        <MemoryRouter>
          <TrialBanner daysLeft={3} />
        </MemoryRouter>
      );
      const link = screen.getByRole('link', { name: /activer l'abonnement/i });
      expect(link).toHaveAttribute('href', '/premium');
    });

    it('is a region landmark labeled Trial', () => {
      render(
        <MemoryRouter>
          <TrialBanner daysLeft={12} />
        </MemoryRouter>
      );
      expect(screen.getByRole('region', { name: /trial/i })).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
      const { container } = render(
        <MemoryRouter>
          <TrialBanner daysLeft={12} endDate="2026-05-21" />
        </MemoryRouter>
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **6.20** Remplacer le stub par la version complète.

  `dashboard/src/components/v2/system/TrialBanner.tsx` :

  ```tsx
  import { Link } from 'react-router-dom';

  export interface TrialBannerProps {
    daysLeft: number;
    endDate?: string;
  }

  export function TrialBanner({ daysLeft, endDate }: TrialBannerProps) {
    return (
      <div
        role="region"
        aria-label="Trial premium banner"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-2) var(--space-4)',
          background: 'linear-gradient(90deg, var(--primary-soft), var(--surface))',
          color: 'var(--text)',
          borderBottom: '1px solid var(--primary)',
          fontSize: 14,
        }}
      >
        <span>
          Trial premium · J-{daysLeft} · Tout est débloqué
          {endDate ? ` jusqu'au ${endDate}` : ''}
        </span>
        <Link
          to="/premium"
          aria-label="Activer l'abonnement"
          style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'underline' }}
        >
          Activer l'abonnement
        </Link>
      </div>
    );
  }

  export default TrialBanner;
  ```

  Relancer les tests :
  ```bash
  npx vitest run src/components/v2/system/TrialBanner.test.tsx src/components/v2/layout/TrialBannerContainer.test.tsx src/components/v2/layout/LayoutShell.test.tsx
  ```
  **Expected:** tous verts.

- [ ] **6.21** Commit.

  ```bash
  git add dashboard/src/components/v2/system/TrialBanner.tsx dashboard/src/components/v2/system/TrialBanner.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): upgrade TrialBanner with gradient, sticky top, CTA link

  Remplace le stub minimal par la version stylée fintech : gradient
  émeraude, lien /premium, aria-label complet.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

### 6h · RuleChip

**Files**
- Create : `dashboard/src/components/v2/system/RuleChip.tsx`
- Create : `dashboard/src/components/v2/system/RuleChip.test.tsx`

- [ ] **6.22** Test.

  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { axe } from 'jest-axe';
  import { RuleChip } from './RuleChip';

  describe('RuleChip', () => {
    it('renders with label variant', () => {
      render(<RuleChip variant="label" text="QUAND" />);
      expect(screen.getByText('QUAND')).toHaveAttribute('data-variant', 'label');
    });

    it('renders with condition variant', () => {
      render(<RuleChip variant="condition" text="edge ≥ 8%" />);
      expect(screen.getByText('edge ≥ 8%')).toHaveAttribute('data-variant', 'condition');
    });

    it('renders with action variant', () => {
      render(<RuleChip variant="action" text="Notifier Telegram" />);
      expect(screen.getByText('Notifier Telegram')).toHaveAttribute('data-variant', 'action');
    });

    it('has no accessibility violations', async () => {
      const { container } = render(<RuleChip variant="condition" text="edge ≥ 8%" />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **6.23** Implem.

  ```tsx
  export type RuleChipVariant = 'label' | 'condition' | 'action';

  export interface RuleChipProps {
    variant: RuleChipVariant;
    text: string;
  }

  function variantStyle(variant: RuleChipVariant): { background: string; color: string; border: string } {
    if (variant === 'label') {
      return {
        background: 'var(--surface-2)',
        color: 'var(--text-faint)',
        border: '1px solid var(--border)',
      };
    }
    if (variant === 'condition') {
      return {
        background: 'var(--surface)',
        color: 'var(--text)',
        border: '1px solid var(--info)',
      };
    }
    return {
      background: 'var(--primary-soft)',
      color: 'var(--primary)',
      border: '1px solid var(--primary)',
    };
  }

  export function RuleChip({ variant, text }: RuleChipProps) {
    const s = variantStyle(variant);
    return (
      <span
        data-variant={variant}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '2px 10px',
          borderRadius: 'var(--radius-lg)',
          fontSize: 12,
          fontWeight: variant === 'label' ? 700 : 500,
          letterSpacing: variant === 'label' ? 0.5 : 0,
          textTransform: variant === 'label' ? 'uppercase' : 'none',
          background: s.background,
          color: s.color,
          border: s.border,
        }}
      >
        {text}
      </span>
    );
  }

  export default RuleChip;
  ```

- [ ] **6.24** Commit.

  ```bash
  git add dashboard/src/components/v2/system/RuleChip.tsx dashboard/src/components/v2/system/RuleChip.test.tsx
  git commit -m "$(cat <<'EOF'
  feat(v2/foundation): add RuleChip composable with label/condition/action variants

  Chip utilisé par le rules builder (lot 5). 3 variants stylés fintech.

  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  EOF
  )"
  ```

---

## Task 7 · Vérification finale du lot

- [ ] **7.1** Lancer toute la suite.

  ```bash
  cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
  npm run test:ci
  ```
  **Expected:** 100% verts (legacy + tous les nouveaux tests V2).

- [ ] **7.2** Vérifier le build.

  ```bash
  npm run build
  ```
  **Expected:** build réussit sans warning TypeScript.

- [ ] **7.3** Vérifier le lint.

  ```bash
  npm run lint
  ```
  **Expected:** 0 erreur, 0 warning sur les fichiers `v2/`.

- [ ] **7.4** Vérification visuelle dev avec flag ON.

  Dans `dashboard/.env.local`, s'assurer que `VITE_FRONTEND_V2=true`.

  ```bash
  npm run dev
  ```

  Ouvrir `http://localhost:5173/` → **Expected:** voir le shell V2 (header ProbaLab sticky, bottom nav mobile, "HomeV2 WIP" au centre).

  Tester routes :
  - `/matchs` → "MatchesV2 WIP"
  - `/matchs/abc-123` → "MatchDetailV2 WIP" + fixture: abc-123
  - `/premium` → "PremiumV2 WIP"
  - `/compte` → "AccountV2 WIP"
  - `/login`, `/register` → stubs respectifs

- [ ] **7.5** Vérification visuelle dev avec flag OFF.

  Éditer `.env.local` : `VITE_FRONTEND_V2=false`.

  Relancer `npm run dev` → **Expected:** l'ancienne app s'affiche, aucune trace du shell V2.

  Remettre `VITE_FRONTEND_V2=true` avant de continuer.

- [ ] **7.6** Vérifier qu'aucun fichier V2 ne dépasse 300 lignes.

  ```bash
  cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
  find src -path '*v2*' -name '*.ts*' -exec wc -l {} + | awk '$1 > 300 {print "TROP LONG:", $0}'
  ```
  **Expected:** aucune ligne imprimée.

- [ ] **7.7** Vérifier absence de `any` et de `// TODO` dans le code V2.

  ```bash
  grep -rn --include='*.ts' --include='*.tsx' -E '\bany\b|// *TODO' "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard/src" | grep -E 'v2/' || echo "CLEAN"
  ```
  **Expected:** `CLEAN`.

- [ ] **7.8** Push de la branche.

  ```bash
  cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
  git push -u origin feat/frontend-refonte-v1
  ```
  **Expected:** push réussi, branche trackée.

---

## Critères d'acceptation du Lot 1

- [ ] `VITE_FRONTEND_V2=true` en dev → shell V2 complet visible avec 7 routes stubs fonctionnelles.
- [ ] `VITE_FRONTEND_V2=false` en dev → ancien frontend servi sans aucune régression.
- [ ] 100% des tests Vitest verts (`npm run test:ci`).
- [ ] Build production réussi (`npm run build`) sans warning TS.
- [ ] Lint propre (`npm run lint`) sur tout le code `v2/`.
- [ ] 9 composants système présents dans `dashboard/src/components/v2/system/` : StatTile, ProbBar, ValueBadge, OddsChip, BookOddsRow, LockOverlay, TrialBanner, RuleChip — chacun avec son fichier `.test.tsx` et 0 violation jest-axe.
- [ ] Layout shell wraps toutes les pages V2 (header sticky, bottom nav, trial banner conditionnel).
- [ ] Feature flag helper testé (`isFrontendV2Enabled`) lit `VITE_FRONTEND_V2`.
- [ ] Tokens CSS fintech (dark + light) importés depuis `main.tsx`.
- [ ] Types partagés V2 (`FixtureId = string`, `UserRole`, `Sport`, `League`, etc.) dans `src/types/v2/common.ts`.
- [ ] Aucun fichier V2 > 300 lignes.
- [ ] Aucun `any` ni `// TODO` dans le code V2.
- [ ] Tous les commits ont le format `feat(v2/foundation): ...` ou `test(v2/foundation): ...` avec Co-Authored-By Claude Sonnet 4.6.

Quand tous ces points sont cochés, le lot est mergeable sur `main`. Lot suivant : [lot-2-backend.md](./2026-04-21-frontend-refonte-v1-lot-2-backend.md).
