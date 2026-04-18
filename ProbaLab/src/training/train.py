from __future__ import annotations

"""
train_model.py — Entraînement de modèles ML pour la prédiction football.

Modèles entraînés :
  1. XGBoost Classifier : Résultat 1X2 (H/D/A)
  2. XGBoost Classifier : BTTS (Oui/Non)
  3. XGBoost Classifier : Over 2.5 (Oui/Non)
  4. XGBoost Classifier : Over 1.5 (Oui/Non)
  5. XGBoost Regressor  : Total de buts (pour affiner les probas)
  6. Stacking Ensemble  : 1X2 (XGBoost + LightGBM + LogReg → Meta)
  7. Stacking Ensemble  : BTTS
  8. Stacking Ensemble  : Over 2.5

Workflow :
  1. Charge les données de training_data
  2. Prépare les features (imputation, normalisation)
  3. Split train/test (80/20, stratifié)
  4. Entraîne avec cross-validation
  5. Évalue sur le test set
  6. Sauvegarde le modèle + métriques dans ml_models
"""
import base64
import io
import pickle
import warnings
from typing import Any

import numpy as np
import optuna
import xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, log_loss
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from src.config import logger, supabase
from src.constants import FEATURE_COLS
from src.training.variants import get_variant


def get_feature_cols_for_variant(variant_name: str = "baseline") -> list[str]:
    """Retourne FEATURE_COLS pour la variante demandée.

    Args:
        variant_name: "baseline" | "rebalanced" | "pure" | "pure_rebalanced"

    Utilisé par backtest_variants.py pour entraîner les 4 variantes en parallèle.
    Le train.py en prod continue d'utiliser FEATURE_COLS directement pour compat.
    """
    return list(get_variant(variant_name).feature_cols)


# Silence Optuna's verbose output
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ── Safe Deserialization ──────────────────────────────────────────
# Tight whitelist: only the sklearn sub-modules actually used by trained models.
# Avoids allowing arbitrary code hidden under any "sklearn.*" namespace.
_ALLOWED_PREFIXES = (
    "sklearn.ensemble.",
    "sklearn.linear_model.",
    "sklearn.preprocessing.",
    "sklearn.calibration.",
    "sklearn.isotonic",  # IsotonicRegression used for probability calibration
    "sklearn.pipeline.",
    "sklearn.impute.",
    "sklearn.tree.",  # used by ensemble internals
    "sklearn.utils.",  # _bunch, Tags, etc. used by sklearn internals
    "sklearn.base.",  # BaseEstimator and mixin classes
    "numpy.",
    "numpy",  # catches bare "numpy" module for ndarray/dtype
    "xgboost.",
    "lightgbm.",
    "_codecs",
    "builtins",
    "collections",
    "copyreg",
)


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        if any(module.startswith(p) for p in _ALLOWED_PREFIXES):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Blocked: {module}.{name}")


def _safe_loads(data: bytes) -> Any:
    return _RestrictedUnpickler(io.BytesIO(data)).load()


# ═══════════════════════════════════════════════════════════════════
#  CHARGEMENT ET PRÉPARATION DES DONNÉES
# ═══════════════════════════════════════════════════════════════════


