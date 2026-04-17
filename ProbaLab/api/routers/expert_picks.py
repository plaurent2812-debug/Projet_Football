"""
api/routers/expert_picks.py — Expert picks endpoints.

Handles reading, deleting, backfilling, and resolving expert picks
submitted via the Telegram bot.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from typing import Annotated

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request

from api.auth import verify_cron_auth, verify_internal_auth
from api.response_models import ExpertPicksResponse, LatestExpertPickResponse, ResolveExpertPicksResponse
from api.schemas import ResolveExpertPicksRequest
from src.config import supabase
from src.nhl.constants import NHL_FINISHED_STATUSES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/expert-picks", tags=["Expert Picks"])


@router.get(
    "",
    summary="List expert picks for a date",
    response_model=ExpertPicksResponse,
    responses={
        500: {"description": "Internal server error"},
    },
)
def get_expert_picks(
    date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    sport: str | None = Query(None, description="'nhl' | 'football' | None = all"),
):
    """Return expert picks (submitted via Telegram bot) for a given date."""
    import json as _json

    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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

        picks = resp.data or []

        # Enrich each pick with structured data for frontend display
        for pick in picks:
            # Parse selections from expert_note (combinés store JSON here)
            selections = []
            expert_note = pick.get("expert_note", "") or ""
            try:
                parsed_note = _json.loads(expert_note)
                if isinstance(parsed_note, list):
                    selections = parsed_note
            except (ValueError, TypeError):
                pass

            # If no selections from expert_note, build from market/match_label
            if not selections:
                bet_text = pick.get("market", "")
                match_text = pick.get("match_label", "")
                if bet_text or match_text:
                    selections = [{"bet": bet_text, "match": match_text}]

            # Enrich each selection with structured fields
            enriched_selections = []
            for sel in selections:
                bet_raw = sel.get("bet", "")
                match_raw = sel.get("match", "")

                # Detect player name (last capitalized word before "Over" or entire bet)
                player_name = None
                if "Over" in bet_raw:
                    player_name = bet_raw.split(" Over")[0].strip()
                elif "Buteur" in bet_raw:
                    player_name = bet_raw.split(" Buteur")[0].strip()

                # Detect market type
                market_type = bet_raw
                if player_name:
                    market_type = bet_raw.replace(player_name, "").strip()
                    if market_type.startswith("Over 0.5 Points"):
                        market_type = "Points du joueur : 1 ou plus"
                    elif market_type.startswith("Over 0.5 Assists"):
                        market_type = "Passes décisives du joueur : 1 ou plus"
                    elif market_type.startswith("Over 0.5 Goals") or "Buteur" in market_type:
                        market_type = "Buts du joueur : 1 ou plus"

                # Detect if MyMatch (2+ bets from same match)
                is_mymatch = sel.get("is_mymatch", False)

                enriched_selections.append({
                    "match": match_raw,
                    "market": market_type,
                    "player_name": player_name,
                    "bet_raw": bet_raw,
                    "is_mymatch": is_mymatch,
                })

            pick["selections"] = enriched_selections
            pick["is_combine"] = len(enriched_selections) > 1

            # Determine bet type (Safe / Fun / Expert)
            odds_val = float(pick.get("odds") or 0)
            market = (pick.get("market") or "").lower()
            if "safe" in market:
                pick["bet_type"] = "SAFE"
            elif "fun" in market:
                pick["bet_type"] = "FUN"
            elif 1.5 <= odds_val <= 2.5:
                pick["bet_type"] = "SAFE"
            elif odds_val >= 10:
                pick["bet_type"] = "FUN"
            else:
                pick["bet_type"] = "EXPERT"

            # Detect MyMatch at pick level (multiple selections from same match)
            match_names = [s["match"] for s in enriched_selections if s.get("match")]
            unique_matches = set(match_names)
            has_mymatch = False
            if len(match_names) > len(unique_matches):
                has_mymatch = True
                # Mark selections that share a match
                for m in unique_matches:
                    same_match = [s for s in enriched_selections if s.get("match") == m]
                    if len(same_match) > 1:
                        for s in same_match:
                            s["is_mymatch"] = True
            pick["has_mymatch"] = has_mymatch

        return {"date": date, "picks": picks}
    except Exception:
        logger.exception("get_expert_picks failed for date=%s", date)
        return {"date": date, "picks": [], "error": "Internal error"}


@router.delete("/{pick_id}")
def delete_expert_pick(pick_id: int, authorization: str = Header(None)):
    """Delete an expert pick by ID — admin only."""
    verify_internal_auth(authorization)
    try:
        supabase.table("expert_picks").delete().eq("id", pick_id).execute()
        return {"deleted": True, "id": pick_id}
    except Exception:
        logger.exception("delete_expert_pick failed for pick_id=%s", pick_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/backfill")
def backfill_expert_picks(body: dict, request: Request, authorization: str = Header(None)):
    """Admin-only: bulk insert expert picks (bypass RLS via server-side supabase client)."""
    verify_cron_auth(authorization)
    picks = body.get("picks", [])
    if not picks:
        raise HTTPException(status_code=400, detail="No picks provided")
    inserted = []
    errors = []
    for i, p in enumerate(picks):
        try:
            resp = supabase.table("expert_picks").insert(p).execute()
            inserted.append({"index": i, "id": resp.data[0]["id"]})
        except Exception as e:
            logger.warning("backfill_expert_picks: insert index=%d failed", i, exc_info=True)
            errors.append({"index": i, "error": str(e)})
    return {"inserted": len(inserted), "errors": errors, "ids": inserted}


@router.get("/latest", summary="Get the most recent expert pick", response_model=LatestExpertPickResponse)
def get_latest_expert_pick():
    """Return the most recent expert pick — used by frontend polling for notifications."""
    try:
        data = (
            supabase.table("expert_picks")
            .select("id, date, sport, market, match_label, odds, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return {"pick": data[0] if data else None}
    except Exception:
        logger.warning("get_latest_expert_pick failed", exc_info=True)
        return {"pick": None, "error": "Internal error"}


@router.post("/resolve", response_model=ResolveExpertPicksResponse)
def resolve_expert_picks(body: Annotated[ResolveExpertPicksRequest, Body()], request: Request, authorization: str = Header(None)):
    """
    Auto-resolve PENDING expert picks by matching to finished fixtures
    and using Gemini to evaluate WIN/LOSS from free-text bet descriptions.
    Called by Trigger.dev cron each morning.
    """
    verify_cron_auth(authorization)

    date = body.date
    sport = body.sport
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

    finished_fixtures = []

    if not sport or sport == "football":
        fx_resp = (
            supabase.table("fixtures")
            .select("id, home_team, away_team, home_goals, away_goals, status")
            .gte("date", f"{date}T00:00:00Z")
            .lt("date", f"{next_day}T23:59:59Z")
            .in_("status", ["FT", "AET", "PEN"])
            .execute()
        )
        for f in (fx_resp.data or []):
            f["_sport"] = "football"
        finished_fixtures.extend(fx_resp.data or [])

    if not sport or sport == "nhl":
        nhl_resp = (
            supabase.table("nhl_fixtures")
            .select("id, home_team, away_team, home_goals, away_goals, status")
            .gte("date", f"{date}T00:00:00Z")
            .lt("date", f"{next_day}T23:59:59Z")
            .in_("status", list(NHL_FINISHED_STATUSES))
            .execute()
        )
        for f in (nhl_resp.data or []):
            f["_sport"] = "nhl"
        finished_fixtures.extend(nhl_resp.data or [])

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
            "_sport": f.get("_sport", "football"),
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
        except Exception:
            logger.warning("[Expert Resolve] Gemini error", exc_info=True)
            return None

    def _fuzzy_match_fixture(match_label: str, fixtures_list: list) -> dict | None:
        """Try to find a fixture that matches the match_label string.

        Priority:
        1. Exact substring match — both team names appear in the label.
        2. difflib.SequenceMatcher — combined score > 0.4 on both team names.
        """
        from difflib import SequenceMatcher

        if not match_label:
            return None
        label_lower = match_label.lower().strip()
        best_match = None
        best_score = 0.0
        for fx in fixtures_list:
            home_l = (fx.get("home") or "").lower()
            away_l = (fx.get("away") or "").lower()
            if not home_l or not away_l:
                continue
            # Priority 1: both full team names appear verbatim in the label
            if home_l in label_lower and away_l in label_lower:
                return fx
            # Priority 1b: first word of each team (length > 3) appears in label
            home_first = home_l.split()[0] if home_l else ""
            away_first = away_l.split()[0] if away_l else ""
            if len(home_first) > 3 and len(away_first) > 3:
                if home_first in label_lower and away_first in label_lower:
                    return fx
            # Priority 2: fuzzy scoring via SequenceMatcher
            score_h = SequenceMatcher(None, home_l, label_lower).ratio()
            score_a = SequenceMatcher(None, away_l, label_lower).ratio()
            combined = (score_h + score_a) / 2
            if combined > best_score and combined > 0.4:
                best_score = combined
                best_match = fx
        return best_match if best_score > 0.4 else None

    # ── 4. Process each pick ──────────────────────────────────────
    import time as _time

    for pick in picks:
        try:
            match_label = pick.get("match_label", "")
            market = pick.get("market", "")
            expert_note = pick.get("expert_note", "")
            pick_sport = pick.get("sport", "football")
            fx_for_pick = [f for f in fx_list_for_search if f["_sport"] == pick_sport]

            # Parse selections for combinés
            selections = []
            try:
                if expert_note and expert_note.startswith("["):
                    selections = _json.loads(expert_note)
            except Exception:
                pass

            is_combine = len(selections) > 1

            if is_combine:
                # ── Combiné: VOID legs ignored; LOSS on any non-VOID; WIN if all non-VOID WIN ──
                is_loss = False
                has_unknown = False
                all_void = True
                non_void_all_win = True
                details = []
                for sel in selections:
                    sel_bet = sel.get("bet", "")
                    sel_match = sel.get("match", "")
                    fx = _fuzzy_match_fixture(sel_match, fx_for_pick)
                    if not fx:
                        has_unknown = True
                        all_void = False
                        details.append(f"⏳ {sel_match}: match non trouvé")
                        continue

                    result = _evaluate_bet(
                        sel_bet, sel_match,
                        fx["home_goals"], fx["away_goals"],
                        fx["home"], fx["away"]
                    )
                    _time.sleep(0.5)  # Rate limit

                    if result == "VOID":
                        details.append(f"🔄 {sel_bet} ({fx['home']} {fx['home_goals']}-{fx['away_goals']} {fx['away']}): VOID")
                    elif result == "WIN":
                        all_void = False
                        details.append(f"✅ {sel_bet} ({fx['home']} {fx['home_goals']}-{fx['away_goals']} {fx['away']})")
                    elif result == "LOSS":
                        is_loss = True
                        all_void = False
                        non_void_all_win = False
                        details.append(f"❌ {sel_bet} ({fx['home']} {fx['home_goals']}-{fx['away_goals']} {fx['away']})")
                    else:
                        has_unknown = True
                        all_void = False
                        details.append(f"❓ {sel_bet}: évaluation impossible")

                if is_loss:
                    final_result = "LOSS"
                elif has_unknown:
                    errors.append({"pick_id": pick["id"], "error": "Incomplete evaluation", "details": details})
                    continue
                elif all_void:
                    final_result = "VOID"
                else:
                    final_result = "WIN"  # Tous les legs non-VOID sont WIN

                note = " | ".join(details)

            else:
                # ── Pari simple ───────────────────────────────────
                fx = _fuzzy_match_fixture(match_label, fx_for_pick)
                if not fx:
                    # Try with selections[0].match if available
                    if selections and selections[0].get("match"):
                        fx = _fuzzy_match_fixture(selections[0]["match"], fx_for_pick)
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
            logger.warning("resolve_expert_picks: pick_id=%s failed", pick.get("id"), exc_info=True)
            errors.append({"pick_id": pick.get("id"), "error": str(e)})

    return {
        "ok": True,
        "date": date,
        "resolved_count": len(resolved),
        "resolved": resolved,
        "errors": errors,
    }
