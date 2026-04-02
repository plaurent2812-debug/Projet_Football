from __future__ import annotations

"""
Module de calibration des probabilités - Refonte v3.

Implémente :
- Isotonic Regression (non-paramétrique, s'adapte aux données)
- Platt Scaling (régression logistique, robuste sur petits datasets)
- Fallback linéaire (ratio moyen, quand très peu de données)
- Diagnostics détaillés par marché

Le calibrateur choisit automatiquement la meilleure méthode
en fonction de la quantité de données disponibles.
"""

import math
import re
from typing import Any

import numpy as np

# Imports conditionnels pour sklearn
try:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# =============================================================================
# 1. CALIBRATION COEFFICIENTS
# =============================================================================


class CalibrationCoeffs:
    """Stocke les coefficients de calibration pour un marché."""

    def __init__(
        self,
        coef_a: float = 1.0,
        coef_b: float = 0.0,
        accuracy: float = 0.0,
        method: str = "identity",
        n_samples: int = 0,
        brier_before: float = 0.0,
        brier_after: float = 0.0,
    ):
        self.coef_a = coef_a
        self.coef_b = coef_b
        self.global_accuracy = accuracy
        self.method = method
        self.n_samples = n_samples
        self.brier_before = brier_before
        self.brier_after = brier_after
        # Pour Isotonic Regression
        self._isotonic_model = None
        # Pour Platt Scaling
        self._platt_model = None

    def calibrate(self, raw_prob: float) -> float:
        """Applique la calibration à une probabilité brute."""
        if self.method == "isotonic" and self._isotonic_model is not None:
            # Isotonic Regression
            prob = float(self._isotonic_model.predict([raw_prob])[0])
        elif self.method == "platt" and self._platt_model is not None:
            # Platt Scaling (logistic regression)
            logit = np.array([[raw_prob]])
            prob = float(self._platt_model.predict_proba(logit)[0, 1])
        else:
            # Fallback linéaire
            prob = self.coef_a * raw_prob + self.coef_b

        return max(0.01, min(0.99, prob))


# =============================================================================
# 2. DEFAULT MARKETS
# =============================================================================

DEFAULT_MARKETS = ("GOAL", "SHOT", "POINT", "WINNER", "ASSIST")

# Calibrations actives (globales, mises à jour par analyze_history)
calibrations: dict[str, CalibrationCoeffs] = {m: CalibrationCoeffs() for m in DEFAULT_MARKETS}


# =============================================================================
# 3. MARKET DETECTION
# =============================================================================


def _normalize_market_from_pari(pari: str) -> str:
    """Normalise le type de pari vers un marché standard."""
    p = pari.upper()
    if "POINT" in p:
        return "POINT"
    if any(w in p for w in ("BUTEUR", "BUT", "GOAL")):
        return "GOAL"
    if any(w in p for w in ("PASSEUR", "ASSIST", "PASSE")):
        return "ASSIST"
    if any(w in p for w in ("TIR", "SHOT")):
        return "SHOT"
    if any(w in p for w in ("VAINQUEUR", "WINNER", "VICTOIRE")):
        return "WINNER"
    return "UNKNOWN"


def _infer_probability_from_pari(pari: str) -> float:
    """Infère une probabilité estimée à partir du type de pari."""
    p = pari.upper()
    if "POINT" in p:
        return 0.55
    if any(w in p for w in ("BUTEUR", "BUT", "GOAL")):
        return 0.30
    if any(w in p for w in ("PASSEUR", "ASSIST", "PASSE")):
        return 0.40
    if any(w in p for w in ("TIR", "SHOT")):
        m = re.search(r"(\d+)\+?\s*TIR", p)
        if m:
            line = int(m.group(1))
            return {1: 0.75, 2: 0.65, 3: 0.50, 4: 0.35}.get(line, 0.25)
        return 0.50
    if any(w in p for w in ("VAINQUEUR", "WINNER", "VICTOIRE")):
        return 0.55
    return 0.50


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit une valeur en float de manière sécurisée."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else default
    if isinstance(value, str):
        cleaned = value.strip()
        bad = {"", "EMPTY", "IA: MISS", "IA:MISS", "OK", "N/A", "NULL", "UNDEFINED"}
        if cleaned.upper() in bad or cleaned.upper().startswith("IA:"):
            return default
        try:
            if cleaned.endswith("%"):
                return float(cleaned[:-1]) / 100.0
            return float(cleaned)
        except ValueError:
            return default
    return default


# =============================================================================
# 4. BRIER SCORE HELPER
# =============================================================================


def _brier_score(probs: list[float], actuals: list[float]) -> float:
    """Calcule le Brier Score (plus bas = meilleur)."""
    if not probs:
        return 1.0
    return sum((p - a) ** 2 for p, a in zip(probs, actuals)) / len(probs)


