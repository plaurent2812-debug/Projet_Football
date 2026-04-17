"""
backtest_clv.py — Closing Line Value analysis.

CLV (Closing Line Value) is the gold standard for measuring prediction quality.
If our model's implied probabilities consistently beat the closing line,
we have a genuine edge.

CLV = (model_prob / closing_implied_prob) - 1
  > 0 → we beat the market (profitable long-term)
  = 0 → we match the market (break-even before vig)
  < 0 → market is more accurate than our model

Usage:
    python -m src.monitoring.backtest_clv
"""

from __future__ import annotations

from typing import Any

from src.config import logger, supabase


def _load_predictions_with_odds() -> list[dict]:
    """Load evaluated predictions that have matching closing odds.

    Joins prediction_results → fixtures (via fixture_id) → fixture_odds
    (via api_fixture_id) to get closing odds for CLV computation.
    """
    preds = supabase.table("prediction_results").select("*").execute().data
    if not preds:
        return []

    # Step 1: Get fixture_id → api_fixture_id mapping + date
    fixture_ids = list({p["fixture_id"] for p in preds if p.get("fixture_id")})
    if not fixture_ids:
        return []

    fix_map: dict[str, dict] = {}  # fixture_id → {api_fixture_id, date}
    CHUNK = 100
    for i in range(0, len(fixture_ids), CHUNK):
        chunk = fixture_ids[i : i + CHUNK]
        rows = (
            supabase.table("fixtures")
            .select("id, api_fixture_id, date")
            .in_("id", chunk)
            .execute()
            .data
        )
        for r in rows:
            if r.get("api_fixture_id"):
                fix_map[r["id"]] = {"api_fixture_id": r["api_fixture_id"], "date": r.get("date")}

    # Step 2: Load odds by api_fixture_id
    api_fixture_ids = list({v["api_fixture_id"] for v in fix_map.values()})
    if not api_fixture_ids:
        return []

    odds_map: dict[int, dict] = {}
    for i in range(0, len(api_fixture_ids), CHUNK):
        chunk = api_fixture_ids[i : i + CHUNK]
        rows = (
            supabase.table("fixture_odds")
            .select("fixture_api_id, home_win_odds, draw_odds, away_win_odds")
            .in_("fixture_api_id", chunk)
            .execute()
            .data
        )
        for r in rows:
            if r.get("home_win_odds") and r.get("draw_odds") and r.get("away_win_odds"):
                odds_map[r["fixture_api_id"]] = r

    # Step 3: Merge predictions with odds
    merged = []
    for p in preds:
        fid = p.get("fixture_id")
        fix_info = fix_map.get(fid)
        if not fix_info:
            continue
        api_fid = fix_info["api_fixture_id"]
        if api_fid not in odds_map:
            continue
        merged.append({**p, **odds_map[api_fid], "date": fix_info.get("date")})

    return merged


