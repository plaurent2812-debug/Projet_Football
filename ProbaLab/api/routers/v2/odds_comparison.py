"""api/routers/v2/odds_comparison.py — Odds comparison endpoint (Lot 2 · T04).

Returns a flat comparison mapping for a given fixture:
``{market: {selection: [{bookmaker, odds, is_best}, ...]}}``. The heavy lifting
is delegated to the pure helper ``src.models.odds_comparator.build_comparison``
so the route is a thin glue layer (lesson 63). Rate-limited via the shared
slowapi decorator (lesson 64).

Schema source — ``closing_odds`` (migration 051) is already normalized on
``fixture_id / market / selection / bookmaker / odds`` so no dénormalisation
côté route is needed. The legacy ``fixture_odds`` table is *not* queried: it
carries a different shape (one wide row per fixture) and the V2 spec requires
the normalized model.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, ConfigDict

from api.auth import current_user
from api.rate_limit import _rate_limit
from src.config import supabase
from src.models.odds_comparator import build_comparison

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/odds", tags=["odds"])


class OddsComparisonResponse(BaseModel):
    """Route response model. ``comparison`` keeps the nested dict shape so the
    frontend can iterate markets without an extra normalization pass."""

    model_config = ConfigDict(extra="forbid")
    fixture_id: str
    comparison: dict[str, dict[str, list[dict[str, Any]]]]


@router.get(
    "/{fixture_id}/comparison",
    response_model=OddsComparisonResponse,
    summary="Compare bookmaker odds for a fixture, flagging the best per selection.",
)
@_rate_limit("60/minute")
def get_odds_comparison(
    request: Request,
    fixture_id: str = Path(..., min_length=1),
    user: dict = Depends(current_user),
) -> dict[str, Any]:
    """Read normalized odds rows for the fixture and delegate to the pure helper."""
    try:
        rows = (
            supabase.table("closing_odds")
            .select("market, selection, bookmaker, odds")
            .eq("fixture_id", fixture_id)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception(
            "odds_comparison: closing_odds lookup failed for fixture_id=%s", fixture_id
        )
        rows = []

    return {"fixture_id": fixture_id, "comparison": build_comparison(rows)}


__all__ = ["OddsComparisonResponse", "get_odds_comparison", "router"]
