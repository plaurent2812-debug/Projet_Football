"""
Live Match Tracker pour le Football.
Envoie des alertes Telegram spécifiques à la Mi-temps (HT) et à la 70ème minute.

Conditions Mi-temps :
- Score 0-0
- Pour au moins une équipe : xG > 1.2, Tirs > 10, Tirs cadrés >= 4

Conditions 70ème minute :
- Score 0-0
- Pour au moins une équipe dans la 2ème mi-temps : xG > 1.5, Tirs > 8, Tirs cadrés >= 3
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Ajouter la racine au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import LEAGUES, api_get, logger, supabase

# On restreint la surveillance aux ligues majeures pour économiser les quotas API
LEAGUE_IDS = "-".join([str(l["id"]) for l in LEAGUES])


def get_live_fixtures():
    """Récupère les IDs des matchs actuellement en live dans nos ligues."""
    data = api_get("fixtures", {"live": LEAGUE_IDS})
    if not data or not data.get("response"):
        return []

    fixtures = []
    for item in data["response"]:
        status = item.get("fixture", {}).get("status", {}).get("short", "")
        # On ne s'intéresse qu'à la 1H, HT, 2H
        if status in ["1H", "2H", "HT", "LIVE"]:
            fixtures.append(
                {
                    "fixture_id": item["fixture"]["id"],
                    "home_team": item["teams"]["home"]["name"],
                    "away_team": item["teams"]["away"]["name"],
                    "elapsed": item["fixture"]["status"]["elapsed"] or 0,
                    "status": status,
                    "goals_home": item["goals"]["home"] or 0,
                    "goals_away": item["goals"]["away"] or 0,
                }
            )
    return fixtures


def get_live_statistics(fixture_id):
    """Récupère les statistiques détaillées (Total Shots, Shots on Goal, expected_goals)."""
    data = api_get("fixtures/statistics", {"fixture": fixture_id})
    if not data or not data.get("response"):
        return None

    stats_dict = {"home": {}, "away": {}}
    try:
        if len(data["response"]) >= 2:
            home_data = data["response"][0]
            away_data = data["response"][1]

            for item in home_data.get("statistics", []):
                val = item["value"]
                if val is None:
                    val = 0
                stats_dict["home"][item["type"]] = val

            for item in away_data.get("statistics", []):
                val = item["value"]
                if val is None:
                    val = 0
                stats_dict["away"][item["type"]] = val
    except (IndexError, KeyError) as e:
        logger.warning(f"Impossible de parser les statistiques de {fixture_id}: {e}")
        return None

    return stats_dict


def extract_key_stats(stats_dict):
    """Extrait xG, Tirs totaux et Tirs cadrés."""
    if not stats_dict:
        return {"home": {}, "away": {}}

    def _get(team_stats):
        # xG peut être un float string
        xg_str = team_stats.get("expected_goals", "0")
        try:
            xg = float(xg_str)
        except ValueError:
            xg = 0.0

        return {
            "total_shots": int(team_stats.get("Total Shots", 0)),
            "shots_on_target": int(team_stats.get("Shots on Goal", 0)),
            "xg": xg,
        }

    return {"home": _get(stats_dict["home"]), "away": _get(stats_dict["away"])}


def get_match_cache(fixture_id):
    result = (
        supabase.table("football_momentum_cache")
        .select("*")
        .eq("api_fixture_id", fixture_id)
        .execute()
    )
    if result.data:
        record = result.data[0]
        # Dans cette nouvelle version, `stats_history` contiendra un dict: {"ht_stats": {...}, "alerts": []}
        history = record.get("stats_history")
        if isinstance(history, list):
            # Migration depuis l'ancien format
            history = {"ht_stats": None, "alerts": []}
        elif not isinstance(history, dict):
            history = {"ht_stats": None, "alerts": []}
        return history
    return {"ht_stats": None, "alerts": []}


def save_match_cache(fixture_id, cache_data):
    now = datetime.now(timezone.utc).isoformat()
    # Vérifie si la ligne existe
    result = (
        supabase.table("football_momentum_cache")
        .select("id")
        .eq("api_fixture_id", fixture_id)
        .execute()
    )
    if result.data:
        supabase.table("football_momentum_cache").update(
            {"stats_history": cache_data, "last_updated": now}
        ).eq("api_fixture_id", fixture_id).execute()
    else:
        supabase.table("football_momentum_cache").insert(
            {"api_fixture_id": fixture_id, "stats_history": cache_data, "last_updated": now}
        ).execute()


def compute_delta(current, ht):
    """Soustrait les stats HT des stats actuelles pour avoir les stats de la 2ème mi-temps."""
    return {
        "total_shots": max(0, current["total_shots"] - ht["total_shots"]),
        "shots_on_target": max(0, current["shots_on_target"] - ht["shots_on_target"]),
        "xg": max(0.0, current["xg"] - ht["xg"]),
    }


def run_momentum_tracker():
    logger.info("⚡ [Live Tracker] Scan des événements Mi-temps et 70ème minute...")

    live_fixtures = get_live_fixtures()
    if not live_fixtures:
        return {"status": "ok", "matches_analyzed": 0, "alerts_sent": 0}

    alerts = []

    for fix in live_fixtures:
        # Conditions globales : doit être 0-0
        if fix["goals_home"] != 0 or fix["goals_away"] != 0:
            continue

        fid = fix["fixture_id"]
        status = fix["status"]
        elapsed = fix["elapsed"]

        # On vérifie si on est dans la fenêtre HT ou 70'
        # HT = Status 'HT' ou (elapsed == 45 et statut 1H/HT)
        is_ht_window = status == "HT" or (status == "1H" and elapsed >= 45)
        # 70' = Status '2H' et elapsed entre 70 et 74 (pour être sûr de ne pas le rater avec un cron de 5min)
        is_70_window = status == "2H" and 70 <= elapsed <= 74

        if not (is_ht_window or is_70_window):
            continue

        cache = get_match_cache(fid)
        alerts_sent = cache.get("alerts", [])

        # Vérifier si l'alerte a déjà été envoyée
        if is_ht_window and "HT" in alerts_sent:
            continue
        if is_70_window and "70" in alerts_sent:
            continue

        raw_stats = get_live_statistics(fid)
        if not raw_stats:
            continue

        current_stats = extract_key_stats(raw_stats)

        home = fix["home_team"]
        away = fix["away_team"]

        # ─── LOGIQUE MI-TEMPS ───
        if is_ht_window:
            # On enregistre toujours les stats HT pour la 2ème mi-temps
            cache["ht_stats"] = current_stats
            save_match_cache(fid, cache)

            # Condition : xG > 1.2, Tirs > 10, Cadrés >= 4
            def check_ht(stats):
                return (
                    stats["xg"] > 1.2
                    and stats["total_shots"] > 10
                    and stats["shots_on_target"] >= 4
                )

            home_match = check_ht(current_stats["home"])
            away_match = check_ht(current_stats["away"])

            if home_match or away_match:
                team_on_fire = home if home_match else away
                fire_stats = current_stats["home"] if home_match else current_stats["away"]

                alerts.append(
                    {
                        "match": f"{home} 0-0 {away}",
                        "timing": "Mi-temps",
                        "team": team_on_fire,
                        "stats": fire_stats,
                        "type": "HT",
                    }
                )
                cache["alerts"].append("HT")
                save_match_cache(fid, cache)

        # ─── LOGIQUE 70ème MINUTE ───
        elif is_70_window:
            ht_stats = cache.get("ht_stats")
            # S'il n'y a pas de stats HT en cache (car le script n'a pas tourné à la mi-temps),
            # on ne peut pas calculer la 2ème mi-temps précisément. On ignore, ou on fait une approximation ?
            # Pour être strict, on passe.
            if not ht_stats:
                logger.warning(f"[{fid}] Pas de stats HT en cache pour évaluer la 70ème min.")
                continue

            h2_home = compute_delta(current_stats["home"], ht_stats["home"])
            h2_away = compute_delta(current_stats["away"], ht_stats["away"])

            # Condition : xG > 1.5, Tirs > 8, Cadrés >= 3 (dans la mi-temps)
            def check_70(stats):
                return (
                    stats["xg"] > 1.5 and stats["total_shots"] > 8 and stats["shots_on_target"] >= 3
                )

            home_match = check_70(h2_home)
            away_match = check_70(h2_away)

            if home_match or away_match:
                team_on_fire = home if home_match else away
                fire_stats = h2_home if home_match else h2_away

                alerts.append(
                    {
                        "match": f"{home} 0-0 {away}",
                        "timing": f"{elapsed}ème",
                        "team": team_on_fire,
                        "stats": fire_stats,
                        "type": "70",
                    }
                )
                cache["alerts"].append("70")
                save_match_cache(fid, cache)

    # ─── ENVOI TELEGRAM ───
    if alerts:
        from api.routers.trigger import _send_telegram_message

        for a in alerts:
            msg = f"🔥 *ALERTE MATCH 0-0 ({a['timing']})* 🔥\n\n"
            msg += f"⚽ {a['match']}\n"
            msg += f"📈 *{a['team']}* domine très fortement"
            if a["type"] == "70":
                msg += " sur la *2ème mi-temps* !\n\n"
            else:
                msg += " sur la *1ère mi-temps* !\n\n"

            msg += "📊 Stats de la période ciblée :\n"
            msg += f"• xG : {round(a['stats']['xg'], 2)}\n"
            msg += f"• Tirs totaux : {a['stats']['total_shots']}\n"
            msg += f"• Tirs cadrés : {a['stats']['shots_on_target']}\n\n"
            msg += "💣 Un but devrait tomber !"

            logger.info(f"🚨 Alerte envoyée pour {a['match']} ({a['timing']})")
            _send_telegram_message(msg)

    return {"status": "ok", "matches_analyzed": len(live_fixtures), "alerts_sent": len(alerts)}


if __name__ == "__main__":
    run_momentum_tracker()
