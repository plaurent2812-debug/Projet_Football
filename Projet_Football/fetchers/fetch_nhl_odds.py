"""
Récupération des cotes (Odds) pour les matchs NHL du jour via API-Sports (Hockey).
Endpoint: https://v1.hockey.api-sports.io/odds
"""

import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# Setup path to import config module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import supabase, logger, API_FOOTBALL_KEY

# Configuration spécifique pour API-Sports Hockey
HOCKEY_API_URL = "https://v1.hockey.api-sports.io"
HEADERS = {
    "x-rapidapi-host": "v1.hockey.api-sports.io",
    "x-rapidapi-key": API_FOOTBALL_KEY,
}

def fetch_nhl_odds():
    logger.info("[NHL Odds] Démarrage de la récupération des cotes...")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Récupérer les matchs du jour qui n'ont pas encore commencé
    fixtures = (
        supabase.table("nhl_fixtures")
        .select("id, api_fixture_id, home_team, away_team")
        .gte("date", f"{today_str}T00:00:00Z")
        .lt("date", f"{today_str}T23:59:59Z")
        .in_("status", ["NS"])
        .execute()
        .data or []
    )
    
    if not fixtures:
        logger.info("[NHL Odds] Aucun match NS prévu aujourd'hui.")
        return {"status": "ok", "count": 0}
        
    logger.info(f"[NHL Odds] {len(fixtures)} matchs trouvés pour {today_str}")
    
    updated_count = 0
    errors = 0
    
    for fix in fixtures:
        api_id = fix.get("api_fixture_id")
        if not api_id:
            continue
            
        try:
            # Récupération des cotes (bookmaker 1 = Bet365 souvent, mais on peut prendre tout et filtrer plus tard)
            # On prend en priorité le marché "Money Line" ou "Home/Away"
            resp = requests.get(
                f"{HOCKEY_API_URL}/odds", 
                headers=HEADERS, 
                params={"game": api_id}, 
                timeout=15
            )
            
            # API-Sports requests limit
            time.sleep(1)
            
            if resp.status_code != 200:
                logger.error(f"[NHL Odds] Erreur HTTP {resp.status_code} pour le match {api_id}")
                errors += 1
                continue
                
            data = resp.json()
            if not data.get("response"):
                logger.warning(f"[NHL Odds] Aucune cote disponible pour le match {api_id}")
                continue
                
            odds_data = data["response"][0]
            
            # Mettre à jour la base de données
            supabase.table("nhl_fixtures").update({
                "odds_json": odds_data
            }).eq("api_fixture_id", api_id).execute()
            
            logger.info(f"[NHL Odds] ✅ Cotes récupérées pour {fix['home_team']} vs {fix['away_team']}")
            updated_count += 1
            
        except Exception as e:
            logger.error(f"[NHL Odds] Erreur inattendue pour {api_id}: {e}")
            errors += 1
            
    logger.info(f"[NHL Odds] Fin: {updated_count} mis à jour, {errors} erreurs.")
    return {"status": "ok", "updated": updated_count, "errors": errors}

if __name__ == "__main__":
    fetch_nhl_odds()
