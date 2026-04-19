"""value_detector — best odds across books + edge + Kelly fractional.

Design:
    - best_odds_per_selection: max odds for each selection in a market
    - kelly_fractional: (b * p - q) / b * fraction (configurable, default 0.25)
    - detect_value_bets: join model_probs + best_odds → list of value bets ≥ threshold

Used by:
    - Daily pipeline (job_brain) to flag value bets in DB
    - GET /api/value-bets endpoint (SS3 consumer)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from src.constants import (
    KELLY_FRACTION,
    MIN_BOOKMAKERS_FOR_VALUE,
    VALUE_EDGE_USER_FACING,
)

logger = logging.getLogger("football_ia.value_detector")


def best_odds_per_selection(rows: list[dict], *, market: str) -> dict[str, dict]:
    """Retourne {selection: {odds, bookmaker, implied_prob}} avec odds=max."""
    out: dict[str, dict] = {}
    for row in rows:
        if row.get("market") != market:
            continue
        sel = row["selection"]
        odds = float(row["odds"])
        current = out.get(sel)
        if current is None or odds > current["odds"]:
            out[sel] = {
                "odds": odds,
                "bookmaker": row["bookmaker"],
                "implied_prob": 1.0 / odds,
            }
    return out


def kelly_fractional(*, edge: float, odds: float, fraction: float = KELLY_FRACTION) -> float:
    """Kelly fractional conservatrice.

    kelly_full = edge / (odds - 1)
    kelly_frac = kelly_full * fraction (default 0.25)

    Retourne 0 si edge ≤ 0 ou odds ≤ 1.
    """
    if edge <= 0 or odds <= 1.0:
        return 0.0
    kelly_full = edge / (odds - 1.0)
    return max(0.0, min(kelly_full * fraction, fraction))


def detect_value_bets(
    *,
    model_probs: dict[str, float],
    odds_rows: list[dict],
    market: str,
    edge_threshold: float = VALUE_EDGE_USER_FACING,
    min_bookmakers: int = MIN_BOOKMAKERS_FOR_VALUE,
) -> list[dict[str, Any]]:
    """Détecte les value bets sur un marché donné.

    Args:
        model_probs: {"home": 0.60, "draw": 0.25, "away": 0.15} (en [0,1])
        odds_rows: rows de closing_odds OU fixture_odds pour ce fixture/market
        market: "1x2" | "btts" | "over_2_5" | ...
        edge_threshold: 0.05 user-facing, 0.03 admin
        min_bookmakers: skip selection si moins de N bookmakers cotent

    Returns:
        Liste de dicts {selection, proba_model, best_odds, bookmaker, edge_pct, kelly_fractional}
        triés par edge descendant.
    """
    # Comptage bookmakers par selection
    books_by_selection: dict[str, set[str]] = defaultdict(set)
    for row in odds_rows:
        if row.get("market") == market:
            books_by_selection[row["selection"]].add(row["bookmaker"])

    best = best_odds_per_selection(odds_rows, market=market)
    bets: list[dict] = []
    for selection, info in best.items():
        if len(books_by_selection.get(selection, set())) < min_bookmakers:
            continue
        p = model_probs.get(selection)
        if p is None:
            continue
        if not (0.0 <= p <= 1.0):
            continue
        edge = p * info["odds"] - 1.0
        if edge < edge_threshold:
            continue
        k = kelly_fractional(edge=edge, odds=info["odds"])
        bets.append(
            {
                "selection": selection,
                "proba_model": round(p * 100, 2),
                "best_odds": round(info["odds"], 4),
                "bookmaker": info["bookmaker"],
                "edge_pct": round(edge * 100, 2),
                "kelly_fractional": round(k, 4),
            }
        )
    bets.sort(key=lambda b: -b["edge_pct"])
    return bets
