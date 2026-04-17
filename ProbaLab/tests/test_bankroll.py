"""
Tests unitaires pour bankroll.py — Gestion du bankroll.

Les appels Supabase sont mockés.
"""

from unittest.mock import MagicMock, patch

from src.bankroll import (
    DEFAULT_BANKROLL,
    _place_bet_legacy,
    get_bankroll_history,
    get_current_bankroll,
    get_pnl_summary,
    place_bet,
    resolve_bet,
)


class TestGetCurrentBankroll:
    """Tests for get_current_bankroll."""

    @patch("src.bankroll.supabase")
    def test_returns_last_value(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"bankroll_after": 750.0}
        ]
        assert get_current_bankroll() == 750.0

    @patch("src.bankroll.supabase")
    def test_returns_default_when_empty(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        assert get_current_bankroll() == DEFAULT_BANKROLL

    @patch("src.bankroll.supabase")
    def test_returns_default_on_error(self, mock_sb: MagicMock):
        mock_sb.table.side_effect = Exception("DB error")
        assert get_current_bankroll() == DEFAULT_BANKROLL


class TestPlaceBet:
    """Tests for place_bet."""

    @patch("src.bankroll.get_current_bankroll", return_value=500.0)
    @patch("src.bankroll.supabase")
    def test_place_valid_bet(self, mock_sb: MagicMock, mock_bankroll: MagicMock):
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1, "status": "pending"}
        ]
        result = place_bet("safe", 10.0, 2.5, "Test bet")
        assert result["id"] == 1

    @patch("src.bankroll.get_current_bankroll", return_value=5.0)
    def test_reject_bet_exceeding_bankroll(self, mock_bankroll: MagicMock):
        result = place_bet("fun", 50.0, 3.0)
        assert "error" in result


class TestResolveBet:
    """Tests for resolve_bet."""

    @patch("src.bankroll.supabase")
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

    @patch("src.bankroll.supabase")
    def test_resolve_not_found(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        result = resolve_bet(999, won=False)
        assert "error" in result

    @patch("src.bankroll.supabase")
    def test_reject_already_resolved(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "status": "won"}
        ]
        result = resolve_bet(1, won=True)
        assert "error" in result


class TestPnlSummary:
    """Tests for get_pnl_summary."""

    @patch("src.bankroll.get_current_bankroll", return_value=500.0)
    @patch("src.bankroll.supabase")
    def test_empty_data(self, mock_sb: MagicMock, mock_bankroll: MagicMock):
        mock_sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []
        result = get_pnl_summary()
        assert result["total_bets"] == 0
        assert result["current_bankroll"] == 500.0

    @patch("src.bankroll.get_current_bankroll", return_value=520.0)
    @patch("src.bankroll.supabase")
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

    @patch("src.bankroll.supabase")
    def test_pnl_summary_handles_db_error(self, mock_sb: MagicMock):
        mock_sb.table.side_effect = Exception("DB connection lost")
        result = get_pnl_summary()
        assert "error" in result
        assert "DB connection lost" in result["error"]

    @patch("src.bankroll.get_current_bankroll", return_value=500.0)
    @patch("src.bankroll.supabase")
    def test_pnl_by_type_win_rate_and_roi(
        self, mock_sb: MagicMock, mock_bankroll: MagicMock
    ):
        mock_sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"status": "won", "stake": 10, "actual_gain": 15, "ticket_type": "safe"},
            {"status": "won", "stake": 10, "actual_gain": 10, "ticket_type": "safe"},
            {"status": "lost", "stake": 10, "actual_gain": -10, "ticket_type": "safe"},
            {"status": "lost", "stake": 5, "actual_gain": -5, "ticket_type": "fun"},
        ]
        result = get_pnl_summary()
        # Safe: 2W 1L out of 3 → 66.7% win rate; gain 15+10-10 = 15 on 30 staked → 50% ROI
        safe = result["by_type"]["safe"]
        assert safe["bets"] == 3
        assert safe["wins"] == 2
        assert safe["win_rate"] == 66.7
        assert safe["roi_pct"] == 50.0
        # Fun: 0W 1L → 0% win rate, -100% ROI
        fun = result["by_type"]["fun"]
        assert fun["bets"] == 1
        assert fun["wins"] == 0
        assert fun["win_rate"] == 0
        assert fun["roi_pct"] == -100.0


# ═══════════════════════════════════════════════════════════════════
#  Nouveaux tests — Phase 1.3 — couverture des branches manquantes
# ═══════════════════════════════════════════════════════════════════


