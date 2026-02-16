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


def get_fixtures_by_date(league_id: int, date_from: str, date_to: str) -> list[dict]:
    """Fetch fixtures within a specific date range.

    Args:
        league_id: API league identifier.
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).

    Returns:
        List of raw fixture items.
    """
    url_api = "https://v3.football.api-sports.io/fixtures"
    querystring = {
        "league": str(league_id),
        "season": str(SEASON),
        "from": date_from,
        "to": date_to,
        "timezone": "Europe/Paris"
    }

    try:
        response = requests.get(url_api, headers=headers, params=querystring)
        data = response.json()
        return data.get("response", [])
    except Exception as e:
        logger.error(f"Erreur API pour ligue {league_id}: {e}")
        return []


def fetch_and_store(date_from: str = None, date_to: str = None) -> None:
    """Fetch fixtures for a specific range (defaults to next 7 days).

    Args:
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
    """
    from datetime import datetime, timedelta

    if not date_from:
        date_from = datetime.now().strftime("%Y-%m-%d")
    if not date_to:
        date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    logger.info(
        f"--- Démarrage de l'importation par date : {date_from} -> {date_to} ---"
    )
    total_imported = 0

    for league_id in LEAGUES_TO_FETCH:
        logger.info(f"Récupération ligue {league_id}...")
        fixtures_list = get_fixtures_by_date(league_id, date_from, date_to)

        if not fixtures_list:
            continue

        for item in fixtures_list:
            fixture = item["fixture"]
            teams = item["teams"]
            goals = item["goals"]
            league = item["league"]
            
            # Upsert Ligue
            try:
                supabase.table("leagues").upsert({
                    "api_id": league["id"],
                    "name": league["name"],
                    "country": league["country"],
                    "season": league["season"],
                }, on_conflict="api_id").execute()
            except Exception:
                pass

            # Upsert Match
            try:
                stats_raw = {
                    "venue": fixture.get("venue"),
                    "status_short": fixture["status"]["short"],
                    "round": league.get("round"),
                }

                match_data = {
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

                total_imported += 1

            except Exception as e:
                logger.error(f"   [ERREUR] Match {fixture['id']} : {e}")
    
    logger.info(f"--- Terminé : {total_imported} matchs importés ---")


if __name__ == "__main__":
    fetch_and_store()
