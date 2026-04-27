"""tests/test_odds_comparison.py — Route tests for /api/odds/:id/comparison.

Drive the sync FastAPI route via ``__wrapped__`` to bypass slowapi (lesson 64)
and the ``mock_supabase`` fixture so no real network call happens. Routes in
``api/routers/v2/`` are defined as plain sync functions (no ``pytest-asyncio``
installed) — keep tests synchronous to match.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.routers.v2.odds_comparison import get_odds_comparison


def test_odds_comparison_shape(mock_supabase, fake_user):
    """Route returns {fixture_id, comparison} with best-odds flagged correctly."""
    mock_supabase.execute.return_value = MagicMock(
        data=[
            {"market": "1X2", "selection": "H", "bookmaker": "Winamax", "odds": 1.85},
            {"market": "1X2", "selection": "H", "bookmaker": "Unibet", "odds": 1.92},
        ]
    )

    out = get_odds_comparison.__wrapped__(fixture_id="f1", request=MagicMock())

    assert out["fixture_id"] == "f1"
    assert out["comparison"]["1X2"]["H"][0]["bookmaker"] == "Unibet"
    assert out["comparison"]["1X2"]["H"][0]["is_best"] is True


def test_odds_comparison_empty_when_no_rows(mock_supabase, fake_user):
    """No rows in closing_odds → comparison is an empty dict (no crash)."""
    mock_supabase.execute.return_value = MagicMock(data=[])

    out = get_odds_comparison.__wrapped__(fixture_id="unknown-fixture", request=MagicMock())

    assert out["fixture_id"] == "unknown-fixture"
    assert out["comparison"] == {}


def test_odds_comparison_queries_closing_odds(mock_supabase, fake_user):
    """The route targets the ``closing_odds`` table (not legacy fixture_odds)."""
    mock_supabase.execute.return_value = MagicMock(data=[])

    get_odds_comparison.__wrapped__(fixture_id="f42", request=MagicMock())

    # Pick up every .table(name) call regardless of chain position.
    table_calls = [c.args[0] for c in mock_supabase.table.call_args_list if c.args]
    assert "closing_odds" in table_calls
