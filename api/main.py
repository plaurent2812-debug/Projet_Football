"""
ProbaLab API — FastAPI backend for football predictions.

Serves prediction data from Supabase to the React frontend.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path

try:
    import pytz
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

# Add the parent package to the path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "ProbaLab <noreply@probalab.fr>")

from src.config import supabase
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.routers import nhl, players, stripe_webhook, telegram as telegram_router, trigger


# ── Scheduler ────────────────────────────────────────────────
def _scheduled_update_scores():
    """Called by APScheduler every 15 min between 18h-23h Paris."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from datetime import date

        from src.fetchers.results import fetch_and_update_results

        print(f"[scheduler] Mise à jour des scores — {date.today()}")
        fetch_and_update_results()
    except Exception as e:
        print(f"[scheduler] Erreur: {e}")


def _startup_update_scores():
    """Run on startup: update scores for the last 3 days (catch up)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from datetime import date, timedelta

        from src.fetchers.results import fetch_and_update_results

        print("[scheduler] 🚀 Rattrapage des scores au démarrage (J, J-1, J-2)...")
        for delta in range(3):
            d = (date.today() - timedelta(days=delta)).isoformat()
            fetch_and_update_results(d)
        print("[scheduler] ✅ Rattrapage terminé.")
    except Exception as e:
        print(f"[scheduler] Erreur rattrapage: {e}")


def _scheduled_telegram_tickets():
    """Called by APScheduler every day at 10h00 Paris timezone to send tickets to Telegram."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from datetime import date

        from src.telegram_bot import send_telegram_message
        from src.ticket_generator import format_telegram_message, generate_daily_tickets

        print(f"[scheduler] Création et envoi des tickets Telegram — {date.today()}")

        safe, fun = generate_daily_tickets()
        if safe or fun:
            message = format_telegram_message(safe, fun)
            send_telegram_message(message)
            print("[scheduler] ✅ Tickets envoyés sur Telegram.")
        else:
            print("[scheduler] ℹ️ Aucun ticket généré (pas de matchs ou probas faibles).")
    except Exception as e:
        print(f"[scheduler] Erreur Telegram: {e}")


