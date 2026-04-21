# Lot 2 — Backend endpoints (refonte frontend V1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for each endpoint + superpowers:executing-plans for checkpoint gating. TDD strict : chaque test pytest DOIT être écrit et failing avant l'implémentation.

**Parent plan:** [2026-04-21-frontend-refonte-v1-MASTER.md](./2026-04-21-frontend-refonte-v1-MASTER.md)
**Spec source:** [2026-04-21-frontend-refonte-v1-design.md §14](../specs/2026-04-21-frontend-refonte-v1-design.md)

**Goal:** Livrer 10 nouveaux endpoints FastAPI + 3 migrations SQL pour alimenter les lots 3-5 frontend. Chaque endpoint est testé unitairement (route + logique pure), intégré au router existant, et sa logique métier extraite dans `src/` (lesson 63).

**Out of scope:**
- Endpoints déjà existants (`/api/best-bets`, `/api/predictions/:id`, `/api/analysis/:id`) — gérés ailleurs.
- Endpoints Telegram connect flow (backlog Lot 5).
- Cache distribué Redis (cache mémoire process suffit pour V1, cf task T01).

**Racines de travail:**
- Repo : `/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab`
- Package Python : `ProbaLab/` (imports `from api.xxx`, `from src.xxx`)
- Migrations : `ProbaLab/migrations/` (dernière appliquée : `053_advanced_features.sql`)

---

## Invariants Lot 2

- **Python 3.11+**, FastAPI, Pydantic v2 avec `ConfigDict(extra="forbid")` sur tous les modèles.
- **Timezone UTC partout** (lesson 22) : `datetime.now(timezone.utc)`, jamais `datetime.now()` nu.
- **fixture_id typé `str`** (lesson 48) : les filtres DB doivent traiter TEXT, pas int.
- **Auth** :
  - Endpoints `/api/public/*` → aucune auth, rate-limit slowapi stricte.
  - Endpoints `/api/safe-pick`, `/api/matches`, `/api/odds/*/comparison`, `/api/user/*` → `Depends(current_user)`.
  - Aucun endpoint admin dans ce lot.
- **Logique pure extraite** dans `src/` (lesson 63), les routes FastAPI sont de la glue légère (≤ 30 lignes).
- **Tests sans TestClient** quand possible : appeler `endpoint.__wrapped__(...)` pour bypass slowapi (lesson 64).
- **RLS strict** (lesson 59) : toutes tables user ont `service_role_all` + `authenticated_own_rows`.
- **Un commit par cycle TDD** : `test(api/v2): ...` (test failing), puis `feat(api/v2): ...` (implem passing).
- **Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>** sur chaque commit.

### Structure livrée

```
ProbaLab/
├── api/routers/v2/
│   ├── __init__.py
│   ├── public_track_record.py
│   ├── safe_pick.py
│   ├── matches_v2.py
│   ├── odds_comparison.py
│   ├── user_bankroll.py
│   └── user_notifications.py
├── src/models/
│   ├── safe_pick_selector.py
│   ├── matches_aggregator.py
│   ├── odds_comparator.py
│   └── roi_by_market.py
├── src/notifications/
│   └── rules_store.py
├── migrations/
│   ├── 054_user_bankroll_settings.sql
│   ├── 055_user_bets.sql                  (conditionnelle — cf P2)
│   └── 056_notification_rules.sql
└── tests/
    ├── test_public_track_record.py
    ├── test_safe_pick.py
    ├── test_safe_pick_selector.py
    ├── test_matches_v2.py
    ├── test_matches_aggregator.py
    ├── test_odds_comparison.py
    ├── test_odds_comparator.py
    ├── test_user_bankroll_roi_by_market.py
    ├── test_user_bankroll_settings.py
    └── test_user_notification_rules.py
```

---

## Pré-requis

### P0 · Vérifier baseline tests verts

- [ ] Lancer `cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab" && pytest -x -q`
- [ ] Expected: tous les tests existants passent (381+). Si échec → stop, diagnostiquer AVANT de continuer.

### P1 · Inspection schéma Supabase

Objectif : décider si la migration `055_user_bets.sql` est nécessaire (table peut déjà exister via `api/routers/best_bets.py` historique).

- [ ] Exécuter via Supabase MCP : `list_tables` sur schema `public`.
- [ ] Expected output : chercher `user_bets`, `user_bankroll_settings`, `notification_rules`.
  - Si `user_bets` existe → adapter le schéma dans T13 (migration idempotente `CREATE TABLE IF NOT EXISTS ... + ALTER TABLE ADD COLUMN IF NOT EXISTS`).
  - Si `user_bankroll_settings` existe → skip T12.
  - Si `notification_rules` existe → skip T14.
- [ ] Documenter les résultats dans `ProbaLab/tasks/todo.md` section "Lot 2 pré-check schéma".

### P2 · Créer le package `api/routers/v2/`

- [ ] Créer `ProbaLab/api/routers/v2/__init__.py` (fichier vide).
- [ ] Dans `ProbaLab/api/main.py`, ajouter les imports/inclusions des routers v2 (à faire incrémentalement à chaque endpoint — cf chaque task).

### P3 · Installer `fastapi-cache2` si absent

- [ ] Vérifier `ProbaLab/requirements.txt` → `grep -i cache` pour voir si `fastapi-cache2` ou équivalent est présent.
- [ ] Si absent, utiliser un décorateur `functools.lru_cache` wrappé avec TTL maison (déjà pattern projet dans `api/cache.py`). Ne pas ajouter de dépendance si cache mémoire process suffit.

---

## Migrations SQL (tasks préalables aux endpoints user-specific)

### T12 · Migration `054_user_bankroll_settings.sql`

- [ ] Créer `ProbaLab/migrations/054_user_bankroll_settings.sql` :

