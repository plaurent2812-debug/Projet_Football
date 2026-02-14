import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import {
    ChevronRight, Calendar, ChevronLeft, Sparkles, Clock,
    TrendingUp, Target
} from "lucide-react"
import { useNavigate } from "react-router-dom"
import { fetchPredictions } from "@/lib/api"
import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth"


/* ── Confidence indicator ──────────────────────────────────── */
function ConfidencePill({ score }) {
    if (score == null) return null
    const bg = score >= 8
        ? "bg-emerald-500/15 text-emerald-400 ring-emerald-500/20"
        : score >= 6
            ? "bg-amber-500/15 text-amber-400 ring-amber-500/20"
            : "bg-zinc-500/15 text-zinc-400 ring-zinc-500/20"
    return (
        <span className={cn("text-[11px] font-bold tabular-nums px-2 py-0.5 rounded-full ring-1", bg)}>
            {score}<span className="text-[9px] opacity-60">/10</span>
        </span>
    )
}


/* ── Single match row ──────────────────────────────────────── */
function MatchRow({ match }) {
    const navigate = useNavigate()
    const { isPremium } = useAuth()
    const pred = match.prediction
    const time = match.date?.slice(11, 16) || "—"
    const isFinished = match.status === "FT"

    // Determine winner for visual weight
    const homeWon = isFinished && match.home_goals > match.away_goals
    const awayWon = isFinished && match.away_goals > match.home_goals

    return (
        <div
            onClick={() => navigate(`/match/${match.id}`)}
            className={cn(
                "group flex items-center gap-3 sm:gap-4 px-3 sm:px-4 py-3.5 cursor-pointer",
                "hover:bg-accent/40 active:bg-accent/60 transition-all duration-150",
                "border-b border-border/30 last:border-b-0"
            )}
        >
            {/* Time column */}
            <div className="w-11 shrink-0 text-center">
                {isFinished ? (
                    <span className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider">
                        Terminé
                    </span>
                ) : (
                    <div className="flex flex-col items-center">
                        <Clock className="w-3 h-3 text-muted-foreground/50 mb-0.5" />
                        <span className="text-sm font-bold tabular-nums text-foreground">
                            {time}
                        </span>
                    </div>
                )}
            </div>

            {/* Separator */}
            <div className="w-px h-8 bg-border/50 shrink-0" />

            {/* Teams + Score */}
            <div className="flex-1 min-w-0 flex items-center">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <span
                            onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/equipe/${encodeURIComponent(match.home_team)}`)
                            }}
                            className={cn(
                                "text-[13px] font-semibold truncate hover:text-primary hover:underline cursor-pointer transition-colors",
                                homeWon ? "text-foreground" : isFinished ? "text-muted-foreground" : "text-foreground"
                            )}
                        >
                            {match.home_team}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                        <span
                            onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/equipe/${encodeURIComponent(match.away_team)}`)
                            }}
                            className={cn(
                                "text-[13px] font-semibold truncate hover:text-primary hover:underline cursor-pointer transition-colors",
                                awayWon ? "text-foreground" : isFinished ? "text-muted-foreground" : "text-foreground"
                            )}
                        >
                            {match.away_team}
                        </span>
                    </div>
                </div>

                {/* Score if finished */}
                {isFinished && (
                    <div className="w-8 shrink-0 text-center ml-2">
                        <div className={cn("text-[13px] tabular-nums font-bold", homeWon && "text-foreground")}>
                            {match.home_goals}
                        </div>
                        <div className={cn("text-[13px] tabular-nums font-bold mt-1", awayWon && "text-foreground")}>
                            {match.away_goals}
                        </div>
                    </div>
                )}
            </div>

            {/* Indicators */}
            <div className="shrink-0 flex items-center gap-2">
                {pred?.value_bet && isPremium && (
                    <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20">
                        <TrendingUp className="w-3 h-3 text-emerald-400" />
                        <span className="text-[10px] font-bold text-emerald-400 uppercase">Value</span>
                    </div>
                )}
                {pred && <ConfidencePill score={pred.confidence_score} />}
            </div>

            {/* Arrow */}
            <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground group-hover:translate-x-0.5 transition-all shrink-0" />
        </div >
    )
}


/* ── League section ────────────────────────────────────────── */
function LeagueSection({ leagueName, matches }) {
    return (
        <div className="rounded-xl border border-border/50 bg-card/50 overflow-hidden">
            {/* League header */}
            <div className="px-4 py-2.5 flex items-center justify-between border-b border-border/30 bg-accent/20">
                <div className="flex items-center gap-2.5">
                    <div className="w-1 h-4 rounded-full bg-primary" />
                    <span className="text-xs font-bold uppercase tracking-wider text-foreground/90">
                        {leagueName}
                    </span>
                </div>
                <span className="text-[11px] text-muted-foreground font-medium tabular-nums">
                    {matches.length} match{matches.length > 1 ? "s" : ""}
                </span>
            </div>
            {/* Rows */}
            <div>
                {matches.map((match) => (
                    <MatchRow key={match.id} match={match} />
                ))}
            </div>
        </div>
    )
}


