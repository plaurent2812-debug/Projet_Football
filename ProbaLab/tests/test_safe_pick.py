"""Tests for the `/api/safe-pick` endpoint (Lot 2 · T02).

The route is a thin glue layer on top of `select_safe_pick`. These tests
exercise the **real schema wiring** (predictions/fixtures/fixture_odds +
optional NHL) and bypass slowapi via `__wrapped__` (lesson 64).
"""

from __future__ import annotations

from datetime import date as date_type
from unittest.mock import MagicMock

from api.routers.v2.safe_pick import (
    _build_football_candidates,
    _build_nhl_candidates,
    get_safe_pick,
)


def _set_query_results(mock_supabase: MagicMock, results: list[MagicMock]) -> None:
    """Configure ``mock_supabase.execute`` to return the queries in order.

    ``execute()`` is called multiple times per request (fixtures → predictions
    → fixture_odds → nhl_fixtures). Using ``side_effect`` keeps the test
    deterministic when the router issues a fixed sequence of queries.
    """
    mock_supabase.execute.side_effect = results


def test_build_football_candidates_converts_percent_to_decimal() -> None:
    """DB stores probas as percents (0..100) — candidates must be in 0..1."""
    predictions = [
        {
            "fixture_id": "fx-1",
            "proba_home": 75.0,
            "proba_draw": 15.0,
            "proba_away": 10.0,
            "proba_btts": 40.0,
            "proba_over_2_5": 55.0,
            "proba_over_15": 85.0,
            "confidence_score": 8,
        }
    ]
    fixtures_by_id = {
        "fx-1": {
            "id": "fx-1",
            "api_fixture_id": 999,
            "home_team": "A",
            "away_team": "B",
            "date": "2026-04-22T17:00:00+00:00",
            "league_id": 61,
            "league_name": "Ligue 1",
        }
    }
    # No real odds available → implied odds from the probability.
    out = _build_football_candidates(predictions, fixtures_by_id, {})

    # Home at 75% → implied odds = 1/0.75 * 0.95 ≈ 1.27 — out of safe band but
    # still emitted (the selector filters).
    home = next(c for c in out if c["market"] == "1X2" and c["selection"] == "home")
    assert home["confidence"] == 0.8  # confidence_score 8/10
    assert 1.25 <= home["odds"] <= 1.30
    assert home["odds_source"] == "implied"

    # Every emitted candidate must have decimals (sanity vs regression).
    for c in out:
        assert 0.0 <= c["confidence"] <= 1.0


def test_build_football_candidates_uses_real_odds_when_present() -> None:
    """If the bookmaker returns an odds row, we prefer it over implied."""
    predictions = [
        {
            "fixture_id": "fx-2",
            "proba_home": 50.0,
            "proba_draw": 25.0,
            "proba_away": 25.0,
            "confidence_score": 7,
        }
    ]
    fixtures_by_id = {
        "fx-2": {
            "id": "fx-2",
            "api_fixture_id": 123,
            "home_team": "X",
            "away_team": "Y",
            "date": "2026-04-22T19:00:00+00:00",
            "league_id": 39,
            "league_name": "PL",
        }
    }
    odds_by_api_id = {"123": {"fixture_api_id": 123, "home_win_odds": 2.05}}

    out = _build_football_candidates(predictions, fixtures_by_id, odds_by_api_id)
    home = next(c for c in out if c["selection"] == "home")
    assert home["odds"] == 2.05
    assert home["odds_source"] == "real"


