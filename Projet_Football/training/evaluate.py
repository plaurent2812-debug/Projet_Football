from __future__ import annotations

"""
evaluate.py — Évaluation des prédictions vs résultats réels.

Workflow :
  1. Récupère les matchs terminés (FT) qui ont une prédiction
  2. Croise prédictions vs résultats réels
  3. Détermine si chaque type de pari était correct
  4. Génère une analyse post-match (rule-based, pas de Claude)
  5. Sauvegarde dans prediction_results
  6. Affiche un résumé global de performance
  7. Évalue les tickets SAFE / FUN / JACKPOT de l'onglet Pronos
"""
import math
from collections import defaultdict

from config import SEASON, logger, supabase

# ═══════════════════════════════════════════════════════════════════
#  ÉVALUATION D'UN MATCH
# ═══════════════════════════════════════════════════════════════════


def evaluate_match(fixture: dict, prediction: dict) -> dict:
    """Compare a prediction with the actual result of a finished match.

    Computes correctness flags for every bet type (1X2, BTTS, Over/Under,
    correct score, scorer, penalty), calibration metrics (Brier score,
    log-loss), and a rule-based post-match narrative.

    Args:
        fixture: A fixture row dict (must contain ``home_goals``,
            ``away_goals``, and metadata fields).
        prediction: A prediction row dict with probability columns and
            recommended bet.

    Returns:
        A dict ready to upsert into ``prediction_results``.
    """
    hg: int = fixture["home_goals"] or 0
    ag: int = fixture["away_goals"] or 0
    total_goals: int = hg + ag

    # Résultat réel
    if hg > ag:
        actual_result = "H"
    elif hg == ag:
        actual_result = "D"
    else:
        actual_result = "A"

    actual_btts: bool = hg > 0 and ag > 0
    actual_over_05: bool = total_goals > 0
    actual_over_15: bool = total_goals > 1
    actual_over_25: bool = total_goals > 2

    # Score exact correct ?
    pred_score: str = prediction.get("correct_score", "")
    actual_correct_score: bool = False
    if pred_score:
        try:
            ph, pa = pred_score.split("-")
            actual_correct_score = int(ph) == hg and int(pa) == ag
        except (ValueError, AttributeError):
            pass

    # Vérifier si penalty dans le match (via match_events)
    actual_had_penalty: bool = _check_penalty(fixture.get("api_fixture_id"))

    # Vérifier si le buteur prédit a marqué
    actual_scorers_list: list[str] = _get_scorers(fixture.get("api_fixture_id"))
    pred_scorer: str = prediction.get("likely_scorer", "")
    scorer_ok: bool = False
    if pred_scorer and actual_scorers_list:
        # Matching souple : le nom prédit est contenu dans un des buteurs réels
        pred_lower = pred_scorer.lower()
        for s in actual_scorers_list:
            if pred_lower in s.lower() or s.lower() in pred_lower:
                scorer_ok = True
                break

    # ── Évaluation des paris ─────────────────────────────────────
    p_h: int = prediction.get("proba_home", 33)
    p_d: int = prediction.get("proba_draw", 33)
    p_a: int = prediction.get("proba_away", 33)

    # 1X2 : la proba max correspond-elle au résultat ?
    max_pred: int = max(p_h, p_d, p_a)
    if max_pred == p_h:
        pred_result = "H"
    elif max_pred == p_a:
        pred_result = "A"
    else:
        pred_result = "D"
    result_1x2_ok: bool = pred_result == actual_result

    # BTTS
    p_btts: int = prediction.get("proba_btts", 50)
    btts_ok: bool = (p_btts >= 50) == actual_btts

    # Over 0.5
    p_o05: int = prediction.get("proba_over_05", 90)
    over_05_ok: bool = (p_o05 >= 50) == actual_over_05

    # Over 1.5
    p_o15: int = prediction.get("proba_over_15", 70)
    over_15_ok: bool = (p_o15 >= 50) == actual_over_15

    # Over 2.5
    p_o25: int = prediction.get("proba_over_2_5", 50)
    over_25_ok: bool = (p_o25 >= 50) == actual_over_25

    # Penalty
    p_pen: int = prediction.get("proba_penalty") or 0
    penalty_ok: bool = (p_pen >= 30) == actual_had_penalty

    # Pari recommandé
    recommended_bet_ok: bool = _check_recommended_bet(
        prediction.get("recommended_bet", ""),
        actual_result,
        actual_btts,
        actual_over_25,
        total_goals,
    )

    # ── Brier score (mesure de calibration) ──────────────────────
    # Brier = (proba_prédit - outcome)^2, moyenné sur les 3 issues
    outcome_h: float = 1.0 if actual_result == "H" else 0.0
    outcome_d: float = 1.0 if actual_result == "D" else 0.0
    outcome_a: float = 1.0 if actual_result == "A" else 0.0
    brier: float = (
        (p_h / 100 - outcome_h) ** 2 + (p_d / 100 - outcome_d) ** 2 + (p_a / 100 - outcome_a) ** 2
    ) / 3

    # Log loss
    eps: float = 1e-10
    ll: float
    if actual_result == "H":
        ll = -math.log(max(p_h / 100, eps))
    elif actual_result == "D":
        ll = -math.log(max(p_d / 100, eps))
    else:
        ll = -math.log(max(p_a / 100, eps))

    # ── Analyse post-match ───────────────────────────────────────
    post_analysis: str = _generate_post_analysis(
        fixture,
        prediction,
        actual_result,
        hg,
        ag,
        result_1x2_ok,
        btts_ok,
        over_25_ok,
        scorer_ok,
        actual_had_penalty,
    )

    return {
        "fixture_id": fixture["id"],
        "prediction_id": prediction.get("id"),
        "league_id": fixture.get("league_id"),
        "season": SEASON,
        "pred_home": p_h,
        "pred_draw": p_d,
        "pred_away": p_a,
        "pred_btts": p_btts,
        "pred_over_05": p_o05,
        "pred_over_15": p_o15,
        "pred_over_25": p_o25,
        "pred_correct_score": pred_score,
        "pred_likely_scorer": pred_scorer,
        "pred_penalty": p_pen,
        "pred_recommended": prediction.get("recommended_bet", ""),
        "pred_confidence": prediction.get("confidence_score"),
        "model_version": prediction.get("model_version"),
        "actual_home_goals": hg,
        "actual_away_goals": ag,
        "actual_result": actual_result,
        "actual_btts": actual_btts,
        "actual_over_05": actual_over_05,
        "actual_over_15": actual_over_15,
        "actual_over_25": actual_over_25,
        "actual_correct_score": actual_correct_score,
        "actual_had_penalty": actual_had_penalty,
        "actual_scorers": actual_scorers_list or [],
        "result_1x2_ok": result_1x2_ok,
        "btts_ok": btts_ok,
        "over_05_ok": over_05_ok,
        "over_15_ok": over_15_ok,
        "over_25_ok": over_25_ok,
        "correct_score_ok": actual_correct_score,
        "penalty_ok": penalty_ok,
        "scorer_ok": scorer_ok,
        "recommended_bet_ok": recommended_bet_ok,
        "post_analysis": post_analysis,
        "brier_score_1x2": round(brier, 4),
        "log_loss": round(ll, 4),
    }


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def _check_penalty(fixture_api_id: int | None) -> bool:
    """Check whether a penalty was awarded in the given match.

    Args:
        fixture_api_id: API fixture identifier (may be ``None``).

    Returns:
        ``True`` if at least one penalty event is found, ``False``
        otherwise.
    """
    if not fixture_api_id:
        return False
    try:
        events = (
            supabase.table("match_events")
            .select("id")
            .eq("fixture_api_id", fixture_api_id)
            .eq("event_detail", "Penalty")
            .limit(1)
            .execute()
            .data
        )
        return len(events) > 0
    except Exception:
        return False  # Fail silently: penalty check is non-critical


