# Plan — Lot 6 : Migration + Cutover frontend V2

**Date** : 2026-04-21
**Auteur** : Claude (agent TDD)
**Spec source** : `docs/superpowers/specs/2026-04-21-frontend-refonte-v1-design.md` (sections 15, 16, 17)
**Master plan** : `docs/superpowers/plans/2026-04-21-frontend-refonte-v1-MASTER.md`
**Prérequis** : Lots 1 à 5 mergés sur `main`, `VITE_FRONTEND_V2=true` en staging, build vert.
**Branche cible** : `feat/v2-lot-6-migration`
**Stack** : React 19 + Vite 7 + TypeScript strict + react-router v6 + Playwright 1.45+ + Vitest + Testing Library.

---

## Objectifs

1. Rediriger (301/`<Navigate>`) toutes les anciennes routes vers leurs équivalents V2 en conservant les query params.
2. Supprimer proprement les pages legacy devenues obsolètes (Dashboard, ParisDuSoir, Watchlist, HeroShowcase, HomePage, MatchDetail).
3. Garder Admin et Performance intacts (hors scope V1).
4. Installer et configurer Playwright + 3 specs E2E critiques (visitor→trial, browse→premium CTA, premium→rule alert).
5. Ajouter redirects HTTP 301 côté FastAPI pour les bookmarks/liens externes.
6. Documenter cutover + rollback (`CHANGELOG-v2-frontend.md`).
7. Activer le flag `VITE_FRONTEND_V2=true` côté Railway + CI GitHub Actions.
8. Livrer une checklist smoke tests post-cutover.

---

## Cutover — procédure en 2 temps (anti-régression)

| Phase | Quand | Action | Réversibilité |
|---|---|---|---|
| **T0** | Merge de ce Lot 6 | Flag activé en prod, **legacy code toujours présent** (routes legacy désactivées via Navigate mais composants sur disque) | Flipper `VITE_FRONTEND_V2=false` → rollback complet en 1 redeploy |
| **T0 + 7 jours** | Après fenêtre d'observation sans incident | PR de cleanup `chore(cleanup): remove legacy pages` qui supprime fichiers legacy | git revert si besoin |

Le plan couvre **les deux PRs**. La PR 1 (tasks 1–9) active la V2 sans supprimer. La PR 2 (tasks 10–11) est prête mais ne s'exécute qu'après validation manuelle utilisateur (checkpoint explicite).

---

## Table des redirects (source de vérité unique)

| Ancienne route | Nouvelle route | Query params | Type |
|---|---|---|---|
| `/paris-du-soir` | `/matchs?signal=value` | préservés + signal ajouté | Client Navigate |
| `/paris-du-soir/football` | `/matchs?sport=foot&signal=value` | préservés + sport+signal ajoutés | Client Navigate |
| `/football` | `/matchs?sport=foot` | préservés | Client Navigate |
| `/football/match/:id` | `/matchs/:id` | préservés | Client Navigate |
| `/nhl` | `/matchs?sport=nhl` | préservés | Client Navigate |
| `/nhl/match/:id` | `/matchs/:id` | préservés | Client Navigate |
| `/watchlist` | `/compte/bankroll` | préservés | Client Navigate |
| `/hero-showcase` | `/` | ignorés | Client Navigate |

Les mêmes redirects sont doublés côté FastAPI (`api/main.py`) en `RedirectResponse(status_code=301)` pour les user-agents non-JS (bots, curl, partages Slack/Discord).

---

## Tasks

### Task 1 — Scaffold branche + vérif prérequis

**Files** : aucun (lecture seule)

**Steps** :
```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git checkout main && git pull --ff-only
git checkout -b feat/v2-lot-6-migration

# Vérifier flag V2 opérationnel
grep -r "VITE_FRONTEND_V2" dashboard/src/ | head -5
# Doit montrer AppV2 déjà monté dans main.tsx ou App.tsx

cd dashboard
npm run test -- --run
npm run build
# Les deux doivent être verts avant de commencer
```

**Commit** : pas de commit à cette task.

---

### Task 2 — [TDD] Redirects 301 côté React Router (RED)

**Files** :
- `dashboard/src/__tests__/migration/redirects.test.tsx` (nouveau)

**Steps** :

1. Créer le test AVANT toute implémentation. Le test doit échouer parce que les routes legacy renvoient encore leurs anciens composants (ou 404).

