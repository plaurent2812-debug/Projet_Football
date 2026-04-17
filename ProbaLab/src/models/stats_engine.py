from __future__ import annotations

"""
stats_engine.py — Moteur statistique avancé.

Calcule des probabilités basées sur :
  1. Modèle de Poisson (force attaque/défense)
  2. Système ELO interne
  3. Forme récente (pondération exponentielle)
  4. Jours de repos / congestion
  5. Enjeu du match (classement, titre, relégation)
  6. Régression vers la moyenne
  7. Head-to-Head historique
  8. Avantage domicile (granulaire, par équipe)
  9. Impact arbitre (cartons, pénaltys)
  10. Météo
  11. Blessures joueurs clés
  12. Calibration via cotes bookmakers
"""
import math
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from scipy.stats import poisson

from src.config import SEASON, supabase
from src.constants import (
    AVG_ATTACKER_FOULS_DRAWN_PER_90,
    AVG_DEFENDER_FOULS_PER_90,
    BASE_PENALTY_RATE,
    COMPETITION_XG_FACTOR,
    CROSS_LEAGUE_IDS,
    DEFAULT_ELO,
    DIXON_COLES_RHO,
    DIXON_COLES_RHO_BY_LEAGUE,
    DRAW_FACTOR,
    DRAW_FACTOR_BY_LEAGUE,
    ELO_DECAY_RATE,
    ELO_DRAW_DECAY_RATE,
    EURO_COMP_DRAW_BOOST,
    FORM_DECAY_LONG,
    FORM_LOOKBACK_LONG,
    FORM_WEIGHT_LONG,
    FORM_WEIGHT_SHORT,
    HOME_ELO_ADVANTAGE,
    HOME_ELO_ADVANTAGE_BY_LEAGUE,
    HOME_XG_BONUS,
    K_FACTOR,
    K_FACTOR_BY_LEAGUE,
    KELLY_FRACTION,
    KELLY_MAX_BET_FRACTION,
    MIN_VALUE_EDGE,
    PROB_1X2_CEIL,
    PROB_1X2_FLOOR,
    PROB_BTTS_CEIL,
    PROB_BTTS_FLOOR,
    PROB_OVER25_CEIL,
    PROB_OVER25_FLOOR,
    STAKES_DRAW_BOOST,
    WEIGHT_ELO_NO_MARKET,
    WEIGHT_ML,
    WEIGHT_POISSON_NO_MARKET,
    WEIGHT_STATS_VS_ML,
    XG_CEIL,
    XG_FLOOR,
)


# Import calibration — activée dynamiquement selon le volume de données disponibles.
# Platt scaling : actif dès 100 prédictions évaluées.
# Isotonic regression : actif dès 500 prédictions (évite la "fonction en escalier").
def is_calibration_available() -> bool:
    """Check if enough data exists for probability calibration.

    Called at prediction time rather than import time so the check
    reflects the current data volume in ``prediction_results``.

    Returns:
        True when at least 100 evaluated predictions exist, False otherwise.
    """
    try:
        resp = supabase.table("prediction_results").select("id").limit(100).execute()
        return len(resp.data) >= 100
    except Exception:
        return False


# Module-level sentinel kept for backward compatibility with @patch in tests.
# Do NOT read this constant in business logic — call is_calibration_available() instead.
CALIBRATION_AVAILABLE: bool = False

# Import modèles ML entraînés (optionnel)
try:
    from src.models.ml_predictor import get_ml_predictions, load_models

    ML_AVAILABLE = load_models()
except ImportError:
    ML_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════
#  0. BLEND WEIGHTS HELPER
# ═══════════════════════════════════════════════════════════════════


def _get_blend_weights(has_odds: bool, has_ml: bool) -> tuple[float, float, float]:
    """Return adaptive (weight_poisson, weight_elo, weight_market) for step 7.

    These weights govern the Poisson/ELO/Market blend that produces the
    base 1X2 probabilities *before* the ML XGBoost override at step 9.
    When ML is available, step 9 will blend again (60% base + 40% ML),
    so we can afford to lean more on ELO/Market at step 7.

    Scenarios
    ---------
    has_odds=True,  has_ml=True  : Market provides anchor; ML adjusts later.
                                   Reduce Poisson share slightly → more weight
                                   on the market signal which is already
                                   forward-looking.
    has_odds=True,  has_ml=False : Standard blend with full market weight.
    has_odds=False, has_ml=True  : No market; ML will correct heavily.
                                   Use a balanced Poisson/ELO split.
    has_odds=False, has_ml=False : Pure statistical blend; trust Poisson more.

    Returns:
        ``(w_poisson, w_elo, w_market)`` summing to 1.0.
    """
    if has_odds and has_ml:
        # Market + ML available: market is the strongest signal, Poisson/ELO
        # serve as sanity checks. ML (50% in next step) does fine-tuning.
        return (0.25, 0.15, 0.60)
    elif has_odds:
        # Market available but no ML: market-heavy blend
        return (0.35, 0.20, 0.45)
    elif has_ml:
        # No market, but ML will adjust: balanced Poisson/ELO, no market term
        return (WEIGHT_POISSON_NO_MARKET, WEIGHT_ELO_NO_MARKET, 0.0)
    else:
        # Purely statistical: trust Poisson more, ELO as stabiliser
        return (WEIGHT_POISSON_NO_MARKET, WEIGHT_ELO_NO_MARKET, 0.0)


# ═══════════════════════════════════════════════════════════════════
#  1. MODÈLE DE POISSON
# ═══════════════════════════════════════════════════════════════════


def dixon_coles_correction(
    h: int, a: int, lambda_h: float, lambda_a: float, rho: float = DIXON_COLES_RHO
) -> float:
    """Compute the Dixon-Coles correction factor for a single (h, a) cell.

    Note: This function is kept for unit-testing and external callers.
    The main ``poisson_grid`` applies the corrections inline (vectorized)
    for performance.

    Returns:
        Multiplicative correction factor (close to 1.0).
    """
    if h == 0 and a == 0:
        return 1 - lambda_h * lambda_a * rho
    elif h == 0 and a == 1:
        return 1 + lambda_h * rho
    elif h == 1 and a == 0:
        return 1 + lambda_a * rho
    elif h == 1 and a == 1:
        return 1 - rho
    return 1.0


def poisson_grid(
    xg_home: float, xg_away: float, max_goals: int = 7, league_id: int | None = None
) -> dict[str, int | float | str]:
    """Build the Dixon-Coles adjusted Poisson probability grid.

    Computes match-outcome probabilities (1X2, BTTS, over/under, double
    chance) from Poisson distributions for each team's goals, corrected
    with the Dixon-Coles correlation factor for low-scoring outcomes.

    Improvements vs. independent Poisson:
    - Per-league rho (DIXON_COLES_RHO_BY_LEAGUE): accounts for each league's
      specific defensive style and draw rate rather than a global -0.13.
    - Draw calibration: after building the grid, gently scales the diagonal
      to match the league's historical draw rate (DRAW_FACTOR_BY_LEAGUE).
      This corrects the known tendency of Poisson to under-predict draws
      in tight, tactical leagues (Serie A, CL).

    Args:
        xg_home: Expected goals for the home team.
        xg_away: Expected goals for the away team.
        max_goals: Upper bound (exclusive) on goals per team in the grid.
        league_id: Optional league identifier for per-league rho and draw
            calibration.  Falls back to global defaults when ``None``.

    Returns:
        Dictionary containing rounded percentage probabilities for every
        market (home/draw/away, BTTS, over lines, double chance), the most
        likely correct score, and the adjusted xG values used.
    """
    # Per-league base rho (Dixon-Coles correlation parameter)
    # More negative = stronger correction for low-scoring cells (0-0, 1-1…)
    base_rho = (
        DIXON_COLES_RHO_BY_LEAGUE.get(league_id, DIXON_COLES_RHO) if league_id else DIXON_COLES_RHO
    )
    xg_total = xg_home + xg_away
    # Smooth rho scaling: linear interpolation between 2.0 and 3.5 xG total
    # (avoids discontinuous jumps at the thresholds)
    if xg_total < 2.0:
        rho = base_rho * 1.3
    elif xg_total > 3.5:
        rho = base_rho * 0.7
    else:
        # Linear interpolation: 1.3 at 2.0 → 0.7 at 3.5 (continuous)
        scale = 1.3 - 0.6 * (xg_total - 2.0) / 1.5
        rho = base_rho * scale

    # ── Vectorized Poisson grid (replaces double-loop) ────────
    goals = np.arange(max_goals)
    pmf_home = poisson.pmf(goals, xg_home)  # shape (max_goals,)
    pmf_away = poisson.pmf(goals, xg_away)  # shape (max_goals,)
    grid = np.outer(pmf_home, pmf_away)  # shape (max_goals, max_goals)

    # Dixon-Coles correction — only affects 4 low-score cells
    grid[0, 0] *= max(0, 1 - xg_home * xg_away * rho)
    grid[0, 1] *= max(0, 1 + xg_home * rho)
    grid[1, 0] *= max(0, 1 + xg_away * rho)
    grid[1, 1] *= max(0, 1 - rho)

    # Normaliser la grille — la troncature à max_goals perd de la masse
    grid_sum = grid.sum()
    if grid_sum > 0:
        grid /= grid_sum

    # ── Draw calibration (per-league, iterative) ─────────────────
    # Poisson tends to under-predict draws in tactical leagues (Serie A, CL).
    # Iterative correction: each pass applies a capped diagonal scaling,
    # renormalizes, then checks if the target is reached. 3 passes suffice
    # because the cap (±20%) is relaxed enough for convergence.
    target_draw = (
        DRAW_FACTOR_BY_LEAGUE.get(league_id, DRAW_FACTOR) if league_id is not None else None
    )
    if target_draw is not None:
        for _draw_pass in range(3):
            predicted_draw = float(np.trace(grid))
            if predicted_draw < 0.01:
                break
            error = abs(target_draw - predicted_draw)
            if error < 0.005:  # Within 0.5% — converged
                break
            correction = target_draw / predicted_draw
            correction = max(0.80, min(1.20, correction))  # ±20% per pass for better convergence
            np.fill_diagonal(grid, np.diag(grid) * correction)
            grid /= grid.sum()  # Renormalise after diagonal shift

    # ── Vectorized market extraction (replaces 3 double-loops) ─
    # 1X2
    home_win = float(np.tril(grid, k=-1).sum())  # h > a
    draw = float(np.trace(grid))  # h == a
    away_win = float(np.triu(grid, k=1).sum())  # h < a

    # BTTS: both teams score (exclude row 0 and column 0)
    btts = float(grid[1:, 1:].sum())

    # Over lines: total goals = h + a, via broadcasting
    total_goals = goals[:, None] + goals[None, :]  # shape (max_goals, max_goals)
    over_05 = float(grid[total_goals > 0].sum())
    over_15 = float(grid[total_goals > 1].sum())
    over_25 = float(grid[total_goals > 2].sum())
    over_35 = float(grid[total_goals > 3].sum())

    # Score exact le plus probable
    best_h, best_a = np.unravel_index(grid.argmax(), grid.shape)
    correct_score = f"{best_h}-{best_a}"
    correct_score_prob = float(grid[best_h, best_a])

    # ── Combined markets (computed directly from grid) ────────────
    # "DC 1X + Plus de 1.5" = home wins OR draws AND total goals >= 2
    dc1x_over15 = float(grid[(total_goals >= 2) & (goals[:, None] >= goals[None, :])].sum())
    # "DC X2 + Plus de 1.5" = away wins OR draws AND total goals >= 2
    dcx2_over15 = float(grid[(total_goals >= 2) & (goals[None, :] >= goals[:, None])].sum())

    # ── Handicaps asiatiques (vectorized) ─────────────────────
    diff_grid = goals[:, None] - goals[None, :]  # h - a
    ah_home_minus_05 = home_win  # Home wins outright
    ah_home_minus_15 = float(grid[diff_grid >= 2].sum())  # Win by 2+
    ah_home_push_10 = float(grid[diff_grid == 1].sum())  # Win by exactly 1
    ah_home_minus_10 = ah_home_minus_15  # Win by 2+ (full)
    # AH -1.0: full win at diff>=2, half win at diff==1 (push = refund)
    ah_home_minus_10_effective = ah_home_minus_10 + ah_home_push_10 * 0.5

    # ── Enjeux supplémentaires (Clean Sheet, BTTS + Over) ────────
    proba_cs_home = float(grid[:, 0].sum())  # Away scores 0
    proba_cs_away = float(grid[0, :].sum())  # Home scores 0
    proba_btts_over25 = float(grid[1:, 1:][total_goals[1:, 1:] > 2].sum())

    # Force 1X2 sum == 100 (independent rounding can give 99 or 101)
    p_home = round(home_win * 100)
    p_draw = round(draw * 100)
    p_away = 100 - p_home - p_draw

    return {
        "proba_home": p_home,
        "proba_draw": p_draw,
        "proba_away": p_away,
        "proba_btts": round(btts * 100),
        "proba_btts_over25": round(proba_btts_over25 * 100),
        "proba_cs_home": round(proba_cs_home * 100),
        "proba_cs_away": round(proba_cs_away * 100),
        "proba_over_05": round(over_05 * 100),
        "proba_over_15": round(over_15 * 100),
        "proba_over_25": round(over_25 * 100),
        "proba_over_35": round(over_35 * 100),
        "proba_dc_1x": round((home_win + draw) * 100),
        "proba_dc_x2": round((draw + away_win) * 100),
        "proba_dc_12": round((home_win + away_win) * 100),
        "proba_dc1x_over15": round(dc1x_over15 * 100),
        "proba_dcx2_over15": round(dcx2_over15 * 100),
        "xg_home": round(xg_home, 2),
        "xg_away": round(xg_away, 2),
        "correct_score": correct_score,
        "proba_correct_score": round(correct_score_prob * 100, 1),
        # Handicaps asiatiques
        "ah_home_minus_05": round(ah_home_minus_05 * 100),
        "ah_home_minus_10": round(ah_home_minus_10_effective * 100),
        "ah_home_minus_15": round(ah_home_minus_15 * 100),
        "ah_away_plus_05": round((1 - ah_home_minus_05) * 100),
        "ah_away_plus_10": round((1 - ah_home_minus_10_effective) * 100),
        "ah_away_plus_15": round((1 - ah_home_minus_15) * 100),
    }


