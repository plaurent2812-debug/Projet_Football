"""
api/routers/performance.py — Model performance metrics endpoint.

Computes accuracy, Brier score, and benchmark comparisons across all
finished fixtures with predictions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from src.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Performance"])


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
                .select("id, home_team, away_team, home_goals, away_goals, date, status")
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
            page = supabase.table("predictions").select("*").in_("fixture_id", chunk).order("created_at").execute().data or []
            predictions.extend(page)

        # Fetch bookmaker odds for benchmark computation
        bookmaker_odds_by_fixture: dict[str, dict] = {}
        for i in range(0, len(fixture_ids), CHUNK):
            chunk = fixture_ids[i : i + CHUNK]
            odds_page = (
                supabase.table("fixture_odds")
                .select("fixture_api_id, home_win_odds, draw_odds, away_win_odds")
                .in_("fixture_api_id", chunk)
                .execute()
                .data or []
            )
            for o in odds_page:
                fid = str(o["fixture_api_id"])
                if fid not in bookmaker_odds_by_fixture:
                    bookmaker_odds_by_fixture[fid] = o

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

            def get_val(key, default=None):
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
                fid_str = str(f["id"])
                bm_odds = bookmaker_odds_by_fixture.get(fid_str)
                if bm_odds and bm_odds.get("home_win_odds") and bm_odds.get("draw_odds") and bm_odds.get("away_win_odds"):
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
            brier_match = (p_h - o_h)**2 + (p_d - o_d)**2 + (p_a - o_a)**2
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
            fid_str = str(f["id"])
            bm_odds = bookmaker_odds_by_fixture.get(fid_str)
            if bm_odds and bm_odds.get("home_win_odds") and bm_odds.get("draw_odds") and bm_odds.get("away_win_odds"):
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
            "brier_score_1x2_normalized": round(brier_sum / total_with_pred / 2, 3) if total_with_pred else 0,
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