def _get_scorers(fixture_api_id: int | None) -> list[str]:
    """Retrieve the list of distinct scorer names for a match.

    Args:
        fixture_api_id: API fixture identifier (may be ``None``).

    Returns:
        A list of unique player names who scored.
    """
    if not fixture_api_id:
        return []
    try:
        events = (
            supabase.table("match_events")
            .select("player_name")
            .eq("fixture_api_id", fixture_api_id)
            .eq("event_type", "Goal")
            .execute()
            .data
        )
        return list({e["player_name"] for e in events if e.get("player_name")})
    except Exception:
        return []  # Fail silently: scorer list is non-critical


def _check_recommended_bet(
    bet_text: str,
    actual_result: str,
    actual_btts: bool,
    actual_over_25: bool,
    total_goals: int,
) -> bool:
    """Determine whether a recommended bet text was a winner.

    Performs keyword-based matching against the actual match outcome.

    Args:
        bet_text: Free-text recommended bet string.
        actual_result: ``"H"``, ``"D"``, or ``"A"``.
        actual_btts: Whether both teams scored.
        actual_over_25: Whether the match had more than 2.5 goals.
        total_goals: Total number of goals scored.

    Returns:
        ``True`` if the bet text matches the actual outcome.
    """
    if not bet_text:
        return False
    bt: str = bet_text.lower()

    if "domicile" in bt or "victoire" in bt and "ext" not in bt:
        if actual_result == "H":
            return True
    if "extérieur" in bt or "ext" in bt or "visiteur" in bt:
        if actual_result == "A":
            return True
    if "nul" in bt:
        if actual_result == "D":
            return True
    if "btts" in bt or "deux" in bt and "marqu" in bt:
        return actual_btts
    if "2.5" in bt or "plus de 2" in bt:
        return actual_over_25
    if "1.5" in bt:
        return total_goals > 1

    # Fallback : vérifier par nom d'équipe
    return False


