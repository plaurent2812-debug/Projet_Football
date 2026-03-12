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

import base64
import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger("telegram_parser")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """Tu es un assistant expert en paris sportifs.
On te donne une capture d'écran d'un bookmaker (Winamax, Unibet, etc.).
Extrait les informations du pari et réponds UNIQUEMENT en JSON valide.

Règles importantes :
- Ne jamais inclure "MyMatch:" dans le champ market. Si tu vois "MyMatch:", ignore ce préfixe.
- Si c'est un combiné (plusieurs sélections), liste chaque sélection dans le tableau "selections".
- Pour un pari simple, "selections" contient une seule entrée.

Format JSON attendu :
{
  "match_label": "Équipe A vs Équipe B",
  "market": "description du pari sans préfixe MyMatch (ex: Double chance X2 + BTTS)",
  "selections": [
    {"bet": "description sélection 1", "match": "Équipe A vs Équipe B"},
    {"bet": "description sélection 2", "match": "Équipe C vs Équipe D"}
  ],
  "odds": 1.86,
  "date": "YYYY-MM-DD ou null",
  "sport": "football ou nhl",
  "player_name": null
}

Pour un pari simple, "selections" = [{"bet": "<le pari>", "match": "<le match>"}].
Réponds UNIQUEMENT avec le JSON, sans markdown, sans explication.
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

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        # Encode image en base64 pour Gemini
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        user_text = "Analyse ce screenshot de pari Winamax."
        if caption:
            user_text += f"\n\nNote de l'expert : {caption}"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
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

        raw_text = ""
        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                # Skip 'thought' parts from thinking models (2.5-flash)
                if getattr(part, "thought", False):
                    continue
                if hasattr(part, "text") and part.text:
                    raw_text += part.text

        # Fallback: try response.text property
        if not raw_text:
            try:
                raw_text = response.text or ""
            except Exception:
                raw_text = ""

        if not raw_text:
            logger.error("Gemini returned empty text. Candidates: %s", response.candidates if response else "None")
            return {"error": "Gemini a retourné une réponse vide. Réessaie avec un screenshot plus net."}

        # Clean JSON (remove markdown fences if any)
        raw_text = raw_text.strip()
        logger.info("Gemini raw response: %s", raw_text[:300])

        parsed = _extract_json_robust(raw_text)
        if parsed is None:
            raise json.JSONDecodeError(f"Aucun JSON valide trouvé dans la réponse", raw_text, 0)

        # Ensure date fallback to today
        if not parsed.get("date"):
            parsed["date"] = datetime.utcnow().strftime("%Y-%m-%d")

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
