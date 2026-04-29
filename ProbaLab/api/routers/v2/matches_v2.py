"""api/routers/v2/matches_v2.py — Consolidated matches listing (Lot 2 · T03).

Replaces the ad-hoc aggregation previously done on the frontend by combining
several endpoints (/api/predictions + /api/best-bets). Returns matches grouped
by league, filtered by sport/league/signal query params, and sorted by the
chosen strategy.

The heavy lifting lives in `src.models.matches_aggregator.aggregate_matches`
so the route itself stays a thin glue layer (lesson 63) and is rate-limited
via the shared slowapi decorator (lesson 64).

Real Supabase schema — **no ``matches_v2_view`` exists in production**, so
this route now fans out to the source tables directly:

* Football : ``fixtures`` ⋈ ``predictions`` (on ``fixture_id``) ⋈
  ``best_bets`` (on ``fixture_id``, filtered to pending football bets).
* NHL : ``nhl_fixtures`` ⋈ ``best_bets`` (sport=nhl, pending only).

Filters (sport, league, signals) and sorting are applied in Python via the
pure ``aggregate_matches`` helper. N+1 is acceptable for V1 — we aggregate
by date window which already caps the row count.
"""

from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from api.helpers import _get_league_map
from api.rate_limit import _rate_limit
from src.config import supabase
from src.models.matches_aggregator import aggregate_matches

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["matches-v2"])


# Pydantic shapes ---------------------------------------------------------


class LeagueGroup(BaseModel):
    """One league's worth of matches. Extra fields on matches are allowed."""

    model_config = ConfigDict(extra="forbid")
    league_id: int | str
    league_name: str
    matches: list[dict[str, Any]]


class MatchesV2Response(BaseModel):
    """Route response: grouped match listings with totals."""

    model_config = ConfigDict(extra="forbid")
    date: str = Field(..., description="YYYY-MM-DD UTC (the requested day).")
    total: int = Field(..., ge=0, description="Total number of matches across all groups.")
    groups: list[LeagueGroup]


# Confidence threshold above which we tag a match as high-confidence (signal).
# ``predictions.confidence_score`` is 1..10 — 7+ matches the existing
# "Priorité" / "Haute confiance" definition used by the frontend cards.
_CONFIDENCE_SIGNAL_THRESHOLD = 7


# Helpers -----------------------------------------------------------------


def _split_csv(raw: str | None) -> list[str] | None:
    """Split a comma-separated query param into a list, trimming whitespace.

    Returns ``None`` when ``raw`` is falsy so the caller can distinguish
    "no filter" from "empty filter".
    """
    if not raw:
        return None
    values = [p.strip() for p in raw.split(",") if p.strip()]
    return values or None


def _normalise_league_filter(raw_ids: list[str]) -> list[Any]:
    """Cast a list of league_id strings to int when clearly numeric.

    ``fixtures.league_id`` is an integer column, but we accept strings at the
    HTTP boundary. Mixing int/str in ``.in_()`` breaks PostgREST (lesson 48
    pattern), so we coerce here.
    """
    out: list[Any] = []
    for raw in raw_ids:
        out.append(int(raw) if raw.lstrip("-").isdigit() else raw)
    return out


def _confidence_pct(value: Any) -> float:
    """Normalise ``predictions.confidence_score`` (int 1..10) to 0..100.

    Any non-numeric input yields ``0.0`` so downstream sorting is stable.
    """
    if value is None:
        return 0.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score <= 0:
        return 0.0
    if score <= 10:
        return score * 10.0
    # If the column ever starts storing 0..100 natively, pass through.
    return min(score, 100.0)


def _compute_edge_pct(row: dict[str, Any]) -> float:
    """Return the best pending ``best_bets.kelly_edge`` for this fixture.

    ``best_bets.kelly_edge`` is already expressed as a percent. When multiple
    bets are attached to the same fixture, the max edge wins so the "value"
    signal surfaces the strongest opportunity in the UI.
    """
    bets = row.get("_best_bets") or []
    best = 0.0
    for bet in bets:
        edge = bet.get("kelly_edge")
        try:
            edge_float = float(edge) if edge is not None else 0.0
        except (TypeError, ValueError):
            edge_float = 0.0
        if edge_float > best:
            best = edge_float
    return best


def _build_nhl_prediction(fixture: dict[str, Any]) -> dict[str, Any] | None:
    """Expose stored NHL win probabilities in the common listing shape."""
    proba_home = fixture.get("proba_home")
    proba_away = fixture.get("proba_away")
    if proba_home is None and proba_away is None:
        return None
    return {
        "proba_home": proba_home,
        "proba_draw": None,
        "proba_away": proba_away,
        "confidence_score": fixture.get("confidence_score"),
    }


