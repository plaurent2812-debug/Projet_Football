"""api/routers/v2/public_track_record.py — Live public track-record endpoint.

Exposes aggregated quality metrics (CLV 30d, ROI 90d, Brier 30d,
Safe-rate 90d, cumulative ROI curve) for the public marketing surface.
Cached 5 minutes in-process to protect Supabase from bursts.

Column reference (verified against real schema):
  model_health_log : clv_best_mean_30d, brier_30d, recorded_at
  best_bets        : result (WIN/LOSS/VOID/PENDING), odds, market, created_at
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

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
    roi_curve_90d: list[RoiPoint] = Field(
        ..., description="Cumulative ROI daily points over 90 days"
    )


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

    Each data section is wrapped in try/except so that a missing table or
    schema drift degrades gracefully (returns 0) rather than causing a 500.
    """
    now_mono = time.monotonic()
    cached = _CACHE.get("live")
    if cached and now_mono - cached[0] < _CACHE_TTL_SEC:
        return cached[1]

    now_utc = datetime.now(timezone.utc)
    d30 = (now_utc - timedelta(days=30)).isoformat()
    d90 = (now_utc - timedelta(days=90)).isoformat()

    # ── 1. CLV 30d — from model_health_log.clv_best_mean_30d ─────────────
    clv_30d: float = 0.0
    try:
        clv_rows = (
            supabase.table("model_health_log")
            .select("clv_best_mean_30d")
            .gte("recorded_at", d30)
            .execute()
            .data
            or []
        )
        clv_30d = _avg(
            [
                float(r["clv_best_mean_30d"])
                for r in clv_rows
                if r.get("clv_best_mean_30d") is not None
            ],
            2,
        )
    except Exception:
        logger.warning(
            "track-record/live: failed to fetch CLV from model_health_log", exc_info=True
        )

    # ── 2. Brier 30d — from model_health_log.brier_30d (pre-computed) ────
    brier_30d: float = 0.0
    try:
        brier_rows = (
            supabase.table("model_health_log")
            .select("brier_30d")
            .gte("recorded_at", d30)
            .execute()
            .data
            or []
        )
        brier_30d = _avg(
            [float(r["brier_30d"]) for r in brier_rows if r.get("brier_30d") is not None],
            3,
        )
    except Exception:
        logger.warning(
            "track-record/live: failed to fetch Brier from model_health_log", exc_info=True
        )

    # ── 3. ROI 90d + safe_rate 90d + ROI curve — from best_bets ──────────
    # best_bets columns: result (WIN/LOSS/VOID/PENDING), odds, market, created_at
    # ROI = (sum(odds-1) for WINs  -  count(LOSSes)) / total_resolved * 100
    # safe_rate = wins_safe / total_safe_resolved
    # curve = cumulative ROI per calendar day
    roi_90d: float = 0.0
    safe_rate_90d: float = 0.0
    roi_curve_90d: list[dict[str, Any]] = []

    try:
        bet_rows = (
            supabase.table("best_bets")
            .select("result, odds, market, created_at")
            .gte("created_at", d90)
            .in_("result", ["WIN", "LOSS"])
            .execute()
            .data
            or []
        )

        # Global ROI 90d
        total_staked = len(bet_rows)
        total_returned = sum(float(r.get("odds") or 1.0) for r in bet_rows if r["result"] == "WIN")
        if total_staked > 0:
            roi_90d = round((total_returned - total_staked) / total_staked * 100, 2)

        # Safe-rate 90d: WIN rate for SAFE market bets specifically
        safe_bets = [
            r for r in bet_rows if (r.get("market") or "").lower() in ("safe_football", "safe_nhl")
        ]
        safe_resolved = len(safe_bets)
        safe_wins = sum(1 for r in safe_bets if r["result"] == "WIN")
        if safe_resolved > 0:
            safe_rate_90d = round(safe_wins / safe_resolved, 3)

        # ROI curve: cumulative ROI per calendar day
        # Each day: staked = count of resolved bets that day, returned = sum(odds) for wins
        daily_staked: dict[str, int] = {}
        daily_returned: dict[str, float] = {}
        for r in bet_rows:
            raw_date = r.get("created_at") or ""
            day = raw_date[:10] if raw_date else ""
            if not day:
                continue
            daily_staked[day] = daily_staked.get(day, 0) + 1
            if r["result"] == "WIN":
                daily_returned[day] = daily_returned.get(day, 0.0) + float(r.get("odds") or 1.0)

        running_staked = 0
        running_returned = 0.0
        for day in sorted(daily_staked.keys()):
            running_staked += daily_staked[day]
            running_returned += daily_returned.get(day, 0.0)
            cum_roi = (
                round((running_returned - running_staked) / running_staked * 100, 2)
                if running_staked > 0
                else 0.0
            )
            roi_curve_90d.append({"date": day, "cumulative_roi": cum_roi})

    except Exception:
        logger.warning(
            "track-record/live: failed to compute ROI/curve from best_bets", exc_info=True
        )

    payload: dict[str, Any] = {
        "clv_30d": clv_30d,
        "roi_90d": roi_90d,
        "brier_30d": brier_30d,
        "safe_rate_90d": safe_rate_90d,
        "roi_curve_90d": roi_curve_90d,
    }
    _CACHE["live"] = (now_mono, payload)
    return payload
