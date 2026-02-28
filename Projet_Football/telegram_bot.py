import requests
from config import logger

# Try importing telegram config from environment variables (you need to add these)
import os
# Config with fallbacks from trigger.py
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8313502721:AAFOlAmD3zyiz8P143Kc16XcArBg-4g3AzY")
# Support single ID or comma-separated list
DEFAULT_CHATS = "5721158019,7003371099"
raw_ids = os.getenv("TELEGRAM_CHAT_IDS") or os.getenv("TELEGRAM_CHANNEL_ID") or DEFAULT_CHATS
TELEGRAM_CHAT_IDS = [cid.strip() for cid in raw_ids.split(",") if cid.strip()]

def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to all configured Telegram chat IDs."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        logger.warning("Telegram Bot Token ou Chat IDs introuvables. Message non envoyé.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    total_sent = 0
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Message Telegram envoyé avec succès à {chat_id}.")
            total_sent += 1
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message Telegram à {chat_id}: {e}")
            
    return total_sent > 0

# Tests can be performed by running this file locally with the env vars set
if __name__ == "__main__":
    # To test locally:
    # export TELEGRAM_BOT_TOKEN="your_token"
    # export TELEGRAM_CHANNEL_ID="@your_channel_name"
    # python Projet_Football/telegram_bot.py
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
        print("Envoi d'un message test...")
        success = send_telegram_message("🤖 <b>Test depuis ProbaLab</b>\nCeci est un message de test automatisé.")
        print("Succès :" if success else "Échec")
    else:
        print("Veuillez configurer TELEGRAM_BOT_TOKEN et TELEGRAM_CHANNEL_ID pour tester.")