```sql
-- 054_user_bankroll_settings.sql
-- Persistance des réglages de bankroll par user (Kelly fraction, stake cap, stake initial).

CREATE TABLE IF NOT EXISTS public.user_bankroll_settings (
    user_id        UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    stake_initial  NUMERIC(12, 2) NOT NULL DEFAULT 100.00 CHECK (stake_initial >= 0),
    kelly_fraction NUMERIC(4, 3)  NOT NULL DEFAULT 0.250 CHECK (kelly_fraction > 0 AND kelly_fraction <= 1),
    stake_cap_pct  NUMERIC(4, 3)  NOT NULL DEFAULT 0.050 CHECK (stake_cap_pct  > 0 AND stake_cap_pct  <= 1),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.user_bankroll_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.user_bankroll_settings;
CREATE POLICY service_role_all ON public.user_bankroll_settings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS authenticated_own_rows ON public.user_bankroll_settings;
CREATE POLICY authenticated_own_rows ON public.user_bankroll_settings
    FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.tg_user_bankroll_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_bankroll_settings_updated_at ON public.user_bankroll_settings;
CREATE TRIGGER trg_user_bankroll_settings_updated_at
    BEFORE UPDATE ON public.user_bankroll_settings
    FOR EACH ROW EXECUTE FUNCTION public.tg_user_bankroll_settings_updated_at();
```

- [ ] Appliquer via Supabase MCP `apply_migration` ou `run_migration.py`.
- [ ] Vérifier : `SELECT * FROM public.user_bankroll_settings LIMIT 1;` → OK (0 rows).
- [ ] Commit : `feat(db): 054 user_bankroll_settings table + RLS`.

### T13 · Migration `055_user_bets.sql` (conditionnelle — voir P1)

- [ ] Si la table existe déjà avec les colonnes requises (`id, user_id, fixture_id TEXT, market, selection, odds, stake, result, created_at`) → skip, noter dans todo.md.
- [ ] Sinon créer `ProbaLab/migrations/055_user_bets.sql` :

```sql
-- 055_user_bets.sql
-- Paris placés par l'utilisateur (pour ROI by market, bankroll tracking).
-- fixture_id TEXT (lesson 48).

CREATE TABLE IF NOT EXISTS public.user_bets (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fixture_id TEXT NOT NULL,
    market     TEXT NOT NULL,
    selection  TEXT NOT NULL,
    odds       NUMERIC(6, 3) NOT NULL CHECK (odds >= 1.01),
    stake      NUMERIC(12, 2) NOT NULL CHECK (stake >= 0),
    result     TEXT CHECK (result IN ('WIN', 'LOSS', 'VOID', 'PENDING')) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_bets_user_id_created ON public.user_bets(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_bets_user_market     ON public.user_bets(user_id, market);

ALTER TABLE public.user_bets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.user_bets;
CREATE POLICY service_role_all ON public.user_bets
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS authenticated_own_rows ON public.user_bets;
CREATE POLICY authenticated_own_rows ON public.user_bets
    FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
```

- [ ] Appliquer et vérifier.
- [ ] Commit : `feat(db): 055 user_bets table + RLS + indexes`.

### T14 · Migration `056_notification_rules.sql`

- [ ] Créer `ProbaLab/migrations/056_notification_rules.sql` :

```sql
-- 056_notification_rules.sql
-- Règles d'alerte custom par user (rules builder).

CREATE TABLE IF NOT EXISTS public.notification_rules (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name               TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
    conditions         JSONB NOT NULL DEFAULT '[]'::jsonb,
    logic              TEXT NOT NULL CHECK (logic IN ('and', 'or')) DEFAULT 'and',
    channels           TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    secondary_actions  TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_conditions_max_3 CHECK (jsonb_array_length(conditions) <= 3),
    CONSTRAINT chk_channels_valid  CHECK (channels <@ ARRAY['telegram','email','push']::TEXT[])
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_user ON public.notification_rules(user_id, enabled);

ALTER TABLE public.notification_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.notification_rules;
CREATE POLICY service_role_all ON public.notification_rules
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS authenticated_own_rows ON public.notification_rules;
CREATE POLICY authenticated_own_rows ON public.notification_rules
    FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.tg_notification_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notification_rules_updated_at ON public.notification_rules;
CREATE TRIGGER trg_notification_rules_updated_at
    BEFORE UPDATE ON public.notification_rules
    FOR EACH ROW EXECUTE FUNCTION public.tg_notification_rules_updated_at();
```

- [ ] Appliquer et vérifier.
- [ ] Commit : `feat(db): 056 notification_rules table + RLS`.

---

## Tasks endpoints (10 endpoints · TDD strict)

### Fixtures partagées pytest

Avant le premier endpoint, enrichir `ProbaLab/tests/conftest.py` avec fixtures communes.

- [ ] Ajouter fixture `mock_supabase` (MagicMock chainable) :

```python
# ProbaLab/tests/conftest.py  (extrait à ajouter)
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_supabase(monkeypatch):
    """Chainable mock of the Supabase client used across v2 routers."""
    mock = MagicMock()

    def chain(*_args, **_kwargs):
        return mock

    for method in ("table", "select", "eq", "in_", "gte", "lte", "order", "limit",
                   "insert", "update", "upsert", "delete", "single", "range"):
        getattr(mock, method).side_effect = chain

    mock.execute.return_value = MagicMock(data=[], count=0)
    monkeypatch.setattr("src.config.supabase", mock)
    monkeypatch.setattr("api.auth.supabase", mock, raising=False)
    return mock


@pytest.fixture
def fake_user():
    """User payload injected via Depends(current_user)."""
    return {"id": "00000000-0000-0000-0000-000000000001", "role": "premium"}
```

- [ ] Commit : `test(v2): add mock_supabase + fake_user fixtures`.

---

### T01 · `GET /api/public/track-record/live`

**Endpoint public, cache 5 min, rate-limit.**

#### T01.1 · Test route (failing)

- [ ] Créer `ProbaLab/tests/test_public_track_record.py` :

```python
# ProbaLab/tests/test_public_track_record.py
import pytest
from api.routers.v2.public_track_record import get_track_record_live


@pytest.mark.asyncio
async def test_track_record_live_shape(mock_supabase):
    # CLV 30d
    mock_supabase.execute.side_effect = [
        MagicMock(data=[{"clv_pct": 3.1}, {"clv_pct": 4.2}]),  # model_health_log
        MagicMock(data=[{"roi_pct": 12.5, "n_bets": 140}]),    # best_bets agregé
        MagicMock(data=[{"brier": 0.201, "n": 500}]),          # predictions_results
        MagicMock(data=[{"safe_rate": 0.68, "n": 90}]),        # safe picks 90d
        MagicMock(data=[                                       # roi curve
            {"d": "2026-01-22", "cum_roi": 0.0},
            {"d": "2026-04-21", "cum_roi": 12.5},
        ]),
    ]
    from unittest.mock import MagicMock  # noqa: E402

    out = await get_track_record_live.__wrapped__(request=MagicMock())

    assert set(out.keys()) == {"clv_30d", "roi_90d", "brier_30d", "safe_rate_90d", "roi_curve_90d"}
    assert isinstance(out["roi_curve_90d"], list)
    assert out["roi_curve_90d"][0]["date"] == "2026-01-22"
```

