"""
ProbaLab API — FastAPI backend for football predictions.

Serves prediction data from Supabase to the React frontend.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    import pytz
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

# Add the parent package to the path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta
from typing import Optional, Union

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "ProbaLab <noreply@probalab.fr>")

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import supabase

from api.routers import stripe_webhook, nhl

# ── Scheduler ────────────────────────────────────────────────
def _scheduled_update_scores():
    """Called by APScheduler every 15 min between 18h-23h Paris."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from fetchers.results import fetch_and_update_results
        from datetime import date
        print(f"[scheduler] Mise à jour des scores — {date.today()}")
        fetch_and_update_results()
    except Exception as e:
        print(f"[scheduler] Erreur: {e}")


def _startup_update_scores():
    """Run on startup: update scores for the last 3 days (catch up)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from fetchers.results import fetch_and_update_results
        from datetime import date, timedelta
        print("[scheduler] 🚀 Rattrapage des scores au démarrage (J, J-1, J-2)...")
        for delta in range(3):
            d = (date.today() - timedelta(days=delta)).isoformat()
            fetch_and_update_results(d)
        print("[scheduler] ✅ Rattrapage terminé.")
    except Exception as e:
        print(f"[scheduler] Erreur rattrapage: {e}")


@asynccontextmanager
async def lifespan(app_instance):
    """Start/stop APScheduler with the FastAPI app."""
    scheduler = None
    if SCHEDULER_AVAILABLE:
        try:
            paris_tz = pytz.timezone("Europe/Paris")
            scheduler = BackgroundScheduler(timezone=paris_tz)
            # Toutes les 15 min entre 18h00 et 23h45 heure Paris
            scheduler.add_job(
                _scheduled_update_scores,
                trigger=CronTrigger(
                    hour="18-23",
                    minute="0,15,30,45",
                    timezone=paris_tz,
                ),
                id="update_scores",
                name="Mise à jour scores football",
                replace_existing=True,
                misfire_grace_time=300,  # 5 min de tolérance
            )
            # Rattrapage immédiat 10s après le démarrage
            from datetime import datetime as _dt, timedelta as _td
            scheduler.add_job(
                _startup_update_scores,
                trigger="date",
                run_date=_dt.now() + _td(seconds=10),
                id="startup_catchup",
                name="Rattrapage scores au démarrage",
            )
            scheduler.start()
            print("[scheduler] ✅ Démarré — scores auto (18h-23h45) + rattrapage dans 10s")
        except Exception as e:
            print(f"[scheduler] ⚠️  Impossible de démarrer: {e}")
            scheduler = None
    else:
        print("[scheduler] ⚠️  APScheduler non disponible (pip install apscheduler pytz)")

    yield  # L'app tourne ici

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        print("[scheduler] Arrêté.")


app = FastAPI(title="ProbaLab API", version="1.0.0", lifespan=lifespan)

app.include_router(stripe_webhook.router)
app.include_router(nhl.router)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint for Railway / monitoring."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ─── News RSS Cache ─────────────────────────────────────────────

_news_cache: dict = {"data": [], "fetched_at": 0}
_NEWS_TTL = 3600  # 1 hour

RSS_FEEDS = [
    {"url": "https://www.lequipe.fr/rss/actu_rss.xml", "source": "L'Équipe"},
    {"url": "https://rmcsport.bfmtv.com/rss/football/", "source": "RMC Sport"},
    {"url": "https://www.nhl.com/rss/news.xml", "source": "NHL.com"},
]


def _fetch_rss_news() -> list:
    """Fetch and parse RSS feeds, return list of news items."""
    if not HTTPX_AVAILABLE:
        return []
    items = []
    for feed in RSS_FEEDS:
        try:
            resp = httpx.get(feed["url"], timeout=5.0, follow_redirects=True)
            root = ET.fromstring(resp.text)
            channel = root.find("channel")
            if channel is None:
                continue
            for item in channel.findall("item")[:3]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                if title and link:
                    items.append({
                        "title": title,
                        "link": link,
                        "source": feed["source"],
                        "pub_date": pub_date,
                    })
        except Exception:
            pass
    return items[:6]


@app.get("/api/news")
def get_news():
    """Get latest sports news from RSS feeds (cached 1h)."""
    global _news_cache
    now = time.time()
    if now - _news_cache["fetched_at"] > _NEWS_TTL or not _news_cache["data"]:
        _news_cache["data"] = _fetch_rss_news()
        _news_cache["fetched_at"] = now
    return {"news": _news_cache["data"]}


# ─── Resend Email Helpers ───────────────────────────────────────

def _send_resend_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend API. Returns True on success."""
    if not RESEND_API_KEY or not HTTPX_AVAILABLE:
        return False
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": RESEND_FROM, "to": [to], "subject": subject, "html": html},
            timeout=10.0,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