def calculate_team_strengths(league_id: int) -> dict | None:
    """Calculate relative attack and defence strengths for every team in a league.

    Strengths are expressed as ratios to the league average (home and away
    separately), following the Dixon–Coles approach.

    Args:
        league_id: API identifier of the league/competition.

    Returns:
        Dictionary with ``"strengths"`` (per-team attack/defence ratios),
        ``"league_avg_home"`` and ``"league_avg_away"`` averages, or
        ``None`` if insufficient data is available.
    """
    # ── Option 1 : Récupérer TOUS les matchs de la saison pour l'itération bayésienne ──
    # 1. Obtenir les IDs des matchs terminés pour cette ligue
    fixtures_resp = (
        supabase.table("fixtures")
        .select("api_fixture_id")
        .eq("league_id", league_id)
        .in_("status", ["FT", "AET", "PEN"])
        .execute()
    )
    if not fixtures_resp.data:
        return None

    fixture_ids = [f["api_fixture_id"] for f in fixtures_resp.data]

    # Fetch only relevant match_team_stats rows using chunked in_() queries
    # (Supabase has a ~100-200 element limit on in_(), so we chunk)
    CHUNK_SIZE = 100
    all_mts = []
    for i in range(0, len(fixture_ids), CHUNK_SIZE):
        chunk = fixture_ids[i : i + CHUNK_SIZE]
        chunk_resp = (
            supabase.table("match_team_stats")
            .select("fixture_api_id, team_api_id, expected_goals")
            .in_("fixture_api_id", chunk)
            .execute()
        )
        if chunk_resp.data:
            all_mts.extend(chunk_resp.data)

    if not all_mts:
        return None

    # Grouper par match
    matches = {}
    for row in all_mts:
        fid = row["fixture_api_id"]
        if row["expected_goals"] is not None:
            if fid not in matches:
                matches[fid] = []
            matches[fid].append(row)

    # Filtre les matchs où on a bien les 2 équipes
    valid_fixtures = [m for m in matches.values() if len(m) == 2]

    if len(valid_fixtures) < 10:
        return None

    # Moyennes de la ligue
    total_xg = sum(sum(team["expected_goals"] for team in match) for match in valid_fixtures)
    total_matches = len(valid_fixtures)
    league_avg_xg_scored = (total_xg / 2.0) / total_matches

    # 1. Initialiser les forces à 1.0 et compiler les stats brutes (For/Against) vs (Opponents)
    teams_stats = {}
    for match in valid_fixtures:
        t1, t2 = match[0], match[1]

        tid1, xg1 = t1["team_api_id"], t1["expected_goals"]
        tid2, xg2 = t2["team_api_id"], t2["expected_goals"]

        for tid in (tid1, tid2):
            if tid not in teams_stats:
                teams_stats[tid] = {
                    "xg_for": [],
                    "xg_against": [],
                    "opponents": [],
                    "atk": 1.0,
                    "def": 1.0,
                }

        teams_stats[tid1]["xg_for"].append(xg1 / max(league_avg_xg_scored, 0.1))
        teams_stats[tid1]["xg_against"].append(xg2 / max(league_avg_xg_scored, 0.1))
        teams_stats[tid1]["opponents"].append(tid2)

        teams_stats[tid2]["xg_for"].append(xg2 / max(league_avg_xg_scored, 0.1))
        teams_stats[tid2]["xg_against"].append(xg1 / max(league_avg_xg_scored, 0.1))
        teams_stats[tid2]["opponents"].append(tid1)

    # 2. Itération Bayésienne (Schedule Adjustment / Smoothing)
    # Up to 10 iterations with early stop on convergence.
    # xG généré par A = Atk_A * Def_B -> Donc Atk_A = xG généré / Def_B
    for _iteration in range(10):
        max_delta = 0.0
        new_atk = {}
        new_def = {}
        for tid, stats in teams_stats.items():
            if not stats["opponents"]:
                continue

            # Nouvelle force d'attaque = Moyenne des (xG_marqués / Defense_Adversaire)
            opp_def_sum = sum(teams_stats[opp]["def"] for opp in stats["opponents"])
            opp_atk_sum = sum(teams_stats[opp]["atk"] for opp in stats["opponents"])

            # Lissage bayésien avec un prior de 1.0 pour éviter les divisions par zéro sur ptits échantillons
            prior_weight = 3.0

            total_atk_val = sum(xg for xg in stats["xg_for"]) + (1.0 * prior_weight)
            total_atk_div = opp_def_sum + prior_weight
            new_atk[tid] = total_atk_val / total_atk_div

            # Nouvelle force de défense = Moyenne des (xG_concédés / Attaque_Adversaire)
            total_def_val = sum(xg for xg in stats["xg_against"]) + (1.0 * prior_weight)
            total_def_div = opp_atk_sum + prior_weight
            new_def[tid] = total_def_val / total_def_div

        # Normaliser pour que la moyenne reste autour de 1.0
        avg_atk = sum(new_atk.values()) / max(len(new_atk), 1)
        avg_def = sum(new_def.values()) / max(len(new_def), 1)

        # Check convergence before updating
        for tid in new_atk:
            norm_atk = new_atk[tid] / avg_atk
            norm_def = new_def[tid] / avg_def
            delta_atk = abs(norm_atk - teams_stats[tid].get("atk", 1.0))
            delta_def = abs(norm_def - teams_stats[tid].get("def", 1.0))
            max_delta = max(max_delta, delta_atk, delta_def)

        for tid in new_atk:
            teams_stats[tid]["atk"] = new_atk[tid] / avg_atk
            teams_stats[tid]["def"] = new_def[tid] / avg_def

        if max_delta < 0.005:  # Converged
            break

    # Format output (On simule Home/Away différencié plus tard si on a + de données)
    strengths = {}
    for tid, stats in teams_stats.items():
        mp = len(stats["opponents"])
        raw_atk = stats["atk"]
        raw_def = stats["def"]

        strengths[tid] = {
            "home_attack": regress_to_mean(raw_atk, mp, 1.0),
            "home_defense": regress_to_mean(raw_def, mp, 1.0),
            "away_attack": regress_to_mean(raw_atk, mp, 1.0),
            "away_defense": regress_to_mean(raw_def, mp, 1.0),
            "home_advantage": HOME_XG_BONUS,
        }

    return {
        "strengths": strengths,
        "league_avg_home": league_avg_xg_scored * HOME_XG_BONUS,
        "league_avg_away": league_avg_xg_scored * (2.0 - HOME_XG_BONUS),
        "avg_matches_played": total_matches / max(len(teams_stats) / 2.0, 1.0),
    }

    # Map cup/cross-league IDs to their domestic league equivalents.
    # The teams table sometimes stores the cup league_id instead of
    # the domestic one, so we normalise here.


_CUP_TO_DOMESTIC: dict[int, int] = {
    2: None,  # Champions League — no single domestic league
    3: None,  # Europa League
    45: 39,  # FA Cup → Premier League
    66: 61,  # Coupe de France → Ligue 1
    143: 140,  # Copa del Rey → La Liga
    137: 135,  # Coppa Italia → Serie A
    81: 78,  # DFB-Pokal → Bundesliga
}


_DOMESTIC_LEAGUES: set[int] = {39, 61, 62, 78, 135, 140}  # PL, L1, L2, BuLi, Serie A, Liga


def _get_domestic_league_id(team_api_id: int) -> int | None:
    """Look up a team's domestic league.

    Strategy:
      1. Check teams.league_id → if it's a known domestic league, return it.
      2. If it's a cup/European comp, map via _CUP_TO_DOMESTIC.
      3. If still None (team stored as CL/EL), infer from the team's
         most-played domestic league in recent fixtures.

    Returns:
        The domestic league_id, or None if not found.
    """
    resp = supabase.table("teams").select("league_id").eq("api_id", team_api_id).limit(1).execute()
    if not resp.data:
        return None
    lid = resp.data[0].get("league_id")

    # Direct domestic league
    if lid in _DOMESTIC_LEAGUES:
        return lid

    # Known cup → domestic mapping
    if lid in _CUP_TO_DOMESTIC:
        mapped = _CUP_TO_DOMESTIC[lid]
        if mapped is not None:
            return mapped

    # Fallback: infer from fixtures — find the league where this team
    # has played the most matches (excluding European comps and cups)
    try:
        from src.config import logger

        team_name_resp = (
            supabase.table("teams").select("name").eq("api_id", team_api_id).limit(1).execute()
        )
        if not team_name_resp.data:
            return None
        team_name = team_name_resp.data[0]["name"]

        recent = (
            supabase.table("fixtures")
            .select("league_id")
            .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
            .not_.in_("league_id", list(CROSS_LEAGUE_IDS))
            .limit(20)
            .execute()
            .data
            or []
        )
        if recent:
            from collections import Counter

            league_counts = Counter(f["league_id"] for f in recent if f.get("league_id"))
            if league_counts:
                best_lid = league_counts.most_common(1)[0][0]
                logger.info(
                    f"  ↪ Inferred domestic league for {team_name} (id={team_api_id}): {best_lid}"
                )
                return best_lid
    except Exception:
        pass

    return None


def calculate_xg(
    home_team_id: int,
    away_team_id: int,
    league_data: dict | None,
    adjustments: dict | None = None,
) -> tuple[float, float]:
    """Calculate expected goals for a fixture.

    Formula:
        ``xG_home = home_attack * away_defense * league_avg * home_bonus * adjustments``

    When teams are not found in the league's strength data (e.g. in
    Champions League), falls back to each team's domestic league strengths
    and cross-references them to produce unique xG per match.

    Args:
        home_team_id: API identifier of the home team.
        away_team_id: API identifier of the away team.
        league_data: Output of :func:`calculate_team_strengths`, or ``None``.
        adjustments: Optional multipliers (keys ``"home_factor"`` /
            ``"away_factor"``) for form, rest, etc.

    Returns:
        Tuple ``(xg_home, xg_away)`` clamped between ``XG_FLOOR`` and
        ``XG_CEIL``.
    """
    from src.config import logger
    from src.constants import XG_FALLBACK_AWAY, XG_FALLBACK_HOME

    home_s = None
    away_s = None
    home_league_data = None
    away_league_data = None

    # ── Try league-level strengths first (domestic league matches) ──
    if league_data:
        strengths = league_data["strengths"]
        home_s = strengths.get(home_team_id)
        away_s = strengths.get(away_team_id)

    # ── Fallback: use each team's domestic league strengths ──────
    # This is critical for CL/EL/cup matches where league_data is None
    # or the team isn't found in the competition's strength table.
    if not home_s and home_team_id:
        domestic_lid = _get_domestic_league_id(home_team_id)
        if domestic_lid:
            home_league_data = calculate_team_strengths(domestic_lid)
            if home_league_data:
                home_s = home_league_data["strengths"].get(home_team_id)
                logger.info(f"  ↪ Forces domestiques {home_team_id}: league {domestic_lid}")

    if not away_s and away_team_id:
        domestic_lid = _get_domestic_league_id(away_team_id)
        if domestic_lid:
            away_league_data = calculate_team_strengths(domestic_lid)
            if away_league_data:
                away_s = away_league_data["strengths"].get(away_team_id)
                logger.info(f"  ↪ Forces domestiques {away_team_id}: league {domestic_lid}")

    # If still missing after all lookups, use ELO-based xG estimation
    # instead of flat 1.3/1.1 defaults (which produce undifferentiated probas)
    if not home_s or not away_s:
        try:
            elos_resp = (
                supabase.table("team_elo")
                .select("team_api_id, elo_rating")
                .in_("team_api_id", [home_team_id, away_team_id])
                .execute()
                .data
                or []
            )
            elo_lookup = {e["team_api_id"]: e["elo_rating"] for e in elos_resp}
            h_elo = elo_lookup.get(home_team_id, DEFAULT_ELO)
            a_elo = elo_lookup.get(away_team_id, DEFAULT_ELO)

            # ELO-based xG: use expected score to scale around league average ~1.3 goals
            avg_goals = 1.30
            h_exp = elo_expected(h_elo + HOME_ELO_ADVANTAGE, a_elo)
            a_exp = 1.0 - h_exp
            # Scale: favorite gets more xG, underdog gets less
            # h_exp ~0.65 for a 200-ELO advantage → xG ~1.69 vs 0.91
            xg_h = avg_goals * (h_exp / 0.5) * HOME_XG_BONUS
            xg_a = avg_goals * (a_exp / 0.5) * (2.0 - HOME_XG_BONUS)

            xg_h = max(XG_FLOOR, min(XG_CEIL, xg_h))
            xg_a = max(XG_FLOOR, min(XG_CEIL, xg_a))

            logger.info(
                f"  ↪ ELO-based xG for {home_team_id} vs {away_team_id}: "
                f"ELO {h_elo:.0f}-{a_elo:.0f} → xG {xg_h:.2f}-{xg_a:.2f}"
            )
            return xg_h, xg_a
        except Exception:
            pass
        logger.warning(
            f"  ⚠ xG fallback pour {home_team_id} vs {away_team_id} (données insuffisantes)"
        )
        return XG_FALLBACK_HOME, XG_FALLBACK_AWAY

    # ── Determine league context for xG baseline ──────────────────
    if home_league_data or away_league_data:
        # Cross-league: average both teams' domestic league contexts
        src_home = home_league_data or away_league_data or league_data
        src_away = away_league_data or home_league_data or league_data
        league_avg_home = (src_home["league_avg_home"] + src_away["league_avg_home"]) / 2.0
        league_avg_away = (src_home["league_avg_away"] + src_away["league_avg_away"]) / 2.0
    elif league_data:
        league_avg_home = league_data["league_avg_home"]
        league_avg_away = league_data["league_avg_away"]
    else:
        # No league context at all — use reasonable defaults
        league_avg_home = XG_FALLBACK_HOME
        league_avg_away = XG_FALLBACK_AWAY

    # Avantage domicile spécifique à l'équipe, ou la moyenne de la ligue si manquant
    home_bonus = home_s.get("home_advantage", HOME_XG_BONUS)

    xg_home = home_s["home_attack"] * away_s["away_defense"] * league_avg_home * home_bonus
    xg_away = away_s["away_attack"] * home_s["home_defense"] * league_avg_away

    # Appliquer les ajustements (forme, repos, etc.)
    if adjustments:
        xg_home *= adjustments.get("home_factor", 1.0)
        xg_away *= adjustments.get("away_factor", 1.0)

    # Limiter les valeurs extrêmes
    xg_home = max(XG_FLOOR, min(xg_home, XG_CEIL))
    xg_away = max(XG_FLOOR, min(xg_away, XG_CEIL))

    return xg_home, xg_away


