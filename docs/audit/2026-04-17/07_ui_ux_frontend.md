# 07 — UI/UX frontend

> Audit du 2026-04-17 — profondeur **Deep**
> Auditeur : rôle senior UI/UX + frontend
> Périmètre : `ProbaLab/dashboard/` (React 19 + Vite + Tailwind 4 + Radix/shadcn)

---

## 1. Périmètre audité

Frontend ProbaLab — dashboard SPA exposé au public en production.

Code source examiné :

- **Pages** (`src/pages/`) — 15 fichiers, 4 245 LOC au total. Les trois plus lourdes : `MatchDetail.tsx` (727), `HomePage.tsx` (511), `Admin.tsx` (445), `Dashboard.tsx` football (317), `Performance.tsx` (318), `ParisDuSoir.tsx` (429).
- **Routing** : `App.tsx` (429 LOC) — BrowserRouter + 19 `<Route>`, lazy loading, ErrorBoundary avec auto-reload sur chunk errors.
- **Composants** : `src/components/` — `ui/` (10 primitives shadcn), `visuals/` (11 effets animés type NeuralCortex, AuroraBackground, ParticleNetwork), `paris-du-soir/` (7 fichiers), `performance/` (6 fichiers).
- **Design system** : `src/index.css` (828 LOC) — tokens HSL, classes `fs-*` custom (FlashScore-like), `@custom-variant dark`.
- **PWA** : `public/manifest.json` (minimal), `public/sw.js` (push-only, pas de cache offline).
- **Build** : `vite.config.ts` — proxy `/api` et `/nhl` vers `api.probalab.net`, alias `@`. Pas de plugin PWA, pas de compression, pas de bundle analyzer.

---

## 2. État actuel

### 2.1 Ce qui fonctionne bien

1. **Architecture de routing saine.** `App.tsx` utilise `React.lazy()` sur les 17 pages et un `Suspense` unique — bon split de bundle. L'`ErrorBoundary` gère spécifiquement les "Failed to fetch dynamically imported module" (chunks obsolètes après redeploy) avec une garde anti-boucle (`sessionStorage._chunk_reload`) — élégant, rare dans les SPA de ce niveau.
2. **Design tokens bien structurés.** `index.css` définit deux thèmes (light/dark) en HSL, avec tokens sémantiques (`--background`, `--card`, `--primary`, `--destructive`, `--muted-foreground`) et tokens métier (`--fs-live`, `--fs-score-bg`). Le `@custom-variant dark` (Tailwind 4) est correctement câblé.
3. **Bottom nav mobile + header desktop.** `App.tsx:235-279` implémente une `BottomNav` fixe sur `md:hidden` qui duplique les onglets header — pattern standard sur apps sport (FlashScore, SofaScore).
4. **Skip-link accessibilité présent.** `App.tsx:365` — `<a href="#main-content" class="sr-only focus:not-sr-only ...">` est un bon geste de base, malheureusement isolé (voir 2.3).
5. **`@tanstack/react-query` installé et configuré** (`retry: 1`, `refetchOnWindowFocus: false`). Mais peu utilisé — la majorité des pages font des `fetch()` et `useState` manuels (cf `HomePage.tsx:138-190`).
6. **Pivot en cours.** Le design doc `tasks/design_pivot_probas_sportives_2026-04-11.md` corrige explicitement la leçon 55 (feature principale enfouie) : bandeau sticky "Paris du Jour" + Top 3 NHL + dashboard home unifié. La refonte arrive pile sur les problèmes identifiés ci-dessous.

### 2.2 Dette technique / bugs latents

