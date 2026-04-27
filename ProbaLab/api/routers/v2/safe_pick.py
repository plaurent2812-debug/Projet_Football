"""api/routers/v2/safe_pick.py — Safe pick of the day (Lot 2 · T02).

Returns one "safe" bet of the day, selected by the pure function
`src.models.safe_pick_selector.select_safe_pick`. The route itself is a
minimal glue layer (lesson 63): read candidates from Supabase, hand them off
to the selector, wrap the payload with the requested date. Rate-limited via
the shared slowapi decorator (lesson 64).

Real Supabase schema (validated via prod `/api/predictions`):

- ``predictions`` holds **football only** model probabilities in *percent*
  (0..100), joined to ``fixtures`` on ``fixture_id``. There is no
  ``match_date`` / ``sport`` / ``selection`` / ``confidence`` column here —
  those are derived in Python.
- ``fixtures.date`` is the kickoff timestamp (UTC).
- ``fixture_odds`` holds real bookmaker odds, keyed by
  ``fixtures.api_fixture_id``.
- NHL predictions live inside ``nhl_fixtures.stats_json.top_players``
  (player props). We expose them best-effort — if the shape is missing, we
  simply skip NHL for this pick (graceful fallback).
"""

from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from api.rate_limit import _rate_limit
from src.config import supabase
from src.models.safe_pick_selector import (
    MIN_CONFIDENCE_SINGLE,
    ODDS_MAX,
    ODDS_MIN,
    select_safe_pick,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["safe-pick"])


# Pydantic shapes ---------------------------------------------------------


class SafePickSingle(BaseModel):
    """A single-bet safe pick. Extra fields are allowed to carry through the
    candidate row untouched (sport, market, selection, confidence, kickoff…)."""

    model_config = ConfigDict(extra="allow")
    type: Literal["single"]
    fixture_id: str
    odds: float
    confidence: float


class SafePickCombo(BaseModel):
    """A 2-leg combo safe pick."""

    model_config = ConfigDict(extra="allow")
    type: Literal["combo"]
    legs: list[dict[str, Any]] = Field(..., min_length=2, max_length=2)
    odds_product: float


class SafePickResponse(BaseModel):
    """Route response model. ``safe_pick`` is `None` when no candidate passes."""

    model_config = ConfigDict(extra="forbid")
    date: str = Field(..., description="YYYY-MM-DD UTC")
    safe_pick: dict[str, Any] | None
    fallback_message: str | None = None


# Helpers -----------------------------------------------------------------


# Map of football market label → (probability_key, bookmaker_odds_key).
# Kept intentionally small: the markets we consider for a "safe" pick are the
# ones with the most reliable bookmaker prices AND calibrated probas.
_FOOTBALL_MARKETS: list[tuple[str, str, str, str]] = [
    # (market_label, selection_label, proba_key, odds_key)
    ("1X2", "home", "proba_home", "home_win_odds"),
    ("1X2", "draw", "proba_draw", "draw_odds"),
    ("1X2", "away", "proba_away", "away_win_odds"),
    ("BTTS", "yes", "proba_btts", "btts_yes_odds"),
    ("Over/Under 2.5", "over", "proba_over_2_5", "over_25_odds"),
    ("Over/Under 1.5", "over", "proba_over_15", "over_15_odds"),
]


def _pct_to_decimal(value: Any) -> float | None:
    """Convert a percent value stored as float/int (0..100) into 0..1.

    Returns ``None`` if the value is missing or invalid.
    """
    if value is None:
        return None
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return None
    if pct <= 0:
        return None
    # Tolerate already-normalised 0..1 inputs just in case a future migration
    # changes the shape.
    return pct / 100.0 if pct > 1.0 else pct


def _implied_odds(prob: float | None) -> float | None:
    """Return 1/prob (with a safety margin stripped) or ``None`` when prob ≤ 0."""
    if prob is None or prob <= 0:
        return None
    # Subtracting a small margin mirrors what `api/routers/best_bets.py` does
    # for estimated odds (keeps implied odds realistic vs flat 1/p).
    return round((1.0 / prob) * 0.95, 2)