- [ ] Lancer `pytest tests/test_public_track_record.py -v`
- [ ] Expected: FAIL (module inexistant `ModuleNotFoundError`).
- [ ] Commit : `test(api/v2): public track-record live route shape`.

#### T01.2 · Pydantic model + route

- [ ] Créer `ProbaLab/api/routers/v2/public_track_record.py` :

```python
# ProbaLab/api/routers/v2/public_track_record.py
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from api.rate_limit import limiter
from src.config import supabase

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/public", tags=["public"])

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SEC = 300  # 5 minutes


class RoiPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str
    cumulative_roi: float


class TrackRecordLive(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clv_30d: float = Field(..., description="CLV moyen 30 jours (%)")
    roi_90d: float = Field(..., description="ROI 90 jours (%)")
    brier_30d: float = Field(..., description="Brier score 30 jours")
    safe_rate_90d: float = Field(..., description="Hit rate Safe picks 90j (0-1)")
    roi_curve_90d: List[RoiPoint]


@router.get("/track-record/live", response_model=TrackRecordLive)
@limiter.limit("30/minute")
async def get_track_record_live(request: Request) -> dict:
    now = time.monotonic()
    cached = _CACHE.get("live")
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]

    now_utc = datetime.now(timezone.utc)
    d30 = (now_utc - timedelta(days=30)).isoformat()
    d90 = (now_utc - timedelta(days=90)).isoformat()

    clv_rows = supabase.table("model_health_log").select("clv_pct").gte("created_at", d30).execute().data or []
    clv_30d = round(sum(r["clv_pct"] for r in clv_rows) / len(clv_rows), 2) if clv_rows else 0.0

    roi_rows = supabase.table("best_bets").select("roi_pct, n_bets").gte("created_at", d90).execute().data or []
    roi_90d = round(sum(r["roi_pct"] for r in roi_rows) / len(roi_rows), 2) if roi_rows else 0.0

    brier_rows = supabase.table("predictions_results").select("brier").gte("created_at", d30).execute().data or []
    brier_30d = round(sum(r["brier"] for r in brier_rows) / len(brier_rows), 3) if brier_rows else 0.0

    safe_rows = supabase.table("best_bets").select("safe_rate").gte("created_at", d90).execute().data or []
    safe_rate_90d = round(sum(r["safe_rate"] for r in safe_rows) / len(safe_rows), 3) if safe_rows else 0.0

    curve_rows = supabase.table("best_bets").select("d, cum_roi").gte("d", d90).order("d").execute().data or []
    roi_curve_90d = [{"date": r["d"], "cumulative_roi": float(r["cum_roi"])} for r in curve_rows]

    payload = {
        "clv_30d": clv_30d,
        "roi_90d": roi_90d,
        "brier_30d": brier_30d,
        "safe_rate_90d": safe_rate_90d,
        "roi_curve_90d": roi_curve_90d,
    }
    _CACHE["live"] = (now, payload)
    return payload
```

- [ ] Inclure dans `api/main.py` : `from api.routers.v2 import public_track_record as v2_public_tr ; app.include_router(v2_public_tr.router)`.
- [ ] Lancer `pytest tests/test_public_track_record.py -v` → PASS.
- [ ] Commit : `feat(api/v2): GET /api/public/track-record/live with 5min cache`.

---

### T02 · `GET /api/safe-pick?date=YYYY-MM-DD`

**Logique : 1 pari cote ∈ [1.80, 2.20] avec confiance max, sinon combo 2 legs cote produit ∈ [1.80, 2.20], sinon null.**

#### T02.1 · Test logique pure (failing)

- [ ] Créer `ProbaLab/tests/test_safe_pick_selector.py` :

```python
# ProbaLab/tests/test_safe_pick_selector.py
from src.models.safe_pick_selector import select_safe_pick


def test_single_bet_in_band_wins_over_combo():
    candidates = [
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 2.00, "confidence": 0.72},
        {"fixture_id": "f2", "market": "OU", "selection": "O2.5", "odds": 1.85, "confidence": 0.65},
        {"fixture_id": "f3", "market": "1X2", "selection": "A", "odds": 3.10, "confidence": 0.80},  # hors bande
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "single"
    assert out["safe_pick"]["fixture_id"] == "f1"  # confidence la plus haute dans la bande


def test_fallback_combo_2_legs():
    candidates = [
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 1.40, "confidence": 0.82},
        {"fixture_id": "f2", "market": "OU", "selection": "O2.5", "odds": 1.45, "confidence": 0.78},
        {"fixture_id": "f3", "market": "1X2", "selection": "X", "odds": 3.20, "confidence": 0.50},
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"]["type"] == "combo"
    assert len(out["safe_pick"]["legs"]) == 2
    product = out["safe_pick"]["legs"][0]["odds"] * out["safe_pick"]["legs"][1]["odds"]
    assert 1.80 <= product <= 2.20


def test_no_pick_returns_fallback_message():
    candidates = [
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 3.50, "confidence": 0.70},
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is None
    assert "fallback_message" in out and out["fallback_message"]
```

- [ ] Lancer `pytest tests/test_safe_pick_selector.py -v` → FAIL (module inexistant).
- [ ] Commit : `test(api/v2): safe_pick_selector unit cases`.

#### T02.2 · Implémenter `src/models/safe_pick_selector.py`

- [ ] Créer le fichier :

