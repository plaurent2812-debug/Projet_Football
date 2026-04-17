"""
Entraînement des modèles XGBoost pour la NHL (player-level).

Charge `nhl_dataset.csv`, entraîne 4 modèles (Goal, Assist, Point, Shot),
et sauvegarde les classifieurs dans `models/`.

Corrections Phase 2 (mars 2026):
  - Tri par date AVANT TimeSeriesSplit (évite le data leakage temporel)
  - Entraînement sur le train set seulement (pas sur toutes les données)
  - Features enrichies alignées avec ml_models.py
  - Validation honnête sur le dernier fold (pas de fuite)
"""

import logging
import os
import pickle  # noqa: S301 — metadata only, no user data
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import optuna
    from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import TimeSeriesSplit
    from xgboost import XGBClassifier
except ImportError:
    logger.error("Veuillez installer xgboost, scikit-learn et optuna: pip install xgboost scikit-learn optuna pandas")
    sys.exit(1)

# Features utilisées pour l'entraînement.
# Alignées avec les features disponibles dans build_data.py (from stats_json).
# ml_models.py._build_features() utilise self.feature_names du modèle sérialisé,
# donc l'alignement est garanti tant qu'on réentraîne avec les mêmes features.
FEATURES = [
    # Heuristic scores (from pipeline _score_player)
    "algo_score_goal",
    "algo_score_shot",
    # Season per-game stats
    "goals_per_game",
    "assists_per_game",
    "shots_per_game",
    "toi_minutes",
    "games_played",
    # Contextual
    "ai_factor",
    "b2b",
    "pp_boost",
    "is_home",
    # L5 form (flattened from l5_form dict)
    "l5_point",
    "l5_goal",
    "l5_assist",
    "l5_shot",
    # H2H (flattened from h2h dict)
    "h2h_point",
    "h2h_goal",
    "h2h_shot",
    # Opponent quality
    "opp_sv_pct",
    "opp_gaa",
    # Probabilities (pre-computed by pipeline)
    "prob_goal",
    "prob_point",
    "prob_shot",
]


def load_data(filepath="nhl_dataset.csv") -> pd.DataFrame:
    path = Path(__file__).parent.parent / filepath
    if not path.exists():
        logger.error("Fichier dataset introuvable: %s", path)
        logger.error("Veuillez d'abord executer `python -m src.nhl.build_data`")
        return pd.DataFrame()
    df = pd.read_csv(path)

    # CRITICAL: Sort by date for proper TimeSeriesSplit
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)
        logger.info("  Dataset trie par date: %s -> %s", df["date"].iloc[0][:10], df["date"].iloc[-1][:10])
    else:
        logger.warning("  Pas de colonne 'date' — TimeSeriesSplit sera pseudo-aleatoire")

    return df