```typescript
// dashboard/src/__tests__/migration/redirects.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AppV2 from '../../AppV2';

const REDIRECTS: Array<[string, string]> = [
  ['/paris-du-soir', '/matchs?signal=value'],
  ['/paris-du-soir/football', '/matchs?sport=foot&signal=value'],
  ['/football', '/matchs?sport=foot'],
  ['/football/match/12345', '/matchs/12345'],
  ['/nhl', '/matchs?sport=nhl'],
  ['/nhl/match/98765', '/matchs/98765'],
  ['/watchlist', '/compte/bankroll'],
  ['/hero-showcase', '/'],
];

describe('Legacy route redirects', () => {
  it.each(REDIRECTS)('redirects %s -> %s', async (from, to) => {
    render(
      <MemoryRouter initialEntries={[from]}>
        <AppV2 />
      </MemoryRouter>
    );
    // Testid présent uniquement sur la page cible V2
    const landmark = await screen.findByTestId('v2-route-landmark', {}, { timeout: 2000 });
    expect(landmark.dataset.path).toBe(to);
  });

  it('preserves query params on /football?team=PSG', async () => {
    render(
      <MemoryRouter initialEntries={['/football?team=PSG']}>
        <AppV2 />
      </MemoryRouter>
    );
    const landmark = await screen.findByTestId('v2-route-landmark');
    expect(landmark.dataset.path).toContain('sport=foot');
    expect(landmark.dataset.path).toContain('team=PSG');
  });
});
```

2. Lancer `npm run test -- redirects.test.tsx` → doit échouer (RED).

**Commit** :
```bash
git add dashboard/src/__tests__/migration/redirects.test.tsx
git commit -m "$(cat <<'EOF'
test(v2/migration): add failing redirect tests for legacy routes

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3 — [TDD] Redirects 301 côté React Router (GREEN)

**Files** :
- `dashboard/src/components/migration/LegacyRedirect.tsx` (nouveau)
- `dashboard/src/components/migration/RouteLandmark.tsx` (nouveau — helper test)
- `dashboard/src/AppV2.tsx` (modifié)

**Steps** :

1. Helper test landmark — toute route V2 (déjà existantes des lots 2-5) est wrappée par ce composant côté test pour exposer le path courant :

```typescript
// dashboard/src/components/migration/RouteLandmark.tsx
import { useLocation } from 'react-router-dom';
import { useMemo } from 'react';

export function RouteLandmark({ children }: { children: React.ReactNode }) {
  const loc = useLocation();
  const path = useMemo(() => loc.pathname + loc.search, [loc]);
  return (
    <>
      <span data-testid="v2-route-landmark" data-path={path} hidden />
      {children}
    </>
  );
}
```

2. Composant de redirect préservant les query params :

```typescript
// dashboard/src/components/migration/LegacyRedirect.tsx
import { Navigate, useLocation, useParams } from 'react-router-dom';

type Props = {
  /** Template de destination. `:id` est remplacé par params.id. */
  to: string;
  /** Query params à injecter ou merger. */
  inject?: Record<string, string>;
};

export function LegacyRedirect({ to, inject = {} }: Props) {
  const location = useLocation();
  const params = useParams();

  // Substitution des params dynamiques
  let dest = to;
  for (const [k, v] of Object.entries(params)) {
    if (v) dest = dest.replace(`:${k}`, encodeURIComponent(v));
  }

  // Merge query strings : existants préservés, injectés ajoutés s'ils manquent
  const existing = new URLSearchParams(location.search);
  for (const [k, v] of Object.entries(inject)) {
    if (!existing.has(k)) existing.set(k, v);
  }

  const qs = existing.toString();
  const finalDest = qs ? `${dest}${dest.includes('?') ? '&' : '?'}${qs}` : dest;

  return <Navigate to={finalDest} replace />;
}
```

3. Modifier `AppV2.tsx` — wrapper chaque `<Route element>` avec `<RouteLandmark>` et ajouter les routes legacy :

```tsx
// dashboard/src/AppV2.tsx (extrait pertinent)
import { LegacyRedirect } from './components/migration/LegacyRedirect';
import { RouteLandmark } from './components/migration/RouteLandmark';

// ... dans <Routes>
<Route path="/" element={<RouteLandmark><HomeV2 /></RouteLandmark>} />
<Route path="/matchs" element={<RouteLandmark><MatchesV2 /></RouteLandmark>} />
<Route path="/matchs/:id" element={<RouteLandmark><MatchDetailV2 /></RouteLandmark>} />
<Route path="/premium" element={<RouteLandmark><PremiumV2 /></RouteLandmark>} />
<Route path="/compte/*" element={<RouteLandmark><AccountV2 /></RouteLandmark>} />

