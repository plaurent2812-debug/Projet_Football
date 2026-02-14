from __future__ import annotations

"""
Tests d'intégration pour brain.py — fonctions avec mocks Supabase & données enrichies.

Couvre :
  - _format_injuries (pure)
  - build_prompt (données injectées)
  - blend_predictions avec prédictions ML
  - get_matches_to_predict avec mock Supabase
  - extract_json cas limites supplémentaires
"""
import json
from unittest.mock import MagicMock, patch

from brain import (
    _format_injuries,
    blend_predictions,
    build_prompt,
    extract_json,
    get_matches_to_predict,
)

# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def _sample_fixture() -> dict:
    return {
        "id": 1,
        "home_team": "Paris SG",
        "away_team": "Marseille",
        "league_id": 61,
        "date": "2026-02-15",
    }


def _sample_stats(
    *,
    home: int = 50,
    draw: int = 30,
    away: int = 20,
    btts: int = 55,
    o25: int = 60,
) -> dict:
    return {
        "xg_home": 1.65,
        "xg_away": 1.10,
        "proba_home": home,
        "proba_draw": draw,
        "proba_away": away,
        "proba_btts": btts,
        "proba_over_25": o25,
        "proba_over_05": 95,
        "proba_over_15": 78,
        "proba_over_35": 30,
        "proba_penalty": 28,
        "correct_score": "2-1",
        "proba_correct_score": 11,
        "recommended_bet": "Victoire Domicile",
        "confidence_score": 7,
        "context": {
            "elo_home": 1620,
            "elo_away": 1480,
            "form_home": "WWDWW",
            "form_away": "LDWLL",
            "rest_days_home": 5,
            "rest_days_away": 3,
            "congestion_home": 6,
            "congestion_away": 8,
            "stakes_home": "title_race",
            "stakes_away": "midtable",
            "injuries_home_details": [],
            "injuries_away_details": [],
        },
    }


def _sample_ai(
    *,
    home: int = 55,
    draw: int = 25,
    away: int = 20,
    btts: int = 50,
    o25: int = 55,
) -> dict:
    return {
        "proba_home": home,
        "proba_draw": draw,
        "proba_away": away,
        "proba_btts": btts,
        "proba_over_2_5": o25,
        "analysis_text": "Analyse narrative test.",
        "recommended_bet": "BTTS Oui",
        "confidence_score": 6,
        "likely_scorer": "Mbappé",
    }


# ═══════════════════════════════════════════════════════════════════
#  _format_injuries  (pure – pas de mock)
# ═══════════════════════════════════════════════════════════════════


class TestFormatInjuries:
    """Tests du formattage de la liste de blessures."""

    def test_empty_returns_no_absence(self):
        result = _format_injuries("Domicile", [])
        assert "Aucune absence connue" in result
        assert result.startswith("Domicile")

    def test_single_injury_basic(self):
        details = [
            {
                "player_name": "Neymar",
                "position": "ATT",
                "reason": "Genou",
                "impact": "high",
                "goals": 0,
                "assists": 0,
            }
        ]
        result = _format_injuries("Domicile", details)
        assert "Neymar" in result
        assert "ATT" in result
        assert "HIGH" in result

    def test_injury_with_goals_and_assists(self):
        details = [
            {
                "player_name": "Mbappé",
                "position": "ATT",
                "reason": "Cuisse",
                "impact": "critical",
                "goals": 12,
                "assists": 5,
            }
        ]
        result = _format_injuries("Domicile", details)
        assert "12 buts" in result
        assert "5 passes dé." in result

    def test_injury_starter_flag(self):
        details = [
            {
                "player_name": "Marquinhos",
                "position": "DEF",
                "reason": "Suspension",
                "impact": "high",
                "goals": 2,
                "assists": 0,
                "is_starter": True,
            }
        ]
        result = _format_injuries("Domicile", details)
        assert "TITULAIRE" in result

    def test_multiple_injuries(self):
        details = [
            {
                "player_name": "A",
                "position": "DEF",
                "reason": "X",
                "impact": "low",
                "goals": 0,
                "assists": 0,
            },
            {
                "player_name": "B",
                "position": "MIL",
                "reason": "Y",
                "impact": "medium",
                "goals": 0,
                "assists": 0,
            },
        ]
        result = _format_injuries("Extérieur", details)
        assert "A" in result
        assert "B" in result
        assert result.startswith("Extérieur absents")

    def test_missing_fields_use_defaults(self):
        details = [{}]  # all keys missing
        result = _format_injuries("Domicile", details)
        # Defaults to "?"
        assert "?" in result


# ═══════════════════════════════════════════════════════════════════
#  build_prompt
# ═══════════════════════════════════════════════════════════════════