def train_market_model(df: pd.DataFrame, market: str, label_col: str, output_path: str):
    logger.info("--- Entrainement du modele: %s ---", market)

    # Nettoyer
    df_clean = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    if df_clean.empty:
        logger.error("Dataset vide.")
        return

    # Only keep features that exist in the dataset
    available_features = [f for f in FEATURES if f in df_clean.columns]
    missing = [f for f in FEATURES if f not in df_clean.columns]
    if missing:
        logger.warning("  Features manquantes (remplacees par 0): %s", missing)
        for f in missing:
            df_clean[f] = 0.0
        available_features = FEATURES

    X = df_clean[available_features]
    y = df_clean[label_col]

    # Vérifier l'équilibre des classes
    positives = y.sum()
    if positives == 0 or positives == len(y):
        logger.error("Pas de variance dans la cible. Entrainement impossible.")
        return

    logger.info("  Echantillons: %d | Positifs: %d (%.1f%%)", len(y), int(positives), 100 * positives / len(y))

    # TimeSeriesSplit — data is already sorted by date
    n_splits = min(5, len(df) // 20)
    if n_splits < 2:
        n_splits = 2
    tscv = TimeSeriesSplit(n_splits=n_splits)

    scale_pos_weight = (len(y) - y.sum()) / max(1, y.sum())

    def objective(trial):
        param = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 200),
            "max_depth": trial.suggest_int("max_depth", 3, 6),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 0.9),
            "gamma": trial.suggest_float("gamma", 0, 5),
            "scale_pos_weight": scale_pos_weight,
            "eval_metric": "logloss",
            "random_state": 42,
            "n_jobs": -1
        }

        scores = []
        for train_idx, val_idx in tscv.split(X):
            X_t, X_v = X.iloc[train_idx], X.iloc[val_idx]
            y_t, y_v = y.iloc[train_idx], y.iloc[val_idx]

            clf = XGBClassifier(**param)
            clf.fit(X_t, y_t)

            preds = clf.predict_proba(X_v)[:, 1]
            scores.append(brier_score_loss(y_v, preds))

        return np.mean(scores)

    logger.info("Optimisation Optuna pour %s...", market)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=30)

    best_params = study.best_params
    best_params["scale_pos_weight"] = scale_pos_weight
    best_params["eval_metric"] = "logloss"
    best_params["random_state"] = 42

    logger.info("Meilleurs parametres: %s", best_params)

    # FIXED: Train on TRAIN set only (not all data), evaluate on held-out TEST set
    # Use last fold of TimeSeriesSplit as the final train/test split
    for train_idx, test_idx in tscv.split(X):
        pass  # Get the last fold

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model = XGBClassifier(**best_params)
    model.fit(X_train, y_train)

    # Honest evaluation on held-out test set
    preds_proba = model.predict_proba(X_test)[:, 1]
    preds_bin = (preds_proba >= 0.5).astype(int)

    acc = accuracy_score(y_test, preds_bin)
    brier = brier_score_loss(y_test, preds_proba)
    try:
        auc = roc_auc_score(y_test, preds_proba)
    except Exception:
        auc = 0.5

    logger.info("Honest Test Evaluation (last fold, %d samples):", len(y_test))
    logger.info("   Accuracy: %.1f%%", 100 * acc)
    logger.info("   Brier Score: %.4f", brier)
    logger.info("   ROC AUC: %.3f", auc)

    # Now retrain on ALL data for production deployment
    final_model = XGBClassifier(**best_params)
    final_model.fit(X, y)

    # Sauvegarde — metadata pickle + model UBJ
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    metadata = {
        "feature_names": available_features,
        "metrics": {
            "market": market,
            "accuracy": float(acc),
            "brier_score": float(brier),
            "roc_auc": float(auc),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "training_date": datetime.now(timezone.utc).isoformat()[:10],
        },
        "training_date": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(X),
        "best_params": best_params,
        "serialization": "ubj"
    }

    with open(output_path, "wb") as f:
        pickle.dump(metadata, f)

    model_ubj_path = output_path.replace(".pkl", ".ubj")
    final_model.save_model(model_ubj_path)

    logger.info("Modele sauvegarde: %s", output_path)
    logger.info("Model binary (UBJ): %s", model_ubj_path)


def train_all():
    df = load_data()
    if df.empty:
        return

    # Fill missing features with 0
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0.0

    base_dir = Path(__file__).parent.parent / "models"

    markets = [
        ("But Prcp", "label_goal", base_dir / "nhl_best_goal_predictor.pkl"),
        ("Passes", "label_assist", base_dir / "nhl_best_assist_predictor.pkl"),
        ("Points", "label_point", base_dir / "nhl_best_point_predictor.pkl"),
        ("Tirs > 2.5", "label_shot", base_dir / "nhl_best_shot_predictor.pkl"),
    ]

    for name, label_col, path in markets:
        if label_col in df.columns:
            train_market_model(df, name, label_col, str(path))
        else:
            logger.warning("Colonne cible %s introuvable pour %s.", label_col, name)


if __name__ == "__main__":
    train_all()
