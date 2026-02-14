from __future__ import annotations

"""
Tests unitaires pour models/ml_predictor.py — avec mocks modèle et Supabase.

Couvre :
  - build_feature_vector (contextes complets et incomplets)
  - _impute (gestion des NaN)
  - predict_1x2 avec cache de modèles mocké
  - predict_binary avec cache de modèles mocké
  - get_ml_predictions quand aucun modèle chargé
  - load_models quand Supabase ne renvoie rien
"""
import base64
import pickle
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from constants import FEATURE_COLS
from models.ml_predictor import (
    _impute,
    build_feature_vector,
    get_ml_predictions,
    load_models,
    predict_1x2,
    predict_binary,
)

# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def _full_context() -> dict:
    """Return a context dict with every FEATURE_COLS key set."""
    ctx: dict[str, float] = {}
    for i, col in enumerate(FEATURE_COLS):
        ctx[col] = float(i + 1)
    return ctx


def _partial_context() -> dict:
    """Return a context dict with only a few keys populated."""
    return {
        "home_elo": 1600.0,
        "away_elo": 1450.0,
        "elo_diff": 150.0,
    }


def _make_mock_model(n_classes: int = 3) -> MagicMock:
    """Create a mock sklearn-style model with predict_proba."""
    model = MagicMock()
    if n_classes == 3:
        model.predict_proba.return_value = np.array([[0.50, 0.25, 0.25]])
    else:
        model.predict_proba.return_value = np.array([[0.40, 0.60]])
    return model


def _make_mock_label_encoder(classes: list[str] | None = None) -> MagicMock:
    le = MagicMock()
    le.classes_ = np.array(classes or ["A", "D", "H"])
    return le


# ═══════════════════════════════════════════════════════════════════
#  build_feature_vector
# ═══════════════════════════════════════════════════════════════════


class TestBuildFeatureVector:
    """Tests de la construction du vecteur de features."""

    def test_shape_with_full_context(self):
        X = build_feature_vector(_full_context())
        assert X.shape == (1, len(FEATURE_COLS))

    def test_dtype_is_float32(self):
        X = build_feature_vector(_full_context())
        assert X.dtype == np.float32

    def test_values_match_context(self):
        ctx = _full_context()
        X = build_feature_vector(ctx)
        for i, col in enumerate(FEATURE_COLS):
            assert X[0, i] == pytest.approx(ctx[col], abs=1e-4)

    def test_missing_keys_become_nan(self):
        X = build_feature_vector(_partial_context())
        nan_count = int(np.isnan(X).sum())
        # Most columns are missing in partial context
        assert nan_count > 0
        assert nan_count == len(FEATURE_COLS) - 3  # only 3 keys provided

    def test_empty_context_all_nan(self):
        X = build_feature_vector({})
        assert np.isnan(X).all()
        assert X.shape == (1, len(FEATURE_COLS))

    def test_none_value_treated_as_nan(self):
        ctx = {"home_elo": None, "away_elo": 1500.0}
        X = build_feature_vector(ctx)
        idx_home_elo = FEATURE_COLS.index("home_elo")
        idx_away_elo = FEATURE_COLS.index("away_elo")
        assert np.isnan(X[0, idx_home_elo])
        assert X[0, idx_away_elo] == pytest.approx(1500.0, abs=1e-4)


# ═══════════════════════════════════════════════════════════════════
#  _impute
# ═══════════════════════════════════════════════════════════════════


class TestImpute:
    """Tests de l'imputation des valeurs manquantes."""

    @patch("models.ml_predictor._model_cache", {})
    def test_no_imputer_replaces_nan_with_zero(self):
        X = np.array([[1.0, np.nan, 3.0]], dtype=np.float32)
        result = _impute(X, "unknown_model")
        assert result[0, 1] == 0.0
        assert result[0, 0] == pytest.approx(1.0)

    @patch("models.ml_predictor._model_cache", {})
    def test_all_nan_replaced_by_zero(self):
        X = np.array([[np.nan, np.nan, np.nan]], dtype=np.float32)
        result = _impute(X, "some_model")
        assert not np.isnan(result).any()
        assert (result == 0.0).all()

    @patch("models.ml_predictor._model_cache")
    def test_with_imputer_calls_transform(self, mock_cache):
        imputer = MagicMock()
        expected = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        imputer.transform.return_value = expected
        mock_cache.get.return_value = {"imputer": imputer, "model": MagicMock()}

        X = np.array([[1.0, np.nan, 3.0]], dtype=np.float32)
        result = _impute(X, "xgb_1x2")
        imputer.transform.assert_called_once()
        np.testing.assert_array_equal(result, expected)

    @patch("models.ml_predictor._model_cache")
    def test_imputer_failure_falls_back_to_median(self, mock_cache):
        imputer = MagicMock()
        imputer.transform.side_effect = ValueError("shape mismatch")
        mock_cache.get.return_value = {"imputer": imputer, "model": MagicMock()}

        X = np.array([[10.0, np.nan, 30.0]], dtype=np.float32)
        result = _impute(X, "xgb_1x2")
        # Fallback: median of single-row → same row values, NaN replaced with 0
        assert not np.isnan(result).any()