def load_data() -> list[dict] | None:
    """Load all training data from Supabase with pagination.

    Fetches rows from the ``training_data`` table in pages of 1 000 until
    all rows have been retrieved.

    Returns:
        A list of row dicts when data exists, or ``None`` if the table is
        empty.
    """
    all_data: list[dict] = []
    offset: int = 0
    PAGE: int = 1000  # Supabase max rows per request
    while True:
        page = (
            supabase.table("training_data")
            .select("*")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        if not page:
            break
        all_data.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    if not all_data:
        return None
    logger.info(f"  📦 {len(all_data)} exemples chargés")
    return all_data


def prepare_features(
    data: list[dict],
    feature_cols: list[str],
    imputer: SimpleImputer | None = None,
) -> tuple[np.ndarray, SimpleImputer]:
    """Build the feature matrix, optionally applying an existing imputer.

    Extracts numerical feature columns from *data*, converts missing values
    to ``np.nan``.  If *imputer* is provided it is used to transform only
    (no fitting).  Otherwise a new ``SimpleImputer`` is **created but NOT
    fitted** — the caller is responsible for fitting it on the training
    split to avoid data leakage.

    Args:
        data: List of training-data row dicts.
        feature_cols: Ordered list of column names to include.
        imputer: An already-fitted ``SimpleImputer`` to apply.  When
            ``None`` (default) a fresh unfitted imputer is returned.

    Returns:
        A tuple ``(X, imputer)`` where *X* is the feature matrix (imputed
        only when *imputer* was provided) and *imputer* is the
        ``SimpleImputer`` instance.
    """
    X: list[list[float]] = []
    for row in data:
        features: list[float] = []
        for col in feature_cols:
            val = row.get(col)
            if val is None:
                features.append(np.nan)
            else:
                features.append(float(val))
        X.append(features)

    X_arr = np.array(X, dtype=np.float32)

    if imputer is not None:
        # Apply existing imputer (inference / transform-only path)
        X_arr = imputer.transform(X_arr)
    else:
        # Training path: return unfitted imputer — caller fits on train split
        imputer = SimpleImputer(strategy="median")

    return X_arr, imputer


def prepare_target_classification(data: list[dict], target_field: str) -> list[int | str | None]:
    """Extract classification labels from src.training data.

    Booleans are mapped to ``1`` / ``0``; other values are kept as-is.

    Args:
        data: List of training-data row dicts.
        target_field: Column name that holds the target label.

    Returns:
        A list of label values (``int``, ``str``, or ``None``).
    """
    y: list[int | str | None] = []
    for row in data:
        val = row.get(target_field)
        if val is None:
            y.append(None)
        elif isinstance(val, bool):
            y.append(1 if val else 0)
        else:
            y.append(val)
    return y


# ═════════════════════════════════════════════════════════════════
#  OPTUNA HYPERPARAMETER TUNING
# ═════════════════════════════════════════════════════════════════


def _optuna_xgb_params(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
    n_trials: int = 20,
) -> dict:
    """Find optimal XGBoost hyperparameters via Bayesian optimization.

    Uses Optuna with temporal cross-validation to explore the hyperparameter
    space. The objective minimizes log-loss on the validation folds.

    Args:
        X_train: Training feature matrix.
        y_train: Training labels (encoded as integers).
        n_classes: Number of target classes.
        n_trials: Number of Optuna trials to run.

    Returns:
        A dict of optimized XGBoost parameters.
    """
    tscv = TimeSeriesSplit(n_splits=3)

    def objective(trial: optuna.Trial) -> float:
        params: dict = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
            "gamma": trial.suggest_float("gamma", 0, 5),
            "random_state": 42,
            "eval_metric": "mlogloss" if n_classes > 2 else "logloss",
            "use_label_encoder": False,
        }

        if n_classes > 2:
            params["objective"] = "multi:softprob"
            params["num_class"] = n_classes
        else:
            params["objective"] = "binary:logistic"

        model = xgb.XGBClassifier(**params)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
            warnings.filterwarnings("ignore", category=FutureWarning)
            scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring="neg_log_loss")
        return -scores.mean()  # Minimize log_loss

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_params
    best["random_state"] = 42
    best["eval_metric"] = "mlogloss" if n_classes > 2 else "logloss"
    best["use_label_encoder"] = False
    if n_classes > 2:
        best["objective"] = "multi:softprob"
        best["num_class"] = n_classes
    else:
        best["objective"] = "binary:logistic"

    logger.info(f"  🎯 Optuna best trial #{study.best_trial.number} — loss={study.best_value:.4f}")
    logger.info(f"     {best}")
    return best


# ═══════════════════════════════════════════════════════════════════
#  ENTRAÎNEMENT
# ═══════════════════════════════════════════════════════════════════


