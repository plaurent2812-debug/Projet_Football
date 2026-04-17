"""
Extraction des données NHL pour le Machine Learning.
Interroge nhl_fixtures dans Supabase, récupère les stats pré-match (features),
va chercher le boxscore officiel NHL pour les résultats réels (labels),
et génère le dataset CSV.
"""

import time
from pathlib import Path

import httpx
import pandas as pd

from src.config import logger, supabase

NHL_API = "https://api-web.nhle.com/v1"


def fetch_boxscore(game_id: int) -> dict:
    """Récupère le boxscore officiel d'un match."""
    url = f"{NHL_API}/gamecenter/{game_id}/boxscore"
    for _ in range(3):
        try:
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
            time.sleep(1)
        except Exception:
            time.sleep(1)
    return {}


def build_nhl_dataset(output_file="nhl_dataset.csv"):
    logger.info("Début de la création du dataset NHL ML...")

    # 1. Récupérer les matchs terminés avec des prédictions
    response = (
        supabase.table("nhl_fixtures")
        .select("api_fixture_id, date, home_team, away_team, stats_json")
        .in_("status", ["Final", "FINAL", "FT", "OFF"])
        .not_.is_("stats_json", "null")
        .execute()
    )

    fixtures = response.data or []
    logger.info(f"{len(fixtures)} matchs terminés trouvés dans Supabase.")

    dataset_rows = []

    for idx, fix in enumerate(fixtures):
        game_id = fix.get("api_fixture_id")
        stats_json = fix.get("stats_json", {})

        if not game_id or not stats_json:
            continue

        # 2. Récupérer le boxscore pour les résultats (labels)
        boxscore = fetch_boxscore(game_id)
        if not boxscore or "playerByGameStats" not in boxscore:
            logger.warning(f"  [{idx + 1}/{len(fixtures)}] Boxscore non trouvé pour {game_id}")
            continue

        logger.info(f"  [{idx + 1}/{len(fixtures)}] Traitement du match {game_id}...")

        # Consolider les stats réelles du match par joueur (ID ou Nom)
        real_stats = {}  # key: player_id ou full_name en minuscules, value: dict de perfs

        for team_type in ["homeTeam", "awayTeam"]:
            team_data = boxscore.get("playerByGameStats", {}).get(team_type, {})
            # Skaters (Forwards & Defense)
            for role in ["forwards", "defense"]:
                for skater in team_data.get(role, []):
                    name_parts = skater.get("name", {}).get("default", "").lower().split(" ")
                    full_name = " ".join(name_parts)
                    pid = str(skater.get("playerId", ""))

                    real_stats[pid] = {
                        "goals": skater.get("goals", 0),
                        "assists": skater.get("assists", 0),
                        "points": skater.get("points", 0),
                        "shots": skater.get("sog", 0),
                    }
                    real_stats[full_name] = real_stats[pid]  # Alias par nom au cas où

        # 3. Extraire les features des prédictions (stats pré-match) et lier aux labels
        # Les joueurs dans stats_json sont rangés sous home_team et away_team (dans pass 1 ou 2)

        # On fouille dans la structure de stats_json pour trouver les listes de joueurs
        # (Dans nhl_pipeline.py, stats_json = {"home_team": "...", "top_players": [...]})
        # Ou parfois c'est direct la liste des players scorés

        players_to_parse = []
        if isinstance(stats_json, dict) and "top_players" in stats_json:
            players_to_parse = stats_json["top_players"]
        elif isinstance(stats_json, dict):
            # Format par tableau "players" ou "home_players" etc...
            for key in ["players", "match_players", "point", "goal", "assist", "sog"]:
                if key in stats_json and isinstance(stats_json[key], list):
                    players_to_parse.extend(stats_json[key])
        elif isinstance(stats_json, list):
            players_to_parse = stats_json

        # Dédoublonner par player_id
        unique_players = {}
        for p in players_to_parse:
            pid = str(p.get("player_id", ""))
            if pid and pid not in unique_players:
                unique_players[pid] = p

        for pid, player_features in unique_players.items():
            player_name_lower = player_features.get("player_name", "").lower()

            # Chercher la perf réelle
            perf = real_stats.get(pid) or real_stats.get(player_name_lower)

            if perf is not None:
                row = player_features.copy()

                # Créer les labels binaires pour le modèle ML
                row["label_goal"] = 1 if perf["goals"] >= 1 else 0
                row["label_assist"] = 1 if perf["assists"] >= 1 else 0
                row["label_point"] = 1 if perf["points"] >= 1 else 0
                row["label_shot"] = (
                    1 if perf["shots"] >= 3 else 0
                )  # Threshold standard NHL: Over 2.5

                # Conserver l'ID du match pour référence
                row["game_id"] = game_id
                row["date"] = fix.get("date")

                # Nettoyer/Aplatir les objets imbriqués (l5_form, h2h)
                if "l5_form" in row and isinstance(row["l5_form"], dict):
                    for k, v in row["l5_form"].items():
                        row[f"l5_{k}"] = v
                    del row["l5_form"]

                if "h2h" in row and isinstance(row["h2h"], dict):
                    for k, v in row["h2h"].items():
                        row[f"h2h_{k}"] = v
                    del row["h2h"]

                dataset_rows.append(row)

    if not dataset_rows:
        logger.error("Aucune donnée générée. Le array est vide.")
        return

    df = pd.DataFrame(dataset_rows)
    # Supprimer les colonnes techniques dont on n'a pas besoin pour s'entraîner
    # KEEP: date (needed for temporal sort), player_id (for debugging)
    cols_to_drop = ["_skater", "player_name", "team", "opp"]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")

    # Ensure 'date' column is preserved for TimeSeriesSplit sorting
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)
        logger.info(
            f"  📅 Dataset trié par date: {df['date'].iloc[0][:10]} → {df['date'].iloc[-1][:10]}"
        )

    output_path = Path(__file__).parent.parent / output_file
    df.to_csv(output_path, index=False)
    logger.info(f"✅ Dataset généré: {len(dataset_rows)} lignes enregistrées dans {output_path}")


if __name__ == "__main__":
    build_nhl_dataset()