class TestPlaceBetAtomicPath:
    """Covers the RPC atomic path introduced to fix race conditions."""

    @patch("src.bankroll.supabase")
    def test_stake_below_minimum_skipped(self, mock_sb: MagicMock):
        # 0.49€ < 0.50€ minimum → skipped without touching the DB
        result = place_bet("safe", 0.49, 2.0, "Micro bet")
        assert result["status"] == "skipped"
        assert result["reason"] == "stake_below_minimum"
        mock_sb.rpc.assert_not_called()

    @patch("src.bankroll.supabase")
    def test_rpc_returns_single_element_list_unwrapped(self, mock_sb: MagicMock):
        # Supabase sometimes wraps RPC results in a list of 1 — must unwrap
        mock_sb.rpc.return_value.execute.return_value.data = [
            {"id": 42, "status": "pending", "stake": 10.0}
        ]
        result = place_bet("safe", 10.0, 2.0, "Test RPC")
        assert result["id"] == 42
        assert result["status"] == "pending"

    @patch("src.bankroll.supabase")
    def test_rpc_returns_dict_directly(self, mock_sb: MagicMock):
        mock_sb.rpc.return_value.execute.return_value.data = {
            "id": 7,
            "status": "pending",
        }
        result = place_bet("fun", 5.0, 3.0)
        assert result["id"] == 7

    @patch("src.bankroll.supabase")
    def test_rpc_error_dict_returned_as_is(self, mock_sb: MagicMock):
        mock_sb.rpc.return_value.execute.return_value.data = {
            "error": "Stake exceeds bankroll"
        }
        result = place_bet("safe", 1000.0, 2.0)
        assert "error" in result
        assert result["error"] == "Stake exceeds bankroll"

    @patch("src.bankroll._place_bet_legacy")
    @patch("src.bankroll.supabase")
    def test_rpc_exception_falls_back_to_legacy(
        self, mock_sb: MagicMock, mock_legacy: MagicMock
    ):
        # RPC raises → must invoke the legacy fallback path
        mock_sb.rpc.side_effect = Exception("RPC function not found")
        mock_legacy.return_value = {"id": 99, "status": "pending"}

        result = place_bet("safe", 10.0, 2.0, "Fallback test")
        mock_legacy.assert_called_once()
        assert result["id"] == 99

    @patch("src.bankroll._place_bet_legacy")
    @patch("src.bankroll.supabase")
    def test_rpc_none_data_falls_back(
        self, mock_sb: MagicMock, mock_legacy: MagicMock
    ):
        # When the RPC returns no data, the code falls through to legacy
        mock_sb.rpc.return_value.execute.return_value.data = None
        mock_legacy.return_value = {"id": 11, "status": "pending"}

        result = place_bet("safe", 10.0, 2.0)
        mock_legacy.assert_called_once()
        assert result["id"] == 11


class TestPlaceBetLegacyPath:
    """Tests directly against _place_bet_legacy."""

    @patch("src.bankroll.get_current_bankroll", return_value=100.0)
    @patch("src.bankroll.supabase")
    def test_legacy_success_on_first_attempt(
        self, mock_sb: MagicMock, mock_br: MagicMock
    ):
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 5, "status": "pending", "stake": 10.0, "bankroll_after": 90.0}
        ]
        result = _place_bet_legacy("safe", 10.0, 2.0, "Test")
        assert result["id"] == 5

    @patch("src.bankroll.get_current_bankroll", return_value=5.0)
    def test_legacy_rejects_stake_above_bankroll(self, mock_br: MagicMock):
        result = _place_bet_legacy("fun", 50.0, 3.0)
        assert "error" in result
        assert "exceeds bankroll" in result["error"].lower()

    @patch("src.bankroll.get_current_bankroll", return_value=100.0)
    @patch("src.bankroll.supabase")
    def test_legacy_handles_insert_exception(
        self, mock_sb: MagicMock, mock_br: MagicMock
    ):
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Insert failed"
        )
        result = _place_bet_legacy("safe", 10.0, 2.0)
        assert "error" in result
        assert "Insert failed" in result["error"]


class TestGetBankrollHistory:
    @patch("src.bankroll.supabase")
    def test_returns_history_rows(self, mock_sb: MagicMock):
        rows = [
            {
                "date": "2026-04-01",
                "bankroll_after": 500.0,
                "ticket_type": "safe",
                "status": "won",
                "actual_gain": 10.0,
            },
            {
                "date": "2026-04-02",
                "bankroll_after": 495.0,
                "ticket_type": "fun",
                "status": "lost",
                "actual_gain": -5.0,
            },
        ]
        mock_sb.table.return_value.select.return_value.order.return_value.execute.return_value.data = rows
        result = get_bankroll_history()
        assert len(result) == 2
        assert result[0]["bankroll_after"] == 500.0

    @patch("src.bankroll.supabase")
    def test_returns_empty_list_when_no_data(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.order.return_value.execute.return_value.data = None
        result = get_bankroll_history()
        assert result == []

    @patch("src.bankroll.supabase")
    def test_returns_empty_list_on_exception(self, mock_sb: MagicMock):
        mock_sb.table.side_effect = Exception("DB error")
        result = get_bankroll_history()
        assert result == []


class TestResolveBetExtraBranches:
    @patch("src.bankroll.supabase")
    def test_resolve_losing_bet_keeps_deducted_bankroll(self, mock_sb: MagicMock):
        # For a lost bet, bankroll_after stays as-is (stake already deducted)
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
            {"id": 1, "status": "lost", "actual_gain": -10.0}
        ]
        result = resolve_bet(1, won=False)
        assert result["status"] == "lost"
        assert result["actual_gain"] == -10.0

    @patch("src.bankroll.supabase")
    def test_resolve_bet_handles_db_exception(self, mock_sb: MagicMock):
        mock_sb.table.side_effect = Exception("Network error")
        result = resolve_bet(1, won=True)
        assert "error" in result
        assert "Network error" in result["error"]

    @patch("src.bankroll.supabase")
    def test_resolve_bet_update_returns_empty_data_uses_update_dict(
        self, mock_sb: MagicMock
    ):
        # If the .update().execute() call returns no data, fall back to the
        # update dict we sent.
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": 2,
                "status": "pending",
                "stake": 20.0,
                "odds": 3.0,
                "bankroll_before": 500.0,
                "bankroll_after": 480.0,
            }
        ]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = None
        result = resolve_bet(2, won=True)
        assert result["status"] == "won"
        # When data is None, function returns the update dict directly
        assert "actual_gain" in result
