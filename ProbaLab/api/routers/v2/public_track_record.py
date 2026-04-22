"""api/routers/v2/public_track_record.py — Live public track-record endpoint.

Exposes aggregated quality metrics (CLV 30d, ROI 90d, Brier 30d,
Safe-rate 90d, cumulative ROI curve) for the public marketing surface.
Cached 5 minutes in-process to protect Supabase from bursts.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from api.rate_limit import _rate_limit
from src.config import supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/public", tags=["public"])

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SEC = 300  # 5 minutes


class RoiPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str = Field(..., description="ISO date YYYY-MM-DD")
    cumulative_roi: float = Field(..., description="Cumulative ROI at that date (%)")


class TrackRecordLive(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clv_30d: float = Field(..., description="Average CLV over the last 30 days (%)")
    roi_90d: float = Field(..., description="Average ROI over the last 90 days (%)")
    brier_30d: float = Field(..., description="Average Brier score over the last 30 days")
    safe_rate_90d: float = Field(..., description="Safe picks hit rate over the last 90 days (0-1)")
    roi_curve_90d: list[RoiPoint] = Field(..., description="Cumulative ROI daily points over 90 days")


def _avg(values: list[float], digits: int) -> float:
    """Return the rounded arithmetic mean, or 0.0 on empty input."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), digits)


@router.get(
    "/track-record/live",
    response_model=TrackRecordLive,
    summary="Live aggregated track record (CLV/ROI/Brier/Safe rate + ROI curve)",
)
@_rate_limit("30/minute")
def get_track_record_live(request: Request) -> dict[str, Any]:
    """Return live aggregated performance metrics for the public site.

    Cached 5 minutes per process to smooth Supabase load; timezone UTC.
    The Supabase client is synchronous, so the route stays sync on purpose.
    """
    now_mono = time.monotonic()
    cached = _CACHE.get("live")
    if cached and now_mono - cached[0] < _CACHE_TTL_SEC:
        return cached[1]

    now_utc = datetime.now(timezone.utc)
    d30 = (now_utc - timedelta(days=30)).isoformat()
    d90 = (now_utc - timedelta(days=90)).isoformat()

    clv_rows = (
        supabase.table("model_health_log")
        .select("clv_pct")
        .gte("created_at", d30)
        .execute()
        .data
        or []
    )
    clv_30d = _avg([float(r["clv_pct"]) for r in clv_rows if r.get("clv_pct") is not None], 2)

    roi_rows = (
        supabase.table("best_bets")
        .select("roi_pct, n_bets")
        .gte("created_at", d90)
        .execute()
        .data
        or []
    )
    roi_90d = _avg([float(r["roi_pct"]) for r in roi_rows if r.get("roi_pct") is not None], 2)

    brier_rows = (
        supabase.table("predictions_results")
        .select("brier")
        .gte("created_at", d30)
        .execute()
        .data
        or []
    )
    brier_30d = _avg([float(r["brier"]) for r in brier_rows if r.get("brier") is not None], 3)

    safe_rows = (
        supabase.table("best_bets")
        .select("safe_rate")
        .gte("created_at", d90)
        .execute()
        .data
        or []
    )
    safe_rate_90d = _avg(
        [float(r["safe_rate"]) for r in safe_rows if r.get("safe_rate") is not None], 3
    )

    curve_rows = (
        supabase.table("best_bets")
        .select("d, cum_roi")
        .gte("d", d90)
        .order("d")
        .execute()
        .data
        or []
    )
    roi_curve_90d: list[dict[str, Any]] = [
        {"date": cast(str, r["d"]), "cumulative_roi": float(r["cum_roi"])}
        for r in curve_rows
        if r.get("d") is not None and r.get("cum_roi") is not None
    ]

    payload: dict[str, Any] = {
        "clv_30d": clv_30d,
        "roi_90d": roi_90d,
        "brier_30d": brier_30d,
        "safe_rate_90d": safe_rate_90d,
        "roi_curve_90d": roi_curve_90d,
    }
    _CACHE["live"] = (now_mono, payload)
    return payload