class TestBuildPrompt:
    """Tests de la construction du prompt Claude."""

    def test_returns_two_strings(self):
        sys_p, usr_p = build_prompt(_sample_fixture(), _sample_stats(), None)
        assert isinstance(sys_p, str)
        assert isinstance(usr_p, str)

    def test_contains_team_names(self):
        _, usr = build_prompt(_sample_fixture(), _sample_stats(), None)
        assert "Paris SG" in usr
        assert "Marseille" in usr

    def test_contains_xg_values(self):
        _, usr = build_prompt(_sample_fixture(), _sample_stats(), None)
        assert "1.65" in usr
        assert "1.1" in usr

    def test_contains_elo(self):
        _, usr = build_prompt(_sample_fixture(), _sample_stats(), None)
        assert "1620" in usr
        assert "1480" in usr

    def test_h2h_section_present_when_provided(self):
        stats = _sample_stats()
        stats["context"]["h2h"] = {
            "total_matches": 10,
            "team_a_wins": 6,
            "draws": 2,
            "team_b_wins": 2,
        }
        _, usr = build_prompt(_sample_fixture(), stats, None)
        assert "Confrontations directes" in usr

    def test_h2h_section_absent_when_missing(self):
        _, usr = build_prompt(_sample_fixture(), _sample_stats(), None)
        assert "Confrontations directes" not in usr

    def test_scorers_section_present(self):
        scorers = {
            "home_scorers": [
                {
                    "name": "Mbappé",
                    "position": "ATT",
                    "goals_90": 0.8,
                    "total_goals": 18,
                    "synergy": None,
                    "penalty_taker": True,
                },
            ],
            "away_scorers": [],
        }
        _, usr = build_prompt(_sample_fixture(), _sample_stats(), scorers)
        assert "Mbappé" in usr
        assert "Tireur de pen." in usr

    def test_system_prompt_requests_json(self):
        sys_p, _ = build_prompt(_sample_fixture(), _sample_stats(), None)
        assert "JSON" in sys_p

    def test_weather_section(self):
        stats = _sample_stats()
        stats["context"]["weather"] = {
            "description": "Pluie légère",
            "temp": 8,
            "wind_speed": 12,
            "rain_mm": 3,
        }
        _, usr = build_prompt(_sample_fixture(), stats, None)
        assert "Météo" in usr
        assert "Pluie légère" in usr

    def test_referee_section(self):
        stats = _sample_stats()
        stats["context"]["referee"] = {
            "avg_yellows": 4.2,
            "avg_penalties": 0.3,
            "penalty_bias": 1.5,
        }
        _, usr = build_prompt(_sample_fixture(), stats, None)
        assert "Arbitre" in usr
        assert "GÉNÉREUX" in usr

    def test_market_section(self):
        stats = _sample_stats()
        stats["context"]["market"] = {
            "market_home": 52,
            "market_draw": 28,
            "market_away": 20,
        }
        _, usr = build_prompt(_sample_fixture(), stats, None)
        assert "Cotes du marché" in usr


# ═══════════════════════════════════════════════════════════════════
#  blend_predictions — avec données ML
# ═══════════════════════════════════════════════════════════════════


class TestBlendWithML:
    """Tests de la fusion quand des prédictions ML sont présentes."""

    def test_ml_keys_do_not_break_blend(self):
        """blend_predictions ignore extra ML keys gracefully."""
        stats = _sample_stats()
        stats["ml_home"] = 60
        stats["ml_draw"] = 22
        stats["ml_away"] = 18
        result = blend_predictions(stats, _sample_ai())
        total = result["proba_home"] + result["proba_draw"] + result["proba_away"]
        assert total == 100

    def test_blend_with_ai_none_and_ml_keys(self):
        stats = _sample_stats(home=60, draw=25, away=15)
        stats["ml_home"] = 58
        result = blend_predictions(stats, None)
        # Without AI, stats are used as-is for the blend
        assert result["proba_home"] == 60
        assert result["proba_draw"] == 25
        assert result["proba_away"] == 15

    def test_model_version_is_hybrid_v3(self):
        result = blend_predictions(_sample_stats(), _sample_ai())
        assert result["model_version"] == "hybrid_v3"

    def test_no_ai_analysis_fallback_message(self):
        result = blend_predictions(_sample_stats(), None)
        assert (
            "stats uniquement" in result["analysis_text"].lower() or "xG" in result["analysis_text"]
        )

    def test_confidence_score_from_ai(self):
        ai = _sample_ai()
        ai["confidence_score"] = 9
        result = blend_predictions(_sample_stats(), ai)
        assert result["confidence_score"] == 9

    def test_likely_scorer_from_ai(self):
        result = blend_predictions(_sample_stats(), _sample_ai())
        assert result["likely_scorer"] == "Mbappé"


# ═══════════════════════════════════════════════════════════════════
#  get_matches_to_predict  (mock Supabase)
# ═══════════════════════════════════════════════════════════════════


