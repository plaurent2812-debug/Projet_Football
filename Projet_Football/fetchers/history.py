from __future__ import annotations

"""
fetch_history.py — Récupère les matchs terminés + events + lineups + stats équipes.

Endpoints :
  - GET /fixtures?league={id}&season=2025&status=FT     (~8 req)
  - GET /fixtures/events?fixture={id}                   (~N req)
  - GET /fixtures/lineups?fixture={id}                  (~N req)
  - GET /fixtures/statistics?fixture={id}               (~N req)

On traite les N derniers matchs par ligue (configurable).
Extrait aussi les noms d'arbitres pour calculer leurs stats.
"""
from config import (
    LEAGUES,
    SEASON,
    api_get,
    get_request_count,
    logger,
    reset_request_count,
    supabase,
)

# Nombre de derniers matchs à récupérer par ligue
LAST_N_MATCHES = 60


def fetch_finished_fixtures() -> list[int]:
    """Fetch recently finished fixtures and upsert them into Supabase.

    Retrieves up to :data:`LAST_N_MATCHES` per league via the API,
    cleans referee names, and persists them in the ``fixtures`` table.

    Returns:
        A list of API fixture IDs that were fetched.
    """
    reset_request_count()
    logger.info(f"=== Importation des matchs terminés (Saison {SEASON}) ===")
    all_fixture_ids: list[int] = []

    for league in LEAGUES:
        lid: int = league["id"]
        logger.info(f"📋 {league['name']}...")

        data = api_get(
            "fixtures", {"league": lid, "season": SEASON, "status": "FT", "last": LAST_N_MATCHES}
        )
        if not data or not data.get("response"):
            logger.info("   Aucun match terminé.")
            continue

        fixtures: list[dict] = data["response"]
        logger.info(f"   {len(fixtures)} matchs terminés trouvés.")

        batch: list[dict] = []
        for item in fixtures:
            fix = item["fixture"]
            teams = item["teams"]
            goals = item["goals"]
            league_data = item["league"]

            referee: str | None = fix.get("referee")
            # Nettoyer le nom de l'arbitre (enlever le pays entre parenthèses)
            referee_name: str | None = None
            if referee:
                referee_name = referee.split(",")[0].strip()

            batch.append(
                {
                    "api_fixture_id": fix["id"],
                    "date": fix["date"],
                    "league_id": lid,
                    "home_team": teams["home"]["name"],
                    "away_team": teams["away"]["name"],
                    "status": fix["status"]["short"],
                    "home_goals": goals.get("home"),
                    "away_goals": goals.get("away"),
                    "referee_name": referee_name,
                    "stats_json": {
                        "venue": fix.get("venue"),
                        "status_short": fix["status"]["short"],
                        "round": league_data.get("round"),
                    },
                }
            )

            all_fixture_ids.append(fix["id"])

        try:
            supabase.table("fixtures").upsert(batch, on_conflict="api_fixture_id").execute()
            logger.info(f"   ✅ {len(batch)} matchs enregistrés.")
        except Exception as e:
            logger.error(f"   ❌ Erreur fixtures : {e}")

    logger.info(f"Total : {len(all_fixture_ids)} matchs terminés")
    return all_fixture_ids


