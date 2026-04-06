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
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from src.config import SEASON, supabase
from src.constants import (
    AVG_ATTACKER_FOULS_DRAWN_PER_90,
    AVG_DEFENDER_FOULS_PER_90,
    BASE_PENALTY_RATE,
    DEFAULT_ELO,
    DIXON_COLES_RHO,
    DRAW_FACTOR,
    DRAW_FACTOR_BY_LEAGUE,
    ELO_DECAY_RATE,
    HOME_ELO_ADVANTAGE,
    HOME_XG_BONUS,
    K_FACTOR,
    KELLY_FRACTION,
    KELLY_MAX_BET_FRACTION,
    MIN_VALUE_EDGE,
    STAKES_DRAW_BOOST,
    WEIGHT_ELO,
    WEIGHT_ELO_NO_MARKET,
    WEIGHT_MARKET,
    WEIGHT_ML,
    WEIGHT_POISSON,
    WEIGHT_POISSON_NO_MARKET,
    WEIGHT_STATS_VS_ML,
    XG_CEIL,
    XG_FLOOR,
)
from scipy.stats import poisson

# Import calibration (optionnel — n'échoue pas si pas encore de données)
try:
    from src.models.calibrate import apply_calibration

    CALIBRATION_AVAILABLE = True
except ImportError:
    CALIBRATION_AVAILABLE = False

# Import modèles ML entraînés (optionnel)
try:
    from src.models.ml_predictor import get_ml_predictions, load_models

    ML_AVAILABLE = load_models()
except ImportError:
    ML_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════
#  1. MODÈLE DE POISSON
# ═══════════════════════════════════════════════════════════════════


