"""
Tests d'intégration (avec mocks Supabase) pour scorer_engine.py.

Chaque test mocke le client Supabase au niveau du module scorer_engine
et réinitialise les caches globaux pour garantir l'indépendance.
"""

from unittest.mock import MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════
#  HELPERS : MOCK CHAIN BUILDER
# ═══════════════════════════════════════════════════════════════════


def _make_chain(data=None, count=None):
    """Return a MagicMock that supports arbitrary Supabase chain calls.

    Every chained method (.select, .eq, .or_, .in_, .filter, .order,
    .limit, .neq, .gt, .gte, .lt, .lte) returns the same mock so that
    ``mock.table("x").select("...").eq("k", v).execute()`` works.

    ``.execute()`` returns a result object with ``.data`` and ``.count``.
    """
    chain = MagicMock()
    result = MagicMock()
    result.data = data if data is not None else []
    result.count = count
    # Every chainable method returns the same chain
    for method in (
        "select",
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "in_",
        "or_",
        "filter",
        "order",
        "limit",
        "insert",
        "upsert",
        "update",
        "delete",
    ):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = result
    return chain


def _route_tables(table_map: dict[str, MagicMock]):
    """Build a ``table()`` side-effect that routes by table name.

    Args:
        table_map: ``{"table_name": chain_mock, ...}``.
    """

    def _side_effect(name):
        return table_map.get(name, _make_chain())

    return _side_effect


# ═══════════════════════════════════════════════════════════════════
#  TEAM NAME / ID CACHE
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetTeamNameId:
    """Tests for get_team_name and get_team_id with cache behaviour."""

    def test_get_team_name_loads_cache_and_returns(self, mock_sb):
        from models.scorer_engine import get_team_name

        mock_sb.table.return_value = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
                {"api_id": 33, "name": "Olympique De Marseille"},
            ]
        )

        assert get_team_name(85) == "Paris Saint Germain"
        # Second call should NOT trigger another DB query (cached)
        assert get_team_name(33) == "Olympique De Marseille"
        # table() called only once to populate cache
        assert mock_sb.table.call_count == 1

    def test_get_team_name_unknown_id_returns_unknown(self, mock_sb):
        from models.scorer_engine import get_team_name

        mock_sb.table.return_value = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )

        assert get_team_name(9999) == "Unknown"

    def test_get_team_id_returns_correct_id(self, mock_sb):
        from models.scorer_engine import get_team_id

        mock_sb.table.return_value = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
                {"api_id": 33, "name": "Olympique De Marseille"},
            ]
        )

        assert get_team_id("Olympique De Marseille") == 33

    def test_get_team_id_unknown_name_returns_none(self, mock_sb):
        from models.scorer_engine import get_team_id

        mock_sb.table.return_value = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )

        assert get_team_id("Team Inconnu") is None


# ═══════════════════════════════════════════════════════════════════
#  SCORING RATE
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetScoringRate:
    """Tests for get_scoring_rate aggregation logic."""

    def test_no_stats_returns_none(self, mock_sb):
        from models.scorer_engine import get_scoring_rate

        mock_sb.table.return_value = _make_chain(data=[])
        assert get_scoring_rate(1100) is None

    def test_below_90_minutes_returns_none(self, mock_sb):
        from models.scorer_engine import get_scoring_rate

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals": 1,
                    "assists": 0,
                    "shots_total": 5,
                    "shots_on_target": 2,
                    "minutes_played": 60,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 1,
                },
            ]
        )
        assert get_scoring_rate(1100) is None

    def test_valid_stats_computation(self, mock_sb):
        from models.scorer_engine import get_scoring_rate

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals": 10,
                    "assists": 5,
                    "shots_total": 50,
                    "shots_on_target": 25,
                    "minutes_played": 1800,
                    "penalty_scored": 2,
                    "penalty_missed": 1,
                    "appearances": 20,
                },
            ]
        )

        rate = get_scoring_rate(1100)
        assert rate is not None
        assert rate["total_goals"] == 10
        assert rate["total_assists"] == 5
        assert rate["minutes"] == 1800
        assert rate["appearances"] == 20
        # goals_per_90 = 10 * (90/1800) = 0.5
        assert rate["goals_per_90"] == 0.5
        # is_penalty_taker: 2 + 1 >= 2 → True
        assert rate["is_penalty_taker"] is True
        # conversion_rate = 10 / 25 = 0.4
        assert rate["conversion_rate"] == pytest.approx(0.4)

    def test_aggregates_multiple_competitions(self, mock_sb):
        from models.scorer_engine import get_scoring_rate

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals": 8,
                    "assists": 3,
                    "shots_total": 40,
                    "shots_on_target": 20,
                    "minutes_played": 1200,
                    "penalty_scored": 1,
                    "penalty_missed": 0,
                    "appearances": 14,
                },
                {
                    "goals": 2,
                    "assists": 1,
                    "shots_total": 10,
                    "shots_on_target": 5,
                    "minutes_played": 300,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 4,
                },
            ]
        )

        rate = get_scoring_rate(1100)
        assert rate is not None
        assert rate["total_goals"] == 10
        assert rate["minutes"] == 1500
        # goals_per_90 = 10 * 90/1500 = 0.6
        assert rate["goals_per_90"] == 0.6
        # pen_scored + pen_missed = 1 < 2 → not penalty taker
        assert rate["is_penalty_taker"] is False

    def test_none_values_treated_as_zero(self, mock_sb):
        from models.scorer_engine import get_scoring_rate

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals": None,
                    "assists": None,
                    "shots_total": None,
                    "shots_on_target": None,
                    "minutes_played": 900,
                    "penalty_scored": None,
                    "penalty_missed": None,
                    "appearances": 10,
                },
            ]
        )

        rate = get_scoring_rate(1100)
        assert rate is not None
        assert rate["total_goals"] == 0
        assert rate["goals_per_90"] == 0.0
        assert rate["conversion_rate"] == 0.0


