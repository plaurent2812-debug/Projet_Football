"""
api/routers/telegram.py — Webhook Telegram pour les paris de l'expert.

Flow:
1. Expert envoie un screenshot Winamax dans Telegram
2. Webhook reçoit l'image → Gemini Vision OCR l'analyse
3. Bot répond avec un résumé formaté et demande confirmation (👍 / ❌)
4. Si 👍 → le pick est inséré en DB (expert_picks)
5. Si ❌ → pick annulé

Flow Combiné (multi-screenshots):
1. /combo → démarre le mode combiné
2. Chaque screenshot est analysé et les sélections sont accumulées
3. /done <cote> → fusionne tout en un combiné et demande confirmation
4. 👍 / ❌ pour confirmer/annuler
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

# In-memory store: chat_id → combo state
# Each entry: {"selections": [...], "sport": "football", "date": "..."}
_combo_state: dict[int, dict] = {}


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
    import json as _json

    try:
        selections = pick.get("selections") or []
        is_combine = len(selections) > 1

        # Build market label
        if is_combine:
            market = f"Combiné ({len(selections)} sélections)"
            match_label = pick.get("match_label") or "; ".join(
                s.get("match", "") for s in selections if s.get("match")
            )
        else:
            market = pick.get("market") or (selections[0].get("bet") if selections else "")
            match_label = pick.get("match_label") or (selections[0].get("match") if selections else None)

        # Store selections as JSON in expert_note for combinés; otherwise caption
        if is_combine:
            expert_note = _json.dumps(selections, ensure_ascii=False)
        else:
            expert_note = pick.get("expert_note", "")

        # Parse odds value
        odds_val = pick.get("odds")
        if odds_val is not None:
            try:
                odds_val = round(float(odds_val), 2)
            except (ValueError, TypeError):
                odds_val = None

        record = {
            "date": pick.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
            "sport": pick.get("sport", "football"),
            "player_name": pick.get("player_name"),
            "market": market,
            "match_label": match_label,
            "odds": odds_val,
            "confidence": pick.get("confidence", 7),
            "expert_note": expert_note,
            "result": "PENDING",
            "telegram_msg_id": str(chat_id),
        }
        logger.info("Saving expert pick: odds=%s market=%s", odds_val, market)

        try:
            supabase.table("expert_picks").insert(record).execute()
        except Exception as insert_err:
            # If numeric overflow, retry without odds (store in expert_note)
            if "numeric field overflow" in str(insert_err):
                logger.warning("Odds %s overflows column, storing in expert_note", odds_val)
                if expert_note:
                    expert_note = f"[odds={odds_val}] {expert_note}"
                else:
                    expert_note = f"[odds={odds_val}]"
                record["odds"] = None
                record["expert_note"] = expert_note
                supabase.table("expert_picks").insert(record).execute()
            else:
                raise
        logger.info("Expert pick saved: %s", record)
        return True
    except Exception as e:
        logger.error("Supabase insert error: %s | record: %s", e, record if 'record' in dir() else 'N/A')
        return False


def _handle_update(update: dict) -> None:
    """Traite une update Telegram (photo ou texte)."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id: int = message["chat"]["id"]
    text: str = (message.get("text") or message.get("caption") or "").strip()

    # ── Cas 0 : /combo → démarre le mode multi-screenshots ──────
    if text.lower() == "/combo":
        _combo_state[chat_id] = {
            "selections": [],
            "sport": "football",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        _send_message(
            chat_id,
            "🔗 *Mode Combiné activé !*\n\n"
            "Envoie tes screenshots un par un.\n"
            "Quand tu as fini :\n"
            "  `/done 3.45` (avec la cote totale)\n\n"
            "Pour annuler : `/reset`",
        )
        return

    # ── Cas 0b : /done <odds> → finaliser le combiné ────────────
    if text.lower().startswith("/done"):
        combo = _combo_state.get(chat_id)
        if not combo or not combo["selections"]:
            _send_message(chat_id, "⚠️ Pas de combiné en cours. Utilise `/combo` d'abord.")
            return

        # Parse odds from /done command
        parts = text.split()
        odds = None
        if len(parts) >= 2:
            try:
                odds = float(parts[1].replace(",", "."))
            except ValueError:
                pass

        if not odds:
            _send_message(chat_id, "⚠️ Indique la cote totale : `/done 3.45`")
            return

        # Build combined pick
        all_selections = combo["selections"]
        match_labels = []
        for s in all_selections:
            if s.get("match"):
                match_labels.append(s["match"])

        combined_pick = {
            "selections": all_selections,
            "odds": odds,
            "sport": combo["sport"],
            "date": combo["date"],
            "match_label": "; ".join(match_labels),
            "market": f"Combiné ({len(all_selections)} sélections)",
            "expert_note": "",
        }

        # Clear combo state, store as pending pick
        del _combo_state[chat_id]
        _pending_picks[chat_id] = combined_pick

        confirmation = format_confirmation_message(combined_pick)
        _send_message(chat_id, confirmation)
        return

    # ── Cas 0c : /reset → annuler le combiné ────────────────────
    if text.lower() == "/reset":
        if chat_id in _combo_state:
            n = len(_combo_state[chat_id]["selections"])
            del _combo_state[chat_id]
            _send_message(chat_id, f"❌ Combiné annulé ({n} sélections supprimées).")
        else:
            _send_message(chat_id, "Aucun combiné en cours.")
        return

    # ── Cas 1 : Photo reçue ──────────────────────────────────────
    if "photo" in message:
        # Pick the largest photo (best quality)
        photos = message["photo"]
        best_photo = max(photos, key=lambda p: p.get("file_size", 0))
        file_id = best_photo["file_id"]

        in_combo = chat_id in _combo_state

        if in_combo:
            _send_message(chat_id, "📸 Screenshot reçu, extraction des sélections... ⏳")
        else:
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

        # ── Mode Combiné : accumuler les sélections ──────────
        if in_combo:
            combo = _combo_state[chat_id]
            new_selections = pick.get("selections") or []
            if not new_selections:
                # Fallback: create a selection from market/match_label
                new_selections = [{
                    "bet": pick.get("market", ""),
                    "match": pick.get("match_label", ""),
                }]

            combo["selections"].extend(new_selections)

            # Update sport if detected
            if pick.get("sport"):
                combo["sport"] = pick["sport"]

            n = len(combo["selections"])
            sel_summary = "\n".join(
                f"  {i+1}. {s.get('bet', '?')} ({s.get('match', '?')})"
                for i, s in enumerate(combo["selections"])
            )
            _send_message(
                chat_id,
                f"✅ *{len(new_selections)} sélection(s) ajoutée(s) !*\n\n"
                f"📋 *Combiné en cours ({n} sélections) :*\n{sel_summary}\n\n"
                f"📸 Envoie le screenshot suivant\n"
                f"✅ `/done 3.45` pour finaliser\n"
                f"❌ `/reset` pour annuler",
            )
            return

        # ── Mode normal : pari simple ────────────────────────
        _pending_picks[chat_id] = pick
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
        _combo_state.pop(chat_id, None)
        _send_message(chat_id, "❌ Pick annulé.")

    # ── Cas 4 : Commande /status ─────────────────────────────────
    elif text == "/status":
        combo = _combo_state.get(chat_id)
        pending = _pending_picks.get(chat_id)
        if combo:
            n = len(combo["selections"])
            sel_summary = "\n".join(
                f"  {i+1}. {s.get('bet', '?')} ({s.get('match', '?')})"
                for i, s in enumerate(combo["selections"])
            )
            _send_message(
                chat_id,
                f"🔗 *Combiné en cours ({n} sélections) :*\n{sel_summary}\n\n"
                f"📸 Envoie le screenshot suivant\n"
                f"✅ `/done 3.45` pour finaliser",
            )
        elif pending:
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
            "🔗 *Pour un combiné multi-screenshots :*\n"
            "1. `/combo` → démarre le mode combiné\n"
            "2. Envoie tes screenshots un par un\n"
            "3. `/done 3.45` → finalise avec la cote totale\n\n"
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

