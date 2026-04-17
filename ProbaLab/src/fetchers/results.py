from __future__ import annotations

#!/usr/bin/env python3
"""
fetchers/results.py — Mise à jour des scores et statuts des matchs du jour.

Stratégie économique : 2 appels API par match maximum
  - Appel mi-temps  : déclenché quand un match est en statut HT
  - Appel fin match : déclenché quand un match est terminé (FT, AET, PEN)

Ce script est conçu pour être appelé par un CRON toutes les 15 minutes
pendant les plages horaires de matchs.

Usage :
  python3 -m fetchers.results            → Met à jour les matchs du jour
  python3 -m fetchers.results --date 2025-02-18  → Date spécifique
"""


import logging
import os
import sys
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

import requests
from dotenv import load_dotenv

from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
API_KEY = os.getenv("API_FOOTBALL_KEY")

if not API_KEY:
    logger.error("ERREUR: API_FOOTBALL_KEY manquante")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY,
}

# Statuts "terminé" reconnus par l'API Football
FINISHED_STATUSES = {"FT", "AET", "PEN", "AWD", "WO"}
# Statuts "mi-temps"
HALFTIME_STATUSES = {"HT"}
# Statuts "en cours"
LIVE_STATUSES = {"1H", "2H", "HT", "ET", "P", "BT", "INT", "LIVE"}


def fetch_fixture_from_api(api_fixture_id: int) -> dict | None:
    """Appelle l'API Football pour un fixture précis et retourne les données brutes."""
    try:
        resp = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=API_HEADERS,
            params={"id": api_fixture_id},
            timeout=10,
        )
        data = resp.json()
        results = data.get("response", [])
        return results[0] if results else None
    except Exception as e:
        logger.error("  [API ERROR] fixture %s: %s", api_fixture_id, e)
        return None


def update_fixture_in_db(fixture_id: int, api_data: dict) -> None:
    """Met à jour home_goals, away_goals et status dans Supabase."""
    try:
        goals = api_data.get("goals", {})
        status_short = api_data["fixture"]["status"]["short"]
        elapsed = api_data["fixture"]["status"].get("elapsed")

        update_payload = {
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "status": status_short,
        }

        # Stocker aussi le temps écoulé dans stats_json
        # On fait un merge pour ne pas écraser les autres champs
        existing = (
            supabase.table("fixtures")
            .select("stats_json")
            .eq("id", fixture_id)
            .single()
            .execute()
            .data
        )
        existing_stats = existing.get("stats_json") or {} if existing else {}
        existing_stats["elapsed"] = elapsed
        existing_stats["status_short"] = status_short
        update_payload["stats_json"] = existing_stats

        supabase.table("fixtures").update(update_payload).eq("id", fixture_id).execute()
        logger.info(
            "  Fixture %s mis a jour : %s-%s (%s)",
            fixture_id,
            goals.get("home"),
            goals.get("away"),
            status_short,
        )
    except Exception as e:
        logger.error("  [DB ERROR] fixture %s: %s", fixture_id, e)


def fetch_and_update_results(target_date: str | None = None) -> dict:
    """
    Met à jour les scores des matchs du jour depuis l'API Football.

    Logique :
    - Récupère tous les fixtures de la date cible depuis Supabase
    - Pour chaque fixture dont le statut indique qu'il est en cours ou terminé
      (mais pas encore mis à jour), appelle l'API et met à jour la DB
    - Évite les appels inutiles : ne re-fetch pas un match déjà FT avec un score

    Returns:
        dict avec les compteurs : updated, skipped, errors
    """
    if not target_date:
        target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info("Mise a jour des scores — %s", target_date)
    logger.info("=" * 60)

    # Récupère les fixtures du jour depuis Supabase
    # Note: target_date is UTC-based (datetime.now(timezone.utc) above).
    # Fixture dates stored in DB use Europe/Paris timezone (from matches.py API call),
    # so this window may miss late-night matches or include previous-day ones near midnight.
    # Fenêtre élargie (-12h à +36h) pour s'affranchir des différences de timezone UTC/Paris
    from datetime import timedelta

    target_dt = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    date_start = (target_dt - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
    date_end = (target_dt + timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        fixtures = (
            supabase.table("fixtures")
            .select(
                "id, api_fixture_id, status, home_goals, away_goals, date, home_team, away_team"
            )
            .gte("date", date_start)
            .lte("date", date_end)
            .execute()
            .data
            or []
        )
    except Exception as e:
        logger.error("[SUPABASE ERROR] %s", e)
        return {"updated": 0, "skipped": 0, "errors": 1}

    logger.info("%d fixtures trouves pour le %s", len(fixtures), target_date)

    now_utc = datetime.now(timezone.utc)
    updated = 0
    skipped = 0
    errors = 0

    for fix in fixtures:
        fixture_id = fix["id"]
        api_id = fix.get("api_fixture_id")
        current_status = fix.get("status", "NS")
        home_goals = fix.get("home_goals")
        away_goals = fix.get("away_goals")
        home_team = fix.get("home_team", "?")
        away_team = fix.get("away_team", "?")

        if not api_id:
            skipped += 1
            continue

        # Parse la date du match
        try:
            match_dt = datetime.fromisoformat(fix["date"].replace("Z", "+00:00"))
        except Exception:
            skipped += 1
            continue

        # Décision : faut-il appeler l'API ?
        should_fetch = False
        reason = ""

        if (
            current_status in FINISHED_STATUSES
            and home_goals is not None
            and away_goals is not None
        ):
            # Déjà terminé avec score → skip
            skipped += 1
            logger.debug(
                "  %s vs %s — deja FT (%s-%s)", home_team, away_team, home_goals, away_goals
            )
            continue

        if current_status in FINISHED_STATUSES and (home_goals is None or away_goals is None):
            # Terminé mais score manquant → fetch
            should_fetch = True
            reason = "terminé sans score"

        elif current_status in LIVE_STATUSES:
            # En cours → fetch
            should_fetch = True
            reason = f"en cours ({current_status})"

        elif current_status in ("NS", "TBD"):
            # Pas encore commencé : fetch seulement si l'heure de début est passée
            # (avec 5 min de marge pour la mi-temps ~50 min, fin ~100 min)
            minutes_since_start = (now_utc - match_dt).total_seconds() / 60
            if minutes_since_start >= 45:  # Mi-temps probable
                should_fetch = True
                reason = f"démarré il y a ~{int(minutes_since_start)} min"
            else:
                skipped += 1
                continue

        if should_fetch:
            logger.info("  %s vs %s [%s] — appel API...", home_team, away_team, reason)
            api_data = fetch_fixture_from_api(api_id)
            if api_data:
                update_fixture_in_db(fixture_id, api_data)
                updated += 1
            else:
                errors += 1
            # Petite pause pour ne pas surcharger l'API
            time.sleep(0.3)

    logger.info("=" * 60)
    logger.info("Termine : %d mis a jour | %d ignores | %d erreurs", updated, skipped, errors)
    logger.info("=" * 60)

    return {"updated": updated, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    # Support --date YYYY-MM-DD en argument
    date_arg = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--date" and i + 1 < len(sys.argv) - 1:
            date_arg = sys.argv[i + 2]
        elif arg.startswith("20"):  # Format YYYY-...
            date_arg = arg

    fetch_and_update_results(date_arg)
