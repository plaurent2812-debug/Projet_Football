#!/usr/bin/env python3
"""
run_pipeline.py — Orchestrateur du pipeline complet Football IA.

Usage :
  python3 run_pipeline.py          → Pipeline complet (données + analyse)
  python3 run_pipeline.py data     → Seulement la collecte de données
  python3 run_pipeline.py analyze  → Seulement l'analyse (stats + IA)
"""

import sys
import time

from config import get_request_count, logger, reset_request_count


def run_data_pipeline():
    """Collecte toutes les données nécessaires."""
    logger.info("=" * 60)
    logger.info("📊 PHASE 1 : COLLECTE DES DONNÉES")
    logger.info("=" * 60)
    reset_request_count()
    start = time.time()

    # 1. Équipes + Classements + ELO
    logger.info("── Étape 1/5 : Équipes, classements, ELO ──")
    from fetchers.teams import fetch_standings, fetch_teams, init_elo

    fetch_teams()
    fetch_standings()
    init_elo()

    # 2. Matchs à venir (prochaine journée)
    logger.info("── Étape 2/5 : Matchs prochaine journée ──")
    from fetchers.matches import fetch_and_store

    fetch_and_store()

    # 3. Joueurs + Stats saison
    logger.info("── Étape 3/5 : Joueurs + stats saison ──")
    from fetchers.players import fetch_all_players

    fetch_all_players()

    # 4. Historique (matchs terminés + events + lineups + stats)
    logger.info("── Étape 4/5 : Historique des matchs ──")
    from fetchers.history import (
        compute_referee_stats,
        fetch_events_for_fixtures,
        fetch_finished_fixtures,
        fetch_lineups_for_fixtures,
        fetch_team_stats_for_fixtures,
    )

    fixture_ids = fetch_finished_fixtures()
    if fixture_ids:
        fetch_events_for_fixtures(fixture_ids)
        fetch_lineups_for_fixtures(fixture_ids)
        fetch_team_stats_for_fixtures(fixture_ids)
        compute_referee_stats()

    # 5. Contexte (blessures, cotes, H2H, météo) — en parallèle
    logger.info("── Étape 5/5 : Contexte (blessures, cotes, H2H) ──")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from fetchers.context import fetch_h2h, fetch_injuries, fetch_odds, fetch_weather

    fetchers = {
        "injuries": fetch_injuries,
        "odds": fetch_odds,
        "h2h": fetch_h2h,
        "weather": fetch_weather,
    }
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in fetchers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error("Erreur dans fetcher %s: %s", name, e)

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("✅ Données collectées en %.0fs (%d requêtes API)", elapsed, get_request_count())
    logger.info("=" * 60)


def run_analysis():
    """Lance l'analyse statistique + IA."""
    logger.info("=" * 60)
    logger.info("🧠 PHASE 2 : ANALYSE (Stats + IA)")
    logger.info("=" * 60)

    from brain import run_brain

    run_brain()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║          ⚽ FOOTBALL IA — Pipeline v2                   ║")
    logger.info("║   Poisson + ELO + Forme + Repos + Enjeu + Buteur       ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")

    if mode in ("full", "all"):
        run_data_pipeline()
        run_analysis()
    elif mode == "data":
        run_data_pipeline()
    elif mode == "analyze":
        run_analysis()
    else:
        logger.info("Mode inconnu : %s", mode)
        logger.info("Usage : python3 run_pipeline.py [full|data|analyze]")
