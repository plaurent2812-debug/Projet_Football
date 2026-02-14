"""
constants.py — Toutes les constantes du projet Football IA.

Centralise les valeurs magiques pour éviter la duplication
et faciliter le tuning des hyperparamètres.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════
#  POISSON / DIXON-COLES
# ═══════════════════════════════════════════════════════════════════

MAX_GOALS_GRID: int = 7
DIXON_COLES_RHO: float = -0.13  # Corrélation Dixon-Coles (typiquement -0.03 à -0.20)


# ═══════════════════════════════════════════════════════════════════
#  ELO
# ═══════════════════════════════════════════════════════════════════

K_FACTOR: int = 32
HOME_ELO_ADVANTAGE: int = 65
DEFAULT_ELO: int = 1500
ELO_DECAY_RATE: float = 0.001  # Decay ELO temporel (régression vers 1500)


# ═══════════════════════════════════════════════════════════════════
#  FORME RÉCENTE
# ═══════════════════════════════════════════════════════════════════

FORM_DECAY: float = 0.82
FORM_LOOKBACK: int = 6
FORM_RANGE_LOW: float = 0.85  # Score plancher (0.85 + 0 * 0.30)
FORM_RANGE_HIGH: float = 0.30  # Amplitude (0.85 + 1.0 * 0.30 = 1.15)


# ═══════════════════════════════════════════════════════════════════
#  REPOS & CONGESTION
# ═══════════════════════════════════════════════════════════════════

REST_FATIGUE_DAYS: int = 3  # < 3 jours → fatigue
REST_SLIGHT_DAYS: int = 5  # 3-4 jours → léger désavantage
REST_OPTIMAL_DAYS: int = 7  # > 7 jours → repos optimal
REST_FATIGUE_FACTOR: float = 0.92
REST_SLIGHT_FACTOR: float = 0.97
REST_OPTIMAL_FACTOR: float = 1.02
CONGESTION_HIGH: int = 8  # matchs / 30 jours
CONGESTION_MEDIUM: int = 6
CONGESTION_HIGH_FACTOR: float = 0.96
CONGESTION_MEDIUM_FACTOR: float = 0.98


# ═══════════════════════════════════════════════════════════════════
#  ENJEU / STAKES
# ═══════════════════════════════════════════════════════════════════

STAKES_TITLE_FACTOR: float = 1.08
STAKES_CL_FACTOR: float = 1.05
STAKES_RELEGATION_FACTOR: float = 1.06
STAKES_MIDTABLE_FACTOR: float = 0.97
STAKES_TITLE_THRESHOLD: int = 3  # points du leader
STAKES_CL_THRESHOLD: int = 3  # points de la 4ème place
STAKES_RELEGATION_THRESHOLD: int = 3  # points de la zone rouge

# Boost draw pour derbys/matchs à enjeu (les matchs serrés produisent
# plus de nuls et PAS plus de buts — Anderson & Sally, Buraimo et al.)
STAKES_DRAW_BOOST: float = 0.03  # +3% draw quand les deux équipes ont un enjeu élevé


# ═══════════════════════════════════════════════════════════════════
#  AVANTAGE DOMICILE
# ═══════════════════════════════════════════════════════════════════

HOME_XG_BONUS: float = 1.12


# ═══════════════════════════════════════════════════════════════════
#  MÉTÉO
# ═══════════════════════════════════════════════════════════════════

HEAVY_RAIN_MM: float = 5
MODERATE_RAIN_MM: float = 2
HEAVY_RAIN_FACTOR: float = 0.93
MODERATE_RAIN_FACTOR: float = 0.97
STRONG_WIND_KMH: float = 10
MODERATE_WIND_KMH: float = 6
STRONG_WIND_FACTOR: float = 0.95
MODERATE_WIND_FACTOR: float = 0.98
EXTREME_COLD_C: float = 2
EXTREME_HEAT_C: float = 35
EXTREME_TEMP_FACTOR: float = 0.97


# ═══════════════════════════════════════════════════════════════════
#  BLESSURES
# ═══════════════════════════════════════════════════════════════════

INJURY_MIN_MINUTES: int = 90
INJURY_STARTER_SHARE: float = 0.03  # > 3% du temps total
INJURY_ATTACK_FLOOR: float = 0.70
INJURY_DEFENSE_CEIL: float = 1.35

# Seuils d'impact attaquant (part des buts de l'équipe)
ATK_CRITICAL_SHARE: float = 0.30
ATK_MAJOR_SHARE: float = 0.20
ATK_SIGNIFICANT_SHARE: float = 0.10

# Seuils d'impact milieu (passes clés / 90)
MID_CREATOR_KP90: float = 2.0
MID_SIGNIFICANT_KP90: float = 1.0
MID_CREATOR_ASSIST_SHARE: float = 0.25
MID_SIGNIFICANT_ASSIST_SHARE: float = 0.15


# ═══════════════════════════════════════════════════════════════════
#  PENALTY
# ═══════════════════════════════════════════════════════════════════

BASE_PENALTY_RATE: float = 0.30
AVG_DEFENDER_FOULS_PER_90: float = 1.2
AVG_ATTACKER_FOULS_DRAWN_PER_90: float = 1.5
PENALTY_PROBA_MIN: int = 5
PENALTY_PROBA_MAX: int = 65


# ═══════════════════════════════════════════════════════════════════
#  H2H
# ═══════════════════════════════════════════════════════════════════

H2H_MAX_ADJUSTMENT: float = 0.08  # ±8% max
H2H_SENSITIVITY: float = 0.15  # coefficient de conversion winrate → factor


# ═══════════════════════════════════════════════════════════════════
#  PONDÉRATIONS — COMBINAISON FINALE
# ═══════════════════════════════════════════════════════════════════

# Poisson + ELO + Marché
WEIGHT_POISSON: float = 0.55
WEIGHT_ELO: float = 0.25
WEIGHT_MARKET: float = 0.20

# Poisson + ELO (sans marché)
WEIGHT_POISSON_NO_MARKET: float = 0.65
WEIGHT_ELO_NO_MARKET: float = 0.35

# Stats vs IA (brain.py)
WEIGHT_STATS: float = 0.70
WEIGHT_AI: float = 0.30

# Stats vs ML XGBoost
WEIGHT_STATS_VS_ML: float = 0.60
WEIGHT_ML: float = 0.40


# ═══════════════════════════════════════════════════════════════════
#  NUL — ESTIMATION
# ═══════════════════════════════════════════════════════════════════

DRAW_FACTOR: float = 0.26  # ~26% de nuls en moyenne en football (fallback global)
ELO_DRAW_DECAY_RATE: float = 0.002  # Decay du draw factor en fonction de l'écart ELO

# Draw factor calibré par ligue (taux de nuls observé historiquement)
DRAW_FACTOR_BY_LEAGUE: dict[int, float] = {
    61: 0.24,   # Ligue 1
    62: 0.25,   # Ligue 2
    39: 0.23,   # Premier League
    140: 0.26,  # La Liga
    135: 0.27,  # Serie A
    78: 0.22,   # Bundesliga
    2: 0.22,    # Champions League
    3: 0.24,    # Europa League
}


# ═══════════════════════════════════════════════════════════════════
#  XG LIMITES
# ═══════════════════════════════════════════════════════════════════

XG_FLOOR: float = 0.3
XG_CEIL: float = 4.0
XG_FALLBACK_HOME: float = 1.3
XG_FALLBACK_AWAY: float = 1.1


# ═══════════════════════════════════════════════════════════════════
#  CALIBRATION
# ═══════════════════════════════════════════════════════════════════

MIN_CALIBRATION_SAMPLES: int = 20


# ═══════════════════════════════════════════════════════════════════
#  KELLY CRITERION / VALUE BETTING
# ═══════════════════════════════════════════════════════════════════

KELLY_FRACTION: float = 0.25  # Quart-Kelly (conservateur)
KELLY_MAX_BET_FRACTION: float = 0.05  # Max 5% du bankroll par pari
MIN_VALUE_EDGE: float = 0.05  # Edge minimum pour considérer un value bet (5%)


# ═══════════════════════════════════════════════════════════════════
#  SCORER ENGINE — PONDÉRATIONS
# ═══════════════════════════════════════════════════════════════════

W_GOALS_PER_90: float = 0.25
W_FORM: float = 0.20
W_DEFENSE_OPP: float = 0.15
W_GK_OPP: float = 0.10
W_SYNERGY: float = 0.10
W_VS_OPPONENT: float = 0.05
W_PENALTY_TAKER: float = 0.10
W_STARTER: float = 0.05

# Anomalie statistique
EXPECTED_CONVERSION_RATE: float = 0.22
MIN_SHOTS_ON_FOR_ANOMALY: int = 10
SHOTS_ON_PER_90_THRESHOLD: float = 1.0
ANOMALY_CONVERSION_BOOST: float = 1.2
ANOMALY_MUTE_BOOST: float = 1.15
MUTE_MIN_MATCHES: int = 3

# Défense adverse
LEAGUE_AVG_GA_PER_MATCH: float = 1.25
DEFENSE_FACTOR_FLOOR: float = 0.6
DEFENSE_FACTOR_CEIL: float = 1.6

# Gardien adverse
GK_AVG_CONCEDED_PER_90: float = 1.1
GK_AVG_SAVE_RATE: float = 0.70
GK_FACTOR_FLOOR: float = 0.7
GK_FACTOR_CEIL: float = 1.4


# ═══════════════════════════════════════════════════════════════════
#  FEATURE COLUMNS — ML (source unique)
# ═══════════════════════════════════════════════════════════════════

FEATURE_COLS: list[str] = [
    "home_attack_strength",
    "home_defense_strength",
    "away_attack_strength",
    "away_defense_strength",
    "home_elo",
    "away_elo",
    "elo_diff",
    "home_form",
    "away_form",
    "home_rest_days",
    "away_rest_days",
    "home_congestion_30d",
    "away_congestion_30d",
    "home_stakes",
    "away_stakes",
    "h2h_home_winrate",
    "h2h_total_matches",
    "home_injury_count",
    "away_injury_count",
    "home_injury_attack_factor",
    "home_injury_defense_factor",
    "away_injury_attack_factor",
    "away_injury_defense_factor",
    "referee_penalty_bias",
    "market_home_prob",
    "market_draw_prob",
    "market_away_prob",
    "xg_home",
    "xg_away",
    "league_avg_home_goals",
    "league_avg_away_goals",
    # ── Features avancées Phase 5 ──
    "home_momentum",
    "away_momentum",
    "home_fatigue_index",
    "away_fatigue_index",
    "home_goal_diff_avg",
    "away_goal_diff_avg",
    "home_result_variance",
    "away_result_variance",
    "home_clean_sheet_rate",
    "away_clean_sheet_rate",
    # ── Features Phase A2 — High-value additions ──
    "home_ppg_last5",
    "away_ppg_last5",
    "home_btts_rate_last10",
    "away_btts_rate_last10",
    "home_over25_rate_last10",
    "away_over25_rate_last10",
    "home_xg_per_shot",
    "away_xg_per_shot",
    "league_avg_btts_rate",
    "league_avg_over25_rate",
    "elo_diff_squared",
    "form_diff",
]
