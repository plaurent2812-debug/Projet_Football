"""
Tests unitaires pour stats_engine.py — fonctions pures mathématiques.

Ces tests ne nécessitent PAS de connexion Supabase.
Ils testent les calculs de Poisson, ELO, météo, régression.
"""

import pytest

from src.models.stats_engine import (
    calculate_roi,
    calculate_xg,
    dixon_coles_correction,
    elo_expected,
    elo_update,
    elo_with_decay,
    get_elo_probs,
    get_weather_impact,
    kelly_criterion,
    poisson_grid,
    regress_to_mean,
)

# ═══════════════════════════════════════════════════════════════════
#  POISSON
# ═══════════════════════════════════════════════════════════════════


class TestPoissonGrid:
    """Tests de la grille de probabilités Poisson."""

    def test_probabilities_1x2_sum_close_to_100(self):
        result = poisson_grid(1.5, 1.2)
        total = result["proba_home"] + result["proba_draw"] + result["proba_away"]
        assert 98 <= total <= 102, f"Somme 1X2 = {total}, attendu ~100"

    def test_high_xg_home_favors_home(self):
        result = poisson_grid(3.0, 0.5)
        assert result["proba_home"] > result["proba_away"]
        assert result["proba_home"] > 60

    def test_high_xg_away_favors_away(self):
        result = poisson_grid(0.5, 3.0)
        assert result["proba_away"] > result["proba_home"]
        assert result["proba_away"] > 60

    def test_equal_xg_gives_balanced_result(self):
        result = poisson_grid(1.3, 1.3)
        assert abs(result["proba_home"] - result["proba_away"]) < 5

    def test_over_25_increases_with_xg(self):
        low = poisson_grid(0.8, 0.7)
        high = poisson_grid(2.0, 1.8)
        assert high["proba_over_25"] > low["proba_over_25"]

    def test_over_monotonic_ordering(self):
        result = poisson_grid(1.5, 1.3)
        assert result["proba_over_05"] >= result["proba_over_15"]
        assert result["proba_over_15"] >= result["proba_over_25"]
        assert result["proba_over_25"] >= result["proba_over_35"]

    def test_btts_increases_with_both_xg_high(self):
        low = poisson_grid(0.5, 0.5)
        high = poisson_grid(2.0, 2.0)
        assert high["proba_btts"] > low["proba_btts"]

    def test_correct_score_is_valid_format(self):
        result = poisson_grid(1.5, 1.0)
        h, a = result["correct_score"].split("-")
        assert int(h) >= 0 and int(a) >= 0

    def test_correct_score_prob_is_positive(self):
        result = poisson_grid(1.5, 1.0)
        assert result["proba_correct_score"] > 0

    def test_xg_returned_match_input(self):
        result = poisson_grid(1.5, 1.2)
        assert result["xg_home"] == 1.5
        assert result["xg_away"] == 1.2

    def test_double_chance_consistency(self):
        result = poisson_grid(1.5, 1.0)
        assert result["proba_dc_1x"] == result["proba_home"] + result["proba_draw"]
        assert result["proba_dc_x2"] == result["proba_draw"] + result["proba_away"]
        assert result["proba_dc_12"] == result["proba_home"] + result["proba_away"]

    def test_zero_xg_still_works(self):
        result = poisson_grid(0.01, 0.01)
        assert result["proba_draw"] > 50  # 0-0 très probable

    def test_very_high_xg(self):
        result = poisson_grid(4.0, 4.0)
        assert result["proba_over_25"] > 70


# ═══════════════════════════════════════════════════════════════════
#  ELO
# ═══════════════════════════════════════════════════════════════════


class TestEloExpected:
    """Tests du calcul de probabilité attendue ELO."""

    def test_equal_elos_give_50_percent(self):
        assert abs(elo_expected(1500, 1500) - 0.5) < 0.01

    @pytest.mark.parametrize(
        "home_elo,away_elo,expected_relation",
        [
            (1700, 1500, "greater"),
            (1500, 1700, "less"),
        ],
    )
    def test_elo_advantage_direction(self, home_elo, away_elo, expected_relation):
        prob = elo_expected(home_elo, away_elo)
        if expected_relation == "greater":
            assert prob > 0.5
        else:
            assert prob < 0.5

    def test_symmetry(self):
        p1 = elo_expected(1600, 1400)
        p2 = elo_expected(1400, 1600)
        assert abs(p1 + p2 - 1.0) < 0.001

    def test_extreme_difference(self):
        p = elo_expected(2000, 1000)
        assert p > 0.95


