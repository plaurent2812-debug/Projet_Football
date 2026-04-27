"""Tests for the consolidated `/api/matches` endpoint (Lot 2 · T03).

Unlike the first draft (which assumed a ``matches_v2_view``), the real route
fans out to several source tables. These tests wire ``mock_supabase.execute``
in the same order the router issues queries:

1. ``fixtures`` (football)
2. ``predictions``
3. ``best_bets`` (football, pending)
4. ``nhl_fixtures``
5. ``best_bets`` (nhl, pending)

Plus up to 4 more queries triggered by the internal call to
``get_safe_pick.__wrapped__`` (fixtures/predictions/odds/nhl_fixtures again).

Tests call ``get_matches.__wrapped__(...)`` to bypass slowapi (lesson 64).
"""

from __future__ import annotations

from datetime import date as date_type
from unittest.mock import MagicMock

from api.routers.v2.matches_v2 import (
    _confidence_pct,
    _derive_signals,
    get_matches,
)


def _build_execute_side_effect(
    football_fixtures: list[dict],
    football_predictions: list[dict],
    football_bets: list[dict],
    nhl_fixtures: list[dict],
    nhl_bets: list[dict],
    include_football: bool = True,
    include_nhl: bool = True,
    safe_pick_fixtures: list[dict] | None = None,
) -> list[MagicMock]:
    """Build the full execute() side_effect sequence in router order.

    Each branch (football / NHL / safe_pick) short-circuits when fixtures
    come back empty, so the exact query count varies. We compute the
    sequence explicitly to mirror the router's control flow.
    """
    safe_pick_fx = safe_pick_fixtures if safe_pick_fixtures is not None else []
    seq: list[MagicMock] = []

    # ── /api/matches football branch ----------------------------------
    if include_football:
        seq.append(MagicMock(data=football_fixtures))
        if football_fixtures:
            seq.append(MagicMock(data=football_predictions))
            seq.append(MagicMock(data=football_bets))

    # ── /api/matches NHL branch ---------------------------------------
    if include_nhl:
        seq.append(MagicMock(data=nhl_fixtures))
        if nhl_fixtures:
            seq.append(MagicMock(data=nhl_bets))

    # ── /api/safe-pick nested call ------------------------------------
    seq.append(MagicMock(data=safe_pick_fx))
    if safe_pick_fx:
        # predictions + odds only fire when the fixture set is non-empty.
        seq.append(MagicMock(data=[]))
        seq.append(MagicMock(data=[]))
    # The safe_pick NHL fetch is always issued regardless of football.
    seq.append(MagicMock(data=[]))

    return seq


def test_confidence_pct_scales_score_correctly() -> None:
    """1..10 score must become 10..100 percent (pure function)."""
    assert _confidence_pct(7) == 70.0
    assert _confidence_pct(10) == 100.0
    assert _confidence_pct(0) == 0.0
    assert _confidence_pct(None) == 0.0
    assert _confidence_pct("bad") == 0.0


def test_derive_signals_combines_value_safe_confidence() -> None:
    """Signals are derived from prediction + pending bets + safe pick."""
    prediction = {"confidence_score": 8}
    pending_bets = [{"kelly_edge": 3.5}]
    signals = _derive_signals(prediction, pending_bets, safe_fixture_id="fx-1", fixture_id="fx-1")
    assert set(signals) == {"value", "safe", "confidence"}


def test_matches_v2_basic(mock_supabase, fake_user) -> None:
    """A single fixture rolls up into one league group with signals injected."""
    fixtures = [
        {
            "id": "fx-1",
            "api_fixture_id": 10,
            "home_team": "PSG",
            "away_team": "OM",
            "date": "2026-04-21T14:00:00+00:00",
            "status": "NS",
            "league_id": 61,
            "league_name": "Ligue 1",
        }
    ]
    predictions = [
        {
            "fixture_id": "fx-1",
            "proba_home": 60.0,
            "proba_draw": 22.0,
            "proba_away": 18.0,
            "confidence_score": 8,  # → confidence signal
        }
    ]
    mock_supabase.execute.side_effect = _build_execute_side_effect(
        fixtures, predictions, [], [], [], include_nhl=False
    )

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports="football",
        leagues=None,
        signals=None,
        sort="time",
    )

    assert out["date"] == "2026-04-21"
    assert out["total"] == 1
    assert out["groups"][0]["league_id"] == 61
    match = out["groups"][0]["matches"][0]
    assert match["fixture_id"] == "fx-1"
    assert "confidence" in match["signals"]


