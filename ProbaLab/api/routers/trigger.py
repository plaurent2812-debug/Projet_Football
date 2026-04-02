from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.brain import ask_gemini, extract_json
from src.config import api_get, logger, supabase

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ─── Telegram Config ────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")


def _send_telegram_alert(home: str, away: str, analysis: str, bet: str, confidence: int) -> bool:
    """Disabled — Telegram alert notifications removed."""
    return False


import hmac

from fastapi import Depends, Header

CRON_SECRET = os.getenv("CRON_SECRET", "")


def verify_trigger_auth(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()

    # 1. Check CRON Secret (for Trigger.dev worker)
    if CRON_SECRET and hmac.compare_digest(token, CRON_SECRET):
        return True

    # 2. Check Admin JWT (for Dashboard)
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise ValueError("Invalid JWT")

        user_id = user_res.user.id
        db_user = supabase.table("profiles").select("role").eq("id", user_id).execute().data
        if not db_user or db_user[0].get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: Admin only")

    except Exception as e:
        logger.error("[Auth] token verification failed: %s", e, exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=403, detail="Invalid token or unauthorized")

    return True


router = APIRouter(
    prefix="/api/trigger", tags=["Trigger"], dependencies=[Depends(verify_trigger_auth)]
)


class RoleUpdate(BaseModel):
    role: str


class AnalyzeRequest(BaseModel):
    fixture_id: str


# ─── Admin User Management ──────────────────────────────────────


@router.get("/admin/users")
def admin_list_users():
    """List all user profiles (admin only)."""
    result = (
        supabase.table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return {"users": result.data or []}


@router.put("/admin/users/{user_id}/role")
def admin_update_role(user_id: str, body: RoleUpdate):
    """Update a user's role (admin only)."""
    if body.role not in ("free", "premium", "admin"):
        raise HTTPException(status_code=400, detail="Role must be free, premium, or admin")
    result = (
        supabase.table("profiles")
        .update({"role": body.role})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "user": result.data[0]}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: str):
    """Delete a user from auth.users and profiles (admin only)."""
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        logger.warning(f"[Admin] Auth delete failed for {user_id}: {e}")

    try:
        supabase.table("profiles").delete().eq("id", user_id).execute()
    except Exception as e:
        logger.warning(f"[Admin] Profile delete failed for {user_id}: {e}")

    return {"status": "ok", "deleted": user_id}


@router.get("/admin/stats")
def admin_stats():
    """Site-wide KPIs for admin overview."""
    from datetime import datetime, timedelta

    today = datetime.utcnow().strftime("%Y-%m-%d")
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    stats = {}
    try:
        # User counts
        profiles = supabase.table("profiles").select("role", count="exact").execute()
        stats["total_users"] = profiles.count or len(profiles.data or [])
        roles = {}
        for p in profiles.data or []:
            r = p.get("role", "free")
            roles[r] = roles.get(r, 0) + 1
        stats["users_by_role"] = roles

        # Today's predictions
        preds_today = supabase.table("predictions").select("id", count="exact").gte("created_at", today).execute()
        stats["predictions_today"] = preds_today.count or len(preds_today.data or [])

        # Today's fixtures
        fixtures_today = supabase.table("fixtures").select("id", count="exact").gte("match_date", today).lte("match_date", today + "T23:59:59").execute()
        stats["matches_today"] = fixtures_today.count or len(fixtures_today.data or [])

        # Total predictions all time
        preds_all = supabase.table("predictions").select("id", count="exact").execute()
        stats["predictions_total"] = preds_all.count or len(preds_all.data or [])

        # Recent signups (last 7 days)
        recent = supabase.table("profiles").select("id", count="exact").gte("created_at", week_ago).execute()
        stats["signups_last_7d"] = recent.count or len(recent.data or [])

    except Exception as e:
        logger.error(f"[Admin] Stats error: {e}")

    return stats


@router.get("/admin/api-quota")
def admin_api_quota():
    """Check API-Football remaining quota."""
    import requests as req_lib
    try:
        api_key = os.getenv("API_FOOTBALL_KEY", "")
        if not api_key:
            try:
                from src.config import API_FOOTBALL_KEY
                api_key = API_FOOTBALL_KEY or ""
            except Exception:
                pass
        if not api_key:
            return {"error": "API_FOOTBALL_KEY not configured"}

        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": api_key,
        }
        resp = req_lib.get(
            "https://v3.football.api-sports.io/status",
            headers=headers,
            timeout=10,
        )
        raw = resp.json()
        logger.info(f"[Admin] API-Football status raw: {raw}")

        response = raw.get("response", {}) if isinstance(raw, dict) else {}
        if isinstance(response, list) and len(response) > 0:
            response = response[0]
        if not isinstance(response, dict):
            return {"error": "Unexpected response format", "raw": raw}

        account = response.get("account", {})
        requests_info = response.get("requests", {})
        subscription = response.get("subscription", {})

        current = int(requests_info.get("current", 0))
        limit_day = int(requests_info.get("limit_day", 0))

        return {
            "current": current,
            "limit_day": limit_day,
            "remaining": max(0, limit_day - current),
            "plan": subscription.get("plan", "unknown"),
            "end": subscription.get("end", ""),
            "firstname": account.get("firstname", ""),
        }
    except Exception as e:
        logger.error("[Admin] API quota check error: %s", e, exc_info=True)
        return {"error": "Failed to check API quota"}


@router.get("/admin/leagues")
def admin_get_leagues():
    """Get currently tracked leagues."""
    from src.config import LEAGUES
    return {"leagues": LEAGUES}

SYSTEM_PROMPT = """Tu es un expert en paris sportifs spécialisé dans le Live Betting.
On te fournit les statistiques à la mi-temps d'un match (tirs, possession, xG, corners, score).
Ton but est de proposer une analyse courte et percutante (3 phrases max) si tu détectes
une anomalie statistique exploitable, et de suggérer le meilleur pari Live.

IMPORTANT : Réponds UNIQUEMENT avec un JSON valide.
{
  "analysis_text": "L'équipe à domicile a 1.8 xG mais 0 but, 8 tirs cadrés et 70% de possession. Le match devrait tourner en seconde période.",
  "recommended_bet": "Victoire Equipe Domicile ou Prochain But Domicile",
  "confidence_score": 8
}
"""


# ─── Helper ─────────────────────────────────────────────────────
def _get_stat(team_stats: dict, stat_type: str) -> float:
    """Extract a stat value from API-Football statistics response."""
    for s in team_stats.get("statistics", []):
        if s["type"] == stat_type:
            val = s["value"]
            if val is None:
                return 0.0
            if isinstance(val, str) and "%" in val:
                return float(val.replace("%", ""))
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
    return 0.0