class TestEloUpdate:
    """Tests de la mise à jour du rating ELO."""

    def test_win_increases_elo(self):
        new = elo_update(1500, 0.5, 1.0)
        assert new > 1500

    def test_loss_decreases_elo(self):
        new = elo_update(1500, 0.5, 0.0)
        assert new < 1500

    def test_draw_when_expected_no_change(self):
        new = elo_update(1500, 0.5, 0.5)
        assert abs(new - 1500) < 0.1

    def test_big_goal_diff_bigger_change(self):
        small = elo_update(1500, 0.5, 1.0, goal_diff=1)
        big = elo_update(1500, 0.5, 1.0, goal_diff=4)
        assert big > small

    def test_unexpected_win_bigger_change(self):
        expected_win = elo_update(1500, 0.8, 1.0)
        upset_win = elo_update(1500, 0.2, 1.0)
        assert (upset_win - 1500) > (expected_win - 1500)


class TestEloProbs:
    """Tests de la conversion ELO → probabilités 1X2."""

    def test_sum_close_to_100(self):
        result = get_elo_probs(1500, 1500)
        total = result["elo_home"] + result["elo_draw"] + result["elo_away"]
        assert 95 <= total <= 105

    def test_higher_home_elo_favors_home(self):
        result = get_elo_probs(1700, 1400)
        assert result["elo_home"] > result["elo_away"]

    def test_equal_elos_draw_significant(self):
        result = get_elo_probs(1500, 1500)
        assert result["elo_draw"] > 10  # Le nul doit avoir une place

    def test_home_advantage_reflected(self):
        # Même ELO mais le domicile devrait être favorisé
        result = get_elo_probs(1500, 1500)
        assert result["elo_home"] > result["elo_away"]


# ═══════════════════════════════════════════════════════════════════
#  RÉGRESSION VERS LA MOYENNE
# ═══════════════════════════════════════════════════════════════════


class TestRegressToMean:
    """Tests de la régression bayésienne vers la moyenne."""

    def test_small_sample_pulls_to_mean(self):
        result = regress_to_mean(2.0, 3, 1.25)
        assert result < 2.0
        assert result > 1.25

    def test_large_sample_stays_near_observed(self):
        result = regress_to_mean(2.0, 100, 1.25)
        assert abs(result - 2.0) < 0.15

    def test_zero_sample_returns_league_avg(self):
        result = regress_to_mean(2.0, 0, 1.25)
        assert abs(result - 1.25) < 0.01

    def test_equal_values_returns_same(self):
        result = regress_to_mean(1.25, 10, 1.25)
        assert abs(result - 1.25) < 0.01


# ═══════════════════════════════════════════════════════════════════
#  MÉTÉO
# ═══════════════════════════════════════════════════════════════════


class TestWeatherImpact:
    """Tests de l'impact météo sur les xG."""

    def test_no_weather_returns_1(self):
        assert get_weather_impact(None) == 1.0

    def test_normal_weather_no_penalty(self):
        factor = get_weather_impact({"rain_mm": 0, "wind_speed": 3, "temp": 18})
        assert factor == 1.0

    @pytest.mark.parametrize(
        "weather,label",
        [
            ({"rain_mm": 10, "wind_speed": 0, "temp": 15}, "heavy_rain"),
            ({"rain_mm": 0, "wind_speed": 15, "temp": 15}, "strong_wind"),
            ({"rain_mm": 0, "wind_speed": 0, "temp": -5}, "extreme_cold"),
            ({"rain_mm": 0, "wind_speed": 0, "temp": 40}, "extreme_heat"),
        ],
    )
    def test_adverse_weather_reduces_goals(self, weather, label):
        factor = get_weather_impact(weather)
        assert factor < 1.0, f"{label}: expected factor < 1.0, got {factor}"

    def test_cumulative_bad_weather(self):
        rain_only = get_weather_impact({"rain_mm": 8, "wind_speed": 0, "temp": 15})
        rain_and_wind = get_weather_impact({"rain_mm": 8, "wind_speed": 12, "temp": 15})
        assert rain_and_wind < rain_only


# ═══════════════════════════════════════════════════════════════════
#  CALCULATE XG
# ═══════════════════════════════════════════════════════════════════


