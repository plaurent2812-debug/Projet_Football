from __future__ import annotations

import datetime
import hmac
import logging
import math
import os
import pickle
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException

from src.config import supabase

logger = logging.getLogger(__name__)


# ── Safe Pickle Loading ───────────────────────────────────────────
# Tight whitelist: only the sklearn sub-modules actually used by NHL models.
_PICKLE_ALLOWED_PREFIXES = (
    "sklearn.ensemble.",
    "sklearn.linear_model.",
    "sklearn.preprocessing.",
    "sklearn.calibration.",
    "sklearn.pipeline.",
    "sklearn.impute.",
    "sklearn.tree.",
    "sklearn.utils.",
    "sklearn.base.",
    "numpy.",
    "numpy",
    "xgboost.",
    "lightgbm.",
    "_codecs",
    "builtins",
    "collections",
    "copyreg",
)


class _RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only allows whitelisted module prefixes."""

    def find_class(self, module: str, name: str) -> Any:
        if any(module.startswith(p) for p in _PICKLE_ALLOWED_PREFIXES):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            f"Blocked deserialization of {module}.{name} — not in whitelist"
        )


def safe_pickle_load(f) -> Any:
    """Deserialize a file object using the restricted unpickler."""
    return _RestrictedUnpickler(f).load()


from src.nhl.calibration import probability_calibrator

# Imports NHL Modules
from src.nhl.feature_engineering import feature_engineer
from src.nhl.schemas import (
    BrainPrediction,
    BrainRequest,
    BrainResponse,
    CalibrateProbaRequest,
    GameWinProbRequest,
    IngestDataLakeRequest,
    IngestSuiviAlgoRequest,
    UpdateDataLakeResultsRequest,
)

# ML Models Import with Fallback
try:
    from src.nhl.ml_models import (
        assist_predictor,
        goal_predictor,
        load_all_models,
        point_predictor,
        shot_predictor,
    )

    ENHANCED_ML_AVAILABLE = True
except ImportError:
    from src.nhl.ml_models import goal_predictor

    shot_predictor = None
    point_predictor = None
    assist_predictor = None
    load_all_models = None
    ENHANCED_ML_AVAILABLE = False

router = APIRouter(prefix="/nhl", tags=["NHL"])

# --- CONFIGURATION ---
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
MODEL_VERSION = "v31.0.0_ML"


# =============================================================================
# UTILITIES
# =============================================================================


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")):
    """Vérifie la clé API. BLOQUE si invalide ou non configurée (fail-closed)."""
    if not API_SECRET_KEY:
        raise HTTPException(status_code=503, detail="API key not configured on server")
    if not x_api_key or not hmac.compare_digest(x_api_key, API_SECRET_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


# =============================================================================
# MODEL LOADING
# =============================================================================

_game_win_model = None
_game_win_features = []


def _load_game_win_model():
    """Charge le modèle de probabilité de match (pickle + ubj fallback)."""
    global _game_win_model, _game_win_features
    # Correct path: models/nhl/nhl_match_win.pkl
    model_path = "models/nhl/nhl_match_win.pkl"
    if os.path.isfile(model_path):
        try:
            with open(model_path, "rb") as f:
                data = safe_pickle_load(f)

            _game_win_features = data.get("feature_names", [])

            # Use UBJ if available
            ubj_path = model_path.replace(".pkl", ".ubj")
            if os.path.isfile(ubj_path):
                from xgboost import XGBClassifier

                _game_win_model = XGBClassifier()
                _game_win_model.load_model(ubj_path)
                print(f"   ✅ Game model UBJ chargé: {ubj_path}")
            else:
                _game_win_model = data.get("model")
                print(f"   ✅ Game model Pickle chargé: {model_path}")

            metrics = data.get("metrics", {})
            print(f"      AUC={metrics.get('roc_auc', 0):.3f}")
        except Exception as e:
            print(f"   ⚠️ Game model non chargé ({model_path}): {e}")


# Note: We call this when the router is imported or manually?
# Usually in lifespan, but routers don't have lifespan.
# We can load it at module level or on first request. For now, module level call:
_load_game_win_model()

if ENHANCED_ML_AVAILABLE and load_all_models:
    try:
        load_all_models()
    except Exception as e:
        print(f"Error loading models: {e}")
else:
    goal_predictor.load("src/models/nhl_best_goal_predictor.pkl")


# =============================================================================
# CALIBRATION
# =============================================================================


def _load_calibration_from_supabase(silent: bool = False) -> tuple[bool, str, dict | None]:
    """Charge la calibration depuis Supabase."""
    try:
        response = (
            supabase.table("nhl_suivi_algo_clean")
            .select("*")
            .or_(
                "résultat.ilike.%GAGNÉ%,résultat.ilike.%PERDU%,résultat.ilike.%WIN%,résultat.ilike.%LOST%"
            )
            .order("date", desc=True)
            .limit(10000)
            .execute()
        )

        if not response.data:
            return False, "No data in Supabase", None

        # Filtrer et nettoyer
        clean = []
        for row in response.data:
            pari = str(row.get("pari", "")).strip()
            if not pari:
                continue
            resultat = str(row.get("résultat") or row.get("resultat", "")).strip().upper()
            if not any(kw in resultat for kw in ("GAGN", "PERDU", "WIN", "LOST")):
                continue
            clean.append(
                {
                    "pari": pari,
                    "resultat": resultat,
                    "résultat": resultat,
                    "proba_predite": row.get("proba_predite"),
                    "python_prob": row.get("python_prob"),
                    "cote": row.get("cote"),
                    "date": row.get("date"),
                }
            )

        if len(clean) < 10:
            return False, f"Not enough data ({len(clean)} rows)", None

        model_training_date = None
        if goal_predictor.model_metadata:
            model_training_date = goal_predictor.model_metadata.get("training_date", "")
            if model_training_date:
                model_training_date = model_training_date[:10]

        calibrations = probability_calibrator.analyze_history(
            clean, model_training_date=model_training_date
        )
        if not calibrations:
            return False, "Not enough data per market", None

        diagnostics = probability_calibrator.get_diagnostics()
        diagnostics["n_rows_analyzed"] = len(clean)
        diagnostics["markets_calibrated"] = list(calibrations.keys())

        return True, f"{len(calibrations)} markets calibrated", diagnostics

    except Exception as e:
        if not silent:
            print(f"   ❌ Erreur calibration: {e}")
        return False, str(e), None


# Initial load of calibration
_load_calibration_from_supabase(silent=True)


@router.post("/calibrate_from_supabase", dependencies=[Depends(verify_api_key)])
def calibrate_from_supabase():
    """Recalcule la calibration depuis Supabase."""
    ok, msg, diagnostics = _load_calibration_from_supabase(silent=False)
    if not ok:
        return {"ok": False, "message": msg}
    return {
        "ok": True,
        "n_rows_analyzed": diagnostics.get("n_rows_analyzed", 0),
        "markets_calibrated": diagnostics.get("markets_calibrated", []),
        "diagnostics": diagnostics,
    }


@router.get("/calibration_coefficients")
def get_calibration_coefficients():
    coefs = {}
    for mkt, cal in probability_calibrator.calibrations.items():
        coefs[mkt] = {
            "coef_a": cal.coef_a,
            "coef_b": cal.coef_b,
            "accuracy": round(cal.global_accuracy * 100, 1),
            "method": cal.method,
            "n_samples": cal.n_samples,
            "brier_before": cal.brier_before,
            "brier_after": cal.brier_after,
        }
    return {"ok": True, "coefficients": coefs}


@router.post("/apply_calibration")
def apply_calibration(req: CalibrateProbaRequest):
    calibrated = probability_calibrator.calibrate_probability(req.market, req.raw_prob)
    return {
        "market": req.market,
        "raw_prob": req.raw_prob,
        "calibrated_prob": round(calibrated * 100, 2),
    }


# =============================================================================
# PREDICTIONS
# =============================================================================


@router.post("/brain_quick", response_model=BrainResponse)
@router.post("/brain_quick_v2", response_model=BrainResponse)
@router.post("/brain_quick_calibrated", response_model=BrainResponse)
def brain_quick(req: BrainRequest):
    """Endpoint unifié pour les prédictions rapides."""
    predictions = []
    # ml_fallback_used reflects predictor.loaded state (same for all players in a batch)
    ml_fallback_used: dict[str, bool] = {
        "shot": False,
        "assist": False,
        "goal": False,
        "point": False,
    }

    for player in req.players:
        raw = player.dict()

        if "algo_score_goal" not in raw or not raw.get("algo_score_goal"):
            raw["algo_score_goal"] = 50.0
        if "python_vol" not in raw or not raw.get("python_vol"):
            raw["python_vol"] = player.spg

        # --- GOAL ---
        prob_goal_raw = goal_predictor.predict_proba(raw)
        prob_goal = probability_calibrator.calibrate_probability("GOAL", prob_goal_raw)
        math_prob_goal = round(prob_goal * 100, 1)

        # --- SHOTS ---
        home_factor = 1.05 if player.is_home else 0.95
        opp_factor = clamp(player.opp_shots_allowed_avg / 30.0, 0.8, 1.2)
        lam_shots = player.spg * home_factor * opp_factor

        if shot_predictor is not None and shot_predictor.loaded:
            raw_prob_shot = shot_predictor.predict_proba(raw)
        else:
            logger.warning(
                "ML fallback (Poisson) used for SHOT prediction — player %s",
                player.id,
            )
            raw_prob_shot = 1.0 - math.exp(-lam_shots)
            ml_fallback_used["shot"] = True

        cal_prob_shot = probability_calibrator.calibrate_probability("SHOT", raw_prob_shot)
        ratio = cal_prob_shot / max(0.01, raw_prob_shot)
        math_exp_shots = lam_shots * ratio

        # --- POINT ---
        apg = player.apg if player.apg and player.apg > 0 else player.gpg * 0.8

        if point_predictor is not None and point_predictor.loaded:
            raw_prob_point = point_predictor.predict_proba(raw)
        else:
            logger.warning(
                "ML fallback (Poisson) used for POINT prediction — player %s",
                player.id,
            )
            raw_prob_point = 1.0 - math.exp(-(player.gpg + apg) * home_factor)
            ml_fallback_used["point"] = True

        prob_point = probability_calibrator.calibrate_probability("POINT", raw_prob_point)

        # --- ASSIST ---
        if assist_predictor is not None and assist_predictor.loaded:
            raw_prob_assist = assist_predictor.predict_proba(raw)
        else:
            logger.warning(
                "ML fallback (Poisson) used for ASSIST prediction — player %s",
                player.id,
            )
            raw_prob_assist = 1.0 - math.exp(-apg * home_factor)
            ml_fallback_used["assist"] = True

        prob_assist = probability_calibrator.calibrate_probability("ASSIST", raw_prob_assist)

        confidence = "high" if prob_goal_raw > 0.4 else ("medium" if prob_goal_raw > 0.2 else "low")

        predictions.append(
            BrainPrediction(
                id=player.id,
                math_prob_goal=math_prob_goal,
                math_exp_shots=round(math_exp_shots, 2),
                prob_point=round(prob_point * 100, 1),
                prob_assist=round(prob_assist * 100, 1),
                confidence=confidence,
            )
        )

    return BrainResponse(predictions=predictions, ml_fallback_used=ml_fallback_used)


@router.post("/brain_enhanced", response_model=BrainResponse)
def brain_enhanced(req: BrainRequest):
    """Endpoint avancé utilisant feature_engineer."""
    predictions = []

    for player in req.players:
        features = feature_engineer.build_features(player.dict())

        raw_goal = feature_engineer.compute_goal_probability(features)
        raw_point = feature_engineer.compute_point_probability(features)
        raw_assist = feature_engineer.compute_assist_probability(features)
        exp_shots = feature_engineer.compute_shot_expectation(features)

        if req.apply_calibration:
            prob_goal = probability_calibrator.calibrate_probability("GOAL", raw_goal)
            prob_point = probability_calibrator.calibrate_probability("POINT", raw_point)
            prob_assist = probability_calibrator.calibrate_probability("ASSIST", raw_assist)
        else:
            prob_goal, prob_point, prob_assist = raw_goal, raw_point, raw_assist

        predictions.append(
            BrainPrediction(
                id=player.id,
                math_prob_goal=round(prob_goal * 100, 1),
                math_exp_shots=round(exp_shots, 2),
                prob_point=round(prob_point * 100, 1),
                prob_assist=round(prob_assist * 100, 1),
                confidence="high",
            )
        )

    return BrainResponse(predictions=predictions)


@router.post("/game_win_probability")
def game_win_probability(req: GameWinProbRequest):
    if _game_win_model is not None and _game_win_features:
        try:
            features = {
                "home_gaa": req.home_gaa,
                "away_gaa": req.away_gaa,
                "home_l10_win_pct": req.home_l10,
                "away_l10_win_pct": req.away_l10,
                "home_pts_per_game": req.home_pts_per_game,
                "away_pts_per_game": req.away_pts_per_game,
                "gaa_diff": req.away_gaa - req.home_gaa,
                "form_diff": req.home_l10 - req.away_l10,
                "strength_diff": req.home_pts_per_game - req.away_pts_per_game,
                "home_goals_for_avg": 0.0,
                "away_goals_for_avg": 0.0,
                "home_goals_against_avg": req.home_gaa,
                "away_goals_against_avg": req.away_gaa,
            }
            # Note: importing pandas locally to avoid top-level overhead if not used?
            # Already imported at top.
            X = pd.DataFrame([{f: features.get(f, 0) for f in _game_win_features}])
            p_home = float(_game_win_model.predict_proba(X)[0, 1])

            if req.home_is_tired:
                p_home -= 0.04
            if req.away_is_tired:
                p_home += 0.04

            p_home_final = clamp(p_home, 0.20, 0.80)
            return {
                "home_team": req.home_team,
                "away_team": req.away_team,
                "home_win_prob": round(p_home_final * 100),
                "away_win_prob": round((1.0 - p_home_final) * 100),
                "method": "ml_model",
            }
        except Exception:
            pass

    p_home = 0.54
    p_home += (req.away_gaa - req.home_gaa) * 0.06
    p_home += (req.home_l10 - req.away_l10) * 0.12
    p_home += (req.home_pts_per_game - req.away_pts_per_game) * 0.15
    p_home += (req.home_ai_factor - 1.0) * 0.05
    p_home -= (req.away_ai_factor - 1.0) * 0.05
    if req.home_is_tired:
        p_home -= 0.06
    if req.away_is_tired:
        p_home += 0.06

    cal_p = probability_calibrator.calibrate_probability("WINNER", p_home)
    p_home_final = clamp(cal_p, 0.20, 0.80)

    return {
        "home_team": req.home_team,
        "away_team": req.away_team,
        "home_win_prob": round(p_home_final * 100),
        "away_win_prob": round((1.0 - p_home_final) * 100),
        "method": "heuristic",
    }


# =============================================================================
# DATA INGESTION
# =============================================================================


@router.post("/ingest_data_lake", dependencies=[Depends(verify_api_key)])
def ingest_data_lake(req: IngestDataLakeRequest):
    supabase_ok = False
    try:
        data = [r.dict() for r in req.rows]
        for d in data:
            d["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for i in range(0, len(data), 1000):
            supabase.table("nhl_data_lake").insert(data[i : i + 1000]).execute()
        supabase_ok = True
    except Exception as e:
        print(f"   ⚠️ Supabase Error: {e}")

    # No BigQuery support in this migration for now
    return {"inserted": len(req.rows), "supabase": supabase_ok, "bigquery": False}


@router.post("/update_data_lake_results", dependencies=[Depends(verify_api_key)])
def update_data_lake_results(req: UpdateDataLakeResultsRequest):
    updated = 0
    errors = 0

    for row in req.rows:
        try:
            update_data = {}
            if row.result_goal:
                update_data["result_goal"] = row.result_goal
            if row.result_shot:
                update_data["result_shot"] = row.result_shot

            if not update_data:
                continue

            supabase.table("nhl_data_lake").update(update_data).eq("date", row.date).eq(
                "player_id", row.player_id
            ).execute()
            updated += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"   ⚠️ Update data_lake error: {e}")

    return {
        "ok": True,
        "updated": updated,
        "errors": errors,
        "total": len(req.rows),
    }


@router.post("/ingest_suivi_algo", dependencies=[Depends(verify_api_key)])
def ingest_suivi_algo(req: IngestSuiviAlgoRequest):
    supabase_ok = False
    supabase_error = None

    SUIVI_ALGO_COLUMNS = {
        "date",
        "match",
        "type",
        "joueur",
        "pari",
        "cote",
        "resultat",
        "score_reel",
        "id_ref",
    }

    def _suivi_row_for_supabase(row: dict) -> dict:
        out = {k: v for k, v in row.items() if k in SUIVI_ALGO_COLUMNS}
        if "resultat" in out:
            out["résultat"] = out.pop("resultat")
        out["model_version"] = "v1"
        return out

    try:
        data_clean = [_suivi_row_for_supabase(r.dict()) for r in req.rows]
        for i in range(0, len(data_clean), 1000):
            supabase.table("nhl_suivi_algo_clean").upsert(
                data_clean[i : i + 1000], on_conflict="date,match,type,joueur,pari"
            ).execute()
        supabase_ok = True
    except Exception as e:
        supabase_error = str(e)
        print(f"   ⚠️ Supabase Error: {e}")

    return {
        "inserted": len(req.rows),
        "supabase": {"success": supabase_ok, "error": supabase_error},
    }


@router.get("/performance")
def get_nhl_performance(days: int = 30):
    try:
        from datetime import datetime, timedelta, timezone

        cutoff = None
        if days > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        # ── Helper: paginated fetch (Supabase caps at 1000 rows per request) ──
        def _fetch_all(table, select_cols, filters=None, cutoff_date=None):
            """Fetch all rows from a Supabase table, paginating in batches of 1000."""
            all_data = []
            page_size = 1000
            offset = 0
            while True:
                q = supabase.table(table).select(select_cols)
                if filters:
                    for method, args in filters:
                        q = getattr(q, method)(*args)
                if cutoff_date:
                    q = q.gte("date", cutoff_date)
                q = q.order("date", desc=True).range(offset, offset + page_size - 1)
                resp = q.execute()
                batch = resp.data or []
                all_data.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
            return all_data

        # 1. Fetch ALL rows from old table (nhl_suivi_algo_clean)
        rows = _fetch_all(
            "nhl_suivi_algo_clean",
            "date, match, joueur, pari, résultat, proba_predite",
            filters=[("neq", ("résultat", "PENDING"))],
            cutoff_date=cutoff,
        )

        # 2. Fetch from new table (best_bets)
        try:
            raw_bets = _fetch_all(
                "best_bets",
                "date, bet_label, market, result, proba_model",
                filters=[("eq", ("sport", "nhl")), ("neq", ("result", "PENDING"))],
                cutoff_date=cutoff,
            )
        except Exception:
            raw_bets = []

        # Merge new bets into the rows list formatted identically
        for b in raw_bets:
            label = b.get("bet_label") or ""
            # Label format: "Match — Joueur — Pari"
            parts = [p.strip() for p in label.replace(" - ", " — ").split("—")]
            match_str = parts[0] if len(parts) > 0 else ""
            joueur_str = parts[1] if len(parts) > 1 else ""
            pari_str = parts[2] if len(parts) > 2 else b.get("market", "")

            res = b.get("result", "")
            if res == "WIN":
                res = "GAGNÉ"
            elif res == "LOSS":
                res = "PERDU"

            rows.append(
                {
                    "date": b.get("date"),
                    "match": match_str,
                    "joueur": joueur_str,
                    "pari": pari_str,
                    "résultat": res,
                    "proba_predite": b.get("proba_model", 0),
                }
            )

        # ── Classify each row by market type ─────────────────────────
        def _market_type(pari: str) -> str | None:
            p = (pari or "").lower()
            if "but" in p or "goal" in p:
                return "goal"
            if "passe" in p or "assist" in p:
                return "assist"
            if "point" in p:
                return "point"
            if "tir" in p or "shot" in p:
                return "shot"
            return None

        # ── Keep only the TOP 1 player per (date, match, market) ─────
        # Group by (date, match, market), pick the player with highest proba
        from collections import defaultdict

        groups: dict[tuple, list] = defaultdict(list)

        for r in rows:
            res_str = (r.get("résultat") or "").upper()
            if "GAGN" not in res_str and "PERDU" not in res_str:
                continue
            market = _market_type(r.get("pari", ""))
            if not market:
                continue
            day = (r.get("date") or "")[:10]
            match_name = r.get("match", "")
            key = (day, match_name, market)
            groups[key].append(r)

        # For each group, keep only the player with the highest probability
        top1_rows = []
        for key, candidates in groups.items():
            best = max(candidates, key=lambda x: float(x.get("proba_predite") or 0))
            top1_rows.append((key, best))

        # ── Compute stats on top-1 only ──────────────────────────────
        stats = {
            "goal": {"total": 0, "correct": 0, "brier_sum": 0.0},
            "assist": {"total": 0, "correct": 0, "brier_sum": 0.0},
            "point": {"total": 0, "correct": 0, "brier_sum": 0.0},
            "shot": {"total": 0, "correct": 0, "brier_sum": 0.0},
            "all": {"total": 0, "correct": 0, "sum_conf": 0, "brier_sum": 0.0},
        }
        daily = {}

        for (day, _match_name, market), r in top1_rows:
            is_win = "GAGN" in (r.get("résultat") or "").upper()

            stats[market]["total"] += 1
            stats["all"]["total"] += 1
            if is_win:
                stats[market]["correct"] += 1
                stats["all"]["correct"] += 1

            prob = float(r.get("proba_predite") or 50)
            stats["all"]["sum_conf"] += prob

            # Brier score binaire : (proba/100 - outcome)²
            outcome = 1.0 if is_win else 0.0
            brier_match = (prob / 100.0 - outcome) ** 2
            stats[market]["brier_sum"] += brier_match
            stats["all"]["brier_sum"] += brier_match

            if day not in daily:
                daily[day] = {"date": day, "total": 0, "correct": 0}
            daily[day]["total"] += 1
            if is_win:
                daily[day]["correct"] += 1

        def _pct(c, t):
            return round(c / t * 100, 1) if t > 0 else 0

        total_all = stats["all"]["total"]

        # Brier score global (binaire : 0 = parfait, 0.25 = aléatoire)
        brier_global = round(stats["all"]["brier_sum"] / total_all, 4) if total_all > 0 else None

        # Brier par marché
        brier_by_market = {}
        for mkt in ("goal", "assist", "point", "shot"):
            n = stats[mkt]["total"]
            brier_by_market[mkt] = round(stats[mkt]["brier_sum"] / n, 4) if n > 0 else None

        metrics = {
            "days": days,
            "total_matches": total_all,
            "accuracy_goal": _pct(stats["goal"]["correct"], stats["goal"]["total"]),
            "accuracy_assist": _pct(stats["assist"]["correct"], stats["assist"]["total"]),
            "accuracy_point": _pct(stats["point"]["correct"], stats["point"]["total"]),
            "accuracy_shot": _pct(stats["shot"]["correct"], stats["shot"]["total"]),
            "brier_score": brier_global,
            "brier_by_market": brier_by_market,
            "avg_confidence": (
                round(stats["all"]["sum_conf"] / total_all, 1) if total_all > 0 else 0
            ),
            "daily_stats": sorted(daily.values(), key=lambda x: x["date"]),
        }

        return metrics

    except Exception as e:
        logger.error("NHL performance endpoint error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# NHL MATCH TOP PLAYERS
# =============================================================================


@router.get("/match/{fixture_id}/top_players")
def get_nhl_match_top_players(fixture_id: str):
    """
    Return top 5 players per category (goal, assist, point, SOG) for a given NHL fixture.
    Reads from nhl_data_lake for the fixture's date.
    """
    # 1. Get fixture date
    try:
        fixture_data = (
            supabase.table("nhl_fixtures")
            .select("date, home_team, away_team, stats_json")
            .eq("api_fixture_id", fixture_id)
            .limit(1)
            .execute()
            .data
        )
        if not fixture_data:
            # Try by id
            fixture_data = (
                supabase.table("nhl_fixtures")
                .select("date, home_team, away_team, stats_json")
                .eq("id", fixture_id)
                .limit(1)
                .execute()
                .data
            )
        if not fixture_data:
            raise HTTPException(status_code=404, detail="Fixture not found")
        fixture = fixture_data[0]
        match_date = fixture["date"][:10]  # YYYY-MM-DD
        home_team = fixture.get("home_team", "")
        away_team = fixture.get("away_team", "")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("NHL match top players endpoint error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    # 2. Extract players from fixture stats_json
    try:
        stats_json = fixture.get("stats_json") or {}
        rows = stats_json.get("top_players") or []
    except Exception:
        rows = []

    def _top5(rows_sorted: list, prob_key: str) -> list:
        seen = set()
        result = []
        for r in rows_sorted:
            pid = r.get("player_id") or r.get("player_name", "")
            if pid not in seen:
                seen.add(pid)

                # Use ML probability if available, otherwise fallback to heuristics
                if prob_key in r:
                    prob_val = r.get(prob_key, 0)
                elif prob_key == "ml_prob_goal":
                    prob_val = r.get("prob_goal", 0)
                elif prob_key == "ml_prob_assist":
                    prob_val = r.get("prob_assist", 0)
                elif prob_key == "ml_prob_point":
                    prob_val = r.get("prob_point", 0)
                elif prob_key == "ml_prob_shot":
                    prob_val = r.get("prob_shot", 0)
                else:
                    prob_val = 0

                result.append(
                    {
                        "player_id": r.get("player_id", ""),
                        "player_name": r.get("player_name", "Inconnu"),
                        "team": r.get("team", ""),
                        "prob": prob_val,
                        "algo_score_goal": r.get("algo_score_goal", 0),
                        "algo_score_shot": r.get("algo_score_shot", 0),
                    }
                )
            if len(result) >= 5:
                break
        return result

    # Sort by the new ML probabilities or fallback heuristics
    by_goal = sorted(rows, key=lambda r: r.get("ml_prob_goal", r.get("prob_goal", 0)), reverse=True)
    by_shot = sorted(rows, key=lambda r: r.get("ml_prob_shot", r.get("prob_shot", 0)), reverse=True)
    by_point = sorted(
        rows, key=lambda r: r.get("ml_prob_point", r.get("prob_point", 0)), reverse=True
    )
    by_assist = sorted(
        rows, key=lambda r: r.get("ml_prob_assist", r.get("prob_assist", 0)), reverse=True
    )

    return {
        "fixture_id": fixture_id,
        "date": match_date,
        "home_team": home_team,
        "away_team": away_team,
        "top_players": {
            "goal": _top5(by_goal, "ml_prob_goal"),
            "assist": _top5(by_assist, "ml_prob_assist"),
            "point": _top5(by_point, "ml_prob_point"),
            "sog": _top5(by_shot, "ml_prob_shot"),
        },
    }


@router.get("/meta_analysis")
def get_nhl_meta_analysis(date: str = None):
    """Return the DeepThink strategic meta-analysis for today's NHL games.

    Fetches from nhl_data_lake where player_id = 'META_ANALYSIS'.
    """
    if not date:
        date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    # Fetch meta_analysis from nhl_data_lake
    try:
        resp = (
            supabase.table("nhl_data_lake")
            .select("*")
            .eq("player_id", "META_ANALYSIS")
            .eq("date", date)
            .limit(1)
            .execute()
        )
        if resp.data and len(resp.data) > 0:
            row = resp.data[0]
            # Try dedicated column first, then player_name fallback
            analysis = row.get("meta_analysis") or ""
            if not analysis or len(analysis) < 50:
                # Fallback: analysis stored in player_name field
                pname = row.get("player_name", "")
                if pname and len(pname) > 50 and pname != "DeepThink Analysis":
                    analysis = pname
            if analysis and len(analysis) > 50:
                return {"ok": True, "date": date, "analysis": analysis, "source": "deepthink"}
    except Exception:
        pass

    return {"ok": False, "date": date, "analysis": None, "source": None}
