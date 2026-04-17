import os

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import TimeSeriesSplit

from src.config import logger
from src.models.meta_learner import XGBMetaLearner


def train_meta_model(
    target_name: str,
    num_classes: int,
    dataset_path: str = "meta_dataset.csv",
    model_dir: str = "models/football",
):
    """
    Entraîne le Meta-Modèle XGBoost pour prédire un marché donné.
    Utilise une validation croisée temporelle (Time Series Split).
    """
    logger.info(f"🚀 Démarrage de l'entraînement du Meta-Modèle pour {target_name}...")

    if not os.path.exists(dataset_path):
        logger.error(f"Fichier dataset introuvable: {dataset_path}")
        return None

    df = pd.read_csv(dataset_path)
    if df.empty:
        logger.error("Dataset vide.")
        return None

    # Sélection dynamique des features en fonction du target
    feature_cols = [
        "ai_motivation",
        "ai_media_pressure",
        "ai_injury_impact",
        "ai_cohesion",
        "ai_style_risk",
    ]

    if target_name == "target_1x2":
        feature_cols.extend(["proba_home", "proba_draw", "proba_away"])
        file_name = "meta_1x2_model.ubj"
    elif target_name == "target_btts":
        feature_cols.extend(["proba_btts"])
        file_name = "meta_btts_model.ubj"
    elif target_name == "target_over_15":
        feature_cols.extend(["proba_over_15"])
        file_name = "meta_over_15_model.ubj"
    elif target_name == "target_over_25":
        feature_cols.extend(["proba_over_25"])
        file_name = "meta_over_25_model.ubj"
    else:
        logger.error(f"Target inconnu: {target_name}")
        return None

    if target_name not in df.columns:
        logger.error(f"Colonne target {target_name} absente du dataset.")
        return None

    X = df[feature_cols].copy()
    y = df[target_name].copy()

    # On s'assure qu'il n'y a pas de NaNs dans les probas de base
    X.fillna(0, inplace=True)

    logger.info(
        f"Dataset chargé pour {target_name}: {len(X)} échantillons, {len(feature_cols)} features."
    )

    # Time Series Split
    tscv = TimeSeriesSplit(n_splits=5)

    # Paramètres avec objective multi-class ou binary logistic
    objective = "multi:softprob" if num_classes > 2 else "binary:logistic"
    params = {
        "n_estimators": 150,
        "max_depth": 3,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": objective,
        "eval_metric": "mlogloss" if num_classes > 2 else "logloss",
        "random_state": 42,
    }

    if num_classes > 2:
        params["num_class"] = num_classes

    log_losses = []
    accuracies = []

    for fold, (train_index, test_index) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        model = XGBMetaLearner(params=params)
        model.fit(X_train, y_train)

        y_pred_proba = model.predict(X_test)

        # OOF Log Loss et Accuracy handling
        if num_classes > 2:
            loss = log_loss(y_test, y_pred_proba, labels=[0, 1, 2])
            y_pred_class = np.argmax(y_pred_proba, axis=1)
        else:
            loss = log_loss(y_test, y_pred_proba)
            # y_pred_proba is a 1D array of probabilities for class 1 in binary classification
            y_pred_class = (y_pred_proba >= 0.5).astype(int)

        log_losses.append(loss)
        acc = accuracy_score(y_test, y_pred_class)
        accuracies.append(acc)

        logger.info(
            f"  [{target_name}] Fold {fold + 1}: Log Loss = {loss:.4f}, Accuracy = {acc:.4f}"
        )

    logger.info("=" * 50)
    logger.info(
        f"🔹 [{target_name}] Mean Log Loss: {np.mean(log_losses):.4f} (std: {np.std(log_losses):.4f})"
    )
    logger.info(
        f"🔹 [{target_name}] Mean Accuracy: {np.mean(accuracies):.4f} (std: {np.std(accuracies):.4f})"
    )
    logger.info("=" * 50)

    # Entraînement final sur TOUT le dataset
    logger.info(f"[{target_name}] Entraînement final sur tout le dataset historique...")
    final_model = XGBMetaLearner(params=params)
    final_model.fit(X, y)

    # Sauvegarde du modèle
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, file_name)
    final_model.save_model(model_path)
    logger.info(f"✅ Meta-Modèle pour {target_name} sauvegardé dans {model_path}")

    return {
        "target": target_name,
        "log_loss": round(float(np.mean(log_losses)), 4),
        "accuracy": round(float(np.mean(accuracies)), 4),
        "samples": len(X),
    }


def train_all_meta_models():
    """Entraîne tous les méta-modèles disponibles."""
    results = []

    # 1X2 (3 classes : Away=0, Draw=1, Home=2)
    res_1x2 = train_meta_model("target_1x2", num_classes=3)
    if res_1x2:
        results.append(res_1x2)

    # BTTS (2 classes : No=0, Yes=1)
    res_btts = train_meta_model("target_btts", num_classes=2)
    if res_btts:
        results.append(res_btts)

    # Over 1.5 (2 classes : Under=0, Over=1)
    res_o15 = train_meta_model("target_over_15", num_classes=2)
    if res_o15:
        results.append(res_o15)

    # Over 2.5 (2 classes : Under=0, Over=1)
    res_o25 = train_meta_model("target_over_25", num_classes=2)
    if res_o25:
        results.append(res_o25)

    logger.info("🎯 Récapitulatif de l'entraînement META :")
    for r in results:
        logger.info(f"  - {r['target']}: Acc={r['accuracy']:.2f} | LogLoss={r['log_loss']:.4f}")

    return results


if __name__ == "__main__":
    train_all_meta_models()
