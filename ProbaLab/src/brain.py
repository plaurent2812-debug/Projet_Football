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
"""
import json
import re
import time

from src.config import GEMINI_API_KEY, logger, supabase
from src.constants import WEIGHT_AI, WEIGHT_STATS
from google import genai
from google.genai import types
from src.models.scorer_engine import predict_scorers
from src.models.stats_engine import analyze_match, update_elo_from_results
from src.pipeline.inference import predict_meta

import os


def _sanitize_team_name(name: str) -> str:
    """Strip anything that isn't word chars, spaces, hyphens or dots."""
    if not name:
        return "?"
    return re.sub(r'[^\w\s.\-]', '', str(name))[:80]


# ── Client Gemini ─────────────────────────────────────────────
# Initialisation du client Gemini (reportée à l'utilisation pour éviter les crashs d'import)
client = None

def get_gemini_client():
    global client
    if client is None:
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.critical("ERREUR: GEMINI_API_KEY manquante.")
            return None
        client = genai.Client(api_key=api_key)
    return client
MODEL_NAME = "gemini-2.5-flash"


# ═══════════════════════════════════════════════════════════════════
#  EXTRACTION JSON
# ═══════════════════════════════════════════════════════════════════


def extract_json(text: str) -> dict | None:
    """Extract a JSON object from a Gemini response string.

    Attempts three strategies in order:
      1. Direct ``json.loads`` on the whole text.
      2. Regex extraction of a fenced ``json`` code-block.
      3. Regex extraction of the first ``{…}`` block.

    Args:
        text: Raw text returned by the Gemini API.

    Returns:
        Parsed JSON as a dict, or ``None`` if no valid JSON is found.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass
    # Last resort: find all {…} blocks and try parsing each, preferring the first valid one
    for m in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL):
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            continue
    # Ultra-fallback: greedy match (may grab too much but catches nested JSON)
    m = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


# ═══════════════════════════════════════════════════════════════════
#  PROMPT GEMINI ENRICHI
# ═══════════════════════════════════════════════════════════════════


def _format_injuries(side: str, details: list[dict]) -> str:
    """Format a team's injury list as a readable block for the Gemini prompt.

    Args:
        side: Label for the team side (e.g. ``"Domicile"`` or ``"Extérieur"``).
        details: List of injury dicts, each containing keys such as
            ``player_name``, ``position``, ``reason``, ``impact``,
            ``goals``, ``assists``, and ``is_starter``.

    Returns:
        Multi-line string summarising every absence, or a single line
        indicating no known absences when *details* is empty.
    """
    if not details:
        return f"{side} absents : Aucune absence connue"
    lines = [f"{side} absents :"]
    for d in details:
        name = d.get("player_name", "?")
        pos = d.get("position", "?")
        reason = d.get("reason", "?")
        impact = d.get("impact", "?")
        goals = d.get("goals", 0)
        assists = d.get("assists", 0)
        extra = ""
        if goals > 0:
            extra += f", {goals} buts"
        if assists > 0:
            extra += f", {assists} passes dé."
        if d.get("is_starter"):
            extra += ", TITULAIRE"
        lines.append(f"  ⚠️ {name} ({pos}) — {reason} — Impact: {impact.upper()}{extra}")
    return "\n".join(lines)


def get_active_learnings(
    sport: str, limit: int = 5, match_context: str = None
) -> list[str]:
    """Fetch learnings from AI memory, using semantic search when possible.

    If match_context is provided, uses Gemini Embedding 2 to find the
    most relevant learnings via pgvector similarity search. Falls back
    to date-based ordering if semantic search is unavailable.

    Args:
        sport: Sport filter ('football' or 'nhl').
        limit: Max number of learnings to return.
        match_context: Optional text describing the current match for
            semantic matching (e.g. "PSG vs OM, Ligue 1, ELO gap 200").

    Returns:
        List of learning text strings.
    """
    # Strategy 1: Semantic search (if context provided)
    if match_context:
        try:
            from src.embeddings import search_learnings

            results = search_learnings(
                query_text=match_context,
                sport=sport,
                limit=limit,
            )
            if results:
                logger.info(
                    f"[Brain] Semantic learnings: {len(results)} found "
                    f"(top sim: {results[0].get('similarity', '?'):.3f})"
                )
                return [r["learning_text"] for r in results]
        except Exception as e:
            logger.warning(f"[Brain] Semantic search failed, falling back: {e}")

    # Strategy 2: Fallback — date-based ordering
    try:
        response = (
            supabase.table("ai_learnings")
            .select("learning_text")
            .eq("sport", sport)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [r["learning_text"] for r in response.data] if response.data else []
    except Exception as e:
        logger.warning(f"[Brain] Cannot fetch learnings: {e}")
        return []


def build_prompt(fixture: dict, stats: dict, scorers: dict | None) -> tuple[str, str]:
    """Build the system and user prompts enriched with statistical data.

    Assembles a detailed data block from match statistics, context (ELO,
    form, rest days, injuries, H2H, referee, market odds, weather) and
    top-scorer information, then wraps it in a system prompt instructing
    Gemini to return a structured JSON analysis.

    Args:
        fixture: Fixture dict with keys ``home_team``, ``away_team``,
            ``league_id``, and ``date``.
        stats: Output of :func:`analyze_match` containing ``xg_home``,
            ``xg_away``, probabilities, and a ``context`` sub-dict.
        scorers: Output of :func:`predict_scorers` (may be ``None``).

    Returns:
        A ``(system_prompt, user_prompt)`` tuple ready to send to Gemini.
    """
    ctx = stats.get("context", {})

    # Sanitize team names before injecting into prompt
    safe_home = _sanitize_team_name(fixture["home_team"])
    safe_away = _sanitize_team_name(fixture["away_team"])

    # Construire le bloc de contexte factuel
    data_block = f"""