def test_matches_v2_empty(mock_supabase, fake_user) -> None:
    """With no matches anywhere, response is empty but well-formed."""
    mock_supabase.execute.side_effect = _build_execute_side_effect([], [], [], [], [])

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports=None,
        leagues=None,
        signals=None,
        sort="time",
    )

    assert out["total"] == 0
    assert out["groups"] == []


def test_matches_v2_signal_filter_keeps_value_only(mock_supabase, fake_user) -> None:
    """The `signals=value` filter drops rows without a positive-edge pending bet."""
    fixtures = [
        {
            "id": "fx-A",
            "api_fixture_id": 1,
            "home_team": "A1",
            "away_team": "A2",
            "date": "2026-04-21T14:00:00+00:00",
            "league_id": 39,
            "league_name": "PL",
        },
        {
            "id": "fx-B",
            "api_fixture_id": 2,
            "home_team": "B1",
            "away_team": "B2",
            "date": "2026-04-21T17:00:00+00:00",
            "league_id": 39,
            "league_name": "PL",
        },
    ]
    predictions = [
        {"fixture_id": "fx-A", "confidence_score": 5},
        {"fixture_id": "fx-B", "confidence_score": 5},
    ]
    # Only fx-B has a pending best_bet with positive edge → triggers ``value``.
    bets = [
        {
            "fixture_id": "fx-B",
            "sport": "football",
            "market": "Over 2.5 buts",
            "selection": "Over",
            "odds": 1.90,
            "prob": 0.58,
            "kelly_edge": 2.5,
            "result": None,
        }
    ]

    mock_supabase.execute.side_effect = _build_execute_side_effect(
        fixtures, predictions, bets, [], []
    )

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports=None,
        leagues=None,
        signals="value",
        sort="edge",
    )

    assert out["total"] == 1
    match = out["groups"][0]["matches"][0]
    assert match["fixture_id"] == "fx-B"
    assert "value" in match["signals"]
    assert match["edge_pct"] == 2.5


def test_matches_v2_nhl_grouped_under_nhl_league(mock_supabase, fake_user) -> None:
    """NHL fixtures cluster under a synthetic ``NHL`` league group."""
    nhl_fx = [
        {
            "id": "nhl-1",
            "home_team": "BOS",
            "away_team": "NYR",
            "date": "2026-04-21T23:00:00+00:00",
            "status": "NS",
        }
    ]
    mock_supabase.execute.side_effect = _build_execute_side_effect(
        [], [], [], nhl_fx, [], include_football=False
    )

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports="nhl",
        leagues=None,
        signals=None,
        sort="time",
    )

    assert out["total"] == 1
    assert out["groups"][0]["league_id"] == "NHL"
    assert out["groups"][0]["matches"][0]["sport"] == "nhl"


def test_matches_v2_league_filter_excludes_nhl(mock_supabase, fake_user) -> None:
    """When the caller filters by football league IDs, NHL rows are dropped.

    Because ``league_filter`` is non-empty, the NHL branch short-circuits
    before issuing any query at all (see ``_fetch_nhl_rows``), so we pass
    ``include_nhl=False`` to model that in the mock sequence.
    """
    mock_supabase.execute.side_effect = _build_execute_side_effect(
        [], [], [], [], [], include_nhl=False
    )

    out = get_matches.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 21),
        sports=None,
        leagues="61",
        signals=None,
        sort="time",
    )

    # Leagues filter was specified → NHL branch returns nothing.
    assert out["total"] == 0
    assert out["groups"] == []
