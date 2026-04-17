from __future__ import annotations

"""
backtest.py — Backtest complet du système de prédiction NHL.

Analyse la performance sur les données de nhl_suivi_algo_clean :
  1. Accuracy par marché (Buteur, Passeur, Point, Tirs)
  2. Brier Score & calibration
  3. Courbe de calibration (reliability diagram)
  4. ROI simulé avec cotes réelles
  5. Performance par seuil de probabilité
  6. Diagnostic final

Usage :
    python -m src.nhl.backtest
"""
from collections import defaultdict

from src.config import logger, supabase


def _load_data() -> list[dict]:
    """Load all evaluation data from nhl_suivi_algo_clean."""
    rows = supabase.table("nhl_suivi_algo_clean").select("*").execute().data
    if not rows:
        logger.warning("Aucune donnée dans nhl_suivi_algo_clean.")
        return []
    return rows


def _bar(pct: float, width: int = 20) -> str:
    filled = int(pct / (100 / width))
    return "█" * filled + "░" * (width - filled)


def _section(title: str) -> None:
    logger.info("")
    logger.info(f"{'=' * 64}")
    logger.info(f"  {title}")
    logger.info(f"{'=' * 64}")


def run_nhl_backtest() -> dict:
    _section("BACKTEST NHL COMPLET")

    rows = _load_data()
    if not rows:
        return {}

    n = len(rows)
    logger.info(f"  {n} évaluations chargées")

    # ── 1. Accuracy par marché ───────────────────────────────────
    _section("1. ACCURACY PAR MARCHÉ")

    by_market: dict[str, dict] = defaultdict(
        lambda: {
            "wins": 0,
            "total": 0,
            "brier_sum": 0.0,
            "probs": [],
            "outcomes": [],
            "roi_sum": 0.0,
            "roi_bets": 0,
        }
    )

    for r in rows:
        market = r.get("pari", "?")
        won = r.get("résultat", "") == "GAGNÉ"
        prob = r.get("proba_predite")
        cote = r.get("cote")

        by_market[market]["total"] += 1
        if won:
            by_market[market]["wins"] += 1

        if prob is not None and prob > 0:
            p = float(prob) / 100.0
            outcome = 1.0 if won else 0.0
            by_market[market]["brier_sum"] += (p - outcome) ** 2
            by_market[market]["probs"].append(p)
            by_market[market]["outcomes"].append(outcome)

        # ROI with real odds
        if cote is not None and float(cote) > 1.0:
            c = float(cote)
            by_market[market]["roi_bets"] += 1
            if won:
                by_market[market]["roi_sum"] += c - 1.0  # net profit
            else:
                by_market[market]["roi_sum"] -= 1.0  # lost 1 unit

    total_wins = sum(m["wins"] for m in by_market.values())
    total_bets = sum(m["total"] for m in by_market.values())

    for market in sorted(by_market.keys()):
        d = by_market[market]
        pct = round(d["wins"] / d["total"] * 100, 1) if d["total"] > 0 else 0
        brier = round(d["brier_sum"] / d["total"], 4) if d["total"] > 0 else 0
        roi_str = ""
        if d["roi_bets"] > 0:
            roi_pct = round(d["roi_sum"] / d["roi_bets"] * 100, 1)
            roi_str = f"  ROI={roi_pct:+.1f}% ({d['roi_bets']} paris)"
        logger.info(
            f"  {market:25s} {_bar(pct)} {pct:5.1f}% ({d['wins']}/{d['total']})  "
            f"Brier={brier:.4f}{roi_str}"
        )

    global_pct = round(total_wins / total_bets * 100, 1) if total_bets > 0 else 0
    logger.info(f"\n  Global: {global_pct}% ({total_wins}/{total_bets})")

    # ── 2. Courbe de calibration ─────────────────────────────────
    _section("2. COURBE DE CALIBRATION (Reliability Diagram)")

    all_probs = []
    all_outcomes = []
    for d in by_market.values():
        all_probs.extend(d["probs"])
        all_outcomes.extend(d["outcomes"])

    if all_probs:
        n_bins = 10
        bin_size = 1.0 / n_bins
        logger.info(f"  {'Bin':>12s} {'Prédit':>8s} {'Réel':>8s} {'Écart':>7s} {'N':>6s}")
        logger.info(f"  {'─' * 12} {'─' * 8} {'─' * 8} {'─' * 7} {'─' * 6}")

        total_gap = 0
        total_n = 0
        for i in range(n_bins):
            lo = i * bin_size
            hi = (i + 1) * bin_size
            in_bin = [(p, o) for p, o in zip(all_probs, all_outcomes) if lo <= p < hi]
            if not in_bin:
                continue
            mean_pred = sum(p for p, _ in in_bin) / len(in_bin)
            mean_actual = sum(o for _, o in in_bin) / len(in_bin)
            gap = abs(mean_pred - mean_actual)
            logger.info(
                f"  {round(lo * 100):>4d}-{round(hi * 100):>3d}% "
                f"{mean_pred * 100:>7.1f}% {mean_actual * 100:>7.1f}% "
                f"{gap * 100:>6.1f}% {len(in_bin):>5d}"
            )
            total_gap += gap * len(in_bin)
            total_n += len(in_bin)

        avg_gap = total_gap / total_n if total_n > 0 else 0
        logger.info(f"  Écart moyen pondéré : {avg_gap * 100:.1f}%")

    # ── 3. Performance par seuil de probabilité ──────────────────
    _section("3. ACCURACY PAR SEUIL DE PROBABILITÉ")

    thresholds = [(0, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 80), (80, 100)]
    logger.info(f"  {'Seuil':>12s} {'Accuracy':>10s} {'N':>6s} {'Brier':>8s}")
    logger.info(f"  {'─' * 12} {'─' * 10} {'─' * 6} {'─' * 8}")

    for lo, hi in thresholds:
        bucket_rows = [
            r
            for r in rows
            if r.get("proba_predite") is not None and lo <= float(r["proba_predite"]) < hi
        ]
        if not bucket_rows:
            continue
        wins = sum(1 for r in bucket_rows if r.get("résultat") == "GAGNÉ")
        brier_sum = sum(
            (float(r["proba_predite"]) / 100 - (1.0 if r.get("résultat") == "GAGNÉ" else 0.0)) ** 2
            for r in bucket_rows
        )
        pct = round(wins / len(bucket_rows) * 100, 1)
        brier = round(brier_sum / len(bucket_rows), 4)
        logger.info(f"  {lo:>4d}-{hi:>3d}%   {pct:>8.1f}%  {len(bucket_rows):>5d}  {brier:>7.4f}")

    # ── 4. ROI avec cotes réelles ────────────────────────────────
    _section("4. ROI AVEC COTES RÉELLES")

    rows_with_odds = [r for r in rows if r.get("cote") and float(r.get("cote", 0)) > 1.0]
    if rows_with_odds:
        total_staked = len(rows_with_odds)
        total_return = sum(
            float(r["cote"]) if r.get("résultat") == "GAGNÉ" else 0 for r in rows_with_odds
        )
        profit = total_return - total_staked
        roi = round(profit / total_staked * 100, 1) if total_staked > 0 else 0
        wins_odds = sum(1 for r in rows_with_odds if r.get("résultat") == "GAGNÉ")
        avg_odds = round(sum(float(r["cote"]) for r in rows_with_odds) / total_staked, 2)

        logger.info(f"  Paris avec cotes : {total_staked}")
        logger.info(
            f"  Win rate         : {round(wins_odds / total_staked * 100, 1)}% ({wins_odds}/{total_staked})"
        )
        logger.info(f"  Cote moyenne     : {avg_odds}")
        logger.info(f"  ROI              : {roi:+.1f}%")
        logger.info(f"  Profit (units)   : {profit:+.1f}")
    else:
        logger.info("  Aucun pari avec cotes réelles disponible.")
        logger.info("  Pour activer: lancer fetch_nhl_odds.py avant les matchs.")

    # ── 5. Top/Flop players ──────────────────────────────────────
    _section("5. TOP/FLOP JOUEURS (min 5 évaluations)")

    by_player: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0})
    for r in rows:
        name = r.get("joueur", "?")
        by_player[name]["total"] += 1
        if r.get("résultat") == "GAGNÉ":
            by_player[name]["wins"] += 1

    qualified = [(name, d) for name, d in by_player.items() if d["total"] >= 5]
    if qualified:
        qualified.sort(key=lambda x: x[1]["wins"] / x[1]["total"], reverse=True)

        logger.info("  TOP 10:")
        for name, d in qualified[:10]:
            pct = round(d["wins"] / d["total"] * 100, 1)
            logger.info(f"    {name:30s} {pct:5.1f}% ({d['wins']}/{d['total']})")

        logger.info("  FLOP 10:")
        for name, d in qualified[-10:]:
            pct = round(d["wins"] / d["total"] * 100, 1)
            logger.info(f"    {name:30s} {pct:5.1f}% ({d['wins']}/{d['total']})")

    # ── 6. Diagnostic ────────────────────────────────────────────
    _section("6. DIAGNOSTIC")

    issues = []
    strengths = []

    # Accuracy check per market
    for market, d in by_market.items():
        if d["total"] < 10:
            continue
        pct = d["wins"] / d["total"] * 100
        if "Buteur" in market:
            base = 25  # ~25% NHL players score per game
            if pct > base + 3:
                strengths.append(f"{market}: {pct:.1f}% > baseline {base}%")
            elif pct < base - 5:
                issues.append(f"{market}: {pct:.1f}% < baseline {base}%")
        elif "Point" in market:
            base = 45
            if pct > base + 3:
                strengths.append(f"{market}: {pct:.1f}% > baseline {base}%")
            elif pct < base - 5:
                issues.append(f"{market}: {pct:.1f}% < baseline {base}%")

    # Calibration check
    if all_probs:
        avg_gap_pct = avg_gap * 100
        if avg_gap_pct < 3:
            strengths.append(f"Calibration précise (écart moyen {avg_gap_pct:.1f}%)")
        elif avg_gap_pct > 8:
            issues.append(f"Calibration imprécise (écart moyen {avg_gap_pct:.1f}%)")

    # ROI check
    if rows_with_odds:
        if roi > 3:
            strengths.append(f"ROI positif ({roi:+.1f}%) — edge réel")
        elif roi < -5:
            issues.append(f"ROI négatif ({roi:+.1f}%) — pas d'edge sur les cotes")

    if strengths:
        logger.info("  POINTS FORTS:")
        for s in strengths:
            logger.info(f"    + {s}")
    if issues:
        logger.info("  POINTS D'ATTENTION:")
        for i in issues:
            logger.info(f"    - {i}")
    if not issues and not strengths:
        logger.info("  Pas assez de données pour un diagnostic fiable.")

    # Score
    score = 0
    score += min(3, global_pct / 15)  # 0-3
    if all_probs:
        score += max(0, min(3, (0.10 - avg_gap) / 0.10 * 3))  # 0-3 calibration
    if rows_with_odds and roi > 0:
        score += min(2, roi / 5)  # 0-2
    # Monotonicity: higher prob → higher accuracy
    score += 2  # placeholder

    grade = "HIGH" if score >= 7 else "MEDIUM" if score >= 4 else "LOW"
    logger.info(f"\n  NIVEAU GLOBAL : {grade} (score: {score:.1f}/10)")

    return {
        "total": n,
        "global_accuracy": global_pct,
        "by_market": {
            k: {"accuracy": round(v["wins"] / v["total"] * 100, 1) if v["total"] else 0}
            for k, v in by_market.items()
        },
        "grade": grade,
    }


if __name__ == "__main__":
    run_nhl_backtest()
