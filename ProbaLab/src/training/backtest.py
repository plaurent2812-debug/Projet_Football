from __future__ import annotations

"""
backtest.py — Backtest complet du système de prédiction.

Analyse la performance historique des prédictions vs résultats réels :
  1. Accuracy par marché (1X2, BTTS, Over/Under)
  2. Brier Score & Log Loss (calibration)
  3. Courbe de calibration (reliability diagram)
  4. ROI simulé avec Kelly Criterion
  5. Performance par ligue, par confiance, par mois
  6. Détection de dérive temporelle
  7. Analyse des échecs haute-confiance

Usage :
    python -m src.training.backtest
"""
import math
from collections import defaultdict
from datetime import datetime

from src.config import LEAGUES, logger, supabase
from src.constants import KELLY_FRACTION, KELLY_MAX_BET_FRACTION, MIN_VALUE_EDGE

# ═══════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════


def _load_backtest_data() -> list[dict]:
    """Load all prediction_results rows with their prediction data."""
    results = supabase.table("prediction_results").select("*").execute().data
    if not results:
        logger.warning("Aucune donnée dans prediction_results. Lance d'abord evaluate.py.")
        return []
    return results


def _load_fixtures_with_odds() -> dict[str, dict]:
    """Load finished fixtures with their odds for ROI simulation."""
    fixtures = (
        supabase.table("fixtures")
        .select("id, api_fixture_id, home_team, away_team, league_id, date")
        .eq("status", "FT")
        .execute()
        .data
    )
    fix_map = {f["id"]: f for f in fixtures}

    # Load odds
    odds_rows = supabase.table("fixture_odds").select("*").execute().data
    odds_by_fixture_api = {}
    for o in odds_rows:
        fid = o.get("fixture_api_id")
        if fid:
            odds_by_fixture_api[fid] = o

    # Merge odds into fixtures
    for f in fixtures:
        api_id = f.get("api_fixture_id")
        if api_id and api_id in odds_by_fixture_api:
            fix_map[f["id"]]["odds"] = odds_by_fixture_api[api_id]

    return fix_map


# ═══════════════════════════════════════════════════════════════════
#  CORE METRICS
# ═══════════════════════════════════════════════════════════════════


def _accuracy_report(results: list[dict]) -> dict[str, dict]:
    """Compute accuracy for each bet type."""
    metrics = {
        "1X2": "result_1x2_ok",
        "BTTS": "btts_ok",
        "Over 0.5": "over_05_ok",
        "Over 1.5": "over_15_ok",
        "Over 2.5": "over_25_ok",
        "Score exact": "correct_score_ok",
        "Pari recommandé": "recommended_bet_ok",
    }
    report = {}
    for label, field in metrics.items():
        evaluated = [r for r in results if r.get(field) is not None]
        if not evaluated:
            continue
        ok = sum(1 for r in evaluated if r[field])
        total = len(evaluated)
        report[label] = {
            "correct": ok,
            "total": total,
            "accuracy": round(ok / total * 100, 1),
        }
    return report


def _calibration_metrics(results: list[dict]) -> dict[str, float]:
    """Compute Brier score and Log Loss from raw predictions (not stored values).

    Recalculates from pred_home/draw/away + actual_result to avoid
    inconsistencies in stored values (some may use /3, others not).
    """
    briers: list[float] = []
    lls: list[float] = []
    eps = 1e-10

    for r in results:
        p_h = r.get("pred_home")
        p_d = r.get("pred_draw")
        p_a = r.get("pred_away")
        actual = r.get("actual_result")
        if p_h is None or actual is None:
            continue

        # Brier score (standard multi-class, NOT divided by 3)
        oh = 1.0 if actual == "H" else 0.0
        od = 1.0 if actual == "D" else 0.0
        oa = 1.0 if actual == "A" else 0.0
        brier = (p_h / 100 - oh) ** 2 + (p_d / 100 - od) ** 2 + (p_a / 100 - oa) ** 2
        briers.append(brier)

        # Log loss
        if actual == "H":
            lls.append(-math.log(max(p_h / 100, eps)))
        elif actual == "D":
            lls.append(-math.log(max(p_d / 100, eps)))
        else:
            lls.append(-math.log(max(p_a / 100, eps)))

    return {
        "avg_brier": round(sum(briers) / len(briers), 4) if briers else None,
        "avg_log_loss": round(sum(lls) / len(lls), 4) if lls else None,
        "n_brier": len(briers),
        "n_log_loss": len(lls),
    }