def _scheduled_nhl_pipeline():
    """Called by APScheduler at 16h00 and 22h00 Paris — full NHL pipeline + DeepThink."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from datetime import date

        from src.fetchers.nhl_pipeline import run_nhl_pipeline

        print(f"[scheduler] 🏒 Pipeline NHL automatique — {date.today()}")
        result = run_nhl_pipeline()
        n_matches = result.get("matches", 0)
        n_players = result.get("players_analyzed", 0)
        print(f"[scheduler] 🏒 ✅ NHL terminé: {n_matches} matchs, {n_players} joueurs")
    except Exception as e:
        print(f"[scheduler] 🏒 ❌ Erreur NHL pipeline: {e}")


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

            # Envoi des tickets Telegram chaque matin à 10h00 heure Paris
            scheduler.add_job(
                _scheduled_telegram_tickets,
                trigger=CronTrigger(
                    hour="10",
                    minute="0",
                    timezone=paris_tz,
                ),
                id="telegram_tickets",
                name="Envoi tickets Paris Telegram",
                replace_existing=True,
                misfire_grace_time=600,
            )

            # 🏒 NHL Pipeline — 16h00 Paris (premier scan)
            scheduler.add_job(
                _scheduled_nhl_pipeline,
                trigger=CronTrigger(
                    hour="16",
                    minute="0",
                    timezone=paris_tz,
                ),
                id="nhl_pipeline_16h",
                name="NHL Pipeline 16h (premier scan)",
                replace_existing=True,
                misfire_grace_time=900,  # 15 min de tolérance
            )

            # 🏒 NHL Pipeline — 22h00 Paris (mise à jour lineups)
            scheduler.add_job(
                _scheduled_nhl_pipeline,
                trigger=CronTrigger(
                    hour="22",
                    minute="0",
                    timezone=paris_tz,
                ),
                id="nhl_pipeline_22h",
                name="NHL Pipeline 22h (MAJ lineups)",
                replace_existing=True,
                misfire_grace_time=900,
            )

            # Rattrapage immédiat 10s après le démarrage
            from datetime import datetime as _dt
            from datetime import timedelta as _td

            scheduler.add_job(
                _startup_update_scores,
                trigger="date",
                run_date=_dt.now() + _td(seconds=10),
                id="startup_catchup",
                name="Rattrapage scores au démarrage",
            )
            scheduler.start()
            print("[scheduler] ✅ Démarré — scores auto (18h-23h45) + NHL (16h+22h) + rattrapage dans 10s")
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
app.include_router(trigger.router)
app.include_router(telegram_router.router)
app.include_router(players.router, prefix="/api/players", tags=["Players"])

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
                    items.append(
                        {
                            "title": title,
                            "link": link,
                            "source": feed["source"],
                            "pub_date": pub_date,
                        }
                    )
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
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
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
    html = """
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
    html = """
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


def _ensure_dict(data: dict | str | None) -> dict:
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


# ─── Leagues Cache ──────────────────────────────────────────────
_league_cache: dict = {"map": {}, "fetched_at": 0}
_LEAGUE_CACHE_TTL = 3600  # 1 hour


def _get_league_map() -> dict:
    global _league_cache
    now = time.time()
    if now - _league_cache["fetched_at"] > _LEAGUE_CACHE_TTL or not _league_cache["map"]:
        try:
            leagues = supabase.table("leagues").select("api_id, name").execute().data or []
            _league_cache["map"] = {str(l["api_id"]): l["name"] for l in leagues}
            _league_cache["fetched_at"] = now
        except Exception as e:
            print(f"Error fetching leagues: {e}")
            if not _league_cache["map"]:
                return {}
    return _league_cache["map"]


# ─── Expected Value (EV+) Calculator ─────────────────────────────
def _calculate_ev(proba: float | None, odds: float | None) -> float | None:
    """EV = (Probability * Odds) - 1. Returns an edge representing expected ROI."""
    if not proba or not odds or (isinstance(odds, float) and math.isnan(odds)):
        return None
    edge = (proba / 100.0) * odds - 1.0
    return round(edge * 100, 2)  # Return as percentage (e.g. 5.4 for +5.4% EV)

def _get_ev_edges(pred: dict, odds: dict) -> dict:
    """Match model probabilities against bookmaker odds to find edges."""
    if not pred or not odds:
        return {}

    edges = {}
    
    # 1X2 Market
    edges["home"] = _calculate_ev(pred.get("proba_home"), odds.get("home_win_odds"))
    edges["draw"] = _calculate_ev(pred.get("proba_draw"), odds.get("draw_odds"))
    edges["away"] = _calculate_ev(pred.get("proba_away"), odds.get("away_win_odds"))

    # Over 2.5 Market
    proba_over_25 = pred.get("proba_over_2_5") or pred.get("proba_over_25")
    edges["over_25"] = _calculate_ev(proba_over_25, odds.get("over_25_odds"))
    
    # Under 2.5 Market
    if proba_over_25 is not None:
        edges["under_25"] = _calculate_ev(100 - proba_over_25, odds.get("under_25_odds"))

    # BTTS
    edges["btts_yes"] = _calculate_ev(pred.get("proba_btts"), odds.get("btts_yes_odds"))
    if pred.get("proba_btts") is not None:
        edges["btts_no"] = _calculate_ev(100 - pred.get("proba_btts"), odds.get("btts_no_odds"))

    # Only return positive edges (Value Bets) > 2% margin of error
    return {k: v for k, v in edges.items() if v is not None and v > 2.0}


# ─── Football DeepThink Meta-Analysis ───────────────────────────


@app.get("/api/football/meta_analysis")
def get_football_meta_analysis(
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
):
    """Return the DeepThink strategic meta-analysis for football matches."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Try dedicated table first
    try:
        resp = (
            supabase.table("football_meta_analysis")
            .select("*")
            .eq("date", date)
            .limit(1)
            .execute()
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
                return {"ok": True, "date": date, "analysis": analysis, "source": "deepthink_fallback"}
    except Exception:
        pass

    return {"ok": False, "date": date, "analysis": None, "source": None}


# ─── Paris du Soir — Best Bets ──────────────────────────────────


@app.get("/api/best-bets")
def get_best_bets(
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    sport: str | None = Query(None, description="'football' | 'nhl' | None = both"),
):
    """Return the 5 best football + 5 best NHL bets for a given date."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    result = {"date": date, "football": [], "nhl": []}

    # ── Football best bets ────────────────────────────────────────
    if sport in (None, "football"):
        try:
            next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

            # Get fixtures for that date (all statuses — include not-started AND live/finished for tracking)
            fx_resp = (
                supabase.table("fixtures")
                .select("id, home_team, away_team, date, status")
                .gte("date", f"{date}T00:00:00Z")
                .lt("date", f"{next_day}T00:00:00Z")
                .execute()
            )
            fx_map = {f["id"]: f for f in (fx_resp.data or [])}

            if fx_map:
                pred_resp = (
                    supabase.table("predictions")
                    .select(
                        "fixture_id, proba_home, proba_draw, proba_away, "
                        "proba_btts, proba_over_2_5, proba_over_15, "
                        "recommended_bet, confidence_score, is_value_bet, "
                        "analysis_text, proba_over_35"
                    )
                    .in_("fixture_id", list(fx_map.keys()))
                    .gte("confidence_score", 6)
                    .order("confidence_score", desc=True)
                    .execute()
                )

                football_bets = []
                for p in (pred_resp.data or []):
                    fix = fx_map.get(p["fixture_id"])
                    if not fix:
                        continue

                    # Build candidate bets from all markets
                    probas = {
                        "Victoire domicile": p.get("proba_home") or 0,
                        "Match nul": p.get("proba_draw") or 0,
                        "Victoire extérieur": p.get("proba_away") or 0,
                        "BTTS — Les deux équipes marquent": p.get("proba_btts") or 0,
                        "Over 2.5 buts": p.get("proba_over_2_5") or 0,
                        "Over 1.5 buts": p.get("proba_over_15") or 0,
                        "Over 3.5 buts": p.get("proba_over_35") or 0,
                    }

                    for market, proba in probas.items():
                        if proba < 55:
                            continue
                        implied_odds = round(100 / proba, 2) if proba > 0 else 0
                        # Target window: 1.65 – 2.30
                        if not (1.65 <= implied_odds <= 2.30):
                            continue

                        ev_score = (proba / 100) * implied_odds - 1
                        composite = (p.get("confidence_score") or 0) * 10 + ev_score * 50 + proba * 0.3

                        football_bets.append({
                            "id": None,
                            "fixture_id": p["fixture_id"],
                            "label": f"{fix['home_team']} vs {fix['away_team']} — {market}",
                            "market": market,
                            "odds": implied_odds,
                            "confidence": p.get("confidence_score") or 0,
                            "proba_model": proba,
                            "is_value": bool(p.get("is_value_bet")),
                            "ev_score": round(ev_score, 3),
                            "composite": composite,
                            "result": "PENDING",
                        })

                # Sort by composite score, dedupe by fixture
                football_bets.sort(key=lambda x: -x["composite"])
                seen_fixtures = set()
                top5 = []
                for bet in football_bets:
                    if bet["fixture_id"] not in seen_fixtures:
                        top5.append(bet)
                        seen_fixtures.add(bet["fixture_id"])
                    if len(top5) >= 5:
                        break

                result["football"] = top5

        except Exception as e:
            result["football_error"] = str(e)


    # ── NHL best bets ─────────────────────────────────────────────
    if sport in (None, "nhl"):
        try:
            next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

            # ── Step 1: Real bookmaker odds from nhl_odds ─────────
            real_odds_resp = (
                supabase.table("nhl_odds")
                .select("player_name, bookmaker, over_odds, home_team, away_team, game_id, line")
                .eq("game_date", date)
                .gte("over_odds", 1.40)    # cotes >= 1.40 uniquement
                .order("over_odds", desc=True)
                .limit(200)
                .execute()
            )
            real_odds_raw = real_odds_resp.data or []

            # Build player→best odds map (highest odds across bookmakers = best value)
            player_odds_map: dict[str, dict] = {}
            for row in real_odds_raw:
                name = row.get("player_name", "").strip()
                if not name:
                    continue
                odds_val = float(row.get("over_odds") or 0)
                if odds_val <= 1.0:
                    continue
                existing = player_odds_map.get(name)
                if existing is None or odds_val > existing["odds"]:
                    player_odds_map[name] = {
                        "odds": odds_val,
                        "bookmaker": row.get("bookmaker", ""),
                        "home_team": row.get("home_team", ""),
                        "away_team": row.get("away_team", ""),
                        "game_id": row.get("game_id", ""),
                        "line": float(row.get("line") or 0.5),
                    }

            has_real_odds = len(player_odds_map) > 0

            # ── Step 2: Model probabilities from nhl_fixtures.stats_json ────
            # prob_point from the pipeline (~20-60%) matches the Over 0.5 Points market.
            # nhl_data_lake.python_prob = goal probability (~5-15%) — incompatible for EV vs point props.
            fixtures_resp = (
                supabase.table("nhl_fixtures")
                .select("home_team, away_team, stats_json")
                .gte("date", f"{date}T00:00:00Z")
                .lt("date", f"{next_day}T00:00:00Z")
                .execute()
            )

            # Build model map: player_name → {ppg, prob_goal, team, ...}
            model_map: dict[str, dict] = {}
            for fx in (fixtures_resp.data or []):
                top_players = (fx.get("stats_json") or {}).get("top_players", [])
                for p in top_players:
                    name = (p.get("player_name") or "").strip()
                    if not name or name in model_map:
                        continue
                    model_map[name] = {
                        "ppg": float(p.get("points_per_game") or 0),     # for Poisson P(point)
                        "prob_goal": float(p.get("prob_goal") or 0),
                        "prob_assist": float(p.get("prob_assist") or 0),
                        "team": p.get("team", ""),
                        "opp": p.get("opp", ""),
                        "is_home": p.get("is_home", 0),
                        "algo_score_goal": p.get("algo_score_goal", 0),
                        "home_team": fx.get("home_team", ""),
                        "away_team": fx.get("away_team", ""),
                    }

            # ── Step 3: Fuzzy name matching helper ────────────────
            def normalize_name(s: str) -> str:
                """Lowercase, remove accents & punctuation for matching."""
                import unicodedata
                s = unicodedata.normalize("NFD", s.lower())
                s = "".join(c for c in s if unicodedata.category(c) != "Mn")
                return s.replace("-", " ").replace("'", "").strip()

            # ── Step 4: Join odds + model → value bets ────────────
            nhl_bets = []

            if has_real_odds:
                # MODE A: Real odds available — only show genuine value bets
                norm_model_map = {normalize_name(k): v for k, v in model_map.items()}

                for player_name, odds_data in player_odds_map.items():
                    bookie_odds = odds_data["odds"]
                    bookie_implied_prob = 100.0 / bookie_odds  # implied prob for Over 0.5 Points

                    # Match player to model via normalized name
                    norm_name = normalize_name(player_name)
                    model_data = norm_model_map.get(norm_name)

                    # Try partial (last name) match if exact fails
                    if model_data is None:
                        parts = norm_name.split()
                        if len(parts) >= 2:
                            last = parts[-1]
                            for k, v in norm_model_map.items():
                                if last in k:
                                    model_data = v
                                    break

                    if model_data is None:
                        continue  # no model data → skip

                    # P(Over 0.5 Points) = 1 - exp(-ppg)  [Poisson with seasonal avg]
                    # This gives comparable probabilities to bookmaker's Over 0.5 Pts market (50-70% range)
                    import math as _math
                    ppg = float(model_data.get("ppg") or 0)
                    if ppg <= 0:
                        continue

                    point_prob_raw = 1.0 - _math.exp(-ppg)   # Poisson P(X >= 1)
                    point_prob_pct = round(point_prob_raw * 100, 1)

                    # EV = model_prob * bookie_odds - 1
                    ev = round(point_prob_raw * bookie_odds - 1, 3)
                    if ev <= 0:
                        continue  # negative EV → not a value bet

                    # Build label
                    ht = model_data.get("home_team") or odds_data.get("home_team", "")
                    at = model_data.get("away_team") or odds_data.get("away_team", "")
                    team_abbrev = model_data.get("team", "")
                    NHL_ABBREV_TO_NAME_LOCAL = {
                        "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
                        "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks",
                        "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
                        "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
                        "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montréal Canadiens",
                        "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders",
                        "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
                        "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks", "SEA": "Seattle Kraken",
                        "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
                        "UTA": "Utah Hockey Club", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
                        "WSH": "Washington Capitals", "WPG": "Winnipeg Jets",
                    }
                    team_name = NHL_ABBREV_TO_NAME_LOCAL.get(team_abbrev, team_abbrev)
                    is_home = model_data.get("is_home", False)
                    if ht and at:
                        label = f"{player_name} Over 0.5 Points — {ht} vs {at}"
                    else:
                        opp = model_data.get("opp", "")
                        home_away = "vs" if is_home else "@"
                        label = f"{player_name} Over 0.5 Points — {team_name} {home_away} {opp}"

                    nhl_bets.append({
                        "id": None,
                        "player_name": player_name,
                        "team": team_abbrev,
                        "label": label,
                        "market": "player_points_over_0.5",
                        "odds": round(bookie_odds, 2),
                        "confidence": min(10, max(1, int(ev * 20))),
                        "proba_model": round(point_prob_pct, 1),
                        "proba_bookmaker": round(bookie_implied_prob, 1),
                        "ev": ev,
                        "bookmaker": odds_data.get("bookmaker", ""),
                        "is_value": ev > 0.03,
                        "algo_score_goal": model_data.get("algo_score_goal") or 0,
                        "result": "PENDING",
                        "odds_source": "real",
                    })

                # Sort by EV descending, take top 5
                nhl_bets.sort(key=lambda x: -x["ev"])
                result["nhl"] = nhl_bets[:5]
                result["nhl_odds_source"] = "real"

            else:
                # MODE B: No real odds yet
                result["nhl"] = []
                result["nhl_note"] = (
                    f"Les cotes bookmaker NHL pour le {date} ne sont pas encore disponibles "
                    f"(fetch planifié à 21h). Revenez plus tard pour voir les vraies cotes."
                )
                result["nhl_odds_source"] = "pending"

        except Exception as e:
            result["nhl_error"] = str(e)


    # ── Enrich with saved tracking results ───────────────────────
    try:
        saved = (
            supabase.table("best_bets")
            .select("*")
            .eq("date", date)
            .execute()
        )
        saved_map = {}
        for s in (saved.data or []):
            saved_map[s["bet_label"]] = s

        for bet in result["football"]:
            if bet["label"] in saved_map:
                s = saved_map[bet["label"]]
                bet["id"] = s["id"]
                bet["result"] = s.get("result", "PENDING")
                bet["notes"] = s.get("notes", "")

        for bet in result["nhl"]:
            if bet["label"] in saved_map:
                s = saved_map[bet["label"]]
                bet["id"] = s["id"]
                bet["result"] = s.get("result", "PENDING")
                bet["notes"] = s.get("notes", "")

    except Exception:
        pass

    return result


@app.patch("/api/best-bets/{bet_id}/result")
def update_bet_result(
    bet_id: int,
    body: dict,
):
    """Update the result of a tracked bet (admin only — secured by API key)."""
    result_val = body.get("result", "").upper()
    if result_val not in ("WIN", "LOSS", "VOID", "PENDING"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="result must be WIN, LOSS, VOID or PENDING")

    try:
        resp = (
            supabase.table("best_bets")
            .update({
                "result": result_val,
                "notes": body.get("notes", ""),
                "updated_at": datetime.now().isoformat(),
            })
            .eq("id", bet_id)
            .execute()
        )
        return {"ok": True, "updated": resp.data}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/best-bets/save")
def save_best_bets(body: dict):
    """Save a best bet to the tracking table."""
    try:
        bet_data = {
            "date": body.get("date"),
            "sport": body.get("sport"),
            "bet_label": body.get("label"),
            "market": body.get("market"),
            "odds": body.get("odds"),
            "confidence": body.get("confidence"),
            "proba_model": body.get("proba_model"),
            "fixture_id": body.get("fixture_id"),
            "player_name": body.get("player_name"),
            "result": "PENDING",
        }
        resp = supabase.table("best_bets").insert(bet_data).execute()
        return {"ok": True, "id": resp.data[0]["id"] if resp.data else None}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/nhl/fetch-game-stats")
def nhl_fetch_game_stats(body: dict, authorization: str = Header(None)):
    """
    Called by Trigger.dev before resolve: fetches actual player stats
    from the NHL API boxscore and stores them in nhl_player_game_stats.
    """
    expected = f"Bearer {os.getenv('CRON_SECRET', 'super_secret_probalab_2026')}"
    if authorization != expected:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")

    date = body.get("date")
    if not date:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="date required (YYYY-MM-DD)")

    try:
        from src.nhl.fetch_game_stats import fetch_and_store_game_stats
        result = fetch_and_store_game_stats(date)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/nhl/fetch-odds")
def nhl_fetch_odds(body: dict, authorization: str = Header(None)):
    """
    Fetches real NHL player prop odds from The Odds API and stores in nhl_odds.
    Called by the NHL pipeline (schedule-nhl-pipeline or admin trigger).
    Requires ODDS_API_KEY env var to be set.
    """
    expected = f"Bearer {os.getenv('CRON_SECRET', 'super_secret_probalab_2026')}"
    if authorization != expected:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")

    date = body.get("date") or datetime.now().strftime("%Y-%m-%d")

    try:
        from src.nhl.fetch_odds import run as fetch_nhl_odds
        result = fetch_nhl_odds(date)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}




@app.post("/api/best-bets/resolve")
def resolve_best_bets(body: dict, authorization: str = Header(None)):
    """
    Called by Trigger.dev scheduled tasks to auto-resolve PENDING bets.
    Checks match results and updates best_bets table with WIN/LOSS/VOID.
    """
    # Simple auth check
    expected = f"Bearer {os.getenv('CRON_SECRET', 'super_secret_probalab_2026')}"
    if authorization != expected:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")

    date = body.get("date")
    sport = body.get("sport")  # "football" or "nhl"

    if not date or sport not in ("football", "nhl"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="date and sport (football|nhl) required")

    resolved = []
    errors = []

    # ── Load pending bets ─────────────────────────────────────────
    pending = (
        supabase.table("best_bets")
        .select("*")
        .eq("date", date)
        .eq("sport", sport)
        .eq("result", "PENDING")
        .execute()
    )
    bets = pending.data or []

    if not bets:
        return {"ok": True, "date": date, "sport": sport, "resolved": 0, "message": "No pending bets"}

    # ── Football resolution ───────────────────────────────────────
    if sport == "football":
        next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

        # Fetch finished fixtures for that date
        fx_resp = (
            supabase.table("fixtures")
            .select("id, home_team, away_team, home_goals, away_goals, status")
            .gte("date", f"{date}T00:00:00Z")
            .lt("date", f"{next_day}T00:00:00Z")
            .in_("status", ["FT", "AET", "PEN"])
            .execute()
        )
        finished = {f["id"]: f for f in (fx_resp.data or [])}

        # Build a map by team names too (for label matching)
        fx_by_teams = {}
        for f in (fx_resp.data or []):
            key = f"{f['home_team']} vs {f['away_team']}"
            fx_by_teams[key] = f

        for bet in bets:
            try:
                label = bet["bet_label"]   # e.g. "PSG vs Lyon — Over 2.5 buts"
                market = bet["market"]
                fixture_id = bet.get("fixture_id")

                # Try to find the fixture
                fx = None
                if fixture_id and fixture_id in finished:
                    fx = finished[fixture_id]
                else:
                    # Try matching by label prefix "Home vs Away —"
                    for key, f in fx_by_teams.items():
                        if label.startswith(key):
                            fx = f
                            break

                if not fx:
                    # Match not finished yet or not found
                    continue

                h = fx.get("home_goals") or 0
                a = fx.get("away_goals") or 0
                total = h + a

                # Evaluate market
                result_val = None
                if market == "Victoire domicile":
                    result_val = "WIN" if h > a else "LOSS"
                elif market == "Victoire extérieur":
                    result_val = "WIN" if a > h else "LOSS"
                elif market == "Match nul":
                    result_val = "WIN" if h == a else "LOSS"
                elif market == "Over 2.5 buts":
                    result_val = "WIN" if total > 2.5 else "LOSS"
                elif market == "Over 1.5 buts":
                    result_val = "WIN" if total > 1.5 else "LOSS"
                elif market == "Over 3.5 buts":
                    result_val = "WIN" if total > 3.5 else "LOSS"
                elif market in ("BTTS — Les deux équipes marquent", "BTTS"):
                    result_val = "WIN" if (h > 0 and a > 0) else "LOSS"
                else:
                    # Unknown market
                    continue

                # Update best_bets
                (
                    supabase.table("best_bets")
                    .update({
                        "result": result_val,
                        "notes": f"Auto-résolu: {h}-{a} ({fx['status']})",
                        "updated_at": datetime.now().isoformat(),
                    })
                    .eq("id", bet["id"])
                    .execute()
                )
                resolved.append({
                    "id": bet["id"],
                    "label": label,
                    "result": result_val,
                    "score": f"{h}-{a}",
                })

            except Exception as e:
                errors.append({"bet_id": bet.get("id"), "error": str(e)})

    # ── NHL resolution ────────────────────────────────────────────
    elif sport == "nhl":
        next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

        NHL_NAME_TO_ABBREV = {
            "Anaheim Ducks": "ANA", "Boston Bruins": "BOS", "Buffalo Sabres": "BUF",
            "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR", "Chicago Blackhawks": "CHI",
            "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ", "Dallas Stars": "DAL",
            "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM", "Florida Panthers": "FLA",
            "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN", "Montreal Canadiens": "MTL",
            "Montréal Canadiens": "MTL", "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
            "New York Islanders": "NYI", "New York Rangers": "NYR", "Ottawa Senators": "OTT",
            "Philadelphia Flyers": "PHI", "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS",
            "Seattle Kraken": "SEA", "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL",
            "Toronto Maple Leafs": "TOR", "Utah Hockey Club": "UTA", "Vancouver Canucks": "VAN",
            "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH", "Winnipeg Jets": "WPG",
        }

        # Fetch finished NHL fixtures for that game date
        # NHL games listed for date D start between 1h-4h Paris = previous UTC day
        # The Trigger task already adjusts the date, so we search D and D+1
        nhl_resp = (
            supabase.table("nhl_fixtures")
            .select("id, home_team, away_team, home_score, away_score, status")
            .gte("date", f"{date}T00:00:00Z")
            .lt("date", f"{next_day}T23:59:59Z")
            .in_("status", ["FT", "Final", "Official", "OFF"])
            .execute()
        )
        finished_nhl = nhl_resp.data or []

        # Build team-abbrev → fixture map
        fx_by_team = {}
        for f in finished_nhl:
            h_abbrev = NHL_NAME_TO_ABBREV.get(f["home_team"], f["home_team"])
            a_abbrev = NHL_NAME_TO_ABBREV.get(f["away_team"], f["away_team"])
            fx_by_team[h_abbrev] = f
            fx_by_team[a_abbrev] = f

        # ── Real stats resolution from nhl_player_game_stats ─────
        # The table is populated by fetch_game_stats.py (called before this endpoint)
        for bet in bets:
            try:
                label = bet["bet_label"]
                player_name = bet.get("player_name", "")
                if not player_name:
                    # Extract from label: "Leon Draisaitl Over 0.5 Points — EDM vs CAR"
                    parts = label.split(" Over 0.5 Points")
                    player_name = parts[0].strip() if parts else ""

                if not player_name:
                    errors.append({"bet_id": bet.get("id"), "error": "Cannot extract player name"})
                    continue

                # Lookup real stats for that player on game date
                stats_resp = (
                    supabase.table("nhl_player_game_stats")
                    .select("player_name, team, goals, assists, points, shots, game_id")
                    .ilike("player_name", f"%{player_name}%")
                    .eq("game_date", date)
                    .limit(1)
                    .execute()
                )

                if not stats_resp.data:
                    # Stats not yet loaded — check if the game is finished at all
                    player_team = bet.get("team", "")
                    fx = fx_by_team.get(player_team) if player_team else None
                    if fx and fx.get("home_score") is not None:
                        # Game finished but stats not yet in DB — try tomorrow's Trigger run
                        # or mark VOID if we've already waited
                        errors.append({
                            "bet_id": bet.get("id"),
                            "error": f"Stats missing for {player_name} on {date} — will retry",
                        })
                    # else: game not finished yet, skip silently
                    continue

                p_stats = stats_resp.data[0]
                actual_points = int(p_stats.get("points") or 0)
                actual_goals = int(p_stats.get("goals") or 0)
                actual_shots = int(p_stats.get("shots") or 0)
                game_id = p_stats.get("game_id")

                # Determine result based on market
                market = bet.get("market", "player_points_over_0.5")
                if market == "player_points_over_0.5":
                    result_val = "WIN" if actual_points >= 1 else "LOSS"
                elif market == "player_goals_over_0.5":
                    result_val = "WIN" if actual_goals >= 1 else "LOSS"
                elif market == "player_shots_over_2.5":
                    result_val = "WIN" if actual_shots >= 3 else "LOSS"
                else:
                    result_val = "WIN" if actual_points >= 1 else "LOSS"

                note = (
                    f"Auto-résolu: {p_stats['player_name']} — "
                    f"{actual_goals}G {actual_points - actual_goals}A = {actual_points}Pts "
                    f"({actual_shots} tirs) · match {game_id}"
                )

                (
                    supabase.table("best_bets")
                    .update({
                        "result": result_val,
                        "notes": note,
                        "updated_at": datetime.now().isoformat(),
                    })
                    .eq("id", bet["id"])
                    .execute()
                )
                resolved.append({
                    "id": bet["id"],
                    "label": label,
                    "player": player_name,
                    "result": result_val,
                    "goals": actual_goals,
                    "points": actual_points,
                })

            except Exception as e:
                errors.append({"bet_id": bet.get("id"), "error": str(e)})

    return {
        "ok": True,
        "date": date,
        "sport": sport,
        "resolved_count": len(resolved),
        "resolved": resolved,
        "errors": errors,
    }


@app.get("/api/best-bets/stats")
def get_best_bets_stats():
    """Return win rate and ROI stats for both model predictions (best_bets) and expert picks."""
    try:
        from collections import defaultdict

        def calc_stats(bets):
            resolved = [b for b in bets if b["result"] in ("WIN", "LOSS")]
            wins = sum(1 for b in resolved if b["result"] == "WIN")
            losses = sum(1 for b in resolved if b["result"] == "LOSS")
            voids = sum(1 for b in bets if b["result"] == "VOID")
            total = wins + losses
            win_rate = round(wins / total * 100, 1) if total else 0
            roi = 0
            for b in resolved:
                if b["result"] == "WIN":
                    roi += (float(b.get("odds") or 1.85) - 1)
                else:
                    roi -= 1
            roi_pct = round(roi / total * 100, 1) if total else 0
            return {"wins": wins, "losses": losses, "voids": voids, "total": total, "win_rate": win_rate, "roi_pct": roi_pct}

        # ── 1. Expert picks stats (Paris de l'Expert) ─────────────
        expert_resp = (
            supabase.table("expert_picks")
            .select("sport, result, date, odds, market")
            .neq("result", "PENDING")
            .order("date", desc=True)
            .limit(500)
            .execute()
        )
        expert_rows = expert_resp.data or []

        expert_football = [b for b in expert_rows if b["sport"] == "football"]
        expert_nhl = [b for b in expert_rows if b["sport"] == "nhl"]

        # Expert market breakdown
        expert_market_stats = defaultdict(list)
        for b in expert_rows:
            expert_market_stats[b.get("market", "unknown")].append(b)
        expert_market_breakdown = {}
        for market, bets in expert_market_stats.items():
            s = calc_stats(bets)
            if s["total"] > 0:
                expert_market_breakdown[market] = s

        # Expert streak (last 10)
        expert_resolved = [b for b in expert_rows if b["result"] in ("WIN", "LOSS")]
        expert_resolved.sort(key=lambda b: b.get("date", ""), reverse=True)
        expert_last_10 = [b["result"] for b in expert_resolved[:10]]

        # Expert best pick
        expert_wins = [b for b in expert_resolved if b["result"] == "WIN"]
        expert_best_pick = None
        if expert_wins:
            best = max(expert_wins, key=lambda b: float(b.get("odds") or 0))
            expert_best_pick = {
                "label": best.get("market", ""),
                "odds": float(best.get("odds") or 0),
                "date": best.get("date", ""),
                "market": best.get("market", ""),
                "sport": best.get("sport", ""),
            }

        # Expert cumulative P&L
        expert_pl = {}
        for b in expert_rows:
            if b["result"] not in ("WIN", "LOSS"):
                continue
            d = b["date"]
            if d not in expert_pl:
                expert_pl[d] = 0
            if b["result"] == "WIN":
                expert_pl[d] += (float(b.get("odds") or 1.85) - 1)
            else:
                expert_pl[d] -= 1
        expert_cumulative = []
        running = 0
        for d in sorted(expert_pl.keys()):
            running += expert_pl[d]
            expert_cumulative.append({"date": d, "pl": round(running, 2)})

        # Expert timeline
        expert_timeline = defaultdict(lambda: {"wins": 0, "losses": 0})
        for b in expert_rows:
            if b["result"] in ("WIN", "LOSS"):
                d = b["date"]
                if b["result"] == "WIN":
                    expert_timeline[d]["wins"] += 1
                else:
                    expert_timeline[d]["losses"] += 1

        # ── 2. Model predictions stats (best_bets — ProbaLab IA) ──
        model_resp = (
            supabase.table("best_bets")
            .select("sport, result, date, odds, market")
            .neq("result", "PENDING")
            .order("date", desc=True)
            .limit(500)
            .execute()
        )
        model_rows = model_resp.data or []

        model_football = [b for b in model_rows if b["sport"] == "football"]
        model_nhl = [b for b in model_rows if b["sport"] == "nhl"]

        # Model market breakdown (BTTS, Over 2.5, player_points, etc.)
        model_market_stats = defaultdict(list)
        for b in model_rows:
            model_market_stats[b.get("market", "unknown")].append(b)
        model_market_breakdown = {}
        for market, bets in model_market_stats.items():
            s = calc_stats(bets)
            if s["total"] > 0:
                model_market_breakdown[market] = s
        # ── 3. Combined stats (expert + model merged) ────────────
        all_rows = expert_rows + model_rows
        all_football = [b for b in all_rows if b["sport"] == "football"]
        all_nhl = [b for b in all_rows if b["sport"] == "nhl"]

        # Combined market breakdown
        combined_market_stats = defaultdict(list)
        for b in all_rows:
            combined_market_stats[b.get("market", "unknown")].append(b)
        combined_market_breakdown = {}
        for market, bets in combined_market_stats.items():
            s = calc_stats(bets)
            if s["total"] > 0:
                combined_market_breakdown[market] = s

        # Combined timeline
        combined_timeline = defaultdict(lambda: {"wins": 0, "losses": 0})
        for b in all_rows:
            if b["result"] in ("WIN", "LOSS"):
                d = b["date"]
                if b["result"] == "WIN":
                    combined_timeline[d]["wins"] += 1
                else:
                    combined_timeline[d]["losses"] += 1

        # Combined streak (last 10)
        all_resolved = [b for b in all_rows if b["result"] in ("WIN", "LOSS")]
        all_resolved.sort(key=lambda b: b.get("date", ""), reverse=True)
        combined_last_10 = [b["result"] for b in all_resolved[:10]]

        # Combined cumulative P&L
        combined_pl = {}
        for b in all_rows:
            if b["result"] not in ("WIN", "LOSS"):
                continue
            d = b["date"]
            if d not in combined_pl:
                combined_pl[d] = 0
            if b["result"] == "WIN":
                combined_pl[d] += (float(b.get("odds") or 1.85) - 1)
            else:
                combined_pl[d] -= 1
        combined_cumulative = []
        running = 0
        for d in sorted(combined_pl.keys()):
            running += combined_pl[d]
            combined_cumulative.append({"date": d, "pl": round(running, 2)})

        # Combined best pick
        combined_wins = [b for b in all_resolved if b["result"] == "WIN"]
        combined_best_pick = None
        if combined_wins:
            best = max(combined_wins, key=lambda b: float(b.get("odds") or 0))
            combined_best_pick = {
                "label": best.get("bet_label", best.get("market", "")),
                "odds": float(best.get("odds") or 0),
                "date": best.get("date", ""),
                "market": best.get("market", ""),
                "sport": best.get("sport", ""),
            }

        return {
            # Combined stats (all sources)
            "global": calc_stats(all_rows),
            "football": calc_stats(all_football),
            "nhl": calc_stats(all_nhl),
            "by_market": combined_market_breakdown,
            "timeline": [{"date": k, **v} for k, v in sorted(combined_timeline.items())[-30:]],
            "last_10": combined_last_10,
            "best_pick": combined_best_pick,
            "cumulative_pl": combined_cumulative[-60:],
            # Model predictions only (ProbaLab IA accuracy)
            "model_global": calc_stats(model_rows),
            "model_football": calc_stats(model_football),
            "model_nhl": calc_stats(model_nhl),
            "model_by_market": model_market_breakdown,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/best-bets/history")
def get_best_bets_history(
    days: int = Query(30, description="Number of days to look back"),
    sport: str | None = Query(None, description="'football' | 'nhl' | None = both"),
):
    """Return all resolved picks from both best_bets and expert_picks for the history table."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # ── 1. Fetch from best_bets (model predictions) ──────────
        bb_query = (
            supabase.table("best_bets")
            .select("id, date, sport, bet_label, market, odds, confidence, result, player_name")
            .gte("date", cutoff)
            .order("date", desc=True)
            .limit(300)
        )
        if sport:
            bb_query = bb_query.eq("sport", sport)
        bb_rows = bb_query.execute().data or []

        # Tag source
        for r in bb_rows:
            r["source"] = "model"

        # ── 2. Fetch from expert_picks (Telegram expert bets) ────
        ep_query = (
            supabase.table("expert_picks")
            .select("id, date, sport, market, match_label, odds, confidence, result, player_name, expert_note, notes")
            .gte("date", cutoff)
            .order("date", desc=True)
            .limit(300)
        )
        if sport:
            ep_query = ep_query.eq("sport", sport)
        ep_rows = ep_query.execute().data or []

        # Map field names for frontend compatibility
        for r in ep_rows:
            r["bet_label"] = r.get("match_label") or r.get("market") or "Pick Expert"
            r["source"] = "expert"

        # ── 3. Merge and sort by date descending ─────────────────
        all_rows = bb_rows + ep_rows
        all_rows.sort(key=lambda r: r.get("date", ""), reverse=True)

        # Calculate running P&L
        resolved = [r for r in all_rows if r["result"] in ("WIN", "LOSS")]
        total_pl = 0
        for r in resolved:
            if r["result"] == "WIN":
                total_pl += (float(r.get("odds") or 1.85) - 1)
            else:
                total_pl -= 1

        return {
            "picks": all_rows[:300],
            "total": len(all_rows),
            "resolved": len(resolved),
            "total_pl": round(total_pl, 2),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/expert-picks")
def get_expert_picks(
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    sport: str | None = Query(None, description="'nhl' | 'football' | None = all"),
):
    """Return expert picks (submitted via Telegram bot) for a given date."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        query = (
            supabase.table("expert_picks")
            .select("id, date, sport, player_name, market, match_label, odds, confidence, expert_note, result, created_at")
            .eq("date", date)
            .order("created_at", desc=False)
        )
        if sport:
            query = query.eq("sport", sport)
        resp = query.execute()
        return {"date": date, "picks": resp.data or []}
    except Exception as e:
        return {"date": date, "picks": [], "error": str(e)}


@app.delete("/api/expert-picks/{pick_id}")
def delete_expert_pick(pick_id: int):
    """Delete an expert pick by ID — admin only (enforced in UI)."""
    try:
        supabase.table("expert_picks").delete().eq("id", pick_id).execute()
        return {"deleted": True, "id": pick_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/expert-picks/resolve")
def resolve_expert_picks(body: dict, authorization: str = Header(None)):
    """
    Auto-resolve PENDING expert picks by matching to finished fixtures
    and using Gemini to evaluate WIN/LOSS from free-text bet descriptions.
    Called by Trigger.dev cron each morning.
    """
    expected = f"Bearer {os.getenv('CRON_SECRET', 'super_secret_probalab_2026')}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    date = body.get("date")
    sport = body.get("sport")  # optional: "football" or "nhl"
    if not date:
        raise HTTPException(status_code=400, detail="date required (YYYY-MM-DD)")

    resolved = []
    errors = []

    # ── 1. Load pending expert picks ──────────────────────────────
    query = (
        supabase.table("expert_picks")
        .select("*")
        .eq("date", date)
        .eq("result", "PENDING")
    )
    if sport:
        query = query.eq("sport", sport)
    pending = query.execute()
    picks = pending.data or []

    if not picks:
        return {"ok": True, "date": date, "resolved": 0, "message": "No pending picks"}

    # ── 2. Load finished fixtures for that date ───────────────────
    next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")
    fx_resp = (
        supabase.table("fixtures")
        .select("id, home_team, away_team, home_goals, away_goals, status")
        .gte("date", f"{date}T00:00:00Z")
        .lt("date", f"{next_day}T23:59:59Z")
        .in_("status", ["FT", "AET", "PEN"])
        .execute()
    )
    finished_fixtures = fx_resp.data or []

    if not finished_fixtures:
        return {"ok": True, "date": date, "resolved": 0, "message": "No finished fixtures"}

    # Build lookup by team names (lowercased for fuzzy matching)
    fx_list_for_search = []
    for f in finished_fixtures:
        fx_list_for_search.append({
            "home": f["home_team"],
            "away": f["away_team"],
            "home_goals": f.get("home_goals") or 0,
            "away_goals": f.get("away_goals") or 0,
            "status": f["status"],
        })

    # ── 3. Setup Gemini for evaluation ────────────────────────────
    import json as _json
    from google import genai
    from google.genai import types as gtypes

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY missing"}
    gemini_client = genai.Client(api_key=api_key)

    def _evaluate_bet(bet_description: str, match_label: str, score_home: int, score_away: int, home_team: str, away_team: str) -> str | None:
        """Use Gemini to evaluate if a bet is WIN or LOSS given the final score."""
        prompt = f"""Tu es un expert en paris sportifs. Un pari a été placé et le match est terminé.
Détermine si le pari est GAGNÉ (WIN) ou PERDU (LOSS).

Match : {home_team} vs {away_team}
Score final : {home_team} {score_home} - {score_away} {away_team}

Pari : {bet_description}

Réponds UNIQUEMENT par un JSON: {{"result": "WIN"}} ou {{"result": "LOSS"}}
"""
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=50,
                ),
            )
            text = (response.text or "").strip()
            # Extract result
            if "WIN" in text.upper():
                return "WIN"
            elif "LOSS" in text.upper():
                return "LOSS"
            return None
        except Exception as e:
            print(f"[Expert Resolve] Gemini error: {e}")
            return None

    def _fuzzy_match_fixture(match_label: str, fixtures_list: list) -> dict | None:
        """Try to find a fixture that matches the match_label string."""
        if not match_label:
            return None
        label_lower = match_label.lower().strip()
        for fx in fixtures_list:
            home_l = fx["home"].lower()
            away_l = fx["away"].lower()
            # Check if both team names appear in the label
            if home_l in label_lower and away_l in label_lower:
                return fx
            # Also check partial matches (first word of team name)
            home_first = home_l.split()[0] if home_l else ""
            away_first = away_l.split()[0] if away_l else ""
            if len(home_first) > 3 and len(away_first) > 3:
                if home_first in label_lower and away_first in label_lower:
                    return fx
        return None

    # ── 4. Process each pick ──────────────────────────────────────
    import time as _time

    for pick in picks:
        try:
            match_label = pick.get("match_label", "")
            market = pick.get("market", "")
            expert_note = pick.get("expert_note", "")

            # Parse selections for combinés
            selections = []
            try:
                if expert_note and expert_note.startswith("["):
                    selections = _json.loads(expert_note)
            except Exception:
                pass

            is_combine = len(selections) > 1

            if is_combine:
                # ── Combiné: ALL selections must WIN ──────────────
                all_win = True
                details = []
                for sel in selections:
                    sel_bet = sel.get("bet", "")
                    sel_match = sel.get("match", "")
                    fx = _fuzzy_match_fixture(sel_match, fx_list_for_search)
                    if not fx:
                        # Match not found/finished yet → can't resolve
                        all_win = None
                        details.append(f"⏳ {sel_match}: match non trouvé")
                        break
                    result = _evaluate_bet(
                        sel_bet, sel_match,
                        fx["home_goals"], fx["away_goals"],
                        fx["home"], fx["away"]
                    )
                    _time.sleep(0.5)  # Rate limit
                    if result == "WIN":
                        details.append(f"✅ {sel_bet} ({fx['home']} {fx['home_goals']}-{fx['away_goals']} {fx['away']})")
                    elif result == "LOSS":
                        all_win = False
                        details.append(f"❌ {sel_bet} ({fx['home']} {fx['home_goals']}-{fx['away_goals']} {fx['away']})")
                    else:
                        all_win = None
                        details.append(f"❓ {sel_bet}: évaluation impossible")
                        break

                if all_win is None:
                    errors.append({"pick_id": pick["id"], "error": "Incomplete evaluation", "details": details})
                    continue

                final_result = "WIN" if all_win else "LOSS"
                note = " | ".join(details)

            else:
                # ── Pari simple ───────────────────────────────────
                fx = _fuzzy_match_fixture(match_label, fx_list_for_search)
                if not fx:
                    # Try with selections[0].match if available
                    if selections and selections[0].get("match"):
                        fx = _fuzzy_match_fixture(selections[0]["match"], fx_list_for_search)
                if not fx:
                    continue  # Match not finished yet

                bet_desc = market
                if selections and selections[0].get("bet"):
                    bet_desc = selections[0]["bet"]

                final_result = _evaluate_bet(
                    bet_desc, match_label,
                    fx["home_goals"], fx["away_goals"],
                    fx["home"], fx["away"]
                )
                _time.sleep(0.5)
                if not final_result:
                    errors.append({"pick_id": pick["id"], "error": "Gemini evaluation failed"})
                    continue

                note = f"Auto-résolu: {fx['home']} {fx['home_goals']}-{fx['away_goals']} {fx['away']} ({fx['status']})"

            # ── Update in DB ──────────────────────────────────────
            (
                supabase.table("expert_picks")
                .update({
                    "result": final_result,
                    "notes": note,
                })
                .eq("id", pick["id"])
                .execute()
            )
            resolved.append({
                "id": pick["id"],
                "market": market,
                "match": match_label,
                "result": final_result,
                "note": note,
            })

        except Exception as e:
            errors.append({"pick_id": pick.get("id"), "error": str(e)})

    return {
        "ok": True,
        "date": date,
        "resolved_count": len(resolved),
        "resolved": resolved,
        "errors": errors,
    }


@app.get("/api/predictions")
def get_predictions(
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
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
    api_fixture_ids = [f["api_fixture_id"] for f in fixtures if f.get("api_fixture_id")]
    if not fixture_ids:
        return {"date": date, "matches": []}

    # Get predictions for those fixtures
    predictions = (
        supabase.table("predictions").select("*").in_("fixture_id", fixture_ids).execute().data
        or []
    )

    # Get odds for those fixtures
    odds_data = []
    if api_fixture_ids:
        # Avoid Supabase URL length limits by fetching in chunks or just taking top N. 
        # Usually day schedule < 100
        odds_data = (
            supabase.table("fixture_odds").select("*").in_("fixture_api_id", api_fixture_ids).execute().data
            or []
        )
    odds_by_api_id = {str(o["fixture_api_id"]): o for o in odds_data}

    # Get league names (with simple TTL cache)
    league_map = _get_league_map()

    # Get team logos (only for teams present in the fixtures)
    team_names_set = set()
    for f in fixtures:
        if f.get("home_team"):
            team_names_set.add(f["home_team"])
        if f.get("away_team"):
            team_names_set.add(f["away_team"])

    logo_map = {}
    if team_names_set:
        teams_data = (
            supabase.table("teams")
            .select("name, logo_url")
            .in_("name", list(team_names_set))
            .execute()
            .data
            or []
        )
        logo_map = {t["name"]: t.get("logo_url") for t in teams_data if t.get("logo_url")}

    pred_by_fixture = {p["fixture_id"]: p for p in predictions}

    matches = []
    for f in fixtures:
        pred = pred_by_fixture.get(f["id"])
        league_id = f.get("league_id")

        # Parse stats_json safely
        stats = _ensure_dict(pred.get("stats_json") if pred else None)

        # Helper to get value from top-level OR stats_json
        def get_val(key, default=None):
            if not pred:
                return default
            val = pred.get(key)
            if val is not None:
                return val
            return stats.get(key, default)

        matches.append(
            {
                "id": f["id"],
                "home_team": f.get("home_team", "?"),
                "away_team": f.get("away_team", "?"),
                "home_logo": logo_map.get(f.get("home_team", "")),
                "away_logo": logo_map.get(f.get("away_team", "")),
                "date": f.get("date"),
                "status": f.get("status"),
                "home_goals": f.get("home_goals"),
                "away_goals": f.get("away_goals"),
                "events_json": f.get("events_json") or [],
                "elapsed": f.get("elapsed"),
                "live_stats_json": f.get("live_stats_json") or {},
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
                }
                if pred
                else None,
                "odds": odds_by_api_id.get(str(f.get("api_fixture_id"))),
                "value_edges": _get_ev_edges(
                    {
                        "proba_home": get_val("proba_home"),
                        "proba_draw": get_val("proba_draw"),
                        "proba_away": get_val("proba_away"),
                        "proba_btts": get_val("proba_btts"),
                        "proba_over_2_5": get_val("proba_over_2_5") or get_val("proba_over_25"),
                    },
                    odds_by_api_id.get(str(f.get("api_fixture_id"))) or {}
                ) if pred else {}
            }
        )

    return {"date": date, "matches": matches}


@app.get("/api/predictions/{fixture_id}")
def get_prediction_detail(fixture_id: str):
    """Get detailed prediction for a specific fixture."""
    try:
        data = supabase.table("fixtures").select("*").eq("id", fixture_id).limit(1).execute().data
        fixture = data[0] if data else None
    except Exception:
        # Handle invalid UUID format or DB error
        raise HTTPException(status_code=404, detail="Fixture not found")

    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")

    prediction_data = (
        supabase.table("predictions").select("*").eq("fixture_id", fixture_id).execute().data
    )
    prediction = prediction_data[0] if prediction_data else None

    # Parse stats_json if present
    if prediction:
        sj = _ensure_dict(prediction.get("stats_json"))
        prediction["stats_json"] = sj

        # Promote missing fields from stats_json to top-level
        _proba_fields = [
            "proba_over_05",
            "proba_over_15",
            "proba_over_25",
            "proba_over_2_5",
            "proba_over_35",
            "proba_btts",
            "proba_penalty",
            "confidence_score",
            "recommended_bet",
            "correct_score",
            "analysis_text",
            "xg_home",
            "xg_away",
        ]
        for field in _proba_fields:
            if prediction.get(field) is None and sj.get(field) is not None:
                prediction[field] = sj[field]
        # Normalise over_2_5 vs over_25
        if prediction.get("proba_over_25") is None:
            prediction["proba_over_25"] = (
                prediction.get("proba_over_2_5")
                or sj.get("proba_over_2_5")
                or sj.get("proba_over_25")
            )

        # Enrich top_scorers with photos if available
        scorers = prediction.get("top_scorers") or sj.get("top_scorers")
        if scorers and isinstance(scorers, list):
            p_names = [s.get("name") for s in scorers if s.get("name")]
            if p_names:
                try:
                    p_photos = (
                        supabase.table("players")
                        .select("name, photo_url")
                        .in_("name", p_names)
                        .execute()
                        .data
                    )
                    photo_map = {p["name"]: p["photo_url"] for p in p_photos}
                    for s in scorers:
                        if s.get("name") in photo_map:
                            s["photo"] = photo_map[s["name"]]
                    # Update prediction object with enriched scorers
                    prediction["top_scorers"] = scorers
                except Exception:
                    pass

    # Fetch Top Scorers Logic
    home_scorers = []
    away_scorers = []

    if fixture:
        from src.config import SEASON

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
                results.append(
                    {
                        "name": p_info.get("name", "Unknown"),
                        "photo": p_info.get("photo_url"),
                        "goals": s["goals"],
                        "apps": s["appearances"],
                    }
                )
            return results

        try:
            home_scorers = fetch_top_3(home_id)
            away_scorers = fetch_top_3(away_id)
        except Exception:
            pass  # Fail silently if DB error or missing table

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

    # Add team logos to fixture
    if fixture:
        for side, team_col in [("home_logo", "home_team"), ("away_logo", "away_team")]:
            name = fixture.get(team_col)
            if name:
                try:
                    team_row = (
                        supabase.table("teams")
                        .select("logo_url")
                        .eq("name", name)
                        .limit(1)
                        .execute()
                        .data
                    )
                    fixture[side] = team_row[0]["logo_url"] if team_row else None
                except Exception:
                    fixture[side] = None

    # Fetch odds
    odds = None
    if fixture and fixture.get("api_fixture_id"):
        try:
            odds_res = supabase.table("fixture_odds").select("*").eq("fixture_api_id", fixture["api_fixture_id"]).limit(1).execute().data
            if odds_res:
                odds = odds_res[0]
        except Exception:
            pass

    # Calculate Value Edge
    value_edges = _get_ev_edges(prediction, odds or {}) if prediction else {}

    return {
        "fixture": fixture,
        "prediction": prediction,
        "home_scorers": home_scorers,
        "away_scorers": away_scorers,
        "match_stats": match_stats,
        "odds": odds,
        "value_edges": value_edges,
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
            supabase.table("predictions").select("*").in_("fixture_id", fixture_ids).execute().data
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
        brier_sum = 0
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

            # 1X2 accuracy & Brier Score
            ph = get_val("proba_home", 33)
            pd_val = get_val("proba_draw", 33)
            pa = get_val("proba_away", 33)
            
            # Normalize to 0-1
            p_h = ph / 100.0
            p_d = pd_val / 100.0
            p_a = pa / 100.0

            # Actual outcome array [H, D, A]
            o_h = 1 if actual_result == "H" else 0
            o_d = 1 if actual_result == "D" else 0
            o_a = 1 if actual_result == "A" else 0

            # Brier score for this match: sum of squared differences
            brier_match = (p_h - o_h)**2 + (p_d - o_d)**2 + (p_a - o_a)**2
            brier_sum += brier_match

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
            "brier_score_1x2": round(brier_sum / total_with_pred, 3) if total_with_pred else 0,
            "daily_stats": sorted(daily.values(), key=lambda x: x["date"]),
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Team History ──────────────────────────────────────────────


@app.get("/api/team/{team_name}/history")
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


@app.get("/api/team/{team_name}/roster")
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
        except Exception as e:
            print(f"Error fetching roster stats: {e}")
            pass

        return {"team_name": team_name, "roster": roster_data}
    except Exception as e:
        logger.error(f"Error fetching roster for {team_name}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching roster")


# ─── Admin Auth Helper ──────────────────────────────────────────


def _require_admin(authorization: str | None) -> dict:
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
        supabase.table("profiles").select("role").eq("id", str(user_id)).single().execute().data
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

    if mode == "nhl":
        cmd = [
            sys.executable,
            "-c",
            "from src.fetchers.nhl_pipeline import run_nhl_pipeline; run_nhl_pipeline()",
        ]
    else:
        cmd = [sys.executable, "run_pipeline.py"]
        if mode != "full":
            cmd.append(mode)

    with _pipeline_lock:
        _pipeline_state["process"] = None

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

        # Store the process inside lock to allow killing it
        with _pipeline_lock:
            _pipeline_state["process"] = process

        # Read output in real-time
        for line in process.stdout:
            with _pipeline_lock:
                # Append new line and keep last 10k chars
                current_logs = _pipeline_state["logs"] + line
                _pipeline_state["logs"] = current_logs[-10000:]

        process.wait()

        with _pipeline_lock:
            if _pipeline_state["status"] == "cancelled":
                _pipeline_state["logs"] += "\n[Action] Arrêté par l'administrateur."
            else:
                _pipeline_state["status"] = "done" if process.returncode == 0 else "error"
            _pipeline_state["return_code"] = process.returncode
            _pipeline_state["finished_at"] = datetime.now().isoformat()
            _pipeline_state["process"] = None

    except Exception as e:
        with _pipeline_lock:
            _pipeline_state["status"] = "error"
            _pipeline_state["logs"] += f"\nInternal Error: {str(e)}"
            _pipeline_state["finished_at"] = datetime.now().isoformat()
            _pipeline_state["process"] = None


@app.post("/api/cron/run-pipeline")
def cron_run_pipeline(body: dict, authorization: str = Header(None)):
    """
    Trigger the pipeline via Trigger.dev scheduled tasks.
    Authenticated via CRON_SECRET (not Supabase JWT).
    Body: { "mode": "nhl" | "full" | "analyze" | "data" | "results" }
    """
    expected = f"Bearer {os.getenv('CRON_SECRET', 'super_secret_probalab_2026')}"
    if authorization != expected:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")

    mode = body.get("mode", "full")
    if mode not in ("full", "data", "analyze", "results", "nhl"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid mode")

    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            return {"message": "Pipeline already running — skipping", "status": "skipped"}

        _pipeline_state["status"] = "running"
        _pipeline_state["mode"] = mode
        _pipeline_state["started_at"] = datetime.now().isoformat()
        _pipeline_state["finished_at"] = None
        _pipeline_state["logs"] = ""
        _pipeline_state["return_code"] = None

    thread = threading.Thread(target=_run_pipeline_background, args=(mode,), daemon=True)
    thread.start()

    return {
        "ok": True,
        "message": f"Pipeline '{mode}' started via cron",
        "started_at": _pipeline_state["started_at"],
    }


@app.post("/api/admin/run-pipeline")
def admin_run_pipeline(
    mode: str = Query("full", description="Pipeline mode: full, data, analyze, results, or nhl"),
    authorization: str | None = Header(None),
):
    """Trigger the pipeline (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    if mode not in ("full", "data", "analyze", "results", "nhl"):
        raise HTTPException(
            status_code=400, detail="Mode must be: full, data, analyze, results, or nhl"
        )

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


@app.post("/api/admin/stop-pipeline")
def admin_stop_pipeline(authorization: str | None = Header(None)):
    """Stop the running pipeline (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    with _pipeline_lock:
        if _pipeline_state["status"] != "running":
            raise HTTPException(status_code=400, detail="No pipeline is currently running")

        process = _pipeline_state.get("process")
        if process:
            try:
                process.terminate()  # Try graceful SIGTERM
                _pipeline_state["status"] = "cancelled"
                return {"message": "Démarrage de l'arrêt du pipeline en cours..."}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to stop process: {e}")

        # Fallback if status is running but no process found
        _pipeline_state["status"] = "cancelled"
        _pipeline_state["finished_at"] = datetime.now().isoformat()

    return {"message": "Pipeline annulé"}


@app.get("/api/admin/pipeline-status")
def admin_pipeline_status(authorization: str | None = Header(None)):
    """Get current pipeline status (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    with _pipeline_lock:
        state = dict(_pipeline_state)
        # Remove non-serializable fields
        state.pop("process", None)
        return state


@app.post("/api/admin/update-scores")
def admin_update_scores(
    date: str | None = Query(None, description="Date YYYY-MM-DD (default: today)"),
    authorization: str | None = Header(None),
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
            import os
            import sys

            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from src.fetchers.results import fetch_and_update_results

            fetch_and_update_results(date)
        except Exception as e:
            print(f"[update-scores] Error: {e}")

    t = _threading.Thread(target=_run_scores, daemon=True)
    t.start()

    from datetime import date as _date

    target = date or _date.today().isoformat()
    return {"message": f"Score update started for {target}"}
