"""Tests avec mocks Supabase pour stats_engine.py."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest
from models.stats_engine import (
    analyze_match,
    calculate_form,
    calculate_penalty_proba,
    calculate_rest_factor,
    calculate_stakes,
    calculate_team_strengths,
    get_h2h_factor,
    get_injury_impact,
    get_referee_impact,
    odds_to_probs,
)

# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def _route_tables(mock_sb, table_map):
    r"""Configure *mock_sb.table* to return chainable mocks per table name.

    Each call to ``mock_sb.table(name)`` returns a fresh ``MagicMock``
    whose chaining methods (select, eq, in\_, …) always return itself
    and whose ``execute()`` returns data from *table_map[name]*.
    Tables not present in the map return empty data.
    """

    def _table_fn(name):
        q = MagicMock()
        data = table_map.get(name, [])
        for method in (
            "select",
            "eq",
            "neq",
            "in_",
            "or_",
            "order",
            "limit",
            "gte",
            "lte",
            "gt",
            "lt",
            "filter",
            "upsert",
            "insert",
            "update",
            "delete",
        ):
            getattr(q, method).return_value = q
        q.execute.return_value = MagicMock(data=data, count=len(data))
        return q

    mock_sb.table.side_effect = _table_fn


# ═══════════════════════════════════════════════════════════════════
#  1. calculate_team_strengths
# ═══════════════════════════════════════════════════════════════════


class TestCalculateTeamStrengths:
    """Tests de calculate_team_strengths avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_returns_none_for_empty_standings(self, mock_sb):
        """Aucune donnée dans team_standings → None."""
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result = calculate_team_strengths(61)
        assert result is None

    @patch("models.stats_engine.supabase")
    def test_returns_none_for_few_teams(self, mock_sb):
        """Moins de 4 équipes → None (données insuffisantes)."""
        standings = [
            {
                "team_api_id": 85,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 24,
                "home_goals_against": 8,
                "away_goals_for": 18,
                "away_goals_against": 12,
            },
            {
                "team_api_id": 33,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 15,
                "home_goals_against": 14,
                "away_goals_for": 10,
                "away_goals_against": 16,
            },
            {
                "team_api_id": 81,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 14,
                "home_goals_against": 12,
                "away_goals_for": 11,
                "away_goals_against": 15,
            },
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=standings
        )
        result = calculate_team_strengths(61)
        assert result is None

    @patch("models.stats_engine.supabase")
    def test_returns_strengths_for_valid_league(self, mock_sb):
        """4+ équipes → dict avec strengths, league averages."""
        standings = [
            {
                "team_api_id": 85,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 24,
                "home_goals_against": 8,
                "away_goals_for": 18,
                "away_goals_against": 12,
            },
            {
                "team_api_id": 33,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 15,
                "home_goals_against": 14,
                "away_goals_for": 10,
                "away_goals_against": 16,
            },
            {
                "team_api_id": 81,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 14,
                "home_goals_against": 12,
                "away_goals_for": 11,
                "away_goals_against": 15,
            },
            {
                "team_api_id": 95,
                "home_played": 12,
                "away_played": 12,
                "home_goals_for": 12,
                "home_goals_against": 18,
                "away_goals_for": 8,
                "away_goals_against": 20,
            },
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=standings
        )

        result = calculate_team_strengths(61)
        assert result is not None
        assert "strengths" in result
        assert "league_avg_home" in result
        assert "league_avg_away" in result
        assert 85 in result["strengths"]
        assert 95 in result["strengths"]

        # PSG (85) scores 24 home goals in 12 matches = 2.0/match
        # League avg home goals = (24+15+14+12)/(12*4) ≈ 1.354
        # home_attack ≈ 2.0 / 1.354 ≈ 1.48 → strong
        assert result["strengths"][85]["home_attack"] > 1.0

        # Team 95 scores 12 home goals in 12 = 1.0/match → below average
        assert result["strengths"][95]["home_attack"] < 1.0


