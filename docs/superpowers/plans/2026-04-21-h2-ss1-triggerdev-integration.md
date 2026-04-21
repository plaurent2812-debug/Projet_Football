# H2-SS1 — Trigger.dev Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Brancher les 4 jobs H2-SS1 (odds opening/closing, daily CLV, feature drift) dans l'architecture de scheduling réelle (Trigger.dev + endpoints FastAPI) pour rendre le pipeline CLV actif en production.

**Architecture:** 4 endpoints `POST /api/trigger/clv/*` exposés dans `api/routers/trigger.py`, protégés par `verify_trigger_auth`, qui délèguent directement aux fonctions H2-SS1 déjà livrées (`run_snapshot`, `run_daily_clv_snapshot`, `run_snapshot_for_fixtures`, `run_feature_drift_check`). 4 schedules Trigger.dev dans un nouveau fichier `clvPipeline.ts` (cron fixes 08:00 / 09:00 / 09:30 UTC + polling `*/15 * * * *` pour les closing snapshots T-30min).

**Tech Stack:** FastAPI (endpoints), pytest + `TestClient` (tests), Trigger.dev SDK v3 (TypeScript), Railway (Python web service), Supabase (Postgres).

**Reference documents:**
- Spec : [docs/superpowers/specs/2026-04-21-h2-ss1-triggerdev-integration-design.md](../specs/2026-04-21-h2-ss1-triggerdev-integration-design.md)
- Parent spec : [docs/superpowers/specs/2026-04-18-h2-ss1-modele-optimal-clv-design.md](../specs/2026-04-18-h2-ss1-modele-optimal-clv-design.md)

