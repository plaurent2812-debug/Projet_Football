# 08 — Tests & CI/CD

> Auditeur : auditeur technique senior (tests + CI/CD)
> Date : 2026-04-17 — profondeur Medium
> Branche analysée : `feat/pivot-probas-sportives`

## 1. Périmètre audité

- Suite de tests Python : `ProbaLab/tests/` (29 fichiers + sous-dossier `test_api/`)
- Configuration pytest : `ProbaLab/pytest.ini`
- CI GitHub Actions : `.github/workflows/ci.yml`, `.github/workflows/daily-pipeline.yml`
- Déploiement Railway : `ProbaLab/railway.toml`, `ProbaLab/nixpacks.toml`, `ProbaLab/Procfile`
- Makefile, `ruff.toml`, baselines `tasks/baseline_2026-04-10.md`, `tasks/coverage_gaps.md`
- Leçons projet pertinentes : 2026-04-02 (Railway root dir), 2026-04-04 (pyenv/pyproject), 2026-04-10 (×4 : cov-fail-under, scripts de debug parasites, logique inline non testable, TestClient slowapi)

## 2. État actuel

### 2.1 Ce qui fonctionne bien

- **Suite non nulle et structurée** : 29 fichiers de test, 9 102 LOC, **579 `def test_`** ; le CLAUDE.md annonce « 381 tests » — le nombre réel est supérieur (résultat pytest : **423 passed + 178 deselected = 601 items collectés, 579 fonctions `test_`**).
- **Séparation unit / integration** propre via `@pytest.mark.integration` (5 fichiers portent `pytestmark = pytest.mark.integration` — `test_*_integration.py`), déclarés dans `pytest.ini:6-8`.
- **Modules `_logic` extraits** : `api/routers/best_bets_logic.py` existe (≈ leçon 62) et est accompagné de `tests/test_best_bets_logic.py` (87 tests) + `tests/test_best_bets_router.py` (13 tests). C'est la bonne trajectoire.
- **CI lint+test+types** séparée en 3 jobs (`ci.yml:14,31,64`), Python 3.11 pinné, cache pip, artefacts de résultats uploadés.
- **`conftest.py` fournit `MockSupabaseQuery`** — pattern correct pour isoler les tests du réseau.
- **`--cov-fail-under=21`** aligné sur la mesure réelle (21%) depuis la leçon 60 : le gate ne ment plus.
- **Mesure empirique reproduite localement** (voir §4) : **423 passed, 2 failed, 178 deselected, couverture globale 21%** en 6,31 s — la suite unit est rapide et quasi verte.

### 2.2 Dette technique / bugs latents

