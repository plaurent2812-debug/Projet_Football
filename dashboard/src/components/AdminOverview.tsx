import { useState, useEffect } from 'react'
import { supabase } from '@/lib/auth'
import { BarChart3, Users, Zap, Trophy, TrendingUp, Activity, RefreshCw, Globe } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'https://web-production-ff663.up.railway.app'

async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data?.session?.access_token
    return { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
}

export default function AdminOverview() {
    const [stats, setStats] = useState<any>(null)
    const [quota, setQuota] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    const fetchAll = async () => {
        setLoading(true)
        const headers = await getAuthHeaders()
        try {
            const [statsRes, quotaRes] = await Promise.all([
                fetch(`${API_BASE}/api/trigger/admin/stats`, { headers }),
                fetch(`${API_BASE}/api/trigger/admin/api-quota`, { headers }),
            ])
            setStats(await statsRes.json())
            setQuota(await quotaRes.json())
        } catch (e) { console.error(e) }
        finally { setLoading(false) }
    }

    useEffect(() => { fetchAll() }, [])

    const quotaPct = quota ? Math.round((quota.current / quota.limit_day) * 100) : 0
    const quotaColor = quotaPct > 80 ? 'text-red-400' : quotaPct > 50 ? 'text-amber-400' : 'text-emerald-400'
    const quotaBarColor = quotaPct > 80 ? 'bg-red-500' : quotaPct > 50 ? 'bg-amber-500' : 'bg-emerald-500'

    return (
        <div className="space-y-6">
            {/* Refresh */}
            <div className="flex justify-end">
                <button onClick={fetchAll} disabled={loading}
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
                            <div className={`text-3xl font-black ${kpi.color}`}>{loading ? '...' : kpi.value}</div>
                        </div>
                    )
                })}
            </div>

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
                            { name: 'Trigger.dev', cost: '0€', color: 'text-cyan-400' },
                        ].map(item => (
                            <div key={item.name} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                                <span className="text-sm text-muted-foreground">{item.name}</span>
                                <span className={`text-sm font-bold ${item.color}`}>{item.cost}</span>
                            </div>
                        ))}
                        <div className="flex items-center justify-between pt-2 border-t border-white/20">
                            <span className="text-sm font-bold">Total estimé</span>
                            <span className="text-lg font-black text-foreground">~50€/mois</span>
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
