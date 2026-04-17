from __future__ import annotations

"""
fetch_nhl_results.py — Évaluation complète des prédictions NHL.

Refonte mars 2026 :
  - Évalue TOUS les joueurs prédits (pas seulement Top 1)
  - Branche les vraies cotes depuis nhl_odds (pas de cote=1.0 hardcodée)
  - Appelle d'abord update_nhl_results pour s'assurer que les scores sont à jour
  - Calcule Brier score par marché

Workflow :
  1. Met à jour les scores finaux (appelle update_nhl_fixture_results)
  2. Récupère les matchs terminés avec prédictions
  3. Récupère les boxscores via NHL API
  4. Évalue chaque joueur prédit vs résultat réel
  5. Matche les cotes depuis nhl_odds
  6. Stocke dans nhl_suivi_algo_clean
  7. Affiche les métriques

Usage :
    python -m src.fetchers.fetch_nhl_results [days_back]
"""
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

from src.config import logger, supabase
from src.fetchers.update_nhl_results import update_nhl_fixture_results

NHL_API_BOXSCORE = "https://api-web.nhle.com/v1/gamecenter/{}/boxscore"
from src.nhl.constants import NHL_FINISHED_STATUSES as FINISHED_STATUSES

# Markets: (stat_name, pari_label, boxscore_key, threshold)
MARKETS = [
    ("goal", "Buteur", "goals", 1),
    ("assist", "Passeur", "assists", 1),
    ("point", "Point", "points", 1),
    ("shot", "Tirs 3+", "shots", 3),
]


