"""
Tests unitaires pour scorer_engine.py — fonctions pures.
"""

import pytest

from src.models.scorer_engine import get_anomaly_boost

# ═══════════════════════════════════════════════════════════════════
#  ANOMALIE STATISTIQUE
# ═══════════════════════════════════════════════════════════════════


class TestAnomalyBoost:
    """Tests de la détection d'anomalie statistique (tirs élevés, buts faibles)."""

    def test_no_rate_returns_1(self):
        assert get_anomaly_boost(None, {"goals": 0, "matches_played": 0}) == 1.0

    @pytest.mark.parametrize(
        "rate,form,label",
        [
            (
                {"total_shots_on": 5, "shots_on_per_90": 0.5, "conversion_rate": 0.10},
                {"goals": 0, "matches_played": 3},
                "low_shots",
            ),
            (
                {"total_shots_on": 20, "shots_on_per_90": 1.0, "conversion_rate": 0.30},
                {"goals": 3, "matches_played": 5},
                "good_conversion",
            ),
            (
                {"total_shots_on": 15, "shots_on_per_90": 1.5, "conversion_rate": 0.25},
                {"goals": 0, "matches_played": 2},
                "few_matches_no_mute_boost",
            ),
        ],
    )
    def test_no_boost_scenarios(self, rate, form, label):
        assert get_anomaly_boost(rate, form) == 1.0, f"{label}: expected no boost"

    @pytest.mark.parametrize(
        "rate,form,label",
        [
            (
                {"total_shots_on": 30, "shots_on_per_90": 1.5, "conversion_rate": 0.10},
                {"goals": 1, "matches_played": 5},
                "high_shots_low_conversion",
            ),
            (
                {"total_shots_on": 20, "shots_on_per_90": 1.2, "conversion_rate": 0.20},
                {"goals": 0, "matches_played": 4},
                "mute_but_active",
            ),
        ],
    )
    def test_boost_scenarios(self, rate, form, label):
        boost = get_anomaly_boost(rate, form)
        assert boost > 1.0, f"{label}: expected boost > 1.0, got {boost}"