/* ── Dashboard page ────────────────────────────────────────── */
export default function DashboardPage({ date, setDate }) {
    const { isPremium } = useAuth()
    const [matches, setMatches] = useState([])
    const [activeTab, setActiveTab] = useState("all")
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        const d1 = date
        const d2 = new Date(new Date(date).getTime() + 86400000).toISOString().slice(0, 10)

        Promise.all([
            fetchPredictions(d1),
            fetchPredictions(d2)
        ]).then(([res1, res2]) => {
            const combined = [...(res1.matches || []), ...(res2.matches || [])]
                .sort((a, b) => a.date.localeCompare(b.date))
            setMatches(combined)
        }).catch(console.error)
            .finally(() => setLoading(false))
    }, [date])

    const tomorrow = new Date(new Date(date).getTime() + 86400000).toISOString().slice(0, 10)
    const yesterday = new Date(new Date(date).getTime() - 86400000).toISOString().slice(0, 10)

    const filteredMatches = activeTab === "value"
        ? matches.filter(m => m.prediction?.value_bet)
        : matches

    // Group by league
    const byLeague = {}
    for (const m of filteredMatches) {
        const league = m.league_name || "Autre"
        if (!byLeague[league]) byLeague[league] = []
        byLeague[league].push(m)
    }
    const leagueOrder = Object.keys(byLeague).sort()

    const totalAnalyzed = matches.filter(m => m.prediction).length
    const totalValue = matches.filter(m => m.prediction?.value_bet).length

    return (
        <div className="space-y-5 pb-12">
            {/* Header strip */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                {/* Left: Stats */}
                <div className="flex items-center gap-3">
                    <div className="flex items-baseline gap-1.5">
                        <span className="text-2xl font-black tabular-nums">{filteredMatches.length}</span>
                        <span className="text-sm text-muted-foreground font-medium">matchs</span>
                    </div>
                    <div className="w-px h-5 bg-border" />
                    <div className="flex items-baseline gap-1.5">
                        <span className="text-lg font-bold tabular-nums text-primary">{totalAnalyzed}</span>
                        <span className="text-xs text-muted-foreground">analysés</span>
                    </div>
                    {totalValue > 0 && (
                        <>
                            <div className="w-px h-5 bg-border" />
                            <div className="flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                                <span className="text-lg font-bold tabular-nums text-emerald-400">{totalValue}</span>
                                <span className="text-xs text-muted-foreground">value</span>
                            </div>
                        </>
                    )}
                </div>

                {/* Right: Controls */}
                <div className="flex items-center gap-2">
                    {/* Filter tabs */}
                    <div className="flex p-0.5 rounded-lg bg-secondary/50 ring-1 ring-border/50">
                        <button
                            onClick={() => setActiveTab("all")}
                            className={cn(
                                "px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200",
                                activeTab === "all"
                                    ? "bg-card text-foreground shadow-sm"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            Tous
                        </button>
                        {isPremium && (
                            <button
                                onClick={() => setActiveTab("value")}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 flex items-center gap-1",
                                    activeTab === "value"
                                        ? "bg-card text-emerald-400 shadow-sm"
                                        : "text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <Sparkles className="w-3 h-3" />
                                Value
                            </button>
                        )}
                    </div>

                    {/* Date selector */}
                    <div className="flex items-center rounded-lg bg-secondary/50 ring-1 ring-border/50 overflow-hidden">
                        <button
                            onClick={() => setDate(yesterday)}
                            className="p-2 hover:bg-accent/50 transition-colors text-muted-foreground hover:text-foreground"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <input
                            type="date"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                            className="bg-transparent border-none text-xs font-semibold focus:ring-0 focus:outline-none px-1 w-28 text-center tabular-nums"
                        />
                        <button
                            onClick={() => setDate(tomorrow)}
                            className="p-2 hover:bg-accent/50 transition-colors text-muted-foreground hover:text-foreground"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Match list by league */}
            {
                loading ? (
                    <div className="flex flex-col items-center justify-center py-32 space-y-4">
                        <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                        <p className="text-muted-foreground text-xs animate-pulse">
                            Chargement des analyses...
                        </p>
                    </div>
                ) : leagueOrder.length > 0 ? (
                    <div className="space-y-3">
                        {leagueOrder.map(league => (
                            <LeagueSection
                                key={league}
                                leagueName={league}
                                matches={byLeague[league]}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-32 rounded-xl border border-dashed border-border/50 bg-card/30">
                        <Calendar className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
                        <h3 className="text-base font-semibold text-muted-foreground">Aucun match</h3>
                        <p className="text-xs text-muted-foreground/70 mt-1">
                            Essayez une autre date
                        </p>
                    </div>
                )
            }
        </div >
    )
}
