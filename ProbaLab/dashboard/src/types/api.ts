/**
 * TypeScript types mirroring the Pydantic response models in api/response_models.py.
 * Keep in sync with the backend schemas.
 *
 * Mapping conventions:
 *   Optional[float] / Optional[int]  →  number | null
 *   Optional[str]                    →  string | null
 *   dict[str, Any]                   →  Record<string, unknown>
 *   list[Any]                        →  unknown[]
 *   Any                              →  unknown
 *   extra="allow" models             →  index signature [key: string]: unknown
 */

// ─── Shared ──────────────────────────────────────────────────────────────────

/** Generic error envelope returned on 4xx/5xx. */
export interface ErrorResponse {
  detail: string
}

/** Minimal success acknowledgement. */
export interface OkResponse {
  ok: boolean
}

// ─── Health ──────────────────────────────────────────────────────────────────

/** GET /health */
export interface HealthResponse {
  status: string
  timestamp: string
}

// ─── News ────────────────────────────────────────────────────────────────────

/** A single item fetched from an RSS feed. */
export interface NewsItem {
  title: string
  link: string
  source: string
  pub_date: string
}

/** GET /api/news */
export interface NewsResponse {
  news: NewsItem[]
}

// ─── Email ───────────────────────────────────────────────────────────────────

/** POST /api/resend/welcome  •  POST /api/resend/premium-confirm */
export interface EmailSentResponse {
  sent: boolean
}

// ─── Search ──────────────────────────────────────────────────────────────────

/** One prediction result returned by semantic search. */
export interface SearchPredictionItem {
  fixture_id: number | null
  home_team: string
  away_team: string
  date: string | null
  league: string
  analysis_text: string
  proba_home: number | null
  proba_draw: number | null
  proba_away: number | null
  similarity: number
  [key: string]: unknown
}

/** One learning result returned by semantic search. */
export interface SearchLearningItem {
  learning_text: string | null
  tags: unknown
  similarity: number
  [key: string]: unknown
}

/** GET /api/search/semantic */
export interface SemanticSearchResponse {
  query: string
  predictions: SearchPredictionItem[]
  learnings: SearchLearningItem[]
  [key: string]: unknown
}

// ─── Expert Picks ─────────────────────────────────────────────────────────────

/** One selection inside an expert pick (single or combiné leg). */
export interface EnrichedSelection {
  match: string
  market: string
  player_name: string | null
  bet_raw: string
  is_mymatch: boolean
  [key: string]: unknown
}

/** A single expert pick row, enriched for the frontend. */
export interface ExpertPickItem {
  id: number
  date: string
  sport: string
  player_name: string | null
  market: string | null
  match_label: string | null
  odds: number | null
  confidence: number | null
  expert_note: string | null
  result: string | null
  created_at: string | null
  selections: EnrichedSelection[]
  is_combine: boolean
  bet_type: string
  has_mymatch: boolean
  [key: string]: unknown
}

/** GET /api/expert-picks */
export interface ExpertPicksResponse {
  date: string
  picks: ExpertPickItem[]
  [key: string]: unknown
}

/** GET /api/expert-picks/latest */
export interface LatestExpertPickResponse {
  pick: Record<string, unknown> | null
  [key: string]: unknown
}

/** DELETE /api/expert-picks/{pick_id} */
export interface DeleteExpertPickResponse {
  deleted: boolean
  id: number
}

/** POST /api/expert-picks/backfill */
export interface BackfillExpertPicksResponse {
  inserted: number
  errors: Record<string, unknown>[]
  ids: Record<string, unknown>[]
}

/** One resolved pick entry inside the resolve response. */
export interface ResolvedPickDetail {
  id: number
  market: string
  match: string
  result: string
  note: string
  [key: string]: unknown
}

/** POST /api/expert-picks/resolve */
export interface ResolveExpertPicksResponse {
  ok: boolean
  date: string
  resolved_count: number
  resolved: ResolvedPickDetail[]
  errors: Record<string, unknown>[]
  message: string | null
}

// ─── Admin ───────────────────────────────────────────────────────────────────

/** POST /api/admin/run-pipeline  •  POST /api/cron/run-pipeline */
export interface PipelineStartResponse {
  ok: boolean | null
  message: string | null
  started_at: string | null
  status: string | null
  [key: string]: unknown
}

/** GET /api/admin/pipeline-status */
export interface PipelineStatusResponse {
  status: string
  mode: string | null
  started_at: string | null
  finished_at: string | null
  logs: string
  return_code: number | null
  [key: string]: unknown
}

/** POST /api/admin/stop-pipeline */
export interface PipelineStopResponse {
  message: string
}

