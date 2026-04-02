from __future__ import annotations
"""
fetchers/live.py — Mise à jour live toutes les 5 minutes.

Football : API-Football /fixtures?live=all
  - Scores en temps réel
  - Événements : buts (buteur + passeur), cartons, remplacements
  - Statistiques équipes (tirs, possession, xG si dispo)

NHL : api-web.nhle.com/v1/scoreboard/now
  - Scores en temps réel
  - Buts marqués (buteur + passeurs)

Usage :
  python -m src.fetchers.live
"""

import time
from datetime import datetime, timezone

import requests

from src.config import api_get, logger, supabase

# ── NHL ───────────────────────────────────────────────────────────
NHL_API = "https://api-web.nhle.com/v1"


def _nhl_fetch(endpoint: str) -> dict | None:
    try:
        r = requests.get(f"{NHL_API}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"[Live/NHL] {endpoint} failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL — scores + events
# ═══════════════════════════════════════════════════════════════════

def _upsert_football_event(fixture_api_id: int, ev: dict) -> None:
    """Insert or ignore a single match event."""
    event_type = ev.get("type", "")
    event_detail = ev.get("detail", "")
    minute = ev.get("time", {}).get("elapsed")
    extra = ev.get("time", {}).get("extra")

    player = ev.get("player", {}) or {}
    assist = ev.get("assist", {}) or {}
    team = ev.get("team", {}) or {}

    row = {
        "fixture_api_id": fixture_api_id,
        "team_api_id": team.get("id"),
        "player_api_id": player.get("id"),
        "player_name": player.get("name"),
        "assist_player_api_id": assist.get("id"),
        "assist_player_name": assist.get("name"),
        "event_type": event_type,
        "event_detail": event_detail,
        "minute": minute,
        "extra_minute": extra,
    }

    # Upsert on (fixture_api_id, minute, player_api_id, event_type)
    try:
        existing = (
            supabase.table("match_events")
            .select("id")
            .eq("fixture_api_id", fixture_api_id)
            .eq("minute", minute)
            .eq("event_type", event_type)
            .eq("player_api_id", player.get("id") or 0)
            .execute()
        )
        if not existing.data:
            supabase.table("match_events").insert(row).execute()
    except Exception as e:
        logger.debug(f"[Live/Football] event insert error: {e}")


def update_football_live() -> dict:
    """Fetch all live football matches and update scores + events."""
    logger.info("[Live/Football] Fetching live fixtures...")

    data = api_get("fixtures", {"live": "all"})
    if not data:
        logger.info("[Live/Football] No live data returned.")
        return {"updated": 0, "events": 0}

    fixtures = data.get("response", [])
    if not fixtures:
        logger.info("[Live/Football] No live matches right now.")
        return {"updated": 0, "events": 0}

    logger.info(f"[Live/Football] {len(fixtures)} matches en cours.")
    updated = 0
    total_events = 0

    for fix in fixtures:
        fid = fix.get("fixture", {}).get("id")
        if not fid:
            continue

        status = fix.get("fixture", {}).get("status", {}).get("short", "")
        goals = fix.get("goals", {})
        elapsed = fix.get("fixture", {}).get("status", {}).get("elapsed") or 0

        # Find internal fixture id
        try:
            db_fix = (
                supabase.table("fixtures")
                .select("id")
                .eq("api_fixture_id", fid)
                .execute()
            )
            if not db_fix.data:
                continue
            internal_id = db_fix.data[0]["id"]
        except Exception:
            continue

        # Update score + status + elapsed minute
        try:
            supabase.table("fixtures").update({
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "status": status,
                "elapsed": elapsed,
            }).eq("id", internal_id).execute()
            updated += 1
        except Exception as e:
            logger.debug(f"[Live/Football] score update error fid={fid}: {e}")

        # Update events (goals, cards, subs)
        events = fix.get("events") or []
        for ev in events:
            _upsert_football_event(fid, ev)
            total_events += 1

        # Update team statistics if available
        stats_list = fix.get("statistics") or []
        if stats_list:
            stats_payload = {}
            for team_stats in stats_list:
                team_id = (team_stats.get("team") or {}).get("id")
                if not team_id:
                    continue
                parsed = {}
                for stat in (team_stats.get("statistics") or []):
                    key = (stat.get("type") or "").lower().replace(" ", "_")
                    parsed[key] = stat.get("value")
                stats_payload[str(team_id)] = parsed
            try:
                supabase.table("fixtures").update({
                    "live_stats_json": stats_payload,
                }).eq("id", internal_id).execute()
            except Exception as e:
                logger.warning("Failed to update live_stats_json for fixture %s: %s", fid, e)

    logger.info(f"[Live/Football] ✅ {updated} scores | {total_events} events")
    return {"updated": updated, "events": total_events}


# ═══════════════════════════════════════════════════════════════════
#  NHL — scores + buts
# ═══════════════════════════════════════════════════════════════════

def update_nhl_live() -> dict:
    """Fetch NHL scoreboard and update live scores + goals."""
    logger.info("[Live/NHL] Fetching scoreboard...")

    data = _nhl_fetch("/scoreboard/now")
    if not data:
        return {"updated": 0}

    games = data.get("games") or []
    if not games:
        logger.info("[Live/NHL] No NHL games right now.")
        return {"updated": 0}

    live_games = [g for g in games if g.get("gameState") in ("LIVE", "CRIT", "FINAL", "OFF")]
    logger.info(f"[Live/NHL] {len(live_games)} matchs actifs.")
    updated = 0

    for game in live_games:
        game_id = game.get("id")
        if not game_id:
            continue

        home = (game.get("homeTeam") or {})
        away = (game.get("awayTeam") or {})
        home_score = home.get("score", 0)
        away_score = away.get("score", 0)
        state = game.get("gameState", "")
        period = game.get("period", 0)
        clock = (game.get("clock") or {}).get("timeRemaining", "")

        try:
            supabase.table("nhl_fixtures").update({
                "home_score": home_score,
                "away_score": away_score,
                "status": state,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "stats_json": {
                    "period": period,
                    "clock": clock,
                    "home_sog": home.get("sog"),
                    "away_sog": away.get("sog"),
                },
            }).eq("api_fixture_id", game_id).execute()
            updated += 1
        except Exception as e:
            logger.debug(f"[Live/NHL] update error game={game_id}: {e}")

        # Fetch goal details via boxscore
        if state in ("FINAL", "OFF") or home_score + away_score > 0:
            _update_nhl_goals(game_id)

    logger.info(f"[Live/NHL] ✅ {updated} scores mis à jour")
    return {"updated": updated}


def _update_nhl_goals(game_id: int) -> None:
    """Fetch boxscore and upsert goal events for an NHL game."""
    data = _nhl_fetch(f"/gamecenter/{game_id}/boxscore")
    if not data:
        return

    goals = (data.get("summary") or {}).get("scoring") or []
    for period_data in goals:
        period = period_data.get("periodDescriptor", {}).get("number", 0)
        for goal in (period_data.get("goals") or []):
            scorer = goal.get("firstName", {}).get("default", "") + " " + goal.get("lastName", {}).get("default", "")
            scorer = scorer.strip()
            time_str = goal.get("timeInPeriod", "")
            assists = [
                a.get("firstName", {}).get("default", "") + " " + a.get("lastName", {}).get("default", "")
                for a in (goal.get("assists") or [])
            ]

            row = {
                "fixture_api_id": game_id,
                "event_type": "Goal",
                "player_name": scorer,
                "assist_player_name": ", ".join(a.strip() for a in assists) if assists else None,
                "minute": period,
                "event_detail": time_str,
                "team_api_id": (goal.get("teamAbbrev") or {}).get("default"),
            }

            try:
                existing = (
                    supabase.table("match_events")
                    .select("id")
                    .eq("fixture_api_id", game_id)
                    .eq("player_name", scorer)
                    .eq("minute", period)
                    .eq("event_detail", time_str)
                    .execute()
                )
                if not existing.data:
                    supabase.table("match_events").insert(row).execute()
            except Exception as e:
                logger.debug(f"[Live/NHL] goal insert error: {e}")


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def run() -> None:
    start = time.time()
    logger.info("=" * 50)
    logger.info("  ⚡ LIVE UPDATER — Football + NHL")
    logger.info("=" * 50)

    fb = update_football_live()
    nhl = update_nhl_live()

    elapsed = round(time.time() - start, 1)
    logger.info(f"  ✅ Terminé en {elapsed}s — Football: {fb} | NHL: {nhl}")


if __name__ == "__main__":
    run()
