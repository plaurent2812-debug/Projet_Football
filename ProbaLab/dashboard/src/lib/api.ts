import { supabase } from '@/lib/auth'
import type {
  PredictionsListResponse,
  PredictionDetailResponse,
  PerformanceResponse,
  MarketROIResponse,
  NewsResponse,
  MonitoringResponse,
  FootballMetaAnalysisResponse,
  TeamHistoryResponse,
  TeamRosterResponse,
  PipelineStatusResponse,
  PipelineStartResponse,
  PipelineStopResponse,
} from '@/types/api'

export const API_ROOT = import.meta.env.VITE_API_URL || ''
export const API_BASE = API_ROOT.endsWith('/api')
  ? API_ROOT
  : API_ROOT
  ? `${API_ROOT}/api`
  : '/api'
// NHL router uses /nhl prefix (no /api), so we use API_ROOT directly
export const NHL_BASE = API_ROOT

async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session?.access_token) return {}
  return { Authorization: `Bearer ${session.access_token}` }
}

async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json() as Promise<T>
}

/**
 * Typed API object — no internal cache (React Query handles caching).
 * All function names are stable so existing pages can be migrated incrementally.
 */
export const api = {
  // ── Predictions ─────────────────────────────────────────────

  getPredictions(date?: string): Promise<PredictionsListResponse> {
    const params = date ? `?date=${date}` : ''
    return fetchApi<PredictionsListResponse>(`${API_BASE}/predictions${params}`)
  },

  getPredictionDetail(fixtureId: number | string): Promise<PredictionDetailResponse> {
    return fetchApi<PredictionDetailResponse>(`${API_BASE}/predictions/${fixtureId}`)
  },

  // ── Performance ──────────────────────────────────────────────

  getPerformance(days = 30): Promise<PerformanceResponse> {
    return fetchApi<PerformanceResponse>(`${API_BASE}/performance?days=${days}`)
  },

  getNHLPerformance(days = 30): Promise<PerformanceResponse> {
    return fetchApi<PerformanceResponse>(`${NHL_BASE}/nhl/performance?days=${days}`)
  },

  getMarketROI(days = 30): Promise<MarketROIResponse> {
    return fetchApi<MarketROIResponse>(`${API_BASE}/market-roi?days=${days}`)
  },

  // ── Teams ────────────────────────────────────────────────────

  getTeamHistory(teamName: string, limit = 60): Promise<TeamHistoryResponse> {
    return fetchApi<TeamHistoryResponse>(
      `${API_BASE}/team/${encodeURIComponent(teamName)}/history?limit=${limit}`,
    )
  },

  getTeamRoster(teamName: string): Promise<TeamRosterResponse> {
    return fetchApi<TeamRosterResponse>(
      `${API_BASE}/team/${encodeURIComponent(teamName)}/roster`,
    )
  },

  // ── Admin (authenticated) ────────────────────────────────────

  async triggerPipeline(mode = 'full'): Promise<PipelineStartResponse> {
    const headers = await getAuthHeaders()
    const res = await fetch(`${API_BASE}/admin/run-pipeline?mode=${mode}`, {
      method: 'POST',
      headers,
    })
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as { detail?: string }
      throw new Error(err.detail || `API error: ${res.status}`)
    }
    return res.json() as Promise<PipelineStartResponse>
  },

  triggerNHLPipeline(): Promise<PipelineStartResponse> {
    return api.triggerPipeline('nhl')
  },

  async getPipelineStatus(): Promise<PipelineStatusResponse> {
    const headers = await getAuthHeaders()
    return fetchApi<PipelineStatusResponse>(`${API_BASE}/admin/pipeline-status`, {
      headers,
    })
  },

  async stopPipeline(): Promise<PipelineStopResponse> {
    const headers = await getAuthHeaders()
    const res = await fetch(`${API_BASE}/admin/stop-pipeline`, {
      method: 'POST',
      headers,
    })
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as { detail?: string }
      throw new Error(err.detail || `API error: ${res.status}`)
    }
    return res.json() as Promise<PipelineStopResponse>
  },

  // ── News / Monitoring ────────────────────────────────────────

  async getNews(): Promise<NewsResponse> {
    const res = await fetch(`${API_BASE}/news`)
    if (!res.ok) return { news: [] }
    return res.json() as Promise<NewsResponse>
  },

  getMonitoring(): Promise<MonitoringResponse> {
    return fetchApi<MonitoringResponse>(`${API_BASE}/monitoring`)
  },

  // ── Meta-analysis ────────────────────────────────────────────

  async getFootballMetaAnalysis(date?: string): Promise<FootballMetaAnalysisResponse | null> {
    const params = date ? `?date=${date}` : ''
    try {
      const res = await fetch(`${API_BASE}/football/meta_analysis${params}`)
      if (!res.ok) return null
      return res.json() as Promise<FootballMetaAnalysisResponse>
    } catch {
      return null
    }
  },

  async getNHLMetaAnalysis(date?: string): Promise<FootballMetaAnalysisResponse | null> {
    const params = date ? `?date=${date}` : ''
    try {
      const res = await fetch(`${NHL_BASE}/nhl/meta_analysis${params}`)
      if (!res.ok) return null
      return res.json() as Promise<FootballMetaAnalysisResponse>
    } catch {
      return null
    }
  },

  // ── Players ──────────────────────────────────────────────────

  getPlayerProfile(playerId: number | string): Promise<Record<string, unknown>> {
    return fetchApi<Record<string, unknown>>(`${API_BASE}/players/${playerId}`)
  },

  async getNHLMatchTopPlayers(
    fixtureId: number | string,
  ): Promise<Record<string, unknown> | null> {
    const res = await fetch(`${NHL_BASE}/nhl/match/${fixtureId}/top_players`)
    if (!res.ok) return null
    return res.json() as Promise<Record<string, unknown>>
  },
}