**Working directory :** depuis le root du repo `/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab`. Le paquet Python vit sous `ProbaLab/`. Les sous-commandes `pytest`, `ruff` et `ruff format` doivent être lancées depuis `ProbaLab/` (c'est là que vit `pytest.ini` et la vraie racine du package).

**Context note on `api/routers/trigger.py` header comment**
Le fichier porte un docstring historique qui dit *"APScheduler (worker.py) est la SEULE source de scheduling automatique… Ne jamais en faire des crons depuis Trigger.dev"*. **Ce commentaire est obsolète** : APScheduler n'est pas lancé en prod (pas de worker Railway), Trigger.dev EST de facto le scheduler. La Task 1 met à jour ce docstring AVANT d'ajouter les endpoints, pour éviter de laisser un comment trompeur persister.

---

## File Structure

### Nouveaux fichiers

| Path | Rôle |
|---|---|
| `ProbaLab/tests/test_clv_trigger_endpoints.py` | Tests des 4 endpoints avec `TestClient` FastAPI + monkeypatch des fonctions H2-SS1 |
| `ProbaLab/trigger-worker/src/trigger/clvPipeline.ts` | 4 schedules Trigger.dev appelant les endpoints via `fetch` |

### Fichiers modifiés

| Path | Raison |
|---|---|
| `ProbaLab/api/routers/trigger.py` | 1. Mise à jour du docstring historique obsolète. 2. Ajout de 4 endpoints sous `/api/trigger/clv/*` |

### Fichiers inchangés (réutilisés)

- `ProbaLab/src/fetchers/odds_ingestor.py` — fonctions `run_snapshot`, `run_snapshot_for_fixtures`
- `ProbaLab/src/monitoring/clv_engine.py` — fonction `run_daily_clv_snapshot`
- `ProbaLab/src/monitoring/feature_drift.py` — `run_feature_drift_check`, `drift_result_to_alert`
- `ProbaLab/src/notifications.py` — `send_telegram`

---

## Task 1 : Refresh du docstring de `trigger.py` (préparation)

**Files:**
- Modify: `ProbaLab/api/routers/trigger.py:3-20`

- [ ] **Step 1 : Lire le docstring actuel**

Depuis le repo root :

Run: `sed -n '1,20p' ProbaLab/api/routers/trigger.py`

Vérifier que l'en-tête contient bien la phrase `APScheduler (worker.py) est la SEULE source de scheduling automatique`.

- [ ] **Step 2 : Remplacer le docstring**

Ouvre `ProbaLab/api/routers/trigger.py`. Remplace TOUT le docstring de module (de la première ligne `"""` jusqu'au `"""` de fermeture, environ lignes 1 à 20) par :

```python
"""
api/routers/trigger.py — Endpoints admin/trigger pour ProbaLab.

SOURCE DE VÉRITÉ DU SCHEDULING (MAJ 2026-04-21) :
  En production, Trigger.dev Cloud est le scheduler actif — il appelle
  ces endpoints via HTTP POST authentifiés par CRON_SECRET.
  `worker.py` (APScheduler) n'est PAS lancé sur Railway — les cron jobs
  qui y sont définis sont dormants. Toute nouvelle routine périodique
  doit passer par Trigger.dev + un endpoint ici, PAS par APScheduler.

ENDPOINTS CLV (H2-SS1, ajoutés 2026-04-21) sous /api/trigger/clv/* :
  - POST /clv/opening          → run_snapshot("opening")  [08:00 UTC]
  - POST /clv/daily-snapshot   → run_daily_clv_snapshot() [09:00 UTC]
  - POST /clv/drift            → run_feature_drift_check()[09:30 UTC]
  - POST /clv/closing-tick     → snapshot closing T-30min [every 15 min]
"""
```

- [ ] **Step 3 : Vérifier que le fichier parse**

Run: `cd ProbaLab && python -c "from api.routers import trigger; print('OK')"`
Expected: affiche `OK` (aucune erreur d'import).

- [ ] **Step 4 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/api/routers/trigger.py
git commit -m "docs(h2-ss1): refresh trigger.py header — Trigger.dev is the active scheduler"
```

---

## Task 2 : Endpoint `POST /api/trigger/clv/opening`

**Files:**
- Modify: `ProbaLab/api/routers/trigger.py` (ajout endpoint en fin de fichier)
- Create: `ProbaLab/tests/test_clv_trigger_endpoints.py` (squelette + 1er test)

- [ ] **Step 1 : Créer le fichier de tests avec le squelette + 1er test (TDD)**

Create `ProbaLab/tests/test_clv_trigger_endpoints.py` :

```python
"""
Tests pour les endpoints /api/trigger/clv/* (H2-SS1 Trigger.dev integration).

Pattern : TestClient FastAPI + monkeypatch des fonctions H2-SS1 pour éviter
tout appel DB / réseau réel.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

# ── Env vars requis AVANT toute import projet ───────────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("CRON_SECRET", "test-cron-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-cron-secret"}


# ═══════════════════════════════════════════════════════════════
#  /api/trigger/clv/opening
# ═══════════════════════════════════════════════════════════════


def test_clv_opening_requires_auth(client):
    """Endpoint sans header → 401."""
    resp = client.post("/api/trigger/clv/opening", json={})
    assert resp.status_code == 401


def test_clv_opening_rejects_bad_token(client):
    """Token incorrect → 403."""
    resp = client.post(
        "/api/trigger/clv/opening",
        headers={"Authorization": "Bearer WRONG"},
        json={},
    )
    assert resp.status_code == 403


def test_clv_opening_calls_run_snapshot(client, auth_headers, monkeypatch):
    """Happy path : appelle run_snapshot(snapshot_type='opening') et
    retourne rows_submitted + duration_ms."""
    from src.fetchers import odds_ingestor

    called_with: dict = {}

    def fake_run(*, snapshot_type: str) -> int:
        called_with["snapshot_type"] = snapshot_type
        return 42

    monkeypatch.setattr(odds_ingestor, "run_snapshot", fake_run)

    resp = client.post("/api/trigger/clv/opening", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["rows_submitted"] == 42
    assert called_with["snapshot_type"] == "opening"
    assert isinstance(body["duration_ms"], int)
    assert body["duration_ms"] >= 0
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v`
Expected: FAIL — les 3 tests échouent car l'endpoint `/api/trigger/clv/opening` n'existe pas (404 au lieu de 401/403/200).

- [ ] **Step 3 : Implémenter l'endpoint**

Ouvre `ProbaLab/api/routers/trigger.py`. Tout en bas du fichier (après le dernier endpoint existant), AJOUTE :

```python


# ═══════════════════════════════════════════════════════════════
#  H2-SS1 — Pipeline CLV (ajouté 2026-04-21)
# ═══════════════════════════════════════════════════════════════


@router.post("/clv/opening")
def clv_opening_snapshot() -> dict:
    """08:00 UTC — snapshot opening odds via The Odds API Dev.

    Déclenché par Trigger.dev (schedule `clv-opening-snapshot`).
    """
    import time

    from src.fetchers.odds_ingestor import run_snapshot

    t0 = time.monotonic()
    try:
        n = run_snapshot(snapshot_type="opening")
    except Exception as exc:
        logger.exception("[clv/opening] run_snapshot failed")
        raise HTTPException(status_code=500, detail=f"run_snapshot failed: {exc}") from exc

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.info("[clv/opening] rows_submitted=%d duration_ms=%d", n, duration_ms)
    return {"status": "ok", "rows_submitted": n, "duration_ms": duration_ms}
```

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v`
Expected: 3 passed (`test_clv_opening_requires_auth`, `test_clv_opening_rejects_bad_token`, `test_clv_opening_calls_run_snapshot`).

- [ ] **Step 5 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/api/routers/trigger.py ProbaLab/tests/test_clv_trigger_endpoints.py
git commit -m "feat(h2-ss1/trigger): POST /api/trigger/clv/opening"
```

---

## Task 3 : Endpoint `POST /api/trigger/clv/daily-snapshot`

**Files:**
- Modify: `ProbaLab/api/routers/trigger.py` (ajout endpoint à la suite du précédent)
- Modify: `ProbaLab/tests/test_clv_trigger_endpoints.py` (ajout tests)

- [ ] **Step 1 : Ajouter les tests**

Ouvre `ProbaLab/tests/test_clv_trigger_endpoints.py` et APPEND à la fin :

```python


# ═══════════════════════════════════════════════════════════════
#  /api/trigger/clv/daily-snapshot
# ═══════════════════════════════════════════════════════════════


def test_clv_daily_snapshot_requires_auth(client):
    resp = client.post("/api/trigger/clv/daily-snapshot", json={})
    assert resp.status_code == 401


def test_clv_daily_snapshot_returns_payload(client, auth_headers, monkeypatch):
    """Happy path : appelle run_daily_clv_snapshot() et renvoie le résultat
    encapsulé sous 'payload'."""
    from src.monitoring import clv_engine

    fake_payload = {
        "sport": "football",
        "n_matches_clv": 12,
        "clv_vs_pinnacle_1x2": 0.018,
        "variant_id": "baseline",
    }

    def fake_run_daily() -> dict:
        return fake_payload

    monkeypatch.setattr(clv_engine, "run_daily_clv_snapshot", fake_run_daily)

    resp = client.post("/api/trigger/clv/daily-snapshot", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["payload"] == fake_payload


def test_clv_daily_snapshot_500_on_exception(client, auth_headers, monkeypatch):
    """Si run_daily_clv_snapshot lève, renvoyer 500."""
    from src.monitoring import clv_engine

    def fake_run_daily() -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(clv_engine, "run_daily_clv_snapshot", fake_run_daily)

    resp = client.post("/api/trigger/clv/daily-snapshot", headers=auth_headers, json={})
    assert resp.status_code == 500
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v -k daily_snapshot`
Expected: FAIL — l'endpoint `/api/trigger/clv/daily-snapshot` n'existe pas.

- [ ] **Step 3 : Implémenter l'endpoint**

Dans `ProbaLab/api/routers/trigger.py`, à la SUITE de `clv_opening_snapshot`, AJOUTE :

```python


@router.post("/clv/daily-snapshot")
def clv_daily_snapshot_endpoint() -> dict:
    """09:00 UTC — CLV J-1 vs Pinnacle + moyenne FR, upsert model_health_log.

    Déclenché par Trigger.dev (schedule `clv-daily-snapshot`).
    """
    from src.monitoring.clv_engine import run_daily_clv_snapshot

    try:
        payload = run_daily_clv_snapshot()
    except Exception as exc:
        logger.exception("[clv/daily-snapshot] run_daily_clv_snapshot failed")
        raise HTTPException(
            status_code=500, detail=f"run_daily_clv_snapshot failed: {exc}"
        ) from exc

    logger.info(
        "[clv/daily-snapshot] n_matches=%d variant=%s",
        payload.get("n_matches_clv", 0),
        payload.get("variant_id", "?"),
    )
    return {"status": "ok", "payload": payload}
```

- [ ] **Step 4 : Lancer les tests**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v`
Expected: 6 passed total (3 opening + 3 daily-snapshot).

- [ ] **Step 5 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/api/routers/trigger.py ProbaLab/tests/test_clv_trigger_endpoints.py
git commit -m "feat(h2-ss1/trigger): POST /api/trigger/clv/daily-snapshot"
```

---

## Task 4 : Endpoint `POST /api/trigger/clv/drift`

**Files:**
- Modify: `ProbaLab/api/routers/trigger.py`
- Modify: `ProbaLab/tests/test_clv_trigger_endpoints.py`

- [ ] **Step 1 : Ajouter les tests**

Append à `ProbaLab/tests/test_clv_trigger_endpoints.py` :

```python


# ═══════════════════════════════════════════════════════════════
#  /api/trigger/clv/drift
# ═══════════════════════════════════════════════════════════════


def test_clv_drift_requires_auth(client):
    resp = client.post("/api/trigger/clv/drift", json={})
    assert resp.status_code == 401


def test_clv_drift_no_alert_below_threshold(client, auth_headers, monkeypatch):
    """Si drift_result_to_alert renvoie None, send_telegram ne doit pas être appelé."""
    from src.monitoring import feature_drift

    def fake_run(*, alpha: float, window_days: int) -> dict:
        return {"n_drifted": 2, "n_features": 43, "per_feature": {}}

    monkeypatch.setattr(feature_drift, "run_feature_drift_check", fake_run)
    monkeypatch.setattr(feature_drift, "drift_result_to_alert", lambda _r, **_kw: None)

    telegram_calls: list[str] = []
    import api.routers.trigger as trigger_module

    def fake_send(msg: str) -> bool:
        telegram_calls.append(msg)
        return True

    monkeypatch.setattr(trigger_module, "send_telegram", fake_send, raising=False)

    resp = client.post("/api/trigger/clv/drift", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["n_drifted"] == 2
    assert body["alert_sent"] is False
    assert telegram_calls == []


def test_clv_drift_sends_telegram_when_threshold_exceeded(client, auth_headers, monkeypatch):
    """Si drift_result_to_alert renvoie un message, send_telegram doit être appelé 1 fois."""
    from src.monitoring import feature_drift

    def fake_run(*, alpha: float, window_days: int) -> dict:
        return {"n_drifted": 7, "n_features": 43, "per_feature": {}}

    monkeypatch.setattr(feature_drift, "run_feature_drift_check", fake_run)
    monkeypatch.setattr(
        feature_drift, "drift_result_to_alert",
        lambda _r, **_kw: "\u26a0 drift alert",
    )

    telegram_calls: list[str] = []
    import api.routers.trigger as trigger_module

    def fake_send(msg: str) -> bool:
        telegram_calls.append(msg)
        return True

    monkeypatch.setattr(trigger_module, "send_telegram", fake_send, raising=False)

    resp = client.post("/api/trigger/clv/drift", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_drifted"] == 7
    assert body["alert_sent"] is True
    assert len(telegram_calls) == 1
```

- [ ] **Step 2 : Lancer les tests (doivent échouer)**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v -k drift`
Expected: FAIL — endpoint 404.

- [ ] **Step 3 : Implémenter l'endpoint**

Dans `ProbaLab/api/routers/trigger.py`, ajoute d'abord un import en haut du fichier (au niveau des autres imports stdlib/projet déjà présents) s'il n'y est pas déjà :

Cherche l'import existant `from src.config import ...`. Après lui, AJOUTE la ligne suivante si elle n'est pas déjà présente :

```python
from src.notifications import send_telegram
```

Puis à la SUITE de `clv_daily_snapshot_endpoint`, AJOUTE :

```python


@router.post("/clv/drift")
def clv_drift_check() -> dict:
    """09:30 UTC — KS test training vs prod, alerte Telegram si drift CRITICAL.

    Déclenché par Trigger.dev (schedule `clv-feature-drift`).
    """
    from src.monitoring.feature_drift import (
        drift_result_to_alert,
        run_feature_drift_check,
    )

    try:
        result = run_feature_drift_check(alpha=0.01, window_days=30)
    except Exception as exc:
        logger.exception("[clv/drift] run_feature_drift_check failed")
        raise HTTPException(
            status_code=500, detail=f"run_feature_drift_check failed: {exc}"
        ) from exc

    alert = drift_result_to_alert(result, threshold=5)
    alert_sent = False
    if alert:
        try:
            send_telegram(alert)
            alert_sent = True
        except Exception:
            logger.exception("[clv/drift] send_telegram failed (alert not sent)")

    logger.info(
        "[clv/drift] n_drifted=%d / %d alert_sent=%s",
        result.get("n_drifted", 0),
        result.get("n_features", 0),
        alert_sent,
    )
    return {
        "status": "ok",
        "n_drifted": result.get("n_drifted", 0),
        "n_features": result.get("n_features", 0),
        "alert_sent": alert_sent,
    }
```

- [ ] **Step 4 : Lancer les tests**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v`
Expected: 9 passed.

- [ ] **Step 5 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/api/routers/trigger.py ProbaLab/tests/test_clv_trigger_endpoints.py
git commit -m "feat(h2-ss1/trigger): POST /api/trigger/clv/drift with Telegram alert"
```

---

## Task 5 : Endpoint `POST /api/trigger/clv/closing-tick` (polling + dedup)

**Files:**
- Modify: `ProbaLab/api/routers/trigger.py`
- Modify: `ProbaLab/tests/test_clv_trigger_endpoints.py`

**Design rappel** :
- Fenêtre temporelle : fixtures dont `kickoff ∈ [now+15min, now+45min]` (30 min pour couvrir le polling `*/15`)
- Football : table `fixtures`, colonnes `id`, `date`
- NHL : table `nhl_fixtures`, colonnes `game_id`, `game_date`
- Dedup avant appel Odds API : chercher dans `closing_odds` les `fixture_id` déjà présents avec `snapshot_type='closing'`
- Si `to_snapshot` est non vide, appeler `run_snapshot_for_fixtures(to_snapshot)`

- [ ] **Step 1 : Ajouter les tests**

Append à `ProbaLab/tests/test_clv_trigger_endpoints.py` :

```python


# ═══════════════════════════════════════════════════════════════
#  /api/trigger/clv/closing-tick
# ═══════════════════════════════════════════════════════════════


def _make_closing_tick_supabase_mock(
    *,
    football_rows: list[dict] | None = None,
    nhl_rows: list[dict] | None = None,
    already_snapshotted: list[dict] | None = None,
) -> MagicMock:
    """Construit un faux client Supabase pour le endpoint closing-tick.

    Le endpoint fait 3 requêtes :
      1. fixtures.select('id').gte('date', …).lt('date', …).execute()
      2. nhl_fixtures.select('game_id').gte('game_date', …).lt('game_date', …).execute()
      3. closing_odds.select('fixture_id').in_('fixture_id', …).eq('snapshot_type','closing').execute()
    """
    mock = MagicMock()

    def table_side_effect(name: str):
        chain = MagicMock()
        exec_res = MagicMock()
        if name == "fixtures":
            exec_res.data = football_rows or []
        elif name == "nhl_fixtures":
            exec_res.data = nhl_rows or []
        elif name == "closing_odds":
            exec_res.data = already_snapshotted or []
        else:
            exec_res.data = []
        # Chaque appel (.select / .gte / .lt / .in_ / .eq) renvoie le chain lui-même
        for method in ("select", "gte", "lt", "in_", "eq"):
            getattr(chain, method).return_value = chain
        chain.execute.return_value = exec_res
        return chain

    mock.table.side_effect = table_side_effect
    return mock


def test_clv_closing_tick_requires_auth(client):
    resp = client.post("/api/trigger/clv/closing-tick", json={})
    assert resp.status_code == 401


def test_clv_closing_tick_no_fixtures_in_window(client, auth_headers, monkeypatch):
    """Fenêtre vide → 200 avec snapshots=0, run_snapshot_for_fixtures pas appelé."""
    import api.routers.trigger as trigger_module
    from src.fetchers import odds_ingestor

    fake_supa = _make_closing_tick_supabase_mock()
    monkeypatch.setattr(trigger_module, "supabase", fake_supa)

    called_with: list[list[str]] = []

    def fake_run_for(fixture_ids: list[str]) -> int:
        called_with.append(fixture_ids)
        return 0

    monkeypatch.setattr(odds_ingestor, "run_snapshot_for_fixtures", fake_run_for)

    resp = client.post("/api/trigger/clv/closing-tick", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["snapshots"] == 0
    assert called_with == []


def test_clv_closing_tick_snapshots_new_fixtures(client, auth_headers, monkeypatch):
    """2 fixtures football + 1 NHL en fenêtre, aucun déjà snapshotté → run_snapshot_for_fixtures(3 ids)."""
    import api.routers.trigger as trigger_module
    from src.fetchers import odds_ingestor

    fake_supa = _make_closing_tick_supabase_mock(
        football_rows=[{"id": 111}, {"id": 222}],
        nhl_rows=[{"game_id": 2026020500}],
        already_snapshotted=[],
    )
    monkeypatch.setattr(trigger_module, "supabase", fake_supa)

    called_with: list[list[str]] = []

    def fake_run_for(fixture_ids: list[str]) -> int:
        called_with.append(list(fixture_ids))
        return 18

    monkeypatch.setattr(odds_ingestor, "run_snapshot_for_fixtures", fake_run_for)

    resp = client.post("/api/trigger/clv/closing-tick", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["snapshots"] == 18
    assert body["fixture_count"] == 3
    assert len(called_with) == 1
    assert set(called_with[0]) == {"111", "222", "2026020500"}


def test_clv_closing_tick_skips_already_snapshotted(client, auth_headers, monkeypatch):
    """2 fixtures, 1 déjà snapshotté → run_snapshot_for_fixtures n'appelle QUE l'autre."""
    import api.routers.trigger as trigger_module
    from src.fetchers import odds_ingestor

    fake_supa = _make_closing_tick_supabase_mock(
        football_rows=[{"id": 111}, {"id": 222}],
        nhl_rows=[],
        already_snapshotted=[{"fixture_id": "111"}],
    )
    monkeypatch.setattr(trigger_module, "supabase", fake_supa)

    called_with: list[list[str]] = []

    def fake_run_for(fixture_ids: list[str]) -> int:
        called_with.append(list(fixture_ids))
        return 6

    monkeypatch.setattr(odds_ingestor, "run_snapshot_for_fixtures", fake_run_for)

    resp = client.post("/api/trigger/clv/closing-tick", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["snapshots"] == 6
    assert body["fixture_count"] == 1
    assert called_with == [["222"]]


def test_clv_closing_tick_all_already_done_short_circuits(client, auth_headers, monkeypatch):
    """Toutes les fixtures déjà snapshottées → run_snapshot_for_fixtures PAS appelé."""
    import api.routers.trigger as trigger_module
    from src.fetchers import odds_ingestor

    fake_supa = _make_closing_tick_supabase_mock(
        football_rows=[{"id": 111}],
        nhl_rows=[],
        already_snapshotted=[{"fixture_id": "111"}],
    )
    monkeypatch.setattr(trigger_module, "supabase", fake_supa)

    called_with: list[list[str]] = []

    def fake_run_for(fixture_ids: list[str]) -> int:
        called_with.append(list(fixture_ids))
        return 0

    monkeypatch.setattr(odds_ingestor, "run_snapshot_for_fixtures", fake_run_for)

    resp = client.post("/api/trigger/clv/closing-tick", headers=auth_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["snapshots"] == 0
    assert body["already_done"] == 1
    assert called_with == []
```

- [ ] **Step 2 : Lancer les tests (doivent échouer)**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v -k closing_tick`
Expected: 5 FAIL — endpoint 404.

- [ ] **Step 3 : Implémenter l'endpoint**

Dans `ProbaLab/api/routers/trigger.py`, à la SUITE de `clv_drift_check`, AJOUTE :

```python


@router.post("/clv/closing-tick")
def clv_closing_tick() -> dict:
    """Polling toutes les 15 min — snapshot closing odds pour fixtures dont kickoff ∈ [now+15, now+45].

    Déclenché par Trigger.dev (schedule `clv-closing-tick`, cron `*/15 * * * *`).

    Dedup : avant d'appeler The Odds API, on vérifie quelles fixtures sont déjà présentes
    en `closing_odds` avec `snapshot_type='closing'` pour économiser le quota API.
    """
    from datetime import timedelta

    from src.fetchers.odds_ingestor import run_snapshot_for_fixtures

    now = datetime.now(timezone.utc)
    window_start = (now + timedelta(minutes=15)).isoformat()
    window_end = (now + timedelta(minutes=45)).isoformat()

    # 1. Fixtures football en fenêtre
    try:
        foot = (
            supabase.table("fixtures")
            .select("id")
            .gte("date", window_start)
            .lt("date", window_end)
            .execute()
            .data
        ) or []
    except Exception:
        logger.exception("[clv/closing-tick] football fixtures load failed")
        foot = []

    # 2. Fixtures NHL en fenêtre
    try:
        nhl = (
            supabase.table("nhl_fixtures")
            .select("game_id")
            .gte("game_date", window_start)
            .lt("game_date", window_end)
            .execute()
            .data
        ) or []
    except Exception:
        logger.exception("[clv/closing-tick] nhl fixtures load failed")
        nhl = []

    fixture_ids = [str(f["id"]) for f in foot if f.get("id") is not None] + [
        str(f["game_id"]) for f in nhl if f.get("game_id") is not None
    ]

    if not fixture_ids:
        logger.info("[clv/closing-tick] no fixtures in window [%s, %s]", window_start, window_end)
        return {"status": "ok", "snapshots": 0, "message": "no fixtures in window"}

    # 3. Dedup : quelles fixtures sont déjà closing-snapshottées ?
    try:
        done_rows = (
            supabase.table("closing_odds")
            .select("fixture_id")
            .in_("fixture_id", fixture_ids)
            .eq("snapshot_type", "closing")
            .execute()
            .data
        ) or []
    except Exception:
        logger.exception("[clv/closing-tick] dedup query failed — proceeding without dedup")
        done_rows = []

    done_ids = {r["fixture_id"] for r in done_rows if r.get("fixture_id")}
    to_snapshot = [fid for fid in fixture_ids if fid not in done_ids]

    if not to_snapshot:
        logger.info(
            "[clv/closing-tick] all %d fixtures already snapshotted",
            len(done_ids),
        )
        return {"status": "ok", "snapshots": 0, "already_done": len(done_ids)}

    try:
        n = run_snapshot_for_fixtures(to_snapshot)
    except Exception as exc:
        logger.exception("[clv/closing-tick] run_snapshot_for_fixtures failed")
        raise HTTPException(
            status_code=500, detail=f"run_snapshot_for_fixtures failed: {exc}"
        ) from exc

    logger.info(
        "[clv/closing-tick] snapshots=%d fixture_count=%d (already_done=%d)",
        n, len(to_snapshot), len(done_ids),
    )
    return {
        "status": "ok",
        "snapshots": n,
        "fixture_count": len(to_snapshot),
        "already_done": len(done_ids),
    }
```

- [ ] **Step 4 : Lancer TOUS les tests du fichier**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py -v`
Expected: 14 passed.

- [ ] **Step 5 : Lancer ruff**

Run: `cd ProbaLab && ruff format src/ api/ tests/ && ruff check src/ api/ tests/`
Expected: `All checks passed!` (et aucun fichier à reformater).

- [ ] **Step 6 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/api/routers/trigger.py ProbaLab/tests/test_clv_trigger_endpoints.py
git commit -m "feat(h2-ss1/trigger): POST /api/trigger/clv/closing-tick with dedup"
```

---

## Task 6 : Fichier Trigger.dev `clvPipeline.ts`

**Files:**
- Create: `ProbaLab/trigger-worker/src/trigger/clvPipeline.ts`

- [ ] **Step 1 : Vérifier la version SDK Trigger.dev du projet**

Run: `cd ProbaLab/trigger-worker && cat package.json | grep '"@trigger.dev/sdk"'`
Attendu : une ligne du type `"@trigger.dev/sdk": "^3.x.x"` ou similaire. Note la version, elle doit être cohérente avec les autres fichiers `src/trigger/*.ts` (ils utilisent `import { schedules } from "@trigger.dev/sdk"` — même chemin d'import ci-dessous).

- [ ] **Step 2 : Créer `clvPipeline.ts`**

Create `ProbaLab/trigger-worker/src/trigger/clvPipeline.ts` :

```typescript
// ─────────────────────────────────────────────────────────────────
//  H2-SS1 — CLV pipeline schedules (ajouté 2026-04-21)
//  4 schedules qui appellent les endpoints /api/trigger/clv/* sur
//  le service Railway web (api.probalab.net).
// ─────────────────────────────────────────────────────────────────
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

const cronHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${CRON_SECRET}`,
};

async function callEndpoint(path: string, label: string): Promise<unknown> {
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

// 08:00 UTC — snapshot opening odds (matchs J+1 / J)
export const clvOpeningSnapshot = schedules.task({
    id: "clv-opening-snapshot",
    cron: "0 8 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/opening", "clv-opening"),
});

// 09:00 UTC — CLV daily snapshot pour J-1 (model_health_log)
export const clvDailySnapshot = schedules.task({
    id: "clv-daily-snapshot",
    cron: "0 9 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/daily-snapshot", "clv-daily"),
});

// 09:30 UTC — feature drift KS test + Telegram alert
export const clvFeatureDrift = schedules.task({
    id: "clv-feature-drift",
    cron: "30 9 * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/drift", "clv-drift"),
});

// Every 15 min — snapshot closing odds pour matchs dont kickoff ∈ [+15, +45]
export const clvClosingTick = schedules.task({
    id: "clv-closing-tick",
    cron: "*/15 * * * *",
    retry: standardRetry,
    run: async () => callEndpoint("/api/trigger/clv/closing-tick", "clv-closing"),
});
```

- [ ] **Step 3 : Vérifier que le fichier compile (type-check)**

Run: `cd ProbaLab/trigger-worker && npx tsc --noEmit 2>&1 | tail -10`
Expected: aucune erreur (ou uniquement des warnings préexistants — si tu vois des erreurs sur les AUTRES fichiers de `src/trigger/`, c'est préexistant, ignore. Ce qui compte : aucune erreur `clvPipeline.ts`).

- [ ] **Step 4 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/trigger-worker/src/trigger/clvPipeline.ts
git commit -m "feat(h2-ss1/trigger): Trigger.dev schedules for CLV pipeline (4 tasks)"
```

---

## Task 7 : Full local test run avant PR

**Files:** pas de modif, uniquement vérifications.

- [ ] **Step 1 : Tests complets**

Run: `cd ProbaLab && pytest tests/test_clv_trigger_endpoints.py tests/test_odds_ingestor.py tests/test_clv_engine.py tests/test_daily_clv_snapshot.py tests/test_feature_drift.py -v --tb=short 2>&1 | tail -20`

Expected : tous les tests passent. Exactement 14 nouveaux dans `test_clv_trigger_endpoints.py` + les tests H2-SS1 existants.

Si une régression apparaît sur des tests H2-SS1 pré-existants, c'est un bug introduit par Task 2-5 — investiguer avant de continuer.

- [ ] **Step 2 : Ruff format + check**

Run: `cd ProbaLab && ruff format --check src/ api/ tests/ && ruff check src/ api/ tests/`
Expected: `169 files already formatted` (ou similaire) + `All checks passed!`.

Si ruff format signale des fichiers à reformater, lance `ruff format src/ api/ tests/`, puis fais un commit séparé :

```bash
git add ProbaLab/
git commit -m "style(h2-ss1/trigger): apply ruff format"
```

- [ ] **Step 3 : Smoke import**

Run: `cd ProbaLab && SUPABASE_URL=https://test.supabase.co SUPABASE_KEY=fake python -c "from api.main import app; routes = [r.path for r in app.routes if '/clv/' in r.path]; print(sorted(routes))"`

Expected stdout :
```
['/api/trigger/clv/closing-tick', '/api/trigger/clv/daily-snapshot', '/api/trigger/clv/drift', '/api/trigger/clv/opening']
```

- [ ] **Step 4 : Pas de commit à cette étape** (déjà commité dans les tasks précédentes — passe à la suivante).

---

## Task 8 : Push PR et attente CI

**Files:** aucun — opérations git/GitHub.

- [ ] **Step 1 : Créer une branche dédiée et pusher**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git checkout -b feature/h2-ss1-triggerdev main
git log --oneline main..HEAD | head -10
```

Expected: 6 commits visibles (Task 1 docstring, Tasks 2-5 endpoints, Task 6 Trigger.dev TS, éventuellement Task 7 ruff format).

Puis :

```bash
git push -u origin feature/h2-ss1-triggerdev
```

- [ ] **Step 2 : Créer la PR**

```bash
gh pr create --title "feat(h2-ss1): Trigger.dev integration for CLV pipeline" --body "$(cat <<'EOF'
## Summary

Branche les 4 jobs H2-SS1 dans l'architecture de scheduling réelle (Trigger.dev + FastAPI endpoints), rendant le pipeline CLV actif en production.

- **4 nouveaux endpoints** `POST /api/trigger/clv/{opening, daily-snapshot, drift, closing-tick}` dans `api/routers/trigger.py`
- **4 schedules Trigger.dev** dans `trigger-worker/src/trigger/clvPipeline.ts`
- **14 nouveaux tests** dans `tests/test_clv_trigger_endpoints.py`
- **Docstring** de `trigger.py` remis à jour (Trigger.dev est le scheduler actif, APScheduler/worker.py dormant)

## Spec

[docs/superpowers/specs/2026-04-21-h2-ss1-triggerdev-integration-design.md](docs/superpowers/specs/2026-04-21-h2-ss1-triggerdev-integration-design.md)

## Horaires UTC

- `0 8 * * *`  opening snapshot  (The Odds API fetch)
- `0 9 * * *`  daily CLV snapshot (J-1 vs Pinnacle + FR avg)
- `30 9 * * *` feature drift KS test
- `*/15 * * * *` closing snapshot polling (T-30min per match via dedup)

## Test plan

- [x] 14 nouveaux tests unitaires (auth + happy path + erreurs) — tous verts en local
- [x] Ruff format + check verts
- [x] Smoke import : 4 routes `/api/trigger/clv/*` bien mountées
- [ ] CI green sur PR
- [ ] Smoke manuel post-deploy : `curl` sur chaque endpoint
- [ ] Deploy Trigger.dev : 4 schedules visibles dans le dashboard
- [ ] Observation 24h : première row `closing_odds` + première row CLV dans `model_health_log`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3 : Attendre et vérifier la CI**

Run: `gh pr checks --watch 2>&1 | tail -20`

Expected : les 3 jobs CI passent vert (`lint`, `type-check`, `test`). Si l'un échoue, récupère le log et fixe avant de merger :

```bash
gh run view --log-failed
```

- [ ] **Step 4 : Merger la PR**

Une fois les checks verts :

```bash
gh pr merge --squash --delete-branch
```

Ou manuellement via le dashboard GitHub si tu préfères (mode `squash`).

- [ ] **Step 5 : Synchroniser main local**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git checkout main
git pull origin main
git log --oneline -3
```

Expected : le commit squash apparaît en tête.

---

## Task 9 : Smoke test manuel post-deploy Railway

**Files:** aucun — validation en prod.

Note : Railway redéploie automatiquement `main` à chaque push. Attendre ~2-3 min après le merge pour que le nouveau conteneur soit Active.

- [ ] **Step 1 : Vérifier le déploiement Railway**

Dans le dashboard Railway, vérifier que le service `web` affiche `Active` avec le SHA du merge commit. Si déploiement encore en cours, attendre.

- [ ] **Step 2 : Récupérer le `CRON_SECRET` local**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
grep '^CRON_SECRET=' .env | cut -d= -f2-
```

**Important** : ne PAS coller ce secret dans le chat. Utilise-le uniquement dans les commandes shell ci-dessous.

- [ ] **Step 3 : Smoke test `/clv/closing-tick` (le plus safe — ne consomme pas de quota API si pas de match en fenêtre)**

```bash
CRON_SECRET=$(grep '^CRON_SECRET=' .env | cut -d= -f2-)
curl -s -X POST https://api.probalab.net/api/trigger/clv/closing-tick \
  -H "Authorization: Bearer $CRON_SECRET" \
  -H "Content-Type: application/json" \
  -d '{}' | head -20
```

Attendu : un JSON du type `{"status": "ok", "snapshots": 0, "message": "no fixtures in window"}` OU `{"status": "ok", "snapshots": N, "fixture_count": M}` si des matchs sont réellement à T-15→T-45.

Si retour `401` ou `403` : `CRON_SECRET` Railway différent du `.env` local → le vérifier dans les variables d'env Railway.

- [ ] **Step 4 : Smoke test `/clv/drift` (ne consomme pas de quota API)**

```bash
curl -s -X POST https://api.probalab.net/api/trigger/clv/drift \
  -H "Authorization: Bearer $CRON_SECRET" \
  -H "Content-Type: application/json" \
  -d '{}' | head -20
```

Attendu : `{"status": "ok", "n_drifted": N, "n_features": M, "alert_sent": false}`. Si `alert_sent: true` → OK (drift détecté, Telegram envoyé).

- [ ] **Step 5 : Smoke test `/clv/opening` (CONSOMME une requête The Odds API)**

```bash
curl -s -X POST https://api.probalab.net/api/trigger/clv/opening \
  -H "Authorization: Bearer $CRON_SECRET" \
  -H "Content-Type: application/json" \
  -d '{}' | head -20
```

Attendu : `{"status": "ok", "rows_submitted": N>0, "duration_ms": X}`.

- [ ] **Step 6 : Vérifier DB Supabase**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
source .env
curl -s "$SUPABASE_URL/rest/v1/closing_odds?select=count" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Prefer: count=exact"
```

Attendu : `[{"count": N}]` avec N > 0 si l'étape 5 s'est bien passée.

- [ ] **Step 7 : Tag git pour tracer**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git tag -a h2-ss1-triggerdev-deployed -m "H2-SS1 Trigger.dev integration — endpoints deployed on Railway, smoke tests OK"
git push origin h2-ss1-triggerdev-deployed
```

---

## Task 10 : Deploy Trigger.dev + vérification dashboard

**Files:** aucun — opérations Trigger.dev CLI.

- [ ] **Step 1 : Login Trigger.dev (si pas déjà fait)**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/trigger-worker"
npx trigger.dev@latest whoami
```

Si pas connecté : `npx trigger.dev@latest login`.

- [ ] **Step 2 : Deploy**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/trigger-worker"
npx trigger.dev@latest deploy
```

Attendu : log de build, bundle upload, puis message `Deployment completed` ou équivalent. Le dashboard Trigger.dev Cloud reçoit la nouvelle version.

En cas d'erreur d'import pendant le bundling : vérifier que `clvPipeline.ts` est bien détecté (doit apparaître dans la liste des fichiers bundlés).

- [ ] **Step 3 : Vérifier les 4 schedules dans le dashboard Trigger.dev**

Ouvre le dashboard Trigger.dev (cloud.trigger.dev), projet ProbaLab, section **Schedules**. Vérifie que ces 4 IDs apparaissent :

- `clv-opening-snapshot` — next run : demain 08:00 UTC
- `clv-daily-snapshot` — next run : demain 09:00 UTC
- `clv-feature-drift` — next run : demain 09:30 UTC
- `clv-closing-tick` — next run : dans < 15 min

Pour chaque, vérifier que l'état est **Enabled** et que l'environnement est bien **prod** (ou ton env par défaut).

- [ ] **Step 4 : Forcer un premier run manuel de `clv-closing-tick`**

Dans le dashboard Trigger.dev, trouve `clv-closing-tick` dans la liste des schedules, clique sur l'action **Trigger manually** (ou équivalent dans ta version). Vérifie que le run apparaît en `Running` puis `Completed`, et que la réponse contient `{"status": "ok", ...}`.

Si échec : le log affiche l'erreur — probable cause si tu viens juste de configurer Trigger.dev : `CRON_SECRET` manquant côté Trigger.dev env. Dans ce cas, va dans **Environment Variables** du projet Trigger.dev et ajoute `CRON_SECRET` et `API_URL` (valeur `https://api.probalab.net`).

- [ ] **Step 5 : Pas de commit** — opérations externes uniquement.

---

## Task 11 : Observation 24 h — premier pipeline CLV complet

**Files:** aucun — observation.

- [ ] **Step 1 : Demain matin 08:15 UTC — vérifier opening snapshot**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
source .env
curl -s "$SUPABASE_URL/rest/v1/closing_odds?select=sport,bookmaker,market,snapshot_type,snapshot_at&snapshot_type=eq.opening&order=snapshot_at.desc&limit=5" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

Attendu : 5 rows, `snapshot_at` dans les dernières 15 min, `snapshot_type: "opening"`, bookmakers variés (pinnacle + betclic + winamax + unibet + zebet).

- [ ] **Step 2 : Demain 09:15 UTC — vérifier daily CLV snapshot**

```bash
curl -s "$SUPABASE_URL/rest/v1/model_health_log?select=recorded_at,sport,n_matches_clv,clv_vs_pinnacle_1x2,clv_vs_fr_avg_1x2,variant_id&order=recorded_at.desc&limit=3" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

Attendu : nouvelle row avec `recorded_at` proche de 09:00 UTC, `variant_id: "baseline"`, `n_matches_clv > 0` si des matchs ont été joués J-1 (si J-1 = dimanche sans match, `n_matches_clv: 0` ; refaire le test après un jour de matchs).

- [ ] **Step 3 : Demain 09:35 UTC — vérifier feature drift**

Consulter les logs du service Railway web filtrer sur `[clv/drift]`. Attendu : une ligne du type `[clv/drift] n_drifted=N / 43 alert_sent=false` (ou `true` si drift détecté).

Ou dans Trigger.dev dashboard → `clv-feature-drift` → dernier run → log de l'exécution.

- [ ] **Step 4 : Demain soir 22:00 UTC — vérifier closing snapshots sur les matchs du jour**

```bash
curl -s "$SUPABASE_URL/rest/v1/closing_odds?select=sport,fixture_id,bookmaker,snapshot_type,snapshot_at&snapshot_type=eq.closing&order=snapshot_at.desc&limit=20" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

Attendu : rows avec `snapshot_type: "closing"`, `snapshot_at` étalés sur la soirée (correspondant aux T-30min des différents kickoffs).

- [ ] **Step 5 : Documenter l'observation dans `tasks/lessons.md`**

Ajouter une entrée à la fin de `ProbaLab/tasks/lessons.md` :

```
| 2026-04-22 | H2-SS1 Trigger.dev integration déployée, premier pipeline CLV observé (opening=N rows, closing=M rows, daily CLV 1X2 vs Pinnacle=<VAL>%) | APScheduler/worker.py est mort-code en prod (Railway ne lance que uvicorn). Tous les nouveaux crons doivent passer par Trigger.dev + endpoint /api/trigger/*. Vérifier avant de merger un commit qui ajoute des `scheduler.add_job()` dans worker.py |
```

(Remplacer les valeurs `N`, `M`, `<VAL>` par les chiffres réels observés.)

- [ ] **Step 6 : Commit lesson**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/tasks/lessons.md
git commit -m "docs(lessons): H2-SS1 Trigger.dev integration live — worker.py is dead code in prod"
git push origin main
```

---

## Récap couverture spec

| Spec section | Tasks |
|---|---|
| §1 Success 1 : 4 endpoints FastAPI | Tasks 2, 3, 4, 5 |
| §1 Success 2 : 4 schedules Trigger.dev | Task 6 |
| §1 Success 3 : schedules actifs aux bonnes heures | Task 10 Step 3 |
| §1 Success 4 : premier opening snapshot visible 24h | Task 11 Step 1 |
| §1 Success 5 : première row CLV 48h | Task 11 Step 2 |
| §1 Success 6 : pas de régression sur schedules existants | Task 6 `npx tsc --noEmit` + Task 10 dashboard inspection |
| §4.1 contrat `/clv/opening` | Task 2 |
| §4.2 contrat `/clv/closing-tick` + dedup | Task 5 |
| §4.3 contrat `/clv/daily-snapshot` | Task 3 |
| §4.4 contrat `/clv/drift` + Telegram | Task 4 |
| §5 `clvPipeline.ts` 4 schedules | Task 6 |
| §6 error handling | Tasks 2-5 (try/except + HTTPException + fail-loud) |
| §7 tests | Tasks 2-5 (14 tests) |
| §8 deploy sequencing | Tasks 8, 9, 10 |
| §11 R1-R6 risques | Task 5 dedup (R2) + Task 10 Step 4 (R4) |

---

## Self-review notes

**1. Spec coverage** : toutes les sections §1 à §12 du spec sont couvertes par au moins une Task. Le §12 (cohérence décisions antérieures) est informationnel, pas implémentable.

**2. Placeholder scan** : aucun TBD/TODO/"implement later" — chaque step a du code ou une commande concrète.

**3. Type consistency** : les 4 endpoints utilisent tous la forme `-> dict`, le pattern `try/except + HTTPException(500) from exc` est identique sur les 4. Les logs utilisent tous `logger.info` (pas mix `logger.info/log/print`). Les imports sont tous faits dans les handlers (lazy import — cohérent avec le pattern des autres endpoints de `trigger.py`).

**4. Horaires** : ordre UTC cohérent avec spec §3.1 et §5 (08:00 / 09:00 / 09:30, plus `*/15` polling pour closing).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-21-h2-ss1-triggerdev-integration.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — je dispatche un subagent frais par task, review entre chaque, itération rapide.

**2. Inline Execution** — j'exécute les tasks dans cette session avec checkpoints.

**Which approach?**
