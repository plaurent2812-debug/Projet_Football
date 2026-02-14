"""
Tests unitaires pour models/dataclasses.py —
vérification des structures de données typées du projet Football IA.
"""

from __future__ import annotations

from models.dataclasses import (
    EloRating,
    EvaluationResult,
    MatchPrediction,
    PlayerInjuryImpact,
    RefereeImpact,
    ScorerPrediction,
    TeamStrength,
)

# ═══════════════════════════════════════════════════════════════════
#  TEST MatchPrediction
# ═══════════════════════════════════════════════════════════════════


class TestMatchPrediction:
    """Tests for the MatchPrediction dataclass."""

    def _required_fields(self) -> dict:
        """Return the minimal set of required fields."""
        return {
            "proba_home": 55,
            "proba_draw": 25,
            "proba_away": 20,
            "proba_btts": 60,
            "proba_over_05": 95,
            "proba_over_15": 80,
            "proba_over_25": 58,
            "proba_over_35": 30,
            "proba_penalty": 28,
            "proba_dc_1x": 80,
            "proba_dc_x2": 45,
            "proba_dc_12": 75,
            "xg_home": 1.65,
            "xg_away": 1.10,
            "correct_score": "2-1",
            "proba_correct_score": 11,
            "recommended_bet": "Victoire Domicile",
            "confidence_score": 7,
            "analysis_text": "PSG favori à domicile.",
        }

    def test_create_with_required_fields(self):
        """Should create an instance with all required fields."""
        mp = MatchPrediction(**self._required_fields())
        assert mp.proba_home == 55
        assert mp.proba_draw == 25
        assert mp.proba_away == 20
        assert mp.correct_score == "2-1"

    def test_default_likely_scorer_is_none(self):
        """likely_scorer should default to None."""
        mp = MatchPrediction(**self._required_fields())
        assert mp.likely_scorer is None

    def test_default_likely_scorer_proba_is_zero(self):
        """likely_scorer_proba should default to 0."""
        mp = MatchPrediction(**self._required_fields())
        assert mp.likely_scorer_proba == 0

    def test_default_model_version(self):
        """model_version should default to 'hybrid_v1'."""
        mp = MatchPrediction(**self._required_fields())
        assert mp.model_version == "hybrid_v1"

    def test_default_context_is_empty_dict(self):
        """context should default to an empty dict (not shared across instances)."""
        mp1 = MatchPrediction(**self._required_fields())
        mp2 = MatchPrediction(**self._required_fields())
        assert mp1.context == {}
        assert mp1.context is not mp2.context  # separate instances

    def test_default_stats_json_is_empty_dict(self):
        """stats_json should default to an empty dict."""
        mp = MatchPrediction(**self._required_fields())
        assert mp.stats_json == {}

    def test_optional_fields_override(self):
        """Optional fields can be set explicitly."""
        data = {**self._required_fields(), "likely_scorer": "Mbappé", "likely_scorer_proba": 32}
        mp = MatchPrediction(**data)
        assert mp.likely_scorer == "Mbappé"
        assert mp.likely_scorer_proba == 32

    def test_create_from_dict_unpacking(self):
        """Should support **dict creation pattern."""
        data = {**self._required_fields(), "model_version": "hybrid_v4"}
        mp = MatchPrediction(**data)
        assert mp.model_version == "hybrid_v4"


# ═══════════════════════════════════════════════════════════════════
#  TEST PlayerInjuryImpact
# ═══════════════════════════════════════════════════════════════════


class TestPlayerInjuryImpact:
    """Tests for the PlayerInjuryImpact dataclass."""

    def _required_fields(self) -> dict:
        return {
            "player_name": "Marquinhos",
            "position": "Defender",
            "reason": "Knee Injury",
            "impact": "majeur",
        }

    def test_create_with_required_fields(self):
        p = PlayerInjuryImpact(**self._required_fields())
        assert p.player_name == "Marquinhos"
        assert p.position == "Defender"
        assert p.impact == "majeur"

    def test_default_numeric_fields(self):
        """Default impact_attack, impact_defense, goals, assists, etc."""
        p = PlayerInjuryImpact(**self._required_fields())
        assert p.impact_attack == 0.0
        assert p.impact_defense == 0.0
        assert p.goals == 0
        assert p.assists == 0
        assert p.rating == 6.0
        assert p.minutes == 0
        assert p.is_starter is False

    def test_override_optional_fields(self):
        data = {**self._required_fields(), "goals": 5, "is_starter": True, "rating": 7.5}
        p = PlayerInjuryImpact(**data)
        assert p.goals == 5
        assert p.is_starter is True
        assert p.rating == 7.5


# ═══════════════════════════════════════════════════════════════════
#  TEST ScorerPrediction
# ═══════════════════════════════════════════════════════════════════