/** POST /api/admin/update-scores */
export interface UpdateScoresResponse {
  message: string
}

// ─── Best Bets ───────────────────────────────────────────────────────────────

/** A single bet candidate (football or NHL). */
export interface BetCandidate {
  fixture_id: unknown
  label: string
  match: string
  market: string
  odds: number
  proba_model: number
  confidence: number
  ev: number
  is_value: boolean
  odds_source: string
  result: string
  time: string
  id: number | null
  [key: string]: unknown
}

/** The football_safe / nhl_safe envelope. */
export interface SafeBetWrapper {
  type: string
  bet: Record<string, unknown>
  odds: number
  [key: string]: unknown
}

/** The football_fun / nhl_fun envelope. */
export interface FunBetWrapper {
  type: string
  bets: Record<string, unknown>[]
  total_odds: number
  count: number
  [key: string]: unknown
}

/** GET /api/best-bets */
export interface BestBetsResponse {
  date: string
  football: Record<string, unknown>[]
  nhl: Record<string, unknown>[]
  football_safe: SafeBetWrapper | null
  football_fun: FunBetWrapper | null
  nhl_safe: SafeBetWrapper | null
  nhl_fun: FunBetWrapper | null
  [key: string]: unknown
}

/** POST /api/best-bets/save */
export interface SaveBetResponse {
  ok: boolean
  id: number | null
}

/** PATCH /api/best-bets/{bet_id}/result */
export interface UpdateBetResultResponse {
  ok: boolean
  updated: Record<string, unknown>[] | null
  [key: string]: unknown
}

// ─── Monitoring ──────────────────────────────────────────────────────────────

/** Closing Line Value metrics block. */
export interface CLVMetrics {
  clv_best_mean: number
  clv_when_correct: number
  pct_positive_clv: number
  n_matches: number
  verdict: string
  by_league: Record<string, unknown>
  daily_clv: unknown[]
  status: string
  [key: string]: unknown
}

/** Brier score and calibration metrics block. */
export interface BrierMetrics {
  brier_1x2: number | null
  brier_1x2_grade: string | null
  ece: number | null
  ece_grade: string | null
  log_loss: number | null
  btts: number | null
  over15: number | null
  over25: number | null
  n_matches: number
  drift: Record<string, unknown>
  [key: string]: unknown
}

/** GET /api/monitoring */
export interface MonitoringResponse {
  clv: CLVMetrics
  brier: BrierMetrics
  health_score: number
  [key: string]: unknown
}

/** GET /api/monitoring/health */
export interface MonitoringHealthResponse {
  healthy: boolean
  predictions_today: number
  last_prediction_at: string | null
  yesterday_coverage_pct: number | null
  yesterday_fixtures: number
  yesterday_predictions: number
  evaluated_results_total: number
  checked_at: string
  [key: string]: unknown
}

// ─── Performance ─────────────────────────────────────────────────────────────

/** One day's accuracy bucket inside the performance response. */
export interface DailyStatItem {
  date: string
  total: number
  correct: number
}

/** Market coverage counts. */
export interface CoverageStats {
  total_1x2_countable: number
  total_btts: number
  total_over_05: number
  total_over_15: number
  total_over_25: number
  total_over_35: number
  total_score: number
}

/** Single benchmark entry. */
export interface BenchmarkEntry {
  accuracy: number
  total: number
  [key: string]: unknown
}

/** Benchmarks section of the performance response. */
export interface PerformanceBenchmarks {
  always_home: BenchmarkEntry
  bookmaker_implied: BenchmarkEntry
  model: BenchmarkEntry
  [key: string]: unknown
}

/** GET /api/performance */
export interface PerformanceResponse {
  days: number
  total_matches: number
  accuracy_1x2: number
  accuracy_btts: number
  accuracy_over_05: number
  accuracy_over_15: number
  accuracy_over_25: number
  accuracy_over_35: number
  accuracy_score: number
  avg_confidence: number
  value_bets: number
  brier_score_1x2: number
  brier_score_1x2_normalized: number
  daily_stats: DailyStatItem[]
  total_finished: number
  total_without_prediction: number
  skipped_null_probas: number
  skipped_ties: number
  coverage: CoverageStats
  benchmarks: PerformanceBenchmarks | null
  [key: string]: unknown
}

// ─── Market ROI ──────────────────────────────────────────────────────────────

export interface MarketROIEntry {
  label: string
  total: number
  wins: number
  losses: number
  winrate: number
  roi: number
  profitable: boolean
  active: boolean
}

export interface MarketROIResponse {
  days: number
  markets: Record<string, MarketROIEntry>
  active_markets: string[]
  disabled_markets: string[]
}

