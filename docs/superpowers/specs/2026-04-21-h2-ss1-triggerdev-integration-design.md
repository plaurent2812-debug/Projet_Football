# H2-SS1 — Intégration Trigger.dev — Design

> **Parent project** : H2-SS1 (Modèle Optimal & Pipeline CLV)
> **This spec** : branchement du code H2-SS1 déjà livré dans l'architecture de scheduling réelle (Trigger.dev + endpoints FastAPI `/api/trigger/*`)

---

## Contexte

Le code H2-SS1 livré dans PR #7 (36 commits, merged sur main le 2026-04-19) ajoutait 4 cron jobs APScheduler dans `worker.py`. **Mais `worker.py` n'est lancé nulle part en prod** : Railway ne fait tourner que le service `web` (uvicorn), aucun worker séparé.

L'infrastructure de scheduling réelle est :

1. **Trigger.dev Cloud** → appelle des endpoints `/api/trigger/*` exposés par l'API FastAPI sur Railway
2. **GitHub Actions** `.github/workflows/daily-pipeline.yml` → cron 08:00 UTC qui exécute `run_pipeline.py full`

Les 4 jobs H2-SS1 (`job_odds_opening_snapshot`, `job_daily_clv_snapshot`, `job_feature_drift_check`, `job_schedule_closing_snapshots`) codés dans `worker.py` sont donc **orphelins** : ils n'ont jamais tourné en production.

Cette spec décrit comment brancher ces jobs dans Trigger.dev + endpoints FastAPI pour les activer sans modifier le code métier H2-SS1 (odds_ingestor, clv_engine, feature_drift, value_detector restent intacts).

---

## 1. Vue d'ensemble

**Nom** : H2-SS1 Phase Trigger.dev Integration

**Objectif** : Rendre le pipeline CLV H2-SS1 actif en production en l'intégrant à l'architecture existante (Trigger.dev + FastAPI), sans toucher au code métier déjà livré.

**Success criteria** :
1. 4 endpoints FastAPI `/api/trigger/clv/*` déployés, authentifiés, testés
2. 4 schedules Trigger.dev créés dans un nouveau fichier `clvPipeline.ts`
3. Les 4 schedules tournent aux heures fixées (08:00, 09:00, 09:30 UTC + polling `*/15`)
4. Premier snapshot opening observable dans `closing_odds` table dans les 24h post-deploy
5. Premier `run_daily_clv_snapshot` observable dans `model_health_log` dans les 48h post-deploy
6. Aucune régression sur les schedules Trigger.dev existants

**Non-objectifs (explicitement hors scope)** :
- Cleanup des commentaires `// ⚠️ DISABLED` trompeurs dans les 4 fichiers Trigger.dev existants (dette technique séparée)
- Migration/suppression de `worker.py` (mort-code, décision séparée)
- Upsert sur `model_health_log` (follow-up M5 du code review précédent)
- Dashboard admin SS2
- Refonte UX user SS3

---

## 2. Décisions owner figées (brainstorming 2026-04-21)

| # | Sujet | Décision |
|---|---|---|
| 1 | Horaires schedules | A — conforme spec original (08:00 opening / 09:00 CLV / 09:30 drift UTC) |
| 2 | Closing snapshots T-30min | A — polling unique `*/15 * * * *`, endpoint fetch les fixtures dont kickoff ∈ [now+15, now+45] |
| 3 | Naming endpoints | B — préfixe `/api/trigger/clv/*` pour grouping |
| 4 | Cleanup des commentaires DISABLED existants | A — on ne touche pas, scope limité aux 4 nouveaux schedules |

---

## 3. Architecture

### 3.1 Flux

