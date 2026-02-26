from __future__ import annotations
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import supabase, api_get, logger, API_FOOTBALL_KEY
from brain import ask_claude, extract_json

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ─── Telegram Config ────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8313502721:AAFOlAmD3zyiz8P143Kc16XcArBg-4g3AzY")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "5721158019,7003371099").split(",")


def _send_telegram_alert(home: str, away: str, analysis: str, bet: str, confidence: int) -> bool:
    """Send a Telegram message to all registered chat IDs."""
    if not HTTPX_AVAILABLE or not TELEGRAM_BOT_TOKEN:
        logger.warning("[Telegram] httpx not available or no token")
        return False

    message = (
        f"🔥 *ALERTE LIVE — ProbaLab*\n\n"
        f"⚽ *{home} vs {away}*\n\n"
        f"{analysis}\n\n"
        f"💰 *Pari suggéré :* {bet}\n"
        f"📊 *Confiance :* {confidence}/10"
    )

    sent = False
    for chat_id in TELEGRAM_CHAT_IDS:
        chat_id = chat_id.strip()
        if not chat_id:
            continue
        try:
            resp = httpx.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                logger.info(f"[Telegram] ✅ Message envoyé à {chat_id}")
                sent = True
            else:
                logger.error(f"[Telegram] Erreur {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[Telegram] Erreur envoi à {chat_id}: {e}")
    return sent

from fastapi import APIRouter, HTTPException, Depends, Header

CRON_SECRET = os.getenv("CRON_SECRET", "super_secret_probalab_2026")

