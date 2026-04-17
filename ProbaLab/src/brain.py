from __future__ import annotations

"""
brain.py v2 — Pipeline hybride : Stats mathématiques + Narration IA Gemini.

Workflow :
  1. stats_engine.py calcule les probabilités (Poisson + ELO + ML + calibration)
  2. scorer_engine.py identifie le buteur probable + synergies
  3. Les données sont injectées dans le prompt Gemini
  4. Gemini génère l'analyse narrative en s'appuyant sur les vrais chiffres
  5. Résultat final = 100% stats (Phase 1 — le meta-learner IA est désactivé)
     Les AI features sont sauvegardées pour le futur Phase 2 XGBoost.

This module acts as the thin orchestrator.  Implementation details live in:
  - src.ai_service        : Gemini client, extract_json, ask_gemini
  - src.prompts           : build_prompt, get_active_learnings, _format_injuries
  - src.prediction_blender: blend_predictions
  - src.deepthink         : generate_football_deepthink
"""

import json as _json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.ai_service import ask_gemini, extract_json, get_gemini_client  # noqa: F401 — re-exported
from src.config import logger, supabase
from src.deepthink import generate_football_deepthink
from src.models.scorer_engine import predict_scorers
from src.models.stats_engine import analyze_match, update_elo_from_results
from src.prediction_blender import blend_predictions  # noqa: F401 — re-exported
from src.prompts import (
    _format_injuries,  # noqa: F401 — re-exported (used by test_brain_integration)
    build_prompt,  # noqa: F401 — re-exported
    get_active_learnings,  # noqa: F401 — re-exported
)

# ── Optional metrics (no-op when running outside the API process) ─
_METRICS_ENABLED: bool
try:
    from api.metrics import pipeline_duration  # noqa: I001
    from api.metrics import pipeline_runs  # noqa: I001
    from api.metrics import predictions_generated  # noqa: I001

    _METRICS_ENABLED = True
except ImportError:
    _METRICS_ENABLED = False


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════


def get_matches_to_predict(force: bool = False) -> list[dict]:
    """Fetch upcoming fixtures that still need a hybrid-v3 prediction.

    Queries Supabase for all fixtures with status ``"NS"`` (Not Started).
    If force is True, returns all NS fixtures.
    Otherwise, filters out those that already have a ``hybrid_v3`` prediction.

    Returns:
        List of fixture dicts to process.
    """
    logger.info("Récupération des matchs à venir...")
    fixtures = supabase.table("fixtures").select("*").eq("status", "NS").execute().data

    if force:
        logger.info(f"Mode FORCE activé : {len(fixtures)} matchs à re-analyser.")
        return fixtures

    # Batch query: fetch all existing predictions for these fixtures at once
    fixture_ids = [fix["id"] for fix in fixtures]
    if not fixture_ids:
        return []

    existing_predictions = (
        supabase.table("predictions")
        .select("fixture_id, model_version")
        .in_("fixture_id", fixture_ids)
        .execute()
        .data
        or []
    )

    # Build set of fixture_ids that already have a hybrid_v3 prediction
    v3_fixture_ids = {
        p["fixture_id"] for p in existing_predictions if p.get("model_version") == "hybrid_v3"
    }

    to_process = [fix for fix in fixtures if fix["id"] not in v3_fixture_ids]
    logger.info(
        f"{len(to_process)} matchs à analyser (sur {len(fixtures)} NS, {len(v3_fixture_ids)} déjà v3)."
    )
    return to_process