```
┌──────────────────────────────────────────────────────────────────────┐
│ Trigger.dev Cloud (scheduler)                                         │
│  - clv-opening-snapshot  (0 8 * * *)                                  │
│  - clv-daily-snapshot    (0 9 * * *)                                  │
│  - clv-feature-drift     (30 9 * * *)                                 │
│  - clv-closing-tick      (*/15 * * * *)                               │
└────────────────────┬─────────────────────────────────────────────────┘
                     │ POST Authorization: Bearer ${CRON_SECRET}
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Railway web service (uvicorn api.main:app)                            │
│  /api/trigger/clv/opening          → run_snapshot("opening")          │
│  /api/trigger/clv/closing-tick     → filter fixtures + run_snapshot_for_fixtures │
│  /api/trigger/clv/daily-snapshot   → run_daily_clv_snapshot()         │
│  /api/trigger/clv/drift            → run_feature_drift_check() + alert│
└────────────────────┬─────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│ H2-SS1 code métier (inchangé)                                         │
│  src/fetchers/odds_ingestor.py                                        │
│  src/monitoring/clv_engine.py                                         │
│  src/monitoring/feature_drift.py                                      │
└──────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
              Supabase (closing_odds, model_health_log, predictions)
```

### 3.2 Composants par couche

**Couche Scheduling** (Trigger.dev, nouveau fichier)
- `trigger-worker/src/trigger/clvPipeline.ts` — 4 `schedules.task()` qui POSTent sur les endpoints avec `Authorization: Bearer ${CRON_SECRET}` et `standardRetry` (3 tentatives, backoff exponentiel)

**Couche API** (FastAPI, extension de `api/routers/trigger.py`)
- 4 nouvelles routes sous le prefix `/api/trigger/clv/*`
- Dépendance `verify_trigger_auth` (pattern existant)
- Handlers fins qui appellent directement les fonctions H2-SS1 existantes

**Couche Métier** (inchangée)
- `src/fetchers/odds_ingestor.run_snapshot()`, `run_snapshot_for_fixtures()`
- `src/monitoring/clv_engine.run_daily_clv_snapshot()`
- `src/monitoring/feature_drift.run_feature_drift_check()` + `drift_result_to_alert()`

### 3.3 Isolation & interfaces

| De | Vers | Interface |
|---|---|---|
| Trigger.dev schedule | FastAPI endpoint | HTTP POST + Bearer auth |
| FastAPI endpoint | H2-SS1 code métier | Appels Python directs (import) |
| H2-SS1 code métier | Supabase | Client service_role déjà initialisé (`src.config.supabase`) |

**Conséquence** : si demain on veut changer de scheduler (GitHub Actions, APScheduler Railway worker, cron server), on remplace juste la couche scheduling — les endpoints et le code métier sont stables.

---

## 4. Contrats d'endpoints

### 4.1 `POST /api/trigger/clv/opening`

**Auth** : `Authorization: Bearer ${CRON_SECRET}`
**Body** : `{}` (aucun paramètre)
**Handler** :
```python
@router.post("/clv/opening")
def clv_opening_snapshot():
    from src.fetchers.odds_ingestor import run_snapshot
    t0 = time.monotonic()
    n = run_snapshot(snapshot_type="opening")
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {"status": "ok", "rows_submitted": n, "duration_ms": duration_ms}
```
**Erreurs** :
- `OddsAPIQuotaExhausted` → `HTTPException(503, detail="quota exhausted")` + Telegram alert déjà géré dans `run_snapshot`
- `RuntimeError` (all sport_keys failed) → `HTTPException(500)` + Telegram alert déjà géré
- Autre → `HTTPException(500)` générique, log stack côté serveur

### 4.2 `POST /api/trigger/clv/closing-tick`

**Logique** :
```python
@router.post("/clv/closing-tick")
def clv_closing_tick():
    from datetime import datetime, timedelta, timezone
    from src.config import supabase
    from src.fetchers.odds_ingestor import run_snapshot_for_fixtures

    now = datetime.now(timezone.utc)
    window_start = (now + timedelta(minutes=15)).isoformat()
    window_end = (now + timedelta(minutes=45)).isoformat()

    # Fetch fixtures dont kickoff ∈ [T-45, T-15] (fenêtre 30min couvrant le polling */15)
    foot = supabase.table("fixtures").select("id").gte("date", window_start).lt("date", window_end).execute().data or []
    nhl = supabase.table("nhl_fixtures").select("game_id").gte("game_date", window_start).lt("game_date", window_end).execute().data or []
    fixture_ids = [str(f["id"]) for f in foot] + [str(f["game_id"]) for f in nhl]

    if not fixture_ids:
        return {"status": "ok", "snapshots": 0, "message": "no fixtures in window"}

    # Dedup : skip fixtures déjà snapshottés en closing (économise Odds API quota)
    done = supabase.table("closing_odds").select("fixture_id").in_("fixture_id", fixture_ids).eq("snapshot_type", "closing").execute().data or []
    done_ids = {r["fixture_id"] for r in done}
    to_snapshot = [fid for fid in fixture_ids if fid not in done_ids]

    if not to_snapshot:
        return {"status": "ok", "snapshots": 0, "already_done": len(done_ids)}

    n = run_snapshot_for_fixtures(to_snapshot)
    return {"status": "ok", "snapshots": n, "fixture_count": len(to_snapshot)}
```

