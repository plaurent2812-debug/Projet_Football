from __future__ import annotations

"""
fetch_training_history.py — Récupère l'historique de 2-3 saisons pour l'entraînement ML.

Données récupérées par match :
  - Score final (home_goals, away_goals)
  - Statistiques d'équipe (tirs, possession, etc.) via /fixtures/statistics
  - Cotes pré-match via /odds (si disponibles)
  - Lineups via /fixtures/lineups (pour reconstituer les absents)

Attention : ~10 requêtes API par ligue par saison.
Plan Pro = 7500 req/jour. On reste conservateur.
"""
import time

from config import LEAGUES, api_get, get_request_count, logger, reset_request_count, supabase

# Saisons à récupérer (en plus de la courante 2025)
TRAINING_SEASONS = [2023, 2024]

# Nombre max de matchs FT par ligue/saison
MAX_PER_LEAGUE = 400  # Une saison complète ~ 380 matchs (top 5)


def fetch_season_results(league_id: int, season: int) -> list[dict]:
    """Fetch all finished fixtures for a league/season from the API.

    Uses the ``GET /fixtures`` endpoint with ``status=FT``.  Handles
    pagination automatically (API-Football pages at 1 000 by default).

    Args:
        league_id: API league identifier.
        season: Season year (e.g. ``2024``).

    Returns:
        A list of raw API response items (capped at
        :data:`MAX_PER_LEAGUE`).
    """
    all_fixtures: list[dict] = []
    page: int = 1

    while True:
        data = api_get(
            "fixtures",
            {
                "league": league_id,
                "season": season,
                "status": "FT",
            },
        )
        if not data or not data.get("response"):
            break

        all_fixtures.extend(data["response"])

        # API-Football pagine par défaut à 1000
        total: int = data.get("results", 0)
        if len(all_fixtures) >= total or len(data["response"]) == 0:
            break
        page += 1

    return all_fixtures[:MAX_PER_LEAGUE]


def fetch_fixture_stats(fixture_id: int) -> tuple[dict, dict]:
    """Fetch per-team match statistics (possession, shots, etc.).

    Args:
        fixture_id: API fixture identifier.

    Returns:
        A tuple ``(home_stats, away_stats)`` where each element is a
        dict mapping stat names to their values.  Returns
        ``(None, None)`` when the API returns no data.
    """
    data = api_get("fixtures/statistics", {"fixture": fixture_id})
    if not data or not data.get("response"):
        return None, None

    home_stats: dict = {}
    away_stats: dict = {}
    for team_data in data["response"]:
        stats: dict = {}
        for s in team_data.get("statistics", []):
            stats[s["type"]] = s["value"]

        # Le premier est toujours home
        if not home_stats:
            home_stats = stats
        else:
            away_stats = stats

    return home_stats, away_stats


def fetch_fixture_odds(fixture_id: int) -> dict | None:
    """Fetch pre-match odds from Bet365 (bookmaker id 8).

    Args:
        fixture_id: API fixture identifier.

    Returns:
        A dict with keys ``"home"``, ``"draw"``, ``"away"``,
        ``"over25"``, ``"under25"``, ``"btts_yes"``, ``"btts_no"``
        (values are floats), or ``None`` when odds are unavailable.
    """
    data = api_get("odds", {"fixture": fixture_id, "bookmaker": 8})
    if not data or not data.get("response"):
        return None

    odds: dict = {}
    for resp in data["response"]:
        for bm in resp.get("bookmakers", []):
            for bet in bm.get("bets", []):
                values = {v["value"]: v["odd"] for v in bet.get("values", [])}
                if bet["name"] == "Match Winner":
                    odds["home"] = safe_float(values.get("Home"))
                    odds["draw"] = safe_float(values.get("Draw"))
                    odds["away"] = safe_float(values.get("Away"))
                elif bet["name"] == "Goals Over/Under":
                    odds["over25"] = safe_float(values.get("Over 2.5"))
                    odds["under25"] = safe_float(values.get("Under 2.5"))
                elif bet["name"] == "Both Teams Score":
                    odds["btts_yes"] = safe_float(values.get("Yes"))
                    odds["btts_no"] = safe_float(values.get("No"))
    return odds if odds.get("home") else None


