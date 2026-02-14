"""
Tests unitaires pour bankroll.py — Gestion du bankroll.

Les appels Supabase sont mockés.
"""

from unittest.mock import MagicMock, patch

from bankroll import (
    DEFAULT_BANKROLL,
    get_current_bankroll,
    get_pnl_summary,
    place_bet,
    resolve_bet,
)


class TestGetCurrentBankroll:
    """Tests for get_current_bankroll."""

    @patch("bankroll.supabase")
    def test_returns_last_value(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"bankroll_after": 750.0}
        ]
        assert get_current_bankroll() == 750.0

    @patch("bankroll.supabase")
    def test_returns_default_when_empty(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        assert get_current_bankroll() == DEFAULT_BANKROLL

    @patch("bankroll.supabase")
    def test_returns_default_on_error(self, mock_sb: MagicMock):
        mock_sb.table.side_effect = Exception("DB error")
        assert get_current_bankroll() == DEFAULT_BANKROLL


class TestPlaceBet:
    """Tests for place_bet."""

    @patch("bankroll.get_current_bankroll", return_value=500.0)
    @patch("bankroll.supabase")
    def test_place_valid_bet(self, mock_sb: MagicMock, mock_bankroll: MagicMock):
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1, "status": "pending"}
        ]
        result = place_bet("safe", 10.0, 2.5, "Test bet")
        assert result["id"] == 1

    @patch("bankroll.get_current_bankroll", return_value=5.0)
    def test_reject_bet_exceeding_bankroll(self, mock_bankroll: MagicMock):
        result = place_bet("fun", 50.0, 3.0)
        assert "error" in result


class TestResolveBet:
    """Tests for resolve_bet."""

    @patch("bankroll.supabase")
    def test_resolve_winning_bet(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": 1,
                "status": "pending",
                "stake": 10.0,
                "odds": 2.5,
                "bankroll_before": 500.0,
                "bankroll_after": 490.0,
            }
        ]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "status": "won"}
        ]
        result = resolve_bet(1, won=True)
        assert result["status"] == "won"

    @patch("bankroll.supabase")
    def test_resolve_not_found(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        result = resolve_bet(999, won=False)
        assert "error" in result

    @patch("bankroll.supabase")
    def test_reject_already_resolved(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "status": "won"}
        ]
        result = resolve_bet(1, won=True)
        assert "error" in result


class TestPnlSummary:
    """Tests for get_pnl_summary."""

    @patch("bankroll.get_current_bankroll", return_value=500.0)
    @patch("bankroll.supabase")
    def test_empty_data(self, mock_sb: MagicMock, mock_bankroll: MagicMock):
        mock_sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        result = get_pnl_summary()
        assert result["total_bets"] == 0
        assert result["current_bankroll"] == 500.0

    @patch("bankroll.get_current_bankroll", return_value=520.0)
    @patch("bankroll.supabase")
    def test_with_data(self, mock_sb: MagicMock, mock_bankroll: MagicMock):
        mock_sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"status": "won", "stake": 10, "actual_gain": 15, "ticket_type": "safe"},
            {"status": "lost", "stake": 10, "actual_gain": -10, "ticket_type": "fun"},
            {"status": "won", "stake": 20, "actual_gain": 30, "ticket_type": "safe"},
        ]
        result = get_pnl_summary()
        assert result["total_bets"] == 3
        assert result["wins"] == 2
        assert result["losses"] == 1
        assert result["total_staked"] == 40.0
        assert result["total_gain"] == 35.0
        assert "safe" in result["by_type"]
