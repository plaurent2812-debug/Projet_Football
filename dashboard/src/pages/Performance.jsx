import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchPerformance } from "@/lib/api"
import {
    BarChart3, Target, TrendingUp, Percent, Calendar,
    CheckCircle2, XCircle, Trophy, Zap, Activity, Swords
} from "lucide-react"
import { useState, useEffect } from "react"
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Cell
} from "recharts"
import { cn } from "@/lib/utils"


/* ── Accuracy ring (circular progress) ─────────────────────── */
function AccuracyRing({ value, size = 52, strokeWidth = 5 }) {
    const radius = (size - strokeWidth) / 2
    const circumference = 2 * Math.PI * radius
    const offset = circumference - (value / 100) * circumference

    const color = value >= 70
        ? "stroke-emerald-500"
        : value >= 50
            ? "stroke-amber-400"
            : "stroke-red-400"

    return (
        <svg width={size} height={size} className="shrink-0 -rotate-90">
            <circle
                cx={size / 2} cy={size / 2} r={radius}
                className="stroke-secondary"
                strokeWidth={strokeWidth}
                fill="none"
            />
            <circle
                cx={size / 2} cy={size / 2} r={radius}
                className={color}
                strokeWidth={strokeWidth}
                fill="none"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
                style={{ transition: "stroke-dashoffset 1s ease-out" }}
            />
        </svg>
    )
}


/* ── Market accuracy card ──────────────────────────────────── */
function MarketCard({ label, accuracy, icon: Icon, color, isAdmin }) {
    return (
        <div className="flex items-center gap-3 p-3.5 rounded-xl bg-card/50 border border-border/40 hover:border-border/70 transition-colors">
            <div className="relative">
                <AccuracyRing value={accuracy} />
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold tabular-nums rotate-0">
                    {accuracy}%
                </span>
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{label}</p>
                <div className="flex items-center gap-1 mt-0.5">
                    <Icon className={cn("w-3 h-3", color)} />
                    {isAdmin && (
                        <span className={cn("text-[11px] font-medium",
                            accuracy >= 70 ? "text-emerald-400" : accuracy >= 50 ? "text-amber-400" : "text-red-400"
                        )}>
                            {accuracy >= 70 ? "Excellent" : accuracy >= 50 ? "Correct" : "À améliorer"}
                        </span>
                    )}
                </div>
            </div>
        </div>
    )
}


/* ── Stat tile (header KPIs) ───────────────────────────────── */
function StatTile({ value, label, icon: Icon, accent }) {
    return (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-card/50 border border-border/40">
            <div className={cn("p-2 rounded-lg", accent)}>
                <Icon className="w-5 h-5" />
            </div>
            <div>
                <p className="text-2xl font-black tabular-nums">{value}</p>
                <p className="text-[11px] text-muted-foreground font-medium">{label}</p>
            </div>
        </div>
    )
}


/* ── Custom tooltip for charts ─────────────────────────────── */
function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-lg border border-border bg-card p-3 shadow-xl">
            <p className="text-[11px] text-muted-foreground font-medium mb-1">📅 {label}</p>
            {payload.map((p, i) => (
                <p key={i} className="text-sm font-semibold">
                    <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: p.color }} />
                    {p.name}: <span className="tabular-nums">{p.value}</span>
                </p>
            ))}
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════
   Performance Page
   ═══════════════════════════════════════════════════════════ */
