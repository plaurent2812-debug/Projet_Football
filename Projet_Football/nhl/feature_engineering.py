"""
Feature engineering pour prédictions NHL - Refonte v3.
Utilisé par /brain_enhanced pour les calculs avancés.
"""
from typing import Any, Dict
import math


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def build_features(player: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construit un dictionnaire de features à partir des données joueur.
    Prend en compte les stats enrichies si disponibles.
    """
    gpg = float(player.get("gpg") or 0)
    spg = float(player.get("spg") or 0)
    apg = float(player.get("apg") or 0) or gpg * 0.8
    is_home = bool(player.get("is_home", False))
    opp_gaa = float(player.get("opp_gaa") or 3.0)
    opp_shots = float(player.get("opp_shots_allowed_avg") or 30.0)

    # Facteurs contextuels
    home_factor = 1.05 if is_home else 0.95
    opp_factor = _clamp(opp_shots / 30.0, 0.8, 1.2)
    def_factor = 1.0 + 0.08 * (opp_gaa - 3.0)
    def_factor = _clamp(def_factor, 0.7, 1.4)

    # Features avancées (si disponibles)
    shooting_pct = float(player.get("shooting_pct") or 0)
    if shooting_pct <= 0 and spg > 0:
        shooting_pct = gpg / (spg + 0.1)
    shooting_pct = _clamp(shooting_pct, 0, 0.5)

    toi_avg = float(player.get("toi_avg") or 18.0)
    pp_toi = float(player.get("pp_toi_avg") or 0)
    team_pp = float(player.get("team_pp_pct") or 0.20)

    # Back-to-back / fatigue
    is_b2b = bool(player.get("is_back_to_back", False))
    days_rest = int(player.get("days_rest") or 2)
    fatigue_factor = 0.92 if is_b2b else (1.0 + min(0.03, (days_rest - 1) * 0.01))

    # Forme récente (L5)
    gpg_l5 = float(player.get("gpg_l5") or gpg)
    spg_l5 = float(player.get("spg_l5") or spg)

    # Momentum : pondérer forme récente vs saison
    gpg_blend = 0.6 * gpg_l5 + 0.4 * gpg
    spg_blend = 0.6 * spg_l5 + 0.4 * spg

    return {
        "gpg": gpg,
        "spg": spg,
        "apg": apg,
        "gpg_blend": gpg_blend,
        "spg_blend": spg_blend,
        "is_home": is_home,
        "opp_gaa": opp_gaa,
        "opp_shots_allowed_avg": opp_shots,
        "home_factor": home_factor,
        "opp_factor": opp_factor,
        "def_factor": def_factor,
        "shooting_pct": shooting_pct,
        "toi_avg": toi_avg,
        "pp_toi": pp_toi,
        "team_pp": team_pp,
        "fatigue_factor": fatigue_factor,
    }


def compute_goal_probability(features: Dict[str, Any]) -> float:
    """P(marquer au moins 1 but) via Poisson avancé."""
    gpg = features.get("gpg_blend", features["gpg"])
    home = features["home_factor"]
    defn = features["def_factor"]
    fatigue = features.get("fatigue_factor", 1.0)

    # Bonus PP si bon jeu de puissance
    pp_bonus = 1.0
    if features.get("pp_toi", 0) > 3.0 and features.get("team_pp", 0) > 0.22:
        pp_bonus = 1.05

    lam = gpg * home * defn * fatigue * pp_bonus
    raw = 1.0 - math.exp(-lam) if lam > 0 else 0.0
    return _clamp(raw, 0.01, 0.99)


def compute_point_probability(features: Dict[str, Any]) -> float:
    """P(au moins 1 point) via Poisson (buts + assists)."""
    gpg = features.get("gpg_blend", features["gpg"])
    apg = features["apg"]
    home = features["home_factor"]
    defn = features["def_factor"]
    fatigue = features.get("fatigue_factor", 1.0)

    lam = (gpg + apg) * home * defn * fatigue
    raw = 1.0 - math.exp(-lam) if lam > 0 else 0.0
    return _clamp(raw, 0.01, 0.99)


def compute_assist_probability(features: Dict[str, Any]) -> float:
    """P(au moins 1 assist)."""
    apg = features["apg"]
    home = features["home_factor"]
    defn = features["def_factor"]
    fatigue = features.get("fatigue_factor", 1.0)

    lam = apg * home * defn * fatigue
    raw = 1.0 - math.exp(-lam) if lam > 0 else 0.0
    return _clamp(raw, 0.01, 0.99)


def compute_shot_expectation(features: Dict[str, Any]) -> float:
    """Espérance du nombre de tirs."""
    spg = features.get("spg_blend", features["spg"])
    home = features["home_factor"]
    opp = features["opp_factor"]
    fatigue = features.get("fatigue_factor", 1.0)
    return spg * home * opp * fatigue


class _FeatureEngineer:
    build_features = staticmethod(build_features)
    compute_goal_probability = staticmethod(compute_goal_probability)
    compute_point_probability = staticmethod(compute_point_probability)
    compute_assist_probability = staticmethod(compute_assist_probability)
    compute_shot_expectation = staticmethod(compute_shot_expectation)


feature_engineer = _FeatureEngineer()
