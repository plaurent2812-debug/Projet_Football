Plan structuré que tu peux coller tel quel dans Antigravity comme spec / TODO technique.

Phase 0 – Préparation & hygiene
 Créer une branche stack-v2-refactor (NHL + Football).

 Ajouter un champ model_version dans toutes les tables de prédictions :

fixtures, nhl_fixtures, SUIVI_ALGO, nhl_suivi_algo_clean.

Ex : v1 (stack actuel), v2_meta_ai_features, etc.

 Mettre en place un flag de routing :

use_v2_stack (bool) par environnement / ligue pour A/B.

Phase 1 – Refonte usage IA (Gemini → features JSON)
1.1. Définir le schéma JSON IA
 Dans brain.py (Football) et nhl_ai_context.py (ou équivalent) définir un schéma standardisé, ex :

text
{
  "motivation_score": -1.0..1.0,
  "media_pressure": -1.0..1.0,
  "injury_tactical_impact": -1.0..1.0,
  "derby_intensity": -1.0..1.0,
  "schedule_pressure": -1.0..1.0,
  "cohesion_score": -1.0..1.0,
  "style_risk": -1.0..1.0
}
 Écrire un Pydantic model / dataclass AIFeatures pour valider et normaliser ces scores.

1.2. Modifier les prompts Gemini
 Dans brain.build_prompt() / get_ai_game_context() :

Modifier le prompt pour obliger Gemini à sortir uniquement du JSON, sans texte libre.

Ajouter des exemples de JSON dans le prompt.

 Ajouter une fonction parse_ai_features(raw_text) -> AIFeatures.

1.3. Persistance & features ML
 Ajouter des colonnes IA dans Supabase :

Table fixtures : ai_motivation_score, ai_media_pressure, ai_injury_tactical_impact, etc.
​

Table NHL équivalente (ex : nhl_fixtures ou nhl_ai_context).

 Dans la construction de features ML :

Football : enrichir stats_engine.analyze_match() / features XGBoost avec ces champs.

NHL : enrichir _build_features avec ai_factor_* dérivés du JSON (remplacer/compléter l’actuel ai_factor).
​

 Supprimer toute utilisation directe de “probas IA” dans le blend final (Football hybride 70/30, etc.).

Phase 2 – Méta-modèles de stacking (Football + NHL)
2.1. Extraction dataset d’entraînement
 Écrire un script training/prepare_meta_dataset.py qui :

Récupère depuis SUIVI_ALGO / fixtures les matchs passés avec :

p_poisson, p_elo, p_market, p_ml_xgb, p_ai_baseline (si dispo),

labels réels (1X2 ou binaire win / buteur).

 Ajouter des features contextuels simples :

ligue / competition, cote implicite, range de cote, home/away, etc.

2.2. Entraînement Football 1X2
 Créer training/train_meta_1x2.py :

Modèle 1 : regression logistique (baseline).

Modèle 2 : XGBoost léger (max_depth faible, regularization forte).

CV temporelle (split par date).

 Objectif : minimiser log-loss / Brier sur validation.

 Sauvegarder le meilleur modèle dans models/football/meta_1x2.pkl.

2.3. Entraînement NHL (match winner + props principaux)
 Idem pour NHL :

training/train_meta_nhl_win.py pour P(home win).

training/train_meta_nhl_goal_prop.py pour P(>=1 but joueur).

 Inputs : p_poisson, p_team_stats, p_market, p_xgb_player, ai_features, etc.
​

2.4. Intégration dans le runtime
 Football :

Dans stats_engine ou brain.blend_predictions() :

remplacer les pondérations 55/25/20 et 60/40 par un appel au meta-modèle.

 NHL :

Dans calculate_win_prob + endpoints props :

remplacer combinaisons actuelles par meta-modèle.

Phase 3 – Upgrades NHL (GSAx, Bayes par position, lignes)
3.1. Ingestion GSAx
 Créer un job nhl_ingest_gsax.py :

Télécharger les CSV MoneyPuck / NST (cron hebdo).

Normaliser dans table nhl_goalies_advanced : goalie_id, season, gsax, shots_faced, etc.

 Joindre gsax et gsax_per_60 dans nhl_data_lake sur goalie.
​

3.2. Régression bayésienne par position
 Dans la fonction de régression shooting% :

Définir ancres séparées :

anchor_fwd ~ 12–14%, anchor_def ~ 4–6% (calibrés via historique ligue).

Utiliser position du joueur pour choisir l’ancre.

 Ajuster les poids (nb de tirs) par rôle si nécessaire.

3.3. Projected lines & qualité de linemates
 Créer un scraper nhl_scrape_projected_lines.py :