def _generate_post_analysis(
    fixture: dict,
    prediction: dict,
    actual_result: str,
    hg: int,
    ag: int,
    result_ok: bool,
    btts_ok: bool,
    over_ok: bool,
    scorer_ok: bool,
    had_penalty: bool,
) -> str:
    """Generate a rule-based post-match analysis narrative.

    Explains which bets were correct or incorrect with contextual
    details about confidence and probabilities.

    Args:
        fixture: The fixture row dict.
        prediction: The prediction row dict.
        actual_result: ``"H"``, ``"D"``, or ``"A"``.
        hg: Home goals scored.
        ag: Away goals scored.
        result_ok: Whether the 1X2 prediction was correct.
        btts_ok: Whether the BTTS prediction was correct.
        over_ok: Whether the Over 2.5 prediction was correct.
        scorer_ok: Whether the likely-scorer prediction was correct.
        had_penalty: Whether a penalty occurred in the match.

    Returns:
        A single-string narrative summary.
    """
    home: str = fixture["home_team"]
    away: str = fixture["away_team"]
    score: str = f"{hg}-{ag}"

    p_h: int = prediction.get("proba_home", 33)
    p_d: int = prediction.get("proba_draw", 33)
    p_a: int = prediction.get("proba_away", 33)
    confidence: int = prediction.get("confidence_score", 5)

    parts: list[str] = []
    parts.append(f"Score final : {home} {score} {away}.")

    # 1X2
    if result_ok:
        parts.append(f"✅ Résultat 1X2 correct (prédit {p_h}-{p_d}-{p_a}%).")
    else:
        max_p: int = max(p_h, p_d, p_a)
        if actual_result == "D":
            parts.append(f"❌ Nul non anticipé. Notre modèle donnait seulement {p_d}% au nul.")
        elif actual_result == "H":
            parts.append(f"❌ Victoire {home} non anticipée (on donnait {p_h}%).")
        else:
            parts.append(f"❌ Victoire {away} non anticipée (on donnait {p_a}%).")

        # Explication possible
        if max_p > 60 and not result_ok:
            parts.append("Le modèle était très confiant mais s'est trompé — biais possible.")
        if confidence >= 7 and not result_ok:
            parts.append(
                "Haute confiance mais échec : les facteurs qualitatifs (derby, motivation, tactique) n'ont pas été capturés."
            )

    # BTTS
    p_btts: int = prediction.get("proba_btts", 50)
    actual_btts: bool = hg > 0 and ag > 0
    if btts_ok:
        parts.append(f"✅ BTTS correct (prédit {p_btts}%, réel {'Oui' if actual_btts else 'Non'}).")
    else:
        if actual_btts:
            parts.append(f"❌ BTTS raté : les 2 ont marqué malgré seulement {p_btts}% prédit.")
        else:
            parts.append(f"❌ BTTS raté : {p_btts}% prédit mais une équipe n'a pas marqué.")

    # Over 2.5
    total: int = hg + ag
    p_o25: int = prediction.get("proba_over_2_5", 50)
    if over_ok:
        parts.append(f"✅ O2.5 correct ({total} buts, prédit {p_o25}%).")
    else:
        if total > 2:
            parts.append(f"❌ O2.5 raté : {total} buts mais on ne prédisait que {p_o25}%.")
        else:
            parts.append(f"❌ O2.5 raté : seulement {total} buts malgré {p_o25}% prédit.")

    # Buteur
    scorer: str = prediction.get("likely_scorer", "")
    if scorer:
        if scorer_ok:
            parts.append(f"✅ Buteur correct : {scorer} a bien marqué !")
        else:
            parts.append(f"❌ Buteur raté : {scorer} n'a pas marqué.")

    # Penalty
    if had_penalty:
        p_pen: int = prediction.get("proba_penalty", 0)
        parts.append(f"⚽ Penalty dans le match (prédit à {p_pen}%).")

    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════