{/* Legacy redirects */}
<Route path="/paris-du-soir" element={<LegacyRedirect to="/matchs" inject={{ signal: 'value' }} />} />
<Route path="/paris-du-soir/football" element={<LegacyRedirect to="/matchs" inject={{ sport: 'foot', signal: 'value' }} />} />
<Route path="/football" element={<LegacyRedirect to="/matchs" inject={{ sport: 'foot' }} />} />
<Route path="/football/match/:id" element={<LegacyRedirect to="/matchs/:id" />} />
<Route path="/nhl" element={<LegacyRedirect to="/matchs" inject={{ sport: 'nhl' }} />} />
<Route path="/nhl/match/:id" element={<LegacyRedirect to="/matchs/:id" />} />
<Route path="/watchlist" element={<LegacyRedirect to="/compte/bankroll" />} />
<Route path="/hero-showcase" element={<LegacyRedirect to="/" />} />
```

4. `npm run test -- redirects.test.tsx` → doit passer (GREEN).
5. `npm run build` → vert.

**Commit** :
```bash
git add dashboard/src/components/migration/ dashboard/src/AppV2.tsx
git commit -m "$(cat <<'EOF'
feat(v2/migration): redirect legacy routes to V2 equivalents

- LegacyRedirect preserves query params and substitutes :id
- RouteLandmark exposes current path for tests
- 8 redirects wired in AppV2 (paris-du-soir, football, nhl, watchlist, hero-showcase)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4 — [TDD] Redirects 301 backend FastAPI (RED → GREEN)

**Files** :
- `api/tests/test_legacy_redirects.py` (nouveau)
- `api/main.py` (modifié — ajouter middleware)
- `api/middleware/legacy_redirects.py` (nouveau)

**Steps** :

1. Test RED :

```python
# api/tests/test_legacy_redirects.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app, follow_redirects=False)

REDIRECTS = [
    ("/paris-du-soir", "/matchs?signal=value"),
    ("/paris-du-soir/football", "/matchs?sport=foot&signal=value"),
    ("/football", "/matchs?sport=foot"),
    ("/football/match/12345", "/matchs/12345"),
    ("/nhl", "/matchs?sport=nhl"),
    ("/nhl/match/98765", "/matchs/98765"),
    ("/watchlist", "/compte/bankroll"),
    ("/hero-showcase", "/"),
]

@pytest.mark.parametrize("source,target", REDIRECTS)
def test_legacy_redirect_returns_301(source: str, target: str) -> None:
    resp = client.get(source)
    assert resp.status_code == 301, f"{source} should return 301"
    assert resp.headers["location"] == target

def test_query_params_preserved() -> None:
    resp = client.get("/football?team=PSG&date=2026-04-21")
    assert resp.status_code == 301
    loc = resp.headers["location"]
    assert loc.startswith("/matchs?")
    assert "sport=foot" in loc
    assert "team=PSG" in loc
    assert "date=2026-04-21" in loc

def test_non_legacy_route_not_redirected() -> None:
    resp = client.get("/matchs")
    assert resp.status_code != 301
```

2. Lancer `pytest api/tests/test_legacy_redirects.py` → doit échouer (RED).

3. Middleware GREEN :

```python
# api/middleware/legacy_redirects.py
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

# Map statique : source exact -> (target_path, injected_query)
_STATIC: dict[str, tuple[str, dict[str, str]]] = {
    "/paris-du-soir": ("/matchs", {"signal": "value"}),
    "/paris-du-soir/football": ("/matchs", {"sport": "foot", "signal": "value"}),
    "/football": ("/matchs", {"sport": "foot"}),
    "/nhl": ("/matchs", {"sport": "nhl"}),
    "/watchlist": ("/compte/bankroll", {}),
    "/hero-showcase": ("/", {}),
}

# Patterns dynamiques : prefix -> target_prefix (tout suffixe propagé)
_DYNAMIC: list[tuple[str, str]] = [
    ("/football/match/", "/matchs/"),
    ("/nhl/match/", "/matchs/"),
]


def _build_location(target: str, existing_qs: str, inject: dict[str, str]) -> str:
    existing = dict(parse_qsl(existing_qs, keep_blank_values=True))
    for k, v in inject.items():
        existing.setdefault(k, v)
    qs = urlencode(existing)
    return f"{target}?{qs}" if qs else target


class LegacyRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        qs = request.url.query

        if path in _STATIC:
            target, inject = _STATIC[path]
            return RedirectResponse(_build_location(target, qs, inject), status_code=301)

        for prefix, target_prefix in _DYNAMIC:
            if path.startswith(prefix):
                suffix = path[len(prefix):]
                target = f"{target_prefix}{suffix}"
                return RedirectResponse(
                    _build_location(target, qs, {}), status_code=301
                )

        return await call_next(request)
```

4. Brancher dans `api/main.py` :

```python
# api/main.py (ajout)
from api.middleware.legacy_redirects import LegacyRedirectMiddleware

# ... après création app
app.add_middleware(LegacyRedirectMiddleware)
```

5. `pytest api/tests/test_legacy_redirects.py -v` → tout passe.