# ═══════════════════════════════════════════════════════════════════
#  DEFENSE QUALITY
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetDefenseQuality:
    """Tests for get_defense_quality — opponent defence factor."""

    def test_no_standings_returns_neutral(self, mock_sb):
        from models.scorer_engine import get_defense_quality

        mock_sb.table.return_value = _make_chain(data=[])
        factor, info = get_defense_quality(33, is_opponent_home=True)
        assert factor == 1.0
        assert info is None

    def test_few_games_returns_neutral(self, mock_sb):
        from models.scorer_engine import get_defense_quality

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals_against": 3,
                    "played": 2,
                    "home_goals_against": 1,
                    "home_played": 1,
                    "away_goals_against": 2,
                    "away_played": 1,
                },
            ]
        )
        factor, info = get_defense_quality(33, is_opponent_home=False)
        assert factor == 1.0
        assert info is None

    def test_bad_defense_high_factor(self, mock_sb):
        """A leaky defence conceding 2.0 GA/game → factor > 1.0."""
        from models.scorer_engine import get_defense_quality

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals_against": 40,
                    "played": 20,
                    "home_goals_against": 20,
                    "home_played": 10,
                    "away_goals_against": 20,
                    "away_played": 10,
                },
            ]
        )
        factor, info = get_defense_quality(33, is_opponent_home=True)
        # context_ga_pm = 20/10 = 2.0 ; factor = 2.0 / 1.25 = 1.6
        assert factor > 1.0
        assert info is not None
        assert info["context_ga_pm"] == 2.0

    def test_good_defense_low_factor(self, mock_sb):
        """A solid defence conceding 0.5 GA/game → factor < 1.0."""
        from models.scorer_engine import get_defense_quality

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals_against": 10,
                    "played": 20,
                    "home_goals_against": 5,
                    "home_played": 10,
                    "away_goals_against": 5,
                    "away_played": 10,
                },
            ]
        )
        factor, info = get_defense_quality(33, is_opponent_home=False)
        # context_ga_pm = 5/10 = 0.5 ; factor = 0.5/1.25 = 0.4 → clamped to 0.6
        assert factor < 1.0
        assert factor >= 0.6  # floor

    def test_factor_clamped_to_ceil(self, mock_sb):
        """Factor should not exceed DEFENSE_FACTOR_CEIL (1.6)."""
        from models.scorer_engine import get_defense_quality

        mock_sb.table.return_value = _make_chain(
            data=[
                {
                    "goals_against": 80,
                    "played": 20,
                    "home_goals_against": 40,
                    "home_played": 10,
                    "away_goals_against": 40,
                    "away_played": 10,
                },
            ]
        )
        factor, _ = get_defense_quality(33, is_opponent_home=True)
        assert factor <= 1.6


