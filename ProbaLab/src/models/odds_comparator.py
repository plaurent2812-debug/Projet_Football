"""src/models/odds_comparator.py — Odds comparison helper (Lot 2 · T04).

Pure function that turns a flat list of normalized odds rows into a two-level
mapping ``{market: {selection: [entry, ...]}}`` sorted by odds descending, with
exactly one ``is_best=True`` flag per selection (the top odds). I/O-free and
timezone-free: feed it whatever the DB returns after normalization.

Input row shape expected (extra keys are ignored):
    {"market": str, "selection": str, "bookmaker": str, "odds": float | str}

Output entry shape:
    {"bookmaker": str, "odds": float, "is_best": bool}
"""

from __future__ import annotations

from typing import Any


def build_comparison(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Group odds rows by market/selection and flag the best odds per selection.

    Sorting is stable DESC on ``odds`` so that ``[0]`` is always the best
    entry. The first entry in each selection list is tagged ``is_best=True``;
    every other entry is tagged ``False``. Odds are coerced to ``float`` to
    guard against Decimal/str values that can slip through PostgREST responses.
    """
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        market = row["market"]
        selection = row["selection"]
        grouped.setdefault(market, {}).setdefault(selection, []).append(
            {
                "bookmaker": row["bookmaker"],
                "odds": float(row["odds"]),
                "is_best": False,
            }
        )

    for selections in grouped.values():
        for sel_list in selections.values():
            sel_list.sort(key=lambda entry: entry["odds"], reverse=True)
            sel_list[0]["is_best"] = True

    return grouped
