"""
Tests for src/prediction_blender.py — blend stats + AI meta-learner.

Covers:
  - blend_predictions() public API (with/without AI, normalization)
  - _build_fallback_analysis() narrative generation branches
  - _try_meta_blend() gated meta-learner blend
"""

from __future__ import annotations

from unittest.mock import patch

from src.prediction_blender import (
    _build_fallback_analysis,
    _try_meta_blend,
    blend_predictions,
)

# ═══════════════════════════════════════════════════════════════════
#  _build_fallback_analysis
# ═══════════════════════════════════════════════════════════════════


class TestFallbackAnalysis:
    """All narrative branches in _build_fallback_analysis."""

    def test_high_xg_mentions_match_ouvert(self):
        stats = {"xg_home": 1.8, "xg_away": 1.5}  # total = 3.3
        out = _build_fallback_analysis(stats)
        assert "match ouvert" in out
        assert "1.80" in out
        assert "1.50" in out

    def test_medium_xg_mentions_equilibré(self):
        stats = {"xg_home": 1.2, "xg_away": 1.1}  # total = 2.3
        out = _build_fallback_analysis(stats)
        assert "équilibré" in out

    def test_low_xg_mentions_fermé(self):
        stats = {"xg_home": 0.9, "xg_away": 0.8}  # total = 1.7
        out = _build_fallback_analysis(stats)
        assert "fermé" in out

    def test_home_favorite_when_proba_home_high(self):
        stats = {"xg_home": 1.5, "xg_away": 1.0, "proba_home": 60}
        out = _build_fallback_analysis(stats)
        assert "nettement favorite" in out

    def test_away_favorite_when_proba_away_high(self):
        stats = {"xg_home": 1.0, "xg_away": 1.5, "proba_away": 58}
        out = _build_fallback_analysis(stats)
        assert "visiteuse est favorite" in out

    def test_balanced_match_when_home_away_within_10(self):
        stats = {
            "xg_home": 1.3,
            "xg_away": 1.2,
            "proba_home": 40,
            "proba_draw": 28,
            "proba_away": 32,
        }
        out = _build_fallback_analysis(stats)
        assert "de très près" in out

    def test_slight_home_advantage(self):
        stats = {
            "xg_home": 1.5,
            "xg_away": 1.0,
            "proba_home": 48,
            "proba_draw": 27,
            "proba_away": 25,
        }
        out = _build_fallback_analysis(stats)
        assert "domicile" in out
        # Not "nettement favorite" because p_home < 55
        assert "nettement favorite" not in out

    def test_slight_away_advantage(self):
        stats = {
            "xg_home": 1.0,
            "xg_away": 1.5,
            "proba_home": 25,
            "proba_draw": 27,
            "proba_away": 48,
        }
        out = _build_fallback_analysis(stats)
        assert "extérieur" in out

    def test_over_25_high(self):
        stats = {
            "xg_home": 1.5,
            "xg_away": 1.5,
            "proba_home": 40,
            "proba_draw": 25,
            "proba_away": 35,
            "proba_over_2_5": 60,
        }
        out = _build_fallback_analysis(stats)
        assert "Over 2.5" in out
        assert "60" in out

    def test_over_25_low_defensive(self):
        stats = {
            "xg_home": 0.9,
            "xg_away": 0.8,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_over_2_5": 28,
        }
        out = _build_fallback_analysis(stats)
        assert "défensif" in out or "Profil défensif" in out

    def test_btts_high(self):
        # Truncation keeps 4 sentences max: craft stats so BTTS still lands in top-4
        stats = {
            "xg_home": 1.3,
            "xg_away": 1.2,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_btts": 70,
        }
        out = _build_fallback_analysis(stats)
        assert "BTTS" in out
        assert "70" in out

    def test_btts_low_peu_probable(self):
        stats = {
            "xg_home": 1.3,
            "xg_away": 1.2,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_btts": 25,
        }
        out = _build_fallback_analysis(stats)
        assert "peu probable" in out

    def test_form_home_good(self):
        # We must get the form sentence into the top-4, so keep other
        # branches quiet: neutral xG, balanced probas, silent over/btts.
        stats = {
            "xg_home": 1.2,
            "xg_away": 1.1,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_over_2_5": 45,  # not >= 55, not <= 35 → silent
            "proba_btts": 50,  # not >= 60, not <= 35 → silent
            "context": {"form_home": ["W", "W", "W", "W", "L"]},
        }
        out = _build_fallback_analysis(stats)
        assert "grande forme" in out

    def test_form_home_bad(self):
        stats = {
            "xg_home": 1.2,
            "xg_away": 1.1,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_over_2_5": 45,
            "proba_btts": 50,
            "context": {"form_home": ["L", "L", "L", "D", "L"]},
        }
        out = _build_fallback_analysis(stats)
        assert "période difficile" in out

    def test_form_away_good(self):
        stats = {
            "xg_home": 1.2,
            "xg_away": 1.1,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_over_2_5": 45,
            "proba_btts": 50,
            "context": {"form_away": ["W", "W", "W", "W", "D"]},
        }
        out = _build_fallback_analysis(stats)
        assert "belle dynamique" in out

    def test_form_away_bad(self):
        stats = {
            "xg_home": 1.2,
            "xg_away": 1.1,
            "proba_home": 40,
            "proba_draw": 30,
            "proba_away": 30,
            "proba_over_2_5": 45,
            "proba_btts": 50,
            "context": {"form_away": ["L", "L", "L", "L", "D"]},
        }
        out = _build_fallback_analysis(stats)
        assert "manquent de confiance" in out

    def test_form_ignored_when_not_list(self):
        # context.form_home is a non-list value (e.g., string) → must not crash
        stats = {
            "xg_home": 1.2,
            "xg_away": 1.1,
            "context": {"form_home": "WWWLW", "form_away": None},
        }
        out = _build_fallback_analysis(stats)
        # No form sentence in output
        assert "grande forme" not in out
        assert "période difficile" not in out

    def test_output_capped_at_4_sentences(self):
        # Trigger lots of branches to ensure we still get ≤ 4 sentences
        stats = {
            "xg_home": 2.0,
            "xg_away": 1.5,  # high xG (part 1)
            "proba_home": 60,  # home favorite (part 2)
            "proba_draw": 20,
            "proba_away": 20,
            "proba_over_2_5": 70,  # over 2.5 high (part 3)
            "proba_btts": 70,  # btts high (part 4)
            "context": {
                "form_home": ["W", "W", "W", "W", "W"],  # form home good (part 5 → dropped)
                "form_away": ["W", "W", "W", "W", "W"],  # form away good (part 6 → dropped)
            },
        }
        out = _build_fallback_analysis(stats)
        # Roughly count sentences via "." split (ignoring decimals)
        # Better: ensure "dynamique" (form_away good) NOT in the top-4
        assert "belle dynamique" not in out

    def test_defaults_when_stats_empty(self):
        # Should not crash on empty dict — uses defaults
        out = _build_fallback_analysis({})
        assert isinstance(out, str)
        assert len(out) > 0