# ═══════════════════════════════════════════════════════════════════
#  2. calculate_form
# ═══════════════════════════════════════════════════════════════════


class TestCalculateForm:
    """Tests de calculate_form avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_no_recent_matches_returns_default(self, mock_sb):
        """Aucun match récent → forme 0.5, lettres vides."""
        # Chain for home_only=True: table.rv.select.rv.eq.rv.order.rv.eq.rv.limit.rv.execute.rv
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        form, letters = calculate_form("PSG", home_only=True)
        assert form == 0.5
        assert letters == []

    @patch("models.stats_engine.supabase")
    def test_all_wins_gives_high_form(self, mock_sb):
        """3 victoires consécutives → forme ≈ 1.0."""
        results = [
            {
                "home_team": "PSG",
                "away_team": "Lyon",
                "home_goals": 3,
                "away_goals": 1,
                "date": "2026-02-01",
            },
            {
                "home_team": "PSG",
                "away_team": "Marseille",
                "home_goals": 2,
                "away_goals": 0,
                "date": "2026-01-25",
            },
            {
                "home_team": "PSG",
                "away_team": "Monaco",
                "home_goals": 1,
                "away_goals": 0,
                "date": "2026-01-18",
            },
        ]
        # Chain for home_only=True: .table().select().eq().order().eq().limit().execute()
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=results
        )

        form, letters = calculate_form("PSG", home_only=True)
        assert form > 0.8
        assert all(l == "W" for l in letters)
        assert len(letters) == 3

    @patch("models.stats_engine.supabase")
    def test_all_losses_gives_low_form(self, mock_sb):
        """3 défaites consécutives → forme ≈ 0.0."""
        results = [
            {
                "home_team": "Monaco",
                "away_team": "PSG",
                "home_goals": 2,
                "away_goals": 0,
                "date": "2026-02-01",
            },
            {
                "home_team": "PSG",
                "away_team": "Lyon",
                "home_goals": 0,
                "away_goals": 1,
                "date": "2026-01-25",
            },
            {
                "home_team": "Marseille",
                "away_team": "PSG",
                "home_goals": 3,
                "away_goals": 1,
                "date": "2026-01-18",
            },
        ]
        # Chain for home_only=None: .table().select().eq().order().or_().limit().execute()
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.or_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=results
        )

        form, letters = calculate_form("PSG", home_only=None)
        assert form < 0.2
        assert all(l == "L" for l in letters)


# ═══════════════════════════════════════════════════════════════════
#  3. calculate_rest_factor
# ═══════════════════════════════════════════════════════════════════


class TestCalculateRestFactor:
    """Tests de calculate_rest_factor avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_short_rest_fatigue(self, mock_sb):
        """2 jours de repos → facteur 0.92 (fatigue)."""
        # Query 1 (last match): .table().select().eq().or_().order().limit().execute()
        mock_sb.table.return_value.select.return_value.eq.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"date": "2026-02-13T20:00:00+00:00"}]
        )
        # Query 2 (congestion): .table().select().eq().or_().gte().execute()
        mock_sb.table.return_value.select.return_value.eq.return_value.or_.return_value.gte.return_value.execute.return_value = MagicMock(
            count=4
        )

        factor, rest_days, matches_30d = calculate_rest_factor("PSG", "2026-02-15T21:00:00+00:00")
        assert rest_days == 2
        assert factor == pytest.approx(0.92)
        assert matches_30d == 4

    @patch("models.stats_engine.supabase")
    def test_normal_rest_no_penalty(self, mock_sb):
        """6 jours de repos, peu de matchs → facteur 1.0."""
        mock_sb.table.return_value.select.return_value.eq.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"date": "2026-02-09T20:00:00+00:00"}]
        )
        mock_sb.table.return_value.select.return_value.eq.return_value.or_.return_value.gte.return_value.execute.return_value = MagicMock(
            count=3
        )

        factor, rest_days, matches_30d = calculate_rest_factor("PSG", "2026-02-15T21:00:00+00:00")
        assert rest_days == 6
        assert factor == pytest.approx(1.0)
        assert matches_30d == 3

    @patch("models.stats_engine.supabase")
    def test_heavy_congestion_penalty(self, mock_sb):
        """7 jours de repos mais 9 matchs en 30j → facteur 0.96."""
        mock_sb.table.return_value.select.return_value.eq.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"date": "2026-02-08T20:00:00+00:00"}]
        )
        mock_sb.table.return_value.select.return_value.eq.return_value.or_.return_value.gte.return_value.execute.return_value = MagicMock(
            count=9
        )

        factor, rest_days, matches_30d = calculate_rest_factor("PSG", "2026-02-15T21:00:00+00:00")
        assert rest_days == 7
        # 5-7 days → base 1.0, congestion > 8 → * 0.96
        assert factor == pytest.approx(0.96)
        assert matches_30d == 9


