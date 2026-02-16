"""
ProbaLab API — FastAPI backend for football predictions.

Serves prediction data from Supabase to the React frontend.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

# Add the parent package to the path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import supabase

from api.routers import stripe_webhook

app = FastAPI(title="ProbaLab API", version="1.0.0")

app.include_router(stripe_webhook.router)

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
                "proba_home": pred.get("proba_home") if pred else None,
                "proba_draw": pred.get("proba_draw") if pred else None,
                "proba_away": pred.get("proba_away") if pred else None,
                "proba_btts": pred.get("proba_btts") if pred else None,
                "proba_over_25": pred.get("proba_over_25") if pred else (pred.get("proba_over_2_5") if pred else None),
                "recommended_bet": pred.get("recommended_bet") if pred else None,
                "confidence_score": pred.get("confidence_score") if pred else None,
                "kelly_edge": pred.get("kelly_edge") if pred else None,
                "value_bet": pred.get("value_bet") if pred else None,
                "model_version": pred.get("model_version") if pred else None,
                "correct_score": pred.get("correct_score") if pred else None,
                "analysis_text": pred.get("analysis_text") if pred else None,
                "proba_penalty": pred.get("proba_penalty") if pred else None,
                "proba_over_05": pred.get("proba_over_05") if pred else None,
                "proba_over_15": pred.get("proba_over_15") if pred else None,
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
    mode: str = Query("full", description="Pipeline mode: full, data, or analyze"),
    authorization: Optional[str] = Header(None),
):
    """Trigger the pipeline (admin only, requires Supabase JWT)."""
    _require_admin(authorization)

    if mode not in ("full", "data", "analyze"):
        raise HTTPException(status_code=400, detail="Mode must be: full, data, or analyze")

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
