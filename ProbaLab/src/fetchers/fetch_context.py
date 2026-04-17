"""
fetch_context.py — Récupère le contexte des matchs à venir :
  - Blessures/suspensions (GET /injuries)
  - Cotes bookmakers (GET /odds)
  - Head-to-Head (GET /fixtures/headtohead)
  - Météo (OpenWeatherMap, gratuit)

~65 matchs × 3 endpoints = ~195 requêtes API-Football
+ ~65 requêtes OpenWeatherMap (optionnel)
"""

import logging
import os
from datetime import datetime, timezone

import requests

from src.config import LEAGUES, SEASON, api_get, get_request_count, reset_request_count, supabase

logger = logging.getLogger(__name__)


# ── BLESSURES ────────────────────────────────────────────────────
def fetch_injuries():
    """Récupère les joueurs blessés/suspendus pour les prochains matchs."""
    logger.info("=== Importation des blessures/suspensions ===")
    total = 0

    for league in LEAGUES:
        lid = league["id"]
        data = api_get("injuries", {"league": lid, "season": SEASON})
        if not data or not data.get("response"):
            continue

        batch = []
        for item in data["response"]:
            player = item.get("player", {})
            team = item.get("team", {})
            fixture = item.get("fixture", {})

            batch.append(
                {
                    "player_api_id": player.get("id"),
                    "player_name": player.get("name"),
                    "team_api_id": team.get("id"),
                    "league_id": lid,
                    "fixture_api_id": fixture.get("id"),
                    "type": player.get("type"),  # Missing Fixture, Questionable, etc.
                    "reason": player.get("reason"),  # Knee Injury, Suspended, etc.
                }
            )

        if batch:
            # Vider les anciennes blessures de cette ligue puis insérer
            try:
                supabase.table("injuries").delete().eq("league_id", lid).execute()
                supabase.table("injuries").insert(batch).execute()
                total += len(batch)
                logger.info("  %s: %d blessures/suspensions", league["name"], len(batch))
            except Exception as e:
                logger.error("  %s: %s", league["name"], e)

    # ── Synchroniser le flag is_injured (seulement matchs à venir) ──
    logger.info("  Synchronisation du flag is_injured...")
    try:
        # Récupérer les fixture_api_id des matchs NS (à venir)
        ns_fixtures = (
            supabase.table("fixtures").select("api_fixture_id").eq("status", "NS").execute().data
        )
        ns_fids = [f["api_fixture_id"] for f in ns_fixtures if f.get("api_fixture_id")]

        injured_ids = set()
        if ns_fids:
            # Blessures uniquement pour les matchs à venir
            ns_injuries = (
                supabase.table("injuries")
                .select("player_api_id")
                .in_("fixture_api_id", ns_fids)
                .execute()
                .data
            )
            injured_ids = {i["player_api_id"] for i in ns_injuries if i.get("player_api_id")}

        # Reset tous les joueurs à non-blessé
        supabase.table("players").update({"is_injured": False}).eq("is_injured", True).execute()

        # Marquer les blessés actuels
        if injured_ids:
            for pid in injured_ids:
                try:
                    supabase.table("players").update({"is_injured": True}).eq(
                        "api_id", pid
                    ).execute()
                except Exception:
                    pass
            logger.info("  %d joueurs marques comme blesses/absents", len(injured_ids))
        else:
            logger.info("  Aucun joueur blesse detecte pour les matchs a venir")
    except Exception as e:
        logger.warning("  Erreur sync is_injured: %s", e)

    logger.info("Total : %d blessures importees", total)


# ── COTES BOOKMAKERS ─────────────────────────────────────────────
def fetch_odds():
    """Récupère les cotes pré-match pour les fixtures à venir."""
    logger.info("=== Importation des cotes bookmakers ===")

    # Récupérer les fixtures NS
    fixtures = supabase.table("fixtures").select("api_fixture_id").eq("status", "NS").execute().data

    if not fixtures:
        logger.info("   Aucun match a venir.")
        return

    total = 0
    for i, fix in enumerate(fixtures):
        fid = fix["api_fixture_id"]
        if (i + 1) % 20 == 0:
            logger.info("  Odds : %d/%d...", i + 1, len(fixtures))

        data = api_get("odds", {"fixture": fid, "bookmaker": 8})  # 8 = Bet365
        if not data or not data.get("response"):
            continue

        odds_data = {"fixture_api_id": fid, "bookmaker": "Bet365"}

        for resp in data["response"]:
            for bm in resp.get("bookmakers", []):
                for bet in bm.get("bets", []):
                    bet_name = bet.get("name", "")
                    values = {v["value"]: v["odd"] for v in bet.get("values", [])}

                    if bet_name == "Match Winner":
                        odds_data["home_win_odds"] = safe_float(values.get("Home"))
                        odds_data["draw_odds"] = safe_float(values.get("Draw"))
                        odds_data["away_win_odds"] = safe_float(values.get("Away"))

                    elif bet_name == "Goals Over/Under":
                        odds_data["over_15_odds"] = safe_float(values.get("Over 1.5"))
                        odds_data["under_15_odds"] = safe_float(values.get("Under 1.5"))
                        odds_data["over_25_odds"] = safe_float(values.get("Over 2.5"))
                        odds_data["under_25_odds"] = safe_float(values.get("Under 2.5"))
                        odds_data["over_35_odds"] = safe_float(values.get("Over 3.5"))
                        odds_data["under_35_odds"] = safe_float(values.get("Under 3.5"))

                    elif bet_name == "Both Teams Score":
                        odds_data["btts_yes_odds"] = safe_float(values.get("Yes"))
                        odds_data["btts_no_odds"] = safe_float(values.get("No"))

                    elif bet_name == "Double Chance":
                        odds_data["dc_1x_odds"] = safe_float(values.get("Home/Draw"))
                        odds_data["dc_x2_odds"] = safe_float(values.get("Draw/Away"))
                        odds_data["dc_12_odds"] = safe_float(values.get("Home/Away"))

        if odds_data.get("home_win_odds"):
            try:
                supabase.table("fixture_odds").upsert(
                    odds_data, on_conflict="fixture_api_id"
                ).execute()
                total += 1
            except Exception:
                pass

    logger.info("%d matchs avec cotes importees", total)


