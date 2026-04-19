"""
constants.py — Toutes les constantes du projet Football IA.

Centralise les valeurs magiques pour éviter la duplication
et faciliter le tuning des hyperparamètres.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════
#  POISSON / DIXON-COLES
# ═══════════════════════════════════════════════════════════════════

MAX_GOALS_GRID: int = 10
DIXON_COLES_RHO: float = -0.13  # Corrélation Dixon-Coles globale (fallback)

# Rho per-ligue : calibré empiriquement selon le style de jeu et le taux de nuls.
# Plus négatif = correction plus forte sur les scores à faible buts (0-0, 1-1...).
# Méthode : ajuster jusqu'à ce que la proba de nul Poisson ≃ taux historique.
DIXON_COLES_RHO_BY_LEAGUE: dict[int, float] = {
    61: -0.14,  # Ligue 1 — défensif, taux de nuls élevé
    62: -0.13,  # Ligue 2 — similaire à Ligue 1
    39: -0.11,  # Premier League — jeu ouvert, peu de 0-0
    140: -0.12,  # La Liga — équilibré
    135: -0.16,  # Serie A — taux de nuls le plus élevé d'Europe
    78: -0.09,  # Bundesliga — jeu rapide, peu de nuls
    2: -0.17,  # Champions League — très tactique, nuls fréquents
    3: -0.15,  # Europa League — défensif
    848: -0.14,  # Conference League
    66: -0.12,  # Coupe de France
    45: -0.11,  # FA Cup
    143: -0.12,  # Copa del Rey
    137: -0.15,  # Coppa Italia
    81: -0.10,  # DFB-Pokal
}


# ═══════════════════════════════════════════════════════════════════
#  ELO
# ═══════════════════════════════════════════════════════════════════

K_FACTOR: int = 32  # Valeur par défaut (ligue inconnue)
HOME_ELO_ADVANTAGE: int = 65  # Default (fallback)
DEFAULT_ELO: int = 1500

# Per-league home advantage (ELO points).
# Calibrated from historical home win rates:
#   ~60% home wins → +75 ELO, ~55% → +65, ~52% → +50
HOME_ELO_ADVANTAGE_BY_LEAGUE: dict[int, int] = {
    61: 70,  # Ligue 1 — strong home advantage
    62: 70,  # Ligue 2 — strong home advantage
    39: 60,  # Premier League — moderate
    140: 65,  # La Liga — average
    135: 65,  # Serie A — average
    78: 50,  # Bundesliga — weakest in top 5 leagues
    2: 55,  # Champions League — reduced (neutral-ish)
    3: 55,  # Europa League
    848: 55,  # Conference League
    # Coupes nationales (knockout, home advantage réduit)
    45: 55,  # FA Cup — neutral/reduced home advantage
    66: 55,  # Coupe de France
    81: 50,  # DFB-Pokal
    137: 55,  # Coppa Italia
    143: 55,  # Copa del Rey
}
ELO_DECAY_RATE: float = 0.001  # Decay ELO temporel (régression vers 1500)

# K-factor dynamique par ligue : compétitions européennes comptent plus,
# coupes nationales (knockout, small sample) comptent moins.
K_FACTOR_BY_LEAGUE: dict[int, int] = {
    2: 40,  # Champions League — résultats très informatifs
    3: 36,  # Europa League
    848: 34,  # Conference League
    39: 32,  # Premier League
    61: 32,  # Ligue 1
    140: 32,  # La Liga
    135: 32,  # Serie A
    78: 32,  # Bundesliga
    62: 30,  # Ligue 2 (niveau inférieur)
    # Coupes nationales (matchs knockout, signal plus faible)
    66: 24,  # Coupe de France
    45: 24,  # FA Cup
    143: 24,  # Copa del Rey
    137: 24,  # Coppa Italia
    81: 24,  # DFB-Pokal
}


# ═══════════════════════════════════════════════════════════════════
#  FORME RÉCENTE
# ═══════════════════════════════════════════════════════════════════

FORM_DECAY: float = 0.82
FORM_LOOKBACK: int = 6
FORM_RANGE_LOW: float = 0.85  # Score plancher (0.85 + 0 * 0.30)
FORM_RANGE_HIGH: float = 0.30  # Amplitude (0.85 + 1.0 * 0.30 = 1.15)

# Forme long terme : tendance de fond sur 12 matchs (decay plus lent)
FORM_LOOKBACK_LONG: int = 12
FORM_DECAY_LONG: float = 0.90  # Décroissance plus lente → poids plus uniforme sur 12 matchs
# Pondération court/long terme dans le form_factor final
FORM_WEIGHT_SHORT: float = 0.70  # 70% forme 6 matchs
FORM_WEIGHT_LONG: float = 0.30  # 30% tendance 12 matchs


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

# Injury impact is now computed via VORP model (src/models/injury_vorp.py).
# Legacy thresholds removed — the VORP model uses continuous ratings
# with replacement-level baseline (6.5) instead of static thresholds.


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

# Phase 2 meta-learner feature flag.
# Set to True ONLY after retraining the meta-learner with richer features
# (the current model uses only 5 Gemini scores → near-identical probabilities).
# When False, blend_predictions() uses 100% stats regardless of WEIGHT_AI.
META_LEARNER_ENABLED: bool = False

# Stats vs ML XGBoost
WEIGHT_STATS_VS_ML: float = 0.50
WEIGHT_ML: float = 0.50


# ═══════════════════════════════════════════════════════════════════
#  VALUE BET DETECTION (H2-SS1)
# ═══════════════════════════════════════════════════════════════════

USE_MARKET_FEATURES: bool = True  # Active variant baseline; False → pure
MIN_BOOKMAKERS_FOR_VALUE: int = 3  # skip si < 3 bookmakers sur un marché
KELLY_FRACTION: float = 0.25       # Kelly fractional conservateur
VALUE_EDGE_USER_FACING: float = 0.05  # 5% — affichage user
VALUE_EDGE_ADMIN: float = 0.03     # 3% — monitoring interne


# ═══════════════════════════════════════════════════════════════════
#  NUL — ESTIMATION
# ═══════════════════════════════════════════════════════════════════

DRAW_FACTOR: float = 0.28  # ~28% de nuls en moyenne en football (fallback global, was 0.26)
ELO_DRAW_DECAY_RATE: float = 0.002  # Decay du draw factor en fonction de l'écart ELO

# Draw factor calibré par ligue (taux de nuls observé historiquement)
# Recalibré mars 2026 : les valeurs précédentes sous-estimaient les nuls de 3-5%
# (confirmé par backtest: bin 40-50% prédit → 55% réel, pattern = draws manqués)
DRAW_FACTOR_BY_LEAGUE: dict[int, float] = {
    61: 0.27,  # Ligue 1 — ~27% nuls observés (was 0.24)
    62: 0.28,  # Ligue 2 — plus de nuls en L2 (was 0.25)
    39: 0.26,  # Premier League — compétitif (was 0.23)
    140: 0.29,  # La Liga — tactique, beaucoup de nuls (was 0.26)
    135: 0.30,  # Serie A — le plus de nuls d'Europe (was 0.27)
    78: 0.25,  # Bundesliga — jeu ouvert, moins de nuls (was 0.22)
    2: 0.28,  # Champions League — très tactique (was 0.22)
    3: 0.27,  # Europa League — défensif (was 0.24)
    # Coupes nationales (moins de nuls: prolongations/tirs au but)
    66: 0.22,  # Coupe de France (was 0.20)
    45: 0.22,  # FA Cup (was 0.20)
    143: 0.23,  # Copa del Rey (was 0.21)
    137: 0.24,  # Coppa Italia (was 0.22)
    81: 0.21,  # DFB-Pokal (was 0.19)
}


# ═══════════════════════════════════════════════════════════════════
#  XG LIMITES
# ═══════════════════════════════════════════════════════════════════

XG_FLOOR: float = 0.3
XG_CEIL: float = 4.0
XG_FALLBACK_HOME: float = 1.3
XG_FALLBACK_AWAY: float = 1.1

# ═══════════════════════════════════════════════════════════════════
#  COMPÉTITIONS CROSS-LEAGUE
# ═══════════════════════════════════════════════════════════════════

# Leagues where teams come from different domestic leagues
# → need fallback to domestic league strengths
CROSS_LEAGUE_IDS: set[int] = {
    2,  # Champions League
    3,  # Europa League
    66,  # Coupe de France
    45,  # FA Cup
    143,  # Copa del Rey
    137,  # Coppa Italia
    81,  # DFB-Pokal
}

# xG scaling factors by competition type
# CL matches are more tactical/defensive → fewer goals
COMPETITION_XG_FACTOR: dict[int, float] = {
    2: 0.92,  # Champions League — ~8% fewer goals
    3: 0.95,  # Europa League — ~5% fewer goals
    66: 0.97,  # Coupe de France
    45: 0.97,  # FA Cup
    143: 0.97,  # Copa del Rey
    137: 0.97,  # Coppa Italia
    81: 0.97,  # DFB-Pokal
}

# European competition draw boost (higher stakes → more cautious → more draws)
# NOTE: CL (2), EL (3), ECL (848) are in DRAW_FACTOR_BY_LEAGUE,
# so this boost only applies to competitions WITHOUT calibrated draw factors.
EURO_COMP_DRAW_BOOST: dict[int, float] = {
    2: 0.04,  # Champions League: +4% draw probability
    3: 0.03,  # Europa League: +3% draw probability
    848: 0.02,  # Conference League: +2%
}


# ═══════════════════════════════════════════════════════════════════
#  PROBABILITY CLAMPING — prevent extreme/unrealistic values
# ═══════════════════════════════════════════════════════════════════

# 1X2: real bookmaker odds rarely exceed ~70-75% for biggest favorites
# and even the weakest away team gets 5%+ implied probability
PROB_1X2_FLOOR: int = 5
PROB_1X2_CEIL: int = 72

# Markets: BTTS, Over/Under floors and ceilings
PROB_BTTS_FLOOR: int = 18  # Even the most defensive matches have ≥18% BTTS
PROB_BTTS_CEIL: int = 75
PROB_OVER25_FLOOR: int = 15  # O2.5 is never below 15%
PROB_OVER25_CEIL: int = 80


# ═══════════════════════════════════════════════════════════════════
#  CALIBRATION
# ═══════════════════════════════════════════════════════════════════

MIN_CALIBRATION_SAMPLES: int = 100  # Minimum pour Platt scaling fiable
MIN_ISOTONIC_SAMPLES: int = (
    500  # Minimum pour Isotonic regression (évite la "fonction en escalier")
)
BAYESIAN_SHRINKAGE_K: int = 50  # Shrinkage strength for Bayesian 1X2 calibration
# At n=50 samples, trust raw 50%; at n=500, trust raw 91%
# Used when sample count is below MIN_ISOTONIC_SAMPLES

# Base rates for Bayesian 1X2 shrinkage (average across European top leagues)
BASE_RATE_HOME: float = 45.0  # Average home win rate %
BASE_RATE_DRAW: float = 27.0  # Average draw rate %
BASE_RATE_AWAY: float = 28.0  # Average away win rate %


# ═══════════════════════════════════════════════════════════════════
#  KELLY CRITERION / VALUE BETTING
# ═══════════════════════════════════════════════════════════════════
# NOTE: KELLY_FRACTION is defined above in the H2-SS1 block (line ~225).
# Do not redeclare here — the duplicate would silently shadow the first.

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
    "market_home_prob",
    "market_draw_prob",
    "market_away_prob",
    "market_btts_prob",
    "market_over25_prob",
    "market_over15_prob",
    "xg_home",
    "xg_away",
    "home_xg_per_shot",
    "away_xg_per_shot",
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
    "league_avg_btts_rate",
    "league_avg_over25_rate",
    "elo_diff_squared",
    "form_diff",
    # ── Momentum long terme (12 matchs) ──
    "home_form_long",
    "away_form_long",
    "form_long_diff",
]


# ═══════════════════════════════════════════════════════════════════
#  COHERENCE ASSERTIONS — fail fast if constants are misconfigured
# ═══════════════════════════════════════════════════════════════════

assert abs(FORM_WEIGHT_SHORT + FORM_WEIGHT_LONG - 1.0) < 1e-9, (
    f"FORM_WEIGHT_SHORT + FORM_WEIGHT_LONG must equal 1.0, got {FORM_WEIGHT_SHORT + FORM_WEIGHT_LONG}"
)
assert abs(WEIGHT_POISSON + WEIGHT_ELO + WEIGHT_MARKET - 1.0) < 1e-9, (
    f"WEIGHT_POISSON + WEIGHT_ELO + WEIGHT_MARKET must equal 1.0, got {WEIGHT_POISSON + WEIGHT_ELO + WEIGHT_MARKET}"
)
assert abs(WEIGHT_POISSON_NO_MARKET + WEIGHT_ELO_NO_MARKET - 1.0) < 1e-9, (
    "WEIGHT_POISSON_NO_MARKET + WEIGHT_ELO_NO_MARKET must equal 1.0"
)
assert abs(WEIGHT_STATS_VS_ML + WEIGHT_ML - 1.0) < 1e-9, (
    "WEIGHT_STATS_VS_ML + WEIGHT_ML must equal 1.0"
)
assert abs(WEIGHT_STATS + WEIGHT_AI - 1.0) < 1e-9, "WEIGHT_STATS + WEIGHT_AI must equal 1.0"
assert PROB_1X2_FLOOR > 0, "PROB_1X2_FLOOR must be positive"
assert PROB_1X2_CEIL < 100, "PROB_1X2_CEIL must be less than 100"
assert PROB_1X2_FLOOR * 3 <= 100, "3 × PROB_1X2_FLOOR must be ≤ 100 (three outcomes)"
assert XG_FLOOR > 0, "XG_FLOOR must be positive"
assert XG_CEIL > XG_FLOOR, "XG_CEIL must be greater than XG_FLOOR"
assert KELLY_FRACTION > 0 and KELLY_FRACTION <= 1.0, "KELLY_FRACTION must be in (0, 1]"
assert KELLY_MAX_BET_FRACTION > 0 and KELLY_MAX_BET_FRACTION <= 1.0, (
    "KELLY_MAX_BET_FRACTION must be in (0, 1]"
)


# ═══════════════════════════════════════════════════════════════════
#  LEAGUES
# ═══════════════════════════════════════════════════════════════════

# Ligues : 61 = Ligue 1, 62 = Ligue 2, 39 = Premier League, 140 = La Liga,
#          135 = Serie A, 78 = Bundesliga, 2 = Champions League, 3 = Europa League,
#          1 = Coupe du Monde, 4 = Euro
LEAGUES_TO_FETCH: list[int] = [61, 62, 39, 140, 135, 78, 2, 3, 1, 4]


# ═══════════════════════════════════════════════════════════════════
#  API CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Cache TTLs (seconds)
CACHE_TTL_NEWS: int = 3600  # 1 hour — RSS feeds don't change often
CACHE_TTL_LEAGUES: int = 3600  # 1 hour — league metadata is static
CACHE_TTL_MONITORING: int = 300  # 5 min — CLV/Brier are expensive to compute

# Rate limiting
RATE_LIMIT_DEFAULT: str = "60/minute"
RATE_LIMIT_SEARCH: str = "30/minute"
RATE_LIMIT_ADMIN: str = "10/minute"