# ═══════════════════════════════════════════════════════════════════
#  blend_predictions
# ═══════════════════════════════════════════════════════════════════


class TestBlendPredictionsPhase1:
    """Phase 1 = 100% stats (default, META_LEARNER_ENABLED=False)."""

    def test_minimal_stats_passes_through(self):
        stats = {
            "proba_home": 50,
            "proba_draw": 30,
            "proba_away": 20,
            "proba_btts": 55,
            "proba_over_2_5": 48,
        }
        out = blend_predictions(stats, ai_result=None)
        assert out["proba_home"] == 50
        assert out["proba_draw"] == 30
        assert out["proba_away"] == 20
        assert out["proba_btts"] == 55
        assert out["proba_over_2_5"] == 48
        # Phase 1 default version
        assert out["model_version"] == "hybrid_v3"

    def test_probas_sum_to_100_after_normalization(self):
        # Deliberately unnormalized input
        stats = {"proba_home": 60, "proba_draw": 30, "proba_away": 20}
        out = blend_predictions(stats, ai_result=None)
        total = out["proba_home"] + out["proba_draw"] + out["proba_away"]
        assert total == 100

    def test_probas_already_100_unchanged(self):
        stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
        out = blend_predictions(stats, ai_result=None)
        assert out["proba_home"] == 50
        assert out["proba_draw"] == 30
        assert out["proba_away"] == 20

    def test_probas_zero_total_kept_as_is(self):
        # When total == 0 we don't divide — no crash
        stats = {"proba_home": 0, "proba_draw": 0, "proba_away": 0}
        out = blend_predictions(stats, ai_result=None)
        assert out["proba_home"] == 0
        assert out["proba_draw"] == 0
        assert out["proba_away"] == 0

    def test_missing_proba_fields_default_to_50_then_normalized(self):
        out = blend_predictions({}, ai_result=None)
        # Defaults are 50/50/50 (sum=150), normalised to sum=100:
        # 50/150*100 ≈ 33 each, last one adjusts to make total exactly 100.
        total = out["proba_home"] + out["proba_draw"] + out["proba_away"]
        assert total == 100
        assert out["proba_home"] == 33
        assert out["proba_draw"] == 33
        # Away takes the residual to enforce sum == 100
        assert out["proba_away"] == 34
        # Non-1X2 fields keep the raw default (50)
        assert out["proba_btts"] == 50
        assert out["proba_over_2_5"] == 50

    def test_double_chance_computed_from_blended_probas(self):
        stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
        out = blend_predictions(stats, ai_result=None)
        assert out["proba_dc_1x"] == 80  # home + draw
        assert out["proba_dc_x2"] == 50  # draw + away
        assert out["proba_dc_12"] == 70  # home + away

    def test_fallback_analysis_used_when_no_ai(self):
        stats = {
            "xg_home": 1.3,
            "xg_away": 1.2,
            "proba_home": 50,
            "proba_draw": 30,
            "proba_away": 20,
        }
        out = blend_predictions(stats, ai_result=None)
        assert out["ai_features"] == {}
        assert isinstance(out["analysis_text"], str)
        assert len(out["analysis_text"]) > 0

    def test_stats_json_built_with_meta_active_false(self):
        stats = {
            "proba_home": 50,
            "proba_draw": 30,
            "proba_away": 20,
            "xg_home": 1.5,
            "xg_away": 1.2,
            "context": {"home": "A", "away": "B"},
        }
        out = blend_predictions(stats, ai_result=None)
        sj = out["stats_json"]
        assert sj["xg_home"] == 1.5
        assert sj["xg_away"] == 1.2
        assert sj["context"] == {"home": "A", "away": "B"}
        assert sj["meta_active"] is False

    def test_recommended_bet_and_confidence_passthrough(self):
        stats = {
            "proba_home": 50,
            "proba_draw": 30,
            "proba_away": 20,
            "recommended_bet": "Home win",
            "confidence_score": 8,
        }
        out = blend_predictions(stats, ai_result=None)
        assert out["recommended_bet"] == "Home win"
        assert out["confidence_score"] == 8

    def test_recommended_bet_default_empty(self):
        out = blend_predictions(
            {"proba_home": 50, "proba_draw": 30, "proba_away": 20}, ai_result=None
        )
        assert out["recommended_bet"] == ""
        assert out["confidence_score"] == 5


