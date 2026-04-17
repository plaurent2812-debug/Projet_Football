"""
api/helpers.py — Shared utility functions for API routers.

Contains EV calculation, league map cache, and JSON parsing helpers
used by multiple routers.
"""

from __future__ import annotations

import logging
import math

from api.cache import TTLCache
from src.config import supabase
from src.constants import CACHE_TTL_LEAGUES

logger = logging.getLogger(__name__)


def _ensure_dict(data: dict | str | None) -> dict:
    """Helper to safely parse JSON field from Supabase that might be stringified."""
    if not data:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        import json

        try:
            return json.loads(data)
        except Exception:
            return {}
    return {}


# ─── Leagues Cache ──────────────────────────────────────────────
_league_cache = TTLCache(ttl=CACHE_TTL_LEAGUES, name="leagues")


def _get_league_map() -> dict:
    """Fetch leagues from DB, cached 1h. Returns stale data on error."""
    cached = _league_cache.get("map")
    if cached is not None:
        return cached
    try:
        leagues = supabase.table("leagues").select("api_id, name").execute().data or []
        league_map = {str(league["api_id"]): league["name"] for league in leagues}
        _league_cache.set(league_map, "map")
        return league_map
    except Exception:
        logger.warning("Error fetching leagues", exc_info=True)
        # Return stale data if available, otherwise empty dict
        return _league_cache._data.get("map", {})


# ─── Expected Value (EV+) Calculator ─────────────────────────────


def _calculate_ev(proba: float | None, odds: float | None) -> float | None:
    """EV = (Probability * Odds) - 1. Returns an edge representing expected ROI."""
    if not proba or not odds or (isinstance(odds, float) and math.isnan(odds)):
        return None
    edge = (proba / 100.0) * odds - 1.0
    return round(edge * 100, 2)  # Return as percentage (e.g. 5.4 for +5.4% EV)


def _get_ev_edges(pred: dict, odds: dict) -> dict:
    """Match model probabilities against bookmaker odds to find edges."""
    if not pred or not odds:
        return {}

    edges = {}

    # 1X2 Market
    edges["home"] = _calculate_ev(pred.get("proba_home"), odds.get("home_win_odds"))
    edges["draw"] = _calculate_ev(pred.get("proba_draw"), odds.get("draw_odds"))
    edges["away"] = _calculate_ev(pred.get("proba_away"), odds.get("away_win_odds"))

    # Over 2.5 Market
    proba_over_2_5 = pred.get("proba_over_2_5")
    edges["over_25"] = _calculate_ev(proba_over_2_5, odds.get("over_25_odds"))

    # Under 2.5 Market
    if proba_over_2_5 is not None:
        edges["under_25"] = _calculate_ev(100 - proba_over_2_5, odds.get("under_25_odds"))

    # BTTS
    edges["btts_yes"] = _calculate_ev(pred.get("proba_btts"), odds.get("btts_yes_odds"))
    if pred.get("proba_btts") is not None:
        edges["btts_no"] = _calculate_ev(100 - pred.get("proba_btts"), odds.get("btts_no_odds"))

    # Only return positive edges (Value Bets) > 2% margin of error
    return {k: v for k, v in edges.items() if v is not None and v > 2.0}
