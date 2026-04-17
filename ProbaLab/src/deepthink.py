from __future__ import annotations

"""
deepthink.py — DeepThink strategic meta-analysis for football.

Responsibilities:
  - ``generate_football_deepthink`` : query Gemini for a cross-match strategic
    analysis of all upcoming fixtures and upsert the result to
    ``football_meta_analysis`` table.
"""

from datetime import datetime, timedelta, timezone

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY, logger, supabase


def generate_football_deepthink(matches: list[dict], league_names: dict[int, str]) -> None:
    """Generate a DeepThink strategic meta-analysis across all football matches.

    Fetches recent predictions, builds per-match summaries, and calls Gemini
    (gemini-2.5-flash, temperature 0.4) to produce a strategic narrative
    identifying the top 3 value-betting spots.  The result is upserted into
    the ``football_meta_analysis`` table keyed on today's date.

    Args:
        matches: List of fixture dicts processed by the current brain run.
        league_names: Mapping of ``league_id`` → ``league_name`` strings.
    """
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    # Cover matches from NOW until tomorrow at 18:00 UTC (19:00 Paris)
    cutoff = (now + timedelta(days=1)).replace(hour=18, minute=0, second=0)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch predictions for meta-analysis context
    try:
        preds = (
            supabase.table("predictions")
            .select(
                "fixture_id, proba_home, proba_draw, proba_away, "
                "proba_btts, proba_over_2_5, proba_over_15, "
                "recommended_bet, confidence_score, analysis_text"
            )
            .order("confidence_score", desc=True)
            .limit(60)
            .execute()
            .data or []
        )
    except Exception:
        preds = []

    if not preds:
        logger.info("[Football] No predictions available for DeepThink.")
        return

    # Enrich with fixture info — cover next 24h window
    fixture_ids = [p["fixture_id"] for p in preds if p.get("fixture_id")]
    fixtures_map: dict = {}
    if fixture_ids:
        try:
            fx_data = (
                supabase.table("fixtures")
                .select("id, home_team, away_team, league_id, date, status")
                .in_("id", fixture_ids)
                .eq("status", "NS")
                .gte("date", now_str)
                .lt("date", cutoff_str)
                .execute()
                .data or []
            )
            fixtures_map = {f["id"]: f for f in fx_data}
        except Exception:
            pass

    if not fixtures_map:
        logger.info("[Football] No NS fixtures for DeepThink today.")
        return

    # Build match summaries
    summaries = []
    for p in preds:
        fix = fixtures_map.get(p.get("fixture_id"))
        if not fix:
            continue
        league = league_names.get(fix.get("league_id"), "")
        summaries.append(
            f"### {fix['home_team']} vs {fix['away_team']} ({league})\n"
            f"  1X2 : {p.get('proba_home', 0)}% - {p.get('proba_draw', 0)}% - {p.get('proba_away', 0)}%\n"
            f"  BTTS : {p.get('proba_btts', 50)}% | Over 2.5 : {p.get('proba_over_2_5', 50)}%\n"
            f"  Over 1.5 : {p.get('proba_over_15', 70)}%\n"
            f"  Pari recommandé : {p.get('recommended_bet', 'N/A')} "
            f"(confiance : {p.get('confidence_score', 0)}/10)\n"
            f"  Analyse IA : {(p.get('analysis_text') or '')[:200]}"
        )

    if not summaries:
        return

    system_prompt = (
        "Tu es un expert analytique football de niveau élite. Tu t'adresses à des parieurs avertis.\n\n"
        "**MISSION** : Analyse en profondeur TOUS les matchs de la journée. "
        "Identifie les 3 MEILLEURS SPOTS (opportunités à haute value) en croisant les données.\n\n"
        "**Données fournies** : Probabilités 1X2, xG attendus, BTTS, Over/Under, "
        "paris recommandés par le modèle avec score de confiance, et l'analyse IA de chaque match.\n\n"
        "**MARCHÉS AUTORISÉS (uniquement ceux calculés par notre modèle)** :\n"
        "- Victoire Domicile / Victoire Extérieur / Match Nul\n"
        "- Double Chance 1X / Double Chance X2\n"
        "- BTTS Oui\n"
        "- Plus de 1.5 buts / Plus de 2.5 buts / Plus de 3.5 buts\n"
        "- 1X + Plus de 1.5 buts / X2 + Plus de 1.5 buts\n"
        "⚠️ NE JAMAIS recommander de handicap (-1.5, -2.5) ou de marché non listé ci-dessus.\n"
        "⚠️ Ton MARCHÉ CIBLE doit être COHÉRENT avec le pari recommandé par le modèle pour ce match.\n\n"
        "**RAISONNEMENT ATTENDU** : Pour chaque spot identifié, tu dois :\n"
        "1. Expliquer POURQUOI c'est un bon spot (croisement de plusieurs facteurs)\n"
        "2. Identifier le MARCHÉ cible (parmi la liste ci-dessus uniquement)\n"
        "3. Donner un niveau de CONFIANCE (⭐ à ⭐⭐⭐)\n"
        "4. Mentionner les RISQUES potentiels\n\n"
        "**FORMAT** : Rédige en français, style direct de parieur expert. "
        "Commence par un titre '⚽ Analyse Stratégique' puis les 3 spots. "
        "Termine par un bref résumé de la journée (1-2 phrases).\n"
        "Max 500 mots total. Sois percutant et précis.\n"
        "⚠️ Ne dis JAMAIS 'mon modèle', 'mon analyse', 'je'. Utilise 'notre analyse', 'nos experts', 'le modèle'."
    )

    user_prompt = (
        f"Football — {now.strftime('%d/%m/%Y %Hh%M')} UTC — "
        f"Prochaines 24h — {len(summaries)} matchs à analyser :\n\n"
        + "\n\n".join(summaries)
    )

    try:
        gclient = genai.Client(api_key=GEMINI_API_KEY)

        logger.info("[Football] DeepThink: Generating strategic meta-analysis...")
        response = gclient.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )

        result = ""
        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    result += part.text
        if not result:
            result = getattr(response, "text", "") or ""

        if not result or len(result) < 100:
            logger.warning("[Football] DeepThink returned empty/short response")
            return

        logger.info(f"[Football] DeepThink analysis generated ({len(result)} chars)")

        # Store in football_meta_analysis table (upsert by date)
        try:
            supabase.table("football_meta_analysis").upsert(
                {"date": today, "analysis": result, "n_matches": len(summaries)},
                on_conflict="date",
            ).execute()
            logger.info("[Football] DeepThink meta-analysis saved")
        except Exception:
            # Fallback: table might not exist — store in predictions as special row
            logger.warning(
                "[Football] football_meta_analysis table error, trying fallback...",
                exc_info=True,
            )
            try:
                supabase.table("predictions").delete().eq(
                    "fixture_id", "00000000-0000-0000-0000-000000000000"
                ).execute()
            except Exception:
                pass
            try:
                supabase.table("predictions").insert({
                    "fixture_id": "00000000-0000-0000-0000-000000000000",
                    "model_version": "deepthink_meta",
                    "analysis_text": result,
                    "confidence_score": 10,
                    "recommended_bet": f"DeepThink {today}",
                }).execute()
                logger.info("[Football] DeepThink saved (fallback to predictions)")
            except Exception:
                logger.exception("[Football] Error saving meta-analysis")

    except Exception:
        logger.warning("[Football] DeepThink generation failed", exc_info=True)