# ═══════════════════════════════════════════════════════════════════
#  OPPONENT GK FACTOR
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetOpponentGkFactor:
    """Tests for get_opponent_gk_factor."""

    def test_no_goalkeeper_returns_neutral(self, mock_sb):
        from models.scorer_engine import get_opponent_gk_factor

        # players table returns no GK; stats irrelevant
        players_chain = _make_chain(data=[])
        mock_sb.table.return_value = players_chain

        factor, info = get_opponent_gk_factor(33)
        assert factor == 1.0
        assert info is None

    def test_no_gk_with_enough_minutes_returns_neutral(self, mock_sb):
        from models.scorer_engine import get_opponent_gk_factor

        players_chain = _make_chain(data=[{"api_id": 500}])
        stats_chain = _make_chain(
            data=[
                {
                    "player_api_id": 500,
                    "goals_conceded": 5,
                    "saves": 20,
                    "minutes_played": 100,
                    "rating": 6.5,
                },
            ]
        )

        call_count = [0]

        def table_router(name):
            call_count[0] += 1
            if name == "players":
                return players_chain
            return stats_chain

        mock_sb.table.side_effect = table_router

        factor, info = get_opponent_gk_factor(33)
        # 100 minutes < 200 → no valid candidate
        assert factor == 1.0
        assert info is None

    def test_good_gk_factor_below_one(self, mock_sb):
        """A strong GK (high save rate, low conceded) → factor < 1.0."""
        from models.scorer_engine import get_opponent_gk_factor

        players_chain = _make_chain(data=[{"api_id": 500}])
        stats_chain = _make_chain(
            data=[
                {
                    "player_api_id": 500,
                    "goals_conceded": 10,
                    "saves": 80,
                    "minutes_played": 2700,
                    "rating": 7.2,
                },
            ]
        )

        def table_router(name):
            if name == "players":
                return players_chain
            return stats_chain

        mock_sb.table.side_effect = table_router

        factor, info = get_opponent_gk_factor(33)
        # conceded_per_90 = 10*90/2700 ≈ 0.333
        # save_rate = 80/90 ≈ 0.889
        # gk_factor = (0.333/1.1)*0.6 + ((1 - 0.889)/(1 - 0.70))*0.4
        #           ≈ 0.182 + 0.148 = 0.33 → clamped to 0.7
        assert factor < 1.0
        assert info is not None
        assert info["save_rate"] > 80

    def test_bad_gk_factor_above_one(self, mock_sb):
        """A weak GK (low save rate, high conceded) → factor > 1.0."""
        from models.scorer_engine import get_opponent_gk_factor

        players_chain = _make_chain(data=[{"api_id": 500}])
        stats_chain = _make_chain(
            data=[
                {
                    "player_api_id": 500,
                    "goals_conceded": 45,
                    "saves": 40,
                    "minutes_played": 2700,
                    "rating": 6.0,
                },
            ]
        )

        def table_router(name):
            if name == "players":
                return players_chain
            return stats_chain

        mock_sb.table.side_effect = table_router

        factor, info = get_opponent_gk_factor(33)
        # conceded_per_90 = 45*90/2700 = 1.5
        # save_rate = 40/85 ≈ 0.47
        # gk_factor = (1.5/1.1)*0.6 + ((1 - 0.47)/(1 - 0.70))*0.4
        #           ≈ 0.818 + 0.707 ≈ 1.525 → clamped to 1.4
        assert factor > 1.0
        assert info is not None


# ═══════════════════════════════════════════════════════════════════
#  GOALS VS TEAM
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetGoalsVsTeam:
    """Tests for get_goals_vs_team."""

    def test_no_fixtures_returns_zero(self, mock_sb):
        from models.scorer_engine import get_goals_vs_team

        # teams table for get_team_name
        teams_chain = _make_chain(
            data=[
                {"api_id": 33, "name": "Olympique De Marseille"},
            ]
        )
        fixtures_chain = _make_chain(data=[])

        def table_router(name):
            if name == "teams":
                return teams_chain
            return fixtures_chain

        mock_sb.table.side_effect = table_router

        goals, matches = get_goals_vs_team(1100, 33)
        assert goals == 0
        assert matches == 0

    def test_with_goals_against_opponent(self, mock_sb):
        from models.scorer_engine import get_goals_vs_team

        teams_chain = _make_chain(
            data=[
                {"api_id": 33, "name": "Olympique De Marseille"},
            ]
        )
        fixtures_home_chain = _make_chain(
            data=[
                {"api_fixture_id": 101},
                {"api_fixture_id": 102},
            ]
        )
        fixtures_away_chain = _make_chain(
            data=[
                {"api_fixture_id": 103},
            ]
        )
        goals_chain = _make_chain(data=[{"id": 1}], count=2)

        call_idx = [0]
        fixture_calls = [fixtures_home_chain, fixtures_away_chain]

        def table_router(name):
            if name == "teams":
                return teams_chain
            if name == "fixtures":
                idx = min(call_idx[0], len(fixture_calls) - 1)
                result = fixture_calls[idx]
                call_idx[0] += 1
                return result
            if name == "match_events":
                return goals_chain
            return _make_chain()

        mock_sb.table.side_effect = table_router

        goals, matches = get_goals_vs_team(1100, 33)
        assert goals == 2
        assert matches == 3  # 2 home + 1 away


