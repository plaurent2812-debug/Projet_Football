"""
api/response_models.py — Pydantic response models for all API endpoints.

Provides typed response shapes for OpenAPI docs and runtime validation.
Endpoints with dynamic or deeply-nested payloads use ``extra="allow"``
so that new fields never cause serialisation failures.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

# ─── Shared ──────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Generic error envelope returned on 4xx/5xx."""

    detail: str


class OkResponse(BaseModel):
    """Minimal success acknowledgement."""

    ok: bool


# ─── Health ──────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """GET /health"""

    status: str
    timestamp: str
    checks: dict[str, str] | None = None


# ─── News ────────────────────────────────────────────────────────────────────


class NewsItem(BaseModel):
    """A single item fetched from an RSS feed."""

    title: str
    link: str
    source: str
    pub_date: str = ""


class NewsResponse(BaseModel):
    """GET /api/news"""

    news: list[NewsItem]


# ─── Email ───────────────────────────────────────────────────────────────────


class EmailSentResponse(BaseModel):
    """POST /api/resend/welcome  •  POST /api/resend/premium-confirm"""

    sent: bool


# ─── Search ──────────────────────────────────────────────────────────────────


class SearchPredictionItem(BaseModel):
    """One prediction result returned by semantic search."""

    model_config = ConfigDict(extra="allow")

    fixture_id: int | None = None
    home_team: str = "?"
    away_team: str = "?"
    date: str | None = None
    league: str = ""
    analysis_text: str = ""
    proba_home: float | None = None
    proba_draw: float | None = None
    proba_away: float | None = None
    similarity: float = 0.0


class SearchLearningItem(BaseModel):
    """One learning result returned by semantic search."""

    model_config = ConfigDict(extra="allow")

    learning_text: str | None = None
    tags: Any | None = None
    similarity: float = 0.0


class SemanticSearchResponse(BaseModel):
    """GET /api/search/semantic"""

    model_config = ConfigDict(extra="allow")

    query: str
    predictions: list[SearchPredictionItem] = []
    learnings: list[SearchLearningItem] = []


# ─── Expert Picks ────────────────────────────────────────────────────────────


class EnrichedSelection(BaseModel):
    """One selection inside an expert pick (single or combiné leg)."""

    model_config = ConfigDict(extra="allow")

    match: str = ""
    market: str = ""
    player_name: str | None = None
    bet_raw: str = ""
    is_mymatch: bool = False


class ExpertPickItem(BaseModel):
    """A single expert pick row, enriched for the frontend."""

    model_config = ConfigDict(extra="allow")

    id: int
    date: str
    sport: str
    player_name: str | None = None
    market: str | None = None
    match_label: str | None = None
    odds: float | None = None
    confidence: int | None = None
    expert_note: str | None = None
    result: str | None = None
    created_at: str | None = None
    # Enriched fields added at runtime
    selections: list[EnrichedSelection] = []
    is_combine: bool = False
    bet_type: str = "EXPERT"
    has_mymatch: bool = False


class ExpertPicksResponse(BaseModel):
    """GET /api/expert-picks"""

    model_config = ConfigDict(extra="allow")

    date: str
    picks: list[ExpertPickItem]


class LatestExpertPickResponse(BaseModel):
    """GET /api/expert-picks/latest"""

    model_config = ConfigDict(extra="allow")

    pick: dict[str, Any] | None = None


class DeleteExpertPickResponse(BaseModel):
    """DELETE /api/expert-picks/{pick_id}"""

    deleted: bool
    id: int


class BackfillExpertPicksResponse(BaseModel):
    """POST /api/expert-picks/backfill"""

    inserted: int
    errors: list[dict[str, Any]] = []
    ids: list[dict[str, Any]] = []


class ResolvedPickDetail(BaseModel):
    """One resolved pick entry inside the resolve response."""

    model_config = ConfigDict(extra="allow")

    id: int
    market: str
    match: str
    result: str
    note: str


class ResolveExpertPicksResponse(BaseModel):
    """POST /api/expert-picks/resolve"""

    ok: bool
    date: str
    resolved_count: int = 0
    resolved: list[ResolvedPickDetail] = []
    errors: list[dict[str, Any]] = []
    message: str | None = None


# ─── Admin ───────────────────────────────────────────────────────────────────


class PipelineStartResponse(BaseModel):
    """POST /api/admin/run-pipeline  •  POST /api/cron/run-pipeline"""

    model_config = ConfigDict(extra="allow")

    ok: bool | None = None
    message: str | None = None
    started_at: str | None = None
    status: str | None = None


class PipelineStatusResponse(BaseModel):
    """GET /api/admin/pipeline-status"""

    model_config = ConfigDict(extra="allow")

    status: str
    mode: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    logs: str = ""
    return_code: int | None = None


