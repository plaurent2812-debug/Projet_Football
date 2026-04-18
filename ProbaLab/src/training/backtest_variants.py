"""backtest_variants — entraîne les 4 variantes sur holdout commun.

Usage:
    python -m src.training.backtest_variants --out reports/variants_2026-04-19.md

Steps:
    1. Load train + holdout datasets (parquet versionnés, cf spec 4.4)
    2. For each variant: train XGBoost 1X2 → eval on holdout → Brier/LogLoss
    3. Print markdown report to stdout + write to --out
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import log_loss

from src.training.variants import ALL_VARIANTS, MARKET_FEATURE_NAMES, get_variant

logger = logging.getLogger("football_ia.backtest_variants")

_FEATURE_NAMES_MIN = [
    "xg_home", "xg_away", "home_elo", "away_elo", "elo_diff",
    "home_form", "away_form", "form_diff",
    "home_xg_per_shot", "away_xg_per_shot",
    "league_avg_home_goals", "league_avg_away_goals",
    *MARKET_FEATURE_NAMES,
]


def build_synthetic_dataset(
    *, n_train: int, n_holdout: int, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Génère un dataset synthétique cohérent pour les tests.

    Les labels 1X2 dépendent d'un mix de features (ELO diff + form) + bruit.
    Les colonnes market_* sont corrélées au label (simulent un marché efficient).
    """
    rng = np.random.default_rng(seed)
    n = n_train + n_holdout
    elo_diff = rng.normal(0, 100, n)
    form_diff = rng.normal(0, 1, n)

    # Proba home (logistic)
    logit_h = 0.005 * elo_diff + 0.3 * form_diff
    p_home = 1.0 / (1.0 + np.exp(-logit_h))
    p_home = np.clip(p_home, 0.1, 0.85)
    p_draw = 0.25 - 0.05 * np.abs(logit_h)
    p_draw = np.clip(p_draw, 0.08, 0.32)
    p_away = np.clip(1.0 - p_home - p_draw, 0.05, 0.7)
    # renormalise
    totals = p_home + p_draw + p_away
    p_home, p_draw, p_away = p_home / totals, p_draw / totals, p_away / totals

    u = rng.random(n)
    labels = np.where(u < p_home, 0, np.where(u < p_home + p_draw, 1, 2))

    df = pd.DataFrame({
        "match_date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "xg_home": rng.uniform(0.5, 3.0, n),
        "xg_away": rng.uniform(0.5, 3.0, n),
        "home_elo": rng.normal(1600, 100, n),
        "away_elo": rng.normal(1600, 100, n),
        "elo_diff": elo_diff,
        "home_form": rng.uniform(0, 3, n),
        "away_form": rng.uniform(0, 3, n),
        "form_diff": form_diff,
        "home_xg_per_shot": rng.uniform(0.08, 0.15, n),
        "away_xg_per_shot": rng.uniform(0.08, 0.15, n),
        "league_avg_home_goals": np.full(n, 1.5),
        "league_avg_away_goals": np.full(n, 1.2),
        # market features: implied probs avec bruit
        "market_home_prob": p_home * 100 + rng.normal(0, 2, n),
        "market_draw_prob": p_draw * 100 + rng.normal(0, 2, n),
        "market_away_prob": p_away * 100 + rng.normal(0, 2, n),
        "market_btts_prob": rng.uniform(40, 65, n),
        "market_over25_prob": rng.uniform(40, 65, n),
        "market_over15_prob": rng.uniform(60, 85, n),
        "label_1x2": labels,
    })
    # Compléter les autres FEATURE_COLS avec zéros (le modèle apprend à les ignorer)
    for col in [
        "home_attack_strength", "home_defense_strength", "away_attack_strength",
        "away_defense_strength", "home_rest_days", "away_rest_days",
        "home_congestion_30d", "away_congestion_30d", "home_stakes", "away_stakes",
        "h2h_home_winrate", "h2h_total_matches", "home_injury_count",
        "away_injury_count", "home_momentum", "away_momentum",
        "home_fatigue_index", "away_fatigue_index", "home_goal_diff_avg",
        "away_goal_diff_avg", "home_result_variance", "away_result_variance",
        "home_clean_sheet_rate", "away_clean_sheet_rate", "home_ppg_last5",
        "away_ppg_last5", "home_btts_rate_last10", "away_btts_rate_last10",
        "home_over25_rate_last10", "away_over25_rate_last10",
        "league_avg_btts_rate", "league_avg_over25_rate",
        "elo_diff_squared", "home_form_long", "away_form_long", "form_long_diff",
    ]:
        df[col] = 0.0
    df["elo_diff_squared"] = df["elo_diff"] ** 2

    train = df.iloc[:n_train].reset_index(drop=True)
    holdout = df.iloc[n_train:].reset_index(drop=True)
    return train, holdout


def _one_hot(y: np.ndarray, n_classes: int = 3) -> np.ndarray:
    out = np.zeros((len(y), n_classes))
    out[np.arange(len(y)), y] = 1
    return out


def evaluate_variant(
    variant_name: str,
    *,
    train: pd.DataFrame,
    holdout: pd.DataFrame,
) -> dict[str, Any]:
    """Entraîne une variante sur train, évalue sur holdout → Brier + LogLoss."""
    cfg = get_variant(variant_name)
    cols = [c for c in cfg.feature_cols if c in train.columns]

    X_train = train[cols].to_numpy(dtype=float)
    y_train = train["label_1x2"].to_numpy(dtype=int)
    X_hold = holdout[cols].to_numpy(dtype=float)
    y_hold = holdout["label_1x2"].to_numpy(dtype=int)

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="multi:softprob",
        num_class=3,
        random_state=42,
        eval_metric="mlogloss",
        verbosity=0,
    )
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_hold)
    brier = float(np.mean(
        np.sum((probs - _one_hot(y_hold, 3)) ** 2, axis=1) / 3.0
    ))
    ll = float(log_loss(y_hold, probs, labels=[0, 1, 2]))

    return {
        "variant": variant_name,
        "n_features": len(cols),
        "n_train": len(train),
        "n_holdout": len(holdout),
        "brier_1x2": round(brier, 5),
        "log_loss_1x2": round(ll, 5),
        "status": "OK",
    }


def run_all_variants(
    *,
    train: pd.DataFrame,
    holdout: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Entraîne les 4 variantes, isole les échecs."""
    results: list[dict] = []
    for cfg in ALL_VARIANTS:
        try:
            res = evaluate_variant(cfg.name, train=train, holdout=holdout)
        except Exception as exc:
            logger.exception("variant %s failed", cfg.name)
            res = {
                "variant": cfg.name,
                "status": "FAILED",
                "error": str(exc),
                "n_features": len(cfg.feature_cols),
            }
        results.append(res)
    return results


def format_markdown_report(results: list[dict]) -> str:
    lines = [
        "# Variants backtest report",
        "",
        "| Variant | n_features | Brier 1X2 | LogLoss 1X2 | Status |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['variant']} | {r.get('n_features', '?')} | "
            f"{r.get('brier_1x2', '?')} | {r.get('log_loss_1x2', '?')} | "
            f"{r.get('status', '?')} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=False, default=None)
    args = parser.parse_args()

    # Placeholder : en prod, charger parquet versionnés cf spec 4.4
    train, holdout = build_synthetic_dataset(n_train=1000, n_holdout=300, seed=42)
    results = run_all_variants(train=train, holdout=holdout)
    md = format_markdown_report(results)
    print(md)
    if args.out:
        with open(args.out, "w") as f:
            f.write(md)