def _derive_signals(
    prediction: dict[str, Any] | None,
    pending_bets: list[dict[str, Any]],
    safe_fixture_id: str | None,
    fixture_id: str,
) -> list[str]:
    """Infer the ``signals`` list (value / safe / confidence) for one row.

    * ``value``     → at least one pending best_bet with positive kelly_edge.
    * ``safe``      → this fixture is the current Safe Pick of the day.
    * ``confidence``→ prediction.confidence_score ≥ 7.
    """
    signals: list[str] = []
    if any(
        (bet.get("kelly_edge") or 0) and float(bet.get("kelly_edge") or 0) > 0
        for bet in pending_bets
    ):
        signals.append("value")
    if safe_fixture_id and fixture_id == safe_fixture_id:
        signals.append("safe")
    if prediction:
        try:
            score = float(prediction.get("confidence_score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        if score >= _CONFIDENCE_SIGNAL_THRESHOLD:
            signals.append("confidence")
    return signals


def _fetch_football_rows(
    iso: str,
    next_day_iso: str,
    league_filter: list[Any] | None,
) -> list[dict[str, Any]]:
    """Fetch football fixtures + predictions + pending best_bets for the day."""
    try:
        query = supabase.table("fixtures").select("*").gte("date", iso).lt("date", next_day_iso)
        if league_filter:
            query = query.in_("league_id", league_filter)
        fixtures = query.execute().data or []
    except Exception:
        logger.exception("matches_v2: failed to fetch football fixtures for %s", iso)
        return []

    if not fixtures:
        return []

    fixture_ids = [str(f["id"]) for f in fixtures if f.get("id") is not None]

    predictions: list[dict[str, Any]] = []
    try:
        predictions = (
            supabase.table("predictions")
            .select("*")
            .in_("fixture_id", fixture_ids)
            .order("created_at")
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("matches_v2: failed to fetch predictions for %s", iso)

    pred_by_fix: dict[str, dict[str, Any]] = {}
    for p in predictions:
        key = str(p.get("fixture_id"))
        # Keep the FIRST prediction per fixture (lesson 32) — Supabase orders
        # by created_at asc.
        pred_by_fix.setdefault(key, p)

    # Pending best_bets for this set of fixtures — used to derive ``value``
    # signal + edge_pct. Filtering on ``result=PENDING`` reflects the V2
    # semantics in the user spec: only surface live signals.
    best_bets: list[dict[str, Any]] = []
    try:
        best_bets = (
            supabase.table("best_bets")
            .select("fixture_id, sport, market, selection, odds, prob, kelly_edge, result")
            .in_("fixture_id", fixture_ids)
            .eq("sport", "football")
            .is_("result", "null")
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning("matches_v2: football best_bets lookup failed for %s", iso, exc_info=True)

    bets_by_fix: dict[str, list[dict[str, Any]]] = {}
    for bet in best_bets:
        bets_by_fix.setdefault(str(bet.get("fixture_id")), []).append(bet)

    # League names come from the separate ``leagues`` table (keyed by api_id)
    # since ``fixtures.league_name`` is NULL for most rows.
    league_map = _get_league_map()

    rows: list[dict[str, Any]] = []
    for fx in fixtures:
        fid = str(fx.get("id"))
        pred = pred_by_fix.get(fid)
        pending_bets = bets_by_fix.get(fid, [])
        lid = fx.get("league_id")
        league_name = (
            fx.get("league_name")
            or (league_map.get(str(lid)) if lid is not None else None)
            or "Ligue"
        )
        row = {
            "fixture_id": fid,
            "sport": "football",
            "league_id": lid,
            "league_name": league_name,
            "home_team": fx.get("home_team"),
            "away_team": fx.get("away_team"),
            "home_logo": fx.get("home_logo"),
            "away_logo": fx.get("away_logo"),
            "status": fx.get("status"),
            "home_goals": fx.get("home_goals"),
            "away_goals": fx.get("away_goals"),
            "kickoff_utc": fx.get("date"),
            "prediction": pred,
            "confidence": _confidence_pct(pred.get("confidence_score") if pred else None),
            "_best_bets": pending_bets,
        }
        row["edge_pct"] = _compute_edge_pct(row)
        rows.append(row)
    return rows


def _fetch_nhl_rows(
    iso: str,
    next_day_iso: str,
    league_filter: list[Any] | None,
) -> list[dict[str, Any]]:
    """Fetch NHL fixtures + pending best_bets for the day (best-effort)."""
    # NHL has no ``league_id`` column — if the caller filtered by leagues
    # we cannot expose NHL matches (they're an implicit single league).
    if league_filter:
        return []

    try:
        fixtures = (
            supabase.table("nhl_fixtures")
            .select("*")
            .gte("date", iso)
            .lt("date", next_day_iso)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning("matches_v2: nhl_fixtures fetch failed for %s", iso, exc_info=True)
        return []

    if not fixtures:
        return []

    fixture_ids = [str(f["id"]) for f in fixtures if f.get("id") is not None]
    best_bets: list[dict[str, Any]] = []
    try:
        best_bets = (
            supabase.table("best_bets")
            .select("fixture_id, sport, market, selection, odds, prob, kelly_edge, result")
            .in_("fixture_id", fixture_ids)
            .eq("sport", "nhl")
            .is_("result", "null")
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning("matches_v2: nhl best_bets lookup failed for %s", iso, exc_info=True)

    bets_by_fix: dict[str, list[dict[str, Any]]] = {}
    for bet in best_bets:
        bets_by_fix.setdefault(str(bet.get("fixture_id")), []).append(bet)

    rows: list[dict[str, Any]] = []
    for fx in fixtures:
        fid = str(fx.get("id"))
        pending_bets = bets_by_fix.get(fid, [])
        prediction = _build_nhl_prediction(fx)
        row = {
            "fixture_id": fid,
            "sport": "nhl",
            # Synthetic league grouping so NHL rows cluster together in the UI.
            "league_id": "NHL",
            "league_name": "NHL",
            "home_team": fx.get("home_team"),
            "away_team": fx.get("away_team"),
            "status": fx.get("status"),
            "home_goals": fx.get("home_goals")
            if fx.get("home_goals") is not None
            else fx.get("home_score"),
            "away_goals": fx.get("away_goals")
            if fx.get("away_goals") is not None
            else fx.get("away_score"),
            "kickoff_utc": fx.get("date"),
            "prediction": prediction,
            "confidence": _confidence_pct(
                prediction.get("confidence_score") if prediction else None
            ),
            "_best_bets": pending_bets,
        }
        row["edge_pct"] = _compute_edge_pct(row)
        rows.append(row)
    return rows


# Route -------------------------------------------------------------------


@router.get(
    "/matches",
    response_model=MatchesV2Response,
    summary="Consolidated football + NHL matches listing grouped by league.",
)
@_rate_limit("30/minute")
def get_matches(
    request: Request,
    date: date_type | None = Query(
        default=None,
        description="Target UTC date (YYYY-MM-DD). Defaults to today UTC.",
    ),
    sports: str | None = Query(
        default=None,
        description="CSV of sport keys ('football', 'nhl'). Omit for all.",
    ),
    leagues: str | None = Query(
        default=None,
        description="CSV of league_id filters (e.g. '39,61').",
    ),
    signals: str | None = Query(
        default=None,
        description="CSV of signal labels ('value', 'safe', 'confidence').",
    ),
    sort: Literal["time", "edge", "confidence"] = Query(
        default="time",
        description="Sort strategy applied inside each league group.",
    ),
) -> dict[str, Any]:
    """Return the day's matches grouped by league, UTC timestamps preserved."""
    target = date if date is not None else datetime.now(timezone.utc).date()
    iso = target.isoformat()
    next_day_iso = (target + timedelta(days=1)).isoformat()

    sport_filter = _split_csv(sports)
    league_filter_raw = _split_csv(leagues)
    signal_filter = _split_csv(signals)
    league_filter = _normalise_league_filter(league_filter_raw) if league_filter_raw else None

    include_football = sport_filter is None or "football" in sport_filter
    include_nhl = sport_filter is None or "nhl" in sport_filter

    rows: list[dict[str, Any]] = []
    if include_football:
        rows.extend(_fetch_football_rows(iso, next_day_iso, league_filter))
    if include_nhl:
        rows.extend(_fetch_nhl_rows(iso, next_day_iso, league_filter))

    # Resolve the Safe Pick of the day (best-effort: selector failures must
    # not break the listing). Reused here so the "safe" signal is coherent
    # with /api/safe-pick.
    safe_fixture_id: str | None = None
    try:
        # Lazy import to avoid a circular dep at module import time.
        from api.routers.v2.safe_pick import get_safe_pick  # noqa: PLC0415

        safe_payload = get_safe_pick.__wrapped__(  # type: ignore[attr-defined]
            request=request,
            date=target,
        )
        pick = safe_payload.get("safe_pick") if isinstance(safe_payload, dict) else None
        if isinstance(pick, dict):
            if pick.get("type") == "single":
                safe_fixture_id = str(pick.get("fixture_id")) if pick.get("fixture_id") else None
            # Combos expose per-leg fixture_ids — we do not propagate multi-leg
            # "safe" signal to the listing to keep the tag unambiguous.
    except Exception:
        logger.warning("matches_v2: safe_pick lookup failed for %s", iso, exc_info=True)

    # Inject derived ``signals`` per row + strip internal helper keys.
    enriched: list[dict[str, Any]] = []
    for row in rows:
        pending_bets = row.pop("_best_bets", [])
        fid = str(row.get("fixture_id") or "")
        row["signals"] = _derive_signals(
            row.get("prediction"),
            pending_bets,
            safe_fixture_id,
            fid,
        )
        enriched.append(row)

    groups = aggregate_matches(enriched, signals=signal_filter, sort=sort)
    total = sum(len(g["matches"]) for g in groups)
    return {"date": iso, "total": total, "groups": groups}
