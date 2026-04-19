"""Tests pour src/training/variants.py — configs des 4 variantes ML."""

from __future__ import annotations

import pytest

from src.constants import FEATURE_COLS
from src.training.variants import (
    ALL_VARIANTS,
    MARKET_FEATURE_NAMES,
    VariantConfig,  # noqa: F401 — imported to verify export (part of public API)
    get_variant,
)


def test_all_four_variants_registered():
    names = {v.name for v in ALL_VARIANTS}
    assert names == {"baseline", "rebalanced", "pure", "pure_rebalanced"}


def test_baseline_matches_current_feature_cols():
    cfg = get_variant("baseline")
    # baseline = FEATURE_COLS existant, poids actuels
    assert cfg.feature_cols == FEATURE_COLS
    assert cfg.weight_poisson == 0.55
    assert cfg.weight_elo == 0.25
    assert cfg.weight_market == 0.20


def test_pure_has_no_market_features():
    cfg = get_variant("pure")
    for mf in MARKET_FEATURE_NAMES:
        assert mf not in cfg.feature_cols, f"pure doit exclure {mf}"


def test_rebalanced_keeps_market_but_shifts_weights():
    cfg = get_variant("rebalanced")
    assert "market_home_prob" in cfg.feature_cols
    assert cfg.weight_poisson == pytest.approx(0.40, abs=1e-6)
    assert cfg.weight_elo == pytest.approx(0.20, abs=1e-6)
    assert cfg.weight_market == pytest.approx(0.40, abs=1e-6)


def test_pure_rebalanced_has_no_market_and_no_market_weight():
    cfg = get_variant("pure_rebalanced")
    for mf in MARKET_FEATURE_NAMES:
        assert mf not in cfg.feature_cols
    # Sans marché : 0.65/0.35 (cf constants NO_MARKET)
    assert cfg.weight_poisson == pytest.approx(0.65, abs=1e-6)
    assert cfg.weight_elo == pytest.approx(0.35, abs=1e-6)
    assert cfg.weight_market == 0.0


def test_variant_weights_sum_to_one():
    for cfg in ALL_VARIANTS:
        total = cfg.weight_poisson + cfg.weight_elo + cfg.weight_market
        assert abs(total - 1.0) < 1e-6, f"{cfg.name}: weights sum to {total}"


def test_get_variant_raises_on_unknown():
    with pytest.raises(ValueError):
        get_variant("does_not_exist")
