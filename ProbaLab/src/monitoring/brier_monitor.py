"""
brier_monitor.py — Brier Score & Calibration Drift Monitoring.

Computes calibration quality metrics on a rolling window and alerts
when the model's probability estimates degrade.

Metrics:
    - Brier Score: mean squared error of probability estimates (lower = better)
    - Log Loss: cross-entropy loss (more sensitive to confident wrong predictions)
    - ECE (Expected Calibration Error): mean absolute gap between predicted
      and observed frequencies in probability bins
    - Reliability diagram data: for visualization

Thresholds (1X2 market):
    - Brier < 0.19 → EXCELLENT
    - Brier < 0.21 → GOOD
    - Brier < 0.23 → ACCEPTABLE
    - Brier >= 0.23 → DEGRADED

Usage:
    python -m src.monitoring.brier_monitor
"""

from __future__ import annotations

import math
from typing import Any

from src.config import logger, supabase

# ── Thresholds ────────────────────────────────────────────────────
BRIER_THRESHOLDS = {
    "1x2": {"excellent": 0.19, "good": 0.21, "acceptable": 0.23},
    "binary": {"excellent": 0.20, "good": 0.22, "acceptable": 0.25},
}


def _load_results() -> list[dict]:
    """Load all evaluated prediction results."""
    return supabase.table("prediction_results").select("*").execute().data or []


def compute_brier_1x2(results: list[dict]) -> dict[str, Any]:
    """Compute Brier score for 1X2 predictions.

    Brier score for multi-class: mean over all classes of (predicted - actual)^2
    For 1X2: BS = (1/N) * sum((p_h - y_h)^2 + (p_d - y_d)^2 + (p_a - y_a)^2)
    """
    scores = []
    for r in results:
        pred_h = r.get("pred_home")
        pred_d = r.get("pred_draw")
        pred_a = r.get("pred_away")
        actual = r.get("actual_result")

        if pred_h is None or pred_d is None or pred_a is None or actual is None:
            continue

        p_h, p_d, p_a = pred_h / 100.0, pred_d / 100.0, pred_a / 100.0
        y_h = 1.0 if actual == "H" else 0.0
        y_d = 1.0 if actual == "D" else 0.0
        y_a = 1.0 if actual == "A" else 0.0

        bs = (p_h - y_h) ** 2 + (p_d - y_d) ** 2 + (p_a - y_a) ** 2
        scores.append(bs)

    if not scores:
        return {"brier": None, "n": 0, "status": "NO_DATA"}

    brier = sum(scores) / len(scores)
    thresholds = BRIER_THRESHOLDS["1x2"]

    if brier < thresholds["excellent"]:
        grade = "EXCELLENT"
    elif brier < thresholds["good"]:
        grade = "GOOD"
    elif brier < thresholds["acceptable"]:
        grade = "ACCEPTABLE"
    else:
        grade = "DEGRADED"

    return {
        "brier": round(brier, 4),
        "n": len(scores),
        "grade": grade,
    }


def compute_log_loss_1x2(results: list[dict]) -> dict[str, Any]:
    """Compute log loss for 1X2 predictions."""
    losses = []
    eps = 1e-15  # Prevent log(0)

    for r in results:
        pred_h = r.get("pred_home")
        pred_d = r.get("pred_draw")
        pred_a = r.get("pred_away")
        actual = r.get("actual_result")

        if pred_h is None or actual is None:
            continue

        p_h = max(eps, min(1 - eps, pred_h / 100.0))
        p_d = max(eps, min(1 - eps, pred_d / 100.0))
        p_a = max(eps, min(1 - eps, pred_a / 100.0))

        if actual == "H":
            ll = -math.log(p_h)
        elif actual == "D":
            ll = -math.log(p_d)
        else:
            ll = -math.log(p_a)

        losses.append(ll)

    if not losses:
        return {"log_loss": None, "n": 0}

    return {
        "log_loss": round(sum(losses) / len(losses), 4),
        "n": len(losses),
    }


