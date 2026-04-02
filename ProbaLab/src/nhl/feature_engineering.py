"""
Feature engineering pour prédictions NHL - Refonte v3.
Utilisé par /brain_enhanced pour les calculs avancés.
"""

import math
from typing import Any


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def build_features(player: dict[str, Any]) -> dict[str, Any]:
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

    # Facteur défensif de base (GAA)
    def_factor = 1.0 + 0.08 * (opp_gaa - 3.0)

    # Facteur gardien (Save % vs Moyenne Ligue)
    # Moyenne ligue SV% ~ 0.903
    opp_sv_pct = float(player.get("opp_sv_pct") or 0.903)
    opp_sv_pct = _clamp(opp_sv_pct, 0.850, 0.950)

    # Chaque écart de .010 par rapport à la moyenne impacte de ~5%
    goalie_factor = 1.0 + (0.903 - opp_sv_pct) * 5.0
    goalie_factor = _clamp(goalie_factor, 0.8, 1.25)

    def_factor = def_factor * goalie_factor
    def_factor = _clamp(def_factor, 0.65, 1.5)

    # Features avancées (si disponibles)
    shooting_pct = float(player.get("shooting_pct") or 0)
    if shooting_pct <= 0 and spg > 0:
        shooting_pct = gpg / (spg + 0.1)

    # Régression du shooting% vers la moyenne (10.8%)
    league_avg_shooting = 0.108
    # Estimation du nombre de tirs pris cette saison
    goals_this_season = float(
        player.get("goals_this_season") or (gpg * 82) / 2
    )  # Approximation si manquant
    shots_taken = goals_this_season / max(shooting_pct, 0.01) if shooting_pct > 0 else 0

    # Formule de régression bayésienne (poids = 150 tirs)
    weight = 150.0
    if shots_taken > 0:
        shooting_pct = ((shooting_pct * shots_taken) + (league_avg_shooting * weight)) / (
            shots_taken + weight
        )
    else:
        shooting_pct = league_avg_shooting

    shooting_pct = _clamp(shooting_pct, 0, 0.5)

    toi_avg = float(player.get("toi_avg") or 18.0)
    pp_toi = float(player.get("pp_toi_avg") or 0)
    team_pp = float(player.get("team_pp_pct") or 0.20)

    # PP TOI Share (fraction of team PP time this player plays)
    pp_share = float(player.get("pp_share") or 0)
    if pp_share <= 0 and pp_toi > 0:
        # Estimate from raw PP TOI: avg team total PP is ~4min/game
        pp_share = _clamp(pp_toi / 4.0, 0, 1.0)

    # Opponent PK L10 estimate and penalty volume
    opp_pk_l10 = float(player.get("opp_pk_l10_est") or 0.80)
    opp_penalty_volume = float(player.get("opp_penalty_volume") or 1.0)

    # Back-to-back / fatigue contextualisée
    is_b2b = bool(player.get("is_back_to_back", False))
    opp_is_b2b = bool(player.get("opp_is_back_to_back", False))
    days_rest = int(player.get("days_rest") or 2)

    if is_b2b and opp_is_b2b:
        fatigue_factor = 0.96
    elif is_b2b:
        fatigue_factor = 0.92
    else:
        fatigue_factor = 1.0 + min(0.03, (days_rest - 1) * 0.01)

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
        "pp_share": pp_share,
        "opp_pk_l10": opp_pk_l10,
        "opp_penalty_volume": opp_penalty_volume,
        "fatigue_factor": fatigue_factor,
    }


def compute_goal_probability(features: dict[str, Any]) -> float:
    """P(marquer au moins 1 but) via Poisson avancé."""
    gpg = features.get("gpg_blend", features["gpg"])
    home = features["home_factor"]
    defn = features["def_factor"]
    fatigue = features.get("fatigue_factor", 1.0)

    # PP bonus: uses PP share, opponent PK L10, and opponent penalty volume
    pp_bonus = 1.0
    pp_share = features.get("pp_share", 0)
    opp_pk_l10 = features.get("opp_pk_l10", 0.80)
    opp_penalty_vol = features.get("opp_penalty_volume", 1.0)

    if pp_share > 0.3 and features.get("team_pp", 0) > 0.18:
        # Base PP bonus from team PP%
        base_pp = 1.0 + (features.get("team_pp", 0.20) - 0.20) * 0.5
        # Scale by how bad the opponent's PK is (worse PK = bigger boost)
        pk_weakness = 1.0 + (0.80 - opp_pk_l10) * 2.0
        pk_weakness = _clamp(pk_weakness, 0.85, 1.30)
        # Scale by opponent penalty volume
        pp_bonus = base_pp * pk_weakness * _clamp(opp_penalty_vol, 0.9, 1.2)
        # Scale by player's PP share involvement
        pp_bonus = 1.0 + (pp_bonus - 1.0) * _clamp(pp_share, 0.1, 1.0)

    lam = gpg * home * defn * fatigue * pp_bonus
    raw = 1.0 - math.exp(-lam) if lam > 0 else 0.0
    return _clamp(raw, 0.01, 0.99)


def compute_point_probability(features: dict[str, Any]) -> float:
    """P(au moins 1 point) via Poisson (buts + assists)."""
    gpg = features.get("gpg_blend", features["gpg"])
    apg = features["apg"]
    home = features["home_factor"]
    defn = features["def_factor"]
    fatigue = features.get("fatigue_factor", 1.0)

    lam = (gpg + apg) * home * defn * fatigue
    raw = 1.0 - math.exp(-lam) if lam > 0 else 0.0
    return _clamp(raw, 0.01, 0.99)


def compute_assist_probability(features: dict[str, Any]) -> float:
    """P(au moins 1 assist)."""
    apg = features["apg"]
    home = features["home_factor"]
    defn = features["def_factor"]
    fatigue = features.get("fatigue_factor", 1.0)

    lam = apg * home * defn * fatigue
    raw = 1.0 - math.exp(-lam) if lam > 0 else 0.0
    return _clamp(raw, 0.01, 0.99)


def compute_shot_expectation(features: dict[str, Any]) -> float:
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
