# 12 — Roadmap : Devenir la meilleure app de prédiction sportive

> Date : 2026-04-17
> Synthèse cross-domaines des annexes 01-11
> Horizon : H1 (0-4 sem) / H2 (1-3 mois) / H3 (3-12 mois)

---

## 1. Principes de priorisation

1. **Impact × 1/Effort** : chaque item P0/P1/P2 est positionné selon son rapport valeur/coût estimé dans les annexes source.
2. **Remédier avant d'ajouter** : aucun pivot public, aucune nouvelle feature grand public tant que les bugs P0 des leçons ne sont pas clos. Une transparence radicale sur des probas biaisées serait contre-productive (annexes 02, 11).
3. **Dépendances techniques** : le monitoring persistant conditionne le pivot ; l'analytics conditionne tout pilotage produit ; l'upgrade Odds API conditionne le scope NHL.
4. **Single writer convention** : un seul scheduler, un seul descripteur de déploiement, une seule source de vérité par thème (prix, version Python, BP vs pivot).
5. **Mesurer avant de vanter** : pas de page "Méthodologie / Brier public" sans walk-forward validation chiffré derrière.

---

## 2. Backlog agrégé P0 (bloquant pour L3+)

| # | Action | Annexe | Effort | Impact | Dépendances |
|---|--------|--------|--------|--------|-------------|
| P0-1 | Fix `eval_set=(X_test, y_test)` leakage (train.py:393,564) → validation split séparé | 02, 11 | 0.5j | Haut (métriques -2-5% biaisées) | — |
| P0-2 | Fix `sample_weight` CV (`params=` → `fit_params=`, train.py:369) | 02, 11 | 0.5j | Moyen | — |
| P0-3 | Rééquilibrer `WEIGHT_MARKET` 0.20 → 0.45-0.50 + backtest 12 mois | 02, 11 | 4h dev + 1j backtest | Haut (CLV +1-3%) | P0-1 |
| P0-4 | Brancher `run_monitoring_alerts()` en cron + créer table `model_health_log` | 03, 11 | 1-2j | Critique (gate Phase 2 pivot inopérant sans) | — |
| P0-5 | Fix fallback ML NHL silencieux (init 2 étapes + log WARNING + `ml_fallback_used` exposé) | 04, 11 | 1j | Haut (Brier NHL honnête) | — |
| P0-6 | Fermer `/api/admin/update-scores` à tout appel sans auth (header `X-Internal-Cron` ou CRON_SECRET) | 06, 11 | 0.5j | Haut (DoS quota API-Football) | — |
| P0-7 | `extra="forbid"` sur tous les schemas requête (`api/schemas.py`) | 06 | 0.5j | Moyen (mass-assignment) | — |
| P0-8 | Retirer `detail=str(e)` résiduel (`players.py:162`) | 06 | 5min | Bas mais trivial | — |
| P0-9 | Installer Plausible (ou PostHog) + 6 événements funnel dashboard | 09, 11 | 1j | Critique (piloter = mesurer) | — |
| P0-10 | Décider budget Odds API Pro ~500$/mois OU restreindre scope NHL à `player_goals` publiquement | 04, 11 | 1j (décision) | Critique pivot NHL | — |
| P0-11 | Walk-forward temporal validation (TimeSeriesSplit sur 3-6 mois hold-out, publier Brier) | 01 | 2-3j | Critique (crédibilité "52-55% accuracy") | P0-1 |
| P0-12 | Réconcilier BP v2 ↔ pivot (posture A/B/C tranchée, gating premium v2 défini) + aligner prix UI/BP (9,99 vs 14,99) | 09, 11 | 1j décision + 0.5j UI | Critique stratégique | — |
| P0-13 | Nettoyer legacy `Projet_Football/` : Makefile, `daily-pipeline.yml`, `ruff.toml` ciblent `ProbaLab/` | 08 | 1j | Haut (CI ment aujourd'hui) | — |
| P0-14 | Trancher dualité scheduler APScheduler ↔ endpoints `/api/trigger/*` (supprimer les 27 doublons OU le worker) + corriger commentaire `main.py:15` | 05 | 1-2j | Haut (drift scheduler déjà coûté, leçon 64) | — |
| P0-15 | Corriger `railway.toml` (2 services mais un seul `[services.deploy]`) + choisir une seule source de vérité (supprimer Procfile OU nixpacks.toml) + harmoniser Python 3.11 partout | 08 | 1j | Haut (worker peut ne pas démarrer) | — |
| P0-16 | Supprimer/déplacer `src/test_auth.py`, `src/test_connection.py`, `src/test_api_halves.py` vers `scripts/debug/` (fixent au réseau à l'import) | 08 | 2h | Moyen | — |
| P0-17 | Fix 2 tests flaky `test_stats_engine.py::TestCalculateXg` (baseline 2026-04-10 déjà signalés) | 08 | 0.5j | Moyen | — |
| P0-18 | Éradiquer `datetime.now()` / `datetime.utcnow()` nus (54 occurrences) → `datetime.now(timezone.utc)` + pre-commit ruff rule | 05, 06 | 1-2j | Haut (frontière UTC déjà coûté leçon 22, 66) | — |
| P0-19 | Lint typographie CI : règle ESLint / script bloquant `text-[9-11px]` + remplacer 154 occurrences par `text-xs`/`text-sm` | 07, 11 | 2-3j | Critique UX (leçon 54 violée 154× en prod) | — |
| P0-20 | A11y clavier/SR minimale : `<div onClick>` → `<button>` (100 éléments), `alt` sur logos équipes (HomePage, Dashboard, MatchDetail) | 07 | 3-4j | Haut (risque légal EAA + WCAG fail) | — |
| P0-21 | Créer `src/types/api.ts` + générer via `generate-types.sh` ; supprimer `useState<any>` sur Home/ParisDuSoir | 07 | 1-2j | Moyen (régression leçon 59) | — |
| P0-22 | Page `/methodology` publique : Brier 90j live, schéma Dixon-Coles, comparaison vs Forebet/Sportytrader | 09, 10, 11 | 2-3j | Critique (différenciateur invisible) | P0-4, P0-11 |

**Total P0 : 22 items, effort cumulé ~22-28 jours dev**.

---

## 3. Backlog agrégé P1 (passage L4)

| # | Action | Annexe | Effort | Impact |
|---|--------|--------|--------|--------|
| P1-1 | Découper `trigger.py` (1687 LOC, 27 endpoints) en package `trigger/` + extraction logique `src/services/` | 05, 08 | 5-8j | Haut (testabilité + leçon 62) |
| P1-2 | Découper `best_bets.py` (1428 LOC) en `reader/writer/resolver/stats` | 05 | 3-5j | Haut |
| P1-3 | Remplacer `threading.Thread` par `BackgroundTasks` ou `arq` / `dramatiq` | 05 | 2-3j | Haut (threads orphelins au reboot) |
| P1-4 | `pydantic-settings` centralisé (30 `os.getenv` dispersés) + fail-fast au boot | 05 | 1j | Moyen |
| P1-5 | Lockfile `uv.lock` / `poetry.lock` + CI qui échoue si pas committé | 05 | 1j | Moyen |
| P1-6 | Supabase via `Depends(get_supabase)` sur 3 gros routers | 05 | 2-3j | Moyen (tests sans monkey-patch) |
| P1-7 | `response_model=` obligatoire sur tout endpoint + test OpenAPI qui bloque | 05 | 2j | Moyen |
| P1-8 | Retry HTTP externe (tenacity) sur 8 appels bruts `requests.get` dans routers | 05 | 1j | Moyen |
| P1-9 | Meta-learner retraining avec 50+ features (injury VORP, xG deltas, ELO diff, form blend) | 01, 02 | 3-5j | Haut (+0.5-1% accuracy) |
| P1-10 | Model versioning : hash SHA256 + timestamp + git SHA + Brier dans metadata | 02, 03 | 1-2j | Moyen (rollback possible) |
| P1-11 | Feature drift KS test dans `drift_detector.py` (training vs 30j prod) | 03 | 2-3j | Moyen |
| P1-12 | Dashboard admin React `/admin/model-health` : Recharts timeline Brier/ECE, features driftées | 03 | 3j | Haut (pilotage ML) |
| P1-13 | Upgrade Odds API Pro → couvrir `player_points` + `player_assists` + Pinnacle fallback | 04 | 2 sem (+ budget) | Critique pivot NHL full-scope |
| P1-14 | Tests NHL ≥ 50% coverage (calibration, feature engineering, endpoints, e2e mock) | 04, 08 | 2 sem | Haut |
| P1-15 | Expansion dataset calibration NHL 2× (depuis `nhl_data_lake` + `nhl_suivi_algo_clean`) | 04 | 1 sem | Moyen |
| P1-16 | Calibration per-player NHL (gate ≥ 30 samples/joueur, fallback global) | 04 | 1 mois | Moyen |
| P1-17 | Rate limiting différencié par tier (free/premium/admin) via `key_func` custom JWT | 06 | 1 sem | Moyen |
| P1-18 | CSP + Permissions-Policy dans `SecurityHeadersMiddleware` | 06 | 0.5j | Moyen |
| P1-19 | Audit log admin uniformisé : decorator `@audit_admin_action` + `admin_audit_log` table | 05, 06 | 2j | Moyen (RGPD + forensic) |
| P1-20 | MFA admin (TOTP Supabase Auth, exiger `aal2` dans `_require_admin`) | 06 | 1-2j | Haut (compromission) |
| P1-21 | `pip-audit` + `bandit` + `gitleaks` dans la CI, bloquants HIGH | 06, 08 | 1j | Haut (CVE non détectée) |
| P1-22 | Unifier 5 `RestrictedUnpickler` dans `src/security/safe_deserialize.py` | 06 | 0.5j | Bas |
| P1-23 | `mypy --strict` bloquant sur modules stables (`bankroll`, `prediction_blender`, `best_bets_logic`) | 08 | 1j | Moyen |
| P1-24 | Test e2e pipeline (`test_pipeline_e2e.py`, marqué integration, seed fixtures + predictions + scores) | 08 | 3-5j | Haut |
| P1-25 | Monter `--cov-fail-under` par paliers 21 → 40 → 60 | 08 | suivi continu | Haut |
| P1-26 | Smoke post-deploy Railway (curl /health + rollback si KO) | 08 | 1j | Moyen |
| P1-27 | Tests UI vitest + Testing Library (`BetCard`, `MatchRow`, `ParisDuSoir`, HomePage hero) 60% | 07 | 5-7j | Moyen |
| P1-28 | PWA complète : `vite-plugin-pwa` + manifest 192/512 PNG + `shortcuts` | 07 | 2-3j | Moyen (iOS dégradé actuel) |
| P1-29 | Refactor pages > 400 LOC (`MatchDetail` 727, `HomePage` 511, `ParisDuSoir` 429) cible 250 max | 07 | 5-8j | Moyen |
| P1-30 | React Query partout (remplacer `useState + useEffect + fetch`) | 07 | 3-5j | Moyen |
| P1-31 | Audit light mode : remplacer couleurs hardcodées par tokens, fournir `dark:` variants | 07 | 2-3j | Moyen |
| P1-32 | Endpoint `/api/create-checkout-session` serveur + Customer Portal Stripe intégré | 09 | 1-2j | Haut (coupons, trials, annual) |
| P1-33 | Offre annuelle 119€ effectivement déployée en UI | 09 | 1j | Moyen |
| P1-34 | NPS in-app (1 question mensuelle après J+30) | 09 | 1j | Moyen |
| P1-35 | Dashboard admin métriques produit (DAU/WAU/MAU, signups, upgrade, churn) | 09 | 3-4j | Haut |
| P1-36 | Confidence intervals Monte Carlo (Poisson λ_home/λ_away → quantiles 5/50/95%) | 01 | 2-3j | Moyen (communication honnête) |
| P1-37 | Per-league dynamic rho recalibration (cronjob mensuel) | 01 | 1-2j | Moyen |
| P1-38 | User research : 8-10 interviews parieurs francophones (Reddit, Telegram, LinkedIn) | 09 | 5j étalés | Haut |
| P1-39 | Définir 3 personas (informé / occasionnel / curieux) | 09 | 2j | Moyen |

**Total P1 : 39 items, effort cumulé ~80-110 jours dev**.

---

## 4. Backlog agrégé P2 (polish L4→L5)

| # | Action | Annexe | Impact |
|---|--------|--------|--------|
| P2-1 | Async-first FastAPI (httpx async Supabase + API-Football) | 05 | Gain p50 -40% |
| P2-2 | API versioning `/api/v1/` + reverse proxy | 05 | Découpler |
| P2-3 | Sentry pour exceptions applicatives | 05 | Alerting |
| P2-4 | Tests de contrat OpenAPI (leçon 59 régression-proof) | 05 | Moyen |
| P2-5 | Ensemble voting XGBoost + LightGBM + HistGradient | 02 | +0.5% accuracy |
| P2-6 | OOF predictions pour stacking meta-learner | 02 | +0.5-1% |
| P2-7 | Feature importance drift alerting hebdomadaire | 02, 03 | Diagnostic |
| P2-8 | Latency monitoring par endpoint | 03 | Standard |
| P2-9 | Alerting multi-canal (Discord backup Telegram) | 03 | Redondance |
| P2-10 | CLV tracking en cron quotidien + persistance | 03 | Standard pro |
| P2-11 | Refactor `api/routers/nhl.py` (873 LOC) — sortir logique métier | 04 | Moyen |
| P2-12 | Dédupliquer feature engineering NHL (single source of truth) | 04 | Moyen |
| P2-13 | Vault secrets (Doppler / 1Password Connect) + rotation 90j automatisée | 06 | Compliance |
| P2-14 | Centralisation logs (Axiom / Datadog / Grafana Loki) | 06 | SIEM |
| P2-15 | Pen test externe trimestriel + bug bounty modeste | 06 | L5 |
| P2-16 | WAF (Cloudflare / Railway natif) | 06 | Protection |
| P2-17 | pytest-xdist + mutation testing (mutmut) sur `bankroll` et `best_bets_logic` | 08 | Qualité tests |
| P2-18 | Preview env par PR Railway | 08 | DX |
| P2-19 | Explicabilité UI des picks ("Pourquoi ?" → stack edge + Poisson + ELO + ML + Gemini) | 07, 09, 10 | **Différenciateur L5** |
| P2-20 | i18n EN/ES (marché x5) | 07 | Expansion |
| P2-21 | Gestures mobile (swipe dates, pull-to-refresh, haptic) + Core Web Vitals RUM | 07 | UX mobile |
| P2-22 | A/B testing framework (Growthbook ou flags custom) | 09 | Optimisation |
| P2-23 | Content SEO pilier (10 articles méthodo / mois) | 09 | Acquisition scalable |
| P2-24 | Public leaderboard picks historique (moat "track record") | 09 | Moat |
| P2-25 | Onboarding interactif + éducation probabiliste embarquée (tooltips Kelly / EV / CLV) | 07, 10 | Rétention |
| P2-26 | App native iOS/Android (ou PWA avancée) | 07, 09 | Marché mobile |
| P2-27 | Ablation study par composant (Poisson-only / ELO-only / Market-only) publié | 01 | Marketing scientifique |

**Total P2 : 27 items, effort cumulé ~60-90 jours dev**.

---

## 5. Horizons temporels

### H1 — Stabilisation (0-4 semaines)

Objectif : clôre les P0 critiques, poser les fondations du pivot, livrer le plan "prérequis avant Phase 1 pivot" de l'annexe 11.

Livrables :
- **Bugs ML critiques clos** (P0-1, P0-2, P0-3, P0-11) : eval_set fixé, sample_weight CV corrigé, WEIGHT_MARKET rééquilibré, walk-forward validation publié. Brier réel mesuré et connu.
- **Monitoring brancé en prod** (P0-4) : `run_monitoring_alerts()` en cron 08:30, table `model_health_log` peuplée quotidiennement.
- **Sécurité P0 fermée** (P0-6, P0-7, P0-8, P0-18) : update-scores protégé, `extra="forbid"`, fuite `detail=str(e)` retirée, `datetime.now()` migration + pre-commit rule.
- **Analytics installé** (P0-9) : Plausible actif, 6 événements funnel (`landing_viewed`, `signup_started`, `signup_completed`, `premium_viewed`, `checkout_clicked`, `checkout_completed`).
- **Infrastructure propre** (P0-13, P0-14, P0-15, P0-16, P0-17) : legacy `Projet_Football/` archivé, scheduler tranché (APScheduler only), `railway.toml` corrigé, Python 3.11 partout, scripts debug hors tests/, 2 tests flaky verts.
- **Positionnement clair** (P0-12) : posture A/B/C tranchée, BP v2.1 réconcilié avec pivot, prix aligné (9,99 ou 14,99), gating premium v2 défini.
- **NHL décidé** (P0-10) : soit budget Odds API Pro confirmé, soit scope Safe NHL publiquement restreint à `player_goals`. Fix fallback silencieux (P0-5).
- **UI foundation pivot-ready** (P0-19, P0-20, P0-21) : 154 violations typographie remplacées, `<div onClick>` accessibles, `src/types/api.ts` partagé.
- **Page `/methodology` publique** (P0-22) : Brier 90j live, schéma Dixon-Coles, comparaison concurrents — le différenciateur devient visible.

**Fin H1 = feu vert pour la Phase 1 du pivot.** Aucun des 13 prérequis de l'annexe 11 ne reste ouvert.

---

### H2 — Pivot + Passage L3+ (1-3 mois)

Objectif : exécuter le pivot avec amendements (annexe 11), monter tous les domaines à ≥ L3, poser au moins une L4 pilote.

Livrables :
- **Pivot livré en prod** (4 phases du plan) avec gating Phase 2 quantitatif (Brier < 0.21, ROI virtuel 30j > -5%, coverage ≥ 80%, ≥ 3 marchés distincts Safe foot). Si scope NHL restreint en H1, communiqué publiquement.
- **Architecture L3** : `trigger.py` et `best_bets.py` découpés en packages (P1-1, P1-2). `pydantic-settings` centralisé (P1-4). Lockfile `uv.lock` en CI (P1-5). `threading.Thread` remplacé par `BackgroundTasks`/`arq` (P1-3). Supabase via DI sur 3 gros routers (P1-6).
- **ML L3+** : meta-learner ré-entraîné avec 50+ features (P1-9), model versioning posé (P1-10), feature drift KS test (P1-11). Dashboard admin model-health React (P1-12).
- **NHL L4 pilote** (conditionnel au budget P0-10) : Odds API Pro câblé (P1-13), tests NHL ≥ 50% (P1-14), dataset calibration 2× (P1-15), calibration per-player démarrée (P1-16).
- **Sécurité L3+ → L4** : rate limiting par tier (P1-17), CSP + Permissions-Policy (P1-18), audit log admin uniformisé (P1-19), MFA admin (P1-20), pip-audit+bandit+gitleaks en CI (P1-21).
- **Tests L3** : e2e pipeline (P1-24), `--cov-fail-under=40` atteint (P1-25), mypy strict sur modules stables (P1-23), smoke post-deploy Railway (P1-26).
- **Produit L3** : checkout serveur + Customer Portal (P1-32), annuel 119€ UI (P1-33), NPS in-app (P1-34), dashboard admin DAU/MAU/churn (P1-35). User research 8-10 interviews (P1-38), personas documentées (P1-39).
- **UI L3 complète** : tests vitest 60% (P1-27), PWA complète icons 192/512 (P1-28), refactor pages > 400 LOC (P1-29), React Query partout (P1-30), light mode audité (P1-31).

**Fin H2** : pivot en prod, tous domaines ≥ L3, une L4 pilote (au choix : UI/UX ou monitoring ML ou sécurité).

---

### H3 — Différenciation L5 (3-12 mois)

Objectif : dépasser les leaders sur 2-3 dimensions identifiées en annexe 10 §5 (zones blanches).

Livrables ambitieux :
- **L5 "Transparence radicale"** (zone blanche §5.1) : page `/methodology` étendue, dashboard public Brier + log-loss + CLV vs Pinnacle par marché et par ligue, historique glissant 30/90/365j. Public leaderboard picks historique (P2-24). Ablation study par composant publié (P2-27). Aucun concurrent ne fait ça — ProbaLab devient "le site qui ne triche pas".
- **L5 "Explainability narrative"** (zone blanche §5.2) : chaque pick affiche les 3 features ML dominantes (SHAP-like), le narratif Gemini structuré, et la divergence ML vs marché (P2-19). Killer feature 2026 sur laquelle personne n'investit.
- **L5 "Éducation probabiliste embarquée"** (zone blanche §5.5) : tooltips contextuels EV/Kelly/CLV sur chaque pick, onboarding interactif gamifié (P2-25). Angle francophone presque vide.
- **Expansion structurelle** : i18n EN/ES (P2-20) = marché x5. SEO pilier 2 articles méthodo/mois (P2-23). App mobile ou PWA avancée (P2-26). A/B testing framework sur 3 décisions majeures (P2-22).
- **MLOps/Infra L4-L5** : Sentry (P2-3), centralisation logs (P2-14), secrets rotation automatisée (P2-13), pen test trimestriel (P2-15), WAF (P2-16). Async-first FastAPI (P2-1) + API versioning (P2-2).

**Fin H3** : 2-3 dimensions L5 démontrables vs leaders. Plateforme positionnée comme "héritier francophone de FiveThirtyEight pour les paris sportifs".

---

## 6. Jalons de succès

**Fin H1 (semaine 4)** :
- 0 bug P0 documenté par les leçons (eval_set, sample_weight, WEIGHT_MARKET, UTC, update-scores).
- Couverture tests ≥ 30% (baseline 21% → +9 pts via P0-16 nettoyage + extraction modules).
- Plausible actif + 6 événements funnel tracés.
- Monitoring en cron avec `model_health_log` peuplée depuis ≥ 7j.
- Prérequis pivot NHL réglés (budget OU scope restreint assumé).
- Page `/methodology` publique en ligne avec Brier 90j.
- 154 violations typographie closes + lint CI bloquant.

**Fin H2 (mois 3)** :
- Pivot en prod avec amendements (Phase 4 design_pivot livrée).
- Tous domaines ≥ L3 (moteur probas L3+, ML L3, monitoring L3, NHL L3+, archi L3, sécu L3+, UI L3, tests L3, produit L3).
- Une L4 pilote livrée (ex : monitoring dashboard admin complet, ou UI/UX post-refactor + PWA, ou sécu avec MFA + CSP + audit log).
- Couverture tests ≥ 60%. 0 endpoint sans `response_model`. 0 `threading.Thread` dans routes.
- NPS in-app instrumenté, 8-10 interviews user research réalisées.

**Fin H3 (mois 12)** :
- 2-3 dimensions L5 démontrables publiquement vs leaders (cf. zones blanches §5 annexe 10).
- Brier foot < 0.21, Brier NHL < 0.23 affichés en continu.
- Lighthouse Performance mobile > 90 sur HomePage, /methodology, /paris-du-jour.
- Trafic mobile ≥ 60%, app installable PWA propre.
- i18n EN/ES si analytics montre pertinence. SEO pilier (≥ 20 articles publiés).
- Tiers d'abonnés mesurable (conversion free→premium ≥ 3%, churn mensuel < 5%).

---

## 7. KPIs de suivi

Métriques à afficher dans le dashboard admin (tableau de bord cible P1-12, P1-35) :

| KPI | Source | Objectif | Cadence |
|-----|--------|----------|---------|
| Brier Score foot (rolling 30j) | `model_health_log` | < 0.21 | Quotidien |
| Brier Score NHL (rolling 30j) | `model_health_log` | < 0.23 | Quotidien |
| Couverture tests global | `pytest --cov` CI | 30% (H1) → 60% (H2) → 75% (H3) | Par PR |
| Lighthouse Performance mobile | Core Web Vitals RUM | > 90 | Hebdo |
| Lighthouse Accessibility | CI + manuel | > 95 (WCAG 2.1 AA) | Hebdo |
| ROI virtuel 30j par catégorie Safe/Fun/Value | Table `best_bets` | Safe > 0%, Value > +3% | Quotidien |
| Taux conversion free → premium | Plausible funnel | > 3% | Hebdo |
| DAU / WAU / MAU | Plausible | Croissance MoM > 10% | Quotidien |
| Churn mensuel premium | Stripe + DB | < 5% | Mensuel |
| NPS in-app | Widget J+30 | > 30 | Mensuel |
| Temps résolution bug critique | Incident log | < 24h | Par incident |
| Drift alert count (Brier 7j vs 30j) | `drift_detector.py` | 0 alert non résolue > 48h | Quotidien |
| `ml_fallback_used` rate NHL | logs | < 10% | Quotidien |
| Quota API-Football / Odds API consumption | logs | < 80% plan | Quotidien |
| CLV vs Pinnacle (foot, quand dispo) | `backtest_clv.py` | > +2% | Hebdo |

---

## 8. Dépendances inter-domaines (graph)

Chaîne critique pivot :
```
P0-1/2/3 (fix bugs ML)  →  P0-11 (walk-forward)  →  P0-22 (page méthodologie publique)
        ↓                          ↓
P0-4 (monitoring cron)  →  model_health_log  →  Gate Phase 2 pivot quantitatif
        ↓                          ↓
Phase 1 pivot (générateurs)  →  Phase 2 observation silencieuse  →  Go/No-Go chiffré  →  Phase 3 UI
```

Chaîne critique produit :
```
P0-9 (Plausible)  →  P1-35 (dashboard KPI)  →  P2-22 (A/B testing)
P0-12 (posture A/B/C)  →  P1-32 (checkout serveur)  →  P1-33 (annuel 119€)  →  offres segmentées
```

Chaîne critique NHL :
```
P0-10 (décision budget Odds Pro)  →  P1-13 (upgrade Odds API)  →  P1-15 (dataset 2×)  →  P1-16 (per-player calibration)
P0-5 (fix fallback silencieux)  →  P1-14 (tests NHL 50%)  →  Safe/Fun NHL fiabilisés
```

Chaîne critique confiance (transparence radicale L5) :
```
P0-1/2/3 (bugs ML)  →  P0-11 (walk-forward)  →  P1-10 (model versioning)  →  P2-24 (leaderboard public)
P0-4 (monitoring)  →  P1-12 (dashboard model-health)  →  P2-27 (ablation study publiée)
```

Blocages majeurs à surveiller :
- **Sans P0-4 (monitoring en cron + model_health_log), la Phase 2 pivot est inopérante** — gate purement qualitatif, décision à l'intuition.
- **Sans P0-1/2/3 (fix bugs ML), la page /methodology expose des probas biaisées** — transparence radicale se retourne contre ProbaLab.
- **Sans P0-9 (Plausible), le pivot est livré aveugle** — impossible de mesurer si Safe/Fun/Value convertit.
- **Sans P0-10 (décision Odds API Pro), le scope NHL est flottant** — risque "mode dégradé silencieux" (cotes implicites pour `player_points`).
- **Sans P0-12 (BP vs pivot tranché), les partenaires/investisseurs lisent deux produits différents**.

---

## 9. Ce qui ne va PAS dans la roadmap (assumptions explicites)

1. **Budget Odds API Pro (~500$/mois NHL) : hypothèse OK**. Si non validé, l'annexe 04 impose un scope Safe NHL restreint à `player_goals`. Conséquence : tout le volet "NHL L4 pilote en H2" disparaît, et le différenciateur §5.4 (NHL européen avec xG + EV + mobile) devient inatteignable sans partenariat data.

2. **Effort pivot : 13-20j du design doc doublé par les prérequis P0**. L'annexe 11 conclut explicitement "5-8 semaines au total" (13-20j dev + 15-20j prérequis). La roadmap H1 est construite sur cette base — si l'owner veut tenir "13-20j" sans prérequis, il accepte les risques R10-R18 listés dans l'annexe 11 (bugs ML exposés, monitoring aveugle, pas d'analytics, scope NHL non résolu, prix non aligné, etc.).

3. **Analytics produit : 1j Plausible OU 3j PostHog**. La BP originale n'a pas budgété les ~3-5j nécessaires pour instrumenter 20+ événements produit (funnel complet, feature adoption, session recording équivalent). Si seul le funnel core est installé en H1, les KPIs avancés (Time-to-first-value, feature adoption par segment, churn driver) attendent H2-H3.

4. **Capacité solopreneur**. Avec une cadence ~5h/semaine citée dans les annexes, H1 (22 items P0, 22-28j dev) prend **en réalité 11-14 semaines calendaires, pas 4**. La roadmap "4 semaines" suppose un effort ~40h/semaine pendant H1. À défaut, découper : H1a (semaines 1-2, bugs ML + sécu P0) et H1b (semaines 3-6, infra + analytics + UI P0). Communiquer le vrai rythme à l'owner.

5. **L'ambition "meilleure app du marché"** reste non écrite dans le BP (annexe 09 P3). Tant que la posture (A/B/C annexe 09 §7) n'est pas tranchée, "meilleure" au sens grand public (SofaScore-level) est hors d'atteinte, et "meilleure" au sens francophone spécialiste reste atteignable en 12-18 mois. La roadmap H3 parie sur cette seconde lecture.

6. **Dépendance Gemini (analyses narratives IA)** non traitée dans les annexes côté coût/quota/latence. Si l'explainability narrative (zone blanche §5.2, cœur de L5 en H3) dépend de Gemini, il faut tracker le coût par pick et prévoir un fallback local (e.g. features SHAP sans narratif).

7. **Tests UI + e2e (P1-24, P1-27)** pèsent 10-15j cumulés mais ne figurent dans aucune baseline chiffrée avant la roadmap. Ce budget est un ajout net, pas une ré-allocation.

8. **Les zones blanches §5 annexe 10 sont identifiées mais non validées marché**. L'hypothèse "transparence radicale + explainability + éducation = 3 dimensions L5 défendables" repose sur l'absence actuelle des concurrents, pas sur une demande explicite des utilisateurs. P1-38 (user research 8-10 interviews) sert justement à valider — si les interviews montrent que les utilisateurs s'en fichent, la stratégie H3 doit pivoter.

---

*Fin annexe 12. Roadmap synthèse, alimentée par les §5 P0/P1/P2 des annexes 01-11.*