@app.post("/api/resend/welcome")
def send_welcome_email(payload: dict):
    """Send welcome email after registration."""
    email = payload.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#f8faff">
      <div style="text-align:center;margin-bottom:32px">
        <h1 style="color:#1E40AF;font-size:28px;margin:0">⚡ ProbaLab</h1>
        <p style="color:#64748b;margin-top:8px">Analyses sportives augmentées par l'IA</p>
      </div>
      <div style="background:white;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
        <h2 style="color:#1e293b;margin-top:0">Bienvenue sur ProbaLab ! 🎉</h2>
        <p style="color:#475569;line-height:1.6">
          Votre compte est créé. Vous avez maintenant accès aux probabilités 1X2 et aux paris recommandés
          pour tous les matchs de football et de NHL.
        </p>
        <p style="color:#475569;line-height:1.6">
          Passez en <strong style="color:#1E40AF">Premium</strong> pour débloquer toutes les statistiques avancées :
          BTTS, Over/Under, buteurs probables, analyse IA et bien plus.
        </p>
        <div style="text-align:center;margin-top:24px">
          <a href="https://probalab.fr/football" style="background:#1E40AF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
            Voir les matchs →
          </a>
        </div>
      </div>
      <p style="color:#94a3b8;font-size:12px;text-align:center;margin-top:24px">
        ProbaLab fournit des analyses statistiques à titre informatif uniquement. Ce site ne constitue pas un conseil en paris sportifs.
      </p>
    </div>
    """
    ok = _send_resend_email(email, "Bienvenue sur ProbaLab ⚡", html)
    return {"sent": ok}


@app.post("/api/resend/premium-confirm")
def send_premium_confirm_email(payload: dict):
    """Send premium confirmation email after payment."""
    email = payload.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#f8faff">
      <div style="text-align:center;margin-bottom:32px">
        <h1 style="color:#1E40AF;font-size:28px;margin:0">⚡ ProbaLab</h1>
      </div>
      <div style="background:white;border-radius:12px;padding:32px;border:1px solid #e2e8f0">
        <h2 style="color:#1e293b;margin-top:0">Votre abonnement Premium est actif ! 🏆</h2>
        <p style="color:#475569;line-height:1.6">
          Félicitations ! Vous avez maintenant accès à toutes les fonctionnalités ProbaLab Premium :
        </p>
        <ul style="color:#475569;line-height:2">
          <li>✅ BTTS, Over 0.5 / 1.5 / 2.5 / 3.5</li>
          <li>✅ Score exact et penalty</li>
          <li>✅ Buteurs probables avec probabilités</li>
          <li>✅ Analyse IA complète de chaque match</li>
          <li>✅ Expected Goals (xG)</li>
          <li>✅ NHL : Top 5 buteurs, passeurs, tirs</li>
        </ul>
        <div style="text-align:center;margin-top:24px">
          <a href="https://probalab.fr/football" style="background:#1E40AF;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
            Accéder à ProbaLab →
          </a>
        </div>
      </div>
      <p style="color:#94a3b8;font-size:12px;text-align:center;margin-top:24px">
        ProbaLab fournit des analyses statistiques à titre informatif uniquement.
      </p>
    </div>
    """
    ok = _send_resend_email(email, "Votre abonnement Premium ProbaLab est actif 🏆", html)
    return {"sent": ok}