def run_brain() -> None:
    """Run the full hybrid prediction pipeline.

    Orchestrates the end-to-end workflow:
      1. Update ELO ratings from recent results.
      2. Retrieve upcoming fixtures without a ``hybrid_v3`` prediction.
      3. For each fixture: compute statistical probabilities, identify
         likely scorers, query Gemini for narrative analysis, blend
         results, and persist the final prediction to Supabase.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  FOOTBALL IA — Brain v2 (Hybrid Stats + IA)")
    logger.info("=" * 60)

    _pipeline_start = time.time()

    # 1. Mettre à jour les ELO
    logger.info("Mise à jour des ratings ELO...")
    try:
        update_elo_from_results()
        logger.info("   ELO mis à jour.")
    except Exception:
        logger.warning("ELO update failed", exc_info=True)

    # 2. Charger les matchs (FORCE=True pour recalculer si demandé)
    matches = get_matches_to_predict(force=True)
    logger.info("--- %s matchs à analyser ---", len(matches))

    # 3. Charger les noms de ligues
    leagues = supabase.table("leagues").select("api_id, name").execute().data
    league_names = {l["api_id"]: l["name"] for l in leagues}

    def process_match(args: tuple[int, dict]) -> None:
        i, fix = args

        league_name = league_names.get(fix["league_id"], f"Ligue {fix['league_id']}")
        logger.info(
            f"[{i + 1}/{len(matches)}] {fix['home_team']} vs {fix['away_team']} ({league_name})"
        )

        # ── A. Stats mathématiques ───────────────────────────────
        logger.info("   Calcul des stats...")
        try:
            stats_result = analyze_match(fix)
            logger.info("xG: %s-%s", stats_result["xg_home"], stats_result["xg_away"])
        except Exception:
            logger.warning(
                "Stats computation failed for %s vs %s",
                fix.get("home_team", "?"),
                fix.get("away_team", "?"),
                exc_info=True,
            )
            stats_result = {
                "proba_home": 40,
                "proba_draw": 30,
                "proba_away": 30,
                "proba_btts": 50,
                "proba_over_2_5": 50,
                "proba_over_15": 75,
                "proba_over_35": 30,
                "proba_dc_1x": 70,
                "proba_dc_x2": 60,
                "proba_dc_12": 70,
                "xg_home": 1.3,
                "xg_away": 1.1,
                "model_version": "fallback",
                "recommended_bet": "Plus de 1.5 buts",
                "confidence_score": 3,
                "context": {},
            }

        # ── B. Buteur probable ───────────────────────────────────
        logger.info("   Identification des buteurs...")
        try:
            scorers = predict_scorers(
                fix["home_team"],
                fix["away_team"],
                stats_result.get("xg_home", 1.3),
                stats_result.get("xg_away", 1.1),
            )
            if scorers and scorers.get("likely_scorer"):
                logger.info("%s (%s%%)", scorers["likely_scorer"], scorers["likely_scorer_proba"])
            else:
                logger.info("pas de données suffisantes")
                scorers = None
        except Exception:
            logger.warning(
                "Scorers prediction failed for %s vs %s",
                fix.get("home_team", "?"),
                fix.get("away_team", "?"),
                exc_info=True,
            )
            scorers = None

        # ── C. Analyse IA ────────────────────────────────────────
        logger.info("   Analyse Gemini...")
        system_prompt, user_prompt = build_prompt(fix, stats_result, scorers)
        ai_text = ask_gemini(system_prompt, user_prompt)
        ai_result_dict = extract_json(ai_text) if ai_text else None

        ai_result = None
        if ai_result_dict:
            try:
                from src.models.ai_features import AIFeatures

                ai_result = AIFeatures.model_validate(ai_result_dict)
                logger.info("   Analyse Gemini OK (JSON validé)")
            except Exception:
                logger.exception(
                    "AIFeatures validation failed for %s vs %s",
                    fix.get("home_team", "?"),
                    fix.get("away_team", "?"),
                )
        else:
            logger.warning("   JSON introuvable, stats uniquement")

        # Sleep to avoid [Errno 35] Resource temporarily unavailable (API limits)
        time.sleep(2.0)

        # ── D. Fusion ────────────────────────────────────────────
        try:
            final = blend_predictions(stats_result, ai_result)

            # Ajouter buteurs si dispo (top 3 avec analyse)
            if scorers and scorers.get("likely_scorer"):
                if not final.get("likely_scorer"):
                    final["likely_scorer"] = scorers["likely_scorer"]
                final["likely_scorer_proba"] = scorers.get("likely_scorer_proba", 0)

            if scorers and scorers.get("top_scorers"):
                # Stocker les top 3 buteurs dans stats_json
                if not final.get("stats_json") or not isinstance(final.get("stats_json"), dict):
                    final["stats_json"] = final.get("stats_json") or {}
                    if isinstance(final["stats_json"], str):
                        try:
                            final["stats_json"] = _json.loads(final["stats_json"])
                        except Exception:
                            final["stats_json"] = {}
                final["stats_json"]["top_scorers"] = scorers["top_scorers"]

        except Exception:
            logger.exception(
                "Prediction blending failed for %s vs %s",
                fix.get("home_team", "?"),
                fix.get("away_team", "?"),
            )
            return

        # ── E. Sauvegarde ────────────────────────────────────────
        try:
            # Mettre la raison dans stats_json (la colonne n'existe pas)
            if final.get("likely_scorer_reason"):
                if not final.get("stats_json") or not isinstance(final.get("stats_json"), dict):
                    final["stats_json"] = final.get("stats_json") or {}
                final["stats_json"]["likely_scorer_reason"] = final["likely_scorer_reason"]

            if not final.get("stats_json") or not isinstance(final.get("stats_json"), dict):
                final["stats_json"] = final.get("stats_json") or {}

            # Injecter les probas supplémentaires dans stats_json (audit + fallback)
            extra_probas = [
                "proba_dc_1x",
                "proba_dc_x2",
                "proba_dc_12",
                "proba_penalty",
                "proba_correct_score",
            ]
            for key in extra_probas:
                if final.get(key) is not None:
                    final["stats_json"][key] = final[key]

            # CLV tracking: save market odds at prediction time
            ctx = final.get("context") or {}
            market_snapshot = ctx.get("market")
            if market_snapshot:
                final["stats_json"]["odds_at_prediction"] = {
                    "market_home": market_snapshot.get("market_home"),
                    "market_draw": market_snapshot.get("market_draw"),
                    "market_away": market_snapshot.get("market_away"),
                    "overround": market_snapshot.get("overround"),
                }

            insert_data = {
                "fixture_id": fix["id"],
                "analysis_text": final.get("analysis_text", ""),
                "proba_home": final["proba_home"],
                "proba_draw": final["proba_draw"],
                "proba_away": final["proba_away"],
                "proba_btts": final["proba_btts"],
                "proba_over_2_5": final.get("proba_over_2_5"),
                "proba_over_05": final.get("proba_over_05"),
                "proba_over_15": final.get("proba_over_15"),
                "proba_over_35": final.get("proba_over_35"),
                "correct_score": final.get("correct_score"),
                "recommended_bet": final.get("recommended_bet", ""),
                "confidence_score": final.get("confidence_score", 5),
                "likely_scorer": final.get("likely_scorer"),
                "likely_scorer_proba": final.get("likely_scorer_proba"),
                "model_version": final.get("model_version", "hybrid_v3"),
                "stats_json": final.get("stats_json"),
                "ai_features": final.get("ai_features", {}),
            }

            # Generate semantic embedding for prediction search
            try:
                from src.embeddings import build_match_profile_text, get_embedding

                embed_text = final.get("analysis_text", "")
                profile = build_match_profile_text(fix, stats_result)
                embed_text = f"{profile} | {embed_text}" if embed_text else profile

                pred_embedding = get_embedding(embed_text)
                if pred_embedding:
                    insert_data["embedding"] = pred_embedding
            except Exception as emb_err:
                logger.debug(f"Embedding skipped: {emb_err}")

            # Vérifier si une prédiction existe déjà pour ce match et ce modèle
            existing = (
                supabase.table("predictions")
                .select("id")
                .eq("fixture_id", fix["id"])
                .eq("model_version", insert_data["model_version"])
                .execute()
                .data
            )

            if existing:
                prediction_id = existing[0]["id"]
                supabase.table("predictions").update(insert_data).eq("id", prediction_id).execute()
                action_msg = f"Prédiction mise à jour (ID: {prediction_id})"
            else:
                supabase.table("predictions").insert(insert_data).execute()
                action_msg = "Nouvelle prédiction créée"

            logger.info(
                f"   {action_msg} → {final['proba_home']}-{final['proba_draw']}-{final['proba_away']} | {final.get('recommended_bet')}"
            )

            if _METRICS_ENABLED:
                predictions_generated.labels(sport="football", league=league_name).inc()

            # Clean up stale predictions from other model versions
            try:
                stale = (
                    supabase.table("predictions")
                    .select("id, model_version")
                    .eq("fixture_id", fix["id"])
                    .neq("model_version", insert_data["model_version"])
                    .execute()
                    .data
                    or []
                )
                if stale:
                    stale_ids = [s["id"] for s in stale]
                    supabase.table("predictions").delete().in_("id", stale_ids).execute()
                    logger.info(f"   Nettoyé {len(stale_ids)} prédiction(s) obsolète(s)")
            except Exception as cleanup_err:
                logger.debug(f"   Cleanup skipped: {cleanup_err}")

        except Exception:
            logger.exception(
                "Prediction save failed for %s vs %s",
                fix.get("home_team", "?"),
                fix.get("away_team", "?"),
            )

    logger.info("Exécution asynchrone (ThreadPool, 5 workers)")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_match, (i, fix)): fix for i, fix in enumerate(matches)}
        for future in as_completed(futures):
            future.result()  # surface exceptions

    logger.info("=" * 60)
    logger.info("  Pipeline terminé : %s matchs analysés", len(matches))
    logger.info("=" * 60)

    # ── 4. DeepThink Strategic Meta-Analysis ─────────────────────
    if matches:
        try:
            generate_football_deepthink(matches, league_names)
        except Exception:
            logger.warning("[Football] DeepThink meta-analysis failed", exc_info=True)

    if _METRICS_ENABLED:
        _elapsed = time.time() - _pipeline_start
        pipeline_runs.labels(mode="football", status="success").inc()
        pipeline_duration.labels(mode="football").observe(_elapsed)


if __name__ == "__main__":
    run_brain()
