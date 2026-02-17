import os
import math
import datetime
import pickle
import pandas as pd
from typing import List, Optional, Dict, Tuple, Any

from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel

from config import supabase

# Imports NHL Modules
from Projet_Football.nhl.feature_engineering import feature_engineer
from Projet_Football.nhl.calibration import probability_calibrator
from Projet_Football.nhl.schemas import (
    BrainRequest, BrainResponse, BrainPrediction,
    GameWinProbRequest, CalibrateProbaRequest,
    IngestDataLakeRequest, IngestSuiviAlgoRequest,
    UpdateDataLakeResultsRequest, DailyAnalysisRequest
)

# ML Models Import with Fallback
try:
    from Projet_Football.nhl.ml_models import (
        goal_predictor, shot_predictor, point_predictor,
        assist_predictor, load_all_models, ModelBacktester
    )
    ENHANCED_ML_AVAILABLE = True
except ImportError:
    from Projet_Football.nhl.ml_models import goal_predictor, ModelBacktester
    shot_predictor = None
    point_predictor = None
    assist_predictor = None
    load_all_models = None
    ENHANCED_ML_AVAILABLE = False

router = APIRouter(prefix="/nhl", tags=["nhl"])

# --- CONFIGURATION ---
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
MODEL_VERSION = "v31.0.0_ML"