# =============================================================================
# 5. CALIBRATION METHODS
# =============================================================================


def _fit_isotonic(probs: np.ndarray, actuals: np.ndarray) -> IsotonicRegression | None:
    """Entraîne une Isotonic Regression."""
    if not SKLEARN_AVAILABLE:
        return None
    try:
        ir = IsotonicRegression(y_min=0.01, y_max=0.99, out_of_bounds="clip")
        ir.fit(probs, actuals)
        return ir
    except Exception:
        return None


def _fit_platt(probs: np.ndarray, actuals: np.ndarray) -> LogisticRegression | None:
    """Entraîne un Platt Scaling (régression logistique sur les probas)."""
    if not SKLEARN_AVAILABLE:
        return None
    try:
        lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
        X = probs.reshape(-1, 1)
        lr.fit(X, actuals)
        return lr
    except Exception:
        return None


def _fit_linear(probs: list[float], actuals: list[float]) -> tuple[float, float]:
    """Calibration linéaire simple : ratio moyen + offset."""
    mean_pred = np.mean(probs) if probs else 0.5
    mean_actual = np.mean(actuals) if actuals else 0.5

    if mean_pred < 1e-6:
        return 1.0, 0.0

    coef_a = mean_actual / mean_pred
    coef_a = max(0.5, min(2.0, coef_a))

    # Calcul de l'offset pour mieux caler les extrêmes
    # On minimise MSE: a*p + b ≈ actual
    # b = mean_actual - a * mean_pred
    coef_b = mean_actual - coef_a * mean_pred
    coef_b = max(-0.2, min(0.2, coef_b))

    return round(coef_a, 4), round(coef_b, 4)


# =============================================================================
# 6. MAIN ANALYSIS
# =============================================================================


