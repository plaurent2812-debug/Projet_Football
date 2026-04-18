"""
alerting.py — Automated alerting for model performance degradation.

Runs post-pipeline checks and sends Telegram alerts when thresholds
are exceeded:
  1. Brier drift: recent window significantly worse than historical
  2. Data completeness: too few predictions vs scheduled fixtures
  3. Prediction volume: zero predictions today

Usage:
    from src.monitoring.alerting import check_and_alert
    check_and_alert(supabase, send_telegram_fn=send_telegram)
"""

from __future__ import annotations

import html as _html
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("football_ia")


def check_and_alert(
    supabase,
    send_telegram_fn: Callable[[str], bool] | None = None,
) -> list[str]:
    """Run all monitoring checks and send alerts if thresholds exceeded.

    Args:
        supabase: Supabase client instance.
        send_telegram_fn: Callable that accepts an HTML string and sends it
            via Telegram.  If ``None``, alerts are logged but not sent.

    Returns:
        List of alert message strings (empty if everything is healthy).
    """
    alerts: list[str] = []

    brier_alert = _check_brier_drift(supabase)
    if brier_alert:
        alerts.append(brier_alert)

    completeness_alert = _check_data_completeness(supabase)
    if completeness_alert:
        alerts.append(completeness_alert)

    volume_alert = _check_prediction_volume(supabase)
    if volume_alert:
        alerts.append(volume_alert)

    clv_alert = _check_clv_drift(supabase)
    if clv_alert:
        alerts.append(clv_alert)

    if alerts:
        msg = "\u26a0\ufe0f <b>ALERTES MONITORING</b>\n\n" + "\n\n".join(alerts)
        logger.warning("Monitoring alerts (%d): %s", len(alerts), alerts)
        if send_telegram_fn:
            send_telegram_fn(msg)
            logger.warning("Sent %d monitoring alert(s) via Telegram", len(alerts))
    else:
        logger.info("Monitoring checks passed — no alerts")

    return alerts


# ── Individual checks ────────────────────────────────────────────


def _check_brier_drift(supabase) -> str | None:
    """Alert if recent Brier score is >10% worse than historical average.

    Uses the same ``prediction_results`` table and Brier computation
    as :mod:`src.monitoring.brier_monitor` but compares a rolling
    window of the last 30 evaluated matches against the all-time mean.
    """
    try:
        from src.monitoring.brier_monitor import (
            compute_brier_1x2,
            compute_rolling_brier,
            detect_drift,
        )

        results = supabase.table("prediction_results").select("*").execute().data or []
        if len(results) < 40:
            # Not enough data for meaningful drift detection
            return None

        brier_all = compute_brier_1x2(results)
        brier_val = brier_all.get("brier")
        if brier_val is None:
            return None

        rolling = compute_rolling_brier(results, window=30)
        drift = detect_drift(rolling, threshold=0.03)

        if drift.get("drift_detected"):
            overall = drift["overall_mean_brier"]
            last = drift["last_window_brier"]
            delta = drift["delta"]
            return (
                f"\U0001f4c9 <b>Drift Brier</b>: "
                f"derniers 30 matchs {_html.escape(str(last))} "
                f"vs moyenne {_html.escape(str(overall))} "
                f"(delta {_html.escape(f'{delta:+.4f}')})"
            )
        return None
    except Exception as e:
        logger.error("Brier drift check failed: %s", e)
        return None


def _check_data_completeness(supabase) -> str | None:
    """Alert if fewer than 80% of yesterday's fixtures have predictions."""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        # Count predictions created yesterday
        preds = (
            supabase.table("predictions")
            .select("id", count="exact")
            .gte("created_at", yesterday)
            .lt("created_at", today)
            .execute()
        )
        pred_count = preds.count if preds.count is not None else len(preds.data or [])

        # Count fixtures scheduled for yesterday
        fixtures = (
            supabase.table("fixtures")
            .select("id", count="exact")
            .gte("date", yesterday)
            .lt("date", today)
            .execute()
        )
        fix_count = fixtures.count if fixtures.count is not None else len(fixtures.data or [])

        if fix_count > 0 and pred_count < fix_count * 0.8:
            pct = round(pred_count / fix_count * 100)
            return (
                f"\U0001f4c9 <b>Compl\u00e9tude donn\u00e9es</b>: "
                f"seulement {pred_count}/{fix_count} matchs hier ont "
                f"des pr\u00e9dictions ({pct}%)"
            )
        return None
    except Exception as e:
        logger.error("Data completeness check failed: %s", e)
        return None


def _check_prediction_volume(supabase) -> str | None:
    """Alert if no predictions were created today."""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = (
            supabase.table("predictions")
            .select("id", count="exact")
            .gte("created_at", today)
            .execute()
        )
        count = result.count if result.count is not None else len(result.data or [])

        if count == 0:
            return "\U0001f6a8 <b>Volume pr\u00e9dictions</b>: AUCUNE pr\u00e9diction aujourd'hui!"
        return None
    except Exception as e:
        logger.error("Prediction volume check failed: %s", e)
        return None


def _check_clv_drift(supabase_client) -> str | None:
    """Retourne un message alerte si CLV 1X2 vs Pinnacle sur 7 jours est négatif.

    Thresholds:
      - 7d mean CLV < -3% → CRITICAL
      - 7d mean CLV < -1% → WARNING
      - sinon None
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        rows = (
            supabase_client.table("model_health_log")
            .select("clv_vs_pinnacle_1x2")
            .gte("recorded_at", cutoff)
            .order("recorded_at", desc=True)
            .limit(7)
            .execute()
            .data
        ) or []
    except Exception:
        logger.exception("_check_clv_drift load failed")
        return None

    valid = [
        float(r["clv_vs_pinnacle_1x2"])
        for r in rows
        if r.get("clv_vs_pinnacle_1x2") is not None
    ]
    if len(valid) < 3:
        return None
    mean_clv = sum(valid) / len(valid)
    if mean_clv < -0.03:
        return (
            f"\U0001f534 <b>CRITICAL — CLV 7j négatif</b>\n"
            f"Mean CLV vs Pinnacle 1X2 = {mean_clv:+.2%} sur {len(valid)} jours"
        )
    if mean_clv < -0.01:
        return (
            f"\u26a0\ufe0f <b>WARNING — CLV 7j dégradé</b>\n"
            f"Mean CLV vs Pinnacle 1X2 = {mean_clv:+.2%} sur {len(valid)} jours"
        )
    return None
