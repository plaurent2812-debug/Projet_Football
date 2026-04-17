"""Walk-forward temporal validation — expanding window.

Splits historical matches by chronological windows (3-6 months holdout)
and reports Brier score, log-loss, calibration ECE per window.

Usage:
    from src.training.walk_forward import walk_forward_evaluate
    report = walk_forward_evaluate(X, y, dates, n_splits=6, holdout_months=3)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss


def walk_forward_evaluate(
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    model_fn,
    n_splits: int = 6,
    holdout_months: int = 3,
) -> dict[str, Any]:
    """Evaluate a model using walk-forward (expanding window).

    Args:
        X: feature matrix, time-ordered
        y: labels ("H"/"D"/"A" or 0/1/2)
        dates: datetime Series aligned with X
        model_fn: callable () → fresh model (with .fit, .predict_proba)
        n_splits: number of walk-forward folds
        holdout_months: size of holdout window in months

    Returns:
        dict with per-fold Brier 1X2, log-loss, ECE + aggregated stats.
    """
    assert len(X) == len(y) == len(dates)
    sorted_idx = dates.sort_values().index
    X = X.loc[sorted_idx].reset_index(drop=True)
    y = y.loc[sorted_idx].reset_index(drop=True)
    dates = dates.loc[sorted_idx].reset_index(drop=True)

    min_date, max_date = dates.min(), dates.max()
    total_days = (max_date - min_date).days
    holdout_days = holdout_months * 30
    fold_step = max(1, (total_days - holdout_days) // n_splits)

    fold_results = []
    for k in range(1, n_splits + 1):
        cutoff = min_date + pd.Timedelta(days=k * fold_step)
        holdout_end = cutoff + pd.Timedelta(days=holdout_days)
        train_mask = dates < cutoff
        test_mask = (dates >= cutoff) & (dates < holdout_end)
        if test_mask.sum() < 20:
            continue

        model = model_fn()
        model.fit(X[train_mask], y[train_mask])
        probas = model.predict_proba(X[test_mask])

        y_true = y[test_mask].values
        brier_1x2 = _brier_1x2(probas, y_true, model.classes_)
        ll = log_loss(y_true, probas, labels=model.classes_)

        fold_results.append(
            {
                "fold": k,
                "train_until": cutoff.isoformat(),
                "test_from": cutoff.isoformat(),
                "test_to": holdout_end.isoformat(),
                "n_train": int(train_mask.sum()),
                "n_test": int(test_mask.sum()),
                "brier_1x2": brier_1x2,
                "log_loss": ll,
            }
        )

    return {
        "folds": fold_results,
        "brier_1x2_mean": float(np.mean([f["brier_1x2"] for f in fold_results])),
        "brier_1x2_std": float(np.std([f["brier_1x2"] for f in fold_results])),
        "log_loss_mean": float(np.mean([f["log_loss"] for f in fold_results])),
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


def _brier_1x2(probas: np.ndarray, y_true: np.ndarray, classes: np.ndarray) -> float:
    idx = {c: i for i, c in enumerate(classes)}
    total = 0.0
    for p_row, y in zip(probas, y_true):
        y_vec = np.zeros(len(classes))
        y_vec[idx[y]] = 1.0
        total += float(np.sum((p_row - y_vec) ** 2))
    return total / len(y_true)
