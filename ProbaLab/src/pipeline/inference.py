import os

import pandas as pd

from src.config import logger
from src.models.meta_learner import XGBMetaLearner

# Singleton pour garder les modèles en RAM
_MODELS = {"1x2": None, "btts": None, "over_15": None, "over_25": None}


def get_meta_model(model_name: str) -> XGBMetaLearner | None:
    global _MODELS
    if _MODELS[model_name] is None:
        file_map = {
            "1x2": "meta_1x2_model.ubj",
            "btts": "meta_btts_model.ubj",
            "over_15": "meta_over_15_model.ubj",
            "over_25": "meta_over_25_model.ubj",
        }
        model_path = os.path.join("models/football", file_map[model_name])
        if not os.path.exists(model_path):
            return None

        try:
            model = XGBMetaLearner()
            model.model.load_model(model_path)
            _MODELS[model_name] = model
            logger.info(f"✅ Meta-Modèle {model_name} chargé en mémoire avec succès.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du Meta-Modèle {model_name}: {e}")
            return None

    return _MODELS[model_name]


def predict_meta(stats_result: dict, ai_features: dict) -> dict | None:
    """
    Prend les prédictions de base (stats) et les features IA,
    et utilise les Meta-Modèles XGBoost pour prédire toutes les probabilités ajustées.
    """
    results = {}

    # Base AI features used by all models
    base_feats = {
        "ai_motivation": ai_features.get("motivation_score", 0.0),
        "ai_media_pressure": ai_features.get("media_pressure", 0.0),
        "ai_injury_impact": ai_features.get("injury_tactical_impact", 0.0),
        "ai_cohesion": ai_features.get("cohesion_score", 0.0),
        "ai_style_risk": ai_features.get("style_risk", 0.0),
    }

    try:
        # 1. Prediction 1X2
        model_1x2 = get_meta_model("1x2")
        if model_1x2:
            row_1x2 = base_feats.copy()
            row_1x2.update(
                {
                    "proba_home": stats_result.get("proba_home", 0.33),
                    "proba_draw": stats_result.get("proba_draw", 0.33),
                    "proba_away": stats_result.get("proba_away", 0.33),
                }
            )
            # Ensure correct column order matching training
            cols_1x2 = [
                "ai_motivation",
                "ai_media_pressure",
                "ai_injury_impact",
                "ai_cohesion",
                "ai_style_risk",
                "proba_home",
                "proba_draw",
                "proba_away",
            ]
            df_1x2 = pd.DataFrame([row_1x2])[cols_1x2].fillna(0)
            preds_1x2 = model_1x2.predict(df_1x2)[0]
            # [0]=Away, [1]=Draw, [2]=Home
            results["proba_away_meta"] = round(float(preds_1x2[0]) * 100)
            results["proba_draw_meta"] = round(float(preds_1x2[1]) * 100)
            results["proba_home_meta"] = round(float(preds_1x2[2]) * 100)

        # 2. Prediction BTTS
        model_btts = get_meta_model("btts")
        if model_btts:
            row_btts = base_feats.copy()
            row_btts.update({"proba_btts": stats_result.get("proba_btts", 0.0)})
            cols_btts = [
                "ai_motivation",
                "ai_media_pressure",
                "ai_injury_impact",
                "ai_cohesion",
                "ai_style_risk",
                "proba_btts",
            ]
            df_btts = pd.DataFrame([row_btts])[cols_btts].fillna(0)
            preds_btts = model_btts.predict(df_btts)[0]
            # Binary logistic returns proba of class 1 (Yes)
            results["proba_btts_meta"] = round(float(preds_btts) * 100)

        # 3. Prediction Over 1.5
        model_o15 = get_meta_model("over_15")
        if model_o15:
            row_o15 = base_feats.copy()
            row_o15.update({"proba_over_15": stats_result.get("proba_over_15", 0.0)})
            cols_o15 = [
                "ai_motivation",
                "ai_media_pressure",
                "ai_injury_impact",
                "ai_cohesion",
                "ai_style_risk",
                "proba_over_15",
            ]
            df_o15 = pd.DataFrame([row_o15])[cols_o15].fillna(0)
            preds_o15 = model_o15.predict(df_o15)[0]
            results["proba_over_15_meta"] = round(float(preds_o15) * 100)

        # 4. Prediction Over 2.5
        model_o25 = get_meta_model("over_25")
        if model_o25:
            row_o25 = base_feats.copy()
            row_o25.update({"proba_over_25": stats_result.get("proba_over_25", 0.0)})
            cols_o25 = [
                "ai_motivation",
                "ai_media_pressure",
                "ai_injury_impact",
                "ai_cohesion",
                "ai_style_risk",
                "proba_over_25",
            ]
            df_o25 = pd.DataFrame([row_o25])[cols_o25].fillna(0)
            preds_o25 = model_o25.predict(df_o25)[0]
            results["proba_over_25_meta"] = round(float(preds_o25) * 100)

        return results if results else None

    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'inférence Meta-Modèle: {e}")
        return None
