import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.training.walk_forward import walk_forward_evaluate


def test_walk_forward_returns_expected_folds():
    rng = np.random.default_rng(42)
    n = 500
    dates = pd.Series(pd.date_range("2024-01-01", periods=n, freq="D"))
    X = pd.DataFrame(rng.normal(size=(n, 5)), columns=[f"f{i}" for i in range(5)])
    y = pd.Series(rng.choice(["H", "D", "A"], size=n, p=[0.45, 0.25, 0.30]))

    def mk():
        return LogisticRegression(max_iter=500)

    report = walk_forward_evaluate(X, y, dates, mk, n_splits=4, holdout_months=1)
    assert 3 <= len(report["folds"]) <= 4
    assert 0.0 <= report["brier_1x2_mean"] <= 2.0
    for fold in report["folds"]:
        assert fold["n_train"] > 0 and fold["n_test"] > 0
