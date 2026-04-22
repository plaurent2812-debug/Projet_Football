"""Tests for the consolidated `/api/matches` endpoint (Lot 2 · T03).

The route is a thin wrapper around `aggregate_matches`; these tests verify
the wiring (query param parsing, Supabase → aggregator → response shape).
Tests call `get_matches.__wrapped__(...)` to bypass slowapi (lesson 64).
"""

from __future__ import annotations

from datetime import date as date_type
from unittest.mock import MagicMock

from api.routers.v2.matches_v2 import get_matches


def test_matches_v2_basic(mock_supabase, fake_user) -> None:
    """A single row should roll up into exactly one group with that match."""
    mock_supabase.execute.return_value = MagicMock(
        data=[
            {
                "fixture_id": "f1",
                "league_id": 39,
                "league_name": "PL",
                "kickoff_utc": "2026-04-21T14:00:00+00:00",
                "signals": ["safe"],
                "confidence": 0.75,
                "edge_pct": 0.0,
            }
        ]
    )

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports="football",
        leagues=None,
        signals=None,
        sort="time",
        user=fake_user,
    )

    assert out["date"] == "2026-04-21"
    assert out["total"] == 1
    assert out["groups"][0]["league_id"] == 39
    assert out["groups"][0]["matches"][0]["fixture_id"] == "f1"


def test_matches_v2_empty(mock_supabase, fake_user) -> None:
    """With no matches, `groups` is an empty list and `total` is 0."""
    mock_supabase.execute.return_value = MagicMock(data=[])

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports=None,
        leagues=None,
        signals=None,
        sort="time",
        user=fake_user,
    )

    assert out["total"] == 0
    assert out["groups"] == []


def test_matches_v2_signals_filter_applied(mock_supabase, fake_user) -> None:
    """The `signals` query param must feed the aggregator's any-of filter."""
    mock_supabase.execute.return_value = MagicMock(
        data=[
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
    )

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports=None,
        leagues=None,
        signals="value",
        sort="edge",
        user=fake_user,
    )

    assert out["total"] == 1
    assert out["groups"][0]["matches"][0]["fixture_id"] == "f2"
