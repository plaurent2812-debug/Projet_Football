"""
fetch_players.py — Récupère joueurs + stats saison de chaque équipe.

Endpoint : GET /players?team={id}&season=2025&page={n}
Paginé : 20 joueurs par page.
~160 équipes × ~2 pages = ~320 requêtes
"""

import logging

from src.config import SEASON, api_get, get_request_count, reset_request_count, supabase

logger = logging.getLogger(__name__)


def safe_int(val):
    """Convertit en int, retourne 0 si None."""
    return int(val) if val is not None else 0


def safe_float(val):
    """Convertit en float, retourne None si impossible."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def fetch_players_for_team(team_api_id, team_name):
    """Récupère tous les joueurs d'une équipe avec pagination."""
    page = 1
    total_players = 0
    all_players = []
    all_stats = []

    while True:
        data = api_get("players", {"team": team_api_id, "season": SEASON, "page": page})
        if not data or not data.get("response"):
            break

        results = data["response"]
        paging = data.get("paging", {})

        for item in results:
            p = item["player"]
            stats_list = item.get("statistics", [])

            # Extraire hauteur/poids
            height = None
            if p.get("height"):
                try:
                    height = float(p["height"].replace(" cm", "").strip())
                except (ValueError, AttributeError):
                    pass

            weight = None
            if p.get("weight"):
                try:
                    weight = float(p["weight"].replace(" kg", "").strip())
                except (ValueError, AttributeError):
                    pass

            # Données joueur
            player_data = {
                "api_id": p["id"],
                "name": p.get("name", "Unknown"),
                "team_api_id": team_api_id,
                "nationality": p.get("nationality"),
                "age": p.get("age"),
                "height_cm": height,
                "weight_kg": weight,
                "photo_url": p.get("photo"),
                "is_injured": p.get("injured", False),
            }

            # Position depuis les stats (première entrée)
            if stats_list:
                player_data["position"] = stats_list[0].get("games", {}).get("position")

                # Stats saison — TOUTES les compétitions (Ligue 1, UCL, etc.)
                for s in stats_list:
                    games = s.get("games", {})
                    goals = s.get("goals", {})
                    shots = s.get("shots", {})
                    passes = s.get("passes", {})
                    dribbles = s.get("dribbles", {})
                    tackles = s.get("tackles", {})
                    duels = s.get("duels", {})
                    fouls = s.get("fouls", {})
                    cards = s.get("cards", {})
                    penalty = s.get("penalty", {})

                    league_id = s.get("league", {}).get("id")
                    if not league_id:
                        continue

                    stat_data = {
                        "player_api_id": p["id"],
                        "team_api_id": team_api_id,
                        "league_id": league_id,
                        "season": SEASON,
                        "appearances": safe_int(games.get("appearences")),  # typo dans l'API
                        "minutes_played": safe_int(games.get("minutes")),
                        "rating": safe_float(games.get("rating")),
                        "goals": safe_int(goals.get("total")),
                        "assists": safe_int(goals.get("assists")),
                        "goals_conceded": safe_int(goals.get("conceded")),
                        "saves": safe_int(goals.get("saves")),
                        "shots_total": safe_int(shots.get("total")),
                        "shots_on_target": safe_int(shots.get("on")),
                        "passes_total": safe_int(passes.get("total")),
                        "passes_key": safe_int(passes.get("key")),
                        "passes_accuracy": safe_int(passes.get("accuracy")),
                        "dribbles_attempts": safe_int(dribbles.get("attempts")),
                        "dribbles_success": safe_int(dribbles.get("success")),
                        "tackles_total": safe_int(tackles.get("total")),
                        "interceptions": safe_int(tackles.get("interceptions")),
                        "duels_total": safe_int(duels.get("total")),
                        "duels_won": safe_int(duels.get("won")),
                        "fouls_drawn": safe_int(fouls.get("drawn")),
                        "fouls_committed": safe_int(fouls.get("committed")),
                        "yellow_cards": safe_int(cards.get("yellow")),
                        "red_cards": safe_int(cards.get("red")),
                        "penalty_scored": safe_int(penalty.get("scored")),
                        "penalty_missed": safe_int(penalty.get("missed")),
                        "penalty_saved": safe_int(penalty.get("saved")),
                    }
                    all_stats.append(stat_data)

            all_players.append(player_data)
            total_players += 1

        # Pagination
        if page >= paging.get("total", 1):
            break
        page += 1

    # Upsert en batch
    if all_players:
        try:
            supabase.table("players").upsert(all_players, on_conflict="api_id").execute()
        except Exception as e:
            logger.error("      Erreur players upsert : %s", e)

    if all_stats:
        try:
            supabase.table("player_season_stats").upsert(
                all_stats, on_conflict="player_api_id,league_id,season"
            ).execute()
        except Exception as e:
            logger.error("      Erreur stats upsert : %s", e)

    return total_players


def fetch_all_players():
    """Récupère les joueurs de toutes les équipes de toutes les ligues."""
    reset_request_count()
    logger.info("=== Importation des joueurs + stats saison (%s) ===", SEASON)

    # Charger les équipes depuis Supabase
    all_teams = supabase.table("teams").select("api_id, name, league_id").execute().data
    if not all_teams:
        logger.error("Aucune equipe en base. Lance fetch_teams.py d'abord.")
        return

    total = 0
    for i, team in enumerate(all_teams):
        count = fetch_players_for_team(team["api_id"], team["name"])
        logger.info("  (%d/%d) %s: %d joueurs", i + 1, len(all_teams), team["name"], count)
        total += count

    logger.info("=" * 50)
    logger.info("Total : %d joueurs importes (%d requetes API)", total, get_request_count())


if __name__ == "__main__":
    fetch_all_players()
