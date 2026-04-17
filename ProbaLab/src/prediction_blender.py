from __future__ import annotations

"""
prediction_blender.py — Prediction blending logic (stats + AI meta-learner).

Responsibilities:
  - ``_build_fallback_analysis`` : generate a French narrative from raw stats
                                   when Gemini is unavailable
  - ``_try_meta_blend``          : Phase 2 XGBoost meta-learner blend (gated)
  - ``blend_predictions``        : public entry point that merges stats + AI
"""

from src.config import logger
from src.constants import META_LEARNER_ENABLED, WEIGHT_AI, WEIGHT_STATS

# ═══════════════════════════════════════════════════════════════════
#  FALLBACK ANALYSIS (when Gemini is unavailable)
# ═══════════════════════════════════════════════════════════════════


def _build_fallback_analysis(stats_result: dict) -> str:
    """Build a meaningful French analysis from available stats when Gemini fails."""
    xg_home = stats_result.get("xg_home", 1.3)
    xg_away = stats_result.get("xg_away", 1.1)
    xg_total = xg_home + xg_away
    p_home = stats_result.get("proba_home", 33)
    p_draw = stats_result.get("proba_draw", 33)
    p_away = stats_result.get("proba_away", 33)
    p_btts = stats_result.get("proba_btts", 50)
    p_over25 = stats_result.get("proba_over_2_5", 45)

    parts = []

    # xG assessment
    if xg_total >= 3.0:
        parts.append(
            f"Les xG attendus sont élevés ({xg_home:.2f} - {xg_away:.2f}), annonçant un match ouvert avec de nombreuses occasions."
        )
    elif xg_total >= 2.2:
        parts.append(
            f"Les xG attendus ({xg_home:.2f} - {xg_away:.2f}) suggèrent un match équilibré avec un potentiel offensif correct."
        )
    else:
        parts.append(
            f"Les xG attendus sont modérés ({xg_home:.2f} - {xg_away:.2f}), ce qui laisse présager un match plutôt fermé."
        )

    # Favorite assessment
    if p_home >= 55:
        parts.append(
            f"L'équipe à domicile est nettement favorite ({p_home}%) grâce à sa supériorité statistique."
        )
    elif p_away >= 55:
        parts.append(
            f"L'équipe visiteuse est favorite ({p_away}%) malgré son déplacement, un profil intéressant."
        )
    elif abs(p_home - p_away) < 10:
        parts.append(
            f"Les équipes se tiennent de très près ({p_home}% - {p_draw}% - {p_away}%), un match incertain."
        )
    else:
        dom = "domicile" if p_home > p_away else "extérieur"
        parts.append(f"Léger avantage pour l'équipe à {dom}, mais le match reste ouvert.")

    # Goals market
    if p_over25 >= 55:
        parts.append(
            f"Le marché Over 2.5 buts est bien orienté ({p_over25}%), les deux équipes ayant un profil offensif."
        )
    elif p_over25 <= 35:
        parts.append(
            f"Profil défensif pour cette rencontre avec seulement {p_over25}% de chances de voir plus de 2.5 buts."
        )

    # BTTS
    if p_btts >= 60:
        parts.append(f"Les deux équipes devraient marquer (BTTS à {p_btts}%).")
    elif p_btts <= 35:
        parts.append(
            f"Il est peu probable que les deux équipes trouvent le chemin des filets (BTTS à {p_btts}%)."
        )

    # Context from form/rest if available
    ctx = stats_result.get("context", {})
    form_home = ctx.get("form_home")
    form_away = ctx.get("form_away")
    if form_home and isinstance(form_home, list):
        wins_h = form_home.count("W")
        if wins_h >= 4:
            parts.append("L'équipe à domicile est en grande forme récente.")
        elif wins_h <= 1:
            parts.append("L'équipe à domicile traverse une période difficile.")
    if form_away and isinstance(form_away, list):
        wins_a = form_away.count("W")
        if wins_a >= 4:
            parts.append("Les visiteurs affichent une belle dynamique.")
        elif wins_a <= 1:
            parts.append("Les visiteurs manquent de confiance en déplacement.")

    return " ".join(parts[:4])  # Keep it concise: max 4 sentences


# ═══════════════════════════════════════════════════════════════════
#  META-LEARNER BLEND (Phase 2 — gated)
# ═══════════════════════════════════════════════════════════════════


