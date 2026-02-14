"""
Tests unitaires pour brain.py — fonctions pures (pas d'appel API).
"""

from brain import blend_predictions, extract_json

# ═══════════════════════════════════════════════════════════════════
#  EXTRACTION JSON
# ═══════════════════════════════════════════════════════════════════


class TestExtractJson:
    """Tests de l'extraction JSON depuis la réponse Claude."""

    def test_pure_json(self):
        text = '{"proba_home": 55, "proba_draw": 25, "proba_away": 20}'
        result = extract_json(text)
        assert result is not None
        assert result["proba_home"] == 55

    def test_json_in_markdown_block(self):
        text = '```json\n{"proba_home": 55, "proba_draw": 25}\n```'
        result = extract_json(text)
        assert result is not None
        assert result["proba_home"] == 55

    def test_json_in_generic_markdown_block(self):
        text = '```\n{"proba_home": 42}\n```'
        result = extract_json(text)
        assert result is not None
        assert result["proba_home"] == 42

    def test_json_with_surrounding_text(self):
        text = 'Voici mon analyse:\n{"proba_home": 60, "proba_draw": 20, "proba_away": 20}\nFin.'
        result = extract_json(text)
        assert result is not None
        assert result["proba_home"] == 60

    def test_invalid_json_returns_none(self):
        assert extract_json("pas du json du tout") is None

    def test_empty_string_returns_none(self):
        assert extract_json("") is None

    def test_nested_json(self):
        text = '{"proba_home": 55, "context": {"form": "WWDLW"}}'
        result = extract_json(text)
        assert result is not None
        assert result["context"]["form"] == "WWDLW"

    def test_json_with_special_chars(self):
        text = '{"analysis_text": "L\'équipe est en forme. 85% de chance."}'
        result = extract_json(text)
        assert result is not None


# ═══════════════════════════════════════════════════════════════════
#  BLEND PREDICTIONS
# ═══════════════════════════════════════════════════════════════════


class TestBlendPredictions:
    """Tests de la fusion stats + IA."""

    def _make_stats(self, h=50, d=30, a=20, btts=55, o25=60):
        return {
            "proba_home": h,
            "proba_draw": d,
            "proba_away": a,
            "proba_btts": btts,
            "proba_over_25": o25,
            "proba_over_05": 95,
            "proba_over_15": 78,
            "proba_over_35": 30,
            "proba_penalty": 28,
            "correct_score": "1-1",
            "proba_correct_score": 12,
            "xg_home": 1.5,
            "xg_away": 1.1,
            "recommended_bet": "Victoire Domicile",
            "confidence_score": 7,
            "context": {},
        }

    def _make_ai(self, h=55, d=25, a=20, btts=50, o25=55):
        return {
            "proba_home": h,
            "proba_draw": d,
            "proba_away": a,
            "proba_btts": btts,
            "proba_over_2_5": o25,
            "analysis_text": "Analyse test",
            "recommended_bet": "BTTS Oui",
            "confidence_score": 6,
            "likely_scorer": "Mbappé",
        }

    def test_blend_normalizes_to_100(self):
        result = blend_predictions(self._make_stats(), self._make_ai())
        total = result["proba_home"] + result["proba_draw"] + result["proba_away"]
        assert total == 100

    def test_without_ai_uses_stats_only(self):
        stats = self._make_stats(h=60, d=25, a=15)
        result = blend_predictions(stats, None)
        assert result["proba_home"] == 60
        assert result["proba_draw"] == 25
        assert result["proba_away"] == 15

    def test_blend_is_weighted_average(self):
        stats = self._make_stats(h=50, d=30, a=20)
        ai = self._make_ai(h=70, d=20, a=10)
        result = blend_predictions(stats, ai)
        # 70% stats + 30% AI → home devrait être entre 50 et 70
        assert 50 <= result["proba_home"] <= 70

    def test_ai_analysis_preserved(self):
        result = blend_predictions(self._make_stats(), self._make_ai())
        assert result["analysis_text"] == "Analyse test"

    def test_ai_recommended_bet_used(self):
        result = blend_predictions(self._make_stats(), self._make_ai())
        assert result["recommended_bet"] == "BTTS Oui"

    def test_stats_json_present(self):
        result = blend_predictions(self._make_stats(), self._make_ai())
        assert "stats_json" in result
        assert "xg_home" in result["stats_json"]

    def test_double_chance_correct(self):
        result = blend_predictions(self._make_stats(), self._make_ai())
        assert result["proba_dc_1x"] == result["proba_home"] + result["proba_draw"]
        assert result["proba_dc_x2"] == result["proba_draw"] + result["proba_away"]
        assert result["proba_dc_12"] == result["proba_home"] + result["proba_away"]

    def test_non_blended_fields_from_stats(self):
        stats = self._make_stats()
        result = blend_predictions(stats, self._make_ai())
        assert result["proba_over_05"] == 95
        assert result["proba_over_15"] == 78
        assert result["proba_over_35"] == 30
        assert result["proba_penalty"] == 28