**Commit** :
```bash
git add api/middleware/legacy_redirects.py api/tests/test_legacy_redirects.py api/main.py
git commit -m "$(cat <<'EOF'
feat(v2/migration): FastAPI middleware for legacy route 301 redirects

Mirrors client-side LegacyRedirect rules so crawlers, curl,
and social unfurlers follow the new URLs.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5 — Ajout `data-testid` ciblés dans composants V2 (lots 3-5)

**Files** (micro-edits, une ligne chacune) :
- `dashboard/src/pages/v2/HomeV2.tsx` — ajouter `data-testid="home-landing"` sur root, `data-testid="trial-banner"` sur la bannière trial, `data-testid="cta-register-trial"` sur bouton essai gratuit.
- `dashboard/src/pages/v2/MatchesV2.tsx` — `data-testid="matches-list"` sur liste, `data-testid="match-card"` sur chaque carte.
- `dashboard/src/pages/v2/MatchDetailV2.tsx` — `data-testid="match-detail"` sur root, `data-testid="premium-cta"` sur le CTA flouté, `data-testid="premium-lock-overlay"` sur l'overlay floute.
- `dashboard/src/pages/v2/PremiumV2.tsx` — `data-testid="premium-pricing"`, `data-testid="track-record-live"`.
- `dashboard/src/pages/v2/account/NotificationsTab.tsx` — `data-testid="notifications-tab"`, `data-testid="new-rule-button"`, `data-testid="rule-form"`, `data-testid="rule-name-input"`, `data-testid="rule-edge-input"`, `data-testid="rule-channel-telegram"`, `data-testid="rule-channel-push"`, `data-testid="rule-save"`, `data-testid="rule-list-item"`.
- `dashboard/src/pages/v2/RegisterV2.tsx` (ou modal) — `data-testid="register-form"`, `data-testid="register-email"`, `data-testid="register-password"`, `data-testid="register-pseudo"`, `data-testid="register-submit"`.

**Steps** :
1. Pour chaque fichier, ouvrir, ajouter l'attribut, sauver.
2. `npm run test` pour vérifier aucun test unitaire existant ne casse.
3. `npm run build` vert.

**Commit** :
```bash
git add dashboard/src/pages/v2/
git commit -m "$(cat <<'EOF'
chore(v2): add data-testid hooks for Playwright selectors

Stable selectors covering registration flow, match list,
match detail, premium CTA and notification rule form.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6 — Installation Playwright + config

**Files** :
- `dashboard/package.json` (modifié — deps + scripts)
- `dashboard/playwright.config.ts` (nouveau)
- `dashboard/e2e/fixtures/auth.ts` (nouveau)
- `dashboard/.gitignore` (modifié — `playwright-report`, `test-results`)

**Steps** :

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/dashboard"
npm install -D @playwright/test@^1.45.0
npx playwright install --with-deps chromium
```

Config :

```typescript
// dashboard/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

const FRONTEND_URL = process.env.E2E_FRONTEND_URL ?? 'http://localhost:5173';
const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // sessions partagées sur backend local
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: FRONTEND_URL,
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    extraHTTPHeaders: {
      'x-e2e-backend': BACKEND_URL,
    },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: process.env.CI
    ? [
        {
          command: 'npm run preview -- --port 5173',
          port: 5173,
          reuseExistingServer: false,
          timeout: 120_000,
          env: { VITE_FRONTEND_V2: 'true' },
        },
      ]
    : undefined, // dev local : services lancés à la main
});
```

Fixture auth :

```typescript
// dashboard/e2e/fixtures/auth.ts
import { test as base, expect, Page, APIRequestContext } from '@playwright/test';

type AuthFixtures = {
  premiumPage: Page;
};

export const test = base.extend<AuthFixtures>({
  premiumPage: async ({ browser, request }, use) => {
    const backend = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000';
    // Appel API direct pour récupérer le cookie de session premium
    const email = process.env.E2E_PREMIUM_EMAIL ?? 'e2e-premium@probalab.test';
    const password = process.env.E2E_PREMIUM_PASSWORD ?? 'e2e-premium-pass';
    const resp = await request.post(`${backend}/auth/login`, {
      data: { email, password },
    });
    expect(resp.status(), 'login premium user').toBe(200);
    const cookies = resp.headersArray().filter((h) => h.name.toLowerCase() === 'set-cookie');

    const ctx = await browser.newContext();
    for (const c of cookies) {
      const [pair] = c.value.split(';');
      const [name, value] = pair.split('=');
      await ctx.addCookies([{
        name, value,
        url: process.env.E2E_FRONTEND_URL ?? 'http://localhost:5173',
      }]);
    }
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },
});