# ═══════════════════════════════════════════════════════════════════
#  4. calculate_stakes
# ═══════════════════════════════════════════════════════════════════

_FULL_STANDINGS = [
    {"team_api_id": 85, "rank": 1, "points": 55},
    {"team_api_id": 33, "rank": 2, "points": 54},
    {"team_api_id": 81, "rank": 3, "points": 50},
    {"team_api_id": 95, "rank": 4, "points": 45},
    {"team_api_id": 96, "rank": 5, "points": 40},
    {"team_api_id": 97, "rank": 6, "points": 38},
    {"team_api_id": 98, "rank": 7, "points": 35},
    {"team_api_id": 99, "rank": 8, "points": 30},
    {"team_api_id": 100, "rank": 9, "points": 28},
    {"team_api_id": 101, "rank": 10, "points": 25},
    {"team_api_id": 102, "rank": 11, "points": 23},
    {"team_api_id": 103, "rank": 12, "points": 20},
    {"team_api_id": 104, "rank": 13, "points": 18},
    {"team_api_id": 105, "rank": 14, "points": 16},
    {"team_api_id": 106, "rank": 15, "points": 14},
    {"team_api_id": 107, "rank": 16, "points": 12},
    {"team_api_id": 108, "rank": 17, "points": 10},
    {"team_api_id": 109, "rank": 18, "points": 8},
]


