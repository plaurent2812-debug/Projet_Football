from __future__ import annotations

from typing import Any

SPORT_MIN_NEW_RESULTS = {
    "football": 100,
    "nhl": 50,
}

MIN_DRIFT_RESULTS = {
    "football": 30,
    "nhl": 20,
}

MIN_DATA_COMPLETENESS = 0.80
MIN_HOURS_BETWEEN_AUTO_TRAINING = 48
BRIER_DRIFT_THRESHOLD = 0.02
CLV_DRIFT_THRESHOLD = -0.01
ECE_DEGRADED_THRESHOLD = 0.08


def _float(context: dict[str, Any], key: str, default: float | None = None) -> float | None:
    value = context.get(key, default)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(context: dict[str, Any], key: str, default: int = 0) -> int:
    value = context.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def should_retrain(context: dict[str, Any]) -> dict[str, Any]:
    """Decide whether to start a candidate training run.

    This policy intentionally creates candidates only. Promotion remains a
    separate decision based on holdout metrics, so manual runs cannot silently
    replace the active production model.
    """
    sport = str(context.get("sport", "football")).lower()
    market = str(context.get("market", "1x2")).lower()
    trigger_reason = str(context.get("trigger_reason", "scheduled")).lower()
    new_results_count = _int(context, "new_results_count")
    data_completeness = _float(context, "data_completeness_pct", 1.0)
    hours_since_last_training = _float(context, "hours_since_last_training")

    reasons: list[str] = []
    blocked_by: list[str] = []
    can_auto_promote = trigger_reason != "manual"

    if trigger_reason == "manual":
        return {
            "should_retrain": True,
            "trigger_reason": "manual",
            "sport": sport,
            "market": market,
            "reasons": ["manual_candidate"],
            "blocked_by": [],
            "can_auto_promote": False,
        }

    if data_completeness is not None and data_completeness < MIN_DATA_COMPLETENESS:
        blocked_by.append("low_data_completeness")

    if (
        hours_since_last_training is not None
        and hours_since_last_training < MIN_HOURS_BETWEEN_AUTO_TRAINING
    ):
        blocked_by.append("cooldown_active")

    min_new_results = SPORT_MIN_NEW_RESULTS.get(sport, SPORT_MIN_NEW_RESULTS["football"])
    if trigger_reason == "scheduled":
        if new_results_count >= min_new_results:
            reasons.append("enough_new_results")
        else:
            blocked_by.append("insufficient_new_results")

    brier_7d = _float(context, "brier_7d")
    brier_30d = _float(context, "brier_30d")
    min_drift_results = MIN_DRIFT_RESULTS.get(sport, MIN_DRIFT_RESULTS["football"])
    if brier_7d is not None and brier_30d is not None:
        if brier_7d > brier_30d + BRIER_DRIFT_THRESHOLD and new_results_count >= min_drift_results:
            reasons.append("brier_drift")

    clv_7d = _float(context, "clv_7d")
    if (
        clv_7d is not None
        and clv_7d < CLV_DRIFT_THRESHOLD
        and new_results_count >= min_drift_results
    ):
        reasons.append("negative_clv")

    ece_30d = _float(context, "ece_30d")
    if (
        ece_30d is not None
        and ece_30d > ECE_DEGRADED_THRESHOLD
        and new_results_count >= min_drift_results
    ):
        reasons.append("ece_degraded")

    should_run = bool(reasons) and not blocked_by

    return {
        "should_retrain": should_run,
        "trigger_reason": trigger_reason,
        "sport": sport,
        "market": market,
        "reasons": reasons,
        "blocked_by": blocked_by,
        "can_auto_promote": can_auto_promote and should_run,
    }
