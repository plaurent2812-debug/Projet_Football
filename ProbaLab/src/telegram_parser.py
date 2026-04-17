"""
telegram_parser.py — Analyse un screenshot Winamax avec Gemini Vision.

Extrait:
  - player_name   : Nom du joueur (si paris joueur)
  - market        : Type de pari (ex: "Over 0.5 Points")
  - odds          : Cote décimale (ex: 2.45)
  - match_label   : "Équipe A vs Équipe B"
  - sport         : "nhl" | "football"
  - date          : YYYY-MM-DD (date du match détectée ou aujourd'hui)
  - expert_note   : Texte libre capturé (ex: caption envoyé avec l'image)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone

logger = logging.getLogger("telegram_parser")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """Tu es un assistant expert en paris sportifs.
On te donne une capture d'écran d'une appli de paris (Winamax, Unibet, Betclic, MyMatch, etc.).

TON OBJECTIF : extraire UNIQUEMENT les informations utiles du pari.
IGNORE TOUT LE RESTE : boutons, navigation, logos, pubs, headers, icônes, etc.

CE QUE TU DOIS EXTRAIRE :
1. Les noms des équipes ou joueurs impliqués
2. Le type de pari (victoire, over/under, points joueur, BTTS, double chance, etc.)
3. La cote totale (le nombre décimal, ex: 3.55)
4. Le sport (football, nhl, basketball, tennis...)
5. La date du match si visible

RÈGLES :
- IGNORE les préfixes "MyMatch:", "MYMATCH", "Mon Pari", etc.
- Si c'est un combiné avec plusieurs sélections sur plusieurs matchs, liste CHAQUE sélection
- Une sélection = un pari sur un match spécifique
- Si tu vois "Points du joueur : 1 ou plus", le market est "Over 0.5 Points"
- Si tu vois "Buts du joueur : 1 ou plus", le market est "Buteur"
- Détecte le sport automatiquement (NHL si tu vois des équipes NHL, football sinon)
- Si la cote est au format virgule (3,55), convertis en point (3.55)

FORMAT JSON — réponds UNIQUEMENT avec ce JSON, rien d'autre :
{
  "match_label": "Équipe A vs Équipe B",
  "market": "description claire du pari",
  "selections": [
    {"bet": "Sean Durzi Over 0.5 Points", "match": "Utah Mammoth vs Chicago Blackhawks"},
    {"bet": "Cale Makar Over 0.5 Points", "match": "Seattle Kraken vs Colorado Avalanche"}
  ],
  "odds": 3.55,
  "date": "YYYY-MM-DD ou null",
  "sport": "football ou nhl",
  "player_name": null
}

Pour un pari simple : "selections" = [{"bet": "<le pari>", "match": "<le match>"}].
NE METS PAS de markdown, pas de ```json, pas d'explication. JUSTE le JSON brut.
"""


def _extract_json_robust(text: str) -> dict | None:
    """Extrait un objet JSON depuis une réponse Gemini (3 stratégies).

    1. json.loads direct sur le texte complet.
    2. Extraction depuis un bloc ```json ... ```.
    3. Extraction du premier bloc { ... } trouvé.
    """
    if not text:
        return None
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


def parse_winamax_screenshot(image_bytes: bytes, caption: str = "") -> dict:
    """
    Analyse une image de pari Winamax et retourne les champs extraits.

    Args:
        image_bytes: Image en bytes (JPEG/PNG)
        caption: Texte optionnel envoyé avec l'image par l'utilisateur

    Returns:
        dict avec les clés: player_name, market, odds, match_label, sport, date, expert_note
        ou {"error": "..."} en cas d'échec
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY non définie")
        return {"error": "GEMINI_API_KEY manquante"}

    raw_text = ""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        user_text = "Analyse ce screenshot de pari sportif. Extrait les matchs, paris et cotes."
        if caption:
            user_text += f"\n\nNote de l'expert : {caption}"

        # gemini-2.5-flash-lite: non-thinking, fast, returns clean JSON
        # gemini-2.5-flash: fallback (thinking model, response needs JSON extraction)
        models_to_try = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type="image/jpeg",
                                ),
                                types.Part.from_text(text=user_text),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        max_output_tokens=2048,
                    ),
                )

                # Extract text from response
                raw_text = ""
                try:
                    raw_text = response.text or ""
                except Exception:
                    if response and response.candidates:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, "text") and part.text:
                                raw_text += part.text

                if raw_text and raw_text.strip():
                    logger.info("Model %s returned %d chars", model_name, len(raw_text))
                    break
                else:
                    logger.warning("Model %s returned empty response, trying next", model_name)

            except Exception as e:
                logger.warning("Model %s failed: %s, trying next", model_name, e)
                continue

        if not raw_text or not raw_text.strip():
            logger.error("All models returned empty text")
            return {
                "error": "Gemini a retourné une réponse vide. Réessaie avec un screenshot plus net."
            }

        raw_text = raw_text.strip()
        logger.info("Gemini raw response: %s", raw_text[:300])

        parsed = _extract_json_robust(raw_text)
        if parsed is None:
            raise json.JSONDecodeError("Aucun JSON valide trouvé dans la réponse", raw_text, 0)

        # Ensure date fallback to today
        if not parsed.get("date"):
            parsed["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Add expert note from caption
        parsed["expert_note"] = caption or ""

        logger.info(
            "Screenshot parsed: %s %s @%s",
            parsed.get("player_name") or parsed.get("market"),
            parsed.get("match_label", ""),
            parsed.get("odds"),
        )
        return parsed

    except json.JSONDecodeError as e:
        logger.error("JSON parse error: %s | raw: %s", e, raw_text[:500] if raw_text else "(empty)")
        return {"error": f"Impossible de parser la réponse Gemini: {e}"}
    except Exception as e:
        logger.error("Gemini Vision error: %s", e, exc_info=True)
        return {"error": str(e)}


def format_confirmation_message(pick: dict) -> str:
    """Formatte le message de confirmation Telegram."""
    sport_emoji = "🏒" if pick.get("sport") == "nhl" else "⚽"
    lines = ["🎯 *Pick détecté :*", ""]

    if pick.get("player_name"):
        lines.append(f"👤 {pick['player_name']}")

    # Combiné : liste chaque sélection
    selections = pick.get("selections") or []
    if len(selections) > 1:
        lines.append(f"{sport_emoji} *Combiné ({len(selections)} sélections) :*")
        for sel in selections:
            bet = sel.get("bet", "")
            match = sel.get("match", "")
            lines.append(f"  • {bet}" + (f" ({match})" if match else ""))
    else:
        if pick.get("market"):
            lines.append(f"{sport_emoji} {pick['market']}")
        if pick.get("match_label"):
            lines.append(f"🏟 {pick['match_label']}")

    if pick.get("odds"):
        lines.append(f"💰 @{pick['odds']}")
    if pick.get("date"):
        lines.append(f"📅 {pick['date']}")
    if pick.get("expert_note"):
        lines.append(f"💬 _{pick['expert_note']}_")

    lines.extend(["", "Confirmer ? 👍 ou ❌"])
    return "\n".join(lines)
