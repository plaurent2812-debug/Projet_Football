"""
Module ML pour prédictions NHL - Refonte v3.
Charge les modèles XGBoost entraînés et fournit des prédictions.
Utilise TRAINING_FEATURES de train_enhanced_model comme source unique de vérité.
"""
import os
import math
import pickle
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

# Suppression de la dépendance à train_enhanced_model
TRAINING_MODULE_AVAILABLE = False
TRAINING_FEATURES = ['algo_score_goal', 'python_vol', 'is_home']
prepare_features = None


class EnhancedGoalPredictor:
    """
    Prédicteur utilisant un modèle XGBoost entraîné.
    Fallback sur Poisson si le modèle n'est pas disponible.
    """

    def __init__(self):
        self.model = None
        self.feature_names: List[str] = []
        self.model_metadata: Dict[str, Any] = {}

    def load(self, path: str) -> bool:
        """Charge le modèle depuis un fichier pickle."""
        if not os.path.isfile(path):
            print(f"   ⚠️ Modèle non trouvé: {path}")
            return False
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)

            if isinstance(data, dict):
                self.model = data.get('model')
                self.feature_names = data.get('feature_names', [])
                self.model_metadata = data.get('metrics', {})
                # Capturer la date d'entraînement (stockée au top-level)
                if 'training_date' in data:
                    self.model_metadata['training_date'] = data['training_date']
            else:
                # Ancien format (modèle seul)
                self.model = data
                self.feature_names = ['algo_score_goal', 'python_vol', 'is_home']

            market = self.model_metadata.get('market', os.path.basename(path))
            acc = self.model_metadata.get('accuracy', 0)
            auc = self.model_metadata.get('roc_auc', 0)
            print(f"   ✅ Modèle chargé: {path}")
            if acc > 0:
                print(f"      Acc={acc:.2%}, AUC={auc:.3f}, Features={len(self.feature_names)}")
            return True
        except Exception as e:
            print(f"   ❌ Erreur chargement: {e}")
            self.model = None
            return False

    def _build_features(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Construit le DataFrame de features depuis les données joueur.
        Compatible avec les modèles anciens (3 features) et enrichis.

        IMPORTANT: Les features doivent être construites de la MÊME façon
        qu'à l'entraînement (prepare_features dans train_enhanced_model.py).
        Pas de dérivation circulaire algo_score → gpg → shooting_pct.
        """
        # Features de base
        algo_score = float(data.get('algo_score_goal', 50) or 50)
        python_vol = float(data.get('python_vol', 0) or 0)
        is_home = int(data.get('is_home', 0) or 0)

        # Features odds (pré-match, légitimes)
        implied_prob = float(data.get('implied_prob', 0) or 0)
        cote_num = float(data.get('cote_num', 0) or 0)

        # Stats joueur directes (pas dérivées de algo_score)
        gpg = float(data.get('gpg', 0) or 0)
        spg = float(data.get('spg', 0) or python_vol) if python_vol > 0 else float(data.get('spg', 0) or 0)
        apg = float(data.get('apg', 0) or 0)
        opp_gaa = float(data.get('opp_gaa', 3.0) or 3.0)
        toi_avg = float(data.get('toi_avg', 18.0) or 18.0)

        # Shooting % : utiliser la vraie stat, pas une dérivation circulaire
        shooting_pct = float(data.get('shooting_pct', 0) or 0)
        if shooting_pct <= 0:
            shooting_pct = 0.10  # Moyenne NHL ~10%
        shooting_pct = max(0, min(0.5, shooting_pct))

        # Features combinées (vraies stats prioritaires)
        goals_avg_5 = float(data.get('goals_avg_5', 0) or 0)
        shots_avg_5 = float(data.get('shots_avg_5', 0) or 0)
        goals_per_game = goals_avg_5 if goals_avg_5 > 0 else gpg
        shots_per_game = shots_avg_5 if shots_avg_5 > 0 else spg
        toi_minutes = float(data.get('toi_avg_real', 0) or toi_avg)
        toi_minutes = max(5, min(30, toi_minutes))
        opp_defense = float(data.get('opp_defense_rating', 0) or (opp_gaa / 3.0))
        assists_per_game = float(data.get('assists_avg_5', 0) or apg)
        points_per_game = float(data.get('points_avg_5', 0) or (goals_per_game + assists_per_game))
        goals_momentum = float(data.get('goals_trend', 0) or 0)

        # gpg_estimate aligné avec le training : vraies stats, sinon neutre
        gpg_estimate = goals_per_game if goals_per_game > 0 else 0.25

        # Features d'interaction
        offense_vs_defense = goals_per_game * opp_defense
        volume_efficiency = shots_per_game * shooting_pct
        home_boost = is_home * goals_per_game

        # Features enrichies
        opp_goalie_save_pct = float(data.get('opp_goalie_save_pct', 0.9) or 0.9)
        goalie_difficulty = (1.0 - opp_goalie_save_pct) * goals_per_game
        team_gf = float(data.get('team_goals_for_avg', 0) or 0)
        team_ga = float(data.get('team_goals_against_avg', 0) or 0)
        team_support = team_gf - team_ga
        goals_vs_opp = float(data.get('goals_vs_opp', 0) or 0)
        matchup_advantage = goals_vs_opp - goals_per_game

        # Shooting efficiency : vraie stat, pas dérivée
        shooting_efficiency = float(data.get('shooting_efficiency', 0) or 0)
        if shooting_efficiency <= 0 and shots_per_game > 0:
            shooting_efficiency = goals_per_game / (shots_per_game + 0.1)

        features = {
            'algo_score_goal': algo_score,
            'python_vol': python_vol,
            'is_home': is_home,
            'implied_prob': implied_prob,
            'cote_num': cote_num,
            'gpg_estimate': gpg_estimate,
            'spg': spg,
            'shooting_pct': shooting_pct,
            'toi_avg': toi_avg,
            'opp_gaa': opp_gaa,
            'goals_per_game': goals_per_game,
            'shots_per_game': shots_per_game,
            'toi_minutes': toi_minutes,
            'opp_defense': opp_defense,
            'assists_per_game': assists_per_game,
            'points_per_game': points_per_game,
            'goals_momentum': goals_momentum,
            'offense_vs_defense': offense_vs_defense,
            'volume_efficiency': volume_efficiency,
            'home_boost': home_boost,
            'goals_avg_3': float(data.get('goals_avg_3', 0) or 0),
            'goals_avg_5': goals_avg_5,
            'goals_avg_10': float(data.get('goals_avg_10', 0) or 0),
            'assists_avg_5': assists_per_game,
            'shots_avg_5': shots_per_game,
            'toi_avg_real': toi_minutes,
            'goals_trend': goals_momentum,
            'shooting_efficiency': shooting_efficiency,
            'power_play_goals_avg': float(data.get('power_play_goals_avg', 0) or 0),
            'consistency': float(data.get('consistency', 1.0) or 1.0),
            'goals_vs_opp': goals_vs_opp,
            'points_avg_5': points_per_game,
            'opp_defense_rating': opp_defense,
            'opp_goalie_save_pct': opp_goalie_save_pct,
            'opp_goalie_gaa_recent': float(data.get('opp_goalie_gaa_recent', 3.0) or 3.0),
            'team_goals_for_avg': team_gf,
            'team_goals_against_avg': team_ga,
            'team_form': float(data.get('team_form', 0) or 0),
            'team_win_streak': float(data.get('team_win_streak', 0) or 0),
            'goalie_difficulty': goalie_difficulty,
            'team_support': team_support,
            'matchup_advantage': matchup_advantage,
        }

        # Si le modèle a des feature_names, n'utiliser que celles-là
        if self.feature_names:
            df = pd.DataFrame([features])
            for feat in self.feature_names:
                if feat not in df.columns:
                    df[feat] = 0.0
            return df[self.feature_names]
        else:
            # Ancien format : 3 features
            return pd.DataFrame(
                [[algo_score, python_vol, is_home]],
                columns=['algo_score_goal', 'python_vol', 'is_home']
            )

    def predict_proba(self, data: Dict[str, Any]) -> float:
        """Retourne P(au moins 1 but) pour un joueur."""
        if self.model is not None:
            return self._predict_ml(data)
        return self._predict_fallback(data)

    def _predict_ml(self, data: Dict[str, Any]) -> float:
        """Prédiction via XGBoost."""
        try:
            X = self._build_features(data)
            proba = self.model.predict_proba(X)[0, 1]
            return float(max(0.01, min(0.99, proba)))
        except Exception as e:
            # print(f"   ⚠️ Erreur ML, fallback: {e}")
            return self._predict_fallback(data)

    def _predict_fallback(self, data: Dict[str, Any]) -> float:
        """Fallback Poisson quand pas de modèle ML."""
        gpg = float(data.get('gpg', 0) or 0)
        if gpg <= 0:
            # Utiliser goals_avg_5 enrichi si disponible, sinon valeur neutre NHL
            gpg = float(data.get('goals_avg_5', 0) or 0)
        if gpg <= 0:
            gpg = 0.25  # ~20 buts / 82 matchs, valeur neutre

        is_home = bool(data.get('is_home', False))
        home_factor = 1.05 if is_home else 0.95

        lam = gpg * home_factor
        prob = 1.0 - math.exp(-lam) if lam > 0 else 0.0
        return max(0.01, min(0.99, prob))


# =============================================================================
# SINGLETONS (compatibilité avec main.py)
# =============================================================================

goal_predictor = EnhancedGoalPredictor()
shot_predictor = EnhancedGoalPredictor()
point_predictor = EnhancedGoalPredictor()
assist_predictor = EnhancedGoalPredictor()


def load_all_models() -> Dict[str, EnhancedGoalPredictor]:
    """Charge tous les modèles disponibles."""
    loaded = {}
    
    # Chemin absolu ou relatif adapté (à configurer)
    # On suppose que les modèles sont dans un dossier "models" à la racine ou relatif
    
    # Pour le moment, on utilise un chemin relatif simple, à adapter selon le déploiement
    base_path = "models"
    
    models = {
        'GOAL': (f'{base_path}/best_goal_predictor.pkl', goal_predictor),
        'SHOT': (f'{base_path}/best_shot_predictor.pkl', shot_predictor),
        'POINT': (f'{base_path}/best_point_predictor.pkl', point_predictor),
        'ASSIST': (f'{base_path}/best_assist_predictor.pkl', assist_predictor),
    }

    for name, (path, predictor) in models.items():
        if os.path.isfile(path) and predictor.load(path):
            loaded[name] = predictor

    return loaded


# Alias pour compatibilité
class GoalPredictor(EnhancedGoalPredictor):
    pass


class ModelBacktester:
    """Évalue les performances du modèle sur données historiques."""

    def __init__(self, predictor: EnhancedGoalPredictor):
        self.predictor = predictor

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or 'label_goal' not in df.columns:
            return {"error": "DataFrame vide ou sans label_goal"}

        for col in ('algo_score_goal', 'python_vol', 'is_home'):
            if col not in df.columns:
                df[col] = 0

        predictions = []
        actuals = df['label_goal'].tolist()

        for _, row in df.iterrows():
            prob = self.predictor.predict_proba(row.to_dict())
            predictions.append(prob)

        pred_binary = [1 if p >= 0.5 else 0 for p in predictions]
        correct = sum(1 for p, a in zip(pred_binary, actuals) if p == a)
        accuracy = correct / len(actuals) if actuals else 0

        brier = (
            sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(actuals)
            if actuals else 1.0
        )

        bins = self._calibration_bins(predictions, actuals)

        return {
            "total_samples": len(actuals),
            "accuracy": round(accuracy * 100, 2),
            "brier_score": round(brier, 4),
            "calibration_bins": bins,
            "model_loaded": self.predictor.model is not None,
        }

    def _calibration_bins(self, predictions, actuals, n_bins=5):
        edges = np.linspace(0, 1, n_bins + 1)
        bins = []
        for i in range(n_bins):
            lo, hi = edges[i], edges[i + 1]
            mask = [(lo <= p < hi) for p in predictions]
            preds = [p for p, m in zip(predictions, mask) if m]
            acts = [a for a, m in zip(actuals, mask) if m]
            if preds:
                bins.append({
                    "range": f"{lo:.1f}-{hi:.1f}",
                    "count": len(preds),
                    "avg_predicted": round(sum(preds) / len(preds), 3),
                    "avg_actual": round(sum(acts) / len(acts), 3),
                })
        return bins