def _try_meta_blend(
    stats_result: dict,
    ai_features_dict: dict,
    final: dict,
) -> bool:
    """Attempt Phase 2 meta-learner blend and mutate *final* in-place.

    The meta-learner is gated by two conditions:
      1. The model files must exist on disk (loaded via ``predict_meta``).
      2. The ``WEIGHT_AI`` constant must be > 0 (feature flag in constants.py).

    When both conditions are met, probabilities are blended as:
      ``final_proba = WEIGHT_STATS * stats_proba + WEIGHT_AI * meta_proba``

    NOTE: The current meta-learner only uses 5 Gemini AI features
    (motivation, media_pressure, etc.) which tend to be very similar
    across matches, producing near-identical probabilities regardless of
    opponent.  Keep ``WEIGHT_AI = 0`` in constants.py until the model is
    retrained with a richer feature set.

    Args:
        stats_result: Raw stats-engine probabilities (0-100 int scale).
        ai_features_dict: AI feature dict extracted from Gemini response.
        final: Output dict already seeded with stats probabilities.
            Modified in-place if meta-learner succeeds.

    Returns:
        ``True`` if the meta-learner was applied, ``False`` otherwise.
    """
    if not META_LEARNER_ENABLED or WEIGHT_AI <= 0:
        return False

    try:
        from src.pipeline.inference import predict_meta

        meta_preds = predict_meta(stats_result, ai_features_dict)
        if not meta_preds:
            logger.info("Phase 2 meta-learner unavailable — no model files found, using pure stats")
            return False

        # 1X2 blend
        if (
            meta_preds.get("proba_home_meta") is not None
            and meta_preds.get("proba_draw_meta") is not None
            and meta_preds.get("proba_away_meta") is not None
        ):
            blended_home = round(
                WEIGHT_STATS * final["proba_home"] + WEIGHT_AI * meta_preds["proba_home_meta"]
            )
            blended_draw = round(
                WEIGHT_STATS * final["proba_draw"] + WEIGHT_AI * meta_preds["proba_draw_meta"]
            )
            blended_away = 100 - blended_home - blended_draw
            final["proba_home"] = blended_home
            final["proba_draw"] = blended_draw
            final["proba_away"] = blended_away

        # BTTS blend
        if meta_preds.get("proba_btts_meta") is not None and final.get("proba_btts") is not None:
            final["proba_btts"] = round(
                WEIGHT_STATS * final["proba_btts"] + WEIGHT_AI * meta_preds["proba_btts_meta"]
            )

        # Over 1.5 blend
        if (
            meta_preds.get("proba_over_15_meta") is not None
            and final.get("proba_over_15") is not None
        ):
            final["proba_over_15"] = round(
                WEIGHT_STATS * final["proba_over_15"] + WEIGHT_AI * meta_preds["proba_over_15_meta"]
            )

        # Over 2.5 blend
        if (
            meta_preds.get("proba_over_25_meta") is not None
            and final.get("proba_over_2_5") is not None
        ):
            final["proba_over_2_5"] = round(
                WEIGHT_STATS * final["proba_over_2_5"]
                + WEIGHT_AI * meta_preds["proba_over_25_meta"]
            )

        logger.info(
            "Phase 2 meta-learner active — blended with WEIGHT_STATS=%.2f / WEIGHT_AI=%.2f",
            WEIGHT_STATS,
            WEIGHT_AI,
        )
        return True

    except Exception:
        logger.warning("Phase 2 meta-learner failed, falling back to pure stats", exc_info=True)
        return False


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════