Source : DailyFaceoff / autres, stocker dans nhl_projected_lines (team, line, players, pp_unit, timestamp).

 Dans le pipeline features :

Ajouter :

linemate_avg_points60, linemate_avg_xg60 (approx via stats publiques),

is_promoted_to_top_line (bool),

pp_unit (PP1/PP2).

 Intégrer ces features dans _build_features pour les modèles joueurs.
​
3.4 Modèles de Comptage
Mission : Remplacer la classification binaire XGBoost actuelle (P(>= 1 but)) par un modèle de distribution (Régression de Poisson ou Binomiale Négative). Prédire l'espérance totale (xG/xPoints) du joueur pour en dériver mathématiquement P(=0), P(>=1), P(>=2).

Phase 4 – Upgrades Football (vrais xG, nul, VORP)
4.1. Ingestion de vrais xG
 Écrire football_ingest_xg.py :

Source : Understat / FBref / API-Football (selon ce que tu choisis).

Stockage dans team_xg_stats : team_id, match_id, xg_for, xg_against, xg_diff, xg_per_shot, etc.
​

 Ajouter les colonnes xG dans fixtures (join match_id).

4.2. Utilisation xG dans Stats Engine
 Dans stats_engine.analyze_match() :

Ajouter des features :

xg_diff_last5, xg_for_last5, xg_against_last5, xg_luck (goals - xG).

Option : remplacer progressivement la force d’attaque/défense basée sur buts par une version basée sur xG.

4.3. Draw probability dynamique
 Supprimer la logique “draw rate fixe” par ligue dans la conversion ELO → proba (ou la rendre purement indicative).
​

 Laisser Poisson + Dixon-Coles calculer la proba de nul à partir des xG home/away.

 Garder une éventuelle calibration légère par ligue en post-process (Platt / isotonic par marché “Draw”).

4.4. Blessures : implémenter VORP
 Dans player_stats et injuries :

Calculer pour chaque joueur :

valeur offensive/défensive (buts/90, xG/90, key passes/90, interceptions/90, etc.).

 Créer un module injury_vorp.py qui :

estime un vorp_attack et vorp_defense pour chaque joueur blessé vs remplaçant probable,

renvoie un team_attack_factor / team_defense_factor continu plutôt que des seuils statiques.

4.5 "Poisson Bivarié" :
Mission : Implémenter une matrice de Poisson Bivarié (ou Skellam) pour modéliser la corrélation Domicile/Extérieur. En déduire le 1X2, le BTTS et l'Over/Under à partir de cette matrice de score exact unique pour une cohérence interne de 100%.

Phase 5 – Calibration & CLV
5.1. Révision des seuils de calibration
 Dans calibrate.py (Foot + NHL) :

Appliquer la nouvelle règle :

< 200 obs : identité (ou linéaire soft).

200–1000 : Platt scaling.

> 1000 : isotonic regression.

 Ajouter calcul de ECE (Expected Calibration Error) par marché + ligue.

5.2. CLV (Closing Line Value)
 Étendre SUIVI_ALGO :

colonnes : closing_odds, closing_odds_provider, closing_timestamp.
​

 Créer un job fetch_closing_odds.py :

Récupérer les cotes close (Pinnacle ou proxy) T-1 min du coup d’envoi.

 Créer un script analyze_clv.py :

calculer distribution de ln(closing_odds / taken_odds),

% de bets avec CLV positive.

Phase 6 – Expés, A/B et déploiement
 Mettre en place un mode “expérimental” :

sur chaque match : stocker pred_v1 et pred_v2 (meta+features IA+GSAx/xG) en parallèle, avec model_version.

 Ajouter une vue/endpoint GET /performance_by_version :

Brier, log-loss, ROI, CLV par model_version, marché, ligue.

 Critères de rollout :

v2 > v1 sur :

Brier/log-loss (stat. significatif),

CLV moyenne > 0,

pas de dégradation majeure sur ligues clés (NHL + top 5 ligues européennes).

Phase 7 – Nettoyage & docs
 Supprimer les anciennes pondérations manuelles inutilisées dans le code (ou les taguer comme deprecated_v1).

 Documenter :

schéma JSON des IA features,

schéma des nouvelles tables (nhl_goalies_advanced, team_xg_stats, ai_features, etc.),

protocole d’entraînement des meta-modèles.

 Mettre à jour les notebooks / scripts de monitoring (calibration + CLV) pour suivi hebdo.

Tu peux prendre ce plan comme base de fichier STACK_V2_PLAN.md dans ton repo, et attaquer Phase 1 → Phase 2 en priorité (IA→features + stacking), puis NHL/Foot features, puis calibration/CLV.