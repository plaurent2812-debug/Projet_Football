import math
from datetime import datetime, timezone

from src.config import supabase


def calculate_metrics_for_match(pred_home_prob, pred_draw_prob, pred_away_prob, actual_result):
    """Calcule le Brier Score et le Log Loss pour un match 1X2."""
    probs = {"H": pred_home_prob, "D": pred_draw_prob, "A": pred_away_prob}

    # Validation : les probabilités doivent sommer à 1.0
    total_prob = sum(probs.values())
    if total_prob == 0:
        return None, None, False

    probs = {k: v / total_prob for k, v in probs.items()}

    # Encodage One-Hot de la réalité
    actual_one_hot = {"H": 0, "D": 0, "A": 0}
    if actual_result in actual_one_hot:
        actual_one_hot[actual_result] = 1

    # 1. Brier Score = Somme globale des (Prédiction - Réalité)^2
    brier_score = sum(
        (probs[outcome] - actual_one_hot[outcome]) ** 2 for outcome in ["H", "D", "A"]
    )

    # 2. Log Loss = -ln(Probabilité de l'événement qui s'est réellement produit)
    # Clip pour éviter log(0)
    epsilon = 1e-15
    prob_actual = max(min(probs.get(actual_result, 0), 1 - epsilon), epsilon)
    log_loss = -math.log(prob_actual)

    # 3. Prédiction correcte ? (1X2 OK)
    predicted_result = max(probs, key=probs.get)
    result_1x2_ok = predicted_result == actual_result

    return brier_score, log_loss, result_1x2_ok


def calculate_boolean_metrics(pred_prob, actual_boolean):
    """Calcule Brier Score et Log Loss pour une feature binaire (ex: BTTS, Over 2.5)."""
    if pred_prob is None or actual_boolean is None:
        return None, None, None

    prob_yes = pred_prob / 100.0 if pred_prob > 1 else pred_prob  # Handle 0-100 or 0-1
    prob_no = 1.0 - prob_yes

    actual_yes = 1 if actual_boolean else 0
    actual_no = 0 if actual_boolean else 1

    brier_score = ((prob_yes - actual_yes) ** 2) + ((prob_no - actual_no) ** 2)

    epsilon = 1e-15
    p_actual = prob_yes if actual_boolean else prob_no
    p_actual = max(min(p_actual, 1 - epsilon), epsilon)
    log_loss = -math.log(p_actual)

    is_ok = (prob_yes > 0.5) == actual_boolean

    return brier_score, log_loss, is_ok


def evaluate_recent_matches(days_back=7):
    """Récupère les matchs terminés récents et met à jour prediction_results dans Supabase."""

    print(f"[{datetime.now(timezone.utc)}] Démarrage de l'évaluation ML (Brier/LogLoss)...")

    # 1. Récupérer les fixtures terminées récemment
    from datetime import timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    fixtures_response = (
        supabase.table("fixtures")
        .select("id, home_goals, away_goals, status")
        .eq("status", "FT")
        .gte("date", cutoff)
        .execute()
    )

    fixtures = fixtures_response.data or []
    if not fixtures:
        print("Aucun match terminé récent trouvé.")
        return

    fixture_map = {f["id"]: f for f in fixtures}
    fixture_ids = list(fixture_map.keys())

    # 2. Récupérer les prédictions existantes pour ces fixtures
    predictions_response = (
        supabase.table("predictions").select("*").in_("fixture_id", fixture_ids).execute()
    )

    predictions = predictions_response.data or []
    if not predictions:
        print("Aucune prédiction correspondante trouvée.")
        return

    print(f"Évaluation de {len(predictions)} prédictions...")

    updates_count = 0

    for pred in predictions:
        fix = fixture_map.get(pred["fixture_id"])
        if not fix:
            continue

        # Parse stats_json
        stats = pred.get("stats_json") or {}
        if isinstance(stats, str):
            import json

            try:
                stats = json.loads(stats)
            except:
                stats = {}

        def get_val(key, default=None):
            val = pred.get(key)
            if val is not None:
                return val
            return stats.get(key, default)

        # Actuals
        hg = fix.get("home_goals", 0) or 0
        ag = fix.get("away_goals", 0) or 0
        total_goals = hg + ag
        actual_result = "H" if hg > ag else ("D" if hg == ag else "A")
        actual_btts = hg > 0 and ag > 0
        actual_over_05 = total_goals > 0.5
        actual_over_15 = total_goals > 1.5
        actual_over_25 = total_goals > 2.5

        # 1X2 Probs
        ph = get_val("proba_home")
        pd_val = get_val("proba_draw")
        pa = get_val("proba_away")

        if ph is not None and pd_val is not None and pa is not None:
            # Scale to 0-1
            if ph > 1 or pd_val > 1 or pa > 1:
                ph, pd_val, pa = ph / 100.0, pd_val / 100.0, pa / 100.0

            brier_1x2, ll_1x2, ok_1x2 = calculate_metrics_for_match(ph, pd_val, pa, actual_result)

            if brier_1x2 is not None:
                # Check if we already have a record in prediction_results
                existing_res = (
                    supabase.table("prediction_results")
                    .select("id")
                    .eq("fixture_id", fix["id"])
                    .execute()
                )

                record = {
                    "fixture_id": fix["id"],
                    "prediction_id": pred["id"],
                    "pred_home": int(ph * 100),
                    "pred_draw": int(pd_val * 100),
                    "pred_away": int(pa * 100),
                    "actual_result": actual_result,
                    "actual_home_goals": hg,
                    "actual_away_goals": ag,
                    "brier_score_1x2": round(brier_1x2, 4),
                    "log_loss": round(ll_1x2, 4),
                    "result_1x2_ok": ok_1x2,
                    "model_version": "v1",
                }

                if existing_res.data:
                    # Update
                    supabase.table("prediction_results").update(record).eq(
                        "id", existing_res.data[0]["id"]
                    ).execute()
                else:
                    # Insert
                    supabase.table("prediction_results").insert(record).execute()

                updates_count += 1
                print(
                    f"Match {fix['id']} ({actual_result}) -> Brier: {brier_1x2:.3f}, LogLoss: {ll_1x2:.3f}"
                )

    print(f"[{datetime.now(timezone.utc)}] ✅ Terminé. {updates_count} matchs évalués/mis à jour.")

    # ─── Backtest Reminder Logic ──────────────────────────────────
    # User requested a notification to run a backtest after 30-50 new matches.
    # Baseline was 126 matches at the time of this implementation.
    try:
        total_res = supabase.table("prediction_results").select("id", count="exact").execute()
        total_count = total_res.count or 0

        # We'll use 126 as the baseline (last big batch)
        # We alert every 30 matches above that baseline
        baseline = 126
        diff = total_count - baseline

        if diff >= 30:
            from src.notifications import send_telegram
            msg = (
                f"📊 *Rappel Backtest — ProbaLab*\n\n"
                f"Il y a maintenant *{total_count}* matchs évalués (soit *+{diff}* nouveaux).\n\n"
                f"C'est le moment idéal pour relancer un backtest et vérifier l'impact des dernières corrections !\n\n"
                f"👉 `python3 -m src.training.backtest`"
            )
            send_telegram(msg, parse_mode="Markdown")
            print(f"[Reminder] Notification envoyée (diff={diff})")
    except Exception as e:
        print(f"[Reminder] Erreur lors du calcul du rappel: {e}")


if __name__ == "__main__":
    evaluate_recent_matches(days_back=7)