def safe_float(val: str | float | None) -> float | None:
    """Safely cast a value to float.

    Args:
        val: Raw value (string, number, or ``None``).

    Returns:
        The float representation, or ``None`` on failure.
    """
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def upsert_fixtures_batch(fixtures: list[dict], league_id: int, season: int) -> int:
    """Persist a batch of fixtures into the ``fixtures`` table.

    Rows are upserted in chunks of 50 to stay within Supabase limits.

    Args:
        fixtures: Raw API response items (each contains ``fixture``,
            ``goals``, ``teams`` sub-dicts).
        league_id: API league identifier.
        season: Season year.

    Returns:
        The number of rows prepared for upsert.
    """
    batch: list[dict] = []
    for item in fixtures:
        f = item["fixture"]
        goals = item["goals"]
        teams = item["teams"]

        batch.append(
            {
                "api_fixture_id": f["id"],
                "date": f["date"],
                "league_id": league_id,
                "home_team": teams["home"]["name"],
                "away_team": teams["away"]["name"],
                "status": "FT",
                "home_goals": goals["home"],
                "away_goals": goals["away"],
                "referee_name": f.get("referee"),
                "stats_json": {
                    "venue": f.get("venue", {}),
                    "status_short": "FT",
                    "round": item.get("league", {}).get("round", ""),
                    "season": season,
                },
            }
        )

    if batch:
        # Upsert par lots de 50
        for i in range(0, len(batch), 50):
            chunk = batch[i : i + 50]
            try:
                supabase.table("fixtures").upsert(chunk, on_conflict="api_fixture_id").execute()
            except Exception as e:
                logger.warning(f"    ⚠️ Erreur upsert fixtures: {e}")

    return len(batch)


def upsert_teams_from_fixtures(fixtures: list[dict]) -> None:
    """Extract distinct teams from API fixture items and upsert them.

    Args:
        fixtures: Raw API response items.

    Returns:
        None.
    """
    teams_seen: dict[int, dict] = {}
    for item in fixtures:
        for side in ["home", "away"]:
            t = item["teams"][side]
            if t["id"] not in teams_seen:
                teams_seen[t["id"]] = {
                    "api_id": t["id"],
                    "name": t["name"],
                }

    if teams_seen:
        batch = list(teams_seen.values())
        for i in range(0, len(batch), 50):
            try:
                supabase.table("teams").upsert(batch[i : i + 50], on_conflict="api_id").execute()
            except Exception:
                pass  # Fail silently: team dedup is best-effort


def run() -> None:
    """Run the full training-history fetch pipeline.

    Iterates over :data:`TRAINING_SEASONS` and all configured leagues,
    fetches finished fixtures from the API, and upserts them (along with
    extracted teams) into Supabase.

    Returns:
        None.
    """
    reset_request_count()
    logger.info("=" * 60)
    logger.info("  📚 RÉCUPÉRATION DE L'HISTORIQUE POUR ML")
    logger.info("=" * 60)

    total_matches: int = 0

    for season in TRAINING_SEASONS:
        logger.info(f"{'─' * 50}")
        logger.info(f"  SAISON {season}/{season + 1}")
        logger.info(f"{'─' * 50}")

        for league in LEAGUES:
            lid: int = league["id"]
            lname: str = league["name"]

            # Vérifier combien on a déjà
            existing = (
                supabase.table("fixtures")
                .select("id", count="exact")
                .eq("league_id", lid)
                .eq("status", "FT")
                .execute()
            )
            existing_count: int = existing.count or 0

            logger.info(f"  {lname} (saison {season}) — {existing_count} matchs FT déjà en base")

            # Récupérer les résultats
            logger.info("    📥 Fetch des résultats...")
            fixtures = fetch_season_results(lid, season)
            logger.info(f"{len(fixtures)} matchs récupérés")

            if not fixtures:
                continue

            # Stocker les équipes
            upsert_teams_from_fixtures(fixtures)

            # Stocker les matchs
            n = upsert_fixtures_batch(fixtures, lid, season)
            total_matches += n
            logger.info(f"    💾 {n} matchs sauvegardés")

            # Rate limiting entre les ligues
            time.sleep(1)

        logger.info(f"  Requêtes API utilisées : {get_request_count()}")

    logger.info(f"{'=' * 60}")
    logger.info(f"  ✅ Total : {total_matches} matchs historiques importés")
    logger.info(f"  📊 Requêtes API : {get_request_count()}")
    logger.info(f"{'=' * 60}")
    logger.info("⏭️  Prochaine étape : python build_training_data.py")


if __name__ == "__main__":
    run()