def fetch_boxscore(api_game_id: str) -> dict | None:
    url = NHL_API_BOXSCORE.format(api_game_id)
    try:
        resp = httpx.get(url, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        logger.error(f"[NHL] Erreur boxscore {api_game_id}: {e}")
        return None


def extract_actual_stats(boxscore: dict) -> dict:
    """Returns {player_id: {goals, assists, points, shots}, player_name_lower: same}"""
    stats = {}
    if not boxscore:
        return stats

    try:
        player_types = boxscore.get("playerByGameStats", {})
        for team_key in ["homeTeam", "awayTeam"]:
            team_stats = player_types.get(team_key, {})
            skaters = team_stats.get("forwards", []) + team_stats.get("defense", [])
            for player in skaters:
                player_id = str(player.get("playerId", ""))
                name = player.get("name", {}).get("default", "")
                row = {
                    "goals": player.get("goals", 0),
                    "assists": player.get("assists", 0),
                    "points": player.get("points", 0),
                    "shots": player.get("sog", 0),
                }
                if player_id:
                    stats[player_id] = row
                if name:
                    stats[name.lower()] = row
    except Exception as e:
        logger.error(f"[NHL] Erreur parsing boxscore: {e}")

    return stats


def _load_odds_for_date(game_date: str) -> dict:
    """Load odds from nhl_odds table, keyed by player_name.lower().

    Returns: {player_name_lower: best_over_odds}
    """
    try:
        rows = (
            supabase.table("nhl_odds")
            .select("player_name, over_odds, bookmaker")
            .eq("game_date", game_date)
            .execute()
            .data
        ) or []
    except Exception:
        return {}

    # Keep best (lowest) over odds per player (most favorable for the bettor)
    odds_map: dict[str, float] = {}
    for r in rows:
        name = (r.get("player_name") or "").lower().strip()
        price = r.get("over_odds")
        if not name or not price:
            continue
        price = float(price)
        if name not in odds_map or price < odds_map[name]:
            odds_map[name] = price

    return odds_map


def evaluate_nhl_predictions(days_back: int = 3) -> dict:
    """Full evaluation of all NHL player predictions."""
    logger.info("=" * 60)
    logger.info("  🏒 ÉVALUATION DES PRÉDICTIONS NHL")
    logger.info("=" * 60)

    # Step 0: Update fixture scores first
    update_nhl_fixture_results(days_back)

    today = datetime.now(timezone.utc)
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Step 1: Fetch completed fixtures
    try:
        fixtures = (
            supabase.table("nhl_fixtures")
            .select(
                "id, api_fixture_id, date, home_team, away_team, status, home_score, away_score, stats_json"
            )
            .gte("date", f"{start_date}T00:00:00Z")
            .in_("status", list(FINISHED_STATUSES))
            .execute()
            .data
        ) or []
    except Exception as e:
        logger.error(f"[NHL] Erreur récupération matchs terminés: {e}")
        return {"ok": False, "error": str(e)}

    logger.info(f"  {len(fixtures)} matchs terminés depuis {start_date}")

    # Step 2: Check which are already evaluated
    try:
        already = (
            supabase.table("nhl_suivi_algo_clean")
            .select("date, match")
            .gte("date", start_date)
            .execute()
            .data
        ) or []
        already_keys = {(r["date"], r["match"]) for r in already}
    except Exception:
        already_keys = set()

    total_evals = 0
    total_wins = 0
    total_bets = 0
    stats_by_market: dict[str, dict] = {}

    for fix in fixtures:
        match_str = f"{fix['home_team']} vs {fix['away_team']}"
        api_id = fix.get("api_fixture_id")
        date_str = fix.get("date", "")[:10]

        stats_json = fix.get("stats_json") or {}
        top_players = stats_json.get("top_players") or []
        if not top_players:
            continue

        # Skip if already evaluated
        if (date_str, match_str) in already_keys:
            continue

        # Fetch boxscore
        boxscore = fetch_boxscore(api_id)
        if not boxscore:
            continue

        actual_stats = extract_actual_stats(boxscore)
        if not actual_stats:
            continue

        # Load odds for this date
        odds_map = _load_odds_for_date(date_str)

        logger.info(f"  Évaluation {match_str} ({len(top_players)} joueurs)...")

        evaluations = []
        match_wins = 0
        match_total = 0

        for player in top_players:
            p_name = player.get("player_name", "")
            p_id = str(player.get("player_id", ""))
            if not p_name:
                continue

            # Find actual stats
            p_stat = actual_stats.get(p_id) or actual_stats.get(p_name.lower(), {})
            if not p_stat:
                continue

            # Look up odds for this player
            player_odds = odds_map.get(p_name.lower(), 0)

            for stat_name, pari_label, box_key, threshold in MARKETS:
                # Get predicted probability
                ml_prob = player.get(f"ml_prob_{stat_name}")
                heur_prob = player.get(f"prob_{stat_name}")
                prob = ml_prob if ml_prob is not None else heur_prob
                if prob is None or prob <= 0:
                    continue

                actual_val = p_stat.get(box_key, 0)
                is_winner = actual_val >= threshold
                resultat = "GAGNÉ" if is_winner else "PERDU"

                # Use real odds for point market, 0 otherwise
                cote = player_odds if stat_name == "point" and player_odds > 0 else 0

                evaluations.append(
                    {
                        "date": date_str,
                        "match": match_str,
                        "type": "Performance Joueur",
                        "joueur": p_name,
                        "pari": pari_label,
                        "résultat": resultat,
                        "score_reel": str(actual_val),
                        "proba_predite": round(float(prob), 1),
                        "python_prob": round(float(prob), 1),
                        "model_version": "v2",
                        "cote": round(cote, 3) if cote else None,
                        "id_ref": str(api_id),
                    }
                )

                match_total += 1
                if is_winner:
                    match_wins += 1

                # Track by market
                if pari_label not in stats_by_market:
                    stats_by_market[pari_label] = {"wins": 0, "total": 0, "brier_sum": 0}
                stats_by_market[pari_label]["total"] += 1
                if is_winner:
                    stats_by_market[pari_label]["wins"] += 1
                # Brier: (prob/100 - outcome)^2
                outcome = 1.0 if is_winner else 0.0
                stats_by_market[pari_label]["brier_sum"] += (prob / 100 - outcome) ** 2

        # Insert evaluations
        if evaluations:
            # Batch insert (upsert by unique constraint)
            for batch_start in range(0, len(evaluations), 100):
                batch = evaluations[batch_start : batch_start + 100]
                try:
                    supabase.table("nhl_suivi_algo_clean").upsert(
                        batch, on_conflict="date,match,type,joueur,pari"
                    ).execute()
                except Exception as e:
                    logger.error(f"  ⚠️ Erreur insertion: {e}")

            total_evals += len(evaluations)
            total_wins += match_wins
            total_bets += match_total
            pct = round(match_wins / match_total * 100, 1) if match_total > 0 else 0
            logger.info(f"    {match_wins}/{match_total} hits ({pct}%) — {len(evaluations)} lignes")

        time.sleep(0.5)

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  📊 RÉSUMÉ : {total_evals} évaluations, {total_wins}/{total_bets} hits")
    logger.info("=" * 60)

    if total_bets > 0:
        logger.info(f"  Global : {round(total_wins / total_bets * 100, 1)}%")

    for market, data in sorted(stats_by_market.items()):
        n = data["total"]
        w = data["wins"]
        pct = round(w / n * 100, 1) if n > 0 else 0
        brier = round(data["brier_sum"] / n, 4) if n > 0 else 0
        logger.info(f"  {market:20s} : {pct:5.1f}% ({w}/{n})  Brier={brier:.4f}")

    return {
        "ok": True,
        "fixtures_evaluated": len(fixtures),
        "total_evaluations": total_evals,
        "total_wins": total_wins,
        "total_bets": total_bets,
        "by_market": stats_by_market,
    }


if __name__ == "__main__":
    days = 3
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    evaluate_nhl_predictions(days)
