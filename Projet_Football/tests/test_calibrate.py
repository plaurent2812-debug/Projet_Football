"""
Tests unitaires pour calibrate.py — fonctions de calibration ML.
"""

import numpy as np
from models.calibrate import compute_bias, fit_isotonic_calibration, fit_platt_scaling

# ═══════════════════════════════════════════════════════════════════
#  PLATT SCALING
# ═══════════════════════════════════════════════════════════════════


class TestPlattScaling:
    """Tests de la calibration Platt (régression logistique)."""

    def test_insufficient_samples_returns_identity(self):
        X = np.array([[0.5], [0.6]])
        y = np.array([1, 0])
        a, b, _, _ = fit_platt_scaling(X, y)
        assert a == 1.0 and b == 0.0

    def test_returns_four_values(self):
        np.random.seed(42)
        X = np.random.uniform(0.2, 0.8, size=(50, 1))
        y = (X.ravel() > 0.5).astype(float)
        result = fit_platt_scaling(X, y)
        assert len(result) == 4

    def test_calibration_improves_or_maintains_brier(self):
        np.random.seed(42)
        X = np.random.uniform(0.1, 0.9, size=(100, 1))
        y = (X.ravel() + np.random.normal(0, 0.15, 100) > 0.5).astype(float)
        _, _, brier_before, brier_after = fit_platt_scaling(X, y)
        if brier_after is not None:
            # La calibration devrait améliorer ou au pire maintenir le Brier
            assert brier_after <= brier_before + 0.02

    def test_perfect_calibration(self):
        X = np.array([[0.1], [0.3], [0.5], [0.7], [0.9]] * 10)
        y = np.array([0, 0, 0, 1, 1] * 10).astype(float)
        a, b, brier_before, brier_after = fit_platt_scaling(X, y)
        assert brier_before is not None


# ═══════════════════════════════════════════════════════════════════
#  BIAIS
# ═══════════════════════════════════════════════════════════════════


class TestComputeBias:
    """Tests du calcul de biais."""

    def test_overestimation_positive_bias(self):
        X = np.array([[0.8], [0.7], [0.9]])
        y = np.array([0, 0, 1])
        bias = compute_bias(X, y)
        assert bias > 0  # On surestime

    def test_underestimation_negative_bias(self):
        X = np.array([[0.2], [0.3], [0.1]])
        y = np.array([1, 1, 0])
        bias = compute_bias(X, y)
        assert bias < 0  # On sous-estime

    def test_perfect_calibration_zero_bias(self):
        X = np.array([[0.5]])
        y = np.array([0.5])
        assert abs(compute_bias(X, y)) < 0.001

    def test_empty_returns_zero(self):
        X = np.array([]).reshape(-1, 1)
        y = np.array([])
        assert compute_bias(X, y) == 0.0


# ═══════════════════════════════════════════════════════════════════
#  ISOTONIC CALIBRATION
# ═══════════════════════════════════════════════════════════════════


class TestIsotonicCalibration:
    """Tests de la calibration isotonique."""

    def test_insufficient_samples_returns_none(self):
        X = np.array([[0.5], [0.6]])
        y = np.array([1, 0])
        model, brier_before, brier_after = fit_isotonic_calibration(X, y)
        assert model is None
        assert brier_before is None
        assert brier_after is None

    def test_returns_model_and_brier(self):
        np.random.seed(42)
        X = np.random.uniform(0.1, 0.9, size=(100, 1))
        y = (X.ravel() + np.random.normal(0, 0.15, 100) > 0.5).astype(float)
        model, brier_before, brier_after = fit_isotonic_calibration(X, y)
        assert model is not None
        assert brier_before is not None
        assert brier_after is not None

    def test_calibrated_predictions_are_monotonic(self):
        np.random.seed(42)
        X = np.random.uniform(0.1, 0.9, size=(100, 1))
        y = (X.ravel() > 0.5).astype(float)
        model, _, _ = fit_isotonic_calibration(X, y)
        if model is not None:
            test_x = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
            calibrated = model.predict(test_x)
            # Isotonic regression should be monotonically increasing
            for i in range(len(calibrated) - 1):
                assert calibrated[i] <= calibrated[i + 1] + 1e-10

    def test_calibration_improves_brier(self):
        np.random.seed(42)
        X = np.random.uniform(0.0, 1.0, size=(200, 1))
        y = (X.ravel() + np.random.normal(0, 0.2, 200) > 0.5).astype(float)
        _, brier_before, brier_after = fit_isotonic_calibration(X, y)
        if brier_before is not None and brier_after is not None:
            assert brier_after <= brier_before + 0.02

    def test_flat_vector_accepted(self):
        """Should handle flat (n,) arrays."""
        np.random.seed(42)
        X_flat = np.random.uniform(0.1, 0.9, size=50)
        y = (X_flat > 0.5).astype(float)
        model, _, _ = fit_isotonic_calibration(X_flat, y)
        assert model is not None
