# Audit 360° ProbaLab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produire un audit 360° stratégique de ProbaLab sur 9 domaines + benchmark concurrentiel + évaluation du pivot en cours + roadmap pour devenir la meilleure app de prédiction sportive du marché (foot + NHL). Livrable = 12 documents markdown dans `docs/audit/2026-04-17/`.

**Architecture:** Investigation en lecture seule (aucune modification de code). Utilisation massive de Read/Grep/Glob pour le code, WebFetch/WebSearch pour le benchmark, Supabase MCP pour la DB. Rédaction suivant template uniforme (L1-L5 scoring + gap vs leader + P0/P1/P2 gaps). Livraison en 3 batches avec points d'arrêt pour feedback owner.

**Tech Stack:** Outils Claude Code (Read, Grep, Glob, WebFetch, WebSearch, Bash pour git). Pas de code à exécuter dans l'app. Spec source : `docs/superpowers/specs/2026-04-17-audit-360-probalab-design.md`.

---

## File Structure

### Livrables (tous dans `docs/audit/2026-04-17/`)

| Fichier | Responsabilité | Longueur visée |
|---|---|---|
| `00_EXECUTIVE_SUMMARY.md` | Décideur : verdict, scoring, top forces/faiblesses, quick wins, pivot, roadmap, KPIs | 8-10 pages |
| `01_moteur_probabilites.md` | Poisson/Dixon-Coles, ELO, features, continuité rho, masse capturée | 5-8 pages |
| `02_machine_learning.md` | XGBoost, calibration isotonique, blending 70/30, meta-learner, data leakage | 5-8 pages |
| `03_monitoring_ml.md` | Brier, drift KS, calibration prod, dashboard admin, alerting | 4-6 pages |
| `04_nhl_specifique.md` | Player props, fetchers, team normalization, schedule fallback, ML blend | 5-7 pages |
| `05_architecture_backend.md` | FastAPI, routers, pipelines, APScheduler, fichiers > 500 LOC | 4-6 pages |
| `06_securite.md` | RLS, auth, rate limit, secrets, Pydantic, webhooks, security headers | 4-6 pages |
| `07_ui_ux_frontend.md` | React, navigation, mobile, a11y, dark mode, Lighthouse | 5-8 pages |
| `08_tests_cicd.md` | Couverture, qualité, CI GitHub, Railway deploy, tests E2E | 3-5 pages |
| `09_produit_positionnement.md` | BP, value prop, monétisation Stripe, funnel, analytics | 4-6 pages |
| `10_benchmark_concurrentiel.md` | Forebet, Infogol, PredictZ, RebelBetting, Pinnacle, SofaScore, OneFootball, Action Network, MoneyPuck | 6-10 pages |
| `11_evaluation_pivot.md` | Verdict GO/GO-amendé/PAUSE/STOP sur le pivot en cours | 3-5 pages |
| `12_roadmap_meilleure_app.md` | Cartographie gaps P0/P1/P2 cross-domaines + 3 horizons | 4-6 pages |

### Fichiers d'investigation (notes temporaires, pas livrables finaux)