class PipelineStopResponse(BaseModel):
    """POST /api/admin/stop-pipeline"""

    message: str


class UpdateScoresResponse(BaseModel):
    """POST /api/admin/update-scores"""

    message: str


# ─── Best Bets ───────────────────────────────────────────────────────────────


class BetCandidate(BaseModel):
    """A single bet candidate (football or NHL)."""

    model_config = ConfigDict(extra="allow")

    fixture_id: Any | None = None
    label: str = ""
    match: str = ""
    market: str = ""
    odds: float = 1.0
    proba_model: float = 0.0
    confidence: float = 0.0
    ev: float = 0.0
    is_value: bool = False
    odds_source: str = "estimated"
    result: str = "PENDING"
    time: str = ""
    id: int | None = None


class SafeBetWrapper(BaseModel):
    """The ``football_safe`` / ``nhl_safe`` envelope."""

    model_config = ConfigDict(extra="allow")

    type: str = "SAFE"
    bet: dict[str, Any]
    odds: float


class FunBetWrapper(BaseModel):
    """The ``football_fun`` / ``nhl_fun`` envelope."""

    model_config = ConfigDict(extra="allow")

    type: str = "FUN"
    bets: list[dict[str, Any]]
    total_odds: float
    count: int


class BestBetsResponse(BaseModel):
    """GET /api/best-bets"""

    model_config = ConfigDict(extra="allow")

    date: str
    football: list[dict[str, Any]] = []
    nhl: list[dict[str, Any]] = []
    football_safe: SafeBetWrapper | None = None
    football_fun: FunBetWrapper | None = None
    nhl_safe: SafeBetWrapper | None = None
    nhl_fun: FunBetWrapper | None = None


class SaveBetResponse(BaseModel):
    """POST /api/best-bets/save"""

    ok: bool
    id: int | None = None


class UpdateBetResultResponse(BaseModel):
    """PATCH /api/best-bets/{bet_id}/result"""

    model_config = ConfigDict(extra="allow")

    ok: bool
    updated: list[dict[str, Any]] | None = None


# ─── Monitoring ──────────────────────────────────────────────────────────────


class CLVMetrics(BaseModel):
    """Closing Line Value metrics block."""

    model_config = ConfigDict(extra="allow")

    clv_best_mean: float = 0.0
    clv_when_correct: float = 0.0
    pct_positive_clv: float = 0.0
    n_matches: int = 0
    verdict: str = "NO_DATA"
    by_league: dict[str, Any] = {}
    daily_clv: list[Any] = []
    status: str = "NO_DATA"


class BrierMetrics(BaseModel):
    """Brier score and calibration metrics block."""

    model_config = ConfigDict(extra="allow")

    brier_1x2: float | None = None
    brier_1x2_grade: str | None = None
    ece: float | None = None
    ece_grade: str | None = None
    log_loss: float | None = None
    btts: float | None = None
    over15: float | None = None
    over25: float | None = None
    n_matches: int = 0
    drift: dict[str, Any] = {}


class MonitoringResponse(BaseModel):
    """GET /api/monitoring"""

    model_config = ConfigDict(extra="allow")

    clv: CLVMetrics
    brier: BrierMetrics
    health_score: float = 5.0


class MonitoringHealthResponse(BaseModel):
    """GET /api/monitoring/health"""

    model_config = ConfigDict(extra="allow")

    healthy: bool
    predictions_today: int = 0
    last_prediction_at: str | None = None
    yesterday_coverage_pct: float | None = None
    yesterday_fixtures: int = 0
    yesterday_predictions: int = 0
    evaluated_results_total: int = 0
    checked_at: str


# ─── Performance ─────────────────────────────────────────────────────────────


class DailyStatItem(BaseModel):
    """One day's accuracy bucket inside the performance response."""

    date: str
    total: int
    correct: int


class CoverageStats(BaseModel):
    """Market coverage counts."""

    total_1x2_countable: int = 0
    total_btts: int = 0
    total_over_05: int = 0
    total_over_15: int = 0
    total_over_25: int = 0
    total_over_35: int = 0
    total_score: int = 0


class BenchmarkEntry(BaseModel):
    """Single benchmark entry."""

    model_config = ConfigDict(extra="allow")

    accuracy: float = 0.0
    total: int = 0


class PerformanceBenchmarks(BaseModel):
    """Benchmarks section of the performance response."""

    model_config = ConfigDict(extra="allow")

    always_home: BenchmarkEntry
    bookmaker_implied: BenchmarkEntry
    model: BenchmarkEntry


