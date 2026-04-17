"""
api/routers/teams.py — Team-related endpoints.

Provides team match history, roster data, and football meta-analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from src.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Teams"])


@router.get("/football/meta_analysis", summary="Get DeepThink strategic meta-analysis")
def get_football_meta_analysis(
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
):
    """Return the DeepThink strategic meta-analysis for football matches."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Try dedicated table first
    try:
        resp = (
            supabase.table("football_meta_analysis").select("*").eq("date", date).limit(1).execute()
        )
        if resp.data and len(resp.data) > 0:
            row = resp.data[0]
            analysis = row.get("analysis", "")
            if analysis and len(analysis) > 50:
                return {"ok": True, "date": date, "analysis": analysis, "source": "deepthink"}
    except Exception:
        pass

    # Fallback: check predictions table for special meta row
    try:
        resp = (
            supabase.table("predictions")
            .select("analysis_text, recommended_bet")
            .eq("fixture_id", "00000000-0000-0000-0000-000000000000")
            .eq("model_version", "deepthink_meta")
            .limit(1)
            .execute()
        )
        if resp.data and len(resp.data) > 0:
            row = resp.data[0]
            analysis = row.get("analysis_text", "")
            bet_date = (row.get("recommended_bet") or "").replace("DeepThink ", "")
            if analysis and len(analysis) > 50 and bet_date == date:
                return {
                    "ok": True,
                    "date": date,
                    "analysis": analysis,
                    "source": "deepthink_fallback",
                }
    except Exception:
        pass

    return {"ok": False, "date": date, "analysis": None, "source": None}


@router.get("/team/{team_name}/history")
def get_team_history(team_name: str, limit: int = Query(60, ge=1, le=100)):
    """Get the finished matches for a given team in the current season."""
    # Query home matches
    home_matches = (
        supabase.table("fixtures")
        .select("*")
        .eq("home_team", team_name)
        .eq("status", "FT")
        .order("date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    # Query away matches
    away_matches = (
        supabase.table("fixtures")
        .select("*")
        .eq("away_team", team_name)
        .eq("status", "FT")
        .order("date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    # Merge and sort by date desc, keep top N
    all_matches = sorted(
        home_matches + away_matches, key=lambda x: x.get("date", ""), reverse=True
    )[:limit]

    # Compute result from team's perspective
    results = []
    wins, draws, losses = 0, 0, 0
    current_streak = {"type": None, "count": 0}

    for m in all_matches:
        hg = m.get("home_goals", 0) or 0
        ag = m.get("away_goals", 0) or 0
        is_home = m["home_team"] == team_name
        opponent = m["away_team"] if is_home else m["home_team"]
        score = f"{hg}-{ag}"

        if is_home:
            result = "V" if hg > ag else ("N" if hg == ag else "D")
        else:
            result = "V" if ag > hg else ("N" if hg == ag else "D")

        if result == "V":
            wins += 1
        elif result == "N":
            draws += 1
        else:
            losses += 1

        # Track streak
        if current_streak["type"] is None:
            current_streak = {"type": result, "count": 1}
        elif current_streak["type"] == result:
            current_streak["count"] += 1

        results.append(
            {
                "fixture_id": m.get("id"),
                "date": m.get("date", "")[:10],
                "opponent": opponent,
                "score": score,
                "result": result,
                "home_away": "D" if is_home else "E",
                "league_id": m.get("league_id"),
            }
        )

    return {
        "team_name": team_name,
        "matches": results,
        "summary": {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "total": len(results),
            "streak": current_streak,
        },
    }


@router.get("/team/{team_name}/roster")
def get_team_roster(team_name: str):
    """Get the current roster for a given team via player squads."""
    # First, need to lookup the team api_id to use api-football squads endpoint
    team_data = (
        supabase.table("teams").select("api_id").eq("name", team_name).limit(1).execute().data
    )

    if not team_data or not team_data[0].get("api_id"):
        # Attempt fallback to fixtures if team not in teams table
        fix_data = (
            supabase.table("fixtures")
            .select("home_team_id")
            .eq("home_team", team_name)
            .limit(1)
            .execute()
            .data
        )
        if not fix_data or not fix_data[0].get("home_team_id"):
            raise HTTPException(status_code=404, detail="Team API ID not found")
        team_api_id = fix_data[0]["home_team_id"]
    else:
        team_api_id = team_data[0]["api_id"]

    try:
        from src.config import SEASON, api_get

        # The players/squads endpoint returns the current squad of a team
        resp = api_get("players/squads", {"team": team_api_id})
        if not resp or not resp.get("response"):
            return {"team_name": team_name, "roster": []}

        roster_data = resp["response"][0].get("players", [])

        # --- Fetch season stats ---
        try:
            stats_data = (
                supabase.table("player_season_stats")
                .select("player_api_id, appearances, goals, assists, goals_conceded")
                .eq("team_api_id", team_api_id)
                .eq("season", SEASON)
                .execute()
                .data
            )
            if stats_data:
                stats_map = {}
                for s in stats_data:
                    p_id = s["player_api_id"]
                    if p_id not in stats_map:
                        stats_map[p_id] = {
                            "appearances": 0,
                            "goals": 0,
                            "assists": 0,
                            "goals_conceded": 0,
                        }
                    stats_map[p_id]["appearances"] += s.get("appearances") or 0
                    stats_map[p_id]["goals"] += s.get("goals") or 0
                    stats_map[p_id]["assists"] += s.get("assists") or 0
                    stats_map[p_id]["goals_conceded"] += s.get("goals_conceded") or 0

                for player in roster_data:
                    p_id = player.get("id")
                    if p_id in stats_map:
                        player["appearances"] = stats_map[p_id]["appearances"]
                        player["goals"] = stats_map[p_id]["goals"]
                        player["assists"] = stats_map[p_id]["assists"]
                        player["goals_conceded"] = stats_map[p_id]["goals_conceded"]
        except Exception:
            logger.warning("Error fetching roster stats for team=%s", team_name, exc_info=True)

        return {"team_name": team_name, "roster": roster_data}
    except Exception:
        logger.exception("Error fetching roster for team=%s", team_name)
        raise HTTPException(status_code=500, detail="Error fetching roster")