def _detect_anomalies(t1: dict, t2: dict, score_home: int, score_away: int) -> list[str]:
    """Multi-criteria anomaly detection. Returns a list of triggered anomaly labels.
    An alert is fired if >= 2 anomalies are detected.
    """
    anomalies = []

    t1_shots = _get_stat(t1, "Shots on Goal")
    t2_shots = _get_stat(t2, "Shots on Goal")
    t1_xg = _get_stat(t1, "expected_goals")
    t2_xg = _get_stat(t2, "expected_goals")
    t1_poss = _get_stat(t1, "Ball Possession")
    t2_poss = _get_stat(t2, "Ball Possession")
    t1_corners = _get_stat(t1, "Corner Kicks")
    t2_corners = _get_stat(t2, "Corner Kicks")
    t1_total_shots = _get_stat(t1, "Total Shots")
    t2_total_shots = _get_stat(t2, "Total Shots")

    t1_name = t1.get("team", {}).get("name", "Team1")
    t2_name = t2.get("team", {}).get("name", "Team2")

    # ── Critère 1 : xG élevé mais aucun but ──────────────────────
    if t1_xg >= 1.2 and score_home == 0:
        anomalies.append(f"{t1_name} a {t1_xg} xG mais 0 but")
    if t2_xg >= 1.2 and score_away == 0:
        anomalies.append(f"{t2_name} a {t2_xg} xG mais 0 but")

    # ── Critère 2 : Domination aux tirs cadrés ───────────────────
    if t1_shots >= t2_shots + 4:
        anomalies.append(f"{t1_name} domine aux tirs cadrés ({int(t1_shots)} vs {int(t2_shots)})")
    elif t2_shots >= t1_shots + 4:
        anomalies.append(f"{t2_name} domine aux tirs cadrés ({int(t2_shots)} vs {int(t1_shots)})")

    # ── Critère 3 : Score inversé (équipe dominante perd ou fait nul) ──
    t1_dominance = (t1_shots > t2_shots + 2) and (t1_poss >= 55)
    t2_dominance = (t2_shots > t1_shots + 2) and (t2_poss >= 55)
    if t1_dominance and score_home <= score_away:
        anomalies.append(f"{t1_name} domine mais ne mène pas ({score_home}-{score_away})")
    if t2_dominance and score_away <= score_home:
        anomalies.append(f"{t2_name} domine mais ne mène pas ({score_home}-{score_away})")

    # ── Critère 4 : Écart de corners flagrant (pression constante) ──
    if t1_corners >= t2_corners + 5:
        anomalies.append(f"{t1_name} a {int(t1_corners)} corners vs {int(t2_corners)}")
    elif t2_corners >= t1_corners + 5:
        anomalies.append(f"{t2_name} a {int(t2_corners)} corners vs {int(t1_corners)}")

    # ── Critère 5 : Volume de tirs total écrasant ────────────────
    if t1_total_shots >= t2_total_shots + 8:
        anomalies.append(f"{t1_name} a tiré {int(t1_total_shots)} fois vs {int(t2_total_shots)}")
    elif t2_total_shots >= t1_total_shots + 8:
        anomalies.append(f"{t2_name} a tiré {int(t2_total_shots)} fois vs {int(t1_total_shots)}")

    return anomalies


# ─── Routes ─────────────────────────────────────────────────────


@router.get("/daily-matches")
def get_daily_matches():
    """Returns all matches planned for today that haven't started yet."""
    today = datetime.now().strftime("%Y-%m-%d")
    fixtures = (
        supabase.table("fixtures")
        .select("id, api_fixture_id, date, home_team, away_team")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .in_("status", ["NS", "TBD"])
        .execute()
        .data
        or []
    )
    return {"date": today, "matches": fixtures}


@router.post("/analyze-halftime")
def analyze_halftime(req: AnalyzeRequest):
    """Fetches half-time stats, detects anomalies with multi-criteria, and triggers AI if needed."""
    logger.info(f"[Live] Analyze halftime triggered for fixture {req.fixture_id}")

    # 1. Get fixture from DB
    fixture_data = supabase.table("fixtures").select("*").eq("id", req.fixture_id).execute().data
    if not fixture_data:
        raise HTTPException(status_code=404, detail="Fixture not found")

    fixture = fixture_data[0]
    api_id = fixture["api_fixture_id"]

    # 2. Get live stats from API-Football
    stats_resp = api_get("fixtures/statistics", {"fixture": api_id})
    if not stats_resp or not stats_resp.get("response"):
        return {"status": "skipped", "message": "No live stats available"}

    stats_list = stats_resp["response"]
    if len(stats_list) < 2:
        return {"status": "skipped", "message": "Incomplete live stats"}

    team1 = stats_list[0]
    team2 = stats_list[1]

    # 3. Get current score from API-Football
    score_resp = api_get("fixtures", {"id": api_id})
    score_home, score_away = 0, 0
    if score_resp and score_resp.get("response"):
        goals = score_resp["response"][0].get("goals", {})
        score_home = goals.get("home", 0) or 0
        score_away = goals.get("away", 0) or 0

    # 4. Multi-criteria anomaly detection (need >= 2 triggers)
    anomalies = _detect_anomalies(team1, team2, score_home, score_away)
    logger.info(
        f"[Live] {fixture['home_team']} vs {fixture['away_team']}: {len(anomalies)} anomalies détectées"
    )

    if len(anomalies) < 2:
        return {
            "status": "no_anomaly",
            "anomalies_found": len(anomalies),
            "details": anomalies,
            "message": "Pas assez d'anomalies détectées (minimum 2 requises).",
        }

    # 5. Build rich prompt for Claude
    t1_name = team1.get("team", {}).get("name", fixture["home_team"])
    t2_name = team2.get("team", {}).get("name", fixture["away_team"])

    user_prompt = f"""
MATCH: {fixture["home_team"]} vs {fixture["away_team"]}
SCORE MI-TEMPS: {score_home} - {score_away}

STATISTIQUES MI-TEMPS:
[{t1_name}]
- Possession: {_get_stat(team1, "Ball Possession")}%
- Tirs Cadrés: {int(_get_stat(team1, "Shots on Goal"))}
- Tirs Totaux: {int(_get_stat(team1, "Total Shots"))}
- xG: {_get_stat(team1, "expected_goals")}
- Corners: {int(_get_stat(team1, "Corner Kicks"))}

[{t2_name}]
- Possession: {_get_stat(team2, "Ball Possession")}%
- Tirs Cadrés: {int(_get_stat(team2, "Shots on Goal"))}
- Tirs Totaux: {int(_get_stat(team2, "Total Shots"))}
- xG: {_get_stat(team2, "expected_goals")}
- Corners: {int(_get_stat(team2, "Corner Kicks"))}

ANOMALIES DÉTECTÉES:
{chr(10).join(f"⚠️ {a}" for a in anomalies)}

Analyse ces anomalies et recommande le meilleur pari en direct. Retourne le JSON.
    """

    ai_text = ask_gemini(SYSTEM_PROMPT, user_prompt)
    ai_result = extract_json(ai_text) if ai_text else None

    if not ai_result:
        return {"status": "error", "message": "AI failed to return valid JSON"}

    # 6. Save to live_alerts
    alert_text = ai_result.get("analysis_text", "")
    alert_bet = ai_result.get("recommended_bet", "")
    alert_confidence = ai_result.get("confidence_score", 5)

    supabase.table("live_alerts").insert(
        {
            "fixture_id": req.fixture_id,
            "analysis_text": alert_text,
            "recommended_bet": alert_bet,
            "confidence_score": alert_confidence,
        }
    ).execute()

    # 7. Send Telegram notification
    _send_telegram_alert(
        home=fixture["home_team"],
        away=fixture["away_team"],
        analysis=alert_text,
        bet=alert_bet,
        confidence=alert_confidence,
    )

    logger.info(f"[Live] 🔥 ALERTE CRÉÉE pour {fixture['home_team']} vs {fixture['away_team']}")
    return {"status": "alert_created", "anomalies": anomalies, "alert": ai_result}