class TestCalculateXg:
    """Tests du calcul des expected goals."""

    def test_fallback_when_no_data(self):
        xg_h, xg_a = calculate_xg(85, 33, None)
        # Bayesian iteration may shift xG from base values; bounds check only
        assert 0.5 <= xg_h <= 2.5 and 0.5 <= xg_a <= 2.5
        assert xg_h > xg_a  # Home team (85) should still get higher xG

    def test_strong_team_gets_higher_xg(self, sample_league_data):
        xg_h, xg_a = calculate_xg(85, 33, sample_league_data)
        assert xg_h > xg_a  # Team 85 is stronger

    def test_xg_within_bounds(self, sample_league_data):
        xg_h, xg_a = calculate_xg(85, 33, sample_league_data)
        assert 0.3 <= xg_h <= 4.0
        assert 0.3 <= xg_a <= 4.0

    def test_adjustments_modify_xg(self, sample_league_data):
        base_h, base_a = calculate_xg(85, 33, sample_league_data)
        adj_h, adj_a = calculate_xg(
            85, 33, sample_league_data, adjustments={"home_factor": 1.2, "away_factor": 0.8}
        )
        assert adj_h > base_h
        assert adj_a < base_a

    def test_unknown_team_fallback(self, sample_league_data):
        xg_h, xg_a = calculate_xg(9999, 9998, sample_league_data)
        # ELO-based fallback or flat fallback — xG should be in valid range
        assert 0.3 <= xg_h <= 4.0 and 0.3 <= xg_a <= 4.0


# ═══════════════════════════════════════════════════════════════════
#  DIXON-COLES
# ═══════════════════════════════════════════════════════════════════


class TestDixonColes:
    """Tests for the Dixon-Coles correction factor."""

    @pytest.mark.parametrize(
        "home_goals,away_goals,label",
        [
            (0, 0, "0-0"),
            (1, 1, "1-1"),
        ],
    )
    def test_low_draw_score_increases_with_negative_rho(self, home_goals, away_goals, label):
        # With negative rho, 0-0 and 1-1 become MORE likely (Poisson under-estimates draws)
        factor = dixon_coles_correction(home_goals, away_goals, 1.5, 1.2, rho=-0.13)
        assert factor > 1.0, f"{label}: expected factor > 1.0 with negative rho, got {factor}"

    @pytest.mark.parametrize(
        "home_goals,away_goals,label",
        [
            (0, 1, "0-1"),
            (1, 0, "1-0"),
        ],
    )
    def test_one_sided_low_score_decreases_with_negative_rho(self, home_goals, away_goals, label):
        # 0-1 and 1-0 become LESS likely with negative rho
        factor = dixon_coles_correction(home_goals, away_goals, 1.5, 1.2, rho=-0.13)
        assert factor < 1.0, f"{label}: expected factor < 1.0 with negative rho, got {factor}"

    @pytest.mark.parametrize(
        "home_goals,away_goals",
        [
            (2, 1),
            (3, 0),
            (2, 3),
        ],
    )
    def test_high_score_no_correction(self, home_goals, away_goals):
        """For scorelines > 1, correction should be 1.0."""
        assert dixon_coles_correction(home_goals, away_goals, 1.5, 1.2) == 1.0

    def test_zero_rho_gives_identity(self):
        """With rho=0, all corrections should be 1.0."""
        for h in range(3):
            for a in range(3):
                assert dixon_coles_correction(h, a, 1.5, 1.2, rho=0.0) == 1.0

    def test_poisson_grid_uses_dixon_coles(self):
        """Verify Dixon-Coles is integrated into the Poisson grid."""
        result = poisson_grid(1.5, 1.2)
        # With Dixon-Coles, sum should still be ~100%
        total = result["proba_home"] + result["proba_draw"] + result["proba_away"]
        assert 95 <= total <= 105


# ═══════════════════════════════════════════════════════════════════
#  ELO TEMPORAL DECAY
# ═══════════════════════════════════════════════════════════════════


