"""api/routers/v2/user_bankroll.py — User bankroll endpoints (Lot 2 · T05+T06).

Three user-scoped routes, all sync (lesson 64):

1. ``GET  /api/user/bankroll/roi-by-market`` — per-market ROI breakdown over
   a rolling window (default 30 days). Delegates metrics to the pure helper
   ``src.models.roi_by_market.compute_roi_by_market``.

2. ``GET  /api/user/bankroll/settings`` — Kelly fraction + stake cap + stake
   initial for the current user. Falls back to sensible defaults when no row
   exists yet in ``user_bankroll_settings`` (first visit).

3. ``PUT  /api/user/bankroll/settings`` — Pydantic-v2 strict upsert of the
   above. Extra fields rejected, ranges validated on the model.

Schema
- ``best_bets`` (read) — columns ``fixture_id, user_id, market, odds, stake,
  result, created_at``. Filter on ``user_id = current_user.id`` and
  ``created_at >= now - window days``.
- ``user_bankroll_settings`` (read/write) — PK ``user_id UUID`` referencing
  ``auth.users(id)``. Migration 054 is the source of truth for RLS policies.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from api.auth import current_user
from api.rate_limit import _rate_limit
from src.config import supabase
from src.models.roi_by_market import compute_roi_by_market

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user/bankroll", tags=["bankroll"])


# ──────────────────────────────────────────────────────────────────────
# Pydantic shapes
# ──────────────────────────────────────────────────────────────────────


class RoiByMarketRow(BaseModel):
    """One row of the per-market ROI breakdown."""

    model_config = ConfigDict(extra="forbid")
    market: str
    roi: float
    n: int = Field(..., ge=0)
    wins: int = Field(..., ge=0)
    losses: int = Field(..., ge=0)
    voids: int = Field(..., ge=0)


class RoiByMarketResponse(BaseModel):
    """Route response. ``window_days`` echoes the resolved query param."""

    model_config = ConfigDict(extra="forbid")
    window_days: int = Field(..., ge=1)
    rows: list[RoiByMarketRow]


class BankrollSettings(BaseModel):
    """Bankroll preferences — used for both GET and PUT bodies.

    Ranges follow the plan exactly:
    - stake_initial: > 0
    - kelly_fraction: ∈ (0, 1]
    - stake_cap_pct:  ∈ (0, 1]  (fraction of bankroll per bet)
    """

    model_config = ConfigDict(extra="forbid")
    stake_initial: float = Field(..., ge=0)
    kelly_fraction: float = Field(..., gt=0, le=1)
    stake_cap_pct: float = Field(..., gt=0, le=1)


# ──────────────────────────────────────────────────────────────────────
# Defaults (in sync with migration 054)
# ──────────────────────────────────────────────────────────────────────

_DEFAULT_STAKE_INITIAL = 100.0
_DEFAULT_KELLY_FRACTION = 0.25
_DEFAULT_STAKE_CAP_PCT = 0.05


def _default_settings() -> dict[str, float]:
    return {
        "stake_initial": _DEFAULT_STAKE_INITIAL,
        "kelly_fraction": _DEFAULT_KELLY_FRACTION,
        "stake_cap_pct": _DEFAULT_STAKE_CAP_PCT,
    }


# ──────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/roi-by-market",
    response_model=RoiByMarketResponse,
    summary="Per-market ROI breakdown for the current user over a rolling window.",
)
@_rate_limit("60/minute")
def get_roi_by_market(
    request: Request,
    window: int = Query(30, ge=1, le=365),
    user: dict = Depends(current_user),
) -> dict[str, Any]:
    """Return per-market ROI rows for ``current_user`` over the last ``window`` days."""
    since = (datetime.now(timezone.utc) - timedelta(days=window)).isoformat()
    try:
        rows = (
            supabase.table("best_bets")
            .select("market, odds, stake, result")
            .eq("user_id", user["id"])
            .gte("created_at", since)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("roi_by_market: best_bets lookup failed for user=%s", user.get("id"))
        rows = []

    return {"window_days": window, "rows": compute_roi_by_market(rows)}


@router.get(
    "/settings",
    response_model=BankrollSettings,
    summary="Return the current user's bankroll settings (Kelly fraction, stake cap).",
)
@_rate_limit("60/minute")
def get_bankroll_settings(
    request: Request,
    user: dict = Depends(current_user),
) -> dict[str, float]:
    """Fetch bankroll settings for ``current_user`` or fall back to defaults."""
    try:
        data = (
            supabase.table("user_bankroll_settings")
            .select("stake_initial, kelly_fraction, stake_cap_pct")
            .eq("user_id", user["id"])
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("bankroll_settings GET: lookup failed for user=%s", user.get("id"))
        data = []

    if not data:
        return _default_settings()

    row = data[0] if isinstance(data, list) else data
    # Coerce numerics so Pydantic validation doesn't trip on Decimal values
    # returned by PostgREST.
    return {
        "stake_initial": float(row.get("stake_initial") or _DEFAULT_STAKE_INITIAL),
        "kelly_fraction": float(row.get("kelly_fraction") or _DEFAULT_KELLY_FRACTION),
        "stake_cap_pct": float(row.get("stake_cap_pct") or _DEFAULT_STAKE_CAP_PCT),
    }


@router.put(
    "/settings",
    response_model=BankrollSettings,
    summary="Upsert the current user's bankroll settings (strict Pydantic validation).",
)
@_rate_limit("30/minute")
def put_bankroll_settings(
    request: Request,
    payload: BankrollSettings = Body(...),
    user: dict = Depends(current_user),
) -> dict[str, float]:
    """Upsert bankroll settings for ``current_user``.

    ``user_id`` is injected from the authenticated context — never trusted from
    the body. RLS (migration 054) also enforces ``auth.uid() = user_id`` as a
    second line of defense.
    """
    record = payload.model_dump()
    record["user_id"] = user["id"]

    try:
        supabase.table("user_bankroll_settings").upsert(record, on_conflict="user_id").execute()
    except Exception:
        logger.exception("bankroll_settings PUT: upsert failed for user=%s", user.get("id"))
        # Surface a generic 500 so the client sees the failure instead of a
        # silent "no-op OK".
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Bankroll settings save failed")

    return payload.model_dump()


__all__ = [
    "BankrollSettings",
    "RoiByMarketResponse",
    "RoiByMarketRow",
    "get_bankroll_settings",
    "get_roi_by_market",
    "put_bankroll_settings",
    "router",
]
