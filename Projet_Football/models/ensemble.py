from __future__ import annotations

"""
ensemble.py — Stacking Ensemble pour prédictions football.

Architecture :
  Couche 1 (Base Learners) :
    - XGBoost Classifier
    - LightGBM Classifier
    - Logistic Regression (calibrée)

  Couche 2 (Meta-Learner) :
    - Logistic Regression sur les probas de la couche 1
    + features de confiance (convergence, écart max)

Avantage : chaque modèle capture des patterns différents.
XGBoost excelle sur les interactions, LightGBM sur les catégories,
LogReg fournit une baseline stable et bien calibrée.
"""
import base64
import math
import pickle
from typing import Any

import lightgbm as lgb
import numpy as np
import xgboost as xgb
from config import logger, supabase
from constants import FEATURE_COLS
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ═══════════════════════════════════════════════════════════════════
#  STACKING ENSEMBLE — TRAINING
# ═══════════════════════════════════════════════════════════════════


def train_stacking_ensemble(
    X: np.ndarray,
    y: list[int | str | None],
    model_name: str,
    target_name: str,
    n_classes: int = 2,
    imputer: Any = None,
) -> dict | None:
    """Train a 2-layer stacking ensemble with temporal cross-validation.

    Layer 1 trains XGBoost, LightGBM, and Logistic Regression.
    Layer 2 trains a meta-learner on the stacked out-of-fold predictions
    from Layer 1, augmented with confidence features.

    Args:
        X: Feature matrix (all samples).
        y: Target labels (may contain None entries).
        model_name: Identifier for the ensemble.
        target_name: Name of the target column.
        n_classes: Number of classes.
        imputer: Fitted imputer to bundle with the model.

    Returns:
        A dict ready to upsert into ``ml_models``, or ``None``
        when there are fewer than 50 valid samples.
    """
    logger.info(f"\n  {'─' * 50}")
    logger.info(f"  🏗️ Entraînement STACKING ENSEMBLE : {model_name}")
    logger.info(f"  {'─' * 50}")

    # ── Filtrer les None ─────────────────────────────────────────
    valid = [(x, yi) for x, yi in zip(X, y) if yi is not None]
    if len(valid) < 50:
        logger.warning(f"  ⚠️ Pas assez de données ({len(valid)} < 50). Skipped.")
        return None

    X_valid = np.array([v[0] for v in valid])
    y_valid = np.array([v[1] for v in valid])

    # Encoder les labels si texte (H/D/A)
    le: LabelEncoder | None = None
    if isinstance(y_valid[0], str):
        le = LabelEncoder()
        y_valid = le.fit_transform(y_valid)
        n_classes = len(le.classes_)
        logger.info(f"  Classes : {list(le.classes_)}")

    logger.info(f"  Échantillons : {len(y_valid)}")
    logger.info(f"  Distribution : {dict(zip(*np.unique(y_valid, return_counts=True)))}")

    # ── Split temporel ───────────────────────────────────────────
    tscv = TimeSeriesSplit(n_splits=5)
    split_indices = list(tscv.split(X_valid))
    train_idx, test_idx = split_indices[-1]
    X_train, X_test = X_valid[train_idx], X_valid[test_idx]
    y_train, y_test = y_valid[train_idx], y_valid[test_idx]

    logger.info(f"  TimeSeriesSplit : train={len(X_train)}, test={len(X_test)}")

    # ── Couche 1 : Base Learners ─────────────────────────────────
    base_models = _build_base_learners(n_classes)
    oof_probas = _generate_oof_predictions(base_models, X_train, y_train, n_classes)

    # Entraîner les base learners sur tout le train set
    fitted_base = {}
    for name, model in base_models.items():
        if name == "logreg":
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_train)
            model.fit(X_scaled, y_train)
            fitted_base[name] = {"model": model, "scaler": scaler}
        else:
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
            fitted_base[name] = {"model": model}

    # ── Couche 2 : Meta-Learner ──────────────────────────────────
    meta_features_train = _build_meta_features(oof_probas, n_classes)
    meta_model = LogisticRegression(
        max_iter=1000,
        C=1.0,
        solver="lbfgs",
        multi_class="multinomial" if n_classes > 2 else "auto",
    )
    meta_model.fit(meta_features_train, y_train)
    logger.info(f"  Meta-learner entraîné sur {meta_features_train.shape[1]} meta-features")

    # ── Évaluation sur le test set ───────────────────────────────
    test_probas = _predict_base_probas(fitted_base, X_test, n_classes)
    meta_features_test = _build_meta_features(test_probas, n_classes)
    y_pred_meta = meta_model.predict(meta_features_test)
    y_proba_meta = meta_model.predict_proba(meta_features_test)

    acc = accuracy_score(y_test, y_pred_meta)
    f1 = f1_score(y_test, y_pred_meta, average="weighted")
    ll = log_loss(y_test, y_proba_meta)

    brier: float | None = None
    if n_classes == 2:
        brier = brier_score_loss(y_test, y_proba_meta[:, 1])

    logger.info(f"  📊 Ensemble Test Accuracy : {acc:.4f}")
    logger.info(f"  📊 Ensemble Test F1       : {f1:.4f}")
    if brier is not None:
        logger.info(f"  📊 Ensemble Test Brier    : {brier:.4f}")
    logger.info(f"  📊 Ensemble Test Log Loss : {ll:.4f}")

    # Comparer avec chaque base learner individuel
    for name, item in fitted_base.items():
        model = item["model"]
        if name == "logreg":
            X_eval = item["scaler"].transform(X_test)
        else:
            X_eval = X_test
        y_pred_base = model.predict(X_eval)
        base_acc = accuracy_score(y_test, y_pred_base)
        logger.info(f"    vs {name:10s} seul : {base_acc:.4f}")

    # ── Sérialiser ───────────────────────────────────────────────
    payload: dict[str, Any] = {
        "base_models": fitted_base,
        "meta_model": meta_model,
        "label_encoder": le,
        "imputer": imputer,
        "n_classes": n_classes,
        "model_type": "stacking_ensemble",
    }
    model_b64 = base64.b64encode(pickle.dumps(payload)).decode("utf-8")

    result: dict = {
        "model_name": model_name,
        "model_type": "stacking_ensemble",
        "target": target_name,
        "accuracy": round(float(acc), 4),
        "f1_score": round(float(f1), 4),
        "brier_score": round(float(brier), 4) if brier is not None else None,
        "log_loss_val": round(float(ll), 4),
        "feature_importance": {},
        "model_params": {"architecture": "xgboost+lightgbm+logreg→meta_logreg"},
        "model_weights": model_b64,
        "training_samples": len(y_valid),
        "feature_names": FEATURE_COLS,
        "is_active": True,
    }

    return result


