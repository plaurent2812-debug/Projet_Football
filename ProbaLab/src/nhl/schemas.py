from pydantic import BaseModel


class BrainPlayer(BaseModel):
    id: str
    name: str | None = ""
    gpg: float
    spg: float
    apg: float | None = 0.0
    opp_gaa: float = 3.0
    is_home: bool | None = False
    opp_shots_allowed_avg: float | None = 30.0
    shooting_pct: float | None = None
    toi_avg: float | None = None
    pp_toi_avg: float | None = None
    team_pp_pct: float | None = None
    is_back_to_back: bool | None = False
    days_rest: int | None = 2
    gpg_l5: float | None = None
    spg_l5: float | None = None


class BrainRequest(BaseModel):
    players: list[BrainPlayer]
    apply_calibration: bool = True


class BrainPrediction(BaseModel):
    id: str
    math_prob_goal: float
    math_exp_shots: float
    prob_point: float | None = 0.0
    prob_assist: float | None = 0.0
    confidence: str | None = "medium"


class BrainResponse(BaseModel):
    predictions: list[BrainPrediction]
    ml_fallback_used: dict[str, bool] = {
        "shot": False,
        "assist": False,
        "goal": False,
        "point": False,
    }


class GameWinProbRequest(BaseModel):
    home_team: str
    away_team: str
    home_gaa: float
    away_gaa: float
    home_l10: float
    away_l10: float
    home_pts_per_game: float
    away_pts_per_game: float
    home_ai_factor: float = 1.0
    away_ai_factor: float = 1.0
    home_is_tired: bool = False
    away_is_tired: bool = False


class CalibrateProbaRequest(BaseModel):
    market: str
    raw_prob: float


class DataLakeRow(BaseModel):
    date: str
    player_id: str
    player_name: str | None = ""
    team: str
    opp: str
    algo_score_goal: int
    algo_score_shot: int
    is_home: int
    python_prob: float
    python_vol: float
    result_goal: str | None = ""
    result_shot: str | None = ""


class IngestDataLakeRequest(BaseModel):
    rows: list[DataLakeRow]


class SuiviAlgoRow(BaseModel):
    date: str
    match: str
    type: str
    joueur: str
    pari: str
    cote: float
    resultat: str
    score_reel: str | None = ""
    diagnostic_ia: str | None = ""
    analyse_postmortem: str | None = ""
    id_ref: str | None = ""


class IngestSuiviAlgoRequest(BaseModel):
    rows: list[SuiviAlgoRow]


class MarketStat(BaseModel):
    market: str
    total: int
    wins: int
    accuracy: float


class DailyAnalysisRequest(BaseModel):
    """Payload envoyé par Google Apps Script après Vérifier & Analyser."""

    date: str  # ISO format YYYY-MM-DD
    total_bets: int
    wins: int
    losses: int
    accuracy: float
    market_stats: list[MarketStat] = []
    trigger_retrain: bool = True  # Déclencher le réentraînement ML


class UpdateDataLakeResultRow(BaseModel):
    date: str
    player_id: str
    result_goal: str = ""
    result_shot: str = ""


class UpdateDataLakeResultsRequest(BaseModel):
    rows: list[UpdateDataLakeResultRow]
