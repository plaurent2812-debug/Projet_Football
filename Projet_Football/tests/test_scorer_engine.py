"""
Tests unitaires pour scorer_engine.py — fonctions pures.
"""

from models.scorer_engine import get_anomaly_boost

# ═══════════════════════════════════════════════════════════════════
#  ANOMALIE STATISTIQUE
# ═══════════════════════════════════════════════════════════════════


class TestAnomalyBoost:
    """Tests de la détection d'anomalie statistique (tirs élevés, buts faibles)."""

    def test_no_rate_returns_1(self):
        assert get_anomaly_boost(None, {"goals": 0, "matches_played": 0}) == 1.0

    def test_low_shots_no_boost(self):
        rate = {"total_shots_on": 5, "shots_on_per_90": 0.5, "conversion_rate": 0.10}
        form = {"goals": 0, "matches_played": 3}
        assert get_anomaly_boost(rate, form) == 1.0

    def test_high_shots_low_conversion_gives_boost(self):
        rate = {"total_shots_on": 30, "shots_on_per_90": 1.5, "conversion_rate": 0.10}
        form = {"goals": 1, "matches_played": 5}
        boost = get_anomaly_boost(rate, form)
        assert boost > 1.0  # Rebond probable

    def test_mute_but_active_gives_boost(self):
        rate = {"total_shots_on": 20, "shots_on_per_90": 1.2, "conversion_rate": 0.20}
        form = {"goals": 0, "matches_played": 4}
        boost = get_anomaly_boost(rate, form)
        assert boost > 1.0  # Muet mais tirs au cadre → rebond

    def test_good_conversion_no_boost(self):
        rate = {"total_shots_on": 20, "shots_on_per_90": 1.0, "conversion_rate": 0.30}
        form = {"goals": 3, "matches_played": 5}
        assert get_anomaly_boost(rate, form) == 1.0

    def test_few_matches_no_mute_boost(self):
        rate = {"total_shots_on": 15, "shots_on_per_90": 1.5, "conversion_rate": 0.25}
        form = {"goals": 0, "matches_played": 2}  # < 3 matchs → pas d'anomalie "muet"
        assert get_anomaly_boost(rate, form) == 1.0
