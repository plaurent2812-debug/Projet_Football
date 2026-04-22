"""src/models/matches_aggregator.py — Matches listing aggregation (Lot 2 · T03).

Pure filter/sort/group helper used by `/api/matches`. The caller passes a
flat list of match rows coming from Supabase (already joined with signals,
edge, confidence). This function applies optional signal filtering, sorts
rows by the requested key, and groups them by league while preserving the
first-appearance order of each league (stable, deterministic output).

Kept intentionally free of I/O to make unit tests trivial (lesson 63).
"""

from __future__ import annotations

from typing import Any, Literal

SortKey = Literal["time", "edge", "confidence"]


def aggregate_matches(
    rows: list[dict[str, Any]],
    signals: list[str] | None = None,
    sort: SortKey = "time",
) -> list[dict[str, Any]]:
    """Filter → sort → group match rows by league.

    Args:
        rows: raw match rows (each must expose ``league_id``, ``league_name``
            and ``kickoff_utc``; ``signals``/``edge_pct``/``confidence`` are
            optional and default to empty/0).
        signals: optional list of signal labels ("value", "safe",
            "confidence"). A row is kept if *any* of its signals matches one
            of the requested labels. ``None`` or empty list disables the
            filter.
        sort: sorting strategy applied *before* grouping.
            - ``"time"``: ascending by ISO kickoff timestamp.
            - ``"edge"``: descending by ``edge_pct`` (0 when missing).
            - ``"confidence"``: descending by ``confidence`` (0 when missing).

    Returns:
        A list of league groups ``[{"league_id", "league_name", "matches":
        [row, ...]}]``. Empty input → empty list.
    """
    if signals:
        rows = [row for row in rows if any(s in row.get("signals", []) for s in signals)]

    key_fn = {
        "time": lambda r: r.get("kickoff_utc", ""),
        "edge": lambda r: -_safe_float(r.get("edge_pct")),
        "confidence": lambda r: -_safe_float(r.get("confidence")),
    }[sort]

    sorted_rows = sorted(rows, key=key_fn)

    groups: dict[Any, dict[str, Any]] = {}
    for row in sorted_rows:
        lid = row["league_id"]
        group = groups.setdefault(
            lid,
            {
                "league_id": lid,
                "league_name": row.get("league_name", ""),
                "matches": [],
            },
        )
        group["matches"].append(row)

    return list(groups.values())


def _safe_float(value: Any) -> float:
    """Cast-to-float helper that swallows None/invalid inputs (defaults to 0)."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