1. **Typographie illisible massivement déployée — leçon 54 non appliquée.**
   Comptage brut :
   - `text-[9px]` : **27 occurrences** dans 9 fichiers (ParisDuSoir, NHLPage, Dashboard, StatsDashboard, HistorySection, ExpertPickCard…)
   - `text-[10px]` : **101 occurrences** dans 23 fichiers
   - `text-[11px]` : **26 occurrences** dans 11 fichiers
   - Total < 12px : **154 occurrences dans 26 fichiers**
   La leçon 54 interdit pourtant < 12px. Exemples de régression :
   - `HomePage.tsx:25` — label `Alerte Mi-Temps` en `text-[10px]` (info live critique).
   - `HomePage.tsx:200` — bouton PRO header en `text-[10px]`.
   - `BetCard.tsx:146` — "bankroll" sous Kelly en `text-[10px]`.
   - `components/paris-du-soir/StatsDashboard.tsx` — 24 occurrences de `text-[9px]`/`[10px]` cumulées, sur la page "feature principale" du site.
   Conclusion : la lesson a été documentée mais jamais propagée. C'est un lint non-respecté.

2. **A11y : couverture quasi nulle sur une SPA grand public.**
   - `aria-label` : **21 occurrences, 5 fichiers**.
   - `role=` : **9 occurrences, 4 fichiers** (dont 2 viennent de `ui/table.tsx` primitif).
   - `alt=` : **8 occurrences, 4 fichiers** — alors que `HomePage` et `Dashboard` affichent des dizaines de logos d'équipes avec `alt=""` (`HomePage.tsx:70, 94`).
   - `tabIndex` : **1 seule occurrence** dans tout `src/` (`Dashboard.tsx:69`). Or on compte **101 `onClick`** — donc ~100 éléments cliquables (`<div onClick={…}>`) qui ne sont ni `button`, ni `role="button"`, ni focusables au clavier. Les cartes match, cards Football/NHL, MatchRow VIP de la HomePage : **toutes inaccessibles au clavier**.
   - Score WCAG 2.1 AA estimé : échec sur 1.3.1 (info/relationships), 2.1.1 (keyboard), 2.4.7 (focus visible), 4.1.2 (name/role/value). Impossible de passer un audit formel en l'état.

3. **Navigation desktop : feature principale ambiguë.**
   `App.tsx:136-190` définit dans le header trois NavLink sport + "Value Bets" (4e onglet) + Perf + Admin. La leçon 55 est partiellement corrigée : "Value Bets" a été déplacée à la 3e position (après Football/NHL) et affichée en amber. Mais :
   - Depuis la HomePage, l'utilisateur accède à Value Bets via CTA hero (1 clic) **ou** header (1 clic) — OK.
   - Depuis `/football`, `/nhl` ou `/match/:id`, pas de CTA de retour vers Value Bets à l'intérieur du contenu. Sur mobile, la bottom nav sauve. Sur desktop, l'utilisateur en profondeur doit monter au header. À 1 clic mais peu discoverable.
   - Le pivot en cours prévoit un **bandeau sticky "Paris du Jour"** sur toutes les pages — non encore implémenté. Tant qu'il ne l'est pas, la leçon 55 n'est corrigée qu'à moitié.

4. **API shape consistency — régression leçon 59 guérie mais fragile.**
   `HomePage.tsx:468-485` consomme `betStats.last_10` en supposant la shape `{result, label, odds}`. Le code accepte aussi `bet.bet_label` comme fallback, trace écrite de l'incident. **Aucun type TypeScript partagé** : `betStats` est `useState<any>` (`ParisDuSoir.tsx:87`, HomePage n'a pas de type), il n'existe pas de fichier `src/types/api.ts` global — le répertoire `src/types/` existe mais n'est pas référencé par les pages auditées. La leçon 59 peut re-casser à chaque modif backend sans filet.

5. **Service Worker minimaliste.**
   `public/sw.js` gère uniquement les push notifications — pas de `install`/`activate`, pas de cache strategy, pas de précache. `manifest.json` est incomplet : **une seule icône** (favicon.svg), pas de `192x192` / `512x512` PNG (iOS l'exige pour l'ajout à l'écran d'accueil), pas de `screenshots`, pas de `shortcuts`. Le PWA est donc "installable en théorie" mais dégradé sur iOS/Android. Pas de `vite-plugin-pwa` — todo.md Phase 5.4 non exécuté.