```python
# ProbaLab/src/models/safe_pick_selector.py
from __future__ import annotations
from itertools import combinations
from typing import Any

ODDS_MIN, ODDS_MAX = 1.80, 2.20
MIN_CONFIDENCE_SINGLE = 0.60


def select_safe_pick(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return {'safe_pick': {...}} or {'safe_pick': None, 'fallback_message': '...'}."""
    singles = [
        c for c in candidates
        if ODDS_MIN <= c["odds"] <= ODDS_MAX and c["confidence"] >= MIN_CONFIDENCE_SINGLE
    ]
    if singles:
        best = max(singles, key=lambda c: c["confidence"])
        return {"safe_pick": {"type": "single", **best}}

    low_odds = sorted(
        [c for c in candidates if c["odds"] < ODDS_MIN],
        key=lambda c: c["confidence"], reverse=True,
    )
    for a, b in combinations(low_odds, 2):
        if a["fixture_id"] == b["fixture_id"]:
            continue
        product = a["odds"] * b["odds"]
        if ODDS_MIN <= product <= ODDS_MAX:
            return {"safe_pick": {"type": "combo", "legs": [a, b], "odds_product": round(product, 2)}}

    return {
        "safe_pick": None,
        "fallback_message": "Aucun pari Safe ne correspond aux critères aujourd'hui. Revenez demain.",
    }
```

- [ ] Lancer `pytest tests/test_safe_pick_selector.py -v` → PASS.
- [ ] Commit : `feat(api/v2): safe_pick_selector logic (single + combo fallback)`.

#### T02.3 · Test route `/api/safe-pick` (failing)

- [ ] Créer `ProbaLab/tests/test_safe_pick.py` :

```python
# ProbaLab/tests/test_safe_pick.py
from unittest.mock import MagicMock
import pytest
from api.routers.v2.safe_pick import get_safe_pick


@pytest.mark.asyncio
async def test_safe_pick_uses_selector(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 2.0, "confidence": 0.72},
    ])
    out = await get_safe_pick.__wrapped__(date="2026-04-21", request=MagicMock(), user=fake_user)
    assert out["safe_pick"]["type"] == "single"
    assert out["safe_pick"]["fixture_id"] == "f1"


@pytest.mark.asyncio
async def test_safe_pick_empty_returns_message(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[])
    out = await get_safe_pick.__wrapped__(date="2026-04-21", request=MagicMock(), user=fake_user)
    assert out["safe_pick"] is None
    assert out["fallback_message"]
```

- [ ] FAIL attendu. Commit : `test(api/v2): /api/safe-pick route`.

#### T02.4 · Route FastAPI

- [ ] Créer `ProbaLab/api/routers/v2/safe_pick.py` :

```python
# ProbaLab/api/routers/v2/safe_pick.py
from __future__ import annotations
from datetime import date as date_type
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from api.auth import current_user
from api.rate_limit import limiter
from src.config import supabase
from src.models.safe_pick_selector import select_safe_pick

router = APIRouter(prefix="/api", tags=["safe-pick"])


class SafePickResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    safe_pick: dict[str, Any] | None
    fallback_message: str | None = None


@router.get("/safe-pick", response_model=SafePickResponse)
@limiter.limit("60/minute")
async def get_safe_pick(
    request: Request,
    date: date_type = Query(..., description="YYYY-MM-DD UTC"),
    user: dict = Depends(current_user),
) -> dict:
    iso = date.isoformat()
    rows = (
        supabase.table("predictions")
        .select("fixture_id, market, selection, odds, confidence")
        .eq("match_date", iso)
        .execute()
        .data
        or []
    )
    return select_safe_pick([dict(r) for r in rows])
```

- [ ] Inclure dans `api/main.py`.
- [ ] `pytest tests/test_safe_pick.py -v` → PASS.
- [ ] Commit : `feat(api/v2): GET /api/safe-pick with single/combo selection`.

---

### T03 · `GET /api/matches`

**Endpoint consolidé foot + NHL, filtres `date, sports, leagues, signals, sort`, structure groupée par ligue.**

#### T03.1 · Test logique agrégation (failing)

- [ ] Créer `ProbaLab/tests/test_matches_aggregator.py` :

```python
# ProbaLab/tests/test_matches_aggregator.py
from src.models.matches_aggregator import aggregate_matches


def test_group_by_league_and_sort_by_time():
    rows = [
        {"fixture_id": "f2", "league_id": 39, "league_name": "Premier League",
         "kickoff_utc": "2026-04-21T17:00:00+00:00", "signals": ["value"], "confidence": 0.6, "edge_pct": 8.0},
        {"fixture_id": "f1", "league_id": 39, "league_name": "Premier League",
         "kickoff_utc": "2026-04-21T14:00:00+00:00", "signals": ["safe"], "confidence": 0.75, "edge_pct": 3.0},
        {"fixture_id": "f3", "league_id": 61, "league_name": "Ligue 1",
         "kickoff_utc": "2026-04-21T19:00:00+00:00", "signals": [], "confidence": 0.5, "edge_pct": 0.0},
    ]
    out = aggregate_matches(rows, sort="time")
    assert [g["league_id"] for g in out] == [39, 61]  # ordre stable d'apparition
    assert [m["fixture_id"] for m in out[0]["matches"]] == ["f1", "f2"]


def test_filter_by_signal():
    rows = [
        {"fixture_id": "f1", "league_id": 39, "league_name": "PL",
         "kickoff_utc": "2026-04-21T14:00:00+00:00", "signals": ["safe"], "confidence": 0.7, "edge_pct": 0.0},
        {"fixture_id": "f2", "league_id": 39, "league_name": "PL",
         "kickoff_utc": "2026-04-21T17:00:00+00:00", "signals": ["value"], "confidence": 0.6, "edge_pct": 8.0},
    ]
    out = aggregate_matches(rows, signals=["value"], sort="edge")
    assert len(out) == 1
    assert out[0]["matches"][0]["fixture_id"] == "f2"
```

- [ ] FAIL. Commit : `test(api/v2): matches_aggregator grouping + sort + signals`.

#### T03.2 · Implémenter `src/models/matches_aggregator.py`

- [ ] Créer le fichier :

```python
# ProbaLab/src/models/matches_aggregator.py
from __future__ import annotations
from typing import Any, Literal

SortKey = Literal["time", "edge", "confidence"]


def aggregate_matches(
    rows: list[dict[str, Any]],
    signals: list[str] | None = None,
    sort: SortKey = "time",
) -> list[dict[str, Any]]:
    if signals:
        rows = [r for r in rows if any(s in r.get("signals", []) for s in signals)]

    key_fn = {
        "time": lambda r: r["kickoff_utc"],
        "edge": lambda r: -float(r.get("edge_pct", 0.0)),
        "confidence": lambda r: -float(r.get("confidence", 0.0)),
    }[sort]

    groups: dict[int, dict[str, Any]] = {}
    for row in sorted(rows, key=key_fn):
        lid = row["league_id"]
        g = groups.setdefault(lid, {"league_id": lid, "league_name": row["league_name"], "matches": []})
        g["matches"].append(row)

    return list(groups.values())
```

