#!/usr/bin/env python3
"""
fetchers/fetch_nhl_results.py — Évaluation des prédictions NHL (Top 1).

Récupère les scores réels des matchs terminés via l'API NHL et évalue
la performance des prédictions Top 1 (Buteur, Passeur, Point).
Les résultats sont stockés dans Supabase -> nhl_suivi_algo_clean.
"""

import os
import sys
import time
from datetime import datetime, timedelta

import httpx

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..")))
from src.config import logger, supabase

NHL_API_BOXSCORE = "https://api-web.nhle.com/v1/gamecenter/{}/boxscore"
FINISHED_STATUSES = {"FINAL", "OFF"}


def fetch_boxscore(api_game_id: str) -> dict | None:
    url = NHL_API_BOXSCORE.format(api_game_id)
    try:
        resp = httpx.get(url, timeout=10)
        return resp.json()
    except Exception as e:
        logger.error(f"[NHL] Erreur récupération boxscore {api_game_id}: {e}")
        return None


def extract_actual_stats(boxscore: dict) -> dict:
    """Returns a dict mapping player name to their stats: {"goals": X, "assists": X, "points": X}"""
    stats = {}
    if not boxscore:
        return stats

    try:
        player_types = boxscore.get("playerByGameStats", {})
        for team_key in ["homeTeam", "awayTeam"]:
            team_stats = player_types.get(team_key, {})
            # Only checking skaters (forverds/defense) for goals/assists/points
            skaters = team_stats.get("forwards", []) + team_stats.get("defense", [])

            for player in skaters:
                player_id = str(player.get("playerId", ""))
                name = player.get("name", {}).get("default", "")
                # fallback if playerId is mysteriously missing
                key = player_id if player_id else name.lower()
                if not key:
                    continue

                stats[key] = {
                    "goals": player.get("goals", 0),
                    "assists": player.get("assists", 0),
                    "points": player.get("points", 0),
                    "shots": player.get("sog", 0),  # Boxscore property is 'sog' not 'shots'
                }
    except Exception as e:
        logger.error(f"[NHL] Erreur parsing boxscore: {e}")

    return stats


def evaluate_nhl_predictions(days_back=3):
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Fetch recently completed matches
    try:
        fixtures = (
            supabase.table("nhl_fixtures")
            .select(
                "id, api_fixture_id, date, home_team, away_team, status, home_score, away_score, stats_json"
            )
            .gte("date", start_date)
            .in_("status", ["FINAL", "OFF", "FT"])
            .execute()
            .data
        ) or []
    except Exception as e:
        logger.error(f"[NHL] Erreur récupération des matchs terminés : {e}")
        return

    logger.info(f"[NHL] {len(fixtures)} matchs terminés trouvés depuis {start_date}")

    for fix in fixtures:
        match_str = f"{fix['home_team']} vs {fix['away_team']}"
        api_id = fix.get("api_fixture_id")
        date_str = fix.get("date")[:10] if fix.get("date") else start_date

        # Parse top predictions
        stats_json = fix.get("stats_json") or {}
        top_players_raw = stats_json.get("top_players") or []

        if not top_players_raw:
            logger.info(f"[NHL] Pas de prédictions pour {match_str} (skip)")
            continue

        # Get TOP 1 for each category based on ML probability (with fallback)
        def get_top_1(category_key):
            sorted_players = sorted(
                top_players_raw,
                key=lambda r: r.get(f"ml_{category_key}", r.get(category_key, 0)),
                reverse=True,
            )
            return sorted_players[0] if sorted_players else None

        top1_goal = get_top_1("prob_goal")
        top1_assist = get_top_1("prob_assist")
        top1_point = get_top_1("prob_point")
        top1_shot = get_top_1("prob_shot")

        if not top1_goal and not top1_assist and not top1_point and not top1_shot:
            continue

        logger.info(f"[NHL] Évaluation {match_str}...")

        boxscore = fetch_boxscore(api_id)
        if not boxscore:
            continue

        actual_stats = extract_actual_stats(boxscore)

        # Prepare evaluation rows for Supabase
        evaluations = []

        def add_eval(player_dict, stat_name, pari_name, achieved_key, expected_val=1):
            if not player_dict:
                return

            p_name = player_dict.get("player_name", "")
            p_id = str(player_dict.get("player_id", ""))
            if not p_name:
                return

            if p_id in actual_stats:
                p_stat = actual_stats[p_id]
            else:
                p_stat = actual_stats.get(p_name.lower(), {})

            actual_val = p_stat.get(achieved_key, 0)

            is_winner = actual_val >= expected_val
            resultat = "GAGNÉ" if is_winner else "PERDU"
            ml_prob = player_dict.get(
                f"ml_prob_{stat_name}", player_dict.get(f"prob_{stat_name}", 0)
            )

            # Formating
            evaluations.append(
                {
                    "date": date_str,
                    "match": match_str,
                    "type": "Performance Joueur",
                    "joueur": p_name,
                    "pari": pari_name,
                    "resultat": resultat,
                    "score_reel": str(actual_val),
                    "proba_predite": ml_prob,
                    "python_prob": ml_prob,
                    "cote": 1.0,  # Dummy odds, maybe fetch later if integrated
                    "id_ref": api_id,
                }
            )

        add_eval(top1_goal, "goal", "Buteur (Top 1)", "goals")
        add_eval(top1_assist, "assist", "Passeur (Top 1)", "assists")
        add_eval(top1_point, "point", "Point (Top 1)", "points")
        add_eval(top1_shot, "shot", "Tirs cadrés (Top 1)", "shots", expected_val=3)

        # Insert into DB
        if evaluations:
            try:
                # rename resultat -> résultat for DB column
                for ev in evaluations:
                    ev["résultat"] = ev.pop("resultat")

                # Upsert to avoid duplicates
                supabase.table("nhl_suivi_algo_clean").upsert(
                    evaluations, on_conflict="date,match,type,joueur,pari"
                ).execute()
                logger.info(f"  ✅ Inséré {len(evaluations)} évaluations pour {match_str}")
            except Exception as e:
                logger.error(f"[NHL] Erreur d'insertion dans nhl_suivi_algo_clean : {e}")

        time.sleep(0.5)


if __name__ == "__main__":
    days = 3
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    evaluate_nhl_predictions(days)
