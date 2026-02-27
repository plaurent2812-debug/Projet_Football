import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays } from "date-fns"
import { fr } from "date-fns/locale"
import { ChevronLeft, ChevronRight, Calendar, Flame, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { supabase } from "@/lib/auth"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const LIVE_STATUSES = ["1P", "2P", "3P", "OT", "SO", "LIVE"]

const getMatchLabel = (match) => {
    if (match.status === "FT" || ["Final", "FINAL", "OFF"].includes(match.status)) return null

    const conf = match.confidence_score
    const recBet = match.recommended_bet?.toLowerCase() || ""
    const pred = match.predictions_json || {}
    const aiHome = pred.ai_home_factor || 1.0
    const aiAway = pred.ai_away_factor || 1.0

    // 1. Top Confidence
    if (conf >= 8) return { text: "Top Confiance", color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" }

    // 2. Avoid (Low confidence)
    if (conf != null && conf < 5) return { text: "À éviter", color: "bg-red-500/10 text-red-600 dark:text-red-400" }

    // 3. Offensive / Open Game
    if (aiHome > 1.2 || aiAway > 1.2 || recBet.includes("over") || recBet.includes("+")) {
        return { text: "Match Offensif", color: "bg-orange-500/10 text-orange-600 dark:text-orange-400" }
    }

    // 4. Defensive / Under
    if (aiHome < 0.8 || aiAway < 0.8 || recBet.includes("under") || recBet.includes("-")) {
        return { text: "Match Défensif", color: "bg-blue-500/10 text-blue-600 dark:text-blue-400" }
    }

    return null
}

/* ── NHL Match Row ─────────────────────────────────────────── */
function NHLMatchRow({ match }) {
    const navigate = useNavigate()
    const time = match.date ? new Date(match.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : "--:--"
    const isFinished = ["FT", "Final", "FINAL", "OFF"].includes(match.status)
    const isLive = LIVE_STATUSES.includes(match.status)
    const homeWon = isFinished && match.home_score > match.away_score
    const awayWon = isFinished && match.away_score > match.home_score
    const label = getMatchLabel(match)

    // Period label for live badge
    const periodLabel = {
        "1P": "1ère",
        "2P": "2ème",
        "3P": "3ème",
        "OT": "Prol.",
        "SO": "Tirs",
        "LIVE": "Live",
    }[match.status] || "Live"

    const hasScore = isFinished || isLive
    // Extract goals from stats_json
    const goals = match.stats_json?.goals || []
    const homeGoals = goals.filter(g => g.team?.toLowerCase().includes(match.home_team?.split(' ').pop()?.toLowerCase()))
    const awayGoals = goals.filter(g => g.team?.toLowerCase().includes(match.away_team?.split(' ').pop()?.toLowerCase()))

    return (
        <div
            className="match-card group flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-accent/40 border-b border-border/30 last:border-0 transition-colors"
            onClick={() => navigate(`/nhl/match/${match.api_fixture_id || match.id}`)}
        >
            {/* Time */}
            <div className="w-14 shrink-0 text-center">
                {isLive ? (
                    <Badge variant="destructive" className="text-[10px] px-1.5 h-5 animate-pulse">{periodLabel}</Badge>
                ) : isFinished ? (
                    <Badge className="text-[10px] px-1.5 h-5 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-0">Terminé</Badge>
                ) : (
                    <span className="text-xs font-bold tabular-nums text-foreground/80">{time}</span>
                )}
            </div>

            {/* Teams */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-5 h-5 rounded bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                        <div className="min-w-0">
                            <span className={cn("text-sm block", homeWon ? "font-bold" : "font-medium text-foreground/80")}>
                                {match.home_team}
                            </span>
                            {hasScore && homeGoals.length > 0 && (
                                <span className="text-[10px] text-muted-foreground block truncate">
                                    {homeGoals.map((g, i) => `⚽ ${g.player}${g.period ? ` (${g.period})` : ''}`).join(', ')}
                                </span>
                            )}
                        </div>
                    </div>
                    <span className={cn("text-sm font-bold tabular-nums shrink-0",
                        isLive ? "text-red-500" : homeWon ? "text-foreground" : "text-muted-foreground/50"
                    )}>
                        {match.home_score ?? (isFinished ? "0" : "-")}
                    </span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-1">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-5 h-5 rounded bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.away_team?.charAt(0)}
                        </div>
                        <div className="min-w-0">
                            <span className={cn("text-sm block", awayWon ? "font-bold" : "font-medium text-foreground/80")}>
                                {match.away_team}
                            </span>
                            {hasScore && awayGoals.length > 0 && (
                                <span className="text-[10px] text-muted-foreground block truncate">
                                    {awayGoals.map((g, i) => `⚽ ${g.player}${g.period ? ` (${g.period})` : ''}`).join(', ')}
                                </span>
                            )}
                        </div>
                    </div>
                    <span className={cn("text-sm font-bold tabular-nums shrink-0",
                        isLive ? "text-red-500" : awayWon ? "text-foreground" : "text-muted-foreground/50"
                    )}>
                        {match.away_score ?? (isFinished ? "0" : "-")}
                    </span>
                </div>
            </div>

            {/* Analytical Label */}
            {label && (
                <div className="hidden sm:flex shrink-0">
                    <Badge variant="outline" className={cn("text-[10px] px-2 py-0 h-5 border-0 font-bold", label.color)}>
                        {label.text}
                    </Badge>
                </div>
            )}

            <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground/60 shrink-0 transition-colors" />
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════
   NHL Page
   ═══════════════════════════════════════════════════════════ */
export default function NHLPage({ date, setDate }) {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)

    const fetchMatches = useCallback((showLoading = true) => {
        if (showLoading) setLoading(true)
        const start = new Date(date); start.setHours(0, 0, 0, 0)
        const end = new Date(date); end.setHours(23, 59, 59, 999)

        supabase
            .from('nhl_fixtures')
            .select('*')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .order('date', { ascending: true })
            .then(({ data }) => setMatches(data || []))
            .catch(console.error)
            .finally(() => { if (showLoading) setLoading(false) })
    }, [date])

    // Initial fetch when date changes
    useEffect(() => { fetchMatches(true) }, [fetchMatches])

    // Auto-refresh every 30s when any match is live
    useEffect(() => {
        const hasLive = matches.some(m => LIVE_STATUSES.includes(m.status))
        if (!hasLive) return
        const interval = setInterval(() => fetchMatches(false), 30_000)
        return () => clearInterval(interval)
    }, [matches, fetchMatches])

    const handleDateChange = (days) => {
        setDate(addDays(new Date(date), days).toISOString().slice(0, 10))
    }

    return (
        <div className="space-y-4 animate-fade-in-up">
            {/* Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                    <h1 className="text-xl font-black tracking-tight">🏒 NHL</h1>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {matches.length} match{matches.length !== 1 ? 's' : ''} ce jour
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

            {/* Matches */}
            <Card className="border-border/50 overflow-hidden">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-3">
                        <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                        <p className="text-xs text-muted-foreground animate-pulse">Chargement des matchs NHL...</p>
                    </div>
                ) : matches.length > 0 ? (
                    matches.map(m => <NHLMatchRow key={m.id} match={m} />)
                ) : (
                    <div className="flex flex-col items-center justify-center py-24 text-center">
                        <Calendar className="w-10 h-10 text-muted-foreground/30 mb-4" />
                        <h3 className="font-bold text-base">Aucun match NHL</h3>
                        <p className="text-sm text-muted-foreground mt-1">Essayez une autre date.</p>
                    </div>
                )}
            </Card>
        </div>
    )
}
