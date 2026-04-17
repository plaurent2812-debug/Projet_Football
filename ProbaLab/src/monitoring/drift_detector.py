"""
drift_detector.py — Detecte la degradation du modele et declenche un retrain.

Logique :
  - Compare le Brier score sur les 7 derniers jours vs les 30 derniers jours
  - Si Brier_7j > Brier_30j + DRIFT_THRESHOLD -> alerte + retrain
  - Envoie une notification Telegram via alerting.py
"""

from __future__ import annotations

import html as _html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import supabase

logger = logging.getLogger("football_ia")

# Seuil de drift : si Brier 7j depasse Brier 30j de plus de cette valeur
DRIFT_THRESHOLD = 0.02


def _load_results_since(cutoff: datetime) -> list[dict]:
    """Charge les prediction_results depuis une date donnee (UTC)."""
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return (
        supabase.table("prediction_results")
        .select("pred_home,pred_draw,pred_away,actual_result,created_at")
        .gte("created_at", cutoff_str)
        .execute()
        .data
        or []
    )


def _compute_brier_1x2(results: list[dict]) -> float | None:
    """Calcule le Brier score multiclasse 1X2 sur une liste de resultats.

    Formule : BS = (1/N) * sum((p_h - y_h)^2 + (p_d - y_d)^2 + (p_a - y_a)^2)
    Retourne None si aucune donnee valide.
    """
    scores: list[float] = []
    for r in results:
        pred_h = r.get("pred_home")
        pred_d = r.get("pred_draw")
        pred_a = r.get("pred_away")
        actual = r.get("actual_result")

        if pred_h is None or pred_d is None or pred_a is None or actual is None:
            continue

        p_h = pred_h / 100.0
        p_d = pred_d / 100.0
        p_a = pred_a / 100.0

        y_h = 1.0 if actual == "H" else 0.0
        y_d = 1.0 if actual == "D" else 0.0
        y_a = 1.0 if actual == "A" else 0.0

        bs = (p_h - y_h) ** 2 + (p_d - y_d) ** 2 + (p_a - y_a) ** 2
        scores.append(bs)

    if not scores:
        return None

    return sum(scores) / len(scores)


def _send_drift_alert(brier_7d: float, brier_30d: float, delta: float) -> None:
    """Envoie une alerte Telegram si le drift est detecte."""
    try:
        from src.notifications import send_telegram
    except Exception:
        send_telegram = None  # type: ignore[assignment]

    msg = (
        "\u26a0\ufe0f <b>DRIFT DETECTE — Degradation modele ML</b>\n\n"
        f"Brier 7j  : <b>{_html.escape(f'{brier_7d:.4f}')}</b>\n"
        f"Brier 30j : {_html.escape(f'{brier_30d:.4f}')}\n"
        f"Delta     : <b>{_html.escape(f'+{delta:.4f}')}</b> "
        f"(seuil {_html.escape(f'{DRIFT_THRESHOLD:.2f}')})\n\n"
        "Le retraining hebdomadaire sera anticipe."
    )

    logger.warning(
        "[drift_detector] Drift detecte — Brier 7j=%.4f vs 30j=%.4f (delta=+%.4f)",
        brier_7d,
        brier_30d,
        delta,
    )

    if send_telegram:
        try:
            send_telegram(msg)
        except Exception as e:
            logger.error("[drift_detector] Echec envoi Telegram: %s", e)
    else:
        logger.warning("[drift_detector] Telegram non configure — alerte loggee uniquement")


def check_drift() -> dict[str, Any]:
    """Compare le Brier score sur 7j vs 30j et signale le drift si detecte.

    Returns:
        dict avec les cles :
          - drifted (bool)
          - brier_7d (float | None)
          - brier_30d (float | None)
          - delta (float | None)
    """
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    logger.info("[drift_detector] Chargement des resultats des 7 et 30 derniers jours...")

    results_7d = _load_results_since(cutoff_7d)
    results_30d = _load_results_since(cutoff_30d)

    logger.info(
        "[drift_detector] %d resultats sur 7j, %d sur 30j",
        len(results_7d),
        len(results_30d),
    )

    brier_7d = _compute_brier_1x2(results_7d)
    brier_30d = _compute_brier_1x2(results_30d)

    if brier_7d is None or brier_30d is None:
        logger.info(
            "[drift_detector] Donnees insuffisantes (7j=%s, 30j=%s) — drift non evalue",
            brier_7d,
            brier_30d,
        )
        return {
            "drifted": False,
            "brier_7d": brier_7d,
            "brier_30d": brier_30d,
            "delta": None,
        }

    delta = brier_7d - brier_30d
    drifted = delta > DRIFT_THRESHOLD

    logger.info(
        "[drift_detector] Brier 7j=%.4f | Brier 30j=%.4f | delta=%.4f | seuil=%.2f | drift=%s",
        brier_7d,
        brier_30d,
        delta,
        DRIFT_THRESHOLD,
        drifted,
    )

    if drifted:
        _send_drift_alert(brier_7d, brier_30d, delta)

    return {
        "drifted": drifted,
        "brier_7d": round(brier_7d, 4),
        "brier_30d": round(brier_30d, 4),
        "delta": round(delta, 4),
    }


if __name__ == "__main__":
    result = check_drift()
    logger.info("Drift check result: %s", result)