@router.get("/check-active-matches")
def check_active_matches():
    """Lite check to see if we have any active or upcoming matches.
    Used by Trigger.dev to skip useless runs and save compute costs.
    """
    from datetime import timedelta
    now_utc = datetime.utcnow()
    next_15m = (now_utc + timedelta(minutes=15)).isoformat()
    today_start = now_utc.replace(hour=0, minute=0, second=0).isoformat()
    today_end = now_utc.replace(hour=23, minute=59, second=59).isoformat()

    # 1. Check for LIVE matches in DB
    active_statuses = ["1H", "2H", "HT", "ET", "LIVE", "BT"]
    res_active = supabase.table("fixtures").select("id", count="exact").in_("status", active_statuses).execute()
    has_active = (res_active.count or 0) > 0

    # 2. Check for matches starting in the next 15 mins
    res_upcoming = supabase.table("fixtures").select("id", count="exact").eq("status", "NS").gte("date", now_utc.isoformat()).lte("date", next_15m).execute()
    has_upcoming = (res_upcoming.count or 0) > 0

    # 3. Quick NHL check (16h-08h UTC)
    hour = now_utc.hour
    nhl_active_window = (hour >= 16 or hour <= 8)

    return {
        "active": has_active,
        "upcoming_soon": has_upcoming,
        "nhl_window": nhl_active_window,
        "summary": "Skip if not active and not upcoming and not in NHL window"
    }


# ─── Live Scores Update ─────────────────────────────────────────


@router.post("/update-live-scores")
def update_live_scores(detail: bool = Query(False, description="Fetch events & stats (every 5 min)")):
    """Fetch all live scores from API-Football and update Supabase fixtures table.
    
    When detail=False (default): only updates score/status/elapsed (1 API call).
    When detail=True: also fetches events, stats, and checks stale matches.
    """
    logger.info(f"[Live Scores] Fetching live fixtures (detail={detail})...")

    resp = api_get("fixtures", {"live": "all"})
    live_fixtures = resp.get("response", []) if resp else []

    if not live_fixtures:
        logger.info("[Live Scores] No live matches found.")
        return {"status": "ok", "updated": 0, "finished": 0, "errors": 0, "total_live": 0}

    # Map API status to our status codes
    status_map = {
        "1H": "1H", "HT": "HT", "2H": "2H", "ET": "ET", "P": "PEN",
        "FT": "FT", "AET": "FT", "PEN": "FT", "BT": "BT",
        "SUSP": "SUSP", "INT": "INT", "LIVE": "LIVE",
    }

    batch_updates = []
    errors = 0
    live_api_ids = set()

    # Optimization: Fetch existing fixtures in one go to get their internal IDs
    api_ids = [str(lf.get("fixture", {}).get("id")) for lf in live_fixtures if lf.get("fixture", {}).get("id")]
    existing_map = {}
    if api_ids:
        db_res = supabase.table("fixtures").select("id, api_fixture_id").in_("api_fixture_id", api_ids).execute()
        existing_map = {str(item["api_fixture_id"]): item["id"] for item in db_res.data or []}

    for lf in live_fixtures:
        api_fixture_id = lf.get("fixture", {}).get("id")
        if not api_fixture_id: continue
        
        live_api_ids.add(api_fixture_id)
        internal_id = existing_map.get(str(api_fixture_id))
        if not internal_id: continue # Match not in our DB, ignore

        goals = lf.get("goals", {})
        status_short = lf.get("fixture", {}).get("status", {}).get("short", "")

        update_data = {
            "id": internal_id, # Required for upsert to update
            "api_fixture_id": api_fixture_id,
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "status": status_map.get(status_short, status_short),
            "elapsed": lf.get("fixture", {}).get("status", {}).get("elapsed"),
        }

        # Detailed fetch (every 10 min)
        if detail:
            # Events
            try:
                events_resp = api_get("fixtures/events", {"fixture": api_fixture_id})
                if events_resp and events_resp.get("response"):
                    goals_list = []
                    for ev in events_resp["response"]:
                        if ev.get("type") == "Goal" and ev.get("comments") != "Penalty Shootout":
                            assist = ev.get("assist", {}) or {}
                            goals_list.append({
                                "team": ev.get("team", {}).get("name", ""),
                                "player": ev.get("player", {}).get("name", ""),
                                "player_id": ev.get("player", {}).get("id"),
                                "assist": assist.get("name"),
                                "assist_id": assist.get("id"),
                                "time": ev.get("time", {}).get("elapsed", ""),
                                "detail": ev.get("detail", ""),
                                "half": "1H" if (ev.get("time", {}).get("elapsed", 0) or 0) <= 45 else "2H",
                            })
                    update_data["events_json"] = goals_list
            except Exception: pass

            # Stats
            try:
                stats_resp = api_get("fixtures/statistics", {"fixture": api_fixture_id})
                if stats_resp and stats_resp.get("response"):
                    live_stats = {}
                    for team_stats in stats_resp["response"]:
                        team_name = team_stats.get("team", {}).get("name", "")
                        side = "home" if team_name == lf.get("teams", {}).get("home", {}).get("name") else "away"
                        stats_dict = {s.get("type", ""): s.get("value") for s in team_stats.get("statistics", [])}
                        live_stats[side] = {
                            "team": team_name,
                            "shots_total": stats_dict.get("Total Shots"),
                            "shots_on": stats_dict.get("Shots on Goal"),
                            "possession": stats_dict.get("Ball Possession"),
                            "corners": stats_dict.get("Corner Kicks"),
                            "xg": stats_dict.get("expected_goals"),
                        }
                    update_data["live_stats_json"] = live_stats
            except Exception: pass

        batch_updates.append(update_data)

    # Perform batch update
    updated_count = 0
    if batch_updates:
        try:
            supabase.table("fixtures").upsert(batch_updates).execute()
            updated_count = len(batch_updates)
        except Exception as e:
            logger.error(f"[Live Scores] Batch update error: {e}")
            errors = len(batch_updates)

    # ── 2nd pass: detect recently finished matches (only in detail mode) ──
    if not detail:
        logger.info(f"[Live Scores] ✅ Quick update: {updated_count} fixtures synchronized.")
        return {"status": "ok", "updated": updated_count, "finished": 0, "errors": errors, "total_live": len(live_fixtures)}

    # Fixtures in our DB marked as live/NS but no longer in the API live response
    today = datetime.now().strftime("%Y-%m-%d")
    stale_statuses = ["1H", "2H", "HT", "ET", "LIVE", "BT", "NS"]
    try:
        stale_fixtures = (
            supabase.table("fixtures")
            .select("id, api_fixture_id, status")
            .gte("date", f"{today}T00:00:00Z")
            .lt("date", f"{today}T23:59:59Z")
            .in_("status", stale_statuses)
            .execute()
            .data
            or []
        )
    except Exception:
        stale_fixtures = []

    finished_count = 0
    for sf in stale_fixtures:
        sf_api_id = sf.get("api_fixture_id")
        if not sf_api_id or sf_api_id in live_api_ids:
            continue  # Still live or no API ID

        # This match is marked live in DB but not in API — it just finished
        try:
            import time as _time

            fix_resp = api_get("fixtures", {"id": sf_api_id})
            _time.sleep(0.3)
            if not fix_resp or not fix_resp.get("response"):
                continue

            fix_data = fix_resp["response"][0]
            api_status = fix_data.get("fixture", {}).get("status", {}).get("short", "")
            goals = fix_data.get("goals", {})

            status_map = {
                "FT": "FT",
                "AET": "FT",
                "PEN": "FT",
                "NS": "NS",
                "PST": "POST",
                "CANC": "CANC",
                "1H": "1H",
                "2H": "2H",
                "HT": "HT",
            }
            final_status = status_map.get(api_status, api_status)

            update_data = {
                "status": final_status,
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
            }

            # Also fetch events for the finished match
            try:
                events_resp = api_get("fixtures/events", {"fixture": sf_api_id})
                _time.sleep(0.3)
                if events_resp and events_resp.get("response"):
                    raw_events = events_resp["response"]
                    goals_list = []
                    for ev in raw_events:
                        if ev.get("type") == "Goal" and ev.get("comments") != "Penalty Shootout":
                            goals_list.append(
                                {
                                    "team": ev.get("team", {}).get("name", ""),
                                    "player": ev.get("player", {}).get("name", ""),
                                    "player_id": ev.get("player", {}).get("id"),
                                    "assist": ev.get("assist", {}).get("name", "")
                                    if ev.get("assist")
                                    else "",
                                    "assist_id": ev.get("assist", {}).get("id")
                                    if ev.get("assist")
                                    else None,
                                    "time": ev.get("time", {}).get("elapsed", ""),
                                    "extra_time": ev.get("time", {}).get("extra"),
                                    "detail": ev.get("detail", ""),
                                    "half": "1H"
                                    if (ev.get("time", {}).get("elapsed", 0) or 0) <= 45
                                    else "2H",
                                }
                            )
                    update_data["events_json"] = goals_list
            except Exception:
                pass

            supabase.table("fixtures").update(update_data).eq("api_fixture_id", sf_api_id).execute()
            finished_count += 1
            logger.info(
                f"[Live Scores] 🏁 Match {sf_api_id} terminé → {final_status} ({goals.get('home')}-{goals.get('away')})"
            )
        except Exception as e:
            logger.error(f"[Live Scores] Error finishing {sf_api_id}: {e}")

    logger.info(
        f"[Live Scores] ✅ {updated_count} live mis à jour, {finished_count} terminés, {errors} erreurs"
    )
    return {
        "status": "ok",
        "updated": updated_count,
        "finished": finished_count,
        "errors": errors,
        "total_live": len(live_fixtures),
    }


