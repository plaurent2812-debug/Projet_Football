"""Tests end-to-end : 4 variantes entraînées sur dataset synthétique."""
from __future__ import annotations

from src.training.backtest_variants import (
    build_synthetic_dataset,
    evaluate_variant,
    run_all_variants,
)


def test_build_synthetic_dataset_returns_train_holdout():
    train, holdout = build_synthetic_dataset(n_train=200, n_holdout=50, seed=42)
    assert len(train) == 200
    assert len(holdout) == 50
    # Holdout temporellement postérieur au train
    assert holdout["match_date"].min() >= train["match_date"].max()


def test_evaluate_variant_returns_brier():
    train, holdout = build_synthetic_dataset(n_train=400, n_holdout=100, seed=7)
    result = evaluate_variant("baseline", train=train, holdout=holdout)
    assert "brier_1x2" in result
    assert 0.0 < result["brier_1x2"] < 1.0
    assert result["variant"] == "baseline"
    assert result["n_holdout"] == 100


def test_run_all_variants_returns_four():
    train, holdout = build_synthetic_dataset(n_train=400, n_holdout=100, seed=1)
    results = run_all_variants(train=train, holdout=holdout)
    assert len(results) == 4
    names = {r["variant"] for r in results}
    assert names == {"baseline", "rebalanced", "pure", "pure_rebalanced"}


def test_run_all_variants_isolates_failures(monkeypatch):
    """Si une variante crash, les 3 autres sont quand même renvoyées avec status."""
    from src.training import backtest_variants

    original_evaluate = backtest_variants.evaluate_variant

    def fake_evaluate(name, **kwargs):
        if name == "rebalanced":
            raise RuntimeError("boom")
        return original_evaluate(name, **kwargs)

    monkeypatch.setattr(backtest_variants, "evaluate_variant", fake_evaluate)
    train, holdout = build_synthetic_dataset(n_train=300, n_holdout=80, seed=3)
    results = run_all_variants(train=train, holdout=holdout)
    assert len(results) == 4
    reb = next(r for r in results if r["variant"] == "rebalanced")
    assert reb.get("status") == "FAILED"
    # Les 3 autres sont OK
    ok = [r for r in results if r.get("status") != "FAILED"]
    assert len(ok) == 3