# ═══════════════════════════════════════════════════════════════════
#  2. SYSTÈME ELO
# ═══════════════════════════════════════════════════════════════════


def elo_expected(elo_a: float, elo_b: float) -> float:
    """Compute the expected score for player A given both Elo ratings.

    Args:
        elo_a: Elo rating of player/team A.
        elo_b: Elo rating of player/team B.

    Returns:
        Expected score (win probability) for A, between 0.0 and 1.0.
    """
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def elo_update(
    elo: float, expected: float, actual: float, k: int = K_FACTOR, goal_diff: int = 1
) -> float:
    """Update an Elo rating after a single match result.

    Includes a logarithmic goal-difference multiplier so that
    convincing victories carry more weight.

    Args:
        elo: Current Elo rating.
        expected: Expected score (from :func:`elo_expected`).
        actual: Actual result (1.0 win, 0.5 draw, 0.0 loss).
        k: K-factor controlling update magnitude.
        goal_diff: Absolute goal difference of the match.

    Returns:
        Updated Elo rating.
    """
    goal_factor = math.log(abs(goal_diff) + 1) + 1
    return elo + k * goal_factor * (actual - expected)


def elo_with_decay(
    elo: float,
    days_since_last: int,
    decay_rate: float = ELO_DECAY_RATE,
    baseline: int = DEFAULT_ELO,
) -> float:
    """Regress Elo towards baseline when a team hasn't played recently.

    Uses exponential decay so that long inactive periods gradually pull
    the rating back to the league average (1500).

    Args:
        elo: Current Elo rating.
        days_since_last: Days since the team's last match.
        decay_rate: Exponential decay coefficient.
        baseline: Elo value to regress towards.

    Returns:
        Decayed Elo rating.
    """
    if days_since_last <= 0:
        return elo
    regression = (elo - baseline) * math.exp(-decay_rate * days_since_last)
    return baseline + regression


def get_elo_probs(home_elo: float, away_elo: float, league_id: int | None = None) -> dict[str, int]:
    """Convert Elo ratings into 1X2 probabilities including a draw factor.

    A home-advantage offset is added before computing expected scores.
    A draw component is estimated from the league-calibrated draw rate,
    decayed by the ELO gap (closer teams → more draws).

    Args:
        home_elo: Elo rating of the home team.
        away_elo: Elo rating of the away team.
        league_id: Optional league identifier for calibrated draw factor.

    Returns:
        Dictionary with keys ``"elo_home"``, ``"elo_draw"``, ``"elo_away"``
        as rounded integer percentages.
    """
    home_adv = (
        HOME_ELO_ADVANTAGE_BY_LEAGUE.get(league_id, HOME_ELO_ADVANTAGE)
        if league_id
        else HOME_ELO_ADVANTAGE
    )
    p_home = elo_expected(home_elo + home_adv, away_elo)
    p_away = 1.0 - p_home

    # Draw factor: league-calibrated base, decays with ELO gap
    base_draw = DRAW_FACTOR_BY_LEAGUE.get(league_id, DRAW_FACTOR)
    elo_gap = abs(home_elo - away_elo)
    draw_decay = math.exp(-ELO_DRAW_DECAY_RATE * elo_gap)
    draw_prob = base_draw * draw_decay
    # Ensure draw stays in a reasonable football range
    # Even the biggest mismatches still draw ~15% of the time
    # (backtest showed draws under-predicted; raised floor from 0.12 to 0.15)
    draw_prob = max(0.15, min(0.35, draw_prob))

    # Redistribute: remove draw's share proportionally from home/away
    remaining = 1.0 - draw_prob
    p_home *= remaining
    p_away *= remaining

    elo_home = round(p_home * 100)
    elo_draw = round(draw_prob * 100)
    elo_away = 100 - elo_home - elo_draw  # Force sum == 100

    return {
        "elo_home": elo_home,
        "elo_draw": elo_draw,
        "elo_away": elo_away,
    }


def update_elo_from_results() -> dict[int, float]:
    """Recompute Elo ratings for every team from all finished fixtures.

    Loads current ratings from the ``team_elo`` table, iterates over
    completed fixtures in chronological order, applies
    :func:`elo_update` for each result, and persists the new ratings
    back to the database via upsert.

    Returns:
        Mapping of ``team_api_id`` to their updated Elo rating.
    """
    # Charger les ELO actuels
    elos_raw = supabase.table("team_elo").select("*").execute().data
    elos = {e["team_api_id"]: e["elo_rating"] for e in elos_raw}

    # Charger les fixtures terminées, triées par date
    fixtures = (
        supabase.table("fixtures")
        .select("api_fixture_id, home_team, away_team, home_goals, away_goals, league_id, date")
        .eq("status", "FT")
        .order("date")
        .execute()
        .data
    )

    # Charger mapping nom -> api_id
    teams = supabase.table("teams").select("api_id, name").execute().data
    name_to_id = {t["name"]: t["api_id"] for t in teams}

    # Track last match date for each team to apply decay
    last_match_dates: dict[int, datetime] = {}

    for fix in fixtures:
        hid = name_to_id.get(fix["home_team"])
        aid = name_to_id.get(fix["away_team"])
        if not hid or not aid:
            continue
        if hid not in elos or aid not in elos:
            continue

        match_dt = datetime.fromisoformat(fix["date"].replace("Z", "+00:00"))

        # Apply decay to both teams if they haven't played in >14 days
        for tid in [hid, aid]:
            if tid in last_match_dates:
                days_inactive = (match_dt - last_match_dates[tid]).days
                if days_inactive > 14:
                    elos[tid] = elo_with_decay(elos[tid], days_inactive)
            last_match_dates[tid] = match_dt

        hg = fix["home_goals"] or 0
        ag = fix["away_goals"] or 0
        gd = abs(hg - ag)

        h_adv = HOME_ELO_ADVANTAGE_BY_LEAGUE.get(fix.get("league_id"), HOME_ELO_ADVANTAGE)
        h_elo = elos[hid] + h_adv
        a_elo = elos[aid]

        h_exp = elo_expected(h_elo, a_elo)
        a_exp = elo_expected(a_elo, h_elo)

        if hg > ag:
            h_act, a_act = 1.0, 0.0
        elif hg == ag:
            h_act, a_act = 0.5, 0.5
        else:
            h_act, a_act = 0.0, 1.0

        # K-factor dynamique : CL/EL comptent plus, coupes nationales moins
        k = K_FACTOR_BY_LEAGUE.get(fix.get("league_id"), K_FACTOR)
        elos[hid] = elo_update(elos[hid], h_exp, h_act, k=k, goal_diff=gd)
        elos[aid] = elo_update(elos[aid], a_exp, a_act, k=k, goal_diff=gd)

    # Sauvegarder
    batch = [{"team_api_id": tid, "elo_rating": round(r, 1)} for tid, r in elos.items()]
    if batch:
        supabase.table("team_elo").upsert(batch, on_conflict="team_api_id").execute()

    return elos


# ═══════════════════════════════════════════════════════════════════
#  3. FORME RÉCENTE (pondération exponentielle)
# ═══════════════════════════════════════════════════════════════════


def calculate_form(
    team_name: str,
    n: int = 6,
    decay: float = 0.82,
    home_only: bool | None = None,
    name_to_elo: dict[str, float] | None = None,
) -> tuple[float, list[str]]:
    """Calculate the recent form of a team using exponential weighting.

    Each of the last *n* results is weighted by ``decay ** i`` (most
    recent first). If ``name_to_elo`` is provided, a Strength of Schedule
    multiplier (opponent_elo / 1500) is applied so that results against
    stronger teams count for more.

    Args:
        team_name: Canonical team name as stored in the fixtures table.
        n: Number of most-recent matches to consider.
        decay: Exponential decay factor applied per match index.
        home_only: ``True`` to consider home matches only, ``False`` for
            away matches only, ``None`` for all matches.
        name_to_elo: Optional mapping of team names to their ELO ratings.

    Returns:
        Tuple of ``(form_score, form_letters)`` where *form_score* is a
        float in [0, 1] and *form_letters* is a list of ``"W"``/``"D"``/``"L"``
        strings ordered most-recent first.
    """
    query = (
        supabase.table("fixtures")
        .select("home_team, away_team, home_goals, away_goals, date")
        .eq("status", "FT")
        .order("date", desc=True)
    )

    if home_only is True:
        query = query.eq("home_team", team_name)
    elif home_only is False:
        query = query.eq("away_team", team_name)
    else:
        query = query.or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")

    results = query.limit(n).execute().data
    if not results:
        return 0.5, []

    form_score = 0
    total_weight = 0
    form_letters = []

    for i, r in enumerate(results):
        weight = decay**i
        is_home = r["home_team"] == team_name
        opponent_name = r["away_team"] if is_home else r["home_team"]

        # Strength of schedule multiplier
        sos_multiplier = 1.0
        if name_to_elo:
            opp_elo = name_to_elo.get(opponent_name, 1500)
            sos_multiplier = opp_elo / 1500.0

        gf = r["home_goals"] if is_home else r["away_goals"]
        ga = r["away_goals"] if is_home else r["home_goals"]

        if gf is None or ga is None:
            continue

        if gf > ga:
            form_score += 3 * sos_multiplier * weight
            form_letters.append("W")
        elif gf == ga:
            form_score += 1 * sos_multiplier * weight
            form_letters.append("D")
        else:
            form_letters.append("L")

        # Denominator: max points per match (3) × weight, so form_score ∈ [0, 1]
        # This is correct: a team winning every match gets 1.0, losing every match gets 0.0
        total_weight += 3 * weight

    raw = form_score / total_weight if total_weight > 0 else 0.5
    # Clamp to [0, 1] — SOS multiplier can push score slightly above 1.0
    return max(0.0, min(1.0, raw)), form_letters


# ═══════════════════════════════════════════════════════════════════
#  4. REPOS ET CONGESTION
# ═══════════════════════════════════════════════════════════════════


