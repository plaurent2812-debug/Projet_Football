from __future__ import annotations

"""
fetch_teams.py — Récupère les équipes + classements de chaque ligue.

Endpoints utilisés :
  - GET /teams?league={id}&season=2025       (~8 requêtes)
  - GET /standings?league={id}&season=2025   (~8 requêtes)
Total : ~16 requêtes
"""
from config import (
    LEAGUES,
    SEASON,
    api_get,
    get_request_count,
    logger,
    reset_request_count,
    supabase,
)


def populate_leagues_table() -> None:
    """Upsert LEAGUES from config into the leagues table."""
    logger.info("   -> Peuplement de la table `leagues`...")
    batch = []
    for l in LEAGUES:
        batch.append({
            "api_id": l["id"],
            "name": l["name"],
            "country": l["country"],
        })
    try:
        supabase.table("leagues").upsert(batch, on_conflict="api_id").execute()
        logger.info(f"      ✅ {len(batch)} ligues mises à jour.")
    except Exception as e:
        logger.error(f"      ❌ Erreur ligues : {e}")


def fetch_teams() -> int:
    """Fetch all teams for every tracked league and upsert into Supabase.

    Calls ``GET /teams`` for each league, extracts team + venue
    metadata, and upserts them into the ``teams`` table.

    Returns:
        The total number of teams imported.
    """
    reset_request_count()
    logger.info(f"=== Importation des équipes (Saison {SEASON}) ===")
    
    # Étape 0 : Peupler la table des ligues
    populate_leagues_table()
    
    total: int = 0

    for league in LEAGUES:
        lid: int = league["id"]
        logger.info(f"📋 {league['name']}...")

        data = api_get("teams", {"league": lid, "season": SEASON})
        if not data or not data.get("response"):
            logger.info("   Aucune équipe trouvée.")
            continue

        teams: list[dict] = data["response"]
        logger.info(f"   {len(teams)} équipes trouvées.")

        batch: list[dict] = []
        for item in teams:
            t = item["team"]
            v = item.get("venue") or {}
            batch.append(
                {
                    "api_id": t["id"],
                    "name": t["name"],
                    "league_id": lid,
                    "logo_url": t.get("logo"),
                    "venue_name": v.get("name"),
                    "venue_city": v.get("city"),
                    "country": league["country"],
                }
            )

        try:
            supabase.table("teams").upsert(batch, on_conflict="api_id").execute()
            total += len(batch)
            logger.info(f"   ✅ {len(batch)} équipes enregistrées.")
        except Exception as e:
            logger.error(f"   ❌ Erreur upsert : {e}")

    logger.info(f"{'=' * 50}")
    logger.info(f"Total : {total} équipes importées ({get_request_count()} requêtes API)")
    return total


def fetch_standings() -> int:
    """Fetch full standings (home/away splits) for every tracked league.

    Calls ``GET /standings`` for each league, flattens the nested
    response into per-team rows, and upserts them into
    ``team_standings``.

    Returns:
        The total number of standing entries imported.
    """
    logger.info(f"=== Importation des classements (Saison {SEASON}) ===")
    total: int = 0

    for league in LEAGUES:
        lid: int = league["id"]
        logger.info(f"📊 {league['name']}...")

        data = api_get("standings", {"league": lid, "season": SEASON})
        if not data or not data.get("response"):
            logger.info("   Pas de classement disponible.")
            continue

        # L'API retourne une liste de groupes (poules CL, etc.)
        for group in data["response"]:
            standings_list = group.get("league", {}).get("standings", [])
            for standings_group in standings_list:
                batch: list[dict] = []
                for entry in standings_group:
                    team = entry["team"]
                    all_stats = entry.get("all", {})
                    home = entry.get("home", {})
                    away = entry.get("away", {})

                    batch.append(
                        {
                            "team_api_id": team["id"],
                            "league_id": lid,
                            "season": SEASON,
                            "rank": entry.get("rank"),
                            "points": entry.get("points", 0),
                            "goal_diff": entry.get("goalsDiff", 0),
                            "form": entry.get("form"),
                            "played": all_stats.get("played", 0),
                            "wins": all_stats.get("win", 0),
                            "draws": all_stats.get("draw", 0),
                            "losses": all_stats.get("lose", 0),
                            "goals_for": all_stats.get("goals", {}).get("for", 0),
                            "goals_against": all_stats.get("goals", {}).get("against", 0),
                            "home_played": home.get("played", 0),
                            "home_wins": home.get("win", 0),
                            "home_draws": home.get("draw", 0),
                            "home_losses": home.get("lose", 0),
                            "home_goals_for": home.get("goals", {}).get("for", 0),
                            "home_goals_against": home.get("goals", {}).get("against", 0),
                            "away_played": away.get("played", 0),
                            "away_wins": away.get("win", 0),
                            "away_draws": away.get("draw", 0),
                            "away_losses": away.get("lose", 0),
                            "away_goals_for": away.get("goals", {}).get("for", 0),
                            "away_goals_against": away.get("goals", {}).get("against", 0),
                        }
                    )

                if batch:
                    try:
                        supabase.table("team_standings").upsert(
                            batch, on_conflict="team_api_id,league_id,season"
                        ).execute()
                        total += len(batch)
                    except Exception as e:
                        logger.error(f"   ❌ Erreur classement : {e}")

        logger.info("   ✅ Classement enregistré.")

    logger.info(f"{'=' * 50}")
    logger.info(f"Total : {total} entrées de classement ({get_request_count()} requêtes API)")
    return total


def init_elo() -> None:
    """Initialise ELO ratings to 1 500 for every team in the database.

    Reads all teams from the ``teams`` table and creates (or updates)
    a row in ``team_elo`` with the default rating.

    Returns:
        None.
    """
    logger.info("=== Initialisation des ratings ELO ===")

    # Récupérer toutes les équipes
    teams = supabase.table("teams").select("api_id, name, league_id").execute().data
    if not teams:
        logger.info("   Aucune équipe en base.")
        return

    batch: list[dict] = []
    for t in teams:
        batch.append(
            {
                "team_api_id": t["api_id"],
                "team_name": t["name"],
                "league_id": t["league_id"],
                "elo_rating": 1500.0,
            }
        )

    try:
        supabase.table("team_elo").upsert(batch, on_conflict="team_api_id").execute()
        logger.info(f"   ✅ {len(batch)} ratings ELO initialisés à 1500.")
    except Exception as e:
        logger.error(f"   ❌ Erreur ELO : {e}")


if __name__ == "__main__":
    fetch_teams()
    fetch_standings()
    init_elo()
