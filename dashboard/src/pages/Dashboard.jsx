import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    ChevronLeft, ChevronRight, Flame, Clock,
    TrendingUp, Trophy, Calendar, Filter, X
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth"
import { fetchPredictions } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

/* ── Match Row ─────────────────────────────────────────────── */
function MatchRow({ match }) {
    const navigate = useNavigate()
    const pred = match.prediction
    const isFinished = ["FT", "AET", "PEN"].includes(match.status)
    const isLive = ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(match.status)
    const homeWon = isFinished && match.home_goals > match.away_goals
    const awayWon = isFinished && match.away_goals > match.home_goals
    const time = match.date?.slice(11, 16) || "--:--"
    const isHot = pred?.confidence_score >= 7 && !isFinished

    return (
        <div
            className="match-card group flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-accent/40 border-b border-border/30 last:border-0 transition-colors"
            onClick={() => navigate(`/football/match/${match.id}`)}
        >
            {/* Time / Status */}
            <div className="w-12 shrink-0 text-center">
                {isLive ? (
                    <Badge variant="destructive" className="text-[10px] px-1.5 h-5 animate-pulse">LIVE</Badge>
                ) : isFinished ? (
                    <span className="text-[10px] font-bold text-muted-foreground">FIN</span>
                ) : (
                    <span className="text-xs font-bold tabular-nums text-foreground/80">{time}</span>
                )}
            </div>

            {/* Teams + Score */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-5 h-5 rounded-full bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                        <span className={cn("text-sm truncate", homeWon ? "font-bold" : "font-medium text-foreground/80")}>
                            {match.home_team}
                        </span>
                    </div>
                    <span className={cn("text-sm font-bold tabular-nums min-w-[20px] text-center shrink-0",
                        isLive ? "text-red-500" : homeWon ? "text-foreground" : "text-muted-foreground/50"
                    )}>
                        {match.home_goals ?? (isFinished ? "0" : "-")}
                    </span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-1">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-5 h-5 rounded-full bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.away_team?.charAt(0)}
                        </div>
                        <span className={cn("text-sm truncate", awayWon ? "font-bold" : "font-medium text-foreground/80")}>
                            {match.away_team}
                        </span>
                    </div>
                    <span className={cn("text-sm font-bold tabular-nums min-w-[20px] text-center shrink-0",
                        isLive ? "text-red-500" : awayWon ? "text-foreground" : "text-muted-foreground/50"
                    )}>
                        {match.away_goals ?? (isFinished ? "0" : "-")}
                    </span>
                </div>
            </div>

            {/* Prediction info */}
            <div className="shrink-0 flex flex-col items-end gap-1 min-w-[80px]">
                {isHot && (
                    <div className="flex items-center gap-1">
                        <Flame className="w-3.5 h-3.5 text-orange-500 flame-badge" />
                        <span className="text-[10px] font-bold text-orange-500">HOT</span>
                    </div>
                )}
                {pred?.recommended_bet && (
                    <span className="text-[10px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded truncate max-w-[80px]">
                        {pred.recommended_bet.split(' ').slice(0, 2).join(' ')}
                    </span>
                )}
                {pred?.confidence_score != null && (
                    <Badge className={cn(
                        "text-[10px] h-4 px-1.5 border-0",
                        pred.confidence_score >= 8 ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" :
                            pred.confidence_score >= 6 ? "bg-amber-500/15 text-amber-600 dark:text-amber-400" :
                                "bg-muted text-muted-foreground"
                    )}>
                        {pred.confidence_score}/10
                    </Badge>
                )}
            </div>

            <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground/60 shrink-0 transition-colors" />
        </div>
    )
}

/* ── League Section ────────────────────────────────────────── */
function LeagueSection({ leagueName, leagueId, matches }) {
    if (!matches?.length) return null
    return (
        <div id={`league-${leagueId}`} className="mb-4">
            <div className="flex items-center gap-2.5 px-4 py-2.5 bg-accent/40 border-b border-border/30">
                <div className="w-6 h-6 rounded bg-card border border-border/50 flex items-center justify-center shadow-sm">
                    <Trophy className="w-3 h-3 text-muted-foreground" />
                </div>
                <span className="text-sm font-bold text-foreground">{leagueName}</span>
                <span className="text-xs text-muted-foreground ml-auto">{matches.length} match{matches.length > 1 ? 's' : ''}</span>
            </div>
            {matches.map(m => <MatchRow key={m.id} match={m} />)}
        </div>
    )
}

/* ── League Sidebar ────────────────────────────────────────── */
function LeagueSidebar({ leagues, selectedLeague, onSelect }) {
    return (
        <aside className="hidden lg:block w-56 shrink-0">
            <div className="sticky top-20 bg-card rounded-xl border border-border/50 overflow-hidden">
                <div className="px-3 py-2.5 border-b border-border/30 bg-accent/30">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Championnats</p>
                </div>
                <div className="p-1.5 space-y-0.5 max-h-[70vh] overflow-y-auto">
                    <button
                        onClick={() => onSelect(null)}
                        className={cn(
                            "w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                            !selectedLeague ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                        )}
                    >
                        <Filter className="w-3.5 h-3.5" />
                        Tous les matchs
                    </button>
                    {leagues.map(({ name, id, count }) => (
                        <button
                            key={id}
                            onClick={() => onSelect(id)}
                            className={cn(
                                "w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg text-sm font-medium transition-colors text-left",
                                selectedLeague === id ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
                            )}
                        >
                            <span className="truncate">{name}</span>
                            <span className="text-[10px] bg-muted rounded px-1 shrink-0">{count}</span>
                        </button>
                    ))}
                </div>
            </div>
        </aside>
    )
}

/* ═══════════════════════════════════════════════════════════
   Football Dashboard Page
   ═══════════════════════════════════════════════════════════ */
export default function FootballPage({ date, setDate, selectedLeague, setSelectedLeague }) {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetchPredictions(date)
            .then(r => setMatches(r.matches || []))
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [date])

    const handleDateChange = (days) => {
        setDate(addDays(new Date(date), days).toISOString().slice(0, 10))
    }

    // Build league list
    const byLeague = {}
    matches.forEach(m => {
        const key = m.league_id || "other"
        if (!byLeague[key]) byLeague[key] = { name: m.league_name || "Autres", id: key, matches: [] }
        byLeague[key].matches.push(m)
    })
    const leagues = Object.values(byLeague)
        .map(l => ({ ...l, count: l.matches.length }))
        .sort((a, b) => a.name.localeCompare(b.name))

    const filteredLeagues = selectedLeague
        ? leagues.filter(l => l.id === selectedLeague)
        : leagues

    const totalMatches = filteredLeagues.reduce((s, l) => s + l.matches.length, 0)

    return (
        <div className="flex gap-6 animate-fade-in-up">
            {/* Sidebar championnats */}
            <LeagueSidebar
                leagues={leagues}
                selectedLeague={selectedLeague}
                onSelect={setSelectedLeague}
            />

            {/* Main content */}
            <div className="flex-1 min-w-0">
                {/* Header controls */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
                    <div>
                        <h1 className="text-xl font-black tracking-tight">⚽ Football</h1>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            {totalMatches} match{totalMatches !== 1 ? 's' : ''} analysé{totalMatches !== 1 ? 's' : ''}
                        </p>
                    </div>

                    {/* Date navigation */}
                    <div className="flex items-center gap-1 bg-card border border-border/50 rounded-xl p-1 shadow-sm">
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg" onClick={() => handleDateChange(-1)}>
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <div className="flex items-center gap-2 px-3 min-w-[140px] justify-center">
                            <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                            <span className="text-sm font-bold capitalize">
                                {format(new Date(date), "EEE d MMM", { locale: fr })}
                            </span>
                        </div>
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg" onClick={() => handleDateChange(1)}>
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>
                </div>

                {/* Active filter indicator */}
                {selectedLeague && (
                    <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm">
                        <Filter className="w-3.5 h-3.5 text-primary" />
                        <span className="font-semibold text-primary">
                            {leagues.find(l => l.id === selectedLeague)?.name}
                        </span>
                        <button
                            onClick={() => setSelectedLeague(null)}
                            className="ml-auto p-0.5 rounded hover:bg-primary/10 transition-colors"
                        >
                            <X className="w-3.5 h-3.5 text-muted-foreground" />
                        </button>
                    </div>
                )}

                {/* Content */}
                <Card className="border-border/50 overflow-hidden">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-3">
                            <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                            <p className="text-xs text-muted-foreground animate-pulse">Chargement des matchs...</p>
                        </div>
                    ) : filteredLeagues.length > 0 ? (
                        filteredLeagues.map(league => (
                            <LeagueSection
                                key={league.id}
                                leagueName={league.name}
                                leagueId={league.id}
                                matches={league.matches}
                            />
                        ))
                    ) : (
                        <div className="flex flex-col items-center justify-center py-24 text-center">
                            <Calendar className="w-10 h-10 text-muted-foreground/30 mb-4" />
                            <h3 className="font-bold text-base">Aucun match trouvé</h3>
                            <p className="text-sm text-muted-foreground mt-1 max-w-[220px]">
                                Essayez une autre date ou supprimez le filtre.
                            </p>
                            <Button variant="outline" size="sm" className="mt-4" onClick={() => setSelectedLeague(null)}>
                                Voir tous les matchs
                            </Button>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    )
}
