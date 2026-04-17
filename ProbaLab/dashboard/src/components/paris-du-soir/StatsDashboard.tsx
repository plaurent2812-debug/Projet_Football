import { BarChart3, TrendingUp, Target } from "lucide-react"
import { cn } from "@/lib/utils"

interface SportStats {
    total: number
    wins: number
    losses: number
    win_rate: number
    roi_pct?: number
    roi_singles_pct?: number
    combines_count?: number
}

interface MarketData {
    total: number
    wins: number
    losses: number
    win_rate: number
    roi_pct: number
}

interface Stats {
    global: SportStats
    football: SportStats
    nhl: SportStats
    by_market_football?: Record<string, MarketData>
    by_market_nhl?: Record<string, MarketData>
    timeline?: Array<{ date: string; wins: number; losses: number }>
    model_by_market?: Record<string, MarketData>
    model_football?: SportStats & { total: number }
    model_nhl?: SportStats & { total: number }
    expert_by_market?: Record<string, MarketData>
    expert_football?: SportStats & { total: number }
    expert_nhl?: SportStats & { total: number }
    error?: boolean
}

// ── Sub-components ────────────────────────────────────────────

function StatCard({ label, data, color }: { label: string; data: SportStats | null; color: string }) {
    if (!data || data.total === 0) return (
        <div className="rounded-xl border border-border/60 bg-card p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">{label}</p>
            <p className="text-muted-foreground text-sm">Aucun resultat</p>
        </div>
    )
    return (
        <div className={cn("rounded-xl border p-3 overflow-hidden", color)}>
            <p className="text-xs text-muted-foreground mb-1.5 truncate">{label}</p>
            <div className="flex items-end gap-1">
                <span className="text-xl font-black leading-tight">{data.win_rate}%</span>
                <span className="text-xs text-muted-foreground mb-0.5">reussite</span>
            </div>
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-muted-foreground flex-wrap">
                <span className="text-emerald-400 font-semibold">{data.wins}W</span>
                <span className="text-red-400 font-semibold">{data.losses}L</span>
            </div>
            <div className={cn("text-xs font-bold mt-1", (data.roi_singles_pct ?? data.roi_pct ?? 0) >= 0 ? "text-emerald-400" : "text-red-400")}>
                ROI {(data.roi_singles_pct ?? data.roi_pct ?? 0) >= 0 ? "+" : ""}{data.roi_singles_pct ?? data.roi_pct}%
                {(data.combines_count ?? 0) > 0 && <span className="text-muted-foreground font-normal ml-1">(singles)</span>}
            </div>
            <div className="mt-1.5 h-1.5 rounded-full bg-border/40 overflow-hidden">
                <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-700"
                    style={{ width: `${data.win_rate}%` }}
                />
            </div>
        </div>
    )
}

function MarketRow({ market, data }: { market: string; data: MarketData }) {
    return (
        <div className="flex items-center justify-between px-4 py-2.5">
            <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="text-xs text-foreground font-medium truncate">
                    {market}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                    {data.total} paris
                </span>
            </div>
            <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs font-bold">{data.win_rate}%</span>
                <span className="text-xs text-emerald-400">{data.wins}W</span>
                <span className="text-xs text-red-400">{data.losses}L</span>
                <span className={cn(
                    "text-xs font-semibold w-14 text-right",
                    data.roi_pct >= 0 ? "text-emerald-400" : "text-red-400"
                )}>
                    {data.roi_pct >= 0 ? "+" : ""}{data.roi_pct}%
                </span>
            </div>
        </div>
    )
}

// ── Main component ────────────────────────────────────────────

interface StatsDashboardProps {
    stats: Stats | null
    isAdmin: boolean
}

