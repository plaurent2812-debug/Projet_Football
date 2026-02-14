from __future__ import annotations

"""
ml_predictor.py — Chargement et utilisation des modèles ML entraînés.

Charge les modèles XGBoost depuis Supabase (table ml_models),
les met en cache, et fournit des prédictions probabilistes.
"""
import base64
import pickle
from typing import Any

import numpy as np
from config import logger, supabase
from constants import FEATURE_COLS
from numpy.typing import NDArray

# Cache des modèles chargés
_model_cache: dict[str, dict[str, Any]] = {}
_cache_loaded: bool = False

# Lazy import pour éviter les imports circulaires
_ensemble_module = None


def load_models() -> bool:
    """Load all active ML models from the Supabase ``ml_models`` table.

    Deserialises base-64-encoded pickle payloads and stores them in the
    module-level :data:`_model_cache` dict.  Subsequent calls are no-ops
    once the cache has been populated.

    Returns:
        ``True`` if at least one model is available in cache, ``False``
        otherwise.
    """
    global _model_cache, _cache_loaded

    if _cache_loaded:
        return bool(_model_cache)

    try:
        rows: list[dict] = (
            supabase.table("ml_models")
            .select("model_name, model_weights, is_active")
            .eq("is_active", True)
            .execute()
            .data
        )

        for row in rows:
            name: str = row["model_name"]
            weights_b64: str | None = row.get("model_weights")
            if not weights_b64:
                continue
            try:
                payload: dict[str, Any] = pickle.loads(base64.b64decode(weights_b64))
                _model_cache[name] = payload
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur chargement modèle {name}: {e}")

        _cache_loaded = True
        if _model_cache:
            logger.info(
                f"  🤖 {len(_model_cache)} modèles ML chargés : {list(_model_cache.keys())}"
            )
        return bool(_model_cache)
    except Exception:
        _cache_loaded = True
        return False


def build_feature_vector(context: dict) -> NDArray[np.float32]:
    """Build a feature matrix from a match context dictionary.

    Iterates over :data:`constants.FEATURE_COLS` and extracts the
    corresponding value from *context*, replacing missing entries with
    ``NaN``.

    Args:
        context: Dictionary whose keys match :data:`FEATURE_COLS`
            (e.g. ``elo_home``, ``form_home``, …).

    Returns:
        NumPy array of shape ``(1, n_features)`` with dtype
        ``float32``.
    """
    features: list[float] = []
    for col in FEATURE_COLS:
        val = context.get(col)
        features.append(float(val) if val is not None else np.nan)

    X: NDArray[np.float32] = np.array([features], dtype=np.float32)
    return X


def _impute(X: NDArray[np.float32], model_name: str) -> NDArray[np.float32]:
    """Impute missing values using the saved imputer or a fallback strategy.

    If the cached model payload contains an ``imputer`` object, it is
    applied via ``transform``.  On failure (or if no imputer exists),
    ``NaN`` values are replaced with per-column medians or ``0.0``.

    Args:
        X: Feature matrix of shape ``(1, n_features)``.
        model_name: Key into :data:`_model_cache` to retrieve the
            associated imputer.

    Returns:
        Imputed feature matrix with the same shape as *X*.
    """
    payload: dict[str, Any] | None = _model_cache.get(model_name)
    if payload and payload.get("imputer"):
        try:
            X = payload["imputer"].transform(X)
        except Exception:
            # Fallback : remplacer NaN par la médiane globale
            col_medians: NDArray[np.floating] = np.nanmedian(X, axis=0)
            for i in range(X.shape[1]):
                if np.isnan(X[0, i]):
                    X[0, i] = col_medians[i] if not np.isnan(col_medians[i]) else 0.0
    else:
        # Pas d'imputer — remplacer les NaN par 0
        X = np.nan_to_num(X, nan=0.0)
    return X


def predict_1x2(context: dict) -> dict[str, int] | None:
    """Predict Home / Draw / Away probabilities using the XGBoost 1X2 model.

    Args:
        context: Match context dict (see :func:`build_feature_vector`).

    Returns:
        Dict with keys ``ml_home``, ``ml_draw``, ``ml_away`` (each an
        integer percentage), or ``None`` if the ``xgb_1x2`` model is not
        loaded.
    """
    if "xgb_1x2" not in _model_cache:
        return None

    X: NDArray[np.float32] = build_feature_vector(context)
    X = _impute(X, "xgb_1x2")

    model = _model_cache["xgb_1x2"]["model"]
    le = _model_cache["xgb_1x2"].get("label_encoder")

    probas: NDArray[np.floating] = model.predict_proba(X)[0]

    if le:
        classes: NDArray = le.classes_  # ['A', 'D', 'H'] typiquement
        proba_map: dict[str, float] = dict(zip(classes, probas))
    else:
        proba_map = {"H": probas[0], "D": probas[1], "A": probas[2]}

    return {
        "ml_home": round(proba_map.get("H", 0.33) * 100),
        "ml_draw": round(proba_map.get("D", 0.33) * 100),
        "ml_away": round(proba_map.get("A", 0.33) * 100),
    }


