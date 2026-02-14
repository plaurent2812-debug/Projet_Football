"""
ab_testing.py — A/B testing pour comparer des versions de modèles.

Permet de faire tourner 2 modèles en parallèle sur les mêmes matchs,
d'enregistrer leurs prédictions respectives, puis de comparer
automatiquement les métriques (Brier score, accuracy, ROI).

Usage :
    1. Enregistrer les prédictions de chaque modèle via record_prediction()
    2. Après les résultats, évaluer via evaluate_ab_test()
    3. Obtenir un rapport via get_ab_report()
"""

from __future__ import annotations

from typing import Any

import numpy as np
from config import logger, supabase

TABLE: str = "ab_test_predictions"


# ═══════════════════════════════════════════════════════════════════
#  MIGRATION SQL (à exécuter manuellement dans Supabase)
# ═══════════════════════════════════════════════════════════════════

MIGRATION_SQL: str = """
CREATE TABLE IF NOT EXISTS ab_test_predictions (
    id SERIAL PRIMARY KEY,
    fixture_api_id INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    proba_home NUMERIC(5,2),
    proba_draw NUMERIC(5,2),
    proba_away NUMERIC(5,2),
    proba_btts NUMERIC(5,2),
    proba_over25 NUMERIC(5,2),
    predicted_result TEXT,
    actual_result TEXT,
    brier_score NUMERIC(8,6),
    correct BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fixture_api_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_ab_model ON ab_test_predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_ab_fixture ON ab_test_predictions(fixture_api_id);
"""


# ═══════════════════════════════════════════════════════════════════
#  ENREGISTREMENT DES PRÉDICTIONS
# ═══════════════════════════════════════════════════════════════════


def record_prediction(
    fixture_api_id: int,
    model_version: str,
    proba_home: float,
    proba_draw: float,
    proba_away: float,
    proba_btts: float | None = None,
    proba_over25: float | None = None,
) -> dict[str, Any]:
    """Record a prediction from a specific model version for A/B comparison.

    Args:
        fixture_api_id: Unique fixture identifier.
        model_version: Model version name (e.g. ``"hybrid_v3"``, ``"ensemble_v4"``).
        proba_home: Predicted home win probability (0–100).
        proba_draw: Predicted draw probability (0–100).
        proba_away: Predicted away win probability (0–100).
        proba_btts: Predicted BTTS probability (optional).
        proba_over25: Predicted Over 2.5 probability (optional).

    Returns:
        The inserted/updated row as a dict.
    """
    # Déterminer le résultat prédit
    best = max(proba_home, proba_draw, proba_away)
    if best == proba_home:
        predicted = "H"
    elif best == proba_away:
        predicted = "A"
    else:
        predicted = "D"

    row: dict[str, Any] = {
        "fixture_api_id": fixture_api_id,
        "model_version": model_version,
        "proba_home": round(proba_home, 2),
        "proba_draw": round(proba_draw, 2),
        "proba_away": round(proba_away, 2),
        "proba_btts": round(proba_btts, 2) if proba_btts is not None else None,
        "proba_over25": round(proba_over25, 2) if proba_over25 is not None else None,
        "predicted_result": predicted,
    }

    try:
        result = (
            supabase.table(TABLE).upsert(row, on_conflict="fixture_api_id,model_version").execute()
        )
        logger.info(
            "A/B: %s — fixture %d — pred %s (H:%.0f D:%.0f A:%.0f)",
            model_version,
            fixture_api_id,
            predicted,
            proba_home,
            proba_draw,
            proba_away,
        )
        return result.data[0] if result.data else row
    except Exception as e:
        logger.error("Erreur A/B record: %s", e)
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════
#  ÉVALUATION APRÈS RÉSULTATS
# ═══════════════════════════════════════════════════════════════════


