"""feature_drift — Kolmogorov-Smirnov test training vs last N days prod.

Purpose:
    Detect silent fetcher/source biases that shift feature distributions
    between training time and serving time. If a feature drifts, predictions
    become unreliable even if the model itself is unchanged.

Usage:
    from src.monitoring.feature_drift import run_feature_drift_check
    result = run_feature_drift_check(alpha=0.01, window_days=30)

Design:
    - ks_test_feature: numeric KS test on two samples, ignoring NaNs
    - run_feature_drift_check: loads training + last N days prod, returns per-feature stats
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from scipy import stats

from src.config import supabase
from src.constants import FEATURE_COLS

logger = logging.getLogger("football_ia.feature_drift")


def ks_test_feature(
    train_values: np.ndarray,
    prod_values: np.ndarray,
    alpha: float = 0.01,
) -> dict[str, Any]:
    """KS test between two numeric distributions.

    Returns dict with: statistic, p_value, drift_detected, n_train, n_prod.
    """
    t = np.asarray(train_values, dtype=float)
    p = np.asarray(prod_values, dtype=float)
    t = t[~np.isnan(t)]
    p = p[~np.isnan(p)]

    if len(t) < 2 or len(p) < 2:
        return {
            "statistic": None,
            "p_value": None,
            "drift_detected": False,
            "n_train": len(t),
            "n_prod": len(p),
        }

    stat, p_value = stats.ks_2samp(t, p)
    return {
        "statistic": float(stat),
        "p_value": float(p_value),
        "drift_detected": bool(p_value < alpha),
        "n_train": len(t),
        "n_prod": len(p),
    }


def _load_training_distribution() -> dict[str, np.ndarray]:
    """Load feature values from training_data table."""
    rows = (
        supabase.table("training_data").select(",".join(FEATURE_COLS)).limit(10000).execute().data
    ) or []
    out: dict[str, np.ndarray] = {}
    for feat in FEATURE_COLS:
        values = [r.get(feat) for r in rows if r.get(feat) is not None]
        out[feat] = np.asarray(values, dtype=float)
    return out


def _load_prod_distribution(window_days: int = 30) -> dict[str, np.ndarray]:
    """Load feature values from predictions stats_json over last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    rows = (
        supabase.table("predictions")
        .select("stats_json")
        .gte("created_at", cutoff)
        .limit(10000)
        .execute()
        .data
    ) or []
    out: dict[str, list[float]] = {f: [] for f in FEATURE_COLS}
    for r in rows:
        stats_json = r.get("stats_json") or {}
        features = stats_json.get("features") or {}
        for feat in FEATURE_COLS:
            v = features.get(feat)
            if v is not None:
                try:
                    out[feat].append(float(v))
                except (TypeError, ValueError):
                    pass
    return {k: np.asarray(v, dtype=float) for k, v in out.items()}


def run_feature_drift_check(
    *,
    alpha: float = 0.01,
    window_days: int = 30,
) -> dict[str, Any]:
    train = _load_training_distribution()
    prod = _load_prod_distribution(window_days=window_days)

    per_feature: dict[str, dict] = {}
    n_drifted = 0
    for feat in FEATURE_COLS:
        if feat not in train or feat not in prod:
            continue
        res = ks_test_feature(train[feat], prod[feat], alpha=alpha)
        per_feature[feat] = res
        if res["drift_detected"]:
            n_drifted += 1

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "alpha": alpha,
        "window_days": window_days,
        "n_features": len(per_feature),
        "n_drifted": n_drifted,
        "per_feature": per_feature,
    }


def drift_result_to_alert(result: dict, *, threshold: int = 5) -> str | None:
    """Retourne un message HTML Telegram si n_drifted >= threshold, sinon None."""
    n_drifted = result.get("n_drifted", 0)
    if n_drifted < threshold:
        return None
    drifted_names = [
        name
        for name, info in (result.get("per_feature") or {}).items()
        if info.get("drift_detected")
    ][:10]
    lines = [
        "\u26a0\ufe0f <b>CRITICAL — Feature drift</b>",
        f"n_drifted={n_drifted} / {result.get('n_features')}",
        f"alpha={result.get('alpha')}",
        "Features: " + ", ".join(drifted_names),
    ]
    return "\n".join(lines)