def analyze_history(
    history: list[dict[str, Any]],
    model_training_date: str | None = None,
) -> dict[str, CalibrationCoeffs]:
    """
    Analyse l'historique SUIVI_ALGO et calibre les probabilités.

    Stratégie :
    - >= 50 données par marché → Isotonic Regression
    - >= 20 données → Platt Scaling
    - >= 5 données → Calibration linéaire
    - < 5 → Identité (pas de calibration)

    Si model_training_date est fourni, seules les données APRÈS cette date
    sont utilisées pour la calibration (évite contamination train/calibration).
    Si la calibration dégrade le Brier score, on garde l'identité.
    """
    if not history or len(history) < 10:
        # print(f"   ⚠️ Calibration: pas assez de données ({len(history) if history else 0})")
        return {}

    # Filtrage temporel si model_training_date fourni
    if model_training_date:
        before_count = len(history)
        history = [r for r in history if str(r.get("date", "")) > model_training_date]
        # print(f"   📅 Filtrage temporel: {before_count} → {len(history)} (après {model_training_date})")
        if len(history) < 10:
            # print(f"   ⚠️ Pas assez de données post-entraînement pour calibrer")
            return {}

    # Grouper par marché
    by_market: dict[str, list[tuple[float, float]]] = {}
    processed = 0
    skipped = 0

    for row in history:
        pari = str(row.get("pari") or "").strip()
        if not pari:
            skipped += 1
            continue

        resultat = str(row.get("résultat") or row.get("resultat") or "").strip().upper()
        if "GAGN" in resultat or "WIN" in resultat:
            actual = 1.0
        elif "PERDU" in resultat or "LOST" in resultat:
            actual = 0.0
        else:
            skipped += 1
            continue

        market = _normalize_market_from_pari(pari)
        if market == "UNKNOWN":
            skipped += 1
            continue

        # Récupérer ou inférer la probabilité
        proba = _safe_float(row.get("proba_predite") or row.get("proba_prédite"))
        if proba <= 0:
            proba = _safe_float(row.get("python_prob"))
        if proba <= 0 or proba >= 1.0:
            # Fallback : utiliser la probabilité implicite de la cote si disponible
            cote = _safe_float(row.get("cote"))
            if cote > 1.0:
                proba = 1.0 / cote
            else:
                proba = _infer_probability_from_pari(pari)
        if proba > 1.0:
            proba = proba / 100.0
        proba = max(0.05, min(0.95, proba))

        by_market.setdefault(market, []).append((proba, actual))
        processed += 1

    # print(f"   📊 Calibration: {processed} traitées, {skipped} ignorées")

    # Calculer les calibrations par marché
    result: dict[str, CalibrationCoeffs] = {}

    for market, pairs in by_market.items():
        n = len(pairs)
        if n < 5:
            # print(f"   ⚠️ {market}: {n} données (min: 5)")
            continue

        probs_list = [p[0] for p in pairs]
        actuals_list = [p[1] for p in pairs]
        probs_arr = np.array(probs_list)
        actuals_arr = np.array(actuals_list)

        # Accuracy brute
        correct = sum(1 for p, a in pairs if (p >= 0.5) == (a >= 0.5))
        accuracy = correct / n
        brier_before = _brier_score(probs_list, actuals_list)

        # Choisir la méthode de calibration
        cal = CalibrationCoeffs(
            accuracy=round(accuracy, 4),
            n_samples=n,
            brier_before=round(brier_before, 4),
        )

        if n >= 50 and SKLEARN_AVAILABLE:
            # Isotonic Regression (le plus flexible)
            ir = _fit_isotonic(probs_arr, actuals_arr)
            if ir is not None:
                calibrated = ir.predict(probs_arr)
                brier_after = round(_brier_score(calibrated.tolist(), actuals_list), 4)
                # GARDE-FOU : ne calibrer que si ça améliore le Brier score
                if brier_after < brier_before:
                    cal._isotonic_model = ir
                    cal.method = "isotonic"
                    cal.brier_after = brier_after
                    cal.coef_a, cal.coef_b = _fit_linear(probs_list, actuals_list)
                    # print(f"   ✅ {market}: Isotonic Regression ({n} données, "
                    #       f"Brier: {brier_before:.4f} → {brier_after:.4f})")
                else:
                    pass
                    # print(f"   ⚠️ {market}: Isotonic rejetée (Brier: {brier_before:.4f} → {brier_after:.4f})")

        if cal.method == "identity" and n >= 20 and SKLEARN_AVAILABLE:
            # Platt Scaling (fallback)
            platt = _fit_platt(probs_arr, actuals_arr)
            if platt is not None:
                calibrated = platt.predict_proba(probs_arr.reshape(-1, 1))[:, 1]
                brier_after = round(_brier_score(calibrated.tolist(), actuals_list), 4)
                if brier_after < brier_before:
                    cal._platt_model = platt
                    cal.method = "platt"
                    cal.brier_after = brier_after
                    cal.coef_a, cal.coef_b = _fit_linear(probs_list, actuals_list)
                    # print(f"   ✅ {market}: Platt Scaling ({n} données, "
                    #       f"Brier: {brier_before:.4f} → {brier_after:.4f})")
                else:
                    pass
                    # print(f"   ⚠️ {market}: Platt rejetée (Brier: {brier_before:.4f} → {brier_after:.4f})")

        if cal.method == "identity" and n >= 5:
            # Linéaire simple
            coef_a, coef_b = _fit_linear(probs_list, actuals_list)
            calibrated_linear = [max(0, min(1, coef_a * p + coef_b)) for p in probs_list]
            brier_after = round(_brier_score(calibrated_linear, actuals_list), 4)
            if brier_after < brier_before:
                cal.coef_a, cal.coef_b = coef_a, coef_b
                cal.method = "linear"
                cal.brier_after = brier_after
                # print(f"   ✅ {market}: Linéaire a={coef_a}, b={coef_b} ({n} données, "
                #       f"accuracy={accuracy:.1%})")
            else:
                pass
                # print(f"   ⚠️ {market}: Linéaire rejetée, identité conservée ({n} données, "
                #       f"accuracy={accuracy:.1%})")

        calibrations[market] = cal
        result[market] = cal

    return result


# =============================================================================
# 7. PUBLIC API
# =============================================================================


def calibrate_probability(market: str, raw_prob: float) -> float:
    """Applique la calibration au marché donné."""
    cal = calibrations.get(market.upper())
    if cal is None:
        return max(0.01, min(0.99, raw_prob))
    return cal.calibrate(raw_prob)


def get_diagnostics() -> dict[str, Any]:
    """Retourne les diagnostics pour l'API."""
    diag = {
        "markets": list(calibrations.keys()),
        "coefficients": {},
    }
    for market, cal in calibrations.items():
        diag["coefficients"][market] = {
            "coef_a": cal.coef_a,
            "coef_b": cal.coef_b,
            "accuracy": cal.global_accuracy,
            "method": cal.method,
            "n_samples": cal.n_samples,
            "brier_before": cal.brier_before,
            "brier_after": cal.brier_after,
        }
    return diag


# =============================================================================
# 8. SINGLETON (compatibilité main.py)
# =============================================================================


class _ProbabilityCalibrator:
    calibrations = calibrations

    @staticmethod
    def calibrate_probability(market: str, raw_prob: float) -> float:
        return calibrate_probability(market, raw_prob)

    @staticmethod
    def analyze_history(
        history: list[dict[str, Any]],
        model_training_date: str | None = None,
    ) -> dict[str, CalibrationCoeffs]:
        return analyze_history(history, model_training_date=model_training_date)

    @staticmethod
    def get_diagnostics() -> dict[str, Any]:
        return get_diagnostics()


probability_calibrator = _ProbabilityCalibrator()
