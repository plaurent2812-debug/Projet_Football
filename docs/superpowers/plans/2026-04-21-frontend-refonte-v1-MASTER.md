# Frontend Refonte V1 — Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each lot. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refondre le frontend ProbaLab (dashboard SPA React 19 + Vite + Tailwind 4) pour aligner UX/UI avec le pitch "probas + value bets", identité Fintech/Trading, mobile-first, track record CLV public.

**Architecture:** Refonte incrémentale par lots. Feature flag `VITE_FRONTEND_V2=true` bascule vers les nouvelles routes. Ancien code conservé jusqu'au cutover final. Chaque lot livre du code testable et mergeable indépendamment.

**Tech Stack:** React 19 · Vite 7 · Tailwind CSS 4 · shadcn/Radix UI · TanStack Query 5 · Recharts 3 · react-router-dom 7 · Vitest · Playwright (nouveau). Backend FastAPI existant étendu.

**Spec source:** [docs/superpowers/specs/2026-04-21-frontend-refonte-v1-design.md](../specs/2026-04-21-frontend-refonte-v1-design.md)

---

## Structure du plan · 6 lots séquentiels

Chaque lot est un plan autonome dans son propre fichier. Exécution dans l'ordre — chaque lot s'appuie sur les précédents.

| # | Lot | Fichier | Livre |
|---|---|---|---|
| 1 | **Foundation** | [lot-1-foundation.md](./2026-04-21-frontend-refonte-v1-lot-1-foundation.md) | Design system (tokens, composants système), routing V2, feature flag, layout shell (header/bottom nav/trial banner) |
| 2 | **Backend endpoints** | [lot-2-backend.md](./2026-04-21-frontend-refonte-v1-lot-2-backend.md) | Nouveaux endpoints : `/api/safe-pick`, `/api/public/track-record/live`, `/api/matches`, `/api/odds/:id/comparison`, `/api/user/bankroll/roi-by-market`, CRUD rules |
| 3 | **Accueil + Matchs** | [lot-3-home-matches.md](./2026-04-21-frontend-refonte-v1-lot-3-home-matches.md) | Pages `/` (landing + dashboard) et `/matchs` avec filtres |
| 4 | **Fiche match** | [lot-4-match-detail.md](./2026-04-21-frontend-refonte-v1-lot-4-match-detail.md) | Page `/matchs/:id` 2 colonnes sticky desktop, ordre A mobile, gating free/premium |
| 5 | **Premium + Compte** | [lot-5-premium-account.md](./2026-04-21-frontend-refonte-v1-lot-5-premium-account.md) | Landing `/premium` avec track record live, page `/compte` avec tabs profil + abonnement + bankroll + notifications (rules builder) |
| 6 | **Migration + Cutover** | [lot-6-migration.md](./2026-04-21-frontend-refonte-v1-lot-6-migration.md) | Redirects 301 anciennes routes, suppression pages legacy, tests E2E Playwright des 3 parcours critiques, activation flag en prod |

---

## Invariants partagés (respectés par chaque lot)

### Conventions de code
- **TypeScript strict** partout. `any` interdit sauf exceptions documentées en commentaire.
- **Fichiers ≤ 300 lignes**. Au-delà, split par responsabilité (lesson 63 : logique pure séparée des routes).
- **Composants purs** prioritaires. Side-effects dans hooks custom (`useFoo`).
- **Pas de `// TODO`** dans le code livré. Toute incomplétude = task restante dans le lot.

### Tests
- **TDD strict** : test écrit et failing AVANT implémentation pour chaque composant.
- **Vitest** pour unitaires (`*.test.tsx` à côté du composant).
- **Testing Library** pour interactions composants.
- **Playwright** introduit au lot 6 pour E2E.
- Chaque lot doit finir **tests verts** (`npm run test:ci` dans `ProbaLab/dashboard/`).

### Structure des fichiers frontend
```
ProbaLab/dashboard/src/
├── app/
│   ├── App.tsx                 (routing principal, inchangé hors routes v2)
│   └── v2/
│       ├── AppV2.tsx           (nouveau routing v2)
│       └── routes.tsx          (table des routes v2)
├── components/
│   ├── ui/                     (shadcn existants — inchangés)
│   └── v2/
│       ├── system/             (StatTile, ProbBar, ValueBadge, OddsChip, BookOddsRow, LockOverlay, TrialBanner, RuleChip)
│       ├── layout/             (HeaderV2, BottomNavV2, LayoutShell, TrialBannerContainer)
│       ├── home/               (HeroLanding, SafeOfTheDayCard, MatchRow, StatStrip, ValueBetsTeaser, PremiumCTA)
│       ├── matches/            (DateScroller, SportChips, LeagueGroup, FilterSidebar, MatchesTable)
│       ├── match-detail/       (MatchHero, StatsComparative, H2HSection, AIAnalysis, CompositionsSection, AllMarketsGrid, RecoCard, BookOddsList, ValueBetsList, StickyActions)
│       ├── premium/            (LiveTrackRecord, PricingCards, TransparencyGuarantee, FAQShort)
│       ├── account/            (AccountTabs, ProfileTab, SubscriptionTab, BankrollTab, NotificationsTab, RuleBuilder)
│       └── common/             (ErrorBoundary, LoadingState, EmptyState)
├── hooks/v2/                   (useMatches, useMatchDetail, useSafePick, useTrackRecord, useBankroll, useNotificationRules)
├── lib/v2/                     (api client typé, format helpers, date helpers)
├── pages/v2/                   (HomeV2, MatchesV2, MatchDetailV2, PremiumV2, AccountV2, LoginV2, RegisterV2)
├── styles/v2/
│   └── tokens.css              (CSS vars palette fintech)
├── types/v2/                   (tous les types TS partagés entre composants)
└── test/setup.ts               (déjà existant)
```

