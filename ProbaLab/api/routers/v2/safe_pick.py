"""api/routers/v2/safe_pick.py — Safe pick of the day (Lot 2 · T02).

Returns one "safe" bet of the day, selected by the pure function
`src.models.safe_pick_selector.select_safe_pick`. The route itself is a
minimal glue layer (lesson 63): read candidates from Supabase, hand them off
to the selector, wrap the payload with the requested date. Rate-limited via
the shared slowapi decorator (lesson 64).
"""

from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from api.auth import current_user
from api.rate_limit import _rate_limit
from src.config import supabase
from src.models.safe_pick_selector import select_safe_pick

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
    user: dict = Depends(current_user),
) -> dict[str, Any]:
    """Return at most one safe pick for the given date.

    Candidates are fetched from the ``predictions`` table using the
    ``match_date`` column (UTC). The pure selector decides whether to promote
    a single bet (odds ∈ [1.80, 2.20], high confidence) or fall back on a
    2-leg combo whose odds product sits in the same window.
    """
    target = date if date is not None else datetime.now(timezone.utc).date()
    iso = target.isoformat()

    try:
        response = (
            supabase.table("predictions")
            .select("fixture_id, sport, market, selection, odds, confidence, kickoff_utc")
            .eq("match_date", iso)
            .execute()
        )
        rows = response.data or []
    except Exception:
        logger.exception("safe_pick: failed to fetch candidates for date=%s", iso)
        rows = []

    # Ensure fixture_id is treated as str (lesson 48) and filter incomplete rows.
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if row.get("fixture_id") is None:
            continue
        if row.get("odds") is None or row.get("confidence") is None:
            continue
        normalized = dict(row)
        normalized["fixture_id"] = str(normalized["fixture_id"])
        try:
            normalized["odds"] = float(normalized["odds"])
            normalized["confidence"] = float(normalized["confidence"])
        except (TypeError, ValueError):
            continue
        candidates.append(normalized)

    payload = select_safe_pick(candidates)
    return {
        "date": iso,
        "safe_pick": payload["safe_pick"],
        "fallback_message": payload.get("fallback_message"),
    }