class TestEloDecay:
    """Tests for the ELO temporal decay function."""

    def test_no_decay_when_zero_days(self):
        assert elo_with_decay(1600, 0) == 1600

    @pytest.mark.parametrize(
        "initial_elo,days,expected_direction,bound",
        [
            (1700, 60, "down", (1500, 1700)),
            (1300, 60, "up", (1300, 1500)),
        ],
    )
    def test_decay_pulls_toward_baseline(self, initial_elo, days, expected_direction, bound):
        """Teams above 1500 decay down; teams below 1500 decay up."""
        decayed = elo_with_decay(initial_elo, days)
        low, high = bound
        assert low < decayed < high, (
            f"ELO {initial_elo} after {days} days: expected between {low} and {high}, got {decayed}"
        )

    def test_longer_inactivity_more_decay(self):
        d30 = elo_with_decay(1700, 30)
        d90 = elo_with_decay(1700, 90)
        assert d90 < d30  # 90 days should decay more

    def test_baseline_team_stays(self):
        """A team at exactly 1500 should stay at 1500."""
        assert elo_with_decay(1500, 100) == 1500


# ═══════════════════════════════════════════════════════════════════
#  KELLY CRITERION & ROI
# ═══════════════════════════════════════════════════════════════════


class TestKellyAndROI:
    """Tests for value betting functions."""

    @pytest.mark.parametrize(
        "proba,odds,expected_roi,label",
        [
            (60, 2.0, 0.2, "positive value bet"),
            (30, 2.0, -0.4, "negative bad bet"),
            (50, 2.0, 0.0, "break even"),
        ],
    )
    def test_roi_calculation(self, proba, odds, expected_roi, label):
        roi = calculate_roi(proba, odds)
        assert abs(roi - expected_roi) < 0.001, f"{label}: expected {expected_roi}, got {roi}"

    def test_kelly_zero_when_no_edge(self):
        # Model says 40%, odds 2.0 → edge = -0.2 → no bet
        bet = kelly_criterion(40, 2.0, 1000)
        assert bet == 0.0

    def test_kelly_positive_with_edge(self):
        # Model says 60%, odds 2.5 → edge = 0.5 → should bet
        bet = kelly_criterion(60, 2.5, 1000)
        assert bet > 0

    def test_kelly_respects_max_fraction(self):
        # Even with huge edge, should not exceed max_bet_fraction
        bet = kelly_criterion(95, 10.0, 1000, fraction=1.0, max_bet_fraction=0.05)
        assert bet <= 1000 * 0.05

    def test_kelly_zero_bankroll(self):
        bet = kelly_criterion(60, 2.5, 0)
        assert bet == 0.0


# ═══════════════════════════════════════════════════════════════════
#  HANDICAPS ASIATIQUES
# ═══════════════════════════════════════════════════════════════════


class TestAsianHandicaps:
    """Tests for Asian handicap probabilities in poisson_grid."""

    def test_ah_keys_present(self):
        result = poisson_grid(1.5, 1.0)
        for key in [
            "ah_home_minus_05",
            "ah_home_minus_10",
            "ah_home_minus_15",
            "ah_away_plus_05",
            "ah_away_plus_10",
            "ah_away_plus_15",
        ]:
            assert key in result, f"Missing key: {key}"

    def test_ah_minus_05_equals_home_win(self):
        """AH -0.5 home should equal the home win probability."""
        result = poisson_grid(1.5, 1.0)
        assert result["ah_home_minus_05"] == result["proba_home"]

    @pytest.mark.parametrize("line", ["05", "10", "15"])
    def test_ah_complementary(self, line):
        """AH home + AH away should sum to ~100% for each handicap line."""
        result = poisson_grid(1.5, 1.2)
        total = result[f"ah_home_minus_{line}"] + result[f"ah_away_plus_{line}"]
        assert 95 <= total <= 105, f"AH ±{line}: {total}% not ~100"

    def test_ah_hierarchy(self):
        """Bigger handicap should be harder to cover."""
        result = poisson_grid(2.0, 1.0)
        assert result["ah_home_minus_05"] >= result["ah_home_minus_10"]
        assert result["ah_home_minus_10"] >= result["ah_home_minus_15"]

    def test_dominant_team_high_ah(self):
        """A dominant team (3.0 xG vs 0.5 xG) should cover -1.5 often."""
        result = poisson_grid(3.0, 0.5)
        assert result["ah_home_minus_15"] > 40  # Should cover -1.5 frequently

    def test_balanced_match_ah(self):
        """In a balanced match, AH -0.5 should be close to home win prob."""
        result = poisson_grid(1.2, 1.2)
        assert result["ah_home_minus_05"] < 50  # Home can't be favored