# ═══════════════════════════════════════════════════════════════════
#  predict_1x2  (mock model cache)
# ═══════════════════════════════════════════════════════════════════


class TestPredict1x2:
    """Tests de la prédiction 1X2 avec modèle XGBoost mocké."""

    @patch("models.ml_predictor._model_cache", {})
    def test_returns_none_when_no_model(self):
        result = predict_1x2(_full_context())
        assert result is None

    @patch("models.ml_predictor._model_cache")
    def test_returns_dict_with_ml_keys(self, mock_cache):
        model = _make_mock_model(n_classes=3)
        le = _make_mock_label_encoder(["A", "D", "H"])
        mock_cache.__contains__ = lambda self, k: k == "xgb_1x2"
        mock_cache.__getitem__ = lambda self, k: {
            "model": model,
            "label_encoder": le,
            "imputer": None,
        }
        mock_cache.get = lambda k, default=None: (
            {"model": model, "label_encoder": le, "imputer": None} if k == "xgb_1x2" else default
        )

        result = predict_1x2(_full_context())
        assert result is not None
        assert "ml_home" in result
        assert "ml_draw" in result
        assert "ml_away" in result

    @patch("models.ml_predictor._model_cache")
    def test_probabilities_are_integers(self, mock_cache):
        model = _make_mock_model(n_classes=3)
        le = _make_mock_label_encoder(["A", "D", "H"])
        mock_cache.__contains__ = lambda self, k: k == "xgb_1x2"
        mock_cache.__getitem__ = lambda self, k: {
            "model": model,
            "label_encoder": le,
            "imputer": None,
        }
        mock_cache.get = lambda k, default=None: (
            {"model": model, "label_encoder": le, "imputer": None} if k == "xgb_1x2" else default
        )

        result = predict_1x2(_full_context())
        assert isinstance(result["ml_home"], int)
        assert isinstance(result["ml_draw"], int)
        assert isinstance(result["ml_away"], int)

    @patch("models.ml_predictor._model_cache")
    def test_label_encoder_maps_correctly(self, mock_cache):
        """Classes ['A','D','H'] with probas [0.50,0.25,0.25] → A=50, D=25, H=25."""
        model = MagicMock()
        model.predict_proba.return_value = np.array([[0.20, 0.30, 0.50]])
        le = _make_mock_label_encoder(["A", "D", "H"])
        payload = {"model": model, "label_encoder": le, "imputer": None}
        mock_cache.__contains__ = lambda self, k: k == "xgb_1x2"
        mock_cache.__getitem__ = lambda self, k: payload
        mock_cache.get = lambda k, default=None: payload if k == "xgb_1x2" else default

        result = predict_1x2(_full_context())
        # H maps to index 2 → 0.50, D → index 1 → 0.30, A → index 0 → 0.20
        assert result["ml_home"] == 50
        assert result["ml_draw"] == 30
        assert result["ml_away"] == 20

    @patch("models.ml_predictor._model_cache")
    def test_no_label_encoder_uses_positional(self, mock_cache):
        model = MagicMock()
        model.predict_proba.return_value = np.array([[0.55, 0.25, 0.20]])
        payload = {"model": model, "label_encoder": None, "imputer": None}
        mock_cache.__contains__ = lambda self, k: k == "xgb_1x2"
        mock_cache.__getitem__ = lambda self, k: payload
        mock_cache.get = lambda k, default=None: payload if k == "xgb_1x2" else default

        result = predict_1x2(_full_context())
        # Without label_encoder: H=probas[0], D=probas[1], A=probas[2]
        assert result["ml_home"] == 55
        assert result["ml_draw"] == 25
        assert result["ml_away"] == 20


# ═══════════════════════════════════════════════════════════════════
#  predict_binary  (mock model cache)
# ═══════════════════════════════════════════════════════════════════


