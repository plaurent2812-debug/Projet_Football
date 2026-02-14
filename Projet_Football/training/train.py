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
import pickle
import warnings

import numpy as np

warnings.filterwarnings("ignore")

import optuna
import xgboost as xgb
from config import logger, supabase
from constants import FEATURE_COLS
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, log_loss
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import LabelEncoder

# Silence Optuna's verbose output
optuna.logging.set_verbosity(optuna.logging.WARNING)

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


def prepare_features(data: list[dict], feature_cols: list[str]) -> tuple[np.ndarray, SimpleImputer]:
    """Build the feature matrix and fit a median imputer.

    Extracts numerical feature columns from *data*, converts missing values
    to ``np.nan``, then applies median imputation.

    Args:
        data: List of training-data row dicts.
        feature_cols: Ordered list of column names to include.

    Returns:
        A tuple ``(X, imputer)`` where *X* is the imputed feature matrix
        and *imputer* is the fitted ``SimpleImputer``.
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

    # Imputation des valeurs manquantes
    imputer = SimpleImputer(strategy="median")
    X_arr = imputer.fit_transform(X_arr)

    return X_arr, imputer


def prepare_target_classification(data: list[dict], target_field: str) -> list[int | str | None]:
    """Extract classification labels from training data.

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
    n_trials: int = 50,
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
        scores = cross_val_score(
            model, X_train, y_train, cv=tscv, scoring="neg_log_loss"
        )
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

    # Cross-validation temporelle (5 folds)
    cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring="accuracy")
    logger.info(f"  CV Accuracy (temporal) : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Entraînement final
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Évaluation
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

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

    # Sérialiser le modèle
    model_bytes = pickle.dumps({"model": model, "imputer": None, "label_encoder": le})
    model_b64 = base64.b64encode(model_bytes).decode("utf-8")

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
        "model_params": params,
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

    logger.info(f"  TimeSeriesSplit : train={len(X_train)}, test={len(X_test)}")

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

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

    model_bytes = pickle.dumps({"model": model, "imputer": None})
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

    # Préparer les features
    X, imputer = prepare_features(data, FEATURE_COLS)
    logger.info(f"  Features : {X.shape[1]} colonnes, {X.shape[0]} lignes")
    logger.info(f"  NaN restants : {np.isnan(X).sum()}")

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
    from models.ensemble import train_stacking_ensemble

    logger.info(f"\n{'=' * 60}")
    logger.info("  🏗️ STACKING ENSEMBLES")
    logger.info(f"{'=' * 60}")

    result_ens_1x2 = train_stacking_ensemble(
        X, y_1x2, "ensemble_1x2", "result", n_classes=3, imputer=imputer
    )
    result_ens_btts = train_stacking_ensemble(
        X, y_btts, "ensemble_btts", "btts", n_classes=2, imputer=imputer
    )
    result_ens_o25 = train_stacking_ensemble(
        X, y_o25, "ensemble_over25", "over_25", n_classes=2, imputer=imputer
    )

    # ── Sauvegarder les modèles ───────────────────────────────────
    logger.info(f"\n{'=' * 60}")
    logger.info("  💾 SAUVEGARDE DES MODÈLES")
    logger.info(f"{'=' * 60}")

    # Sauvegarder aussi l'imputer
    base64.b64encode(pickle.dumps(imputer)).decode("utf-8")

    all_results = [
        result_1x2, result_btts, result_o25, result_o15, result_o05, result_goals,
        result_ens_1x2, result_ens_btts, result_ens_o25,
    ]

    for result in all_results:
        if result is None:
            continue
        try:
            # Ajouter l'imputer aux weights
            model_data = pickle.loads(base64.b64decode(result["model_weights"]))
            model_data["imputer"] = imputer
            result["model_weights"] = base64.b64encode(pickle.dumps(model_data)).decode("utf-8")

            supabase.table("ml_models").upsert(result, on_conflict="model_name").execute()
            logger.info(
                f"  ✅ {result['model_name']} sauvegardé (acc={result['accuracy']}, n={result['training_samples']})"
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