def verify_trigger_auth(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
        
    token = authorization.replace("Bearer ", "").strip()
    
    # 1. Check CRON Secret (for Trigger.dev worker)
    if token == CRON_SECRET:
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
        logger.error(f"[Auth] ❌ token verification failed: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=403, detail=f"Invalid token or unauthorized: {str(e)}")
        
    return True

router = APIRouter(prefix="/api/trigger", tags=["Trigger"], dependencies=[Depends(verify_trigger_auth)])

class AnalyzeRequest(BaseModel):
    fixture_id: str

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
        .data or []
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
    logger.info(f"[Live] {fixture['home_team']} vs {fixture['away_team']}: {len(anomalies)} anomalies détectées")

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
MATCH: {fixture['home_team']} vs {fixture['away_team']}
SCORE MI-TEMPS: {score_home} - {score_away}

STATISTIQUES MI-TEMPS:
[{t1_name}]
- Possession: {_get_stat(team1, 'Ball Possession')}%
- Tirs Cadrés: {int(_get_stat(team1, 'Shots on Goal'))}
- Tirs Totaux: {int(_get_stat(team1, 'Total Shots'))}
- xG: {_get_stat(team1, 'expected_goals')}
- Corners: {int(_get_stat(team1, 'Corner Kicks'))}

[{t2_name}]
- Possession: {_get_stat(team2, 'Ball Possession')}%
- Tirs Cadrés: {int(_get_stat(team2, 'Shots on Goal'))}
- Tirs Totaux: {int(_get_stat(team2, 'Total Shots'))}
- xG: {_get_stat(team2, 'expected_goals')}
- Corners: {int(_get_stat(team2, 'Corner Kicks'))}

ANOMALIES DÉTECTÉES:
{chr(10).join(f'⚠️ {a}' for a in anomalies)}

Analyse ces anomalies et recommande le meilleur pari en direct. Retourne le JSON.
    """

    ai_text = ask_claude(SYSTEM_PROMPT, user_prompt)
    ai_result = extract_json(ai_text) if ai_text else None

    if not ai_result:
        return {"status": "error", "message": "AI failed to return valid JSON"}

    # 6. Save to live_alerts
    alert_text = ai_result.get("analysis_text", "")
    alert_bet = ai_result.get("recommended_bet", "")
    alert_confidence = ai_result.get("confidence_score", 5)

    supabase.table("live_alerts").insert({
        "fixture_id": req.fixture_id,
        "analysis_text": alert_text,
        "recommended_bet": alert_bet,
        "confidence_score": alert_confidence
    }).execute()

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


# ─── Live Scores Update ─────────────────────────────────────────

@router.post("/update-live-scores")
def update_live_scores():
    """Fetch all live scores from API-Football and update Supabase fixtures table."""
    logger.info("[Live Scores] Fetching live fixtures...")

    resp = api_get("fixtures", {"live": "all"})
    live_fixtures = resp.get("response", []) if resp else []

    updated = 0
    errors = 0
    live_api_ids = set()

    for lf in live_fixtures:
        api_fixture_id = lf.get("fixture", {}).get("id")
        goals = lf.get("goals", {})
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        status_short = lf.get("fixture", {}).get("status", {}).get("short", "")

        if not api_fixture_id:
            continue

        live_api_ids.add(api_fixture_id)

        try:
            # Map API status to our status codes
            status_map = {
                "1H": "1H", "HT": "HT", "2H": "2H",
                "ET": "ET", "P": "PEN", "FT": "FT",
                "AET": "FT", "PEN": "FT",
                "BT": "BT", "SUSP": "SUSP", "INT": "INT",
                "LIVE": "LIVE",
            }
            our_status = status_map.get(status_short, status_short)

            update_data = {
                "home_goals": home_goals,
                "away_goals": away_goals,
                "status": our_status,
                "elapsed": lf.get("fixture", {}).get("status", {}).get("elapsed"),
            }

            # Fetch match events (goals, assists)
            try:
                import time as _time
                events_resp = api_get("fixtures/events", {"fixture": api_fixture_id})
                if events_resp and events_resp.get("response"):
                    raw_events = events_resp["response"]
                    # Build clean goals list
                    goals_list = []
                    for ev in raw_events:
                        if ev.get("type") == "Goal" and ev.get("comments") != "Penalty Shootout":
                            goal_info = {
                                "team": ev.get("team", {}).get("name", ""),
                                "player": ev.get("player", {}).get("name", ""),
                                "assist": ev.get("assist", {}).get("name", "") if ev.get("assist") else "",
                                "time": ev.get("time", {}).get("elapsed", ""),
                                "extra_time": ev.get("time", {}).get("extra"),
                                "detail": ev.get("detail", ""),  # "Normal Goal", "Penalty", "Own Goal"
                                "half": "1H" if (ev.get("time", {}).get("elapsed", 0) or 0) <= 45 else "2H",
                            }
                            goals_list.append(goal_info)
                    update_data["events_json"] = goals_list
            except Exception as ev_err:
                logger.warning(f"[Live Scores] Events fetch error for {api_fixture_id}: {ev_err}")

            result = (
                supabase.table("fixtures")
                .update(update_data)
                .eq("api_fixture_id", api_fixture_id)
                .execute()
            )
            if result.data:
                updated += 1
        except Exception as e:
            logger.error(f"[Live Scores] Error updating fixture {api_fixture_id}: {e}")
            errors += 1

    # ── 2nd pass: detect recently finished matches ──
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
            .data or []
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
                "FT": "FT", "AET": "FT", "PEN": "FT",
                "NS": "NS", "PST": "POST", "CANC": "CANC",
                "1H": "1H", "2H": "2H", "HT": "HT",
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
                            goals_list.append({
                                "team": ev.get("team", {}).get("name", ""),
                                "player": ev.get("player", {}).get("name", ""),
                                "assist": ev.get("assist", {}).get("name", "") if ev.get("assist") else "",
                                "time": ev.get("time", {}).get("elapsed", ""),
                                "extra_time": ev.get("time", {}).get("extra"),
                                "detail": ev.get("detail", ""),
                                "half": "1H" if (ev.get("time", {}).get("elapsed", 0) or 0) <= 45 else "2H",
                            })
                    update_data["events_json"] = goals_list
            except Exception:
                pass

            supabase.table("fixtures").update(update_data).eq("api_fixture_id", sf_api_id).execute()
            finished_count += 1
            logger.info(f"[Live Scores] 🏁 Match {sf_api_id} terminé → {final_status} ({goals.get('home')}-{goals.get('away')})")
        except Exception as e:
            logger.error(f"[Live Scores] Error finishing {sf_api_id}: {e}")

    logger.info(f"[Live Scores] ✅ {updated} live mis à jour, {finished_count} terminés, {errors} erreurs")
    return {"status": "ok", "updated": updated, "finished": finished_count, "errors": errors, "total_live": len(live_fixtures)}


# ─── Generic Telegram sender ────────────────────────────────────

def _send_telegram_message(text: str) -> bool:
    """Send a raw Telegram message to all registered chat IDs."""
    if not HTTPX_AVAILABLE or not TELEGRAM_BOT_TOKEN:
        return False
    sent = False
    for chat_id in TELEGRAM_CHAT_IDS:
        chat_id = chat_id.strip()
        if not chat_id:
            continue
        try:
            resp = httpx.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                sent = True
        except Exception as e:
            logger.error(f"[Telegram] Erreur: {e}")
    return sent


# ─── 1. Automated Daily Pipeline ────────────────────────────────

@router.post("/run-daily-pipeline")
def run_daily_pipeline():
    """Run the full prediction pipeline (data collection + AI analysis) and send a Telegram summary."""
    import time as _time
    logger.info("[Pipeline] 🚀 Démarrage du pipeline automatique...")
    start = _time.time()

    try:
        from run_pipeline import run_data_pipeline, run_analysis
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
        .data or []
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
        .select("home_team, away_team, proba_home, proba_draw, proba_away, "
                "proba_btts, proba_over_25, proba_over_15, "
                "home_goals, away_goals, status")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .eq("status", "FT")
        .not_.is_("proba_home", "null")
        .execute()
        .data or []
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
        match_results.append(f"{'✅' if correct else '❌'} {f['home_team']} {hg}-{ag} {f['away_team']}")

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
        .select("id, api_fixture_id, home_team, away_team, "
                "proba_home, proba_draw, proba_away, "
                "proba_btts, proba_over_25")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .in_("status", ["NS", "TBD"])
        .not_.is_("proba_home", "null")
        .execute()
        .data or []
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

                        # Value = our probability - implied probability
                        # If > 15% edge, it's a value bet
                        MIN_EDGE = 15

                        checks = [
                            ("Victoire " + fix["home_team"], our_home, implied_home, home_odd),
                            ("Match Nul", our_draw, implied_draw, draw_odd),
                            ("Victoire " + fix["away_team"], our_away, implied_away, away_odd),
                        ]

                        for label, our_prob, implied_prob, odd in checks:
                            edge = our_prob - implied_prob
                            if edge >= MIN_EDGE and our_prob >= 40:
                                value_bets.append({
                                    "match": f"{fix['home_team']} vs {fix['away_team']}",
                                    "bet": label,
                                    "our_proba": our_prob,
                                    "implied_proba": implied_prob,
                                    "edge": edge,
                                    "odd": odd,
                                })

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
        .data or []
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
        .select("id, api_fixture_id, date, home_team, away_team, "
                "proba_home, proba_away, odds_json")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .in_("status", ["NS", "TBD", ""])
        .not_.is_("proba_home", "null")
        .execute()
        .data or []
    )

    if not fixtures:
        _send_telegram_message(f"🏒 *NHL Value Bets — {today}*\n\nAucun match NHL avec prédictions aujourd'hui.")
        return {"status": "no_matches", "value_bets": []}

    # 2. Get top players from nhl_data_lake
    all_players = (
        supabase.table("nhl_data_lake")
        .select("player_name, team, python_prob, algo_score_goal, algo_score_shot, is_home")
        .eq("date", today)
        .execute()
        .data or []
    )

    value_bets = []

    for fix in fixtures:
        home = fix["home_team"]
        away = fix["away_team"]
        our_home = fix.get("proba_home", 0) or 0
        our_away = fix.get("proba_away", 0) or 0

        # Filter players for this match
        match_players = [
            p for p in all_players
            if (p.get("team", "").lower() in (home.lower(), away.lower()))
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
                    result.append({
                        "name": name,
                        "team": p.get("team", ""),
                        "prob": round(float(p.get("python_prob", 0) or 0) * 100, 1),
                        "goal_score": p.get("algo_score_goal", 0),
                        "shot_score": p.get("algo_score_shot", 0),
                    })
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
                bet_options.append(("Victoire " + home, our_home, home_odd_real, value_score_home, edge_home))

        if our_away > 0 and away_odd_real > 0:
            implied_away = 100 / away_odd_real
            edge_away = our_away - implied_away
            if not is_real_odd or edge_away >= 3.0:
                value_score_away = edge_away * away_odd_real
                bet_options.append(("Victoire " + away, our_away, away_odd_real, value_score_away, edge_away))

        # Pick best value bet
        best_bet = max(bet_options, key=lambda x: x[3]) if bet_options else None

        value_bets.append({
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
        })

    # 3. Build Telegram message
    lines = [f"🏒 *NHL VALUE BETS — {today}*\n"]

    for vb in value_bets:
        lines.append(f"⚽ *{vb['match']}*")
        if vb['recommended_bet'] != "Aucune Value":
            lines.append(f"   💰 *{vb['recommended_bet']}* @ {vb['recommended_odd']} {'(Cote Bookmaker)' if vb['is_real_odd'] else '(Estimation)'}")
            lines.append(f"   📊 Proba: {vb['recommended_proba']}% (Edge: +{vb['edge']}%)")
        else:
            lines.append(f"   ❌ *Aucune value bet détectée*")
        
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
        from fetchers.fetch_nhl_odds import fetch_nhl_odds
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
        from fetchers.live_momentum import run_momentum_tracker
        result = run_momentum_tracker()
    except Exception as e:
        logger.error(f"[Football Momentum] ❌ Erreur: {e}")
        return {"status": "error", "message": str(e)}

    logger.info(f"[Football Momentum] ✅ Terminé en {round(time.time() - start)}s")
    return result


@router.post("/nhl-update-live-scores")
def nhl_update_live_scores():
    """Fetch live NHL scores from Hockey API and update nhl_fixtures table."""
    import requests as _requests
    import time as _time

    logger.info("[NHL Live Scores] 🏒 Fetching live NHL scores...")

    today = datetime.now().strftime("%Y-%m-%d")

    # Get today's NHL fixtures
    fixtures = (
        supabase.table("nhl_fixtures")
        .select("id, api_fixture_id, home_team, away_team, status")
        .gte("date", f"{today}T00:00:00Z")
        .lt("date", f"{today}T23:59:59Z")
        .execute()
        .data or []
    )

    if not fixtures:
        return {"status": "no_fixtures", "updated": 0}

    # Hockey API-Sports config
    HOCKEY_API_URL = "https://v1.hockey.api-sports.io"
    HOCKEY_HEADERS = {
        "x-rapidapi-host": "v1.hockey.api-sports.io",
        "x-rapidapi-key": API_FOOTBALL_KEY,
    }

    # Map Hockey API statuses to our frontend statuses
    STATUS_MAP = {
        "NS": "NS",       # Not Started
        "Q1": "1P",       # 1st Period
        "Q2": "2P",       # 2nd Period
        "Q3": "3P",       # 3rd Period
        "OT": "OT",       # Overtime
        "BT": "FT",       # Break Time (between periods) — treat as live
        "P": "SO",        # Penalties (Shootout)
        "FT": "FT",       # Full Time (regular)
        "AOT": "FT",      # After Overtime
        "AP": "FT",       # After Penalties
        "CANC": "CANC",   # Cancelled
        "POST": "POST",   # Postponed
        "SUSP": "SUSP",   # Suspended
        "AWD": "FT",      # Awarded
        "WO": "FT",       # Walkover
    }

    # Statuses that mean "game is in progress"
    LIVE_STATUSES = {"Q1", "Q2", "Q3", "OT", "BT", "P"}

    updated = 0
    errors = 0

    for fix in fixtures:
        api_id = fix.get("api_fixture_id")
        if not api_id:
            continue

        # Skip already finished fixtures
        if fix.get("status") in ("FT", "CANC", "POST"):
            continue

        try:
            resp = _requests.get(
                f"{HOCKEY_API_URL}/games",
                headers=HOCKEY_HEADERS,
                params={"id": api_id},
                timeout=15,
            )
            _time.sleep(0.5)  # Rate limit

            if resp.status_code != 200:
                logger.warning(f"[NHL Live] HTTP {resp.status_code} for game {api_id}")
                continue

            data = resp.json()
            games = data.get("response", [])
            if not games:
                continue

            game = games[0]
            scores = game.get("scores", {})
            home_goals = scores.get("home")
            away_goals = scores.get("away")
            api_status = game.get("status", {}).get("short", "")
            our_status = STATUS_MAP.get(api_status, api_status)

            # BT (Break Time) means intermission — show as live with last period status
            if api_status == "BT":
                # During break, keep period context (show as live, not finished)
                our_status = "LIVE"

            update_data = {"status": our_status}
            if home_goals is not None:
                update_data["home_goals"] = home_goals
            if away_goals is not None:
                update_data["away_goals"] = away_goals

            # Fetch game events (goals, assists) from Hockey API
            try:
                events_resp = _requests.get(
                    f"{HOCKEY_API_URL}/games/events",
                    headers=HOCKEY_HEADERS,
                    params={"game": api_id},
                    timeout=15,
                )
                _time.sleep(0.5)  # Rate limit

                if events_resp.status_code == 200:
                    events_data = events_resp.json().get("response", [])
                    # Build a clean goals list with scorer + assists
                    goals_list = []
                    for ev in events_data:
                        if ev.get("type", "").lower() in ("goal", "score"):
                            goal_info = {
                                "team": ev.get("team", {}).get("name", ""),
                                "player": ev.get("players", [{}])[0].get("player", {}).get("name", "") if ev.get("players") else "",
                                "assists": [],
                                "period": ev.get("period", ""),
                                "minute": ev.get("minute", ""),
                                "comment": ev.get("comment", ""),  # PP, SH, EN, etc.
                            }
                            # Extract assists from additional players
                            for p in ev.get("players", [])[1:]:
                                assist_name = p.get("player", {}).get("name", "")
                                if assist_name:
                                    goal_info["assists"].append(assist_name)
                            goals_list.append(goal_info)

                    if goals_list or events_data:
                        update_data["stats_json"] = {
                            "events": events_data,
                            "goals": goals_list,
                        }
            except Exception as ev_err:
                logger.warning(f"[NHL Live] Events fetch error for {api_id}: {ev_err}")

            supabase.table("nhl_fixtures").update(
                update_data
            ).eq("api_fixture_id", api_id).execute()
            updated += 1

        except Exception as e:
            logger.error(f"[NHL Live] Error updating {api_id}: {e}")
            errors += 1

    logger.info(f"[NHL Live Scores] ✅ {updated} scores mis à jour, {errors} erreurs")
    return {"status": "ok", "updated": updated, "errors": errors}


@router.post("/nhl-run-pipeline")
def nhl_run_pipeline():
    """Run the full NHL pipeline (data collection + player scoring) and send a Telegram summary."""
    import time as _time
    logger.info("[NHL Pipeline] 🏒 Démarrage du pipeline NHL...")
    start = _time.time()

    try:
        from fetchers.nhl_pipeline import run_nhl_pipeline
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