class TestCalculateStakes:
    """Tests de calculate_stakes avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_empty_standings_returns_default(self, mock_sb):
        """Classement vide → (1.0, 'inconnu')."""
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )
        factor, label = calculate_stakes(85, 61)
        assert factor == 1.0
        assert label == "inconnu"

    @patch("models.stats_engine.supabase")
    def test_title_contender_gets_boost(self, mock_sb):
        """Équipe 1ère (leader) → factor 1.08, label 'titre'."""
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=_FULL_STANDINGS
        )
        factor, label = calculate_stakes(85, 61)
        assert factor == 1.08
        assert label == "titre"

    @patch("models.stats_engine.supabase")
    def test_relegation_candidate_gets_boost(self, mock_sb):
        """Équipe 18ème, proche de la zone rouge → factor 1.06, label 'relégation'."""
        standings = [
            {"team_api_id": 85, "rank": 1, "points": 55},
            {"team_api_id": 33, "rank": 2, "points": 50},
            {"team_api_id": 81, "rank": 3, "points": 48},
            {"team_api_id": 95, "rank": 4, "points": 45},
            {"team_api_id": 96, "rank": 5, "points": 42},
            {"team_api_id": 97, "rank": 6, "points": 40},
            {"team_api_id": 98, "rank": 7, "points": 38},
            {"team_api_id": 99, "rank": 8, "points": 35},
            {"team_api_id": 100, "rank": 9, "points": 33},
            {"team_api_id": 101, "rank": 10, "points": 30},
            {"team_api_id": 102, "rank": 11, "points": 28},
            {"team_api_id": 103, "rank": 12, "points": 25},
            {"team_api_id": 104, "rank": 13, "points": 22},
            {"team_api_id": 105, "rank": 14, "points": 20},
            {"team_api_id": 106, "rank": 15, "points": 18},
            {"team_api_id": 107, "rank": 16, "points": 15},
            {"team_api_id": 108, "rank": 17, "points": 14},
            {"team_api_id": 109, "rank": 18, "points": 13},
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=standings
        )
        factor, label = calculate_stakes(109, 61)
        assert factor == 1.06
        assert label == "relégation"

    @patch("models.stats_engine.supabase")
    def test_midtable_team_gets_malus(self, mock_sb):
        """Équipe en milieu de tableau → factor 0.97, label 'milieu de tableau'."""
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=_FULL_STANDINGS
        )
        # team 100 is rank 9 out of 18 → middle third (7-12)
        factor, label = calculate_stakes(100, 61)
        assert factor == 0.97
        assert label == "milieu de tableau"


# ═══════════════════════════════════════════════════════════════════
#  5. get_h2h_factor
# ═══════════════════════════════════════════════════════════════════


class TestGetH2hFactor:
    """Tests de get_h2h_factor avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_no_h2h_returns_neutral(self, mock_sb):
        """Pas d'historique H2H → (1.0, 1.0, None)."""
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        h, a, data = get_h2h_factor(85, 33)
        assert h == 1.0
        assert a == 1.0
        assert data is None

    @patch("models.stats_engine.supabase")
    def test_dominant_h2h_gives_boost(self, mock_sb):
        """Équipe dominante en H2H → boost pour le dominant."""
        h2h_data = [
            {
                "team_a_api_id": 33,
                "team_b_api_id": 85,
                "total_matches": 10,
                "team_a_wins": 3,
                "team_b_wins": 5,
                "draws": 2,
            }
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=h2h_data
        )

        h, a, data = get_h2h_factor(85, 33)
        # sorted([85,33]) = [33,85] → team_a=33, team_b=85
        # home_team_id=85 is team_b → home_wr = team_b_wins/total = 5/10 = 0.5
        # away_wr = team_a_wins/total = 3/10 = 0.3
        assert h > 1.0  # 85 has winning record
        assert a < 1.0
        assert data is not None

    @patch("models.stats_engine.supabase")
    def test_balanced_h2h_stays_near_neutral(self, mock_sb):
        """H2H équilibré → facteurs proches de 1.0."""
        h2h_data = [
            {
                "team_a_api_id": 33,
                "team_b_api_id": 85,
                "total_matches": 12,
                "team_a_wins": 4,
                "team_b_wins": 4,
                "draws": 4,
            }
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=h2h_data
        )

        h, a, data = get_h2h_factor(85, 33)
        # home_wr = 4/12 = 0.333 ≈ 0.33 → factor ≈ 1.0 + (0.333 - 0.33)*0.15 ≈ 1.0005
        assert 0.99 < h < 1.01
        assert 0.99 < a < 1.01


# ═══════════════════════════════════════════════════════════════════
#  6. get_referee_impact
# ═══════════════════════════════════════════════════════════════════


class TestGetRefereeImpact:
    """Tests de get_referee_impact avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_no_referee_returns_none(self, mock_sb):
        """Pas de nom d'arbitre → None."""
        result = get_referee_impact(None)
        assert result is None

    @patch("models.stats_engine.supabase")
    def test_unknown_referee_returns_none(self, mock_sb):
        """Arbitre inconnu (pas dans la base) → None."""
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        result = get_referee_impact("Inconnu")
        assert result is None

    @patch("models.stats_engine.supabase")
    def test_known_referee_returns_stats(self, mock_sb):
        """Arbitre connu → dict avec avg_yellows, penalty_bias, etc."""
        ref_data = [
            {
                "name": "Turpin",
                "avg_yellows_per_match": 4.5,
                "avg_reds_per_match": 0.2,
                "avg_penalties_per_match": 0.35,
                "avg_fouls_per_match": 24.0,
                "matches_officiated": 50,
            }
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=ref_data)
        )
        result = get_referee_impact("Turpin")

        assert result is not None
        assert result["avg_yellows"] == 4.5
        assert result["avg_reds"] == 0.2
        assert result["avg_penalties"] == 0.35
        assert result["avg_fouls"] == 24.0
        assert result["matches"] == 50
        # penalty_bias = 0.35 / 0.3 ≈ 1.17 > 1.0
        assert result["penalty_bias"] > 1.0