def compute_ece(results: list[dict], n_bins: int = 10) -> dict[str, Any]:
    """Compute Expected Calibration Error (ECE) and reliability diagram data.

    Groups predictions into bins by confidence, then measures the gap
    between predicted probability and actual frequency in each bin.

    ECE = sum(|bin_size / total| * |avg_predicted - avg_actual|) for all bins
    """
    # Collect (predicted_prob, was_correct) for the predicted winner
    records: list[tuple[float, int]] = []

    for r in results:
        pred_h = r.get("pred_home", 0)
        pred_d = r.get("pred_draw", 0)
        pred_a = r.get("pred_away", 0)
        actual = r.get("actual_result")

        if actual is None:
            continue

        # Take the probability of the predicted winner
        preds = {"H": pred_h, "D": pred_d, "A": pred_a}
        predicted_winner = max(preds, key=preds.get)
        confidence = preds[predicted_winner] / 100.0
        correct = 1 if predicted_winner == actual else 0
        records.append((confidence, correct))

    if not records:
        return {"ece": None, "bins": [], "n": 0}

    # Build bins
    bins: list[dict] = []
    total = len(records)
    ece = 0.0

    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins

        bin_records = [(p, c) for p, c in records if lo <= p < hi or (i == n_bins - 1 and p == hi)]

        if not bin_records:
            bins.append(
                {
                    "range": f"{lo:.1f}-{hi:.1f}",
                    "n": 0,
                    "avg_predicted": round((lo + hi) / 2, 2),
                    "avg_actual": None,
                    "gap": None,
                }
            )
            continue

        avg_pred = sum(p for p, _ in bin_records) / len(bin_records)
        avg_actual = sum(c for _, c in bin_records) / len(bin_records)
        gap = abs(avg_pred - avg_actual)
        ece += (len(bin_records) / total) * gap

        bins.append(
            {
                "range": f"{lo:.1f}-{hi:.1f}",
                "n": len(bin_records),
                "avg_predicted": round(avg_pred, 3),
                "avg_actual": round(avg_actual, 3),
                "gap": round(gap, 3),
            }
        )

    return {
        "ece": round(ece, 4),
        "bins": bins,
        "n": total,
        "grade": "EXCELLENT"
        if ece < 0.03
        else ("GOOD" if ece < 0.05 else ("ACCEPTABLE" if ece < 0.08 else "DEGRADED")),
    }


def compute_binary_brier(results: list[dict], pred_field: str, actual_fn) -> dict[str, Any]:
    """Compute Brier score for a binary market (BTTS, Over 2.5, etc.)."""
    scores = []
    for r in results:
        p = r.get(pred_field)
        a = actual_fn(r)
        if p is None or a is None:
            continue
        prob = p / 100.0
        actual = 1.0 if a else 0.0
        scores.append((prob - actual) ** 2)

    if not scores:
        return {"brier": None, "n": 0}

    brier = sum(scores) / len(scores)
    thresholds = BRIER_THRESHOLDS["binary"]

    return {
        "brier": round(brier, 4),
        "n": len(scores),
        "grade": (
            "EXCELLENT"
            if brier < thresholds["excellent"]
            else "GOOD"
            if brier < thresholds["good"]
            else "ACCEPTABLE"
            if brier < thresholds["acceptable"]
            else "DEGRADED"
        ),
    }


def compute_rolling_brier(results: list[dict], window: int = 30) -> list[dict]:
    """Compute Brier score on a rolling window to detect drift."""
    # Sort by date
    dated = [r for r in results if r.get("pred_home") is not None and r.get("actual_result")]
    dated.sort(key=lambda r: r.get("created_at", r.get("date", "")))

    rolling = []
    for i in range(window, len(dated) + 1):
        batch = dated[i - window : i]
        bs = compute_brier_1x2(batch)
        if bs.get("brier") is not None:
            rolling.append(
                {
                    "window_end": i,
                    "brier": bs["brier"],
                    "n": bs["n"],
                }
            )

    return rolling