def run_evaluation() -> None:
    """Evaluate all finished matches that have an unevaluated prediction.

    Fetches finished fixtures joined with predictions, evaluates each
    one, persists results, and prints global performance stats.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  📊 ÉVALUATION DES PRÉDICTIONS")
    logger.info("=" * 60)

    # 1. Matchs terminés avec prédiction
    finished = supabase.table("fixtures").select("*").eq("status", "FT").execute().data
    predictions = supabase.table("predictions").select("*").execute().data
    pred_map: dict = {p["fixture_id"]: p for p in predictions}

    # 2. Déjà évalués ?
    already = supabase.table("prediction_results").select("fixture_id").execute().data
    already_ids: set = {r["fixture_id"] for r in already}

    to_evaluate: list[tuple[dict, dict]] = []
    for f in finished:
        if f["id"] in pred_map and f["id"] not in already_ids:
            to_evaluate.append((f, pred_map[f["id"]]))

    logger.info(f"{len(to_evaluate)} matchs à évaluer (sur {len(finished)} terminés)")

    if not to_evaluate:
        logger.info("Rien de nouveau à évaluer.")
        _print_global_stats()
        return

    # 3. Évaluer chaque match
    results: list[dict] = []
    for fix, pred in to_evaluate:
        try:
            result = evaluate_match(fix, pred)
            results.append(result)
            status = "✅" if result["result_1x2_ok"] else "❌"
            logger.info(
                f"  {status} {fix['home_team']} {fix['home_goals']}-{fix['away_goals']} {fix['away_team']}"
            )
        except Exception as e:
            logger.warning(f"  ⚠️ Erreur {fix['home_team']} vs {fix['away_team']}: {e}")

    # 4. Sauvegarder
    if results:
        for r in results:
            try:
                supabase.table("prediction_results").upsert(r, on_conflict="fixture_id").execute()
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur sauvegarde: {e}")

        logger.info(f"✅ {len(results)} évaluations sauvegardées")

    # 5. Résumé global
    _print_global_stats()


def _print_global_stats() -> None:
    """Print an overview of prediction accuracy across all evaluated matches.

    Displays per-bet-type accuracy bars, average Brier score, and
    average log-loss.

    Returns:
        None.
    """
    all_results = supabase.table("prediction_results").select("*").execute().data

    if not all_results:
        logger.info("Pas encore de données de performance.")
        return

    n: int = len(all_results)
    logger.info(f"{'=' * 60}")
    logger.info(f"  📈 PERFORMANCE GLOBALE ({n} matchs évalués)")
    logger.info(f"{'=' * 60}")

    metrics: dict[str, str] = {
        "Résultat 1X2": "result_1x2_ok",
        "BTTS": "btts_ok",
        "Over 0.5": "over_05_ok",
        "Over 1.5": "over_15_ok",
        "Over 2.5": "over_25_ok",
        "Score exact": "correct_score_ok",
        "Buteur": "scorer_ok",
        "Penalty": "penalty_ok",
        "Pari recommandé": "recommended_bet_ok",
    }

    for label, field in metrics.items():
        ok = sum(1 for r in all_results if r.get(field))
        total = sum(1 for r in all_results if r.get(field) is not None)
        if total > 0:
            pct = round(ok / total * 100, 1)
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            logger.info(f"  {label:20s} {bar} {pct:5.1f}% ({ok}/{total})")

    # Brier score moyen
    briers: list[float] = [
        r["brier_score_1x2"] for r in all_results if r.get("brier_score_1x2") is not None
    ]
    if briers:
        avg_brier: float = sum(briers) / len(briers)
        logger.info(f"  Brier Score moyen : {avg_brier:.4f} (plus bas = mieux, <0.20 = excellent)")

    # Log loss moyen
    lls: list[float] = [r["log_loss"] for r in all_results if r.get("log_loss") is not None]
    if lls:
        avg_ll: float = sum(lls) / len(lls)
        logger.info(f"  Log Loss moyen   : {avg_ll:.4f} (plus bas = mieux, <1.0 = bon)")


# ═══════════════════════════════════════════════════════════════════
#  ÉVALUATION DES TICKETS (SAFE / FUN / JACKPOT)
# ═══════════════════════════════════════════════════════════════════


def _evaluate_single_pick(pick: dict, fixture: dict) -> bool:
    """Determine whether a single ticket pick was a winner.

    Args:
        pick: A ``ticket_picks`` row dict with ``bet_type``.
        fixture: A finished fixture dict with ``home_goals``,
            ``away_goals``, etc.

    Returns:
        ``True`` if the pick was a winner, ``False`` otherwise.
    """
    hg: int = fixture.get("home_goals") or 0
    ag: int = fixture.get("away_goals") or 0
    total_goals: int = hg + ag
    bet: str = pick.get("bet_type", "")

    if "Dom" in bet or "dom" in bet:
        return hg > ag
    if "Ext" in bet or "ext" in bet:
        return ag > hg
    if "BTTS" in bet or "btts" in bet:
        return hg > 0 and ag > 0
    if "2.5" in bet:
        return total_goals > 2
    if "1.5" in bet:
        return total_goals > 1
    if "Nul" in bet or "nul" in bet:
        return hg == ag

    return False


def evaluate_tickets() -> None:
    """Evaluate all ticket picks for finished matches not yet evaluated.

    Fetches unevaluated picks (``is_won IS NULL``), checks the actual
    match result, and updates each pick accordingly.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  🎫 ÉVALUATION DES TICKETS (SAFE / FUN / JACKPOT)")
    logger.info("=" * 60)

    # 1. Picks non évalués
    unevaluated = (
        supabase.table("ticket_picks")
        .select("*")
        .is_("is_won", "null")
        .execute()
        .data
    )

    if not unevaluated:
        logger.info("Aucun pick de ticket à évaluer.")
        _print_ticket_stats()
        return

    # 2. Récupérer les fixtures terminées correspondantes
    fixture_ids = list({p["fixture_id"] for p in unevaluated})
    finished_fixtures: dict[int, dict] = {}

    # Charger par lots de 50 pour éviter les requêtes trop longues
    for i in range(0, len(fixture_ids), 50):
        batch = fixture_ids[i : i + 50]
        rows = (
            supabase.table("fixtures")
            .select("*")
            .eq("status", "FT")
            .in_("id", batch)
            .execute()
            .data
        )
        for f in rows:
            finished_fixtures[f["id"]] = f

    if not finished_fixtures:
        logger.info("Aucun match terminé à évaluer pour les tickets.")
        _print_ticket_stats()
        return

    # 3. Évaluer chaque pick
    evaluated_count: int = 0
    for pick in unevaluated:
        fid = pick["fixture_id"]
        if fid not in finished_fixtures:
            continue  # Match pas encore terminé

        fixture = finished_fixtures[fid]
        is_won: bool = _evaluate_single_pick(pick, fixture)

        try:
            supabase.table("ticket_picks").update(
                {"is_won": is_won, "evaluated_at": "now()"}
            ).eq("id", pick["id"]).execute()
            evaluated_count += 1

            status = "✅" if is_won else "❌"
            logger.info(
                f"  {status} [{pick['ticket_type']}] "
                f"{pick['home_team']} vs {pick['away_team']} — "
                f"{pick['bet_type']} (conf {pick['confidence']}%)"
            )
        except Exception as e:
            logger.warning(f"  ⚠️ Erreur mise à jour pick {pick['id']}: {e}")

    logger.info(f"✅ {evaluated_count} picks de tickets évalués")

    # 4. Résumé
    _print_ticket_stats()