def _calibration_curve(results: list[dict], n_bins: int = 10) -> list[dict]:
    """Build a reliability diagram: predicted vs actual frequency.

    Groups predictions into probability bins and compares the mean
    predicted probability against the actual hit rate.
    """
    # Collect (predicted_prob, actual_outcome) for each 1X2 class
    pairs: list[tuple[float, float]] = []
    for r in results:
        p_h = r.get("pred_home")
        p_d = r.get("pred_draw")
        p_a = r.get("pred_away")
        actual = r.get("actual_result")
        if p_h is None or actual is None:
            continue
        # Add all three classes
        pairs.append((p_h / 100, 1.0 if actual == "H" else 0.0))
        pairs.append((p_d / 100, 1.0 if actual == "D" else 0.0))
        pairs.append((p_a / 100, 1.0 if actual == "A" else 0.0))

    if not pairs:
        return []

    # Bin
    bin_size = 1.0 / n_bins
    bins: list[dict] = []
    for i in range(n_bins):
        lo = i * bin_size
        hi = (i + 1) * bin_size
        in_bin = [(p, a) for p, a in pairs if lo <= p < hi]
        if not in_bin:
            continue
        mean_pred = sum(p for p, _ in in_bin) / len(in_bin)
        mean_actual = sum(a for _, a in in_bin) / len(in_bin)
        bins.append(
            {
                "bin": f"{round(lo * 100)}-{round(hi * 100)}%",
                "mean_predicted": round(mean_pred * 100, 1),
                "actual_frequency": round(mean_actual * 100, 1),
                "count": len(in_bin),
                "gap": round(abs(mean_pred - mean_actual) * 100, 1),
            }
        )
    return bins


# ═══════════════════════════════════════════════════════════════════
#  ROI SIMULATION (Kelly Criterion)
# ═══════════════════════════════════════════════════════════════════


def _simulate_kelly_roi(
    results: list[dict],
    fixtures: dict[str, dict],
    initial_bankroll: float = 1000.0,
) -> dict:
    """Simulate betting with Kelly Criterion on historical predictions.

    For each prediction where we have odds, compute the Kelly stake
    and simulate the P&L.
    """
    bankroll = initial_bankroll
    bets_placed = 0
    bets_won = 0
    total_staked = 0.0
    total_returned = 0.0
    history: list[dict] = []
    skipped_no_odds = 0
    skipped_no_edge = 0

    for r in results:
        fid = r.get("fixture_id")
        if not fid or fid not in fixtures:
            continue

        fix = fixtures[fid]
        odds_data = fix.get("odds")
        if not odds_data:
            skipped_no_odds += 1
            continue

        # Determine best bet: the outcome with highest predicted probability
        p_h = r.get("pred_home", 33)
        p_d = r.get("pred_draw", 33)
        p_a = r.get("pred_away", 33)
        actual = r.get("actual_result")

        # Map to odds
        bets = []
        h_odds = odds_data.get("home_win_odds") or odds_data.get("odds_home")
        d_odds = odds_data.get("draw_odds") or odds_data.get("odds_draw")
        a_odds = odds_data.get("away_win_odds") or odds_data.get("odds_away")

        if h_odds and float(h_odds) > 1:
            bets.append(("H", p_h / 100, float(h_odds)))
        if d_odds and float(d_odds) > 1:
            bets.append(("D", p_d / 100, float(d_odds)))
        if a_odds and float(a_odds) > 1:
            bets.append(("A", p_a / 100, float(a_odds)))

        if not bets:
            skipped_no_odds += 1
            continue

        # Find the value bet with highest edge
        best_bet = None
        best_edge = 0
        best_kelly = 0

        for outcome, prob, odds in bets:
            edge = prob * odds - 1.0
            if edge > MIN_VALUE_EDGE:
                kelly_full = edge / (odds - 1.0) if odds > 1.0 else 0
                kelly_stake = kelly_full * KELLY_FRACTION  # Quarter-Kelly
                kelly_stake = min(kelly_stake, KELLY_MAX_BET_FRACTION)  # Cap at 5%

                if edge > best_edge:
                    best_edge = edge
                    best_kelly = kelly_stake
                    best_bet = (outcome, prob, odds)

        if not best_bet:
            skipped_no_edge += 1
            continue

        outcome, prob, odds = best_bet
        stake = round(bankroll * best_kelly, 2)

        if stake < 1.0:
            skipped_no_edge += 1
            continue

        # Place bet
        bets_placed += 1
        total_staked += stake
        bankroll -= stake

        won = outcome == actual
        if won:
            winnings = stake * odds
            bankroll += winnings
            total_returned += winnings
            bets_won += 1

        history.append(
            {
                "fixture_id": fid,
                "outcome": outcome,
                "prob": round(prob * 100, 1),
                "odds": odds,
                "edge": round(best_edge * 100, 1),
                "stake": stake,
                "won": won,
                "bankroll": round(bankroll, 2),
            }
        )

    roi = ((total_returned - total_staked) / total_staked * 100) if total_staked > 0 else 0

    return {
        "initial_bankroll": initial_bankroll,
        "final_bankroll": round(bankroll, 2),
        "profit": round(bankroll - initial_bankroll, 2),
        "roi_pct": round(roi, 2),
        "bets_placed": bets_placed,
        "bets_won": bets_won,
        "win_rate": round(bets_won / bets_placed * 100, 1) if bets_placed > 0 else 0,
        "total_staked": round(total_staked, 2),
        "total_returned": round(total_returned, 2),
        "avg_odds": round(sum(h["odds"] for h in history) / len(history), 2) if history else 0,
        "avg_edge": round(sum(h["edge"] for h in history) / len(history), 1) if history else 0,
        "skipped_no_odds": skipped_no_odds,
        "skipped_no_edge": skipped_no_edge,
        "history": history,
    }


