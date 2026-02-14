"""
Tests unitaires pour models/ab_testing.py — Comparaison de modèles.

Les appels Supabase sont mockés.
"""

from unittest.mock import MagicMock, patch

from models.ab_testing import get_ab_report, record_prediction


class TestRecordPrediction:
    """Tests for record_prediction."""

    @patch("models.ab_testing.supabase")
    def test_records_home_favorite(self, mock_sb: MagicMock):
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"fixture_api_id": 123, "model_version": "v3", "predicted_result": "H"}
        ]
        result = record_prediction(123, "v3", proba_home=65, proba_draw=20, proba_away=15)
        assert result["predicted_result"] == "H"

    @patch("models.ab_testing.supabase")
    def test_records_away_favorite(self, mock_sb: MagicMock):
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"fixture_api_id": 456, "model_version": "v4", "predicted_result": "A"}
        ]
        result = record_prediction(456, "v4", proba_home=20, proba_draw=25, proba_away=55)
        assert result["predicted_result"] == "A"

    @patch("models.ab_testing.supabase")
    def test_records_draw_favorite(self, mock_sb: MagicMock):
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"fixture_api_id": 789, "model_version": "v3", "predicted_result": "D"}
        ]
        result = record_prediction(789, "v3", proba_home=30, proba_draw=40, proba_away=30)
        assert result["predicted_result"] == "D"

    @patch("models.ab_testing.supabase")
    def test_handles_error(self, mock_sb: MagicMock):
        mock_sb.table.return_value.upsert.side_effect = Exception("DB error")
        result = record_prediction(123, "v3", 50, 25, 25)
        assert "error" in result


class TestGetAbReport:
    """Tests for get_ab_report."""

    @patch("models.ab_testing.supabase")
    def test_empty_data(self, mock_sb: MagicMock):
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = []
        report = get_ab_report()
        assert report == {}

    @patch("models.ab_testing.supabase")
    def test_report_with_two_models(self, mock_sb: MagicMock):
        mock_data = [
            # Model v3
            {"model_version": "v3", "correct": True, "brier_score": 0.15, "actual_result": "H"},
            {"model_version": "v3", "correct": True, "brier_score": 0.10, "actual_result": "A"},
            {"model_version": "v3", "correct": False, "brier_score": 0.45, "actual_result": "D"},
            # Model v4 — better
            {"model_version": "v4", "correct": True, "brier_score": 0.08, "actual_result": "H"},
            {"model_version": "v4", "correct": True, "brier_score": 0.05, "actual_result": "A"},
            {"model_version": "v4", "correct": True, "brier_score": 0.12, "actual_result": "D"},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = mock_data

        report = get_ab_report()
        assert "v3" in report
        assert "v4" in report
        assert report["v3"]["total"] == 3
        assert report["v4"]["total"] == 3
        assert report["v4"]["accuracy"] > report["v3"]["accuracy"]
        assert report["v4"]["avg_brier"] < report["v3"]["avg_brier"]
        assert report.get("_best_model") == "v4"

    @patch("models.ab_testing.supabase")
    def test_report_single_model(self, mock_sb: MagicMock):
        mock_data = [
            {"model_version": "v3", "correct": True, "brier_score": 0.15, "actual_result": "H"},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value.data = mock_data

        report = get_ab_report()
        assert "v3" in report
        assert "_best_model" not in report  # Only one model, no comparison
