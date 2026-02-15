from __future__ import annotations

"""
brain.py v2 — Pipeline hybride : Stats mathématiques + Narration IA Claude.

Workflow :
  1. stats_engine.py calcule les probabilités (Poisson + ELO + facteurs)
  2. scorer_engine.py identifie le buteur probable + synergies
  3. Les données sont injectées dans le prompt Claude
  4. Claude génère l'analyse narrative en s'appuyant sur les vrais chiffres
  5. Résultat final = 70% stats math + 30% ajustement IA
"""
import json
import re
import time

from anthropic import Anthropic
from config import ANTHROPIC_KEY, logger, supabase
from constants import WEIGHT_AI, WEIGHT_STATS
from models.scorer_engine import predict_scorers
from models.stats_engine import analyze_match, update_elo_from_results

# ── Client Anthropic ─────────────────────────────────────────────
if not ANTHROPIC_KEY:
    logger.critical("ERREUR: ANTHROPIC_API_KEY manquante.")
    exit()

client = Anthropic(api_key=ANTHROPIC_KEY)
MODEL_NAME = "claude-sonnet-4-20250514"


# ═══════════════════════════════════════════════════════════════════
#  EXTRACTION JSON
# ═══════════════════════════════════════════════════════════════════


def extract_json(text: str) -> dict | None:
    """Extract a JSON object from a Claude response string.

    Attempts three strategies in order:
      1. Direct ``json.loads`` on the whole text.
      2. Regex extraction of a fenced ``json`` code-block.
      3. Regex extraction of the first ``{…}`` block.

    Args:
        text: Raw text returned by the Claude API.

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
    m = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


# ═══════════════════════════════════════════════════════════════════
#  PROMPT CLAUDE ENRICHI
# ═══════════════════════════════════════════════════════════════════


def _format_injuries(side: str, details: list[dict]) -> str:
    """Format a team's injury list as a readable block for the Claude prompt.

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


def build_prompt(fixture: dict, stats: dict, scorers: dict | None) -> tuple[str, str]:
    """Build the system and user prompts enriched with statistical data.

    Assembles a detailed data block from match statistics, context (ELO,
    form, rest days, injuries, H2H, referee, market odds, weather) and
    top-scorer information, then wraps it in a system prompt instructing
    Claude to return a structured JSON analysis.

    Args:
        fixture: Fixture dict with keys ``home_team``, ``away_team``,
            ``league_id``, and ``date``.
        stats: Output of :func:`analyze_match` containing ``xg_home``,
            ``xg_away``, probabilities, and a ``context`` sub-dict.
        scorers: Output of :func:`predict_scorers` (may be ``None``).

    Returns:
        A ``(system_prompt, user_prompt)`` tuple ready to send to Claude.
    """
    ctx = stats.get("context", {})

    # Construire le bloc de contexte factuel
    data_block = f"""
=== DONNÉES STATISTIQUES (calculées par notre modèle) ===

MATCH : {fixture["home_team"]} (DOM) vs {fixture["away_team"]} (EXT)
LIGUE : Ligue ID {fixture["league_id"]}  |  DATE : {fixture["date"]}

--- Modèle Poisson ajusté ---
xG Domicile : {stats["xg_home"]}  |  xG Extérieur : {stats["xg_away"]}
Poisson →  Dom: {stats["proba_home"]}%  |  Nul: {stats["proba_draw"]}%  |  Ext: {stats["proba_away"]}%
BTTS: {stats["proba_btts"]}%  |  O2.5: {stats["proba_over_25"]}%  |  Score exact probable: {stats["correct_score"]}

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

    system_prompt = """Tu es un analyste senior chez un fonds de paris sportifs quantitatif.
Tu reçois des données statistiques calculées par notre modèle mathématique (Poisson, ELO, forme, etc.).
Ta mission : générer une analyse narrative et ajuster si nécessaire les probabilités en fonction de facteurs qualitatifs que les modèles ne capturent pas (derby, enjeu psychologique, conditions spéciales).

IMPORTANT : Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après.
{
  "proba_home": int (0-100),
  "proba_draw": int (0-100),
  "proba_away": int (0-100),
  "proba_btts": int (0-100),
  "proba_over_2_5": int (0-100),
  "analysis_text": "Analyse narrative de 3-5 phrases expliquant les facteurs clés et pourquoi tu ajustes (ou non) les probas du modèle.",
  "recommended_bet": "Le pari à plus forte value (ex: 'BTTS Oui', 'Victoire Domicile', 'Plus de 2.5 buts')",
  "confidence_score": int (1-10),
  "likely_scorer": "Nom du buteur le plus probable",
  "likely_scorer_reason": "Explication en 1-2 phrases de pourquoi ce joueur est le plus susceptible de marquer (forme récente, historique face à cet adversaire, position, stats de tirs/xG)",
  "adjustment_reason": "Si tu ajustes les probas du modèle, explique pourquoi en 1 phrase."
}"""

    user_prompt = f"""{data_block}

