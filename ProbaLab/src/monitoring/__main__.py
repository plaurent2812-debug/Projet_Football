"""
Monitoring CLI — Run all prediction quality diagnostics.

Usage:
    python -m src.monitoring             # Run all checks
    python -m src.monitoring --clv       # CLV only
    python -m src.monitoring --brier     # Brier only
    python -m src.monitoring --features  # Feature audit only
    python -m src.monitoring --quality   # Data quality only
    python -m src.monitoring --alerts    # Run alerting checks (+ send Telegram)
"""

from __future__ import annotations

import json
import sys
from typing import Any

from src.config import logger


def run_all(flags: set[str] | None = None) -> dict[str, Any]:
    """Run all monitoring checks and produce a consolidated report."""
    run_clv = flags is None or "clv" in flags
    run_brier = flags is None or "brier" in flags
    run_features = flags is None or "features" in flags
    run_quality = flags is None or "quality" in flags

    report: dict[str, Any] = {}

    logger.info("\n" + "=" * 60)
    logger.info("  PREDICTION QUALITY DIAGNOSTICS")
    logger.info("=" * 60 + "\n")

    # 1. CLV Backtest
    if run_clv:
        from src.monitoring.backtest_clv import run as clv_run

        report["clv"] = clv_run()

    # 2. Brier Score Monitor
    if run_brier:
        from src.monitoring.brier_monitor import run as brier_run

        report["brier"] = brier_run()

    # 3. Feature Importance Audit
    if run_features:
        from src.monitoring.feature_audit import run as feature_run

        report["features"] = feature_run()

    # 4. Data Quality
    if run_quality:
        from src.monitoring.data_quality import run as quality_run

        report["data_quality"] = quality_run()

    # ── Consolidated verdict ──────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  CONSOLIDATED REPORT")
    logger.info("=" * 60)

    scores = []

    # CLV score (0-10)
    clv = report.get("clv", {})
    if clv.get("clv_best_mean") is not None:
        clv_val = clv["clv_best_mean"]
        if clv_val > 0.05:
            clv_score = 10
        elif clv_val > 0.02:
            clv_score = 8
        elif clv_val > 0:
            clv_score = 7
        elif clv_val > -0.02:
            clv_score = 5
        else:
            clv_score = 3
        scores.append(("CLV", clv_score, clv.get("verdict", "?")))
        logger.info(
            f"  CLV          : {clv_score}/10 — {clv.get('verdict', '?')} (mean={clv_val:+.4f})"
        )

    # Brier score (0-10)
    brier = report.get("brier", {})
    health = brier.get("health_score")
    if health is not None:
        scores.append(("Brier", health, brier.get("brier_1x2", {}).get("grade", "?")))
        logger.info(
            f"  Calibration  : {health}/10 — Brier={brier.get('brier_1x2', {}).get('brier', '?')}"
        )

    # Feature health (0-10)
    features = report.get("features", {})
    if features.get("status"):
        feat_score = (
            10 if features["status"] == "HEALTHY" else (6 if features["status"] == "WARNING" else 3)
        )
        scores.append(("Features", feat_score, features["status"]))
        logger.info(f"  ML Features  : {feat_score}/10 — {features['status']}")

    # Data quality (0-10)
    dq = report.get("data_quality", {})
    if dq.get("status"):
        dq_score = {
            "HEALTHY": 10,
            "OK": 10,
            "WARNING": 6,
            "CRITICAL": 3,
            "ERROR": 2,
            "NO_DATA": 5,
        }.get(dq["status"], 5)
        scores.append(("DataQuality", dq_score, dq["status"]))
        logger.info(f"  Data Quality : {dq_score}/10 — {dq['status']}")

    if scores:
        overall = round(sum(s for _, s, _ in scores) / len(scores), 1)
        logger.info(f"\n  OVERALL SCORE: {overall}/10")
        report["overall_score"] = overall
    else:
        logger.warning("  No data available for scoring.")
        report["overall_score"] = None

    # Drift alert
    drift = brier.get("drift", {})
    if drift.get("drift_detected"):
        logger.warning("\n  *** ALERT: Calibration drift detected! Consider recalibrating. ***")

    logger.info("\n" + "=" * 60)
    return report


if __name__ == "__main__":
    flags = None
    args = set(sys.argv[1:])
    if args:
        flags = set()
        if "--clv" in args:
            flags.add("clv")
        if "--brier" in args:
            flags.add("brier")
        if "--features" in args:
            flags.add("features")
        if "--quality" in args:
            flags.add("quality")
        if not flags:
            flags = None

    # Run alerting checks
    if "--alerts" in args:
        from src.config import supabase
        from src.monitoring.alerting import check_and_alert
        from src.notifications import send_telegram

        alerts = check_and_alert(supabase, send_telegram_fn=send_telegram)
        if alerts:
            logger.warning("Alerts: %s", alerts)
        else:
            logger.info("No alerts triggered.")
        sys.exit(0)

    report = run_all(flags)

    # Optionally dump full JSON report
    if "--json" in args:
        # Remove non-serializable entries
        print(json.dumps(report, default=str, indent=2))