def _build_football_candidates(
    predictions: list[dict[str, Any]],
    fixtures_by_id: dict[str, dict[str, Any]],
    odds_by_api_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Turn each football prediction into one candidate per market.

    One row becomes up to N candidates (one per market in `_FOOTBALL_MARKETS`).
    The selector then picks the best of all candidates across all matches.
    """
    out: list[dict[str, Any]] = []
    for pred in predictions:
        fixture_id = str(pred.get("fixture_id") or "")
        if not fixture_id:
            continue
        fix = fixtures_by_id.get(fixture_id)
        if not fix:
            continue

        confidence_score = pred.get("confidence_score")
        # confidence_score is an int 1..10 in DB — normalise to 0..1.
        try:
            confidence = float(confidence_score) / 10.0 if confidence_score is not None else 0.0
        except (TypeError, ValueError):
            confidence = 0.0

        api_fid = fix.get("api_fixture_id")
        odds_row = odds_by_api_id.get(str(api_fid)) if api_fid is not None else None

        for market, selection, proba_key, odds_key in _FOOTBALL_MARKETS:
            prob = _pct_to_decimal(pred.get(proba_key))
            if prob is None:
                continue

            real_odds = None
            if odds_row is not None:
                raw = odds_row.get(odds_key)
                try:
                    real_odds = float(raw) if raw is not None and float(raw) > 1.0 else None
                except (TypeError, ValueError):
                    real_odds = None

            odds_val = real_odds if real_odds else _implied_odds(prob)
            if odds_val is None or odds_val < 1.05:
                continue

            out.append(
                {
                    "fixture_id": fixture_id,
                    "sport": "football",
                    "market": market,
                    "selection": selection,
                    "odds": float(odds_val),
                    "confidence": confidence,
                    "kickoff_utc": fix.get("date"),
                    "league_id": fix.get("league_id"),
                    "league_name": fix.get("league_name"),
                    "home_team": fix.get("home_team"),
                    "away_team": fix.get("away_team"),
                    "odds_source": "real" if real_odds else "implied",
                }
            )
    return out


def _build_nhl_candidates(nhl_fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build best-effort NHL candidates from ``nhl_fixtures.stats_json.top_players``.

    The NHL pipeline stores player props inside ``stats_json``. Each entry
    may expose ``prob_point`` / ``prob_assist`` / ``prob_goal`` / ``prob_shot``
    in *percent*. We only surface points + assists (the same markets the
    existing ticket generator uses for NHL singles). If any field is missing
    or malformed, we skip the row silently — this mirrors the spec's
    "graceful fallback" requirement.
    """
    out: list[dict[str, Any]] = []
    for fix in nhl_fixtures or []:
        fixture_id = str(fix.get("id") or "")
        if not fixture_id:
            continue
        stats = fix.get("stats_json") or {}
        if not isinstance(stats, dict):
            continue
        players = stats.get("top_players") or []
        if not isinstance(players, list):
            continue

        for pl in players:
            if not isinstance(pl, dict):
                continue
            for market, prob_key in (
                ("Player Points", "prob_point"),
                ("Player Assists", "prob_assist"),
            ):
                prob = _pct_to_decimal(pl.get(prob_key))
                if prob is None:
                    continue
                odds_val = _implied_odds(prob)
                if odds_val is None or odds_val < 1.05:
                    continue
                # Confidence for NHL: use the probability itself as a proxy
                # (no confidence_score column available). Clamp to [0, 1].
                confidence = max(0.0, min(1.0, prob))
                out.append(
                    {
                        "fixture_id": fixture_id,
                        "sport": "nhl",
                        "market": market,
                        "selection": pl.get("player_name") or "",
                        "odds": float(odds_val),
                        "confidence": confidence,
                        "kickoff_utc": fix.get("date"),
                        "home_team": fix.get("home_team"),
                        "away_team": fix.get("away_team"),
                        "odds_source": "implied",
                    }
                )
    return out


# Route -------------------------------------------------------------------


@router.get(
    "/safe-pick",
    response_model=SafePickResponse,
    summary="Safe pick of the day (single cote ∈ [1.80, 2.20] or 2-leg combo).",
)
@_rate_limit("30/minute")
def get_safe_pick(
    request: Request,
    date: date_type | None = Query(
        default=None,
        description="Target UTC date (YYYY-MM-DD). Defaults to today UTC.",
    ),
) -> dict[str, Any]:
    """Return at most one safe pick for the given date.

    The route joins ``fixtures`` (for the UTC day) with ``predictions`` +
    ``fixture_odds`` (football) and best-effort ``nhl_fixtures`` (NHL).
    Candidates are one-per-market-per-fixture and are fed to the pure
    selector which picks the single-best or a 2-leg combo whose odds
    product sits in the [1.80, 2.20] band.
    """
    target = date if date is not None else datetime.now(timezone.utc).date()
    iso = target.isoformat()
    next_day_iso = (target + timedelta(days=1)).isoformat()

    # ── Football --------------------------------------------------------
    fixtures: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    odds_rows: list[dict[str, Any]] = []
    try:
        fixtures = (
            supabase.table("fixtures")
            .select(
                "id, api_fixture_id, home_team, away_team, date, status, league_id, league_name"
            )
            .gte("date", iso)
            .lt("date", next_day_iso)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("safe_pick: failed to fetch fixtures for date=%s", iso)

    fixtures_by_id: dict[str, dict[str, Any]] = {}
    fixture_ids: list[str] = []
    api_fids: list[Any] = []
    for f in fixtures:
        if not isinstance(f, dict):
            continue
        fid = f.get("id")
        if fid is None:
            continue
        key = str(fid)
        fixtures_by_id[key] = f
        fixture_ids.append(key)
        if f.get("api_fixture_id") is not None:
            api_fids.append(f["api_fixture_id"])

    if fixture_ids:
        try:
            predictions = (
                supabase.table("predictions")
                .select(
                    "fixture_id, proba_home, proba_draw, proba_away, proba_btts, "
                    "proba_over_2_5, proba_over_15, confidence_score, recommended_bet"
                )
                .in_("fixture_id", fixture_ids)
                .gte("confidence_score", 6)
                .execute()
                .data
                or []
            )
        except Exception:
            logger.exception("safe_pick: failed to fetch predictions for date=%s", iso)
            predictions = []

    if api_fids:
        try:
            odds_rows = (
                supabase.table("fixture_odds")
                .select(
                    "fixture_api_id, home_win_odds, draw_odds, away_win_odds, "
                    "btts_yes_odds, over_25_odds, over_15_odds"
                )
                .in_("fixture_api_id", api_fids)
                .execute()
                .data
                or []
            )
        except Exception:
            logger.exception("safe_pick: failed to fetch odds for date=%s", iso)
            odds_rows = []

    odds_by_api_id = {
        str(o.get("fixture_api_id")): o for o in odds_rows if o.get("fixture_api_id") is not None
    }

    football_candidates = _build_football_candidates(predictions, fixtures_by_id, odds_by_api_id)

    # ── NHL (best-effort) ----------------------------------------------
    nhl_fixtures: list[dict[str, Any]] = []
    try:
        nhl_fixtures = (
            supabase.table("nhl_fixtures")
            .select("id, home_team, away_team, date, status, stats_json")
            .gte("date", iso)
            .lt("date", next_day_iso)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning("safe_pick: NHL fetch failed (non-fatal) for date=%s", iso, exc_info=True)
        nhl_fixtures = []

    nhl_candidates = _build_nhl_candidates(nhl_fixtures)

    # ── Select ----------------------------------------------------------
    candidates = football_candidates + nhl_candidates
    payload = select_safe_pick(candidates)
    return {
        "date": iso,
        "safe_pick": payload["safe_pick"],
        "fallback_message": payload.get("fallback_message"),
    }


# Re-export selector band constants so routers/tests can reference a single
# source of truth without reaching into ``src.models`` twice.
__all__ = [
    "ODDS_MIN",
    "ODDS_MAX",
    "MIN_CONFIDENCE_SINGLE",
    "SafePickResponse",
    "router",
    "get_safe_pick",
]
