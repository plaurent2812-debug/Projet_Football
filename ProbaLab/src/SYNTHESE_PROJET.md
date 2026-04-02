# SYNTHÈSE COMPLÈTE DU PROJET — Football IA
> Dernière mise à jour : 10 février 2026, 01h15

---

## 1. VUE D'ENSEMBLE

Système complet de **prédiction de matchs de football** combinant :
- **Modèle statistique** (Poisson, ELO, forme, repos, enjeu, H2H, arbitre, météo, blessures)
- **Intelligence artificielle** (Gemini / Google GenAI pour l'analyse narrative)
- **Machine Learning** (XGBoost entraîné sur 5 444 matchs historiques)
- **Google Sheet** comme interface utilisateur (affichage, value betting, performance)
- **Supabase** comme base de données centrale
- **API-Football v3** comme source de données

### Ligues suivies
Ligue 1, Ligue 2, Premier League, La Liga, Serie A, Bundesliga, Champions League, Europa League.

---

## 2. ARCHITECTURE DES FICHIERS

```
Projet_Football/
│
├── config.py                    # Config partagée (Supabase, API-Football, clés)
├── .env                         # Variables d'environnement (SUPABASE_URL, SUPABASE_KEY, API_FOOTBALL_KEY, GEMINI_API_KEY)
│
├── ── PIPELINE PRINCIPAL ──
├── fetch_matches.py             # Import des prochains matchs depuis API-Football
├── fetch_context.py             # Récupère contexte (blessures, cotes, H2H, joueurs)
├── fetch_teams.py               # Import des équipes
├── fetch_players.py             # Import des joueurs et stats
├── stats_engine.py              # ⭐ Moteur statistique principal (Poisson, ELO, forme, etc.)
├── scorer_engine.py             # Prédiction du buteur le plus probable
├── brain.py                     # ⭐ Orchestrateur : stats → Gemini → prédictions finales
├── run_pipeline.py              # Lance le pipeline complet (fetch + analyse)
│
├── ── MACHINE LEARNING ──
├── fetch_training_history.py    # Récupère 2 saisons historiques (2023-2024) depuis API-Football
├── build_training_data.py       # ⭐ Construit les feature vectors (optimisé : 8s pour 5000+ matchs)
├── train_model.py               # ⭐ Entraîne 6 modèles XGBoost
├── ml_predictor.py              # Charge et utilise les modèles ML depuis Supabase
├── calibrate.py                 # Calibration Platt Scaling des probabilités
├── evaluate.py                  # Évaluation des prédictions vs résultats réels
│
├── ── UTILITAIRES ──
├── backfill_value.py            # Backfill proba_over_05 et proba_penalty sur anciens pronostics
├── fetch_history.py             # Import historique de matchs
├── test_connection.py           # Test de connexion Supabase
│
├── ── GOOGLE APPS SCRIPT ──
├── google_apps_script/
│   ├── Code.js                  # ⭐ Interface Google Sheet (affichage, value betting, performance)
│   ├── .clasp.json              # Config clasp (ID du projet Apps Script)
│   └── appsscript.json          # Manifest Apps Script
│
├── ── MIGRATIONS SQL (Supabase) ──
├── migrations/
│   ├── 001_stats_tables.sql     # Tables principales (fixtures, teams, players, predictions, etc.)
│   ├── 002_value_columns.sql    # Colonnes proba_over_05 et proba_penalty
│   ├── 003_performance_tracking.sql  # Tables prediction_results et calibration
│   └── 004_ml_training.sql      # Tables training_data et ml_models
```

---

## 3. BASE DE DONNÉES SUPABASE

### Tables principales
| Table | Description |
|-------|------------|
| `fixtures` | Tous les matchs (NS, FT, etc.) avec scores |
| `teams` | Équipes avec api_id |
| `team_standings` | Classements par ligue/saison |
| `team_elo` | Ratings ELO par équipe |
| `players` | Joueurs (position, is_injured) |
| `player_season_stats` | Stats saison par joueur (buts, passes, rating…) |
| `injuries` | Blessures en cours |
| `referees` | Arbitres et leurs tendances |
| `h2h_cache` | Historique des confrontations directes |
| `fixture_odds` | Cotes bookmakers par match |
| `leagues` | Ligues suivies |
| `predictions` | ⭐ Prédictions générées (probas, analyse, buteur, score) |
| `prediction_results` | Évaluation prédiction vs résultat réel |
| `calibration` | Paramètres Platt Scaling par type de pari |
| `training_data` | ⭐ 5 444 feature vectors pour ML (31 features + targets) |
| `ml_models` | ⭐ 6 modèles XGBoost sérialisés (pickle base64) |

### Toutes les migrations sont exécutées (001 à 004).

---

## 4. MODÈLES ML EN PLACE

Entraînés sur **5 444 matchs** (saisons 2023-2024, 8 ligues) :

| Modèle | Type | Précision | Cible |
|--------|------|-----------|-------|
| `xgb_1x2` | Classifier | 51.2% | Résultat H/D/A |
| `xgb_btts` | Classifier | 52.9% | Les 2 marquent |
| `xgb_over05` | Classifier | **93.6%** | Plus de 0.5 buts |
| `xgb_over15` | Classifier | **76.1%** | Plus de 1.5 buts |
| `xgb_over25` | Classifier | 55.1% | Plus de 2.5 buts |
| `xgb_total_goals` | Regressor | MAE 1.34 | Nombre total de buts |

### Intégration
- `stats_engine.py` charge les modèles via `ml_predictor.py`
- **Blend** : 60% probabilités statistiques + 40% probabilités ML
- Les modèles sont stockés dans Supabase (`ml_models`) et chargés automatiquement
- `model_version` dans les prédictions : `hybrid_v3_ml`

### 31 Features utilisées
`home/away_attack_strength`, `home/away_defense_strength`, `home/away_elo`, `elo_diff`, `home/away_form`, `home/away_rest_days`, `home/away_congestion_30d`, `home/away_stakes`, `h2h_home_winrate`, `h2h_total_matches`, `home/away_injury_count`, `home/away_injury_attack_factor`, `home/away_injury_defense_factor`, `referee_penalty_bias`, `market_home/draw/away_prob`, `xg_home/away`, `league_avg_home/away_goals`

---

## 5. GOOGLE SHEET — FONCTIONNALITÉS

### Onglet "⚽ Prédictions"
- Affichage par ligue avec bandeaux colorés
- Colonnes : V%, N%, D%, BTTS%, O0.5%, O1.5%, O2.5%, Score probable, Buteur, Pen%, Absents clés, Pari recommandé, Confiance, Analyse
- **Value Betting** : ✓ (value) ou ✗ (éviter) en comparant modèle vs bookmaker (+5% edge)
- Filtre automatique sur la ligne 4
- Couleurs conditionnelles sur toutes les probas

### Onglet "📈 Performance"
- **Section 1** : Taux de réussite par type de pari (1X2, BTTS, O0.5, O1.5, O2.5, Score exact, Buteur, Pari recommandé)
- **Section 2** : Performance par ligue (1X2%, BTTS%, O0.5%, O1.5%, O2.5%, Score exact%)
- **Section 3** : Analyse post-match détaillée (✅/❌ par catégorie + analyse textuelle)
- **Autonome** : met à jour les scores via API-Football, évalue en direct, pas besoin de scripts Python

### Onglet "🎰 Pronos"
- **Génération automatique** de 3 tickets de paris combinés sur les matchs du jour
- **🔒 Ticket SAFE** : Cote 2-3, 1-3 sélections ultra-sûres (Double Chance, Over 1.5, favoris forts). Priorité absolue à la probabilité de réussite.
- **🎲 Ticket FUN** : Cote ~20, 3-5 sélections diversifiées (1X2, BTTS, Over/Under). Mix de types de paris pour variété et valeur.
- **💎 Ticket JACKPOT** : Cote 50+, 4-8 sélections incluant des paris exotiques (score exact, buteur). Ancres sûres + paris risqués.
- **Algorithme expert** : scoring par qualité (proba + value betting + confiance), 1 pari par match, diversité des catégories
- **Indicateurs** : cote estimée, probabilité, confiance, value betting, gain potentiel (10€/20€/50€)
- **Notation** : système d'étoiles (⭐) évaluant la solidité de chaque ticket
- **Résumé comparatif** des 3 tickets en fin de page
- Si aucun match aujourd'hui, prend automatiquement la prochaine date disponible

### Menu "⚽ Football IA"
1. 🚀 Tout lancer (Import + Analyse + Affichage)
2. 📥 Importer les matchs
3. 🧠 Lancer l'analyse IA
4. 📊 Rafraîchir l'affichage
5. 📈 Performance & Analyse post-match
6. 🎰 Générer les Pronos du jour
7. ⚙️ Configurer les clés API

### Déploiement
- `clasp push --force` depuis `google_apps_script/`
- Script ID dans `.clasp.json` (voir fichier local, non versionné)

---

## 6. PIPELINE D'UTILISATION

### Quotidien (prédictions)
```bash
# Depuis le Sheet : menu Football IA → Tout lancer
# Ou en Python :
python run_pipeline.py
# Ou manuellement :
python fetch_matches.py       # Import matchs
python fetch_context.py       # Contexte (blessures, cotes, H2H)
python brain.py               # Analyse stats + IA → prédictions
```
Puis dans le Sheet : "📊 Rafraîchir l'affichage"

### Post-match (évaluation)
Dans le Sheet : "📈 Performance & Analyse post-match"
(Automatiquement : met à jour les scores, évalue, affiche)

### Ré-entraînement ML (périodique, ex: mensuel)
```bash
python fetch_training_history.py   # Récupère nouveaux matchs terminés
python build_training_data.py      # Construit les features (~8 secondes)
python train_model.py              # Entraîne les 6 modèles XGBoost (~10 secondes)
```
Les modèles sont automatiquement stockés dans Supabase et chargés par `stats_engine.py`.

---

## 7. POINTS TECHNIQUES IMPORTANTS

### Optimisations réalisées
- `build_training_data.py` : pré-charge TOUTES les données Supabase en mémoire → 8s au lieu de potentiellement des heures (évite ~100 000 requêtes individuelles)
- `train_model.py` : pagination correcte (blocs de 1000) pour charger les 5 444+ exemples
- Serialisation JSON : conversion explicite des `float32` numpy pour Supabase

### Bugs corrigés
- `scorer_engine.py` : `.not_()` remplacé par `.filter("...", "not.is", "null")` (compat supabase-py 2.10)
- Google Sheet : `filter.remove()` avant `merge()` pour éviter "cellules dépassent filtre"
- `train_model.py` : `float32` → `float()` pour la sérialisation JSON du régresseur

### Blessures
- `fetch_context.py` synchronise le flag `is_injured` dans la table `players`
- `scorer_engine.py` exclut les blessés des prédictions de buteurs
- `stats_engine.py` calcule `attack_factor` et `defense_factor` granulaires par poste/rating
- Le Sheet affiche les absents clés (colonne "🏥 Absents clés")

### Calibration
- `calibrate.py` applique le Platt Scaling sur les probas (si données suffisantes dans `prediction_results`)
- Appliqué après le blend stats+ML dans `stats_engine.py`

---

## 8. PROCHAINES AMÉLIORATIONS POSSIBLES

1. **Plus de données d'entraînement** : ajouter d'autres ligues/saisons
2. **Hyper-parameter tuning** : GridSearch/Bayesian sur les XGBoost
3. **Modèle de scoring** : prédire le nombre de buts par équipe (pas juste total)
4. **Vérification buteur** : croiser avec les événements de match pour valider la prédiction buteur
5. **Cotes Over 0.5** : vérifier si API-Football fournit les cotes O0.5 pour le value betting
6. **Automatisation** : cron/scheduler pour lancer le pipeline automatiquement chaque jour
7. **Feature engineering avancé** : ajouter des features comme la possession moyenne, tirs cadrés, etc.
8. **Stacking/Ensemble** : combiner plusieurs modèles (LightGBM, Random Forest) en plus de XGBoost

---

## 9. ENVIRONNEMENT TECHNIQUE

- **Python** : 3.10.12 (pyenv)
- **Packages** : supabase-py, requests, scipy, numpy, scikit-learn, xgboost, google-genai, python-dotenv
- **Node/clasp** : pour le déploiement Google Apps Script
- **Supabase** : PostgreSQL hébergé
- **API-Football** : v3 (plan avec rate limiting 300 req/min)
- **Google GenAI** : Gemini 2.5 Pro (`gemini-2.5-pro`)
- **Workspace** : `/Users/pierrelaurent/Desktop/Projet_Football`
- **Pas de git** initialisé sur le projet
