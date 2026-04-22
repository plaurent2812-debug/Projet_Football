"""src/models/safe_pick_selector.py — Safe pick selection logic (Lot 2 · T02).

Pure function that picks the safest bet of the day from a pool of prediction
candidates. "Safe" is defined as:

1. A single bet with odds ∈ [ODDS_MIN, ODDS_MAX] AND confidence >= MIN_CONFIDENCE_SINGLE
   (highest confidence wins). Covers both football and NHL candidates.
2. Fallback: a 2-leg combo whose odds *product* ∈ [ODDS_MIN, ODDS_MAX], built from
   low-odds candidates (odds < ODDS_MIN) sorted by confidence descending. The first
   eligible pair (by confidence priority) is returned.
3. Otherwise `{"safe_pick": None, "fallback_message": "..."}`.

The function is intentionally free of I/O and timezone concerns: callers pass
already-normalized candidate dicts, the selector never touches the DB.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

# Inclusive bounds for the "safe" target return window (single or combo product).
ODDS_MIN = 1.80
ODDS_MAX = 2.20

# Minimum model confidence for a SINGLE to be considered safe. Combo legs are
# not filtered on confidence individually — the product band already constrains
# the implied risk, and sorting by confidence gives a sensible deterministic order.
MIN_CONFIDENCE_SINGLE = 0.60

# User-facing message returned when nothing qualifies.
_FALLBACK_MESSAGE = (
    "Aucun pari Safe ne correspond aux critères aujourd'hui. Revenez demain."
)


def select_safe_pick(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return `{'safe_pick': {...}, 'fallback_message': None}` or a null payload.

    Args:
        candidates: a list of prediction dicts. Each must contain at least
            ``fixture_id``, ``odds`` (float), ``confidence`` (float, 0..1).
            Optional keys (``sport``, ``market``, ``selection``, ...) are
            preserved in the returned payload.

    Returns:
        A dict with two keys: ``safe_pick`` (dict or None) and
        ``fallback_message`` (str or None). ``safe_pick["type"]`` is either
        ``"single"`` (flat attributes) or ``"combo"`` (with ``legs`` +
        ``odds_product``).
    """
    singles = [
        c
        for c in candidates
        if ODDS_MIN <= c["odds"] <= ODDS_MAX and c["confidence"] >= MIN_CONFIDENCE_SINGLE
    ]
    if singles:
        best = max(singles, key=lambda c: c["confidence"])
        return {"safe_pick": {"type": "single", **best}, "fallback_message": None}

    # Combo fallback: only low-odds candidates (< ODDS_MIN) can realistically
    # combine back into the [1.80, 2.20] product band. Sort by confidence so
    # the combo with the most informed legs wins the deterministic pick.
    low_odds = sorted(
        (c for c in candidates if c["odds"] < ODDS_MIN),
        key=lambda c: c["confidence"],
        reverse=True,
    )
    for a, b in combinations(low_odds, 2):
        # Never build a combo out of two legs on the same fixture (correlated risk).
        if a["fixture_id"] == b["fixture_id"]:
            continue
        product = a["odds"] * b["odds"]
        if ODDS_MIN <= product <= ODDS_MAX:
            return {
                "safe_pick": {
                    "type": "combo",
                    "legs": [a, b],
                    "odds_product": round(product, 2),
                },
                "fallback_message": None,
            }

    return {"safe_pick": None, "fallback_message": _FALLBACK_MESSAGE}