export { expect } from '@playwright/test';
```

Scripts `package.json` :

```json
{
  "scripts": {
    "e2e": "playwright test",
    "e2e:ui": "playwright test --ui",
    "e2e:headed": "playwright test --headed"
  }
}
```

`.gitignore` :
```
playwright-report/
test-results/
```

**Commit** :
```bash
git add dashboard/package.json dashboard/package-lock.json dashboard/playwright.config.ts dashboard/e2e/ dashboard/.gitignore
git commit -m "$(cat <<'EOF'
chore(v2/e2e): install Playwright and base config

Config targets dev server by default, preview in CI with
VITE_FRONTEND_V2=true. Premium auth fixture logs in via API
and injects session cookies.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7 — E2E Spec 1 : visitor-to-trial

**Files** :
- `dashboard/e2e/visitor-to-trial.spec.ts` (nouveau)

```typescript
// dashboard/e2e/visitor-to-trial.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Visitor to trial (< 60s)', () => {
  test('registers and sees trial banner + Safe of the day', async ({ page }) => {
    const uniqueEmail = `e2e-trial+${Date.now()}@probalab.test`;

    await page.goto('/');
    await expect(page.getByTestId('home-landing')).toBeVisible();
    // Landing visible + preview flouté pour visiteur
    await expect(page.getByTestId('premium-lock-overlay').first()).toBeVisible();

    // CTA Essai gratuit
    await page.getByTestId('cta-register-trial').click();

    // Formulaire
    await expect(page.getByTestId('register-form')).toBeVisible();
    await page.getByTestId('register-email').fill(uniqueEmail);
    await page.getByTestId('register-password').fill('E2eTrial!2026');
    await page.getByTestId('register-pseudo').fill(`trial${Date.now()}`);
    await page.getByTestId('register-submit').click();

    // Redirigé sur / connecté
    await page.waitForURL('/', { timeout: 15_000 });
    await expect(page.getByTestId('trial-banner')).toBeVisible();

    // Safe du jour présent
    const safe = page.locator('[data-testid="safe-ticket-today"]');
    await expect(safe).toBeVisible();

    // Badge premium NOT visible (trial != premium paid)
    await expect(page.getByTestId('premium-badge')).toHaveCount(0);
  });
});
```

**Commit** :
```bash
git add dashboard/e2e/visitor-to-trial.spec.ts
git commit -m "$(cat <<'EOF'
test(v2/e2e): visitor-to-trial registration flow

Covers: landing visible → CTA trial → register form →
home with trial banner + Safe du jour in under 60s.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8 — E2E Spec 2 : browse-to-premium-cta

**Files** :
- `dashboard/e2e/browse-to-premium-cta.spec.ts` (nouveau)

```typescript
// dashboard/e2e/browse-to-premium-cta.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Browse to premium CTA', () => {
  test('visitor hits premium page with pricing + live track record', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('home-landing')).toBeVisible();

    // Navigation matchs
    await page.getByRole('link', { name: /matchs/i }).first().click();
    await page.waitForURL(/\/matchs/);
    await expect(page.getByTestId('matches-list')).toBeVisible();

    // Premier match disponible
    const firstCard = page.getByTestId('match-card').first();
    await expect(firstCard).toBeVisible();
    await firstCard.click();

    // Fiche match avec contenu premium flouté
    await expect(page.getByTestId('match-detail')).toBeVisible();
    await expect(page.getByTestId('premium-lock-overlay')).toBeVisible();

    // CTA premium
    const cta = page.getByTestId('premium-cta').first();
    await expect(cta).toBeVisible();
    await cta.click();

    // Page premium
    await page.waitForURL('/premium');
    await expect(page.getByTestId('premium-pricing')).toBeVisible();
    await expect(page.getByTestId('track-record-live')).toBeVisible();
  });
});
```

**Commit** :
```bash
git add dashboard/e2e/browse-to-premium-cta.spec.ts
git commit -m "$(cat <<'EOF'
test(v2/e2e): visitor browse flow to premium CTA

Covers: / → /matchs → match card → blurred detail →
/premium with pricing and live track record.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9 — E2E Spec 3 : premium-rule-alert

**Files** :
- `dashboard/e2e/premium-rule-alert.spec.ts` (nouveau)

