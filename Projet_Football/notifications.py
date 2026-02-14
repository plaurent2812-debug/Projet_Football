"""
notifications.py — Notifications Telegram & Discord pour Football IA.

Envoie des alertes automatiques pour les value bets détectés
et les résumés quotidiens de prédictions.

Configuration requise dans .env :
    TELEGRAM_BOT_TOKEN=<token>
    TELEGRAM_CHAT_ID=<chat_id>
    DISCORD_WEBHOOK_URL=<url>  (optionnel)
"""

from __future__ import annotations

import os
from typing import Any

import requests
from config import logger

# ── Configuration ──────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")
DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_URL")


# ═══════════════════════════════════════════════════════════════════
#  TELEGRAM
# ═══════════════════════════════════════════════════════════════════


def send_telegram(
    message: str,
    chat_id: str | None = None,
    token: str | None = None,
    parse_mode: str = "HTML",
) -> bool:
    """Send a message via Telegram Bot API.

    Args:
        message: Message text (supports HTML or Markdown formatting).
        chat_id: Telegram chat/channel ID.  Defaults to env var.
        token: Bot API token.  Defaults to env var.
        parse_mode: ``"HTML"`` or ``"Markdown"``.

    Returns:
        ``True`` if the message was sent successfully, ``False`` otherwise.
    """
    token = token or TELEGRAM_BOT_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("Telegram non configuré (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID manquant)")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Notification Telegram envoyée")
            return True
        else:
            logger.error("Telegram HTTP %d: %s", resp.status_code, resp.text[:200])
            return False
    except requests.RequestException as e:
        logger.error("Erreur Telegram: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════════
#  DISCORD
# ═══════════════════════════════════════════════════════════════════


def send_discord(
    message: str,
    webhook_url: str | None = None,
) -> bool:
    """Send a message to a Discord channel via webhook.

    Args:
        message: Plain text message content.
        webhook_url: Discord webhook URL.  Defaults to env var.

    Returns:
        ``True`` if successful, ``False`` otherwise.
    """
    webhook_url = webhook_url or DISCORD_WEBHOOK_URL

    if not webhook_url:
        logger.warning("Discord non configuré (DISCORD_WEBHOOK_URL manquant)")
        return False

    try:
        resp = requests.post(
            webhook_url,
            json={"content": message},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            logger.info("Notification Discord envoyée")
            return True
        else:
            logger.error("Discord HTTP %d: %s", resp.status_code, resp.text[:200])
            return False
    except requests.RequestException as e:
        logger.error("Erreur Discord: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════════
#  MESSAGES FORMATÉS
# ═══════════════════════════════════════════════════════════════════


def format_value_bets(predictions: list[dict[str, Any]]) -> str:
    """Format value bets as an HTML message for Telegram.

    Args:
        predictions: List of prediction dicts containing match info
            and value bet indicators.

    Returns:
        Formatted HTML string ready for Telegram.
    """
    value_bets = [p for p in predictions if p.get("is_value")]

    if not value_bets:
        return ""

    msg = "🔥 <b>VALUE BETS DÉTECTÉS</b>\n\n"

    for bet in value_bets:
        home = bet.get("home_team", "?")
        away = bet.get("away_team", "?")
        prediction = bet.get("prediction", "?")
        proba = bet.get("confidence", bet.get("proba_home", "?"))
        odds = bet.get("odds", "?")
        edge = bet.get("edge", "?")

        msg += f"⚽ <b>{home}</b> vs <b>{away}</b>\n"
        msg += f"   📊 {prediction} @ {odds}"
        if isinstance(proba, (int, float)):
            msg += f" (modèle: {proba}%)"
        if isinstance(edge, (int, float)):
            msg += f" — edge: +{edge:.1f}%"
        msg += "\n\n"

    return msg


def format_daily_summary(stats: dict[str, Any]) -> str:
    """Format a daily performance summary for notifications.

    Args:
        stats: Dictionary with keys like ``total_matches``,
            ``correct_1x2``, ``value_bets_count``, ``brier_score``.

    Returns:
        Formatted HTML string.
    """
    total = stats.get("total_matches", 0)
    correct = stats.get("correct_1x2", 0)
    rate = round(correct / total * 100, 1) if total > 0 else 0
    vb_count = stats.get("value_bets_count", 0)
    brier = stats.get("brier_score")

    msg = "📋 <b>RÉSUMÉ QUOTIDIEN</b>\n\n"
    msg += f"📊 Matchs analysés : <b>{total}</b>\n"
    msg += f"✅ Réussite 1X2 : <b>{correct}/{total}</b> ({rate}%)\n"
    msg += f"💰 Value bets : <b>{vb_count}</b>\n"

    if brier is not None:
        msg += f"🎯 Brier Score : <b>{brier:.4f}</b>\n"

    msg += "\n📈 Détails sur le dashboard"
    return msg


def format_ticket_result(
    ticket_type: str,
    picks: list[dict[str, Any]],
    won: bool,
    stake: float,
    gain: float,
) -> str:
    """Format a combined ticket result notification.

    Args:
        ticket_type: ``"Safe"``, ``"Fun"``, or ``"Jackpot"``.
        picks: List of pick dicts with ``match`` and ``result`` keys.
        won: Whether the ticket won.
        stake: Stake amount.
        gain: Net gain (positive) or loss (negative).

    Returns:
        Formatted HTML string.
    """
    emoji = "✅" if won else "❌"
    type_emojis = {"Safe": "🛡️", "Fun": "🎯", "Jackpot": "🎰"}

    msg = f"{emoji} <b>TICKET {ticket_type.upper()}</b> {type_emojis.get(ticket_type, '🎫')}\n\n"

    for pick in picks:
        match_name = pick.get("match", "?")
        result = pick.get("result", "?")
        pick_ok = pick.get("correct", False)
        icon = "✅" if pick_ok else "❌"
        msg += f"{icon} {match_name} — {result}\n"

    msg += f"\n💰 Mise: {stake:.2f}€"
    if won:
        msg += f" → <b>+{gain:.2f}€</b> 🎉"
    else:
        msg += f" → <b>{gain:.2f}€</b>"

    return msg


# ═══════════════════════════════════════════════════════════════════
#  FONCTION PRINCIPALE : NOTIFIER
# ═══════════════════════════════════════════════════════════════════


def notify_value_bets(predictions: list[dict[str, Any]]) -> None:
    """Send value bet alerts to all configured channels.

    Args:
        predictions: List of prediction dicts from the analysis pipeline.
    """
    msg = format_value_bets(predictions)
    if not msg:
        logger.info("Aucun value bet à notifier")
        return

    send_telegram(msg)
    # Discord version (pas de HTML)
    plain_msg = msg.replace("<b>", "**").replace("</b>", "**")
    send_discord(plain_msg)


def notify_daily_summary(stats: dict[str, Any]) -> None:
    """Send the daily summary to all configured channels.

    Args:
        stats: Performance statistics dictionary.
    """
    msg = format_daily_summary(stats)
    send_telegram(msg)
    plain_msg = msg.replace("<b>", "**").replace("</b>", "**")
    send_discord(plain_msg)
