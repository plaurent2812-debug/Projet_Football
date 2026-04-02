import { useState, useEffect } from 'react'
import { supabase } from '@/lib/auth'
import { BarChart3, Users, Zap, Trophy, TrendingUp, Activity, RefreshCw, Globe, Target, AlertTriangle } from 'lucide-react'
import { API_ROOT, fetchMonitoring } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data?.session?.access_token
    if (!token) console.warn("Admin request without auth token — may be rejected")
    return { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
}

function CLVTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null
    const d = payload[0]
    return (
        <div className="rounded-lg border border-white/10 bg-background/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
            <p className="font-semibold">{label}</p>
            <p className={d.value >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                CLV: {(d.value * 100).toFixed(1)}%
            </p>
            <p className="text-muted-foreground">{d.payload.n} matchs</p>
        </div>
    )
}

export default function AdminOverview() {
    const [stats, setStats] = useState<any>(null)
    const [quota, setQuota] = useState<any>(null)
    const [monitoring, setMonitoring] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [monLoading, setMonLoading] = useState(true)

    const fetchAll = async () => {
        setLoading(true)
        const headers = await getAuthHeaders()
        try {
            const [statsRes, quotaRes] = await Promise.all([
                fetch(`${API_ROOT}/api/trigger/admin/stats`, { headers }),
                fetch(`${API_ROOT}/api/trigger/admin/api-quota`, { headers }),
            ])
            setStats(await statsRes.json())
            setQuota(await quotaRes.json())
        } catch (e) { console.error(e) }
        finally { setLoading(false) }
    }

    const fetchMon = async () => {
        setMonLoading(true)
        try {
            const data = await fetchMonitoring()
            setMonitoring(data)
        } catch (e) { console.error(e) }
        finally { setMonLoading(false) }
    }

    useEffect(() => { fetchAll(); fetchMon() }, [])

    const quotaPct = quota?.limit_day ? Math.round((quota.current / quota.limit_day) * 100) : 0
    const quotaColor = quotaPct > 80 ? 'text-red-400' : quotaPct > 50 ? 'text-amber-400' : 'text-emerald-400'
    const quotaBarColor = quotaPct > 80 ? 'bg-red-500' : quotaPct > 50 ? 'bg-amber-500' : 'bg-emerald-500'

    // CLV helpers
    const clv = monitoring?.clv || {}
    const brier = monitoring?.brier || {}
    const clvMean = clv.clv_best_mean ?? 0
    const clvColor = clv.verdict === 'BEATING_MARKET' ? 'text-emerald-400' : clv.verdict === 'MATCHING_MARKET' ? 'text-amber-400' : 'text-red-400'
    const clvBorder = clv.verdict === 'BEATING_MARKET' ? 'border-emerald-500/20' : clv.verdict === 'MATCHING_MARKET' ? 'border-amber-500/20' : 'border-red-500/20'
    const clvBg = clv.verdict === 'BEATING_MARKET' ? 'from-emerald-500/10 to-emerald-500/5' : clv.verdict === 'MATCHING_MARKET' ? 'from-amber-500/10 to-amber-500/5' : 'from-red-500/10 to-red-500/5'

    const pctClv = clv.pct_positive_clv ?? 0
    const pctColor = pctClv > 50 ? 'text-emerald-400' : 'text-red-400'
    const pctBorder = pctClv > 50 ? 'border-emerald-500/20' : 'border-red-500/20'
    const pctBg = pctClv > 50 ? 'from-emerald-500/10 to-emerald-500/5' : 'from-red-500/10 to-red-500/5'

    const brierVal = brier.brier_1x2
    const brierColor = brierVal == null ? 'text-muted-foreground' : brierVal < 0.60 ? 'text-emerald-400' : brierVal < 0.65 ? 'text-amber-400' : 'text-red-400'
    const brierBorder = brierVal == null ? 'border-white/10' : brierVal < 0.60 ? 'border-emerald-500/20' : brierVal < 0.65 ? 'border-amber-500/20' : 'border-red-500/20'
    const brierBg = brierVal == null ? 'from-white/5 to-white/5' : brierVal < 0.60 ? 'from-emerald-500/10 to-emerald-500/5' : brierVal < 0.65 ? 'from-amber-500/10 to-amber-500/5' : 'from-red-500/10 to-red-500/5'

    const dailyClv = (clv.daily_clv || []).slice(-30).map((d: any) => ({
        ...d,
        date_short: d.date?.slice(5) || '',
    }))

    const leagueNames: Record<number, string> = {
        39: 'PL', 61: 'L1', 140: 'Liga', 135: 'Serie A', 78: 'BuLi',
        2: 'CL', 3: 'EL', 62: 'L2', 848: 'ECL',
    }

    return (
        <div className="space-y-6">
            {/* Refresh */}
            <div className="flex justify-end">
                <button onClick={() => { fetchAll(); fetchMon() }} disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors">
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Rafraîchir
                </button>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: 'Utilisateurs', value: stats?.total_users ?? '—', icon: Users, color: 'text-violet-400', bg: 'from-violet-500/10 to-violet-500/5', border: 'border-violet-500/20' },
                    { label: 'Prédictions (Aujourd\'hui)', value: stats?.predictions_today ?? '—', icon: Zap, color: 'text-blue-400', bg: 'from-blue-500/10 to-blue-500/5', border: 'border-blue-500/20' },
                    { label: 'Matchs (Aujourd\'hui)', value: stats?.matches_today ?? '—', icon: Trophy, color: 'text-amber-400', bg: 'from-amber-500/10 to-amber-500/5', border: 'border-amber-500/20' },
                    { label: 'Inscriptions (7j)', value: stats?.signups_last_7d ?? '—', icon: TrendingUp, color: 'text-emerald-400', bg: 'from-emerald-500/10 to-emerald-500/5', border: 'border-emerald-500/20' },
                ].map(kpi => {
                    const Icon = kpi.icon
                    return (
                        <div key={kpi.label} className={`glass rounded-2xl border ${kpi.border} p-5 bg-gradient-to-br ${kpi.bg}`}>
                            <div className="flex items-center justify-between mb-3">
                                <Icon className={`w-5 h-5 ${kpi.color}`} />
                                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{kpi.label}</span>
                            </div>
                            {loading ? (
                                <div className="h-9 w-16 rounded-lg bg-white/10 animate-pulse" />
                            ) : (
                                <div className={`text-3xl font-black ${kpi.color}`}>{kpi.value}</div>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* ═══════════ MODEL QUALITY SECTION ═══════════ */}
            <div className="pt-2">
                <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2 mb-4">
                    <Target className="w-4 h-4" /> Qualité du Modèle
                    {monitoring?.health_score != null && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                            monitoring.health_score >= 7 ? 'bg-emerald-500/20 text-emerald-400' :
                            monitoring.health_score >= 4 ? 'bg-amber-500/20 text-amber-400' :
                            'bg-red-500/20 text-red-400'
                        }`}>
                            {monitoring.health_score}/10
                        </span>
                    )}
                </h2>

                {/* CLV + Brier KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                    <div className={`glass rounded-2xl border ${clvBorder} p-5 bg-gradient-to-br ${clvBg}`}>
                        <div className="flex items-center justify-between mb-3">
                            <TrendingUp className={`w-5 h-5 ${clvColor}`} />
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">CLV Moyen</span>
                        </div>
                        {monLoading ? (
                            <div className="h-9 w-20 rounded-lg bg-white/10 animate-pulse" />
                        ) : (
                            <>
                                <div className={`text-3xl font-black ${clvColor}`}>
                                    {clvMean >= 0 ? '+' : ''}{(clvMean * 100).toFixed(1)}%
                                </div>
                                <div className="text-[10px] text-muted-foreground mt-1">
                                    {clv.n_matches || 0} matchs — {clv.verdict === 'BEATING_MARKET' ? 'Bat le marché' : clv.verdict === 'MATCHING_MARKET' ? 'Niveau marché' : clv.verdict === 'NO_DATA' ? 'Pas de données' : 'Sous le marché'}
                                </div>
                            </>
                        )}
                    </div>

                    <div className={`glass rounded-2xl border ${pctBorder} p-5 bg-gradient-to-br ${pctBg}`}>
                        <div className="flex items-center justify-between mb-3">
                            <Activity className={`w-5 h-5 ${pctColor}`} />
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">% CLV Positif</span>
                        </div>
                        {monLoading ? (
                            <div className="h-9 w-16 rounded-lg bg-white/10 animate-pulse" />
                        ) : (
                            <>
                                <div className={`text-3xl font-black ${pctColor}`}>{pctClv}%</div>
                                <div className="text-[10px] text-muted-foreground mt-1">
                                    {clv.n_positive_clv ?? 0} / {clv.n_matches ?? 0} paris
                                </div>
                            </>
                        )}
                    </div>

                    <div className={`glass rounded-2xl border ${brierBorder} p-5 bg-gradient-to-br ${brierBg}`}>
                        <div className="flex items-center justify-between mb-3">
                            <BarChart3 className={`w-5 h-5 ${brierColor}`} />
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Brier 1X2</span>
                        </div>
                        {monLoading ? (
                            <div className="h-9 w-16 rounded-lg bg-white/10 animate-pulse" />
                        ) : (
                            <>
                                <div className={`text-3xl font-black ${brierColor}`}>{brierVal?.toFixed(4) ?? '—'}</div>
                                <div className="text-[10px] text-muted-foreground mt-1">
                                    {brier.brier_1x2_grade ?? '—'} — ECE: {brier.ece?.toFixed(3) ?? '—'}
                                    {brier.drift?.drift_detected && (
                                        <span className="text-red-400 ml-1 inline-flex items-center gap-0.5">
                                            <AlertTriangle className="w-3 h-3" /> Drift
                                        </span>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* CLV Daily Chart + League Table */}
                <div className="grid md:grid-cols-3 gap-6">
                    {/* Chart */}
                    <div className="md:col-span-2 glass rounded-2xl border border-white/10 p-6">
                        <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                            <TrendingUp className="w-4 h-4 text-cyan-400" />
                            CLV Quotidien (30 derniers jours)
                        </h3>
                        {monLoading ? (
                            <div className="h-48 bg-white/5 rounded-lg animate-pulse" />
                        ) : dailyClv.length > 0 ? (
                            <div className="h-48">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={dailyClv} barGap={1}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                        <XAxis dataKey="date_short" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} />
                                        <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                                        <Tooltip content={<CLVTooltip />} />
                                        <Bar dataKey="clv" radius={[3, 3, 0, 0]}>
                                            {dailyClv.map((_: any, i: number) => (
                                                <Cell key={i} fill={dailyClv[i].clv >= 0 ? '#10b981' : '#ef4444'} fillOpacity={0.7} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <p className="text-sm text-muted-foreground py-8 text-center">Pas de données CLV disponibles</p>
                        )}
                    </div>

                    {/* League CLV Table */}
                    <div className="glass rounded-2xl border border-white/10 p-6">
                        <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                            <Globe className="w-4 h-4 text-violet-400" />
                            CLV par Ligue
                        </h3>
                        {monLoading ? (
                            <div className="space-y-2">
                                {[1,2,3,4].map(i => <div key={i} className="h-6 bg-white/5 rounded animate-pulse" />)}
                            </div>
                        ) : Object.keys(clv.by_league || {}).length > 0 ? (
                            <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                {Object.entries(clv.by_league || {})
                                    .sort((a: any, b: any) => (b[1].clv_mean ?? 0) - (a[1].clv_mean ?? 0))
                                    .map(([lid, info]: [string, any]) => {
                                        const name = leagueNames[Number(lid)] || `L${lid}`
                                        const val = info.clv_mean ?? 0
                                        return (
                                            <div key={lid} className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
                                                <span className="text-xs font-medium">{name}</span>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] text-muted-foreground">{info.n}m</span>
                                                    <span className={`text-xs font-bold ${val >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {val >= 0 ? '+' : ''}{(val * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    })}
                            </div>
                        ) : (
                            <p className="text-sm text-muted-foreground py-4 text-center">Pas de données</p>
                        )}
                    </div>
                </div>
            </div>

            {/* ═══════════ INFRA SECTION ═══════════ */}
            <div className="grid md:grid-cols-2 gap-6">
                {/* API-Football Quota */}
                <div className="glass rounded-2xl border border-white/10 p-6">
                    <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                        <Globe className="w-4 h-4 text-green-400" />
                        API-Football — Quota du jour
                    </h3>
                    {quota?.error ? (
                        <p className="text-sm text-red-400">{quota.error}</p>
                    ) : quota ? (
                        <div className="space-y-4">
                            <div className="flex items-end justify-between">
                                <div>
                                    <span className={`text-4xl font-black ${quotaColor}`}>{quota.current?.toLocaleString()}</span>
                                    <span className="text-muted-foreground text-sm"> / {quota.limit_day?.toLocaleString()}</span>
                                </div>
                                <span className={`text-lg font-bold ${quotaColor}`}>{quotaPct}%</span>
                            </div>
                            <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden">
                                <div className={`h-full ${quotaBarColor} rounded-full transition-all duration-500`} style={{ width: `${quotaPct}%` }} />
                            </div>
                            <div className="flex justify-between text-[11px] text-muted-foreground">
                                <span>Restant: <strong className="text-foreground">{quota.remaining?.toLocaleString()}</strong></span>
                                <span>Plan: <strong className="text-foreground">{quota.plan}</strong></span>
                            </div>
                        </div>
                    ) : (
                        <div className="h-20 bg-white/5 rounded-lg animate-pulse" />
                    )}
                </div>

                {/* Cost Estimation */}
                <div className="glass rounded-2xl border border-white/10 p-6">
                    <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                        <BarChart3 className="w-4 h-4 text-amber-400" />
                        Estimation Coûts Mensuels
                    </h3>
                    <div className="space-y-3">
                        {[
                            { name: 'API-Football', cost: '29€', color: 'text-green-400' },
                            { name: 'Gemini 2.5 Flash', cost: '~12-16€', color: 'text-blue-400' },
                            { name: 'Railway (backend)', cost: '~5€', color: 'text-orange-400' },
                            { name: 'Vercel (frontend)', cost: '0€', color: 'text-emerald-400' },
                            { name: 'Supabase (DB)', cost: '0€', color: 'text-violet-400' },
                            { name: 'Trigger.dev', cost: '10€', color: 'text-cyan-400' },
                        ].map(item => (
                            <div key={item.name} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                                <span className="text-sm text-muted-foreground">{item.name}</span>
                                <span className={`text-sm font-bold ${item.color}`}>{item.cost}</span>
                            </div>
                        ))}
                        <div className="flex items-center justify-between pt-2 border-t border-white/20">
                            <span className="text-sm font-bold">Total estimé</span>
                            <span className="text-lg font-black text-foreground">~60€/mois</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Users by Role + Predictions Stats */}
            <div className="grid md:grid-cols-2 gap-6">
                <div className="glass rounded-2xl border border-white/10 p-6">
                    <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                        <Users className="w-4 h-4 text-violet-400" />
                        Répartition des rôles
                    </h3>
                    <div className="space-y-3">
                        {Object.entries(stats?.users_by_role || {}).map(([role, count]: [string, any]) => {
                            const total = stats?.total_users || 1
                            const pct = Math.round((count / total) * 100)
                            const colors: any = { admin: 'bg-red-500', premium: 'bg-amber-500', free: 'bg-slate-500' }
                            return (
                                <div key={role}>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="capitalize font-semibold">{role}</span>
                                        <span className="text-muted-foreground">{count} ({pct}%)</span>
                                    </div>
                                    <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                                        <div className={`h-full ${colors[role] || 'bg-blue-500'} rounded-full`} style={{ width: `${pct}%` }} />
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>

                <div className="glass rounded-2xl border border-white/10 p-6">
                    <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                        <Activity className="w-4 h-4 text-blue-400" />
                        Prédictions
                    </h3>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-3 rounded-xl bg-blue-500/5 border border-blue-500/20">
                            <span className="text-sm text-muted-foreground">Aujourd'hui</span>
                            <span className="text-2xl font-black text-blue-400">{stats?.predictions_today ?? '—'}</span>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-xl bg-violet-500/5 border border-violet-500/20">
                            <span className="text-sm text-muted-foreground">Total (all-time)</span>
                            <span className="text-2xl font-black text-violet-400">{stats?.predictions_total?.toLocaleString() ?? '—'}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
