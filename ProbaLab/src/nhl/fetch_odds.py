"""
fetch_odds.py — Récupère les vraies cotes bookmaker NHL (player props) depuis The Odds API.

Marchés : player_points (Over 0.5 points)
Bookmakers : DraftKings, FanDuel, BetMGM (US)

Usage:
    python -m src.nhl.fetch_odds [--date 2026-03-07]

The Odds API key: ODDS_API_KEY env var
Free plan: 500 req/mois (suffisant pour ~31 req/mois à raison de 1 fetch/soir)
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import requests

from src.config import setup_logger, supabase

logger = setup_logger("nhl_fetch_odds")

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "icehockey_nhl"

# Priority bookmakers (US — most complete NHL player props coverage)
BOOKMAKERS = ["draftkings", "fanduel", "betmgm", "williamhill_us", "bovada"]


def _get(path: str, params: dict) -> dict | None:
    """Appel The Odds API avec gestion d'erreurs."""
    params["apiKey"] = ODDS_API_KEY
    url = f"{ODDS_API_BASE}{path}"
    try:
        resp = requests.get(url, params=params, timeout=20)
        remaining = resp.headers.get("x-requests-remaining", "?")
        used = resp.headers.get("x-requests-used", "?")
        logger.debug(
            "Odds API %s → %d | remaining=%s used=%s", path, resp.status_code, remaining, used
        )

        if resp.status_code == 401:
            logger.error("ODDS_API_KEY invalide ou manquante")
            return None
        if resp.status_code == 422:
            logger.error("Paramètres invalides: %s", resp.text[:200])
            return None
        if resp.status_code == 429:
            logger.warning("Rate limit atteint (429)")
            return None
        if resp.status_code != 200:
            logger.error("HTTP %d: %s", resp.status_code, resp.text[:200])
            return None

        return resp.json()
    except requests.RequestException as e:
        logger.error("Erreur réseau: %s", e)
        return None


def fetch_events(date_str: str) -> list[dict]:
    """Récupère les events NHL pour une date donnée."""
    # The Odds API filtre les events via commenceTimeFrom/To (ISO 8601)
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        day = datetime.now(timezone.utc)

    # On prend la journée entière en UTC (les matchs NHL à 01h-05h UTC = nuit du jour J+1 Paris)
    # Pour March 7 Paris = March 6 21h UTC → March 7 07h UTC
    from_dt = day.replace(hour=0, minute=0, second=0)
    to_dt = from_dt + timedelta(days=1, hours=8)  # jusqu'à 08h UTC du lendemain

    data = _get(
        f"/sports/{SPORT}/events",
        {
            "commenceTimeFrom": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commenceTimeTo": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    if not data:
        return []

    events = data if isinstance(data, list) else data.get("data", [])
    logger.info("Found %d NHL events for %s", len(events), date_str)
    return events


def fetch_player_props(event_id: str, home_team: str, away_team: str) -> list[dict]:
    """Récupère les player props pour un match spécifique."""
    data = _get(
        f"/sports/{SPORT}/events/{event_id}/odds",
        {
            "regions": "us",
            "markets": "player_points",
            "oddsFormat": "decimal",
            "bookmakers": ",".join(BOOKMAKERS),
        },
    )

    if not data:
        return []

    rows = []
    bookmakers_list = data.get("bookmakers", [])

    for bookie in bookmakers_list:
        bookie_key = bookie.get("key", "")
        for market in bookie.get("markets", []):
            if market.get("key") != "player_points":
                continue
            for outcome in market.get("outcomes", []):
                # The Odds API format: name = 'Over'/'Under', description = player name
                direction = outcome.get("name", "").lower()  # 'over' or 'under'
                name = outcome.get("description", "").strip()  # player name
                price = outcome.get("price", 0.0)
                point = outcome.get("point", None)  # ex: 0.5 or 1.5

                if not name or direction != "over":
                    continue
                # Only keep Over 0.5 (standard NHL point prop)
                # Some books offer Over 1.5 — we only want the 0.5 line
                if point is not None and float(point) > 0.5:
                    continue

                rows.append(
                    {
                        "game_id": event_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "player_name": name,
                        "bookmaker": bookie_key,
                        "market": "player_points",
                        "line": float(point) if point is not None else 0.5,
                        "over_odds": float(price),
                    }
                )

    logger.debug("  %s vs %s → %d player prop rows", home_team, away_team, len(rows))
    return rows


def save_odds_to_supabase(rows: list[dict], game_date: str) -> int:
    """Upsert les cotes dans nhl_odds."""
    if not rows:
        return 0

    # Ajouter game_date à chaque row
    records = [{**r, "game_date": game_date} for r in rows]

    try:
        result = (
            supabase.table("nhl_odds")
            .upsert(records, on_conflict="game_id,player_name,bookmaker,market")
            .execute()
        )
        count = len(result.data or [])
        logger.info("Upserted %d rows into nhl_odds", count)
        return count
    except Exception as e:
        logger.error("Supabase upsert error: %s", e)
        return 0


def run(date_str: str | None = None) -> dict:
    """Point d'entrée principal."""
    if not ODDS_API_KEY:
        return {"ok": False, "error": "ODDS_API_KEY non définie"}

    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info("Fetching NHL odds for %s", date_str)

    events = fetch_events(date_str)
    if not events:
        logger.warning("Aucun event NHL trouvé pour %s", date_str)
        return {"ok": True, "events": 0, "rows": 0, "date": date_str}

    all_rows = []
    for event in events:
        event_id = event.get("id", "")
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        if not event_id:
            continue

        props = fetch_player_props(event_id, home, away)
        all_rows.extend(props)
        time.sleep(0.5)  # politesse envers l'API

    saved = save_odds_to_supabase(all_rows, date_str)

    return {
        "ok": True,
        "date": date_str,
        "events": len(events),
        "player_props_fetched": len(all_rows),
        "rows_saved": saved,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NHL player prop odds from The Odds API")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    result = run(args.date)
    logger.info("Result: %s", result)