def _build_base_learners(n_classes: int) -> dict:
    """Create the three base learner instances."""
    xgb_params: dict = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "eval_metric": "mlogloss" if n_classes > 2 else "logloss",
        "use_label_encoder": False,
    }
    if n_classes > 2:
        xgb_params["objective"] = "multi:softprob"
        xgb_params["num_class"] = n_classes
    else:
        xgb_params["objective"] = "binary:logistic"

    lgb_params: dict = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "verbose": -1,
    }
    if n_classes > 2:
        lgb_params["objective"] = "multiclass"
        lgb_params["num_class"] = n_classes
    else:
        lgb_params["objective"] = "binary"

    logreg = LogisticRegression(
        max_iter=1000,
        C=0.5,
        solver="lbfgs",
        multi_class="multinomial" if n_classes > 2 else "auto",
        random_state=42,
    )

    return {
        "xgboost": xgb.XGBClassifier(**xgb_params),
        "lightgbm": lgb.LGBMClassifier(**lgb_params),
        "logreg": logreg,
    }


def _generate_oof_predictions(
    base_models: dict,
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
) -> dict[str, np.ndarray]:
    """Generate out-of-fold predictions for each base learner.

    Uses TimeSeriesSplit to avoid look-ahead bias. Each sample in the
    training set gets a prediction from a model that never saw it.
    """
    tscv = TimeSeriesSplit(n_splits=5)
    oof: dict[str, np.ndarray] = {}

    for name, model_template in base_models.items():
        oof_probas = np.zeros((len(X_train), n_classes))

        for fold_train, fold_val in tscv.split(X_train):
            X_fold_train = X_train[fold_train]
            y_fold_train = y_train[fold_train]
            X_fold_val = X_train[fold_val]

            # Clone the model for this fold
            if name == "xgboost":
                fold_model = xgb.XGBClassifier(**model_template.get_params())
            elif name == "lightgbm":
                fold_model = lgb.LGBMClassifier(**model_template.get_params())
            else:
                fold_model = LogisticRegression(**model_template.get_params())

            if name == "logreg":
                scaler = StandardScaler()
                X_fold_train_s = scaler.fit_transform(X_fold_train)
                X_fold_val_s = scaler.transform(X_fold_val)
                fold_model.fit(X_fold_train_s, y_fold_train)
                oof_probas[fold_val] = fold_model.predict_proba(X_fold_val_s)
            else:
                fold_model.fit(X_fold_train, y_fold_train, verbose=False)
                oof_probas[fold_val] = fold_model.predict_proba(X_fold_val)

        oof[name] = oof_probas
        logger.info(f"    OOF {name} : shape {oof_probas.shape}")

    return oof