**Pourquoi la fenêtre est 30min et non 15min** : le polling tourne toutes les 15min, donc pour garantir qu'un match soit capturé au moins une fois dans sa fenêtre T-45 à T-15, on prend la fenêtre complète de 30min. Double-capture est possible mais prévenue par le check `done_ids`.

### 4.3 `POST /api/trigger/clv/daily-snapshot`

**Handler** :
```python
@router.post("/clv/daily-snapshot")
def clv_daily_snapshot():
    from src.monitoring.clv_engine import run_daily_clv_snapshot
    result = run_daily_clv_snapshot()
    return {"status": "ok", "payload": result}
```

Le `run_daily_clv_snapshot` existant :
- Accepte `target_date=None` → calcule J-1 par défaut
- Retourne `{n_matches_clv, clv_vs_pinnacle_1x2, ...}` (cf. `src/monitoring/clv_engine.py`)
- Insert dans `model_health_log`

### 4.4 `POST /api/trigger/clv/drift`

**Handler** :
```python
@router.post("/clv/drift")
def clv_drift_check():
    from src.monitoring.feature_drift import run_feature_drift_check, drift_result_to_alert
    from src.notifications import send_telegram

    result = run_feature_drift_check(alpha=0.01, window_days=30)
    alert = drift_result_to_alert(result, threshold=5)
    if alert:
        send_telegram(alert)
    return {"status": "ok", "n_drifted": result["n_drifted"], "n_features": result["n_features"], "alert_sent": alert is not None}
```

---

## 5. Trigger.dev schedules (fichier unique `clvPipeline.ts`)

```typescript
import { schedules } from "@trigger.dev/sdk";

const API_URL = process.env.API_URL || "https://web-production-ff663.up.railway.app";
const CRON_SECRET = process.env.CRON_SECRET || "";

const standardRetry = {
    maxAttempts: 3,
    factor: 1.5,
    minTimeoutInMs: 3000,
    maxTimeoutInMs: 60000,
    randomize: true,
};

const cronHeaders = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${CRON_SECRET}`,
};

async function callEndpoint(path: string, label: string): Promise<object> {
    const res = await fetch(`${API_URL}${path}`, {
        method: "POST",
        headers: cronHeaders,
        body: JSON.stringify({}),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`[${label}] ${path} failed (${res.status}): ${text}`);
    }
    const result = await res.json();
    console.log(`[${label}] OK:`, result);
    return result;
}

export const clvOpeningSnapshot = schedules.task({
    id: "clv-opening-snapshot",
    cron: "0 8 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/opening", "clv-opening"),
});

export const clvDailySnapshot = schedules.task({
    id: "clv-daily-snapshot",
    cron: "0 9 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/daily-snapshot", "clv-daily"),
});

export const clvFeatureDrift = schedules.task({
    id: "clv-feature-drift",
    cron: "30 9 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/drift", "clv-drift"),
});