=== DONNÉES STATISTIQUES (calculées par notre modèle) ===

MATCH : {safe_home} (DOM) vs {safe_away} (EXT)
LIGUE : Ligue ID {fixture["league_id"]}  |  DATE : {fixture["date"]}

--- Modèle Poisson ajusté ---
xG Domicile : {stats.get("xg_home", "?")}  |  xG Extérieur : {stats.get("xg_away", "?")}
Poisson →  Dom: {stats.get("proba_home", "?")}%  |  Nul: {stats.get("proba_draw", "?")}%  |  Ext: {stats.get("proba_away", "?")}%
BTTS: {stats.get("proba_btts", "?")}%  |  O2.5: {stats.get("proba_over_2_5", "?")}%  |  Score exact probable: {stats.get("correct_score", "?")}

--- ELO ---
ELO Domicile : {ctx.get("elo_home", "?")}  |  ELO Extérieur : {ctx.get("elo_away", "?")}

--- Forme récente ---
Domicile (à la maison) : {ctx.get("form_home", "?")}
Extérieur (en déplacement) : {ctx.get("form_away", "?")}

--- Repos ---
Domicile : {ctx.get("rest_days_home", "?")} jours de repos ({ctx.get("congestion_home", "?")} matchs/30j)
Extérieur : {ctx.get("rest_days_away", "?")} jours de repos ({ctx.get("congestion_away", "?")} matchs/30j)

--- Enjeu ---
Domicile : {ctx.get("stakes_home", "?")}
Extérieur : {ctx.get("stakes_away", "?")}

--- Blessures ---
{_format_injuries("Domicile", ctx.get("injuries_home_details", []))}
{_format_injuries("Extérieur", ctx.get("injuries_away_details", []))}"""

    # H2H
    h2h = ctx.get("h2h")
    if h2h:
        data_block += f"""

--- Confrontations directes (derniers {h2h.get("total_matches", "?")} matchs) ---
Dom: {h2h.get("team_a_wins", "?")}V  |  Nuls: {h2h.get("draws", "?")}  |  Ext: {h2h.get("team_b_wins", "?")}V"""

    # Arbitre
    ref = ctx.get("referee")
    if ref:
        data_block += f"""

--- Arbitre ---
Cartons jaunes/match : {ref.get("avg_yellows", "?")}  |  Penaltys/match : {ref.get("avg_penalties", "?")}
Tendance penalty : {"GÉNÉREUX" if ref.get("penalty_bias", 1) > 1.3 else "NORMAL" if ref.get("penalty_bias", 1) > 0.8 else "SÉVÈRE"}"""

    # Marché
    market = ctx.get("market")
    if market:
        data_block += f"""