export default function PerformancePage() {
    const [data, setData] = useState(null)
    const [jours, setJours] = useState(30)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        setLoading(true)
        setError(null)
        fetchPerformance(jours)
            .then(setData)
            .catch(err => {
                console.error(err)
                setError(err.message)
            })
            .finally(() => setLoading(false))
    }, [jours])

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
                    onClick={() => setJours(jours)}
                    className="px-4 py-2 bg-secondary rounded-md text-sm font-medium hover:bg-secondary/80"
                >
                    Réessayer
                </button>
            </div>
        )
    }

    if (!data) return null

    const chartData = data.daily_stats.map(d => ({
        ...d,
        accuracy: d.total > 0 ? Math.round((d.correct / d.total) * 100) : 0,
        date_short: d.date?.slice(5) || d.date
    }))

    // Market accuracy data for the grid
    const markets = [
        { label: "Résultat 1X2", accuracy: data.accuracy_1x2, icon: Swords, color: "text-indigo-400" },
        { label: "But des 2 équipes", accuracy: data.accuracy_btts, icon: Percent, color: "text-emerald-400" },
        { label: "Plus de 0.5 buts", accuracy: data.accuracy_over_05 ?? "—", icon: TrendingUp, color: "text-blue-400" },
        { label: "Plus de 1.5 buts", accuracy: data.accuracy_over_15 ?? "—", icon: TrendingUp, color: "text-blue-400" },
        { label: "Plus de 2.5 buts", accuracy: data.accuracy_over_25 ?? "—", icon: TrendingUp, color: "text-amber-400" },
        { label: "Plus de 3.5 buts", accuracy: data.accuracy_over_35 ?? "—", icon: TrendingUp, color: "text-orange-400" },
        { label: "Score exact", accuracy: data.accuracy_score ?? "—", icon: Target, color: "text-purple-400" },
    ].filter(m => m.accuracy !== "—")

    return (
        <div className="space-y-6 pb-12">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-black tracking-tight">Performance</h1>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        Taux de réussite sur les {jours} derniers jours
                    </p>
                </div>
                <div className="flex p-0.5 rounded-lg bg-secondary/50 ring-1 ring-border/50">
                    {[7, 14, 30, 60, 90].map((d) => (
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
                            {d}j
                        </button>
                    ))}
                </div>
            </div>

            {/* KPI cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatTile
                    value={data.total_matches}
                    label="Matchs analysés"
                    icon={BarChart3}
                    accent="bg-indigo-500/10 text-indigo-400"
                />
                <StatTile
                    value={`${data.accuracy_1x2}%`}
                    label="Précision 1X2"
                    icon={Target}
                    accent="bg-emerald-500/10 text-emerald-400"
                />
                <StatTile
                    value={data.avg_confidence}
                    label="Confiance moyenne"
                    icon={Zap}
                    accent="bg-amber-500/10 text-amber-400"
                />
                <StatTile
                    value={data.value_bets}
                    label="Paris value"
                    icon={Trophy}
                    accent="bg-purple-500/10 text-purple-400"
                />
            </div>

            {/* Per-market accuracy grid */}
            <Card className="bg-card/50 border-border/50">
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-sm">
                        <Activity className="w-4 h-4 text-primary" />
                        Taux de réussite par marché
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
                                isAdmin={true}
                            />
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Chart: Daily accuracy + volume (combined) */}
            {chartData.length > 0 && (
                <Card className="bg-card/50 border-border/50">
                    <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-sm">
                            <Calendar className="w-4 h-4 text-primary" />
                            Résultats jour par jour
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[280px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData} barGap={2}>
                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="oklch(0.25 0.008 260)"
                                        vertical={false}
                                    />
                                    <XAxis
                                        dataKey="date_short"
                                        tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "oklch(0.25 0.008 260 / 0.3)" }} />
                                    <Bar
                                        dataKey="total"
                                        name="Analysés"
                                        radius={[4, 4, 0, 0]}
                                        maxBarSize={32}
                                    >
                                        {chartData.map((entry, i) => (
                                            <Cell
                                                key={i}
                                                fill="oklch(0.35 0.01 260)"
                                            />
                                        ))}
                                    </Bar>
                                    <Bar
                                        dataKey="correct"
                                        name="Corrects"
                                        radius={[4, 4, 0, 0]}
                                        maxBarSize={32}
                                    >
                                        {chartData.map((entry, i) => {
                                            const acc = entry.total > 0 ? entry.correct / entry.total : 0
                                            return (
                                                <Cell
                                                    key={i}
                                                    fill={acc >= 0.6
                                                        ? "oklch(0.7 0.18 155)"
                                                        : acc >= 0.4
                                                            ? "oklch(0.75 0.16 85)"
                                                            : "oklch(0.65 0.2 260)"
                                                    }
                                                />
                                            )
                                        })}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                        {/* Legend */}
                        <div className="flex items-center justify-center gap-6 mt-3">
                            <div className="flex items-center gap-1.5">
                                <div className="w-3 h-3 rounded-sm" style={{ background: "oklch(0.35 0.01 260)" }} />
                                <span className="text-[11px] text-muted-foreground">Matchs analysés</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-3 h-3 rounded-sm" style={{ background: "oklch(0.7 0.18 155)" }} />
                                <span className="text-[11px] text-muted-foreground">Corrects</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}


