"""CLV engine — rigorous Closing Line Value computation per market.

Usage:
    from src.monitoring.clv_engine import run_daily_clv_snapshot
    run_daily_clv_snapshot()  # upsert model_health_log for yesterday

Design:
    - fair_prob_from_odds: decimal odds → raw implied (with vig)
    - remove_overround: list of odds for a closed market → fair probs (sum=1)
    - compute_clv: CLV = model_prob / closing_fair_prob - 1, clamped to [-1, +1]
    - aggregate_clv_by_market: joins predictions + closing_odds + results (Task 10)
    - run_daily_clv_snapshot: cron entrypoint (Task 11)
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from src.config import supabase

logger = logging.getLogger("football_ia.clv_engine")


def fair_prob_from_odds(odds: float) -> float:
    """Décimal → proba implicite avec vig (pas encore dé-overroundée)."""
    if odds < 1.01:
        raise ValueError(f"Invalid decimal odds: {odds} (must be >= 1.01)")
    return 1.0 / odds


def remove_overround(odds_list: list[float]) -> list[float]:
    """Retire le vig d'un marché fermé (toutes les issues mutuellement exclusives).

    Normalisation proportionnelle (méthode la plus utilisée, équivalente à
    `margin_weights` de Shin 1993 quand overround est faible).

    Args:
        odds_list: cotes décimales de toutes les issues (ex: [home, draw, away])

    Returns:
        probas fair (sum=1). Liste vide si input vide.
    """
    if not odds_list:
        return []
    implied = [fair_prob_from_odds(o) for o in odds_list]
    overround = sum(implied)
    if overround <= 0:
        return []
    return [p / overround for p in implied]


def compute_clv(*, model_prob: float, closing_fair_prob: float) -> float:
    """CLV = (model_prob / closing_fair_prob) - 1, clampé à [-1, +1].

    - CLV > 0  → on battait la closing line (edge)
    - CLV = 0  → on matchait la closing line
    - CLV < 0  → closing line était meilleure que notre probs
    """
    if closing_fair_prob <= 0:
        return 1.0 if model_prob > 0 else -1.0
    raw = (model_prob / closing_fair_prob) - 1.0
    return max(-1.0, min(1.0, raw))


def aggregate_clv_by_market(
    *,
    predictions: list[dict],
    closing_odds_rows: list[dict],
    market: str,
    bookmaker: str,
) -> dict:
    """Jointure predictions × closing_odds pour un (market, bookmaker).

    Args:
        predictions: rows de prediction_results avec pred_home/draw/away ou pred_yes/no
            selon le marché, et actual_result.
        closing_odds_rows: rows de closing_odds (déjà filtrés snapshot_type='closing').
        market: "1x2" | "btts" | "over_2_5" | ...
        bookmaker: nom canonique (pinnacle, betclic, ...).

    Returns:
        Dict avec n_matches, clv_mean (sur le pick du modèle), clv_<selection> moyens
        par issue, n_positive.
    """
    # Index closing odds par (fixture_id, selection)
    by_fix: dict[str, dict[str, float]] = defaultdict(dict)
    for row in closing_odds_rows:
        if row["market"] != market or row["bookmaker"] != bookmaker:
            continue
        by_fix[row["fixture_id"]][row["selection"]] = float(row["odds"])

    if not by_fix:
        return {"n_matches": 0, "clv_mean": 0.0}

    selections_for_market = _selections_for_market(market)
    clv_by_selection: dict[str, list[float]] = defaultdict(list)
    pick_clvs: list[float] = []

    for pred in predictions:
        fid = pred.get("fixture_id")
        if fid not in by_fix:
            continue
        odds_by_sel = by_fix[fid]
        if not all(s in odds_by_sel for s in selections_for_market):
            continue
        ordered_odds = [odds_by_sel[s] for s in selections_for_market]
        fair_probs = remove_overround(ordered_odds)
        if not fair_probs:
            continue

        model_probs = _model_probs_for_market(pred, market)
        if model_probs is None or len(model_probs) != len(selections_for_market):
            continue

        clvs: list[float] = []
        for sel, mp, fp in zip(selections_for_market, model_probs, fair_probs):
            clv = compute_clv(model_prob=mp, closing_fair_prob=fp)
            clv_by_selection[sel].append(clv)
            clvs.append(clv)
        # Pick = selection avec max model_prob
        pick_idx = max(range(len(model_probs)), key=lambda i: model_probs[i])
        pick_clvs.append(clvs[pick_idx])

    n = len(pick_clvs)
    if n == 0:
        return {"n_matches": 0, "clv_mean": 0.0}
    out: dict = {
        "n_matches": n,
        "clv_mean": sum(pick_clvs) / n,
        "n_positive": sum(1 for c in pick_clvs if c > 0),
        "pct_positive": round(sum(1 for c in pick_clvs if c > 0) / n * 100, 1),
    }
    for sel, values in clv_by_selection.items():
        out[f"clv_{sel}"] = sum(values) / len(values)
    return out


def _selections_for_market(market: str) -> list[str]:
    if market == "1x2":
        return ["home", "draw", "away"]
    if market == "moneyline":
        return ["home", "away"]
    if market == "btts":
        return ["yes", "no"]
    if market.startswith("over_") or market == "totals_nhl":
        return ["over", "under"]
    raise ValueError(f"Unknown market: {market}")


def _model_probs_for_market(pred: dict, market: str) -> list[float] | None:
    """Extrait [p1, p2, ...] en [0,1] depuis une row prediction_results."""

    def _norm(value) -> float | None:
        if value is None:
            return None
        v = float(value)
        return v / 100.0 if v > 1.5 else v

    if market == "1x2":
        h = _norm(pred.get("pred_home"))
        d = _norm(pred.get("pred_draw"))
        a = _norm(pred.get("pred_away"))
        if None in (h, d, a):
            return None
        return [h, d, a]
    if market == "moneyline":
        h = _norm(pred.get("pred_home"))
        a = _norm(pred.get("pred_away"))
        if None in (h, a):
            return None
        return [h, a]
    if market == "btts":
        y = _norm(pred.get("pred_btts_yes") or pred.get("proba_btts"))
        if y is None:
            return None
        return [y, 1.0 - y]
    if market == "over_2_5":
        o = _norm(pred.get("pred_over_25") or pred.get("proba_over_25"))
        if o is None:
            return None
        return [o, 1.0 - o]
    return None


def _load_predictions_for_date(target: date) -> list[dict]:
    """Charge les prediction_results pour les matchs dont match_date == target.

    Joint prediction_results × fixtures (et nhl_fixtures) par fixture_id
    pour filtrer sur la vraie date du match (pas created_at du post-match eval).
    """
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    # Step 1: fixture_ids (football + NHL) whose match date is in window
    fixture_ids: set[str] = set()

    try:
        foot_rows = (
            supabase.table("fixtures")
            .select("id")
            .gte("date", start.isoformat())
            .lt("date", end.isoformat())
            .execute()
            .data
        ) or []
        fixture_ids.update(str(r["id"]) for r in foot_rows if r.get("id"))
    except Exception:
        logger.exception("[_load_predictions_for_date] football fixtures load failed")

    try:
        nhl_rows = (
            supabase.table("nhl_fixtures")
            .select("game_id")
            .gte("game_date", start.isoformat())
            .lt("game_date", end.isoformat())
            .execute()
            .data
        ) or []
        fixture_ids.update(str(r["game_id"]) for r in nhl_rows if r.get("game_id"))
    except Exception:
        logger.exception("[_load_predictions_for_date] nhl fixtures load failed")

    if not fixture_ids:
        return []

    # Step 2: load prediction_results matching those fixture_ids
    # PostgREST supports .in_() but chunks large lists — keep it simple
    fixture_id_list = list(fixture_ids)
    rows: list[dict] = []
    CHUNK = 200
    for i in range(0, len(fixture_id_list), CHUNK):
        chunk = fixture_id_list[i : i + CHUNK]
        try:
            r = (
                supabase.table("prediction_results")
                .select("*")
                .in_("fixture_id", chunk)
                .execute()
                .data
            ) or []
            rows.extend(r)
        except Exception:
            logger.exception("[_load_predictions_for_date] prediction_results chunk failed")

    return rows


def _load_closing_odds_for_date(target: date) -> list[dict]:
    """Charge les closing_odds dont match_start dans la journée target."""
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    rows = (
        supabase.table("closing_odds")
        .select("*")
        .eq("snapshot_type", "closing")
        .gte("match_start", start.isoformat())
        .lt("match_start", end.isoformat())
        .execute()
        .data
    ) or []
    return rows


_FR_BOOKMAKERS = ["betclic", "winamax", "unibet", "zebet"]


def _compute_fr_avg_clv(
    predictions: list[dict], closing_rows: list[dict], market: str
) -> float | None:
    per_book: list[float] = []
    for bk in _FR_BOOKMAKERS:
        res = aggregate_clv_by_market(
            predictions=predictions,
            closing_odds_rows=closing_rows,
            market=market,
            bookmaker=bk,
        )
        if res["n_matches"] > 0:
            per_book.append(res["clv_mean"])
    if not per_book:
        return None
    return sum(per_book) / len(per_book)


def run_daily_clv_snapshot(*, target_date: date | None = None) -> dict:
    """Entrypoint cron — calcule CLV vs Pinnacle + moyenne FR pour J-1.

    Upsert une row dans model_health_log avec toutes les colonnes CLV.
    """
    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    predictions = _load_predictions_for_date(target_date)
    closing_rows = _load_closing_odds_for_date(target_date)

    if not predictions:
        logger.info("[clv_snapshot] No predictions for %s — skip", target_date)
        return {"n_matches_clv": 0}

    # Calculs Pinnacle
    p_1x2 = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=closing_rows,
        market="1x2",
        bookmaker="pinnacle",
    )
    p_btts = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=closing_rows,
        market="btts",
        bookmaker="pinnacle",
    )
    p_over25 = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=closing_rows,
        market="over_2_5",
        bookmaker="pinnacle",
    )
    p_nhl_ml = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=closing_rows,
        market="moneyline",
        bookmaker="pinnacle",
    )
    p_nhl_goals = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=closing_rows,
        market="totals_nhl",
        bookmaker="pinnacle",
    )

    # Moyennes FR
    fr_1x2 = _compute_fr_avg_clv(predictions, closing_rows, "1x2")
    fr_btts = _compute_fr_avg_clv(predictions, closing_rows, "btts")
    fr_over25 = _compute_fr_avg_clv(predictions, closing_rows, "over_2_5")

    variant_id = os.getenv("PROBALAB_ACTIVE_VARIANT", "baseline")
    n_total = p_1x2.get("n_matches", 0)

    row = {
        "sport": "football",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "n_matches_clv": n_total,
        "clv_vs_pinnacle_1x2": p_1x2.get("clv_mean"),
        "clv_vs_pinnacle_btts": p_btts.get("clv_mean"),
        "clv_vs_pinnacle_over25": p_over25.get("clv_mean"),
        "clv_vs_pinnacle_nhl_ml": p_nhl_ml.get("clv_mean"),
        "clv_vs_pinnacle_nhl_goals": p_nhl_goals.get("clv_mean"),
        "clv_vs_fr_avg_1x2": fr_1x2,
        "clv_vs_fr_avg_btts": fr_btts,
        "clv_vs_fr_avg_over25": fr_over25,
        "variant_id": variant_id,
    }
    supabase.table("model_health_log").insert(row).execute()
    logger.info(
        "[clv_snapshot] variant=%s n=%d clv_1x2_vs_pinnacle=%s",
        variant_id,
        n_total,
        p_1x2.get("clv_mean"),
    )
    return row