- [ ] `pytest tests/test_matches_aggregator.py -v` → PASS.
- [ ] Commit : `feat(api/v2): matches_aggregator pure logic`.

#### T03.3 · Test route (failing)

- [ ] Créer `ProbaLab/tests/test_matches_v2.py` :

```python
# ProbaLab/tests/test_matches_v2.py
from unittest.mock import MagicMock
import pytest
from api.routers.v2.matches_v2 import get_matches


@pytest.mark.asyncio
async def test_matches_v2_basic(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[
        {"fixture_id": "f1", "league_id": 39, "league_name": "PL",
         "kickoff_utc": "2026-04-21T14:00:00+00:00", "signals": ["safe"], "confidence": 0.75, "edge_pct": 0.0},
    ])
    out = await get_matches.__wrapped__(
        request=MagicMock(), date="2026-04-21", sports="foot", leagues=None,
        signals=None, sort="time", user=fake_user,
    )
    assert out["groups"][0]["league_id"] == 39
    assert out["groups"][0]["matches"][0]["fixture_id"] == "f1"
```

- [ ] FAIL. Commit : `test(api/v2): /api/matches route shape`.

#### T03.4 · Route FastAPI

- [ ] Créer `ProbaLab/api/routers/v2/matches_v2.py` :

```python
# ProbaLab/api/routers/v2/matches_v2.py
from __future__ import annotations
from datetime import date as date_type
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from api.auth import current_user
from api.rate_limit import limiter
from src.config import supabase
from src.models.matches_aggregator import aggregate_matches

router = APIRouter(prefix="/api", tags=["matches-v2"])


class MatchesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    groups: list[dict]


@router.get("/matches", response_model=MatchesResponse)
@limiter.limit("120/minute")
async def get_matches(
    request: Request,
    date: date_type = Query(...),
    sports: str | None = Query(None, description="CSV: foot,nhl"),
    leagues: str | None = Query(None, description="CSV league_ids"),
    signals: str | None = Query(None, description="CSV: value,safe"),
    sort: Literal["time", "edge", "confidence"] = Query("time"),
    user: dict = Depends(current_user),
) -> dict:
    iso = date.isoformat()
    query = supabase.table("matches_v2_view").select("*").eq("match_date", iso)
    if sports:
        query = query.in_("sport", [s.strip() for s in sports.split(",") if s.strip()])
    if leagues:
        query = query.in_("league_id", [int(x) for x in leagues.split(",") if x.strip().isdigit()])

    rows = query.execute().data or []
    signal_list = [s.strip() for s in signals.split(",")] if signals else None
    return {"groups": aggregate_matches(rows, signals=signal_list, sort=sort)}
```

- [ ] Note : `matches_v2_view` sera créée dans une task DB ultérieure ou mockée via JOIN runtime ; à V1, requête directe `predictions` + `fixtures` + `best_bets` acceptable. Si la view manque, noter dans `tasks/todo.md`.
- [ ] Inclure dans `api/main.py`.
- [ ] `pytest tests/test_matches_v2.py -v` → PASS.
- [ ] Commit : `feat(api/v2): GET /api/matches consolidated foot+nhl listing`.

---

### T04 · `GET /api/odds/{fixture_id}/comparison`

#### T04.1 · Test logique pure

- [ ] Créer `ProbaLab/tests/test_odds_comparator.py` :

```python
# ProbaLab/tests/test_odds_comparator.py
from src.models.odds_comparator import build_comparison


def test_best_odds_flagged_per_selection():
    rows = [
        {"market": "1X2", "selection": "H", "bookmaker": "Winamax", "odds": 1.85},
        {"market": "1X2", "selection": "H", "bookmaker": "Unibet",   "odds": 1.92},
        {"market": "1X2", "selection": "X", "bookmaker": "Winamax", "odds": 3.40},
    ]
    out = build_comparison(rows)
    assert out["1X2"]["H"][0]["bookmaker"] == "Unibet"
    assert out["1X2"]["H"][0]["is_best"] is True
    assert out["1X2"]["H"][1]["is_best"] is False
    assert out["1X2"]["X"][0]["is_best"] is True
```

- [ ] FAIL → commit `test(api/v2): odds_comparator unit`.

#### T04.2 · Implémenter

- [ ] Créer `ProbaLab/src/models/odds_comparator.py` :

```python
# ProbaLab/src/models/odds_comparator.py
from __future__ import annotations
from typing import Any


def build_comparison(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[dict]]]:
    grouped: dict[str, dict[str, list[dict]]] = {}
    for r in rows:
        m, s = r["market"], r["selection"]
        grouped.setdefault(m, {}).setdefault(s, []).append(
            {"bookmaker": r["bookmaker"], "odds": float(r["odds"]), "is_best": False}
        )
    for m in grouped.values():
        for sel_list in m.values():
            sel_list.sort(key=lambda x: x["odds"], reverse=True)
            sel_list[0]["is_best"] = True
    return grouped
```

- [ ] PASS → commit `feat(api/v2): odds_comparator highlights best odds`.

#### T04.3 · Test route

- [ ] Créer `ProbaLab/tests/test_odds_comparison.py` :

```python
# ProbaLab/tests/test_odds_comparison.py
from unittest.mock import MagicMock
import pytest
from api.routers.v2.odds_comparison import get_odds_comparison


@pytest.mark.asyncio
async def test_odds_comparison_shape(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[
        {"market": "1X2", "selection": "H", "bookmaker": "Winamax", "odds": 1.85},
        {"market": "1X2", "selection": "H", "bookmaker": "Unibet",   "odds": 1.92},
    ])
    out = await get_odds_comparison.__wrapped__(
        fixture_id="f1", request=MagicMock(), user=fake_user,
    )
    assert out["comparison"]["1X2"]["H"][0]["bookmaker"] == "Unibet"
```

- [ ] FAIL → commit `test(api/v2): /api/odds/:id/comparison route`.

#### T04.4 · Route

- [ ] Créer `ProbaLab/api/routers/v2/odds_comparison.py` :