6. **Chiffrement dark mode incomplet.**
   Grep `dark:` : 21 occurrences dans 5 fichiers seulement. Le design system dark est porté à 95% par les **tokens CSS** (`.dark { --background: ... }` dans `index.css`), donc la majorité des composants héritent — mais dès qu'on sort des tokens (couleurs hardcodées `text-emerald-400`, `bg-emerald-500/5` présentes partout dans `BetCard.tsx:88-96`), on perd l'inversion. Exemples de fonds/bordures hardcodés en `*/5` et `*/20` qui ne s'adaptent pas au light mode. Light mode probablement cassé sur plusieurs pages — à vérifier visuellement, mais forte présomption.

7. **`index.css` de 828 lignes.** CSS monolithique avec classes utilitaires custom (`fs-match-row`, `fs-bottom-nav`, `fs-summary-bar`, `fs-league-header`, `logo-container`, `glow-value`, `flame-badge`, `prob-bar-fill`). 16 classes `fs-*` référencées dans les composants. Cohabite avec Tailwind — dette future si Tailwind 5 change la syntaxe `@custom-variant`.

### 2.3 Code smells repérés

1. **`useState<any>` et types absents.** `ParisDuSoir.tsx` : `bets`, `stats`, `expertPicks`, `history` → tous `any`. Pas de `src/types/api.ts`. Sur une SPA de 4 245 LOC pages + ~3 000 LOC components, c'est indigne. Toutes les lessons liées aux API shape (59) sont structurellement non prévenues.
2. **Pages hors échelle.** `MatchDetail.tsx` = 727 LOC. `HomePage.tsx` = 511 LOC. `ParisDuSoir.tsx` = 429 LOC avec `BetSection` sous-composant inline + 3 `useEffect` concurrents. Refactor nécessaire — on ne teste rien à cette taille.
3. **`<div onClick>` partout au lieu de `<button>`.** `HomePage.tsx:55, 351, 381` — cartes Football/NHL sur la home. `BetCard.tsx` — toutes les actions. C'est un choix esthétique (pas de reset CSS de `button`) mais qui casse clavier, screen reader, focus ring, Enter/Space. À corriger : `Button` shadcn `variant="ghost"` fait le boulot.
4. **Pas de framework de tests UI.** `components/__tests__/` existe mais vide ou quasi — les tests frontend ne semblent pas pratiqués (vitest installé mais sans suite dédiée UI). Les régressions leçons 54/55/56/59 sont donc structurellement non détectables en CI.
5. **`ErrorBoundary` en classe legacy.** `App.tsx:24` — classe JSX non typée (`constructor(props)` sans types). React 19 permet d'utiliser `react-error-boundary` ou un pattern hooks. Fonctionne, mais pas idiomatique.
6. **Strings dur-codées françaises.** Pas de i18n. Stratégique si l'ambition est "meilleure app du marché" (monde anglophone = potentiel de marché x5).
7. **Hero HomePage chargé.** `HomePage.tsx:198-230` superpose `NeuralCortex` (60 nodes animés), un SVG logo avec filter blur, un CTA hero, puis 4 sections (Value Bets card, social proof, ROI bar, shortcuts grid, VIP spots). Leçon 56 ("dashboard bruyant") partiellement applicable — densité visuelle haute en dépit de la refonte. Les visuels `NeuralCortex`/`AuroraBackground`/`ParticleNetwork` ajoutent ~3-5 ko JS chacun et consomment GPU en permanence — check mobile low-end à faire.
8. **Manifeste React Router v7 non exploité.** React Router 7.13 est installé mais aucun `loader`/`action`/streaming SSR — reste en mode SPA classique. OK, mais ne pas updater juste pour la version.

