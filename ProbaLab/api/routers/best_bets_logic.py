"""
api/routers/best_bets_logic.py — Pure business logic for best bets.

Extracted from best_bets.py to make the resolution/statistics logic
unit-testable without going through FastAPI endpoints or Supabase.

Keep this module FREE of:
- FastAPI imports
- Supabase imports
- Any side effects

Only pure functions operating on plain dicts and primitives.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# ═══════════════════════════════════════════════════════════════════
#  MARKET NORMALIZATION
# ═══════════════════════════════════════════════════════════════════

CATEGORY_MARKETS: set[str] = {"fun_football", "fun_nhl", "safe_football", "safe_nhl"}

MARKET_NORMALIZE: dict[str, str] = {
    # BTTS duplicates
    "BTTS — Les deux équipes marquent": "BTTS",
    "BTTS Oui": "BTTS",
    # NHL player markets → clean French names
    "player_points_over_0.5": "Points (NHL)",
    "player_goals_over_0.5": "Buts (NHL)",
    "player_assists_over_0.5": "Passes (NHL)",
    "player_shots_over_2.5": "Tirs (NHL)",
    # Expert enrichment duplicates
    "Points du joueur : 1 ou plus": "Points (NHL)",
    "Passes décisives du joueur : 1 ou plus": "Passes (NHL)",
    "Buts du joueur : 1 ou plus": "Buts (NHL)",
    # Double Chance variants
    "Double chance 1N": "Double Chance 1N",
    "Double Chance 1X": "Double Chance 1N",
}


def normalize_market(raw: str, bet_label: str = "") -> str:
    """Normalize a raw market name into a canonical form.

    For category meta-tags ("safe_football", "fun_nhl", ...), extract
    the actual market from the bet label (the text after " — " or "—").

    Returns the special value ``"__skip__"`` when the market cannot be
    normalized (typically because the label looks like a match name).
    """
    if raw in CATEGORY_MARKETS and bet_label:
        for sep in (" — ", "—"):
            if sep in bet_label:
                actual = bet_label.split(sep, 1)[1].strip()
                # Skip if extracted value looks like a match name
                if " vs " in actual.lower():
                    return "__skip__"
                return MARKET_NORMALIZE.get(actual, actual)
        return "__skip__"
    # Skip if the raw market itself is a match name (malformed expert picks)
    if " vs " in raw.lower() or " vs. " in raw.lower():
        return "__skip__"
    return MARKET_NORMALIZE.get(raw, raw)


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL MARKET RESOLUTION
# ═══════════════════════════════════════════════════════════════════


def evaluate_single_football_market(
    market_name: str, home_goals: int, away_goals: int
) -> str | None:
    """Evaluate a single football market against a final score.

    Args:
        market_name: Canonical market name (e.g., "Victoire domicile",
            "Over 2.5 buts", "BTTS Oui").
        home_goals: Final home team goals.
        away_goals: Final away team goals.

    Returns:
        "WIN", "LOSS", or None if the market is unknown.
    """
    total = home_goals + away_goals
    if market_name == "Victoire domicile":
        return "WIN" if home_goals > away_goals else "LOSS"
    if market_name == "Victoire extérieur":
        return "WIN" if away_goals > home_goals else "LOSS"
    if market_name == "Match nul":
        return "WIN" if home_goals == away_goals else "LOSS"
    if market_name in ("Double Chance 1N", "Double Chance 1X"):
        return "WIN" if home_goals >= away_goals else "LOSS"
    if market_name == "Double Chance X2":
        return "WIN" if away_goals >= home_goals else "LOSS"
    if market_name == "Over 2.5 buts":
        return "WIN" if total > 2.5 else "LOSS"
    if market_name == "Over 1.5 buts":
        return "WIN" if total > 1.5 else "LOSS"
    if market_name == "Over 3.5 buts":
        return "WIN" if total > 3.5 else "LOSS"
    if market_name in ("BTTS — Les deux équipes marquent", "BTTS", "BTTS Oui"):
        return "WIN" if (home_goals > 0 and away_goals > 0) else "LOSS"
    return None


def evaluate_football_combo(combo_market: str, home_goals: int, away_goals: int) -> str | None:
    """Resolve a football combo market (legs joined by " + ").

    Rules (mirror the inline logic in ``resolve_best_bets``):
      - Any LOSS leg → combo LOSS immediately (short-circuit).
      - Unknown leg (returns None) → combo is PENDING (this function
        returns ``None`` to mean "cannot decide yet").
      - All legs VOID → combo VOID.
      - Otherwise, all non-VOID legs WIN → combo WIN.
      - Any other residual state → None (unexpected, let caller keep PENDING).

    Args:
        combo_market: Combo market name, e.g. "Victoire domicile + BTTS Oui".
        home_goals: Final home goals.
        away_goals: Final away goals.

    Returns:
        "WIN", "LOSS", "VOID", or None when the combo cannot be resolved.
    """
    parts = [p.strip() for p in combo_market.split(" + ")]
    has_loss = False
    has_unknown = False
    all_void = True
    non_void_all_win = True

    for part in parts:
        part_result = evaluate_single_football_market(part, home_goals, away_goals)
        if part_result is None:
            has_unknown = True
            all_void = False
            continue
        if part_result == "VOID":
            continue  # Leg VOID ignored — counts neither WIN nor LOSS
        all_void = False
        if part_result == "LOSS":
            has_loss = True
            non_void_all_win = False
            break  # Short-circuit on first LOSS leg
        # part_result == "WIN" — continue

    if has_loss:
        return "LOSS"
    if has_unknown:
        return None  # Pending — unknown legs
    if all_void:
        return "VOID"
    if non_void_all_win:
        return "WIN"
    return None  # Unexpected residual state


# ═══════════════════════════════════════════════════════════════════
#  NHL PLAYER MARKET RESOLUTION
# ═══════════════════════════════════════════════════════════════════


def evaluate_nhl_player_market(
    market: str, points: int, goals: int, assists: int, shots: int
) -> str:
    """Evaluate a NHL player prop market against actual game stats.

    Args:
        market: Market key. Known values:
            - "player_points_over_0.5" → points ≥ 1
            - "player_goals_over_0.5"  → goals ≥ 1
            - "player_assists_over_0.5" → assists ≥ 1
            - "player_shots_over_2.5"  → shots ≥ 3
            Any unknown market defaults to points ≥ 1.
        points: Total points scored by the player in the game.
        goals: Goals scored.
        assists: Assists.
        shots: Shots on goal.

    Returns:
        "WIN" or "LOSS".
    """
    if market == "player_points_over_0.5":
        return "WIN" if points >= 1 else "LOSS"
    if market == "player_goals_over_0.5":
        return "WIN" if goals >= 1 else "LOSS"
    if market == "player_assists_over_0.5":
        return "WIN" if assists >= 1 else "LOSS"
    if market == "player_shots_over_2.5":
        return "WIN" if shots >= 3 else "LOSS"
    # Default: fall back to points market
    return "WIN" if points >= 1 else "LOSS"


def extract_nhl_market_from_label(label: str) -> str:
    """Guess the NHL market key from a bet label.

    Used when ``market`` is a category meta-tag like "safe_nhl" / "fun_nhl"
    and the real market must be inferred from the human-readable label.
    """
    if "Marquer un but" in label:
        return "player_goals_over_0.5"
    if "Faire une passe" in label:
        return "player_assists_over_0.5"
    if "Over 0.5 Points" in label:
        return "player_points_over_0.5"
    if "Tirs" in label or "tirs" in label:
        return "player_shots_over_2.5"
    return "player_points_over_0.5"


# ═══════════════════════════════════════════════════════════════════
#  STATS COMPUTATION (win rate + ROI)
# ═══════════════════════════════════════════════════════════════════


def calc_stats(raw_bets: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute win rate and ROI statistics over a list of bets.

    Expects each bet dict to contain at least: ``market``, ``result``,
    ``odds``, ``date``.

    FUN combos (``market`` = "fun_football" or "fun_nhl") are grouped
    per ``(date, market)`` and resolved as a single multi-leg bet:
      - LOSS on any leg → combo LOSS
      - All non-VOID legs WIN → combo WIN
      - All legs VOID → combo VOID
      - Otherwise PENDING (ignored in stats)

    Returns a dict with keys: wins, losses, voids, total, win_rate,
    roi_pct, roi_singles_pct, singles_count, combines_count, and
    optionally odds_estimated_count + sample_warning.
    """
    # Group FUN bets as combos
    grouped_bets: list[dict[str, Any]] = []
    fun_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for b in raw_bets:
        if b["market"] in ("fun_football", "fun_nhl"):
            key = (b["date"], b["market"])
            if key not in fun_groups:
                fun_groups[key] = []
            fun_groups[key].append(b)
        else:
            grouped_bets.append(b)

    for key, legs in fun_groups.items():
        date, market = key
        # VOID legs are ignored in combo resolution
        non_void_legs = [leg for leg in legs if leg["result"] != "VOID"]
        has_loss = any(leg["result"] == "LOSS" for leg in non_void_legs)
        all_non_void_win = bool(non_void_legs) and all(
            leg["result"] == "WIN" for leg in non_void_legs
        )
        is_void = len(non_void_legs) == 0  # All legs VOID

        res = "PENDING"
        if has_loss:
            res = "LOSS"
        elif is_void:
            res = "VOID"
        elif all_non_void_win:
            res = "WIN"

        # Combine odds
        total_odds = 1.0
        for leg in legs:
            o = leg.get("odds")
            if o:
                total_odds *= float(o)
        # Fun bets often have estimated total odds ~20 if not precisely calculated
        if total_odds == 1.0:
            total_odds = 20.0

        grouped_bets.append(
            {
                "date": date,
                "market": market,
                "result": res,
                "odds": total_odds,
            }
        )

    resolved = [b for b in grouped_bets if b["result"] in ("WIN", "LOSS")]
    wins = sum(1 for b in resolved if b["result"] == "WIN")
    losses = sum(1 for b in resolved if b["result"] == "LOSS")
    voids = sum(1 for b in grouped_bets if b["result"] == "VOID")
    total = wins + losses
    win_rate = round(wins / total * 100, 1) if total else 0

    roi = 0.0  # Full ROI (all bets)
    roi_singles = 0.0  # ROI singles only (odds <= 3.0)
    singles_count = 0
    combines_count = 0
    odds_estimated = 0

    for b in resolved:
        odds_val = b.get("odds")
        if not odds_val:
            odds_val = 1.85
            odds_estimated += 1
        else:
            odds_val = float(odds_val)

        # Full ROI
        if b["result"] == "WIN":
            roi += odds_val - 1
        else:
            roi -= 1

        # Singles ROI (odds <= 3.0 = paris simples)
        if odds_val <= 3.0:
            singles_count += 1
            if b["result"] == "WIN":
                roi_singles += odds_val - 1
            else:
                roi_singles -= 1
        else:
            combines_count += 1

    roi_pct = round(roi / total * 100, 1) if total else 0
    roi_singles_pct = round(roi_singles / singles_count * 100, 1) if singles_count else 0

    result: dict[str, Any] = {
        "wins": wins,
        "losses": losses,
        "voids": voids,
        "total": total,
        "win_rate": win_rate,
        "roi_pct": roi_pct,
        "roi_singles_pct": roi_singles_pct,
        "singles_count": singles_count,
        "combines_count": combines_count,
    }
    if odds_estimated > 0:
        result["odds_estimated_count"] = odds_estimated
    if total > 0 and total < 10:
        result["sample_warning"] = f"Basé sur seulement {total} paris résolus"
    return result


def build_market_breakdown(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group bets by normalized market and compute per-market stats.

    Skips rows whose market normalizes to "__skip__" (malformed entries).
    Only returns markets that have at least one resolved bet.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in rows:
        label = b.get("bet_label") or b.get("match_label") or ""
        key = normalize_market(b.get("market", "unknown"), label)
        if key == "__skip__":
            continue
        grouped[key].append(b)

    breakdown: dict[str, dict[str, Any]] = {}
    for market, bets in grouped.items():
        s = calc_stats(bets)
        if s["total"] > 0:
            breakdown[market] = s
    return breakdown
