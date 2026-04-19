"""GET /api/value-bets — consommé par SS3 UI (homepage + page match)."""

from __future__ import annotations

import logging
from datetime import date as _date
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from src.config import supabase
from src.constants import VALUE_EDGE_USER_FACING
from src.models.value_detector import best_odds_per_selection, detect_value_bets

router = APIRouter(prefix="/api", tags=["Value Bets"])
logger = logging.getLogger("football_ia.api.value_bets")


def _load_day_matches(target: _date) -> list[dict]:
    """Charge predictions + closing_odds + fixture meta pour la journée."""
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    preds = (
        supabase.table("predictions")
        .select("*")
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
        .execute()
        .data
    ) or []
    if not preds:
        return []

    fixture_ids = list({p["fixture_id"] for p in preds if p.get("fixture_id")})
    if not fixture_ids:
        return []

    odds_rows = (
        supabase.table("closing_odds").select("*").in_("fixture_id", fixture_ids).execute().data
    ) or []
    odds_by_fixture: dict[str, list[dict]] = {}
    for r in odds_rows:
        odds_by_fixture.setdefault(r["fixture_id"], []).append(r)

    matches: list[dict] = []
    for p in preds:
        fid = p["fixture_id"]
        market_odds = odds_by_fixture.get(fid, [])

        model_probs_1x2 = _probs_1x2(p)
        model_probs_btts = _probs_btts(p)
        model_probs_over25 = _probs_over25(p)

        probabilities: dict[str, dict] = {}
        if model_probs_1x2:
            probabilities["1x2"] = _to_pct_dict(model_probs_1x2)
        if model_probs_btts:
            probabilities["btts"] = _to_pct_dict(model_probs_btts)
        if model_probs_over25:
            probabilities["over_2_5"] = _to_pct_dict(model_probs_over25)

        best_odds_flat: dict[str, dict] = {}
        for market in ("1x2", "btts", "over_2_5"):
            best = best_odds_per_selection(market_odds, market=market)
            for sel, info in best.items():
                best_odds_flat[f"{market}.{sel}"] = {
                    "bookmaker": info["bookmaker"],
                    "odds": round(info["odds"], 4),
                    "implied": round(info["implied_prob"] * 100, 2),
                }

        value_bets: list[dict] = []
        for market, probs in (
            ("1x2", model_probs_1x2),
            ("btts", model_probs_btts),
            ("over_2_5", model_probs_over25),
        ):
            if not probs:
                continue
            vbets = detect_value_bets(
                model_probs=probs,
                odds_rows=market_odds,
                market=market,
                edge_threshold=VALUE_EDGE_USER_FACING,
            )
            for vb in vbets:
                vb["market"] = market
                value_bets.append(vb)

        matches.append(
            {
                "fixture_id": fid,
                "sport": p.get("sport", "football"),
                "league": p.get("league_name", ""),
                "home_team": p.get("home_team", ""),
                "away_team": p.get("away_team", ""),
                "kickoff": p.get("match_start") or p.get("kickoff"),
                "probabilities": probabilities,
                "best_odds": best_odds_flat,
                "value_bets": value_bets,
            }
        )
    return matches


def _probs_1x2(pred: dict) -> dict[str, float] | None:
    h, d, a = pred.get("proba_home"), pred.get("proba_draw"), pred.get("proba_away")
    if None in (h, d, a):
        return None
    return {"home": float(h) / 100.0, "draw": float(d) / 100.0, "away": float(a) / 100.0}


def _probs_btts(pred: dict) -> dict[str, float] | None:
    y = pred.get("proba_btts")
    if y is None:
        return None
    y_float = float(y) / 100.0 if float(y) > 1.5 else float(y)
    return {"yes": y_float, "no": 1.0 - y_float}


def _probs_over25(pred: dict) -> dict[str, float] | None:
    o = pred.get("proba_over_25")
    if o is None:
        return None
    o_float = float(o) / 100.0 if float(o) > 1.5 else float(o)
    return {"over": o_float, "under": 1.0 - o_float}


def _to_pct_dict(probs: dict[str, float]) -> dict[str, float]:
    return {k: round(v * 100, 2) for k, v in probs.items()}


@router.get("/value-bets")
def get_value_bets(
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    try:
        target = _date.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"bad date: {exc}") from exc
    matches = _load_day_matches(target)
    return {"date": date, "matches": matches}