### 2.4 Gaps vs bonnes pratiques UI mobile (SofaScore, OneFootball)

| Critère | SofaScore / OneFootball | ProbaLab |
|---|---|---|
| Time-to-first-score (mobile) | < 1.5 s | lazy chunk + NeuralCortex + fetch series — probable 3-5 s sur 4G |
| Offline fallback | partiel (derniers scores en cache) | aucun (sw.js push-only) |
| Pull-to-refresh | natif | absent |
| Swipe entre journées | fluide | `fs-date-bar` horizontal scroll, pas de gesture |
| Live score push haptic | oui | push notif OK, pas de haptic (navigator.vibrate absent) |
| Tap target 44×44 min | respecté | `w-4 h-4` logos + cliquables à `py-1` : non (iOS HIG échec) |
| Typographie corps | ≥ 13 px | 9-11 px sur 26 fichiers |
| A11y VoiceOver | équipes, scores annoncés | `alt=""` sur logos, `<div onClick>` non annoncés |
| Thème système | oui | oui (ThemeProvider) — OK |
| Fréquence refresh données live | 10-30 s websocket | polling absent sur HomePage/Dashboard (sauf `live_alerts` au mount) |

**Verdict** : ProbaLab a les intentions FlashScore (naming `fs-*`) mais l'exécution reste en-deçà sur 6/10 critères critiques mobile.

---

## 3. Niveau de maturité : **L2 / L5** (fonctionnel, sous L3)

Justification :

- **L1 (MVP fragile)** : non. Architecture solide, routing clean, design tokens, pages livrées.
- **L2 (fonctionnel)** : **oui**. Tout marche. Les flux primaires fonctionnent pour un user moyen sur desktop, en dark mode.
- **L3 (solide commercial)** : **pas encore**. A11y échoue audit formel ; 154 violations de la leçon 54 ; light mode probablement cassé ; aucune gesture mobile native ; pas de tests UI. Un product owner exigeant refuserait le signoff.
- **L4/L5** : hors-sujet pour l'instant.

Le pivot en cours peut faire passer à **L3** s'il inclut : fix typographie systématique, bandeau sticky cross-page, types API partagés, correction a11y des `<div onClick>`.

---

## 4. Benchmark vs leader du marché

**Leaders retenus** : SofaScore (UX mobile best-in-class), OneFootball (grand public européen), Action Network (US, betting-first avec picks + tracker).

| Dimension | SofaScore | OneFootball | Action Network | ProbaLab (2026-04-17) |
|---|---|---|---|---|
| Home dashboard clarity | 9/10 | 8/10 | 8/10 | 5/10 (visuels bruyants, hero trop haut) |
| Time-to-value (bet/pick) | N/A | N/A | 2 clics | 1-2 clics après pivot (4 avant) |
| Mobile gestures natives | excellent | excellent | bon | absent |
| Typographie / lisibilité | 14 px min | 14 px min | 13 px min | 9-11 px fréquent |
| A11y WCAG AA | pass | pass partiel | pass | fail |
| PWA installable qualité | oui, riche | oui | partiel | présent mais dégradé |
| Dark mode qualité | exemplaire | exemplaire | bon | dark OK, light suspect |
| Personnalisation (watchlist) | poussée | poussée | simple | `/watchlist` présent mais secondaire |
| Push live pertinents | oui (buts, cartons) | oui | picks | push picks OK, pas de live goals |
| Explicabilité picks (critique ProbaLab) | N/A | N/A | narrative + stats | **différenciateur possible** : Gemini + stats, mais sous-exploité UI |

Traduction : ProbaLab est **derrière sur les fondamentaux UX mobile** (typographie, a11y, gesture) mais dispose d'un atout narratif unique (explication IA + moteur 3 couches) qu'aucun concurrent n'expose proprement. La surface UI doit rattraper avant de capitaliser dessus.

---

## 5. Gaps pour passer au niveau supérieur

### P0 — Bloquants L2 → L3 (2 semaines)

