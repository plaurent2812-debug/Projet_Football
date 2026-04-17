from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.config import SEASON, api_get, supabase

logger = logging.getLogger("probalab.players")
router = APIRouter(tags=["Players"])


def clean_player_data(raw_data: list) -> dict | None:
    if not raw_data:
        return None

    player_info = raw_data[0].get("player", {})
    statistics = raw_data[0].get("statistics", [])

    if not player_info or not statistics:
        return None

    # Get primary team from first stat entry (usually the main one)
    primary_team = statistics[0].get("team", {})

    # Restructure statistics to be easier to consume on the frontend
    stats_cleaned = []

    for stat in statistics:
        league = stat.get("league", {})
        games = stat.get("games", {})
        goals = stat.get("goals", {})
        shots = stat.get("shots", {})
        passes = stat.get("passes", {})
        tackles = stat.get("tackles", {})
        duels = stat.get("duels", {})
        dribbles = stat.get("dribbles", {})
        fouls = stat.get("fouls", {})
        cards = stat.get("cards", {})
        penalty = stat.get("penalty", {})

        stats_cleaned.append(
            {
                "league_id": league.get("id"),
                "league_name": league.get("name"),
                "league_logo": league.get("logo"),
                "team_id": stat.get("team", {}).get("id"),
                "team_name": stat.get("team", {}).get("name"),
                "team_logo": stat.get("team", {}).get("logo"),
                "appearances": games.get("appearences", 0),
                "lineups": games.get("lineups", 0),
                "minutes": games.get("minutes", 0),
                "rating": games.get("rating"),
                "goals": goals.get("total", 0),
                "assists": goals.get("assists", 0),
                "conceded": goals.get("conceded", 0),
                "saves": goals.get("saves", 0),
                "shots_total": shots.get("total", 0),
                "shots_on": shots.get("on", 0),
                "passes_total": passes.get("total", 0),
                "passes_key": passes.get("key", 0),
                "passes_accuracy": passes.get("accuracy", 0),
                "tackles_total": tackles.get("total", 0),
                "tackles_blocks": tackles.get("blocks", 0),
                "tackles_interceptions": tackles.get("interceptions", 0),
                "duels_total": duels.get("total", 0),
                "duels_won": duels.get("won", 0),
                "dribbles_attempts": dribbles.get("attempts", 0),
                "dribbles_success": dribbles.get("success", 0),
                "dribbles_past": dribbles.get("past", 0),
                "fouls_drawn": fouls.get("drawn", 0),
                "fouls_committed": fouls.get("committed", 0),
                "yellow": cards.get("yellow", 0),
                "yellowred": cards.get("yellowred", 0),
                "red": cards.get("red", 0),
                "penalty_won": penalty.get("won", 0),
                "penalty_committed": penalty.get("commited", 0),
                "penalty_scored": penalty.get("scored", 0),
                "penalty_missed": penalty.get("missed", 0),
                "penalty_saved": penalty.get("saved", 0),
            }
        )

    return {
        "player_id": player_info.get("id"),
        "name": player_info.get("name"),
        "firstname": player_info.get("firstname"),
        "lastname": player_info.get("lastname"),
        "age": player_info.get("age"),
        "nationality": player_info.get("nationality"),
        "height": player_info.get("height"),
        "weight": player_info.get("weight"),
        "photo": player_info.get("photo"),
        "position": statistics[0].get("games", {}).get("position"),
        "team_id": primary_team.get("id"),
        "team_name": primary_team.get("name"),
        "team_logo": primary_team.get("logo"),
        "stats_json": {"competitions": stats_cleaned},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{player_id}")
def get_player_profile(player_id: int):
    """
    Get detailed player profile and statistics.
    Checks cache in Supabase first to save API calls, refetches if > 7 days old.
    """
    try:
        # 1. Check database cache
        try:
            res = (
                supabase.table("football_players").select("*").eq("player_id", player_id).execute()
            )
        except Exception:
            # If the table doesn't exist yet, we catch the error and fallback to fetching without caching
            res = None

        db_player = res.data[0] if res and res.data else None

        if db_player:
            # Check elapsed time
            updated_at_str = db_player.get("updated_at")
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - updated_at).days
                    if age_days < 7:
                        # Return cached version
                        return {"source": "cache", "player": db_player}
                except ValueError:
                    pass

        # 2. Not in cache or too old -> Fetch from API-Football
        logger.info(f"Fetching fresh data for player {player_id}")
        raw_resp = api_get("players", {"id": player_id, "season": SEASON})

        if not raw_resp or "response" not in raw_resp or not raw_resp["response"]:
            if db_player:
                # Fallback to expired cache if API fails
                return {"source": "expired_cache", "player": db_player}
            raise HTTPException(status_code=404, detail="Player not found in API")

        cleaned_player = clean_player_data(raw_resp["response"])
        if not cleaned_player:
            raise HTTPException(status_code=404, detail="Could not parse player data")

        # 3. Update or Insert into database
        try:
            supabase.table("football_players").upsert(cleaned_player).execute()
            # If table doesn't exist, this will fail but we'll catch it and still return player
        except Exception as e:
            logger.warning(f"Could not cache player {player_id}: {e}")

        return {"source": "api", "player": cleaned_player}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error in players endpoint")
        raise HTTPException(status_code=500, detail="Internal error")
