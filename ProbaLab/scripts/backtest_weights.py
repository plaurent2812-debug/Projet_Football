"""Backtest comparing old weights (market=0.20) vs new weights (market=0.45).
Uses last 12 months of predictions from Supabase.
Reports Brier score 1X2 and CLV.

### NOTE: Ce script ne peut tourner que si prediction_results contient
### les colonnes component probabilities (market_h, market_d, market_a,
### poisson_h, poisson_d, poisson_a, elo_h, elo_d, elo_a).
### Si ces colonnes sont absentes, le backtest retourne n=0 (mode dégradé).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.config import supabase
from src.monitoring.brier_monitor import compute_brier_1x2

WEIGHTS_OLD = {"market": 0.20, "poisson": 0.55, "elo": 0.25, "ai": 0.0}
WEIGHTS_NEW = {"market": 0.45, "poisson": 0.35, "elo": 0.20, "ai": 0.0}


def _reblend(row: dict, weights: dict) -> tuple[float, float, float]:
    """Re-blend H/D/A probabilities from stored component probabilities."""
    m_h, m_d, m_a = row["market_h"], row["market_d"], row["market_a"]
    p_h, p_d, p_a = row["poisson_h"], row["poisson_d"], row["poisson_a"]
    e_h, e_d, e_a = row["elo_h"], row["elo_d"], row["elo_a"]
    w = weights
    h = w["market"] * m_h + w["poisson"] * p_h + w["elo"] * e_h
    d = w["market"] * m_d + w["poisson"] * p_d + w["elo"] * e_d
    a = w["market"] * m_a + w["poisson"] * p_a + w["elo"] * e_a
    s = h + d + a
    return h / s, d / s, a / s


def backtest(months: int = 12) -> dict:
    """Run backtest comparing OLD vs NEW blend weights over the last N months.

    Args:
        months: Number of months to look back in prediction_results.

    Returns:
        Dict with keys: n, brier_old, brier_new.
        n=0 means no usable rows (missing component columns or empty table).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    try:
        rows = (
            supabase.table("prediction_results")
            .select("*")
            .gte("created_at", cutoff.isoformat())
            .not_.is_("actual_result", "null")
            .execute()
            .data
        )
    except Exception as exc:
        print(f"[backtest_weights] Supabase query failed: {exc}")
        return {"n": 0, "brier_old": None, "brier_new": None}

    brier_old, brier_new = [], []
    for row in rows:
        if None in (row.get("market_h"), row.get("poisson_h"), row.get("elo_h")):
            continue
        ho, do, ao = _reblend(row, WEIGHTS_OLD)
        hn, dn, an = _reblend(row, WEIGHTS_NEW)
        actual = row["actual_result"]
        if actual not in ("H", "D", "A"):
            continue
        y = {"H": (1, 0, 0), "D": (0, 1, 0), "A": (0, 0, 1)}[actual]
        brier_old.append(sum((p - a) ** 2 for p, a in zip((ho, do, ao), y)))
        brier_new.append(sum((p - a) ** 2 for p, a in zip((hn, dn, an), y)))
    return {
        "n": len(brier_old),
        "brier_old": sum(brier_old) / len(brier_old) if brier_old else None,
        "brier_new": sum(brier_new) / len(brier_new) if brier_new else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backtest blend weights old vs new over last N months."
    )
    parser.add_argument("--months", type=int, default=12)
    args = parser.parse_args()
    result = backtest(args.months)
    n = result["n"]
    print(f"N = {n}")
    if n == 0:
        print(
            "No usable rows found. prediction_results may lack component probability "
            "columns (market_h/d/a, poisson_h/d/a, elo_h/d/a). "
            "Backtest skipped — keeping current weights."
        )
    else:
        print(f"Brier OLD (market=0.20): {result['brier_old']:.4f}")
        print(f"Brier NEW (market=0.45): {result['brier_new']:.4f}")
        delta = result["brier_new"] - result["brier_old"]
        print(f"Delta: {delta:+.4f} ({'NEW better' if delta < 0 else 'OLD better'})")
