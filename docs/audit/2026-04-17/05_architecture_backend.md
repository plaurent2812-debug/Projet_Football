# 05 — Architecture backend

> Profondeur : **Medium** (confirme/infirme l'audit architecture du 2026-04-10, voir `ProbaLab/tasks/todo.md` Phase 4 et baseline `tasks/baseline_2026-04-10.md`).
> Scope : FastAPI (`ProbaLab/api/`), scheduler APScheduler (`ProbaLab/worker.py`), modules métier (`ProbaLab/src/`), `pyproject.toml`, dépendances.
> Méthode : lecture seule, preuves `fichier:ligne` ou leçon N.

---

## 1. Périmètre audité

- **17 routers FastAPI** (`ProbaLab/api/routers/`) montés dans `api/main.py:98-113` sous FastAPI 0.109+.
- **1 worker cron** (`ProbaLab/worker.py`, 370 LOC) — APScheduler `BlockingScheduler` avec 18 jobs cron `Europe/Paris`.
- **56 modules métier** dans `ProbaLab/src/` (brain, blender, bankroll, ticket_generator, fetchers, NHL pipeline, training, monitoring).
- **Packaging** : `pyproject.toml` (setuptools, `requires-python=">=3.10"`) + `requirements.txt` à plat (pas de lock).
- **Middlewares** : CORS, Security Headers, Request-ID, Prometheus Instrumentator, rate-limiting slowapi.

Total : **13 872 LOC** Python (hors tests), dont **3 988 LOC concentrées dans 3 routers** (29 %).

---

## 2. État actuel

### 2.1 Ce qui fonctionne bien

- **`api/main.py` épuré** (225 LOC). Lifespan propre, Security Headers présent (`api/main.py:147-161`), exception handler global qui masque les stacks (`api/main.py:179-186`) — conforme leçon 15 et 42.
- **Middlewares ordonnés LIFO correctement commentés** (`api/main.py:143-146`, `164-165`) — preuve de compréhension du stack Starlette.
- **Auth centralisée** dans `api/auth.py` (`verify_cron_auth`, `verify_internal_auth`) — utilisée par les routers sensibles (`best_bets.py:716`, `best_bets.py:741`, `best_bets.py:769`, `best_bets.py:792`). `CRON_SECRET` comparé via `hmac.compare_digest` (`trigger.py:44`) — leçon 19 appliquée.
- **Rate-limiting fail-loud** : `api/rate_limit.py` expose `RATE_LIMITING` et un no-op si slowapi indisponible ; le main enregistre l'exception handler conditionnellement (`api/main.py:93-95`) — leçon 40 appliquée.
- **Logique métier Best Bets extraite** : `api/routers/best_bets_logic.py` (365 LOC) contient `evaluate_football_combo`, `evaluate_single_football_market`, `evaluate_nhl_player_market`, `calc_stats` — conforme à la leçon 62 (routers = glue, logique = module pur).
- **Anti-pattern `sys.path.insert` éradiqué** : **0 occurrence** dans `src/` et `api/` (seule mention résiduelle dans `tasks/lessons.md`). Le `pip install -e .` via `pyproject.toml` fonctionne — leçon 44 appliquée.
- **`response_model=` utilisé** sur 13 endpoints (best_bets 3, nhl 4, predictions 2, news 1, expert_picks 3) — typage Pydantic côté sortie présent sur les routes critiques.
- **APScheduler worker structuré** : `max_instances=1` + `coalesce=True` sur chaque job (`worker.py:294-334`), jobs groupés par fréquence, docstrings explicitant les dépendances inter-jobs (`job_nhl_fetch_odds` doit tourner APRÈS `job_nhl_pipeline`, voir `worker.py:159-166`).
- **Gating intelligent** sur `job_live` pour économiser le quota API (`worker.py:38-40`).
- **Bankroll atomique** via RPC Postgres `place_bet_atomic` (`src/bankroll.py:86-95`) avec fallback legacy — leçon 21 appliquée.
- **Prometheus /metrics exposé** (`api/main.py:90`) — observabilité de base OK.

### 2.2 Dette technique / bugs latents

- **`api/routers/trigger.py` — 1687 LOC, 27 endpoints, 3 responsabilités mélangées** : admin users (lines 83-218), live half-time analysis (lines 227-440), data pipelines (lines 477-695, 728-810, 924-1203), NHL-specific (lines 1205-1653), reflection (lines 1675-1687). C'est un **god-router**. Aucun `response_model=` sur aucune route. Aucun découpage par sous-prefix.
- **`api/routers/best_bets.py` — 1428 LOC, 9 endpoints, mixe** : GET best bets (44-706), update result (709-735), save (738-759), NHL stats fetch (762-781), NHL odds fetch (784-802), backfill (805-845), resolve (848-1105), stats (1107-1291), history (1293-1428). La fonction `get_best_bets` seule fait ~660 LOC. Mérite un package `best_bets/` (reader.py, writer.py, resolver.py, stats.py).
- **`datetime.now()` nu encore présent dans le code (hors `worker.py`)** — leçon 22 violée :
  - `trigger.py:319, 592, 945, 983, 1087, 1208, 1227, 1456` (7 occurrences)
  - `best_bets.py:67, 727, 794, 957, 1078` (5 occurrences)
  - `admin.py:118, 126, 150, 185, 217` (5 occurrences)
  - `monitoring.py:98, 99, 164, 174, 178` (5 occurrences)
  - `teams.py:27`, `bankroll.py:233`, `src/nhl/*.py` (5+ occurrences)
  - Total : **~40 occurrences `datetime.now()` + 14 `datetime.utcnow()` (déprécié Python 3.12)**. Risque : comparaisons naive vs aware, fenêtres UTC incohérentes, piège déjà documenté côté NHL (leçon 66).
- **`trigger.py:448` `datetime.utcnow()`** dans `check-active-matches` → `.isoformat()` sans `Z` → comparaison string avec `f"{today}T00:00:00Z"` ailleurs = bug latent en frontière UTC.
- **Migration Trigger.dev → APScheduler incomplète (leçon 64)** : le worker couvre 18 jobs, mais le router `trigger.py` expose toujours 27 endpoints censés être appelés par Trigger.dev (`/run-daily-pipeline`, `/detect-value-bets`, `/nhl-value-bets`, `/nhl-run-pipeline`, `/run-reflection`, `/football-momentum`, `/nhl-ml-reminder`, `/nhl-fetch-odds`, `/fetch-lineups`, etc.). Plusieurs sont-ils encore câblés ? `api/main.py:15` porte le commentaire `"APScheduler removed — all scheduling handled by Trigger.dev"` qui contredit directement la présence du worker APScheduler. **Un des deux commentaires est faux.** La dualité "cron interne + endpoints cron externes" est une source de drift (cf. bug NHL schedule de la leçon 64).
- **Threading manuel pour long-jobs** : `trigger.py:743`, `admin.py:155, 190, 263` lancent `threading.Thread(daemon=True)` dans des endpoints FastAPI. Anti-pattern FastAPI : préférer `BackgroundTasks` (utilisé uniquement dans `telegram.py:496`) ou un vrai job queue (Celery / RQ / arq). Risque : threads orphelins au redémarrage, pas de retry, pas d'observabilité.
- **`requires-python = ">=3.10"`** dans `pyproject.toml:8` alors que la leçon 45 précise que pyenv local était 3.10.12 ; Python 3.10 atteindra EOL en octobre 2026. Pas de lockfile (pas de `poetry.lock`, pas de `uv.lock`, pas de `requirements.lock`) → dépendances non reproductibles.
- **Dépendances non pinées finement** : `scikit-learn==1.5.2` (pinée, OK), mais `fastapi>=0.109.0`, `xgboost>=2.0.0`, `supabase>=2.0.0` en `>=` ouvert = upgrades majeures silencieuses possibles entre environnements.

### 2.3 Code smells repérés

- **Imports lazy systématiques dans les endpoints** : `trigger.py:933 (from run_pipeline import ...)`, `trigger.py:1405, 1424, 1610, 1628, 1680` — dizaines d'imports locaux dans le corps des fonctions. Raison historique (éviter side-effects au boot), mais à présent que les modules `src/` sont propres (leçon 47 appliquée via `src/constants.py`), ces imports devraient remonter en tête de fichier.
- **Absence totale de `response_model` dans `trigger.py`** (27 endpoints, 0 `response_model=`). Les retours sont des `dict` libres → documentation OpenAPI vide, impossibilité pour le frontend de typer.
- **`update_live_scores` (`trigger.py:478-695`, 217 LOC)** : une fonction unique qui fetch live, parse statuts, batch upsert, détecte stale, re-fetch finished, parse events — 5 responsabilités. Ingérable à tester.
- **Duplication de logique status-mapping** : `STATUS_MAP` redéfini dans `trigger.py:494-498`, `trigger.py:627-637`, `trigger.py:1445-1451` — 3 copies divergentes.
- **Requests externes sans retry** dans les routers : `trigger.py:1468 (requests.get NHLE)`, `trigger.py:1548 (landing NHLE)`, `trigger.py:187 (API-Football status)`, `best_bets.py` (via `fetch_nhl_odds`). `api_get` dispose d'un retry côté `src/config.py` (leçon 18) mais `requests.get` brut ne l'utilise pas → perte de data silencieuse possible.
- **`asyncio`/`await` absent dans 95 % des endpoints** : seulement 10 `async def` sur ~90 endpoints. FastAPI tourne en thread-pool sync par défaut → perte de throughput sur les I/O Supabase.
- **Hardcoded URLs** : `https://api.probalab.net` (`worker.py:84`), `https://api-web.nhle.com/v1/...` (`trigger.py:1461-1463, 1549`) — devrait être en config.
- **Mélange `print()` + `logger` dans `api/evaluate_predictions.py:67,185`** — logs non structurés hors stack JSON.
- **`HTTPException(detail=str(e))` dans `stripe_webhook.py`** (1 occurrence restante) — leçon 15 partiellement appliquée.
- **Commentaire obsolète `api/main.py:15`** : `"# APScheduler removed — all scheduling handled by Trigger.dev"` faux depuis la réintroduction du worker.

### 2.4 Gaps vs. bonnes pratiques FastAPI/SaaS

- Pas d'architecture en couches (routers → services → repositories). La couche "service" existe seulement pour `api/services/email.py`. Ailleurs, les routers parlent directement à `supabase.table(...)` (couplage fort → tests nécessitent mocker Supabase partout).
- Pas de DTO d'entrée sur la majorité des endpoints POST — `body: dict` utilisé dans `best_bets.py:764, 786` au lieu de schemas Pydantic → pas de validation 422 automatique.
- Pas de dependency injection pour Supabase (`from src.config import supabase` est un singleton global importé partout) — impossible à mocker sans monkey-patch.
- Pas de versioning d'API (`/api/v1/...`). Tout est sous `/api/` direct → rupture de contrat future = breaking change frontal.
- Pas de pagination standardisée sur les endpoints list (ex : `/api/best-bets/history` — `best_bets.py:1293`).
- Observabilité : Prometheus expose les métriques HTTP standards, mais **aucun Sentry / Rollbar** pour les exceptions applicatives ; audit log admin absent malgré la leçon 43 qui l'exige.
- Pas de CI de type "contract test" qui valide la shape des réponses — leçon 59 documente un bug shape qui a cassé la prod.

---

## 3. Niveau de maturité : **L2/L5** (quasi-L3)

- **L1 – MVP** : dépassé. Structure modulaire, CI, auth, rate-limit, health-check, métriques Prometheus en place.
- **L2 – Production stable** : **atteint**. Middlewares sécurité, exception handler global, logique métier partiellement extraite, pyproject.toml propre, worker cron opérationnel, plus de `sys.path.insert`.
- **L3 – Industrialisable** : **non atteint**. Bloquants : 2 god-routers (3 115 LOC à 2), 40+ `datetime.now()` nus, dualité scheduler interne/externe non résolue, threading brut dans endpoints, pas de DI, pas de versioning API, pas de lockfile.
- **L4 – Scalable / multi-tenant** : hors scope (nécessiterait async-first, repository pattern, jobs queue propre, feature flags, blue/green).
- **L5 – Platform-grade** : très loin.

**Verdict** : L2 solide, bord L3. Le travail de consolidation post-audit 2026-04-10 a effacé les dettes les plus bruyantes (sys.path, sécurité, main.py), mais les deux monolithes `trigger.py` et `best_bets.py` portent encore 23 % du code backend et restent intouchables sans extraction progressive.

---

## 4. Benchmark vs. standard industrie

Référence : **FastAPI production-grade patterns** (cf. Netflix Dispatch, Jonra Springs, Full-Stack FastAPI template de tiangolo), **architecture hexagonale / DDD léger** adapté au Python.

| Critère | Standard industrie | ProbaLab |
|---|---|---|
| Découpage router | < 300 LOC, < 10 endpoints par router | `trigger.py` 1687 LOC / 27 endpoints, `best_bets.py` 1428 / 9 |
| Couches (router/service/repo) | 3 couches obligatoires | 2 partielles (router + logic module pour best_bets uniquement) |
| DI Supabase / DB | `Depends()` sur session DB | Singleton `supabase` global importé |
| Typage entrée/sortie | 100 % Pydantic I/O | ~70 % sortie, ~40 % entrée |
| Async-first I/O | `async def` + `httpx.AsyncClient` | 10 endpoints async sur ~90 |
| Job scheduling | 1 seul mécanisme (cron interne OU worker queue) | APScheduler + endpoints Trigger.dev cohabitent |
| Background work | `BackgroundTasks` ou Celery/arq | `threading.Thread(daemon=True)` dans routes |
| Secrets / config | `pydantic-settings` avec validation | `os.getenv` disséminé (~30 occurrences) |
| Lockfile | `poetry.lock` / `uv.lock` obligatoire | Absent (`requirements.txt >=`) |
| API versioning | `/api/v1/`, `/api/v2/` | `/api/` non versionné |
| Observabilité applicative | Sentry + Prometheus + logs JSON | Prometheus + logs JSON, pas de Sentry |
| Audit log admin | Table dédiée + dashboard | Absent (leçon 43 non appliquée) |

**Score estimé : 5.5 / 11 critères satisfaits** — milieu de peloton, cohérent avec L2.

---

## 5. Gaps pour passer au niveau supérieur

### P0 — Bloquants L3 (2-3 semaines)

1. **Découper `trigger.py` en package** `api/routers/trigger/` : `admin.py` (users/stats/quota), `live.py` (halftime + update-live-scores), `pipeline.py` (daily/recap/value-bets), `nhl.py` (nhl-* endpoints), `reflection.py`. Cible : 5 fichiers < 400 LOC chacun. Extraire aussi la logique dans `src/services/` (live_analysis, pipeline_runner, nhl_runner).
2. **Découper `best_bets.py` en package** `api/routers/best_bets/` : `reader.py` (GET), `writer.py` (PATCH/POST save), `resolver.py` (resolve + backfill), `stats.py` (stats + history). La logique existe déjà pour partie dans `best_bets_logic.py` (bien fait) — continuer.
3. **Trancher sur le scheduler** : soit on garde APScheduler interne et on **supprime les 27 endpoints `/api/trigger/*`** devenus doublons, soit on garde Trigger.dev et on supprime `worker.py`. État actuel = double dette. Le commentaire `api/main.py:15` doit être mis à jour une fois tranché.
4. **Éradiquer `datetime.now()` / `datetime.utcnow()`** : 54 occurrences à remplacer par `datetime.now(timezone.utc)` (leçon 22). Un `ruff` custom rule ou un grep CI bloquerait toute régression.

### P1 — Robustesse (1-2 semaines)

5. **Remplacer `threading.Thread` par `BackgroundTasks`** (ou mieux, **arq** / **dramatiq**) pour `retrain_models` (`trigger.py:743`), `run_pipeline` (`admin.py:155, 190`), et `run_scores` (`admin.py:263`). Ajouter visibilité via Prometheus (gauge "jobs_running").
6. **Introduire `pydantic-settings`** pour centraliser `os.getenv` dispersés : `CRON_SECRET`, `API_FOOTBALL_KEY`, `TELEGRAM_*`, `STRIPE_*`, `ALLOWED_ORIGINS`, `API_BASE_URL`. Fail-fast au boot si champ requis manquant.
7. **Ajouter lockfile** : migration vers `uv` ou `poetry` ; CI qui échoue si `uv.lock` pas committé.
8. **Injecter Supabase par `Depends(get_supabase)`** au minimum dans les 3 gros routers → tests sans monkey-patch global.
9. **`response_model=` obligatoire** sur tout endpoint `/api/*` : ajouter un test qui lit le schéma OpenAPI et échoue si un endpoint n'a pas de response model.
10. **Retry systématique pour les clients HTTP externes** : wrapper `requests.get`/`httpx.get` dans un helper `http_get_with_retry` (tenacity) et remplacer les 8 appels bruts dans `api/` (leçon 18 étendue).

### P2 — Industrialisation (3-4 semaines)

11. **Async-first** sur les endpoints I/O-bound (Supabase via `httpx` async, API-Football). Gain p50 estimé : -40 % sous charge.
12. **API versioning** `/api/v1/` + reverse proxy côté Railway pour découpler backend/frontend.
13. **Audit log admin** (leçon 43) : table `admin_audit_log` + décorateur `@audit_log` sur `verify_internal_auth`.
14. **Sentry** pour les exceptions applicatives (`logger.exception` seul ne remonte pas d'alerte).
15. **Tests de contrat** (leçon 59) : un test qui instancie chaque `response_model` avec la shape attendue par le frontend — bloquerait les drifts shape.

---

## 6. Risques identifiés

| Risque | Sévérité | Probabilité | Preuve |
|---|---|---|---|
| Drift scheduler Trigger.dev ↔ APScheduler silencieux → job NHL cassé pendant X jours | Haute | Élevée (déjà arrivé, leçon 64) | `api/main.py:15` vs `worker.py:289` |
| Fenêtre UTC `datetime.now()` décalée → paris mal datés aux frontières de journée | Haute | Moyenne (déjà vu, leçons 22, 66) | 40+ occurrences |
| Thread daemon tué par restart Railway → pipeline ML à moitié exécuté, modèle corrompu | Haute | Moyenne | `trigger.py:743`, `admin.py:155-263` |
| Upgrade auto d'une dépendance majeure (fastapi, supabase, xgboost) | Moyenne | Moyenne | `requirements.txt` `>=` + pas de lock |
| `trigger.py` / `best_bets.py` intouchables → toute modif prend des heures | Haute | Certaine | 3 115 LOC cumulées |
| Pas de Sentry → erreur en prod = découverte uniquement si un user se plaint | Moyenne | Élevée | pas d'intégration |
| Audit log admin absent → actions admin non traçables (RGPD + forensic) | Moyenne | Faible | leçon 43 non appliquée |
| Dual import de `datetime, timezone` + `datetime.utcnow()` dans même fichier | Faible | Moyenne | `trigger.py:5` + `trigger.py:448` |

---

## 7. Recommandations stratégiques

1. **Figer la dualité scheduler en 2 semaines max**. Choisir APScheduler (déjà là, zéro coût externe) et transformer les 27 endpoints `/api/trigger/*` en endpoints de diagnostic (`GET /api/admin/jobs/{id}/trigger`) réservés à l'admin. Bénéfice immédiat : moins de drift, moins de dette conceptuelle.
2. **Ne pas tout refactorer d'un coup**. Sortir 1 sous-package par sprint. Ordre recommandé : (a) `trigger/admin.py` (270 LOC, risque minimal), (b) `trigger/nhl.py` (450 LOC, autonome), (c) `best_bets/resolver.py` (extension de `best_bets_logic.py` déjà fait).
3. **Ajouter un pre-commit ruff rule pour `datetime.now()` / `datetime.utcnow()` nu**. Migration massive (sed-friendly) + garde-fou permanent. Gain : ferme définitivement la leçon 22.
4. **Introduire `pydantic-settings` + un `Settings` singleton fail-fast**. Les 30 `os.getenv` actuels deviennent un objet typé, documenté, validé au boot — une heure de travail, ROI énorme sur l'onboarding.
5. **Documenter le contrat "router = glue, logique = service"** dans `CLAUDE.md`. Formaliser la leçon 62 pour éviter la récidive sur les futurs routers.
6. **Ne pas toucher à `best_bets_logic.py`** (365 LOC) — c'est le module le plus sain du backend, modèle à suivre.
7. **Reporter l'async-first** : L4 peut attendre. Prioriser L3 (découpage + scheduler + config) qui débloque tout.

---

## 8. Liens internes

- `ProbaLab/tasks/lessons.md` — leçons 18, 22, 42, 43, 44, 47, 62, 64 directement référencées.
- `ProbaLab/tasks/todo.md` — Phase 4 audit 2026-04-10 (baseline).
- `ProbaLab/tasks/baseline_2026-04-10.md` — métriques de référence.
- `ProbaLab/api/main.py` — entrée FastAPI.
- `ProbaLab/api/routers/trigger.py` — god-router #1.
- `ProbaLab/api/routers/best_bets.py` — god-router #2.
- `ProbaLab/api/routers/best_bets_logic.py` — modèle à suivre.
- `ProbaLab/worker.py` — APScheduler (18 jobs).
- `ProbaLab/pyproject.toml` — packaging.
- Annexes sœurs : `01_moteur_probabilites.md`, `02_machine_learning.md`, `03_monitoring_ml.md`, `04_nhl_specifique.md`.
