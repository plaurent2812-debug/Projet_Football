import logging
import time
from datetime import datetime, timezone

from src.brain import ask_gemini, build_prompt, extract_json
from src.config import supabase
from src.models.ai_features import AIFeatures
from src.models.stats_engine import analyze_match

logger = logging.getLogger(__name__)

def run_historical_backfill(limit=500):
    logger.info(f"🚀 Début du backfill complet V2 (Stats + IA) pour {limit} matchs...")

    # Récupérer les ID déjà dans la table predictions
    logger.info("📡 Vérification des prédictions existantes pour ignorer les doublons...")
    pred_res = supabase.table("predictions").select("fixture_id").execute()
    already_predicted = {str(r.get("fixture_id")) for r in (pred_res.data or [])}

    # 1. Trouver les fixtures terminées
    logger.info("📡 Récupération des matchs de football terminés dans la table 'fixtures'...")
    res = supabase.table("fixtures")\
        .select("*")\
        .in_("status", ["FT", "AET", "PEN"])\
        .order("date", desc=True)\
        .limit(2000)\
        .execute()

    fixtures = res.data or []
    if not fixtures:
        logger.warning("Aucune fixture trouvée.")
        return

    to_backfill = []
    for f in fixtures:
        fix_id = str(f["api_fixture_id"])
        if fix_id not in already_predicted:
            to_backfill.append(f)
            if len(to_backfill) >= limit:
                break

    logger.info(f"🔍 {len(to_backfill)} matchs de football vont être processés et insérés dans predictions.")

    if not to_backfill:
        return

    # 2. Boucle sur les fixtures à prédire
    success_count = 0
    error_count = 0

    for i, fixture in enumerate(to_backfill):
        fix_id = fixture["api_fixture_id"]
        logger.info(f"[{i+1}/{len(to_backfill)}] Génération V2 complète pour Fixture {fix_id}...")

        try:
            # Reconstruire les stats (avec le nouveau modèle VORP/xG)
            stats_result = analyze_match(fixture)

            # IA
            system_prompt, user_prompt = build_prompt(fixture, stats_result, None)
            ai_text = ask_gemini(system_prompt, user_prompt)
            ai_dict = extract_json(ai_text) if ai_text else None

            if not ai_dict:
                logger.warning(f"  ⚠️ Échec de l'extraction JSON IA pour Fixture {fix_id}. On skip.")
                logger.warning(f"  📝 Texte brut Gemini : {ai_text}")
                error_count += 1
                continue

            # Valider avec Pydantic
            ai_features_obj = AIFeatures.model_validate(ai_dict)
            final_features = ai_features_obj.model_dump()

            # Preparation de l'insertion
            insert_data = {
                "fixture_id": fix_id,
                "proba_home": stats_result.get("proba_home", 0),
                "proba_draw": stats_result.get("proba_draw", 0),
                "proba_away": stats_result.get("proba_away", 0),
                "proba_btts": stats_result.get("proba_btts", 0),
                "proba_over_15": stats_result.get("proba_over_15", 0),
                "proba_over_2_5": stats_result.get("proba_over_25", 0),
                "ai_features": final_features,
                "analysis_text": final_features.get("analysis_text", ""),
                "model_version": "v2",
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            # Insertion Supabase
            supabase.table("predictions").insert(insert_data).execute()

            success_count += 1
            logger.info("  ✅ Succès. Prédiction complète insérée.")

        except Exception as e:
            logger.error(f"  ❌ Erreur lors du backfill Fixture {fix_id}: {e}")
            error_count += 1

        # Pause API Rate limit (Gemini Flash gratuit a un quota par minute, 4 sec de pause = max 15 requêtes/min)
        time.sleep(4)

    logger.info(f"🏁 Backfill terminé ! {success_count} insérés, {error_count} erreurs.")

if __name__ == "__main__":
    # Commençons le vrai backfill (long process in background)
    run_historical_backfill(limit=500)
