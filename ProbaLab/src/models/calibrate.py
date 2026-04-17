from __future__ import annotations

"""
calibrate.py — Calibration ML des probabilités.

Utilise les résultats passés pour ajuster les prédictions futures.

Techniques :
  1. Platt Scaling (régression logistique) par type de pari — actif dès 100 échantillons
  2. Analyse de biais par ligue
  3. Pondération par confiance
  4. Isotonic Regression si assez de données — actif dès 500 échantillons
     (évite la "fonction en escalier" avec peu de données)

Le modèle est recalculé à chaque appel et les paramètres sont
sauvegardés dans la table `calibration` de Supabase.
"""
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from src.config import logger, supabase
from src.constants import (
    BASE_RATE_AWAY,
    BASE_RATE_DRAW,
    BASE_RATE_HOME,
    BAYESIAN_SHRINKAGE_K,
    MIN_ISOTONIC_SAMPLES,
)

# Seuil minimum pour que les algorithmes de fitting fonctionnent correctement
MIN_SAMPLES: int = 20  # Seuil bas pour fit_platt_scaling / fit_isotonic_calibration
# Seuils de confiance pour apply_calibration (importés de constants) :
#   MIN_CALIBRATION_SAMPLES = 100  → Platt scaling fiable
#   MIN_ISOTONIC_SAMPLES    = 500  → Isotonic sans "fonction en escalier"

# Cache en mémoire des modèles isotonic (évite de refitter à chaque prédiction)
_isotonic_cache: dict[str, IsotonicRegression | None] = {}

# Cache TTL — auto-invalidate after 1 hour (3600 seconds)
import time as _time

_CACHE_TTL_SECONDS: int = 3600
_cache_created_at: float = _time.monotonic()


# ═══════════════════════════════════════════════════════════════════
#  1. CHARGEMENT DES DONNÉES
# ═══════════════════════════════════════════════════════════════════


def load_results() -> list[dict]:
    """Load all evaluated prediction results from Supabase.

    Returns:
        List of result dicts from the ``prediction_results`` table, or
        an empty list when no data is available.
    """
    data: list[dict] = supabase.table("prediction_results").select("*").execute().data
    if not data:
        return []
    return data