class PerformanceResponse(BaseModel):
    """GET /api/performance"""

    model_config = ConfigDict(extra="allow")

    days: int
    total_matches: int
    accuracy_1x2: float
    accuracy_btts: float
    accuracy_over_05: float = 0.0
    accuracy_over_15: float = 0.0
    accuracy_over_25: float = 0.0
    accuracy_over_35: float = 0.0
    accuracy_score: float = 0.0
    avg_confidence: float
    value_bets: int
    brier_score_1x2: float = 0.0
    brier_score_1x2_normalized: float = 0.0
    daily_stats: list[DailyStatItem] = []
    total_finished: int = 0
    total_without_prediction: int = 0
    skipped_null_probas: int = 0
    skipped_ties: int = 0
    coverage: CoverageStats = CoverageStats()
    benchmarks: PerformanceBenchmarks | None = None


# ─── Predictions ─────────────────────────────────────────────────────────────


class PredictionBlock(BaseModel):
    """The nested ``prediction`` object inside a match item."""

    model_config = ConfigDict(extra="allow")

    proba_home: float | None = None
    proba_draw: float | None = None
    proba_away: float | None = None
    proba_btts: float | None = None
    proba_over_2_5: float | None = None
    recommended_bet: str | None = None
    confidence_score: float | None = None
    kelly_edge: float | None = None
    value_bet: bool | None = None
    model_version: str | None = None
    correct_score: str | None = None
    analysis_text: str | None = None
    proba_penalty: float | None = None
    proba_over_05: float | None = None
    proba_over_15: float | None = None
    proba_over_35: float | None = None


class BestValueBlock(BaseModel):
    """The ``best_value`` object — highest positive-EV market for a fixture."""

    market: str
    edge: float
    odds: float | None = None


class MatchItem(BaseModel):
    """One enriched fixture + prediction row returned by GET /api/predictions."""

    model_config = ConfigDict(extra="allow")

    id: Any  # UUID string from Supabase
    home_team: str = "?"
    away_team: str = "?"
    home_logo: str | None = None
    away_logo: str | None = None
    date: str | None = None
    status: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    events_json: list[Any] = []
    elapsed: int | None = None
    live_stats_json: dict[str, Any] = {}
    league_id: int | None = None
    league_name: str = "Ligue"
    prediction: PredictionBlock | None = None
    odds: dict[str, Any] | None = None
    value_edges: dict[str, Any] = {}
    best_value: BestValueBlock | None = None
    is_value_bet: bool = False


class PredictionsListResponse(BaseModel):
    """GET /api/predictions"""

    date: str
    matches: list[MatchItem]


class TopScorerItem(BaseModel):
    """One top-scorer entry in the prediction detail view."""

    model_config = ConfigDict(extra="allow")

    name: str = "Unknown"
    photo: str | None = None
    goals: int = 0
    apps: int = 0


class PredictionDetailResponse(BaseModel):
    """GET /api/predictions/{fixture_id}"""

    model_config = ConfigDict(extra="allow")

    fixture: dict[str, Any] | None = None
    prediction: dict[str, Any] | None = None
    home_scorers: list[TopScorerItem] = []
    away_scorers: list[TopScorerItem] = []
    match_stats: list[dict[str, Any]] = []
    odds: dict[str, Any] | None = None
    value_edges: dict[str, Any] = {}


# ─── Teams ───────────────────────────────────────────────────────────────────


class TeamMatchResult(BaseModel):
    """One historical match from a team's perspective."""

    model_config = ConfigDict(extra="allow")

    fixture_id: Any | None = None
    date: str = ""
    opponent: str = ""
    score: str = ""
    result: str = ""
    home_away: str = ""
    league_id: int | None = None


class TeamSummary(BaseModel):
    """Win/draw/loss summary for a team history response."""

    model_config = ConfigDict(extra="allow")

    wins: int = 0
    draws: int = 0
    losses: int = 0
    total: int = 0
    streak: dict[str, Any] = {}


class TeamHistoryResponse(BaseModel):
    """GET /api/team/{team_name}/history"""

    team_name: str
    matches: list[TeamMatchResult]
    summary: TeamSummary


class RosterPlayerItem(BaseModel):
    """One player entry from the API-Football squads endpoint."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    name: str | None = None
    age: int | None = None
    number: int | None = None
    position: str | None = None
    photo: str | None = None
    # Enriched stats
    appearances: int | None = None
    goals: int | None = None
    assists: int | None = None
    goals_conceded: int | None = None


class TeamRosterResponse(BaseModel):
    """GET /api/team/{team_name}/roster"""

    team_name: str
    roster: list[RosterPlayerItem]


class FootballMetaAnalysisResponse(BaseModel):
    """GET /api/football/meta_analysis"""

    ok: bool
    date: str
    analysis: str | None = None
    source: str | None = None
