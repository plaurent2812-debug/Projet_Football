"""
Tests d'intégration pour training/evaluate.py —
évaluation des prédictions vs résultats réels.

Toutes les interactions Supabase sont mockées.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# We patch supabase at the module level where it is imported
SUPABASE_PATCH = "training.evaluate.supabase"


# ═══════════════════════════════════════════════════════════════════
#  HELPERS : construction de données de test
# ═══════════════════════════════════════════════════════════════════


def _make_fixture(
    home_goals: int = 2,
    away_goals: int = 1,
    *,
    fixture_id: int = 100,
    api_fixture_id: int = 9999,
    home_team: str = "Paris Saint Germain",
    away_team: str = "Olympique De Marseille",
    league_id: int = 61,
) -> dict:
    """Build a minimal finished-fixture dict."""
    return {
        "id": fixture_id,
        "api_fixture_id": api_fixture_id,
        "home_team": home_team,
        "away_team": away_team,
        "league_id": league_id,
        "status": "FT",
        "home_goals": home_goals,
        "away_goals": away_goals,
    }


def _make_prediction(
    *,
    prediction_id: int = 10,
    proba_home: int = 55,
    proba_draw: int = 25,
    proba_away: int = 20,
    proba_btts: int = 60,
    proba_over_05: int = 95,
    proba_over_15: int = 80,
    proba_over_2_5: int = 58,
    proba_penalty: int = 25,
    correct_score: str = "2-1",
    recommended_bet: str = "Victoire Domicile",
    confidence_score: int = 7,
    likely_scorer: str = "Kylian Mbappé",
    model_version: str = "hybrid_v3_ml",
) -> dict:
    """Build a minimal prediction dict."""
    return {
        "id": prediction_id,
        "fixture_id": 100,
        "proba_home": proba_home,
        "proba_draw": proba_draw,
        "proba_away": proba_away,
        "proba_btts": proba_btts,
        "proba_over_05": proba_over_05,
        "proba_over_15": proba_over_15,
        "proba_over_2_5": proba_over_2_5,
        "proba_penalty": proba_penalty,
        "correct_score": correct_score,
        "recommended_bet": recommended_bet,
        "confidence_score": confidence_score,
        "likely_scorer": likely_scorer,
        "model_version": model_version,
    }


def _mock_supabase_no_events():
    """Return a mock supabase where match_events returns no rows."""
    mock_sb = MagicMock()
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])
    mock_sb.table.return_value = mock_query
    return mock_sb


def _mock_supabase_with_events(penalty: bool = False, scorers: list[str] | None = None):
    """Return a mock supabase with configurable event data.

    Because _check_penalty and _get_scorers both call supabase.table("match_events")
    we need side_effect to return different query objects for successive calls.
    """
    scorers = scorers or []

    # Penalty query object
    pen_query = MagicMock()
    pen_query.select.return_value = pen_query
    pen_query.eq.return_value = pen_query
    pen_query.limit.return_value = pen_query
    pen_data = [{"id": 1}] if penalty else []
    pen_query.execute.return_value = MagicMock(data=pen_data)

    # Scorers query object
    scorer_query = MagicMock()
    scorer_query.select.return_value = scorer_query
    scorer_query.eq.return_value = scorer_query
    scorer_query.limit.return_value = scorer_query
    scorer_data = [{"player_name": s} for s in scorers]
    scorer_query.execute.return_value = MagicMock(data=scorer_data)

    mock_sb = MagicMock()
    # First call → penalty, second call → scorers
    mock_sb.table.side_effect = [pen_query, scorer_query]
    return mock_sb


# ═══════════════════════════════════════════════════════════════════
#  TEST _check_penalty
# ═══════════════════════════════════════════════════════════════════


class TestCheckPenalty:
    """Tests for _check_penalty helper."""

    @patch(SUPABASE_PATCH)
    def test_penalty_found(self, mock_sb):
        """Should return True when a Penalty event exists."""
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = MagicMock(data=[{"id": 42}])
        mock_sb.table.return_value = query

        from training.evaluate import _check_penalty

        assert _check_penalty(9999) is True

    @patch(SUPABASE_PATCH)
    def test_penalty_not_found(self, mock_sb):
        """Should return False when no Penalty event exists."""
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = MagicMock(data=[])
        mock_sb.table.return_value = query

        from training.evaluate import _check_penalty

        assert _check_penalty(9999) is False

    def test_penalty_none_fixture_id(self):
        """Should return False immediately when fixture_api_id is None."""
        from training.evaluate import _check_penalty

        assert _check_penalty(None) is False

    @patch(SUPABASE_PATCH)
    def test_penalty_exception_returns_false(self, mock_sb):
        """Should return False if supabase raises an exception."""
        mock_sb.table.side_effect = Exception("DB error")

        from training.evaluate import _check_penalty

        assert _check_penalty(9999) is False


# ═══════════════════════════════════════════════════════════════════
#  TEST _get_scorers
# ═══════════════════════════════════════════════════════════════════


class TestGetScorers:
    """Tests for _get_scorers helper."""

    @patch(SUPABASE_PATCH)
    def test_returns_scorer_names(self, mock_sb):
        """Should return a list of unique scorer names."""
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(
            data=[
                {"player_name": "Mbappé"},
                {"player_name": "Dembélé"},
                {"player_name": "Mbappé"},  # duplicate
            ]
        )
        mock_sb.table.return_value = query

        from training.evaluate import _get_scorers

        result = _get_scorers(9999)
        assert set(result) == {"Mbappé", "Dembélé"}

    @patch(SUPABASE_PATCH)
    def test_returns_empty_for_no_goals(self, mock_sb):
        """Should return empty list when no Goal events exist."""
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock(data=[])
        mock_sb.table.return_value = query

        from training.evaluate import _get_scorers

        assert _get_scorers(9999) == []

    def test_returns_empty_for_none_fixture_id(self):
        """Should return [] immediately when fixture_api_id is None."""
        from training.evaluate import _get_scorers

        assert _get_scorers(None) == []

    @patch(SUPABASE_PATCH)
    def test_exception_returns_empty(self, mock_sb):
        """Should return [] on exception."""
        mock_sb.table.side_effect = Exception("DB error")

        from training.evaluate import _get_scorers

        assert _get_scorers(9999) == []


# ═══════════════════════════════════════════════════════════════════
#  TEST _generate_post_analysis
# ═══════════════════════════════════════════════════════════════════


class TestGeneratePostAnalysis:
    """Tests for _generate_post_analysis narrative builder."""

    def test_correct_result_message(self):
        from training.evaluate import _generate_post_analysis

        fixture = _make_fixture(2, 1)
        prediction = _make_prediction()
        text = _generate_post_analysis(
            fixture,
            prediction,
            "H",
            2,
            1,
            result_ok=True,
            btts_ok=True,
            over_ok=True,
            scorer_ok=False,
            had_penalty=False,
        )
        assert "Score final" in text
        assert "2-1" in text
        assert "✅ Résultat 1X2 correct" in text

    def test_incorrect_result_draw(self):
        from training.evaluate import _generate_post_analysis

        fixture = _make_fixture(1, 1)
        prediction = _make_prediction(proba_home=55, proba_draw=25, proba_away=20)
        text = _generate_post_analysis(
            fixture,
            prediction,
            "D",
            1,
            1,
            result_ok=False,
            btts_ok=True,
            over_ok=False,
            scorer_ok=False,
            had_penalty=False,
        )
        assert "❌" in text
        assert "Nul non anticipé" in text

    def test_incorrect_result_away_win(self):
        from training.evaluate import _generate_post_analysis

        fixture = _make_fixture(0, 2)
        prediction = _make_prediction(proba_home=55, proba_draw=25, proba_away=20)
        text = _generate_post_analysis(
            fixture,
            prediction,
            "A",
            0,
            2,
            result_ok=False,
            btts_ok=False,
            over_ok=False,
            scorer_ok=False,
            had_penalty=False,
        )
        assert "❌" in text
        assert "Marseille" in text  # away team name

    def test_scorer_correct_message(self):
        from training.evaluate import _generate_post_analysis

        fixture = _make_fixture(2, 0)
        prediction = _make_prediction(likely_scorer="Mbappé")
        text = _generate_post_analysis(
            fixture,
            prediction,
            "H",
            2,
            0,
            result_ok=True,
            btts_ok=True,
            over_ok=True,
            scorer_ok=True,
            had_penalty=False,
        )
        assert "✅ Buteur correct" in text
        assert "Mbappé" in text

    def test_penalty_mentioned(self):
        from training.evaluate import _generate_post_analysis

        fixture = _make_fixture(1, 0)
        prediction = _make_prediction(proba_penalty=35)
        text = _generate_post_analysis(
            fixture,
            prediction,
            "H",
            1,
            0,
            result_ok=True,
            btts_ok=True,
            over_ok=False,
            scorer_ok=False,
            had_penalty=True,
        )
        assert "Penalty dans le match" in text
        assert "35%" in text

    def test_high_confidence_wrong_message(self):
        """High confidence + wrong result should produce bias warning."""
        from training.evaluate import _generate_post_analysis

        fixture = _make_fixture(0, 1)
        prediction = _make_prediction(
            proba_home=70,
            proba_draw=15,
            proba_away=15,
            confidence_score=8,
        )
        text = _generate_post_analysis(
            fixture,
            prediction,
            "A",
            0,
            1,
            result_ok=False,
            btts_ok=False,
            over_ok=False,
            scorer_ok=False,
            had_penalty=False,
        )
        assert "biais possible" in text.lower() or "confiant" in text.lower()


# ═══════════════════════════════════════════════════════════════════
#  TEST evaluate_match — SCÉNARIOS COMPLETS
# ═══════════════════════════════════════════════════════════════════


class TestEvaluateMatch:
    """Integration-level tests for evaluate_match with mocked Supabase."""

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_home_win_predicted_correctly(self, _mock_sb):
        """Home win predicted (highest proba_home) and actual H → result_1x2_ok True."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(3, 1)
        prediction = _make_prediction(proba_home=60, proba_draw=20, proba_away=20)
        result = evaluate_match(fixture, prediction)

        assert result["actual_result"] == "H"
        assert result["result_1x2_ok"] is True
        assert result["actual_home_goals"] == 3
        assert result["actual_away_goals"] == 1
        assert result["fixture_id"] == 100

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_draw_predicted_wrong(self, _mock_sb):
        """Predict home win but actual result is draw."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(1, 1)
        prediction = _make_prediction(proba_home=50, proba_draw=25, proba_away=25)
        result = evaluate_match(fixture, prediction)

        assert result["actual_result"] == "D"
        assert result["result_1x2_ok"] is False

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_away_win_predicted_correctly(self, _mock_sb):
        """Away win predicted and correct."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(0, 2)
        prediction = _make_prediction(proba_home=15, proba_draw=25, proba_away=60)
        result = evaluate_match(fixture, prediction)

        assert result["actual_result"] == "A"
        assert result["result_1x2_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_btts_correct_both_score(self, _mock_sb):
        """BTTS predicted ≥50% and both teams scored → btts_ok True."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(2, 1)
        prediction = _make_prediction(proba_btts=65)
        result = evaluate_match(fixture, prediction)

        assert result["actual_btts"] is True
        assert result["btts_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_btts_incorrect_one_team_blanked(self, _mock_sb):
        """BTTS predicted ≥50% but one team didn't score → btts_ok False."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(2, 0)
        prediction = _make_prediction(proba_btts=70)
        result = evaluate_match(fixture, prediction)

        assert result["actual_btts"] is False
        assert result["btts_ok"] is False

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_correct_score_hit(self, _mock_sb):
        """Predicted correct score matches actual score."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(2, 1)
        prediction = _make_prediction(correct_score="2-1")
        result = evaluate_match(fixture, prediction)

        assert result["actual_correct_score"] is True
        assert result["correct_score_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_correct_score_miss(self, _mock_sb):
        """Predicted correct score doesn't match actual score."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(1, 0)
        prediction = _make_prediction(correct_score="2-1")
        result = evaluate_match(fixture, prediction)

        assert result["actual_correct_score"] is False

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_over_under_thresholds(self, _mock_sb):
        """Check over 0.5 / 1.5 / 2.5 flags with a 3-1 scoreline."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(3, 1)  # 4 goals
        prediction = _make_prediction(
            proba_over_05=95,
            proba_over_15=80,
            proba_over_2_5=60,
        )
        result = evaluate_match(fixture, prediction)

        assert result["actual_over_05"] is True
        assert result["actual_over_15"] is True
        assert result["actual_over_25"] is True
        assert result["over_05_ok"] is True
        assert result["over_15_ok"] is True
        assert result["over_25_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_goalless_draw_overs(self, _mock_sb):
        """0-0 draw: all overs should be False."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(0, 0)
        prediction = _make_prediction(
            proba_over_05=30,
            proba_over_15=20,
            proba_over_2_5=10,
            proba_btts=30,
        )
        result = evaluate_match(fixture, prediction)

        assert result["actual_over_05"] is False
        assert result["actual_over_15"] is False
        assert result["actual_over_25"] is False
        assert result["actual_btts"] is False
        # predictions were <50 for overs → correct
        assert result["over_05_ok"] is True
        assert result["over_15_ok"] is True
        assert result["over_25_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_brier_score_perfect_prediction(self, _mock_sb):
        """Brier score should be low for a confident correct prediction."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(3, 0)
        prediction = _make_prediction(proba_home=90, proba_draw=5, proba_away=5)
        result = evaluate_match(fixture, prediction)

        assert result["brier_score_1x2"] < 0.05

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_brier_score_bad_prediction(self, _mock_sb):
        """Brier score should be high for a confident wrong prediction."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(0, 3)  # away win
        prediction = _make_prediction(proba_home=90, proba_draw=5, proba_away=5)
        result = evaluate_match(fixture, prediction)

        assert result["brier_score_1x2"] > 0.25

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_log_loss_correct_prediction(self, _mock_sb):
        """Log loss should be low when prediction matches outcome."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(2, 0)
        prediction = _make_prediction(proba_home=80, proba_draw=10, proba_away=10)
        result = evaluate_match(fixture, prediction)

        assert result["log_loss"] < 0.5

    @patch(SUPABASE_PATCH)
    def test_scorer_ok_with_matching_name(self, mock_sb):
        """Scorer is correct when predicted name is found in scorers list."""
        # Set up the two successive table calls (penalty then scorers)
        pen_query = MagicMock()
        pen_query.select.return_value = pen_query
        pen_query.eq.return_value = pen_query
        pen_query.limit.return_value = pen_query
        pen_query.execute.return_value = MagicMock(data=[])

        scorer_query = MagicMock()
        scorer_query.select.return_value = scorer_query
        scorer_query.eq.return_value = scorer_query
        scorer_query.execute.return_value = MagicMock(
            data=[
                {"player_name": "K. Mbappé"},
                {"player_name": "O. Dembélé"},
            ]
        )

        mock_sb.table.side_effect = [pen_query, scorer_query]

        from training.evaluate import evaluate_match

        fixture = _make_fixture(2, 0)
        prediction = _make_prediction(likely_scorer="Mbappé")
        result = evaluate_match(fixture, prediction)

        assert result["scorer_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_penalty_ok_predicted_low_no_penalty(self, _mock_sb):
        """Penalty proba <30 and no penalty → penalty_ok True."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(1, 0)
        prediction = _make_prediction(proba_penalty=10)
        result = evaluate_match(fixture, prediction)

        assert result["actual_had_penalty"] is False
        assert result["penalty_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_result_contains_all_expected_keys(self, _mock_sb):
        """The returned dict should contain all expected fields."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(1, 1)
        prediction = _make_prediction()
        result = evaluate_match(fixture, prediction)

        expected_keys = {
            "fixture_id",
            "prediction_id",
            "league_id",
            "season",
            "pred_home",
            "pred_draw",
            "pred_away",
            "pred_btts",
            "pred_over_05",
            "pred_over_15",
            "pred_over_25",
            "pred_correct_score",
            "pred_likely_scorer",
            "pred_penalty",
            "pred_recommended",
            "pred_confidence",
            "model_version",
            "actual_home_goals",
            "actual_away_goals",
            "actual_result",
            "actual_btts",
            "actual_over_05",
            "actual_over_15",
            "actual_over_25",
            "actual_correct_score",
            "actual_had_penalty",
            "actual_scorers",
            "result_1x2_ok",
            "btts_ok",
            "over_05_ok",
            "over_15_ok",
            "over_25_ok",
            "correct_score_ok",
            "penalty_ok",
            "scorer_ok",
            "recommended_bet_ok",
            "post_analysis",
            "brier_score_1x2",
            "log_loss",
        }
        assert expected_keys.issubset(result.keys())

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_recommended_bet_ok_victoire_domicile(self, _mock_sb):
        """recommended_bet_ok should be True when 'Victoire Domicile' and H wins."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(2, 0)
        prediction = _make_prediction(recommended_bet="Victoire Domicile")
        result = evaluate_match(fixture, prediction)

        assert result["recommended_bet_ok"] is True

    @patch(SUPABASE_PATCH, new_callable=lambda: _mock_supabase_no_events)
    def test_post_analysis_is_string(self, _mock_sb):
        """post_analysis should always be a non-empty string."""
        from training.evaluate import evaluate_match

        fixture = _make_fixture(1, 2)
        prediction = _make_prediction()
        result = evaluate_match(fixture, prediction)

        assert isinstance(result["post_analysis"], str)
        assert len(result["post_analysis"]) > 0