# =============================================================================
# UTILITIES
# =============================================================================

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Vérifie la clé API. BLOQUE si invalide (sauf si non configurée)."""
    if not API_SECRET_KEY:
        return True
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# =============================================================================
# MODEL LOADING
# =============================================================================

_game_win_model = None
_game_win_features = []

def _load_game_win_model():
    """Charge le modèle de probabilité de match si disponible."""
    global _game_win_model, _game_win_features
    model_path = "models/best_game_win_predictor.pkl"
    if os.path.isfile(model_path):
        try:
            with open(model_path, "rb") as f:
                data = pickle.load(f)
            _game_win_model = data.get('model')
            _game_win_features = data.get('feature_names', [])
            metrics = data.get('metrics', {})
            print(f"   ✅ Game model chargé: AUC={metrics.get('roc_auc', 0):.3f}")
        except Exception as e:
            print(f"   ⚠️ Game model non chargé: {e}")

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
    goal_predictor.load("models/best_goal_predictor.pkl")


# =============================================================================
# CALIBRATION
# =============================================================================

def _load_calibration_from_supabase(silent: bool = False) -> Tuple[bool, str, Optional[Dict]]:
    """Charge la calibration depuis Supabase."""
    try:
        response = supabase.table("nhl_suivi_algo_clean")\
            .select("*")\
            .or_("résultat.ilike.%GAGNÉ%,résultat.ilike.%PERDU%,résultat.ilike.%WIN%,résultat.ilike.%LOST%")\
            .order("date", desc=True)\
            .limit(10000)\
            .execute()

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
            clean.append({
                "pari": pari,
                "resultat": resultat,
                "résultat": resultat,
                "proba_predite": row.get("proba_predite"),
                "python_prob": row.get("python_prob"),
                "cote": row.get("cote"),
                "date": row.get("date"),
            })

        if len(clean) < 10:
            return False, f"Not enough data ({len(clean)} rows)", None

        model_training_date = None
        if goal_predictor.model_metadata:
            model_training_date = goal_predictor.model_metadata.get('training_date', '')
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

    for player in req.players:
        raw = player.dict()

        if 'algo_score_goal' not in raw or not raw.get('algo_score_goal'):
            raw['algo_score_goal'] = 50.0
        if 'python_vol' not in raw or not raw.get('python_vol'):
            raw['python_vol'] = player.spg

        # --- GOAL ---
        prob_goal_raw = goal_predictor.predict_proba(raw)
        prob_goal = probability_calibrator.calibrate_probability("GOAL", prob_goal_raw)
        math_prob_goal = round(prob_goal * 100, 1)

        # --- SHOTS ---
        home_factor = 1.05 if player.is_home else 0.95
        opp_factor = clamp(player.opp_shots_allowed_avg / 30.0, 0.8, 1.2)
        lam_shots = player.spg * home_factor * opp_factor

        if ENHANCED_ML_AVAILABLE and shot_predictor and shot_predictor.model is not None:
            raw_prob_shot = shot_predictor.predict_proba(raw)
        else:
            raw_prob_shot = 1.0 - math.exp(-lam_shots)

        cal_prob_shot = probability_calibrator.calibrate_probability("SHOT", raw_prob_shot)
        ratio = cal_prob_shot / max(0.01, raw_prob_shot)
        math_exp_shots = lam_shots * ratio

        # --- POINT ---
        apg = player.apg if player.apg and player.apg > 0 else player.gpg * 0.8

        if ENHANCED_ML_AVAILABLE and point_predictor and point_predictor.model is not None:
            raw_prob_point = point_predictor.predict_proba(raw)
        else:
            raw_prob_point = 1.0 - math.exp(-(player.gpg + apg) * home_factor)

        prob_point = probability_calibrator.calibrate_probability("POINT", raw_prob_point)

        # --- ASSIST ---
        if ENHANCED_ML_AVAILABLE and assist_predictor and assist_predictor.model is not None:
            raw_prob_assist = assist_predictor.predict_proba(raw)
        else:
            raw_prob_assist = 1.0 - math.exp(-apg * home_factor)

        prob_assist = probability_calibrator.calibrate_probability("ASSIST", raw_prob_assist)

        confidence = "high" if prob_goal_raw > 0.4 else ("medium" if prob_goal_raw > 0.2 else "low")

        predictions.append(BrainPrediction(
            id=player.id,
            math_prob_goal=math_prob_goal,
            math_exp_shots=round(math_exp_shots, 2),
            prob_point=round(prob_point * 100, 1),
            prob_assist=round(prob_assist * 100, 1),
            confidence=confidence,
        ))

    return BrainResponse(predictions=predictions)


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

        predictions.append(BrainPrediction(
            id=player.id,
            math_prob_goal=round(prob_goal * 100, 1),
            math_exp_shots=round(exp_shots, 2),
            prob_point=round(prob_point * 100, 1),
            prob_assist=round(prob_assist * 100, 1),
            confidence="high",
        ))

    return BrainResponse(predictions=predictions)

@router.post("/game_win_probability")
def game_win_probability(req: GameWinProbRequest):
    if _game_win_model is not None and _game_win_features:
        try:
            features = {
                'home_gaa': req.home_gaa,
                'away_gaa': req.away_gaa,
                'home_l10_win_pct': req.home_l10,
                'away_l10_win_pct': req.away_l10,
                'home_pts_per_game': req.home_pts_per_game,
                'away_pts_per_game': req.away_pts_per_game,
                'gaa_diff': req.away_gaa - req.home_gaa,
                'form_diff': req.home_l10 - req.away_l10,
                'strength_diff': req.home_pts_per_game - req.away_pts_per_game,
                'home_goals_for_avg': 0.0,
                'away_goals_for_avg': 0.0,
                'home_goals_against_avg': req.home_gaa,
                'away_goals_against_avg': req.away_gaa,
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
            d['ts'] = datetime.datetime.utcnow().isoformat() + "Z"
        for i in range(0, len(data), 1000):
            supabase.table("nhl_data_lake").insert(data[i:i+1000]).execute()
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

            supabase.table("nhl_data_lake")\
                .update(update_data)\
                .eq("date", row.date)\
                .eq("player_id", row.player_id)\
                .execute()
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
    
    SUIVI_ALGO_COLUMNS = {"date", "match", "type", "joueur", "pari", "cote", "resultat", "score_reel", "id_ref"}

    def _suivi_row_for_supabase(row: dict) -> dict:
        out = {k: v for k, v in row.items() if k in SUIVI_ALGO_COLUMNS}
        if "resultat" in out:
            out["résultat"] = out.pop("resultat")
        return out

    try:
        data_clean = [_suivi_row_for_supabase(r.dict()) for r in req.rows]
        for i in range(0, len(data_clean), 1000):
            supabase.table("nhl_suivi_algo_clean").upsert(
                data_clean[i:i+1000],
                on_conflict="date,match,type,joueur,pari"
            ).execute()
        supabase_ok = True
    except Exception as e:
        supabase_error = str(e)
        print(f"   ⚠️ Supabase Error: {e}")

    return {
        "inserted": len(req.rows),
        "supabase": {"success": supabase_ok, "error": supabase_error},
    }


@router.get("/suivi_stats", dependencies=[Depends(verify_api_key)])
def suivi_stats():
    # Implementation simplified for now, as it was quite long in original file
    # and depends on logic that might need specific supabase table structure.
    # We will implement a basic version.
    
    try:
        resp = supabase.table("nhl_suivi_algo_clean") \
            .select("type,\"résultat\"") \
            .or_("résultat.ilike.%GAGNÉ%,résultat.ilike.%PERDU%") \
            .execute()
        
        rows = resp.data or []
        total = len(rows)
        wins = sum(1 for r in rows if "GAGN" in (r.get("résultat") or "").upper())
        
        return {
            "ok": True,
            "total": total,
            "wins": wins,
            "rate": round(wins/total*100, 1) if total > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