def calculate_rest_factor(team_name: str, match_date: str) -> tuple[float, int, int, bool]:
    """Calculate a rest / fixture-congestion multiplier for a team.

    Rest bands:
        * < 3 days  — fatigue (−8 %)
        * 3-4 days  — slight disadvantage (−3 %)
        * 5-7 days  — normal (0 %)
        * > 7 days  — optimal rest (+2 %)

    An additional congestion penalty is applied when the team has played
    many matches in the last 30 days.

    Args:
        team_name: Canonical team name as stored in the fixtures table.
        match_date: ISO-8601 date string of the upcoming match.

    Returns:
        Tuple of ``(rest_factor, rest_days, matches_30d, is_severe_fatigue)`` where
        *rest_factor* is a float multiplier (< 1 = fatigued),
        *rest_days* is the number of days since the last match,
        *matches_30d* is the match count over the past 30 days, and
        *is_severe_fatigue* is True if played <3 days ago with >=6 matches this month.
    """
    match_dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))

    # Dernier match joué
    last_match = (
        supabase.table("fixtures")
        .select("date")
        .eq("status", "FT")
        .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
        .order("date", desc=True)
        .limit(1)
        .execute()
        .data
    )

    rest_factor = 1.0
    rest_days = 7  # Défaut

    if last_match:
        last_dt = datetime.fromisoformat(last_match[0]["date"].replace("Z", "+00:00"))
        rest_days = (match_dt - last_dt).days

        if rest_days < 3:
            rest_factor = 0.92
        elif rest_days < 5:
            rest_factor = 0.97
        elif rest_days > 7:
            rest_factor = 1.02

    # Congestion : matchs dans les 30 derniers jours
    thirty_days_ago = (match_dt - timedelta(days=30)).isoformat()
    recent = (
        supabase.table("fixtures")
        .select("id", count="exact")
        .eq("status", "FT")
        .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
        .gte("date", thirty_days_ago)
        .execute()
    )

    matches_30d = recent.count or 0
    if matches_30d > 8:
        rest_factor *= 0.96  # Très chargé
    elif matches_30d > 6:
        rest_factor *= 0.98

    is_severe_fatigue = False
    # European Fatigue Factor: Short rest + Congested calendar
    if rest_days < 3 and matches_30d >= 6:
        rest_factor = 0.85
        is_severe_fatigue = True

    return rest_factor, rest_days, matches_30d, is_severe_fatigue


# ═══════════════════════════════════════════════════════════════════
#  5. ENJEU DU MATCH
# ═══════════════════════════════════════════════════════════════════


def calculate_stakes(team_api_id: int, league_id: int) -> tuple[float, str]:
    """Evaluate the competitive stakes for a team in its league.

    Returns a motivation multiplier ranging from 0.95 (nothing to play
    for) to 1.08 (title race), together with a human-readable label.

    Stake categories:
        * Title race / Champions League qualification — boost ++
        * Relegation battle — boost +
        * Mid-table with nothing to play for — slight malus

    Args:
        team_api_id: API identifier of the team.
        league_id: API identifier of the league/competition.

    Returns:
        Tuple of ``(stakes_factor, label)`` where *stakes_factor* is a
        float multiplier and *label* is one of ``"titre"``,
        ``"qualification CL/EL"``, ``"relégation"``,
        ``"milieu de tableau"``, ``"normal"``, or ``"inconnu"``.
    """
    standings = (
        supabase.table("team_standings")
        .select("*")
        .eq("league_id", league_id)
        .eq("season", SEASON)
        .order("rank")
        .execute()
        .data
    )

    if not standings:
        return 1.0, "inconnu"

    # Trouver l'équipe
    team_standing = None
    for s in standings:
        if s["team_api_id"] == team_api_id:
            team_standing = s
            break

    if not team_standing:
        return 1.0, "inconnu"

    rank = team_standing["rank"]
    total_teams = len(standings)
    points = team_standing["points"]

    # Points du leader
    leader_pts = standings[0]["points"]
    # Points de la zone de relégation (3 derniers)
    relegation_rank = max(total_teams - 3, 1)
    relegation_pts = (
        standings[min(relegation_rank, len(standings) - 1)]["points"]
        if len(standings) >= relegation_rank
        else 0
    )

    # Distance aux enjeux
    pts_from_top = leader_pts - points
    pts_from_cl = (
        (standings[min(3, len(standings) - 1)]["points"] - points) if len(standings) > 3 else 0
    )
    pts_from_relegation = points - relegation_pts

    if pts_from_top <= 3:
        return 1.08, "titre"
    elif pts_from_cl <= 3 and rank <= 6:
        return 1.05, "qualification CL/EL"
    elif pts_from_relegation <= 3 and rank >= total_teams - 5:
        return 1.06, "relégation"
    elif rank > total_teams // 3 and rank < 2 * total_teams // 3:
        return 0.97, "milieu de tableau"
    else:
        return 1.0, "normal"


# ═══════════════════════════════════════════════════════════════════
#  6. RÉGRESSION VERS LA MOYENNE
# ═══════════════════════════════════════════════════════════════════


def regress_to_mean(observed: float, sample_size: int, league_avg: float, weight: int = 8) -> float:
    """Apply Bayesian regression toward the league mean.

    With many observations the observed value dominates; with few the
    estimate is pulled toward the league average.

    Args:
        observed: Observed per-match statistic for the team.
        sample_size: Number of matches the observation is based on.
        league_avg: League-wide average for the same statistic.
        weight: Prior strength — number of pseudo-observations at the
            league average.

    Returns:
        Regressed estimate as a float.
    """
    return (observed * sample_size + league_avg * weight) / (sample_size + weight)


# ═══════════════════════════════════════════════════════════════════
#  7. HEAD-TO-HEAD
# ═══════════════════════════════════════════════════════════════════


def get_h2h_factor(home_team_id: int, away_team_id: int) -> tuple[float, float, dict | None]:
    """Return xG adjustment factors based on the head-to-head record.

    If one side clearly dominates the historical matchups it receives a
    small boost (capped at ±8 %).

    Args:
        home_team_id: API identifier of the home team.
        away_team_id: API identifier of the away team.

    Returns:
        Tuple of ``(home_h2h_factor, away_h2h_factor, h2h_record)``
        where factors are floats in [0.92, 1.08] and *h2h_record* is the
        raw row from the ``h2h_cache`` table (or ``None`` if no history).
    """
    pair = sorted([home_team_id, away_team_id])
    h2h = (
        supabase.table("h2h_cache")
        .select("*")
        .eq("team_a_api_id", pair[0])
        .eq("team_b_api_id", pair[1])
        .execute()
        .data
    )

    if not h2h:
        return 1.0, 1.0, None

    h = h2h[0]
    total = max(h["total_matches"], 1)

    # Déterminer qui est A
    if h["team_a_api_id"] == home_team_id:
        home_wr = h["team_a_wins"] / total
        away_wr = h["team_b_wins"] / total
    else:
        home_wr = h["team_b_wins"] / total
        away_wr = h["team_a_wins"] / total

    # Atténuer l'impact si H2H datent (beaucoup de matchs = historique long)
    # Avec ≤5 matchs récents, le facteur s'applique pleinement
    # Avec 20+ matchs, les anciens matchs diluent → réduire l'amplitude
    recency_damper = min(1.0, 8.0 / max(total, 1))

    # Petit ajustement (max ±5%), atténué par la fraîcheur
    home_h2h = 1.0 + (home_wr - 0.33) * 0.15 * recency_damper
    away_h2h = 1.0 + (away_wr - 0.33) * 0.15 * recency_damper

    return (
        max(0.92, min(1.08, home_h2h)),
        max(0.92, min(1.08, away_h2h)),
        h,
    )


# ═══════════════════════════════════════════════════════════════════
#  8. IMPACT ARBITRE
# ═══════════════════════════════════════════════════════════════════


def get_referee_impact(referee_name: str | None) -> dict | None:
    """Retrieve referee tendency statistics.

    Used to adjust penalty probability and, indirectly, expected goals.

    Args:
        referee_name: Name of the referee, or ``None`` if unknown.

    Returns:
        Dictionary with keys ``"avg_yellows"``, ``"avg_reds"``,
        ``"avg_penalties"``, ``"avg_fouls"``, ``"penalty_bias"``, and
        ``"matches"``, or ``None`` if the referee is unknown or not found.
    """
    if not referee_name:
        return None

    ref = supabase.table("referees").select("*").eq("name", referee_name).execute().data
    if not ref:
        return None

    r = ref[0]
    # Un arbitre qui siffle beaucoup de pénaltys → plus de buts
    # Moyenne en Europe : ~0.3 penalty par match
    penalty_bias = r["avg_penalties_per_match"] / 0.3 if r["avg_penalties_per_match"] else 1.0

    return {
        "avg_yellows": r["avg_yellows_per_match"],
        "avg_reds": r["avg_reds_per_match"],
        "avg_penalties": r["avg_penalties_per_match"],
        "avg_fouls": r["avg_fouls_per_match"],
        "penalty_bias": round(penalty_bias, 2),
        "matches": r["matches_officiated"],
    }


# ═══════════════════════════════════════════════════════════════════
#  9. IMPACT MÉTÉO
# ═══════════════════════════════════════════════════════════════════


def get_weather_impact(weather_json: dict | None) -> float:
    """Compute an xG adjustment factor based on weather conditions.

    Heavy rain or strong wind reduce expected goals (−5 % to −10 %);
    extreme temperatures also incur a small penalty.

    Args:
        weather_json: Dictionary with optional keys ``"wind_speed"``
            (m/s), ``"rain_mm"`` (mm), and ``"temp"`` (°C), or ``None``.

    Returns:
        Multiplicative factor (≤ 1.0 in adverse weather, 1.0 otherwise).
    """
    if not weather_json:
        return 1.0

    factor = 1.0
    wind = weather_json.get("wind_speed", 0)
    rain = weather_json.get("rain_mm", 0)
    temp = weather_json.get("temp", 15)

    if rain > 5:
        factor *= 0.93  # Pluie forte
    elif rain > 2:
        factor *= 0.97  # Pluie modérée

    if wind > 10:
        factor *= 0.95  # Vent fort
    elif wind > 6:
        factor *= 0.98

    if temp < 2 or temp > 35:
        factor *= 0.97  # Conditions extrêmes

    return factor


# ═══════════════════════════════════════════════════════════════════
#  10. IMPACT BLESSURES
# ═══════════════════════════════════════════════════════════════════


def get_injury_impact(
    team_api_id: int, fixture_api_id: int | None = None
) -> tuple[float, float, list[dict]]:
    """Evaluate the impact of player absences on a team's strength.

    Uses a position-aware model: goalkeepers and top scorers weigh
    more than squad players.

    Args:
        team_api_id: API identifier of the team.
        fixture_api_id: Optional fixture API id (currently unused but
            reserved for fixture-specific injury lists).

    Returns:
        Tuple of ``(attack_factor, defense_factor, injured_details)``
        where:

        * *attack_factor* (0.70–1.0) — multiplier on the team's own xG
          (lower means more attacking quality lost).
        * *defense_factor* (1.0–1.35) — multiplier on xG conceded
          (higher means more defensive quality lost).
        * *injured_details* — list of dicts with per-player impact
          breakdown, sorted most-critical first.
    """
    # ── 1. Récupérer les blessés (table injuries + flag players.is_injured) ──
    inj_from_table = (
        supabase.table("injuries")
        .select("player_api_id, player_name, reason, type")
        .eq("team_api_id", team_api_id)
        .execute()
        .data
    )

    inj_from_flag = (
        supabase.table("players")
        .select("api_id, name, position")
        .eq("team_api_id", team_api_id)
        .eq("is_injured", True)
        .execute()
        .data
    )

    # Fusionner (dédupliquer par player_api_id)
    injured_ids_set = set()
    injured_raw = []
    for inj in inj_from_table:
        pid = inj.get("player_api_id")
        if pid and pid not in injured_ids_set:
            injured_ids_set.add(pid)
            injured_raw.append(inj)
    for p in inj_from_flag:
        pid = p.get("api_id")
        if pid and pid not in injured_ids_set:
            injured_ids_set.add(pid)
            injured_raw.append(
                {
                    "player_api_id": pid,
                    "player_name": p.get("name"),
                    "reason": "Blessé (flag joueur)",
                    "type": "Missing Fixture",
                }
            )

    if not injured_raw:
        return 1.0, 1.0, []

    injured_ids = list(injured_ids_set)

    # ── 2. Récupérer poste + stats de chaque blessé ──
    players_info = (
        supabase.table("players")
        .select("api_id, name, position")
        .in_("api_id", injured_ids)
        .execute()
        .data
    )
    pos_map = {p["api_id"]: p.get("position", "Unknown") for p in players_info}

    stats = (
        supabase.table("player_season_stats")
        .select(
            "player_api_id, rating, goals, assists, minutes_played, "
            "goals_conceded, saves, clean_sheets, "
            "shots_on_target, passes_key, penalty_scored, penalty_missed"
        )
        .eq("season", SEASON)
        .in_("player_api_id", injured_ids)
        .execute()
        .data
    )
    stats_map = {s["player_api_id"]: s for s in stats}

    # ── 3. Stats totales de l'équipe pour calculer les parts ──
    team_stats = (
        supabase.table("player_season_stats")
        .select("player_api_id, goals, assists, minutes_played")
        .eq("team_api_id", team_api_id)
        .eq("season", SEASON)
        .execute()
        .data
    )

    team_total_goals = max(sum(s["goals"] or 0 for s in team_stats), 1)
    team_total_assists = max(sum(s["assists"] or 0 for s in team_stats), 1)
    team_total_minutes = max(sum(s["minutes_played"] or 0 for s in team_stats), 1)

    # ── 4. Construire la liste des blessés améliorée pour le VORP ──
    missing_players = []

    for inj in injured_raw:
        pid = inj.get("player_api_id")
        if not pid:
            continue

        position = pos_map.get(pid, "Unknown")
        s = stats_map.get(pid, {})
        name = inj.get("player_name", "?")
        reason = inj.get("reason", "?")

        rating = s.get("rating", 6.0)
        mins = s.get("minutes_played", 0)
        is_starter = mins > getattr(team_total_minutes, "real", 0) * 0.03

        missing_players.append(
            {
                "player_name": name,
                "position": position,
                "reason": reason,
                "rating": rating,
                "minutes_played": mins,
                "is_starter": is_starter,
                "goals": s.get("goals", 0),
                "assists": s.get("assists", 0),
            }
        )

    # ── 5. Calcul des facteurs finaux via VORP ──
    from src.models.injury_vorp import calculate_vorp_impact

    team_context = {
        "total_goals": getattr(team_total_goals, "real", 1),
        "total_assists": getattr(team_total_assists, "real", 1),
    }

    attack_factor, defense_factor = calculate_vorp_impact(missing_players, team_context)

    # ── 6. Préparation des détails pour l'affichage/log ──
    injured_details = missing_players  # Could be augmented by VORP impact strings if needed, keeping simple for now

    # Sort roughly by importance (starters with highest rating first)
    injured_details.sort(key=lambda x: (x["is_starter"], x["rating"] or 0.0), reverse=True)

    return attack_factor, defense_factor, injured_details