class TestGetMatchesToPredict:
    """Tests de la récupération des matchs via Supabase mockée."""

    @patch("brain.supabase")
    def test_returns_fixtures_without_predictions(self, mock_sb):
        fixtures = [{"id": 10, "home_team": "PSG", "away_team": "OL", "status": "NS"}]
        # fixtures query
        fix_query = MagicMock()
        fix_query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=fixtures
        )
        # predictions query — no existing prediction
        pred_query = MagicMock()
        pred_query.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        mock_sb.table.side_effect = lambda t: fix_query if t == "fixtures" else pred_query

        result = get_matches_to_predict()
        assert len(result) == 1
        assert result[0]["id"] == 10

    @patch("brain.supabase")
    def test_skips_fixtures_with_hybrid_v3(self, mock_sb):
        fixtures = [{"id": 10, "status": "NS"}]
        existing_preds = [{"id": 99, "model_version": "hybrid_v3"}]

        fix_query = MagicMock()
        fix_query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=fixtures
        )
        pred_query = MagicMock()
        pred_query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=existing_preds
        )

        mock_sb.table.side_effect = lambda t: fix_query if t == "fixtures" else pred_query

        result = get_matches_to_predict()
        assert len(result) == 0

    @patch("brain.supabase")
    def test_includes_fixtures_with_old_model_version(self, mock_sb):
        fixtures = [{"id": 10, "status": "NS"}]
        existing_preds = [{"id": 99, "model_version": "old_v0"}]

        fix_query = MagicMock()
        fix_query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=fixtures
        )
        pred_query = MagicMock()
        pred_query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=existing_preds
        )

        mock_sb.table.side_effect = lambda t: fix_query if t == "fixtures" else pred_query

        result = get_matches_to_predict()
        assert len(result) == 1

    @patch("brain.supabase")
    def test_empty_fixtures_returns_empty(self, mock_sb):
        fix_query = MagicMock()
        fix_query.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        mock_sb.table.side_effect = lambda t: fix_query

        result = get_matches_to_predict()
        assert result == []

    @patch("brain.supabase")
    def test_multiple_fixtures_mixed(self, mock_sb):
        """Two fixtures: one already predicted (hybrid_v3), one not."""
        fixtures = [
            {"id": 10, "status": "NS"},
            {"id": 20, "status": "NS"},
        ]

        fix_query = MagicMock()
        fix_query.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=fixtures
        )

        # Return different prediction data depending on fixture_id
        pred_results = {
            10: [{"id": 99, "model_version": "hybrid_v3"}],
            20: [],
        }

        def make_pred_chain(table_name):
            if table_name == "fixtures":
                return fix_query
            chain = MagicMock()

            def eq_side_effect(field, value):
                result_mock = MagicMock()
                result_mock.execute.return_value = MagicMock(data=pred_results.get(value, []))
                return result_mock

            chain.select.return_value.eq = eq_side_effect
            return chain

        mock_sb.table.side_effect = make_pred_chain

        result = get_matches_to_predict()
        assert len(result) == 1
        assert result[0]["id"] == 20


# ═══════════════════════════════════════════════════════════════════
#  extract_json — cas limites supplémentaires
# ═══════════════════════════════════════════════════════════════════


class TestExtractJsonEdgeCases:
    """Tests additionnels de l'extraction JSON."""

    def test_json_with_trailing_comma_fails(self):
        """Trailing commas are invalid JSON."""
        text = '{"a": 1, "b": 2,}'
        result = extract_json(text)
        # Python's json.loads rejects trailing commas
        assert result is None

    def test_multiline_json_block(self):
        text = """```json
{
    "proba_home": 45,
    "proba_draw": 30,
    "proba_away": 25
}
```"""
        result = extract_json(text)
        assert result is not None
        assert result["proba_home"] == 45

    def test_json_with_unicode(self):
        text = '{"team": "Zürich FC", "emoji": "⚽"}'
        result = extract_json(text)
        assert result is not None
        assert result["team"] == "Zürich FC"

    def test_multiple_json_blocks_greedy_mismatch_returns_none(self):
        """Greedy regex spans from first { to last }, producing invalid JSON."""
        text = 'Avant {"a": 1} milieu {"b": 2} après'
        result = extract_json(text)
        # The greedy regex captures '{"a": 1} milieu {"b": 2}' which is
        # not valid JSON, so extract_json correctly returns None.
        assert result is None

    def test_json_with_newlines_in_string(self):
        text = '{"text": "line1\\nline2"}'
        result = extract_json(text)
        assert result is not None
        assert "line1" in result["text"]

    def test_json_with_integer_values(self):
        text = '{"a": 0, "b": -5, "c": 100}'
        result = extract_json(text)
        assert result is not None
        assert result["b"] == -5

    def test_deeply_nested_json(self):
        obj = {"level1": {"level2": {"level3": {"value": 42}}}}
        text = json.dumps(obj)
        result = extract_json(text)
        assert result is not None
        assert result["level1"]["level2"]["level3"]["value"] == 42