# ═══════════════════════════════════════════════════════════════════
#  PLAYER SYNERGIES
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetPlayerSynergies:
    """Tests for get_player_synergies."""

    def test_no_events_returns_empty(self, mock_sb):
        from models.scorer_engine import get_player_synergies

        mock_sb.table.return_value = _make_chain(data=[])
        result = get_player_synergies(85)
        assert result == []

    def test_with_assist_pairs(self, mock_sb):
        from models.scorer_engine import get_player_synergies

        events = [
            {
                "player_api_id": 1100,
                "player_name": "Mbappé",
                "assist_player_api_id": 1200,
                "assist_player_name": "Dembélé",
            },
            {
                "player_api_id": 1100,
                "player_name": "Mbappé",
                "assist_player_api_id": 1200,
                "assist_player_name": "Dembélé",
            },
            {
                "player_api_id": 1100,
                "player_name": "Mbappé",
                "assist_player_api_id": 1300,
                "assist_player_name": "Vitinha",
            },
        ]
        mock_sb.table.return_value = _make_chain(data=events)

        result = get_player_synergies(85)
        assert len(result) == 2
        # Sorted by count descending
        assert result[0]["count"] == 2
        assert result[0]["assister_name"] == "Dembélé"
        assert result[0]["scorer_name"] == "Mbappé"
        assert result[1]["count"] == 1

    def test_skips_events_without_ids(self, mock_sb):
        from models.scorer_engine import get_player_synergies

        events = [
            {
                "player_api_id": None,
                "player_name": "?",
                "assist_player_api_id": 1200,
                "assist_player_name": "Dembélé",
            },
            {
                "player_api_id": 1100,
                "player_name": "Mbappé",
                "assist_player_api_id": None,
                "assist_player_name": None,
            },
        ]
        mock_sb.table.return_value = _make_chain(data=events)

        result = get_player_synergies(85)
        assert result == []


# ═══════════════════════════════════════════════════════════════════
#  INJURED IDS
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestGetInjuredIds:
    """Tests for _get_injured_ids."""

    def test_no_injuries_returns_empty(self, mock_sb):
        from models.scorer_engine import _get_injured_ids

        teams_chain = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )
        fixtures_chain = _make_chain(data=[])
        players_chain = _make_chain(data=[])

        def table_router(name):
            if name == "teams":
                return teams_chain
            if name == "fixtures":
                return fixtures_chain
            if name == "players":
                return players_chain
            return _make_chain()

        mock_sb.table.side_effect = table_router

        result = _get_injured_ids(85)
        assert result == set()

    def test_with_injuries_from_injuries_table(self, mock_sb):
        from models.scorer_engine import _get_injured_ids

        teams_chain = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )
        fixtures_chain = _make_chain(
            data=[
                {"api_fixture_id": 201},
            ]
        )
        injuries_chain = _make_chain(
            data=[
                {"player_api_id": 1100},
                {"player_api_id": 1200},
            ]
        )
        players_chain = _make_chain(data=[])

        def table_router(name):
            if name == "teams":
                return teams_chain
            if name == "fixtures":
                return fixtures_chain
            if name == "injuries":
                return injuries_chain
            if name == "players":
                return players_chain
            return _make_chain()

        mock_sb.table.side_effect = table_router

        result = _get_injured_ids(85)
        assert 1100 in result
        assert 1200 in result

    def test_with_is_injured_flag_on_players(self, mock_sb):
        from models.scorer_engine import _get_injured_ids

        teams_chain = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )
        fixtures_chain = _make_chain(data=[])
        players_chain = _make_chain(
            data=[
                {"api_id": 1300},
            ]
        )

        def table_router(name):
            if name == "teams":
                return teams_chain
            if name == "fixtures":
                return fixtures_chain
            if name == "players":
                return players_chain
            return _make_chain()

        mock_sb.table.side_effect = table_router

        result = _get_injured_ids(85)
        assert 1300 in result

    def test_combines_both_injury_sources(self, mock_sb):
        from models.scorer_engine import _get_injured_ids

        teams_chain = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )
        fixtures_chain = _make_chain(data=[{"api_fixture_id": 201}])
        injuries_chain = _make_chain(data=[{"player_api_id": 1100}])
        players_chain = _make_chain(data=[{"api_id": 1300}])

        def table_router(name):
            if name == "teams":
                return teams_chain
            if name == "fixtures":
                return fixtures_chain
            if name == "injuries":
                return injuries_chain
            if name == "players":
                return players_chain
            return _make_chain()

        mock_sb.table.side_effect = table_router

        result = _get_injured_ids(85)
        assert result == {1100, 1300}


# ═══════════════════════════════════════════════════════════════════
#  _RANK_SCORERS
# ═══════════════════════════════════════════════════════════════════


