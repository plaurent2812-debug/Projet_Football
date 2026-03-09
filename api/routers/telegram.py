"""
api/routers/telegram.py — Webhook Telegram pour les paris de l'expert.

Flow:
1. Expert envoie un screenshot Winamax dans Telegram
2. Webhook reçoit l'image → Gemini Vision OCR l'analyse
3. Bot répond avec un résumé formaté et demande confirmation (👍 / ❌)
4. Si 👍 → le pick est inséré en DB (expert_picks)
5. Si ❌ → pick annulé
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

import requests
from fastapi import APIRouter, BackgroundTasks, Request, Response

from src.config import supabase
from src.telegram_parser import format_confirmation_message, parse_winamax_screenshot

logger = logging.getLogger("telegram_router")

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_EXPERT_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# In-memory store: chat_id → pending pick dict
# (simple dict, ok for single-instance Railway deployment)
_pending_picks: dict[int, dict] = {}


def _send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    """Envoie un message Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non défini")
        return
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
    except Exception as e:
        logger.error("Telegram sendMessage error: %s", e)


def _download_telegram_file(file_id: str) -> bytes | None:
    """Télécharge un fichier depuis Telegram."""
    try:
        # Get file path
        resp = requests.get(
            f"{TELEGRAM_API}/getFile",
            params={"file_id": file_id},
            timeout=10,
        )
        file_path = resp.json()["result"]["file_path"]
        # Download file
        file_resp = requests.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
            timeout=30,
        )
        return file_resp.content
    except Exception as e:
        logger.error("Telegram file download error: %s", e)
        return None


def _save_expert_pick(pick: dict, chat_id: int) -> bool:
    """Insert le pick validé dans Supabase."""
    try:
        record = {
            "date": pick.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
            "sport": pick.get("sport", "nhl"),
            "player_name": pick.get("player_name"),
            "market": pick.get("market"),
            "match_label": pick.get("match_label"),
            "odds": pick.get("odds"),
            "confidence": pick.get("confidence", 7),
            "expert_note": pick.get("expert_note", ""),
            "result": "PENDING",
            "telegram_msg_id": str(chat_id),
        }
        supabase.table("expert_picks").insert(record).execute()
        logger.info("Expert pick saved: %s", record)
        return True
    except Exception as e:
        logger.error("Supabase insert error: %s", e)
        return False


def _handle_update(update: dict) -> None:
    """Traite une update Telegram (photo ou texte)."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id: int = message["chat"]["id"]
    text: str = (message.get("text") or message.get("caption") or "").strip()

    # ── Cas 1 : Photo reçue ──────────────────────────────────────
    if "photo" in message:
        # Pick the largest photo (best quality)
        photos = message["photo"]
        best_photo = max(photos, key=lambda p: p.get("file_size", 0))
        file_id = best_photo["file_id"]

        _send_message(chat_id, "📸 Screenshot reçu, analyse en cours... ⏳")

        image_bytes = _download_telegram_file(file_id)
        if not image_bytes:
            _send_message(chat_id, "❌ Impossible de télécharger l'image. Réessaie.")
            return

        pick = parse_winamax_screenshot(image_bytes, caption=text)

        if "error" in pick:
            _send_message(
                chat_id,
                f"⚠️ Erreur lors de l'analyse : {pick['error']}\n\nRéessaie ou envoie les infos en texte.",
            )
            return

        # Store pending pick
        _pending_picks[chat_id] = pick

        # Send confirmation message
        confirmation = format_confirmation_message(pick)
        _send_message(chat_id, confirmation)

    # ── Cas 2 : Confirmation 👍 ──────────────────────────────────
    elif text in ("👍", "✅", "oui", "ok", "yes"):
        pending = _pending_picks.pop(chat_id, None)
        if not pending:
            _send_message(chat_id, "Aucun pick en attente. Envoie d'abord un screenshot.")
            return

        if _save_expert_pick(pending, chat_id):
            player = pending.get("player_name") or pending.get("market", "Pick")
            _send_message(
                chat_id,
                f"✅ *{player}* ajouté aux Paris de l'Expert ! Il apparaîtra sur le site dans quelques secondes. 🎯",
            )
        else:
            _send_message(chat_id, "❌ Erreur lors de la sauvegarde. Réessaie.")

    # ── Cas 3 : Annulation ❌ ────────────────────────────────────
    elif text in ("❌", "non", "no", "annuler", "cancel"):
        _pending_picks.pop(chat_id, None)
        _send_message(chat_id, "❌ Pick annulé.")

    # ── Cas 4 : Commande /status ─────────────────────────────────
    elif text == "/status":
        pending = _pending_picks.get(chat_id)
        if pending:
            _send_message(chat_id, f"Pick en attente :\n{format_confirmation_message(pending)}")
        else:
            _send_message(chat_id, "Aucun pick en attente. Envoie un screenshot Winamax 📸")

    # ── Cas 5 : /start ou aide ───────────────────────────────────
    elif text.startswith("/start") or text == "/aide":
        _send_message(
            chat_id,
            "🎯 *ProbaLab Expert Bot*\n\n"
            "Envoie un screenshot de ton pari Winamax et je l'afficherai automatiquement sur le site !\n\n"
            "📸 *Comment ça marche :*\n"
            "1. Envoie une capture d'écran de ton pari\n"
            "2. Je te montre le récap du pick détecté\n"
            "3. Réponds *👍* pour publier ou *❌* pour annuler\n\n"
            "Tu peux aussi ajouter une note dans la légende de la photo.",
        )


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook Telegram — reçoit les updates et les traite en arrière-plan."""
    try:
        update = await request.json()
        background_tasks.add_task(_handle_update, update)
        return Response(content="ok", status_code=200)
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return Response(content="ok", status_code=200)  # Always 200 to Telegram