def _ensure_dict(data: Union[dict, str, None]) -> dict:
    """Helper to safely parse JSON field from Supabase that might be stringified."""
    if not data:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        import json
        try:
            return json.loads(data)
        except Exception:
            return {}
    return {}


@app.get("/api/predictions")
def get_predictions(
    date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
):
    """Get predictions for a given date (defaults to today)."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Get fixtures for that date
    next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

    fixtures = (
        supabase.table("fixtures")
        .select("*")
        .gte("date", date)
        .lt("date", next_day)
        .order("date")
        .execute()
        .data
        or []
    )

    fixture_ids = [f["id"] for f in fixtures]
    if not fixture_ids:
        return {"date": date, "matches": []}

    # Get predictions for those fixtures
    predictions = (
        supabase.table("predictions")
        .select("*")
        .in_("fixture_id", fixture_ids)
        .execute()
        .data
        or []
    )

    # Get league names
    leagues = (
        supabase.table("leagues")
        .select("api_id, name")
        .execute()
        .data
        or []
    )
    league_map = {str(l["api_id"]): l["name"] for l in leagues}

    pred_by_fixture = {p["fixture_id"]: p for p in predictions}

    matches = []
    for f in fixtures:
        pred = pred_by_fixture.get(f["id"])
        league_id = f.get("league_id")
        
        # Parse stats_json safely
        stats = _ensure_dict(pred.get("stats_json") if pred else None)
        
        # Helper to get value from top-level OR stats_json
        def get_val(key, default=None):
            if not pred: return default
            val = pred.get(key)
            if val is not None: return val
            return stats.get(key, default)

        matches.append({
            "id": f["id"],
            "home_team": f.get("home_team", "?"),
            "away_team": f.get("away_team", "?"),
            "date": f.get("date"),
            "status": f.get("status"),
            "home_goals": f.get("home_goals"),
            "away_goals": f.get("away_goals"),
            "league_id": league_id,
            "league_name": league_map.get(str(league_id), "Ligue"),
            "prediction": {
                "proba_home": get_val("proba_home"),
                "proba_draw": get_val("proba_draw"),
                "proba_away": get_val("proba_away"),
                "proba_btts": get_val("proba_btts"),
                "proba_over_25": get_val("proba_over_2_5") or get_val("proba_over_25"),
                "recommended_bet": get_val("recommended_bet"),
                "confidence_score": get_val("confidence_score"),
                "kelly_edge": get_val("kelly_edge"),
                "value_bet": get_val("value_bet"),
                "model_version": get_val("model_version"),
                "correct_score": get_val("correct_score"),
                "analysis_text": get_val("analysis_text"),
                "proba_penalty": get_val("proba_penalty"),
                "proba_over_05": get_val("proba_over_05"),
                "proba_over_15": get_val("proba_over_15"),
                "proba_over_35": get_val("proba_over_35"),
            } if pred else None,
        })

    return {"date": date, "matches": matches}



@app.get("/api/predictions/{fixture_id}")
def get_prediction_detail(fixture_id: str):
    """Get detailed prediction for a specific fixture."""
    try:
        data = (
            supabase.table("fixtures")
            .select("*")
            .eq("id", fixture_id)
            .limit(1)
            .execute()
            .data
        )
        fixture = data[0] if data else None
    except Exception as e:
        # Handle invalid UUID format or DB error
        raise HTTPException(status_code=404, detail="Fixture not found")

    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")

    prediction_data = (
        supabase.table("predictions")
        .select("*")
        .eq("fixture_id", fixture_id)
        .execute()
        .data
    )
    prediction = prediction_data[0] if prediction_data else None

    # Parse stats_json if present
    if prediction:
        sj = _ensure_dict(prediction.get("stats_json"))
        prediction["stats_json"] = sj

        # Promote missing fields from stats_json to top-level
        _proba_fields = [
            "proba_over_05", "proba_over_15", "proba_over_25", "proba_over_2_5",
            "proba_over_35", "proba_btts", "proba_penalty",
            "confidence_score", "recommended_bet", "correct_score",
            "analysis_text", "xg_home", "xg_away",
        ]
        for field in _proba_fields:
            if prediction.get(field) is None and sj.get(field) is not None:
                prediction[field] = sj[field]
        # Normalise over_2_5 vs over_25
        if prediction.get("proba_over_25") is None:
            prediction["proba_over_25"] = prediction.get("proba_over_2_5") or sj.get("proba_over_2_5") or sj.get("proba_over_25")


    # Fetch Top Scorers Logic
    home_scorers = []
    away_scorers = []
    
    if fixture:
        from config import SEASON
        home_id = fixture.get("home_team_id")
        away_id = fixture.get("away_team_id")

        def fetch_top_3(team_id):
            if not team_id: 
                return []
            # 1. Get stats
            stats = (
                supabase.table("player_season_stats")
                .select("player_api_id, goals, appearances")
                .eq("team_api_id", team_id)
                .eq("season", SEASON)
                .order("goals", desc=True)
                .limit(3)
                .execute()
                .data
            )
            if not stats: 
                return []
            
            # 2. Get player details
            p_ids = [s["player_api_id"] for s in stats]
            players = (
                supabase.table("players")
                .select("api_id, name, photo_url")
                .in_("api_id", p_ids)
                .execute()
                .data
            )
            p_map = {p["api_id"]: p for p in players}

            # 3. Merge
            results = []
            for s in stats:
                p_info = p_map.get(s["player_api_id"], {})
                results.append({
                    "name": p_info.get("name", "Unknown"),
                    "photo": p_info.get("photo_url"),
                    "goals": s["goals"],
                    "apps": s["appearances"]
                })
            return results

        try:
            home_scorers = fetch_top_3(home_id)
            away_scorers = fetch_top_3(away_id)
        except Exception:
            pass # Fail silently if DB error or missing table

    # Fetch Match Stats (Shots, xG, etc.) if available
    match_stats = []
    if fixture and fixture.get("api_fixture_id"):
        try:
            match_stats = (
                supabase.table("match_team_stats")
                .select("*")
                .eq("fixture_api_id", fixture["api_fixture_id"])
                .execute()
                .data
            )
        except Exception:
            pass

    return {
        "fixture": fixture,
        "prediction": prediction,
        "home_scorers": home_scorers,
        "away_scorers": away_scorers,
        "match_stats": match_stats,
    }


@app.get("/api/performance")
def get_performance(days: int = Query(30, description="Rolling window in days")):
    """Get model performance metrics over the last N days."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Get finished fixtures with predictions
        finished = (
            supabase.table("fixtures")
            .select("id, home_team, away_team, home_goals, away_goals, date, status")
            .eq("status", "FT")
            .gte("date", cutoff)
            .order("date")
            .execute()
            .data
            or []
        )

        fixture_ids = [f["id"] for f in finished]
        if not fixture_ids:
            return {
                "days": days,
                "total_matches": 0,
                "accuracy_1x2": 0,
                "accuracy_btts": 0,
                "avg_confidence": 0,
                "value_bets": 0,
                "daily_stats": [],
            }

        predictions = (
            supabase.table("predictions")
            .select("*")
            .in_("fixture_id", fixture_ids)
            .execute()
            .data
            or []
        )

        pred_by_fixture = {p["fixture_id"]: p for p in predictions}

        correct_1x2 = 0
        correct_btts = 0
        correct_over_05 = 0
        correct_over_15 = 0
        correct_over_25 = 0
        correct_over_35 = 0
        correct_score = 0
        total_over_05 = 0
        total_over_15 = 0
        total_over_25 = 0
        total_over_35 = 0
        total_score = 0
        total_with_pred = 0
        total_conf = 0
        value_bets_count = 0
        daily: dict[str, dict] = {}

        for f in finished:
            pred = pred_by_fixture.get(f["id"])
            if not pred:
                continue

            # Helper to get field from top-level or stats_json
            stats_json = pred.get("stats_json") or {}
            def get_val(key, default=None):
                val = pred.get(key)
                if val is not None:
                    return val
                return stats_json.get(key, default)

            total_with_pred += 1
            total_conf += pred.get("confidence_score", 5)

            hg = f.get("home_goals", 0) or 0
            ag = f.get("away_goals", 0) or 0
            total_goals = hg + ag
            actual_result = "H" if hg > ag else ("D" if hg == ag else "A")
            actual_btts = hg > 0 and ag > 0

            # 1X2 accuracy
            ph = get_val("proba_home", 33)
            pd_val = get_val("proba_draw", 33)
            pa = get_val("proba_away", 33)
            predicted_result = "H" if ph >= pd_val and ph >= pa else ("A" if pa >= pd_val else "D")
            if predicted_result == actual_result:
                correct_1x2 += 1

            # BTTS accuracy
            btts_pred = (get_val("proba_btts", 50)) > 50
            if btts_pred == actual_btts:
                correct_btts += 1

            # Over 0.5
            p_o05 = get_val("proba_over_05")
            if p_o05 is not None:
                total_over_05 += 1
                if (p_o05 > 50) == (total_goals > 0.5):
                    correct_over_05 += 1

            # Over 1.5
            p_o15 = get_val("proba_over_15")
            if p_o15 is not None:
                total_over_15 += 1
                if (p_o15 > 50) == (total_goals > 1.5):
                    correct_over_15 += 1

            # Over 2.5
            p_o25 = get_val("proba_over_2_5") or get_val("proba_over_25")
            if p_o25 is not None:
                total_over_25 += 1
                if (p_o25 > 50) == (total_goals > 2.5):
                    correct_over_25 += 1

            # Over 3.5
            p_o35 = get_val("proba_over_35")
            if p_o35 is not None:
                total_over_35 += 1
                if (p_o35 > 50) == (total_goals > 3.5):
                    correct_over_35 += 1

            # Score exact
            pred_score = get_val("correct_score")
            if pred_score:
                total_score += 1
                actual_score = f"{hg}-{ag}"
                if str(pred_score).strip() == actual_score:
                    correct_score += 1

            # Value bets (handle both keys)
            if pred.get("value_bet") or pred.get("is_value_bet"):
                value_bets_count += 1

            # Daily aggregation
            day = f["date"][:10] if f.get("date") else "unknown"
            if day not in daily:
                daily[day] = {"date": day, "total": 0, "correct": 0}
            daily[day]["total"] += 1
            if predicted_result == actual_result:
                daily[day]["correct"] += 1

        def _pct(correct: int, total: int) -> float:
            return round(correct / total * 100, 1) if total else 0

        return {
            "days": days,
            "total_matches": total_with_pred,
            "accuracy_1x2": _pct(correct_1x2, total_with_pred),
            "accuracy_btts": _pct(correct_btts, total_with_pred),
            "accuracy_over_05": _pct(correct_over_05, total_over_05),
            "accuracy_over_15": _pct(correct_over_15, total_over_15),
            "accuracy_over_25": _pct(correct_over_25, total_over_25),
            "accuracy_over_35": _pct(correct_over_35, total_over_35),
            "accuracy_score": _pct(correct_score, total_score),
            "avg_confidence": round(total_conf / total_with_pred, 1) if total_with_pred else 0,
            "value_bets": value_bets_count,
            "daily_stats": sorted(daily.values(), key=lambda x: x["date"]),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Team History ──────────────────────────────────────────────


@app.get("/api/team/{team_name}/history")
def get_team_history(team_name: str, limit: int = Query(20, ge=1, le=50)):
    """Get the last N finished matches for a given team."""
    # Query home matches
    home_matches = (
        supabase.table("fixtures")
        .select("*")
        .eq("home_team", team_name)
        .eq("status", "FT")
        .order("date", desc=True)
        .limit(limit)
        .execute()
        .data or []
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
        .data or []
    )

    # Merge and sort by date desc, keep top N
    all_matches = sorted(home_matches + away_matches, key=lambda x: x.get("date", ""), reverse=True)[:limit]

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

        results.append({
            "date": m.get("date", "")[:10],
            "opponent": opponent,
            "score": score,
            "result": result,
            "home_away": "D" if is_home else "E",
            "league_id": m.get("league_id"),
        })

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

# ─── Admin Auth Helper ──────────────────────────────────────────


def _require_admin(authorization: Optional[str]) -> dict:
    """Verify the Supabase JWT and check the user has admin role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        user_resp = supabase.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    profile = (
        supabase.table("profiles")
        .select("role")
        .eq("id", str(user_id))
        .single()
        .execute()
        .data
    )

    if not profile or profile.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return profile


# ─── Admin Endpoints ────────────────────────────────────────────

# In-memory pipeline state
_pipeline_state = {
    "status": "idle",  # idle | running | done | error
    "mode": None,
    "started_at": None,
    "finished_at": None,
    "logs": "",
    "return_code": None,
}
_pipeline_lock = threading.Lock()


def _run_pipeline_background(mode: str):
    """Run the pipeline in a background thread and capture output."""
    global _pipeline_state
    project_dir = str(Path(__file__).resolve().parent.parent)
    cmd = [sys.executable, "run_pipeline.py"]
    if mode != "full":
        cmd.append(mode)

    try:
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        # Read output in real-time
        for line in process.stdout:
            with _pipeline_lock:
                # Append new line and keep last 10k chars
                current_logs = _pipeline_state["logs"] + line
                _pipeline_state["logs"] = current_logs[-10000:]
        
        process.wait()

        with _pipeline_lock:
            _pipeline_state["status"] = "done" if process.returncode == 0 else "error"
            _pipeline_state["return_code"] = process.returncode
            _pipeline_state["finished_at"] = datetime.now().isoformat()
            
    except Exception as e:
        with _pipeline_lock:
            _pipeline_state["status"] = "error"
            _pipeline_state["logs"] += f"\nInternal Error: {str(e)}"
            _pipeline_state["finished_at"] = datetime.now().isoformat()


@app.post("/api/admin/run-pipeline")
def admin_run_pipeline(
    mode: str = Query("full", description="Pipeline mode: full, data, analyze, or results"),
    authorization: Optional[str] = Header(None),
):
    """Trigger the pipeline (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    if mode not in ("full", "data", "analyze", "results"):
        raise HTTPException(status_code=400, detail="Mode must be: full, data, analyze, or results")

    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            raise HTTPException(status_code=409, detail="Pipeline already running")

        _pipeline_state["status"] = "running"
        _pipeline_state["mode"] = mode
        _pipeline_state["started_at"] = datetime.now().isoformat()
        _pipeline_state["finished_at"] = None
        _pipeline_state["logs"] = ""
        _pipeline_state["return_code"] = None

    thread = threading.Thread(target=_run_pipeline_background, args=(mode,), daemon=True)
    thread.start()

    return {"message": f"Pipeline '{mode}' started", "started_at": _pipeline_state["started_at"]}


@app.get("/api/admin/pipeline-status")
def admin_pipeline_status(authorization: Optional[str] = Header(None)):
    """Get current pipeline status (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    with _pipeline_lock:
        return dict(_pipeline_state)


@app.post("/api/admin/update-scores")
def admin_update_scores(
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (default: today)"),
    authorization: Optional[str] = Header(None),
):
    """
    Update match scores for a given date from API Football.
    Designed to be called by a CRON job every 15 minutes during match hours.
    No auth required when called internally (Railway CRON), but JWT accepted.
    """
    # Allow unauthenticated calls from Railway CRON (internal network)
    # If Authorization header is present, validate it
    if authorization:
        try:
            _require_admin(authorization)
        except HTTPException:
            raise

    import threading as _threading

    def _run_scores():
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from fetchers.results import fetch_and_update_results
            fetch_and_update_results(date)
        except Exception as e:
            print(f"[update-scores] Error: {e}")

    t = _threading.Thread(target=_run_scores, daemon=True)
    t.start()

    from datetime import date as _date
    target = date or _date.today().isoformat()
    return {"message": f"Score update started for {target}"}

