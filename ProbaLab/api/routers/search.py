"""
api/routers/search.py — Semantic search endpoint using Gemini Embedding 2.

Searches predictions and learnings by natural language query.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from src.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Search"])


def _get_league_map() -> dict:
    """Fetch league id→name mapping from Supabase (thin wrapper for search router).

    The canonical cache lives in main.py; this is a lightweight fallback used
    only within this router to avoid a circular import.  The TTL-based version
    in main.py is the authoritative one for all other endpoints.
    """
    try:
        leagues = supabase.table("leagues").select("api_id, name").execute().data or []
        return {str(league["api_id"]): league["name"] for league in leagues}
    except Exception:
        logger.warning("search router: failed to fetch league map", exc_info=True)
        return {}


@router.get("/semantic")
def semantic_search(
    request: Request,
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    sport: str = Query("all", description="'football' | 'nhl' | 'all'"),
):
    """Search predictions and learnings using Gemini Embedding 2 semantic similarity.

    Examples:
        /api/search/semantic?q=derby match with high stakes
        /api/search/semantic?q=upset away win with low xG
        /api/search/semantic?q=defensive match few goals
    """
    try:
        from src.embeddings import search_learnings, search_predictions
    except ImportError:
        raise HTTPException(status_code=500, detail="Embedding module not available")

    results: dict = {"query": q, "predictions": [], "learnings": []}

    # Search predictions
    if sport in ("all", "football"):
        try:
            pred_results = search_predictions(q, limit=limit)
            if pred_results:
                # Enrich with fixture info
                fixture_ids = [r["fixture_id"] for r in pred_results if r.get("fixture_id")]
                fixtures_map: dict = {}
                if fixture_ids:
                    try:
                        fx_resp = (
                            supabase.table("fixtures")
                            .select("id, home_team, away_team, date, league_id, status")
                            .in_("id", fixture_ids)
                            .execute()
                        )
                        fixtures_map = {f["id"]: f for f in (fx_resp.data or [])}
                    except Exception:
                        pass

                league_map = _get_league_map()

                for r in pred_results:
                    fix = fixtures_map.get(r.get("fixture_id"), {})
                    league_name = league_map.get(str(fix.get("league_id", "")), "")
                    results["predictions"].append(
                        {
                            "fixture_id": r.get("fixture_id"),
                            "home_team": fix.get("home_team", "?"),
                            "away_team": fix.get("away_team", "?"),
                            "date": fix.get("date"),
                            "league": league_name,
                            "analysis_text": (r.get("analysis_text") or "")[:300],
                            "proba_home": r.get("proba_home"),
                            "proba_draw": r.get("proba_draw"),
                            "proba_away": r.get("proba_away"),
                            "similarity": round(r.get("similarity", 0), 4),
                        }
                    )
        except Exception:
            logger.warning("Semantic search predictions failed", exc_info=True)
            results["predictions_error"] = "Search unavailable"

    # Search learnings
    if sport in ("all", "football"):
        try:
            learning_results = search_learnings(q, sport="football", limit=min(limit, 5))
            results["learnings"] = [
                {
                    "learning_text": r.get("learning_text"),
                    "tags": r.get("context_tags"),
                    "similarity": round(r.get("similarity", 0), 4),
                }
                for r in learning_results
            ]
        except Exception:
            logger.warning("Semantic search learnings failed", exc_info=True)
            results["learnings_error"] = "Search unavailable"

    return results