--- Cotes du marché (Bet365) ---
Marché →  Dom: {market.get("market_home", "?")}%  |  Nul: {market.get("market_draw", "?")}%  |  Ext: {market.get("market_away", "?")}%"""

    # Météo
    weather = ctx.get("weather")
    if weather:
        data_block += f"""

--- Météo prévue ---
{weather.get("description", "?")}  |  {weather.get("temp", "?")}°C  |  Vent: {weather.get("wind_speed", "?")} km/h  |  Pluie: {weather.get("rain_mm", 0)} mm"""

    # Buteur probable
    if scorers:
        data_block += "\n\n--- Buteurs probables ---"
        for side, key in [("Domicile", "home_scorers"), ("Extérieur", "away_scorers")]:
            top = scorers.get(key, [])[:3]
            if top:
                data_block += f"\n{side} :"
                for s in top:
                    syn = f" (synergie: {s['synergy']})" if s.get("synergy") else ""
                    pen = " ⚽ Tireur de pen." if s.get("penalty_taker") else ""
                    data_block += f"\n  - {s['name']} ({s['position']}) : {s['goals_90']} buts/90, {s['total_goals']} buts saison{pen}{syn}"

    # Build match context for semantic learning retrieval
    match_context = (
        f"{safe_home} vs {safe_away}, "
        f"Ligue {fixture['league_id']}, "
        f"xG {stats.get('xg_home', '?')}-{stats.get('xg_away', '?')}, "
        f"ELO {ctx.get('elo_home', '?')} vs {ctx.get('elo_away', '?')}, "
        f"Form home={ctx.get('form_home', '?')} away={ctx.get('form_away', '?')}"
    )
    learnings = get_active_learnings("football", match_context=match_context)
    learnings_block = ""
    if learnings:
        learnings_block = "\n\n--- LEÇONS D'AUTO-CORRECTION (MÉMOIRE DU MODÈLE) ---\nPrends particulièrement en compte ces enseignements tirés de tes erreurs passées :\n"
        for i, l in enumerate(learnings, 1):
            learnings_block += f"{i}. {l}\n"

    # Inject similar historical matches for context enrichment
    similar_block = ""
    try:
        from src.embeddings import find_similar_matches

        similar = find_similar_matches(fixture, stats, limit=3)
        if similar:
            similar_block = "\n\n--- MATCHS HISTORIQUES SIMILAIRES ---\n"
            for sm in similar:
                sim_score = sm.get('similarity', 0)
                sm_text = (sm.get('analysis_text') or '')[:150]
                ph = sm.get('proba_home', '?')
                pd_ = sm.get('proba_draw', '?')
                pa = sm.get('proba_away', '?')
                similar_block += (
                    f"  • [{sim_score:.0%} similaire] {ph}-{pd_}-{pa} — {sm_text}...\n"
                )
    except Exception as e:
        logger.debug(f"[Brain] Similar matches unavailable: {e}")

    system_prompt = f"""Tu es un expert en paris sportifs renommé et un analyste tactique de haut niveau.
Tu reçois des données statistiques avancées issues de nos modèles.
Ta mission : extraire des "features" quantitatives (-1.0 à 1.0) évaluant le contexte qualitatif du match.{learnings_block}

CONSIGNES STRICTES :
- Analyse le contexte global (enjeu, blessures, météo, style).
- Quantifie chaque dimension requise entre -1.0 et 1.0. 
  * 1.0 = Extrême positif / Impact total
  * 0.0 = Neutre / Équilibré
  * -1.0 = Extrême négatif / Désastreux
- Rédige une analyse brève (3-5 phrases) justifiant tes scores.
- Évite le jargon de data scientist (ELO, Poisson), utilise des termes de scouting/football.
- ⚠️ LANGUE OBLIGATOIRE : Tous les champs textuels (analysis_text, likely_scorer_reason) DOIVENT être rédigés EN FRANÇAIS. Ne réponds JAMAIS en anglais.