def _build_rank_scorers_tables(
    *,
    team_players=None,
    team_standings=None,
    gk_players=None,
    gk_stats=None,
    synergy_events=None,
    injured_fixtures=None,
    injured_players=None,
    injuries=None,
    opp_fixtures_home=None,
    opp_fixtures_away=None,
    opp_goals_events=None,
    recent_fixtures=None,
    recent_goals=None,
    recent_lineups=None,
    player_stats_map=None,
    teams=None,
):
    """Build a table router for _rank_scorers with reasonable defaults.

    Call order inside ``_rank_scorers`` (determines counter values):

    **players** table:
      [0] team players  (``_rank_scorers`` main query)
      [1] injured flag  (``_get_injured_ids`` → ``is_injured`` flag)
      [2] GK ids        (``get_opponent_gk_factor``)

    **player_season_stats** table:
      [0] GK stats      (``get_opponent_gk_factor``, **only if** gk_players)
      [1+] per-player   (``get_scoring_rate`` for each outfield player)

    **fixtures** table:
      [0] upcoming       (``_get_injured_ids``)
      [1] opp home       (``_rank_scorers`` — goals-vs pre-load)
      [2] opp away       (``_rank_scorers`` — goals-vs pre-load)
      [3] recent          (``_rank_scorers`` — recent-form pre-load)

    **match_events** table:
      [0] synergy events (``get_player_synergies``)
      [1] goals-vs opp   (``_rank_scorers`` — only if opp_fixture_ids)
      [2] recent goals   (``_rank_scorers`` — only if recent_fids)
    """
    if teams is None:
        teams = [
            {"api_id": 85, "name": "Paris Saint Germain"},
            {"api_id": 33, "name": "Olympique De Marseille"},
        ]
    if team_players is None:
        team_players = []
    if team_standings is None:
        team_standings = []
    if gk_players is None:
        gk_players = []
    if gk_stats is None:
        gk_stats = []
    if synergy_events is None:
        synergy_events = []
    if injured_fixtures is None:
        injured_fixtures = []
    if injured_players is None:
        injured_players = []
    if injuries is None:
        injuries = []
    if opp_fixtures_home is None:
        opp_fixtures_home = []
    if opp_fixtures_away is None:
        opp_fixtures_away = []
    if opp_goals_events is None:
        opp_goals_events = []
    if recent_fixtures is None:
        recent_fixtures = []
    if recent_goals is None:
        recent_goals = []
    if recent_lineups is None:
        recent_lineups = []
    if player_stats_map is None:
        player_stats_map = {}

    players_call = [0]
    fixtures_call = [0]
    events_call = [0]
    stats_call = [0]

    def table_router(name):
        if name == "teams":
            return _make_chain(data=teams)

        if name == "players":
            c = players_call[0]
            players_call[0] += 1
            if c == 0:
                return _make_chain(data=team_players)
            elif c == 1:
                # _get_injured_ids → is_injured flag query
                return _make_chain(data=injured_players)
            elif c == 2:
                # get_opponent_gk_factor → GK ids
                return _make_chain(data=gk_players)
            return _make_chain(data=[])

        if name == "team_standings":
            return _make_chain(data=team_standings)

        if name == "player_season_stats":
            c = stats_call[0]
            stats_call[0] += 1
            # GK stats call only happens when gk_players is non-empty
            if gk_players and c == 0:
                return _make_chain(data=gk_stats)
            else:
                offset = 1 if gk_players else 0
                keys = list(player_stats_map.keys())
                idx = c - offset
                if 0 <= idx < len(keys):
                    return _make_chain(data=player_stats_map[keys[idx]])
                return _make_chain(data=[])

        if name == "match_events":
            c = events_call[0]
            events_call[0] += 1
            if c == 0:
                return _make_chain(data=synergy_events)
            elif c == 1:
                return _make_chain(data=opp_goals_events)
            elif c == 2:
                return _make_chain(data=recent_goals)
            return _make_chain(data=[])

        if name == "match_lineups":
            return _make_chain(data=recent_lineups)

        if name == "fixtures":
            c = fixtures_call[0]
            fixtures_call[0] += 1
            if c == 0:
                return _make_chain(data=injured_fixtures)
            elif c == 1:
                return _make_chain(data=opp_fixtures_home)
            elif c == 2:
                return _make_chain(data=opp_fixtures_away)
            elif c == 3:
                return _make_chain(data=recent_fixtures)
            return _make_chain(data=[])

        if name == "injuries":
            return _make_chain(data=injuries)

        return _make_chain()

    return table_router


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestRankScorers:
    """Tests for _rank_scorers — main ranking engine."""

    def test_ranking_order_by_score(self, mock_sb):
        from models.scorer_engine import _rank_scorers

        # Two forwards with different goal records
        team_players = [
            {"api_id": 1100, "name": "Star Striker", "position": "Attacker"},
            {"api_id": 1200, "name": "Backup Forward", "position": "Attacker"},
        ]
        player_stats_map = {
            1100: [
                {
                    "goals": 15,
                    "assists": 5,
                    "shots_total": 60,
                    "shots_on_target": 30,
                    "minutes_played": 1800,
                    "penalty_scored": 2,
                    "penalty_missed": 0,
                    "appearances": 20,
                }
            ],
            1200: [
                {
                    "goals": 3,
                    "assists": 2,
                    "shots_total": 20,
                    "shots_on_target": 8,
                    "minutes_played": 900,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 12,
                }
            ],
        }

        router = _build_rank_scorers_tables(
            team_players=team_players,
            player_stats_map=player_stats_map,
        )
        mock_sb.table.side_effect = router

        scorers = _rank_scorers(85, 33, team_xg=1.5, is_opponent_home=False)
        assert len(scorers) >= 1
        # Star Striker (more goals) should be ranked first
        assert scorers[0]["name"] == "Star Striker"

    def test_goalkeepers_excluded(self, mock_sb):
        from models.scorer_engine import _rank_scorers

        team_players = [
            {"api_id": 500, "name": "The Goalkeeper", "position": "Goalkeeper"},
            {"api_id": 1100, "name": "Forward", "position": "Attacker"},
        ]
        player_stats_map = {
            1100: [
                {
                    "goals": 10,
                    "assists": 3,
                    "shots_total": 40,
                    "shots_on_target": 20,
                    "minutes_played": 1800,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 20,
                }
            ],
        }

        router = _build_rank_scorers_tables(
            team_players=team_players,
            player_stats_map=player_stats_map,
        )
        mock_sb.table.side_effect = router

        scorers = _rank_scorers(85, 33, team_xg=1.5, is_opponent_home=False)
        names = [s["name"] for s in scorers]
        assert "The Goalkeeper" not in names

    def test_injured_players_excluded(self, mock_sb):
        from models.scorer_engine import _rank_scorers

        team_players = [
            {"api_id": 1100, "name": "Healthy Player", "position": "Attacker"},
            {"api_id": 1200, "name": "Injured Player", "position": "Attacker"},
        ]
        player_stats_map = {
            1100: [
                {
                    "goals": 10,
                    "assists": 3,
                    "shots_total": 40,
                    "shots_on_target": 20,
                    "minutes_played": 1800,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 20,
                }
            ],
            1200: [
                {
                    "goals": 12,
                    "assists": 5,
                    "shots_total": 50,
                    "shots_on_target": 25,
                    "minutes_played": 1800,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 20,
                }
            ],
        }

        router = _build_rank_scorers_tables(
            team_players=team_players,
            player_stats_map=player_stats_map,
            injured_players=[{"api_id": 1200}],  # Injured Player flagged
        )
        mock_sb.table.side_effect = router

        scorers = _rank_scorers(85, 33, team_xg=1.5, is_opponent_home=False)
        names = [s["name"] for s in scorers]
        assert "Injured Player" not in names
        assert "Healthy Player" in names

    def test_proba_field_is_bounded(self, mock_sb):
        from models.scorer_engine import _rank_scorers

        team_players = [
            {"api_id": 1100, "name": "Forward", "position": "Attacker"},
        ]
        player_stats_map = {
            1100: [
                {
                    "goals": 20,
                    "assists": 8,
                    "shots_total": 80,
                    "shots_on_target": 40,
                    "minutes_played": 1800,
                    "penalty_scored": 3,
                    "penalty_missed": 1,
                    "appearances": 20,
                }
            ],
        }

        router = _build_rank_scorers_tables(
            team_players=team_players,
            player_stats_map=player_stats_map,
        )
        mock_sb.table.side_effect = router

        scorers = _rank_scorers(85, 33, team_xg=2.0, is_opponent_home=False)
        assert len(scorers) >= 1
        for s in scorers:
            assert 3 <= s["proba"] <= 45

    def test_max_eight_scorers_returned(self, mock_sb):
        from models.scorer_engine import _rank_scorers

        team_players = [
            {"api_id": 1000 + i, "name": f"Player {i}", "position": "Attacker"} for i in range(12)
        ]
        player_stats_map = {
            (1000 + i): [
                {
                    "goals": 5,
                    "assists": 2,
                    "shots_total": 30,
                    "shots_on_target": 15,
                    "minutes_played": 1000,
                    "penalty_scored": 0,
                    "penalty_missed": 0,
                    "appearances": 12,
                }
            ]
            for i in range(12)
        }

        router = _build_rank_scorers_tables(
            team_players=team_players,
            player_stats_map=player_stats_map,
        )
        mock_sb.table.side_effect = router

        scorers = _rank_scorers(85, 33, team_xg=1.5, is_opponent_home=False)
        assert len(scorers) <= 8


