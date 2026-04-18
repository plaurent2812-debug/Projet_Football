"""Tests pour feature_drift — KS test training vs prod."""
from __future__ import annotations

import numpy as np

from src.monitoring.feature_drift import (
    ks_test_feature,
    run_feature_drift_check,
)


def test_ks_identical_distributions_returns_p_close_to_1():
    rng = np.random.default_rng(seed=42)
    train = rng.normal(0, 1, 1000)
    prod = rng.normal(0, 1, 500)
    result = ks_test_feature(train, prod)
    assert result["p_value"] > 0.01
    assert result["drift_detected"] is False


def test_ks_shifted_distribution_detects_drift():
    rng = np.random.default_rng(seed=42)
    train = rng.normal(0, 1, 1000)
    prod = rng.normal(0.5, 1, 500)  # mean-shifted
    result = ks_test_feature(train, prod, alpha=0.01)
    assert result["drift_detected"] is True
    assert result["p_value"] < 0.01


def test_ks_ignores_nans():
    train = np.array([1.0, 2.0, np.nan, 3.0, 4.0])
    prod = np.array([1.0, np.nan, 2.5, 3.0])
    result = ks_test_feature(train, prod)
    assert "p_value" in result
    # Pas de NaN dans la statistique
    assert not np.isnan(result["p_value"])


def test_ks_empty_input_returns_no_drift():
    result = ks_test_feature(np.array([]), np.array([1.0, 2.0]))
    assert result["drift_detected"] is False
    assert result["p_value"] is None


def test_run_feature_drift_check_aggregates(monkeypatch):
    """Test global : charge distributions train+prod, retourne dict per feature."""
    from src.monitoring import feature_drift

    rng = np.random.default_rng(seed=123)
    def _fake_train():
        return {
            "elo_diff": rng.normal(0, 100, 500),
            "home_form": rng.normal(2, 1, 500),
        }
    def _fake_prod(window_days=30):
        return {
            "elo_diff": rng.normal(0, 100, 200),
            "home_form": rng.normal(5, 1, 200),  # drift sur form
        }

    monkeypatch.setattr(feature_drift, "_load_training_distribution", _fake_train)
    monkeypatch.setattr(feature_drift, "_load_prod_distribution", _fake_prod)

    result = run_feature_drift_check(alpha=0.01, window_days=30)
    assert "per_feature" in result
    assert "home_form" in result["per_feature"]
    assert result["per_feature"]["home_form"]["drift_detected"] is True
    assert result["n_drifted"] >= 1
