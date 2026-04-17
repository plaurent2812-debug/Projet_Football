# Plan d'Actions Correctives — ProbaLab

> Source : `01_PROBALAB_actions_correctives.md` (audit du 2026-04-10)
> Exécution étape par étape dans l'ordre de priorité P0 → P1 → P2.

## ACTION REQUISE OWNER — Migration SQL à appliquer manuellement

**Task B1 (2026-04-17)** — La migration `050_model_health_log.sql` a été créée mais n'a pas pu être appliquée automatiquement (pas de psql local, MCP non accessible, Management API requiert un token différent).

**À faire via Supabase Studio** (https://supabase.com/dashboard/project/yskpqdnidxojoclmqcxn/editor) :

```sql
create table if not exists model_health_log (
    id bigserial primary key,
    recorded_at timestamptz not null default now(),
    sport text not null check (sport in ('football','nhl')),
    brier_7d numeric,
    brier_30d numeric,
    log_loss_30d numeric,
    ece_30d numeric,
    clv_best_mean_30d numeric,
    drift_detected boolean default false,
    data_completeness_pct numeric,
    prediction_volume_today integer,
    alert_count integer default 0,
    ml_fallback_rate numeric,
    notes text
);

create index if not exists idx_model_health_log_recorded_at
    on model_health_log(recorded_at desc);
create index if not exists idx_model_health_log_sport_date
    on model_health_log(sport, recorded_at desc);

alter table model_health_log enable row level security;

create policy "service_role_all_model_health_log"
    on model_health_log for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
```

Après application : les tests `pytest tests/test_model_health_log.py -m integration -v` doivent passer en PASS.

---

## État de départ (constaté après exploration)

Beaucoup d'éléments cités dans l'audit existent déjà dans le code :

- Monitoring ML : `src/monitoring/` contient `brier_monitor.py`, `alerting.py`, `drift_detector.py`, `data_quality.py`, `feature_audit.py`
- Sécurité : `SecurityHeadersMiddleware` actif, `hmac.compare_digest` sur CRON_SECRET, `api/schemas.py` avec 7 modèles Pydantic, `api/rate_limit.py` avec slowapi
- Dette tech : `api/main.py` découpé (225 lignes), routeurs séparés dans `api/routers/`, `best_bets.py` = 1635 lignes (pas 69KB comme dans l'audit)
- Tests : 381 tests dans `tests/`, CI avec `--cov-fail-under=40`

Le plan ci-dessous cible ce qui manque réellement, pas ce qui existe déjà.

---

## PHASE 0 — Préparation (30 min)

- [ ] 0.1 Nettoyer les fichiers de test temporaires à la racine
  - Supprimer : `test_keys.py`, `test_perf.py`, `test_perf2.py`, `test_perf3.py`, `=2.0.0`, `.DS_Store`
  - Supprimer à la racine repo : `probalab_pivot.py`, `BP_ProbaLab_v2.pdf`, `CLAUDE-CODE-COMMANDS.md` (vérifier avant)
- [ ] 0.2 Lancer la suite de tests actuelle pour mesurer baseline
  - `pytest tests/ -m "not integration" --cov=src --cov=api --cov-report=term-missing -q`
  - Noter : nb tests, % couverture global, % couverture `best_bets.py`, `trigger.py`, `brain.py`
- [ ] 0.3 Créer une branche de travail `chore/audit-2026-04-10`
- [ ] 0.4 Commit 0 — nettoyage + baseline

---

## PHASE 1 — Action 1 — Tests chemins critiques (P0, 3-5j)

**Objectif :** couverture > 60% global, > 80% sur `best_bets` + blending. Aucun path de résolution de pari sans test.

### 1.1 — Identifier les chemins critiques non couverts (1h)
- [ ] Générer rapport couverture par fichier : `pytest --cov=api.routers.best_bets --cov=api.routers.trigger --cov=src.brain --cov=src.prediction_blender --cov=src.bankroll --cov-report=term-missing`
- [ ] Lister dans `tasks/coverage_gaps.md` :
  - Fonctions non couvertes dans `best_bets.py` (résolution WON/LOST, calcul ROI, Kelly)
  - Fonctions non couvertes dans `trigger.py` (orchestration jobs)
  - Fonctions non couvertes dans `prediction_blender.py` (70/30 blending)
  - Fonctions non couvertes dans `bankroll.py`

### 1.2 — Tests résolution paris (best_bets) (6-8h)
- [ ] Créer `tests/test_best_bets_resolution.py` avec fixtures réalistes
  - Test WIN simple (odds 2.0, 100€ stake → +100€)
  - Test LOSS simple (odds 2.0, 100€ stake → -100€)
  - Test VOID (remboursé)
  - Test PENDING (fixture pas encore terminée)
  - Test combo 3 legs WIN
  - Test combo 3 legs dont 1 LOSS → LOSS global
  - Test combo avec VOID (leg annulé → odds recalculées sur legs restants)
  - Test résolution AET/PEN (cf leçon 2026-04-02)
- [ ] Chaque test : `# Arrange / # Act / # Assert` explicites
- [ ] Exécuter en isolé pour vérifier chaque fail → pass

### 1.3 — Tests Kelly Criterion + ROI + bankroll (4h)
- [ ] Créer `tests/test_bankroll_kelly.py`
  - Test calcul Kelly fractionnel (edge 5%, odds 2.1, proba 50%)
  - Test Kelly plafonné à 5% de bankroll
  - Test ROI cumulé sur 10 paris mixés WIN/LOSS
  - Test drawdown max
  - Test edge case : edge ≤ 0 → stake = 0

### 1.4 — Tests blending 70/30 (2-3h)
- [ ] Créer `tests/test_prediction_blender.py`
  - Test blend 70% stats + 30% ML avec probas identiques → résultat identique
  - Test blend quand ML manquant → fallback 100% stats
  - Test blend quand stats manquants → erreur explicite
  - Test somme probas toujours = 100 (cf leçon 2026-03-19)

### 1.5 — Test end-to-end pipeline (4-6h)
- [ ] Créer `tests/test_pipeline_e2e.py` (marqué `@pytest.mark.integration`)
  - Mock minimal : seed `fixtures` + `predictions` + `best_bets` en mémoire
  - Exécuter : fetch → predict → resolve → ROI
  - Vérifier : `prediction_results` contient la bonne actual_result
  - Vérifier : `best_bets.result` = WIN/LOSS correct
  - Vérifier : ROI cumulé calculable

### 1.6 — Remplacer MockSupabase par schema de test (optionnel, 6h)
- [ ] Évaluer : vaut le coût vs bénéfice
- [ ] Si oui : setup Supabase local via Docker, fixture conftest qui démarre/arrête
- [ ] Sinon : améliorer les mocks existants pour être plus réalistes

### 1.7 — Monter le seuil CI (30 min)
- [ ] Vérifier que la couverture globale passe 60% en local
- [ ] Modifier `.github/workflows/ci.yml` : `--cov-fail-under=60`
- [ ] Commit + push, vérifier CI verte

### 1.8 — Commits par sous-section
- Commit 1 : `test: add best_bets resolution test suite`
- Commit 2 : `test: add Kelly + bankroll coverage`
- Commit 3 : `test: add blending layer tests`
- Commit 4 : `test: add e2e pipeline integration test`
- Commit 5 : `ci: raise coverage threshold to 60%`

---

## PHASE 2 — Action 2 — Monitoring ML en production (P0, 5-8j)

**Objectif :** détecter dégradation modèles dans les 24h, dashboard admin fonctionnel.

### 2.1 — Auditer l'existant (1h)
- [ ] Lire en détail `src/monitoring/brier_monitor.py`, `alerting.py`, `drift_detector.py`, `feature_audit.py`
- [ ] Vérifier dans `api/routers/trigger.py` si un job cron lance déjà ces checks
- [ ] Identifier : quoi est déjà lancé automatiquement, quoi ne l'est pas

### 2.2 — Pipeline monitoring quotidien (4-6h)
- [ ] Vérifier/créer un job quotidien qui appelle `check_and_alert()` + `check_drift()`
  - Via `api/routers/trigger.py` (endpoint protégé CRON_SECRET)
  - Ou via `run_pipeline.py` en fin de pipeline
- [ ] Logger résultat dans table `model_health_log` (créer si absente)
- [ ] Vérifier alerte Telegram part bien si seuil dépassé (test manuel en forçant un Brier élevé)

### 2.3 — Feature drift avec KS test (4-6h)
- [ ] Étendre `src/monitoring/drift_detector.py` avec nouvelle fonction `check_feature_drift()`
- [ ] Pour chaque feature numérique utilisée par XGBoost :
  - Calculer distribution training (depuis le dataset d'entraînement sauvegardé)
  - Calculer distribution production (derniers 30j de `predictions`)
  - Kolmogorov-Smirnov test (scipy.stats.ks_2samp)
  - Flag feature driftée si p-value < 0.01
- [ ] Alerte si > 3 features driftent simultanément
- [ ] Test unitaire avec distributions synthétiques

### 2.4 — Table prediction_audit_log (2-3h)
- [ ] Vérifier si `prediction_results` suffit déjà (lecture rapide schema)
- [ ] Si besoin : créer migration `prediction_audit_log` (prediction_id, market, proba, odds, actual, timestamp)
- [ ] Requête RPC calibration glissante par marché
- [ ] Sinon : utiliser `prediction_results` existant et créer les vues/RPC nécessaires

### 2.5 — Dashboard admin `/admin/model-health` (6-8h)
- [ ] Backend : endpoint `GET /api/admin/model-health` (auth admin)
  - Retourne : brier_7d, brier_30d, drift_status, feature_drift_list, volume_today
  - Graphique temporel : brier score par jour sur 90j
- [ ] Frontend : nouvelle page `dashboard/src/pages/Admin.tsx` étendue ou nouvelle section
  - KPI cards (Brier 7j, 30j, status)
  - Graphique Recharts : Brier score timeline
  - Tableau features driftées
  - Bouton "Relancer les checks"

### 2.6 — Model versioning + rollback (4-6h)
- [ ] Dans `src/training/train.py` : après training, sauver `.pkl` avec hash + timestamp dans Supabase Storage
- [ ] Avant de promouvoir un modèle : backtest sur 48h de données récentes
- [ ] Si nouveau Brier > ancien Brier : SKIP l'upsert (cf leçon 2026-04-03)
- [ ] Si déployé et sous-performe sur 48h : rollback automatique vers version précédente
- [ ] Endpoint admin `POST /api/admin/rollback-model` pour rollback manuel

### 2.7 — Commits
- Commit 1 : `feat(monitoring): activate daily monitoring pipeline`
- Commit 2 : `feat(monitoring): add feature drift detection (KS test)`
- Commit 3 : `feat(monitoring): admin model-health dashboard endpoint`
- Commit 4 : `feat(monitoring): admin dashboard UI`
- Commit 5 : `feat(training): model versioning + automatic rollback`

---

## PHASE 3 — Action 4 — Sécurité API (P1, 2-3j)

**Objectif :** 0 endpoint POST sans Pydantic strict, rate limiting différencié.

### 3.1 — Audit endpoints publics (1h)
- [ ] Grep tous les `@router.post`, `@router.delete`, `@router.put` dans `api/routers/`
- [ ] Lister dans `tasks/endpoints_audit.md` : chemin, auth, Pydantic model, rate_limit
- [ ] Identifier les gaps

### 3.2 — Pydantic strict `extra="forbid"` (2-3h)
- [ ] Modifier `api/schemas.py` : ajouter `model_config = ConfigDict(extra="forbid")` sur TOUS les modèles
- [ ] Lancer la suite de tests → corriger les tests qui passent des champs extras
- [ ] Ajouter les modèles Pydantic manquants identifiés en 3.1

### 3.3 — Rate limiting différencié (4-6h)
- [ ] Étendre `src/constants.py` :
  ```python
  RATE_LIMIT_FREE = "30/minute;500/day"
  RATE_LIMIT_PREMIUM = "120/minute;5000/day"
  RATE_LIMIT_ADMIN = "1000/minute"
  ```
- [ ] Modifier `api/rate_limit.py` : key_func custom qui lit le JWT et retourne (ip, tier)
- [ ] Décorateur `_rate_limit_tiered()` qui applique la limite en fonction du tier utilisateur
- [ ] Appliquer sur les endpoints utilisateur (predictions, best-bets, performance)
- [ ] Test : envoyer 31 requêtes en 1 minute avec JWT free → 429
- [ ] Test : envoyer 31 requêtes en 1 minute avec JWT premium → OK

### 3.4 — Rotation CRON_SECRET (2-3h)
- [ ] Modifier `api/auth.py` : supporter 2 secrets simultanément (`CRON_SECRET` et `CRON_SECRET_PREV`)
- [ ] `verify_cron_auth` accepte les deux pendant la période de rotation
- [ ] Documenter la procédure dans `tasks/runbook_secret_rotation.md`
  - Étape 1 : définir CRON_SECRET_NEW dans Railway
  - Étape 2 : déployer (les 2 secrets acceptés)
  - Étape 3 : mettre à jour les appelants (Trigger.dev, GitHub Actions)
  - Étape 4 : retirer l'ancien secret

### 3.5 — Audit GET sans auth (1h)
- [ ] Lister tous les `@router.get` sans `verify_internal_auth` ou `Depends(current_user)`
- [ ] Pour chacun : vérifier qu'il n'expose pas d'emails, user_id internes, config
- [ ] Corriger les fuites

### 3.6 — Commits
- Commit 1 : `security: Pydantic strict extra=forbid on all schemas`
- Commit 2 : `security: tiered rate limiting (free/premium/admin)`
- Commit 3 : `security: CRON_SECRET rotation support`
- Commit 4 : `security: audit + fix public GET endpoints`

---

## PHASE 4 — Action 5 — Dette technique Python (P1, 2-3j)

**Objectif :** structure de code cohérente, fichiers focus.

### 4.1 — Vérifier l'état réel (déjà partiellement fait) (30 min)
- [ ] `wc -l api/routers/*.py src/*.py`
- [ ] Identifier les fichiers > 500 LOC qui méritent vraiment un split
- [ ] NOTE : `api/main.py` est déjà à 225 lignes (bon), `best_bets.py` à 1635 (à split), `trigger.py` à 1687 (à split)

### 4.2 — Découper `api/routers/best_bets.py` (6-8h)
- [ ] Analyser les sections actuelles du fichier
- [ ] Créer nouveau package `api/routers/best_bets/`
  - `__init__.py` (exporte le router)
  - `router.py` — endpoints FastAPI
  - `resolver.py` — logique résolution WIN/LOSS/VOID
  - `calculator.py` — ROI, Kelly, bankroll P&L
  - `formatter.py` — formatage Telegram/Discord
- [ ] Migrer le code en préservant les imports publics
- [ ] Lancer les tests après chaque sous-découpe (tests Phase 1 garantissent le filet)
- [ ] Aucun fichier résultant > 500 LOC

### 4.3 — Découper `api/routers/trigger.py` (6-8h)
- [ ] Mêmes principes : package `api/routers/trigger/`
  - `router.py` — endpoints /run, /pipeline, /results, /nhl
  - `pipeline_job.py` — orchestration pipeline ML
  - `results_job.py` — résolution paris
  - `live_job.py` — live scores
  - `nhl_job.py` — jobs spécifiques NHL

### 4.4 — Standardiser les tests (1h)
- [ ] Vérifier : tous les tests sont dans `tests/`, miroir de la structure `src/` et `api/`
- [ ] Déplacer les tests orphelins
- [ ] Supprimer `tests/scratch_*.py` s'ils ne servent pas

### 4.5 — Imports circulaires (1-2h)
- [ ] `python -m pyflakes src/ api/` pour détecter
- [ ] Corriger les imports circulaires détectés (souvent : extraire des constantes dans un module pur)

### 4.6 — Commits
- Commit 1 : `refactor(best_bets): split into package (router/resolver/calculator/formatter)`
- Commit 2 : `refactor(trigger): split into package by job type`
- Commit 3 : `chore: standardize tests/ structure`
- Commit 4 : `refactor: remove circular imports`

---

## PHASE 5 — Action 3 — Frontend enrichi (P2, 10-15j)

**Objectif :** dashboards interactifs, PWA, mode sombre, Lighthouse > 90.

### 5.1 — Mode sombre (4-6h)
- [ ] Ajouter `darkMode: 'class'` dans `tailwind.config.js`
- [ ] Créer hook `useDarkMode()` avec persistence localStorage
- [ ] Ajouter toggle dans le header
- [ ] Passer sur tous les composants principaux : ajouter classes `dark:` là où nécessaire
- [ ] Vérifier sur les pages : Home, Dashboard, Performance, ParisDuSoir, MatchDetail

### 5.2 — Dashboard predictions enrichi (1-2j)
- [ ] Vue par ligue : filtres forme / cote / confiance (composant réutilisable `PredictionsFilterBar`)
- [ ] Graphique calibration interactif sur `Performance.tsx` : predicted vs actual par bucket de 10%
- [ ] Courbes ROI par marché (1X2, BTTS, O/U) avec Recharts LineChart

### 5.3 — Composants manquants (1-2j)
- [ ] Bankroll tracker visuel : courbe P&L + drawdown max (nouvelle page `/bankroll`)
- [ ] Live match widget avec momentum indicator (sur `MatchDetail.tsx`)
- [ ] Comparateur de picks user vs algo (optionnel P2)

### 5.4 — PWA (1j)
- [ ] Ajouter `vite-plugin-pwa`
- [ ] Service worker : cache stratégie stale-while-revalidate pour les routes data
- [ ] Manifest : icônes, nom, theme color
- [ ] Test installation mobile

### 5.5 — Notifications push (1-2j)
- [ ] Frontend : bouton "Activer les notifications" dans le profil
- [ ] Appeler `/api/push/subscribe` avec la souscription
- [ ] Backend : vérifier que `pywebpush` est bien configuré (déjà présent d'après l'audit)
- [ ] Job quotidien qui envoie les value bets 1h avant les matchs
- [ ] Test : activer sur un device, recevoir une notif

### 5.6 — Optimisation Lighthouse (1j)
- [ ] Lancer audit actuel : `npm run build && npx lighthouse <url>`
- [ ] Identifier les gaps Performance
- [ ] Lazy-load les routes via `React.lazy`
- [ ] Compression images, preload fonts
- [ ] Objectif : > 90 Performance + > 95 Accessibility

### 5.7 — Commits
- Commit 1 : `feat(ui): dark mode support`
- Commit 2 : `feat(ui): enriched performance dashboard with calibration + ROI charts`
- Commit 3 : `feat(ui): bankroll tracker page`
- Commit 4 : `feat(pwa): installable app with service worker`
- Commit 5 : `feat(push): web push notifications for pre-match value bets`
- Commit 6 : `perf: lighthouse optimizations`

---

## VÉRIFICATION FINALE

- [ ] Suite de tests verte (`pytest tests/ -m "not integration"`)
- [ ] Couverture ≥ 60% global, ≥ 80% sur `best_bets` et `prediction_blender`
- [ ] CI GitHub Actions verte
- [ ] Monitoring ML : alerte reçue en test manuel en < 24h
- [ ] Dashboard admin accessible avec KPI
- [ ] 0 endpoint POST sans Pydantic strict
- [ ] Rate limiting testé par tier
- [ ] Aucun fichier routeur > 500 LOC
- [ ] PWA installable, push notifications fonctionnelles
- [ ] Lighthouse Performance > 90

---

## NOTES D'EXÉCUTION

- On attaque dans l'ordre : **Phase 0 → 1 → 2 → 3 → 4 → 5**
- Validation user entre chaque phase (au moins les P0)
- Chaque phase : tests verts + commit avant passage à la suivante
- Mise à jour `tasks/lessons.md` après toute erreur rencontrée
- Si un bug imprévu bloque une phase : STOP, diagnostic, lessons, re-planifier