```typescript
// dashboard/e2e/premium-rule-alert.spec.ts
import { test, expect } from './fixtures/auth';

test.describe('Premium user — notification rule', () => {
  test('creates an edge-based rule with Telegram + Push channels', async ({ premiumPage: page }) => {
    await page.goto('/compte/notifications');
    await expect(page.getByTestId('notifications-tab')).toBeVisible();

    const ruleName = `E2E Edge Rule ${Date.now()}`;

    await page.getByTestId('new-rule-button').click();
    await expect(page.getByTestId('rule-form')).toBeVisible();

    await page.getByTestId('rule-name-input').fill(ruleName);
    await page.getByTestId('rule-edge-input').fill('8');
    await page.getByTestId('rule-channel-telegram').check();
    await page.getByTestId('rule-channel-push').check();
    await page.getByTestId('rule-save').click();

    // La règle apparaît dans la liste
    const item = page.getByTestId('rule-list-item').filter({ hasText: ruleName });
    await expect(item).toBeVisible();

    // Toggle on par défaut
    const toggle = item.getByRole('switch');
    await expect(toggle).toBeChecked();

    // Reload -> persistance
    await page.reload();
    await expect(page.getByTestId('rule-list-item').filter({ hasText: ruleName })).toBeVisible();
  });
});
```

**Commit** :
```bash
git add dashboard/e2e/premium-rule-alert.spec.ts
git commit -m "$(cat <<'EOF'
test(v2/e2e): premium user creates notification rule

Covers: API login premium → /compte/notifications → new rule
(edge >= 8%, Telegram + Push) → persists across reload.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10 — Cleanup `App.tsx` (shim) + conservation Admin / Performance / Login / CGU / Confidentialité

**Files** :
- `dashboard/src/App.tsx` (modifié)
- `dashboard/src/main.tsx` (vérifié — doit déjà mounter AppV2 si flag true)

**Steps** :

1. `App.tsx` devient un shim minimal. Si le flag est off, fallback sur les pages légitimes restantes (Login, Admin, Performance, CGU, Confidentialité) via router minimal.

```tsx
// dashboard/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppV2 from './AppV2';
import Login from './pages/Login';
import Admin from './pages/Admin';
import Performance from './pages/Performance';
import CGU from './pages/CGU';
import Confidentialite from './pages/Confidentialite';

const V2_ENABLED = import.meta.env.VITE_FRONTEND_V2 === 'true';