IMPORTANT : Réponds UNIQUEMENT avec un objet JSON valide respectant SCRUPULEUSEMENT cette structure, sans texte avant ni après :
{{
  "motivation_score": float (-1.0 à 1.0),
  "media_pressure": float (-1.0 à 1.0),
  "injury_tactical_impact": float (-1.0 à 1.0, 1.0 avantage Domicile, -1.0 avantage Extérieur),
  "cohesion_score": float (-1.0 à 1.0),
  "style_risk": float (-1.0 à 1.0, 1.0 ultra-offensif attendu, -1.0 bus défensif),
  "analysis_text": "Analyse narrative EN FRANÇAIS de 3-5 phrases expliquant ces notes.",
  "likely_scorer": "Nom du buteur probable ou null",
  "likely_scorer_reason": "Explication EN FRANÇAIS de pourquoi ce joueur, ou null"
}}"""

    user_prompt = f"""{data_block}{similar_block}

En te basant sur ces données statistiques ET ton expertise football, extrais tes évaluations sous forme de features JSON quantifiées entre -1.0 et 1.0. 
Concentre-toi sur l'intangible que les chiffres purs (xG, cotes) montrent mal : la pression mentale, la désorganisation tactique liée aux blessés, ou l'urgence de résultat."""

    return system_prompt, user_prompt


# ═══════════════════════════════════════════════════════════════════
#  APPEL GEMINI
# ═══════════════════════════════════════════════════════════════════


def ask_gemini(system_prompt: str, user_prompt: str) -> str | None:
    """Send an enriched prompt to the Gemini API and return the raw response.

    Args:
        system_prompt: System-level instruction defining Gemini's role.
        user_prompt: User-level message containing the statistical data
            and analysis request.

    Returns:
        The text content of Gemini's reply, or ``None`` on API error.
    """
    gclient = get_gemini_client()
    if not gclient:
        return None

    # TODO: google-genai SDK does not expose a native per-request timeout param.
    # Using a simple retry (1 retry) to handle transient failures.
    for _attempt in range(2):
        try:
            response = gclient.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    max_output_tokens=4000,
                    response_mime_type="application/json",
                ),
            )
            if response and response.text:
                return response.text
            logger.warning("Gemini attempt %d: response has no text", _attempt + 1)
        except Exception as e:
            logger.warning("Gemini attempt %d failed: %s", _attempt + 1, e)
        if _attempt == 0:
            time.sleep(2)
    return None


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

    # Determine match profile
    parts = []

    # xG assessment
    if xg_total >= 3.0:
        parts.append(f"Les xG attendus sont élevés ({xg_home:.2f} - {xg_away:.2f}), annonçant un match ouvert avec de nombreuses occasions.")
    elif xg_total >= 2.2:
        parts.append(f"Les xG attendus ({xg_home:.2f} - {xg_away:.2f}) suggèrent un match équilibré avec un potentiel offensif correct.")
    else:
        parts.append(f"Les xG attendus sont modérés ({xg_home:.2f} - {xg_away:.2f}), ce qui laisse présager un match plutôt fermé.")

    # Favorite assessment
    if p_home >= 55:
        parts.append(f"L'équipe à domicile est nettement favorite ({p_home}%) grâce à sa supériorité statistique.")
    elif p_away >= 55:
        parts.append(f"L'équipe visiteuse est favorite ({p_away}%) malgré son déplacement, un profil intéressant.")
    elif abs(p_home - p_away) < 10:
        parts.append(f"Les équipes se tiennent de très près ({p_home}% - {p_draw}% - {p_away}%), un match incertain.")
    else:
        dom = "domicile" if p_home > p_away else "extérieur"
        parts.append(f"Léger avantage pour l'équipe à {dom}, mais le match reste ouvert.")

    # Goals market
    if p_over25 >= 55:
        parts.append(f"Le marché Over 2.5 buts est bien orienté ({p_over25}%), les deux équipes ayant un profil offensif.")
    elif p_over25 <= 35:
        parts.append(f"Profil défensif pour cette rencontre avec seulement {p_over25}% de chances de voir plus de 2.5 buts.")

    # BTTS
    if p_btts >= 60:
        parts.append(f"Les deux équipes devraient marquer (BTTS à {p_btts}%).")
    elif p_btts <= 35:
        parts.append(f"Il est peu probable que les deux équipes trouvent le chemin des filets (BTTS à {p_btts}%).")

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
#  FUSION STATS + IA
# ═══════════════════════════════════════════════════════════════════


def blend_predictions(stats_result: dict, ai_result: AIFeatures | None) -> dict:
    """Blend structural logic. (Temporarily pure stats in Phase 1).

    Phase 1: Gemini output is now pure features (no probabilities).
    The prediction is currently 100% statistical. AI features are saved
    in the payload for future ML training.

    Args:
        stats_result: Probabilities and metadata from the statistical
            engine (Poisson + ELO model).
        ai_result: Parsed AIFeatures from Gemini's response, or ``None``.

    Returns:
        Merged prediction dict ready for database insertion.
    """
    final = {}

    # Phase 1: 100% stats. If WEIGHT_AI changes, this logic must be updated.
    if WEIGHT_AI > 0:
        logger.warning("WEIGHT_AI=%s but Phase 1 uses 100%% stats — IA blend disabled", WEIGHT_AI)

    # Phase 1: 100% stats until Phase 2 XGBoost is ready
    fields_to_keep = ["proba_home", "proba_draw", "proba_away", "proba_btts", "proba_over_2_5"]
    for field in fields_to_keep:
        final[field] = stats_result.get(field, 50)

    # Normaliser 1X2
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
    
    # Intégrer les AI Features si présentes
    ai_features_dict = {}
    if ai_result:
        if hasattr(ai_result, "model_dump"):
            ai_features_dict = ai_result.model_dump()
        elif isinstance(ai_result, dict):
            ai_features_dict = ai_result
        final["ai_features"] = ai_features_dict
        final["analysis_text"] = ai_features_dict.get("analysis_text") if isinstance(ai_result, dict) else ai_result.analysis_text
        final["likely_scorer"] = ai_features_dict.get("likely_scorer") if isinstance(ai_result, dict) else ai_result.likely_scorer
        final["likely_scorer_reason"] = ai_features_dict.get("likely_scorer_reason") if isinstance(ai_result, dict) else ai_result.likely_scorer_reason
    else:
        final["ai_features"] = {}
        final["analysis_text"] = _build_fallback_analysis(stats_result)

    # Meta-Learner XGBoost désactivé (mars 2026) :
    # Le meta-learner n'utilise que 5 features IA Gemini (motivation, media_pressure, etc.)
    # qui sont trop similaires d'un match à l'autre → probas quasi identiques pour tous les matchs.
    # Les probas du stats_engine (Poisson + ELO + ML XGBoost + calibration) sont plus fiables.
    # À réactiver après réentraînement du meta-learner avec plus de features.
    final["model_version"] = "hybrid_v3"

    # Soft cap already applied in stats_engine.analyze_match() + clamp_probabilities().
    # No duplicate cap needed here (Phase 1 = 100% stats passthrough).

    # Pour l'instant on reprend la recommandation 100% issue des stats (Phase 1)
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
        "proba_over_2_5": final.get("proba_over_2_5") or stats_result.get("proba_over_2_5") or stats_result.get("proba_over_25"),
        "proba_over_35": final.get("proba_over_35"),
        "proba_dc_1x": final.get("proba_dc_1x"),
        "proba_dc_x2": final.get("proba_dc_x2"),
        "correct_score": final.get("correct_score"),
        "proba_correct_score": final.get("proba_correct_score"),
    }

    return final


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════


def get_matches_to_predict(force: bool = False) -> list[dict]:
    """Fetch upcoming fixtures that still need a hybrid-v1 prediction.

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
    # instead of N individual queries (N+1 → 1 query)
    fixture_ids = [fix["id"] for fix in fixtures]
    if not fixture_ids:
        return []

    existing_predictions = (
        supabase.table("predictions")
        .select("fixture_id, model_version")
        .in_("fixture_id", fixture_ids)
        .execute()
        .data or []
    )

    # Build set of fixture_ids that already have a hybrid_v3 prediction
    v3_fixture_ids = {
        p["fixture_id"] for p in existing_predictions
        if p.get("model_version") == "hybrid_v3"
    }

    to_process = [fix for fix in fixtures if fix["id"] not in v3_fixture_ids]
    logger.info(f"{len(to_process)} matchs à analyser (sur {len(fixtures)} NS, {len(v3_fixture_ids)} déjà v3).")
    return to_process