def fetch_events_for_fixtures(fixture_ids: list[int]) -> None:
    """Fetch match events (goals, cards, subs) for a list of fixtures.

    Retrieves events via ``GET /fixtures/events`` and upserts them
    into the ``match_events`` table.

    Args:
        fixture_ids: List of API fixture identifiers to process.

    Returns:
        None.
    """
    # Filtrer ceux qui ont déjà des events
    ids_to_fetch = filter_existing_ids("match_events", "fixture_api_id", fixture_ids)

    if not ids_to_fetch:
        logger.info("=== Events : Tout est déjà à jour ===")
        return

    logger.info(f"=== Importation des events ({len(ids_to_fetch)} matchs à traiter) ===")

    for i, fid in enumerate(ids_to_fetch):
        if (i + 1) % 50 == 0 or i == 0:
            logger.info(f"  Events : {i + 1}/{len(ids_to_fetch)}...")

        data = api_get("fixtures/events", {"fixture": fid})
        if not data or not data.get("response"):
            continue

        events: list[dict] = data["response"]
        batch: list[dict] = []
        for ev in events:
            team = ev.get("team", {})
            player = ev.get("player", {})
            assist = ev.get("assist", {})

            batch.append(
                {
                    "fixture_api_id": fid,
                    "team_api_id": team.get("id"),
                    "player_api_id": player.get("id"),
                    "player_name": player.get("name"),
                    "assist_player_api_id": assist.get("id"),
                    "assist_player_name": assist.get("name"),
                    "event_type": ev.get("type"),
                    "event_detail": ev.get("detail"),
                    "minute": ev.get("time", {}).get("elapsed"),
                    "extra_minute": ev.get("time", {}).get("extra"),
                }
            )

        if batch:
            try:
                supabase.table("match_events").upsert(batch).execute()
            except Exception:
                # Insert simple si pas de contrainte unique
                try:
                    supabase.table("match_events").insert(batch).execute()
                except Exception:
                    pass  # Events déjà insérés

    logger.info("  ✅ Events importés.")


def filter_existing_ids(table_name: str, id_column: str, fixture_ids: list[int]) -> list[int]:
    """Return only fixture_ids that are NOT present in the specified table."""
    if not fixture_ids:
        return []
    
    existing_ids = set()
    # Process in chunks of 30 to avoid URL length issues
    chunk_size = 30
    for i in range(0, len(fixture_ids), chunk_size):
        chunk = fixture_ids[i:i + chunk_size]
        try:
            response = supabase.table(table_name)\
                .select(id_column)\
                .in_(id_column, chunk)\
                .execute()
            for row in response.data:
                existing_ids.add(row[id_column])
        except Exception as e:
            logger.warning(f"⚠️ Erreur check existance {table_name}: {e}")
            
    missing = [fid for fid in fixture_ids if fid not in existing_ids]
    skipped = len(fixture_ids) - len(missing)
    if skipped > 0:
        logger.info(f"   ⏩ {skipped} matchs déjà en base ({table_name}), ignorés.")
    
    return missing


def fetch_lineups_for_fixtures(fixture_ids: list[int]) -> None:
    """Fetch starting lineups and substitutes for a list of fixtures.

    Retrieves lineups via ``GET /fixtures/lineups`` and upserts them
    into the ``match_lineups`` table.

    Args:
        fixture_ids: List of API fixture identifiers to process.

    Returns:
        None.
    """
    # Filtrer ceux qui ont déjà des lineups
    ids_to_fetch = filter_existing_ids("match_lineups", "fixture_api_id", fixture_ids)
    
    if not ids_to_fetch:
        logger.info("=== Compositions : Tout est déjà à jour ===")
        return

    logger.info(f"=== Importation des compositions ({len(ids_to_fetch)} matchs à traiter) ===")

    for i, fid in enumerate(ids_to_fetch):
        if (i + 1) % 50 == 0 or i == 0:
            logger.info(f"  Lineups : {i + 1}/{len(ids_to_fetch)}...")

        data = api_get("fixtures/lineups", {"fixture": fid})
        if not data or not data.get("response"):
            continue

        batch: list[dict] = []
        for team_lineup in data["response"]:
            team_id: int | None = team_lineup.get("team", {}).get("id")

            # Titulaires
            for p in team_lineup.get("startXI", []):
                player = p.get("player", {})
                batch.append(
                    {
                        "fixture_api_id": fid,
                        "team_api_id": team_id,
                        "player_api_id": player.get("id"),
                        "player_name": player.get("name"),
                        "position": player.get("pos"),
                        "grid_position": player.get("grid"),
                        "is_substitute": False,
                    }
                )

            # Remplaçants
            for p in team_lineup.get("substitutes", []):
                player = p.get("player", {})
                batch.append(
                    {
                        "fixture_api_id": fid,
                        "team_api_id": team_id,
                        "player_api_id": player.get("id"),
                        "player_name": player.get("name"),
                        "position": player.get("pos"),
                        "grid_position": None,
                        "is_substitute": True,
                    }
                )

        if batch:
            try:
                supabase.table("match_lineups").upsert(
                    batch, on_conflict="fixture_api_id,team_api_id,player_api_id"
                ).execute()
            except Exception:
                pass  # Lineups déjà insérées

    logger.info("  ✅ Compositions importées.")