1. **Lint de typographie.** Ajouter une règle ESLint custom ou un script CI qui fail sur `text-[9px|10px|11px]`. Remplacer les 154 occurrences par `text-xs` (12) ou `text-sm` (14). Non négociable — leçon 54 déjà coûté une correction post-feedback user.
2. **Accessibilité clavier/SR minimale.** Convertir `<div onClick>` → `<button>` ou ajouter `role="button" tabIndex={0} onKeyDown={Enter|Space}` sur les 100 éléments cliquables non-natifs. Ajouter `alt` aux logos équipes (`alt={team.name}`) dans HomePage, Dashboard, MatchDetail. Cible : `aria-label` couverture > 50 occurrences, tous les patterns cliquables focusables.
3. **Types API partagés.** Créer `src/types/api.ts` avec `Bet`, `Prediction`, `Match`, `BetStats`, `Pick`. Générer avec `dashboard/generate-types.sh` (déjà présent — vérifier utilisation). Supprimer tous les `useState<any>` en pages.
4. **Bandeau sticky "Paris du Jour" cross-page.** Livrer le pivot (design doc 2026-04-11 D3) — 1 clic garanti depuis toutes les pages y compris `/match/:id`.
5. **Audit light mode manuel.** Parcourir toutes les pages en `html:not(.dark)`. Remplacer les couleurs hardcodées `bg-emerald-500/5` par des tokens (`bg-primary/5`) ou fournir des variantes `dark:`.

### P1 — Montée L3 → L4 (4-6 semaines)

6. **Tests UI vitest + Testing Library.** Viser 60% de couverture composants critiques : `BetCard`, `MatchRow` (HomePage+Dashboard), `ParisDuSoir`, `HomePage` hero + stats. Ajouter tests spécifiques leçons 54/55/59 (régression-proof).
7. **PWA complète.** `vite-plugin-pwa` + cache strategy network-first pour `/api`, stale-while-revalidate pour images. Manifest avec icons 192/512 PNG + `shortcuts` (direct `Value Bets`, `Today's Matches`).
8. **Gestures mobile.** `swipe` entre journées sur Dashboard/NHLPage (`react-swipeable` ou Pointer Events). Pull-to-refresh sur HomePage et Dashboard. Haptic feedback sur actions (`navigator.vibrate`).
9. **Refactor pages > 400 LOC.** Sortir les sous-composants inline de `MatchDetail.tsx`, `HomePage.tsx`, `ParisDuSoir.tsx` en fichiers dédiés. Seuil cible : 250 LOC max par page.
10. **React Query partout.** Remplacer les `useState + useEffect + fetch` par `useQuery` avec `staleTime` approprié. Unifie la gestion loading/error, élimine les re-fetches au mount.

### P2 — Différenciation L4 → L5 (2-3 mois)

11. **Explicabilité UI des picks.** Sur chaque `BetCard`, un lien "Pourquoi ?" qui affiche la stack (edge, Poisson %, ELO, ML confidence, narrative Gemini). Aucun concurrent ne le fait à ce niveau.
12. **Mode focus single-match.** Page `/match/:id` en plein écran, animations d'entrée coup par coup pour les matchs live (compatible avec le scheduler push).
13. **i18n EN/ES.** `i18next` + `@intlify/unplugin-vue-i18n`-équivalent React. Marché x5 potentiel.
14. **SSR ou RSC sur landing.** React Router v7 supporte SSR — landing optimisée SEO (actuellement SPA pure, Google indexe moins bien).
15. **Design system documenté.** Storybook ou Ladle pour les 10 primitives `ui/` + les patterns métier (`BetCard`, `MatchRow`). Onboarding dev futur.

---

## 6. Risques identifiés