| Gravité | Problème | Preuve |
|---|---|---|
| P0 | **Makefile obsolète** : cible tout le dossier `Projet_Football/` (legacy), qui n'est plus le répertoire de build. `make test`, `make lint`, `make typecheck` ne testent **rien** de la stack `ProbaLab/`. Un dev qui tape `make test` croit valider, ne valide rien. | `Makefile:5-8` : `PROJECT := Projet_Football`, `SRC := $(PROJECT)/models ...` |
| P0 | **Workflow `daily-pipeline.yml` casse** : exécute `cd Projet_Football && python run_pipeline.py full` sur un dossier non maintenu. Leçon 28 (Railway root dir) appliquée à Railway mais pas à GH Actions. | `.github/workflows/daily-pipeline.yml:34,44,53` |
| P0 | **`railway.toml` mal structuré** : deux `[[services]]` mais un seul `[services.deploy]` (ligne 19) — le deuxième écrase le premier. En pratique, un seul service prend effet. | `railway.toml:4-22` |
| P0 | **Procfile redondant avec railway.toml + nixpacks.toml** : trois descripteurs de démarrage en conflit potentiel (`Procfile:1`, `nixpacks.toml:2`, `railway.toml:9`). Risque de comportement différent selon le chemin de build Railway. |
| P1 | **3 scripts de debug dans `src/`** qui frappent la DB au simple import : `src/test_auth.py`, `src/test_connection.py`, `src/test_api_halves.py`. Préfixe `test_` → collectés par pytest si on change `testpaths`. Exactement la classe de bug de la leçon 61. | `src/test_auth.py:1-5` : `from src.config import supabase; ... supabase.table("profiles").select("role").execute()` à l'import. |
| P1 | **`test_nhl_pipeline.py` quasi vide** : 4 LOC, 1 test. Pas de couverture réelle du pipeline NHL qui vient juste d'être migré (leçon 64 — APScheduler migration incomplète). | `wc -l tests/test_nhl_pipeline.py` = 4 |
| P1 | **Aucun test e2e pipeline** (`fetch → predict → resolve → ROI`). `coverage_gaps.md` §Phase 1.5 planifie `tests/test_pipeline_e2e.py` mais il n'existe pas. Les 3 bugs sports majeurs de la leçon 64-67 seraient tombés sur un e2e. |
| P1 | **`--cov-fail-under=21`** — seuil correct mais extrêmement bas pour une plateforme en prod avec paiements Stripe, RLS, Kelly/ROI. Une industrie SaaS early-stage vise 70% unit + smoke e2e. Le seuil doit monter par paliers (plan baseline : 19→60→80) mais il est resté à 21. |
| P1 | **`mypy --ignore-missing-imports ... \|\| true`** (`ci.yml:78`) : le type-check ne bloque jamais. En pratique c'est un `echo` coûteux, pas une porte de qualité. |
| P2 | **2 tests flaky** observés sur `test_stats_engine.py::TestCalculateXg` (`test_fallback_when_no_data`, `test_unknown_team_fallback`) — baseline mentionnait déjà des échecs env-dependent (Supabase client init). Toujours présents le 2026-04-17. |
| P2 | **Aucun workflow de release / canary / rollback** : Railway redéploie sur push `main`, pas d'étape "promote to prod après smoke". |
| P2 | **`ruff.toml:32`** : `per-file-ignores` pointe `Projet_Football/tests/*` — dossier legacy. Les ignores sur `ProbaLab/tests/*` ne sont pas définis. |

### 2.3 Code smells repérés

- **24 fonctions `_snake` privées** dans `api/routers/` (grep `^def _|^async def _` → 24 matches, concentrés dans `trigger.py` (5), `stripe_webhook.py` (6), `telegram.py` (5)). Ce sont exactement le type d'helpers imbriqués qui deviennent non-testables (leçon 62). `trigger.py` fait 1 687 LOC et est mesuré à 10% de couverture dans `baseline_2026-04-10.md`. Même verdict pour `stripe_webhook.py` (185 LOC, logique de signature + race conditions — cf leçon 2026-04-03 Stripe webhook).
- **Gros fichiers à 0% de couverture** : `src/ticket_generator.py` (507 lignes), `src/training/train.py` (343), `src/training/backtest.py` (370), `src/reflection_engine.py` (50), `src/nhl/train_match.py` (151), `src/monitoring/*` (5 fichiers × 60-180 lignes). Ce sont des briques métier critiques (génération de tickets combos, entraînement modèles, backtest, monitoring Brier/drift).
- **Mélange `Projet_Football/` + `ProbaLab/`** dans le repo : 2 arborescences, duplication documentée par la leçon 2026-04-02 ("11 fichiers divergeaient silencieusement"). Toujours visible : `Projet_Football/` est référencé dans `Makefile` et `daily-pipeline.yml`.
- **`conftest.py` fournit le mock mais n'est pas appliqué par défaut** (cf note baseline : « plusieurs tests tapent la vraie DB via `from src.config import supabase` »).
- **Aucune fixture pour les secrets** : la CI passe `SUPABASE_URL` et `SUPABASE_KEY` depuis `secrets.*` (`ci.yml:35-36`) mais hardcode `API_FOOTBALL_KEY: "test"` et `GEMINI_API_KEY: "test"`. Si un test sollicite réellement ces APIs, il crashe silencieusement ou fait un appel réel selon l'état du mock.

