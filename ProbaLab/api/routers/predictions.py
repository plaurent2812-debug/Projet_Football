"""
api/routers/predictions.py — Football predictions endpoints.

Serves prediction lists for a given date and detailed prediction
views for a single fixture.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from api.helpers import _ensure_dict, _get_ev_edges, _get_league_map
from api.rate_limit import _rate_limit
from api.response_models import PredictionDetailResponse, PredictionsListResponse
from src.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get(
    "",
    summary="List predictions for a date",
    response_model=PredictionsListResponse,
    responses={
        500: {"description": "Internal server error"},
    },
)
@_rate_limit("30/minute")
def get_predictions(
    request: Request,
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
):
    """Get predictions for a given date (defaults to today)."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        supabase.table("predictions").select("*").in_("fixture_id", fixture_ids).order("created_at").execute().data
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

    pred_by_fixture = {str(p["fixture_id"]): p for p in predictions}

    matches = []
    for f in fixtures:
        pred = pred_by_fixture.get(str(f["id"]))
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

        # Compute value edges (model prob vs bookmaker odds)
        _market_labels = {
            "home": "Victoire Domicile", "draw": "Match Nul", "away": "Victoire Extérieur",
            "over_25": "Plus de 2.5 buts", "under_25": "Moins de 2.5 buts",
            "btts_yes": "BTTS Oui", "btts_no": "BTTS Non",
        }
        _odds_row = odds_by_api_id.get(str(f.get("api_fixture_id"))) or {}
        _edges = _get_ev_edges(
            {
                "proba_home": get_val("proba_home"),
                "proba_draw": get_val("proba_draw"),
                "proba_away": get_val("proba_away"),
                "proba_btts": get_val("proba_btts"),
                "proba_over_2_5": get_val("proba_over_2_5") or get_val("proba_over_25"),
            },
            _odds_row,
        ) if pred else {}
        # Best value: highest edge with its odds
        # Exclude low-quality predictions from value bets:
        # - Fallback 40-30-30 (stats engine failed)
        # - Low confidence (< 5) → model is uncertain
        _conf = get_val("confidence_score", 0) or 0
        _is_fallback = (
            pred and get_val("proba_home") == 40
            and get_val("proba_draw") == 30
            and get_val("proba_away") == 30
            and _conf <= 3
        ) or _conf < 5
        _best_value = None
        if _edges and not _is_fallback:
            _best_key = max(_edges, key=_edges.get)
            _odds_keys = {
                "home": "home_win_odds", "draw": "draw_odds", "away": "away_win_odds",
                "over_25": "over_25_odds", "under_25": "under_25_odds",
                "btts_yes": "btts_yes_odds", "btts_no": "btts_no_odds",
            }
            _best_odds = _odds_row.get(_odds_keys.get(_best_key, ""), None)
            if _edges[_best_key] >= 5.0:  # MIN_VALUE_EDGE = 5%
                _best_value = {
                    "market": _market_labels.get(_best_key, _best_key),
                    "edge": _edges[_best_key],
                    "odds": _best_odds,
                }

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
                    "proba_over_2_5": get_val("proba_over_2_5"),
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
                "value_edges": _edges,
                "best_value": _best_value,
                "is_value_bet": bool(_best_value),
            }
        )

    return {"date": date, "matches": matches}


@router.get(
    "/{fixture_id}",
    summary="Get prediction detail for a fixture",
    response_model=PredictionDetailResponse,
    responses={
        404: {"description": "Fixture not found"},
        500: {"description": "Internal server error"},
    },
)
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
        supabase.table("predictions")
        .select("*")
        .eq("fixture_id", fixture_id)
        .order("created_at")
        .limit(1)
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
        # Normalise over_2_5 vs over_25 (stats_engine stores proba_over_25 without underscore)
        if prediction.get("proba_over_2_5") is None:
            prediction["proba_over_2_5"] = (
                sj.get("proba_over_2_5")
                or prediction.get("proba_over_25")
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
            logger.debug("fetch_top_3 failed for fixture", exc_info=True)

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
