from __future__ import annotations

"""
update_nhl_results.py — Met à jour les nhl_fixtures avec les scores finaux.

Workflow :
  1. Récupère les fixtures NHL en status "NS" des 3 derniers jours
  2. Pour chacune, interroge l'API NHL pour le score final
  3. Met à jour status → "Final", home_score, away_score

Ce script DOIT tourner avant fetch_nhl_results.py (évaluation).

Usage :
    python -m src.fetchers.update_nhl_results [--days 3]
"""
import argparse
import time
from datetime import datetime, timedelta, timezone

import httpx

from src.config import logger, supabase

NHL_SCHEDULE_URL = "https://api-web.nhle.com/v1/schedule/{date}"
NHL_BOXSCORE_URL = "https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"


def _fetch_json(url: str) -> dict | None:
    for attempt in range(3):
        try:
            resp = httpx.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"[NHL] HTTP {resp.status_code} on {url}, retry {attempt + 1}")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"[NHL] Error {e} on {url}, retry {attempt + 1}")
            time.sleep(1)
    return None


def update_nhl_fixture_results(days_back: int = 3) -> dict:
    """Fetch final scores from NHL API and update nhl_fixtures."""
    logger.info("=" * 60)
    logger.info("  🏒 MISE À JOUR SCORES NHL")
    logger.info("=" * 60)

    today = datetime.now(timezone.utc)
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # 1. Get fixtures from recent days
    try:
        from src.nhl.constants import NHL_FINISHED_STATUSES

        all_recent = (
            supabase.table("nhl_fixtures")
            .select("id, api_fixture_id, date, home_team, away_team, status")
            .gte("date", f"{start_date}T00:00:00Z")
            .execute()
            .data
        ) or []
        pending = [f for f in all_recent if f.get("status") not in NHL_FINISHED_STATUSES]
    except Exception as e:
        logger.error(f"[NHL] Error fetching pending fixtures: {e}")
        return {"ok": False, "error": str(e)}

    logger.info(f"  {len(pending)} fixtures en status 'NS' depuis {start_date}")

    if not pending:
        logger.info("  Rien à mettre à jour.")
        return {"ok": True, "updated": 0}

    updated = 0
    for fix in pending:
        api_id = fix.get("api_fixture_id")
        if not api_id:
            continue

        # Fetch boxscore from NHL API
        boxscore = _fetch_json(NHL_BOXSCORE_URL.format(game_id=api_id))
        if not boxscore:
            continue

        game_state = boxscore.get("gameState", "")
        # NHL API states: "FUT" (future), "LIVE", "CRIT" (critical), "OFF" (official/final)
        from src.nhl.constants import NHL_FINISHED_STATUSES

        if game_state not in NHL_FINISHED_STATUSES:
            continue

        # Extract final scores
        home_score = boxscore.get("homeTeam", {}).get("score")
        away_score = boxscore.get("awayTeam", {}).get("score")

        if home_score is None or away_score is None:
            continue

        # Update fixture in Supabase
        try:
            supabase.table("nhl_fixtures").update(
                {
                    "status": "Final",
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                }
            ).eq("id", fix["id"]).execute()

            updated += 1
            logger.info(
                f"  ✅ {fix['home_team']} {home_score}-{away_score} {fix['away_team']} → Final"
            )
        except Exception as e:
            logger.error(f"  ⚠️ Error updating {fix['home_team']} vs {fix['away_team']}: {e}")

        time.sleep(0.3)

    logger.info(f"  {updated}/{len(pending)} fixtures mises à jour")
    return {"ok": True, "pending": len(pending), "updated": updated}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    args = parser.parse_args()
    result = update_nhl_fixture_results(args.days)
    logger.info("Result: %s", result)