1. **Réputationnel — feedback user typographie déjà encaissé.** La leçon 54 est documentée depuis le 2026-04-05. 12 jours plus tard, 154 violations toujours en prod. Si un nouveau user se plaint publiquement (TrustPilot, Reddit), le signal "correctifs non appliqués" est pire que l'erreur initiale.
2. **Légal/conformité.** Dans l'UE, une app grand public non-accessible expose à la directive EAA (European Accessibility Act, juin 2025 applicable). Paris sportifs est un secteur scruté (ARJEL/ANJ en France). A11y fail + affichage ROI = surface légale.
3. **Light mode cassé silencieusement.** Si un user switch via `ModeToggle`, probable que 30-50% du contenu devient illisible. Aucun test ne le détecte. Churn silencieux.
4. **Pivot incomplet = pire que pas de pivot.** Si le bandeau sticky n'est livré que sur HomePage mais pas sur `/match/:id`, la leçon 55 n'est pas corrigée. Mieux vaut livrer le pivot en 1 shot que par moitiés.
5. **PWA iOS dégradée.** Ajout à l'écran d'accueil produit une icône vectorielle floue sur Safari iOS (pas de 512×512 PNG). Perception "low quality" immédiate.
6. **Bundle size non mesuré.** `visuals/` contient 11 composants animés (canvas/SVG). Aucune extraction par route visible — tout peut se retrouver dans le chunk HomePage. À mesurer avec `rollup-plugin-visualizer`.

---

## 7. Recommandations stratégiques

1. **Figer L3 comme jalon pivot.** Le pivot en cours (`feat/pivot-probas-sportives`) ne doit pas être mergé tant que les 5 P0 ne sont pas livrés. Ça garantit que le pivot ne re-exporte pas les mêmes défauts UI.
2. **Créer un `UI_STANDARDS.md`.** 1 page, 10 règles max : tailles min (12/14/16), interaction clavier obligatoire, alt obligatoire, tokens pas de couleurs hardcodées, etc. Lu en pré-commit hook.
3. **Lint CI frontend strict.** `eslint-plugin-jsx-a11y` en warning aujourd'hui, puis en error dans 1 mois. Règle custom "no-tiny-text" pour les tailles arbitraires < 12 px.
4. **Internaliser un "responsable UX" sur chaque PR touchant `pages/`.** Même s'il est le développeur, checklist explicite a11y + lisibilité + light mode. La leçon 54 aurait été attrapée à la review si la checklist existait.
5. **Investir sur l'explicabilité avant sur les effets.** Les visuals (NeuralCortex, Aurora, Particle) sont cosmétiques ; l'avantage concurrentiel ProbaLab est la **transparence du pick**. Construire la card "Pourquoi ce pick" plutôt qu'un 12ᵉ effet.
6. **Monitorer les Core Web Vitals en prod.** Pas de trace de `web-vitals` ou RUM — ajouter `@vercel/speed-insights` ou équivalent pour détecter les régressions mobile silencieuses (LCP, CLS, INP).
7. **Tests Playwright sur flux Value Bets.** Un seul test E2E : home → Value Bets → tracker un bet → voir dans historique. Couvre les 4 leçons UI en un smoke test.

---

## 8. Liens internes

- Leçons UI de référence : `ProbaLab/tasks/lessons.md` lignes 54-56, 59.
- Pivot en cours : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`.
- Plan d'action : `ProbaLab/tasks/todo.md` Phases 5.1 (dark mode), 5.4 (PWA).
- Inventaire Pages : `ProbaLab/dashboard/src/pages/` (15 fichiers).
- Routing : `ProbaLab/dashboard/src/App.tsx:136-279` (Header + BottomNav + Routes).
- Design system : `ProbaLab/dashboard/src/index.css` (828 LOC, `fs-*` + tokens HSL).
- PWA : `ProbaLab/dashboard/public/manifest.json`, `ProbaLab/dashboard/public/sw.js`.
- Audits frères : voir `00_EXECUTIVE_SUMMARY.md` (à produire), `09_produit_positionnement.md` (à produire), `11_evaluation_pivot.md` (à produire).
