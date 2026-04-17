"""
api/routers/monitoring.py — Model quality monitoring endpoints.

Provides CLV, Brier score, calibration health and data-quality checks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from api.cache import TTLCache
from api.response_models import MonitoringHealthResponse, MonitoringResponse
from src.config import supabase
from src.constants import CACHE_TTL_MONITORING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])

# ── Monitoring cache (CLV + Brier are expensive to compute) ────────
_monitoring_cache = TTLCache(ttl=CACHE_TTL_MONITORING, name="monitoring")


def _compute_monitoring() -> dict:
    """Compute CLV + Brier monitoring payload (expensive — called via cache)."""
    from src.monitoring.backtest_clv import run as run_clv
    from src.monitoring.brier_monitor import run as run_brier

    clv_result: dict = {}
    brier_result: dict = {}

    try:
        clv_result = run_clv()
    except Exception:
        logger.warning("CLV computation failed", exc_info=True)
        clv_result = {"status": "ERROR"}

    try:
        brier_result = run_brier()
    except Exception:
        logger.warning("Brier computation failed", exc_info=True)
        brier_result = {"status": "ERROR"}

    return {
        "clv": {
            "clv_best_mean": clv_result.get("clv_best_mean", 0),
            "clv_when_correct": clv_result.get("clv_when_correct", 0),
            "pct_positive_clv": clv_result.get("pct_positive_clv", 0),
            "n_matches": clv_result.get("n_matches", 0),
            "verdict": clv_result.get("verdict", "NO_DATA"),
            "by_league": clv_result.get("by_league", {}),
            "daily_clv": clv_result.get("daily_clv", []),
            "status": clv_result.get("status", "NO_DATA"),
        },
        "brier": {
            "brier_1x2": brier_result.get("brier_1x2", {}).get("brier"),
            "brier_1x2_grade": brier_result.get("brier_1x2", {}).get("grade"),
            "ece": brier_result.get("ece", {}).get("ece"),
            "ece_grade": brier_result.get("ece", {}).get("grade"),
            "log_loss": brier_result.get("log_loss_1x2", {}).get("log_loss"),
            "btts": brier_result.get("binary_markets", {}).get("BTTS", {}).get("brier"),
            "over15": brier_result.get("binary_markets", {}).get("Over 1.5", {}).get("brier"),
            "over25": brier_result.get("binary_markets", {}).get("Over 2.5", {}).get("brier"),
            "n_matches": brier_result.get("n_matches", 0),
            "drift": brier_result.get("drift", {}),
        },
        "health_score": brier_result.get("health_score", 5),
    }


@router.get(
    "",
    summary="Get model quality monitoring metrics",
    responses={
        500: {"description": "Internal server error"},
    },
)
def get_monitoring():
    """Get model quality monitoring: CLV, Brier, calibration health."""
    try:
        return _monitoring_cache.get_or_set("monitoring", _compute_monitoring)
    except Exception:
        logger.exception("get_monitoring failed")
        return {"error": "Internal error", "health_score": 0}


@router.get("/health", summary="Quick data-quality health check")
def monitoring_health():
    """Quick data-quality health check — lightweight, no heavy computation.

    Returns prediction counts, last prediction timestamp, fixture
    coverage, and a simple boolean ``healthy`` flag.
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        # Today's predictions
        preds_today_resp = (
            supabase.table("predictions")
            .select("id, created_at", count="exact")
            .gte("created_at", today)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        preds_today = (
            preds_today_resp.count
            if preds_today_resp.count is not None
            else len(preds_today_resp.data or [])
        )
        last_prediction_at = (
            preds_today_resp.data[0]["created_at"]
            if preds_today_resp.data
            else None
        )

        # Yesterday's fixture coverage
        fixtures_yesterday = (
            supabase.table("fixtures")
            .select("id", count="exact")
            .gte("date", yesterday)
            .lt("date", today)
            .execute()
        )
        fix_count = (
            fixtures_yesterday.count
            if fixtures_yesterday.count is not None
            else len(fixtures_yesterday.data or [])
        )

        preds_yesterday_resp = (
            supabase.table("predictions")
            .select("id", count="exact")
            .gte("created_at", yesterday)
            .lt("created_at", today)
            .execute()
        )
        preds_yesterday = (
            preds_yesterday_resp.count
            if preds_yesterday_resp.count is not None
            else len(preds_yesterday_resp.data or [])
        )
        coverage_pct = (
            round(preds_yesterday / fix_count * 100, 1) if fix_count > 0 else None
        )

        # Evaluated results count
        eval_count_resp = (
            supabase.table("prediction_results")
            .select("id", count="exact")
            .execute()
        )
        evaluated_total = (
            eval_count_resp.count
            if eval_count_resp.count is not None
            else len(eval_count_resp.data or [])
        )

        # Quick healthy heuristic
        healthy = preds_today > 0 or datetime.now(timezone.utc).hour < 10

        return {
            "healthy": healthy,
            "predictions_today": preds_today,
            "last_prediction_at": last_prediction_at,
            "yesterday_coverage_pct": coverage_pct,
            "yesterday_fixtures": fix_count,
            "yesterday_predictions": preds_yesterday,
            "evaluated_results_total": evaluated_total,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        logger.exception("Monitoring health check error")
        return {"healthy": False, "error": "Internal error", "checked_at": datetime.now(timezone.utc).isoformat()}