@router.post("/evaluate-performance")
def evaluate_performance():
    """Trigger immediate performance evaluation for all recently finished football matches."""
    logger.info("[Performance] 📈 Évaluation des performances ML (Brier/LogLoss)...")
    try:
        from api.evaluate_predictions import evaluate_recent_matches

        evaluate_recent_matches(days_back=3)
        return {"status": "ok", "message": "ML Evaluation successfully run"}
    except Exception as e:
        logger.error(f"[Performance] Error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/retrain-models")
def retrain_models():
    """Endpoint for Trigger.dev or Vertex AI to trigger a full ML model retraining."""
    logger.info("[MLOps] 🚀 Déclenchement du réentrainement continu...")
    try:
        # 1. Build new training data vectors
        from src.training import build_data

        build_data.run(rebuild=False)

        # 2. Retrain the XGBoost models and push them to Supabase
        from src.training import train

        train.run()

        return {"status": "ok", "message": "ML Models successfully retrained and deployed"}
    except Exception as e:
        logger.error(f"[MLOps] Retraining Failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/retrain-meta-model")
def retrain_meta_model():
    """Endpoint for Trigger.dev to trigger XGBoost Meta-Model training (Phase 2 & 3)."""
    logger.info("[MLOps] 🚀 Déclenchement du réentrainement Méta-Modèle XGBoost...")
    try:
        from src.training.prepare_meta_dataset import extract_meta_dataset
        from src.training.train_meta_1x2 import train_meta_1x2

        # 1. Extraction des données (jointure Predictions + Fixtures réelles)
        dataset_path = "meta_dataset.csv"
        df = extract_meta_dataset()
        if df.empty:
            return {"status": "skipped", "message": "Pas assez de données pour l'entraînement Meta"}
        
        df.to_csv(dataset_path, index=False)

        # 2. Entraînement et Sauvegarde du Modèle
        metrics = train_meta_1x2(dataset_path=dataset_path, model_dir="models/football")

        # 3. Notification Telegram
        if metrics:
            msg = (
                f"🤖 *XGBoost Meta-Modèle Ré-entraîné*\n\n"
                f"📊 *Échantillons :* {metrics['samples']} matchs\n"
                f"🎯 *Log Loss (CV) :* {metrics['log_loss']}\n"
                f"✅ *Accuracy (CV) :* {metrics['accuracy'] * 100:.1f}%\n\n"
                f"Le modèle a été mis à jour avec succès en production."
            )
            _send_telegram_message(msg)

        return {"status": "ok", "message": "XGBoost Meta-Model successfully retrained and saved", "metrics": metrics}
    except Exception as e:
        logger.error(f"[MLOps] Meta-Model Retraining Failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/nhl-retrain-model")
def nhl_retrain_model():
    """Retrain NHL match-level XGBoost models (Win + Over 5.5)."""
    logger.info("[MLOps] 🏒🧠 NHL Match ML Retraining...")
    try:
        from src.nhl.train_match import train_nhl_match_models

        result = train_nhl_match_models()

        if result.get("success"):
            metrics = result.get("metrics", {})
            msg = (
                f"🏒🧠 *NHL XGBoost Match ML Retrained*\n\n"
                f"📊 *Échantillons :* {result['n_samples']} matchs\n"
            )
            for name, m in metrics.items():
                msg += f"🎯 *{name}* : Acc={m['accuracy']:.1%} | Brier={m['brier_score']:.4f}\n"
            _send_telegram_message(msg)

        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"[MLOps] NHL Retraining Failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/fetch-lineups")