class TestPredictBinary:
    """Tests de la prédiction binaire (BTTS, Over)."""

    @patch("models.ml_predictor._model_cache", {})
    def test_returns_none_when_model_missing(self):
        result = predict_binary("xgb_btts", _full_context())
        assert result is None

    @patch("models.ml_predictor._model_cache")
    def test_returns_integer_percentage(self, mock_cache):
        model = _make_mock_model(n_classes=2)
        payload = {"model": model, "imputer": None}
        mock_cache.__contains__ = lambda self, k: k == "xgb_btts"
        mock_cache.__getitem__ = lambda self, k: payload
        mock_cache.get = lambda k, default=None: payload if k == "xgb_btts" else default

        result = predict_binary("xgb_btts", _full_context())
        assert isinstance(result, int)
        assert 0 <= result <= 100

    @patch("models.ml_predictor._model_cache")
    def test_uses_positive_class_probability(self, mock_cache):
        model = MagicMock()
        # probas[0]=0.30 (negative), probas[1]=0.70 (positive)
        model.predict_proba.return_value = np.array([[0.30, 0.70]])
        payload = {"model": model, "imputer": None}
        mock_cache.__contains__ = lambda self, k: k == "xgb_over25"
        mock_cache.__getitem__ = lambda self, k: payload
        mock_cache.get = lambda k, default=None: payload if k == "xgb_over25" else default

        result = predict_binary("xgb_over25", _full_context())
        assert result == 70


# ═══════════════════════════════════════════════════════════════════
#  get_ml_predictions  (no models loaded)
# ═══════════════════════════════════════════════════════════════════


class TestGetMlPredictions:
    """Tests de l'agrégation des prédictions ML."""

    @patch("models.ml_predictor.load_models", return_value=False)
    def test_returns_empty_when_no_models(self, mock_load):
        result = get_ml_predictions(_full_context())
        assert result == {}
        mock_load.assert_called_once()

    @patch("models.ml_predictor.load_models", return_value=True)
    @patch(
        "models.ml_predictor.predict_1x2",
        return_value={"ml_home": 50, "ml_draw": 30, "ml_away": 20},
    )
    @patch("models.ml_predictor.predict_binary", return_value=None)
    @patch("models.ml_predictor.predict_total_goals", return_value=None)
    def test_includes_1x2_when_available(self, mock_tg, mock_bin, mock_1x2, mock_load):
        result = get_ml_predictions(_full_context())
        assert result["ml_home"] == 50
        assert result["ml_draw"] == 30

    @patch("models.ml_predictor.load_models", return_value=True)
    @patch("models.ml_predictor.predict_1x2", return_value=None)
    @patch("models.ml_predictor.predict_binary", return_value=65)
    @patch("models.ml_predictor.predict_total_goals", return_value=2.75)
    def test_includes_btts_and_total_goals(self, mock_tg, mock_bin, mock_1x2, mock_load):
        result = get_ml_predictions(_full_context())
        assert "ml_btts" in result
        assert result["ml_total_goals"] == 2.75


# ═══════════════════════════════════════════════════════════════════
#  load_models  (mock Supabase)
# ═══════════════════════════════════════════════════════════════════


class TestLoadModels:
    """Tests du chargement des modèles depuis Supabase."""

    @patch("models.ml_predictor._cache_loaded", False)
    @patch("models.ml_predictor._model_cache", {})
    @patch("models.ml_predictor.supabase")
    def test_no_rows_returns_false(self, mock_sb):
        query = MagicMock()
        query.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_sb.table.return_value = query

        result = load_models()
        assert result is False

    @patch("models.ml_predictor._cache_loaded", False)
    @patch("models.ml_predictor._model_cache", {})
    @patch("models.ml_predictor.supabase")
    def test_valid_model_loaded_into_cache(self, mock_sb):
        # Serialize a simple payload
        payload = {"model": "fake_model", "imputer": None}
        b64_weights = base64.b64encode(pickle.dumps(payload)).decode()

        query = MagicMock()
        query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"model_name": "xgb_1x2", "model_weights": b64_weights, "is_active": True}]
        )
        mock_sb.table.return_value = query

        result = load_models()
        assert result is True

    @patch("models.ml_predictor._cache_loaded", False)
    @patch("models.ml_predictor._model_cache", {})
    @patch("models.ml_predictor.supabase")
    def test_row_without_weights_skipped(self, mock_sb):
        query = MagicMock()
        query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"model_name": "xgb_1x2", "model_weights": None, "is_active": True}]
        )
        mock_sb.table.return_value = query

        result = load_models()
        assert result is False  # no model actually loaded

    @patch("models.ml_predictor._cache_loaded", False)
    @patch("models.ml_predictor._model_cache", {})
    @patch("models.ml_predictor.supabase")
    def test_supabase_exception_returns_false(self, mock_sb):
        mock_sb.table.side_effect = Exception("connection error")

        result = load_models()
        assert result is False

    @patch("models.ml_predictor._model_cache", {"xgb_1x2": {}})
    @patch("models.ml_predictor._cache_loaded", True)
    def test_already_loaded_skips_query(self):
        # Should not call supabase at all — just return from cache
        result = load_models()
        assert result is True

    @patch("models.ml_predictor._model_cache", {})
    @patch("models.ml_predictor._cache_loaded", True)
    def test_already_loaded_empty_cache_returns_false(self):
        result = load_models()
        assert result is False
