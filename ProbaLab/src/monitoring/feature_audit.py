"""
feature_audit.py — ML Feature Importance Audit.

Detects potential data leakage from bookmaker odds in ML models.
If market features (market_home_prob, market_draw_prob, market_away_prob)
dominate feature importance, the ML model is essentially copying the market
rather than learning independent signals.

Thresholds:
    - Market features > 50% total importance → CRITICAL (pure market copy)
    - Market features > 30% total importance → WARNING (heavy market reliance)
    - Market features < 30% total importance → OK (model learns real patterns)

Usage:
    python -m src.monitoring.feature_audit
"""
from __future__ import annotations

import base64
import io
import pickle
from typing import Any

from src.config import logger, supabase
from src.constants import FEATURE_COLS

MARKET_FEATURES = {"market_home_prob", "market_draw_prob", "market_away_prob"}


def _load_model_importances() -> dict[str, dict[str, float]]:
    """Load feature importances from all active XGBoost models."""
    rows = (
        supabase.table("ml_models")
        .select("model_name, feature_importance, model_type, is_active")
        .eq("is_active", True)
        .execute()
        .data
    )

    results: dict[str, dict[str, float]] = {}
    for row in rows:
        name = row["model_name"]
        imp = row.get("feature_importance")
        if imp and isinstance(imp, dict):
            results[name] = {k: float(v) for k, v in imp.items()}

    return results


def audit_model(model_name: str, importances: dict[str, float]) -> dict[str, Any]:
    """Audit a single model's feature importance for data leakage.

    Returns:
        Dict with market_share, top_features, verdict, and recommendations.
    """
    total_imp = sum(importances.values())
    if total_imp == 0:
        return {"model": model_name, "status": "NO_IMPORTANCE_DATA"}

    # Normalize to percentages
    normalized = {k: v / total_imp for k, v in importances.items()}

    # Market features share
    market_share = sum(normalized.get(f, 0) for f in MARKET_FEATURES)

    # Top 10 features
    top_features = sorted(normalized.items(), key=lambda x: -x[1])[:10]

    # ELO features share
    elo_features = {"home_elo", "away_elo", "elo_diff", "elo_diff_squared"}
    elo_share = sum(normalized.get(f, 0) for f in elo_features)

    # Form features share
    form_features = {"home_form", "away_form", "form_diff", "home_form_long", "away_form_long", "form_long_diff"}
    form_share = sum(normalized.get(f, 0) for f in form_features)

    # Verdict
    if market_share > 0.50:
        verdict = "CRITICAL_LEAKAGE"
        recommendation = (
            "Market features dominate (>50%). The ML model is essentially copying bookmaker odds. "
            "Consider removing market features and retraining, or using them only as a separate "
            "calibration signal rather than an input feature."
        )
    elif market_share > 0.30:
        verdict = "WARNING_MARKET_HEAVY"
        recommendation = (
            "Market features are heavily weighted (>30%). The model partially relies on bookmaker "
            "odds. Consider reducing their weight or adding a 'market_available' binary feature "
            "instead of raw probabilities."
        )
    else:
        verdict = "OK"
        recommendation = "Market features are within acceptable range. Model learns real patterns."

    return {
        "model": model_name,
        "market_share_pct": round(market_share * 100, 1),
        "elo_share_pct": round(elo_share * 100, 1),
        "form_share_pct": round(form_share * 100, 1),
        "top_10_features": [(f, round(v * 100, 1)) for f, v in top_features],
        "verdict": verdict,
        "recommendation": recommendation,
    }


def run() -> dict[str, Any]:
    """Run the full feature importance audit on all active models."""
    logger.info("=" * 60)
    logger.info("  FEATURE IMPORTANCE AUDIT — Data Leakage Check")
    logger.info("=" * 60)

    all_importances = _load_model_importances()
    if not all_importances:
        logger.warning("  No models with feature importance data found.")
        return {"status": "NO_DATA", "models": []}

    results = []
    any_critical = False
    any_warning = False

    for model_name, importances in sorted(all_importances.items()):
        audit = audit_model(model_name, importances)
        results.append(audit)

        icon = {"OK": "  ", "WARNING_MARKET_HEAVY": "  ", "CRITICAL_LEAKAGE": "  "}
        logger.info(f"\n  {icon.get(audit.get('verdict', ''), '  ')} {model_name}:")
        logger.info(f"    Market features  : {audit.get('market_share_pct', 0):.1f}%")
        logger.info(f"    ELO features     : {audit.get('elo_share_pct', 0):.1f}%")
        logger.info(f"    Form features    : {audit.get('form_share_pct', 0):.1f}%")
        logger.info(f"    Verdict          : {audit.get('verdict', 'UNKNOWN')}")

        if audit.get("top_10_features"):
            logger.info("    Top 5 features:")
            for fname, pct in audit["top_10_features"][:5]:
                marker = " [MARKET]" if fname in MARKET_FEATURES else ""
                logger.info(f"      {fname:35s} {pct:5.1f}%{marker}")

        if audit.get("verdict") == "CRITICAL_LEAKAGE":
            any_critical = True
        elif audit.get("verdict") == "WARNING_MARKET_HEAVY":
            any_warning = True

    overall = "CRITICAL" if any_critical else ("WARNING" if any_warning else "HEALTHY")
    logger.info(f"\n  Overall: {overall}")

    return {
        "status": overall,
        "models": results,
        "n_models_audited": len(results),
    }


if __name__ == "__main__":
    run()
