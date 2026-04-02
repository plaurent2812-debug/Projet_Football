"""
worker.py — Cron worker pour Railway (service séparé du web).

Tâches planifiées :
  - Toutes les 5 min  : live scores + events (football + NHL)
  - Toutes les 15 min : màj résultats FT
  - Toutes les heures : fetch nouveaux fixtures
  - Tous les jours 6h : pipeline IA complet (brain)

Usage :
  python worker.py
"""

import time
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("worker")


def job_live() -> None:
    """Toutes les 5 min — scores + events live football + NHL."""
    try:
        from src.fetchers.live import run
        run()
    except Exception as e:
        logger.error(f"[job_live] {e}")


def job_results() -> None:
    """Toutes les 15 min — mise à jour scores FT."""
    try:
        from src.fetchers.results import fetch_and_update_results
        fetch_and_update_results()
    except Exception as e:
        logger.error(f"[job_results] {e}")


def job_matches() -> None:
    """Toutes les heures — fetch nouveaux fixtures."""
    try:
        from src.fetchers.matches import fetch_and_store
        fetch_and_store()
    except Exception as e:
        logger.error(f"[job_matches] {e}")


def job_brain() -> None:
    """Tous les jours à 6h — pipeline IA complet."""
    try:
        from src.brain import run_brain
        run_brain()
    except Exception as e:
        logger.error(f"[job_brain] {e}")


def job_nhl_evaluation() -> None:
    """Tous les jours à 8h — scores NHL + évaluation complète."""
    try:
        from src.fetchers.fetch_nhl_results import evaluate_nhl_predictions
        evaluate_nhl_predictions(days_back=3)
    except Exception as e:
        logger.error(f"[job_nhl_eval] {e}")


def job_football_evaluation() -> None:
    """Tous les jours à 8h30 — évaluation foot + recalibration."""
    try:
        from src.training.evaluate import run_evaluation
        from src.models.calibrate import run_calibration
        run_evaluation()
        run_calibration()
    except Exception as e:
        logger.error(f"[job_football_eval] {e}")


def main() -> None:
    scheduler = BlockingScheduler(timezone="Europe/Paris")

    # Toutes les 5 min
    scheduler.add_job(job_live, CronTrigger(minute="*/5"), id="live", max_instances=1, coalesce=True)

    # Toutes les 15 min
    scheduler.add_job(job_results, CronTrigger(minute="*/15"), id="results", max_instances=1, coalesce=True)

    # Toutes les heures (à la minute 30)
    scheduler.add_job(job_matches, CronTrigger(minute=30), id="matches", max_instances=1, coalesce=True)

    # Tous les jours à 6h00
    scheduler.add_job(job_brain, CronTrigger(hour=6, minute=0), id="brain", max_instances=1, coalesce=True)

    # Tous les jours à 8h00 — évaluation NHL (après matchs de nuit US)
    scheduler.add_job(job_nhl_evaluation, CronTrigger(hour=8, minute=0), id="nhl_eval", max_instances=1, coalesce=True)

    # Tous les jours à 8h30 — évaluation foot + recalibration
    scheduler.add_job(job_football_evaluation, CronTrigger(hour=8, minute=30), id="football_eval", max_instances=1, coalesce=True)

    logger.info("=" * 50)
    logger.info("  ⚙️  Worker démarré")
    logger.info("  - Live scores    : */5 min")
    logger.info("  - Résultats FT   : */15 min")
    logger.info("  - Fixtures       : toutes les heures")
    logger.info("  - Pipeline brain : 6h00 quotidien")
    logger.info("  - NHL évaluation : 8h00 quotidien")
    logger.info("  - Foot éval+calib: 8h30 quotidien")
    logger.info("=" * 50)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker arrêté.")


if __name__ == "__main__":
    main()
