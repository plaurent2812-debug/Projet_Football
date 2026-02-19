import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    ChevronLeft, ChevronRight, Flame, Clock,
    Trophy, Calendar, Filter, X, Activity, Target
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"

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
    const hasScore = isFinished || isLive

    return (
        <div
            className="match-card group flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-accent/40 border-b border-border/30 last:border-0 transition-colors"
            onClick={() => navigate(`/football/match/${match.id}`)}
        >
            {/* Time / Status */}
            <div className="w-11 shrink-0 text-center">
                {isLive ? (
                    <Badge variant="destructive" className="text-[10px] px-1.5 h-5 animate-pulse">LIVE</Badge>
                ) : isFinished ? (
                    <span className="text-[10px] font-bold text-muted-foreground">FIN</span>
                ) : (
                    <span className="text-xs font-bold tabular-nums text-foreground/80">{time}</span>
                )}
            </div>

            {/* Teams + Score — 3-column layout */}
            <div className="flex-1 min-w-0 flex items-center gap-2">
                {/* Home team */}
                <div className="flex-1 flex items-center gap-1.5 min-w-0 justify-end">
                    <span className={cn("text-sm truncate text-right", homeWon ? "font-bold" : "font-medium text-foreground/80")}>
                        {match.home_team}
                    </span>
                    {match.home_logo ? (
                        <img src={match.home_logo} alt="" className="w-5 h-5 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-5 h-5 rounded-full bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                    )}
                </div>

                {/* Score / VS */}
                <div className="shrink-0 w-16 text-center">
                    {hasScore ? (
                        <div className={cn(
                            "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-sm font-black tabular-nums",
                            isLive ? "bg-red-500/10 text-red-500" : "bg-muted/60 text-foreground"
                        )}>
                            <span className={homeWon ? "text-primary" : ""}>{match.home_goals ?? 0}</span>
                            <span className="text-muted-foreground/40 text-xs">-</span>
                            <span className={awayWon ? "text-primary" : ""}>{match.away_goals ?? 0}</span>
                        </div>
                    ) : (
                        <span className="text-xs font-bold text-muted-foreground/30">VS</span>
                    )}
                </div>

                {/* Away team */}
                <div className="flex-1 flex items-center gap-1.5 min-w-0">
                    {match.away_logo ? (
                        <img src={match.away_logo} alt="" className="w-5 h-5 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-5 h-5 rounded-full bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.away_team?.charAt(0)}
                        </div>
                    )}
                    <span className={cn("text-sm truncate", awayWon ? "font-bold" : "font-medium text-foreground/80")}>
                        {match.away_team}
                    </span>
                </div>
            </div>

            {/* Prediction info */}
            <div className="shrink-0 flex flex-col items-end gap-1 min-w-[72px]">
                {isFinished && pred ? (() => {
                    // Determine predicted outcome from 1X2 probas
                    const pH = pred.proba_home ?? 0
                    const pD = pred.proba_draw ?? 0
                    const pA = pred.proba_away ?? 0
                    const predicted = pH >= pD && pH >= pA ? "H" : pA >= pH && pA >= pD ? "A" : "D"
                    const hg = match.home_goals ?? 0
                    const ag = match.away_goals ?? 0
                    const actual = hg > ag ? "H" : ag > hg ? "A" : "D"
                    const correct = predicted === actual
                    return (
                        <Badge className={cn(
                            "text-[10px] h-5 px-1.5 border-0 gap-1",
                            correct
                                ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                                : "bg-red-500/10 text-red-500"
                        )}>
                            {correct ? "✅" : "❌"} {correct ? "Correct" : "Raté"}
                        </Badge>
                    )
                })() : (
                    <>
                        {isHot && (
                            <div className="flex items-center gap-1">
                                <Flame className="w-3.5 h-3.5 text-orange-500 flame-badge" />
                                <span className="text-[10px] font-bold text-orange-500">HOT</span>
                            </div>
                        )}
                        {!isFinished && pred?.recommended_bet && (
                            <span className="text-[10px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded truncate max-w-[72px]">
                                {pred.recommended_bet.split(' ').slice(0, 2).join(' ')}
                            </span>
                        )}
                        {pred?.confidence_score != null && !isFinished && (
                            <Badge className={cn(
                                "text-[10px] h-4 px-1.5 border-0",
                                pred.confidence_score >= 8 ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" :
                                    pred.confidence_score >= 6 ? "bg-amber-500/15 text-amber-600 dark:text-amber-400" :
                                        "bg-muted text-muted-foreground"
                            )}>
                                {pred.confidence_score}/10
                            </Badge>
                        )}
                    </>
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
    const [minConfidence, setMinConfidence] = useState(0)
    const [marketFilter, setMarketFilter] = useState('all') // all, 1x2, btts, over

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

    // Filter matches
    const filteredMatches = matches.filter(m => {
        const pred = m.prediction
        const conf = pred?.confidence_score || 0
        if (conf < minConfidence) return false

        if (marketFilter !== 'all') {
            const bet = (pred?.recommended_bet || "").toLowerCase()
            if (marketFilter === '1x2' && !/victoire|match nul|vainqueur|1|2|n/.test(bet)) return false
            if (marketFilter === 'btts' && !/btts|les deux|both teams/.test(bet)) return false
            if (marketFilter === 'over' && !/over|plus de/.test(bet)) return false
        }
        return true
    })

    // Build league list from filtered matches
    const byLeague = {}
    filteredMatches.forEach(m => {
        const key = m.league_id || "other"
        if (!byLeague[key]) byLeague[key] = { name: m.league_name || "Autres", id: key, matches: [] }
        byLeague[key].matches.push(m)
    })

    // Sort leagues alphabetically
    const leagues = Object.values(byLeague)
        .sort((a, b) => a.name.localeCompare(b.name))

    // Apply sidebar league selection
    const displayedLeagues = selectedLeague
        ? leagues.filter(l => l.id === selectedLeague)
        : leagues

    const totalMatches = displayedLeagues.reduce((s, l) => s + l.matches.length, 0)
    const totalRaw = matches.length

    console.log("Dashboard Render:", { date, matches: matches.length, loading, leagues: leagues.length, displayed: displayedLeagues.length })

    return (
        <div className="flex gap-6">
            <LeagueSidebar
                leagues={leagues}
                selectedLeague={selectedLeague}
                onSelect={setSelectedLeague}
            />

            {/* Main content */}
            <div className="flex-1 min-w-0">
                {/* Header controls: Title + Filters + Date */}
                <div className="flex flex-col gap-4 mb-4">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                        <div>
                            <h1 className="text-xl font-black tracking-tight">⚽ Football</h1>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {totalMatches} match{totalMatches !== 1 ? 's' : ''} affiché{totalMatches !== 1 ? 's' : ''}
                                {totalMatches !== totalRaw && <span className="opacity-60"> (sur {totalRaw})</span>}
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

                    {/* Filter Bar */}
                    <div className="flex flex-wrap items-center gap-2">
                        {/* Confidence Filter */}
                        <div className="relative">
                            <select
                                value={minConfidence}
                                onChange={(e) => setMinConfidence(Number(e.target.value))}
                                className="appearance-none pl-8 pr-8 py-2 bg-card border border-border/50 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-border transition-colors cursor-pointer"
                            >
                                <option value={0}>Toutes confiances</option>
                                <option value={6}>Confiance 6+</option>
                                <option value={7}>Confiance 7+ (Hot)</option>
                                <option value={8}>Confiance 8+ (Safe)</option>
                            </select>
                            <Activity className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
                            <ChevronRight className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rotate-90 text-muted-foreground/50 pointer-events-none" />
                        </div>

                        {/* Market Filter */}
                        <div className="relative">
                            <select
                                value={marketFilter}
                                onChange={(e) => setMarketFilter(e.target.value)}
                                className="appearance-none pl-8 pr-8 py-2 bg-card border border-border/50 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-border transition-colors cursor-pointer"
                            >
                                <option value="all">Tous les paris</option>
                                <option value="1x2">1X2 (Victoire)</option>
                                <option value="btts">Les deux marquent / BTTS</option>
                                <option value="over">Over / Under</option>
                            </select>
                            <Target className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
                            <ChevronRight className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rotate-90 text-muted-foreground/50 pointer-events-none" />
                        </div>

                        {/* Reset Filters */}
                        {(minConfidence > 0 || marketFilter !== 'all') && (
                            <button
                                onClick={() => { setMinConfidence(0); setMarketFilter('all'); }}
                                className="px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                            >
                                Réinitialiser
                            </button>
                        )}
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
                    ) : displayedLeagues.length > 0 ? (
                        displayedLeagues.map(league => (
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