En te basant sur ces données statistiques ET ton expertise football, génère ton analyse.
Si les stats du modèle te semblent correctes, garde les probabilités proches.
Si tu identifies un facteur qualitatif non capturé (derby, pression, historique particulier), ajuste en expliquant pourquoi.
Reste réaliste et cohérent avec les données."""

    return system_prompt, user_prompt


# ═══════════════════════════════════════════════════════════════════
#  APPEL CLAUDE
# ═══════════════════════════════════════════════════════════════════


def ask_claude(system_prompt: str, user_prompt: str) -> str | None:
    """Send an enriched prompt to the Claude API and return the raw response.

    Args:
        system_prompt: System-level instruction defining Claude's role.
        user_prompt: User-level message containing the statistical data
            and analysis request.

    Returns:
        The text content of Claude's reply, or ``None`` on API error.
    """
    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1500,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text  # type: ignore[union-attr]
    except Exception as e:
        logger.error("Erreur Anthropic : %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════
#  FUSION STATS + IA
# ═══════════════════════════════════════════════════════════════════


def blend_predictions(stats_result: dict, ai_result: dict | None) -> dict:
    """Blend statistical and AI probability predictions with dynamic weights.

    B2: Instead of fixed 70/30 weights, dynamically adjusts based on:
    - AI confidence score (higher → more AI weight)
    - Convergence between models (agreement → more total confidence)
    - Stats spread (dominant outcome → trust stats more)

    Args:
        stats_result: Probabilities and metadata from the statistical
            engine (Poisson + ELO model).
        ai_result: Parsed JSON from Claude's response, or ``None`` when
            the AI call failed or returned invalid JSON.

    Returns:
        Merged prediction dict ready for database insertion.
    """
    fields_to_blend = ["proba_home", "proba_draw", "proba_away", "proba_btts", "proba_over_25"]

    # B2: Dynamic weight calculation
    w_stats = WEIGHT_STATS  # base: 0.70
    w_ai = WEIGHT_AI        # base: 0.30

    if ai_result:
        ai_conf = ai_result.get("confidence_score", 5)
        stats_spread = max(
            stats_result.get("proba_home", 33),
            stats_result.get("proba_draw", 33),
            stats_result.get("proba_away", 33),
        ) - min(
            stats_result.get("proba_home", 33),
            stats_result.get("proba_draw", 33),
            stats_result.get("proba_away", 33),
        )

        # High AI confidence → shift weight toward AI (max +10%)
        if ai_conf >= 8:
            w_ai = min(0.40, WEIGHT_AI + 0.10)
        elif ai_conf >= 6:
            w_ai = min(0.35, WEIGHT_AI + 0.05)
        elif ai_conf <= 3:
            w_ai = max(0.15, WEIGHT_AI - 0.15)

        # Dominant stats spread → trust stats more
        if stats_spread > 25:
            w_ai = max(0.20, w_ai - 0.05)

        w_stats = 1.0 - w_ai

    final = {}
    for field in fields_to_blend:
        s_val = stats_result.get(field, 50)
        a_val = ai_result.get(field, s_val) if ai_result else s_val
        final[field] = round(s_val * w_stats + a_val * w_ai)

    # Normaliser 1X2
    total = final["proba_home"] + final["proba_draw"] + final["proba_away"]
    if total > 0 and total != 100:
        final["proba_home"] = round(final["proba_home"] / total * 100)
        final["proba_draw"] = round(final["proba_draw"] / total * 100)
        final["proba_away"] = 100 - final["proba_home"] - final["proba_draw"]

    # Champs non blendés (directement du modèle stats ou IA)
    final["proba_over_05"] = stats_result.get("proba_over_05")
    final["proba_over_15"] = stats_result.get("proba_over_15")
    final["proba_over_35"] = stats_result.get("proba_over_35")
    final["proba_penalty"] = stats_result.get("proba_penalty")
    final["proba_dc_1x"] = final["proba_home"] + final["proba_draw"]
    final["proba_dc_x2"] = final["proba_draw"] + final["proba_away"]
    final["proba_dc_12"] = final["proba_home"] + final["proba_away"]
    final["correct_score"] = stats_result.get("correct_score")
    final["proba_correct_score"] = stats_result.get("proba_correct_score")
    final["model_version"] = "hybrid_v3"

    # Kelly / value bet fields from stats engine
    final["kelly_edge"] = stats_result.get("kelly_edge")
    final["kelly_fraction"] = stats_result.get("kelly_fraction")
    final["value_bet"] = stats_result.get("value_bet", False)

    # Blend weights used (for audit)
    final["blend_weights"] = {"stats": round(w_stats, 2), "ai": round(w_ai, 2)}

    # Analyse et recommandation de l'IA
    if ai_result:
        final["analysis_text"] = ai_result.get("analysis_text", "")
        final["recommended_bet"] = ai_result.get(
            "recommended_bet", stats_result.get("recommended_bet", "")
        )
        final["confidence_score"] = ai_result.get(
            "confidence_score", stats_result.get("confidence_score", 5)
        )
        final["likely_scorer"] = ai_result.get("likely_scorer")
        final["likely_scorer_reason"] = ai_result.get("likely_scorer_reason")
    else:
        final["analysis_text"] = (
            f"Analyse stats uniquement. xG: {stats_result.get('xg_home')}-{stats_result.get('xg_away')}."
        )
        final["recommended_bet"] = stats_result.get("recommended_bet", "")
        final["confidence_score"] = stats_result.get("confidence_score", 5)

    # Stats JSON pour audit
    final["stats_json"] = {
        "xg_home": stats_result.get("xg_home"),
        "xg_away": stats_result.get("xg_away"),
        "context": stats_result.get("context"),
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

    to_process = []
    for fix in fixtures:
        existing = (
            supabase.table("predictions")
            .select("id, model_version")
            .eq("fixture_id", fix["id"])
            .execute()
            .data
        )

        # Re-prédire si l'ancienne version n'est pas hybrid_v3
        has_v3 = any(p.get("model_version") == "hybrid_v3" for p in existing)
        if not has_v3:
            to_process.append(fix)

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

    for i, fix in enumerate(matches):
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
                "proba_over_25": 50,
                "proba_over_15": 75,
                "proba_over_35": 30,
                "proba_dc_1x": 70,
                "proba_dc_x2": 60,
                "proba_dc_12": 70,
                "correct_score": "1-1",
                "proba_correct_score": 12,
                "xg_home": 1.3,
                "xg_away": 1.1,
                "model_version": "fallback",
                "recommended_bet": "BTTS Oui",
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
        logger.info("   🧠 Analyse Claude...")
        system_prompt, user_prompt = build_prompt(fix, stats_result, scorers)
        ai_text = ask_claude(system_prompt, user_prompt)
        ai_result = extract_json(ai_text) if ai_text else None

        if ai_result:
            logger.info("   ✅ Analyse Claude OK")
        else:
            logger.warning("   ⚠️ JSON invalide, stats uniquement")

        # ── D. Fusion ────────────────────────────────────────────
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

        # ── E. Sauvegarde ────────────────────────────────────────
        try:
            # Supprimer l'ancienne prédiction si elle existe
            supabase.table("predictions").delete().eq("fixture_id", fix["id"]).execute()

            insert_data = {
                "fixture_id": fix["id"],
                "analysis_text": final.get("analysis_text", ""),
                "proba_home": final["proba_home"],
                "proba_draw": final["proba_draw"],
                "proba_away": final["proba_away"],
                "proba_btts": final["proba_btts"],
                "proba_over_2_5": final.get("proba_over_25", final.get("proba_over_2_5")),
                "proba_over_05": final.get("proba_over_05"),
                "proba_over_15": final.get("proba_over_15"),
                "proba_over_35": final.get("proba_over_35"),
                "proba_penalty": final.get("proba_penalty"),
                "proba_dc_1x": final.get("proba_dc_1x"),
                "proba_dc_x2": final.get("proba_dc_x2"),
                "proba_dc_12": final.get("proba_dc_12"),
                "correct_score": final.get("correct_score"),
                "proba_correct_score": final.get("proba_correct_score"),
                "recommended_bet": final.get("recommended_bet", ""),
                "confidence_score": final.get("confidence_score", 5),
                "likely_scorer": final.get("likely_scorer"),
                "likely_scorer_proba": final.get("likely_scorer_proba"),
                "likely_scorer_reason": final.get("likely_scorer_reason"),
                "model_version": final.get("model_version", "hybrid_v3"),
                "stats_json": final.get("stats_json"),
            }

            supabase.table("predictions").insert(insert_data).execute()
            logger.info(
                f"   💾 Prédiction enregistrée → {final['proba_home']}-{final['proba_draw']}-{final['proba_away']} | {final.get('recommended_bet')}"
            )

        except Exception as e:
            logger.error("   ❌ Erreur sauvegarde : %s", e)

        time.sleep(1)

    logger.info("=" * 60)
    logger.info("  ✅ Pipeline terminé : %s matchs analysés", len(matches))
    logger.info("=" * 60)


if __name__ == "__main__":
    run_brain()
