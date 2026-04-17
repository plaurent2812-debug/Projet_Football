"""
fetch_game_stats.py
───────────────────
Fetches actual NHL player stats for a given date from the NHL API boxscore.
Stores goals/assists/points in nhl_player_game_stats for auto-resolution of best_bets.

Called by:
  - POST /api/nhl/fetch-game-stats  (Railway API, triggered by Trigger.dev)
  - python -m src.nhl.fetch_game_stats --date 2026-03-07  (manual)

NHL API used:
  https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore
"""

import argparse
import time
from datetime import datetime, timedelta, timezone

import httpx

from src.config import logger, supabase
from src.nhl.constants import NHL_NAME_TO_ABBREV

NHL_API = "https://api-web.nhle.com/v1"


def fetch_boxscore(game_id: int) -> dict:
    """Fetch official boxscore for a game from the NHL API."""
    url = f"{NHL_API}/gamecenter/{game_id}/boxscore"
    for attempt in range(3):
        try:
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"Boxscore {game_id}: HTTP {resp.status_code}, retry {attempt + 1}")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Boxscore {game_id}: error {e}, retry {attempt + 1}")
            time.sleep(1)
    return {}


def parse_players_from_boxscore(
    boxscore: dict, home_team_abbrev: str, away_team_abbrev: str
) -> list[dict]:
    """Extract per-player goals/assists/points/shots from a boxscore."""
    results = []
    mappings = [("homeTeam", home_team_abbrev), ("awayTeam", away_team_abbrev)]

    for team_key, team_abbrev in mappings:
        team_data = boxscore.get("playerByGameStats", {}).get(team_key, {})
        for role in ["forwards", "defense"]:
            for skater in team_data.get(role, []):
                pid = str(skater.get("playerId", ""))
                name = skater.get("name", {}).get("default", "")
                if not pid or not name:
                    continue
                results.append(
                    {
                        "player_id": pid,
                        "player_name": name,
                        "team": team_abbrev,
                        "goals": int(skater.get("goals") or 0),
                        "assists": int(skater.get("assists") or 0),
                        "points": int(skater.get("points") or 0),
                        "shots": int(skater.get("sog") or skater.get("shots") or 0),
                        "toi": skater.get("toi", ""),
                    }
                )
    return results


def fetch_and_store_game_stats(date: str) -> dict:
    """
    Fetch actual player stats for all NHL games on `date`, store in nhl_player_game_stats.
    Returns summary dict.
    """
    logger.info(f"[NHL Stats] Fetching game stats for {date}")

    next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

    # Load finished NHL fixtures for that date
    fx_resp = (
        supabase.table("nhl_fixtures")
        .select("id, api_fixture_id, home_team, away_team, home_score, away_score, status")
        .gte("date", f"{date}T00:00:00Z")
        .lt("date", f"{next_day}T23:59:59Z")
        .in_("status", ["Final", "FINAL", "FT", "OFF"])
        .execute()
    )
    fixtures = fx_resp.data or []
    logger.info(f"[NHL Stats] Found {len(fixtures)} finished fixture(s) for {date}")

    total_players = 0
    errors = []

    for fx in fixtures:
        game_id = fx.get("api_fixture_id")
        if not game_id:
            continue

        home_abbrev = NHL_NAME_TO_ABBREV.get(fx["home_team"], fx["home_team"][:3].upper())
        away_abbrev = NHL_NAME_TO_ABBREV.get(fx["away_team"], fx["away_team"][:3].upper())

        logger.info(
            f"  Fetching boxscore for game {game_id} ({fx['home_team']} vs {fx['away_team']})"
        )
        boxscore = fetch_boxscore(game_id)

        if not boxscore or "playerByGameStats" not in boxscore:
            logger.warning(f"  No boxscore data for game {game_id}")
            errors.append({"game_id": game_id, "error": "No boxscore data"})
            continue

        players = parse_players_from_boxscore(boxscore, home_abbrev, away_abbrev)
        logger.info(f"  {len(players)} players found in boxscore")

        for p in players:
            row = {
                "game_id": int(game_id),
                "game_date": date,
                "player_id": p["player_id"],
                "player_name": p["player_name"],
                "team": p["team"],
                "goals": p["goals"],
                "assists": p["assists"],
                "points": p["points"],
                "shots": p["shots"],
                "toi": p["toi"],
            }
            try:
                # Upsert: update if game_id + player_id already exists
                supabase.table("nhl_player_game_stats").upsert(
                    row, on_conflict="game_id,player_id"
                ).execute()
                total_players += 1
            except Exception as e:
                errors.append({"player": p["player_name"], "error": str(e)})

        time.sleep(0.3)  # Be gentle with the NHL API

    result = {
        "ok": True,
        "date": date,
        "games_processed": len(fixtures),
        "players_stored": total_players,
        "errors": errors,
    }
    logger.info(f"[NHL Stats] Done: {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NHL player game stats")
    parser.add_argument(
        "--date",
        default=(datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
        help="Game date YYYY-MM-DD (default: yesterday)",
    )
    args = parser.parse_args()
    result = fetch_and_store_game_stats(args.date)
    logger.info("Result: %s", result)
