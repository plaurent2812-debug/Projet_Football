"""Produit le rapport walk-forward pour publication (page /methodology).

Lit les prédictions historiques de Supabase, ré-entraîne par fold, publie JSON.
Output: ProbaLab/public/walk_forward_report.json (consommé par le frontend).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import supabase
from src.training.walk_forward import walk_forward_evaluate


def _load_history() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    rows = (
        supabase.table("prediction_results")
        .select("*")
        .not_.is_("actual_result", "null")
        .execute()
        .data
    )
    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.dropna(subset=["actual_result"]).sort_values("created_at")
    feature_cols = [c for c in df.columns if c.startswith(("market_", "poisson_", "elo_"))]
    X = df[feature_cols].fillna(0.0)
    y = df["actual_result"]
    dates = df["created_at"]
    return X, y, dates


def _write_minimal_report(out_path: Path, reason: str) -> None:
    """Write a minimal JSON report with an error disclaimer when data is insufficient."""
    report = {
        "error": reason,
        "folds": [],
        "brier_1x2_mean": None,
        "brier_1x2_std": None,
        "log_loss_mean": None,
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Minimal report written (error state): {out_path}")
    print(f"Reason: {reason}")


def main(out_path: Path = Path("dashboard/public/walk_forward_report.json")):
    from xgboost import XGBClassifier

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Load historical data ---
    try:
        X, y, dates = _load_history()
    except Exception as e:
        _write_minimal_report(out_path, f"Insufficient historical data: {e}")
        return

    # --- Validate data sufficiency ---
    if X.empty or len(X) < 100:
        _write_minimal_report(
            out_path,
            "Insufficient historical data: fewer than 100 rows with actual_result in prediction_results",
        )
        return

    if X.shape[1] == 0:
        _write_minimal_report(
            out_path,
            "Insufficient historical data: no market_*/poisson_*/elo_* feature columns found in prediction_results",
        )
        return

    valid_labels = {"H", "D", "A"}
    if not set(y.unique()).issubset(valid_labels):
        _write_minimal_report(
            out_path,
            f"Insufficient historical data: unexpected labels {set(y.unique()) - valid_labels}",
        )
        return

    # --- Run walk-forward evaluation ---
    def mk():
        return XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            max_depth=4,
            n_estimators=200,
            learning_rate=0.05,
            random_state=42,
        )

    y_encoded = y.map({"H": 0, "D": 1, "A": 2})
    try:
        report = walk_forward_evaluate(X, y_encoded, dates, mk, n_splits=6, holdout_months=3)
    except Exception as e:
        _write_minimal_report(out_path, f"Walk-forward evaluation failed: {e}")
        return

    out_path.write_text(json.dumps(report, indent=2))
    print(f"Report written: {out_path}")
    print(f"Brier 1X2 mean (across {len(report['folds'])} folds): {report['brier_1x2_mean']:.4f}")


if __name__ == "__main__":
    main()
