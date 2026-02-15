from __future__ import annotations

import os
from collections import defaultdict

import requests
from config import logger
from dotenv import load_dotenv
from supabase import Client, create_client

# 1. Chargement des secrets
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
api_key = os.getenv("API_FOOTBALL_KEY")

if not api_key:
    logger.error("ERREUR: API_FOOTBALL_KEY manquante dans le fichier .env")
    exit()

supabase: Client = create_client(url, key)

# 2. Configuration API-Football
# Ligues : 61 = Ligue 1, 62 = Ligue 2, 39 = Premier League, 140 = La Liga,
#          135 = Serie A, 78 = Bundesliga, 2 = Champions League, 3 = Europa League,
#          1 = Coupe du Monde, 4 = Euro
LEAGUES_TO_FETCH = [61, 62, 39, 140, 135, 78, 2, 3, 1, 4]
SEASON = 2025

headers = {"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": api_key}


def get_next_round_fixtures(league_id: int) -> tuple[list[dict], str | None]:
    """Fetch upcoming fixtures and return only those from the next round.

    Retrieves up to 20 upcoming matches for the given league, groups
    them by round name, and returns the earliest round.

    Args:
        league_id: API league identifier.

    Returns:
        A tuple ``(fixtures, round_name)`` where *fixtures* is a list
        of raw API response items for the next round and *round_name*
        is the round label (e.g. ``"Regular Season - 25"``).  Returns
        ``([], None)`` when no upcoming matches exist.
    """
    url_api: str = "https://v3.football.api-sports.io/fixtures"
    # On prend 20 matchs pour être sûr de couvrir une journée complète
    querystring: dict[str, str] = {"league": str(league_id), "season": str(SEASON), "next": "20"}

    response = requests.get(url_api, headers=headers, params=querystring)
    data = response.json()

    if "response" not in data or not data["response"]:
        return [], None

    fixtures_list: list[dict] = data["response"]

    # Grouper par journée (round)
    by_round: defaultdict[str, list[dict]] = defaultdict(list)
    for item in fixtures_list:
        round_name: str = item["league"]["round"]
        by_round[round_name].append(item)

    # Prendre la première journée (la plus proche) = la prochaine
    first_round: str = list(by_round.keys())[0]
    return by_round[first_round], first_round


def fetch_and_store() -> None:
    """Fetch next-round fixtures for every league and store them in Supabase.

    Iterates over :data:`LEAGUES_TO_FETCH`, calls
    :func:`get_next_round_fixtures` for each league, upserts the league
    metadata into ``leagues``, and upserts each fixture into ``fixtures``.

    Returns:
        None.
    """
    logger.info(
        f"--- Démarrage de l'importation — Prochaine journée par ligue (Saison {SEASON}) ---"
    )
    total_imported: int = 0

    for league_id in LEAGUES_TO_FETCH:
        logger.info(f"Récupération pour la ligue {league_id}...")
        fixtures_list, round_name = get_next_round_fixtures(league_id)

        if not fixtures_list:
            logger.info(" -> Aucun match à venir pour cette ligue.")
            continue

        logger.info(f" -> Journée : {round_name} — {len(fixtures_list)} matchs")

        for item in fixtures_list:
            fixture = item["fixture"]
            teams = item["teams"]
            goals = item["goals"]
            league = item["league"]

            # A. On s'assure que la Ligue existe dans la table 'leagues'
            try:
                supabase.table("leagues").upsert(
                    {
                        "api_id": league["id"],
                        "name": league["name"],
                        "country": league["country"],
                        "season": league["season"],
                    },
                    on_conflict="api_id",
                ).execute()
            except Exception as e:
                logger.info(f"Info Ligue: {e}")

            # B. On insère le Match dans 'fixtures'
            try:
                stats_raw: dict = {
                    "venue": fixture.get("venue"),
                    "status_short": fixture["status"]["short"],
                    "round": round_name,
                }

                match_data: dict = {
                    "api_fixture_id": fixture["id"],
                    "date": fixture["date"],
                    "league_id": league["id"],
                    "home_team": teams["home"]["name"],
                    "away_team": teams["away"]["name"],
                    "status": fixture["status"]["short"],
                    "home_goals": goals.get("home"),
                    "away_goals": goals.get("away"),
                    "stats_json": stats_raw,
                }

                supabase.table("fixtures").upsert(
                    match_data, on_conflict="api_fixture_id"
                ).execute()

                logger.info(f"   [OK] {teams['home']['name']} vs {teams['away']['name']}")
                total_imported += 1

            except Exception as e:
                logger.error(f"   [ERREUR] Insertion match : {e}")

    logger.info(f"--- Terminé : {total_imported} matchs importés au total ---")


if __name__ == "__main__":
    fetch_and_store()
