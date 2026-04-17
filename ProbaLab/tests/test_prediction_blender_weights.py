"""Tests for blend weight constants in src/constants.py.

Task A3 — H1 Stabilisation.
Backtest (2026-04-17) returned N=0 because prediction_results lacks
component probability columns (market_h/d/a, poisson_h/d/a, elo_h/d/a).
Weights kept at their current values; market-dominance assertion is
marked xfail until the backtest can run on real data and confirms GO.
See scripts/backtest_weights.py.

Note: constants.py has two independent weight groups:
  - Layer 1 (signal blend): WEIGHT_MARKET + WEIGHT_POISSON + WEIGHT_ELO = 1.0
  - Layer 2 (stats vs AI): WEIGHT_STATS + WEIGHT_AI = 1.0
These are separate blending stages. This test covers Layer 1 only.
"""

import pytest

from src.constants import WEIGHT_ELO, WEIGHT_MARKET, WEIGHT_POISSON


def test_weights_sum_to_one() -> None:
    """Market + Poisson + ELO signal-blend weights must sum to exactly 1.0."""
    total = WEIGHT_MARKET + WEIGHT_POISSON + WEIGHT_ELO
    assert abs(total - 1.0) < 1e-9, f"Signal blend weights must sum to 1.0, got {total}"


@pytest.mark.xfail(
    reason=(
        "Backtest 2026-04-17 skipped (prediction_results lacks component columns). "
        "WEIGHT_MARKET not yet promoted to dominant. "
        "Re-run scripts/backtest_weights.py once columns are populated, then remove xfail."
    ),
    strict=False,
)
def test_market_weight_is_dominant() -> None:
    """Lesson 52: market signal (52-55% accuracy) should be the dominant weight.

    This assertion is ASPIRATIONAL — it will pass once Task A3 is fully executed
    (backtest confirms GO and constants.py is updated to WEIGHT_MARKET=0.45).
    """
    assert max(WEIGHT_POISSON, WEIGHT_ELO) <= WEIGHT_MARKET, (
        f"WEIGHT_MARKET={WEIGHT_MARKET} must dominate Poisson={WEIGHT_POISSON} and ELO={WEIGHT_ELO}"
    )
