import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.brain import ask_gemini, extract_json
from src.config import logger, supabase


def process_daily_reflection(sport="football"):
    """
    Analyzes yesterday's failed high-confidence predictions
    to extract actionable learnings using Gemini.
    """
    logger.info(f"[Reflection] Démarrage de l'auto-analyse pour le {sport}...")

    # We fetch from prediction_results where recommended_bet_ok is False and confidence >= 7
    try:
        response = (
            supabase.table("prediction_results")
            .select("*, fixtures(date, home_team, away_team)")
            .eq("recommended_bet_ok", False)
            .gte("pred_confidence", 7)
            .order("fixture_id", desc=True)
            .limit(10)
            .execute()
        )
    except Exception as e:
        logger.error(f"[Reflection] Erreur lors de la récupération des données : {e}")
        return

    failed_preds = response.data
    if not failed_preds:
        logger.info("[Reflection] Aucun échec critique récent à analyser. Modèle parfait ! ✅")
        return

    # Prevent analyzing the same match twice
    try:
        existing = supabase.table("ai_learnings").select("source_match_id").execute()
        existing_ids = {str(r["source_match_id"]) for r in existing.data}
    except Exception:
        existing_ids = set()

    new_learnings = 0
    for row in failed_preds:
        fixture = row.get("fixtures", {})
        if not fixture:
            continue

        if str(row["fixture_id"]) in existing_ids:
            continue

        match_name = f"{fixture.get('home_team')} vs {fixture.get('away_team')}"
        logger.info(
            f"[Reflection] Analyse de l'échec sur {match_name} (Confiance: {row['pred_confidence']}/10)"
        )

        system_prompt = """Tu es l'ingénieur en Machine Learning principal d'un modèle de prédiction sportive.
Ton but est d'analyser une de nos pires prédictions récentes (forte confiance mais pari raté).
Tu vas lire les probabilités prédictes, le score réel, et l'analyse post-match.
Extrais-en UNE leçon globale et réutilisable (un 'learning') pour ne plus faire la même erreur à l'avenir.
La leçon doit être une règle directe, claire et actionnable (1 phrase max).

Tu dois répondre UNIQUEMENT en JSON valide avec ce format :
{
  "learning_text": "Ne pas sous-estimer la résilience défensive à l'extérieur des équipes mal classées.",
  "context_tags": ["exterieur", "defense", "football"]
}"""

        user_prompt = f"""
MATCH : {match_name}
SCORE RÉEL : {row["actual_home_goals"]} - {row["actual_away_goals"]}

NOS PRÉDICTIONS :
- Proba Victoire Domicile: {row["pred_home"]}%
- Proba Nul: {row["pred_draw"]}%
- Proba Victoire Extérieur: {row["pred_away"]}%
- Pari Recommandé: {row["pred_recommended"]}
- Confiance du modèle: {row["pred_confidence"]}/10

RÉSUMÉ POST-MATCH (pourquoi on s'est trompé) :
{row["post_analysis"]}

Génère ton analyse et ta leçon (learning_text) au format JSON.
"""

        ai_response = ask_gemini(system_prompt, user_prompt)
        ai_json = extract_json(ai_response)

        if ai_json and "learning_text" in ai_json:
            learning_text = ai_json["learning_text"]
            tags = ai_json.get("context_tags", ["football"])
            if sport not in tags:
                tags.append(sport)

            # Generate semantic embedding for future retrieval
            from src.embeddings import get_embedding

            embedding = get_embedding(learning_text)

            try:
                insert_data = {
                    "sport": sport,
                    "context_tags": tags,
                    "learning_text": learning_text,
                    "source_match_id": row["fixture_id"],
                    "confidence": row["pred_confidence"],
                }
                if embedding:
                    insert_data["embedding"] = embedding

                supabase.table("ai_learnings").insert(insert_data).execute()
                new_learnings += 1
                emb_status = "✅" if embedding else "⚠️ sans embedding"
                logger.info(f"   💡 Leçon apprise ({emb_status}) : {learning_text}")
            except Exception as e:
                logger.error(f"   ❌ Erreur d'insertion DB: {e}")
        else:
            logger.warning("   ⚠️ Gemini n'a pas retourné de JSON valide pour ce match.")

    logger.info(
        f"[Reflection] Terminé ! {new_learnings} nouvelles règles ajoutées à la mémoire du modèle."
    )


if __name__ == "__main__":
    process_daily_reflection("football")
