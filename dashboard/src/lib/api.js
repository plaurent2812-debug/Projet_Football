import { supabase } from '@/lib/auth'

const API_ROOT = import.meta.env.VITE_API_URL || ''
const API_BASE = API_ROOT.endsWith('/api') ? API_ROOT : (API_ROOT ? `${API_ROOT}/api` : '/api')

async function getAuthHeaders() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) return {}
    return { Authorization: `Bearer ${session.access_token}` }
}

export async function fetchPredictions(date) {
    const params = date ? `?date=${date}` : ''
    const res = await fetch(`${API_BASE}/predictions${params}`)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function fetchPredictionDetail(fixtureId) {
    const res = await fetch(`${API_BASE}/predictions/${fixtureId}`)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function fetchPerformance(days = 30) {
    const res = await fetch(`${API_BASE}/performance?days=${days}`)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function fetchTeamHistory(teamName, limit = 20) {
    const res = await fetch(`${API_BASE}/team/${encodeURIComponent(teamName)}/history?limit=${limit}`)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function triggerPipeline(mode = 'full') {
    const headers = await getAuthHeaders()
    const res = await fetch(`${API_BASE}/admin/run-pipeline?mode=${mode}`, {
        method: 'POST',
        headers,
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `API error: ${res.status}`)
    }
    return res.json()
}

export async function fetchPipelineStatus() {
    const headers = await getAuthHeaders()
    const res = await fetch(`${API_BASE}/admin/pipeline-status`, { headers })
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function fetchNews() {
    const res = await fetch(`${API_BASE}/news`)
    if (!res.ok) return { news: [] }
    return res.json()
}

export async function fetchNHLMatchTopPlayers(fixtureId) {
    const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/nhl/match/${fixtureId}/top_players`)
    if (!res.ok) return null
    return res.json()
}
