from typing import List, Optional
from pydantic import BaseModel

class BrainPlayer(BaseModel):
    id: str
    name: Optional[str] = ""
    gpg: float
    spg: float
    apg: Optional[float] = 0.0
    opp_gaa: float = 3.0
    is_home: Optional[bool] = False
    opp_shots_allowed_avg: Optional[float] = 30.0
    shooting_pct: Optional[float] = None
    toi_avg: Optional[float] = None
    pp_toi_avg: Optional[float] = None
    team_pp_pct: Optional[float] = None
    is_back_to_back: Optional[bool] = False
    days_rest: Optional[int] = 2
    gpg_l5: Optional[float] = None
    spg_l5: Optional[float] = None


class BrainRequest(BaseModel):
    players: List[BrainPlayer]
    apply_calibration: bool = True


class BrainPrediction(BaseModel):
    id: str
    math_prob_goal: float
    math_exp_shots: float
    prob_point: Optional[float] = 0.0
    prob_assist: Optional[float] = 0.0
    confidence: Optional[str] = "medium"


class BrainResponse(BaseModel):
    predictions: List[BrainPrediction]


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
    player_name: Optional[str] = ""
    team: str
    opp: str
    algo_score_goal: int
    algo_score_shot: int
    is_home: int
    python_prob: float
    python_vol: float
    result_goal: Optional[str] = ""
    result_shot: Optional[str] = ""


class IngestDataLakeRequest(BaseModel):
    rows: List[DataLakeRow]


class SuiviAlgoRow(BaseModel):
    date: str
    match: str
    type: str
    joueur: str
    pari: str
    cote: float
    resultat: str
    score_reel: Optional[str] = ""
    diagnostic_ia: Optional[str] = ""
    analyse_postmortem: Optional[str] = ""
    id_ref: Optional[str] = ""


class IngestSuiviAlgoRequest(BaseModel):
    rows: List[SuiviAlgoRow]


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
    market_stats: List[MarketStat] = []
    trigger_retrain: bool = True  # Déclencher le réentraînement ML


class UpdateDataLakeResultRow(BaseModel):
    date: str
    player_id: str
    result_goal: str = ""
    result_shot: str = ""


class UpdateDataLakeResultsRequest(BaseModel):
    rows: List[UpdateDataLakeResultRow]
