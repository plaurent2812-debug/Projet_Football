"""Tests pour clv_engine — math CLV per-market, overround removal."""

from __future__ import annotations

import math

import pytest

from src.monitoring.clv_engine import (
    compute_clv,
    fair_prob_from_odds,
    remove_overround,
)


def test_fair_prob_from_odds_basic():
    assert fair_prob_from_odds(2.0) == 0.5
    assert fair_prob_from_odds(1.50) == pytest.approx(1 / 1.50, abs=1e-6)


def test_fair_prob_rejects_invalid():
    with pytest.raises(ValueError):
        fair_prob_from_odds(0.95)
    with pytest.raises(ValueError):
        fair_prob_from_odds(-1.0)


def test_remove_overround_1x2():
    # Exemple : 1.5 / 4.0 / 7.0 → implied=[0.667, 0.25, 0.143], sum=1.060
    fair = remove_overround([1.5, 4.0, 7.0])
    assert math.isclose(sum(fair), 1.0, abs_tol=1e-6)
    # Ordre préservé
    assert fair[0] > fair[1] > fair[2]


def test_remove_overround_empty_returns_empty():
    assert remove_overround([]) == []


def test_remove_overround_rejects_invalid_odds():
    with pytest.raises(ValueError):
        remove_overround([2.0, 0.5])


def test_compute_clv_positive_when_model_beats_closing():
    """Modèle prédit 60%, closing implique 50% fair → CLV = 0.60/0.50 - 1 = +0.20."""
    clv = compute_clv(model_prob=0.60, closing_fair_prob=0.50)
    assert clv == pytest.approx(0.20, abs=1e-6)


def test_compute_clv_negative_when_model_under_closing():
    clv = compute_clv(model_prob=0.40, closing_fair_prob=0.50)
    assert clv == pytest.approx(-0.20, abs=1e-6)


def test_compute_clv_clamped_to_one_on_degenerate_closing():
    # closing_fair_prob extrêmement faible → CLV pourrait exploser, on cap à +1.0
    clv = compute_clv(model_prob=0.50, closing_fair_prob=0.01)
    assert clv == 1.0


def test_compute_clv_floored_at_minus_one():
    clv = compute_clv(model_prob=0.0, closing_fair_prob=0.50)
    assert clv == -1.0


def test_aggregate_clv_by_market_1x2():
    from src.monitoring.clv_engine import aggregate_clv_by_market

    predictions = [
        {
            "fixture_id": "fx1",
            "pred_home": 60.0,
            "pred_draw": 25.0,
            "pred_away": 15.0,
            "actual_result": "H",
        },
        {
            "fixture_id": "fx2",
            "pred_home": 40.0,
            "pred_draw": 30.0,
            "pred_away": 30.0,
            "actual_result": "A",
        },
    ]
    closing_odds = [
        # fx1 Pinnacle h/d/a : 1.80 / 3.60 / 4.80 (fair ~55/27/17)
        {
            "fixture_id": "fx1",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "home",
            "odds": 1.80,
            "line": None,
        },
        {
            "fixture_id": "fx1",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "draw",
            "odds": 3.60,
            "line": None,
        },
        {
            "fixture_id": "fx1",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "away",
            "odds": 4.80,
            "line": None,
        },
        # fx2 Pinnacle 2.50 / 3.20 / 2.80 (fair ~38/30/33)
        {
            "fixture_id": "fx2",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "home",
            "odds": 2.50,
            "line": None,
        },
        {
            "fixture_id": "fx2",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "draw",
            "odds": 3.20,
            "line": None,
        },
        {
            "fixture_id": "fx2",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "away",
            "odds": 2.80,
            "line": None,
        },
    ]

    result = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=closing_odds,
        market="1x2",
        bookmaker="pinnacle",
    )
    assert result["n_matches"] == 2
    # CLV on the model's "pick" (side with highest prob) against fair closing
    # fx1 pick = home (60%) vs ~55% fair → positive CLV
    # fx2 pick = home (40%) vs ~38% fair → slightly positive
    assert -0.5 < result["clv_mean"] < 0.5
    assert "clv_home" in result
    assert "clv_draw" in result
    assert "clv_away" in result


def test_aggregate_clv_returns_zero_n_when_no_closing():
    from src.monitoring.clv_engine import aggregate_clv_by_market

    predictions = [
        {
            "fixture_id": "fx99",
            "pred_home": 50,
            "pred_draw": 30,
            "pred_away": 20,
            "actual_result": "H",
        }
    ]
    result = aggregate_clv_by_market(
        predictions=predictions,
        closing_odds_rows=[],
        market="1x2",
        bookmaker="pinnacle",
    )
    assert result["n_matches"] == 0