def predict_binary(model_name: str, context: dict) -> int | None:
    """Predict a binary outcome probability (e.g. BTTS, Over 2.5).

    Args:
        model_name: Key of the cached model (e.g. ``"xgb_btts"``,
            ``"xgb_over25"``).
        context: Match context dict (see :func:`build_feature_vector`).

    Returns:
        Probability of the positive class as an integer percentage
        (0–100), or ``None`` if the requested model is not loaded.
    """
    if model_name not in _model_cache:
        return None

    X: NDArray[np.float32] = build_feature_vector(context)
    X = _impute(X, model_name)

    model = _model_cache[model_name]["model"]
    probas: NDArray[np.floating] = model.predict_proba(X)[0]

    # probas[1] = probabilité de la classe positive (True/1)
    return round(float(probas[1]) * 100)


def predict_total_goals(context: dict) -> float | None:
    """Predict the expected total goals for a match (regression).

    Args:
        context: Match context dict (see :func:`build_feature_vector`).

    Returns:
        Predicted total goals as a float rounded to two decimals, or
        ``None`` if the ``xgb_total_goals`` model is not loaded.
    """
    if "xgb_total_goals" not in _model_cache:
        return None

    X: NDArray[np.float32] = build_feature_vector(context)
    X = _impute(X, "xgb_total_goals")

    model = _model_cache["xgb_total_goals"]["model"]
    pred: float = model.predict(X)[0]
    return round(float(pred), 2)


def get_ml_predictions(context: dict) -> dict[str, int | float]:
    """Collect all available ML predictions for a match.

    Prefers stacking ensemble predictions when available, with fallback
    to standalone XGBoost models.

    Args:
        context: Match context dict (see :func:`build_feature_vector`).

    Returns:
        Dict with keys such as ``ml_home``, ``ml_draw``, ``ml_away``,
        ``ml_btts``, ``ml_over25``, ``ml_over15``, ``ml_over05``, and
        ``ml_total_goals``.  Only keys whose models are available are
        included.
    """
    if not load_models():
        return {}

    result: dict[str, int | float] = {}

    # ── Essayer l'ensemble en priorité (meilleur modèle) ──────────
    global _ensemble_module
    if _ensemble_module is None:
        try:
            from models import ensemble as _ens
            _ensemble_module = _ens
        except ImportError:
            _ensemble_module = False  # type: ignore[assignment]

    ensemble_used = False
    if _ensemble_module:
        # 1X2 Ensemble
        ens_1x2 = _ensemble_module.predict_ensemble(context, "ensemble_1x2")
        if ens_1x2:
            result.update(ens_1x2)
            ensemble_used = True

        # BTTS Ensemble
        ens_btts = _ensemble_module.predict_ensemble_binary(context, "ensemble_btts")
        if ens_btts is not None:
            result["ml_btts"] = ens_btts

        # Over 2.5 Ensemble
        ens_o25 = _ensemble_module.predict_ensemble_binary(context, "ensemble_over25")
        if ens_o25 is not None:
            result["ml_over25"] = ens_o25

    # ── Fallback XGBoost si pas d'ensemble ────────────────────────
    if not ensemble_used:
        r1x2: dict[str, int] | None = predict_1x2(context)
        if r1x2:
            result.update(r1x2)

    if "ml_btts" not in result:
        btts: int | None = predict_binary("xgb_btts", context)
        if btts is not None:
            result["ml_btts"] = btts

    if "ml_over25" not in result:
        o25: int | None = predict_binary("xgb_over25", context)
        if o25 is not None:
            result["ml_over25"] = o25

    # Over 1.5 (XGBoost only for now)
    o15: int | None = predict_binary("xgb_over15", context)
    if o15 is not None:
        result["ml_over15"] = o15

    # Over 0.5 (XGBoost only for now)
    o05: int | None = predict_binary("xgb_over05", context)
    if o05 is not None:
        result["ml_over05"] = o05

    # Total buts
    tg: float | None = predict_total_goals(context)
    if tg is not None:
        result["ml_total_goals"] = tg

    return result