def train_classifier(
    X: np.ndarray,
    y: list[int | str | None],
    model_name: str,
    target_name: str,
    n_classes: int = 2,
) -> dict | None:
    """Train an XGBoost classifier with cross-validation.

    Filters out ``None`` labels, optionally encodes string classes, then
    performs a 5-fold CV followed by a final fit on an 80/20 split.

    Args:
        X: Feature matrix (all samples, including those with ``None`` labels).
        y: Target labels — may contain ``None`` entries to be filtered.
        model_name: Identifier stored alongside the model artefact.
        target_name: Name of the target column for logging / metadata.
        n_classes: Expected number of classes (overridden when a
            ``LabelEncoder`` is used).

    Returns:
        A dict ready to upsert into ``ml_models``, or ``None`` when
        there are fewer than 50 valid samples.
    """
    logger.info(f"\n  {'─' * 50}")
    logger.info(f"  🤖 Entraînement : {model_name} (target: {target_name})")
    logger.info(f"  {'─' * 50}")

    # Filtrer les None
    valid = [(x, yi) for x, yi in zip(X, y) if yi is not None]
    if len(valid) < 50:
        logger.warning(f"  ⚠️ Pas assez de données ({len(valid)} < 50 minimum). Skipped.")
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

    # Split train/test — Backtesting temporel (données triées par date)
    # TimeSeriesSplit respecte l'ordre chronologique pour éviter le look-ahead bias
    tscv = TimeSeriesSplit(n_splits=5)
    split_indices = list(tscv.split(X_valid))
    # Utiliser le dernier split (le plus grand set d'entraînement)
    train_idx, test_idx = split_indices[-1]
    X_train, X_test = X_valid[train_idx], X_valid[test_idx]
    y_train, y_test = y_valid[train_idx], y_valid[test_idx]

    # Fit imputer on train split ONLY to prevent data leakage
    fold_imputer = SimpleImputer(strategy="median")
    X_train = fold_imputer.fit_transform(X_train)
    X_test = fold_imputer.transform(X_test)

    logger.info(f"  TimeSeriesSplit : train={len(X_train)}, test={len(X_test)}")

    # Hyperparamètres XGBoost — Optuna ou fallback
    try:
        logger.info("  🔍 Optuna tuning (50 trials)...")
        params = _optuna_xgb_params(X_train, y_train, n_classes, n_trials=50)
    except Exception as e:
        logger.warning(f"  ⚠️ Optuna failed ({e}), using defaults")
        params = {
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
            params["objective"] = "multi:softprob"
            params["num_class"] = n_classes
        else:
            params["objective"] = "binary:logistic"

    model = xgb.XGBClassifier(**params)

    # Pondération des classes pour corriger le déséquilibre naturel
    # 1X2 : ~40% Home / ~25% Draw / ~35% Away → sans correction, le modèle sur-prédit Home
    sample_weight_train = compute_sample_weight(class_weight="balanced", y=y_train)

    # Cross-validation temporelle (5 folds) — with balanced sample weights
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
        warnings.filterwarnings("ignore", category=FutureWarning)
        cv_scores = cross_val_score(
            model,
            X_train,
            y_train,
            cv=tscv,
            scoring="accuracy",
            fit_params={"sample_weight": sample_weight_train},
        )
    logger.info(
        f"  CV Accuracy (temporal, balanced) : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}"
    )
    logger.info(f"  CV Folds : {[round(s, 4) for s in cv_scores.tolist()]}")

    # ── Split train into fit + calibration sets ─────────────────
    # Reserve 20% of training data for post-training probability calibration.
    # Isotonic regression per class corrects XGBoost's overconfident softmax.
    cal_size = max(len(X_train) // 5, 30)
    X_train_fit, X_cal = X_train[:-cal_size], X_train[-cal_size:]
    y_train_fit, y_cal = y_train[:-cal_size], y_train[-cal_size:]
    weight_fit = sample_weight_train[:-cal_size]

    logger.info(
        f"  Split calibration : fit={len(X_train_fit)}, cal={len(X_cal)}, test={len(X_test)}"
    )

    # Validation split from training set (separate from test set)
    # Used for early stopping — never touches the holdout test set
    # Temporal slice to preserve time-series ordering
    val_size = max(int(len(X_train_fit) * 0.15), 20)
    X_train_early = X_train_fit[:-val_size]
    X_val = X_train_fit[-val_size:]
    y_train_early = y_train_fit[:-val_size]
    y_val = y_train_fit[-val_size:]
    weight_early = weight_fit[:-val_size]

    # Entraînement final
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
        warnings.filterwarnings("ignore", category=FutureWarning)
        model.fit(
            X_train_early,
            y_train_early,
            sample_weight=weight_early,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

    # ── Post-training probability calibration ─────────────────
    # Fit IsotonicRegression per class on the calibration set to correct
    # XGBoost's probability outputs. This is critical for Brier score.
    calibrators: list[IsotonicRegression] | None = None
    try:
        y_proba_cal = model.predict_proba(X_cal)
        calibrators = []
        for k in range(n_classes):
            ir = IsotonicRegression(out_of_bounds="clip")
            y_binary = (y_cal == k).astype(float)
            ir.fit(y_proba_cal[:, k], y_binary)
            calibrators.append(ir)
        logger.info(
            f"  🎯 Isotonic calibration fitted on {len(X_cal)} samples ({n_classes} classes)"
        )
    except Exception as e:
        logger.warning(f"  ⚠️ Calibration step failed: {e}")
        calibrators = None

    # Évaluation — apply calibration if available
    y_proba_raw = model.predict_proba(X_test)

    if calibrators:
        # Apply isotonic calibration to test probabilities
        y_proba_calibrated = np.column_stack(
            [calibrators[k].predict(y_proba_raw[:, k]) for k in range(n_classes)]
        )
        # Renormalize rows to sum to 1.0
        row_sums = y_proba_calibrated.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1.0)
        y_proba = y_proba_calibrated / row_sums

        ll_raw = log_loss(y_test, y_proba_raw)
        ll_cal = log_loss(y_test, y_proba)
        logger.info(f"  Log Loss raw:        {ll_raw:.4f}")
        logger.info(f"  Log Loss calibrated: {ll_cal:.4f}")
        if ll_cal >= ll_raw:
            logger.warning("  ⚠️ Calibration degraded log loss — discarding calibrators")
            y_proba = y_proba_raw
            calibrators = None
        else:
            logger.info("  ✅ Calibration improved probabilities")
    else:
        y_proba = y_proba_raw

    y_pred = np.argmax(y_proba, axis=1)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    # Brier score (pour binaire)
    brier: float | None = None
    if n_classes == 2:
        brier = brier_score_loss(y_test, y_proba[:, 1])

    ll = log_loss(y_test, y_proba)

    logger.info(f"  Test Accuracy : {acc:.4f}")
    logger.info(f"  Test F1       : {f1:.4f}")
    if brier is not None:
        logger.info(f"  Test Brier    : {brier:.4f}")
    logger.info(f"  Test Log Loss : {ll:.4f}")

    # Feature importance
    importance = model.feature_importances_
    feat_imp: dict[str, float] = {}
    for fname, imp in sorted(zip(FEATURE_COLS, importance), key=lambda x: -x[1]):
        feat_imp[fname] = round(float(imp), 4)
        if imp > 0.03:
            logger.info(f"    {fname:35s} {imp:.4f}")

    # Sérialiser le modèle — XGBoost via save_raw(), sklearn via pickle
    # Note: pickle used here for sklearn model serialization (internal, trusted models only)
    payload = {
        "xgb_model_bytes": base64.b64encode(model.get_booster().save_raw("ubj")).decode("utf-8"),
        "xgb_model_format": "ubj",
        "imputer": None,
        "label_encoder": le,
        "calibrators": calibrators,  # IsotonicRegression per class (or None)
    }
    model_bytes = pickle.dumps(payload)
    model_b64 = base64.b64encode(model_bytes).decode("utf-8")

    # Enrichir model_params avec les scores CV par fold
    params_with_cv = {
        **params,
        "cv_fold_scores": cv_scores.tolist(),
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
    }

    # Sauvegarder
    result: dict = {
        "model_name": model_name,
        "model_type": "xgboost",
        "target": target_name,
        "accuracy": round(float(acc), 4),
        "f1_score": round(float(f1), 4),
        "brier_score": round(float(brier), 4) if brier is not None else None,
        "log_loss_val": round(float(ll), 4),
        "feature_importance": feat_imp,
        "model_params": params_with_cv,
        "model_weights": model_b64,
        "training_samples": len(y_valid),
        "feature_names": FEATURE_COLS,
        "is_active": True,
    }

    return result


def train_regressor(
    X: np.ndarray,
    y_data: list[dict],
    model_name: str,
    target_name: str,
) -> dict | None:
    """Train an XGBoost regressor for total-goals prediction.

    Args:
        X: Feature matrix (all samples).
        y_data: Raw row dicts — the ``"total_goals"`` key is used as
            the regression target.
        model_name: Identifier stored alongside the model artefact.
        target_name: Name of the target column for logging / metadata.

    Returns:
        A dict ready to upsert into ``ml_models``, or ``None`` when
        there are fewer than 50 valid samples.
    """
    logger.info(f"\n  {'─' * 50}")
    logger.info(f"  🤖 Entraînement : {model_name} (target: {target_name})")
    logger.info(f"  {'─' * 50}")

    y = [row.get("total_goals") for row in y_data]
    valid = [(x, yi) for x, yi in zip(X, y) if yi is not None]
    if len(valid) < 50:
        logger.warning("  ⚠️ Pas assez de données. Skipped.")
        return None

    X_valid = np.array([v[0] for v in valid])
    y_valid = np.array([v[1] for v in valid], dtype=np.float32)

    # Backtesting temporel
    tscv = TimeSeriesSplit(n_splits=5)
    split_indices = list(tscv.split(X_valid))
    train_idx, test_idx = split_indices[-1]
    X_train, X_test = X_valid[train_idx], X_valid[test_idx]
    y_train, y_test = y_valid[train_idx], y_valid[test_idx]

    # Fit imputer on train split ONLY to prevent data leakage
    fold_imputer = SimpleImputer(strategy="median")
    X_train = fold_imputer.fit_transform(X_train)
    X_test = fold_imputer.transform(X_test)

    logger.info(f"  TimeSeriesSplit : train={len(X_train)}, test={len(X_test)}")

    # Validation split from training set (separate from test set)
    # Used for early stopping — never touches the holdout test set
    # Temporal slice to preserve time-series ordering
    val_size_reg = max(int(len(X_train) * 0.15), 20)
    X_train_reg = X_train[:-val_size_reg]
    X_val_reg = X_train[-val_size_reg:]
    y_train_reg = y_train[:-val_size_reg]
    y_val_reg = y_train[-val_size_reg:]

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
        warnings.filterwarnings("ignore", category=FutureWarning)
        model.fit(X_train_reg, y_train_reg, eval_set=[(X_val_reg, y_val_reg)], verbose=False)

    y_pred = model.predict(X_test)
    mae: float = float(np.mean(np.abs(y_pred - y_test)))
    rmse: float = float(np.sqrt(np.mean((y_pred - y_test) ** 2)))

    logger.info(f"  Test MAE  : {mae:.3f} buts")
    logger.info(f"  Test RMSE : {rmse:.3f} buts")
    logger.info(f"  Moyenne réelle : {y_test.mean():.2f} | Prédite : {y_pred.mean():.2f}")

    importance = model.feature_importances_
    feat_imp: dict[str, float] = {}
    for fname, imp in sorted(zip(FEATURE_COLS, importance), key=lambda x: -x[1]):
        feat_imp[fname] = round(float(imp), 4)

    payload = {
        "xgb_model_bytes": base64.b64encode(model.get_booster().save_raw("ubj")).decode("utf-8"),
        "xgb_model_format": "ubj",
        "imputer": None,
        "label_encoder": None,
    }
    model_bytes = pickle.dumps(payload)
    model_b64 = base64.b64encode(model_bytes).decode("utf-8")

    return {
        "model_name": model_name,
        "model_type": "xgboost_regressor",
        "target": target_name,
        "accuracy": round(float(1.0 - mae / max(float(y_test.mean()), 1)), 4),
        "f1_score": None,
        "brier_score": round(float(rmse), 4),
        "log_loss_val": round(float(mae), 4),
        "feature_importance": feat_imp,
        "model_params": {"mae": round(float(mae), 4), "rmse": round(float(rmse), 4)},
        "model_weights": model_b64,
        "training_samples": int(len(y_valid)),
        "feature_names": FEATURE_COLS,
        "is_active": True,
    }


def _optuna_lgb_params(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
    n_trials: int = 20,
) -> dict:
    """Find optimal LightGBM hyperparameters via Bayesian optimization."""
    import lightgbm as lgb

    tscv = TimeSeriesSplit(n_splits=3)

    def objective(trial: optuna.Trial) -> float:
        params: dict = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
            "random_state": 42,
            "verbose": -1,
        }

        if n_classes > 2:
            params["objective"] = "multiclass"
            params["num_class"] = n_classes
        else:
            params["objective"] = "binary"

        model = lgb.LGBMClassifier(**params)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
            warnings.filterwarnings("ignore", category=UserWarning, module="lightgbm")
            warnings.filterwarnings("ignore", category=FutureWarning)
            scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring="neg_log_loss")
        return -scores.mean()

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_params
    best["random_state"] = 42
    best["verbose"] = -1
    if n_classes > 2:
        best["objective"] = "multiclass"
        best["num_class"] = n_classes
    else:
        best["objective"] = "binary"

    return best


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════