def detect_drift(rolling: list[dict], threshold: float = 0.03) -> dict[str, Any]:
    """Detect calibration drift from rolling Brier scores.

    Compares the last window's Brier to the overall average.
    A positive delta > threshold indicates degradation.
    """
    if len(rolling) < 3:
        return {"drift_detected": False, "reason": "insufficient_data"}

    all_briers = [r["brier"] for r in rolling]
    overall_mean = sum(all_briers) / len(all_briers)
    last_brier = rolling[-1]["brier"]
    delta = last_brier - overall_mean

    return {
        "drift_detected": delta > threshold,
        "overall_mean_brier": round(overall_mean, 4),
        "last_window_brier": round(last_brier, 4),
        "delta": round(delta, 4),
        "threshold": threshold,
    }


def run() -> dict[str, Any]:
    """Run the full Brier score monitoring suite."""
    logger.info("=" * 60)
    logger.info("  BRIER SCORE MONITOR — Calibration Quality")
    logger.info("=" * 60)

    results = _load_results()
    if not results:
        logger.warning("  No evaluated predictions found.")
        return {"status": "NO_DATA"}

    logger.info(f"  {len(results)} matchs évalués")

    # 1X2
    brier_1x2 = compute_brier_1x2(results)
    ll_1x2 = compute_log_loss_1x2(results)
    ece_data = compute_ece(results)

    logger.info(f"\n  1X2 Metrics (n={brier_1x2.get('n', 0)}):")
    logger.info(
        f"    Brier Score : {brier_1x2.get('brier', 'N/A')} [{brier_1x2.get('grade', '?')}]"
    )
    logger.info(f"    Log Loss    : {ll_1x2.get('log_loss', 'N/A')}")
    logger.info(f"    ECE         : {ece_data.get('ece', 'N/A')} [{ece_data.get('grade', '?')}]")

    # Reliability diagram
    if ece_data.get("bins"):
        logger.info("    Reliability Diagram:")
        for b in ece_data["bins"]:
            if b["n"] > 0:
                bar_pred = "#" * int((b["avg_predicted"] or 0) * 20)
                bar_act = "*" * int((b["avg_actual"] or 0) * 20)
                logger.info(
                    f"      {b['range']} (n={b['n']:3d}) pred={bar_pred:20s} act={bar_act:20s} gap={b['gap']:.3f}"
                )

    # Binary markets
    binary_markets = {
        "BTTS": ("pred_btts", lambda r: r.get("actual_btts")),
        "Over 2.5": ("pred_over_25", lambda r: r.get("actual_over_25")),
        "Over 1.5": ("pred_over_15", lambda r: r.get("actual_over_15")),
    }

    binary_results = {}
    for market_name, (pred_field, actual_fn) in binary_markets.items():
        br = compute_binary_brier(results, pred_field, actual_fn)
        binary_results[market_name] = br
        if br.get("brier") is not None:
            logger.info(f"\n  {market_name} (n={br['n']}):")
            logger.info(f"    Brier Score : {br['brier']} [{br['grade']}]")

    # Rolling drift detection
    rolling = compute_rolling_brier(results)
    drift = detect_drift(rolling)

    if drift.get("drift_detected"):
        logger.warning("\n  DRIFT DETECTED:")
        logger.warning(f"    Overall Brier : {drift['overall_mean_brier']}")
        logger.warning(f"    Last window   : {drift['last_window_brier']}")
        logger.warning(
            f"    Delta         : {drift['delta']:+.4f} (threshold: {drift['threshold']})"
        )
    else:
        logger.info(f"\n  No drift detected (delta={drift.get('delta', 'N/A')})")

    # Overall health score (1-10)
    health = 10
    b = brier_1x2.get("brier")
    if b is not None:
        if b >= 0.23:
            health -= 4
        elif b >= 0.21:
            health -= 2
        elif b >= 0.19:
            health -= 1

    e = ece_data.get("ece")
    if e is not None:
        if e >= 0.08:
            health -= 3
        elif e >= 0.05:
            health -= 1

    if drift.get("drift_detected"):
        health -= 2

    health = max(1, min(10, health))
    logger.info(f"\n  Health Score: {health}/10")

    return {
        "status": "OK",
        "n_matches": len(results),
        "brier_1x2": brier_1x2,
        "log_loss_1x2": ll_1x2,
        "ece": ece_data,
        "binary_markets": binary_results,
        "drift": drift,
        "health_score": health,
    }


if __name__ == "__main__":
    run()