### 2.4 Gaps vs. standard industrie (CI/CD)

| Pratique standard SaaS early-stage | État ProbaLab |
|---|---|
| Couverture ≥ 70% | **21%** (mesuré) |
| Tests e2e pipeline critique | Absent (Phase 1.5 jamais faite) |
| Canary / blue-green deploys | Absent — push `main` → deploy direct Railway |
| Rollback automatisé en cas d'échec smoke post-deploy | Absent |
| Health check post-deploy (bloquant) | Partiel : `healthcheckPath = "/health"` dans `railway.toml:10` mais pas gaté dans la CI |
| Type check bloquant | Non (`\|\| true` dans `ci.yml:78`) |
| Tests parallèles (`pytest-xdist`) | Non |
| Mutation testing / property-based | Absent |
| Secret scanning (gitleaks) dans la CI | Absent |
| Dépendency scanning (Dependabot / pip-audit) | Non visible |
| Preview envs par PR | Non |
| Tests de charge / perf | Absent |

## 3. Niveau de maturité : **L2 / L5**

- L1 — *Ad hoc* : dépassé (CI existe, tests structurés).
- **L2 — Basique (actuel)** : suite unit fonctionnelle, CI qui bloque sur lint + tests, couverture honnêtement mesurée mais basse ; plusieurs gates cosmétiques (mypy `|| true`) ; scripts de build legacy non nettoyés ; aucun e2e.
- L3 — Intermédiaire : couverture 60%+, e2e, type-check bloquant, déploiements gated par smoke — **non atteint**.
- L4 — Avancé : canary, feature flags, tests de charge, mutation testing — absent.
- L5 — Excellence : SLO automatisés, rollback auto, chaos testing — absent.

## 4. Benchmark vs. standard industrie

Référence : SaaS Python/FastAPI early-stage qui gère argent utilisateur (Stripe), quotas API externes (API-Football, Gemini, Odds API), et prédictions ML.

| Dimension | Standard | ProbaLab | Écart |
|---|---|---|---|
| Tests unitaires (modules purs) | 80%+ | ~21% global, mais ≥55% sur `bankroll`, `prediction_blender`, `best_bets_logic` (les modules déjà extraits) | -60 pts global |
| Tests integration (DB mockée) | Couverture des endpoints critiques | Endpoints partiellement testés (`test_best_bets_router.py` 13 tests) ; `trigger.py` (1 687 LOC) à 10% | Gros |
| Tests e2e | 1 smoke + 3-5 happy paths critiques | 0 | -5 |
| Temps de CI | < 10 min | Non mesuré ici, a priori < 5 min (423 tests en 6 s en local) | OK |
| Reprodutibilité | Python version pinnée partout | 3.11 dans `ci.yml`, **3.10 dans `daily-pipeline.yml`**, `ruff.toml:1` target `py310`, `pyproject.toml` `>=3.11` (leçon 2026-04-04) | Incohérence persistante |
| Config déploiement | 1 source de vérité | 3 (`Procfile`, `nixpacks.toml`, `railway.toml` mal formé) | -3 |
| Sécurité CI | Secret scan + SCA | 0 | Gros |

### Mesure empirique de la couverture (2026-04-17)

Commande exécutée (depuis `ProbaLab/`) :
```
pyenv exec python -m pytest tests/ -m "not integration" \
  --timeout=60 --cov=src --cov=api --cov-report=term \
  --ignore=tests/test_db.py --ignore=tests/test_db_cs.py --ignore=tests/test_dembele.py -q
```

Résultat :
```
TOTAL    15471  12278    21%
========== 2 failed, 423 passed, 178 deselected, 15 warnings in 6.31s ==========
```