# ═══════════════════════════════════════════════════════════════════
#  11. CALIBRATION ODDS BOOKMAKERS
# ═══════════════════════════════════════════════════════════════════


def odds_to_probs(fixture_api_id: int) -> dict | None:
    """Convert bookmaker odds into implied probabilities.

    Removes the overround (vig) to obtain fair probabilities.

    Args:
        fixture_api_id: API identifier of the fixture.

    Returns:
        Dictionary with keys ``"market_home"``, ``"market_draw"``,
        ``"market_away"`` (integer percentages) and ``"overround"``,
        or ``None`` if odds are unavailable.
    """
    odds = (
        supabase.table("fixture_odds")
        .select("*")
        .eq("fixture_api_id", fixture_api_id)
        .execute()
        .data
    )

    if not odds:
        return None

    o = odds[0]
    if not o.get("home_win_odds"):
        return None

    # Probabilités implicites (avec overround)
    raw_h = 1 / o["home_win_odds"]
    raw_d = 1 / o["draw_odds"] if o.get("draw_odds") else 0.25
    raw_a = 1 / o["away_win_odds"]
    overround = raw_h + raw_d + raw_a

    def _bin_prob(yes_key: str, no_key: str) -> float | None:
        y, n = o.get(yes_key), o.get(no_key)
        if not y or not n:
            return None
        ry, rn = 1 / y, 1 / n
        return round(ry / (ry + rn) * 100)

    return {
        "market_home": round(raw_h / overround * 100),
        "market_draw": round(raw_d / overround * 100),
        "market_away": round(raw_a / overround * 100),
        "overround": round(overround, 3),
        "market_btts": _bin_prob("btts_yes_odds", "btts_no_odds"),
        "market_over25": _bin_prob("over_25_odds", "under_25_odds"),
        "market_over15": _bin_prob("over_15_odds", "under_15_odds"),
    }


# ═══════════════════════════════════════════════════════════════════
#  12. PROBABILITÉ DE PENALTY
# ═══════════════════════════════════════════════════════════════════


def calculate_penalty_proba(
    fixture: dict,
    referee_impact: dict | None = None,
    stakes_home: float = 1.0,
    stakes_away: float = 1.0,
    home_id: int | None = None,
    away_id: int | None = None,
) -> tuple[int, float, dict]:
    """Estimate the probability that at least one penalty is awarded.

    The model combines five factors:
        1. Historical base rate (~0.30 pen/match in Europe).
        2. Referee tendency (avg penalties per match vs base rate).
        3. Defender foul rate for both teams.
        4. Attacker foul-drawing ability and dribble frequency.
        5. Match stakes / tension (high-stakes → more fouls → more pens).

    Args:
        fixture: Fixture dictionary (currently used for context only).
        referee_impact: Output of :func:`get_referee_impact`, or ``None``.
        stakes_home: Stakes multiplier for the home team.
        stakes_away: Stakes multiplier for the away team.
        home_id: API identifier of the home team, or ``None``.
        away_id: API identifier of the away team, or ``None``.

    Returns:
        Tuple of ``(proba_penalty, lambda_pen, details)`` where
        *proba_penalty* is an integer percentage (5–45 %),
        *lambda_pen* is the Poisson λ for penalties in the match, and
        *details* is a breakdown dict of contributing factors.
    """
    lambda_pen = BASE_PENALTY_RATE

    details = {"base_rate": BASE_PENALTY_RATE}

    # ── 1. Facteur arbitre ────────────────────────────────────────
    ref_factor = 1.0
    if referee_impact and referee_impact.get("avg_penalties"):
        ref_avg = referee_impact["avg_penalties"]
        if ref_avg > 0:
            ref_factor = ref_avg / BASE_PENALTY_RATE
            ref_factor = max(0.5, min(2.5, ref_factor))  # Cap [0.5 - 2.5]
        details["referee_avg_pen"] = ref_avg
        details["referee_factor"] = round(ref_factor, 2)

    # ── 2. Facteur défenseurs fautifs ─────────────────────────────
    # On regarde les fouls_committed des défenseurs de chaque équipe
    def_fouls_factor = 1.0
    if home_id and away_id:
        try:
            # Défenseurs de l'équipe domicile (adversaires des attaquants visiteurs)
            home_def = (
                supabase.table("players")
                .select("api_id")
                .eq("team_api_id", home_id)
                .eq("position", "Defender")
                .execute()
                .data
            )
            home_def_ids = [d["api_id"] for d in home_def]

            # Défenseurs de l'équipe extérieure
            away_def = (
                supabase.table("players")
                .select("api_id")
                .eq("team_api_id", away_id)
                .eq("position", "Defender")
                .execute()
                .data
            )
            away_def_ids = [d["api_id"] for d in away_def]

            all_def_ids = home_def_ids + away_def_ids

            if all_def_ids:
                def_stats = (
                    supabase.table("player_season_stats")
                    .select("fouls_committed, minutes_played")
                    .eq("season", SEASON)
                    .in_("player_api_id", all_def_ids)
                    .execute()
                    .data
                )

                total_fouls = sum(s["fouls_committed"] or 0 for s in def_stats)
                total_mins = sum(s["minutes_played"] or 0 for s in def_stats)

                if total_mins > 500:
                    fouls_per_90 = total_fouls * 90 / total_mins
                    # Moyenne européenne ~1.2 fautes/90 par défenseur
                    def_fouls_factor = fouls_per_90 / AVG_DEFENDER_FOULS_PER_90
                    def_fouls_factor = max(0.7, min(1.5, def_fouls_factor))

            details["def_fouls_factor"] = round(def_fouls_factor, 2)
        except Exception:
            pass  # Non-critical: penalty proba still works without this factor

    # ── 3. Facteur attaquants provocateurs ────────────────────────
    att_draws_factor = 1.0
    if home_id and away_id:
        try:
            home_att = (
                supabase.table("players")
                .select("api_id")
                .eq("team_api_id", home_id)
                .in_("position", ["Attacker", "Midfielder"])
                .execute()
                .data
            )
            away_att = (
                supabase.table("players")
                .select("api_id")
                .eq("team_api_id", away_id)
                .in_("position", ["Attacker", "Midfielder"])
                .execute()
                .data
            )

            all_att_ids = [a["api_id"] for a in home_att + away_att]

            if all_att_ids:
                att_stats = (
                    supabase.table("player_season_stats")
                    .select("fouls_drawn, dribbles_attempts, dribbles_success, minutes_played")
                    .eq("season", SEASON)
                    .in_("player_api_id", all_att_ids)
                    .execute()
                    .data
                )

                total_drawn = sum(s["fouls_drawn"] or 0 for s in att_stats)
                total_dribbles = sum(s["dribbles_attempts"] or 0 for s in att_stats)
                total_mins = sum(s["minutes_played"] or 0 for s in att_stats)

                if total_mins > 500:
                    drawn_per_90 = total_drawn * 90 / total_mins
                    dribbles_per_90 = total_dribbles * 90 / total_mins
                    # Moyenne ~1.5 fouls_drawn/90 par attaquant/milieu
                    draw_factor = drawn_per_90 / AVG_ATTACKER_FOULS_DRAWN_PER_90
                    # Dribbleurs attirent les fautes en surface
                    dribble_bonus = 1.0 + max(0, (dribbles_per_90 - 2.0)) * 0.05
                    att_draws_factor = draw_factor * dribble_bonus
                    att_draws_factor = max(0.7, min(1.5, att_draws_factor))

            details["att_draws_factor"] = round(att_draws_factor, 2)
        except Exception:
            pass  # Non-critical: penalty proba still works without this factor

    # ── 4. Facteur enjeu / tension ────────────────────────────────
    # Matchs à enjeu → plus de pression → plus de fautes → plus de penaltys
    stakes_factor = 1.0
    avg_stakes = (stakes_home + stakes_away) / 2
    if avg_stakes > 1.05:
        stakes_factor = 1.15  # Match à gros enjeu
    elif avg_stakes > 1.02:
        stakes_factor = 1.08
    elif avg_stakes < 0.98:
        stakes_factor = 0.95  # Peu d'enjeu = moins agressif
    details["stakes_factor"] = round(stakes_factor, 2)

    # ── 5. Combinaison ────────────────────────────────────────────
    # On utilise la racine carrée pour les facteurs défenseurs/attaquants
    # afin de ne pas surpondérer
    lambda_pen = (
        BASE_PENALTY_RATE
        * ref_factor
        * math.sqrt(def_fouls_factor)
        * math.sqrt(att_draws_factor)
        * stakes_factor
    )

    # P(au moins 1 penalty) = 1 - P(0 penalty) = 1 - e^(-lambda)
    proba = (1 - math.exp(-lambda_pen)) * 100
    proba = round(max(5, min(45, proba)))  # Cap réaliste : 5-45% (moy. européenne ~25-30%)

    details["lambda"] = round(lambda_pen, 3)

    return proba, lambda_pen, details


# ═══════════════════════════════════════════════════════════════════
#  VALUE BETTING & KELLY CRITERION
# ═══════════════════════════════════════════════════════════════════


def calculate_roi(prediction_prob: float, bookmaker_odds: float) -> float:
    """Compute the expected ROI for a bet.

    ROI > 0 indicates a value bet (positive expected value).

    Args:
        prediction_prob: Model's probability estimate (0–100).
        bookmaker_odds: Decimal bookmaker odds (e.g. 2.10).

    Returns:
        Expected ROI as a fraction (e.g. 0.05 means +5%).
    """
    return (prediction_prob / 100) * bookmaker_odds - 1


def kelly_criterion(
    prob: float,
    odds: float,
    bankroll: float,
    fraction: float = KELLY_FRACTION,
    max_bet_fraction: float = KELLY_MAX_BET_FRACTION,
) -> float:
    """Compute optimal bet size using fractional Kelly criterion.

    Uses quarter-Kelly by default for a more conservative approach
    that reduces variance while still capturing most of the edge.

    Args:
        prob: Model's probability estimate (0–100).
        odds: Decimal bookmaker odds.
        bankroll: Current bankroll amount.
        fraction: Kelly fraction (0.25 = quarter-Kelly).
        max_bet_fraction: Maximum fraction of bankroll per bet.

    Returns:
        Recommended bet amount (0 if no edge).
    """
    edge = calculate_roi(prob, odds)
    if edge <= MIN_VALUE_EDGE:
        return 0.0
    kelly_full = edge / (odds - 1) if odds > 1 else 0.0
    bet = bankroll * kelly_full * fraction
    return min(bet, bankroll * max_bet_fraction)


# ═══════════════════════════════════════════════════════════════════
#  11. ADVANCED ML FEATURES — Compute all missing inputs
# ═══════════════════════════════════════════════════════════════════


def compute_advanced_features(
    team_name: str, n_short: int = 5, n_long: int = 10
) -> dict[str, float]:
    """Compute advanced match features for a team from historical fixtures.

    Queries the last *n_long* completed matches and derives:
    ppg_last5, btts_rate_last10, over25_rate_last10, clean_sheet_rate,
    goal_diff_avg, result_variance, and momentum.

    Returns:
        Dictionary with all computed features, empty dict if insufficient data.
    """
    results = (
        supabase.table("fixtures")
        .select("home_team, away_team, home_goals, away_goals")
        .eq("status", "FT")
        .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
        .order("date", desc=True)
        .limit(n_long)
        .execute()
        .data
    )

    if not results or len(results) < 3:
        return {}

    points: list[int] = []
    goal_diffs: list[int] = []
    btts_count = 0
    over25_count = 0
    cs_count = 0

    for r in results:
        is_home = r["home_team"] == team_name
        gf = r["home_goals"] if is_home else r["away_goals"]
        ga = r["away_goals"] if is_home else r["home_goals"]
        if gf is None or ga is None:
            continue

        if gf > ga:
            points.append(3)
        elif gf == ga:
            points.append(1)
        else:
            points.append(0)

        goal_diffs.append(gf - ga)
        if gf > 0 and ga > 0:
            btts_count += 1
        if gf + ga > 2:
            over25_count += 1
        if ga == 0:
            cs_count += 1

    n = len(points)
    if n == 0:
        return {}

    ppg_last5 = sum(points[: min(n_short, n)]) / min(n_short, n)
    btts_rate = btts_count / n
    over25_rate = over25_count / n
    cs_rate = cs_count / n
    gd_avg = sum(goal_diffs) / n

    # Result variance (higher = more unpredictable)
    mean_pts = sum(points) / n
    variance = sum((p - mean_pts) ** 2 for p in points) / max(n - 1, 1) if n > 1 else 0.0

    # Momentum: compare last 3 vs overall average
    momentum = (sum(points[:3]) / 3 - mean_pts) if n >= 4 else 0.0

    return {
        "ppg_last5": round(ppg_last5, 2),
        "btts_rate_last10": round(btts_rate, 3),
        "over25_rate_last10": round(over25_rate, 3),
        "clean_sheet_rate": round(cs_rate, 3),
        "goal_diff_avg": round(gd_avg, 2),
        "result_variance": round(variance, 3),
        "momentum": round(momentum, 2),
    }