```python
# ProbaLab/api/routers/v2/odds_comparison.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, ConfigDict

from api.auth import current_user
from api.rate_limit import limiter
from src.config import supabase
from src.models.odds_comparator import build_comparison

router = APIRouter(prefix="/api/odds", tags=["odds"])


class OddsComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture_id: str
    comparison: dict


@router.get("/{fixture_id}/comparison", response_model=OddsComparisonResponse)
@limiter.limit("120/minute")
async def get_odds_comparison(
    request: Request,
    fixture_id: str = Path(..., min_length=1),
    user: dict = Depends(current_user),
) -> dict:
    rows = (
        supabase.table("closing_odds")
        .select("market, selection, bookmaker, odds")
        .eq("fixture_id", fixture_id)
        .execute()
        .data
        or []
    )
    return {"fixture_id": fixture_id, "comparison": build_comparison(rows)}
```

- [ ] Inclure dans `api/main.py`.
- [ ] PASS → commit `feat(api/v2): GET /api/odds/:id/comparison`.

---

### T05 · `GET /api/user/bankroll/roi-by-market`

#### T05.1 · Test logique pure

- [ ] Créer `ProbaLab/tests/test_user_bankroll_roi_by_market.py` (partie 1 — logique) :

```python
# ProbaLab/tests/test_user_bankroll_roi_by_market.py
from src.models.roi_by_market import compute_roi_by_market


def test_grouping_and_metrics():
    bets = [
        {"market": "1X2",  "odds": 2.00, "stake": 10, "result": "WIN"},
        {"market": "1X2",  "odds": 1.80, "stake": 10, "result": "LOSS"},
        {"market": "1X2",  "odds": 1.50, "stake": 10, "result": "VOID"},
        {"market": "BTTS", "odds": 2.10, "stake": 20, "result": "WIN"},
    ]
    out = compute_roi_by_market(bets)
    one_x_two = next(r for r in out if r["market"] == "1X2")
    assert one_x_two["n"] == 3
    assert one_x_two["wins"] == 1
    assert one_x_two["losses"] == 1
    assert one_x_two["voids"] == 1
    # ROI = (profit / staked_hors_void) * 100
    # profit = (10*2 - 10) - 10 = +0 → ROI 0%
    assert abs(one_x_two["roi"] - 0.0) < 0.01
```

- [ ] FAIL → commit `test(api/v2): roi_by_market computation`.

#### T05.2 · Implémenter

- [ ] Créer `ProbaLab/src/models/roi_by_market.py` :

```python
# ProbaLab/src/models/roi_by_market.py
from __future__ import annotations
from collections import defaultdict
from typing import Any


def compute_roi_by_market(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"n": 0, "wins": 0, "losses": 0, "voids": 0, "staked": 0.0, "profit": 0.0}
    )
    for b in bets:
        k = b["market"]
        buckets[k]["n"] += 1
        stake, odds = float(b["stake"]), float(b["odds"])
        if b["result"] == "WIN":
            buckets[k]["wins"] += 1
            buckets[k]["staked"] += stake
            buckets[k]["profit"] += stake * (odds - 1)
        elif b["result"] == "LOSS":
            buckets[k]["losses"] += 1
            buckets[k]["staked"] += stake
            buckets[k]["profit"] -= stake
        elif b["result"] == "VOID":
            buckets[k]["voids"] += 1

    out = []
    for market, v in buckets.items():
        roi = round((v["profit"] / v["staked"]) * 100, 2) if v["staked"] > 0 else 0.0
        out.append({
            "market": market, "roi": roi,
            "n": int(v["n"]), "wins": int(v["wins"]),
            "losses": int(v["losses"]), "voids": int(v["voids"]),
        })
    return sorted(out, key=lambda r: -r["roi"])
```

- [ ] PASS → commit `feat(api/v2): roi_by_market pure calc`.

#### T05.3 · Test route + T05.4 Route

- [ ] Étendre `test_user_bankroll_roi_by_market.py` :

```python
# (append)
from unittest.mock import MagicMock
import pytest
from api.routers.v2.user_bankroll import get_roi_by_market


@pytest.mark.asyncio
async def test_route_returns_breakdown(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[
        {"market": "1X2", "odds": 2.0, "stake": 10, "result": "WIN"},
    ])
    out = await get_roi_by_market.__wrapped__(window=30, request=MagicMock(), user=fake_user)
    assert out["rows"][0]["market"] == "1X2"
    assert out["rows"][0]["wins"] == 1
```

- [ ] FAIL → commit `test(api/v2): roi-by-market route`.
- [ ] Créer `ProbaLab/api/routers/v2/user_bankroll.py` :

```python
# ProbaLab/api/routers/v2/user_bankroll.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from api.auth import current_user
from api.rate_limit import limiter
from src.config import supabase
from src.models.roi_by_market import compute_roi_by_market

router = APIRouter(prefix="/api/user/bankroll", tags=["bankroll"])


class RoiByMarketRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market: str
    roi: float
    n: int
    wins: int
    losses: int
    voids: int


class RoiByMarketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_days: int
    rows: list[RoiByMarketRow]


@router.get("/roi-by-market", response_model=RoiByMarketResponse)
@limiter.limit("60/minute")
async def get_roi_by_market(
    request: Request,
    window: int = Query(30, ge=1, le=365),
    user: dict = Depends(current_user),
) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=window)).isoformat()
    rows = (
        supabase.table("user_bets")
        .select("market, odds, stake, result")
        .eq("user_id", user["id"])
        .gte("created_at", since)
        .execute()
        .data
        or []
    )
    return {"window_days": window, "rows": compute_roi_by_market(rows)}


class BankrollSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stake_initial: float = Field(..., ge=0)
    kelly_fraction: float = Field(..., gt=0, le=1)
    stake_cap_pct: float = Field(..., gt=0, le=1)


@router.put("/settings", response_model=BankrollSettings)
@limiter.limit("30/minute")
async def put_bankroll_settings(
    request: Request,
    payload: BankrollSettings = Body(...),
    user: dict = Depends(current_user),
) -> dict:
    data = payload.model_dump()
    data["user_id"] = user["id"]
    supabase.table("user_bankroll_settings").upsert(data, on_conflict="user_id").execute()
    return payload.model_dump()
```

