"""
api/routers/performance.py — Model performance metrics endpoint.

Computes accuracy, Brier score, and benchmark comparisons across all
finished fixtures with predictions.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BeforeValidator

from fastapi import APIRouter, HTTPException, Query

from src.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Performance"])

# Simple 60s TTL cache for _compute_performance_summary — hot path on
# V2 landing, avoids 15+ Supabase round-trips per visitor.
_SUMMARY_CACHE: dict[int, tuple[float, dict[str, float]]] = {}
_SUMMARY_CACHE_TTL = 60.0  # seconds

_BANKROLL_SEED_EUR = 1000.0  # Public signal only — real bankroll lives in /api/user/bankroll.


@router.get(
    "/performance",
    summary="Get model performance metrics",
    responses={
        500: {"description": "Internal server error"},
    },
)
def get_performance(days: int = Query(0, description="Rolling window in days (0 = all-time)")):
    """Get model performance metrics over the last N days (0 = all-time)."""
    try:
        cutoff = None
        if days > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        # Only count leagues where predictions are generated
        from src.constants import LEAGUES_TO_FETCH

        # Paginated fetch — Supabase caps at 1000 rows per request
        finished = []
        page_size = 1000
        offset = 0
        while True:
            q = (
                supabase.table("fixtures")
                .select(
                    "id, api_fixture_id, home_team, away_team, home_goals, away_goals, date, status"
                )
                .in_("status", ["FT", "AET", "PEN"])
                .in_("league_id", LEAGUES_TO_FETCH)
            )
            if cutoff:
                q = q.gte("date", cutoff)
            q = q.order("date").range(offset, offset + page_size - 1)
            batch = q.execute().data or []
            finished.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        fixture_ids = [f["id"] for f in finished]
        # Build api_fixture_id lookup for odds queries (fixture_odds uses integer API IDs)
        api_id_by_fixture: dict[str, int] = {}
        for f in finished:
            if f.get("api_fixture_id"):
                api_id_by_fixture[str(f["id"])] = f["api_fixture_id"]
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

        # Fetch predictions in chunks (Supabase URL limit on in_())
        # Order by created_at to ensure deterministic deduplication
        predictions = []
        CHUNK = 100
        for i in range(0, len(fixture_ids), CHUNK):
            chunk = fixture_ids[i : i + CHUNK]
            page = (
                supabase.table("predictions")
                .select("*")
                .in_("fixture_id", chunk)
                .order("created_at")
                .execute()
                .data
                or []
            )
            predictions.extend(page)

        # Fetch bookmaker odds for benchmark computation
        # fixture_odds uses integer api_fixture_id, not UUID fixture id
        api_ids = list(api_id_by_fixture.values())
        bookmaker_odds_by_api_id: dict[int, dict] = {}
        for i in range(0, len(api_ids), CHUNK):
            chunk = api_ids[i : i + CHUNK]
            odds_page = (
                supabase.table("fixture_odds")
                .select("fixture_api_id, home_win_odds, draw_odds, away_win_odds")
                .in_("fixture_api_id", chunk)
                .execute()
                .data
                or []
            )
            for o in odds_page:
                aid = o["fixture_api_id"]
                if aid not in bookmaker_odds_by_api_id:
                    bookmaker_odds_by_api_id[aid] = o

        # Deduplicate: keep FIRST prediction per fixture (oldest = original prediction)
        pred_by_fixture: dict[str, dict] = {}
        for p in predictions:
            fid = str(p["fixture_id"])
            if fid not in pred_by_fixture:
                pred_by_fixture[fid] = p

        correct_1x2 = 0
        correct_btts = 0
        total_btts = 0
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
        total_1x2_countable = 0  # predictions with valid 1X2 probas (no ties)
        skipped_null_probas = 0
        skipped_ties = 0
        total_conf = 0
        # Benchmark counters
        bench_home_total = 0
        bench_home_correct = 0
        bench_bm_total = 0
        bench_bm_correct = 0
        value_bets_count = 0
        brier_sum = 0
        daily: dict[str, dict] = {}

        for f in finished:
            pred = pred_by_fixture.get(str(f["id"]))
            if not pred:
                continue

            # Helper to get field from top-level or stats_json
            stats_json = pred.get("stats_json") or {}

            def get_val(key, default=None, pred=pred, stats_json=stats_json):
                val = pred.get(key)
                if val is not None:
                    return val
                return stats_json.get(key, default)

            hg = f.get("home_goals", 0) or 0
            ag = f.get("away_goals", 0) or 0
            total_goals = hg + ag
            actual_result = "H" if hg > ag else ("D" if hg == ag else "A")
            actual_btts = hg > 0 and ag > 0

            # 1X2 accuracy & Brier Score — skip predictions with NULL probas
            ph = get_val("proba_home")
            pd_val = get_val("proba_draw")
            pa = get_val("proba_away")

            if ph is None or pd_val is None or pa is None:
                skipped_null_probas += 1
                # Still count benchmark "Always Home" for all finished matches with a prediction slot
                bench_home_total += 1
                if actual_result == "H":
                    bench_home_correct += 1
                # Bookmaker benchmark — check if odds available
                bm_odds = bookmaker_odds_by_api_id.get(f.get("api_fixture_id"))
                if (
                    bm_odds
                    and bm_odds.get("home_win_odds")
                    and bm_odds.get("draw_odds")
                    and bm_odds.get("away_win_odds")
                ):
                    h_o = float(bm_odds["home_win_odds"])
                    d_o = float(bm_odds["draw_odds"])
                    a_o = float(bm_odds["away_win_odds"])
                    # Lowest odds = highest implied probability = bookmaker's prediction
                    if h_o < d_o and h_o < a_o:
                        bm_pred = "H"
                    elif a_o < h_o and a_o < d_o:
                        bm_pred = "A"
                    elif d_o < h_o and d_o < a_o:
                        bm_pred = "D"
                    else:
                        bm_pred = None
                    if bm_pred is not None:
                        bench_bm_total += 1
                        if bm_pred == actual_result:
                            bench_bm_correct += 1
                continue

            total_with_pred += 1
            total_conf += pred.get("confidence_score", 5)

            # Normalize to 0-1
            p_h = ph / 100.0
            p_d = pd_val / 100.0
            p_a = pa / 100.0

            # Actual outcome array [H, D, A]
            o_h = 1 if actual_result == "H" else 0
            o_d = 1 if actual_result == "D" else 0
            o_a = 1 if actual_result == "A" else 0

            # Brier score for this match: sum of squared differences
            brier_match = (p_h - o_h) ** 2 + (p_d - o_d) ** 2 + (p_a - o_a) ** 2
            brier_sum += brier_match

            # 1X2 prediction: use strict > to avoid Home bias on ties
            if ph > pd_val and ph > pa:
                predicted_result = "H"
            elif pa > ph and pa > pd_val:
                predicted_result = "A"
            elif pd_val > ph and pd_val > pa:
                predicted_result = "D"
            else:
                # Tie between two or more outcomes — don't count in accuracy
                skipped_ties += 1
                predicted_result = None

            if predicted_result is not None:
                total_1x2_countable += 1
                if predicted_result == actual_result:
                    correct_1x2 += 1

            # Benchmark "Always Home" — for every match with valid probas
            bench_home_total += 1
            if actual_result == "H":
                bench_home_correct += 1

            # Benchmark "Bookmaker implied" — only for matches with bookmaker odds
            bm_odds = bookmaker_odds_by_api_id.get(f.get("api_fixture_id"))
            if (
                bm_odds
                and bm_odds.get("home_win_odds")
                and bm_odds.get("draw_odds")
                and bm_odds.get("away_win_odds")
            ):
                h_o = float(bm_odds["home_win_odds"])
                d_o = float(bm_odds["draw_odds"])
                a_o = float(bm_odds["away_win_odds"])
                if h_o < d_o and h_o < a_o:
                    bm_pred = "H"
                elif a_o < h_o and a_o < d_o:
                    bm_pred = "A"
                elif d_o < h_o and d_o < a_o:
                    bm_pred = "D"
                else:
                    bm_pred = None
                if bm_pred is not None:
                    bench_bm_total += 1
                    if bm_pred == actual_result:
                        bench_bm_correct += 1

            # BTTS accuracy (only count matches with actual BTTS data)
            p_btts = get_val("proba_btts")
            if p_btts is not None:
                total_btts += 1
                if (p_btts > 50) == actual_btts:
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
            p_o25 = get_val("proba_over_2_5")
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

            # Daily aggregation (only count matches with a clear predicted result)
            day = f["date"][:10] if f.get("date") else "unknown"
            if day not in daily:
                daily[day] = {"date": day, "total": 0, "correct": 0}
            if predicted_result is not None:
                daily[day]["total"] += 1
                if predicted_result == actual_result:
                    daily[day]["correct"] += 1

        def _pct(correct: int, total: int) -> float:
            return round(correct / total * 100, 1) if total else 0

        return {
            "days": days,
            "total_matches": total_with_pred,
            # 1X2 accuracy: based on matches with a clear predicted result (no ties)
            "accuracy_1x2": _pct(correct_1x2, total_1x2_countable),
            "accuracy_btts": _pct(correct_btts, total_btts),
            "accuracy_over_05": _pct(correct_over_05, total_over_05),
            "accuracy_over_15": _pct(correct_over_15, total_over_15),
            "accuracy_over_25": _pct(correct_over_25, total_over_25),
            "accuracy_over_35": _pct(correct_over_35, total_over_35),
            "accuracy_score": _pct(correct_score, total_score),
            "avg_confidence": round(total_conf / total_with_pred, 1) if total_with_pred else 0,
            "value_bets": value_bets_count,
            # Brier score for 1X2 (3 outcomes): range [0, 2], normalized to [0, 1] where 0=perfect, 0.5=random
            "brier_score_1x2": round(brier_sum / total_with_pred, 3) if total_with_pred else 0,
            "brier_score_1x2_normalized": round(brier_sum / total_with_pred / 2, 3)
            if total_with_pred
            else 0,
            "daily_stats": sorted(daily.values(), key=lambda x: x["date"]),
            # Coverage info
            "total_finished": len(finished),
            "total_without_prediction": len(finished) - total_with_pred,
            "skipped_null_probas": skipped_null_probas,
            "skipped_ties": skipped_ties,
            # Market coverage: how many predictions have data for each market
            "coverage": {
                "total_1x2_countable": total_1x2_countable,
                "total_btts": total_btts,
                "total_over_05": total_over_05,
                "total_over_15": total_over_15,
                "total_over_25": total_over_25,
                "total_over_35": total_over_35,
                "total_score": total_score,
            },
            # Benchmarks for 1X2 comparison
            "benchmarks": {
                "always_home": {
                    "accuracy": _pct(bench_home_correct, bench_home_total),
                    "total": bench_home_total,
                },
                "bookmaker_implied": {
                    "accuracy": _pct(bench_bm_correct, bench_bm_total),
                    "total": bench_bm_total,
                    "note": "matchs avec cotes bookmaker disponibles uniquement",
                },
                "model": {
                    "accuracy": _pct(correct_1x2, total_1x2_countable),
                    "total": total_1x2_countable,
                },
            },
        }

    except Exception:
        logger.exception("get_performance failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ─── Market ROI (Value Betting Strategy) ─────────────────────


def _compute_market_performance(days: int = 30) -> dict:
    """Compute per-market win rate and simulated ROI from predictions + odds.

    Reusable by both the endpoint and the value bet detection filter.
    """
    from src.constants import LEAGUES_TO_FETCH

    cutoff = None
    if days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # Paginated fetch of finished fixtures
    finished: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        q = (
            supabase.table("fixtures")
            .select("id, api_fixture_id, home_goals, away_goals, date, status")
            .in_("status", ["FT", "AET", "PEN"])
            .in_("league_id", LEAGUES_TO_FETCH)
        )
        if cutoff:
            q = q.gte("date", cutoff)
        q = q.order("date").range(offset, offset + page_size - 1)
        batch = q.execute().data or []
        finished.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    if not finished:
        return {}

    fixture_ids = [f["id"] for f in finished]

    # Fetch predictions in chunks
    CHUNK = 100
    predictions: list[dict] = []
    for i in range(0, len(fixture_ids), CHUNK):
        chunk = fixture_ids[i : i + CHUNK]
        page = (
            supabase.table("predictions")
            .select(
                "fixture_id, proba_home, proba_draw, proba_away, proba_btts, proba_over_2_5, proba_over_25, stats_json"
            )
            .in_("fixture_id", chunk)
            .order("created_at")
            .execute()
            .data
            or []
        )
        predictions.extend(page)

    # Deduplicate: keep first prediction per fixture
    pred_map: dict[str, dict] = {}
    for p in predictions:
        fid = str(p["fixture_id"])
        if fid not in pred_map:
            pred_map[fid] = p

    # Fetch odds
    api_ids = [f["api_fixture_id"] for f in finished if f.get("api_fixture_id")]
    odds_map: dict[int, dict] = {}
    for i in range(0, len(api_ids), CHUNK):
        chunk = api_ids[i : i + CHUNK]
        rows = (
            supabase.table("fixture_odds").select("*").in_("fixture_api_id", chunk).execute().data
            or []
        )
        for r in rows:
            if r["fixture_api_id"] not in odds_map:
                odds_map[r["fixture_api_id"]] = r

    # Track per market-type
    perf: dict[str, dict] = {}

    def _track(key: str, label: str, won: bool, odd: float):
        if key not in perf:
            perf[key] = {"label": label, "wins": 0, "total": 0, "staked": 0.0, "returned": 0.0}
        perf[key]["total"] += 1
        perf[key]["staked"] += 1.0
        if won:
            perf[key]["wins"] += 1
            perf[key]["returned"] += odd

    for f in finished:
        pred = pred_map.get(str(f["id"]))
        if not pred:
            continue
        sj = pred.get("stats_json") or {}

        def _gv(key, default=None, pred=pred, sj=sj):
            v = pred.get(key)
            return v if v is not None else sj.get(key, default)

        hg = f.get("home_goals", 0) or 0
        ag = f.get("away_goals", 0) or 0
        total_goals = hg + ag
        actual = "H" if hg > ag else ("D" if hg == ag else "A")
        actual_btts = hg > 0 and ag > 0
        odds = odds_map.get(f.get("api_fixture_id"), {})

        ph = _gv("proba_home", 0) or 0
        pd_v = _gv("proba_draw", 0) or 0
        pa = _gv("proba_away", 0) or 0

        # 1X2 markets
        if ph > pd_v and ph > pa and ph >= 50 and (odds.get("home_win_odds") or 0) > 1:
            _track("home_win", "Victoire domicile", actual == "H", float(odds["home_win_odds"]))
        if pa > pd_v and pa > ph and pa >= 50 and (odds.get("away_win_odds") or 0) > 1:
            _track("away_win", "Victoire exterieur", actual == "A", float(odds["away_win_odds"]))
        if pd_v > ph and pd_v > pa and pd_v >= 40 and (odds.get("draw_odds") or 0) > 1:
            _track("draw", "Match Nul", actual == "D", float(odds["draw_odds"]))

        # BTTS
        p_btts = _gv("proba_btts", 0) or 0
        if p_btts > 55 and (odds.get("btts_yes_odds") or 0) > 1:
            _track("btts_yes", "BTTS (Oui)", actual_btts, float(odds["btts_yes_odds"]))
        if p_btts < 40 and (odds.get("btts_no_odds") or 0) > 1:
            _track("btts_no", "BTTS (Non)", not actual_btts, float(odds["btts_no_odds"]))

        # Over/Under 2.5
        p_o25 = _gv("proba_over_2_5") or _gv("proba_over_25")
        if p_o25 is not None and p_o25 > 55 and (odds.get("over_25_odds") or 0) > 1:
            _track("over_25", "Over 2.5 buts", total_goals > 2.5, float(odds["over_25_odds"]))
        if p_o25 is not None and p_o25 < 40 and (odds.get("under_25_odds") or 0) > 1:
            _track("under_25", "Under 2.5 buts", total_goals < 2.5, float(odds["under_25_odds"]))

        # Over 1.5 / 3.5
        p_o15 = _gv("proba_over_15")
        if p_o15 is not None and p_o15 > 60 and (odds.get("over_15_odds") or 0) > 1:
            _track("over_15", "Over 1.5 buts", total_goals > 1.5, float(odds["over_15_odds"]))
        p_o35 = _gv("proba_over_35")
        if p_o35 is not None and p_o35 > 55 and (odds.get("over_35_odds") or 0) > 1:
            _track("over_35", "Over 3.5 buts", total_goals > 3.5, float(odds["over_35_odds"]))

        # Double Chance
        dc_1x = ph + pd_v
        if dc_1x >= 65 and (odds.get("dc_1x_odds") or 0) > 1:
            _track("dc_1x", "Double Chance 1X", actual in ("H", "D"), float(odds["dc_1x_odds"]))
        dc_x2 = pd_v + pa
        if dc_x2 >= 65 and (odds.get("dc_x2_odds") or 0) > 1:
            _track("dc_x2", "Double Chance X2", actual in ("D", "A"), float(odds["dc_x2_odds"]))
        dc_12 = ph + pa
        if dc_12 >= 70 and (odds.get("dc_12_odds") or 0) > 1:
            _track("dc_12", "Double Chance 12", actual in ("H", "A"), float(odds["dc_12_odds"]))

    # Compute final metrics
    result = {}
    for key, m in perf.items():
        if m["total"] < 3:
            continue
        winrate = round(m["wins"] / m["total"] * 100, 1)
        roi = round((m["returned"] - m["staked"]) / m["staked"] * 100, 1) if m["staked"] > 0 else 0
        result[key] = {
            "label": m["label"],
            "total": m["total"],
            "wins": m["wins"],
            "losses": m["total"] - m["wins"],
            "winrate": winrate,
            "roi": roi,
            "profitable": roi > 0,
            "active": roi > -5,
        }

    return dict(sorted(result.items(), key=lambda x: x[1]["roi"], reverse=True))


# ─── Performance Summary (V2 landing) ────────────────────────


def _weighted_roi(markets: dict[str, dict]) -> float:
    """Volume-weighted ROI across markets — zero when no bets."""
    total = sum(m["total"] for m in markets.values())
    if not total:
        return 0.0
    return sum(m["roi"] * m["total"] for m in markets.values()) / total


def _compute_performance_summary(window_days: int) -> dict[str, float]:
    """Compute the 4 KPIs surfaced on the V2 landing stat strip.

    Synchronous — performs multiple Supabase queries. Returns primitive floats only.
    Reuses existing aggregates:
    - accuracy: 1X2 accuracy on predictions made in the window (same formula
      as /api/performance).
    - brier: average Brier score on predictions made in the last 7 days
      (frontend label is "Brier 7J").
    - roi: average market ROI weighted by volume, sourced from
      ``_compute_market_performance(window_days)``.
    - bankroll: simulated bankroll assuming a flat 1€ stake on every "active"
      market bet over the window. Good enough as a public signal — the
      real per-user bankroll lives in /api/user/bankroll/*.
    - deltaVs7d: same metric computed on the last 7 days, minus the value
      on the 7 days BEFORE that. Gives a "trend arrow".

    Returns zeros (never raises) when the DB has no data — the endpoint
    stays 200 so the frontend can render its fallbacks.
    """
    now = time.monotonic()
    cached = _SUMMARY_CACHE.get(window_days)
    if cached and now - cached[0] < _SUMMARY_CACHE_TTL:
        return cached[1]

    from src.constants import LEAGUES_TO_FETCH

    # ── ROI + bankroll from market performance ───────────────────
    markets = _compute_market_performance(days=window_days)
    weighted_roi = _weighted_roi(markets)
    bankroll_value = round(_BANKROLL_SEED_EUR * (1.0 + weighted_roi / 100.0), 2)

    # Previous 7d = days 8..14. We don't have a "range" helper so we just
    # compute the delta as roi(7d) - roi(14d weighted), matching the
    # frontend's label "vs 7j". Close enough for a public signal.
    roi_7 = _weighted_roi(_compute_market_performance(days=7))
    roi_14 = _weighted_roi(_compute_market_performance(days=14))
    roi_delta = round(roi_7 - roi_14, 2)

    # ── Accuracy + Brier from predictions/fixtures ───────────────
    from datetime import datetime, timedelta, timezone

    def _accuracy_brier(days: int) -> tuple[float, float]:
        """Return (accuracy_pct, brier_score) over the window. (0.0, 0.0) if empty."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            finished = (
                supabase.table("fixtures")
                .select("id, home_goals, away_goals, date")
                .in_("status", ["FT", "AET", "PEN"])
                .in_("league_id", LEAGUES_TO_FETCH)
                .gte("date", cutoff)
                .order("date")
                .range(0, 999)
                .execute()
                .data
                or []
            )
        except Exception:
            logger.warning("summary: fixtures fetch failed", exc_info=True)
            return 0.0, 0.0

        if not finished:
            return 0.0, 0.0

        fixture_ids = [f["id"] for f in finished]
        preds: list[dict] = []
        CHUNK = 100
        for i in range(0, len(fixture_ids), CHUNK):
            chunk = fixture_ids[i : i + CHUNK]
            try:
                page = (
                    supabase.table("predictions")
                    .select("fixture_id, proba_home, proba_draw, proba_away")
                    .in_("fixture_id", chunk)
                    .order("created_at")
                    .execute()
                    .data
                    or []
                )
            except Exception:
                logger.warning("summary: predictions fetch failed", exc_info=True)
                page = []
            preds.extend(page)

        # Dedupe keeping the FIRST prediction (lesson 32).
        pred_by_fix: dict[str, dict] = {}
        for p in preds:
            fid = str(p["fixture_id"])
            if fid not in pred_by_fix:
                pred_by_fix[fid] = p

        correct = 0
        countable = 0
        brier_sum = 0.0
        brier_n = 0
        for f in finished:
            pred = pred_by_fix.get(str(f["id"]))
            if not pred:
                continue
            ph, pd_, pa = pred.get("proba_home"), pred.get("proba_draw"), pred.get("proba_away")
            if ph is None or pd_ is None or pa is None:
                continue
            hg = f.get("home_goals") or 0
            ag = f.get("away_goals") or 0
            actual = "H" if hg > ag else ("D" if hg == ag else "A")
            # Strict > to avoid home bias on ties (lesson 30).
            if ph > pd_ and ph > pa:
                pred_r = "H"
            elif pa > ph and pa > pd_:
                pred_r = "A"
            elif pd_ > ph and pd_ > pa:
                pred_r = "D"
            else:
                pred_r = None
            if pred_r is not None:
                countable += 1
                if pred_r == actual:
                    correct += 1
            # Brier always computed when probas are valid.
            o_h = 1 if actual == "H" else 0
            o_d = 1 if actual == "D" else 0
            o_a = 1 if actual == "A" else 0
            brier_sum += (
                (ph / 100.0 - o_h) ** 2
                + (pd_ / 100.0 - o_d) ** 2
                + (pa / 100.0 - o_a) ** 2
            )
            brier_n += 1

        acc = round(correct / countable * 100, 1) if countable else 0.0
        brier = round(brier_sum / brier_n, 3) if brier_n else 0.0
        return acc, brier

    acc_window, _ = _accuracy_brier(window_days)
    acc_7d, brier_7d = _accuracy_brier(7)
    acc_14d, brier_14d = _accuracy_brier(14)
    accuracy_delta = round(acc_7d - acc_14d, 1)
    # Lower Brier = better → the frontend treats brier delta differently but
    # we still expose the raw diff; StatStrip handles the tone.
    brier_delta = round(brier_7d - brier_14d, 3)

    result = {
        "roi_value": round(weighted_roi, 2),
        "roi_delta": roi_delta,
        "accuracy_value": acc_window,
        "accuracy_delta": accuracy_delta,
        "brier_value": brier_7d,
        "brier_delta": brier_delta,
        "bankroll_value": bankroll_value,
    }
    _SUMMARY_CACHE[window_days] = (now, result)
    return result


@router.get(
    "/performance/summary",
    summary="V2 landing KPIs (ROI, accuracy, Brier 7J, bankroll)",
    responses={500: {"description": "Internal server error"}},
)
def get_performance_summary(
    window: Annotated[Literal[7, 30, 90], BeforeValidator(int), Query(
        description="Rolling window in days. Only 7, 30, or 90 are permitted.",
    )] = 30,
):
    """Return the 4 KPIs consumed by `usePerformanceSummary` on the V2 landing.

    Shape is fixed by the frontend `PerformanceSummary` type — any drift here
    blanks out the stat strip (lesson 60: API shape must match frontend exactly).
    """
    try:
        s = _compute_performance_summary(window)
        return {
            "roi30d": {"value": s["roi_value"], "deltaVs7d": s["roi_delta"]},
            "accuracy": {"value": s["accuracy_value"], "deltaVs7d": s["accuracy_delta"]},
            "brier7d": {"value": s["brier_value"], "deltaVs7d": s["brier_delta"]},
            "bankroll": {"value": s["bankroll_value"], "currency": "EUR"},
        }
    except Exception:
        logger.exception("get_performance_summary failed")
        # Never 500 the landing — fall back to typed zeros. The frontend's
        # fallback kicks in but the page stays up.
        return {
            "roi30d": {"value": 0.0, "deltaVs7d": 0.0},
            "accuracy": {"value": 0.0, "deltaVs7d": 0.0},
            "brier7d": {"value": 0.0, "deltaVs7d": 0.0},
            "bankroll": {"value": 0.0, "currency": "EUR"},
        }


@router.get(
    "/market-roi",
    summary="Get per-market ROI for value betting strategy",
    responses={500: {"description": "Internal server error"}},
)
def get_market_roi(days: int = Query(30, description="Rolling window in days (0 = all-time)")):
    """Compute per-market win rate and simulated ROI from predictions + odds.

    Used to determine which markets are profitable for value betting
    and to filter future value bet recommendations.
    """
    try:
        markets = _compute_market_performance(days)
        return {
            "days": days,
            "markets": markets,
            "active_markets": [k for k, v in markets.items() if v["active"]],
            "disabled_markets": [k for k, v in markets.items() if not v["active"]],
        }
    except Exception:
        logger.exception("get_market_roi failed")
        raise HTTPException(status_code=500, detail="Internal server error")