class TestScorerPrediction:
    """Tests for the ScorerPrediction dataclass."""

    def _required_fields(self) -> dict:
        return {
            "player_id": 1100,
            "name": "Kylian Mbappé",
            "team": "Paris Saint Germain",
            "position": "Attacker",
            "proba": 35,
            "player_xg": 0.72,
            "raw_score": 8.5,
            "goals_per_90": 0.85,
            "total_goals": 18,
            "total_assists": 7,
        }

    def test_create_with_required_fields(self):
        sp = ScorerPrediction(**self._required_fields())
        assert sp.name == "Kylian Mbappé"
        assert sp.proba == 35
        assert sp.player_xg == 0.72

    def test_default_optional_fields(self):
        sp = ScorerPrediction(**self._required_fields())
        assert sp.penalty_taker is False
        assert sp.synergy is None
        assert sp.goals_vs == 0
        assert sp.matches_vs == 0
        assert sp.form_goals == 0
        assert sp.form_matches == 0
        assert sp.form_factor == 1.0
        assert sp.defense_factor == 1.0
        assert sp.gk_factor == 1.0
        assert sp.conversion_rate == 0.0
        assert sp.analysis == ""

    def test_override_context_fields(self):
        data = {
            **self._required_fields(),
            "penalty_taker": True,
            "synergy": "O. Dembélé",
            "goals_vs": 3,
            "form_factor": 1.2,
        }
        sp = ScorerPrediction(**data)
        assert sp.penalty_taker is True
        assert sp.synergy == "O. Dembélé"
        assert sp.goals_vs == 3
        assert sp.form_factor == 1.2


# ═══════════════════════════════════════════════════════════════════
#  TEST EloRating
# ═══════════════════════════════════════════════════════════════════


class TestEloRating:
    """Tests for the EloRating dataclass."""

    def test_create_elo_rating(self):
        elo = EloRating(
            home_elo=1650.0,
            away_elo=1520.0,
            home_proba=55,
            draw_proba=25,
            away_proba=20,
        )
        assert elo.home_elo == 1650.0
        assert elo.away_elo == 1520.0
        assert elo.home_proba + elo.draw_proba + elo.away_proba == 100

    def test_create_from_dict(self):
        data = {
            "home_elo": 1600.0,
            "away_elo": 1600.0,
            "home_proba": 40,
            "draw_proba": 30,
            "away_proba": 30,
        }
        elo = EloRating(**data)
        assert elo.home_elo == 1600.0
        assert elo.draw_proba == 30


# ═══════════════════════════════════════════════════════════════════
#  TEST TeamStrength
# ═══════════════════════════════════════════════════════════════════


class TestTeamStrength:
    """Tests for the TeamStrength dataclass."""

    def test_create_team_strength(self):
        ts = TeamStrength(
            home_attack=1.4,
            home_defense=0.7,
            away_attack=1.2,
            away_defense=0.8,
        )
        assert ts.home_attack == 1.4
        assert ts.home_defense == 0.7
        assert ts.away_attack == 1.2
        assert ts.away_defense == 0.8

    def test_create_from_dict(self):
        data = {
            "home_attack": 1.0,
            "home_defense": 1.0,
            "away_attack": 1.0,
            "away_defense": 1.0,
        }
        ts = TeamStrength(**data)
        assert ts.home_attack == 1.0


# ═══════════════════════════════════════════════════════════════════
#  TEST RefereeImpact
# ═══════════════════════════════════════════════════════════════════


class TestRefereeImpact:
    """Tests for the RefereeImpact dataclass."""

    def test_create_referee_impact(self):
        ref = RefereeImpact(
            avg_yellows=3.5,
            avg_reds=0.2,
            avg_penalties=0.3,
            avg_fouls=24.0,
            penalty_bias=1.1,
            matches=45,
        )
        assert ref.avg_yellows == 3.5
        assert ref.avg_penalties == 0.3
        assert ref.penalty_bias == 1.1
        assert ref.matches == 45

    def test_create_from_dict(self):
        data = {
            "avg_yellows": 4.0,
            "avg_reds": 0.1,
            "avg_penalties": 0.25,
            "avg_fouls": 22.0,
            "penalty_bias": 0.9,
            "matches": 30,
        }
        ref = RefereeImpact(**data)
        assert ref.avg_reds == 0.1
        assert ref.penalty_bias == 0.9


# ═══════════════════════════════════════════════════════════════════
#  TEST EvaluationResult
# ═══════════════════════════════════════════════════════════════════


class TestEvaluationResult:
    """Tests for the EvaluationResult dataclass."""

    def _required_fields(self) -> dict:
        return {
            "fixture_id": 42,
            "result_correct": True,
            "btts_correct": True,
            "over25_correct": False,
            "correct_score_hit": False,
            "scorer_correct": True,
            "penalty_correct": True,
            "recommended_bet_won": True,
        }

    def test_create_with_required_fields(self):
        ev = EvaluationResult(**self._required_fields())
        assert ev.fixture_id == 42
        assert ev.result_correct is True
        assert ev.over25_correct is False

    def test_default_optional_fields(self):
        ev = EvaluationResult(**self._required_fields())
        assert ev.brier_1x2 == 0.0
        assert ev.log_loss == 0.0
        assert ev.post_analysis == ""

    def test_override_defaults(self):
        data = {
            **self._required_fields(),
            "brier_1x2": 0.15,
            "log_loss": 0.65,
            "post_analysis": "Good prediction.",
        }
        ev = EvaluationResult(**data)
        assert ev.brier_1x2 == 0.15
        assert ev.log_loss == 0.65
        assert ev.post_analysis == "Good prediction."

    def test_create_from_dict(self):
        data = {
            "fixture_id": 99,
            "result_correct": False,
            "btts_correct": False,
            "over25_correct": True,
            "correct_score_hit": True,
            "scorer_correct": False,
            "penalty_correct": False,
            "recommended_bet_won": False,
        }
        ev = EvaluationResult(**data)
        assert ev.fixture_id == 99
        assert ev.result_correct is False
        assert ev.over25_correct is True
        assert ev.correct_score_hit is True