# ── HEAD TO HEAD ─────────────────────────────────────────────────
def fetch_h2h():
    """Récupère l'historique des confrontations directes pour les matchs à venir."""
    logger.info("=== Importation des Head-to-Head ===")

    # Récupérer les fixtures NS avec les noms d'équipes
    fixtures = supabase.table("fixtures").select("*").eq("status", "NS").execute().data
    if not fixtures:
        logger.info("   Aucun match a venir.")
        return

    # Charger le mapping team_name -> team_api_id
    teams = supabase.table("teams").select("api_id, name").execute().data
    name_to_id = {t["name"]: t["api_id"] for t in teams}

    total = 0
    seen_pairs = set()

    for fix in fixtures:
        home_id = name_to_id.get(fix["home_team"])
        away_id = name_to_id.get(fix["away_team"])

        if not home_id or not away_id:
            continue

        # Éviter les doublons (même paire)
        pair = tuple(sorted([home_id, away_id]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        data = api_get("fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": 10})
        if not data or not data.get("response"):
            continue

        matches = data["response"]
        a_wins = 0
        b_wins = 0
        draws = 0
        a_goals = 0
        b_goals = 0
        last_matches = []

        for m in matches:
            gh = m["goals"]["home"] or 0
            ga = m["goals"]["away"] or 0
            th = m["teams"]["home"]["id"]

            # Déterminer qui est A et qui est B
            if th == home_id:
                a_g, b_g = gh, ga
            else:
                a_g, b_g = ga, gh

            a_goals += a_g
            b_goals += b_g

            if a_g > b_g:
                a_wins += 1
            elif a_g < b_g:
                b_wins += 1
            else:
                draws += 1

            last_matches.append(
                {
                    "date": m["fixture"]["date"],
                    "home": m["teams"]["home"]["name"],
                    "away": m["teams"]["away"]["name"],
                    "score": f"{gh}-{ga}",
                }
            )

        h2h_data = {
            "team_a_api_id": home_id,
            "team_b_api_id": away_id,
            "total_matches": len(matches),
            "team_a_wins": a_wins,
            "draws": draws,
            "team_b_wins": b_wins,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "last_matches_json": last_matches,
        }

        try:
            supabase.table("h2h_cache").upsert(
                h2h_data, on_conflict="team_a_api_id,team_b_api_id"
            ).execute()
            total += 1
        except Exception:
            pass

    logger.info("%d H2H importes", total)


# ── MÉTÉO (optionnel) ────────────────────────────────────────────
def fetch_weather():
    """Récupère la météo prévue pour les matchs à venir (OpenWeatherMap)."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        logger.info("OPENWEATHER_API_KEY non configuree, meteo ignoree.")
        return

    logger.info("=== Importation meteo ===")

    fixtures = (
        supabase.table("fixtures")
        .select("api_fixture_id, date, stats_json")
        .eq("status", "NS")
        .execute()
        .data
    )

    total = 0
    for fix in fixtures:
        venue = (fix.get("stats_json") or {}).get("venue", {})
        city = venue.get("city") if isinstance(venue, dict) else None
        if not city:
            continue

        try:
            resp = requests.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "q": city,
                    "appid": api_key,
                    "units": "metric",
                    "cnt": 8,  # 24h de prévision
                },
                timeout=5,
            )
            weather_data = resp.json()

            if weather_data.get("cod") != "200":
                continue

            # Prendre la prévision la plus proche de la date du match
            match_dt = datetime.fromisoformat(fix["date"].replace("Z", "+00:00"))
            closest = min(
                weather_data.get("list", []),
                key=lambda w: abs(
                    datetime.fromtimestamp(w["dt"], tz=timezone.utc).timestamp()
                    - match_dt.timestamp()
                ),
                default=None,
            )

            if closest:
                weather = {
                    "temp": closest["main"]["temp"],
                    "humidity": closest["main"]["humidity"],
                    "wind_speed": closest["wind"]["speed"],
                    "description": closest["weather"][0]["description"],
                    "rain_mm": closest.get("rain", {}).get("3h", 0),
                }

                supabase.table("fixtures").update({"weather_json": weather}).eq(
                    "api_fixture_id", fix["api_fixture_id"]
                ).execute()
                total += 1

        except Exception:
            continue

    logger.info("Meteo recuperee pour %d matchs", total)


def safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    reset_request_count()
    fetch_injuries()
    fetch_odds()
    fetch_h2h()
    fetch_weather()
    logger.info("=" * 50)
    logger.info("Contexte importe. (%d requetes API-Football)", get_request_count())