def _implied_prob(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    return 1.0 / odds if odds > 0 else 0.0


def compute_clv(data: list[dict]) -> dict[str, Any]:
    """Compute CLV metrics for all 1X2 outcomes.

    Returns dict with:
        clv_home, clv_draw, clv_away: mean CLV per outcome
        clv_overall: weighted mean CLV
        n_matches: sample size
        n_positive_clv: how many bets had positive CLV
        by_league: per-league breakdown
    """
    clv_records: list[dict] = []

    for row in data:
        pred_h = row.get("pred_home")
        pred_d = row.get("pred_draw")
        pred_a = row.get("pred_away")
        actual = row.get("actual_result")

        if pred_h is None or pred_d is None or pred_a is None:
            continue

        h_odds = row["home_win_odds"]
        d_odds = row["draw_odds"]
        a_odds = row["away_win_odds"]

        # Remove overround to get fair closing probabilities
        overround = _implied_prob(h_odds) + _implied_prob(d_odds) + _implied_prob(a_odds)
        if overround <= 0:
            continue

        close_h = _implied_prob(h_odds) / overround
        close_d = _implied_prob(d_odds) / overround
        close_a = _implied_prob(a_odds) / overround

        # CLV per outcome: (model_prob / closing_prob) - 1
        model_h = pred_h / 100.0
        model_d = pred_d / 100.0
        model_a = pred_a / 100.0

        clv_h = (model_h / close_h) - 1 if close_h > 0 else 0
        clv_d = (model_d / close_d) - 1 if close_d > 0 else 0
        clv_a = (model_a / close_a) - 1 if close_a > 0 else 0

        # CLV on the recommended side (what we would have bet on)
        best_outcome = max(
            [("H", model_h, clv_h), ("D", model_d, clv_d), ("A", model_a, clv_a)],
            key=lambda x: x[1],
        )

        clv_records.append(
            {
                "fixture_api_id": row.get("fixture_api_id"),
                "league_id": row.get("league_id"),
                "clv_home": clv_h,
                "clv_draw": clv_d,
                "clv_away": clv_a,
                "clv_best": best_outcome[2],
                "best_side": best_outcome[0],
                "actual": actual,
                "model_h": model_h,
                "model_d": model_d,
                "model_a": model_a,
                "close_h": close_h,
                "close_d": close_d,
                "close_a": close_a,
            }
        )

    if not clv_records:
        return {"n_matches": 0, "clv_overall": 0, "daily_clv": [], "status": "NO_DATA"}

    n = len(clv_records)
    mean_clv_h = sum(r["clv_home"] for r in clv_records) / n
    mean_clv_d = sum(r["clv_draw"] for r in clv_records) / n
    mean_clv_a = sum(r["clv_away"] for r in clv_records) / n
    mean_clv_best = sum(r["clv_best"] for r in clv_records) / n
    n_positive = sum(1 for r in clv_records if r["clv_best"] > 0)

    # Per-league breakdown
    by_league: dict[int, dict] = {}
    for r in clv_records:
        lid = r.get("league_id")
        if lid not in by_league:
            by_league[lid] = {"n": 0, "clv_sum": 0.0}
        by_league[lid]["n"] += 1
        by_league[lid]["clv_sum"] += r["clv_best"]

    for lid in by_league:
        by_league[lid]["clv_mean"] = round(by_league[lid]["clv_sum"] / by_league[lid]["n"], 4)

    # Daily CLV breakdown (for chart)
    from collections import defaultdict

    daily: dict[str, list[float]] = defaultdict(list)
    for row, rec in zip(data, clv_records):
        date_str = (row.get("date") or row.get("created_at") or "")[:10]
        if date_str:
            daily[date_str].append(rec["clv_best"])
    daily_clv = sorted(
        [{"date": d, "clv": round(sum(vs) / len(vs), 4), "n": len(vs)} for d, vs in daily.items()],
        key=lambda x: x["date"],
    )

    # CLV on correct predictions only (did we have edge when we were right?)
    correct_clvs = [r["clv_best"] for r in clv_records if r["actual"] == r["best_side"]]
    clv_when_correct = sum(correct_clvs) / len(correct_clvs) if correct_clvs else 0

    return {
        "n_matches": n,
        "clv_home_mean": round(mean_clv_h, 4),
        "clv_draw_mean": round(mean_clv_d, 4),
        "clv_away_mean": round(mean_clv_a, 4),
        "clv_best_mean": round(mean_clv_best, 4),
        "clv_when_correct": round(clv_when_correct, 4),
        "n_positive_clv": n_positive,
        "pct_positive_clv": round(n_positive / n * 100, 1),
        "by_league": by_league,
        "daily_clv": daily_clv,
        "status": "OK" if n >= 30 else "LOW_SAMPLE",
        "verdict": (
            "BEATING_MARKET"
            if mean_clv_best > 0.02
            else "MATCHING_MARKET"
            if mean_clv_best > -0.02
            else "BELOW_MARKET"
        ),
    }


def run() -> dict[str, Any]:
    """Run the full CLV backtest.

    Data pipeline:
      prediction_results.fixture_id → fixtures.api_fixture_id → fixture_odds
    Odds at prediction time are also saved in predictions.stats_json.odds_at_prediction
    (since 2026-03-22) for future opening-vs-closing line analysis.
    """
    logger.info("=" * 60)
    logger.info("  CLV BACKTEST — Closing Line Value")
    logger.info("=" * 60)

    data = _load_predictions_with_odds()
    if not data:
        logger.warning("  No predictions with matching odds found.")
        logger.warning("  Ensure fixture_odds table is populated (via fetchers/odds).")
        return {"status": "NO_DATA"}

    # Count total predictions to report coverage
    try:
        total_preds = supabase.table("prediction_results").select("id", count="exact").execute()
        n_total = total_preds.count or 0
        n_matched = len(data)
        n_missing = n_total - n_matched
        if n_missing > 0:
            logger.info(
                f"  {n_matched}/{n_total} predictions have matching odds ({n_missing} missing)"
            )
        else:
            logger.info(f"  {n_matched} matchs avec cotes disponibles")
    except Exception:
        logger.info(f"  {len(data)} matchs avec cotes disponibles")

    results = compute_clv(data)

    logger.info(f"  CLV moyen (best side)  : {results['clv_best_mean']:+.4f}")
    logger.info(f"  CLV moyen (correct)    : {results['clv_when_correct']:+.4f}")
    logger.info(f"  % CLV positif          : {results['pct_positive_clv']}%")
    logger.info(f"  Verdict                : {results['verdict']}")

    if results.get("by_league"):
        logger.info("  Par ligue :")
        for lid, info in sorted(
            results["by_league"].items(), key=lambda x: x[1].get("clv_mean", 0), reverse=True
        ):
            logger.info(f"    League {lid}: CLV={info['clv_mean']:+.4f} (n={info['n']})")

    return results


if __name__ == "__main__":
    run()
