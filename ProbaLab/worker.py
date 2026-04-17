"""
worker.py — Cron worker pour Railway (service séparé du web).

Schedule optimisé pour le Smart Betting Assistant (value bets).
Flux : Data → Odds → Predict → Edge → Picks → Alertes.

Toutes les heures sont en Europe/Paris.

Usage :
  python worker.py
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("worker")


# ═══════════════════════════════════════════════════════════════
#  JOBS CONTINUS (haute fréquence)
# ═══════════════════════════════════════════════════════════════


def job_live() -> None:
    """*/5 min — scores + events live football + NHL.

    Gating intelligent : football 11h-23h UTC, NHL 16h-08h UTC.
    En dehors de ces fenêtres, le job ne fait rien (économie API).
    """
    try:
        hour = datetime.now(timezone.utc).hour
        football_active = 9 <= hour <= 23
        nhl_active = hour >= 16 or hour <= 8
        if not football_active and not nhl_active:
            return
        from src.fetchers.live import run
        run()
    except Exception:
        logger.exception("[job_live] Error")


def job_results() -> None:
    """*/15 min — mise à jour scores FT."""
    try:
        from src.fetchers.results import fetch_and_update_results
        fetch_and_update_results()
    except Exception:
        logger.exception("[job_results] Error")


def job_fixtures() -> None:
    """Toutes les heures (:30) — fetch nouvelles fixtures."""
    try:
        from src.fetchers.matches import fetch_and_store
        fetch_and_store()
    except Exception:
        logger.exception("[job_fixtures] Error")


# ═══════════════════════════════════════════════════════════════
#  JOBS QUOTIDIENS — NUIT / MATIN
# ═══════════════════════════════════════════════════════════════


def job_resolve_bets() -> None:
    """06:00 — résolution des paris PENDING (7 jours glissants).

    Résout les best_bets football + NHL via l'API interne.
    """
    try:
        import os
        from datetime import timedelta

        import httpx

        cron_secret = os.getenv("CRON_SECRET", "")
        # En prod Railway, le web service est accessible en interne
        api_url = os.getenv("API_BASE_URL", "https://api.probalab.net")
        headers = {"Authorization": f"Bearer {cron_secret}"}

        resolved = 0
        for days_back in range(7):
            date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
            for sport in ("football", "nhl"):
                try:
                    httpx.post(
                        f"{api_url}/api/best-bets/resolve",
                        json={"date": date, "sport": sport},
                        headers=headers,
                        timeout=30,
                    )
                    resolved += 1
                except Exception:
                    logger.warning("[job_resolve_bets] Failed %s/%s", date, sport)

        logger.info("[job_resolve_bets] Résolution terminée (%d appels)", resolved)
    except Exception:
        logger.exception("[job_resolve_bets] Error")


def job_data_pipeline() -> None:
    """07:00 — collecte complète des données (équipes, classements, blessures, météo)."""
    try:
        from run_pipeline import run_data_pipeline
        run_data_pipeline()
        logger.info("[job_data_pipeline] Data pipeline terminé")
    except Exception:
        logger.exception("[job_data_pipeline] Error")


def job_fetch_odds() -> None:
    """07:45 — fetch cotes fraîches (Bet365) AVANT le brain.

    Critique : le brain a besoin d'odds à jour pour calculer
    les edges correctement. Doit tourner AVANT job_brain.
    """
    try:
        from src.fetchers.context import fetch_odds
        fetch_odds()
        logger.info("[job_fetch_odds] Cotes fraîches récupérées")
    except Exception:
        logger.exception("[job_fetch_odds] Error")


def job_nhl_evaluation() -> None:
    """08:00 — évaluation NHL (après matchs de nuit US)."""
    try:
        from src.fetchers.fetch_nhl_results import evaluate_nhl_predictions
        evaluate_nhl_predictions(days_back=3)
    except Exception:
        logger.exception("[job_nhl_eval] Error")


def job_nhl_pipeline() -> None:
    """16:00 & 23:00 — pipeline NHL complet (data + ML + IA).

    Tourne 2 fois par jour :
      - 16:00 → première analyse du matin, alimente job_nhl_picks (17:00)
      - 23:00 → re-run avec compos officielles pour ajuster les probas
               avant les matchs de soirée US (début ~01:00 Paris).

    Écrit dans nhl_fixtures + nhl_data_lake.
    """
    try:
        from src.fetchers.nhl_pipeline import run_nhl_pipeline
        run_nhl_pipeline()
        logger.info("[job_nhl_pipeline] Pipeline NHL terminé")
    except Exception:
        logger.exception("[job_nhl_pipeline] Error")


def job_nhl_fetch_odds() -> None:
    """16:15 & 23:15 — fetch cotes NHL (après le pipeline).

    Doit tourner APRÈS job_nhl_pipeline : fetch_nhl_odds update
    odds_json sur les lignes existantes de nhl_fixtures, donc les
    fixtures doivent exister avant.

    Critique : job_nhl_picks lit odds_json pour calculer l'EV.
    """
    try:
        from src.fetchers.fetch_nhl_odds import fetch_nhl_odds
        fetch_nhl_odds()
        logger.info("[job_nhl_fetch_odds] Cotes NHL récupérées")
    except Exception:
        logger.exception("[job_nhl_fetch_odds] Error")


def job_football_evaluation() -> None:
    """08:30 — évaluation foot + recalibration + draw factor audit."""
    try:
        from src.models.calibrate import recalibrate_draw_factors, run_calibration
        from src.training.evaluate import run_evaluation
        run_evaluation()
        run_calibration()
        recalibrate_draw_factors(months=6)
    except Exception:
        logger.exception("[job_football_eval] Error")


def job_drift_check() -> None:
    """09:00 — détection drift Brier 7j vs 30j."""
    try:
        from src.monitoring.drift_detector import check_drift
        result = check_drift()
        if result.get("drifted"):
            logger.warning(
                "[job_drift_check] Drift détecté — Brier 7j=%s, 30j=%s, delta=%s",
                result["brier_7d"], result["brier_30d"], result["delta"],
            )
        else:
            logger.info(
                "[job_drift_check] Pas de drift — Brier 7j=%s, 30j=%s",
                result["brier_7d"], result["brier_30d"],
            )
    except Exception:
        logger.exception("[job_drift_check] Error")


def job_run_monitoring_alerts() -> None:
    """08:30 UTC — Brier check + drift + persistance model_health_log."""
    from run_pipeline import run_monitoring_alerts
    try:
        run_monitoring_alerts()
    except Exception as e:
        logger.exception("job_run_monitoring_alerts failed: %s", e)


# ═══════════════════════════════════════════════════════════════
#  JOBS QUOTIDIENS — PRÉDICTIONS + VALUE BETS
# ═══════════════════════════════════════════════════════════════


def job_brain() -> None:
    """10:00 — pipeline IA complet (Poisson + ELO + ML + Gemini).

    Tourne APRÈS les odds fraîches (07:45) pour que les prédictions
    intègrent les cotes du marché dans le contexte ML.
    """
    try:
        from src.brain import run_brain
        run_brain()
    except Exception:
        logger.exception("[job_brain] Error")


def job_football_picks() -> None:
    """12:00 — génération value bets football (singles + double + fun).

    Calcule les edges (modèle vs bookmaker) et génère les picks.
    Tourne APRÈS le brain (10:00) pour avoir des prédictions fraîches.
    """
    try:
        from src.ticket_generator import generate_football_picks
        result = generate_football_picks()
        logger.info(
            "[job_football_picks] %s: %d singles, %d double, %d fun",
            result["date"], result["singles"], result["double"], result["fun"],
        )
    except Exception:
        logger.exception("[job_football_picks] Error")


def job_nhl_picks() -> None:
    """17:00 — génération value bets NHL (singles + double + fun).

    Les matchs NHL sont en soirée US (19h-22h ET = 01h-04h Paris).
    Les odds sont disponibles l'après-midi pour les matchs du soir.
    """
    try:
        from src.ticket_generator import generate_nhl_picks
        result = generate_nhl_picks()
        logger.info(
            "[job_nhl_picks] %s: %d singles, %d double, %d fun",
            result["date"], result["singles"], result["double"], result["fun"],
        )
    except Exception:
        logger.exception("[job_nhl_picks] Error")


# ═══════════════════════════════════════════════════════════════
#  JOBS HEBDOMADAIRES
# ═══════════════════════════════════════════════════════════════


def job_weekly_retrain() -> None:
    """Dimanche 03:00 — retraining complet des modèles ML (foot + NHL)."""
    try:
        from src.training.build_data import run as build_data_run
        from src.training.evaluate import run_evaluation
        from src.training.train import run as train_run

        logger.info("[job_weekly_retrain] Étape 1/3 — rebuild features...")
        build_data_run(rebuild=False)

        logger.info("[job_weekly_retrain] Étape 2/3 — entraînement des modèles...")
        train_run()

        logger.info("[job_weekly_retrain] Étape 3/3 — évaluation post-entraînement...")
        run_evaluation()

        logger.info("[job_weekly_retrain] Retraining hebdomadaire terminé.")
    except Exception:
        logger.exception("[job_weekly_retrain] Error")


# ═══════════════════════════════════════════════════════════════
#  MAIN — SCHEDULE
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    scheduler = BlockingScheduler(timezone="Europe/Paris")

    # ── Continu ─────────────────────────────────────────────
    scheduler.add_job(job_live, CronTrigger(minute="*/5"),
                      id="live", max_instances=1, coalesce=True)
    scheduler.add_job(job_results, CronTrigger(minute="*/15"),
                      id="results", max_instances=1, coalesce=True)
    scheduler.add_job(job_fixtures, CronTrigger(minute=30),
                      id="fixtures", max_instances=1, coalesce=True)

    # ── Nuit / Matin ────────────────────────────────────────
    scheduler.add_job(job_resolve_bets, CronTrigger(hour=6, minute=0),
                      id="resolve_bets", max_instances=1, coalesce=True)
    scheduler.add_job(job_data_pipeline, CronTrigger(hour=7, minute=0),
                      id="data_pipeline", max_instances=1, coalesce=True)
    scheduler.add_job(job_fetch_odds, CronTrigger(hour=7, minute=45),
                      id="fetch_odds", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_evaluation, CronTrigger(hour=8, minute=0),
                      id="nhl_eval", max_instances=1, coalesce=True)
    scheduler.add_job(job_football_evaluation, CronTrigger(hour=8, minute=30),
                      id="football_eval", max_instances=1, coalesce=True)
    scheduler.add_job(
        job_run_monitoring_alerts,
        CronTrigger(hour=8, minute=30, timezone="UTC"),
        id="monitoring_alerts_daily",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(job_drift_check, CronTrigger(hour=9, minute=0),
                      id="drift_check", max_instances=1, coalesce=True)

    # ── Prédictions + Value Bets ────────────────────────────
    scheduler.add_job(job_brain, CronTrigger(hour=10, minute=0),
                      id="brain", max_instances=1, coalesce=True)
    scheduler.add_job(job_football_picks, CronTrigger(hour=12, minute=0),
                      id="football_picks", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_pipeline, CronTrigger(hour=16, minute=0),
                      id="nhl_pipeline_afternoon", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_fetch_odds, CronTrigger(hour=16, minute=15),
                      id="nhl_fetch_odds_afternoon", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_picks, CronTrigger(hour=17, minute=0),
                      id="nhl_picks", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_pipeline, CronTrigger(hour=23, minute=0),
                      id="nhl_pipeline_lineups", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_fetch_odds, CronTrigger(hour=23, minute=15),
                      id="nhl_fetch_odds_lineups", max_instances=1, coalesce=True)
    scheduler.add_job(job_nhl_picks, CronTrigger(hour=23, minute=30),
                      id="nhl_picks_lineups", max_instances=1, coalesce=True)

    # ── Hebdomadaire ────────────────────────────────────────
    scheduler.add_job(job_weekly_retrain, CronTrigger(day_of_week="sun", hour=3, minute=0),
                      id="weekly_retrain", max_instances=1, coalesce=True)

    logger.info("=" * 56)
    logger.info("  ⚡ Smart Betting Assistant — Worker démarré")
    logger.info("  ─────────────────────────────────────────")
    logger.info("  CONTINU")
    logger.info("    */5 min  Live scores (gating intelligent)")
    logger.info("    */15 min Résultats FT")
    logger.info("    :30      Nouvelles fixtures")
    logger.info("  QUOTIDIEN")
    logger.info("    06:00    Résolution paris (7j)")
    logger.info("    07:00    Data pipeline complet")
    logger.info("    07:45    Fetch cotes fraîches")
    logger.info("    08:00    Évaluation NHL")
    logger.info("    08:30    Évaluation foot + calibration")
    logger.info("    08:30 UTC Monitoring alerts + persistance model_health_log")
    logger.info("    09:00    Drift detection")
    logger.info("    10:00    Brain IA (prédictions)")
    logger.info("    12:00    Value Bets football")
    logger.info("    16:00    Pipeline NHL (analyse + probas)")
    logger.info("    16:15    Fetch cotes NHL")
    logger.info("    17:00    Value Bets NHL")
    logger.info("    23:00    Pipeline NHL (re-run avec compos officielles)")
    logger.info("    23:15    Fetch cotes NHL (refresh)")
    logger.info("    23:30    Value Bets NHL (re-run post-compos)")
    logger.info("  HEBDOMADAIRE")
    logger.info("    Dim 03:00  ML retrain complet")
    logger.info("=" * 56)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker arrêté.")


if __name__ == "__main__":
    main()