def evaluate_ab_test() -> int:
    """Evaluate all pending A/B predictions against actual results.

    Looks up finished fixtures and computes Brier score + correctness
    for each prediction that hasn't been evaluated yet.

    Returns:
        Number of predictions evaluated.
    """
    try:
        # Prédictions non évaluées
        preds = supabase.table(TABLE).select("*").is_("actual_result", "null").execute().data
        if not preds:
            logger.info("A/B: Aucune prédiction à évaluer")
            return 0

        # Résultats réels
        fixture_ids = list({p["fixture_api_id"] for p in preds})
        fixtures = (
            supabase.table("fixtures")
            .select("api_fixture_id, home_goals, away_goals, status")
            .in_("api_fixture_id", fixture_ids)
            .eq("status", "FT")
            .execute()
            .data
        )

        results_map: dict[int, str] = {}
        for f in fixtures:
            hg = f.get("home_goals")
            ag = f.get("away_goals")
            if hg is not None and ag is not None:
                if hg > ag:
                    results_map[f["api_fixture_id"]] = "H"
                elif hg == ag:
                    results_map[f["api_fixture_id"]] = "D"
                else:
                    results_map[f["api_fixture_id"]] = "A"

        evaluated = 0
        for pred in preds:
            fid = pred["fixture_api_id"]
            if fid not in results_map:
                continue

            actual = results_map[fid]
            correct = pred["predicted_result"] == actual

            # Brier score (pour 1X2)
            p_h = float(pred["proba_home"]) / 100
            p_d = float(pred["proba_draw"]) / 100
            p_a = float(pred["proba_away"]) / 100
            actual_vec = [
                1.0 if actual == "H" else 0.0,
                1.0 if actual == "D" else 0.0,
                1.0 if actual == "A" else 0.0,
            ]
            brier = float(np.mean([(p - a) ** 2 for p, a in zip([p_h, p_d, p_a], actual_vec)]))

            update: dict[str, Any] = {
                "actual_result": actual,
                "correct": correct,
                "brier_score": round(brier, 6),
            }

            supabase.table(TABLE).update(update).eq("id", pred["id"]).execute()
            evaluated += 1

        logger.info("A/B: %d prédictions évaluées", evaluated)
        return evaluated

    except Exception as e:
        logger.error("Erreur A/B evaluate: %s", e)
        return 0


# ═══════════════════════════════════════════════════════════════════
#  RAPPORT COMPARATIF
# ═══════════════════════════════════════════════════════════════════


def get_ab_report() -> dict[str, Any]:
    """Generate a comparative report of all model versions.

    Returns:
        Dictionary keyed by model_version, each containing:
        ``total``, ``correct``, ``accuracy``, ``avg_brier``, and
        ``confidence_interval``.
    """
    try:
        data = supabase.table(TABLE).select("*").not_.is_("actual_result", "null").execute().data
    except Exception as e:
        logger.error("Erreur A/B report: %s", e)
        return {"error": str(e)}

    if not data:
        return {}

    # Grouper par modèle
    models: dict[str, list[dict]] = {}
    for row in data:
        mv = row["model_version"]
        models.setdefault(mv, []).append(row)

    report: dict[str, Any] = {}
    for mv, rows in models.items():
        total = len(rows)
        correct = sum(1 for r in rows if r.get("correct"))
        brier_scores = [float(r["brier_score"]) for r in rows if r.get("brier_score") is not None]

        accuracy = round(correct / total * 100, 1) if total > 0 else 0
        avg_brier = round(float(np.mean(brier_scores)), 4) if brier_scores else None

        # Intervalle de confiance (Wilson score interval approximation)
        ci_low = ci_high = None
        if total >= 10:
            p = correct / total
            z = 1.96  # 95% CI
            denom = 1 + z**2 / total
            center = (p + z**2 / (2 * total)) / denom
            spread = z * (p * (1 - p) / total + z**2 / (4 * total**2)) ** 0.5 / denom
            ci_low = round(max(0, center - spread) * 100, 1)
            ci_high = round(min(1, center + spread) * 100, 1)

        report[mv] = {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "avg_brier": avg_brier,
            "ci_95": (ci_low, ci_high) if ci_low is not None else None,
        }

    # Déterminer le meilleur modèle
    if len(report) >= 2:
        best_model = min(
            report.keys(),
            key=lambda k: report[k]["avg_brier"] if report[k]["avg_brier"] is not None else 999,
        )
        report["_best_model"] = best_model
        report["_comparison"] = (
            f"Meilleur modèle: {best_model} "
            f"(Brier: {report[best_model]['avg_brier']}, "
            f"Accuracy: {report[best_model]['accuracy']}%)"
        )

    return report