export default function App() {
  if (V2_ENABLED) return <AppV2 />;

  // Mode legacy minimal : uniquement pages admin/légales
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/admin/*" element={<Admin />} />
        <Route path="/performance" element={<Performance />} />
        <Route path="/cgu" element={<CGU />} />
        <Route path="/confidentialite" element={<Confidentialite />} />
        <Route path="*" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}
```

2. Ajouter Admin/Performance routes dans AppV2 également (puisque V2 doit les servir aussi) :

```tsx
// dashboard/src/AppV2.tsx (extrait)
<Route path="/admin/*" element={<Admin />} />
<Route path="/performance" element={<Performance />} />
<Route path="/cgu" element={<CGU />} />
<Route path="/confidentialite" element={<Confidentialite />} />
<Route path="/login" element={<Login />} />
```

3. Tests et build :
```bash
cd dashboard
npm run test -- --run
npm run build
```

**Commit** :
```bash
git add dashboard/src/App.tsx dashboard/src/AppV2.tsx
git commit -m "$(cat <<'EOF'
refactor(v2/migration): App.tsx becomes V2 shim, keeps Admin/Performance

When VITE_FRONTEND_V2=true, App mounts AppV2 which serves every
route including Admin, Performance, Login, CGU, Confidentialite.
When false, legacy minimal router still serves those pages.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11 — CHANGELOG + smoke checklist + activation flag CI/Railway

**Files** :
- `docs/CHANGELOG-v2-frontend.md` (nouveau)
- `.github/workflows/ci.yml` (modifié — injection `VITE_FRONTEND_V2=true` dans le build + job E2E)
- Railway : réglage manuel documenté (pas de commit)

**Steps** :

1. Créer `docs/CHANGELOG-v2-frontend.md` :

```markdown
# CHANGELOG — Frontend V2 cutover

## 2026-04-21 — Cutover V2 activé (phase 1/2)

### Breaking changes

- Routes legacy supprimées (redirects 301 actifs) :
  - `/paris-du-soir` -> `/matchs?signal=value`
  - `/paris-du-soir/football` -> `/matchs?sport=foot&signal=value`
  - `/football` -> `/matchs?sport=foot`
  - `/football/match/:id` -> `/matchs/:id`
  - `/nhl` -> `/matchs?sport=nhl`
  - `/nhl/match/:id` -> `/matchs/:id`
  - `/watchlist` -> `/compte/bankroll`
  - `/hero-showcase` -> `/`
- Les query params existants sont préservés; `signal`, `sport` ne sont injectés que s'ils manquent.
- Redirects doublés côté FastAPI (HTTP 301) pour les bookmarks et crawlers.

### Conservé (hors scope V1)

- `/admin/*` — inchangé.
- `/performance` — inchangé (admin only).
- `/login`, `/cgu`, `/confidentialite` — inchangés.

### Procédure rollback d'urgence

1. Railway -> service `frontend` -> variables -> passer `VITE_FRONTEND_V2` à `false`.
2. Redeploy (bouton "Deploy latest").
3. Le shim `App.tsx` bascule vers le router legacy minimal.
4. Pas de git revert nécessaire tant que le cleanup fichiers (phase 2) n'a pas été appliqué.

Délai de rollback mesuré : < 3 minutes (redeploy Railway).

### Phase 2 (prévue T0 + 7 jours si zéro incident)

Suppression des fichiers legacy. Après cette phase, un rollback nécessite un `git revert` du commit de suppression.

Fichiers qui seront supprimés :
- `dashboard/src/pages/Dashboard.tsx`
- `dashboard/src/pages/ParisDuSoir.tsx`
- `dashboard/src/pages/WatchlistPage.tsx`
- `dashboard/src/pages/HeroShowcase.tsx`
- `dashboard/src/pages/HomePage.tsx`
- `dashboard/src/pages/MatchDetail.tsx`
- Composants exclusifs (scan via `grep -r` d'imports).

### Smoke tests post-cutover (manuel, à faire dans les 15 minutes suivant le deploy)

- [ ] `/` charge sans erreur console (DevTools ouvert)
- [ ] Login utilisateur existant fonctionne, trial banner visible si applicable
- [ ] `/matchs` liste au moins 1 match
- [ ] Click match -> fiche détaillée chargée
- [ ] `/premium` affiche KPIs track record
- [ ] `/compte` tabs cliquables (profil, bankroll, notifications, abonnement)
- [ ] Redirects 301 effectifs : `curl -I https://app.probalab.com/paris-du-soir` renvoie `301` + bon `Location`
- [ ] `/admin` accessible pour user admin
- [ ] `/performance` accessible pour user admin
- [ ] Lighthouse mobile score >= 85 sur `/`

### Activation CI

Le workflow `.github/workflows/ci.yml` injecte `VITE_FRONTEND_V2=true` au build. Job `e2e` dédié exécute Playwright contre `npm run preview`.
```

2. Modifier `.github/workflows/ci.yml` (ajouter env sur le build + job e2e) :

```yaml
# .github/workflows/ci.yml — ajouts
jobs:
  frontend-build:
    # ... existant
    env:
      VITE_FRONTEND_V2: 'true'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
        working-directory: dashboard
      - run: npm run build
        working-directory: dashboard
        env:
          VITE_FRONTEND_V2: 'true'

  e2e:
    needs: [frontend-build, backend-tests]
    runs-on: ubuntu-latest
    env:
      VITE_FRONTEND_V2: 'true'
      E2E_FRONTEND_URL: http://localhost:5173
      E2E_BACKEND_URL: http://localhost:8000
      E2E_PREMIUM_EMAIL: ${{ secrets.E2E_PREMIUM_EMAIL }}
      E2E_PREMIUM_PASSWORD: ${{ secrets.E2E_PREMIUM_PASSWORD }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Install backend
        run: pip install -r requirements.txt
      - name: Start backend
        run: uvicorn api.main:app --port 8000 &
      - name: Wait backend
        run: npx wait-on http://localhost:8000/health
      - name: Install frontend
        run: npm ci
        working-directory: dashboard
      - name: Install Playwright
        run: npx playwright install --with-deps chromium
        working-directory: dashboard
      - name: Build
        run: npm run build
        working-directory: dashboard
      - name: Run E2E
        run: npm run e2e
        working-directory: dashboard
      - name: Upload report
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: dashboard/playwright-report
```

3. Railway (manuel, non commité) :
   - Service `frontend` -> Variables -> ajouter `VITE_FRONTEND_V2=true`.
   - Redeploy.
   - Capture d'écran de la variable dans le CHANGELOG si besoin (optionnel).

**Commit** :
```bash
git add docs/CHANGELOG-v2-frontend.md .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
docs(v2): changelog + smoke checklist + CI enables V2 build

- Activates VITE_FRONTEND_V2=true in CI build and E2E
- Adds e2e job running Playwright against preview + backend
- Documents rollback procedure (single env var flip)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Fin de PR 1

Ouvrir la PR `feat/v2-lot-6-migration` -> `main`. Description obligatoire :
- Lien vers CHANGELOG
- Capture smoke checklist
- Note : phase 2 (suppression fichiers) différée de 7 jours.

---

## Phase 2 — Après T0 + 7 jours, si zéro incident

### Task 12 — Cleanup pages legacy (NOUVELLE PR `chore/v2-lot-6-cleanup-legacy`)

**Pré-requis** : validation explicite utilisateur (« OK go phase 2 ») après 7 jours de run en prod sans incident majeur.

**Files à supprimer** :
- `dashboard/src/pages/Dashboard.tsx`
- `dashboard/src/pages/ParisDuSoir.tsx`
- `dashboard/src/pages/WatchlistPage.tsx`
- `dashboard/src/pages/HeroShowcase.tsx`
- `dashboard/src/pages/HomePage.tsx`
- `dashboard/src/pages/MatchDetail.tsx`
- Composants exclusifs détectés par scan (voir Steps).

**Steps** :

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git checkout main && git pull
git checkout -b chore/v2-lot-6-cleanup-legacy

# 1. Scan des composants importés UNIQUEMENT par les pages à supprimer
for page in Dashboard ParisDuSoir WatchlistPage HeroShowcase HomePage MatchDetail; do
  echo "=== $page imports ==="
  grep -E "^import .* from" "dashboard/src/pages/$page.tsx" 2>/dev/null
done > /tmp/legacy-imports.txt

# 2. Pour chaque composant importé, vérifier s'il est utilisé ailleurs. Si non, candidat à suppression.
# (Inspection manuelle requise — ne pas automatiser la suppression.)

# 3. Supprimer les pages une par une, rebuild après chaque
for f in Dashboard.tsx ParisDuSoir.tsx WatchlistPage.tsx HeroShowcase.tsx HomePage.tsx MatchDetail.tsx; do
  git rm "dashboard/src/pages/$f"
  (cd dashboard && npm run build) || { echo "Build broke on $f, reverting"; git checkout "dashboard/src/pages/$f"; break; }
done

# 4. Retirer imports orphelins dans App.tsx (shim) s'il en restait
# 5. Retirer du shim les références à ces pages
```

Mettre à jour `App.tsx` pour ne plus référencer ces pages (après fix build) :
```tsx
// Le shim legacy mode devient encore plus minimal ou disparaît.
// Si on veut simplifier : App.tsx = export default AppV2; et retirer le flag côté code.
// Décision: garder le flag jusqu'à phase 3 (future), mais retirer les routes supprimées.
```

Tests + build :
```bash
cd dashboard
npm run test -- --run
npm run build
npm run e2e # doit rester vert
```

**Commit** :
```bash
git commit -m "$(cat <<'EOF'
chore(cleanup): remove legacy V1 pages after V2 stabilization

Removes Dashboard, ParisDuSoir, WatchlistPage, HeroShowcase,
HomePage, MatchDetail. Redirects remain active via
LegacyRedirect + FastAPI middleware.

Observation window T0+7d complete with zero incident.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Critères de complétion (Definition of Done)

- [ ] `redirects.test.tsx` vert — 8 redirects + preservation query params.
- [ ] `test_legacy_redirects.py` vert — 8 redirects HTTP 301 + preservation + test non-legacy.
- [ ] 3 specs Playwright verts en local et CI.
- [ ] `npm run build` vert avec `VITE_FRONTEND_V2=true`.
- [ ] `npm run test` vert (suite existante intouchée).
- [ ] CHANGELOG-v2-frontend.md à jour avec rollback procédure.
- [ ] CI GitHub Actions exécute job `e2e` en vert.
- [ ] Railway `VITE_FRONTEND_V2=true` activé (capture documentée).
- [ ] Smoke checklist exécutée manuellement post-deploy, tous items cochés.
- [ ] Phase 2 programmée (calendrier T0+7d noté dans `tasks/todo.md`).

---

## Risques identifiés et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Redirect boucle infinie (ex : `/matchs` redirige vers lui-même) | Faible | Élevé | Test unitaire détecte la non-terminaison en < 2s timeout. |
| Composant exclusif supprimé par erreur -> build cassé | Moyen | Moyen | Phase 2 séparée, build après chaque suppression, rollback fichier par fichier. |
| E2E flaky en CI (timing backend) | Moyen | Faible | `retries: 2` en CI, `wait-on` avant start Playwright. |
| Cookie session Playwright non posé | Moyen | Moyen | Fixture `auth.ts` parse `set-cookie` du login API, assert status 200. |
| User premium seed manquant en CI | Moyen | Élevé | Secrets `E2E_PREMIUM_EMAIL/PASSWORD` + seed SQL dans `api/tests/fixtures/`. |
| Crawler Google perd du SEO sur ancien `/football` | Faible | Moyen | 301 permanents côté FastAPI + sitemap.xml à mettre à jour (note : suivi séparé). |

---

## Notes de reprise

- Si Task 5 (data-testid) fait exploser un test visuel snapshot, mettre à jour le snapshot (`npm run test -- -u`) dans le même commit.
- Si Playwright install échoue en CI (manque dépendance système), utiliser `npx playwright install --with-deps` — déjà dans le workflow.
- L'ordre des tasks est strict : 1 -> 11 linéaire. Seules les tasks 7/8/9 (E2E specs) peuvent être parallélisées entre elles une fois la Task 6 mergée.
