"""
Tests unitaires pour training/build_data.py — Feature engineering avancé.

Tests de _advanced_features_from_mem (Phase 5).
"""

from training.build_data import _advanced_features_from_mem


def _make_fixture(home: str, away: str, date: str, hg: int, ag: int) -> dict:
    """Create a minimal fixture dict for testing."""
    return {
        "home_team": home,
        "away_team": away,
        "date": date,
        "home_goals": hg,
        "away_goals": ag,
    }


def _make_data(fixtures: list[dict]) -> dict:
    """Build the data dict with fixtures_by_team index."""
    by_team: dict[str, list[dict]] = {}
    for f in fixtures:
        by_team.setdefault(f["home_team"], []).append(f)
        by_team.setdefault(f["away_team"], []).append(f)
    # Sort by date
    for team in by_team:
        by_team[team].sort(key=lambda x: x["date"])
    return {"fixtures_by_team": by_team}


class TestAdvancedFeatures:
    """Tests for _advanced_features_from_mem."""

    def test_returns_all_keys(self):
        data = _make_data([])
        result = _advanced_features_from_mem(data, "TeamA", "TeamB", "2025-01-10")
        expected_keys = [
            "home_momentum",
            "away_momentum",
            "home_fatigue_index",
            "away_fatigue_index",
            "home_goal_diff_avg",
            "away_goal_diff_avg",
            "home_result_variance",
            "away_result_variance",
            "home_clean_sheet_rate",
            "away_clean_sheet_rate",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_empty_history_defaults(self):
        data = _make_data([])
        result = _advanced_features_from_mem(data, "TeamA", "TeamB", "2025-01-10")
        assert result["home_momentum"] == 0.0
        assert result["away_momentum"] == 0.0
        assert result["home_goal_diff_avg"] == 0.0
        assert result["home_result_variance"] == 0.0
        assert result["home_clean_sheet_rate"] == 0.0

    def test_clean_sheet_rate(self):
        fixtures = [
            _make_fixture("TeamA", "TeamC", "2025-01-01", 2, 0),
            _make_fixture("TeamA", "TeamD", "2025-01-03", 1, 0),
            _make_fixture("TeamA", "TeamE", "2025-01-05", 3, 1),
        ]
        data = _make_data(fixtures)
        result = _advanced_features_from_mem(data, "TeamA", "TeamB", "2025-01-10")
        # 2 clean sheets out of 3 matches
        assert abs(result["home_clean_sheet_rate"] - 0.667) < 0.01

    def test_momentum_positive(self):
        """Team winning recent 3 but lost earlier should have positive momentum."""
        fixtures = [
            _make_fixture("TeamA", "X1", "2025-01-01", 0, 2),  # Loss
            _make_fixture("TeamA", "X2", "2025-01-02", 0, 1),  # Loss
            _make_fixture("TeamA", "X3", "2025-01-03", 0, 1),  # Loss
            _make_fixture("TeamA", "X4", "2025-01-04", 0, 3),  # Loss
            _make_fixture("TeamA", "X5", "2025-01-05", 0, 2),  # Loss
            _make_fixture("TeamA", "X6", "2025-01-06", 0, 1),  # Loss
            _make_fixture("TeamA", "X7", "2025-01-07", 2, 0),  # Win
            _make_fixture("TeamA", "X8", "2025-01-08", 3, 0),  # Win
            _make_fixture("TeamA", "X9", "2025-01-09", 1, 0),  # Win
        ]
        data = _make_data(fixtures)
        result = _advanced_features_from_mem(data, "TeamA", "TeamB", "2025-01-15")
        assert result["home_momentum"] > 0  # Recent form better than 6-match form

    def test_goal_diff_avg_positive(self):
        fixtures = [
            _make_fixture("TeamA", "X1", "2025-01-01", 3, 0),
            _make_fixture("TeamA", "X2", "2025-01-02", 2, 1),
        ]
        data = _make_data(fixtures)
        result = _advanced_features_from_mem(data, "TeamA", "TeamB", "2025-01-10")
        # (3-0 + 2-1) / 2 = 2.0
        assert result["home_goal_diff_avg"] == 2.0

    def test_result_variance(self):
        """All wins → low variance. Mixed results → high variance."""
        # All wins
        fixtures_stable = [
            _make_fixture("TeamA", f"X{i}", f"2025-01-0{i + 1}", 2, 0) for i in range(5)
        ]
        data_stable = _make_data(fixtures_stable)
        result_stable = _advanced_features_from_mem(data_stable, "TeamA", "TeamB", "2025-01-10")

        # Mixed (W, L, D, W, L)
        fixtures_mixed = [
            _make_fixture("TeamA", "X1", "2025-01-01", 2, 0),
            _make_fixture("TeamA", "X2", "2025-01-02", 0, 1),
            _make_fixture("TeamA", "X3", "2025-01-03", 1, 1),
            _make_fixture("TeamA", "X4", "2025-01-04", 3, 0),
            _make_fixture("TeamA", "X5", "2025-01-05", 0, 2),
        ]
        data_mixed = _make_data(fixtures_mixed)
        result_mixed = _advanced_features_from_mem(data_mixed, "TeamA", "TeamB", "2025-01-10")

        assert result_mixed["home_result_variance"] > result_stable["home_result_variance"]