- [ ] Inclure dans `api/main.py`.
- [ ] `pytest tests/test_user_bankroll_roi_by_market.py -v` → PASS.
- [ ] Commit : `feat(api/v2): GET /api/user/bankroll/roi-by-market`.

---

### T06 · `PUT /api/user/bankroll/settings`

*Route déjà co-implémentée dans `user_bankroll.py` (T05). On sépare juste le cycle de test.*

#### T06.1 · Test (failing d'abord)

- [ ] Créer `ProbaLab/tests/test_user_bankroll_settings.py` :

```python
# ProbaLab/tests/test_user_bankroll_settings.py
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError
from api.routers.v2.user_bankroll import put_bankroll_settings, BankrollSettings


@pytest.mark.asyncio
async def test_put_settings_upserts(mock_supabase, fake_user):
    payload = BankrollSettings(stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=0.05)
    out = await put_bankroll_settings.__wrapped__(request=MagicMock(), payload=payload, user=fake_user)
    assert out["stake_initial"] == 100.0
    mock_supabase.table.assert_any_call("user_bankroll_settings")


def test_payload_rejects_invalid_fraction():
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=100.0, kelly_fraction=1.5, stake_cap_pct=0.05)


def test_payload_rejects_extra_fields():
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=0.05, foo="bar")
```

- [ ] Lancer puis PASS (la route existe déjà depuis T05 — ce cycle valide juste la contrainte Pydantic + upsert).
- [ ] Commit : `test(api/v2): user bankroll settings upsert + Pydantic strict`.

---

### T07 · `GET /api/user/notifications/rules`

#### T07.1 · Test failing

- [ ] Créer `ProbaLab/tests/test_user_notification_rules.py` (partie 1) :

```python
# ProbaLab/tests/test_user_notification_rules.py
from unittest.mock import MagicMock
import pytest
from api.routers.v2.user_notifications import list_rules


@pytest.mark.asyncio
async def test_list_rules_returns_user_rules(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[
        {"id": "r1", "user_id": fake_user["id"], "name": "Value foot",
         "conditions": [], "logic": "and", "channels": ["telegram"],
         "secondary_actions": [], "enabled": True,
         "created_at": "2026-04-21T00:00:00+00:00",
         "updated_at": "2026-04-21T00:00:00+00:00"},
    ])
    out = await list_rules.__wrapped__(request=MagicMock(), user=fake_user)
    assert len(out["rules"]) == 1
    assert out["rules"][0]["name"] == "Value foot"
```

- [ ] FAIL → commit `test(api/v2): list notification rules`.

#### T07.2 · Router initial (utilisé aussi par T08–T10)

- [ ] Créer `ProbaLab/api/routers/v2/user_notifications.py` :

```python
# ProbaLab/api/routers/v2/user_notifications.py
from __future__ import annotations
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.auth import current_user
from api.rate_limit import limiter
from src.config import supabase

router = APIRouter(prefix="/api/user/notifications", tags=["notifications"])


class RuleCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(..., min_length=1, max_length=40)
    op: Literal["eq", "gt", "gte", "lt", "lte", "in"]
    value: str | float | int | list[str] | list[float] | list[int]


class NotificationRuleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=80)
    conditions: list[RuleCondition] = Field(default_factory=list, max_length=3)
    logic: Literal["and", "or"] = "and"
    channels: list[Literal["telegram", "email", "push"]] = Field(default_factory=list)
    secondary_actions: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("channels")
    @classmethod
    def _unique_channels(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("channels must be unique")
        return v


class NotificationRuleOut(NotificationRuleIn):
    id: str
    created_at: str
    updated_at: str


class RulesListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[NotificationRuleOut]


@router.get("/rules", response_model=RulesListResponse)
@limiter.limit("60/minute")
async def list_rules(request: Request, user: dict = Depends(current_user)) -> dict:
    rows = (
        supabase.table("notification_rules")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    return {"rules": rows}


@router.post("/rules", response_model=NotificationRuleOut, status_code=201)
@limiter.limit("30/minute")
async def create_rule(
    request: Request,
    payload: NotificationRuleIn = Body(...),
    user: dict = Depends(current_user),
) -> dict:
    data = payload.model_dump()
    data["user_id"] = user["id"]
    res = supabase.table("notification_rules").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="insert_failed")
    return res.data[0]


@router.put("/rules/{rule_id}", response_model=NotificationRuleOut)
@limiter.limit("30/minute")
async def update_rule(
    request: Request,
    rule_id: UUID = Path(...),
    payload: NotificationRuleIn = Body(...),
    user: dict = Depends(current_user),
) -> dict:
    res = (
        supabase.table("notification_rules")
        .update(payload.model_dump())
        .eq("id", str(rule_id))
        .eq("user_id", user["id"])
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="rule_not_found")
    return res.data[0]


@router.delete("/rules/{rule_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_rule(
    request: Request,
    rule_id: UUID = Path(...),
    user: dict = Depends(current_user),
) -> None:
    res = (
        supabase.table("notification_rules")
        .delete()
        .eq("id", str(rule_id))
        .eq("user_id", user["id"])
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="rule_not_found")
```

- [ ] Inclure dans `api/main.py`.
- [ ] `pytest tests/test_user_notification_rules.py -v` → T07 PASS.
- [ ] Commit : `feat(api/v2): GET /api/user/notifications/rules`.

---

### T08 · `POST /api/user/notifications/rules`

#### T08.1 · Test failing

- [ ] Ajouter à `test_user_notification_rules.py` :

```python
from api.routers.v2.user_notifications import create_rule, NotificationRuleIn


@pytest.mark.asyncio
async def test_create_rule_inserts(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[{
        "id": "r1", "user_id": fake_user["id"], "name": "Safe alerts",
        "conditions": [], "logic": "and", "channels": ["telegram"],
        "secondary_actions": [], "enabled": True,
        "created_at": "2026-04-21T00:00:00+00:00",
        "updated_at": "2026-04-21T00:00:00+00:00",
    }])
    payload = NotificationRuleIn(name="Safe alerts", conditions=[], logic="and",
                                 channels=["telegram"], secondary_actions=[], enabled=True)
    out = await create_rule.__wrapped__(request=MagicMock(), payload=payload, user=fake_user)
    assert out["id"] == "r1"


def test_create_rule_rejects_more_than_3_conditions():
    from pydantic import ValidationError
    from api.routers.v2.user_notifications import RuleCondition
    with pytest.raises(ValidationError):
        NotificationRuleIn(name="x", conditions=[
            RuleCondition(field="a", op="eq", value=1),
            RuleCondition(field="b", op="eq", value=1),
            RuleCondition(field="c", op="eq", value=1),
            RuleCondition(field="d", op="eq", value=1),
        ])
```

