"""
Entraînement des modèles XGBoost pour la NHL.
Charge `nhl_dataset.csv`, entraîne 4 modèles (Goal, Assist, Point, Shot),
et sauvegarde les classifieurs dans `models/`.
"""

import os
import sys
import pickle
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

try:
    from xgboost import XGBClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
except ImportError:
    print("Veuillez installer xgboost et scikit-learn: pip install xgboost scikit-learn pandas")
    sys.exit(1)

# Features utilisées pour l'entraînement (elles doivent toutes venir de build_data.py)
FEATURES = [
    "algo_score_goal", "algo_score_shot", "goals_per_game", "assists_per_game",
    "shots_per_game", "toi_minutes", "games_played", "ai_factor", "b2b", "pp_boost",
    "l5_point", "l5_goal", "l5_assist", "l5_shot", "h2h_point", "h2h_goal", "h2h_shot"
]

def load_data(filepath="nhl_dataset.csv") -> pd.DataFrame:
    path = Path(__file__).parent.parent / filepath
    if not path.exists():
        print(f"❌ Fichier dataset introuvable: {path}")
        print("Veuillez d'abord exécuter `python -m Projet_Football.nhl.build_data`")
        return pd.DataFrame()
    return pd.read_csv(path)

def train_market_model(df: pd.DataFrame, market: str, label_col: str, output_path: str):
    print(f"\n--- Entraînement du modèle: {market} ---")
    
    # Nettoyer
    df_clean = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Filtrer ceux qui manquent de la feature de base de l'heuristique pour ne pas bruiter
    if df_clean.empty:
        print("❌ Dataset vide.")
        return
        
    # Validation croisée simple
    X = df_clean[FEATURES]
    y = df_clean[label_col]
    
    # Vérifier l'équilibre des classes
    positives = y.sum()
    if positives == 0 or positives == len(y):
        print("❌ Pas de variance dans la cible (soit que des 0, soit que des 1). Entraînement impossible.")
        return
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    scale_pos_weight = (len(y_train) - sum(y_train)) / max(1, sum(y_train))
    
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Evaluation
    preds_proba = model.predict_proba(X_test)[:, 1]
    preds_bin = (preds_proba >= 0.5).astype(int)
    
    acc = accuracy_score(y_test, preds_bin)
    brier = brier_score_loss(y_test, preds_proba)
    try:
        auc = roc_auc_score(y_test, preds_proba)
    except Exception:
        auc = 0.5
        
    print(f"✅ Accuracy: {acc:.1%}")
    print(f"✅ Brier Score: {brier:.4f}")
    print(f"✅ ROC AUC: {auc:.3f}")
    
    # Sauvegarde
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    metadata = {
        'model': model,
        'feature_names': FEATURES,
        'metrics': {
            'market': market,
            'accuracy': acc,
            'brier_score': brier,
            'roc_auc': auc
        },
        'training_date': datetime.now().isoformat()
    }
    
    with open(output_path, "wb") as f:
        pickle.dump(metadata, f)
        
    print(f"💾 Modèle sauvegardé dans {output_path}")

def train_all():
    df = load_data()
    if df.empty:
        return
        
    # Assurer que les colonnes catégorielles ou textuelles sont ignorées
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0.0 # Remplissage préventif
    
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
            print(f"⚠️ Colonne cible {label_col} introuvable pour {name}.")

if __name__ == "__main__":
    train_all()