- `.audit-notes/` (gitignored, pour brouillons d'investigation si nécessaire)

---

## Convention de workflow

- Chaque batch = 1 branche de travail (déjà sur `feat/pivot-probas-sportives`, on reste dessus)
- Chaque annexe terminée = 1 commit dédié
- Messages de commit : `docs(audit): add [nom du document]`
- Aucune modification du code applicatif (audit = lecture seule stricte)
- Point d'arrêt après chaque batch pour feedback owner

---

## BATCH 1 — Cœur métier (domaines 1-4)

### Task 0 : Préparation du répertoire d'audit

**Files:**
- Create: `docs/audit/2026-04-17/README.md`
- Modify: `.gitignore` (ajouter `.audit-notes/`)

- [ ] **Step 1 : Créer le répertoire d'audit**

```bash
mkdir -p "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/docs/audit/2026-04-17"
```

- [ ] **Step 2 : Créer le README du répertoire**

Contenu de `docs/audit/2026-04-17/README.md` :

```markdown
# Audit 360° ProbaLab — 2026-04-17

Spec source : `docs/superpowers/specs/2026-04-17-audit-360-probalab-design.md`
Plan source : `docs/superpowers/plans/2026-04-17-audit-360-probalab.md`

## Ordre de lecture recommandé

1. `00_EXECUTIVE_SUMMARY.md` — lecture standalone, 15-20 min
2. Annexes `01` à `09` — approfondissement par domaine
3. `10_benchmark_concurrentiel.md` — comparaison marché
4. `11_evaluation_pivot.md` — verdict pivot en cours
5. `12_roadmap_meilleure_app.md` — backlog priorisé

## Échelle de maturité

- **L1** : MVP fragile
- **L2** : Fonctionnel
- **L3** : Solide (niveau commercial sérieux)
- **L4** : Best-in-class
- **L5** : État de l'art / différenciateur
```

- [ ] **Step 3 : Vérifier que .gitignore contient `.audit-notes/`**

```bash
grep -q "^\.audit-notes/" .gitignore || echo ".audit-notes/" >> .gitignore
```

- [ ] **Step 4 : Commit préparation**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/README.md .gitignore
git commit -m "docs(audit): scaffold audit 2026-04-17 directory"
```

---

### Task 1 : Annexe 01 — Moteur de probabilités

**Files:**
- Create: `docs/audit/2026-04-17/01_moteur_probabilites.md`
- Read for investigation : `ProbaLab/src/brain.py`, `ProbaLab/src/prediction_blender.py`, `ProbaLab/src/Projet_Football/` (features foot), `ProbaLab/src/nhl/feature_engineering.py`

- [ ] **Step 1 : Inspection `brain.py`**

Lire intégralement `ProbaLab/src/brain.py`. Noter :
- Type de modèle probabiliste (Poisson / Dixon-Coles / Bivarié ?)
- Gestion rho scaling (cf leçon 1 : continuité aux bornes)
- MAX_GOALS_GRID utilisé (cf leçon 3 : ≥99% masse)
- Normalisation sum=100 (cf leçon 2)
- Boost euro/CL éventuel (cf leçon 4 : pas de double comptage)

- [ ] **Step 2 : Inspection `prediction_blender.py`**

Lire intégralement. Noter :
- Blending 70/30 stats/ML documenté dans CLAUDE.md
- Gestion des cas ML manquant
- Round-à-chaque-étape (cf leçon 53 : garder précision float)

- [ ] **Step 3 : Inspection features foot**

```bash
ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/src/Projet_Football"
```

Lire les fichiers identifiés. Noter :
- Liste des 50+ features déclarées dans CLAUDE.md
- ELO : formule, initialisation, K-factor
- Forme récente : fenêtre, pondération
- Home advantage : fixe ou calibré par ligue

- [ ] **Step 4 : Inspection features NHL**

Lire `ProbaLab/src/nhl/feature_engineering.py` et `ProbaLab/src/nhl/build_data.py`. Noter :
- Features spécifiques NHL (xG, shots on goal, Corsi, Fenwick ?)
- Features player props (points, assists, goals par joueur)
- Séparation data leakage (leçon 12 : fit après split)

- [ ] **Step 5 : Grep des bugs connus non résolus**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab"
```

Rechercher :
- `rho_scaling` — vérifier continuité
- `MAX_GOALS_GRID` — valeur actuelle
- `sum.*100` ou normalisation
- `euro_boost` — présent ou retiré
- `round(` dans les pipelines de probas

- [ ] **Step 6 : Rédaction annexe 01**

Créer `docs/audit/2026-04-17/01_moteur_probabilites.md` selon le template spec §6 :

Sections :
1. Périmètre audité (fichiers lus, lignes)
2. État actuel (fonctionnel, dette, code smells, gaps industrie)
3. Niveau de maturité Lx/L5 + justification
4. Benchmark vs leader (Infogol xG probablement)
5. Gaps P0/P1/P2
6. Risques identifiés
7. Recommandations stratégiques
8. Liens internes

Références obligatoires : leçons 1-7, 49-53 (ajouter `tasks/lessons.md:N`).

- [ ] **Step 7 : Auto-review annexe 01**

Relire le document. Vérifier :
- Aucun "TBD", "TODO", "à compléter"
- Chaque affirmation a une source `fichier:ligne` ou `leçon N`
- Scoring Lx justifié en 2-5 phrases
- Gaps P0/P1/P2 présents et distincts
- Benchmark concret (pas "probablement comparable à")

- [ ] **Step 8 : Commit annexe 01**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/01_moteur_probabilites.md
git commit -m "docs(audit): add 01_moteur_probabilites annex"
```

---

### Task 2 : Annexe 02 — Machine Learning

**Files:**
- Create: `docs/audit/2026-04-17/02_machine_learning.md`
- Read for investigation : `ProbaLab/src/training/train.py`, `ProbaLab/src/training/train_meta.py`, `ProbaLab/src/nhl/ml_models.py`, `ProbaLab/src/nhl/nhl_ml_predictor.py`, `ProbaLab/src/nhl/train.py`, `ProbaLab/src/nhl/train_match.py`

- [ ] **Step 1 : Inspection pipeline training foot**

Lire `ProbaLab/src/training/train.py` et `train_meta.py`. Noter :
- Modèle principal : XGBoost / LightGBM / ensemble ?
- TimeSeriesSplit présent (leçon 12 : pas de data leakage)
- sample_weight appliqué (leçon 9 : sur tous les models)
- eval_set distinct du test (leçon 10)
- Calibration isotonique post-training (leçon 50)
- Upsert conditionnel sur Brier (leçon 40 : skip si pire)

- [ ] **Step 2 : Inspection NHL ML**

Lire `ProbaLab/src/nhl/ml_models.py`, `nhl_ml_predictor.py`, `src/nhl/train.py`, `train_match.py`. Noter :
- Modèle NHL : même stack ou différente ?
- Bug `KeyError: 'model'` documenté dans design pivot R8/R9 — résolu ou pas ?
- Player props models (point, assist, goal) séparés ou unifiés ?

- [ ] **Step 3 : Inspection blending**

Relire `ProbaLab/src/prediction_blender.py` avec angle ML. Noter :
- WEIGHT_AI et feature flag META_LEARNER_ENABLED (leçon 35)
- Poids signal bookmaker vs Poisson vs ELO (leçon 52)

- [ ] **Step 4 : Vérification meta-dataset**

```bash
ls -la "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/meta_dataset.csv"
ls -la "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/nhl_dataset.csv"
```

Noter dates de dernière modification, taille, cohérence avec la date du jour.

- [ ] **Step 5 : Inspection modèles stockés**

Lister les artefacts modèles :

```bash
ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/models" 2>/dev/null
find "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab" -name "*.pkl" -o -name "*.ubj" 2>/dev/null | head -20
```

Noter :
- Versioning (hash + timestamp ?) — cf audit todo.md 2.6
- Rollback possible ?

- [ ] **Step 6 : Grep data leakage patterns**

Chercher `fit_transform` avant split TimeSeries :

Grep `fit_transform` dans `src/training/` et `src/nhl/`. Pour chaque occurrence, vérifier si c'est avant ou après le split train/test.

- [ ] **Step 7 : Rédaction annexe 02**

Créer `docs/audit/2026-04-17/02_machine_learning.md` selon template. Cibler benchmark vs RebelBetting (calibration Brier industrielle), citer leçons 9, 10, 12, 13, 35, 40, 49, 50, 52.

- [ ] **Step 8 : Auto-review et commit**

Vérifier absence de placeholders. Commit :

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/02_machine_learning.md
git commit -m "docs(audit): add 02_machine_learning annex"
```

---

### Task 3 : Annexe 03 — Monitoring ML

**Files:**
- Create: `docs/audit/2026-04-17/03_monitoring_ml.md`
- Read for investigation : `ProbaLab/src/monitoring/brier_monitor.py`, `alerting.py`, `drift_detector.py`, `data_quality.py`, `feature_audit.py`, `backtest_clv.py`

- [ ] **Step 1 : Inspection modules monitoring**

Lire les 6 fichiers `src/monitoring/`. Pour chacun, noter :
- Fonctions publiques exposées
- Seuils configurés (Brier threshold, p-value KS)
- Intégration avec alerting (Telegram ? Discord ?)

- [ ] **Step 2 : Vérifier branchement cron**

Lire `ProbaLab/worker.py` (APScheduler jobs). Chercher :
- Job qui appelle `check_and_alert()` ou équivalent — présent ou absent ?
- Job drift detection — actif ?
- Fréquence (quotidien / horaire / manuel) ?

Également grep dans `api/routers/trigger.py` (1687 LOC) les endpoints monitoring.

- [ ] **Step 3 : Vérifier dashboard admin model-health**

Rechercher dans `dashboard/src/pages/` une page `Admin.tsx` ou `ModelHealth.tsx`. Lire si présente.

Grep dans `api/routers/admin.py` et `monitoring.py` les endpoints `/admin/model-health`.

- [ ] **Step 4 : Vérifier KS test feature drift**

Grep `ks_2samp` ou `kolmogorov` dans `src/monitoring/`. Présent ou absent ?

- [ ] **Step 5 : Inspection table prediction_audit_log**

Via Supabase MCP, lister les tables et chercher `prediction_audit_log` ou équivalent :

```
mcp__33041561-7557-41b0-8f41-9ddec0a459f0__list_tables
```

Noter si la table existe et son schéma.

- [ ] **Step 6 : Rédaction annexe 03**

Créer `docs/audit/2026-04-17/03_monitoring_ml.md`. Cibler benchmark vs systèmes MLOps industriels (Evidently AI, Arize, WhyLabs pour la conceptualisation — même si les concurrents ProbaLab ne sont pas ces outils, le standard vient de là).

Gaps P0 typiques attendus : pipeline monitoring non automatisé, dashboard admin absent, KS test drift manquant — à confirmer factuellement.

- [ ] **Step 7 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/03_monitoring_ml.md
git commit -m "docs(audit): add 03_monitoring_ml annex"
```

---

### Task 4 : Annexe 04 — NHL spécifique

**Files:**
- Create: `docs/audit/2026-04-17/04_nhl_specifique.md`
- Read for investigation : `ProbaLab/src/nhl/*.py` (tous), `ProbaLab/api/routers/nhl.py`, `ProbaLab/src/fetchers/fetch_nhl_player_props.py`, `ProbaLab/src/nhl/fetch_odds.py`

- [ ] **Step 1 : Inspection pipeline NHL complet**

Lire chaque fichier dans `src/nhl/` :
- `build_data.py` — feature engineering
- `calibration.py` — calibration modèle
- `feature_engineering.py` — features NHL
- `fetch_game_stats.py` — fetcher stats
- `fetch_odds.py` — fetcher cotes (The Odds API vs API-Sports)
- `ml_models.py` — modèles
- `nhl_ml_predictor.py` — prédicteur (bug `KeyError: 'model'` à vérifier)
- `schemas.py` — schémas Pydantic
- `train.py` + `train_match.py` — training
- `backtest.py` — backtest

- [ ] **Step 2 : Inspection fetcher player props**

Lire `ProbaLab/src/fetchers/fetch_nhl_player_props.py`. Noter :
- Provider utilisé (The Odds API ?)
- Gestion fallback si pas de data
- Plan API Pro requis (design pivot §7 R2)

- [ ] **Step 3 : Inspection router NHL (873 LOC)**

Lire `ProbaLab/api/routers/nhl.py` en entier. Noter :
- Endpoints publics vs admin
- Normalisation team names (leçon 67 : "St Louis" vs "St. Louis", "Utah Hockey Club" vs "Utah Mammoth")
- Gestion fenêtre temporelle (leçon 66 : now→now+36h vs bornes UTC)

- [ ] **Step 4 : Grep team name mappings**

Chercher les mappings explicites de renames NHL :

Grep `Utah Mammoth`, `Hockey Club`, `St Louis`, `normalize.*team` dans `src/nhl/` et `api/routers/nhl.py`.

- [ ] **Step 5 : Vérifier schedule fallback**

Dans `src/nhl/` (peut-être `fetch_game_stats.py` ou autre) : chercher `fetch_schedule`. Vérifier que le fallback "closest day with games" est bien conditionné sur `day.get("games")` et pas juste sur la date (leçon 65).

- [ ] **Step 6 : Vérifier bug ML blend (R8 design pivot)**

Relire `src/nhl/nhl_ml_predictor.py:102` mentionné dans le design pivot. Le bug `KeyError: 'model'` est-il résolu dans la branche courante ?

- [ ] **Step 7 : Rédaction annexe 04**

Créer `docs/audit/2026-04-17/04_nhl_specifique.md`. Benchmark vs MoneyPuck (réf NHL pro) et Action Network. Leçons à citer : 64, 65, 66, 67.

Analyser aussi :
- Couverture tests NHL (ratio test/code)
- Qualité des commits récents `fix(nhl...)`

- [ ] **Step 8 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/04_nhl_specifique.md
git commit -m "docs(audit): add 04_nhl_specifique annex"
```

---

### ⛳ CHECKPOINT BATCH 1

- [ ] **Step BC1-1 : Livraison batch 1 à l'owner**

Annoncer à l'owner :

> "Batch 1 livré : 4 annexes (moteur probabilités, ML, monitoring ML, NHL). Prêt à présenter les findings haut niveau. Tu veux un résumé oral, ou je continue directement vers le batch 2 ?"

- [ ] **Step BC1-2 : Attendre feedback avant batch 2**

Si ajustements demandés : les appliquer. Sinon : continuer batch 2.

---

## BATCH 2 — Transverse technique + produit (domaines 5-9)

### Task 5 : Annexe 05 — Architecture backend

**Files:**
- Create: `docs/audit/2026-04-17/05_architecture_backend.md`
- Read for investigation : `ProbaLab/api/main.py`, `ProbaLab/api/routers/trigger.py` (1687 LOC), `ProbaLab/api/routers/best_bets.py` (1428 LOC), `ProbaLab/worker.py`, `ProbaLab/run_pipeline.py`, `ProbaLab/pyproject.toml`, `ProbaLab/api/helpers.py`, `ProbaLab/api/services/`

- [ ] **Step 1 : Inventaire LOC par router**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
wc -l ProbaLab/api/routers/*.py ProbaLab/api/*.py ProbaLab/src/*.py | sort -rn | head -30
```

Identifier les fichiers > 500 LOC (indicateur de dette).

- [ ] **Step 2 : Inspection trigger.py (1687 LOC)**

Lire `ProbaLab/api/routers/trigger.py` — focus sur la structure générale (quels jobs, quelle orchestration). Noter :
- Jobs listés
- Duplication éventuelle
- Logique métier mélangée avec glue FastAPI (leçon 62)

- [ ] **Step 3 : Inspection best_bets.py (1428 LOC)**

Même approche. Noter découpage possible en package.

- [ ] **Step 4 : Inspection worker.py (APScheduler)**

Lire `ProbaLab/worker.py` entièrement. Noter :
- Tous les jobs crons, horaires
- Cohérence avec le design pivot §5.1 (nouveaux jobs picks)
- Migration Trigger.dev → APScheduler complète (leçon 64)

- [ ] **Step 5 : Grep anti-patterns**

Grep dans `src/` et `api/` :
- `sys.path.insert` (leçon 44 : doit être zéro)
- `datetime.now()` nu sans timezone (leçon 22)
- `check_then_act` / SELECT avant INSERT (leçon 36)
- `api_get` sans retry

- [ ] **Step 6 : Inspection pyproject.toml**

Lire `ProbaLab/pyproject.toml`. Vérifier :
- `requires-python` (leçon 45 : cohérent avec pyenv local)
- Dépendances à jour ?

- [ ] **Step 7 : Rédaction annexe 05**

Créer `docs/audit/2026-04-17/05_architecture_backend.md`. Profondeur **Medium** (audit existe déjà 2026-04-10). Focus sur ce qui a réellement changé / ce qui reste.

- [ ] **Step 8 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/05_architecture_backend.md
git commit -m "docs(audit): add 05_architecture_backend annex"
```

---

### Task 6 : Annexe 06 — Sécurité

**Files:**
- Create: `docs/audit/2026-04-17/06_securite.md`
- Read for investigation : `ProbaLab/api/auth.py`, `ProbaLab/api/schemas.py`, `ProbaLab/api/rate_limit.py`, `ProbaLab/api/main.py` (middleware), `ProbaLab/api/routers/stripe_webhook.py`, `ProbaLab/api/routers/telegram.py`

- [ ] **Step 1 : Inspection auth.py**

Lire `ProbaLab/api/auth.py`. Noter :
- `hmac.compare_digest` utilisé pour CRON_SECRET (leçon 20)
- Audit log admin présent (leçon 43)
- JWT handling

- [ ] **Step 2 : Inspection schemas.py**

Lire `ProbaLab/api/schemas.py`. Noter :
- Modèles Pydantic présents (7 selon audit 2026-04-10)
- `extra="forbid"` appliqué systématiquement ? (todo.md Phase 3.2)

- [ ] **Step 3 : Inspection rate_limit.py**

Lire `ProbaLab/api/rate_limit.py`. Noter :
- slowapi actif ou fail-silent (leçon 41)
- Rate limit différencié par tier (todo.md Phase 3.3) ?

- [ ] **Step 4 : Audit endpoints POST/DELETE/PUT**

Grep `@router.post`, `@router.delete`, `@router.put` dans tous les routers :

Pour chacun noter :
- Auth utilisée (cron / jwt / admin / aucune)
- Pydantic model présent ?
- Rate limit appliqué ?

- [ ] **Step 5 : Audit endpoints GET sans auth**

Grep `@router.get` sans `Depends(verify_internal_auth)` ni `Depends(current_user)`. Pour chacun vérifier qu'il n'expose pas d'infos sensibles.

- [ ] **Step 6 : Inspection webhooks**

- `stripe_webhook.py` : INSERT atomique ou race condition (leçon 36) ?
- `telegram.py` : fail-closed si secret absent (leçon 37) ?

- [ ] **Step 7 : Security headers**

Grep `SecurityHeadersMiddleware` dans `api/main.py`. Vérifier : X-Frame-Options, HSTS, CSP, X-Content-Type-Options (leçon 42).

- [ ] **Step 8 : RLS Supabase**

Via Supabase MCP, lister les tables principales et vérifier si RLS est activé (leçon 58 : backend doit utiliser service_role, anon côté frontend avec policies strictes).

- [ ] **Step 9 : Rédaction annexe 06**

Créer `docs/audit/2026-04-17/06_securite.md`. Profondeur **Medium**. Leçons à citer : 11, 14-20, 27, 34, 36, 37, 41, 42, 43, 58.

- [ ] **Step 10 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/06_securite.md
git commit -m "docs(audit): add 06_securite annex"
```

---

### Task 7 : Annexe 07 — UI/UX Frontend

**Files:**
- Create: `docs/audit/2026-04-17/07_ui_ux_frontend.md`
- Read for investigation : `ProbaLab/dashboard/src/pages/`, `ProbaLab/dashboard/src/components/`, `ProbaLab/dashboard/src/App.tsx`, `ProbaLab/dashboard/package.json`, `ProbaLab/dashboard/vite.config.ts`, `ProbaLab/dashboard/tailwind.config.*`

- [ ] **Step 1 : Inventaire pages**

```bash
ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/dashboard/src/pages"
```

Lister toutes les pages, noter la taille de chacune.

- [ ] **Step 2 : Inspection App.tsx et navigation**

Lire `ProbaLab/dashboard/src/App.tsx`. Noter :
- Structure de routing (React Router)
- Navigation depth vers feature principale (leçon 55 : 1 clic max)
- Feature "Paris du Soir" vs pivot dashboard unifié

- [ ] **Step 3 : Inspection composants**

Lister `ProbaLab/dashboard/src/components/` et lire les composants principaux (au moins : MatchCard, PredictionCard, ParisDuSoir, Performance). Noter :
- Cohérence design system (Radix UI / shadcn)
- Réutilisation vs duplication
- Mobile-first ?

- [ ] **Step 4 : Grep typographie illisible**

Grep dans `dashboard/src/`:
- `text-\[9px\]`
- `text-\[10px\]`
- `text-\[11px\]`

Chaque occurrence = violation leçon 54.

- [ ] **Step 5 : Dark mode**

Lire `ProbaLab/dashboard/tailwind.config.*`. Vérifier `darkMode: 'class'` configuré (todo.md Phase 5.1). Grep `dark:` dans les composants.

- [ ] **Step 6 : Accessibilité**

Grep `aria-label`, `role=`, `alt=` dans les pages principales. Compter pour évaluer la couverture a11y.

- [ ] **Step 7 : PWA**

Grep `vite-plugin-pwa` dans `dashboard/vite.config.ts` et `package.json`. Service worker présent ?

- [ ] **Step 8 : Audit Lighthouse (optionnel si préview MCP démarrable)**

Si possible, démarrer le dev server et capturer un snapshot mobile/desktop. Sinon, noter dans l'annexe que Lighthouse nécessite test manuel.

- [ ] **Step 9 : Rédaction annexe 07**

Créer `docs/audit/2026-04-17/07_ui_ux_frontend.md`. Profondeur **Deep**. Benchmark vs SofaScore Predictions (mobile-first excellence) et OneFootball (UX). Leçons 54-56, 59.

- [ ] **Step 10 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/07_ui_ux_frontend.md
git commit -m "docs(audit): add 07_ui_ux_frontend annex"
```

---

### Task 8 : Annexe 08 — Tests & CI/CD

**Files:**
- Create: `docs/audit/2026-04-17/08_tests_cicd.md`
- Read for investigation : `ProbaLab/tests/`, `.github/workflows/`, `ProbaLab/pytest.ini`, `ProbaLab/Makefile`, `ProbaLab/railway.toml`, `ProbaLab/nixpacks.toml`, `ProbaLab/Procfile`

- [ ] **Step 1 : Inventaire tests**

```bash
ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/tests" | head -40
wc -l "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/tests"/*.py | tail -5
```

Noter : nombre total de fichiers tests, LOC totales.

- [ ] **Step 2 : Lire le baseline et coverage gaps**

Lire `ProbaLab/tasks/baseline_2026-04-10.md` et `ProbaLab/tasks/coverage_gaps.md`. Utiliser pour établir le point de départ.

- [ ] **Step 3 : Inspection pytest.ini**

Lire `ProbaLab/pytest.ini`. Noter :
- Marqueurs (integration, slow, etc.)
- Options par défaut

- [ ] **Step 4 : Inspection CI**

Lire `.github/workflows/`. Pour chaque workflow :
- Déclencheurs (push, PR)
- Steps (lint, test, coverage)
- Seuil `--cov-fail-under` (leçon 60 : doit ≤ couverture actuelle)

- [ ] **Step 5 : Lancer pytest pour mesurer la couverture actuelle**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab"
pyenv exec python -m pytest tests/ -m "not integration" --cov=src --cov=api --cov-report=term -q 2>&1 | tail -30
```

Si échec d'exécution (env), noter dans l'annexe mais ne pas bloquer.

- [ ] **Step 6 : Grep tests orphelins**

Grep `test_*.py` à la racine du projet (leçon 61 : scripts jetables).

- [ ] **Step 7 : Inspection déploiement**

Lire `railway.toml`, `nixpacks.toml`, `Procfile`. Vérifier root directory (leçon 28).

- [ ] **Step 8 : Rédaction annexe 08**

Créer `docs/audit/2026-04-17/08_tests_cicd.md`. Profondeur **Medium**. Leçons 28, 29, 60, 61, 63.

- [ ] **Step 9 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/08_tests_cicd.md
git commit -m "docs(audit): add 08_tests_cicd annex"
```

---

### Task 9 : Annexe 09 — Produit & Positionnement

**Files:**
- Create: `docs/audit/2026-04-17/09_produit_positionnement.md`
- Read for investigation : `BP_ProbaLab_v2.pdf`, `ProbaLab/AUDIT_COMPLET.md`, `ProbaLab/AUDIT_PROMPT.md`, `ProbaLab/Football_Stack_Audit.pdf`, `ProbaLab/NHL_Stack_Audit.pdf`, `ProbaLab/STACK_V2_PLAN.md`, `ProbaLab/api/routers/stripe_webhook.py`, CLAUDE.md projet

- [ ] **Step 1 : Lire le business plan**

Lire `BP_ProbaLab_v2.pdf` (pages 1-20 si possible, sinon 1-10). Extraire :
- Value proposition déclarée
- Segment cible
- Modèle de revenus
- Concurrents cités
- KPIs produit

- [ ] **Step 2 : Lire les audits existants**

Lire `ProbaLab/AUDIT_COMPLET.md` et `ProbaLab/AUDIT_PROMPT.md`. Noter :
- Ce qui était identifié il y a 1-2 mois
- Ce qui a été résolu depuis (vérifier vs leçons récentes)
- Ce qui reste ouvert

- [ ] **Step 3 : Lire Football_Stack_Audit.pdf et NHL_Stack_Audit.pdf**

Extraire la vision technique initiale et comparer avec l'implémentation actuelle.

- [ ] **Step 4 : Monétisation Stripe**

Lire `ProbaLab/api/routers/stripe_webhook.py`. Noter :
- Plans tarifaires gérés
- Features gating (premium vs free)
- Funnel conversion

- [ ] **Step 5 : Analytics utilisateur**

Grep dans `dashboard/src/` : `analytics`, `posthog`, `mixpanel`, `plausible`, `ga4`, `gtag`. Tracking produit présent ou absent ?

- [ ] **Step 6 : Rédaction annexe 09**

Créer `docs/audit/2026-04-17/09_produit_positionnement.md`. Profondeur **Deep**. Évaluer :
- Positionnement actuel vs pivot vs "meilleure app du marché"
- Monétisation actuelle vs opportunités
- Différenciation réelle vs perçue
- Métriques de succès définies ?

- [ ] **Step 7 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/09_produit_positionnement.md
git commit -m "docs(audit): add 09_produit_positionnement annex"
```

---

### ⛳ CHECKPOINT BATCH 2

- [ ] **Step BC2-1 : Livraison batch 2 à l'owner**

Annoncer :

> "Batch 2 livré : 5 annexes (architecture, sécurité, UI/UX, tests/CI, produit). Les 9 annexes techniques/produit sont complètes. Prêt pour le batch 3 : benchmark concurrentiel + évaluation pivot + roadmap + exec summary."

- [ ] **Step BC2-2 : Attendre feedback avant batch 3**

Appliquer ajustements si demandés.

---

## BATCH 3 — Benchmark + stratégie + synthèse (docs 10, 11, 12, 00)

### Task 10 : Annexe 10 — Benchmark concurrentiel

**Files:**
- Create: `docs/audit/2026-04-17/10_benchmark_concurrentiel.md`

- [ ] **Step 1 : Benchmark tipsters foot — Forebet**

WebFetch `https://www.forebet.com/en/about-forebet`. Extraire :
- Méthodologie affichée (Poisson, stats)
- Features utilisateur
- Markets couverts
- Transparence sur la performance (Brier, accuracy déclarée)

- [ ] **Step 2 : Benchmark Infogol (xG)**

WebFetch `https://www.infogol.net/en`. Noter :
- Usage xG affiché comme différenciateur
- UX mobile
- Niveau de granularité des modèles

- [ ] **Step 3 : Benchmark PredictZ**

WebFetch `https://www.predictz.com/`. Noter :
- Approche prédiction
- Monétisation (abonnement ?)
- Historique tracking

- [ ] **Step 4 : Benchmark RebelBetting**

WebFetch `https://rebelbetting.com/`. Noter :
- Positionnement pro value betting
- Features uniques (closing line comparison)
- Pricing
- Rigueur ML apparente

- [ ] **Step 5 : Benchmark Pinnacle (closing line)**

WebSearch "Pinnacle sportsbook closing line value CLV prediction accuracy". Noter :
- CLV comme gold standard industrie
- Brier / log-loss publiés ?

- [ ] **Step 6 : Benchmark SofaScore Predictions**

WebFetch `https://www.sofascore.com/`. Noter :
- Mobile UX
- Profondeur data par match
- Prédictions intégrées ou via tiers ?

- [ ] **Step 7 : Benchmark OneFootball**

WebFetch `https://onefootball.com/`. Noter :
- UX grand public
- Prédictions vs tipping communautaire

- [ ] **Step 8 : Benchmark Action Network (US)**

WebFetch `https://www.actionnetwork.com/`. Noter :
- Positionnement "smart betting tools"
- Features payantes vs gratuites
- Offre NHL

- [ ] **Step 9 : Benchmark MoneyPuck (NHL spécifique)**

WebFetch `https://moneypuck.com/`. Noter :
- Référence NHL stats/prédictions
- xG pour NHL
- Approche différenciante

- [ ] **Step 10 : Rédaction annexe 10**

Créer `docs/audit/2026-04-17/10_benchmark_concurrentiel.md`. Structure :

```markdown
# Benchmark concurrentiel

## 1. Méthodologie
## 2. Tableau récapitulatif multi-critères
| Concurrent | Segment | Méthode | Markets | UX | Monétisation | Différenciateur |
| ...

## 3. Deep dive par concurrent
### 3.1 Forebet
### 3.2 Infogol
### 3.3 PredictZ
### 3.4 RebelBetting
### 3.5 Pinnacle (référence CLV)
### 3.6 SofaScore
### 3.7 OneFootball
### 3.8 Action Network
### 3.9 MoneyPuck

## 4. Identification des leaders par domaine
(utilisé pour alimenter les §4 "Benchmark vs leader" des annexes 01-09)

## 5. Zones blanches du marché (opportunités différenciantes)
- Features qu'aucun leader ne couvre
- Angles non exploités (IA conversationnelle, explainability, social, éducatif)

## 6. Positionnement ProbaLab proposé
```

- [ ] **Step 11 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/10_benchmark_concurrentiel.md
git commit -m "docs(audit): add 10_benchmark_concurrentiel annex"
```

---

### Task 11 : Annexe 11 — Évaluation du pivot

**Files:**
- Create: `docs/audit/2026-04-17/11_evaluation_pivot.md`
- Read for investigation (relecture critique) : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`, `ProbaLab/tasks/plan_pivot_probas_sportives.md`

- [ ] **Step 1 : Relecture critique du design pivot**

Relire `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md` avec œil adversarial. Chercher :
- Assumptions non validées (§4 A1-A4)
- Risques mal mitigés (§7 R1-R9)
- Décisions open non tranchées (§9)
- Alignement avec les findings des annexes 01-09 (est-ce que le pivot résout les gaps identifiés ?)

- [ ] **Step 2 : Relecture du plan pivot**

Relire `ProbaLab/tasks/plan_pivot_probas_sportives.md`. Noter :
- Faisabilité des 13-20 jours estimés
- Dépendances bloquantes (ODDS_API Pro, bug ML blend NHL)
- Risques d'exécution

- [ ] **Step 3 : Croiser avec benchmark (annexe 10)**

Relire l'annexe 10. Le positionnement "Spécialiste en probabilités sportives" :
- Est-il occupé par un concurrent ?
- Laisse-t-il des zones blanches ?
- Résonne-t-il avec les leaders grand public (SofaScore, OneFootball) ou pro (RebelBetting) ?

- [ ] **Step 4 : Rédaction annexe 11**

Créer `docs/audit/2026-04-17/11_evaluation_pivot.md`. Structure :

```markdown
# Évaluation du pivot "Spécialiste probabilités sportives"

## 1. Rappel du pivot
(3-4 phrases, synthèse du design doc)

## 2. Forces du pivot
## 3. Faiblesses du pivot
## 4. Angles morts / assumptions non validées
## 5. Risques non mitigés
## 6. Alignement avec les findings de l'audit (annexes 01-09)
## 7. Alignement avec le benchmark concurrentiel (annexe 10)

## 8. Verdict

> **Recommandation : [GO / GO avec amendements / PAUSE / STOP]**

## 9. Amendements proposés (si applicable)
- Amendement 1
- Amendement 2
- ...

## 10. Conditions préalables avant démarrage
```

- [ ] **Step 5 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/11_evaluation_pivot.md
git commit -m "docs(audit): add 11_evaluation_pivot annex"
```

---

### Task 12 : Annexe 12 — Roadmap meilleure app

**Files:**
- Create: `docs/audit/2026-04-17/12_roadmap_meilleure_app.md`

- [ ] **Step 1 : Relire les §5 (Gaps P0/P1/P2) des annexes 01-09**

Agréger manuellement tous les gaps P0/P1/P2 identifiés dans les 9 annexes techniques/produit. Tenir un tableau récapitulatif :

| Origin annexe | Gap | Priorité | Effort estimé | Impact attendu |

- [ ] **Step 2 : Croiser avec annexes 10 et 11**

Ajouter :
- Gaps "zone blanche marché" (annexe 10 §5)
- Amendements pivot (annexe 11 §9)

- [ ] **Step 3 : Décider des 3 horizons**

- **H1 (0-4 sem) : Stabilisation + quick wins** — résoudre tous les bugs latents des leçons, exécuter le plan d'actions correctives todo.md déjà planifié, préparer les prérequis du pivot (bug NHL ML blend notamment)
- **H2 (1-3 mois) : Passage à L3+ + exécution pivot** — pivot avec amendements, monitoring ML activé, UI/UX refonte partielle
- **H3 (3-12 mois) : Dépasser les leaders** — 2-3 différenciateurs L5 (à identifier depuis annexe 10 §5)

- [ ] **Step 4 : Rédaction annexe 12**

Créer `docs/audit/2026-04-17/12_roadmap_meilleure_app.md`. Structure :

```markdown
# Roadmap : Devenir la meilleure app de prédiction sportive

## 1. Principes de priorisation
- Impact × 1/Effort
- Dépendances techniques
- Risque (remédier avant d'ajouter)

## 2. Backlog agrégé P0 (bloquant pour L3+)
(tableau : gap, domaine, effort, impact, dépendances)

## 3. Backlog agrégé P1 (passage L4)
## 4. Backlog agrégé P2 (polish L4→L5)

## 5. Horizons temporels
### H1 — Stabilisation (0-4 semaines)
### H2 — Pivot + L3+ (1-3 mois)
### H3 — Différenciation L5 (3-12 mois)

## 6. Jalons de succès
- Fin H1 : 0 bug latent des leçons, couverture tests ≥ 60%, baseline ML monitoring actif
- Fin H2 : pivot en prod, tous domaines ≥ L3, une L4 pilote (ex : UI/UX)
- Fin H3 : 2-3 dimensions L5 démontrables vs leaders

## 7. KPIs de suivi
- Brier score foot/NHL (objectif < 0.21 / < 0.23)
- Couverture tests global (objectif ≥ 75%)
- Lighthouse Performance (objectif > 90)
- ROI virtuel 90j par catégorie de pick
- Taux de conversion free → premium
- NPS utilisateur (si mesurable)
```

- [ ] **Step 5 : Auto-review et commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/12_roadmap_meilleure_app.md
git commit -m "docs(audit): add 12_roadmap_meilleure_app annex"
```

---

### Task 13 : Executive Summary (00)

**Files:**
- Create: `docs/audit/2026-04-17/00_EXECUTIVE_SUMMARY.md`

- [ ] **Step 1 : Relecture de tous les documents 01-12**

Relire rapidement tous les documents déjà écrits (01 à 12). Extraire pour chacun :
- Le niveau L attribué
- Le top 1 finding (force ou faiblesse)
- Le top 1 P0

- [ ] **Step 2 : Rédaction section 1-2 — Verdict et scoring global**

Créer `docs/audit/2026-04-17/00_EXECUTIVE_SUMMARY.md` et écrire :

```markdown
# Executive Summary — Audit ProbaLab 2026-04-17

## 1. Verdict en une phrase
[phrase ciselée — où en est ProbaLab, distance à "meilleure app", effort pour y arriver]

## 2. Scoring global
| Domaine | Niveau actuel | Leader ref | Gap vs leader | Pour passer L+1 |
|---------|---------------|------------|----------------|-----------------|
| Moteur probabilités | L? | Infogol | ... | ... |
| Machine Learning | L? | RebelBetting | ... | ... |
| Monitoring ML | L? | (standard MLOps) | ... | ... |
| NHL spécifique | L? | MoneyPuck | ... | ... |
| Architecture backend | L? | (SaaS standard) | ... | ... |
| Sécurité | L? | (OWASP) | ... | ... |
| UI/UX frontend | L? | SofaScore | ... | ... |
| Tests & CI/CD | L? | (industrie) | ... | ... |
| Produit | L? | Action Network | ... | ... |
```

- [ ] **Step 3 : Rédaction sections 3-4 — Forces et faiblesses**

```markdown
## 3. Top 5 forces de ProbaLab
1. [Force 1] — citation source
2. [Force 2] — citation source
3. [Force 3] — citation source
4. [Force 4] — citation source
5. [Force 5] — citation source

## 4. Top 5 faiblesses critiques
1. [Faiblesse 1] — impact, annexe source
2. [Faiblesse 2] — ...
3. [Faiblesse 3] — ...
4. [Faiblesse 4] — ...
5. [Faiblesse 5] — ...
```

- [ ] **Step 4 : Rédaction section 5 — Top 10 quick wins**

Sélectionner 10 P0 du `12_roadmap` dont impact/effort est maximum et effort < 5 jours.

Format :
```markdown
## 5. Top 10 quick wins
| # | Action | Impact | Effort | Domaine | Fichier |
|---|--------|--------|--------|---------|---------|
| 1 | ... | H | 1j | ... | ... |
```

- [ ] **Step 5 : Rédaction sections 6-7 — Menaces + Opportunités**

```markdown
## 6. Menaces stratégiques
### Techniques
### Produit
### Marché

## 7. Opportunités différenciantes (passage L5)
(2-3 angles issus de annexe 10 §5)
```

- [ ] **Step 6 : Rédaction section 8 — Verdict pivot**

Synthétiser le verdict de l'annexe 11 en 1 paragraphe clair. Reprendre la recommandation GO / GO-amendé / PAUSE / STOP.

- [ ] **Step 7 : Rédaction sections 9-10 — Roadmap + KPIs**

```markdown
## 9. Roadmap haut niveau
- **H1 (0-4 sem)** : [3-5 bullets]
- **H2 (1-3 mois)** : [3-5 bullets]
- **H3 (3-12 mois)** : [3-5 bullets]

## 10. Chiffres clés
- Brier Score foot actuel : [val] — objectif : [val]
- Brier Score NHL actuel : [val] — objectif : [val]
- Couverture tests : [val]% — objectif : 75%
- Bugs latents (leçons non closes) : [n]
- Endpoints sans Pydantic strict : [n]
- Fichiers > 500 LOC : [n]
- Lighthouse estimé : [val]
- ROI virtuel 30j par catégorie : [safe/fun/value]
```

- [ ] **Step 8 : Auto-review exec summary**

Relire en se demandant :
- Un décideur qui ne lit QUE ce document peut-il prendre une décision éclairée ?
- Chaque affirmation est-elle pointée vers une annexe ?
- 8-10 pages max respecté ?

- [ ] **Step 9 : Commit exec summary**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add docs/audit/2026-04-17/00_EXECUTIVE_SUMMARY.md
git commit -m "docs(audit): add 00 executive summary"
```

---

### ⛳ CHECKPOINT FINAL

- [ ] **Step CF-1 : Vérification exhaustivité**

```bash
ls "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/docs/audit/2026-04-17"
```

Doit lister 13 fichiers : `README.md` + 12 documents d'audit. Vérifier qu'aucun n'est vide :

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
wc -l docs/audit/2026-04-17/*.md
```

- [ ] **Step CF-2 : Vérification DoD**

Vérifier les 7 critères d'acceptation §10 de la spec :
- [x] Exhaustivité (12 docs)
- [ ] Actionnabilité (12_roadmap avec P0/P1/P2)
- [ ] Preuves (fichier:ligne partout)
- [ ] Scoring justifié
- [ ] Pas de langue de bois
- [ ] Exec summary autoporteur
- [ ] Verdict pivot clair

- [ ] **Step CF-3 : Livraison finale à l'owner**

Annoncer :

> "Audit 360° complet livré dans `docs/audit/2026-04-17/` : 12 documents + README. Executive summary lisible standalone en 15-20 min. Le `12_roadmap_meilleure_app.md` contient le backlog priorisé pour alimenter un plan d'action via `writing-plans`. Tu veux reviewer maintenant, ou on enchaîne directement sur le plan d'exécution du roadmap ?"

- [ ] **Step CF-4 : Attendre validation owner**

Si revisions demandées : appliquer. Si validation : optionnellement invoquer `writing-plans` sur `12_roadmap_meilleure_app.md`.

---

## Self-review du plan

### 1. Spec coverage

Vérification section par section de la spec :

| Spec section | Couvert par |
|---|---|
| §4 D1 (angle 360°) | Task 0 setup + ensemble du plan |
| §4 D2 (9 domaines) | Tasks 1-9 |
| §4 D3 (profondeur variable) | Noté Deep/Medium dans Tasks 1-9 |
| §4 D4 (benchmark multi-segment) | Task 10 (Steps 1-9 couvrent 9 concurrents) |
| §4 D5 (exec summary + annexes) | Task 13 + Tasks 1-12 |
| §4 D6 (scoring L1-L5 + gap) | Template utilisé Tasks 1-9, grille dans §7 spec |
| §4 D7 (batches avec feedback) | Checkpoints BC1, BC2, CF |
| §4 D8 (audit ≠ plan action) | Reco finale en CF-3 pointe vers writing-plans séparé |
| §5 structure 12 docs | File Structure au début du plan |
| §6 template annexes | Utilisé dans Tasks 1-9 Step de rédaction |
| §7 échelle L1-L5 + règles anti-inflation | Référencé dans chaque Task Step de rédaction |
| §8 méthodologie par domaine | Tasks 1-9 steps d'investigation |
| §9 structure exec summary | Task 13 Steps 2-7 |
| §10 critères d'acceptation (DoD) | Checkpoint final CF-2 |
| §11 timeline | Implicite dans granularité tasks |
| §12 livraison par batches | Checkpoints BC1/BC2/CF |
| §13 après audit | CF-3 |

**Gaps détectés** : aucun. Tous les éléments de la spec sont couverts.

### 2. Placeholder scan

Relu le plan. Aucun "TBD", "TODO", "à compléter" dans les instructions (seulement dans les templates de sortie comme `[val]` = placeholder de données à mesurer, attendu).

### 3. Type consistency

Vérifications :
- Nom du dossier audit : `docs/audit/2026-04-17/` — cohérent partout
- Nommage des 12 docs : `00_EXECUTIVE_SUMMARY.md`, `01_moteur_probabilites.md`, ..., `12_roadmap_meilleure_app.md` — cohérent File Structure et Tasks
- Numérotation Tasks : 0 → 13 sans trou
- Checkpoints : BC1 (fin batch 1), BC2 (fin batch 2), CF (final)
- Chemins ProbaLab : tous en absolu `/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/...`
