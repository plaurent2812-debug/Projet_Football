from __future__ import annotations
"""
nhl_ml_predictor.py — Inférence ML match-level pour la NHL.

Charge les modèles XGBoost entraînés par train_match.py
et fournit des prédictions de victoire et Over 5.5.
Fallback sur les probas Poisson si modèle non disponible.
"""

import io
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import logger


# ── Safe Deserialization ──────────────────────────────────────────
_ALLOWED_PREFIXES = (
    "numpy", "pandas", "sklearn", "xgboost", "lightgbm",
    "_codecs", "builtins", "collections", "copyreg",
)


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        if any(module.startswith(p) for p in _ALLOWED_PREFIXES):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Blocked: {module}.{name}")


def _safe_pickle_load(f) -> Any:
    return _RestrictedUnpickler(f).load()

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "nhl"

# Cache
_models: dict[str, dict] = {}
_loaded = False


def _load_models():
    """Charge les modèles match-level depuis le disque."""
    global _models, _loaded
    if _loaded:
        return

    for name in ["win", "over55"]:
        path = MODEL_DIR / f"nhl_match_{name}.pkl"
        if path.exists():
            try:
                with open(path, "rb") as f:
                    data = _safe_pickle_load(f)
                _models[name] = data
                logger.info(f"  ✅ NHL ML model '{name}' chargé ({data['metrics']['n_samples']} samples)")
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur chargement modèle NHL {name}: {e}")
        else:
            logger.info(f"  ℹ️ NHL ML model '{name}' non trouvé ({path})")

    _loaded = True


def predict_nhl_match(features: dict[str, Any]) -> dict[str, float | None]:
    """
    Prédit la probabilité de victoire domicile et Over 5.5 via ML.

    Args:
        features: dict avec les clés MATCH_FEATURES (proba_home, proba_away, etc.)

    Returns:
        {"ml_home_win": float|None, "ml_over_55": float|None}
        None si modèle non disponible.
    """
    _load_models()

    result = {"ml_home_win": None, "ml_over_55": None}

    for model_key, result_key in [("win", "ml_home_win"), ("over55", "ml_over_55")]:
        if model_key not in _models:
            continue

        model_data = _models[model_key]
        model = model_data["model"]
        feature_names = model_data["feature_names"]

        try:
            # Build feature vector in the correct order
            X = pd.DataFrame([{col: float(features.get(col, 0)) for col in feature_names}])
            X = X.replace([np.inf, -np.inf], 0).fillna(0)

            proba = model.predict_proba(X)[0, 1]
            result[result_key] = round(float(proba) * 100)
        except Exception as e:
            logger.warning(f"  ⚠️ NHL ML prediction failed for {model_key}: {e}")

    return result


def is_available() -> bool:
    """Vérifie si au moins un modèle est chargé."""
    _load_models()
    return len(_models) > 0
