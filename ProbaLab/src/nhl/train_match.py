"""
train_match.py — Entraînement XGBoost match-level pour la NHL.

Construit un dataset à partir des matchs terminés dans nhl_fixtures,
entraîne 2 modèles (Win Prediction + Over 5.5), et sauvegarde dans models/nhl/.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import optuna
    from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import TimeSeriesSplit
    from xgboost import XGBClassifier
except ImportError:
    import logging as _logging

    _logging.getLogger(__name__).error("Install: pip install xgboost scikit-learn pandas optuna")
    sys.exit(1)

from src.config import logger, supabase

# ═══════════════════════════════════════════════════════════════
#  FEATURES pour le modèle match-level
# ═══════════════════════════════════════════════════════════════

MATCH_FEATURES = [
    "proba_home",  # Proba heuristique Poisson: home win %
    "proba_away",  # Proba heuristique Poisson: away win %
    "proba_over_55",  # Proba heuristique Poisson: Over 5.5 %
    "ai_home_factor",  # Facteur IA Gemini pour home
    "ai_away_factor",  # Facteur IA Gemini pour away
]

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "nhl"


def build_match_dataset() -> pd.DataFrame:
    """Construit le dataset d'entraînement depuis Supabase."""
    logger.info("📊 Construction du dataset NHL match-level...")

    res = (
        supabase.table("nhl_fixtures")
        .select(
            "id, date, home_team, away_team, home_score, away_score, "
            "proba_home, proba_away, proba_over_55, "
            "predictions_json, ai_home_factor, ai_away_factor, status"
        )
        .in_("status", ["Final", "FINAL", "FT", "OFF"])
        .order("date")
        .execute()
    )

    fixtures = res.data or []
    logger.info(f"  {len(fixtures)} matchs terminés trouvés.")

    rows = []
    for fix in fixtures:
        home_score = fix.get("home_score")
        away_score = fix.get("away_score")
        if home_score is None or away_score is None:
            continue

        # Get probas from top-level columns OR predictions_json fallback
        proba_home = fix.get("proba_home")
        proba_away = fix.get("proba_away")
        proba_over_55 = fix.get("proba_over_55")
        ai_home = fix.get("ai_home_factor")
        ai_away = fix.get("ai_away_factor")

        # Fallback to predictions_json
        pj = fix.get("predictions_json")
        if isinstance(pj, str):
            try:
                pj = json.loads(pj) if pj and pj != "{}" else {}
            except Exception:
                pj = {}

        if proba_home is None and pj:
            proba_home = pj.get("proba_home")
        if proba_away is None and pj:
            proba_away = pj.get("proba_away")
        if proba_over_55 is None and pj:
            proba_over_55 = pj.get("proba_over_55")
        if ai_home is None and pj:
            ai_home = pj.get("ai_home_factor")
        if ai_away is None and pj:
            ai_away = pj.get("ai_away_factor")

        # Skip if we don't have enough features
        if proba_home is None or proba_away is None:
            continue

        total_goals = int(home_score) + int(away_score)
        home_win = 1 if int(home_score) > int(away_score) else 0

        rows.append(
            {
                "date": fix.get("date", ""),
                "home_team": fix.get("home_team", ""),
                "away_team": fix.get("away_team", ""),
                # Features
                "proba_home": float(proba_home),
                "proba_away": float(proba_away),
                "proba_over_55": float(proba_over_55 or 50),
                "ai_home_factor": float(ai_home or 1.0),
                "ai_away_factor": float(ai_away or 1.0),
                # Labels
                "label_home_win": home_win,
                "label_over_55": 1 if total_goals > 5 else 0,
                # Metadata
                "total_goals": total_goals,
            }
        )

    df = pd.DataFrame(rows)
    logger.info(f"  ✅ Dataset: {len(df)} échantillons")
    if not df.empty:
        logger.info(
            f"     Home wins: {df['label_home_win'].sum()}/{len(df)} "
            f"({df['label_home_win'].mean():.1%})"
        )
        logger.info(
            f"     Over 5.5: {df['label_over_55'].sum()}/{len(df)} "
            f"({df['label_over_55'].mean():.1%})"
        )
    return df


