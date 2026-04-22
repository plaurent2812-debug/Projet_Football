"""Tests unitaires pour la logique pure `aggregate_matches` (Lot 2 · T03).

The aggregator filters rows by signals, sorts them by the requested key, then
groups them by league while preserving the first-appearance ordering of
leagues (same behaviour as `dict.setdefault`).
"""

from __future__ import annotations

from src.models.matches_aggregator import aggregate_matches


def test_group_by_league_and_sort_by_time() -> None:
    """Rows from multiple leagues are grouped; inside each group sorted by kickoff."""
    rows = [
        {
            "fixture_id": "f2",
            "league_id": 39,
            "league_name": "Premier League",
            "kickoff_utc": "2026-04-21T17:00:00+00:00",
            "signals": ["value"],
            "confidence": 0.6,
            "edge_pct": 8.0,
        },
        {
            "fixture_id": "f1",
            "league_id": 39,
            "league_name": "Premier League",
            "kickoff_utc": "2026-04-21T14:00:00+00:00",
            "signals": ["safe"],
            "confidence": 0.75,
            "edge_pct": 3.0,
        },
        {
            "fixture_id": "f3",
            "league_id": 61,
            "league_name": "Ligue 1",
            "kickoff_utc": "2026-04-21T19:00:00+00:00",
            "signals": [],
            "confidence": 0.5,
            "edge_pct": 0.0,
        },
    ]
    out = aggregate_matches(rows, sort="time")
    # Premier League first because its earliest match kicks off before Ligue 1's.
    assert [g["league_id"] for g in out] == [39, 61]
    assert [m["fixture_id"] for m in out[0]["matches"]] == ["f1", "f2"]


def test_filter_by_signal() -> None:
    """Only rows containing one of the requested signals are kept."""
    rows = [
        {
            "fixture_id": "f1",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T14:00:00+00:00",
            "signals": ["safe"],
            "confidence": 0.7,
            "edge_pct": 0.0,
        },
        {
            "fixture_id": "f2",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T17:00:00+00:00",
            "signals": ["value"],
            "confidence": 0.6,
            "edge_pct": 8.0,
        },
    ]
    out = aggregate_matches(rows, signals=["value"], sort="edge")
    assert len(out) == 1
    assert out[0]["matches"][0]["fixture_id"] == "f2"


def test_sort_by_confidence_descending() -> None:
    """`sort='confidence'` should put the highest-confidence match first in each group."""
    rows = [
        {
            "fixture_id": "f_low",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T14:00:00+00:00",
            "signals": [],
            "confidence": 0.55,
            "edge_pct": 0.0,
        },
        {
            "fixture_id": "f_high",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T17:00:00+00:00",
            "signals": [],
            "confidence": 0.85,
            "edge_pct": 0.0,
        },
    ]
    out = aggregate_matches(rows, sort="confidence")
    assert out[0]["matches"][0]["fixture_id"] == "f_high"


def test_no_signal_filter_keeps_all_rows() -> None:
    """Without a signals filter, every row passes through the grouper."""
    rows = [
        {
            "fixture_id": "f1",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T14:00:00+00:00",
            "signals": [],
            "confidence": 0.5,
            "edge_pct": 0.0,
        },
        {
            "fixture_id": "f2",
            "league_id": 61,
            "league_name": "L1",
            "kickoff_utc": "2026-04-21T20:00:00+00:00",
            "signals": [],
            "confidence": 0.6,
            "edge_pct": 0.0,
        },
    ]
    out = aggregate_matches(rows, sort="time")
    total = sum(len(g["matches"]) for g in out)
    assert total == 2
    assert {g["league_id"] for g in out} == {39, 61}


def test_signals_filter_any_match_semantics() -> None:
    """A row matches if at least one of its signals is in the requested set."""
    rows = [
        {
            "fixture_id": "f1",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T14:00:00+00:00",
            "signals": ["safe", "confidence"],
            "confidence": 0.7,
            "edge_pct": 0.0,
        },
        {
            "fixture_id": "f2",
            "league_id": 39,
            "league_name": "PL",
            "kickoff_utc": "2026-04-21T17:00:00+00:00",
            "signals": ["value"],
            "confidence": 0.6,
            "edge_pct": 8.0,
        },
    ]
    # Ask for `confidence` — only f1 qualifies (any-of semantics).
    out = aggregate_matches(rows, signals=["confidence"], sort="time")
    assert len(out) == 1
    assert out[0]["matches"][0]["fixture_id"] == "f1"


def test_empty_rows_returns_empty_groups() -> None:
    """An empty row list should return an empty group list (not None)."""
    out = aggregate_matches([], sort="time")
    assert out == []