# ═══════════════════════════════════════════════════════════════════
#  SEGMENTED ANALYSIS
# ═══════════════════════════════════════════════════════════════════


def _by_league(results: list[dict]) -> dict[int, dict]:
    """Break down accuracy and calibration by league."""
    league_map = {lg["id"]: lg["name"] for lg in LEAGUES}
    by_lid: dict[int, list[dict]] = defaultdict(list)
    for r in results:
        lid = r.get("league_id")
        if lid:
            by_lid[lid].append(r)

    report = {}
    for lid, group in sorted(by_lid.items()):
        ok = sum(1 for r in group if r.get("result_1x2_ok"))
        briers = [r["brier_score_1x2"] for r in group if r.get("brier_score_1x2") is not None]
        avg_brier = round(sum(briers) / len(briers), 4) if briers else None
        report[lid] = {
            "name": league_map.get(lid, f"League {lid}"),
            "n": len(group),
            "accuracy_1x2": round(ok / len(group) * 100, 1) if group else 0,
            "avg_brier": avg_brier,
        }
    return report


def _by_confidence(results: list[dict]) -> list[dict]:
    """Break down accuracy by confidence score bucket."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        conf = r.get("pred_confidence")
        if conf is None:
            continue
        if conf <= 3:
            buckets["1-3 (low)"].append(r)
        elif conf <= 6:
            buckets["4-6 (medium)"].append(r)
        else:
            buckets["7-10 (high)"].append(r)

    report = []
    for label in ["1-3 (low)", "4-6 (medium)", "7-10 (high)"]:
        group = buckets.get(label, [])
        if not group:
            continue
        ok = sum(1 for r in group if r.get("result_1x2_ok"))
        report.append(
            {
                "confidence": label,
                "n": len(group),
                "accuracy_1x2": round(ok / len(group) * 100, 1),
            }
        )
    return report


def _by_month(results: list[dict], fixtures: dict[str, dict]) -> list[dict]:
    """Break down performance by month to detect drift."""
    monthly: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        fid = r.get("fixture_id")
        fix = fixtures.get(fid) if fid else None
        if fix and fix.get("date"):
            try:
                dt = datetime.fromisoformat(fix["date"].replace("Z", "+00:00"))
                key = dt.strftime("%Y-%m")
                monthly[key].append(r)
            except (ValueError, TypeError):
                pass

    report = []
    for month in sorted(monthly.keys()):
        group = monthly[month]
        ok = sum(1 for r in group if r.get("result_1x2_ok"))
        briers = [r["brier_score_1x2"] for r in group if r.get("brier_score_1x2") is not None]
        avg_brier = round(sum(briers) / len(briers), 4) if briers else None
        report.append(
            {
                "month": month,
                "n": len(group),
                "accuracy_1x2": round(ok / len(group) * 100, 1) if group else 0,
                "avg_brier": avg_brier,
            }
        )
    return report


def _high_confidence_failures(results: list[dict]) -> list[dict]:
    """Find predictions where confidence was high but result was wrong."""
    failures = []
    for r in results:
        conf = r.get("pred_confidence") or 0
        if conf >= 7 and not r.get("result_1x2_ok"):
            max_pred = max(r.get("pred_home", 0), r.get("pred_draw", 0), r.get("pred_away", 0))
            failures.append(
                {
                    "fixture_id": r.get("fixture_id"),
                    "league_id": r.get("league_id"),
                    "confidence": conf,
                    "pred_home": r.get("pred_home"),
                    "pred_draw": r.get("pred_draw"),
                    "pred_away": r.get("pred_away"),
                    "actual_result": r.get("actual_result"),
                    "actual_score": f"{r.get('actual_home_goals', '?')}-{r.get('actual_away_goals', '?')}",
                    "max_pred": max_pred,
                }
            )
    return sorted(failures, key=lambda x: -x["confidence"])


# ═══════════════════════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════════════════════


def _print_section(title: str) -> None:
    logger.info("")
    logger.info(f"{'=' * 64}")
    logger.info(f"  {title}")
    logger.info(f"{'=' * 64}")


def _bar(pct: float, width: int = 20) -> str:
    filled = int(pct / (100 / width))
    return "█" * filled + "░" * (width - filled)


def run_backtest() -> dict:
    """Run the full backtest pipeline and return all metrics."""
    _print_section("BACKTEST COMPLET DU SYSTÈME DE PRÉDICTION")

    results = _load_backtest_data()
    if not results:
        return {}

    fixtures = _load_fixtures_with_odds()

    # Enrich results with fixture data (league_id, date) if missing
    for r in results:
        fid = r.get("fixture_id")
        fix = fixtures.get(fid) if fid else None
        if fix:
            if not r.get("league_id"):
                r["league_id"] = fix.get("league_id")

    n = len(results)
    logger.info(f"  {n} prédictions évaluées chargées")

    # ── 1. Accuracy ──────────────────────────────────────────────
    _print_section("1. ACCURACY PAR MARCHÉ")
    acc = _accuracy_report(results)
    for label, data in acc.items():
        logger.info(
            f"  {label:20s} {_bar(data['accuracy'])} "
            f"{data['accuracy']:5.1f}% ({data['correct']}/{data['total']})"
        )

    # ── 2. Calibration ───────────────────────────────────────────
    _print_section("2. CALIBRATION (Brier Score & Log Loss)")
    cal = _calibration_metrics(results)
    if cal["avg_brier"] is not None:
        brier = cal["avg_brier"]
        # Standard multi-class Brier (NOT /3): random baseline = 0.667
        grade = (
            "EXCELLENT"
            if brier < 0.50
            else "BON"
            if brier < 0.58
            else "MOYEN"
            if brier < 0.63
            else "FAIBLE"
        )
        logger.info(f"  Brier Score moyen  : {brier:.4f}  [{grade}]")
        logger.info("    (réf: random=0.667, <0.50 excellent, <0.58 bon, <0.63 moyen)")
    if cal["avg_log_loss"] is not None:
        ll = cal["avg_log_loss"]
        grade = (
            "EXCELLENT" if ll < 0.9 else "BON" if ll < 1.05 else "MOYEN" if ll < 1.2 else "FAIBLE"
        )
        logger.info(f"  Log Loss moyen     : {ll:.4f}  [{grade}]")
        logger.info("    (réf: random=1.099, <0.90 excellent, <1.05 bon, <1.20 moyen)")

    # ── 3. Reliability Diagram ───────────────────────────────────
    _print_section("3. COURBE DE CALIBRATION (Reliability Diagram)")
    cal_curve = _calibration_curve(results)
    if cal_curve:
        logger.info(f"  {'Bin':>12s} {'Prédit':>8s} {'Réel':>8s} {'Écart':>7s} {'N':>6s}")
        logger.info(f"  {'─' * 12} {'─' * 8} {'─' * 8} {'─' * 7} {'─' * 6}")
        total_gap = 0
        for b in cal_curve:
            logger.info(
                f"  {b['bin']:>12s} {b['mean_predicted']:>7.1f}% {b['actual_frequency']:>7.1f}% "
                f"{b['gap']:>6.1f}% {b['count']:>5d}"
            )
            total_gap += b["gap"] * b["count"]
        n_total = sum(b["count"] for b in cal_curve)
        avg_gap = total_gap / n_total if n_total > 0 else 0
        logger.info(f"  Écart moyen pondéré : {avg_gap:.1f}% (plus bas = mieux calibré)")

    # ── 4. Kelly ROI Simulation ──────────────────────────────────
    _print_section("4. SIMULATION ROI (Kelly Criterion)")
    kelly = _simulate_kelly_roi(results, fixtures)
    if kelly["bets_placed"] > 0:
        logger.info(f"  Bankroll initial : {kelly['initial_bankroll']:.0f}€")
        logger.info(f"  Bankroll final   : {kelly['final_bankroll']:.2f}€")
        profit_sign = "+" if kelly["profit"] >= 0 else ""
        logger.info(f"  Profit/Perte     : {profit_sign}{kelly['profit']:.2f}€")
        logger.info(f"  ROI              : {profit_sign}{kelly['roi_pct']:.1f}%")
        logger.info(
            f"  Paris placés     : {kelly['bets_placed']} (gagnés: {kelly['bets_won']}, win rate: {kelly['win_rate']}%)"
        )
        logger.info(f"  Total misé       : {kelly['total_staked']:.2f}€")
        logger.info(f"  Cote moyenne     : {kelly['avg_odds']:.2f}")
        logger.info(f"  Edge moyen       : {kelly['avg_edge']:.1f}%")
        logger.info(f"  Ignorés (pas de cotes) : {kelly['skipped_no_odds']}")
        logger.info(f"  Ignorés (pas d'edge)   : {kelly['skipped_no_edge']}")
    else:
        logger.info("  Aucun pari simulé (pas de cotes disponibles ou pas d'edge)")
        logger.info(
            f"  Ignorés: {kelly['skipped_no_odds']} sans cotes, {kelly['skipped_no_edge']} sans edge"
        )

    # ── 5. By League ─────────────────────────────────────────────
    _print_section("5. PERFORMANCE PAR LIGUE")
    leagues = _by_league(results)
    logger.info(f"  {'Ligue':25s} {'N':>5s} {'Acc 1X2':>8s} {'Brier':>8s}")
    logger.info(f"  {'─' * 25} {'─' * 5} {'─' * 8} {'─' * 8}")
    for data in leagues.values():
        brier_str = f"{data['avg_brier']:.4f}" if data["avg_brier"] is not None else "   N/A"
        logger.info(
            f"  {data['name']:25s} {data['n']:>5d} {data['accuracy_1x2']:>7.1f}% {brier_str:>8s}"
        )

    # ── 6. By Confidence ─────────────────────────────────────────
    _print_section("6. PERFORMANCE PAR NIVEAU DE CONFIANCE")
    conf = _by_confidence(results)
    for c in conf:
        logger.info(
            f"  Confiance {c['confidence']:15s} : {_bar(c['accuracy_1x2'])} "
            f"{c['accuracy_1x2']:5.1f}% (n={c['n']})"
        )

    # ── 7. Monthly Drift ─────────────────────────────────────────
    _print_section("7. DÉRIVE TEMPORELLE (par mois)")
    monthly = _by_month(results, fixtures)
    if monthly:
        logger.info(f"  {'Mois':>8s} {'N':>5s} {'Acc 1X2':>8s} {'Brier':>8s}")
        logger.info(f"  {'─' * 8} {'─' * 5} {'─' * 8} {'─' * 8}")
        for m in monthly:
            brier_str = f"{m['avg_brier']:.4f}" if m["avg_brier"] is not None else "   N/A"
            logger.info(
                f"  {m['month']:>8s} {m['n']:>5d} {m['accuracy_1x2']:>7.1f}% {brier_str:>8s}"
            )

    # ── 8. High-Confidence Failures ──────────────────────────────
    _print_section("8. ÉCHECS HAUTE CONFIANCE (confiance >= 7)")
    failures = _high_confidence_failures(results)
    if failures:
        logger.info(f"  {len(failures)} échecs haute confiance trouvés :")
        for f in failures[:15]:  # Top 15
            league_name = next(
                (lg["name"] for lg in LEAGUES if lg["id"] == f["league_id"]), f"L{f['league_id']}"
            )
            logger.info(
                f"    conf={f['confidence']} | {f['pred_home']}-{f['pred_draw']}-{f['pred_away']}% "
                f"→ réel {f['actual_result']} ({f['actual_score']}) | {league_name}"
            )
    else:
        logger.info("  Aucun échec haute confiance.")

    # ── 9. Diagnostic Final ──────────────────────────────────────
    _print_section("9. DIAGNOSTIC FINAL")
    _print_diagnostic(acc, cal, kelly, conf, cal_curve)

    return {
        "accuracy": acc,
        "calibration": cal,
        "calibration_curve": cal_curve,
        "kelly_simulation": {k: v for k, v in kelly.items() if k != "history"},
        "by_league": leagues,
        "by_confidence": conf,
        "monthly": monthly,
        "high_confidence_failures": len(failures),
    }


def _print_diagnostic(
    acc: dict,
    cal: dict,
    kelly: dict,
    conf: list[dict],
    cal_curve: list[dict],
) -> None:
    """Print a final diagnostic summary with actionable insights."""
    issues = []
    strengths = []

    # Accuracy check
    acc_1x2 = acc.get("1X2", {}).get("accuracy", 0)
    if acc_1x2 >= 50:
        strengths.append(f"1X2 accuracy ({acc_1x2}%) au-dessus du baseline aléatoire (33%)")
    elif acc_1x2 >= 40:
        issues.append(f"1X2 accuracy ({acc_1x2}%) correcte mais améliorable")
    else:
        issues.append(f"1X2 accuracy ({acc_1x2}%) FAIBLE — vérifier le pipeline")

    # Brier check (standard multi-class, random baseline = 0.667)
    brier = cal.get("avg_brier")
    if brier is not None:
        if brier < 0.50:
            strengths.append(f"Brier Score ({brier:.4f}) excellent — probas bien calibrées")
        elif brier < 0.58:
            strengths.append(f"Brier Score ({brier:.4f}) bon — probas correctement calibrées")
        elif brier < 0.63:
            issues.append(f"Brier Score ({brier:.4f}) moyen — calibration à améliorer")
        else:
            issues.append(f"Brier Score ({brier:.4f}) faible — probas proches du random (0.667)")

    # Calibration curve check
    if cal_curve:
        avg_gap = sum(b["gap"] * b["count"] for b in cal_curve) / sum(b["count"] for b in cal_curve)
        if avg_gap < 3:
            strengths.append(f"Calibration très précise (écart moyen {avg_gap:.1f}%)")
        elif avg_gap < 6:
            pass  # Acceptable
        else:
            issues.append(
                f"Calibration imprécise (écart moyen {avg_gap:.1f}%) — activer/recalibrer Platt/Isotonic"
            )

    # Kelly check
    if kelly["bets_placed"] > 0:
        if kelly["roi_pct"] > 5:
            strengths.append(f"Kelly ROI positif ({kelly['roi_pct']:.1f}%) — edge réel détecté")
        elif kelly["roi_pct"] > 0:
            strengths.append(f"Kelly ROI légèrement positif ({kelly['roi_pct']:.1f}%)")
        else:
            issues.append(
                f"Kelly ROI négatif ({kelly['roi_pct']:.1f}%) — pas d'edge réel sur les cotes"
            )
    else:
        issues.append("Pas de simulation Kelly possible (cotes manquantes)")

    # Confidence monotonicity check
    if len(conf) >= 2:
        accs = [c["accuracy_1x2"] for c in conf]
        if accs == sorted(accs):
            strengths.append("Confiance monotone : haute confiance = meilleure accuracy")
        else:
            issues.append("Confiance NON monotone : haute confiance ne corrèle pas avec accuracy")

    # Print
    if strengths:
        logger.info("  POINTS FORTS :")
        for s in strengths:
            logger.info(f"    + {s}")

    if issues:
        logger.info("  POINTS D'ATTENTION :")
        for i in issues:
            logger.info(f"    - {i}")

    if not issues:
        logger.info("  Aucun problème majeur détecté.")

    # Overall grade
    score = 0
    score += min(3, acc_1x2 / 20)  # 0-3 points
    if brier is not None:
        # Standard multi-class: 0.667=random → 0pts, 0.40=excellent → 3pts
        score += max(0, min(3, (0.667 - brier) / 0.267 * 3))
    if kelly["bets_placed"] > 0 and kelly["roi_pct"] > 0:
        score += min(2, kelly["roi_pct"] / 5)  # 0-2 points
    if len(conf) >= 2:
        accs = [c["accuracy_1x2"] for c in conf]
        if accs == sorted(accs):
            score += 2  # 0-2 points

    grade = "HIGH" if score >= 7 else "MEDIUM" if score >= 4 else "LOW"
    logger.info(f"\n  NIVEAU GLOBAL : {grade} (score: {score:.1f}/10)")


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    run_backtest()