class TestBlendPredictionsAIResult:
    """When ai_result is provided (dict or Pydantic-like)."""

    def test_ai_result_dict_populates_fields(self):
        stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
        ai = {
            "analysis_text": "Analyse IA détaillée",
            "likely_scorer": "Mbappé",
            "likely_scorer_reason": "En forme",
            "motivation": 8,
        }
        out = blend_predictions(stats, ai_result=ai)
        assert out["analysis_text"] == "Analyse IA détaillée"
        assert out["likely_scorer"] == "Mbappé"
        assert out["likely_scorer_reason"] == "En forme"
        assert out["ai_features"] == ai

    def test_ai_result_with_model_dump_method(self):
        """Pydantic-like object exposing model_dump()."""

        class FakeAIModel:
            analysis_text = "Analyse depuis le modèle"
            likely_scorer = "Haaland"
            likely_scorer_reason = "Meilleur buteur"

            def model_dump(self):
                return {
                    "analysis_text": self.analysis_text,
                    "likely_scorer": self.likely_scorer,
                    "likely_scorer_reason": self.likely_scorer_reason,
                    "motivation": 9,
                }

        stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
        out = blend_predictions(stats, ai_result=FakeAIModel())
        assert out["analysis_text"] == "Analyse depuis le modèle"
        assert out["likely_scorer"] == "Haaland"
        assert out["ai_features"]["motivation"] == 9


# ═══════════════════════════════════════════════════════════════════
#  _try_meta_blend
# ═══════════════════════════════════════════════════════════════════