def _print_ticket_stats() -> None:
    """Print ticket performance statistics for each ticket type.

    Displays per-type pick accuracy, ticket win rate, and overall
    combined statistics.

    Returns:
        None.
    """
    all_picks = supabase.table("ticket_picks").select("*").execute().data

    if not all_picks:
        logger.info("Pas encore de données de tickets.")
        return

    logger.info(f"\n{'=' * 60}")
    logger.info(f"  🎫 PERFORMANCE DES TICKETS")
    logger.info(f"{'=' * 60}")

    for ticket_type in ["SAFE", "FUN", "JACKPOT"]:
        picks = [p for p in all_picks if p["ticket_type"] == ticket_type]
        if not picks:
            continue

        evaluated = [p for p in picks if p["is_won"] is not None]
        won = [p for p in evaluated if p["is_won"]]

        # Picks individuels
        total_eval = len(evaluated)
        total_won = len(won)
        pct = round(total_won / total_eval * 100, 1) if total_eval > 0 else 0

        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        logger.info(f"\n  🎫 {ticket_type}")
        logger.info(f"    Picks  : {bar} {pct:5.1f}% ({total_won}/{total_eval})")

        # Tickets complets (groupés par date)
        tickets_by_date: dict[str, list[dict]] = defaultdict(list)
        for p in picks:
            tickets_by_date[str(p["ticket_date"])].append(p)

        completed_tickets = 0
        won_tickets = 0
        for date, date_picks in tickets_by_date.items():
            if all(p["is_won"] is not None for p in date_picks):
                completed_tickets += 1
                if all(p["is_won"] for p in date_picks):
                    won_tickets += 1

        if completed_tickets > 0:
            ticket_pct = round(won_tickets / completed_tickets * 100, 1)
            logger.info(
                f"    Tickets: {won_tickets}/{completed_tickets} gagnés ({ticket_pct}%)"
            )


# ═══════════════════════════════════════════════════════════════════
#  ENTRÉE COMBINÉE : PRÉDICTIONS + TICKETS
# ═══════════════════════════════════════════════════════════════════


def run_full_evaluation() -> None:
    """Run both prediction evaluation and ticket evaluation.

    This is the main entry point for the "Performance Post-match"
    action, combining both analyses.

    Returns:
        None.
    """
    run_evaluation()
    evaluate_tickets()


if __name__ == "__main__":
    run_full_evaluation()