def test_safe_pick_uses_real_schema(mock_supabase, fake_user) -> None:
    """End-to-end route wiring: fixtures → predictions → odds → NHL."""
    fixtures = MagicMock(
        data=[
            {
                "id": "fx-100",
                "api_fixture_id": 7000,
                "home_team": "PSG",
                "away_team": "Marseille",
                "date": "2026-04-22T20:00:00+00:00",
                "status": "NS",
                "league_id": 61,
                "league_name": "Ligue 1",
            }
        ]
    )
    predictions = MagicMock(
        data=[
            {
                "fixture_id": "fx-100",
                # 50% → implied odds 1.90 → inside the safe band.
                "proba_home": 50.0,
                "proba_draw": 20.0,
                "proba_away": 30.0,
                "confidence_score": 8,
            }
        ]
    )
    odds = MagicMock(data=[])
    nhl_fixtures = MagicMock(data=[])
    _set_query_results(mock_supabase, [fixtures, predictions, odds, nhl_fixtures])

    out = get_safe_pick.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 22),
    )

    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "single"
    assert out["safe_pick"]["fixture_id"] == "fx-100"
    # Implied odds from a 50% prob with the 0.95 margin land at 1.90.
    assert 1.80 <= out["safe_pick"]["odds"] <= 2.20
    assert out["fallback_message"] is None


def test_safe_pick_empty_returns_fallback(mock_supabase, fake_user) -> None:
    """With no fixtures, `safe_pick` must be None and a fallback message set."""
    _set_query_results(
        mock_supabase,
        [MagicMock(data=[]), MagicMock(data=[]), MagicMock(data=[]), MagicMock(data=[])],
    )

    out = get_safe_pick.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 22),
    )

    assert out["safe_pick"] is None
    assert out["fallback_message"]


def test_safe_pick_falls_back_to_combo_with_low_odds(mock_supabase, fake_user) -> None:
    """Two low-odds implied candidates whose product ∈ band → combo payload."""
    fixtures = MagicMock(
        data=[
            {
                "id": "fx-A",
                "api_fixture_id": 1,
                "home_team": "A1",
                "away_team": "A2",
                "date": "2026-04-22T18:00:00+00:00",
                "league_id": 39,
                "league_name": "PL",
            },
            {
                "id": "fx-B",
                "api_fixture_id": 2,
                "home_team": "B1",
                "away_team": "B2",
                "date": "2026-04-22T19:00:00+00:00",
                "league_id": 39,
                "league_name": "PL",
            },
        ]
    )
    # 70% prob → implied odds ≈ 1.36. 1.36 * 1.36 ≈ 1.85 ∈ [1.80, 2.20].
    predictions = MagicMock(
        data=[
            {
                "fixture_id": "fx-A",
                "proba_home": 70.0,
                "proba_draw": 15.0,
                "proba_away": 15.0,
                "confidence_score": 8,
            },
            {
                "fixture_id": "fx-B",
                "proba_home": 70.0,
                "proba_draw": 15.0,
                "proba_away": 15.0,
                "confidence_score": 7,
            },
        ]
    )
    odds = MagicMock(data=[])
    nhl_fixtures = MagicMock(data=[])
    _set_query_results(mock_supabase, [fixtures, predictions, odds, nhl_fixtures])

    out = get_safe_pick.__wrapped__(
        request=MagicMock(),
        date=date_type(2026, 4, 22),
    )

    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "combo"
    assert len(out["safe_pick"]["legs"]) == 2


def test_nhl_candidates_graceful_on_missing_fields() -> None:
    """NHL best-effort: malformed stats_json must never raise."""
    fixtures = [
        {"id": "nhl-1"},  # no stats_json at all
        {"id": "nhl-2", "stats_json": "not-a-dict"},  # wrong type
        {
            "id": "nhl-3",
            "date": "2026-04-22T23:00:00+00:00",
            "home_team": "BOS",
            "away_team": "NYR",
            "stats_json": {
                "top_players": [
                    {"player_name": "Player A", "prob_point": 65.0},
                    {"player_name": "Player B", "prob_assist": 42.0},
                    "not-a-player",  # wrong shape — should be skipped
                ]
            },
        },
    ]

    candidates = _build_nhl_candidates(fixtures)
    # Only the two valid player rows should be emitted.
    assert len(candidates) == 2
    assert {c["selection"] for c in candidates} == {"Player A", "Player B"}
    for c in candidates:
        assert c["sport"] == "nhl"
        assert c["odds"] >= 1.05
