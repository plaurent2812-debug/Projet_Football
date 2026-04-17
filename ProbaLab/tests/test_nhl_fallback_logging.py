"""
Verify NHL ML predictors expose .loaded flag and log WARNING on fallback.

Tests are split into two layers:
1. Unit tests on EnhancedGoalPredictor directly (no Supabase, no HTTP).
2. Integration test on /brain_quick — skipped because the endpoint requires
   complex Supabase fixtures that are not available in CI.
"""

import logging
import math

import pytest

from src.nhl.ml_models import EnhancedGoalPredictor

# ---------------------------------------------------------------------------
# Unit tests — EnhancedGoalPredictor
# ---------------------------------------------------------------------------


class TestEnhancedGoalPredictorLoadedFlag:
    """EnhancedGoalPredictor.loaded must be False by default and after failure."""

    def test_loaded_false_by_default(self):
        predictor = EnhancedGoalPredictor(target_stat="shot")
        assert predictor.loaded is False

    def test_loaded_false_after_missing_file(self, caplog):
        predictor = EnhancedGoalPredictor(target_stat="shot")
        with caplog.at_level(logging.WARNING, logger="src.nhl.ml_models"):
            result = predictor.load("/nonexistent/path/model.pkl")
        assert result is False
        assert predictor.loaded is False
        assert any("fallback to Poisson" in record.message for record in caplog.records), (
            "Expected WARNING mentioning 'fallback to Poisson' when model file is missing"
        )

    def test_loaded_false_after_corrupt_file(self, caplog, tmp_path):
        corrupt = tmp_path / "corrupt.pkl"
        corrupt.write_bytes(b"not-a-valid-pkl-file")
        predictor = EnhancedGoalPredictor(target_stat="goal")
        with caplog.at_level(logging.WARNING, logger="src.nhl.ml_models"):
            result = predictor.load(str(corrupt))
        assert result is False
        assert predictor.loaded is False
        assert any("fallback to Poisson" in record.message for record in caplog.records), (
            "Expected WARNING mentioning 'fallback to Poisson' when pkl is corrupt"
        )

    def test_loaded_preserves_false_across_multiple_failures(self, caplog):
        predictor = EnhancedGoalPredictor(target_stat="assist")
        predictor.load("/does/not/exist/1.pkl")
        predictor.load("/does/not/exist/2.pkl")
        assert predictor.loaded is False

    def test_all_predictor_types_have_loaded_attribute(self):
        for stat in ("goal", "shot", "point", "assist"):
            p = EnhancedGoalPredictor(target_stat=stat)
            assert hasattr(p, "loaded"), f"EnhancedGoalPredictor({stat}) missing .loaded"
            assert p.loaded is False


class TestEnhancedGoalPredictorFallbackBehavior:
    """predict_proba must return a valid probability even when loaded=False."""

    @pytest.mark.parametrize("stat", ["goal", "shot", "point", "assist"])
    def test_fallback_returns_valid_probability(self, stat):
        predictor = EnhancedGoalPredictor(target_stat=stat)
        assert predictor.loaded is False
        data = {
            "gpg": 0.3,
            "spg": 2.5,
            "apg": 0.4,
            "is_home": True,
            "opp_gaa": 3.0,
        }
        prob = predictor.predict_proba(data)
        assert 0.01 <= prob <= 0.99, f"Fallback prob out of range for {stat}: {prob}"

    def test_fallback_shot_uses_poisson(self):
        """When not loaded, shot predictor uses Poisson with rate spg."""
        predictor = EnhancedGoalPredictor(target_stat="shot")
        data = {"spg": 3.0, "is_home": False}
        prob = predictor.predict_proba(data)
        # Poisson: P(X >= 3) = 1 - P(0) - P(1) - P(2) at rate=3*0.95=2.85
        lam = 3.0 * 0.95
        expected = 1.0 - (math.exp(-lam) + lam * math.exp(-lam) + (lam**2 / 2) * math.exp(-lam))
        assert abs(prob - expected) < 0.01


# ---------------------------------------------------------------------------
# Integration test — /brain_quick endpoint
# Skipped: requires Supabase connection + probability_calibrator init.
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "Endpoint /brain_quick requires complex Supabase fixtures "
        "(probability_calibrator, feature_engineer) — manual smoke test instead. "
        "Run: curl -X POST http://localhost:8000/nhl/brain_quick with a BrainRequest payload "
        "and verify ml_fallback_used is present in the response."
    )
)
def test_brain_quick_exposes_ml_fallback_used_in_response():
    """Integration: /brain_quick response must contain ml_fallback_used dict."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    with patch("api.routers.nhl.shot_predictor") as mock_shot:
        mock_shot.loaded = False
        mock_shot.predict_proba.side_effect = RuntimeError("should not be called")

        payload = {
            "players": [
                {
                    "id": "test-player-1",
                    "name": "Test Player",
                    "gpg": 0.3,
                    "spg": 2.5,
                    "apg": 0.4,
                    "opp_gaa": 3.0,
                    "is_home": True,
                }
            ]
        }
        r = client.post("/nhl/brain_quick", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "ml_fallback_used" in data, "ml_fallback_used must be in response"
        assert data["ml_fallback_used"]["shot"] is True
        assert data["ml_fallback_used"]["goal"] is False
