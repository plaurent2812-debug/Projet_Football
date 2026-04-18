"""Tests pour le registre bookmakers — mapping noms internes ↔ The Odds API keys."""
from __future__ import annotations

import pytest

from src.fetchers.bookmaker_registry import (
    BOOKMAKERS_FR,
    ODDS_API_KEY_BY_BOOKMAKER,
    SPORT_KEYS,
    get_bookmaker_from_api_key,
    normalize_bookmaker,
)


def test_five_bookmakers_registered():
    assert BOOKMAKERS_FR == ["pinnacle", "betclic", "winamax", "unibet", "zebet"]


def test_mapping_has_all_bookmakers():
    for bk in BOOKMAKERS_FR:
        assert bk in ODDS_API_KEY_BY_BOOKMAKER
        assert isinstance(ODDS_API_KEY_BY_BOOKMAKER[bk], str)
        assert len(ODDS_API_KEY_BY_BOOKMAKER[bk]) > 0


def test_reverse_lookup():
    for bk in BOOKMAKERS_FR:
        api_key = ODDS_API_KEY_BY_BOOKMAKER[bk]
        assert get_bookmaker_from_api_key(api_key) == bk


def test_reverse_lookup_unknown_returns_none():
    assert get_bookmaker_from_api_key("does_not_exist") is None


def test_normalize_accepts_aliases():
    assert normalize_bookmaker("Pinnacle") == "pinnacle"
    assert normalize_bookmaker("WINAMAX") == "winamax"
    assert normalize_bookmaker(" Betclic ") == "betclic"


def test_normalize_unknown_raises():
    with pytest.raises(ValueError):
        normalize_bookmaker("fdj")


def test_sport_keys_cover_foot_and_nhl():
    # clés The Odds API — format stable documenté v4
    assert "soccer_france_ligue_one" in SPORT_KEYS["football"]
    assert "soccer_epl" in SPORT_KEYS["football"]
    assert "icehockey_nhl" in SPORT_KEYS["nhl"]
    # 8 ligues foot + 1 NHL
    assert len(SPORT_KEYS["football"]) == 8
    assert len(SPORT_KEYS["nhl"]) == 1


def test_normalize_team_name_handles_punctuation_and_case():
    from src.fetchers.bookmaker_registry import normalize_team_name

    assert normalize_team_name("St. Louis Blues") == normalize_team_name("St Louis Blues")
    assert normalize_team_name("St. LOUIS Blues") == normalize_team_name("st louis blues")


def test_normalize_team_name_drops_hockey_club_suffix():
    from src.fetchers.bookmaker_registry import teams_match

    # Lesson 69 — Utah rename 2025-26
    assert teams_match("Utah Hockey Club", "Utah Mammoth")
    assert teams_match("Utah Hockey Club", "Utah")


def test_normalize_team_name_handles_psg_variant():
    from src.fetchers.bookmaker_registry import teams_match

    assert teams_match("Paris Saint Germain", "Paris Saint-Germain")


def test_normalize_team_name_returns_empty_on_non_string():
    from src.fetchers.bookmaker_registry import normalize_team_name

    assert normalize_team_name(None) == ""  # type: ignore[arg-type]
    assert normalize_team_name(123) == ""  # type: ignore[arg-type]


def test_teams_match_false_for_different_teams():
    from src.fetchers.bookmaker_registry import teams_match

    assert not teams_match("Arsenal", "Chelsea")
