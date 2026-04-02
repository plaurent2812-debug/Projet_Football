"""
Tests unitaires pour embeddings.py — fonctions pures (pas d'appel API).
"""

import math

import pytest

from src.embeddings import (
    build_match_profile_text,
    build_player_profile_text,
    cosine_similarity,
)


# ═══════════════════════════════════════════════════════════════════
#  COSINE SIMILARITY
# ═══════════════════════════════════════════════════════════════════


class TestCosineSimilarity:
    """Tests for the cosine similarity function."""

    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_similar_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 3.1]
        sim = cosine_similarity(a, b)
        assert sim > 0.99  # Very similar

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_both_zero_vectors(self):
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="length mismatch"):
            cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_unit_vectors(self):
        # 45-degree vectors in 2D
        a = [1.0, 0.0]
        b = [math.sqrt(2) / 2, math.sqrt(2) / 2]
        assert cosine_similarity(a, b) == pytest.approx(math.sqrt(2) / 2, abs=1e-10)

    def test_high_dimensional(self):
        """Test with 768-dim vectors (like real embeddings)."""
        a = [float(i) / 768 for i in range(768)]
        b = [float(i + 1) / 768 for i in range(768)]
        sim = cosine_similarity(a, b)
        assert 0.0 < sim < 1.0


# ═══════════════════════════════════════════════════════════════════
#  MATCH PROFILE TEXT
# ═══════════════════════════════════════════════════════════════════


class TestBuildMatchProfileText:
    """Tests for match profile text serialization."""

    def _make_fixture(self, home="PSG", away="OM", league_id=61):
        return {
            "home_team": home,
            "away_team": away,
            "league_id": league_id,
            "date": "2025-03-10",
        }

    def _make_stats(self):
        return {
            "xg_home": 1.8,
            "xg_away": 1.2,
            "proba_home": 55,
            "proba_draw": 25,
            "proba_away": 20,
            "proba_btts": 60,
            "proba_over_25": 65,
            "context": {
                "elo_home": 1700,
                "elo_away": 1500,
                "form_home": "WWDWL",
                "form_away": "LDWLW",
                "rest_days_home": 5,
                "rest_days_away": 3,
                "congestion_home": 6,
                "congestion_away": 8,
                "stakes_home": "Title race",
                "stakes_away": "Mid-table",
                "injuries_home_details": [{"player_name": "Mbappé"}],
                "injuries_away_details": [],
                "h2h": {
                    "team_a_wins": 8,
                    "draws": 3,
                    "team_b_wins": 4,
                    "total_matches": 15,
                },
                "weather": {
                    "description": "Cloudy",
                    "temp": 12,
                    "wind_speed": 15,
                    "rain_mm": 0,
                },
            },
        }

    def test_contains_team_names(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "PSG" in text
        assert "OM" in text

    def test_contains_xg(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "1.8" in text
        assert "1.2" in text

    def test_contains_probabilities(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "55%" in text
        assert "25%" in text

    def test_contains_elo_gap(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "200" in text  # ELO gap

    def test_contains_form(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "WWDWL" in text

    def test_contains_h2h(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "15 matches" in text

    def test_contains_injuries(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "Home 1" in text  # 1 injury home

    def test_contains_weather(self):
        text = build_match_profile_text(self._make_fixture(), self._make_stats())
        assert "Cloudy" in text

    def test_deterministic(self):
        fix = self._make_fixture()
        stats = self._make_stats()
        assert build_match_profile_text(fix, stats) == build_match_profile_text(fix, stats)

    def test_minimal_data(self):
        """Profile text works with minimal fixture/stats."""
        text = build_match_profile_text(
            {"home_team": "A", "away_team": "B"},
            {"xg_home": 1.0, "xg_away": 0.5},
        )
        assert "A" in text
        assert "B" in text


# ═══════════════════════════════════════════════════════════════════
#  PLAYER PROFILE TEXT
# ═══════════════════════════════════════════════════════════════════


class TestBuildPlayerProfileText:
    """Tests for NHL player profile text serialization."""

    def _make_player(self):
        return {
            "player_name": "Connor McDavid",
            "team": "EDM",
            "opp": "CGY",
            "is_home": True,
            "points_per_game": 1.42,
            "goals_per_game": 0.55,
            "assists_per_game": 0.87,
            "shots_per_game": 3.8,
            "prob_goal": 38.5,
            "prob_assist": 52.1,
        }

    def test_contains_player_name(self):
        text = build_player_profile_text(self._make_player())
        assert "Connor McDavid" in text

    def test_contains_team(self):
        text = build_player_profile_text(self._make_player())
        assert "EDM" in text

    def test_contains_opponent(self):
        text = build_player_profile_text(self._make_player())
        assert "CGY" in text

    def test_contains_ppg(self):
        text = build_player_profile_text(self._make_player())
        assert "1.42" in text

    def test_contains_probabilities(self):
        text = build_player_profile_text(self._make_player())
        assert "38.5" in text
        assert "52.1" in text

    def test_minimal_player(self):
        """Works with minimal player data."""
        text = build_player_profile_text({"name": "Test Player", "team": "NYR"})
        assert "Test Player" in text
        assert "NYR" in text


# ═══════════════════════════════════════════════════════════════════
#  EMBEDDING API (mocked)
# ═══════════════════════════════════════════════════════════════════


class TestGetEmbedding:
    """Tests for the embedding API call (with mocking)."""

    def test_get_embedding_returns_correct_dims(self, monkeypatch):
        """Mock Gemini API to verify output shape."""
        class MockEmbedding:
            values = [0.1] * 768

        class MockResult:
            embeddings = [MockEmbedding()]

        class MockModels:
            def embed_content(self, **kwargs):
                assert kwargs.get("config", {}).get("output_dimensionality") == 768
                return MockResult()

        class MockClient:
            models = MockModels()

        import src.embeddings as emb_module
        monkeypatch.setattr(emb_module, "_embed_client", MockClient())

        from src.embeddings import get_embedding
        result = get_embedding("test text")
        assert result is not None
        assert len(result) == 768

    def test_get_embedding_returns_none_on_error(self, monkeypatch):
        """Verify graceful None return on API failure."""
        class MockModels:
            def embed_content(self, **kwargs):
                raise RuntimeError("API unavailable")

        class MockClient:
            models = MockModels()

        import src.embeddings as emb_module
        monkeypatch.setattr(emb_module, "_embed_client", MockClient())

        from src.embeddings import get_embedding
        result = get_embedding("test text")
        assert result is None