def dixon_coles_correction(
    h: int, a: int, lambda_h: float, lambda_a: float, rho: float = DIXON_COLES_RHO
) -> float:
    """Apply the Dixon-Coles correction for low-scoring outcomes.

    The independent Poisson model under-estimates the correlation between
    home and away goals for low scores.  Dixon & Coles (1997) introduced
    a correlation parameter rho that adjusts probabilities for scorelines
    where both teams score 0 or 1.  With a typical negative rho, 0-0 and
    1-1 draws become more likely, while 0-1 and 1-0 become less likely.

    Args:
        h: Home goals.
        a: Away goals.
        lambda_h: Expected goals (xG) for the home team.
        lambda_a: Expected goals (xG) for the away team.
        rho: Correlation parameter (typically -0.03 to -0.20).

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
    xg_home: float, xg_away: float, max_goals: int = 7
) -> dict[str, int | float | str]:
    """Build the Dixon-Coles adjusted Poisson probability grid.

    Computes match-outcome probabilities (1X2, BTTS, over/under, double
    chance) from Poisson distributions for each team's goals, corrected
    with the Dixon-Coles correlation factor for low-scoring outcomes.

    Args:
        xg_home: Expected goals for the home team.
        xg_away: Expected goals for the away team.
        max_goals: Upper bound (exclusive) on goals per team in the grid.

    Returns:
        Dictionary containing rounded percentage probabilities for every
        market (home/draw/away, BTTS, over lines, double chance), the most
        likely correct score, and the adjusted xG values used.
    """
    # B1: Dynamic rho — stronger negative correlation for lower-scoring matches
    # Uses smooth linear interpolation instead of hard step function to avoid
    # discontinuities at the boundaries (e.g. xG 1.99 vs 2.01)
    base_rho = DIXON_COLES_RHO  # -0.13 empirical baseline for top European leagues
    xg_total = xg_home + xg_away
    # Scale factor: 1.3 at xG_total=1.5 (defensive), 1.0 at 2.75, 0.7 at xG_total=4.0
    rho_scale = max(0.7, min(1.3, 1.3 - (xg_total - 1.5) * 0.24))
    rho = base_rho * rho_scale

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

    # Return float percentages — rounding deferred to final output
    # to avoid cascading rounding errors through combination steps
    return {
        "proba_home": home_win * 100,
        "proba_draw": draw * 100,
        "proba_away": away_win * 100,
        "proba_btts": btts * 100,
        "proba_btts_over25": proba_btts_over25 * 100,
        "proba_cs_home": proba_cs_home * 100,
        "proba_cs_away": proba_cs_away * 100,
        "proba_over_05": over_05 * 100,
        "proba_over_15": over_15 * 100,
        "proba_over_25": over_25 * 100,
        "proba_over_35": over_35 * 100,
        "proba_dc_1x": (home_win + draw) * 100,
        "proba_dc_x2": (draw + away_win) * 100,
        "proba_dc_12": (home_win + away_win) * 100,
        "proba_dc1x_over15": dc1x_over15 * 100,
        "proba_dcx2_over15": dcx2_over15 * 100,
        "xg_home": round(xg_home, 2),
        "xg_away": round(xg_away, 2),
        "correct_score": correct_score,
        "proba_correct_score": round(correct_score_prob * 100, 1),
        # Handicaps asiatiques
        "ah_home_minus_05": ah_home_minus_05 * 100,
        "ah_home_minus_10": ah_home_minus_10_effective * 100,
        "ah_home_minus_15": ah_home_minus_15 * 100,
        "ah_away_plus_05": (1 - ah_home_minus_05) * 100,
        "ah_away_plus_10": (1 - ah_home_minus_10_effective) * 100,
        "ah_away_plus_15": (1 - ah_home_minus_15) * 100,
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
    # ── Option 1 : Récupérer les stats xG de la Vue Supabase ──
    xg_stats = (
        supabase.table("team_xg_stats")
        .select("*")
        .eq("league_id", league_id)
        .eq("season", SEASON)
        .execute()
        .data
    )

    if not xg_stats or len(xg_stats) < 4:
        # Fallback de sécurité si la vue n'est pas peuplée
        return None

    # Moyennes de la ligue basées sur les xG
    total_xg_for = sum((s["xg_for_total"] or 0) for s in xg_stats)
    total_xg_against = sum((s["xg_against_total"] or 0) for s in xg_stats)
    total_matches = max(sum(s["matches_played"] for s in xg_stats), 1)

    # Note: La vue agglomère Home et Away pour l'instant (on le séparera plus tard si besoin)
    league_avg_xg_scored = total_xg_for / total_matches
    league_avg_xg_conceded = total_xg_against / total_matches

    # Avantage domicile global fallback
    strengths = {}
    for s in xg_stats:
        tid = s["team_api_id"]
        mp = max(s["matches_played"], 1)

        # Ratios bruts xG
        team_avg_xg_for = (s["xg_for_total"] or 0) / mp
        team_avg_xg_against = (s["xg_against_total"] or 0) / mp
        
        # Vu que xg_stats agglomère home/away, pour l'instant on utilise la même force
        raw_atk = team_avg_xg_for / max(league_avg_xg_scored, 0.5)
        raw_def = team_avg_xg_against / max(league_avg_xg_conceded, 0.5)

        raw_home_atk = raw_atk
        raw_home_def = raw_def
        raw_away_atk = raw_atk
        raw_away_def = raw_def

        # Pour pallier à la vue agrégée, l'avantage domicile est fixé au bonus xG de la ligue (ex: 1.12)
        # On regresse la performance si échantillon faible
        strengths[tid] = {
            "home_attack": regress_to_mean(raw_home_atk, mp, 1.0),
            "home_defense": regress_to_mean(raw_home_def, mp, 1.0),
            "away_attack": regress_to_mean(raw_away_atk, mp, 1.0),
            "away_defense": regress_to_mean(raw_away_def, mp, 1.0),
            "home_advantage": HOME_XG_BONUS
        }

    # Pour xg_home et xg_away, on simule que Home marque X% de plus globalement
    return {
        "strengths": strengths,
        "league_avg_home": league_avg_xg_scored * (HOME_XG_BONUS),
        "league_avg_away": league_avg_xg_scored * (2.0 - HOME_XG_BONUS),
        "avg_matches_played": total_matches / len(xg_stats),
    }


def calculate_xg(
    home_team_id: int,
    away_team_id: int,
    league_data: dict | None,
    adjustments: dict | None = None,
) -> tuple[float, float]:
    """Calculate expected goals for a fixture.

    Formula:
        ``xG_home = home_attack * away_defense * league_avg * home_bonus * adjustments``

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
    if not league_data:
        from src.constants import XG_FALLBACK_AWAY, XG_FALLBACK_HOME

        return XG_FALLBACK_HOME, XG_FALLBACK_AWAY  # Fallback

    strengths = league_data["strengths"]
    home_s = strengths.get(home_team_id)
    away_s = strengths.get(away_team_id)

    if not home_s or not away_s:
        from src.constants import XG_FALLBACK_AWAY, XG_FALLBACK_HOME

        return XG_FALLBACK_HOME, XG_FALLBACK_AWAY

    # Avantage domicile spécifique à l'équipe, ou la moyenne de la ligue si manquant
    home_bonus = home_s.get("home_advantage", HOME_XG_BONUS)

    xg_home = (
        home_s["home_attack"] * away_s["away_defense"] * league_data["league_avg_home"] * home_bonus
    )
    xg_away = away_s["away_attack"] * home_s["home_defense"] * league_data["league_avg_away"]

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
    """Convert Elo ratings into 1X2 probabilities.

    A home-advantage offset is added before computing expected scores,
    and a draw component is estimated from the gap between the two sides.
    When *league_id* is provided, uses the league-calibrated draw factor
    (Serie A draws more than Bundesliga, etc.).

    Args:
        home_elo: Elo rating of the home team.
        away_elo: Elo rating of the away team.
        league_id: Optional league identifier for calibrated draw factor.

    Returns:
        Dictionary with keys ``"elo_home"``, ``"elo_draw"``, ``"elo_away"``
        as rounded integer percentages.
    """
    # On utilise simplement l'ELO_EXPECTED pour les win et loss
    p_home = elo_expected(home_elo + HOME_ELO_ADVANTAGE, away_elo)
    p_away = elo_expected(away_elo, home_elo + HOME_ELO_ADVANTAGE)

    # Normalisation sur 100% (sans nul)
    total = p_home + p_away
    p_home /= total
    p_away /= total

    return {
        "elo_home": p_home * 100,
        "elo_away": p_away * 100,
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
        .select("api_fixture_id, home_team, away_team, home_goals, away_goals, league_id")
        .eq("status", "FT")
        .order("date")
        .execute()
        .data
    )

    # Charger mapping nom -> api_id
    teams = supabase.table("teams").select("api_id, name").execute().data
    name_to_id = {t["name"]: t["api_id"] for t in teams}

    for fix in fixtures:
        hid = name_to_id.get(fix["home_team"])
        aid = name_to_id.get(fix["away_team"])
        if not hid or not aid:
            continue
        if hid not in elos or aid not in elos:
            continue

        hg = fix["home_goals"] or 0
        ag = fix["away_goals"] or 0
        gd = abs(hg - ag)

        h_elo = elos[hid] + HOME_ELO_ADVANTAGE
        a_elo = elos[aid]

        h_exp = elo_expected(h_elo, a_elo)
        a_exp = elo_expected(a_elo, h_elo)

        if hg > ag:
            h_act, a_act = 1.0, 0.0
        elif hg == ag:
            h_act, a_act = 0.5, 0.5
        else:
            h_act, a_act = 0.0, 1.0

        elos[hid] = elo_update(elos[hid], h_exp, h_act, goal_diff=gd)
        elos[aid] = elo_update(elos[aid], a_exp, a_act, goal_diff=gd)

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

        total_weight += 3 * sos_multiplier * weight

    return (form_score / total_weight if total_weight > 0 else 0.5), form_letters


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

        missing_players.append({
            "player_name": name,
            "position": position,
            "reason": reason,
            "rating": rating,
            "minutes_played": mins,
            "is_starter": is_starter,
            "goals": s.get("goals", 0),
            "assists": s.get("assists", 0),
        })

    # ── 5. Calcul des facteurs finaux via VORP ──
    from src.models.injury_vorp import calculate_vorp_impact
    team_context = {
        "total_goals": getattr(team_total_goals, "real", 1),
        "total_assists": getattr(team_total_assists, "real", 1)
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

    return {
        "market_home": raw_h / overround * 100,
        "market_draw": raw_d / overround * 100,
        "market_away": raw_a / overround * 100,
        "overround": round(overround, 3),
        "raw_odds_home": o["home_win_odds"],
        "raw_odds_draw": o.get("draw_odds"),
        "raw_odds_away": o["away_win_odds"],
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
#  MOTEUR PRINCIPAL : ANALYSER UN MATCH
# ═══════════════════════════════════════════════════════════════════


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
    league_data = calculate_team_strengths(league_id)
    xg_home, xg_away = calculate_xg(home_id or 0, away_id or 0, league_data)

    # ── ELO Préalable (requis pour le calcul de forme SOS) ───────
    elos = supabase.table("team_elo").select("team_api_id, elo_rating").execute().data
    elo_map = {e["team_api_id"]: e["elo_rating"] for e in elos}
    name_to_elo = {t["name"]: elo_map.get(t["api_id"], 1500) for t in teams}

    # ── 2. Ajustements ───────────────────────────────────────────
    # Forme (récente pondérée avec Strength of Schedule)
    form_home, form_letters_h = calculate_form(home_team, home_only=True, name_to_elo=name_to_elo)
    form_away, form_letters_a = calculate_form(away_team, home_only=False, name_to_elo=name_to_elo)
    form_factor_h = 0.85 + form_home * 0.30  # Range: 0.85 - 1.15
    form_factor_a = 0.85 + form_away * 0.30
    context["form_home"] = "".join(form_letters_h)
    context["form_away"] = "".join(form_letters_a)

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

    # xG_home = force offensive dom × faiblesse défensive adverse (blessures ext)
    # Compound floor: prevent multiplicative factors from crushing xG below 60%
    # of base (extreme stacking of form+rest+h2h+weather+injuries is unrealistic)
    xg_home_adj = max(xg_home * 0.60, xg_home * home_base * atk_h * def_a)
    # xG_away = force offensive ext × faiblesse défensive dom (blessures dom)
    xg_away_adj = max(xg_away * 0.60, xg_away * away_base * atk_a * def_h)

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

    # ── 4. Grille Poisson ────────────────────────────────────────
    poisson_probs = poisson_grid(xg_home_adj, xg_away_adj)

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
    # All probabilities stay as floats until final output to avoid
    # cascading rounding errors (each round() step adds ±0.5% error).
    # Pondération dynamique :
    w_poisson = WEIGHT_POISSON
    w_elo = WEIGHT_ELO
    w_market = WEIGHT_MARKET

    # Ajustement selon l'avancée de la saison
    # En début de saison (< 8 matchs par équipe en moyenne), l'ELO capture mieux
    # les forces historiques que le Poisson qui se base sur peu de données.
    avg_played = league_data["avg_matches_played"] if league_data else 10
    if avg_played < 8:
        # Transférer 10 points de % de Poisson vers ELO
        w_poisson = max(0.10, w_poisson - 0.10)
        w_elo += 0.10
        context["weights_adjusted"] = "early_season"

    if market:
        final_home = (
            poisson_probs["proba_home"] * w_poisson
            + elo_probs["elo_home"] * w_elo
            + market["market_home"] * w_market
        )
        # On fait pleinement confiance au Poisson Bivarié pour la probabilité du Nul (Phase 4.3)
        final_draw = (
            poisson_probs["proba_draw"] * (w_poisson + w_elo)
            + market["market_draw"] * w_market
        )
        final_away = (
            poisson_probs["proba_away"] * w_poisson
            + elo_probs["elo_away"] * w_elo
            + market["market_away"] * w_market
        )
    else:
        w_p = WEIGHT_POISSON_NO_MARKET
        w_e = WEIGHT_ELO_NO_MARKET
        final_home = poisson_probs["proba_home"] * w_p + elo_probs["elo_home"] * w_e
        final_draw = poisson_probs["proba_draw"] * (w_p + w_e)
        final_away = poisson_probs["proba_away"] * w_p + elo_probs["elo_away"] * w_e

    # Normaliser à 100% (float, no rounding yet)
    total = final_home + final_draw + final_away
    if total > 0:
        final_home = final_home / total * 100
        final_draw = final_draw / total * 100
        final_away = final_away / total * 100

    # ── 7b. Stakes draw boost ──────────────────────────────────
    # When both teams have high stakes (>1.0), boost draw prob
    # and redistribute from home/away proportionally
    if stakes_h > 1.0 and stakes_a > 1.0:
        draw_boost = STAKES_DRAW_BOOST * 100  # e.g. 3%
        final_draw += draw_boost
        # Redistribute boost proportionally from home and away
        home_share = final_home / max(final_home + final_away, 1)
        final_home -= draw_boost * home_share
        final_away = 100 - final_home - final_draw

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
                "h2h_home_winrate": h2h_data.get("team_a_wins", 0)
                / max(h2h_data.get("total_matches", 1), 1)
                if h2h_data
                else 0.33,
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
                "xg_home": xg_home_adj,
                "xg_away": xg_away_adj,
                "league_avg_home_goals": league_data["league_avg_home"] if league_data else None,
                "league_avg_away_goals": league_data["league_avg_away"] if league_data else None,
                # Phase 5 — Features avancées (values will be NaN if unavailable,
                # handled by the imputer in ml_predictor)
                "home_momentum": None,
                "away_momentum": None,
                "home_fatigue_index": context.get("congestion_home", 0),
                "away_fatigue_index": context.get("congestion_away", 0),
                "home_goal_diff_avg": None,
                "away_goal_diff_avg": None,
                "home_result_variance": None,
                "away_result_variance": None,
                "home_clean_sheet_rate": None,
                "away_clean_sheet_rate": None,
            }

            ml_preds = get_ml_predictions(ml_context)
            context["ml_predictions"] = ml_preds

            if ml_preds.get("ml_home") is not None:
                # Pondération : 60% modèle stats, 40% ML XGBoost (floats, no rounding)
                w_stats = WEIGHT_STATS_VS_ML
                w_ml = WEIGHT_ML
                final_home = final_home * w_stats + ml_preds["ml_home"] * w_ml
                final_draw = final_draw * w_stats + ml_preds["ml_draw"] * w_ml
                final_away = 100 - final_home - final_draw

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
            context["ml_active"] = False
            context["ml_error"] = str(e)

    # ── 10. Calibration fine (si disponible) ───────────────────────
    if CALIBRATION_AVAILABLE:
        try:
            lid = league_id
            cal_home = apply_calibration(round(final_home), "1x2_home", lid)
            cal_draw = apply_calibration(round(final_draw), "1x2_draw", lid)
            cal_away = apply_calibration(round(final_away), "1x2_away", lid)
            # Renormaliser à 100% (stay as floats)
            cal_total = cal_home + cal_draw + cal_away
            if cal_total > 0:
                final_home = cal_home / cal_total * 100
                final_draw = cal_draw / cal_total * 100
                final_away = 100 - final_home - final_draw

            poisson_probs["proba_btts"] = apply_calibration(
                round(poisson_probs["proba_btts"]), "btts", lid
            )
            poisson_probs["proba_over_05"] = apply_calibration(
                round(poisson_probs["proba_over_05"]), "over_05", lid
            )
            poisson_probs["proba_over_15"] = apply_calibration(
                round(poisson_probs["proba_over_15"]), "over_15", lid
            )
            poisson_probs["proba_over_25"] = apply_calibration(
                round(poisson_probs["proba_over_25"]), "over_25", lid
            )

            context["ml_calibrated"] = True
        except Exception:
            context["ml_calibrated"] = False  # Non-critical: predictions work without calibration

    # ── 11. Single rounding pass — all probabilities rounded here ─
    final_home = round(final_home)
    final_draw = round(final_draw)
    final_away = 100 - final_home - final_draw

    proba_btts = round(poisson_probs["proba_btts"])
    proba_over_05 = round(poisson_probs["proba_over_05"])
    proba_over_15 = round(poisson_probs["proba_over_15"])
    proba_over_25 = round(poisson_probs["proba_over_25"])
    proba_over_35 = round(poisson_probs["proba_over_35"])

    # ── 12. Résultat final ────────────────────────────────────────
    result: dict[str, Any] = {
        "proba_home": final_home,
        "proba_draw": final_draw,
        "proba_away": final_away,
        "proba_btts": proba_btts,
        "proba_over_05": proba_over_05,
        "proba_over_15": proba_over_15,
        "proba_over_25": proba_over_25,
        "proba_over_35": proba_over_35,
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
        # Handicaps asiatiques (calculés par poisson_grid, rounded here)
        "ah_home_minus_05": round(poisson_probs.get("ah_home_minus_05", 0)),
        "ah_home_minus_10": round(poisson_probs.get("ah_home_minus_10", 0)),
        "ah_home_minus_15": round(poisson_probs.get("ah_home_minus_15", 0)),
        "ah_away_plus_05": round(poisson_probs.get("ah_away_plus_05", 0)),
        "ah_away_plus_10": round(poisson_probs.get("ah_away_plus_10", 0)),
        "ah_away_plus_15": round(poisson_probs.get("ah_away_plus_15", 0)),
    }

    # ── 13. Pari recommandé — Sélection par EXPECTED VALUE, pas probabilité seule ──
    # FIX: Previously picked highest probability market. For value betting,
    # we must select by highest edge (our_prob vs implied_prob) × odds = expected value.
    dc_1x = round(poisson_probs.get("proba_dc_1x", 0))
    dc_x2 = round(poisson_probs.get("proba_dc_x2", 0))
    over_15_prob = proba_over_15
    COMBO_THRESHOLD = 65  # Both legs must clear this to recommend combined bet

    # Build candidate list with associated odds for edge/EV calculation
    candidate_bets: list[tuple[str, float, float | None]] = [
        ("Plus de 1.5 buts", over_15_prob, None),
        ("Plus de 2.5 buts", proba_over_25, None),
        ("BTTS Oui", proba_btts, None),
        ("Victoire Domicile", final_home, market.get("raw_odds_home") if market else None),
        ("Victoire Extérieur", final_away, market.get("raw_odds_away") if market else None),
        ("Match Nul", final_draw, market.get("raw_odds_draw") if market else None),
        ("Double Chance 1X", dc_1x, None),
        ("Double Chance X2", dc_x2, None),
        ("1X + Plus de 1.5 buts", round(poisson_probs.get("proba_dc1x_over15", 0)), None),
        ("X2 + Plus de 1.5 buts", round(poisson_probs.get("proba_dcx2_over15", 0)), None),
    ]

    def _compute_edge_ev(prob: float, odds: float | None) -> tuple[float, float]:
        """Compute (edge, expected_value) for a bet. Edge = ROI = prob*odds - 1."""
        if odds and odds > 1:
            edge = calculate_roi(prob, odds)
            ev = edge * odds  # Expected profit per unit at these odds
            return edge, ev
        # No odds available — use probability distance from 50% as rough proxy
        return (prob - 50) / 100, 0.0

    # Priority rule: combined bets when both legs are strong
    if dc_1x >= COMBO_THRESHOLD and over_15_prob >= COMBO_THRESHOLD:
        combo_prob = round(poisson_probs.get("proba_dc1x_over15", dc_1x))
        edge, _ = _compute_edge_ev(combo_prob, None)
        result["recommended_bet"] = "1X + Plus de 1.5 buts"
        result["kelly_edge"] = round(edge, 3)
        result["kelly_fraction"] = 0
        result["value_bet"] = True
    elif dc_x2 >= COMBO_THRESHOLD and over_15_prob >= COMBO_THRESHOLD:
        combo_prob = round(poisson_probs.get("proba_dcx2_over15", dc_x2))
        edge, _ = _compute_edge_ev(combo_prob, None)
        result["recommended_bet"] = "X2 + Plus de 1.5 buts"
        result["kelly_edge"] = round(edge, 3)
        result["kelly_fraction"] = 0
        result["value_bet"] = True
    else:
        MIN_PROBA = 55
        eligible = [(n, p, o) for n, p, o in candidate_bets if p >= MIN_PROBA]
        pool = eligible if eligible else candidate_bets

        # Select best bet by expected value when odds available, else by probability
        best_name, best_prob, best_odds = max(
            pool,
            key=lambda x: _compute_edge_ev(x[1], x[2])[0] if x[2] else x[1],
        )

        # FIX: kelly_edge now uses actual ROI vs bookmaker odds (not prob - 50)
        edge, _ = _compute_edge_ev(best_prob, best_odds)
        result["recommended_bet"] = best_name
        result["kelly_edge"] = round(edge, 3)

        # FIX: value_bet compares against implied probability, not absolute threshold
        # A bet is a value bet only when our probability exceeds the market's implied probability
        if best_odds and best_odds > 1:
            implied_prob = 100.0 / best_odds
            result["value_bet"] = best_prob > implied_prob and edge >= MIN_VALUE_EDGE
        elif market:
            # For markets without direct odds, compare against market implied probs
            market_implied = {
                "Victoire Domicile": market["market_home"],
                "Match Nul": market["market_draw"],
                "Victoire Extérieur": market["market_away"],
            }
            implied = market_implied.get(best_name)
            if implied:
                result["value_bet"] = (best_prob - implied) / 100 >= MIN_VALUE_EDGE
            else:
                result["value_bet"] = best_prob >= 65
        else:
            # No market data — fall back to absolute probability threshold
            result["value_bet"] = best_prob >= 65

        result["kelly_fraction"] = 0

    # Score de confiance redesigné (1–10)
    # Combine : (a) accord inter-modèles, (b) qualité données, (c) spread 1X2
    sorted_probs = sorted([final_home, final_draw, final_away], reverse=True)
    spread = sorted_probs[0] - sorted_probs[1]

    # 1. Accord inter-modèles (0–4 pts)
    if context.get("ml_active") and context.get("ml_predictions"):
        ml_preds_ctx = context["ml_predictions"]
        ml_home_val = ml_preds_ctx.get("ml_home", final_home)
        spread_poisson_ml = abs(poisson_probs["proba_home"] - ml_home_val)
        if spread_poisson_ml < 5:
            agreement_pts = 4
        elif spread_poisson_ml < 10:
            agreement_pts = 3
        elif spread_poisson_ml < 15:
            agreement_pts = 2
        else:
            agreement_pts = 1
    else:
        agreement_pts = 2  # Default when ML unavailable

    # 2. Qualité des données (0–4 pts)
    data_quality = 0
    if market:
        data_quality += 1
    if h2h_data and h2h_data.get("total_matches", 0) >= 3:
        data_quality += 1
    if league_data:
        data_quality += 1
    if context.get("ml_calibrated"):
        data_quality += 1

    # 3. Spread 1X2 (0–2 pts) — use int() for clean thresholds
    spread_pts = min(2, int(spread // 10))

    confidence = max(1, min(10, agreement_pts + data_quality + spread_pts))
    result["confidence_score"] = confidence

    return result