# ═══════════════════════════════════════════════════════════════════
#  PREDICT_SCORERS
# ═══════════════════════════════════════════════════════════════════


@patch("models.scorer_engine._team_id_cache", {})
@patch("models.scorer_engine._team_name_cache", {})
@patch("models.scorer_engine.supabase")
class TestPredictScorers:
    """Tests for predict_scorers — final prediction entry point."""

    def test_unknown_team_returns_none(self, mock_sb):
        from models.scorer_engine import predict_scorers

        mock_sb.table.return_value = _make_chain(
            data=[
                {"api_id": 85, "name": "Paris Saint Germain"},
            ]
        )

        result = predict_scorers("Paris Saint Germain", "Unknown FC")
        assert result is None

    def test_valid_prediction_structure(self, mock_sb):
        from models.scorer_engine import predict_scorers

        teams = [
            {"api_id": 85, "name": "Paris Saint Germain"},
            {"api_id": 33, "name": "Olympique De Marseille"},
        ]

        # Build a comprehensive mock for the full predict_scorers flow
        players_call = [0]
        stats_call = [0]

        home_players = [
            {"api_id": 1100, "name": "Home Striker", "position": "Attacker"},
        ]
        away_players = [
            {"api_id": 2100, "name": "Away Striker", "position": "Attacker"},
        ]
        player_stats = [
            {
                "goals": 10,
                "assists": 5,
                "shots_total": 50,
                "shots_on_target": 25,
                "minutes_played": 1800,
                "penalty_scored": 0,
                "penalty_missed": 0,
                "appearances": 20,
            }
        ]

        def table_router(name):
            if name == "teams":
                return _make_chain(data=teams)
            if name == "players":
                c = players_call[0]
                players_call[0] += 1
                # Alternate between home/away team players and GK/injury lookups
                if c == 0:
                    return _make_chain(data=home_players)
                elif c == 1:
                    return _make_chain(data=[])  # GK ids for home
                elif c == 2:
                    return _make_chain(data=[])  # injured players home
                elif c == 3:
                    return _make_chain(data=away_players)
                elif c == 4:
                    return _make_chain(data=[])  # GK ids for away
                elif c == 5:
                    return _make_chain(data=[])  # injured players away
                return _make_chain(data=[])
            if name == "player_season_stats":
                c = stats_call[0]
                stats_call[0] += 1
                if c == 0 or c == 2:
                    return _make_chain(data=[])  # GK stats
                return _make_chain(data=player_stats)
            if name == "team_standings":
                return _make_chain(data=[])
            if name == "match_events":
                return _make_chain(data=[])
            if name == "match_lineups":
                return _make_chain(data=[])
            if name == "fixtures":
                return _make_chain(data=[])
            if name == "injuries":
                return _make_chain(data=[])
            return _make_chain()

        mock_sb.table.side_effect = table_router

        result = predict_scorers("Paris Saint Germain", "Olympique De Marseille")
        assert result is not None
        assert "home_scorers" in result
        assert "away_scorers" in result
        assert "top_scorers" in result
        assert "top_synergies_home" in result
        assert "top_synergies_away" in result
        assert "likely_scorer" in result

    def test_at_least_one_scorer_from_each_team(self, mock_sb):
        from models.scorer_engine import predict_scorers

        teams = [
            {"api_id": 85, "name": "Paris Saint Germain"},
            {"api_id": 33, "name": "Olympique De Marseille"},
        ]

        home_players = [
            {"api_id": 1100, "name": "Home Star", "position": "Attacker"},
            {"api_id": 1200, "name": "Home Mid", "position": "Midfielder"},
        ]
        away_players = [
            {"api_id": 2100, "name": "Away Star", "position": "Attacker"},
            {"api_id": 2200, "name": "Away Mid", "position": "Midfielder"},
        ]
        strong_stats = [
            {
                "goals": 15,
                "assists": 7,
                "shots_total": 60,
                "shots_on_target": 30,
                "minutes_played": 1800,
                "penalty_scored": 2,
                "penalty_missed": 0,
                "appearances": 20,
            }
        ]
        weak_stats = [
            {
                "goals": 3,
                "assists": 2,
                "shots_total": 20,
                "shots_on_target": 8,
                "minutes_played": 1000,
                "penalty_scored": 0,
                "penalty_missed": 0,
                "appearances": 12,
            }
        ]

        players_call = [0]
        stats_call = [0]

        def table_router(name):
            if name == "teams":
                return _make_chain(data=teams)
            if name == "players":
                c = players_call[0]
                players_call[0] += 1
                if c == 0:
                    return _make_chain(data=home_players)
                elif c == 3:
                    return _make_chain(data=away_players)
                return _make_chain(data=[])
            if name == "player_season_stats":
                c = stats_call[0]
                stats_call[0] += 1
                # GK stats calls return empty
                if c in (0, 2):
                    return _make_chain(data=[])
                # Even indices after GK: strong; odd: weak
                if (c - 1) % 2 == 0:
                    return _make_chain(data=strong_stats)
                return _make_chain(data=weak_stats)
            if name == "team_standings":
                return _make_chain(data=[])
            if name in ("match_events", "match_lineups"):
                return _make_chain(data=[])
            if name in ("fixtures", "injuries"):
                return _make_chain(data=[])
            return _make_chain()

        mock_sb.table.side_effect = table_router

        result = predict_scorers("Paris Saint Germain", "Olympique De Marseille")
        assert result is not None

        top = result.get("top_scorers", [])
        if len(top) >= 2:
            top_teams = {s["team"] for s in top}
            assert "Paris Saint Germain" in top_teams
            assert "Olympique De Marseille" in top_teams

    def test_backward_compat_keys_present(self, mock_sb):
        """predict_scorers should set likely_scorer and likely_scorer_proba."""
        from models.scorer_engine import predict_scorers

        teams = [
            {"api_id": 85, "name": "Paris Saint Germain"},
            {"api_id": 33, "name": "Olympique De Marseille"},
        ]

        players_call = [0]
        stats_call = [0]

        player_stats = [
            {
                "goals": 10,
                "assists": 5,
                "shots_total": 50,
                "shots_on_target": 25,
                "minutes_played": 1800,
                "penalty_scored": 0,
                "penalty_missed": 0,
                "appearances": 20,
            }
        ]

        def table_router(name):
            if name == "teams":
                return _make_chain(data=teams)
            if name == "players":
                c = players_call[0]
                players_call[0] += 1
                if c == 0:
                    return _make_chain(
                        data=[
                            {"api_id": 1100, "name": "Le Buteur", "position": "Attacker"},
                        ]
                    )
                if c == 3:
                    return _make_chain(
                        data=[
                            {"api_id": 2100, "name": "L'Autre", "position": "Attacker"},
                        ]
                    )
                return _make_chain(data=[])
            if name == "player_season_stats":
                c = stats_call[0]
                stats_call[0] += 1
                if c in (0, 2):
                    return _make_chain(data=[])  # GK stats
                return _make_chain(data=player_stats)
            return _make_chain(data=[])

        mock_sb.table.side_effect = table_router

        result = predict_scorers("Paris Saint Germain", "Olympique De Marseille")
        assert result is not None
        assert "likely_scorer" in result
        assert "likely_scorer_proba" in result
        assert result["likely_scorer"] is not None
        assert isinstance(result["likely_scorer_proba"], int)