export function StatsDashboard({ stats, isAdmin: _isAdmin }: StatsDashboardProps) {
    if (!stats || stats.error) return null

    const { global: g, football: f, nhl: n } = stats

    const footballMarkets = Object.entries(stats.by_market_football || {})
        .filter(([, data]) => data.total >= 3)
        .sort((a, b) => b[1].total - a[1].total)
    const nhlMarkets = Object.entries(stats.by_market_nhl || {})
        .filter(([, data]) => data.total >= 3)
        .sort((a, b) => b[1].total - a[1].total)

    return (
        <div className="mt-6">
            <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-bold">Performance ProbaLab</h2>
                <span className="text-xs text-muted-foreground ml-1">({g.total} paris resolus)</span>
            </div>

            {/* Global stats cards */}
            <div className="grid grid-cols-3 gap-3">
                <StatCard label="Global" data={g} color="border-primary/20 bg-primary/5" />
                <StatCard label="Football" data={f} color="border-emerald-500/20 bg-emerald-500/5" />
                <StatCard label="NHL" data={n} color="border-cyan-500/20 bg-cyan-500/5" />
            </div>

            {/* Market breakdown — separated by sport */}
            {(footballMarkets.length > 0 || nhlMarkets.length > 0) && (
                <div className="mt-4 space-y-3">
                    {footballMarkets.length > 0 && (
                        <div className="rounded-xl border border-border/60 bg-card overflow-hidden">
                            <div className="px-4 py-2.5 border-b border-border/40 flex items-center gap-2">
                                <span className="text-sm">⚽</span>
                                <p className="text-xs font-semibold">Football — par type de pari</p>
                            </div>
                            <div className="divide-y divide-border/30">
                                {footballMarkets.map(([market, data]) => (
                                    <MarketRow key={market} market={market} data={data} />
                                ))}
                            </div>
                        </div>
                    )}

                    {nhlMarkets.length > 0 && (
                        <div className="rounded-xl border border-border/60 bg-card overflow-hidden">
                            <div className="px-4 py-2.5 border-b border-border/40 flex items-center gap-2">
                                <span className="text-sm">🏒</span>
                                <p className="text-xs font-semibold">NHL — par type de pari</p>
                            </div>
                            <div className="divide-y divide-border/30">
                                {nhlMarkets.map(([market, data]) => (
                                    <MarketRow key={market} market={market} data={data} />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* 30-day timeline */}
            {(stats.timeline?.length ?? 0) > 0 && (
                <div className="mt-4 rounded-xl border border-border/60 bg-card p-4">
                    <p className="text-xs text-muted-foreground mb-3">Historique 30 jours</p>
                    <div className="flex items-end gap-0.5 h-12">
                        {stats.timeline!.map((d, i) => {
                            const total = d.wins + d.losses
                            const winPct = total ? d.wins / total : 0
                            return (
                                <div key={i} className="flex-1 flex flex-col gap-0.5 h-full justify-end" title={`${d.date}: ${d.wins}W ${d.losses}L`}>
                                    {d.losses > 0 && (
                                        <div
                                            className="w-full bg-red-500/40 rounded-sm"
                                            style={{ height: `${(d.losses / Math.max(total, 1)) * 100}%` }}
                                        />
                                    )}
                                    {d.wins > 0 && (
                                        <div
                                            className="w-full bg-emerald-500/60 rounded-sm"
                                            style={{ height: `${winPct * 100}%` }}
                                        />
                                    )}
                                </div>
                            )
                        })}
                    </div>
                    <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                        <span>{stats.timeline![0]?.date}</span>
                        <span>{stats.timeline![stats.timeline!.length - 1]?.date}</span>
                    </div>
                </div>
            )}

            {/* Model Prediction Accuracy */}
            {stats.model_by_market && Object.keys(stats.model_by_market).length > 0 && (
                <div className="mt-5">
                    <div className="flex items-center gap-2 mb-3">
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                        <span className="text-xs font-bold uppercase tracking-wider">Performance (30 J)</span>
                        <div className="ml-auto flex items-center gap-1.5">
                            <span className="text-xs font-bold text-muted-foreground uppercase bg-muted px-1.5 py-0.5 rounded">Algo uniquement</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mb-3">
                        {stats.model_football && stats.model_football.total > 0 && (
                            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 overflow-hidden">
                                <p className="text-xs text-muted-foreground mb-1">⚽ Football Algo</p>
                                <div className="flex items-end gap-1">
                                    <span className="text-xl font-black leading-tight">{stats.model_football.win_rate}%</span>
                                    <span className="text-xs text-muted-foreground mb-0.5">reussite</span>
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                                    <span className="text-emerald-400 font-semibold">{stats.model_football.wins}W</span>
                                    <span className="text-red-400 font-semibold">{stats.model_football.losses}L</span>
                                </div>
                            </div>
                        )}
                        {stats.model_nhl && stats.model_nhl.total > 0 && (
                            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3 overflow-hidden">
                                <p className="text-xs text-muted-foreground mb-1">🏒 NHL Algo</p>
                                <div className="flex items-end gap-1">
                                    <span className="text-xl font-black leading-tight">{stats.model_nhl.win_rate}%</span>
                                    <span className="text-xs text-muted-foreground mb-0.5">reussite</span>
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                                    <span className="text-emerald-400 font-semibold">{stats.model_nhl.wins}W</span>
                                    <span className="text-red-400 font-semibold">{stats.model_nhl.losses}L</span>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="rounded-xl border border-border/60 bg-card overflow-hidden">
                        <div className="px-4 py-2.5 border-b border-border/40">
                            <p className="text-xs font-semibold">Precision par type de prediction</p>
                        </div>
                        <div className="divide-y divide-border/30">
                            {Object.entries(stats.model_by_market)
                                .filter(([, data]) => data.total >= 3)
                                .sort(([, a], [, b]) => b.total - a.total)
                                .map(([market, data]) => (
                                    <MarketRow key={market} market={market} data={data} />
                                ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Expert Prediction Accuracy */}
            {stats.expert_by_market && Object.keys(stats.expert_by_market).length > 0 && (
                <div className="mt-5">
                    <div className="flex items-center gap-2 mb-3">
                        <Target className="w-4 h-4 text-amber-500" />
                        <span className="text-xs font-bold uppercase tracking-wider">Performance Expert (30 J)</span>
                        <div className="ml-auto flex items-center gap-1.5">
                            <span className="text-xs font-bold text-muted-foreground uppercase bg-muted px-1.5 py-0.5 rounded">Expert Uniquement</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mb-3">
                        {stats.expert_football && stats.expert_football.total > 0 && (
                            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 overflow-hidden">
                                <p className="text-xs text-muted-foreground mb-1">⚽ Football Expert</p>
                                <div className="flex items-end gap-1">
                                    <span className="text-xl font-black leading-tight">{stats.expert_football.win_rate}%</span>
                                    <span className="text-xs text-muted-foreground mb-0.5">reussite</span>
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                                    <span className="text-emerald-400 font-semibold">{stats.expert_football.wins}W</span>
                                    <span className="text-red-400 font-semibold">{stats.expert_football.losses}L</span>
                                </div>
                            </div>
                        )}
                        {stats.expert_nhl && stats.expert_nhl.total > 0 && (
                            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 overflow-hidden">
                                <p className="text-xs text-muted-foreground mb-1">🏒 NHL Expert</p>
                                <div className="flex items-end gap-1">
                                    <span className="text-xl font-black leading-tight">{stats.expert_nhl.win_rate}%</span>
                                    <span className="text-xs text-muted-foreground mb-0.5">reussite</span>
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                                    <span className="text-emerald-400 font-semibold">{stats.expert_nhl.wins}W</span>
                                    <span className="text-red-400 font-semibold">{stats.expert_nhl.losses}L</span>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="rounded-xl border border-border/60 bg-card overflow-hidden">
                        <div className="px-4 py-2.5 border-b border-border/40">
                            <p className="text-xs font-semibold">Precision par type de pari (Expert)</p>
                        </div>
                        <div className="divide-y divide-border/30">
                            {Object.entries(stats.expert_by_market)
                                .filter(([, data]) => data.total >= 1)
                                .sort(([, a], [, b]) => b.total - a.total)
                                .map(([market, data]) => (
                                    <MarketRow key={market} market={market} data={data} />
                                ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
