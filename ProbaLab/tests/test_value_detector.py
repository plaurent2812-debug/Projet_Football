"""Tests pour value_detector — best odds, edge, Kelly fractional."""

from __future__ import annotations

import pytest

from src.models.value_detector import (
    best_odds_per_selection,
    detect_value_bets,
    kelly_fractional,
)


def test_best_odds_picks_max_per_selection():
    rows = [
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "home", "odds": 1.50},
        {"bookmaker": "betclic", "market": "1x2", "selection": "home", "odds": 1.55},
        {"bookmaker": "winamax", "market": "1x2", "selection": "home", "odds": 1.48},
        {"bookmaker": "unibet", "market": "1x2", "selection": "draw", "odds": 4.20},
        {"bookmaker": "zebet", "market": "1x2", "selection": "draw", "odds": 4.50},
        {"bookmaker": "winamax", "market": "1x2", "selection": "draw", "odds": 4.10},
    ]
    out = best_odds_per_selection(rows, market="1x2")
    assert out["home"]["odds"] == 1.55
    assert out["home"]["bookmaker"] == "betclic"
    assert out["draw"]["odds"] == 4.50


def test_best_odds_ignores_other_markets():
    rows = [
        {"bookmaker": "a", "market": "1x2", "selection": "home", "odds": 1.50},
        {"bookmaker": "b", "market": "btts", "selection": "yes", "odds": 1.80},
    ]
    out = best_odds_per_selection(rows, market="1x2")
    assert "home" in out
    assert "yes" not in out


def test_kelly_fractional_capped_at_configured_fraction():
    # edge=0.10, odds=3.0 → kelly_full = 0.05 → kelly_frac = 0.05 * 0.25 = 0.0125
    k = kelly_fractional(edge=0.10, odds=3.0)
    assert k == pytest.approx(0.0125, abs=1e-4)


def test_kelly_fractional_zero_for_negative_edge():
    assert kelly_fractional(edge=-0.05, odds=2.0) == 0.0


def test_kelly_fractional_zero_for_odds_le_1():
    assert kelly_fractional(edge=0.10, odds=1.0) == 0.0


def test_detect_value_bets_flags_above_5pct_edge():
    model_probs = {"home": 0.60, "draw": 0.25, "away": 0.15}
    rows = [
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "home", "odds": 1.70},
        {"bookmaker": "betclic", "market": "1x2", "selection": "home", "odds": 1.80},
        {"bookmaker": "winamax", "market": "1x2", "selection": "home", "odds": 1.75},
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "draw", "odds": 3.80},
        {"bookmaker": "betclic", "market": "1x2", "selection": "draw", "odds": 4.50},
        {"bookmaker": "winamax", "market": "1x2", "selection": "draw", "odds": 4.00},
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "away", "odds": 6.00},
        {"bookmaker": "betclic", "market": "1x2", "selection": "away", "odds": 6.50},
        {"bookmaker": "winamax", "market": "1x2", "selection": "away", "odds": 6.00},
    ]
    bets = detect_value_bets(
        model_probs=model_probs,
        odds_rows=rows,
        market="1x2",
    )
    # home: 0.60 * 1.80 - 1 = 0.08 (8%, value)
    # draw: 0.25 * 4.50 - 1 = 0.125 (12.5%, value)
    # away: 0.15 * 6.50 - 1 = -0.025 (pas value)
    selections = [b["selection"] for b in bets]
    assert "home" in selections
    assert "draw" in selections
    assert "away" not in selections


def test_detect_value_bets_skips_when_less_than_min_bookmakers():
    model_probs = {"home": 0.60, "draw": 0.25, "away": 0.15}
    # Seulement 2 bookmakers couvrent la selection home
    rows = [
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "home", "odds": 1.70},
        {"bookmaker": "betclic", "market": "1x2", "selection": "home", "odds": 1.80},
    ]
    bets = detect_value_bets(
        model_probs=model_probs,
        odds_rows=rows,
        market="1x2",
    )
    assert bets == []


def test_detect_value_bets_uses_admin_threshold_when_requested():
    model_probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    rows = [
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "home", "odds": 1.90},
        {"bookmaker": "betclic", "market": "1x2", "selection": "home", "odds": 1.92},
        {"bookmaker": "winamax", "market": "1x2", "selection": "home", "odds": 1.91},
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "draw", "odds": 3.80},
        {"bookmaker": "betclic", "market": "1x2", "selection": "draw", "odds": 3.80},
        {"bookmaker": "winamax", "market": "1x2", "selection": "draw", "odds": 3.80},
        {"bookmaker": "pinnacle", "market": "1x2", "selection": "away", "odds": 4.50},
        {"bookmaker": "betclic", "market": "1x2", "selection": "away", "odds": 4.50},
        {"bookmaker": "winamax", "market": "1x2", "selection": "away", "odds": 4.50},
    ]
    # home edge = 0.55 * 1.92 - 1 = 0.056 → user-facing (>=5%) OK
    # draw edge = 0.25 * 3.80 - 1 = -0.05 → pas value
    # away edge = 0.20 * 4.50 - 1 = -0.10 → pas value
    # Avec threshold=0.03, home reste value
    bets_admin = detect_value_bets(
        model_probs=model_probs,
        odds_rows=rows,
        market="1x2",
        edge_threshold=0.03,
    )
    bets_user = detect_value_bets(
        model_probs=model_probs,
        odds_rows=rows,
        market="1x2",
    )
    selections_admin = [b["selection"] for b in bets_admin]
    selections_user = [b["selection"] for b in bets_user]
    assert "home" in selections_admin
    assert "home" in selections_user