def fetch_lineups():
    """Fetch H-1 lineups for upcoming matches and store in Supabase."""
    import time as _time
    from datetime import datetime, timedelta, timezone

    logger.info("[Lineups] 🧤 Fetching upcoming match lineups...")

    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(minutes=30)).isoformat()
    window_end = (now + timedelta(minutes=90)).isoformat()

    try:
        fixtures = (
            supabase.table("fixtures")
            .select("id, api_fixture_id, home_team, away_team, date, stats_json")
            .gte("date", window_start)
            .lte("date", window_end)
            .in_("status", ["NS", "1H", "HT", "2H"])
            .execute()
            .data
            or []
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

    fetched = 0
    for fix in fixtures:
        api_id = fix.get("api_fixture_id")
        if not api_id:
            continue

        # Skip if lineups already fetched
        existing_stats = fix.get("stats_json") or {}
        if existing_stats.get("lineups_fetched"):
            continue

        try:
            resp = api_get("fixtures/lineups", {"fixture": api_id})
            _time.sleep(0.5)

            if not resp or not resp.get("response"):
                continue

            raw_lineups = resp["response"]
            lineups = {}

            for team_data in raw_lineups:
                team_name = team_data.get("team", {}).get("name", "")
                is_home = team_name == fix.get("home_team", "")
                side = "home" if is_home else "away"
                formation = team_data.get("formation", "N/A")
                coach = team_data.get("coach", {}).get("name", "")
                starters = [
                    {
                        "name": p.get("player", {}).get("name", ""),
                        "player_id": p.get("player", {}).get("id"),
                        "number": p.get("player", {}).get("number", ""),
                        "pos": p.get("player", {}).get("pos", ""),
                        "grid": p.get("player", {}).get("grid", ""),
                    }
                    for p in team_data.get("startXI", [])
                ]
                substitutes = [
                    {
                        "name": p.get("player", {}).get("name", ""),
                        "player_id": p.get("player", {}).get("id"),
                        "number": p.get("player", {}).get("number", ""),
                        "pos": p.get("player", {}).get("pos", ""),
                    }
                    for p in team_data.get("substitutes", [])
                ]
                lineups[side] = {
                    "team": team_name,
                    "formation": formation,
                    "coach": coach,
                    "starters": starters,
                    "substitutes": substitutes,
                }

            if lineups:
                existing_stats["lineups"] = lineups
                existing_stats["lineups_fetched"] = True
                existing_stats["lineups_fetched_at"] = now.isoformat()

                supabase.table("fixtures").update({"stats_json": existing_stats}).eq(
                    "id", fix["id"]
                ).execute()

                logger.info(
                    f"[Lineups] ✅ Lineups for {fix.get('home_team')} vs {fix.get('away_team')} saved"
                )
                fetched += 1
        except Exception as e:
            logger.warning(f"[Lineups] Error for {api_id}: {e}")

    return {"status": "ok", "fetched": fetched}


# ─── Generic Telegram sender ────────────────────────────────────


def _send_telegram_message(text: str) -> bool:
    """Disabled — Telegram spam notifications removed.

    Only push notifications for expert picks remain
    (handled by api/routers/telegram.py + push.py).
    """
    return False


# ─── 1. Automated Daily Pipeline ────────────────────────────────


@router.post("/run-daily-pipeline")
def run_daily_pipeline():
    """Run the full prediction pipeline (data collection + AI analysis) and send a Telegram summary."""
    import time as _time

    logger.info("[Pipeline] 🚀 Démarrage du pipeline automatique...")
    start = _time.time()

    try:
        from run_pipeline import run_analysis, run_data_pipeline

        run_data_pipeline()
        run_analysis()
    except Exception as e:
        logger.error(f"[Pipeline] ❌ Erreur: {e}")
        _send_telegram_message(f"❌ *Pipeline échoué*\n\nErreur: {e}")
        return {"status": "error", "message": str(e)}

    elapsed = round(_time.time() - start)

    # Count today's predictions
    today = datetime.now().strftime("%Y-%m-%d")
    predictions = (
        supabase.table("fixtures")
        .select("id, home_team, away_team, proba_home, proba_draw, proba_away")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .not_.is_("proba_home", "null")
        .execute()
        .data
        or []
    )

    # Build Telegram summary
    summary_lines = [f"📋 *Pipeline terminé* ({elapsed}s)\n"]
    summary_lines.append(f"📊 *{len(predictions)} matchs analysés*\n")

    for p in predictions[:8]:  # Max 8 matches to keep message short
        home_pct = p.get("proba_home", 0)
        draw_pct = p.get("proba_draw", 0)
        away_pct = p.get("proba_away", 0)
        fav = p["home_team"] if home_pct >= away_pct else p["away_team"]
        fav_pct = max(home_pct, away_pct)
        summary_lines.append(f"⚽ {p['home_team']} vs {p['away_team']} → {fav} ({fav_pct}%)")

    _send_telegram_message("\n".join(summary_lines))

    logger.info(f"[Pipeline] ✅ Terminé en {elapsed}s — {len(predictions)} matchs")
    return {"status": "ok", "elapsed_seconds": elapsed, "matches_analyzed": len(predictions)}


# ─── 2. Daily Recap (Evening) ───────────────────────────────────


@router.post("/daily-recap")
def daily_recap():
    """Compare today's predictions vs actual results and send a Telegram recap."""
    logger.info("[Recap] 📊 Bilan du jour...")

    today = datetime.now().strftime("%Y-%m-%d")

    # Get all finished matches today with predictions
    fixtures = (
        supabase.table("fixtures")
        .select(
            "home_team, away_team, proba_home, proba_draw, proba_away, "
            "proba_btts, proba_over_25, proba_over_15, "
            "home_goals, away_goals, status"
        )
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .eq("status", "FT")
        .not_.is_("proba_home", "null")
        .execute()
        .data
        or []
    )

    if not fixtures:
        msg = "📊 *Bilan du jour*\n\nAucun match terminé avec prédictions aujourd'hui."
        _send_telegram_message(msg)
        return {"status": "no_matches", "message": msg}

    # Calculate accuracy per market
    markets = {
        "1X2": {"correct": 0, "total": 0},
        "BTTS": {"correct": 0, "total": 0},
        "Over 1.5": {"correct": 0, "total": 0},
        "Over 2.5": {"correct": 0, "total": 0},
    }

    match_results = []

    for f in fixtures:
        hg = f.get("home_goals", 0) or 0
        ag = f.get("away_goals", 0) or 0
        total_goals = hg + ag

        ph = f.get("proba_home", 0) or 0
        pd = f.get("proba_draw", 0) or 0
        pa = f.get("proba_away", 0) or 0

        # 1X2
        predicted = "home" if ph >= pd and ph >= pa else ("draw" if pd >= pa else "away")
        actual = "home" if hg > ag else ("draw" if hg == ag else "away")
        markets["1X2"]["total"] += 1
        correct = predicted == actual
        if correct:
            markets["1X2"]["correct"] += 1
        match_results.append(
            f"{'✅' if correct else '❌'} {f['home_team']} {hg}-{ag} {f['away_team']}"
        )

        # BTTS
        p_btts = f.get("proba_btts")
        if p_btts is not None:
            markets["BTTS"]["total"] += 1
            btts_actual = hg > 0 and ag > 0
            if (p_btts > 50) == btts_actual:
                markets["BTTS"]["correct"] += 1

        # Over 1.5
        p_o15 = f.get("proba_over_15")
        if p_o15 is not None:
            markets["Over 1.5"]["total"] += 1
            if (p_o15 > 50) == (total_goals > 1.5):
                markets["Over 1.5"]["correct"] += 1

        # Over 2.5
        p_o25 = f.get("proba_over_25")
        if p_o25 is not None:
            markets["Over 2.5"]["total"] += 1
            if (p_o25 > 50) == (total_goals > 2.5):
                markets["Over 2.5"]["correct"] += 1

    # Build Telegram recap
    lines = [f"📊 *Bilan du jour — {today}*\n"]
    lines.append(f"*{len(fixtures)} matchs terminés*\n")

    for name, m in markets.items():
        if m["total"] > 0:
            pct = round(100 * m["correct"] / m["total"])
            emoji = "🟢" if pct >= 70 else ("🟡" if pct >= 50 else "🔴")
            lines.append(f"{emoji} *{name}* : {m['correct']}/{m['total']} ({pct}%)")

    lines.append("")
    lines.extend(match_results[:10])

    msg = "\n".join(lines)
    _send_telegram_message(msg)

    logger.info(f"[Recap] ✅ Bilan envoyé : {len(fixtures)} matchs")
    return {"status": "ok", "matches": len(fixtures), "markets": markets}


# ─── 3. Value Bet Detection ─────────────────────────────────────


@router.post("/detect-value-bets")
def detect_value_bets():
    """Compare model probabilities with bookmaker odds to find value bets."""
    logger.info("[Value Bets] 🔍 Recherche de value bets...")

    today = datetime.now().strftime("%Y-%m-%d")

    # Get today's predictions
    fixtures = (
        supabase.table("fixtures")
        .select(
            "id, api_fixture_id, home_team, away_team, "
            "proba_home, proba_draw, proba_away, "
            "proba_btts, proba_over_25"
        )
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .in_("status", ["NS", "TBD"])
        .not_.is_("proba_home", "null")
        .execute()
        .data
        or []
    )

    if not fixtures:
        return {"status": "no_matches", "value_bets": []}

    value_bets = []

    for fix in fixtures:
        api_id = fix.get("api_fixture_id")
        if not api_id:
            continue

        # Get bookmaker odds from API-Football
        odds_resp = api_get("odds", {"fixture": api_id})
        if not odds_resp or not odds_resp.get("response"):
            continue

        bookmakers = odds_resp["response"]
        if not bookmakers:
            continue

        # Parse odds (take first bookmaker's 1X2 market)
        for bm in bookmakers:
            for bet in bm.get("bookmakers", []):
                for mkt in bet.get("bets", []):
                    if mkt.get("name") == "Match Winner":
                        odds_map = {}
                        for val in mkt.get("values", []):
                            odds_map[val["value"]] = float(val["odd"])

                        home_odd = odds_map.get("Home", 0)
                        draw_odd = odds_map.get("Draw", 0)
                        away_odd = odds_map.get("Away", 0)

                        if home_odd <= 0 or draw_odd <= 0 or away_odd <= 0:
                            continue

                        # Implied probabilities (with margin)
                        implied_home = round(100 / home_odd)
                        implied_draw = round(100 / draw_odd)
                        implied_away = round(100 / away_odd)

                        # Our probabilities
                        our_home = fix.get("proba_home", 0) or 0
                        our_draw = fix.get("proba_draw", 0) or 0
                        our_away = fix.get("proba_away", 0) or 0

                        # Value = expected ROI: (our_prob/100 * odd) - 1
                        # If > 10% expected ROI and our_prob >= 40%, it's a value bet
                        MIN_EV = 0.10  # 10% expected ROI

                        checks = [
                            ("Victoire " + fix["home_team"], our_home, implied_home, home_odd),
                            ("Match Nul", our_draw, implied_draw, draw_odd),
                            ("Victoire " + fix["away_team"], our_away, implied_away, away_odd),
                        ]

                        for label, our_prob, implied_prob, odd in checks:
                            ev = (our_prob / 100.0) * odd - 1 if odd and odd > 0 else 0
                            edge = our_prob - implied_prob  # Keep for display
                            if ev >= MIN_EV and our_prob >= 40:
                                value_bets.append(
                                    {
                                        "match": f"{fix['home_team']} vs {fix['away_team']}",
                                        "bet": label,
                                        "our_proba": our_prob,
                                        "implied_proba": implied_prob,
                                        "edge": edge,
                                        "ev": round(ev * 100, 1),  # Expected ROI %
                                        "odd": odd,
                                    }
                                )

                        break  # Only need one bookmaker
                break
            break

    # Send Telegram alert if value bets found
    if value_bets:
        lines = [f"💎 *VALUE BETS — {today}*\n"]
        for vb in value_bets:
            lines.append(
                f"⚽ *{vb['match']}*\n"
                f"   💰 {vb['bet']} @ {vb['odd']}\n"
                f"   📊 Notre modèle: {vb['our_proba']}% vs Marché: {vb['implied_proba']}% "
                f"(*+{vb['edge']}% edge*)\n"
            )
        _send_telegram_message("\n".join(lines))
        logger.info(f"[Value Bets] 🔥 {len(value_bets)} value bets détectés !")
    else:
        _send_telegram_message(f"💎 *Value Bets — {today}*\n\nAucun value bet détecté aujourd'hui.")
        logger.info("[Value Bets] Aucun value bet aujourd'hui.")

    return {"status": "ok", "value_bets": value_bets}


# =============================================================================
# NHL ENDPOINTS
# =============================================================================


@router.get("/nhl-daily-matches")
def get_nhl_daily_matches():
    """Returns all NHL matches planned for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    fixtures = (
        supabase.table("nhl_fixtures")
        .select("id, api_fixture_id, date, home_team, away_team")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .in_("status", ["NS", "TBD", ""])
        .execute()
        .data
        or []
    )
    return {"date": today, "matches": fixtures, "sport": "NHL"}


@router.post("/nhl-value-bets")
def nhl_value_bets():
    """Detect NHL value bets and send Telegram alerts with Top 5 players per category."""
    logger.info("[NHL Value Bets] 🏒 Recherche de value bets NHL...")

    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Get today's NHL fixtures
    fixtures = (
        supabase.table("nhl_fixtures")
        .select("id, api_fixture_id, date, home_team, away_team, proba_home, proba_away, odds_json")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .in_("status", ["NS", "TBD", ""])
        .not_.is_("proba_home", "null")
        .execute()
        .data
        or []
    )

    if not fixtures:
        _send_telegram_message(
            f"🏒 *NHL Value Bets — {today}*\n\nAucun match NHL avec prédictions aujourd'hui."
        )
        return {"status": "no_matches", "value_bets": []}

    # 2. Get top players from nhl_data_lake
    all_players = (
        supabase.table("nhl_data_lake")
        .select("player_name, team, python_prob, algo_score_goal, algo_score_shot, is_home")
        .eq("date", today)
        .execute()
        .data
        or []
    )

    value_bets = []

    for fix in fixtures:
        home = fix["home_team"]
        away = fix["away_team"]
        our_home = fix.get("proba_home", 0) or 0
        our_away = fix.get("proba_away", 0) or 0

        # Filter players for this match
        match_players = [
            p for p in all_players if (p.get("team", "").lower() in (home.lower(), away.lower()))
        ]

        # Top 5 per category
        def top5(players, key, reverse=True):
            sorted_p = sorted(players, key=lambda r: float(r.get(key, 0) or 0), reverse=reverse)
            seen = set()
            result = []
            for p in sorted_p:
                name = p.get("player_name", "")
                if name not in seen:
                    seen.add(name)
                    result.append(
                        {
                            "name": name,
                            "team": p.get("team", ""),
                            "prob": round(float(p.get("python_prob", 0) or 0) * 100, 1),
                            "goal_score": p.get("algo_score_goal", 0),
                            "shot_score": p.get("algo_score_shot", 0),
                        }
                    )
                if len(result) >= 5:
                    break
            return result

        top_buteurs = top5(match_players, "python_prob")
        top_passeurs = top5(match_players, "algo_score_goal")
        top_points = top5(match_players, "python_prob")  # combined proxy
        top_shots = top5(match_players, "algo_score_shot")

        # Extraction des vraies cotes depuis odds_json (API-Sports Hockey)
        odds_json = fix.get("odds_json") or {}
        home_odd_real = 0.0
        away_odd_real = 0.0

        if "bookmakers" in odds_json:
            for bm in odds_json["bookmakers"]:
                # On cherche Bet365 (id 1) ou autre en fallback
                for bet in bm.get("bets", []):
                    # Marché "Money Line" ou "Home/Away" (id 1, 2)
                    if bet.get("id") in (1, 2) or bet.get("name") in ("Home/Away", "Match Winner"):
                        for val in bet.get("values", []):
                            if val.get("value") == "Home":
                                home_odd_real = float(val.get("odd", 0))
                            elif val.get("value") == "Away":
                                away_odd_real = float(val.get("odd", 0))
                if home_odd_real > 0:
                    break

        # S'il n'y a pas de vraie cote, on l'estime
        is_real_odd = home_odd_real > 0 and away_odd_real > 0
        if not is_real_odd:
            home_odd_real = round(100 / our_home, 2) if our_home > 0 else 0
            away_odd_real = round(100 / our_away, 2) if our_away > 0 else 0

        bet_options = []
        if our_home > 0 and home_odd_real > 0:
            implied_home = 100 / home_odd_real
            edge_home = our_home - implied_home
            # Only keep True Value Bets (Edge >= 3% if real odds)
            if not is_real_odd or edge_home >= 3.0:
                value_score_home = edge_home * home_odd_real
                bet_options.append(
                    ("Victoire " + home, our_home, home_odd_real, value_score_home, edge_home)
                )

        if our_away > 0 and away_odd_real > 0:
            implied_away = 100 / away_odd_real
            edge_away = our_away - implied_away
            if not is_real_odd or edge_away >= 3.0:
                value_score_away = edge_away * away_odd_real
                bet_options.append(
                    ("Victoire " + away, our_away, away_odd_real, value_score_away, edge_away)
                )

        # Pick best value bet
        best_bet = max(bet_options, key=lambda x: x[3]) if bet_options else None

        value_bets.append(
            {
                "match": f"{home} vs {away}",
                "home_proba": our_home,
                "away_proba": our_away,
                "recommended_bet": best_bet[0] if best_bet else "Aucune Value",
                "recommended_odd": best_bet[2] if best_bet else 0,
                "recommended_proba": best_bet[1] if best_bet else 0,
                "edge": round(best_bet[4], 1) if best_bet else 0,
                "is_real_odd": is_real_odd,
                "top_buteurs": top_buteurs,
                "top_passeurs": top_passeurs,
                "top_points": top_points,
                "top_shots": top_shots,
            }
        )

    # 3. Build Telegram message
    lines = [f"🏒 *NHL VALUE BETS — {today}*\n"]

    for vb in value_bets:
        lines.append(f"⚽ *{vb['match']}*")
        if vb["recommended_bet"] != "Aucune Value":
            lines.append(
                f"   💰 *{vb['recommended_bet']}* @ {vb['recommended_odd']} {'(Cote Bookmaker)' if vb['is_real_odd'] else '(Estimation)'}"
            )
            lines.append(f"   📊 Proba: {vb['recommended_proba']}% (Edge: +{vb['edge']}%)")
        else:
            lines.append("   ❌ *Aucune value bet détectée*")

        lines.append("")

        # Top 5 Buteurs
        if vb["top_buteurs"]:
            lines.append("   🎯 *Top 5 Buteurs:*")
            for i, p in enumerate(vb["top_buteurs"], 1):
                lines.append(f"   {i}. {p['name']} ({p['prob']}%)")

        # Top 5 +2.5 Tirs Cadrés
        if vb["top_shots"]:
            lines.append("   🎯 *Top 5 +2.5 Tirs:*")
            for i, p in enumerate(vb["top_shots"], 1):
                lines.append(f"   {i}. {p['name']} (score: {p['shot_score']})")

        lines.append("")

    _send_telegram_message("\n".join(lines))
    logger.info(f"[NHL Value Bets] ✅ {len(value_bets)} matchs analysés")
    return {"status": "ok", "matches_analyzed": len(value_bets), "value_bets": value_bets}


@router.post("/nhl-fetch-odds")
def nhl_fetch_odds():
    """Fetch NHL odds from API-Sports and update nhl_fixtures"""
    import time

    logger.info("[NHL Odds] 🏒 Démarrage fetch_nhl_odds...")
    start = time.time()
    try:
        from src.fetchers.fetch_nhl_odds import fetch_nhl_odds

        result = fetch_nhl_odds()
    except Exception as e:
        logger.error(f"[NHL Odds] ❌ Erreur: {e}")
        return {"status": "error", "message": str(e)}

    logger.info(f"[NHL Odds] ✅ Terminé en {round(time.time() - start)}s")
    return result


@router.post("/football-momentum")
def football_momentum():
    """Scan live football matches for extreme momentum shifts"""
    import time

    logger.info("[Football Momentum] 🌪️ Démarrage du scan live...")
    start = time.time()
    try:
        from src.fetchers.live_momentum import run_momentum_tracker

        result = run_momentum_tracker()
    except Exception as e:
        logger.error(f"[Football Momentum] ❌ Erreur: {e}")
        return {"status": "error", "message": str(e)}

    logger.info(f"[Football Momentum] ✅ Terminé en {round(time.time() - start)}s")
    return result


@router.post("/nhl-update-live-scores")
def nhl_update_live_scores():
    """Fetch live NHL scores from official NHLE API and update nhl_fixtures table."""
    import time as _time
    from datetime import datetime, timedelta

    import requests as _requests

    logger.info("[NHL Live Scores] 🏒 Fetching live NHL scores from NHLE API...")

    STATUS_MAP = {
        "PRE": "NS",
        "LIVE": "LIVE",
        "CRIT": "LIVE",
        "FINAL": "FT",
        "OFF": "FT",
    }

    try:
        # We fetch "now", "yesterday" and "2 days ago" to ensure games that just finished are flipped to FT
        # especially given the UTC/US date shift.
        t_now = datetime.now()
        yesterday = (t_now - timedelta(days=1)).strftime("%Y-%m-%d")
        two_days_ago = (t_now - timedelta(days=2)).strftime("%Y-%m-%d")

        urls = [
            "https://api-web.nhle.com/v1/score/now",
            f"https://api-web.nhle.com/v1/score/{yesterday}",
            f"https://api-web.nhle.com/v1/score/{two_days_ago}",
        ]

        all_games = []
        for url in urls:
            resp = _requests.get(url, timeout=15)
            if resp.status_code == 200:
                all_games.extend(resp.json().get("games", []))
            _time.sleep(0.5)

        if not all_games:
            return {"status": "no_games", "updated": 0}

        # Deduplicate by ID
        seen_ids = set()
        api_games = []
        for g in all_games:
            if g.get("id") not in seen_ids:
                seen_ids.add(g.get("id"))
                api_games.append(g)

        updated = 0
        for game in api_games:
            api_id = game.get("id")
            if not api_id:
                continue

            # Find matching DB fixture
            db_fix_resp = (
                supabase.table("nhl_fixtures")
                .select("id, status, home_score, away_score, stats_json, home_team, away_team")
                .eq("api_fixture_id", api_id)
                .execute()
            )
            db_fix_data = db_fix_resp.data

            if not db_fix_data:
                continue

            db_fix = db_fix_data[0]
            db_home_name = db_fix.get("home_team", "")
            db_away_name = db_fix.get("away_team", "")

            # Skip if already finished in our DB
            if db_fix.get("status") in ("FT", "CANC", "POST"):
                continue

            # Extract data
            home_team = game.get("homeTeam", {})
            away_team = game.get("awayTeam", {})
            home_abbrev = home_team.get("abbrev")
            away_abbrev = away_team.get("abbrev")
            nhle_state = game.get("gameState")

            curr_home_score = home_team.get("score")
            curr_away_score = away_team.get("score")
            our_status = STATUS_MAP.get(nhle_state, nhle_state)

            # Period labels
            period = game.get("period")
            if our_status == "LIVE" and period:
                if period == 1:
                    our_status = "1P"
                elif period == 2:
                    our_status = "2P"
                elif period == 3:
                    our_status = "3P"
                elif period > 3:
                    our_status = "OT"

            update_data = {"status": our_status}
            if curr_home_score is not None:
                update_data["home_score"] = curr_home_score
            if curr_away_score is not None:
                update_data["away_score"] = curr_away_score

            # Check if we need to fetch events
            score_changed = (curr_home_score != db_fix.get("home_score")) or (
                curr_away_score != db_fix.get("away_score")
            )
            newly_finished = our_status == "FT" and db_fix.get("status") != "FT"

            if score_changed or newly_finished:
                logger.info(f"[NHL Live] Updating events for {api_id} ({our_status})")
                try:
                    landing_resp = _requests.get(
                        f"https://api-web.nhle.com/v1/gamecenter/{api_id}/landing", timeout=10
                    )
                    if landing_resp.status_code == 200:
                        l_data = landing_resp.json()
                        summary = l_data.get("summary", {})
                        scoring_periods = summary.get("scoring", [])

                        goals_list = []
                        for period_data in scoring_periods:
                            p_num = period_data.get("periodDescriptor", {}).get("number")
                            p_type = period_data.get("periodDescriptor", {}).get(
                                "periodType", "REG"
                            )
                            p_label = str(p_num) if p_type == "REG" else p_type

                            for goal in period_data.get("goals", []):
                                g_abbrev = goal.get("teamAbbrev", {}).get("default", "")
                                team_name = (
                                    db_home_name
                                    if g_abbrev == home_abbrev
                                    else db_away_name
                                    if g_abbrev == away_abbrev
                                    else g_abbrev
                                )

                                goals_list.append(
                                    {
                                        "team": team_name,
                                        "player": goal.get("name", {}).get("default", ""),
                                        "assists": [
                                            a.get("name", {}).get("default", "")
                                            for a in goal.get("assists", [])
                                        ],
                                        "period": p_label,
                                        "minute": goal.get("timeInPeriod", ""),
                                        "comment": goal.get("goalModifier", ""),
                                    }
                                )

                        existing_stats = db_fix.get("stats_json") or {}
                        existing_stats["goals"] = goals_list
                        update_data["stats_json"] = existing_stats
                except Exception as e:
                    logger.warning(f"[NHL Live] Events error for {api_id}: {e}")

            supabase.table("nhl_fixtures").update(update_data).eq("id", db_fix["id"]).execute()
            updated += 1
            _time.sleep(0.1)

        return {"status": "ok", "updated": updated}

    except Exception as e:
        logger.error(f"[NHL Live] Critical error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/nhl-evaluate-performance")
def nhl_evaluate_performance():
    """Trigger the NHL performance evaluation script."""
    logger.info("[NHL Performance] 📈 Démarrage de l'évaluation des performances...")
    try:
        from src.fetchers.fetch_nhl_results import evaluate_nhl_predictions

        evaluate_nhl_predictions(days_back=7)
        return {"status": "ok", "message": "Performance evaluation completed"}
    except Exception as e:
        logger.error(f"[NHL Performance] ❌ Erreur: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/nhl-run-pipeline")
def nhl_run_pipeline():
    """Run the full NHL pipeline (data collection + player scoring) and send a Telegram summary."""
    import time as _time

    logger.info("[NHL Pipeline] 🏒 Démarrage du pipeline NHL...")
    start = _time.time()

    try:
        from src.fetchers.nhl_pipeline import run_nhl_pipeline

        result = run_nhl_pipeline()
    except Exception as e:
        logger.error(f"[NHL Pipeline] ❌ Erreur: {e}")
        _send_telegram_message(f"❌ *Pipeline NHL échoué*\n\nErreur: {e}")
        return {"status": "error", "message": str(e)}

    elapsed = round(_time.time() - start)

    if result.get("status") == "no_games":
        _send_telegram_message("🏒 *Pipeline NHL terminé*\n\nAucun match NHL aujourd'hui.")
        return result

    # Build Telegram summary
    lines = [f"🏒 *Pipeline NHL terminé* ({elapsed}s)\n"]
    lines.append(f"📊 *{result.get('matches', 0)} matchs analysés*")
    lines.append(f"👥 *{result.get('players_analyzed', 0)} joueurs scorés*\n")

    for f in result.get("fixtures", [])[:8]:
        lines.append(f"⚽ {f['match']} → {f['home_pct']}% / {f['away_pct']}%")

    _send_telegram_message("\n".join(lines))

    logger.info(f"[NHL Pipeline] ✅ Terminé en {elapsed}s")
    return result


@router.post("/nhl-ml-reminder")
def nhl_ml_reminder():
    """Send a Telegram reminder to run the NHL ML training pipeline."""
    logger.info("[NHL ML] 🧠 Envoi du rappel d'entraînement Machine Learning...")

    msg = (
        "🧠 *Rappel ProbaLab ML*\n\n"
        "Cela fait 2 semaines ! Il est temps d'entraîner tes modèles prédictifs NHL avec les nouvelles données récoltées.\n\n"
        "👉 *Commandes à lancer sur le serveur :*\n"
        "`cd Projet_Football`\n"
        "`python -m nhl.build_data`\n"
        "`python -m nhl.train`\n\n"
        "Une fois terminé, les nouveaux `.pkl` seront pris en compte automatiquement."
    )
    _send_telegram_message(msg)

    return {"status": "ok"}


@router.post("/run-reflection")
def run_reflection():
    """Trigger the AI Reflection Engine (daily self-correction loop)."""
    logger.info("[Reflection] 🧠 Démarrage du moteur d'auto-analyse IA...")
    try:
        from src.reflection_engine import process_daily_reflection

        process_daily_reflection("football")
        process_daily_reflection("nhl")
        return {"status": "ok", "message": "Reflection engine completed successfully"}
    except Exception as e:
        logger.error(f"[Reflection] ❌ Erreur critique: {e}")
        return {"status": "error", "message": str(e)}
