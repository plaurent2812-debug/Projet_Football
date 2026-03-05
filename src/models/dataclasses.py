"""
dataclasses.py — Structures de données typées pour le projet Football IA.

Remplace les dicts anonymes par des objets structurés avec validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════
#  PRÉDICTION DE MATCH
# ═══════════════════════════════════════════════════════════════════


@dataclass
class MatchPrediction:
    """Résultat complet d'une prédiction pour un match."""

    # Probabilités 1X2
    proba_home: int
    proba_draw: int
    proba_away: int

    # Marchés
    proba_btts: int
    proba_over_05: int
    proba_over_15: int
    proba_over_25: int
    proba_over_35: int
    proba_penalty: int

    # Double chance
    proba_dc_1x: int
    proba_dc_x2: int
    proba_dc_12: int

    # Expected goals
    xg_home: float
    xg_away: float

    # Score exact
    correct_score: str
    proba_correct_score: int

    # Recommandation
    recommended_bet: str
    confidence_score: int  # 1-10
    analysis_text: str

    # Buteur probable
    likely_scorer: str | None = None
    likely_scorer_proba: int = 0

    # Métadonnées
    model_version: str = "hybrid_v1"
    context: dict = field(default_factory=dict)
    stats_json: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════
#  IMPACT BLESSURE D'UN JOUEUR
# ═══════════════════════════════════════════════════════════════════


@dataclass
class PlayerInjuryImpact:
    """Impact d'une absence individuelle sur la force de l'équipe."""

    player_name: str
    position: str  # "Goalkeeper", "Defender", "Midfielder", "Attacker"
    reason: str  # Raison de l'absence
    impact: str  # "CRITIQUE", "majeur", "significatif", "modéré", "mineur", "minimal"

    impact_attack: float = 0.0  # Réduction du xG offensif
    impact_defense: float = 0.0  # Augmentation du xG concédé

    goals: int = 0
    assists: int = 0
    rating: float = 6.0
    minutes: int = 0
    is_starter: bool = False


# ═══════════════════════════════════════════════════════════════════
#  PRÉDICTION DE BUTEUR
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ScorerPrediction:
    """Prédiction de probabilité de but pour un joueur."""

    player_id: int
    name: str
    team: str
    position: str  # "Attacker", "Midfielder", "Defender"

    proba: int  # Probabilité de marquer (%)
    player_xg: float  # xG individuel pour ce match
    raw_score: float  # Score brut de classement

    goals_per_90: float  # Rendement saison
    total_goals: int  # Buts cette saison
    total_assists: int  # Passes décisives

    # Contexte
    penalty_taker: bool = False
    synergy: str | None = None  # Nom du meilleur passeur
    goals_vs: int = 0  # Buts contre cet adversaire
    matches_vs: int = 0  # Matchs contre cet adversaire
    form_goals: int = 0  # Buts récents
    form_matches: int = 0  # Matchs récents joués
    form_factor: float = 1.0  # Facteur de forme
    defense_factor: float = 1.0  # Perméabilité défense adverse
    gk_factor: float = 1.0  # Qualité gardien adverse
    conversion_rate: float = 0.0  # Taux de conversion tirs → buts

    analysis: str = ""


# ═══════════════════════════════════════════════════════════════════
#  CONTEXTE ELO
# ═══════════════════════════════════════════════════════════════════


@dataclass
class EloRating:
    """Couple ELO d'un match."""

    home_elo: float
    away_elo: float
    home_proba: int
    draw_proba: int
    away_proba: int


# ═══════════════════════════════════════════════════════════════════
#  FORCE D'ÉQUIPE (LIGUE)
# ═══════════════════════════════════════════════════════════════════


@dataclass
class TeamStrength:
    """Forces offensives et défensives d'une équipe (domicile/extérieur)."""

    home_attack: float
    home_defense: float
    away_attack: float
    away_defense: float


# ═══════════════════════════════════════════════════════════════════
#  IMPACT ARBITRE
# ═══════════════════════════════════════════════════════════════════


@dataclass
class RefereeImpact:
    """Tendances statistiques d'un arbitre."""

    avg_yellows: float
    avg_reds: float
    avg_penalties: float
    avg_fouls: float
    penalty_bias: float  # > 1.0 = généreux, < 1.0 = sévère
    matches: int


# ═══════════════════════════════════════════════════════════════════
#  RÉSULTAT D'ÉVALUATION
# ═══════════════════════════════════════════════════════════════════


@dataclass
class EvaluationResult:
    """Résultat de l'évaluation d'une prédiction vs résultat réel."""

    fixture_id: int
    result_correct: bool
    btts_correct: bool
    over25_correct: bool
    correct_score_hit: bool
    scorer_correct: bool
    penalty_correct: bool
    recommended_bet_won: bool

    brier_1x2: float = 0.0
    log_loss: float = 0.0
    post_analysis: str = ""