export const clvClosingTick = schedules.task({
    id: "clv-closing-tick",
    cron: "*/15 * * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/closing-tick", "clv-closing"),
});
```

---

## 6. Error handling

| Composant | Erreur | Stratégie |
|---|---|---|
| Trigger.dev schedule | Fetch timeout / network | `standardRetry` 3x (1s, 1.5s, 2.25s base) |
| Trigger.dev schedule | Endpoint returns 5xx | `standardRetry`, puis notification dashboard Trigger.dev |
| FastAPI endpoint | `OddsAPIQuotaExhausted` | `HTTPException(503)` + Telegram alert (déjà géré dans le code métier) |
| FastAPI endpoint | `RuntimeError all sport_keys failed` | `HTTPException(500)` + Telegram (déjà géré) |
| FastAPI endpoint | Exception non catchée | `HTTPException(500)` générique, log stack côté serveur |
| closing-tick | Aucun fixture en fenêtre | Return 200 avec message `no fixtures in window` (non-error) |
| closing-tick | Tous déjà snapshottés | Return 200 avec `already_done: N` (non-error) |

**Principe général** : fail-loud en cas d'erreur critique (lesson 41), 200 silencieux en cas de non-op légitime.

---

## 7. Tests

### 7.1 Unit tests endpoints (`tests/test_clv_trigger_endpoints.py` — nouveau)

Pattern : `TestClient(app)` + `monkeypatch` des fonctions H2-SS1 pour éviter DB/network.

```python
def test_clv_opening_requires_auth(client):
    resp = client.post("/api/trigger/clv/opening")
    assert resp.status_code == 401

