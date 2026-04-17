from __future__ import annotations

"""
prompts.py — Prompt template construction for Gemini analysis.

Responsibilities:
  - ``_format_injuries``   : format a team's injury list for prompt injection
  - ``get_active_learnings``: fetch AI memory learnings (semantic + date fallback)
  - ``build_prompt``       : assemble the (system_prompt, user_prompt) pair
"""

import re

from src.config import logger, supabase


def _sanitize_team_name(name: str) -> str:
    """Strip anything that isn't word chars, spaces, hyphens or dots."""
    if not name:
        return "?"
    return re.sub(r"[^\w\s.\-]", "", str(name))[:80]


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


def get_active_learnings(sport: str, limit: int = 5, match_context: str | None = None) -> list[str]:
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
        except Exception:
            logger.warning("[Brain] Semantic search failed, falling back", exc_info=True)

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
    except Exception:
        logger.warning("[Brain] Cannot fetch learnings", exc_info=True)
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
                sim_score = sm.get("similarity", 0)
                sm_text = (sm.get("analysis_text") or "")[:150]
                ph = sm.get("proba_home", "?")
                pd_ = sm.get("proba_draw", "?")
                pa = sm.get("proba_away", "?")
                similar_block += f"  • [{sim_score:.0%} similaire] {ph}-{pd_}-{pa} — {sm_text}...\n"
    except Exception:
        logger.debug("[Brain] Similar matches unavailable", exc_info=True)

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
