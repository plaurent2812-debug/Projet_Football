"""
Fixtures pytest partagées pour tous les tests du projet Football IA.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════════
#  HELPER : MOCK SUPABASE
# ═══════════════════════════════════════════════════════════════════


class MockSupabaseQuery:
    """Mock chainable pour supabase.table(...).select(...).eq(...).execute()."""

    def __init__(self, data=None, count=None):
        self._data = data or []
        self._count = count

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def gt(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def or_(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def upsert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._data
        result.count = self._count
        return result


class MockSupabase:
    """Mock complet du client Supabase avec routage par table."""

    def __init__(self):
        self._tables = {}

    def set_table_data(self, table_name, data, count=None):
        """Configure les données retournées pour une table."""
        self._tables[table_name] = MockSupabaseQuery(data, count)

    def table(self, name):
        return self._tables.get(name, MockSupabaseQuery())


@pytest.fixture
def mock_supabase():
    """Retourne un MockSupabase configurable."""
    return MockSupabase()


# ═══════════════════════════════════════════════════════════════════
#  FIXTURES : DONNÉES DE TEST
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_fixture():
    """Un match type pour les tests."""
    return {
        "id": 1,
        "api_fixture_id": 12345,
        "home_team": "Paris Saint Germain",
        "away_team": "Olympique De Marseille",
        "league_id": 61,
        "date": "2026-02-15T21:00:00+00:00",
        "status": "NS",
        "home_goals": None,
        "away_goals": None,
        "referee_name": "François Letexier",
        "weather_json": {"temp": 8, "wind_speed": 12, "rain_mm": 0},
        "stats_json": {"round": "Regular Season - 24"},
    }


@pytest.fixture
def sample_finished_fixture():
    """Un match terminé pour les tests d'évaluation."""
    return {
        "id": 2,
        "api_fixture_id": 12346,
        "home_team": "Paris Saint Germain",
        "away_team": "Olympique Lyonnais",
        "league_id": 61,
        "date": "2026-02-08T21:00:00+00:00",
        "status": "FT",
        "home_goals": 3,
        "away_goals": 1,
        "referee_name": "Clément Turpin",
    }


@pytest.fixture
def sample_prediction():
    """Une prédiction type."""
    return {
        "id": 10,
        "fixture_id": 1,
        "proba_home": 55,
        "proba_draw": 25,
        "proba_away": 20,
        "proba_btts": 52,
        "proba_over_2_5": 58,
        "proba_over_05": 95,
        "proba_over_15": 78,
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
        "likely_scorer": "Kylian Mbappé",
        "likely_scorer_proba": 32,
        "model_version": "hybrid_v3_ml",
        "analysis_text": "PSG favori à domicile avec un xG supérieur.",
    }


@pytest.fixture
def sample_league_data():
    """Données de force d'une ligue type."""
    return {
        "strengths": {
            85: {
                "home_attack": 1.4,
                "home_defense": 0.7,
                "away_attack": 1.2,
                "away_defense": 0.8,
            },
            33: {
                "home_attack": 0.9,
                "home_defense": 1.3,
                "away_attack": 0.8,
                "away_defense": 1.1,
            },
            81: {
                "home_attack": 1.1,
                "home_defense": 1.0,
                "away_attack": 1.0,
                "away_defense": 1.0,
            },
        },
        "league_avg_home": 1.45,
        "league_avg_away": 1.10,
    }


@pytest.fixture
def sample_standings():
    """Classement partiel d'une ligue."""
    return [
        {
            "team_api_id": 85,
            "league_id": 61,
            "season": 2025,
            "rank": 1,
            "points": 55,
            "played": 24,
            "home_played": 12,
            "away_played": 12,
            "home_goals_for": 28,
            "home_goals_against": 8,
            "away_goals_for": 20,
            "away_goals_against": 12,
            "goals_against": 20,
        },
        {
            "team_api_id": 33,
            "league_id": 61,
            "season": 2025,
            "rank": 5,
            "points": 38,
            "played": 24,
            "home_played": 12,
            "away_played": 12,
            "home_goals_for": 18,
            "home_goals_against": 14,
            "away_goals_for": 12,
            "away_goals_against": 18,
            "goals_against": 32,
        },
    ]


@pytest.fixture
def sample_player_stats():
    """Stats saison d'un joueur type."""
    return {
        "player_api_id": 1100,
        "team_api_id": 85,
        "season": 2025,
        "goals": 18,
        "assists": 7,
        "shots_total": 85,
        "shots_on_target": 42,
        "minutes_played": 1920,
        "appearances": 22,
        "penalty_scored": 3,
        "penalty_missed": 1,
        "rating": 7.8,
        "position": "Attacker",
    }