def test_clv_opening_calls_run_snapshot(client, monkeypatch):
    called_with = {}
    def fake_run(snapshot_type):
        called_with["snapshot_type"] = snapshot_type
        return 42
    monkeypatch.setattr("src.fetchers.odds_ingestor.run_snapshot", fake_run)
    resp = client.post("/api/trigger/clv/opening", headers={"Authorization": f"Bearer {CRON_SECRET}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["rows_submitted"] == 42
    assert called_with["snapshot_type"] == "opening"

def test_clv_closing_tick_skips_already_snapshotted(client, monkeypatch):
    # 2 fixtures in window, 1 already snapshotted → only 1 new call
    ...

def test_clv_daily_snapshot_returns_result(client, monkeypatch):
    ...

def test_clv_drift_sends_telegram_when_threshold_exceeded(client, monkeypatch):
    ...
```

Coverage ciblée : ≥85% sur les 4 handlers.

### 7.2 Integration locale

Commande manuelle après déploiement :
```bash
curl -X POST https://api.probalab.net/api/trigger/clv/opening \
  -H "Authorization: Bearer $CRON_SECRET" \
  -H "Content-Type: application/json" \
  -d '{}'
```
Attendu : JSON `{status: "ok", rows_submitted: >0, duration_ms: <10000}` (si The Odds API répond).

---

## 8. Déploiement

### 8.1 Séquence

1. **PR GitHub** avec les 3 fichiers modifiés/créés (cf. §9)
2. **Merge sur main** → Railway déploie auto les nouveaux endpoints
3. **Smoke test manuel** : `curl` sur chaque endpoint pour valider qu'ils répondent
4. **Deploy Trigger.dev** : `cd ProbaLab/trigger-worker && npx trigger.dev@latest deploy` (ou push auto selon config Trigger.dev)
5. **Vérification dashboard Trigger.dev** : les 4 nouveaux schedules apparaissent et ont une next-run-time valide
6. **Attente 24h** → premier snapshot opening visible en DB

### 8.2 Rollback

- **Côté endpoints** : revert du commit sur main, Railway redéploie
- **Côté Trigger.dev** : disable manuel des 4 schedules dans le dashboard, ou revert + redeploy trigger-worker

Les migrations DB (051/052/053) sont déjà appliquées — pas de rollback DB nécessaire.

---

## 9. Files touched

### Nouveaux

| Path | Rôle |
|---|---|
| `ProbaLab/trigger-worker/src/trigger/clvPipeline.ts` | 4 schedules Trigger.dev (opening, daily-snapshot, drift, closing-tick) |
| `ProbaLab/tests/test_clv_trigger_endpoints.py` | Tests unit des 4 endpoints avec FastAPI TestClient |

### Modifiés

| Path | Change |
|---|---|
| `ProbaLab/api/routers/trigger.py` | +4 routes sous `/api/trigger/clv/*` |

### Inchangés (dépendances import)

- `ProbaLab/src/fetchers/odds_ingestor.py` — appelé par les endpoints
- `ProbaLab/src/monitoring/clv_engine.py` — appelé par les endpoints
- `ProbaLab/src/monitoring/feature_drift.py` — appelé par les endpoints
- `ProbaLab/src/notifications.py` — `send_telegram` réutilisé

---

## 10. Budget, timing, infra

### 10.1 Budget

- **Trigger.dev** : 4 schedules supplémentaires. Plan Hobby gratuit = 10k task runs/mois. Volume H2-SS1 :
  - opening: 30 runs/mois
  - daily-snapshot: 30 runs/mois
  - drift: 30 runs/mois
  - closing-tick: 2880 runs/mois (*/15 min = 96/jour × 30)
  - **Total : ~2970 runs/mois** → bien sous le free tier
- **Railway** : aucun coût additionnel (même service web)
- **Supabase** : aucun coût additionnel (migrations déjà appliquées)

### 10.2 Timing

- Dev Phase 1 (3 endpoints fixes + tests) : ~45 min
- Dev Phase 2 (closing-tick endpoint + dedup logic + test) : ~30 min
- Déploiement + smoke test : ~15 min
- **Total : ~1h30 à 2h**

### 10.3 Compute

- Endpoint opening : 2-3 min par run (fetch 9 sport_keys × 4 markets)
- Endpoint closing-tick : 5-30 sec selon nb fixtures dans la fenêtre
- Endpoint daily-snapshot : ~1-2 min
- Endpoint drift : ~30 sec

**Total/jour : ~8 min compute Railway web** (négligeable sur plan actuel).

---

## 11. Risques identifiés

| # | Risque | Sévérité | Mitigation |
|---|---|---|---|
| R1 | Collision avec schedules Trigger.dev existants à 07:00 / 08:00 UTC | Basse | Horaires décalés (07:00 → pipeline data, 08:00 → CLV opening, 09:00 → CLV snapshot). Pas de dépendance bloquante entre les deux pipelines. |
| R2 | `closing-tick` double-snapshot le même match si polling chevauche | Basse | UNIQUE constraint `closing_odds` + pré-check `done_ids` côté endpoint |
| R3 | Trigger.dev down → pas de snapshots pendant X heures | Moyenne | Le jour suivant 08:00 UTC opening capture quand même les nouveaux matchs. Les CLV computations ont un buffer de plusieurs jours (J-1 query) |
| R4 | `CRON_SECRET` mal configuré Trigger.dev → tous les calls 401 | Moyenne | Smoke test manuel post-deploy ; alert Telegram sur erreur fetch côté Trigger.dev |
| R5 | Volume closing-tick dépasse free tier Trigger.dev | Basse | 2880/mois sur 10k free = marge 3.5x. Si dépassement, plan Pro = $20/mois |
| R6 | Endpoint closing-tick génère trop de requêtes Odds API (quota) | Moyenne | Dedup `done_ids` déjà prévu. Par ailleurs, `run_snapshot_for_fixtures` filtre les events post-parse → même appels API que le polling existant |

---

## 12. Cohérence avec décisions antérieures

- ✅ Conforme budget ≤ 50 €/mois (Trigger.dev gratuit)
- ✅ Utilise le scheduler qui tourne déjà en prod (Trigger.dev), pas d'infrastructure nouvelle
- ✅ Le code métier H2-SS1 livré dans PR #7 est réutilisé tel quel
- ✅ Pattern d'auth existant (`verify_trigger_auth` + `CRON_SECRET`)
- ✅ Respecte lesson 41 (fail-loud) et lesson 22 (timezones UTC)

---

## 13. Prochaine étape

Invoquer `writing-plans` pour produire le plan d'exécution tâche-par-tâche :
- Task 1 : Endpoint `/api/trigger/clv/opening` + test
- Task 2 : Endpoint `/api/trigger/clv/daily-snapshot` + test
- Task 3 : Endpoint `/api/trigger/clv/drift` + test
- Task 4 : Endpoint `/api/trigger/clv/closing-tick` + dedup logic + test
- Task 5 : Fichier Trigger.dev `clvPipeline.ts` (4 schedules)
- Task 6 : Smoke test local + commit + PR
- Task 7 : Deploy Railway + smoke test prod
- Task 8 : Deploy Trigger.dev + vérification dashboard
- Task 9 : Observation 24h premier snapshot
