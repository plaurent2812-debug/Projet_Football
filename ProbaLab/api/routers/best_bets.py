"""
api/routers/best_bets.py — Best Bets router (Paris du Soir).

Handles football + NHL SAFE/FUN bet generation, result tracking,
resolution, stats, and history.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request

from api.auth import verify_cron_auth, verify_internal_auth
from api.metrics import bets_resolved
from api.rate_limit import _rate_limit
from api.response_models import BestBetsResponse, SaveBetResponse, UpdateBetResultResponse
from api.routers.best_bets_logic import (
    build_market_breakdown,
    calc_stats,
    evaluate_football_combo,
    evaluate_nhl_player_market,
    evaluate_single_football_market,
    extract_nhl_market_from_label,
)
from api.schemas import (
    ResolveBetsRequest,
    ResolveExpertPicksRequest,
    SaveBetRequest,
    UpdateBetResultRequest,
)
from src.config import supabase
from src.nhl.constants import NHL_FINISHED_STATUSES
from src.nhl.constants import NHL_NAME_TO_ABBREV as _NHL_NAME_TO_ABBREV

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Best Bets"])


# ─── Best Bets Endpoints ─────────────────────────────────────────

@router.get(
    "/api/best-bets",
    summary="Get daily best bets (Paris du Soir)",
    response_model=BestBetsResponse,
    responses={
        500: {"description": "Internal server error"},
    },
)
@_rate_limit("30/minute")
def get_best_bets(
    request: Request,
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    sport: str | None = Query(None, description="'football' | 'nhl' | None = both"),
):
    """Return SAFE and FUN bets for football + NHL.

    SAFE: single bet, real odds between 1.9–2.3
    FUN: combined bets, target total odds ~20
    Legacy: football[] and nhl[] arrays preserved for backward compat.
    """
    import math as _math

    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    result = {
        "date": date,
        "football": [],
        "nhl": [],
        "football_safe": None,
        "football_fun": None,
        "nhl_safe": None,
        "nhl_fun": None,
    }

    # ── Football ──────────────────────────────────────────────────
    if sport in (None, "football"):
        try:
            next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

            fx_resp = (
                supabase.table("fixtures")
                .select("id, api_fixture_id, home_team, away_team, date, status")
                .gte("date", f"{date}T00:00:00Z")
                .lt("date", f"{next_day}T00:00:00Z")
                .execute()
            )
            fixtures = fx_resp.data or []
            fx_map = {f["id"]: f for f in fixtures}
            api_to_fix = {f["api_fixture_id"]: f["id"] for f in fixtures}

            if fx_map:
                # Fetch predictions
                pred_resp = (
                    supabase.table("predictions")
                    .select(
                        "fixture_id, proba_home, proba_draw, proba_away, "
                        "proba_btts, proba_over_2_5, proba_over_15, "
                        "recommended_bet, confidence_score, is_value_bet, "
                        "analysis_text, proba_over_35"
                    )
                    .in_("fixture_id", list(fx_map.keys()))
                    .order("confidence_score", desc=True)
                    .execute()
                )
                preds = pred_resp.data or []

                # Fetch real bookmaker odds
                api_fids = [f["api_fixture_id"] for f in fixtures]
                odds_resp = (
                    supabase.table("fixture_odds")
                    .select("*")
                    .in_("fixture_api_id", api_fids)
                    .execute()
                )
                odds_map = {}
                if odds_resp and odds_resp.data:
                    for o in odds_resp.data:
                        fid = api_to_fix.get(o["fixture_api_id"])
                        if fid:
                            odds_map[fid] = o

                # ── Build all football bet candidates ─────────────
                all_candidates = []
                for p in preds:
                    fix = fx_map.get(p["fixture_id"])
                    if not fix:
                        continue
                    real_odds = odds_map.get(p["fixture_id"])
                    match_label = f"{fix['home_team']} vs {fix['away_team']}"

                    # All markets with their real odds and model probas
                    markets = [
                        ("Victoire domicile", real_odds.get("home_win_odds") if real_odds else None, p.get("proba_home") or 0),
                        ("Match nul", real_odds.get("draw_odds") if real_odds else None, p.get("proba_draw") or 0),
                        ("Victoire extérieur", real_odds.get("away_win_odds") if real_odds else None, p.get("proba_away") or 0),
                        ("BTTS Oui", real_odds.get("btts_yes_odds") if real_odds else None, p.get("proba_btts") or 0),
                        ("Over 1.5 buts", real_odds.get("over_15_odds") if real_odds else None, p.get("proba_over_15") or 0),
                        ("Over 2.5 buts", real_odds.get("over_25_odds") if real_odds else None, p.get("proba_over_2_5") or 0),
                        ("Over 3.5 buts", real_odds.get("over_35_odds") if real_odds else None, p.get("proba_over_35") or 0),
                        ("Double Chance 1N", real_odds.get("dc_1x_odds") if real_odds else None, (p.get("proba_home") or 0) + (p.get("proba_draw") or 0)),
                        ("Double Chance X2", real_odds.get("dc_x2_odds") if real_odds else None, (p.get("proba_draw") or 0) + (p.get("proba_away") or 0)),
                    ]

                    for market_name, bookmaker_odds, model_proba in markets:
                        if model_proba < 30:
                            continue
                        # Use real odds if available, else estimate from model probability
                        if bookmaker_odds and bookmaker_odds > 1.0:
                            odds_val = float(bookmaker_odds)
                            odds_source = "real"
                        else:
                            # Only estimate odds for probabilities >= 1% to avoid absurd values
                            odds_val = round((1 / (model_proba / 100)) * 0.95, 2) if model_proba >= 1 else 0
                            odds_source = "estimated"

                        if odds_val < 1.05:
                            continue

                        # EV = prob * odds - 1
                        ev = round((model_proba / 100) * odds_val - 1, 3)
                        # Edge = model_prob - implied_prob (bookmaker)
                        edge_pct = round(((model_proba / 100) - (1.0 / odds_val)) * 100, 1)

                        all_candidates.append({
                            "fixture_id": p["fixture_id"],
                            "label": f"{match_label} — {market_name}",
                            "match": match_label,
                            "market": market_name,
                            "odds": odds_val,
                            "proba_model": model_proba,
                            "proba_bookmaker": round(100 / odds_val, 1) if odds_val > 1.0 else None,
                            "confidence": p.get("confidence_score") or 0,
                            "ev": ev,
                            "edge_pct": edge_pct,
                            "is_value": ev > 0.03,
                            "odds_source": odds_source,
                            "result": "PENDING",
                            "time": fix["date"][11:16] if fix.get("date") else "",
                        })

                # ── Football SAFE: 1 match, 1-2 markets, odds 1.9–2.5 ──
                SAFE_MIN, SAFE_MAX = 1.90, 2.50

                # Group candidates by fixture for combo building
                by_fixture: dict[str, list] = {}
                for c in all_candidates:
                    by_fixture.setdefault(c["fixture_id"], []).append(c)

                safe_options = []

                for fid, cands in by_fixture.items():
                    real_cands = [c for c in cands if c["odds_source"] == "real"]

                    # Option A: Single market in range
                    for c in real_cands:
                        if SAFE_MIN <= c["odds"] <= SAFE_MAX:
                            safe_options.append({
                                "fixture_id": fid,
                                "match": c["match"],
                                "time": c.get("time", ""),
                                "picks": [c["market"]],
                                "label": f"{c['match']} — {c['market']}",
                                "odds": c["odds"],
                                "proba_model": c["proba_model"],
                                "ev": c["ev"],
                                "odds_source": "real",
                                "category": "safe_football",
                                "result": "PENDING",
                            })

                    # Option B: Combine 2 markets on same match
                    # Compatible pairs: (1X2/DC) + (BTTS/Over)
                    outcome_markets = [c for c in real_cands if c["market"] in (
                        "Victoire domicile", "Victoire extérieur", "Match nul",
                        "Double Chance 1N", "Double Chance X2")]
                    goal_markets = [c for c in real_cands if c["market"] in (
                        "BTTS Oui", "Over 1.5 buts", "Over 2.5 buts")]

                    # Positive correlation factor for outcome+goal combos (e.g. "Team wins" + "BTTS")
                    # Teams that win tend to score, creating slight positive correlation vs independence
                    COMBO_CORRELATION_FACTOR = 1.08

                    for om in outcome_markets:
                        for gm in goal_markets:
                            combo_odds = round(om["odds"] * gm["odds"], 2)
                            if SAFE_MIN <= combo_odds <= SAFE_MAX:
                                # Combined proba ≈ P(A) × P(B) × correlation factor
                                combo_proba = round(
                                    (om["proba_model"] / 100) * (gm["proba_model"] / 100) * COMBO_CORRELATION_FACTOR * 100, 1
                                )
                                combo_ev = round((combo_proba / 100) * combo_odds - 1, 3)
                                safe_options.append({
                                    "fixture_id": fid,
                                    "match": om["match"],
                                    "time": om.get("time", ""),
                                    "picks": [om["market"], gm["market"]],
                                    "label": f"{om['match']} — {om['market']} + {gm['market']}",
                                    "odds": combo_odds,
                                    "proba_model": combo_proba,
                                    "ev": combo_ev,
                                    "odds_source": "real",
                                    "category": "safe_football",
                                    "result": "PENDING",
                                })

                if safe_options:
                    safe_options.sort(key=lambda x: -x["ev"])
                    best_safe = safe_options[0]
                    result["football_safe"] = {
                        "type": "SAFE",
                        "bet": best_safe,
                        "odds": best_safe["odds"],
                    }

                # ── Football FUN: combined ~20, max success rate ───
                fun_candidates = [
                    c for c in all_candidates
                    if c["odds"] >= 1.50 and c["proba_model"] >= 40
                ]
                # Dedupe by fixture (1 pick per match)
                seen_fx = set()
                fun_deduped = []
                fun_candidates.sort(key=lambda x: -x["ev"])
                for c in fun_candidates:
                    if c["fixture_id"] not in seen_fx:
                        fun_deduped.append(c)
                        seen_fx.add(c["fixture_id"])

                if len(fun_deduped) >= 3:
                    # Greedy: highest-proba picks first, target 20x, accept 12x+
                    # if adding more picks would drop combined proba below 2%
                    fun_deduped.sort(key=lambda x: -x["proba_model"])

                    selected = []
                    current_odds = 1.0
                    for c in fun_deduped:
                        new_odds = current_odds * c["odds"]
                        if new_odds > 40 and len(selected) >= 3:
                            break
                        if len(selected) >= 3 and current_odds >= 12:
                            combined_p = 1.0
                            for s in selected:
                                combined_p *= s["proba_model"] / 100
                            if combined_p * (c["proba_model"] / 100) < 0.02:
                                break
                        selected.append(c)
                        current_odds = new_odds
                        if current_odds >= 20 and len(selected) >= 3:
                            break
                        if len(selected) >= 5:
                            break

                    if len(selected) >= 3:
                        total_odds = 1.0
                        for s in selected:
                            total_odds *= s["odds"]
                        result["football_fun"] = {
                            "type": "FUN",
                            "bets": selected,
                            "total_odds": round(total_odds, 2),
                            "count": len(selected),
                        }

                # Value-first: uniquement des paris qui battent le marché
                value_candidates = [
                    c for c in all_candidates
                    if c["ev"] > 0 and c["odds_source"] == "real"
                ]
                value_candidates.sort(key=lambda x: -x["ev"])
                seen = set()
                top_value = []
                for b in value_candidates:
                    if b["fixture_id"] not in seen:
                        top_value.append(b)
                        seen.add(b["fixture_id"])
                    if len(top_value) >= 10:
                        break
                result["football"] = top_value

        except Exception:
            logger.exception("Error building football best bets for date=%s", date)
            result["football_error"] = "Internal error"

    # ── NHL ───────────────────────────────────────────────────────
    if sport in (None, "nhl"):
        try:
            next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

            # Step 1: Real bookmaker odds
            real_odds_resp = (
                supabase.table("nhl_odds")
                .select("player_name, bookmaker, over_odds, home_team, away_team, game_id, line, market")
                .eq("game_date", date)
                .gte("over_odds", 1.30)
                .order("over_odds", desc=True)
                .limit(300)
                .execute()
            )
            real_odds_raw = real_odds_resp.data or []

            # Build player→best odds map
            player_odds_map: dict[str, dict] = {}
            for row in real_odds_raw:
                name = (row.get("player_name") or "").strip()
                if not name:
                    continue
                odds_val = float(row.get("over_odds") or 0)
                if odds_val <= 1.0:
                    continue
                market = row.get("market", "player_points")
                key = f"{name}_{market}"
                existing = player_odds_map.get(key)
                if existing is None or odds_val > existing["odds"]:
                    player_odds_map[key] = {
                        "odds": odds_val,
                        "player_name": name,
                        "bookmaker": row.get("bookmaker", ""),
                        "home_team": row.get("home_team", ""),
                        "away_team": row.get("away_team", ""),
                        "game_id": row.get("game_id", ""),
                        "market": market,
                        "line": float(row.get("line") or 0.5),
                    }

            # Step 2: Model probabilities
            fixtures_resp = (
                supabase.table("nhl_fixtures")
                .select("home_team, away_team, stats_json")
                .gte("date", f"{date}T00:00:00Z")
                .lt("date", f"{next_day}T00:00:00Z")
                .execute()
            )

            model_map: dict[str, dict] = {}
            for fx in (fixtures_resp.data or []):
                for p in ((fx.get("stats_json") or {}).get("top_players") or []):
                    name = (p.get("player_name") or "").strip()
                    if not name or name in model_map:
                        continue
                    model_map[name] = {
                        "ppg": float(p.get("points_per_game") or 0),
                        "prob_goal": float(p.get("prob_goal") or 0),
                        "prob_assist": float(p.get("prob_assist") or 0),
                        "team": p.get("team", ""),
                        "opp": p.get("opp", ""),
                        "is_home": p.get("is_home", 0),
                        "home_team": fx.get("home_team", ""),
                        "away_team": fx.get("away_team", ""),
                    }

            # Step 3: Fuzzy matching
            import unicodedata

            def norm(s: str) -> str:
                s = unicodedata.normalize("NFD", s.lower())
                s = "".join(c for c in s if unicodedata.category(c) != "Mn")
                return s.replace("-", " ").replace("'", "").strip()

            norm_model = {norm(k): v for k, v in model_map.items()}

            def find_model(player_name):
                n = norm(player_name)
                m = norm_model.get(n)
                if m:
                    return m
                parts = n.split()
                if len(parts) >= 2:
                    last = parts[-1]
                    for k, v in norm_model.items():
                        if last in k:
                            return v
                return None

            # ── NHL SAFE: 1-2 players, real odds 1.9–2.5 ─────────
            NHL_SAFE_MIN, NHL_SAFE_MAX = 1.90, 2.50

            # Build individual player point bets with positive EV
            point_bets = []
            for key, od in player_odds_map.items():
                if od["market"] != "player_points":
                    continue
                md = find_model(od["player_name"])
                if not md or md.get("ppg", 0) <= 0:
                    continue

                ppg = md["ppg"]
                prob = round((1.0 - _math.exp(-ppg)) * 100, 1)
                ev = round((prob / 100) * od["odds"] - 1, 3)
                if ev <= 0:
                    continue

                ht = md.get("home_team") or od.get("home_team", "")
                at = md.get("away_team") or od.get("away_team", "")

                point_bets.append({
                    "player_name": od["player_name"],
                    "team": md.get("team", ""),
                    "label": f"{od['player_name']} Over 0.5 Points — {ht} vs {at}",
                    "market": "player_points_over_0.5",
                    "odds": round(od["odds"], 2),
                    "proba_model": prob,
                    "ev": ev,
                    "bookmaker": od.get("bookmaker", ""),
                    "odds_source": "real",
                    "game_label": f"{ht} vs {at}",
                })

            nhl_safe_options = []

            # Option A: Single player in range
            for b in point_bets:
                if NHL_SAFE_MIN <= b["odds"] <= NHL_SAFE_MAX:
                    nhl_safe_options.append({
                        "bets": [b],
                        "label": b["label"],
                        "odds": b["odds"],
                        "ev": b["ev"],
                        "category": "safe_nhl",
                    })

            # Option B: Combine 2 players (different games preferred)
            for i in range(len(point_bets)):
                for j in range(i + 1, len(point_bets)):
                    b1, b2 = point_bets[i], point_bets[j]
                    combo_odds = round(b1["odds"] * b2["odds"], 2)
                    if NHL_SAFE_MIN <= combo_odds <= NHL_SAFE_MAX:
                        combo_ev = round(
                            (b1["proba_model"] / 100) * (b2["proba_model"] / 100) * combo_odds - 1, 3
                        )
                        nhl_safe_options.append({
                            "bets": [b1, b2],
                            "label": f"{b1['player_name']} + {b2['player_name']} Over 0.5 Points",
                            "odds": combo_odds,
                            "ev": combo_ev,
                            "category": "safe_nhl",
                        })

            if nhl_safe_options:
                nhl_safe_options.sort(key=lambda x: -x["ev"])
                best_nhl_safe = nhl_safe_options[0]
                result["nhl_safe"] = {
                    "type": "SAFE",
                    "bet": best_nhl_safe,
                    "odds": best_nhl_safe["odds"],
                }

            # ── NHL FUN: goals + assists combined ~20 ─────────────
            nhl_fun_candidates = []
            for name, md in model_map.items():
                prob_goal = md.get("prob_goal", 0)
                prob_assist = md.get("prob_assist", 0)
                ht = md.get("home_team", "")
                at = md.get("away_team", "")

                # Goal prop
                if prob_goal > 5:
                    odds_goal = round((1 / (prob_goal / 100)) * 0.92, 2)
                    if odds_goal >= 2.0:
                        nhl_fun_candidates.append({
                            "label": f"{name} Marquer un but — {ht} vs {at}",
                            "player_name": name,
                            "team": md.get("team", ""),
                            "market": "player_goals_over_0.5",
                            "odds": odds_goal,
                            "proba_model": round(prob_goal, 1),
                            "ev": round((prob_goal / 100) * odds_goal - 1, 3),
                            "odds_source": "estimated",
                            "result": "PENDING",
                        })

                # Assist prop
                if prob_assist > 8:
                    odds_assist = round((1 / (prob_assist / 100)) * 0.92, 2)
                    if odds_assist >= 2.0:
                        nhl_fun_candidates.append({
                            "label": f"{name} Faire une passe — {ht} vs {at}",
                            "player_name": name,
                            "team": md.get("team", ""),
                            "market": "player_assists_over_0.5",
                            "odds": odds_assist,
                            "proba_model": round(prob_assist, 1),
                            "ev": round((prob_assist / 100) * odds_assist - 1, 3),
                            "odds_source": "estimated",
                            "result": "PENDING",
                        })

            if len(nhl_fun_candidates) >= 3:
                # Sort by proba (highest success rate)
                nhl_fun_candidates.sort(key=lambda x: -x["proba_model"])

                # Greedy selection to reach ~20 odds
                TARGET = 20.0
                selected = []
                current = 1.0
                seen_players = set()
                for c in nhl_fun_candidates:
                    if c["player_name"] in seen_players:
                        continue
                    new_odds = current * c["odds"]
                    if new_odds > TARGET * 1.5 and len(selected) >= 3:
                        break
                    selected.append(c)
                    current = new_odds
                    seen_players.add(c["player_name"])
                    if current >= TARGET * 0.7 and len(selected) >= 3:
                        break
                    if len(selected) >= 5:
                        break

                if len(selected) >= 3:
                    total = 1.0
                    for s in selected:
                        total *= s["odds"]
                    result["nhl_fun"] = {
                        "type": "FUN",
                        "bets": selected,
                        "total_odds": round(total, 2),
                        "count": len(selected),
                    }

            # Legacy top 5
            nhl_legacy = []
            for key, od in player_odds_map.items():
                if od["market"] != "player_points":
                    continue
                md = find_model(od["player_name"])
                if not md or md.get("ppg", 0) <= 0:
                    continue
                ppg = md["ppg"]
                prob = round((1.0 - _math.exp(-ppg)) * 100, 1)
                ev = round((prob / 100) * od["odds"] - 1, 3)
                if ev <= 0:
                    continue
                ht = md.get("home_team") or od.get("home_team", "")
                at = md.get("away_team") or od.get("away_team", "")
                nhl_legacy.append({
                    "id": None,
                    "player_name": od["player_name"],
                    "team": md.get("team", ""),
                    "label": f"{od['player_name']} Over 0.5 Points — {ht} vs {at}",
                    "market": "player_points_over_0.5",
                    "odds": round(od["odds"], 2),
                    "proba_model": prob,
                    "proba_bookmaker": round(100 / od["odds"], 1) if od["odds"] > 1.0 else None,
                    "ev": ev,
                    "edge_pct": round(((prob / 100) - (1.0 / od["odds"])) * 100, 1),
                    "bookmaker": od.get("bookmaker", ""),
                    "is_value": ev > 0.03,
                    "odds_source": "real",
                    "result": "PENDING",
                })
            nhl_legacy.sort(key=lambda x: -x["ev"])
            result["nhl"] = nhl_legacy[:10]
            result["nhl_odds_source"] = "real" if player_odds_map else "pending"

        except Exception:
            logger.exception("Error building NHL best bets for date=%s", date)
            result["nhl_error"] = "Internal error"

    # ── Auto-save SAFE/FUN bets to best_bets for tracking ─────────
    try:
        saved = (
            supabase.table("best_bets")
            .select("*")
            .eq("date", date)
            .execute()
        )
        saved_labels = {s["bet_label"]: s for s in (saved.data or [])}

        def _auto_save(label, sport_name, category, odds, proba, fid=None, pname=None):
            """Save bet if not already tracked."""
            if label in saved_labels:
                return saved_labels[label]
            try:
                row = {
                    "date": date,
                    "sport": sport_name,
                    "bet_label": label,
                    "market": category,
                    "odds": odds,
                    "proba_model": proba,
                    "confidence": 7,
                    "result": "PENDING",
                }
                if fid:
                    row["fixture_id"] = fid
                if pname:
                    row["player_name"] = pname
                resp = supabase.table("best_bets").insert(row).execute()
                if resp.data:
                    saved_labels[label] = resp.data[0]
                    return resp.data[0]
            except Exception:
                logger.warning("Auto-save bet failed for label=%s", label, exc_info=True)
            return None

        # Auto-save football SAFE
        if result.get("football_safe"):
            bet = result["football_safe"]["bet"]
            s = _auto_save(
                bet["label"], "football", "safe_football",
                bet["odds"], bet.get("proba_model", 0),
                fid=bet.get("fixture_id")
            )
            if s:
                bet["id"] = s.get("id")
                bet["result"] = s.get("result", "PENDING")

        # Auto-save football FUN
        if result.get("football_fun"):
            for bet in result["football_fun"]["bets"]:
                s = _auto_save(
                    bet["label"], "football", "fun_football",
                    bet["odds"], bet.get("proba_model", 0),
                    fid=bet.get("fixture_id")
                )
                if s:
                    bet["id"] = s.get("id")
                    bet["result"] = s.get("result", "PENDING")

        # Auto-save NHL SAFE
        if result.get("nhl_safe"):
            nhl_safe_data = result["nhl_safe"]["bet"]
            for bet in nhl_safe_data.get("bets", []):
                s = _auto_save(
                    bet["label"], "nhl", "safe_nhl",
                    bet["odds"], bet.get("proba_model", 0),
                    pname=bet.get("player_name")
                )
                if s:
                    bet["id"] = s.get("id")
                    bet["result"] = s.get("result", "PENDING")

        # Auto-save NHL FUN
        if result.get("nhl_fun"):
            for bet in result["nhl_fun"]["bets"]:
                s = _auto_save(
                    bet["label"], "nhl", "fun_nhl",
                    bet["odds"], bet.get("proba_model", 0),
                    pname=bet.get("player_name")
                )
                if s:
                    bet["id"] = s.get("id")
                    bet["result"] = s.get("result", "PENDING")

        # Enrich legacy arrays
        for bet in result.get("football", []):
            if bet.get("label") in saved_labels:
                s = saved_labels[bet["label"]]
                bet["id"] = s["id"]
                bet["result"] = s.get("result", "PENDING")

        for bet in result.get("nhl", []):
            if bet.get("label") in saved_labels:
                s = saved_labels[bet["label"]]
                bet["id"] = s["id"]
                bet["result"] = s.get("result", "PENDING")

    except Exception:
        logger.warning("Auto-save SAFE/FUN bets failed", exc_info=True)

    return result


@router.patch("/api/best-bets/{bet_id}/result", response_model=UpdateBetResultResponse)
def update_bet_result(
    bet_id: int,
    body: Annotated[UpdateBetResultRequest, Body()],
    authorization: str = Header(None),
):
    """Update the result of a tracked bet (admin only)."""
    verify_internal_auth(authorization)
    result_val = body.result.upper()
    if result_val not in ("WIN", "LOSS", "VOID", "PENDING"):
        raise HTTPException(status_code=400, detail="result must be WIN, LOSS, VOID or PENDING")

    try:
        resp = (
            supabase.table("best_bets")
            .update({
                "result": result_val,
                "notes": body.notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", bet_id)
            .execute()
        )
        return {"ok": True, "updated": resp.data}
    except Exception:
        logger.exception("update_bet_result failed for bet_id=%s", bet_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/best-bets/save", response_model=SaveBetResponse)
def save_best_bets(body: Annotated[SaveBetRequest, Body()], authorization: str = Header(None)):
    """Save a best bet to the tracking table (admin only)."""
    verify_internal_auth(authorization)
    try:
        bet_data = {
            "date": body.date,
            "sport": body.sport,
            "bet_label": body.label,
            "market": body.market,
            "odds": body.odds,
            "confidence": body.confidence,
            "proba_model": body.proba_model,
            "fixture_id": body.fixture_id,
            "player_name": body.player_name,
            "result": "PENDING",
        }
        resp = supabase.table("best_bets").insert(bet_data).execute()
        return {"ok": True, "id": resp.data[0]["id"] if resp.data else None}
    except Exception:
        logger.exception("save_best_bets failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/nhl/fetch-game-stats")
@_rate_limit("10/minute")
def nhl_fetch_game_stats(body: dict, request: Request, authorization: str = Header(None)):
    """
    Called by Trigger.dev before resolve: fetches actual player stats
    from the NHL API boxscore and stores them in nhl_player_game_stats.
    """
    verify_cron_auth(authorization)

    date = body.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="date required (YYYY-MM-DD)")

    try:
        from src.nhl.fetch_game_stats import fetch_and_store_game_stats
        result = fetch_and_store_game_stats(date)
        return result
    except Exception:
        logger.exception("fetch_and_store_game_stats failed for date=%s", date)
        return {"ok": False, "error": "Internal error"}


@router.post("/api/nhl/fetch-odds")
@_rate_limit("10/minute")
def nhl_fetch_odds(body: dict, request: Request, authorization: str = Header(None)):
    """
    Fetches real NHL player prop odds from The Odds API and stores in nhl_odds.
    Called by the NHL pipeline (schedule-nhl-pipeline or admin trigger).
    Requires ODDS_API_KEY env var to be set.
    """
    verify_cron_auth(authorization)

    date = body.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        from src.nhl.fetch_odds import run as fetch_nhl_odds
        result = fetch_nhl_odds(date)
        return result
    except Exception:
        logger.exception("fetch_nhl_odds failed for date=%s", date)
        return {"ok": False, "error": "Internal error"}


@router.post("/api/best-bets/backfill")
def backfill_pending_bets(authorization: str = Header(None)):
    """
    Re-tente la résolution sur les 30 derniers jours pour les paris restés PENDING.
    """
    verify_cron_auth(authorization)

    results = []
    # Test over the last 30 days
    for i in range(1, 31):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")

        counts = {"best_bets": 0, "expert_picks": 0}

        # Check best_bets
        bb_req = supabase.table("best_bets").select("id", count="exact").eq("date", d).eq("result", "PENDING").execute()
        if bb_req.count and bb_req.count > 0:
            req_football = ResolveBetsRequest(date=d, sport="football")
            req_nhl = ResolveBetsRequest(date=d, sport="nhl")
            try:
                res_f = resolve_best_bets(req_football, None, authorization)
                res_n = resolve_best_bets(req_nhl, None, authorization)
                counts["best_bets"] += res_f.get("resolved", 0) + res_n.get("resolved", 0)
            except Exception:
                logger.warning("backfill resolve_best_bets failed for date=%s", d, exc_info=True)

        # Check expert_picks — import locally to avoid circular dependency
        ep_req = supabase.table("expert_picks").select("id", count="exact").eq("date", d).eq("result", "PENDING").execute()
        if ep_req.count and ep_req.count > 0:
            req = ResolveExpertPicksRequest(date=d)
            try:
                from api.routers.expert_picks import resolve_expert_picks
                res = resolve_expert_picks(req, None, authorization)
                counts["expert_picks"] += res.get("resolved_count", 0)
            except Exception:
                logger.warning("backfill resolve_expert_picks failed for date=%s", d, exc_info=True)

        if counts["best_bets"] > 0 or counts["expert_picks"] > 0:
            results.append({"date": d, "resolved": counts})

    return {"status": "success", "backfilled_dates": results}


@router.post("/api/best-bets/resolve")
@_rate_limit("10/minute")
def resolve_best_bets(body: Annotated[ResolveBetsRequest, Body()], request: Request, authorization: str = Header(None)):
    """
    Called by Trigger.dev scheduled tasks to auto-resolve PENDING bets.
    Checks match results and updates best_bets table with WIN/LOSS/VOID.
    """
    verify_cron_auth(authorization)

    date = body.date
    sport = body.sport

    if not date or sport not in ("football", "nhl"):
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
                label = bet["bet_label"]   # e.g. "PSG vs Lyon — Victoire domicile"
                market = bet["market"]
                fixture_id = bet.get("fixture_id")

                # If market is a category (safe_football, fun_football, etc.),
                # extract the actual market from the bet_label after "—" or " — "
                actual_market = market
                if market in ("safe_football", "fun_football", "safe_nhl", "fun_nhl"):
                    if " — " in label:
                        actual_market = label.split(" — ", 1)[1].strip()
                    elif "—" in label:
                        actual_market = label.split("—", 1)[1].strip()

                # Try to find the fixture
                fx = None
                fid = None
                try:
                    if fixture_id:
                        fid = int(fixture_id)
                except ValueError:
                    pass

                if fid and fid in finished:
                    fx = finished[fid]
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

                # Handle combo markets (e.g. "Victoire domicile + BTTS Oui")
                if " + " in actual_market:
                    result_val = evaluate_football_combo(actual_market, h, a)
                    if result_val is None:
                        continue  # Pending (unknown leg) or unexpected state
                else:
                    result_val = evaluate_single_football_market(actual_market, h, a)
                    if result_val is None:
                        continue  # Unknown market

                # Update best_bets
                (
                    supabase.table("best_bets")
                    .update({
                        "result": result_val,
                        "notes": f"Auto-résolu: {h}-{a} ({fx['status']})",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
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
                bets_resolved.labels(result=result_val.lower()).inc()

            except Exception as e:
                logger.warning("resolve_best_bets football: bet_id=%s failed", bet.get("id"), exc_info=True)
                errors.append({"bet_id": bet.get("id"), "error": str(e)})

    # ── NHL resolution ────────────────────────────────────────────
    elif sport == "nhl":
        next_day = (datetime.fromisoformat(date) + timedelta(days=1)).strftime("%Y-%m-%d")

        NHL_NAME_TO_ABBREV = _NHL_NAME_TO_ABBREV

        # Fetch finished NHL fixtures for that game date
        nhl_resp = (
            supabase.table("nhl_fixtures")
            .select("id, home_team, away_team, home_score, away_score, status")
            .gte("date", f"{date}T00:00:00Z")
            .lt("date", f"{next_day}T23:59:59Z")
            .in_("status", list(NHL_FINISHED_STATUSES))
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
                    # Fallback: search by last name
                    last_name = player_name.split()[-1] if player_name else ""
                    if last_name and len(last_name) > 2:
                        stats_resp = (
                            supabase.table("nhl_player_game_stats")
                            .select("player_name, team, goals, assists, points, shots, game_id")
                            .ilike("player_name", f"%{last_name}%")
                            .eq("game_date", date)
                            .limit(1)
                            .execute()
                        )

                if not stats_resp.data:
                    # Stats not yet loaded — check if the game is finished at all
                    player_team = bet.get("team", "")
                    fx = fx_by_team.get(player_team) if player_team else None
                    if fx and fx.get("home_score") is not None:
                        errors.append({
                            "bet_id": bet.get("id"),
                            "error": f"Stats missing for {player_name} on {date} — will retry",
                        })
                    continue

                p_stats = stats_resp.data[0]
                actual_points = int(p_stats.get("points") or 0)
                actual_goals = int(p_stats.get("goals") or 0)
                actual_assists = int(p_stats.get("assists") or 0)
                actual_shots = int(p_stats.get("shots") or 0)
                game_id = p_stats.get("game_id")

                # If market is a category, extract actual market from label
                market = bet.get("market", "player_points_over_0.5")
                if market in ("safe_nhl", "fun_nhl"):
                    market = extract_nhl_market_from_label(label)

                result_val = evaluate_nhl_player_market(
                    market,
                    points=actual_points,
                    goals=actual_goals,
                    assists=actual_assists,
                    shots=actual_shots,
                )

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
                        "updated_at": datetime.now(timezone.utc).isoformat(),
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
                bets_resolved.labels(result=result_val.lower()).inc()

            except Exception as e:
                logger.warning("resolve_best_bets nhl: bet_id=%s failed", bet.get("id"), exc_info=True)
                errors.append({"bet_id": bet.get("id"), "error": str(e)})

    return {
        "ok": True,
        "date": date,
        "sport": sport,
        "resolved_count": len(resolved),
        "resolved": resolved,
        "errors": errors,
    }


@router.get("/api/best-bets/stats")
@_rate_limit("30/minute")
def get_best_bets_stats(request: Request):
    """Return win rate and ROI stats for both model predictions (best_bets) and expert picks."""
    try:
        cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        # ── 1. Expert picks stats (Paris de l'Expert) ─────────────
        expert_resp = (
            supabase.table("expert_picks")
            .select("sport, result, date, odds, market, match_label")
            .neq("result", "PENDING")
            .gte("date", cutoff_30d)
            .order("date", desc=True)
            .execute()
        )
        expert_rows = expert_resp.data or []

        expert_football = [b for b in expert_rows if b["sport"] == "football"]
        expert_nhl = [b for b in expert_rows if b["sport"] == "nhl"]

        # Expert market breakdown (normalized)
        expert_market_breakdown = build_market_breakdown(expert_rows)

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
            .select("sport, result, date, odds, market, bet_label")
            .neq("result", "PENDING")
            .gte("date", cutoff_30d)
            .order("date", desc=True)
            .execute()
        )
        model_rows = model_resp.data or []

        model_football = [b for b in model_rows if b["sport"] == "football"]
        model_nhl = [b for b in model_rows if b["sport"] == "nhl"]

        # Model market breakdown (normalized)
        model_market_breakdown = build_market_breakdown(model_rows)
        # ── 3. Combined stats (expert + model merged) ────────────
        all_rows = expert_rows + model_rows
        all_football = [b for b in all_rows if b["sport"] == "football"]
        all_nhl = [b for b in all_rows if b["sport"] == "nhl"]

        # Combined market breakdown — split by sport
        combined_market_football = build_market_breakdown(all_football)
        combined_market_nhl = build_market_breakdown(all_nhl)

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
        combined_last_10 = [
            {
                "result": b["result"],
                "label": b.get("bet_label") or b.get("match_label") or b.get("market", ""),
                "odds": float(b.get("odds") or 0),
            }
            for b in all_resolved[:10]
        ]

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

        # Max winning streak
        max_streak = 0
        current_streak = 0
        for b in all_resolved:
            if b["result"] == "WIN":
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return {
            # Combined stats (all sources)
            "global": calc_stats(all_rows),
            "football": calc_stats(all_football),
            "nhl": calc_stats(all_nhl),
            "by_market_football": combined_market_football,
            "by_market_nhl": combined_market_nhl,
            "timeline": [{"date": k, **v} for k, v in sorted(combined_timeline.items())][-30:],
            "last_10": combined_last_10,
            "best_pick": combined_best_pick,
            "max_streak": max_streak,
            "cumulative_pl": combined_cumulative[-60:],
            # Model predictions only (ProbaLab IA accuracy)
            "model_global": calc_stats(model_rows),
            "model_football": calc_stats(model_football),
            "model_nhl": calc_stats(model_nhl),
            "model_by_market": model_market_breakdown,
            # Expert predictions only
            "expert_global": calc_stats(expert_rows),
            "expert_football": calc_stats(expert_football),
            "expert_nhl": calc_stats(expert_nhl),
            "expert_by_market": expert_market_breakdown,
        }
    except Exception:
        logger.exception("get_best_bets_stats failed")
        return {"error": "Internal error"}


@router.get("/api/best-bets/history")
def get_best_bets_history(
    days: int = Query(30, description="Number of days to look back"),
    sport: str | None = Query(None, description="'football' | 'nhl' | None = both"),
    source: str | None = Query(None, description="'expert' | 'model' | 'all'"),
    date_from: str | None = Query(None, description="Start date YYYY-MM-DD (overrides days)"),
    date_to: str | None = Query(None, description="End date YYYY-MM-DD"),
):
    """Return all resolved picks from both best_bets and expert_picks for the history table."""
    try:
        if date_from:
            cutoff = date_from
        else:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        # ── 1. Fetch from best_bets (model predictions) ──────────
        bb_query = (
            supabase.table("best_bets")
            .select("id, date, sport, bet_label, market, odds, confidence, result, player_name")
            .gte("date", cutoff)
            .order("date", desc=True)
        )
        if date_to:
            bb_query = bb_query.lte("date", date_to)
        if sport:
            bb_query = bb_query.eq("sport", sport)
        bb_rows = bb_query.execute().data or []

        # Tag source
        for r in bb_rows:
            r["source"] = "model"

        # Group FUN bets
        grouped_bb = []
        fun_groups = {}
        for b in bb_rows:
            if b.get("market") in ("fun_football", "fun_nhl"):
                k = (b["date"], b["market"])
                if k not in fun_groups:
                    fun_groups[k] = []
                fun_groups[k].append(b)
            else:
                grouped_bb.append(b)

        for (d, m), legs in fun_groups.items():
            # VOID legs are ignored in combo resolution — only WIN/LOSS/unknown matter
            non_void_legs = [l for l in legs if l.get("result") != "VOID"]
            has_loss = any(l.get("result") == "LOSS" for l in non_void_legs)
            all_non_void_win = bool(non_void_legs) and all(l.get("result") == "WIN" for l in non_void_legs)
            is_void = len(non_void_legs) == 0  # All legs VOID

            res = "PENDING"
            if has_loss: res = "LOSS"
            elif is_void: res = "VOID"
            elif all_non_void_win: res = "WIN"

            tot_odds = 1.0
            labels = []
            for l in legs:
                o = l.get("odds")
                if o: tot_odds *= float(o)
                lb = l.get("bet_label") or l.get("player_name") or ""
                if lb: labels.append(lb)

            if tot_odds == 1.0: tot_odds = 20.0

            combo = legs[0].copy()
            combo["result"] = res
            combo["odds"] = tot_odds
            combo["bet_label"] = " + ".join(labels)
            grouped_bb.append(combo)

        bb_rows = grouped_bb

        # ── 2. Fetch from expert_picks (Telegram expert bets) ────
        ep_query = (
            supabase.table("expert_picks")
            .select("id, date, sport, market, match_label, odds, confidence, result, player_name, expert_note, notes")
            .gte("date", cutoff)
            .order("date", desc=True)
        )
        if date_to:
            ep_query = ep_query.lte("date", date_to)
        if sport:
            ep_query = ep_query.eq("sport", sport)
        ep_rows = ep_query.execute().data or []

        # Map field names for frontend compatibility
        for r in ep_rows:
            r["bet_label"] = r.get("match_label") or r.get("market") or "Pick Expert"
            r["source"] = "expert"

        # ── 3. Merge and sort by date descending ─────────────────
        if source == "expert":
            all_rows = ep_rows
        elif source == "model":
            all_rows = bb_rows
        else:
            all_rows = bb_rows + ep_rows

        all_rows.sort(key=lambda r: r.get("date", ""), reverse=True)

        # Calculate full stats matching frontend expectations
        resolved = [r for r in all_rows if r["result"] in ("WIN", "LOSS")]
        wins = sum(1 for r in resolved if r["result"] == "WIN")
        losses = sum(1 for r in resolved if r["result"] == "LOSS")
        total_pl = 0
        odds_estimated = 0
        for r in resolved:
            odds_val = r.get("odds")
            if not odds_val:
                odds_val = 1.85
                odds_estimated += 1
            else:
                odds_val = float(odds_val)

            if r["result"] == "WIN":
                total_pl += (odds_val - 1)
            else:
                total_pl -= 1

        return {
            "picks": all_rows[:300],
            "stats": {
                "total": len(all_rows),
                "resolved": len(resolved),
                "wins": wins,
                "losses": losses,
                "total_pl": round(total_pl, 2),
                "win_rate": round(wins / len(resolved) * 100) if len(resolved) > 0 else 0,
                "odds_estimated": odds_estimated,
            }
        }
    except Exception:
        logger.exception("get_best_bets_history failed")
        return {"error": "Internal error"}