def fetch_team_stats_for_fixtures(fixture_ids: list[int]) -> None:
    """Fetch per-team match statistics for a list of fixtures.

    Retrieves possession, shots, corners, etc. via
    ``GET /fixtures/statistics`` and upserts them into
    ``match_team_stats``.

    Args:
        fixture_ids: List of API fixture identifiers to process.

    Returns:
        None.
    """
    # Filtrer ceux qui ont déjà des stats
    ids_to_fetch = filter_existing_ids("match_team_stats", "fixture_api_id", fixture_ids)

    if not ids_to_fetch:
        logger.info("=== Stats : Tout est déjà à jour ===")
        return

    logger.info(f"=== Importation des stats équipe ({len(ids_to_fetch)} matchs à traiter) ===")

    def parse_stat(stats_list: list[dict], stat_name: str) -> int | float:
        """Extract a single stat value from an API statistics list.

        Args:
            stats_list: The ``statistics`` array returned by the API.
            stat_name: The ``"type"`` key to look up (e.g.
                ``"Ball Possession"``).

        Returns:
            The parsed numeric value, or ``0`` when missing.
        """
        for s in stats_list:
            if s.get("type") == stat_name:
                val = s.get("value")
                if val is None:
                    return 0
                if isinstance(val, str) and val.endswith("%"):
                    try:
                        return float(val.replace("%", ""))
                    except ValueError:
                        return 0
                try:
                    return int(val) if isinstance(val, (int, float)) else int(float(val))
                except (ValueError, TypeError):
                    return 0
        return 0

    for i, fid in enumerate(ids_to_fetch):
        if (i + 1) % 50 == 0 or i == 0:
            logger.info(f"  Stats : {i + 1}/{len(ids_to_fetch)}...")

        data = api_get("fixtures/statistics", {"fixture": fid})
        if not data or not data.get("response"):
            continue

        batch: list[dict] = []
        for team_stats in data["response"]:
            team_id: int | None = team_stats.get("team", {}).get("id")
            stats: list[dict] = team_stats.get("statistics", [])

            batch.append(
                {
                    "fixture_api_id": fid,
                    "team_api_id": team_id,
                    "possession": parse_stat(stats, "Ball Possession"),
                    "shots_total": parse_stat(stats, "Total Shots"),
                    "shots_on_target": parse_stat(stats, "Shots on Goal"),
                    "shots_off_target": parse_stat(stats, "Shots off Goal"),
                    "blocked_shots": parse_stat(stats, "Blocked Shots"),
                    "corners": parse_stat(stats, "Corner Kicks"),
                    "offsides": parse_stat(stats, "Offsides"),
                    "fouls": parse_stat(stats, "Fouls"),
                    "yellow_cards": parse_stat(stats, "Yellow Cards"),
                    "red_cards": parse_stat(stats, "Red Cards"),
                    "passes_total": parse_stat(stats, "Total passes"),
                    "passes_accurate": parse_stat(stats, "Passes accurate"),
                    "passes_pct": parse_stat(stats, "Passes %"),
                    "expected_goals": parse_stat(stats, "expected_goals"),
                }
            )

        if batch:
            try:
                supabase.table("match_team_stats").upsert(
                    batch, on_conflict="fixture_api_id,team_api_id"
                ).execute()
            except Exception:
                pass

    logger.info("  ✅ Stats équipe importées.")