def train_model(df: pd.DataFrame, target: str, model_name: str) -> dict | None:
    """Entraîne un modèle XGBoost pour un target donné."""
    logger.info(f"\n--- Entraînement: {model_name} (target={target}) ---")

    if df.empty or target not in df.columns:
        logger.error(f"❌ Dataset vide ou target {target} manquant")
        return None

    # Clean
    df_clean = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    X = df_clean[MATCH_FEATURES]
    y = df_clean[target]

    positives = int(y.sum())
    if positives == 0 or positives == len(y):
        logger.error("❌ Pas de variance dans la cible")
        return None

    # Time Series Split (chronological)
    n_splits = min(5, len(df) // 10)
    if n_splits < 2:
        logger.warning("⚠️ Trop peu de données pour cross-validation, entraînement direct")
        n_splits = 2

    tscv = TimeSeriesSplit(n_splits=n_splits)

    scale_pos_weight = (len(y) - positives) / max(1, positives)

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
            "n_jobs": -1,
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

    logger.info(f"🚀 Optimisation Optuna pour {model_name}...")
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=20)

    best_params = study.best_params
    best_params["scale_pos_weight"] = scale_pos_weight
    best_params["eval_metric"] = "logloss"
    best_params["random_state"] = 42

    logger.info(f"✅ Meilleurs paramètres: {best_params}")

    # FIXED: Honest evaluation on held-out last fold (model trained on train only)
    splits = list(tscv.split(X))
    fold = len(splits) - 1
    train_idx, test_idx = splits[-1]

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model = XGBClassifier(**best_params)
    model.fit(X_train, y_train)

    preds = model.predict_proba(X_test)[:, 1]
    brier = brier_score_loss(y_test, preds)
    acc = accuracy_score(y_test, (preds >= 0.5).astype(int))
    try:
        auc = roc_auc_score(y_test, preds)
    except Exception:
        auc = 0.5

    logger.info(
        f"  Honest Test (fold {fold}, {len(y_test)} samples): "
        f"Brier={brier:.4f} Acc={acc:.1%} AUC={auc:.3f}"
    )

    # Retrain on ALL data for production deployment
    final_model = XGBClassifier(**best_params)
    final_model.fit(X, y, verbose=False)

    # Save
    os.makedirs(MODEL_DIR, exist_ok=True)
    output_path = MODEL_DIR / f"nhl_match_{model_name}.pkl"

    metadata = {
        "feature_names": MATCH_FEATURES,
        "metrics": {
            "brier_score": float(brier),
            "accuracy": float(acc),
            "roc_auc": float(auc),
            "n_samples": len(df),
        },
        "training_date": datetime.now(timezone.utc).isoformat(),
        "serialization": "ubj",
    }

    # Save metadata as pickle
    with open(output_path, "wb") as f:
        pickle.dump(metadata, f)

    # Save model binary as UBJ
    model_ubj_path = str(output_path).replace(".pkl", ".ubj")
    final_model.save_model(model_ubj_path)

    # Timestamped snapshot
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    versioned_path = str(output_path).replace(".pkl", f"_{date_tag}.pkl")
    with open(versioned_path, "wb") as f:
        pickle.dump(metadata, f)

    logger.info(f"  💾 Modèle sauvegardé: {output_path}")
    logger.info(f"  📦 Model binary (UBJ): {model_ubj_path}")
    return metadata["metrics"]


def train_nhl_match_models() -> dict:
    """Point d'entrée principal: construit le dataset et entraîne les 2 modèles."""
    logger.info("🏒🧠 NHL Match-Level ML Training")
    logger.info("=" * 50)

    df = build_match_dataset()
    if df.empty or len(df) < 20:
        msg = f"Pas assez de données ({len(df)} matchs). Minimum: 20."
        logger.warning(f"⚠️ {msg}")
        return {"success": False, "message": msg, "n_samples": len(df)}

    results = {}

    # 1. Win Prediction
    win_metrics = train_model(df, "label_home_win", "win")
    if win_metrics:
        results["win"] = win_metrics

    # 2. Over 5.5
    over_metrics = train_model(df, "label_over_55", "over55")
    if over_metrics:
        results["over55"] = over_metrics

    logger.info("\n" + "=" * 50)
    logger.info("🎯 Récapitulatif NHL ML:")
    for name, m in results.items():
        logger.info(
            f"  {name}: Acc={m['accuracy']:.1%} | Brier={m['brier_score']:.4f} | AUC={m['roc_auc']:.3f}"
        )

    return {
        "success": True,
        "models_trained": list(results.keys()),
        "metrics": results,
        "n_samples": len(df),
    }


if __name__ == "__main__":
    train_nhl_match_models()