// ─── Predictions ─────────────────────────────────────────────────────────────

/** The nested prediction object inside a match item. */
export interface PredictionBlock {
  proba_home: number | null
  proba_draw: number | null
  proba_away: number | null
  proba_btts: number | null
  proba_over_2_5: number | null
  recommended_bet: string | null
  confidence_score: number | null
  kelly_edge: number | null
  value_bet: boolean | null
  model_version: string | null
  correct_score: string | null
  analysis_text: string | null
  proba_penalty: number | null
  proba_over_05: number | null
  proba_over_15: number | null
  proba_over_35: number | null
  [key: string]: unknown
}

/** The best_value object — highest positive-EV market for a fixture. */
export interface BestValueBlock {
  market: string
  edge: number
  odds: number | null
}

/** One enriched fixture + prediction row returned by GET /api/predictions. */
export interface MatchItem {
  id: unknown
  home_team: string
  away_team: string
  home_logo: string | null
  away_logo: string | null
  date: string | null
  status: string | null
  home_goals: number | null
  away_goals: number | null
  events_json: unknown[]
  elapsed: number | null
  live_stats_json: Record<string, unknown>
  league_id: number | null
  league_name: string
  prediction: PredictionBlock | null
  odds: Record<string, unknown> | null
  value_edges: Record<string, unknown>
  best_value: BestValueBlock | null
  is_value_bet: boolean
  [key: string]: unknown
}

/** GET /api/predictions */
export interface PredictionsListResponse {
  date: string
  matches: MatchItem[]
}

/** One top-scorer entry in the prediction detail view. */
export interface TopScorerItem {
  name: string
  photo: string | null
  goals: number
  apps: number
  [key: string]: unknown
}

/** GET /api/predictions/{fixture_id} */
export interface PredictionDetailResponse {
  fixture: Record<string, unknown> | null
  prediction: Record<string, unknown> | null
  home_scorers: TopScorerItem[]
  away_scorers: TopScorerItem[]
  match_stats: Record<string, unknown>[]
  odds: Record<string, unknown> | null
  value_edges: Record<string, unknown>
  [key: string]: unknown
}

// ─── Teams ───────────────────────────────────────────────────────────────────

/** One historical match from a team's perspective. */
export interface TeamMatchResult {
  fixture_id: unknown
  date: string
  opponent: string
  score: string
  result: string
  home_away: string
  league_id: number | null
  [key: string]: unknown
}

/** Win/draw/loss summary for a team history response. */
export interface TeamSummary {
  wins: number
  draws: number
  losses: number
  total: number
  streak: Record<string, unknown>
  [key: string]: unknown
}

/** GET /api/team/{team_name}/history */
export interface TeamHistoryResponse {
  team_name: string
  matches: TeamMatchResult[]
  summary: TeamSummary
}

/** One player entry from the API-Football squads endpoint. */
export interface RosterPlayerItem {
  id: number | null
  name: string | null
  age: number | null
  number: number | null
  position: string | null
  photo: string | null
  appearances: number | null
  goals: number | null
  assists: number | null
  goals_conceded: number | null
  [key: string]: unknown
}

/** GET /api/team/{team_name}/roster */
export interface TeamRosterResponse {
  team_name: string
  roster: RosterPlayerItem[]
}

/** GET /api/football/meta_analysis */
export interface FootballMetaAnalysisResponse {
  ok: boolean
  date: string
  analysis: string | null
  source: string | null
}

// ─── NHL (no Pydantic models yet — shapes inferred from API usage) ────────────

/** Player profile response from GET /api/players/{player_id}. */
export interface PlayerProfileResponse {
  id: number
  name: string
  team: string | null
  position: string | null
  stats: Record<string, number>
  [key: string]: unknown
}

/** NHL top players response from GET /nhl/match/{fixture_id}/top_players. */
export interface NHLTopPlayersResponse {
  ok: boolean
  players: Array<{
    id: number
    name: string
    team: string
    stats: Record<string, number>
  }> | null
  [key: string]: unknown
}

// ─── Backward-compatible aliases ─────────────────────────────────────────────
// These re-export under the names used by src/lib/api.ts before the rename.

/** @deprecated Use PredictionsListResponse */
export type PredictionsResponse = PredictionsListResponse

/** @deprecated Use FootballMetaAnalysisResponse */
export type MetaAnalysisResponse = FootballMetaAnalysisResponse

/** @deprecated Use PipelineStartResponse */
export type PipelineTriggerResponse = PipelineStartResponse

/** @deprecated Use MatchItem */
export type Match = MatchItem