Donc **21% de couverture globale mesurée** (baseline 2026-04-10 : 19% → +2 pts en 7 jours). Fichiers critiques :
- `src/prediction_blender.py` : **100%** (était 55%, gap Phase 1.4 fermé)
- `src/bankroll.py` : ≥ 77% (baseline)
- `api/routers/best_bets_logic.py` : haute (module extrait + 87 tests dédiés)
- `api/routers/trigger.py` : encore très bas (baseline 10%, pas de nouveau test_trigger)
- `src/ticket_generator.py`, `src/training/train.py`, `src/monitoring/*` : **0%**

## 5. Gaps pour passer au niveau supérieur

### P0 (bloquants, semaine)

1. **Nettoyer le legacy `Projet_Football/`** — soit le supprimer du repo, soit le marquer `archive/`. Mettre à jour `Makefile`, `daily-pipeline.yml`, `ruff.toml` pour cibler `ProbaLab/`. Aujourd'hui `make test` est un faux positif silencieux.
2. **Corriger `railway.toml`** (deux services mais un seul bloc `[services.deploy]` — le worker n'a pas de config effective). Adopter **une seule** source : soit `railway.toml`, soit `Procfile` + `nixpacks.toml`. Pas les trois.
3. **Supprimer/déplacer `src/test_auth.py`, `src/test_connection.py`, `src/test_api_halves.py`** vers `scripts/debug/` — leçon 61 partiellement appliquée (scripts des `tests/` nettoyés, ceux de `src/` oubliés).
4. **Fixer les 2 tests flaky** `test_stats_engine.py::TestCalculateXg::test_fallback_when_no_data` et `test_unknown_team_fallback` — baseline les signalait déjà, toujours rouges.
5. **Harmoniser la version Python** partout : `ci.yml` (3.11) vs `daily-pipeline.yml` (3.10) vs `ruff.toml` target py310 vs `pyproject.toml` requires-python >=3.11.

### P1 (mois)

6. **Test e2e pipeline** (`tests/test_pipeline_e2e.py`, marqué `integration`) — seed 2 fixtures + 2 predictions + 3 best_bets, simuler scores FT/AET, asserter ROI. Plan déjà prêt dans `coverage_gaps.md:98-105`.
7. **Monter `--cov-fail-under` par paliers** : 21 → 30 (après extraction `trigger.py`) → 40 → 60. Chaque PR qui baisse la couverture est bloqué.
8. **Rendre mypy bloquant** sur les modules stables (`src/bankroll`, `src/prediction_blender`, `api/routers/best_bets_logic`) — ajouter un flag `--strict` ciblé au lieu de `|| true` global.
9. **Extraire la logique pure de `trigger.py` (1 687 LOC, 10% cov)** dans `api/routers/trigger_logic.py`, même pattern que `best_bets_logic.py`. Cible : 60% couverture sur trigger.
10. **Ajouter un smoke post-deploy Railway** : step CI qui `curl /health` après déploiement et rollback si KO.

### P2 (trimestre)

11. **Secret scanning** (gitleaks) + **dependency scan** (pip-audit, Dependabot) dans `ci.yml`.
12. **pytest-xdist** pour paralléliser quand la suite dépassera 30 s.
13. **Mutation testing** (mutmut) ciblé sur `bankroll.py` et `best_bets_logic.py` — les modules où les tests sont denses, pour mesurer leur qualité réelle.
14. **Preview environment par PR** (Railway supporte ça nativement via PR deployments).

## 6. Risques identifiés

| Risque | Probabilité | Impact | Mitigation recommandée |
|---|---|---|---|
| Déploiement d'une régression silencieuse sur `trigger.py` (résolution ROI, Kelly, combos) | Élevée (90% du code non couvert) | Financier (Kelly stake incorrect, combos restant PENDING — leçon 27) | P1-#7, P1-#9 |
| Workflow `daily-pipeline.yml` exécute du code legacy — les notifs Telegram et les évaluations quotidiennes peuvent être déconnectées du vrai pipeline | Moyenne | Données utilisateur incohérentes avec le dashboard | P0-#1 |
| Le worker Railway ne démarre pas (bloc `[services.deploy]` unique) — aucune alerte car pas de healthcheck worker | Moyenne | Jobs APScheduler jamais exécutés (leçon 64 déjà prévenue) | P0-#2 |
| Scripts `src/test_*.py` attrapés par un `pytest .` non scopé → crash réseau Supabase à la collecte | Faible mais déjà vu (leçon 61) | CI rouge en cascade | P0-#3 |
| Couverture 21% → un contributeur supprime involontairement un path métier sans alerte CI | Élevée | Correctness | P1-#7 |
| `mypy || true` ignore des régressions de typage (fixture_id mélange int/str, cf leçon 2026-04-04) | Élevée | Bugs RLS / queries | P1-#8 |
| Stripe webhook (`stripe_webhook.py`, 185 LOC, 6 fonctions `_snake`) non testé end-to-end — race conditions déjà documentées (leçon Stripe webhook check-then-act) | Moyenne | Facturation / duplication d'événements | Ajouter tests router dédiés |

## 7. Recommandations stratégiques

1. **Consolider la stack** avant d'ajouter des features. Le legacy `Projet_Football/` est un risque d'exécution (CI daily) et un bruit cognitif. Un PR de cleanup de 1 jour libère plusieurs semaines de confusion.
2. **Contractualiser la couverture par paliers**, pas par un objectif global flou. Ex. écrire dans `CLAUDE.md` : "chaque nouveau module dans `api/routers/*_logic.py` doit être ≥ 80%". Le seuil global monte mécaniquement.
3. **Transformer `trigger.py` et `stripe_webhook.py`** en router fin + module logique pur, sur le modèle éprouvé de `best_bets_logic.py`. C'est la plus grosse dette de testabilité (leçon 62 déjà identifiée).
4. **Un seul descripteur de déploiement** (`railway.toml` correctement rempli). Supprimer `Procfile` et `nixpacks.toml` si redondants. La multi-source masque les bugs (leçon 28 Railway root dir, déjà un cas vécu).
5. **Rendre les gates de qualité réellement bloquants** : mypy sans `|| true` sur les modules stables, `--cov-fail-under` qui progresse, tests flaky zéro-tolérance. Une CI qui bloque *parfois* ne bloque pas.
6. **E2E minimal avant tout nouveau marché sportif**. Le pivot `feat/pivot-probas-sportives` ajoute du scope — sans e2e, chaque nouveau marché ajoute N bugs potentiels × nombre de sports.

## 8. Liens internes

- `ProbaLab/tasks/baseline_2026-04-10.md` — baseline couverture 19%, discordance avec CLAUDE.md documentée
- `ProbaLab/tasks/coverage_gaps.md` — plan détaillé Phase 1.2/1.3/1.4/1.5 (§5 P1 recommandations)
- `ProbaLab/tasks/lessons.md` lignes 28, 60-63 — racines des recommandations P0
- `ProbaLab/pytest.ini` — marqueurs `integration` / `slow`
- `.github/workflows/ci.yml:54` — `--cov-fail-under=21` (réduit après leçon 60)
- `.github/workflows/daily-pipeline.yml:34` — cible `Projet_Football/` (legacy)
- `ProbaLab/railway.toml:4-22` — deux services, un seul `[services.deploy]`
- `ProbaLab/api/routers/best_bets_logic.py` — **bon pattern** à répliquer sur `trigger.py` et `stripe_webhook.py`
- `ProbaLab/tests/test_best_bets_logic.py` (87 tests) + `tests/test_best_bets_router.py` (13 tests) — bon modèle de découpage logique vs router