def compute_team_shot_stats(team_api_id: int, league_id: int) -> dict[str, float | None]:
    """Compute xG-per-shot from match_team_stats for a given team/league.

    Returns:
        Dictionary with ``xg_per_shot``, or empty if no data.
    """
    fix_resp = (
        supabase.table("fixtures")
        .select("api_fixture_id")
        .eq("league_id", league_id)
        .in_("status", ["FT", "AET", "PEN"])
        .execute()
    )
    if not fix_resp.data:
        return {}

    fixture_ids = [f["api_fixture_id"] for f in fix_resp.data]
    all_stats: list[dict] = []
    CHUNK = 100
    for i in range(0, len(fixture_ids), CHUNK):
        chunk = fixture_ids[i : i + CHUNK]
        resp = (
            supabase.table("match_team_stats")
            .select("expected_goals, shots_total")
            .eq("team_api_id", team_api_id)
            .in_("fixture_api_id", chunk)
            .execute()
        )
        if resp.data:
            all_stats.extend(resp.data)

    if not all_stats:
        return {}

    total_xg = 0.0
    total_shots = 0
    for s in all_stats:
        xg = s.get("expected_goals")
        shots = s.get("shots_total")
        if xg is not None and shots is not None and shots > 0:
            total_xg += xg
            total_shots += shots

    return {"xg_per_shot": round(total_xg / total_shots, 4)} if total_shots > 0 else {}


def compute_league_rates(league_id: int) -> dict[str, float]:
    """Compute league-level BTTS and Over 2.5 historical rates.

    Returns:
        Dictionary with ``league_avg_btts_rate`` and ``league_avg_over25_rate``.
    """
    results = (
        supabase.table("fixtures")
        .select("home_goals, away_goals")
        .eq("league_id", league_id)
        .in_("status", ["FT", "AET", "PEN"])
        .execute()
        .data
    )

    if not results or len(results) < 10:
        return {"league_avg_btts_rate": 0.50, "league_avg_over25_rate": 0.48}

    btts = over25 = total = 0
    for r in results:
        hg, ag = r.get("home_goals"), r.get("away_goals")
        if hg is None or ag is None:
            continue
        total += 1
        if hg > 0 and ag > 0:
            btts += 1
        if hg + ag > 2:
            over25 += 1

    return {
        "league_avg_btts_rate": round(btts / max(total, 1), 3),
        "league_avg_over25_rate": round(over25 / max(total, 1), 3),
    }


# ═══════════════════════════════════════════════════════════════════
#  MOTEUR PRINCIPAL : ANALYSER UN MATCH
# ═══════════════════════════════════════════════════════════════════


def clamp_probabilities(result: dict[str, Any]) -> dict[str, Any]:
    """Apply realistic bounds to all probabilities.

    Prevents extreme/unrealistic values. No single 1X2 outcome can be
    below PROB_1X2_FLOOR or above PROB_1X2_CEIL. Markets (BTTS, Over)
    are also bounded. Over lines are enforced to be monotonically
    decreasing (O0.5 ≥ O1.5 ≥ O2.5 ≥ O3.5).
    """
    # ── 1X2 clamping with iterative redistribution ────────────────
    h, d, a = result["proba_home"], result["proba_draw"], result["proba_away"]

    # Step 1: enforce floor — raise any below minimum, take from max
    for _ in range(3):
        vals = [h, d, a]
        for i in range(3):
            if vals[i] < PROB_1X2_FLOOR:
                deficit = PROB_1X2_FLOOR - vals[i]
                vals[i] = PROB_1X2_FLOOR
                # Take from the largest value
                max_idx = max((j for j in range(3) if j != i), key=lambda j: vals[j])
                vals[max_idx] -= deficit
        h, d, a = vals

    # Step 2: enforce ceiling — cap any above maximum, redistribute excess
    for _ in range(3):
        vals = [h, d, a]
        for i in range(3):
            if vals[i] > PROB_1X2_CEIL:
                excess = vals[i] - PROB_1X2_CEIL
                vals[i] = PROB_1X2_CEIL
                # Distribute excess proportionally to the others
                others = [j for j in range(3) if j != i]
                other_sum = sum(vals[j] for j in others)
                if other_sum > 0:
                    for j in others:
                        vals[j] += excess * vals[j] / other_sum
                else:
                    for j in others:
                        vals[j] += excess / len(others)
        h, d, a = vals

    # Round and normalize to exactly 100
    result["proba_home"] = round(h)
    result["proba_draw"] = round(d)
    result["proba_away"] = 100 - result["proba_home"] - result["proba_draw"]

    # Safety: ensure away doesn't go below floor after rounding
    if result["proba_away"] < PROB_1X2_FLOOR:
        result["proba_away"] = PROB_1X2_FLOOR
        result["proba_home"] = 100 - result["proba_draw"] - result["proba_away"]

    # Recalculate double chance from clamped 1X2
    result["proba_dc_1x"] = result["proba_home"] + result["proba_draw"]
    result["proba_dc_x2"] = result["proba_draw"] + result["proba_away"]
    result["proba_dc_12"] = result["proba_home"] + result["proba_away"]

    # ── Markets clamping ──────────────────────────────────────────
    result["proba_btts"] = max(PROB_BTTS_FLOOR, min(PROB_BTTS_CEIL, result["proba_btts"]))
    result["proba_over_25"] = max(PROB_OVER25_FLOOR, min(PROB_OVER25_CEIL, result["proba_over_25"]))

    # ── Monotonic over lines: O0.5 ≥ O1.5 ≥ O2.5 ≥ O3.5 ────────
    # Use soft enforcement: preserve values when already monotonic,
    # only pull up to maintain the chain (no arbitrary +5 gap).
    o25 = result["proba_over_25"]
    o15 = result["proba_over_15"]
    o05 = result["proba_over_05"]
    o35 = result["proba_over_35"]

    # Enforce chain from bottom up: O3.5 ≤ O2.5 ≤ O1.5 ≤ O0.5
    o35 = min(o35, o25 - 1)
    o35 = max(2, o35)
    o15 = max(o15, o25 + 1)  # O1.5 must be > O2.5
    o05 = max(o05, o15 + 1)  # O0.5 must be > O1.5
    o05 = min(99, o05)

    result["proba_over_35"] = o35
    result["proba_over_15"] = o15
    result["proba_over_05"] = o05

    # ── Cross-market coherence: BTTS ≤ O0.5 (logical constraint) ──
    # If both teams score, at least 2 goals → BTTS ≤ Over 1.5 is always true.
    # More precisely: BTTS implies Over 1.5 (at least 1-1).
    if result["proba_btts"] > o15:
        result["proba_btts"] = o15

    return result