def run() -> None:
    """Execute the full ML training pipeline.

    Loads training data, prepares features, trains all classifiers
    (1X2, BTTS, Over 2.5, Over 1.5, Over 0.5) and one regressor
    (total goals), then persists models and metrics to Supabase.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  🧠 ENTRAÎNEMENT DES MODÈLES ML")
    logger.info("=" * 60)

    data = load_data()
    if not data:
        logger.error("\n  ❌ Aucune donnée dans training_data.")
        logger.info(
            "  Lance d'abord : python fetch_training_history.py && python build_training_data.py"
        )
        return

    # Préparer les features (X still contains NaN — imputation happens after split)
    X, imputer = prepare_features(data, FEATURE_COLS)
    logger.info(f"  Features : {X.shape[1]} colonnes, {X.shape[0]} lignes")
    logger.info(f"  NaN avant imputation : {np.isnan(X).sum()}")

    # Fit a global imputer on ALL data for inference-time use (saved with models).
    # Training uses per-fold imputers to avoid leakage — this one is only for serving.
    imputer.fit(X)
    logger.info(f"  Imputer global fit pour inférence (médiane sur {X.shape[0]} lignes)")

    # ── 1. Résultat 1X2 ──────────────────────────────────────────
    y_1x2 = prepare_target_classification(data, "result")
    result_1x2 = train_classifier(X, y_1x2, "xgb_1x2", "result", n_classes=3)

    # ── 2. BTTS ──────────────────────────────────────────────────
    y_btts = prepare_target_classification(data, "btts")
    result_btts = train_classifier(X, y_btts, "xgb_btts", "btts", n_classes=2)

    # ── 3. Over 2.5 ──────────────────────────────────────────────
    y_o25 = prepare_target_classification(data, "over_25")
    result_o25 = train_classifier(X, y_o25, "xgb_over25", "over_25", n_classes=2)

    # ── 4. Over 1.5 ──────────────────────────────────────────────
    y_o15 = prepare_target_classification(data, "over_15")
    result_o15 = train_classifier(X, y_o15, "xgb_over15", "over_15", n_classes=2)

    # ── 5. Over 0.5 ──────────────────────────────────────────────
    y_o05 = prepare_target_classification(data, "over_05")
    result_o05 = train_classifier(X, y_o05, "xgb_over05", "over_05", n_classes=2)

    # ── 6. Total buts (régression) ────────────────────────────────
    result_goals = train_regressor(X, data, "xgb_total_goals", "total_goals")

    # ── 7-9. Stacking Ensembles ──────────────────────────────────
    from src.models.ensemble import train_stacking_ensemble

    logger.info(f"\n{'=' * 60}")
    logger.info("  🏗️ STACKING ENSEMBLES")
    logger.info(f"{'=' * 60}")

    # Tune LightGBM for the 1X2 ensemble
    try:
        logger.info("  🔍 LightGBM tuning for 1X2...")
        lgb_tuned_1x2 = _optuna_lgb_params(X, y_1x2, n_classes=3)
    except Exception:
        lgb_tuned_1x2 = None

    result_ens_1x2 = train_stacking_ensemble(
        X,
        y_1x2,
        "ensemble_1x2",
        "result",
        n_classes=3,
        imputer=imputer,
        lgb_tuned_params=lgb_tuned_1x2,
    )

    # Tune LightGBM for the binary ensembles
    try:
        logger.info("  🔍 LightGBM tuning for binary models...")
        lgb_tuned_binary = _optuna_lgb_params(X, y_btts, n_classes=2)
    except Exception:
        lgb_tuned_binary = None

    result_ens_btts = train_stacking_ensemble(
        X,
        y_btts,
        "ensemble_btts",
        "btts",
        n_classes=2,
        imputer=imputer,
        lgb_tuned_params=lgb_tuned_binary,
    )
    result_ens_o25 = train_stacking_ensemble(
        X,
        y_o25,
        "ensemble_over25",
        "over_25",
        n_classes=2,
        imputer=imputer,
        lgb_tuned_params=lgb_tuned_binary,
    )

    # ── Sauvegarder les modèles ───────────────────────────────────
    logger.info(f"\n{'=' * 60}")
    logger.info("  💾 SAUVEGARDE DES MODÈLES")
    logger.info(f"{'=' * 60}")

    # Sauvegarder aussi l'imputer
    base64.b64encode(pickle.dumps(imputer)).decode("utf-8")

    all_results = [
        result_1x2,
        result_btts,
        result_o25,
        result_o15,
        result_o05,
        result_goals,
        result_ens_1x2,
        result_ens_btts,
        result_ens_o25,
    ]

    for result in all_results:
        if result is None:
            continue
        try:
            # Ajouter l'imputer aux weights
            model_data = _safe_loads(base64.b64decode(result["model_weights"]))
            model_data["imputer"] = imputer
            result["model_weights"] = base64.b64encode(pickle.dumps(model_data)).decode("utf-8")

            # ── Auto-promote : ne promouvoir que si le nouveau modèle est meilleur ──
            # IMPORTANT : si le nouveau modèle est moins bon, on skip le upsert
            # pour ne pas écraser le bon modèle actif avec une version dégradée.
            new_brier = result.get("brier_score")
            should_save = True
            if new_brier is not None:
                existing = (
                    supabase.table("ml_models")
                    .select("brier_score")
                    .eq("model_name", result["model_name"])
                    .eq("is_active", True)
                    .execute()
                    .data
                )
                old_brier = existing[0]["brier_score"] if existing else None
                if old_brier is not None and new_brier >= old_brier:
                    should_save = False
                    logger.warning(
                        f"  Model not promoted (skipped): {result['model_name']} — "
                        f"new Brier {new_brier} >= old Brier {old_brier} — modele actif conserve"
                    )
                else:
                    result["is_active"] = True
                    if old_brier is not None:
                        logger.info(
                            f"  Promoted {result['model_name']}: "
                            f"new Brier {new_brier} < old Brier {old_brier}"
                        )

            if should_save:
                supabase.table("ml_models").upsert(result, on_conflict="model_name").execute()
                status = "actif" if result.get("is_active") else "inactif"
                logger.info(
                    f"  {result['model_name']} sauvegarde [{status}] "
                    f"(acc={result['accuracy']}, n={result['training_samples']})"
                )
        except Exception as e:
            logger.error(f"  ❌ Erreur sauvegarde {result['model_name']}: {e}")

    logger.info(f"\n{'=' * 60}")
    logger.info("  ✅ Entraînement terminé !")
    logger.info("  Les modèles sont sauvegardés dans Supabase (table ml_models)")
    logger.info("  Ils seront utilisés automatiquement par stats_engine.py")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    run()