class TestTryMetaBlend:
    """Gated meta-learner blending path."""

    def test_returns_false_when_meta_learner_disabled(self):
        stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
        final = dict(stats)
        # Default: META_LEARNER_ENABLED = False
        assert _try_meta_blend(stats, {}, final) is False
        # Final must not have been mutated
        assert final["proba_home"] == 50

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0)
    def test_returns_false_when_weight_ai_zero(self):
        final = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
        assert _try_meta_blend({}, {}, final) is False

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0.3)
    @patch("src.prediction_blender.WEIGHT_STATS", 0.7)
    def test_returns_false_when_predict_meta_missing(self):
        # predict_meta returns None/empty → gracefully degrades
        with patch("src.pipeline.inference.predict_meta", return_value=None):
            final = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
            assert _try_meta_blend({}, {}, final) is False

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0.3)
    @patch("src.prediction_blender.WEIGHT_STATS", 0.7)
    def test_returns_false_on_exception(self):
        with patch("src.pipeline.inference.predict_meta", side_effect=RuntimeError("boom")):
            final = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
            assert _try_meta_blend({}, {}, final) is False

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0.3)
    @patch("src.prediction_blender.WEIGHT_STATS", 0.7)
    def test_full_blend_1x2_when_meta_complete(self):
        meta_preds = {
            "proba_home_meta": 70,
            "proba_draw_meta": 20,
            "proba_away_meta": 10,
        }
        with patch("src.pipeline.inference.predict_meta", return_value=meta_preds):
            final = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
            assert _try_meta_blend({}, {}, final) is True
            # Blended: 0.7 * 50 + 0.3 * 70 = 56
            assert final["proba_home"] == 56
            # Blended: 0.7 * 30 + 0.3 * 20 = 27
            assert final["proba_draw"] == 27
            # Blended: 100 - 56 - 27 = 17
            assert final["proba_away"] == 17

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0.3)
    @patch("src.prediction_blender.WEIGHT_STATS", 0.7)
    def test_partial_blend_only_btts(self):
        meta_preds = {
            "proba_home_meta": None,
            "proba_btts_meta": 80,
            "proba_over_15_meta": None,
            "proba_over_25_meta": None,
        }
        with patch("src.pipeline.inference.predict_meta", return_value=meta_preds):
            final = {
                "proba_home": 50,
                "proba_draw": 30,
                "proba_away": 20,
                "proba_btts": 40,
            }
            assert _try_meta_blend({}, {}, final) is True
            # 1X2 unchanged (meta home is None)
            assert final["proba_home"] == 50
            # BTTS blended: 0.7 * 40 + 0.3 * 80 = 52
            assert final["proba_btts"] == 52

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0.3)
    @patch("src.prediction_blender.WEIGHT_STATS", 0.7)
    def test_over_markets_blended(self):
        meta_preds = {
            "proba_home_meta": None,
            "proba_over_15_meta": 80,
            "proba_over_25_meta": 55,
        }
        with patch("src.pipeline.inference.predict_meta", return_value=meta_preds):
            final = {
                "proba_home": 50,
                "proba_draw": 30,
                "proba_away": 20,
                "proba_over_15": 60,
                "proba_over_2_5": 45,
            }
            assert _try_meta_blend({}, {}, final) is True
            # Over 1.5: 0.7 * 60 + 0.3 * 80 = 66
            assert final["proba_over_15"] == 66
            # Over 2.5: 0.7 * 45 + 0.3 * 55 = 48
            assert final["proba_over_2_5"] == 48


class TestBlendPredictionsMetaPath:
    """End-to-end through blend_predictions when meta-learner is active."""

    @patch("src.prediction_blender.META_LEARNER_ENABLED", True)
    @patch("src.prediction_blender.WEIGHT_AI", 0.3)
    @patch("src.prediction_blender.WEIGHT_STATS", 0.7)
    def test_model_version_switches_to_hybrid_v4_meta(self):
        meta_preds = {
            "proba_home_meta": 60,
            "proba_draw_meta": 25,
            "proba_away_meta": 15,
        }
        with patch("src.pipeline.inference.predict_meta", return_value=meta_preds):
            stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20}
            out = blend_predictions(stats, ai_result={"analysis_text": "ai"})
            assert out["model_version"] == "hybrid_v4_meta"
            # Double Chance must be recomputed after meta blend
            assert out["proba_dc_1x"] == out["proba_home"] + out["proba_draw"]
            assert out["proba_dc_x2"] == out["proba_draw"] + out["proba_away"]
            assert out["proba_dc_12"] == out["proba_home"] + out["proba_away"]
            assert out["stats_json"]["meta_active"] is True
