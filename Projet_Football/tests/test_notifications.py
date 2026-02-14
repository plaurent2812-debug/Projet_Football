"""
Tests unitaires pour notifications.py — Telegram & Discord.

Tous les appels HTTP sont mockés.
"""

from unittest.mock import MagicMock, patch

from notifications import (
    format_daily_summary,
    format_ticket_result,
    format_value_bets,
    send_discord,
    send_telegram,
)

# ═══════════════════════════════════════════════════════════════════
#  FORMAT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


class TestFormatValueBets:
    """Tests for format_value_bets."""

    def test_empty_list_returns_empty(self):
        assert format_value_bets([]) == ""

    def test_no_value_bets_returns_empty(self):
        preds = [{"home_team": "A", "away_team": "B", "is_value": False}]
        assert format_value_bets(preds) == ""

    def test_formats_value_bet(self):
        preds = [
            {
                "home_team": "PSG",
                "away_team": "Lyon",
                "is_value": True,
                "prediction": "1",
                "confidence": 72,
                "odds": 1.85,
                "edge": 8.5,
            }
        ]
        msg = format_value_bets(preds)
        assert "VALUE BETS" in msg
        assert "PSG" in msg
        assert "Lyon" in msg
        assert "72%" in msg
        assert "1.85" in msg

    def test_multiple_value_bets(self):
        preds = [
            {"home_team": "Arsenal", "away_team": "Burnley", "is_value": True, "prediction": "1"},
            {"home_team": "Chelsea", "away_team": "Derby", "is_value": True, "prediction": "2"},
            {"home_team": "Watford", "away_team": "Fulham", "is_value": False},
        ]
        msg = format_value_bets(preds)
        assert "Arsenal" in msg
        assert "Chelsea" in msg
        assert "Watford" not in msg  # Not a value bet


class TestFormatDailySummary:
    """Tests for format_daily_summary."""

    def test_formats_with_all_fields(self):
        stats = {
            "total_matches": 20,
            "correct_1x2": 12,
            "value_bets_count": 3,
            "brier_score": 0.2145,
        }
        msg = format_daily_summary(stats)
        assert "RÉSUMÉ QUOTIDIEN" in msg
        assert "20" in msg
        assert "12/20" in msg
        assert "60.0%" in msg
        assert "0.2145" in msg

    def test_formats_without_brier(self):
        stats = {"total_matches": 5, "correct_1x2": 3}
        msg = format_daily_summary(stats)
        assert "5" in msg
        assert "Brier" not in msg

    def test_zero_matches(self):
        stats = {"total_matches": 0, "correct_1x2": 0}
        msg = format_daily_summary(stats)
        assert "0%" in msg


class TestFormatTicketResult:
    """Tests for format_ticket_result."""

    def test_winning_ticket(self):
        picks = [
            {"match": "PSG - Lyon", "result": "1-0", "correct": True},
            {"match": "OM - Nice", "result": "2-1", "correct": True},
        ]
        msg = format_ticket_result("Safe", picks, won=True, stake=10, gain=25)
        assert "TICKET SAFE" in msg
        assert "✅" in msg
        assert "+25.00€" in msg

    def test_losing_ticket(self):
        picks = [
            {"match": "PSG - Lyon", "result": "0-1", "correct": False},
        ]
        msg = format_ticket_result("Fun", picks, won=False, stake=10, gain=-10)
        assert "❌" in msg
        assert "TICKET FUN" in msg


# ═══════════════════════════════════════════════════════════════════
#  SEND FUNCTIONS (MOCKED HTTP)
# ═══════════════════════════════════════════════════════════════════


class TestSendTelegram:
    """Tests for send_telegram (HTTP is mocked)."""

    def test_returns_false_without_config(self):
        result = send_telegram("test", chat_id=None, token=None)
        assert result is False

    @patch("notifications.requests.post")
    def test_sends_successfully(self, mock_post: MagicMock):
        mock_post.return_value = MagicMock(status_code=200)
        result = send_telegram("Hello", chat_id="123", token="tok")
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "123" in str(call_kwargs)

    @patch("notifications.requests.post")
    def test_handles_http_error(self, mock_post: MagicMock):
        mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")
        result = send_telegram("Hello", chat_id="123", token="tok")
        assert result is False

    @patch("notifications.requests.post")
    def test_handles_network_error(self, mock_post: MagicMock):
        import requests

        mock_post.side_effect = requests.ConnectionError("fail")
        result = send_telegram("Hello", chat_id="123", token="tok")
        assert result is False


class TestSendDiscord:
    """Tests for send_discord (HTTP is mocked)."""

    def test_returns_false_without_config(self):
        result = send_discord("test", webhook_url=None)
        assert result is False

    @patch("notifications.requests.post")
    def test_sends_successfully(self, mock_post: MagicMock):
        mock_post.return_value = MagicMock(status_code=204)
        result = send_discord("Hello", webhook_url="https://discord.com/api/webhooks/test")
        assert result is True

    @patch("notifications.requests.post")
    def test_handles_error(self, mock_post: MagicMock):
        mock_post.return_value = MagicMock(status_code=400, text="Bad Request")
        result = send_discord("Hello", webhook_url="https://discord.com/api/webhooks/test")
        assert result is False
