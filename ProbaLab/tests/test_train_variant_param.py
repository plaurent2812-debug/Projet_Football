"""Tests : train.py lit FEATURE_COLS via get_variant(), pas via import direct."""
from __future__ import annotations


def test_train_module_has_variant_aware_feature_loader():
    """Assure qu'il existe une fonction get_feature_cols_for_variant(name)."""
    from src.training import train
    assert hasattr(train, "get_feature_cols_for_variant"), (
        "train.py doit exposer get_feature_cols_for_variant(variant_name) "
        "pour permettre l'entraînement des 4 variantes"
    )


def test_get_feature_cols_for_variant_returns_expected():
    from src.training.train import get_feature_cols_for_variant

    base = get_feature_cols_for_variant("baseline")
    assert "market_home_prob" in base
    pure = get_feature_cols_for_variant("pure")
    assert "market_home_prob" not in pure
    assert len(pure) == len(base) - 6