def _build_meta_features(
    probas: dict[str, np.ndarray],
    n_classes: int,
) -> np.ndarray:
    """Build meta-feature matrix from base learner probability outputs.

    Includes:
      - Raw probabilities from each base learner
      - Confidence features: max_prob, convergence (std of predictions),
        entropy of the average prediction
    """
    # Stack all base probabilities
    all_probas = []
    for name in sorted(probas.keys()):
        all_probas.append(probas[name])

    # Raw probas: (n_samples, n_models * n_classes)
    stacked = np.hstack(all_probas)

    # Confidence features
    n_models = len(probas)
    n_samples = stacked.shape[0]
    avg_probas = np.zeros((n_samples, n_classes))
    for p in all_probas:
        avg_probas += p
    avg_probas /= n_models

    # Max probability (higher = more confident)
    max_prob = avg_probas.max(axis=1, keepdims=True)

    # Convergence: how much models agree (lower std = more agreement)
    agreement = np.zeros((n_samples, 1))
    for i in range(n_samples):
        class_stds = []
        for c in range(n_classes):
            vals = [probas[name][i, c] for name in probas]
            class_stds.append(np.std(vals))
        agreement[i, 0] = 1.0 - np.mean(class_stds)  # Higher = more agreement

    # Entropy of average prediction
    entropy = np.zeros((n_samples, 1))
    for i in range(n_samples):
        for c in range(n_classes):
            p = avg_probas[i, c]
            if p > 1e-10:
                entropy[i, 0] -= p * math.log(p)

    meta = np.hstack([stacked, max_prob, agreement, entropy])
    return meta


def _predict_base_probas(
    fitted_base: dict,
    X: np.ndarray,
    n_classes: int,
) -> dict[str, np.ndarray]:
    """Get probability predictions from all fitted base models."""
    probas: dict[str, np.ndarray] = {}
    for name in sorted(fitted_base.keys()):
        item = fitted_base[name]
        model = item["model"]
        if name == "logreg":
            X_scaled = item["scaler"].transform(X)
            probas[name] = model.predict_proba(X_scaled)
        else:
            probas[name] = model.predict_proba(X)
    return probas


# ═══════════════════════════════════════════════════════════════════
#  STACKING ENSEMBLE — PREDICTION (runtime)
# ═══════════════════════════════════════════════════════════════════

# Cache for loaded ensemble
_ensemble_cache: dict[str, Any] = {}
_ensemble_loaded: bool = False


def load_ensemble(model_name: str = "ensemble_1x2") -> bool:
    """Load a stacking ensemble from the Supabase ``ml_models`` table.

    Returns:
        ``True`` if the ensemble is loaded and ready.
    """
    global _ensemble_cache, _ensemble_loaded

    if model_name in _ensemble_cache:
        return True

    try:
        rows = (
            supabase.table("ml_models")
            .select("model_name, model_weights, is_active, model_type")
            .eq("model_name", model_name)
            .eq("is_active", True)
            .execute()
            .data
        )

        if not rows:
            return False

        row = rows[0]
        if row.get("model_type") != "stacking_ensemble":
            return False

        weights_b64 = row.get("model_weights")
        if not weights_b64:
            return False

        payload = pickle.loads(base64.b64decode(weights_b64))
        _ensemble_cache[model_name] = payload
        logger.info(f"  🏗️ Ensemble {model_name} chargé")
        return True

    except Exception as e:
        logger.warning(f"  ⚠️ Erreur chargement ensemble {model_name}: {e}")
        return False


def predict_ensemble(
    context: dict,
    model_name: str = "ensemble_1x2",
) -> dict[str, int] | None:
    """Predict using the stacking ensemble.

    Args:
        context: Match context dict with feature values.
        model_name: Key of the ensemble in cache.

    Returns:
        Dict with probability keys (e.g. ``ml_home``, ``ml_draw``,
        ``ml_away``), or ``None`` if the ensemble is not loaded.
    """
    if not load_ensemble(model_name):
        return None

    payload = _ensemble_cache[model_name]
    base_models = payload["base_models"]
    meta_model = payload["meta_model"]
    le = payload.get("label_encoder")
    imputer = payload.get("imputer")
    n_classes = payload.get("n_classes", 3)

    # Build feature vector
    features = []
    for col in FEATURE_COLS:
        val = context.get(col)
        features.append(float(val) if val is not None else np.nan)
    X = np.array([features], dtype=np.float32)

    # Impute
    if imputer:
        try:
            X = imputer.transform(X)
        except Exception:
            X = np.nan_to_num(X, nan=0.0)
    else:
        X = np.nan_to_num(X, nan=0.0)

    # Get base probabilities
    probas = _predict_base_probas(base_models, X, n_classes)

    # Build meta features + predict
    meta_features = _build_meta_features(probas, n_classes)
    final_probas = meta_model.predict_proba(meta_features)[0]

    if le:
        classes = le.classes_
        proba_map = dict(zip(classes, final_probas))
    else:
        if n_classes == 3:
            proba_map = {"H": final_probas[0], "D": final_probas[1], "A": final_probas[2]}
        else:
            proba_map = {1: final_probas[1]}

    # Return format depends on model type
    if n_classes == 3:
        return {
            "ml_home": round(proba_map.get("H", 0.33) * 100),
            "ml_draw": round(proba_map.get("D", 0.33) * 100),
            "ml_away": round(proba_map.get("A", 0.33) * 100),
        }
    else:
        return {"ml_prob": round(float(final_probas[1]) * 100)}


def predict_ensemble_binary(
    context: dict,
    model_name: str,
) -> int | None:
    """Predict a binary outcome using a stacking ensemble.

    Returns:
        Probability of the positive class as an integer (0–100),
        or ``None`` if unavailable.
    """
    result = predict_ensemble(context, model_name)
    if result is None:
        return None
    return result.get("ml_prob")