def blend_predictions(stats_result: dict, ai_result: object | None) -> dict:
    """Blend stats and optional meta-learner predictions.

    Phase 1 (default): 100% stats from stats_engine.  AI features from
    Gemini are saved in the payload for future ML training.

    Phase 2 (activated when WEIGHT_AI > 0 AND meta-model files present):
    Blended predictions using the XGBoost meta-learner:
      ``final_proba = WEIGHT_STATS * stats_proba + WEIGHT_AI * meta_proba``

    Args:
        stats_result: Probabilities and metadata from the statistical
            engine (Poisson + ELO + ML XGBoost).
        ai_result: Parsed AIFeatures from Gemini's response, or ``None``.
            Accepts either a Pydantic model instance or a plain dict.

    Returns:
        Merged prediction dict ready for database insertion.
    """
    final: dict = {}

    # ── Base probabilities from stats engine ─────────────────────
    fields_to_keep = ["proba_home", "proba_draw", "proba_away", "proba_btts", "proba_over_2_5"]
    for field in fields_to_keep:
        final[field] = stats_result.get(field, 50)

    # Normalise 1X2
    total = final["proba_home"] + final["proba_draw"] + final["proba_away"]
    if total > 0 and total != 100:
        final["proba_home"] = round(final["proba_home"] / total * 100)
        final["proba_draw"] = round(final["proba_draw"] / total * 100)
        final["proba_away"] = 100 - final["proba_home"] - final["proba_draw"]

    # Champs annexes
    final["proba_over_05"] = stats_result.get("proba_over_05")
    final["proba_over_15"] = stats_result.get("proba_over_15")
    final["proba_over_35"] = stats_result.get("proba_over_35")
    final["proba_penalty"] = stats_result.get("proba_penalty")
    final["proba_dc_1x"] = final["proba_home"] + final["proba_draw"]
    final["proba_dc_x2"] = final["proba_draw"] + final["proba_away"]
    final["proba_dc_12"] = final["proba_home"] + final["proba_away"]
    final["correct_score"] = stats_result.get("correct_score")
    final["proba_correct_score"] = stats_result.get("proba_correct_score")

    # ── AI Features extraction ────────────────────────────────────
    ai_features_dict: dict = {}
    if ai_result:
        if hasattr(ai_result, "model_dump"):
            ai_features_dict = ai_result.model_dump()
        elif isinstance(ai_result, dict):
            ai_features_dict = ai_result
        final["ai_features"] = ai_features_dict
        final["analysis_text"] = (
            ai_features_dict.get("analysis_text")
            if isinstance(ai_result, dict)
            else ai_result.analysis_text  # type: ignore[union-attr]
        )
        final["likely_scorer"] = (
            ai_features_dict.get("likely_scorer")
            if isinstance(ai_result, dict)
            else ai_result.likely_scorer  # type: ignore[union-attr]
        )
        final["likely_scorer_reason"] = (
            ai_features_dict.get("likely_scorer_reason")
            if isinstance(ai_result, dict)
            else ai_result.likely_scorer_reason  # type: ignore[union-attr]
        )
    else:
        final["ai_features"] = {}
        final["analysis_text"] = _build_fallback_analysis(stats_result)

    # ── Phase 2 meta-learner (gated by META_LEARNER_ENABLED=True) ─
    meta_active = _try_meta_blend(stats_result, ai_features_dict, final)

    if meta_active:
        final["model_version"] = "hybrid_v4_meta"
        # Recompute Double Chance after potential meta blend
        final["proba_dc_1x"] = final["proba_home"] + final["proba_draw"]
        final["proba_dc_x2"] = final["proba_draw"] + final["proba_away"]
        final["proba_dc_12"] = final["proba_home"] + final["proba_away"]
    else:
        logger.debug("Phase 2 meta-learner inactive — using pure stats (WEIGHT_AI=%.2f)", WEIGHT_AI)
        final["model_version"] = "hybrid_v3"

    final["recommended_bet"] = stats_result.get("recommended_bet", "")
    final["confidence_score"] = stats_result.get("confidence_score", 5)

    # Stats JSON pour audit + frontend Top 5 Marchés
    final["stats_json"] = {
        "xg_home": stats_result.get("xg_home"),
        "xg_away": stats_result.get("xg_away"),
        "context": stats_result.get("context"),
        # Probas marchés (utilisées par Dashboard TopMarketsCard)
        "proba_home": final.get("proba_home"),
        "proba_draw": final.get("proba_draw"),
        "proba_away": final.get("proba_away"),
        "proba_btts": final.get("proba_btts"),
        "proba_over_05": final.get("proba_over_05"),
        "proba_over_15": final.get("proba_over_15"),
        "proba_over_2_5": final.get("proba_over_2_5")
        or stats_result.get("proba_over_2_5")
        or stats_result.get("proba_over_25"),
        "proba_over_35": final.get("proba_over_35"),
        "proba_dc_1x": final.get("proba_dc_1x"),
        "proba_dc_x2": final.get("proba_dc_x2"),
        "correct_score": final.get("correct_score"),
        "proba_correct_score": final.get("proba_correct_score"),
        "meta_active": meta_active,
    }

    return final