# ═══════════════════════════════════════════════════════════════════
#  _BUILD_SCORER_ANALYSIS
# ═══════════════════════════════════════════════════════════════════


class TestBuildScorerAnalysis:
    """Tests for _build_scorer_analysis — text analysis builder.

    This function is pure (no DB calls), so no Supabase mock needed.
    """

    def _base_scorer(self, **overrides):
        """Return a base scorer dict with sensible defaults."""
        scorer = {
            "position": "Attacker",
            "goals_90": 0.5,
            "total_goals": 10,
            "total_assists": 5,
            "form_goals": 2,
            "form_matches": 5,
            "form_factor": 1.0,
            "conversion_rate": 0.25,
            "penalty_taker": False,
            "synergy": None,
            "defense_factor": 1.0,
            "gk_factor": 1.0,
            "goals_vs": 0,
            "matches_vs": 0,
            "shots_90": 1.0,
        }
        scorer.update(overrides)
        return scorer

    def test_position_label_attacker(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(position="Attacker"))
        assert "Attaquant" in analysis

    def test_position_label_midfielder(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(position="Midfielder"))
        assert "Milieu" in analysis

    def test_position_label_defender(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(position="Defender"))
        assert "Défenseur" in analysis

    def test_hot_form_indicator(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(
            self._base_scorer(
                form_factor=1.5,
                form_goals=4,
                form_matches=5,
            )
        )
        assert "🔥" in analysis
        assert "en forme" in analysis

    def test_cold_form_indicator(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(
            self._base_scorer(
                form_factor=0.6,
                form_goals=0,
                form_matches=5,
            )
        )
        assert "⚠️" in analysis
        assert "muet" in analysis

    def test_penalty_taker_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(penalty_taker=True))
        assert "pénalty" in analysis

    def test_synergy_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(synergy="Dembélé"))
        assert "synergie" in analysis
        assert "Dembélé" in analysis

    def test_fragile_defense_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(defense_factor=1.4))
        assert "défense adverse fragile" in analysis

    def test_solid_defense_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(defense_factor=0.7))
        assert "défense adverse solide" in analysis

    def test_weak_gk_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(gk_factor=1.35))
        assert "gardien adverse fébrile" in analysis

    def test_goals_vs_opponent_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(goals_vs=3, matches_vs=5))
        assert "3 buts en 5 matchs vs adversaire" in analysis

    def test_high_shots_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer(shots_90=2.0))
        assert "tirs cadrés/90" in analysis

    def test_low_conversion_rebound_mention(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(
            self._base_scorer(
                conversion_rate=0.10,
                shots_90=1.5,
            )
        )
        assert "rebond probable" in analysis

    def test_season_stats_always_present(self):
        from models.scorer_engine import _build_scorer_analysis

        analysis = _build_scorer_analysis(self._base_scorer())
        assert "buts/90 min" in analysis
        assert "buts saison" in analysis
