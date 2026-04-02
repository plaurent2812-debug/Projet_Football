#!/usr/bin/env python3
"""
run_pipeline.py — Orchestrateur du pipeline complet Football IA.

Usage :
  python3 run_pipeline.py          → Pipeline complet (données + analyse)
  python3 run_pipeline.py data     → Seulement la collecte de données
  python3 run_pipeline.py analyze  → Seulement l'analyse (stats + IA)
  python3 run_pipeline.py results  → Mise à jour des scores du jour (CRON 15min)
  python3 run_pipeline.py results --date 2025-02-18  → Date spécifique
"""
from __future__ import annotations

import sys
import time

from src.config import get_request_count, logger, reset_request_count


def run_data_pipeline():
    """Collecte toutes les données nécessaires."""
    logger.info("=" * 60)
    logger.info("📊 PHASE 1 : COLLECTE DES DONNÉES")
    logger.info("=" * 60)
    reset_request_count()
    start = time.time()

    # 1. Équipes + Classements + ELO
    logger.info("── Étape 1/5 : Équipes, classements, ELO ──")
    from src.fetchers.teams import fetch_standings, fetch_teams, init_elo

    fetch_teams()
    fetch_standings()
    init_elo()

    # 2. Matchs à venir (prochaine journée)
    logger.info("── Étape 2/5 : Matchs prochaine journée ──")
    from src.fetchers.matches import fetch_and_store

    fetch_and_store()

    # 3. Joueurs + Stats saison
    logger.info("── Étape 3/5 : Joueurs + stats saison ──")
    from src.fetchers.players import fetch_all_players

    fetch_all_players()

    # 4. Historique (matchs terminés + events + lineups + stats)
    logger.info("── Étape 4/5 : Historique des matchs ──")
    from src.fetchers.history import (
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

    from src.fetchers.context import fetch_h2h, fetch_injuries, fetch_odds, fetch_weather

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

    from src.brain import run_brain

    run_brain()


def run_results(date: str | None = None):
    """Met à jour les scores des matchs du jour depuis l'API Football."""
    logger.info("=" * 60)
    logger.info("🔄 PHASE SCORES : Mise à jour des résultats")
    logger.info("=" * 60)

    from src.fetchers.results import fetch_and_update_results

    stats = fetch_and_update_results(date)
    logger.info(
        "✅ Scores : %d mis à jour | %d ignorés | %d erreurs",
        stats["updated"],
        stats["skipped"],
        stats["errors"],
    )


def run_monitoring_alerts():
    """Run post-pipeline monitoring checks and send Telegram alerts."""
    logger.info("=" * 60)
    logger.info("🔍 PHASE MONITORING : Vérification qualité")
    logger.info("=" * 60)

    try:
        from src.config import supabase
        from src.monitoring.alerting import check_and_alert
        from src.notifications import send_telegram

        alerts = check_and_alert(supabase, send_telegram_fn=send_telegram)
        if alerts:
            logger.warning("Monitoring: %d alerte(s) envoyée(s)", len(alerts))
        else:
            logger.info("✅ Monitoring: aucune alerte")
    except Exception as e:
        logger.error("Erreur monitoring: %s", e)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    # Support --date pour le mode results
    date_arg = None
    for i, arg in enumerate(sys.argv[2:]):
        if arg == "--date" and i + 1 < len(sys.argv) - 2:
            date_arg = sys.argv[i + 3]
        elif arg.startswith("20"):
            date_arg = arg

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║          ⚽ FOOTBALL IA — Pipeline v2                   ║")
    logger.info("║   Poisson + ELO + Forme + Repos + Enjeu + Buteur       ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")

    if mode in ("full", "all"):
        run_data_pipeline()
        run_analysis()
        run_monitoring_alerts()
    elif mode == "data":
        run_data_pipeline()
    elif mode == "analyze":
        run_analysis()
    elif mode == "results":
        run_results(date_arg)
    else:
        logger.info("Mode inconnu : %s", mode)
        logger.info("Usage : python3 run_pipeline.py [full|data|analyze|results]")
        logger.info("        python3 run_pipeline.py results --date 2025-02-18")