**Règle** : tout code V2 vit sous `v2/`. Le code legacy reste intouché jusqu'au lot 6.

### Conventions de commit
- Un commit par step TDD (test fail → implem → pass → commit).
- Format : `feat(v2/<area>): <message court>` ou `test(v2/<area>): <message>`.
- Co-Authored-By Claude sur chaque commit (lesson standard projet).
- Jamais `--no-verify`.

### Rollback & feature flag
- Env var `VITE_FRONTEND_V2` dans `dashboard/.env.local` + Railway prod.
- `false` (défaut) → ancien code servi, V2 totalement invisible.
- `true` → routes V2 actives, anciennes routes redirigent (lot 6).
- Un bug en prod sur V2 = flag à `false` en 1 minute, retour immédiat à l'ancien.

### Dépendance backend
- Lot 2 livre les endpoints consommés par lots 3–5.
- Lots 3–5 peuvent commencer sur mocks (TanStack Query avec `msw` pour les dev), mais doivent switcher sur vrais endpoints avant merge.

---

## Pré-requis globaux (à faire une fois avant le lot 1)

### P1 · Installer dépendances manquantes
```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/dashboard"
npm install --save-dev @playwright/test msw @testing-library/react-hooks
npm install react-hook-form zod @hookform/resolvers
```

**Expected:** installation propre, 0 peer dependency error bloquant.

### P2 · Vérifier tests existants verts (baseline)
```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/dashboard"
npm run test:ci
```

**Expected:** tous les tests actuels passent. Si échec : diagnostiquer et fixer AVANT de démarrer les lots (sinon on ne saura pas distinguer régression vs état initial cassé).

### P3 · Créer la branche de travail
```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git checkout -b feat/frontend-refonte-v1
```

### P4 · Activer la variable d'env dev
Créer/modifier `ProbaLab/dashboard/.env.local` :
```
VITE_FRONTEND_V2=true
VITE_API_URL=http://localhost:8000
```

Ne PAS committer ce fichier (déjà dans `.gitignore` si existant, sinon ajouter).

---

## Ordre d'exécution recommandé

```
P1-P4 (pré-requis) → Lot 1 (foundation) → Lot 2 (backend)
                                       → Lot 3 (home + matches) ─┐
                                       → Lot 4 (match detail)    ├→ Lot 6 (migration + cutover)
                                       → Lot 5 (premium+compte)  ─┘
```

Lots 3, 4, 5 peuvent partiellement se paralléliser (branches séparées) une fois lots 1 et 2 mergés, mais en pratique exécution séquentielle plus sûre (tests d'intégration, éviter conflits de merge sur `AppV2.tsx`).

---

## Critères d'acceptation master (fin de refonte)

- [ ] `VITE_FRONTEND_V2=true` → application V2 complète et utilisable.
- [ ] `VITE_FRONTEND_V2=false` → ancien code servi sans régression.
- [ ] `npm run test:ci` vert (unit + component).
- [ ] `npm run e2e` vert (3 parcours Playwright : inscription trial, visiteur → voir match → CTA premium, premium crée règle alerte).
- [ ] Lighthouse mobile ≥ 85 Performance / ≥ 95 Accessibility sur `/` et `/matchs`.
- [ ] Bundle JS initial < 250 Ko gzippé (hors chunks lazy).
- [ ] Zero console warning/error en prod.
- [ ] Tous les endpoints backend nouveaux documentés (OpenAPI auto-généré FastAPI).
- [ ] Redirects 301 actifs pour : `/paris-du-soir`, `/football`, `/football/match/:id`, `/nhl`, `/nhl/match/:id`, `/watchlist`, `/hero-showcase`.
- [ ] Matrice d'accès (section 3 du spec) respectée pour visiteur/free/trial/premium.

---

## Points d'attention transverses

### Timezone (lesson 22)
Toute date/heure manipulée côté frontend doit respecter la convention projet : UTC en source, conversion en timezone user pour affichage. Utiliser `date-fns-tz` si besoin de conversion (non installé actuellement — lot 1 P1 si nécessaire).

### fixture_id typage (lesson 48)
`fixtures.id` est TEXT côté DB (UUIDs + IDs numériques). Côté frontend = `string` partout, jamais `number`. Type partagé :
```typescript
export type FixtureId = string;
```

### RLS Supabase (lesson 59)
Toutes les requêtes frontend passent par le backend FastAPI (pas d'accès direct Supabase depuis le browser sauf auth). Service role côté backend, anon côté frontend avec RLS strict.

### Accessibilité
- Tous les composants systèmes (lot 1) doivent avoir des tests axe-core via `@testing-library/jest-dom` + `jest-axe`.
- Focus visible obligatoire (outline primary).
- Aria labels sur barres de probas, chips, boutons icônes.

### Mobile-first strict
- Chaque composant designé d'abord à 375px, desktop = extension.
- Tests composants avec `window.innerWidth` à 375 et 1280.

---

## Prochaine étape

Lancer le **Lot 1 — Foundation** : [lot-1-foundation.md](./2026-04-21-frontend-refonte-v1-lot-1-foundation.md)

Les 6 fichiers de lots seront créés dans l'ordre, chacun en suivant ce master.