def analyze_match(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run a full probabilistic analysis of a fixture.

    Combines Poisson model, Elo ratings, bookmaker odds, ML predictions
    (if available), and contextual adjustments (form, rest, stakes,
    head-to-head, injuries, referee, weather) into a single unified
    prediction dictionary.

    Args:
        fixture: Dictionary describing the fixture with at least keys
            ``"home_team"``, ``"away_team"``, ``"league_id"``,
            ``"date"``, and optionally ``"api_fixture_id"``,
            ``"referee_name"``, ``"weather_json"``.

    Returns:
        Dictionary containing all market probabilities (1X2, BTTS,
        over/under, double chance, penalty, correct score), adjusted
        xG values, a recommended bet, a confidence score (1–10),
        the model version string, and a ``"context"`` sub-dict with
        every intermediate signal used in the computation.
    """
    home_team = fixture["home_team"]
    away_team = fixture["away_team"]
    league_id = fixture["league_id"]
    match_date = fixture["date"]
    fixture_api_id = fixture.get("api_fixture_id")
    referee_name = fixture.get("referee_name")
    weather = fixture.get("weather_json")

    # Mapping nom -> id
    teams = supabase.table("teams").select("api_id, name").execute().data
    name_to_id = {t["name"]: t["api_id"] for t in teams}
    home_id = name_to_id.get(home_team)
    away_id = name_to_id.get(away_team)

    context: dict[str, Any] = {}

    # ── 1. Poisson de base ───────────────────────────────────────
    # For cross-league competitions (CL, EL, cups), skip league-level
    # strengths (too few matches) — calculate_xg will use each team's
    # domestic league strengths instead.
    league_data = None if league_id in CROSS_LEAGUE_IDS else calculate_team_strengths(league_id)
    xg_home, xg_away = calculate_xg(home_id or 0, away_id or 0, league_data)

    # ── Competition factor (CL/EL/Cup matches are less high-scoring) ──
    comp_factor = COMPETITION_XG_FACTOR.get(league_id, 1.0)
    if comp_factor != 1.0:
        xg_home *= comp_factor
        xg_away *= comp_factor
        context["competition_xg_factor"] = comp_factor
        from src.config import logger

        logger.info(
            f"  🏆 Facteur compétition ({league_id}): ×{comp_factor} → xG {xg_home:.2f}/{xg_away:.2f}"
        )

    # ── ELO Préalable (requis pour le calcul de forme SOS) ───────
    elos = supabase.table("team_elo").select("team_api_id, elo_rating").execute().data
    elo_map = {e["team_api_id"]: e["elo_rating"] for e in elos}
    name_to_elo = {t["name"]: elo_map.get(t["api_id"], 1500) for t in teams}

    # ── 2. Ajustements ───────────────────────────────────────────
    # Forme (récente pondérée avec Strength of Schedule)
    form_home, form_letters_h = calculate_form(home_team, home_only=True, name_to_elo=name_to_elo)
    form_away, form_letters_a = calculate_form(away_team, home_only=False, name_to_elo=name_to_elo)
    context["form_home"] = "".join(form_letters_h)
    context["form_away"] = "".join(form_letters_a)

    # Momentum long terme (12 matchs, decay lent) — capture la tendance de fond
    form_long_home, _ = calculate_form(
        home_team,
        n=FORM_LOOKBACK_LONG,
        decay=FORM_DECAY_LONG,
        home_only=True,
        name_to_elo=name_to_elo,
    )
    form_long_away, _ = calculate_form(
        away_team,
        n=FORM_LOOKBACK_LONG,
        decay=FORM_DECAY_LONG,
        home_only=False,
        name_to_elo=name_to_elo,
    )
    context["form_long_home"] = round(form_long_home, 3)
    context["form_long_away"] = round(form_long_away, 3)

    # form_factor = 70% forme courte (6 matchs) + 30% tendance longue (12 matchs)
    form_factor_h = FORM_WEIGHT_SHORT * (0.85 + form_home * 0.30) + FORM_WEIGHT_LONG * (
        0.85 + form_long_home * 0.30
    )
    form_factor_a = FORM_WEIGHT_SHORT * (0.85 + form_away * 0.30) + FORM_WEIGHT_LONG * (
        0.85 + form_long_away * 0.30
    )

    # Repos
    rest_h, rest_days_h, congestion_h, severe_h = calculate_rest_factor(home_team, match_date)
    rest_a, rest_days_a, congestion_a, severe_a = calculate_rest_factor(away_team, match_date)
    context["rest_days_home"] = rest_days_h
    context["rest_days_away"] = rest_days_a
    context["congestion_home"] = congestion_h
    context["congestion_away"] = congestion_a
    context["severe_fatigue_home"] = severe_h
    context["severe_fatigue_away"] = severe_a

    # Enjeu
    stakes_h, stakes_label_h = calculate_stakes(home_id, league_id) if home_id else (1.0, "inconnu")
    stakes_a, stakes_label_a = calculate_stakes(away_id, league_id) if away_id else (1.0, "inconnu")
    context["stakes_home"] = stakes_label_h
    context["stakes_away"] = stakes_label_a

    # H2H
    h2h_h, h2h_a, h2h_data = (
        get_h2h_factor(home_id, away_id) if home_id and away_id else (1.0, 1.0, None)
    )
    context["h2h"] = h2h_data

    # Blessures (version granulaire par poste)
    if home_id:
        atk_h, def_h, injured_h = get_injury_impact(home_id, fixture_api_id)
    else:
        atk_h, def_h, injured_h = 1.0, 1.0, []
    if away_id:
        atk_a, def_a, injured_a = get_injury_impact(away_id, fixture_api_id)
    else:
        atk_a, def_a, injured_a = 1.0, 1.0, []

    context["injuries_home"] = [i.get("player_name", "?") for i in injured_h]
    context["injuries_away"] = [i.get("player_name", "?") for i in injured_a]
    context["injuries_home_details"] = injured_h
    context["injuries_away_details"] = injured_a

    # Arbitre
    ref_impact = get_referee_impact(referee_name)
    context["referee"] = ref_impact

    # Météo
    weather_factor = get_weather_impact(weather)
    context["weather"] = weather

    # ── 3. Facteurs combinés ─────────────────────────────────────
    # Blessures : impact séparé attaque / défense
    # atk_h : réduit les xG de l'équipe dom (si leur attaquant est blessé)
    # def_h : augmente les xG de l'adversaire (si leur défenseur/gardien est blessé)
    # Utiliser sqrt(weather_factor) par côté pour éviter le double-impact
    # (weather_factor appliqué aux DEUX côtés = impact cumulé trop fort)
    weather_per_side = math.sqrt(weather_factor) if weather_factor < 1.0 else weather_factor
    # Stakes NO LONGER applied to xG — high-stakes matches produce tighter
    # games, not more goals (Anderson & Sally, Buraimo et al.)
    home_base = form_factor_h * rest_h * h2h_h * weather_per_side
    away_base = form_factor_a * rest_a * h2h_a * weather_per_side

    # Guard-fou: cap the total multiplier product to avoid excessive compression.
    # Without this, cascading penalties (bad form + fatigue + injuries + rain + h2h)
    # can compress xG by 40%+, producing unrealistically low outputs.
    MIN_TOTAL_MULTIPLIER = 0.65
    home_total_mult = home_base * atk_h * def_a
    away_total_mult = away_base * atk_a * def_h
    if home_total_mult < MIN_TOTAL_MULTIPLIER:
        home_total_mult = MIN_TOTAL_MULTIPLIER
    if away_total_mult < MIN_TOTAL_MULTIPLIER:
        away_total_mult = MIN_TOTAL_MULTIPLIER

    # xG_home = force offensive dom × faiblesse défensive adverse (blessures ext)
    xg_home_adj = xg_home * home_total_mult
    # xG_away = force offensive ext × faiblesse défensive dom (blessures dom)
    xg_away_adj = xg_away * away_total_mult

    # Si l'arbitre siffle beaucoup de pénaltys, léger boost aux buts
    if ref_impact and ref_impact["penalty_bias"] > 1.3:
        xg_home_adj *= 1.03
        xg_away_adj *= 1.03

    # ── 3.b Fusion xG Live (In-Play) ─────────────────────────────
    status = fixture.get("status", "NS")
    if status in ["1H", "2H", "HT", "LIVE", "ET", "P"]:
        elapsed = int(fixture.get("elapsed") or 0)
        live_stats = fixture.get("live_stats_json")
        if (
            elapsed > 0
            and isinstance(live_stats, dict)
            and "home" in live_stats
            and "away" in live_stats
        ):
            try:
                # API-Football renvoie parfois None ou ""
                val_h = live_stats["home"].get("xg")
                val_a = live_stats["away"].get("xg")
                obs_xg_home = float(val_h) if val_h else 0.0
                obs_xg_away = float(val_a) if val_a else 0.0

                if obs_xg_home > 0 or obs_xg_away > 0:
                    elapsed_fraction = min(elapsed / 90.0, 1.0)
                    # Le expected goals à la fin du match est ce qu'ils ont déjà généré
                    # + ce qu'ils sont censés générer dans le temps restant
                    rem_fraction = 1.0 - elapsed_fraction
                    xg_home_adj = obs_xg_home + (xg_home_adj * rem_fraction)
                    xg_away_adj = obs_xg_away + (xg_away_adj * rem_fraction)

                    context["live_xg_fusion"] = {
                        "elapsed": elapsed,
                        "obs_xg_home": obs_xg_home,
                        "obs_xg_away": obs_xg_away,
                        "blended_xg_home": round(xg_home_adj, 2),
                        "blended_xg_away": round(xg_away_adj, 2),
                    }
            except (ValueError, TypeError):
                pass

    # ── 4. Grille Poisson (rho per-ligue + calibration nuls) ─────
    # Clamp xG to realistic range before Poisson to prevent extreme inputs
    xg_home_adj = max(XG_FLOOR, min(XG_CEIL, xg_home_adj))
    xg_away_adj = max(XG_FLOOR, min(XG_CEIL, xg_away_adj))
    poisson_probs = poisson_grid(xg_home_adj, xg_away_adj, league_id=league_id)

    # ── 5. ELO ───────────────────────────────────────────────────

    home_elo_raw = elo_map.get(home_id, 1500)
    away_elo_raw = elo_map.get(away_id, 1500)

    # Appliquer le decay ELO si l'équipe n'a pas joué récemment
    home_elo = elo_with_decay(home_elo_raw, rest_days_h) if rest_days_h > 14 else home_elo_raw
    away_elo = elo_with_decay(away_elo_raw, rest_days_a) if rest_days_a > 14 else away_elo_raw

    elo_probs = get_elo_probs(home_elo, away_elo, league_id=league_id)
    context["elo_home"] = round(home_elo)
    context["elo_away"] = round(away_elo)
    if home_elo != home_elo_raw or away_elo != away_elo_raw:
        context["elo_decayed"] = True

    # ── 6. Cotes du marché ───────────────────────────────────────
    market = odds_to_probs(fixture_api_id) if fixture_api_id else None
    context["market"] = market

    # ── 7. Combinaison finale ────────────────────────────────────
    # Pondération adaptive selon disponibilité marché/ML
    w_poisson, w_elo, w_market = _get_blend_weights(
        has_odds=bool(market),
        has_ml=ML_AVAILABLE,
    )
    context["blend_weights"] = {
        "w_poisson": w_poisson,
        "w_elo": w_elo,
        "w_market": w_market,
    }

    # Ajustement selon l'avancée de la saison
    # En début de saison (< 8 matchs par équipe en moyenne), l'ELO capture mieux
    # les forces historiques que le Poisson qui se base sur peu de données.
    avg_played = league_data["avg_matches_played"] if league_data else 10
    if avg_played < 8:
        # Transférer 10 points de % de Poisson vers ELO (sauf si Poisson déjà bas)
        w_poisson = max(0.10, w_poisson - 0.10)
        w_elo = min(0.60, w_elo + 0.10)
        context["weights_adjusted"] = "early_season"

    if market:
        final_home = (
            poisson_probs["proba_home"] * w_poisson
            + elo_probs["elo_home"] * w_elo
            + market["market_home"] * w_market
        )
        final_draw = (
            poisson_probs["proba_draw"] * w_poisson
            + elo_probs["elo_draw"] * w_elo
            + market["market_draw"] * w_market
        )
        final_away = (
            poisson_probs["proba_away"] * w_poisson
            + elo_probs["elo_away"] * w_elo
            + market["market_away"] * w_market
        )
    else:
        # w_market == 0.0 when no market; use w_poisson and w_elo directly
        final_home = poisson_probs["proba_home"] * w_poisson + elo_probs["elo_home"] * w_elo
        final_draw = poisson_probs["proba_draw"] * w_poisson + elo_probs["elo_draw"] * w_elo
        final_away = poisson_probs["proba_away"] * w_poisson + elo_probs["elo_away"] * w_elo

    # Normaliser à 100% (garder en float — arrondi final en fin de pipeline)
    total = final_home + final_draw + final_away
    if total > 0:
        final_home = final_home / total * 100
        final_draw = final_draw / total * 100
        final_away = 100.0 - final_home - final_draw

    # ── 8. Probabilité de penalty ────────────────────────────────
    try:
        pen_proba, pen_lambda, pen_details = calculate_penalty_proba(
            fixture,
            referee_impact=ref_impact,
            stakes_home=stakes_h,
            stakes_away=stakes_a,
            home_id=home_id,
            away_id=away_id,
        )
    except Exception:
        pen_proba, _pen_lambda, pen_details = (
            26,
            0.30,
            {},
        )  # Fallback: use league-average penalty rate
    context["penalty"] = pen_details

    # ── 9. Prédictions ML XGBoost (si modèles entraînés) ─────────
    if ML_AVAILABLE:
        try:
            ml_context = {
                "home_attack_strength": league_data["strengths"].get(home_id, {}).get("home_attack")
                if league_data and league_data.get("strengths")
                else None,
                "home_defense_strength": league_data["strengths"]
                .get(home_id, {})
                .get("home_defense")
                if league_data and league_data.get("strengths")
                else None,
                "away_attack_strength": league_data["strengths"].get(away_id, {}).get("away_attack")
                if league_data and league_data.get("strengths")
                else None,
                "away_defense_strength": league_data["strengths"]
                .get(away_id, {})
                .get("away_defense")
                if league_data and league_data.get("strengths")
                else None,
                "home_elo": home_elo,
                "away_elo": away_elo,
                "elo_diff": home_elo - away_elo,
                "home_form": form_home,
                "away_form": form_away,
                "home_rest_days": context.get("rest_days_home", 7),
                "away_rest_days": context.get("rest_days_away", 7),
                "home_congestion_30d": context.get("congestion_home", 4),
                "away_congestion_30d": context.get("congestion_away", 4),
                "home_stakes": stakes_h,
                "away_stakes": stakes_a,
                "h2h_home_winrate": (
                    h2h_data.get("team_a_wins", 0) / max(h2h_data.get("total_matches", 1), 1)
                    if h2h_data and h2h_data.get("team_a_api_id") == home_id
                    else (
                        h2h_data.get("team_b_wins", 0) / max(h2h_data.get("total_matches", 1), 1)
                        if h2h_data
                        else 0.33
                    )
                ),
                "h2h_total_matches": h2h_data.get("total_matches", 0) if h2h_data else 0,
                "home_injury_count": len(injured_h),
                "away_injury_count": len(injured_a),
                "home_injury_attack_factor": atk_h,
                "home_injury_defense_factor": def_h,
                "away_injury_attack_factor": atk_a,
                "away_injury_defense_factor": def_a,
                "referee_penalty_bias": ref_impact.get("penalty_bias", 1.0) if ref_impact else 1.0,
                "market_home_prob": market.get("market_home") if market else None,
                "market_draw_prob": market.get("market_draw") if market else None,
                "market_away_prob": market.get("market_away") if market else None,
                "market_btts_prob": market.get("market_btts") if market else None,
                "market_over25_prob": market.get("market_over25") if market else None,
                "market_over15_prob": market.get("market_over15") if market else None,
                "xg_home": xg_home_adj,
                "xg_away": xg_away_adj,
                "league_avg_home_goals": league_data["league_avg_home"] if league_data else None,
                "league_avg_away_goals": league_data["league_avg_away"] if league_data else None,
            }

            # ── Compute advanced features (replace NaN-filled Phase 5/A2) ──
            try:
                adv_home = compute_advanced_features(home_team)
                adv_away = compute_advanced_features(away_team)
            except Exception:
                adv_home, adv_away = {}, {}

            ml_context.update(
                {
                    # Phase 5 features
                    "home_momentum": adv_home.get("momentum", 0),
                    "away_momentum": adv_away.get("momentum", 0),
                    "home_fatigue_index": context.get("congestion_home", 0),
                    "away_fatigue_index": context.get("congestion_away", 0),
                    "home_goal_diff_avg": adv_home.get("goal_diff_avg", 0),
                    "away_goal_diff_avg": adv_away.get("goal_diff_avg", 0),
                    "home_result_variance": adv_home.get("result_variance", 0),
                    "away_result_variance": adv_away.get("result_variance", 0),
                    "home_clean_sheet_rate": adv_home.get("clean_sheet_rate", 0),
                    "away_clean_sheet_rate": adv_away.get("clean_sheet_rate", 0),
                }
            )

            # Phase A2 features
            try:
                # xG per shot (from match_team_stats — uses 14 unused columns)
                shot_home = compute_team_shot_stats(home_id, league_id) if home_id else {}
                shot_away = compute_team_shot_stats(away_id, league_id) if away_id else {}
                # League-level rates
                league_rates = compute_league_rates(league_id)
            except Exception:
                shot_home, shot_away, league_rates = {}, {}, {}

            ml_context.update(
                {
                    "home_ppg_last5": adv_home.get("ppg_last5", 1.5),
                    "away_ppg_last5": adv_away.get("ppg_last5", 1.5),
                    "home_btts_rate_last10": adv_home.get("btts_rate_last10", 0.5),
                    "away_btts_rate_last10": adv_away.get("btts_rate_last10", 0.5),
                    "home_over25_rate_last10": adv_home.get("over25_rate_last10", 0.5),
                    "away_over25_rate_last10": adv_away.get("over25_rate_last10", 0.5),
                    "home_xg_per_shot": shot_home.get("xg_per_shot"),
                    "away_xg_per_shot": shot_away.get("xg_per_shot"),
                    "league_avg_btts_rate": league_rates.get("league_avg_btts_rate", 0.5),
                    "league_avg_over25_rate": league_rates.get("league_avg_over25_rate", 0.48),
                    "elo_diff_squared": (home_elo - away_elo) ** 2,
                    "form_diff": form_home - form_away,
                    # Momentum long terme (12 matchs)
                    "home_form_long": form_long_home,
                    "away_form_long": form_long_away,
                    "form_long_diff": form_long_home - form_long_away,
                }
            )

            ml_preds = get_ml_predictions(ml_context)
            context["ml_predictions"] = ml_preds

            if ml_preds.get("ml_home") is not None:
                # Pondération : 50% modèle stats, 50% ML XGBoost
                w_stats = WEIGHT_STATS_VS_ML
                w_ml = WEIGHT_ML
                final_home = final_home * w_stats + ml_preds["ml_home"] * w_ml
                final_draw = final_draw * w_stats + ml_preds["ml_draw"] * w_ml
                final_away = 100.0 - final_home - final_draw

            if ml_preds.get("ml_btts") is not None:
                poisson_probs["proba_btts"] = (
                    poisson_probs["proba_btts"] * 0.6 + ml_preds["ml_btts"] * 0.4
                )
            if ml_preds.get("ml_over25") is not None:
                poisson_probs["proba_over_25"] = (
                    poisson_probs["proba_over_25"] * 0.6 + ml_preds["ml_over25"] * 0.4
                )
            if ml_preds.get("ml_over15") is not None:
                poisson_probs["proba_over_15"] = (
                    poisson_probs["proba_over_15"] * 0.6 + ml_preds["ml_over15"] * 0.4
                )
            if ml_preds.get("ml_over05") is not None:
                poisson_probs["proba_over_05"] = (
                    poisson_probs["proba_over_05"] * 0.6 + ml_preds["ml_over05"] * 0.4
                )

            context["ml_active"] = True
        except Exception as e:
            logger.warning("ML prediction failed", exc_info=True)
            context["ml_active"] = False
            context["ml_error"] = str(e)

    # ── 9b. Stakes draw boost (applied AFTER ML to avoid contradictions) ──
    # When both teams have high stakes (>1.0), boost draw prob
    # and redistribute from home/away proportionally
    if stakes_h > 1.0 and stakes_a > 1.0:
        draw_boost = STAKES_DRAW_BOOST * 100  # e.g. 3%
        final_draw = final_draw + draw_boost
        home_share = final_home / max(final_home + final_away, 1)
        final_home = final_home - draw_boost * home_share
        final_away = 100.0 - final_home - final_draw

    # ── 9c. European competition draw boost ────────────────────
    # CL/EL matches are higher stakes → more cautious → more draws
    # Only apply if this league does NOT already have a calibrated draw factor
    # in DRAW_FACTOR_BY_LEAGUE (which the Poisson draw calibration already uses).
    # Applying both would double-count the CL/EL draw tendency.
    euro_boost = EURO_COMP_DRAW_BOOST.get(league_id, 0)
    has_calibrated_draw = league_id in DRAW_FACTOR_BY_LEAGUE
    if euro_boost > 0 and not has_calibrated_draw:
        boost_pts = euro_boost * 100
        final_draw = final_draw + boost_pts
        home_share = final_home / max(final_home + final_away, 1)
        final_home = final_home - boost_pts * home_share
        final_away = 100.0 - final_home - final_draw
        context["euro_draw_boost"] = euro_boost

    # ── 10. Calibration fine (si disponible) ───────────────────────
    # 1X2: Bayesian shrinkage (safe with any sample size, converges to identity with more data).
    # Replaces the disabled Platt scaling which produced degenerate params with <100 samples.
    # Once MIN_ISOTONIC_SAMPLES (500) is reached, apply_calibration will use Isotonic instead.
    try:
        from src.models.calibrate import calibrate_1x2_bayesian

        final_home, final_draw, final_away = calibrate_1x2_bayesian(
            final_home, final_draw, final_away, league_id=league_id
        )
        context["calibration_1x2"] = "bayesian_shrinkage"
    except Exception:
        context["calibration_1x2"] = "skipped"

    if is_calibration_available():
        try:
            from src.models.calibrate import apply_calibration

            lid = league_id
            # BTTS and Over markets: binary calibration via Platt/Isotonic
            poisson_probs["proba_btts"] = apply_calibration(
                poisson_probs["proba_btts"], "btts", lid
            )
            poisson_probs["proba_over_05"] = apply_calibration(
                poisson_probs["proba_over_05"], "over_05", lid
            )
            poisson_probs["proba_over_15"] = apply_calibration(
                poisson_probs["proba_over_15"], "over_15", lid
            )
            poisson_probs["proba_over_25"] = apply_calibration(
                poisson_probs["proba_over_25"], "over_25", lid
            )

            context["ml_calibrated"] = True
        except Exception:
            context["ml_calibrated"] = False  # Non-critical: predictions work without calibration

    # ── 10b. Soft cap — probas 1X2 plafonnées à 85% ──────────────
    # Capping prevents compounding factors from producing unrealistic extremes.
    # 85% allows strong favorites (PSG vs lower division) while preventing
    # degenerate probabilities.
    MAX_WIN_PROB = 85
    if final_home > MAX_WIN_PROB:
        excess = final_home - MAX_WIN_PROB
        final_home = MAX_WIN_PROB
        total_remaining = final_draw + final_away
        if total_remaining > 0:
            final_draw = final_draw + excess * (final_draw / total_remaining)
            final_away = 100.0 - final_home - final_draw
        else:
            final_draw = final_draw + excess * 0.5
            final_away = 100.0 - final_home - final_draw
    elif final_away > MAX_WIN_PROB:
        excess = final_away - MAX_WIN_PROB
        final_away = MAX_WIN_PROB
        total_remaining = final_draw + final_home
        if total_remaining > 0:
            final_draw = final_draw + excess * (final_draw / total_remaining)
            final_home = 100.0 - final_away - final_draw
        else:
            final_draw = final_draw + excess * 0.5
            final_home = 100.0 - final_away - final_draw

    # ── ARRONDI FINAL — une seule fois en fin de pipeline ─────────
    final_home = round(final_home)
    final_draw = round(final_draw)
    final_away = 100 - final_home - final_draw

    # ── 10. Résultat final ────────────────────────────────────────
    result = {
        "proba_home": final_home,
        "proba_draw": final_draw,
        "proba_away": final_away,
        "proba_btts": poisson_probs["proba_btts"],
        "proba_over_05": poisson_probs["proba_over_05"],
        "proba_over_15": poisson_probs["proba_over_15"],
        "proba_over_25": poisson_probs["proba_over_25"],
        "proba_over_35": poisson_probs["proba_over_35"],
        "proba_penalty": pen_proba,
        "proba_dc_1x": final_home + final_draw,
        "proba_dc_x2": final_draw + final_away,
        "proba_dc_12": final_home + final_away,
        "correct_score": poisson_probs["correct_score"],
        "proba_correct_score": poisson_probs["proba_correct_score"],
        "xg_home": round(xg_home_adj, 2),
        "xg_away": round(xg_away_adj, 2),
        "model_version": "hybrid_v3_ml"
        if context.get("ml_active")
        else ("hybrid_v2_calibrated" if context.get("ml_calibrated") else "hybrid_v1"),
        "context": context,
        # Handicaps asiatiques (calculés par poisson_grid)
        "ah_home_minus_05": poisson_probs.get("ah_home_minus_05"),
        "ah_home_minus_10": poisson_probs.get("ah_home_minus_10"),
        "ah_home_minus_15": poisson_probs.get("ah_home_minus_15"),
        "ah_away_plus_05": poisson_probs.get("ah_away_plus_05"),
        "ah_away_plus_10": poisson_probs.get("ah_away_plus_10"),
        "ah_away_plus_15": poisson_probs.get("ah_away_plus_15"),
    }

    # B3: Pari recommandé — Priorité à la probabilité la plus élevée (seuil min 55%)
    # Marchés inclus (Over 0.5 exclu car cote quasi nulle)

    # Use FINAL blended probabilities for bet recommendation (not raw Poisson)
    dc_1x = final_home + final_draw
    dc_x2 = final_draw + final_away
    over_15 = poisson_probs["proba_over_15"]
    COMBO_THRESHOLD = 65  # Both legs must clear this to recommend combined bet

    # Priority rule: if both DC and Over 1.5 are individually strong → recommend combined
    if dc_1x >= COMBO_THRESHOLD and over_15 >= COMBO_THRESHOLD:
        result["recommended_bet"] = "1X + Plus de 1.5 buts"
        result["kelly_edge"] = round((poisson_probs.get("proba_dc1x_over15", dc_1x) - 50) / 100, 3)
        result["kelly_fraction"] = 0
        result["value_bet"] = True
    elif dc_x2 >= COMBO_THRESHOLD and over_15 >= COMBO_THRESHOLD:
        result["recommended_bet"] = "X2 + Plus de 1.5 buts"
        result["kelly_edge"] = round((poisson_probs.get("proba_dcx2_over15", dc_x2) - 50) / 100, 3)
        result["kelly_fraction"] = 0
        result["value_bet"] = True
    else:
        candidate_bets: list[tuple[str, float]] = [
            ("Plus de 1.5 buts", over_15),
            ("Plus de 2.5 buts", poisson_probs["proba_over_25"]),
            ("BTTS Oui", poisson_probs["proba_btts"]),
            ("Victoire Domicile", final_home),
            ("Victoire Extérieur", final_away),
            ("Match Nul", final_draw),
            ("Double Chance 1X", dc_1x),
            ("Double Chance X2", dc_x2),
            ("1X + Plus de 1.5 buts", poisson_probs.get("proba_dc1x_over15", 0)),
            ("X2 + Plus de 1.5 buts", poisson_probs.get("proba_dcx2_over15", 0)),
        ]

        MIN_PROBA = 55
        eligible = [(name, prob) for name, prob in candidate_bets if prob >= MIN_PROBA]

        if eligible:
            best_name, best_prob = max(eligible, key=lambda x: x[1])
        else:
            best_name, best_prob = max(candidate_bets, key=lambda x: x[1])

        result["recommended_bet"] = best_name
        result["kelly_edge"] = round((best_prob - 50) / 100, 3)
        result["kelly_fraction"] = 0
        result["value_bet"] = best_prob >= 65

    # Score de confiance redesigné (1–10)
    # Redesigned march 2026: old formula rewarded polarized predictions (high spread)
    # which were often wrong (draws missed). New formula:
    #   (a) model agreement (Poisson vs ML vs market)
    #   (b) data quality
    #   (c) prediction clarity — penalize close 3-way races AND extreme overconfidence
    sorted_probs = sorted([final_home, final_draw, final_away], reverse=True)
    spread = sorted_probs[0] - sorted_probs[1]

    # 1. Accord inter-modèles (0–3 pts)
    agreement_pts = 0
    n_sources = 0
    source_winners = []  # Which outcome each source picks

    # Poisson winner
    poisson_vals = [
        poisson_probs["proba_home"],
        poisson_probs["proba_draw"],
        poisson_probs["proba_away"],
    ]
    poisson_winner = ["H", "D", "A"][poisson_vals.index(max(poisson_vals))]
    source_winners.append(poisson_winner)
    n_sources += 1

    # ML winner
    if context.get("ml_active") and context.get("ml_predictions"):
        ml_preds_ctx = context["ml_predictions"]
        ml_h = ml_preds_ctx.get("ml_home", 0)
        ml_d = ml_preds_ctx.get("ml_draw", 0)
        ml_a = ml_preds_ctx.get("ml_away", 0)
        if ml_h or ml_d or ml_a:
            ml_vals = [ml_h, ml_d, ml_a]
            ml_winner = ["H", "D", "A"][ml_vals.index(max(ml_vals))]
            source_winners.append(ml_winner)
            n_sources += 1

    # Market winner
    if market:
        mkt_vals = [
            market.get("market_home", 0),
            market.get("market_draw", 0),
            market.get("market_away", 0),
        ]
        if any(mkt_vals):
            mkt_winner = ["H", "D", "A"][mkt_vals.index(max(mkt_vals))]
            source_winners.append(mkt_winner)
            n_sources += 1

    # Count agreement: all sources pick the same winner
    if n_sources >= 2:
        winner_counts = Counter(source_winners)
        most_common_count = winner_counts.most_common(1)[0][1]
        if most_common_count == n_sources:
            agreement_pts = 3  # Full agreement
        elif most_common_count >= 2:
            agreement_pts = 2  # Partial agreement
        else:
            agreement_pts = 0  # No agreement
    else:
        agreement_pts = 1  # Only one source

    # 2. Qualité des données (0–3 pts)
    data_quality = 0
    if market:
        data_quality += 1
    if h2h_data and h2h_data.get("total_matches", 0) >= 3:
        data_quality += 1
    if league_data:
        data_quality += 1

    # 3. Prediction clarity (0–3 pts)
    # Moderate spread = good. Too low (3-way toss-up) or too high (overconfident) = bad
    # Sweet spot: spread 15-30 points
    if spread < 8:
        clarity_pts = 0  # 3-way toss-up, inherently unpredictable
    elif spread < 15:
        clarity_pts = 1  # Slight favorite, still uncertain
    elif spread < 30:
        clarity_pts = 3  # Clear favorite, most reliable zone
    elif spread < 40:
        clarity_pts = 2  # Strong favorite, but draw risk often missed
    else:
        clarity_pts = 1  # Extreme favorite, often overconfident

    # 4. Draw risk penalty (-1 pt if draw is close to the favorite)
    draw_penalty = 0
    if final_draw >= 28 and spread < 20:
        draw_penalty = -1  # High draw probability + close match = unreliable

    confidence = max(1, min(10, agreement_pts + data_quality + clarity_pts + draw_penalty))
    result["confidence_score"] = confidence

    # ── 11. Final probability clamping ─────────────────────────────
    # Ensures no extreme/unrealistic values survive the pipeline
    result = clamp_probabilities(result)

    return result
