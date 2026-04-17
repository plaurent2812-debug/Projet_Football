"""
data_quality.py — Monitor data completeness and quality across the pipeline.

Checks:
  1. Recent fixtures have predictions (coverage)
  2. Predictions have matching odds in fixture_odds (CLV readiness)
  3. Finished matches have match_events (results evaluation readiness)
  4. No null probabilities in recent predictions

Usage:
    python -m src.monitoring.data_quality
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import supabase

logger = logging.getLogger("football_ia")


def _check_prediction_coverage(yesterday: str) -> dict[str, Any]:
    """Check that recent fixtures have predictions."""
    try:
        # Fixtures from yesterday or earlier that are NS or FT
        fixtures = (
            supabase.table("fixtures")
            .select("id, status", count="exact")
            .lte("date", yesterday)
            .gte("date", (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"))
            .execute()
        )
        n_fixtures = fixtures.count or 0
        fixture_ids = [f["id"] for f in (fixtures.data or [])]

        if not fixture_ids:
            return {"status": "NO_DATA", "n_fixtures": 0, "n_with_predictions": 0}

        # Check how many have predictions
        CHUNK = 100
        n_with_preds = 0
        for i in range(0, len(fixture_ids), CHUNK):
            chunk = fixture_ids[i : i + CHUNK]
            preds = (
                supabase.table("predictions")
                .select("fixture_id", count="exact")
                .in_("fixture_id", chunk)
                .execute()
            )
            n_with_preds += preds.count or 0

        coverage = round(n_with_preds / n_fixtures * 100, 1) if n_fixtures > 0 else 0
        return {
            "status": "OK" if coverage >= 80 else ("WARNING" if coverage >= 50 else "CRITICAL"),
            "n_fixtures": n_fixtures,
            "n_with_predictions": n_with_preds,
            "coverage_pct": coverage,
        }
    except Exception as e:
        logger.error("Prediction coverage check failed: %s", e)
        return {"status": "ERROR", "error": str(e)}


def _check_odds_coverage() -> dict[str, Any]:
    """Check that predictions have matching odds for CLV computation."""
    try:
        # Get recent predictions (last 7 days)
        preds = (
            supabase.table("predictions")
            .select("fixture_id")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
            .data
            or []
        )
        if not preds:
            return {"status": "NO_DATA", "n_predictions": 0, "n_with_odds": 0}

        fixture_ids = list({p["fixture_id"] for p in preds})

        # Get api_fixture_ids for these fixtures
        CHUNK = 100
        api_ids: list[int] = []
        for i in range(0, len(fixture_ids), CHUNK):
            chunk = fixture_ids[i : i + CHUNK]
            rows = (
                supabase.table("fixtures")
                .select("api_fixture_id")
                .in_("id", chunk)
                .not_.is_("api_fixture_id", "null")
                .execute()
                .data
                or []
            )
            api_ids.extend(r["api_fixture_id"] for r in rows if r.get("api_fixture_id"))

        if not api_ids:
            return {
                "status": "CRITICAL",
                "n_predictions": len(preds),
                "n_with_odds": 0,
                "coverage_pct": 0,
            }

        # Check how many have odds
        n_with_odds = 0
        for i in range(0, len(api_ids), CHUNK):
            chunk = api_ids[i : i + CHUNK]
            odds = (
                supabase.table("fixture_odds")
                .select("fixture_api_id", count="exact")
                .in_("fixture_api_id", chunk)
                .execute()
            )
            n_with_odds += odds.count or 0

        coverage = round(n_with_odds / len(preds) * 100, 1) if preds else 0
        return {
            "status": "OK" if coverage >= 70 else ("WARNING" if coverage >= 40 else "CRITICAL"),
            "n_predictions": len(preds),
            "n_with_odds": n_with_odds,
            "coverage_pct": coverage,
        }
    except Exception as e:
        logger.error("Odds coverage check failed: %s", e)
        return {"status": "ERROR", "error": str(e)}


def _check_events_completeness() -> dict[str, Any]:
    """Check that finished matches have match events recorded."""
    try:
        # Finished matches from last 7 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        finished = (
            supabase.table("fixtures")
            .select("api_fixture_id", count="exact")
            .eq("status", "FT")
            .gte("date", cutoff)
            .execute()
        )
        n_finished = finished.count or 0
        api_ids = [f["api_fixture_id"] for f in (finished.data or []) if f.get("api_fixture_id")]

        if not api_ids:
            return {"status": "NO_DATA", "n_finished": n_finished, "n_with_events": 0}

        # Check events
        CHUNK = 100
        n_with_events = 0
        for i in range(0, len(api_ids), CHUNK):
            chunk = api_ids[i : i + CHUNK]
            events = (
                supabase.table("match_events")
                .select("fixture_api_id", count="exact")
                .in_("fixture_api_id", chunk)
                .execute()
            )
            n_with_events += events.count or 0

        # Events count is per-event not per-fixture, so approximate
        return {
            "status": "OK" if n_with_events > 0 else "WARNING",
            "n_finished": n_finished,
            "n_with_events": n_with_events,
            "note": "n_with_events counts individual events, not unique fixtures",
        }
    except Exception as e:
        logger.error("Events completeness check failed: %s", e)
        return {"status": "ERROR", "error": str(e)}


def _check_null_probabilities() -> dict[str, Any]:
    """Check for predictions with null probability fields."""
    try:
        # Recent predictions with null probas
        nulls = (
            supabase.table("predictions")
            .select("id", count="exact")
            .is_("proba_home", "null")
            .execute()
        )
        n_null_home = nulls.count or 0

        nulls_draw = (
            supabase.table("predictions")
            .select("id", count="exact")
            .is_("proba_draw", "null")
            .execute()
        )
        n_null_draw = nulls_draw.count or 0

        total = supabase.table("predictions").select("id", count="exact").execute()
        n_total = total.count or 0

        n_null = max(n_null_home, n_null_draw)
        pct_null = round(n_null / n_total * 100, 1) if n_total > 0 else 0

        return {
            "status": "OK" if pct_null == 0 else ("WARNING" if pct_null < 5 else "CRITICAL"),
            "n_total_predictions": n_total,
            "n_null_proba_home": n_null_home,
            "n_null_proba_draw": n_null_draw,
            "pct_null": pct_null,
        }
    except Exception as e:
        logger.error("Null probabilities check failed: %s", e)
        return {"status": "ERROR", "error": str(e)}


def check_data_quality() -> dict[str, Any]:
    """Run all data quality checks and return a health report.

    Returns:
        Dictionary with overall status, individual check results,
        and a timestamp.
    """
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    checks: list[dict[str, Any]] = []

    # 1. Prediction coverage
    pred_cov = _check_prediction_coverage(yesterday)
    checks.append({"name": "prediction_coverage", **pred_cov})

    # 2. Odds coverage (CLV readiness)
    odds_cov = _check_odds_coverage()
    checks.append({"name": "odds_coverage", **odds_cov})

    # 3. Events completeness
    events = _check_events_completeness()
    checks.append({"name": "events_completeness", **events})

    # 4. Null probabilities
    nulls = _check_null_probabilities()
    checks.append({"name": "null_probabilities", **nulls})

    # Overall status
    statuses = [c["status"] for c in checks]
    if "CRITICAL" in statuses:
        overall = "CRITICAL"
    elif "ERROR" in statuses:
        overall = "ERROR"
    elif "WARNING" in statuses:
        overall = "WARNING"
    elif all(s == "NO_DATA" for s in statuses):
        overall = "NO_DATA"
    else:
        overall = "HEALTHY"

    report = {
        "status": overall,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return report


def run() -> dict[str, Any]:
    """Run data quality checks and log results."""
    logger.info("=" * 60)
    logger.info("  DATA QUALITY MONITOR")
    logger.info("=" * 60)

    report = check_data_quality()

    for check in report["checks"]:
        name = check["name"]
        status = check["status"]
        icon = {
            "OK": "OK",
            "WARNING": "WARN",
            "CRITICAL": "CRIT",
            "ERROR": "ERR",
            "NO_DATA": "N/A",
        }.get(status, "?")
        logger.info(f"  [{icon:4s}] {name}")
        for k, v in check.items():
            if k not in ("name", "status"):
                logger.info(f"         {k}: {v}")

    logger.info(f"\n  Overall: {report['status']}")
    logger.info("=" * 60)

    return report


if __name__ == "__main__":
    run()