- [ ] PASS (code déjà en place depuis T07).
- [ ] Commit : `test(api/v2): POST create rule + max_length=3 guard`.

---

### T09 · `PUT /api/user/notifications/rules/{rule_id}`

#### T09.1 · Tests

- [ ] Append :

```python
from api.routers.v2.user_notifications import update_rule


@pytest.mark.asyncio
async def test_update_rule_scoped_to_user(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[{
        "id": "r1", "user_id": fake_user["id"], "name": "Renamed",
        "conditions": [], "logic": "and", "channels": ["email"],
        "secondary_actions": [], "enabled": True,
        "created_at": "2026-04-21T00:00:00+00:00",
        "updated_at": "2026-04-21T00:00:00+00:00",
    }])
    from uuid import UUID
    payload = NotificationRuleIn(name="Renamed", channels=["email"])
    out = await update_rule.__wrapped__(
        request=MagicMock(),
        rule_id=UUID("11111111-1111-1111-1111-111111111111"),
        payload=payload, user=fake_user,
    )
    assert out["name"] == "Renamed"


@pytest.mark.asyncio
async def test_update_rule_404_when_not_found(mock_supabase, fake_user):
    from fastapi import HTTPException
    from uuid import UUID
    mock_supabase.execute.return_value = MagicMock(data=[])
    with pytest.raises(HTTPException) as exc:
        await update_rule.__wrapped__(
            request=MagicMock(),
            rule_id=UUID("11111111-1111-1111-1111-111111111111"),
            payload=NotificationRuleIn(name="X"),
            user=fake_user,
        )
    assert exc.value.status_code == 404
```

- [ ] PASS → commit : `test(api/v2): PUT update rule + 404 on foreign id`.

---

### T10 · `DELETE /api/user/notifications/rules/{rule_id}`

#### T10.1 · Tests

- [ ] Append :

```python
from api.routers.v2.user_notifications import delete_rule


@pytest.mark.asyncio
async def test_delete_rule_happy(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[{"id": "r1"}])
    from uuid import UUID
    res = await delete_rule.__wrapped__(
        request=MagicMock(),
        rule_id=UUID("11111111-1111-1111-1111-111111111111"),
        user=fake_user,
    )
    assert res is None


@pytest.mark.asyncio
async def test_delete_rule_404(mock_supabase, fake_user):
    from fastapi import HTTPException
    from uuid import UUID
    mock_supabase.execute.return_value = MagicMock(data=[])
    with pytest.raises(HTTPException) as exc:
        await delete_rule.__wrapped__(
            request=MagicMock(),
            rule_id=UUID("11111111-1111-1111-1111-111111111111"),
            user=fake_user,
        )
    assert exc.value.status_code == 404
```

- [ ] PASS → commit : `test(api/v2): DELETE rule + 404 on missing`.

---

## T11 · Test d'intégration end-to-end (OpenAPI + smoke)

- [ ] Créer `ProbaLab/tests/test_v2_integration.py` :

```python
# ProbaLab/tests/test_v2_integration.py
from fastapi.testclient import TestClient
from api.main import app


def test_openapi_contains_all_v2_endpoints():
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = set(schema["paths"].keys())
    expected = {
        "/api/public/track-record/live",
        "/api/safe-pick",
        "/api/matches",
        "/api/odds/{fixture_id}/comparison",
        "/api/user/bankroll/roi-by-market",
        "/api/user/bankroll/settings",
        "/api/user/notifications/rules",
        "/api/user/notifications/rules/{rule_id}",
    }
    missing = expected - paths
    assert not missing, f"missing endpoints: {missing}"
```

- [ ] Lancer `pytest tests/test_v2_integration.py -v` → PASS.
- [ ] Commit : `test(api/v2): integration — OpenAPI exposes all 8 v2 paths`.

---

## Verification finale

- [ ] `cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab" && pytest -x -q`
- [ ] Expected: **TOUS** les tests passent (baseline + nouveaux du Lot 2).
- [ ] Lancer `ruff check ProbaLab/` → 0 erreur.
- [ ] Lancer `mypy ProbaLab/api/routers/v2 ProbaLab/src/models` → 0 erreur bloquante.
- [ ] Vérifier `curl -s http://localhost:8000/openapi.json | jq '.paths | keys' | grep -E "(safe-pick|track-record|matches|odds|bankroll|notifications)"` → 8 paths listés.
- [ ] Smoke test manuel (avec serveur dev local + JWT valide) :
  - `GET /api/public/track-record/live` → 200 JSON valide.
  - `GET /api/safe-pick?date=2026-04-21` → 200.
  - `GET /api/matches?date=2026-04-21&sports=foot` → 200.
- [ ] Mettre à jour `ProbaLab/tasks/todo.md` : marquer Lot 2 = done.
- [ ] Ajouter une entrée dans `ProbaLab/tasks/lessons.md` si une surprise rencontrée.

---

## Critères d'acceptation Lot 2

- [ ] 10 endpoints livrés, documentés dans OpenAPI.
- [ ] 3 migrations appliquées (ou T13 skippée si `user_bets` déjà existante et conforme).
- [ ] RLS strict sur `user_bankroll_settings`, `user_bets`, `notification_rules` (service_role_all + authenticated_own_rows).
- [ ] Logique métier extraite dans `src/models/` et `src/notifications/` (≤ 120 lignes par fichier).
- [ ] Tests pytest verts : routes + logique pure + intégration OpenAPI.
- [ ] Pydantic v2 strict (`extra="forbid"`) partout, timezone UTC systématique.
- [ ] Aucun `fixture_id` typé `int` (lesson 48) dans le code livré.
- [ ] Commits respectant le format `feat(api/v2): ...` / `test(api/v2): ...` / `feat(db): ...` avec Co-Authored-By.

---

## Prochaine étape

Lot 3 — Accueil + Matchs : [2026-04-21-frontend-refonte-v1-lot-3-home-matches.md](./2026-04-21-frontend-refonte-v1-lot-3-home-matches.md)
