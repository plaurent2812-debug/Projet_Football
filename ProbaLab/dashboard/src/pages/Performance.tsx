import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
    BarChart3, Target, TrendingUp, Percent,
    CheckCircle2, XCircle, Trophy, Zap, Activity, Swords, Info,
    ShieldCheck, ShieldOff, ArrowUpRight, ArrowDownRight,
} from "lucide-react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import type { MarketROIResponse, MarketROIEntry } from "@/types/api"

import { StatTile, MarketCard, InfoTooltip } from "@/components/performance/ui"
import { BrierCard } from "@/components/performance/BrierCard"
import { CoverageSection } from "@/components/performance/CoverageSection"
import { BenchmarksSection } from "@/components/performance/BenchmarksSection"
import { DailyChart } from "@/components/performance/DailyChart"


/* ── Market strategy row ──────────────────────────────────── */
function MarketStrategyRow({ data }: { data: MarketROIEntry }) {
    const isActive = data.active
    const isProfitable = data.roi > 0
    return (
        <div className={cn(
            "flex items-center gap-3 p-3 rounded-lg border transition-colors",
            isActive
                ? "bg-card/50 border-border/40"
                : "bg-red-500/5 border-red-500/20 opacity-70"
        )}>
            <div className={cn(
                "p-1.5 rounded-md",
                isProfitable ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
            )}>
                {isActive ? <ShieldCheck className="w-4 h-4" /> : <ShieldOff className="w-4 h-4" />}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{data.label}</p>
                <p className="text-[11px] text-muted-foreground">
                    {data.total} paris · {data.winrate}% winrate
                </p>
            </div>
            <div className="text-right">
                <div className={cn(
                    "flex items-center gap-0.5 text-sm font-bold tabular-nums",
                    isProfitable ? "text-emerald-400" : "text-red-400"
                )}>
                    {isProfitable
                        ? <ArrowUpRight className="w-3.5 h-3.5" />
                        : <ArrowDownRight className="w-3.5 h-3.5" />
                    }
                    {data.roi > 0 ? "+" : ""}{data.roi}%
                </div>
                <p className="text-[10px] text-muted-foreground">ROI</p>
            </div>
            <div className={cn(
                "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider",
                isActive
                    ? (isProfitable ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400")
                    : "bg-red-500/15 text-red-400"
            )}>
                {isActive ? (isProfitable ? "Actif" : "Surveil.") : "Off"}
            </div>
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════
   Performance Page
   ═══════════════════════════════════════════════════════════ */
export default function PerformancePage() {
    const [data, setData] = useState<any>(null)
    const [marketROI, setMarketROI] = useState<MarketROIResponse | null>(null)
    const [jours, setJours] = useState(90)
    const [sport, setSport] = useState("football")
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [retryKey, setRetryKey] = useState(0)

    useEffect(() => {
        setLoading(true)
        setError(null)

        import('@/lib/api').then(({ fetchPerformance, fetchNHLPerformance, fetchMarketROI }) => {
            const fetcher = sport === 'nhl' ? fetchNHLPerformance : fetchPerformance

            const promises: Promise<any>[] = [fetcher(jours)]
            if (sport === 'football') {
                promises.push(fetchMarketROI(jours).catch(() => null))
            }

            Promise.all(promises)
                .then(([perfData, roiData]) => {
                    setData(perfData)
                    if (roiData) setMarketROI(roiData)
                })
                .catch((err: Error) => {
                    console.error(err)
                    setError(err.message)
                })
                .finally(() => setLoading(false))
        })
    }, [jours, sport, retryKey])

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32">
                <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-32 text-center space-y-4">
                <div className="p-4 bg-destructive/10 rounded-full text-destructive">
                    <XCircle className="w-8 h-8" />
                </div>
                <div>
                    <h3 className="text-lg font-semibold">Erreur de chargement</h3>
                    <p className="text-muted-foreground">{error}</p>
                </div>
                <button
                    onClick={() => { setError(null); setRetryKey(k => k + 1) }}
                    className="px-4 py-2 bg-secondary rounded-md text-sm font-medium hover:bg-secondary/80"
                >
                    Reessayer
                </button>
            </div>
        )
    }

    if (!data) return null

    const chartData = data.daily_stats.map((d: any) => ({
        ...d,
        accuracy: d.total > 0 ? Math.round((d.correct / d.total) * 100) : 0,
        date_short: d.date?.slice(5) || d.date,
    }))

    const coverage = data.coverage ?? {}
    const benchmarks = data.benchmarks ?? null

    // Market accuracy data for the grid based on sport
    const markets = sport === 'football' ? [
        { label: "Resultat 1X2", accuracy: data.accuracy_1x2, icon: Swords, color: "text-indigo-400", total: coverage.total_1x2_countable },
        { label: "But des 2 equipes", accuracy: data.accuracy_btts, icon: Percent, color: "text-emerald-400", total: coverage.total_btts },
        { label: "Plus de 0.5 buts", accuracy: data.accuracy_over_05 ?? "—", icon: TrendingUp, color: "text-blue-400", total: coverage.total_over_05 },
        { label: "Plus de 1.5 buts", accuracy: data.accuracy_over_15 ?? "—", icon: TrendingUp, color: "text-blue-400", total: coverage.total_over_15 },
        { label: "Plus de 2.5 buts", accuracy: data.accuracy_over_25 ?? "—", icon: TrendingUp, color: "text-amber-400", total: coverage.total_over_25 },
        { label: "Plus de 3.5 buts", accuracy: data.accuracy_over_35 ?? "—", icon: TrendingUp, color: "text-orange-400", total: coverage.total_over_35 },
        { label: "Score exact (exp.)", accuracy: data.accuracy_score ?? "—", icon: Target, color: "text-purple-400", total: coverage.total_score },
    ].filter(m => m.accuracy !== "—") : [
        { label: "Taux Buts (Top 1)", accuracy: data.accuracy_goal, icon: Target, color: "text-emerald-400", total: undefined },
        { label: "Taux Passes (Top 1)", accuracy: data.accuracy_assist, icon: Target, color: "text-blue-400", total: undefined },
        { label: "Taux Points (Top 1)", accuracy: data.accuracy_point, icon: Target, color: "text-amber-400", total: undefined },
        { label: "Taux Tirs (Top 1)", accuracy: data.accuracy_shot, icon: Target, color: "text-orange-400", total: undefined },
    ].filter(m => m.accuracy !== "—")

    const brierScore: number | null = sport === 'football'
        ? (data.brier_score_1x2_normalized ?? data.brier_score_1x2 ?? null)
        : (data.brier_score ?? null)

    return (
        <div className="space-y-6 pb-12">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-black tracking-tight">Performance</h1>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        Taux de reussite sur les {jours > 0 ? `${jours} derniers jours` : "toute la periode"}
                    </p>
                </div>

                <div className="flex items-center gap-4 flex-wrap">
                    {/* Sport Toggle */}
                    <div className="flex p-0.5 rounded-lg bg-secondary/50 ring-1 ring-border/50">
                        <button
                            onClick={() => setSport("football")}
                            className={cn(
                                "px-4 py-1.5 text-xs font-semibold rounded-md transition-all duration-200",
                                sport === "football" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            Football
                        </button>
                        <button
                            onClick={() => setSport("nhl")}
                            className={cn(
                                "px-4 py-1.5 text-xs font-semibold rounded-md transition-all duration-200",
                                sport === "nhl" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            NHL
                        </button>
                    </div>

                    {/* Date Toggle */}
                    <div className="flex p-0.5 rounded-lg bg-secondary/50 ring-1 ring-border/50">
                        {[{ d: 0, label: "Tout" }, { d: 7, label: "7j" }, { d: 14, label: "14j" }, { d: 30, label: "30j" }, { d: 60, label: "60j" }, { d: 90, label: "90j" }].map(({ d, label }) => (
                            <button
                                key={d}
                                onClick={() => setJours(d)}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200",
                                    jours === d
                                        ? "bg-card text-foreground shadow-sm"
                                        : "text-muted-foreground hover:text-foreground"
                                )}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* KPI cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatTile
                    value={data.total_finished ? `${data.total_matches}/${data.total_finished}` : data.total_matches}
                    label="Matchs analyses"
                    icon={BarChart3}
                    accent="bg-indigo-500/10 text-indigo-400"
                />

                {sport === 'football' ? (
                    <>
                        <StatTile
                            value={`${data.accuracy_1x2}%`}
                            label="Precision 1X2"
                            icon={Target}
                            accent="bg-emerald-500/10 text-emerald-400"
                        />
                        <div className="flex items-center gap-3 p-4 rounded-xl bg-card/50 border border-border/40">
                            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                                <Activity className="w-5 h-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-black tabular-nums">
                                    {data.brier_score_1x2_normalized != null
                                        ? data.brier_score_1x2_normalized.toFixed(3)
                                        : data.brier_score_1x2?.toFixed(3) || "—"}
                                </p>
                                <div className="flex items-center gap-1">
                                    <p className="text-xs text-muted-foreground font-medium">Calibration</p>
                                    <div className="group relative">
                                        <Info className="w-3 h-3 text-muted-foreground cursor-help" />
                                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-card border border-border rounded-lg shadow-xl text-xs text-muted-foreground w-52 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                                            <strong className="text-foreground">Brier Score normalise</strong> — qualite des probabilites sur une echelle 0 a 1.
                                            <br /><span className="text-emerald-400">0 = parfait</span> · 0.25 = hasard · <span className="text-red-400">0.5 = mauvais</span>.
                                            <br />Moins c'est bas, mieux c'est.
                                        </div>
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground">(0 = parfait · 0.33 = hasard)</p>
                            </div>
                        </div>
                        <StatTile
                            value={data.avg_confidence}
                            label="Confiance moyenne"
                            icon={Zap}
                            accent="bg-amber-500/10 text-amber-400"
                        />
                        {data.value_bets > 0 && (
                            <StatTile
                                value={data.value_bets}
                                label="Paris value"
                                icon={Trophy}
                                accent="bg-purple-500/10 text-purple-400"
                            />
                        )}
                    </>
                ) : (
                    <>
                        <StatTile
                            value={`${data.accuracy_goal}%`}
                            label="Buteurs Top 1"
                            icon={Target}
                            accent="bg-emerald-500/10 text-emerald-400"
                        />
                        <div className="flex items-center gap-3 p-4 rounded-xl bg-card/50 border border-border/40">
                            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                                <Activity className="w-5 h-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-black tabular-nums">
                                    {data.brier_score != null
                                        ? data.brier_score.toFixed(3)
                                        : "—"}
                                </p>
                                <div className="flex items-center gap-1">
                                    <p className="text-xs text-muted-foreground font-medium">Calibration</p>
                                    <div className="group relative">
                                        <Info className="w-3 h-3 text-muted-foreground cursor-help" />
                                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-card border border-border rounded-lg shadow-xl text-xs text-muted-foreground w-52 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                                            <strong className="text-foreground">Brier Score</strong> — qualite des probabilites binaires.
                                            <br /><span className="text-emerald-400">0 = parfait</span> · 0.25 = hasard · <span className="text-red-400">0.5 = mauvais</span>.
                                        </div>
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground">(0 = parfait · 0.33 = hasard)</p>
                            </div>
                        </div>
                        <StatTile
                            value={`${data.accuracy_point}%`}
                            label="Points Top 1"
                            icon={Target}
                            accent="bg-amber-500/10 text-amber-400"
                        />
                        <StatTile
                            value={data.avg_confidence}
                            label="Confiance moy."
                            icon={Zap}
                            accent="bg-purple-500/10 text-purple-400"
                        />
                    </>
                )}
            </div>

            {/* Per-market accuracy grid */}
            <Card className="bg-card/50 border-border/50">
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-sm">
                        <Activity className="w-4 h-4 text-primary" />
                        Taux de reussite par marche
                        <InfoTooltip content={
                            <>
                                <strong className="text-foreground block mb-1">Intervalle de confiance Wilson 95%</strong>
                                La marge (±x%) indique l'incertitude statistique due a la taille de l'echantillon.
                                Un grand echantillon = marge faible = metrique fiable.
                            </>
                        } />
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                        {markets.map(m => (
                            <MarketCard
                                key={m.label}
                                label={m.label}
                                accuracy={m.accuracy}
                                icon={m.icon}
                                color={m.color}
                                total={m.total}
                            />
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Brier score detail */}
            {brierScore != null && (
                <BrierCard score={brierScore} />
            )}

            {/* Benchmarks — football only */}
            {sport === 'football' && benchmarks && (
                <BenchmarksSection
                    benchmarks={benchmarks}
                    modelAccuracy={data.accuracy_1x2}
                />
            )}

            {/* Coverage — football only */}
            {sport === 'football' && data.total_finished != null && (
                <CoverageSection
                    totalMatches={data.total_matches}
                    totalFinished={data.total_finished}
                    skippedNullProbas={data.skipped_null_probas ?? 0}
                    skippedTies={data.skipped_ties ?? 0}
                    coverage={coverage}
                />
            )}

            {/* Chart: Daily accuracy + volume */}
            <DailyChart chartData={chartData} />

            {/* Value Betting Strategy — Market Performance */}
            {sport === 'football' && marketROI && marketROI.markets && Object.keys(marketROI.markets).length > 0 && (
                <Card className="bg-card/50 border-border/50">
                    <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-sm">
                            <Trophy className="w-4 h-4 text-primary" />
                            Strategie Value Betting — Performance par marche
                        </CardTitle>
                        <p className="text-[11px] text-muted-foreground mt-1">
                            Les marches avec un ROI &lt; -5% sont automatiquement desactives dans la detection des value bets.
                        </p>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {Object.entries(marketROI.markets).map(([key, mkt]) => (
                                <MarketStrategyRow key={key} data={mkt} />
                            ))}
                        </div>

                        {/* Summary stats */}
                        <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border/30">
                            <div className="flex items-center gap-1.5">
                                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                                <span className="text-xs text-muted-foreground">
                                    <span className="font-semibold text-foreground">{marketROI.active_markets?.length || 0}</span> marches actifs
                                </span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <ShieldOff className="w-3.5 h-3.5 text-red-400" />
                                <span className="text-xs text-muted-foreground">
                                    <span className="font-semibold text-foreground">{marketROI.disabled_markets?.length || 0}</span> desactives
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
