"""tests/test_user_bankroll_roi_by_market.py — Unit + route tests for
/api/user/bankroll/roi-by-market (Lot 2 · T05).

Two sections:

1. Pure logic: ``compute_roi_by_market`` aggregates per-market metrics.
2. Route glue: ``get_roi_by_market`` reads ``best_bets`` for the current user
   and hands the rows off to the pure function.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.models.roi_by_market import compute_roi_by_market


# ──────────────────────────────────────────────────────────────────────
# Pure logic
# ──────────────────────────────────────────────────────────────────────


def test_grouping_and_metrics():
    """Metrics are grouped per market; VOIDs do not count toward ROI staked."""
    bets = [
        {"market": "1X2", "odds": 2.00, "stake": 10, "result": "WIN"},
        {"market": "1X2", "odds": 1.80, "stake": 10, "result": "LOSS"},
        {"market": "1X2", "odds": 1.50, "stake": 10, "result": "VOID"},
        {"market": "BTTS", "odds": 2.10, "stake": 20, "result": "WIN"},
    ]

    out = compute_roi_by_market(bets)

    one_x_two = next(r for r in out if r["market"] == "1X2")
    assert one_x_two["n"] == 3
    assert one_x_two["wins"] == 1
    assert one_x_two["losses"] == 1
    assert one_x_two["voids"] == 1
    # profit = (10 * (2-1)) - 10 = 0 ; staked (hors void) = 20 → ROI 0 %
    assert abs(one_x_two["roi"] - 0.0) < 0.01

    btts = next(r for r in out if r["market"] == "BTTS")
    assert btts["wins"] == 1
    assert btts["losses"] == 0
    # profit = 20 * (2.10 - 1) = 22 ; staked = 20 → ROI 110 %
    assert abs(btts["roi"] - 110.0) < 0.01


def test_only_losses_gives_negative_roi():
    """A market with only losses has ROI = -100%."""
    bets = [
        {"market": "O/U", "odds": 1.90, "stake": 10, "result": "LOSS"},
        {"market": "O/U", "odds": 2.10, "stake": 10, "result": "LOSS"},
    ]

    out = compute_roi_by_market(bets)

    ou = next(r for r in out if r["market"] == "O/U")
    assert ou["wins"] == 0
    assert ou["losses"] == 2
    assert ou["roi"] == -100.0


def test_only_voids_gives_zero_roi():
    """Only VOID bets → no staked, ROI falls back to 0.0 (no division by zero)."""
    bets = [
        {"market": "1X2", "odds": 2.00, "stake": 10, "result": "VOID"},
    ]

    out = compute_roi_by_market(bets)

    row = out[0]
    assert row["market"] == "1X2"
    assert row["n"] == 1
    assert row["voids"] == 1
    assert row["roi"] == 0.0


def test_empty_input_returns_empty_list():
    """No bets → empty output (no crash)."""
    assert compute_roi_by_market([]) == []


def test_sort_desc_by_roi():
    """Output rows are sorted by ROI descending so the UI can show top markets first."""
    bets = [
        {"market": "LowROI", "odds": 1.50, "stake": 10, "result": "LOSS"},
        {"market": "HighROI", "odds": 3.00, "stake": 10, "result": "WIN"},
        {"market": "MidROI", "odds": 2.00, "stake": 10, "result": "WIN"},
    ]

    out = compute_roi_by_market(bets)

    markets_in_order = [r["market"] for r in out]
    assert markets_in_order == ["HighROI", "MidROI", "LowROI"]


# ──────────────────────────────────────────────────────────────────────
# Route glue
# ──────────────────────────────────────────────────────────────────────


def test_route_returns_breakdown(mock_supabase, fake_user):
    """Route returns ``{window_days, rows}`` with per-market ROI rows."""
    from api.routers.v2.user_bankroll import get_roi_by_market

    mock_supabase.execute.return_value = MagicMock(
        data=[{"market": "1X2", "odds": 2.0, "stake": 10, "result": "WIN"}]
    )

    out = get_roi_by_market.__wrapped__(
        window=30, request=MagicMock(), user=fake_user
    )

    assert out["window_days"] == 30
    assert out["rows"][0]["market"] == "1X2"
    assert out["rows"][0]["wins"] == 1
    # ROI = (10 * (2-1)) / 10 * 100 = 100 %
    assert abs(out["rows"][0]["roi"] - 100.0) < 0.01


def test_route_queries_best_bets_for_current_user(mock_supabase, fake_user):
    """The route targets ``best_bets`` filtered on user_id = current_user.id."""
    from api.routers.v2.user_bankroll import get_roi_by_market

    mock_supabase.execute.return_value = MagicMock(data=[])

    get_roi_by_market.__wrapped__(
        window=30, request=MagicMock(), user=fake_user
    )

    table_calls = [c.args[0] for c in mock_supabase.table.call_args_list if c.args]
    assert "best_bets" in table_calls

    # ``user_id`` is passed to .eq() — guard against any regression that would
    # leak another user's data via a different column name.
    eq_calls = mock_supabase.eq.call_args_list
    assert any(
        call.args and call.args[0] == "user_id" and call.args[1] == fake_user["id"]
        for call in eq_calls
    )


def test_route_defaults_to_30_day_window(mock_supabase, fake_user):
    """Default window is 30 days when the query param is omitted."""
    from api.routers.v2.user_bankroll import get_roi_by_market

    mock_supabase.execute.return_value = MagicMock(data=[])

    out = get_roi_by_market.__wrapped__(
        window=30, request=MagicMock(), user=fake_user
    )

    assert out["window_days"] == 30
    assert out["rows"] == []