def prepare_dataset(
    results: list[dict],
    pred_field: str,
    actual_field: str,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Prepare feature / label arrays for a single bet type.

    Args:
        results: Evaluated result dicts (from :func:`load_results`).
        pred_field: Key holding the predicted probability (0–100).
        actual_field: Key holding the binary actual outcome.

    Returns:
        A ``(X, y)`` tuple where *X* has shape ``(n, 1)`` with values
        normalised to [0, 1] and *y* is a 1-D binary array.
    """
    X: list[float] = []
    y: list[float] = []
    for r in results:
        p = r.get(pred_field)
        a = r.get(actual_field)
        if p is not None and a is not None:
            X.append(p / 100.0)  # Normaliser 0-1
            y.append(1.0 if a else 0.0)
    return np.array(X).reshape(-1, 1), np.array(y)


# ═══════════════════════════════════════════════════════════════════
#  2. PLATT SCALING (Régression Logistique)
# ═══════════════════════════════════════════════════════════════════


def fit_platt_scaling(
    X: NDArray[np.floating],
    y: NDArray[np.floating],
) -> tuple[float, float, float | None, float | None]:
    """Calibrate probabilities via logistic regression (Platt Scaling).

    Fits ``calibrated = sigmoid(a * raw_prob + b)`` and measures
    improvement via the Brier score.

    Args:
        X: Predicted probabilities with shape ``(n, 1)``, values in
            [0, 1].
        y: Binary ground-truth labels with shape ``(n,)``.

    Returns:
        A ``(a, b, brier_before, brier_after)`` tuple.  When there are
        fewer than :data:`MIN_SAMPLES` observations, ``(1.0, 0.0, None,
        None)`` is returned (identity mapping).
    """
    if len(X) < MIN_SAMPLES:
        return 1.0, 0.0, None, None

    # Brier avant calibration
    brier_before: float = brier_score_loss(y, X.ravel())

    # Fit
    lr: LogisticRegression = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
    try:
        lr.fit(X, y)
        a: float = lr.coef_[0][0]
        b: float = lr.intercept_[0]

        # Probas calibrées
        calibrated: NDArray[np.floating] = lr.predict_proba(X)[:, 1]
        brier_after: float = brier_score_loss(y, calibrated)

        return round(float(a), 4), round(float(b), 4), round(brier_before, 4), round(brier_after, 4)
    except Exception:
        return 1.0, 0.0, round(brier_before, 4), None  # Fallback: no calibration adjustment


def fit_isotonic_calibration(
    X: NDArray[np.floating],
    y: NDArray[np.floating],
) -> tuple[IsotonicRegression | None, float | None, float | None]:
    """Calibrate probabilities via isotonic regression.

    Isotonic regression is a non-parametric method that fits a
    monotonically increasing step function to map raw probabilities
    to calibrated ones. It is more flexible than Platt scaling and
    can capture non-linear miscalibrations.

    Args:
        X: Predicted probabilities with shape ``(n, 1)`` or ``(n,)``,
            values in [0, 1].
        y: Binary ground-truth labels with shape ``(n,)``.

    Returns:
        A ``(model, brier_before, brier_after)`` tuple.  When there are
        fewer than :data:`MIN_SAMPLES` observations, ``(None, None,
        None)`` is returned.
    """
    x_flat = X.ravel()
    if len(x_flat) < MIN_SAMPLES:
        return None, None, None

    brier_before: float = brier_score_loss(y, x_flat)

    try:
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(x_flat, y)
        calibrated = iso.predict(x_flat)
        brier_after: float = brier_score_loss(y, calibrated)
        return iso, round(brier_before, 4), round(brier_after, 4)
    except Exception:
        return None, round(brier_before, 4), None


# ═══════════════════════════════════════════════════════════════════
#  3. ANALYSE DE BIAIS
# ═══════════════════════════════════════════════════════════════════


def compute_bias(X: NDArray[np.floating], y: NDArray[np.floating]) -> float:
    """Compute the mean prediction bias.

    A positive value means the model over-estimates the probability; a
    negative value means it under-estimates.

    Args:
        X: Predicted probabilities with shape ``(n, 1)``, values in
            [0, 1].
        y: Binary ground-truth labels with shape ``(n,)``.

    Returns:
        Mean signed difference ``mean(predictions − actuals)``, rounded
        to four decimals.  Returns ``0.0`` when *X* is empty.
    """
    if len(X) == 0:
        return 0.0
    predictions: NDArray[np.floating] = X.ravel()
    actuals: NDArray[np.floating] = y
    bias: float = float(np.mean(predictions - actuals))
    return round(bias, 4)


# ═══════════════════════════════════════════════════════════════════
#  4. CALIBRATION PAR TYPE DE PARI
# ═══════════════════════════════════════════════════════════════════

BET_TYPES: dict[str, tuple[str, str, Callable[[dict], bool | None]]] = {
    "1x2_home": ("pred_home", "result_1x2_ok", lambda r: r.get("actual_result") == "H"),
    "1x2_draw": ("pred_draw", "result_1x2_ok", lambda r: r.get("actual_result") == "D"),
    "1x2_away": ("pred_away", "result_1x2_ok", lambda r: r.get("actual_result") == "A"),
    "btts": ("pred_btts", "btts_ok", lambda r: r.get("actual_btts")),
    "over_05": ("pred_over_05", "over_05_ok", lambda r: r.get("actual_over_05")),
    "over_15": ("pred_over_15", "over_15_ok", lambda r: r.get("actual_over_15")),
    "over_25": ("pred_over_25", "over_25_ok", lambda r: r.get("actual_over_25")),
}


def calibrate_all(results: list[dict], league_id: int | None = None) -> list[dict]:
    """Calibrate all bet types and return parameter rows.

    For each entry in :data:`BET_TYPES`, prepares the dataset (optionally
    filtered by league), fits Platt scaling, measures accuracy and bias,
    and assembles a calibration row.

    Args:
        results: Evaluated result dicts from :func:`load_results`.
        league_id: If provided, only results for this league are used.
            Pass ``None`` for a global (cross-league) calibration.

    Returns:
        List of calibration row dicts suitable for upserting into the
        Supabase ``calibration`` table.
    """
    if league_id:
        filtered: list[dict] = [r for r in results if r.get("league_id") == league_id]
    else:
        filtered = results

    calibration_rows: list[dict] = []

    for bet_type, (pred_field, _, actual_fn) in BET_TYPES.items():
        # Préparer les données
        X_list: list[float] = []
        y_list: list[float] = []
        for r in filtered:
            p = r.get(pred_field)
            a = actual_fn(r)
            if p is not None and a is not None:
                X_list.append(p / 100.0)
                y_list.append(1.0 if a else 0.0)

        X: NDArray[np.floating] = (
            np.array(X_list).reshape(-1, 1) if X_list else np.array([]).reshape(-1, 1)
        )
        y: NDArray[np.floating] = np.array(y_list)

        n: int = len(y)
        if n < 5:
            continue

        # Accuracy
        accuracy: float | None
        if n > 0:
            correct: int = sum(1 for xi, yi in zip(X.ravel(), y) if (xi >= 0.5) == (yi >= 0.5))
            accuracy = round(correct / n, 4)
        else:
            accuracy = None

        # Platt scaling
        a_coef, b_coef, brier_before, brier_after = fit_platt_scaling(X, y)

        # Biais
        bias: float = compute_bias(X, y)

        # Brier score final
        brier: float | None = brier_after if brier_after is not None else brier_before

        row: dict = {
            "bet_type": bet_type,
            "league_id": league_id,
            "platt_a": a_coef,
            "platt_b": b_coef,
            "bias": bias,
            "sample_size": n,
            "accuracy": accuracy,
            "brier_score": brier,
        }
        calibration_rows.append(row)

    return calibration_rows


# ═══════════════════════════════════════════════════════════════════
#  5. APPLICATION DE LA CALIBRATION
# ═══════════════════════════════════════════════════════════════════


def apply_calibration(raw_prob: int, bet_type: str, league_id: int | None = None) -> int:
    """Apply calibration to a raw probability.

    Strategy:
      - ``sample_size >= MIN_ISOTONIC_SAMPLES`` (500) : Isotonic Regression
        (non-parametric, captures non-linearities, smooth with enough data).
      - ``sample_size >= MIN_SAMPLES`` (100) : Platt Scaling (logistic regression,
        parametric and robust with moderate data).
      - Otherwise: returns *raw_prob* unchanged.

    Auto-invalidates caches after ``_CACHE_TTL_SECONDS`` to pick up fresh
    calibration parameters without requiring a process restart.

    Args:
        raw_prob: Raw probability in percent (0–100).
        bet_type: Bet category key (e.g. ``"1x2_home"``, ``"btts"``).
        league_id: Optional league filter; falls back to global params.

    Returns:
        Calibrated probability in percent (0–100).
    """
    # Auto-invalidate stale caches
    global _cache_created_at
    if _time.monotonic() - _cache_created_at > _CACHE_TTL_SECONDS:
        clear_cache()
        _cache_created_at = _time.monotonic()

    calib: dict | None = _get_calibration_params(bet_type, league_id)
    if not calib:
        return raw_prob

    sample_size: int = calib.get("sample_size", 0)

    # ── Isotonic regression (500+ samples) ────────────────────────
    if sample_size >= MIN_ISOTONIC_SAMPLES:
        iso = _get_or_fit_isotonic(bet_type, league_id)
        if iso is not None:
            x: float = raw_prob / 100.0
            calibrated: float = float(iso.predict([x])[0])
            return round(calibrated * 100)

    # ── Platt scaling (100+ samples) ──────────────────────────────
    if sample_size < MIN_SAMPLES:
        return raw_prob

    a: float = calib.get("platt_a", 1.0)
    b: float = calib.get("platt_b", 0.0)

    # Sanity check: reject degenerate Platt parameters
    # (e.g. a=50 maps all inputs to sigmoid ≈ 1.0, destroying differentiation)
    if abs(a) > 20 or abs(b) > 20:
        return raw_prob

    x = raw_prob / 100.0
    z: float = a * x + b
    z = max(-10, min(10, z))  # Protection overflow
    calibrated = 1.0 / (1.0 + np.exp(-z))

    return round(calibrated * 100)


_calibration_cache: dict[str, dict] = {}


def _get_calibration_params(bet_type: str, league_id: int | None = None) -> dict | None:
    """Retrieve calibration parameters from Supabase (with in-memory cache).

    Looks up league-specific parameters first; falls back to the global
    (``league_id IS NULL``) row if no league-specific entry exists.

    Args:
        bet_type: Bet category key.
        league_id: Optional league filter.

    Returns:
        Calibration row dict, or ``None`` if no parameters are stored.
    """
    cache_key: str = f"{bet_type}_{league_id}"
    if cache_key in _calibration_cache:
        return _calibration_cache[cache_key]

    # D'abord chercher par ligue
    if league_id:
        result: list[dict] = (
            supabase.table("calibration")
            .select("*")
            .eq("bet_type", bet_type)
            .eq("league_id", league_id)
            .execute()
            .data
        )
        if result:
            _calibration_cache[cache_key] = result[0]
            return result[0]

    # Sinon, calibration globale
    result = (
        supabase.table("calibration")
        .select("*")
        .eq("bet_type", bet_type)
        .is_("league_id", "null")
        .execute()
        .data
    )
    if result:
        _calibration_cache[cache_key] = result[0]
        return result[0]

    return None


def clear_cache() -> None:
    """Flush the in-memory calibration parameter cache.

    Should be called after a recalibration run so that subsequent
    :func:`apply_calibration` calls pick up the fresh parameters.

    Returns:
        None.
    """
    global _calibration_cache, _isotonic_cache
    _calibration_cache = {}
    _isotonic_cache = {}


def _get_or_fit_isotonic(bet_type: str, league_id: int | None = None) -> IsotonicRegression | None:
    """Return a cached isotonic regression model, fitting it on first call.

    Loads all evaluated prediction results, filters to the given bet type
    and league, and fits an :class:`IsotonicRegression` when at least
    :data:`MIN_ISOTONIC_SAMPLES` samples are available.  The model is cached
    in :data:`_isotonic_cache` for the lifetime of the process.

    Args:
        bet_type: Bet category key (e.g. ``"1x2_home"``, ``"btts"``).
        league_id: Optional league filter.

    Returns:
        Fitted :class:`IsotonicRegression`, or ``None`` when insufficient data.
    """
    cache_key: str = f"iso_{bet_type}_{league_id}"
    if cache_key in _isotonic_cache:
        return _isotonic_cache[cache_key]

    # Correspondance bet_type → champs de probabilité et d'outcome
    _BET_PRED_FIELDS: dict[str, tuple[str, Callable[[dict], bool | None]]] = {
        "1x2_home": ("pred_home", lambda r: r.get("actual_result") == "H"),
        "1x2_draw": ("pred_draw", lambda r: r.get("actual_result") == "D"),
        "1x2_away": ("pred_away", lambda r: r.get("actual_result") == "A"),
        "btts": ("pred_btts", lambda r: r.get("actual_btts")),
        "over_05": ("pred_over_05", lambda r: r.get("actual_over_05")),
        "over_15": ("pred_over_15", lambda r: r.get("actual_over_15")),
        "over_25": ("pred_over_25", lambda r: r.get("actual_over_25")),
    }
    if bet_type not in _BET_PRED_FIELDS:
        _isotonic_cache[cache_key] = None
        return None

    pred_field, actual_fn = _BET_PRED_FIELDS[bet_type]

    try:
        results: list[dict] = load_results()
        if league_id:
            results = [r for r in results if r.get("league_id") == league_id]

        X_list: list[float] = []
        y_list: list[float] = []
        for r in results:
            p = r.get(pred_field)
            a = actual_fn(r)
            if p is not None and a is not None:
                X_list.append(p / 100.0)
                y_list.append(1.0 if a else 0.0)

        if len(X_list) < MIN_ISOTONIC_SAMPLES:
            _isotonic_cache[cache_key] = None
            return None

        x_arr = np.array(X_list)
        y_arr = np.array(y_list)
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(x_arr, y_arr)
        _isotonic_cache[cache_key] = iso
        return iso
    except Exception:
        _isotonic_cache[cache_key] = None
        return None


# ═══════════════════════════════════════════════════════════════════
#  6. BAYESIAN SHRINKAGE — 1X2 CALIBRATION (low sample count)
# ═══════════════════════════════════════════════════════════════════


def _get_1x2_sample_count() -> int:
    """Return the number of evaluated 1X2 predictions available for calibration.

    Counts rows in ``prediction_results`` where ``pred_home`` is not null,
    which indicates a fully evaluated 1X2 prediction.

    Returns:
        Sample count (0 if query fails or no data).
    """
    try:
        resp = (
            supabase.table("prediction_results")
            .select("id", count="exact")
            .not_.is_("pred_home", "null")
            .execute()
        )
        return resp.count or 0
    except Exception:
        return 0


def calibrate_1x2_bayesian(
    proba_home: float,
    proba_draw: float,
    proba_away: float,
    league_id: int | None = None,
) -> tuple[float, float, float]:
    """Bayesian shrinkage calibration for 1X2 when sample size is small.

    Shrinks extreme predictions toward the base rate (league average).
    With more data, the shrinkage factor approaches 1.0 and this converges
    to identity.

    **Skipped entirely when n >= 200** — once we have enough evaluated
    predictions, the raw model probabilities are trusted as-is, and
    Isotonic/Platt calibration handles the fine-tuning instead.

    Formula: ``calibrated = base_rate + shrinkage * (raw - base_rate)``
    where ``shrinkage = n / (n + k)``, *n* = sample count, *k* = shrinkage strength.

    Args:
        proba_home: Raw home win probability (0–100 scale).
        proba_draw: Raw draw probability (0–100 scale).
        proba_away: Raw away win probability (0–100 scale).
        league_id: Optional league id (reserved for future per-league base rates).

    Returns:
        Tuple of ``(cal_home, cal_draw, cal_away)`` as integers summing to 100.
    """
    n = _get_1x2_sample_count()

    # With enough data (200+ evaluated predictions), skip shrinkage entirely.
    # The model's probabilities have earned enough trust, and Platt/Isotonic
    # calibration handles fine-tuning via apply_calibration().
    if n >= 200:
        return proba_home, proba_draw, proba_away

    shrinkage = n / (n + BAYESIAN_SHRINKAGE_K) if n > 0 else 0.0

    # Base rates — could be per-league in the future
    base_home = BASE_RATE_HOME
    base_draw = BASE_RATE_DRAW
    base_away = BASE_RATE_AWAY

    cal_home = base_home + shrinkage * (proba_home - base_home)
    cal_draw = base_draw + shrinkage * (proba_draw - base_draw)
    cal_away = base_away + shrinkage * (proba_away - base_away)

    # Normalize to exactly 100
    total = cal_home + cal_draw + cal_away
    if total > 0:
        cal_home = round(cal_home / total * 100)
        cal_draw = round(cal_draw / total * 100)
        cal_away = 100 - cal_home - cal_draw
    else:
        cal_home, cal_draw, cal_away = 45, 27, 28

    return cal_home, cal_draw, cal_away


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════


def run_calibration() -> None:
    """Recalibrate all bet-type models and persist parameters.

    Loads evaluated results, performs global calibration, then
    per-league calibration (for leagues with at least 10 results),
    upserts parameter rows into the Supabase ``calibration`` table,
    and clears the local cache.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  🤖 CALIBRATION ML DES PRÉDICTIONS")
    logger.info("=" * 60)

    results: list[dict] = load_results()
    if not results:
        logger.warning("Pas de données d'évaluation. Lance d'abord evaluate.py.")
        return

    logger.info(f"{len(results)} matchs évalués disponibles pour la calibration")

    # ── Calibration globale ───────────────────────────────────────
    logger.info("── Calibration globale ──")
    global_rows: list[dict] = calibrate_all(results, league_id=None)
    _save_and_print(global_rows)

    # ── Calibration par ligue ─────────────────────────────────────
    league_ids: list[int] = list({r["league_id"] for r in results if r.get("league_id")})
    for lid in sorted(league_ids):
        league_results: list[dict] = [r for r in results if r.get("league_id") == lid]
        if len(league_results) < 10:
            continue
        logger.info(f"── Ligue {lid} ({len(league_results)} matchs) ──")
        league_rows: list[dict] = calibrate_all(results, league_id=lid)
        _save_and_print(league_rows)

    clear_cache()
    logger.info(f"{'=' * 60}")
    logger.info("  ✅ Calibration terminée")
    logger.info(f"{'=' * 60}")


def _save_and_print(rows: list[dict]) -> None:
    """Upsert calibration rows to Supabase and log a summary line for each.

    Args:
        rows: Calibration parameter dicts produced by
            :func:`calibrate_all`.

    Returns:
        None.
    """
    for row in rows:
        try:
            supabase.table("calibration").upsert(row, on_conflict="bet_type,league_id").execute()
        except Exception:
            logger.warning(
                "Calibration save failed for bet_type=%s", row.get("bet_type"), exc_info=True
            )

        bias = row.get("bias")
        bias_str = f"+{bias}" if bias is not None and bias > 0 else str(bias)
        acc = row.get("accuracy")
        brier = row.get("brier_score")
        platt_a = row.get("platt_a")
        platt_b = row.get("platt_b")
        acc_s = f"{acc:.1%}" if acc is not None else "N/A"
        brier_s = f"{brier:.4f}" if brier is not None else "N/A"
        pa_s = f"{platt_a:.3f}" if platt_a is not None else "N/A"
        pb_s = f"{platt_b:.3f}" if platt_b is not None else "N/A"
        logger.info(
            f"  {row['bet_type']:15s}  n={row['sample_size']:4d}  "
            f"acc={acc_s}  brier={brier_s}  bias={bias_str}  "
            f"platt=[{pa_s}, {pb_s}]"
        )


# ═══════════════════════════════════════════════════════════════════
#  7. RECALIBRATION AUTO DES DRAW FACTORS
# ═══════════════════════════════════════════════════════════════════

from datetime import datetime
from datetime import timezone as _tz


def recalibrate_draw_factors(months: int = 6) -> dict[int, float]:
    """Compute recommended draw factors per league from recent results.

    Loads completed fixtures (status FT/AET/PEN) from the last *months*
    months, computes the observed draw rate per league, and compares it
    to the current ``DRAW_FACTOR_BY_LEAGUE`` values in ``constants.py``.

    Recommendations are logged but ``constants.py`` is never modified
    automatically — apply them manually after review.

    Args:
        months: Lookback window in months (default 6).

    Returns:
        Dict mapping ``league_id`` to the recommended new draw factor
        (rounded to 2 decimal places).  Only leagues with enough data
        (>=50 completed matches) are included.
    """
    from src.constants import DRAW_FACTOR_BY_LEAGUE

    cutoff = datetime.now(_tz.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Step back `months` months
    year = cutoff.year
    month = cutoff.month - months
    while month <= 0:
        month += 12
        year -= 1
    cutoff = cutoff.replace(year=year, month=month)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    logger.info("Recalibration draw factors depuis %s", cutoff_str)

    try:
        rows = (
            supabase.table("fixtures")
            .select("league_id, goals_home, goals_away")
            .in_("status", ["FT", "AET", "PEN"])
            .gte("date", cutoff_str)
            .execute()
            .data
        )
    except Exception:
        logger.exception("Erreur chargement fixtures pour draw recalibration")
        return {}

    if not rows:
        logger.warning("Aucun fixture trouvé pour la recalibration draw factors")
        return {}

    # Agrégation par ligue
    league_stats: dict[int, dict[str, int]] = {}
    for row in rows:
        lid = row.get("league_id")
        gh = row.get("goals_home")
        ga = row.get("goals_away")
        if lid is None or gh is None or ga is None:
            continue
        try:
            lid = int(lid)
            gh = int(gh)
            ga = int(ga)
        except (TypeError, ValueError):
            continue

        if lid not in league_stats:
            league_stats[lid] = {"total": 0, "draws": 0}
        league_stats[lid]["total"] += 1
        if gh == ga:
            league_stats[lid]["draws"] += 1

    MIN_MATCHES = 50  # Minimum for a statistically meaningful rate
    recommendations: dict[int, float] = {}

    logger.info("=" * 60)
    logger.info("  DRAW FACTOR RECALIBRATION — derniers %d mois", months)
    logger.info("=" * 60)
    logger.info(
        "  %-8s  %-8s  %-10s  %-12s  %-12s  %s",
        "league",
        "matches",
        "draw_rate",
        "current_df",
        "recommended",
        "delta",
    )

    for lid, stats in sorted(league_stats.items()):
        total = stats["total"]
        if total < MIN_MATCHES:
            logger.debug(
                "  Ligue %d: seulement %d matchs — ignorée (min=%d)", lid, total, MIN_MATCHES
            )
            continue

        observed_rate = round(stats["draws"] / total, 2)
        current_df = DRAW_FACTOR_BY_LEAGUE.get(lid, 0.28)

        # Smooth recommendation: blend 70% observed + 30% current (Bayesian prior)
        # This avoids overreacting to short-term variance in a 6-month window.
        recommended = round(0.70 * observed_rate + 0.30 * current_df, 2)
        delta = round(recommended - current_df, 2)
        delta_str = f"+{delta}" if delta > 0 else str(delta)

        recommendations[lid] = recommended
        change_marker = " <-- UPDATE RECOMMENDED" if abs(delta) >= 0.02 else ""
        logger.info(
            "  %-8d  %-8d  %-10.2f  %-12.2f  %-12.2f  %s%s",
            lid,
            total,
            observed_rate,
            current_df,
            recommended,
            delta_str,
            change_marker,
        )

    logger.info("=" * 60)
    logger.info(
        "  %d ligues analysées, %d mises à jour recommandées (delta >= 0.02)",
        len(recommendations),
        sum(
            1
            for lid, rec in recommendations.items()
            if abs(rec - DRAW_FACTOR_BY_LEAGUE.get(lid, 0.28)) >= 0.02
        ),
    )
    logger.info("  Pour appliquer, mettre à jour DRAW_FACTOR_BY_LEAGUE dans src/constants.py")
    logger.info("=" * 60)

    return recommendations


if __name__ == "__main__":
    run_calibration()
