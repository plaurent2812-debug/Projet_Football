import { supabase } from '@/lib/auth'

export const API_ROOT = import.meta.env.VITE_API_URL || ''
export const API_BASE = API_ROOT.endsWith('/api') ? API_ROOT : (API_ROOT ? `${API_ROOT}/api` : '/api')
// NHL router uses /nhl prefix (no /api), so we use API_ROOT directly
export const NHL_BASE = API_ROOT

async function getAuthHeaders() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) return {}
    return { Authorization: `Bearer ${session.access_token}` }
}

const cache = {}
const CACHE_TTL = 60 * 1000 // 60 seconds

/** Clear all cached API responses (call on logout) */
export function clearApiCache() {
    for (const key of Object.keys(cache)) {
        delete cache[key]
    }
}

export async function fetchPredictions(date, skipCache = false) {
    const params = date ? `?date=${date}` : ''
    const url = `${API_BASE}/predictions${params}`

    // Check cache
    if (!skipCache && cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }

    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()

    // Save to cache
    cache[url] = { data, timestamp: Date.now() }
    return data
}

export async function fetchPredictionDetail(fixtureId) {
    const url = `${API_BASE}/predictions/${fixtureId}`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }
    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()
    cache[url] = { data, timestamp: Date.now() }
    return data
}

export async function fetchPerformance(days = 30) {
    const url = `${API_BASE}/performance?days=${days}`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }

    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()
    cache[url] = { data, timestamp: Date.now() }
    return data
}

export async function fetchNHLPerformance(days = 30) {
    const url = `${NHL_BASE}/nhl/performance?days=${days}`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }

    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()
    cache[url] = { data, timestamp: Date.now() }
    return data
}

export async function fetchTeamHistory(teamName, limit = 60) {
    const url = `${API_BASE}/team/${encodeURIComponent(teamName)}/history?limit=${limit}`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }
    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()
    cache[url] = { data, timestamp: Date.now() }
    return data
}

export async function fetchTeamRoster(teamName) {
    const url = `${API_BASE}/team/${encodeURIComponent(teamName)}/roster`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }
    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()
    cache[url] = { data, timestamp: Date.now() }
    return data
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

export async function triggerNHLPipeline() {
    return triggerPipeline('nhl')
}


export async function fetchPipelineStatus() {
    const headers = await getAuthHeaders()
    const res = await fetch(`${API_BASE}/admin/pipeline-status`, { headers })
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function stopPipeline() {
    const headers = await getAuthHeaders()
    const res = await fetch(`${API_BASE}/admin/stop-pipeline`, {
        method: 'POST',
        headers,
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `API error: ${res.status}`)
    }
    return res.json()
}

export async function fetchNews() {
    const res = await fetch(`${API_BASE}/news`)
    if (!res.ok) return { news: [] }
    return res.json()
}

export async function fetchNHLMatchTopPlayers(fixtureId) {
    const res = await fetch(`${NHL_BASE}/nhl/match/${fixtureId}/top_players`)
    if (!res.ok) return null
    return res.json()
}

export async function fetchNHLMetaAnalysis(date) {
    const params = date ? `?date=${date}` : ''
    const url = `${NHL_BASE}/nhl/meta_analysis${params}`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL * 5) {
        return cache[url].data
    }
    try {
        const res = await fetch(url)
        if (!res.ok) return null
        const data = await res.json()
        if (data?.ok) cache[url] = { data, timestamp: Date.now() }
        return data
    } catch {
        return null
    }
}

export async function fetchPlayerProfile(playerId) {
    const res = await fetch(`${API_BASE}/players/${playerId}`)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.json()
}

export async function fetchMonitoring() {
    const url = `${API_BASE}/monitoring`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL) {
        return cache[url].data
    }
    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    const data = await res.json()
    cache[url] = { data, timestamp: Date.now() }
    return data
}

export async function fetchFootballMetaAnalysis(date) {
    const params = date ? `?date=${date}` : ''
    const url = `${API_BASE}/football/meta_analysis${params}`
    if (cache[url] && Date.now() - cache[url].timestamp < CACHE_TTL * 5) {
        return cache[url].data
    }
    try {
        const res = await fetch(url)
        if (!res.ok) return null
        const data = await res.json()
        if (data?.ok) cache[url] = { data, timestamp: Date.now() }
        return data
    } catch {
        return null
    }
}
