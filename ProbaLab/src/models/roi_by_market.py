"""src/models/roi_by_market.py — Per-market ROI aggregation (Lot 2 · T05).

Pure function that turns a list of resolved bets into a per-market breakdown
suitable for the ROI-by-market chart on the bankroll page. I/O-free: feed it
already-resolved rows from ``best_bets`` (WIN / LOSS / VOID / PENDING).

Conventions
- ``WIN`` bet: profit = stake * (odds - 1), contributes to staked denominator.
- ``LOSS`` bet: profit = -stake, contributes to staked denominator.
- ``VOID`` bet: not counted toward staked/profit, but counted in ``voids``/``n``.
- ``PENDING`` (or any other value): incremented in ``n`` only — profit/staked
  untouched so the breakdown reflects *resolved* performance. The route layer
  is free to pre-filter PENDING bets.

Output is sorted by ROI descending so the UI can show the top markets first.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_roi_by_market(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate per-market ROI metrics from a flat list of resolved bets.

    Each input bet must expose ``market``, ``odds``, ``stake`` and ``result``.
    Returns a list of ``{market, roi, n, wins, losses, voids}`` dicts, sorted
    DESC on ``roi``. ROI is expressed as a percent (e.g. ``100.0`` = +100%).
    """
    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "n": 0,
            "wins": 0,
            "losses": 0,
            "voids": 0,
            "staked": 0.0,
            "profit": 0.0,
        }
    )

    for bet in bets:
        market = bet["market"]
        bucket = buckets[market]
        bucket["n"] += 1

        try:
            stake = float(bet.get("stake") or 0.0)
            odds = float(bet.get("odds") or 0.0)
        except (TypeError, ValueError):
            # Guard against stray None/str values without crashing the
            # aggregation — we still increment ``n`` so the caller sees the row.
            continue

        result = bet.get("result")
        if result == "WIN":
            bucket["wins"] += 1
            bucket["staked"] += stake
            bucket["profit"] += stake * (odds - 1.0)
        elif result == "LOSS":
            bucket["losses"] += 1
            bucket["staked"] += stake
            bucket["profit"] -= stake
        elif result == "VOID":
            bucket["voids"] += 1
        # PENDING and other values count in ``n`` only.

    rows: list[dict[str, Any]] = []
    for market, data in buckets.items():
        staked = data["staked"]
        roi = round((data["profit"] / staked) * 100.0, 2) if staked > 0 else 0.0
        rows.append(
            {
                "market": market,
                "roi": roi,
                "n": int(data["n"]),
                "wins": int(data["wins"]),
                "losses": int(data["losses"]),
                "voids": int(data["voids"]),
            }
        )

    rows.sort(key=lambda row: row["roi"], reverse=True)
    return rows