def run_brain() -> None:
    """Run the full hybrid prediction pipeline.

    Orchestrates the end-to-end workflow:
      1. Update ELO ratings from recent results.
      2. Retrieve upcoming fixtures without a ``hybrid_v2`` prediction.
      3. For each fixture: compute statistical probabilities, identify
         likely scorers, query Claude for narrative analysis, blend
         results, and persist the final prediction to Supabase.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  ⚽ FOOTBALL IA — Brain v2 (Hybrid Stats + IA)")
    logger.info("=" * 60)

    # 1. Mettre à jour les ELO
    logger.info("📊 Mise à jour des ratings ELO...")
    try:
        update_elo_from_results()
        logger.info("   ✅ ELO mis à jour.")
    except Exception as e:
        logger.warning("   ⚠️ ELO non mis à jour : %s", e)

    # 2. Charger les matchs (FORCE=True pour être sûr de recalculer si demandé)
    matches = get_matches_to_predict(force=True)
    logger.info("--- %s matchs à analyser ---", len(matches))

    # 3. Charger les noms de ligues
    leagues = supabase.table("leagues").select("api_id, name").execute().data
    league_names = {l["api_id"]: l["name"] for l in leagues}

    def process_match(args):
        i, fix = args

        league_name = league_names.get(fix["league_id"], f"Ligue {fix['league_id']}")
        logger.info(
            f"[{i + 1}/{len(matches)}] {fix['home_team']} vs {fix['away_team']} ({league_name})"
        )

        # ── A. Stats mathématiques ───────────────────────────────
        logger.info("   📐 Calcul des stats...")
        try:
            stats_result = analyze_match(fix)
            logger.info("xG: %s-%s", stats_result["xg_home"], stats_result["xg_away"])
        except Exception as e:
            logger.warning("⚠️ Erreur stats : %s", e)
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
        logger.info("   ⚽ Identification des buteurs...")
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
        except Exception as e:
            logger.warning("⚠️ %s", e)
            scorers = None

        # ── C. Analyse IA ────────────────────────────────────────
        logger.info("   🧠 Analyse Gemini...")
        system_prompt, user_prompt = build_prompt(fix, stats_result, scorers)
        ai_text = ask_gemini(system_prompt, user_prompt)
        ai_result_dict = extract_json(ai_text) if ai_text else None

        ai_result = None
        if ai_result_dict:
            try:
                from src.models.ai_features import AIFeatures
                ai_result = AIFeatures.model_validate(ai_result_dict)
                logger.info("   ✅ Analyse Gemini OK (JSON validé)")
            except Exception as e:
                logger.error("AIFeatures validation failed for %s vs %s: %s",
                             fix.get("home_team", "?"), fix.get("away_team", "?"), e)
        else:
            logger.warning("   ⚠️ JSON introuvable, stats uniquement")

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
                        import json as _json

                        try:
                            final["stats_json"] = _json.loads(final["stats_json"])
                        except Exception:
                            final["stats_json"] = {}
                final["stats_json"]["top_scorers"] = scorers["top_scorers"]

        except Exception as e:
            logger.error("⚠️ Erreur blending : %s", e)
            return

        # ── E. Sauvegarde ────────────────────────────────────────
        try:
            # Mettre la raison dans stats_json car la colonne n'existe pas
            if final.get("likely_scorer_reason"):
                if not final.get("stats_json") or not isinstance(final.get("stats_json"), dict):
                    final["stats_json"] = final.get("stats_json") or {}
                final["stats_json"]["likely_scorer_reason"] = final["likely_scorer_reason"]

            # Ajouter les probas manquantes dans stats_json
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

            # CLV tracking: save market odds at prediction time so CLV can
            # be computed later by comparing to closing line.
            # The odds are already fetched in analyze_match → odds_to_probs.
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
                from src.embeddings import get_embedding, build_match_profile_text

                embed_text = final.get("analysis_text", "")
                # Enrich with match profile for better similarity
                profile = build_match_profile_text(fix, stats_result)
                if embed_text:
                    embed_text = f"{profile} | {embed_text}"
                else:
                    embed_text = profile

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
                # Mise à jour
                prediction_id = existing[0]["id"]
                supabase.table("predictions").update(insert_data).eq("id", prediction_id).execute()
                action_msg = f"🔄 Prédiction mise à jour (ID: {prediction_id})"
            else:
                # Insertion
                supabase.table("predictions").insert(insert_data).execute()
                action_msg = "💾 Nouvelle prédiction créée"

            logger.info(
                f"   {action_msg} → {final['proba_home']}-{final['proba_draw']}-{final['proba_away']} | {final.get('recommended_bet')}"
            )

            # Clean up any stale predictions from other model versions for this fixture
            # This prevents the old meta_v2 / fallback predictions from causing data conflicts
            try:
                stale = (
                    supabase.table("predictions")
                    .select("id, model_version")
                    .eq("fixture_id", fix["id"])
                    .neq("model_version", insert_data["model_version"])
                    .execute()
                    .data or []
                )
                if stale:
                    stale_ids = [s["id"] for s in stale]
                    supabase.table("predictions").delete().in_("id", stale_ids).execute()
                    logger.info(f"   🗑️ Nettoyé {len(stale_ids)} prédiction(s) obsolète(s)")
            except Exception as cleanup_err:
                logger.debug(f"   Cleanup skipped: {cleanup_err}")

        except Exception as e:
            logger.error("   ❌ Erreur sauvegarde : %s", e)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info("⚡ Exécution asynchrone (ThreadPool, 5 workers)")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_match, (i, fix)): fix for i, fix in enumerate(matches)}
        for future in as_completed(futures):
            future.result()  # Catch exceptions safely

    logger.info("=" * 60)
    logger.info("  ✅ Pipeline terminé : %s matchs analysés", len(matches))
    logger.info("=" * 60)

    # ── 4. 🧠 DeepThink Strategic Meta-Analysis ──────────────────
    if matches:
        try:
            _generate_football_deepthink(matches, league_names)
        except Exception as e:
            logger.warning(f"[Football] DeepThink meta-analysis failed: {e}")


def _generate_football_deepthink(matches: list, league_names: dict) -> None:
    """Generate a DeepThink strategic meta-analysis across all football matches."""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    # Cover matches from NOW until tomorrow at 18:00 UTC (19:00 Paris)
    # This captures tonight's matches + tomorrow's daytime matches
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
    fixtures_map = {}
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
        "Max 500 mots total. Sois percutant et précis."
    )

    user_prompt = (
        f"Football — {now.strftime('%d/%m/%Y %Hh%M')} UTC — "
        f"Prochaines 24h — {len(summaries)} matchs à analyser :\n\n"
        + "\n\n".join(summaries)
    )

    try:
        gclient = genai.Client(api_key=GEMINI_API_KEY)

        logger.info("[Football] 🧠 DeepThink: Generating strategic meta-analysis...")
        response = gclient.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=8192,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=4096,
                ),
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

        logger.info(f"[Football] 🧠 DeepThink analysis generated ({len(result)} chars)")

        # Store in football_meta_analysis table (upsert by date)
        try:
            supabase.table("football_meta_analysis").upsert(
                {"date": today, "analysis": result, "n_matches": len(summaries)},
                on_conflict="date",
            ).execute()
            logger.info("[Football] ✅ DeepThink meta-analysis saved")
        except Exception as e1:
            # Fallback: create table might not exist, store in predictions as special row
            logger.warning(f"[Football] football_meta_analysis table error ({e1}), trying fallback...")
            try:
                # Delete old meta if exists
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
                logger.info("[Football] ✅ DeepThink saved (fallback to predictions)")
            except Exception as e2:
                logger.error(f"[Football] Error saving meta-analysis: {e2}")

    except Exception as e:
        logger.warning(f"[Football] DeepThink generation failed: {e}")


if __name__ == "__main__":
    run_brain()