# ═══════════════════════════════════════════════════════════════════
#  7. odds_to_probs
# ═══════════════════════════════════════════════════════════════════


class TestOddsToProbs:
    """Tests de odds_to_probs avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_no_odds_returns_none(self, mock_sb):
        """Pas de cotes disponibles → None."""
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        result = odds_to_probs(12345)
        assert result is None

    @patch("models.stats_engine.supabase")
    def test_valid_odds_returns_probs(self, mock_sb):
        """Cotes valides → probabilités normalisées proches de 100 %."""
        odds_data = [
            {
                "fixture_api_id": 12345,
                "home_win_odds": 1.5,
                "draw_odds": 4.0,
                "away_win_odds": 6.0,
            }
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=odds_data)
        )

        result = odds_to_probs(12345)
        assert result is not None
        total = result["market_home"] + result["market_draw"] + result["market_away"]
        assert 95 <= total <= 105
        assert result["market_home"] > result["market_away"]
        assert "overround" in result

    @patch("models.stats_engine.supabase")
    def test_odds_without_home_win_returns_none(self, mock_sb):
        """Cotes présentes mais home_win_odds manquant → None."""
        odds_data = [
            {
                "fixture_api_id": 99999,
                "home_win_odds": None,
                "draw_odds": 3.5,
                "away_win_odds": 2.0,
            }
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=odds_data)
        )

        result = odds_to_probs(99999)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
#  8. get_injury_impact
# ═══════════════════════════════════════════════════════════════════


class TestGetInjuryImpact:
    """Tests de get_injury_impact avec mock Supabase."""

    @patch("models.stats_engine.supabase")
    def test_no_injuries_returns_neutral(self, mock_sb):
        """Aucun blessé → (1.0, 1.0, [])."""
        # injuries table: .table().select().eq().execute()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        # players table with eq.eq: .table().select().eq().eq().execute()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        atk, dfn, details = get_injury_impact(85)
        assert atk == 1.0
        assert dfn == 1.0
        assert details == []

    @patch("models.stats_engine.supabase")
    def test_critical_attacker_reduces_attack(self, mock_sb):
        """Attaquant star blessé → atk_factor < 1.0, impact CRITIQUE."""
        injuries = [
            {
                "player_api_id": 1100,
                "player_name": "Mbappé",
                "reason": "Hamstring",
                "type": "Missing Fixture",
            },
        ]
        players = [
            {"api_id": 1100, "name": "Mbappé", "position": "Attacker"},
        ]
        all_stats = [
            {
                "player_api_id": 1100,
                "goals": 25,
                "assists": 7,
                "minutes_played": 2000,
                "rating": 7.8,
                "goals_conceded": 0,
                "saves": 0,
                "clean_sheets": 0,
                "shots_on_target": 50,
                "passes_key": 20,
                "penalty_scored": 1,
                "penalty_missed": 0,
            },
            {
                "player_api_id": 1200,
                "goals": 10,
                "assists": 5,
                "minutes_played": 1800,
                "rating": 6.5,
                "goals_conceded": 0,
                "saves": 0,
                "clean_sheets": 0,
                "shots_on_target": 30,
                "passes_key": 10,
                "penalty_scored": 0,
                "penalty_missed": 0,
            },
            {
                "player_api_id": 1300,
                "goals": 5,
                "assists": 8,
                "minutes_played": 1600,
                "rating": 6.2,
                "goals_conceded": 0,
                "saves": 0,
                "clean_sheets": 0,
                "shots_on_target": 15,
                "passes_key": 25,
                "penalty_scored": 0,
                "penalty_missed": 0,
            },
        ]
        _route_tables(
            mock_sb,
            {
                "injuries": injuries,
                "players": players,
                "player_season_stats": all_stats,
            },
        )

        atk, dfn, details = get_injury_impact(85)
        # team_total_goals = 25+10+5 = 40
        # goal_share = 25/40 = 0.625 ≥ 0.30 → impact_attack = 0.20 + 0.03 (pen) = 0.23
        # attack_factor = max(0.70, 1.0 - 0.23) = 0.77
        assert atk < 1.0
        assert dfn == 1.0  # Attacker injury doesn't affect defense
        assert len(details) == 1
        assert details[0]["impact"] == "CRITIQUE"
        assert details[0]["player_name"] == "Mbappé"


# ═══════════════════════════════════════════════════════════════════
#  9. calculate_penalty_proba
# ═══════════════════════════════════════════════════════════════════


class TestCalculatePenaltyProba:
    """Tests de calculate_penalty_proba."""

    @patch("models.stats_engine.supabase")
    def test_base_rate_without_extras(self, mock_sb):
        """Pas d'arbitre, pas d'équipes → proba basée sur le taux moyen."""
        proba, lam, details = calculate_penalty_proba(
            fixture={},
            referee_impact=None,
            stakes_home=1.0,
            stakes_away=1.0,
            home_id=None,
            away_id=None,
        )
        # lambda = BASE_PENALTY_RATE = 0.30
        # proba = (1 - exp(-0.30)) * 100 ≈ 26 %
        assert proba == round((1 - math.exp(-0.30)) * 100)
        assert "base_rate" in details

    @patch("models.stats_engine.supabase")
    def test_high_penalty_referee_boosts_proba(self, mock_sb):
        """Arbitre sévère (0.6 pen/match) → proba nettement plus élevée."""
        ref_impact = {
            "avg_yellows": 5.0,
            "avg_reds": 0.3,
            "avg_penalties": 0.6,
            "avg_fouls": 25.0,
            "penalty_bias": 2.0,
            "matches": 50,
        }
        proba, lam, details = calculate_penalty_proba(
            fixture={},
            referee_impact=ref_impact,
            stakes_home=1.0,
            stakes_away=1.0,
            home_id=None,
            away_id=None,
        )
        # ref_factor = 0.6 / 0.30 = 2.0
        # lambda = 0.30 * 2.0 = 0.60
        # proba = (1 - exp(-0.60)) * 100 ≈ 45 %
        base_proba = round((1 - math.exp(-0.30)) * 100)
        assert proba > base_proba
        assert details.get("referee_factor") == 2.0

    @patch("models.stats_engine.supabase")
    def test_high_stakes_boosts_proba(self, mock_sb):
        """Match à gros enjeu (stakes > 1.05) → stakes_factor = 1.15."""
        proba, lam, details = calculate_penalty_proba(
            fixture={},
            referee_impact=None,
            stakes_home=1.08,
            stakes_away=1.06,
            home_id=None,
            away_id=None,
        )
        # avg_stakes = (1.08 + 1.06) / 2 = 1.07 > 1.05 → stakes_factor = 1.15
        assert details.get("stakes_factor") == 1.15
        assert proba >= 26  # Higher than base ~26 %


# ═══════════════════════════════════════════════════════════════════
#  10. analyze_match (intégration)
# ═══════════════════════════════════════════════════════════════════


class TestAnalyzeMatch:
    """Test d'intégration de analyze_match avec mocks complets."""

    @patch("models.stats_engine.CALIBRATION_AVAILABLE", False)
    @patch("models.stats_engine.ML_AVAILABLE", False)
    @patch("models.stats_engine.supabase")
    def test_full_analysis_returns_expected_structure(self, mock_sb):
        """analyze_match renvoie un dict complet avec probas 1X2, xG, etc."""
        fixture = {
            "home_team": "Paris Saint Germain",
            "away_team": "Olympique De Marseille",
            "league_id": 61,
            "date": "2026-02-15T21:00:00+00:00",
            "api_fixture_id": 12345,
            "referee_name": "Letexier",
            "weather_json": {"temp": 8, "wind_speed": 5, "rain_mm": 0},
        }
        standings = [
            {
                "team_api_id": 85,
                "home_played": 12,
                "away_played": 12,
                "rank": 1,
                "points": 55,
                "home_goals_for": 24,
                "home_goals_against": 8,
                "away_goals_for": 18,
                "away_goals_against": 12,
            },
            {
                "team_api_id": 33,
                "home_played": 12,
                "away_played": 12,
                "rank": 5,
                "points": 38,
                "home_goals_for": 15,
                "home_goals_against": 14,
                "away_goals_for": 10,
                "away_goals_against": 16,
            },
            {
                "team_api_id": 81,
                "home_played": 12,
                "away_played": 12,
                "rank": 3,
                "points": 48,
                "home_goals_for": 14,
                "home_goals_against": 12,
                "away_goals_for": 11,
                "away_goals_against": 15,
            },
            {
                "team_api_id": 95,
                "home_played": 12,
                "away_played": 12,
                "rank": 4,
                "points": 45,
                "home_goals_for": 12,
                "home_goals_against": 18,
                "away_goals_for": 8,
                "away_goals_against": 20,
            },
        ]
        fixtures_data = [
            {
                "home_team": "Paris Saint Germain",
                "away_team": "Lyon",
                "home_goals": 2,
                "away_goals": 1,
                "date": "2026-02-08T20:00:00+00:00",
                "id": 1,
                "status": "FT",
            },
        ]
        _route_tables(
            mock_sb,
            {
                "teams": [
                    {"api_id": 85, "name": "Paris Saint Germain"},
                    {"api_id": 33, "name": "Olympique De Marseille"},
                ],
                "team_standings": standings,
                "fixtures": fixtures_data,
                "h2h_cache": [],
                "injuries": [],
                "players": [],
                "player_season_stats": [],
                "referees": [],
                "team_elo": [
                    {"team_api_id": 85, "elo_rating": 1650},
                    {"team_api_id": 33, "elo_rating": 1420},
                ],
                "fixture_odds": [],
            },
        )

        result = analyze_match(fixture)

        # ── Structure checks ──
        assert isinstance(result, dict)
        for key in (
            "proba_home",
            "proba_draw",
            "proba_away",
            "proba_btts",
            "proba_over_05",
            "proba_over_15",
            "proba_over_25",
            "proba_over_35",
            "proba_penalty",
            "proba_dc_1x",
            "proba_dc_x2",
            "proba_dc_12",
            "correct_score",
            "proba_correct_score",
            "xg_home",
            "xg_away",
            "model_version",
            "context",
            "recommended_bet",
            "confidence_score",
        ):
            assert key in result, f"Missing key: {key}"

        # ── Probability sanity checks ──
        assert result["proba_home"] + result["proba_draw"] + result["proba_away"] == 100
        assert 0 <= result["proba_btts"] <= 100
        assert 0 <= result["proba_over_25"] <= 100
        assert 5 <= result["proba_penalty"] <= 65  # Capped by the engine
        assert result["xg_home"] > 0
        assert result["xg_away"] > 0
        assert 1 <= result["confidence_score"] <= 10

        # Double chance consistency
        assert result["proba_dc_1x"] == result["proba_home"] + result["proba_draw"]
        assert result["proba_dc_x2"] == result["proba_draw"] + result["proba_away"]
        assert result["proba_dc_12"] == result["proba_home"] + result["proba_away"]

        # Without ML/calibration
        assert result["model_version"] == "hybrid_v1"