def compute_referee_stats() -> None:
    """Compute aggregated referee statistics from match data.

    Joins fixtures (with referees) to match events and team stats to
    derive per-referee averages for yellows, reds, penalties, and fouls,
    then upserts the results into the ``referees`` table.

    Returns:
        None.
    """
    logger.info("=== Calcul des stats arbitres ===")

    # Récupérer les fixtures avec arbitre
    fixtures = (
        supabase.table("fixtures")
        .select("api_fixture_id, referee_name")
        .neq("referee_name", None)
        .neq("status", "NS")
        .execute()
        .data
    )

    if not fixtures:
        logger.info("   Aucun match avec arbitre trouvé.")
        return

    # Récupérer les events et stats
    referee_data: dict[str, dict[str, int]] = {}
    for fix in fixtures:
        ref: str | None = fix["referee_name"]
        if not ref:
            continue

        if ref not in referee_data:
            referee_data[ref] = {
                "matches": 0,
                "yellows": 0,
                "reds": 0,
                "penalties": 0,
                "fouls": 0,
            }

        referee_data[ref]["matches"] += 1

    # Enrichir avec les events (penalties, cartons)
    events = (
        supabase.table("match_events")
        .select("fixture_api_id, event_type, event_detail")
        .execute()
        .data
    )

    # Mapper fixture_id -> referee
    fix_to_ref: dict[int, str] = {
        f["api_fixture_id"]: f["referee_name"] for f in fixtures if f["referee_name"]
    }

    for ev in events:
        ref = fix_to_ref.get(ev["fixture_api_id"])
        if not ref or ref not in referee_data:
            continue

        if ev["event_type"] == "Card":
            if "Yellow" in (ev["event_detail"] or ""):
                referee_data[ref]["yellows"] += 1
            if "Red" in (ev["event_detail"] or ""):
                referee_data[ref]["reds"] += 1

        if ev["event_type"] == "Goal" and ev["event_detail"] == "Penalty":
            referee_data[ref]["penalties"] += 1

    # Enrichir avec les fouls depuis match_team_stats
    team_stats = supabase.table("match_team_stats").select("fixture_api_id, fouls").execute().data

    for ts in team_stats:
        ref = fix_to_ref.get(ts["fixture_api_id"])
        if ref and ref in referee_data:
            referee_data[ref]["fouls"] += ts.get("fouls", 0)

    # Upsert les stats arbitres
    batch: list[dict] = []
    for name, rd in referee_data.items():
        m: int = max(rd["matches"], 1)
        batch.append(
            {
                "name": name,
                "matches_officiated": rd["matches"],
                "total_yellows": rd["yellows"],
                "total_reds": rd["reds"],
                "total_penalties": rd["penalties"],
                "total_fouls": rd["fouls"],
                "avg_yellows_per_match": round(rd["yellows"] / m, 2),
                "avg_reds_per_match": round(rd["reds"] / m, 2),
                "avg_penalties_per_match": round(rd["penalties"] / m, 2),
                "avg_fouls_per_match": round(rd["fouls"] / m, 2),
            }
        )

    if batch:
        try:
            supabase.table("referees").upsert(batch, on_conflict="name").execute()
            logger.info(f"   ✅ {len(batch)} arbitres avec stats enregistrés.")
        except Exception as e:
            logger.error(f"   ❌ Erreur referees : {e}")


if __name__ == "__main__":
    fixture_ids = fetch_finished_fixtures()

    if fixture_ids:
        fetch_events_for_fixtures(fixture_ids)
        fetch_lineups_for_fixtures(fixture_ids)
        fetch_team_stats_for_fixtures(fixture_ids)
        compute_referee_stats()

    logger.info(f"{'=' * 50}")
    logger.info(f"Pipeline historique terminé. ({get_request_count()} requêtes API au total)")