// ── Backward-compatible named exports ─────────────────────────
// These shims let all existing pages (which import named functions from
// api.js) continue to compile unchanged while the migration to React Query
// hooks proceeds incrementally.  They delegate to `api` so there is a
// single source of truth.

/** @deprecated Use usePredictions() hook from @/lib/queries */
export function fetchPredictions(
  date?: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _skipCache = false,
): Promise<PredictionsListResponse> {
  return api.getPredictions(date)
}

/** @deprecated Use usePredictionDetail() hook from @/lib/queries */
export function fetchPredictionDetail(
  fixtureId: number | string,
): Promise<PredictionDetailResponse> {
  return api.getPredictionDetail(fixtureId)
}

/** @deprecated Use useFootballPerformance() hook from @/lib/queries */
export function fetchPerformance(days = 30): Promise<PerformanceResponse> {
  return api.getPerformance(days)
}

/** @deprecated Use useNHLPerformance() hook from @/lib/queries */
export function fetchNHLPerformance(days = 30): Promise<PerformanceResponse> {
  return api.getNHLPerformance(days)
}

/** @deprecated Use useMarketROI() hook from @/lib/queries */
export function fetchMarketROI(days = 30): Promise<MarketROIResponse> {
  return api.getMarketROI(days)
}

/** @deprecated Use useTeamHistory() hook from @/lib/queries */
export function fetchTeamHistory(
  teamName: string,
  limit = 60,
): Promise<TeamHistoryResponse> {
  return api.getTeamHistory(teamName, limit)
}

/** @deprecated Use useTeamRoster() hook from @/lib/queries */
export function fetchTeamRoster(teamName: string): Promise<TeamRosterResponse> {
  return api.getTeamRoster(teamName)
}

/** @deprecated Use api.triggerPipeline() directly */
export function triggerPipeline(mode = 'full'): Promise<PipelineStartResponse> {
  return api.triggerPipeline(mode)
}

/** @deprecated Use api.triggerNHLPipeline() directly */
export function triggerNHLPipeline(): Promise<PipelineStartResponse> {
  return api.triggerNHLPipeline()
}

/** @deprecated Use usePipelineStatus() hook from @/lib/queries */
export function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  return api.getPipelineStatus()
}

/** @deprecated Use api.stopPipeline() directly */
export function stopPipeline(): Promise<PipelineStopResponse> {
  return api.stopPipeline()
}

/** @deprecated Use useNews() hook from @/lib/queries */
export function fetchNews(): Promise<NewsResponse> {
  return api.getNews()
}

/** @deprecated Use useMonitoring() hook from @/lib/queries */
export function fetchMonitoring(): Promise<MonitoringResponse> {
  return api.getMonitoring()
}

/** @deprecated Use useFootballMetaAnalysis() hook from @/lib/queries */
export function fetchFootballMetaAnalysis(
  date?: string,
): Promise<FootballMetaAnalysisResponse | null> {
  return api.getFootballMetaAnalysis(date)
}

/** @deprecated Use useNHLMetaAnalysis() hook from @/lib/queries */
export function fetchNHLMetaAnalysis(
  date?: string,
): Promise<FootballMetaAnalysisResponse | null> {
  return api.getNHLMetaAnalysis(date)
}

/** @deprecated Use usePlayerProfile() hook from @/lib/queries */
export function fetchPlayerProfile(
  playerId: number | string,
): Promise<Record<string, unknown>> {
  return api.getPlayerProfile(playerId)
}

/** @deprecated Use useNHLMatchTopPlayers() hook from @/lib/queries */
export function fetchNHLMatchTopPlayers(
  fixtureId: number | string,
): Promise<Record<string, unknown> | null> {
  return api.getNHLMatchTopPlayers(fixtureId)
}

/** @deprecated No longer needed — React Query handles caching */
export function clearApiCache(): void {
  // no-op: cache is managed by React Query's QueryClient
}
