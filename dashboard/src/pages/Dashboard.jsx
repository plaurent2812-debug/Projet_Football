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
    const isLive = match.status === "1H" || match.status === "2H" || match.status === "HT"

    // Determine winner for visual weight
    const homeWon = isFinished && match.home_goals > match.away_goals
    const awayWon = isFinished && match.away_goals > match.home_goals

    return (
        <div
            onClick={() => navigate(`/match/${match.id}`)}
            className={cn(
                "group flex items-center gap-2 sm:gap-4 px-3 py-2 cursor-pointer h-10 sm:h-11", // Compact height
                "hover:bg-accent/40 active:bg-accent/60 transition-colors duration-150",
                "border-b border-border/30 last:border-b-0"
            )}
        >
            {/* Star (Favorite) */}
            <div
                className="shrink-0 text-muted-foreground/30 hover:text-amber-400 cursor-pointer transition-colors p-1"
                onClick={(e) => { e.stopPropagation(); /* toggle favorite */ }}
            >
                <Star className="w-4 h-4" />
            </div>

            {/* Time / Status */}
            <div className="w-12 shrink-0 text-center flex flex-col justify-center">
                {isFinished ? (
                    <span className="text-[10px] font-bold text-muted-foreground/70">Fin</span>
                ) : isLive ? (
                    <span className="text-[10px] font-bold text-red-500 animate-pulse">Live</span>
                ) : (
                    <span className="text-xs font-medium tabular-nums text-foreground/80">{time}</span>
                )}
            </div>

            {/* Teams & Score Container */}
            <div className="flex-1 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
                {/* Home Team */}
                <span className={cn(
                    "text-sm truncate text-right",
                    homeWon ? "font-bold text-foreground" : "font-medium text-foreground/80",
                    isFinished && !homeWon && "text-muted-foreground"
                )}>
                    {match.home_team}
                </span>

                {/* Score / VS */}
                <div className="w-12 text-center flex items-center justify-center font-bold tabular-nums text-sm bg-accent/20 rounded px-1 min-w-[40px]">
                    {isFinished || isLive ? (
                        <>
                            <span className={cn(homeWon && "text-primary")}>{match.home_goals}</span>
                            <span className="mx-1 opacity-40">-</span>
                            <span className={cn(awayWon && "text-primary")}>{match.away_goals}</span>
                        </>
                    ) : (
                        <span className="text-muted-foreground/40 text-[10px]">-</span>
                    )}
                </div>

                {/* Away Team */}
                <span className={cn(
                    "text-sm truncate text-left",
                    awayWon ? "font-bold text-foreground" : "font-medium text-foreground/80",
                    isFinished && !awayWon && "text-muted-foreground"
                )}>
                    {match.away_team}
                </span>
            </div>

            {/* Indicators (Value Bet, etc) */}
            <div className="w-20 shrink-0 flex justify-end">
                {pred?.value_bet && isPremium && (
                    <span className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                        VAL
                    </span>
                )}
            </div>
        </div>
    )
}

/* ── League section ────────────────────────────────────────── */
function LeagueSection({ leagueName, matches }) {
    return (
        <div className="rounded-lg border border-border/50 bg-card overflow-hidden shadow-sm mb-4">
            {/* League header */}
            <div className="px-3 py-2 flex items-center justify-between bg-muted/30 border-b border-border/30">
                <div className="flex items-center gap-2">
                    {/* Flag placeholder could go here */}
                    <span className="text-xs font-bold uppercase tracking-tight text-foreground/70">
                        {leagueName}
                    </span>
                </div>
                <span className="text-[10px] text-muted-foreground font-medium tabular-nums bg-background/50 px-1.5 rounded">
                    {matches.length}
                </span>
            </div>
            {/* Rows */}
            <div className="divide-y divide-border/10">
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
