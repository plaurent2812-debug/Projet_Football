import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays } from "date-fns"
import { fr } from "date-fns/locale"
import { ChevronLeft, ChevronRight, Calendar, Flame, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { supabase } from "@/lib/auth"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

/* ── NHL Match Row ─────────────────────────────────────────── */
function NHLMatchRow({ match }) {
    const navigate = useNavigate()
    const time = match.date ? new Date(match.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : "--:--"
    const isFinished = match.status === "FT" || match.status === "Final"
    const isLive = ["1P", "2P", "3P", "OT", "SO", "LIVE"].includes(match.status)
    const homeWon = isFinished && match.home_goals > match.away_goals
    const awayWon = isFinished && match.away_goals > match.home_goals
    const isHot = match.confidence_score >= 7 && !isFinished

    return (
        <div
            className="match-card group flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-accent/40 border-b border-border/30 last:border-0 transition-colors"
            onClick={() => navigate(`/nhl/match/${match.api_fixture_id || match.id}`)}
        >
            {/* Time */}
            <div className="w-12 shrink-0 text-center">
                {isLive ? (
                    <Badge variant="destructive" className="text-[10px] px-1.5 h-5 animate-pulse">LIVE</Badge>
                ) : isFinished ? (
                    <span className="text-[10px] font-bold text-muted-foreground">FIN</span>
                ) : (
                    <span className="text-xs font-bold tabular-nums text-foreground/80">{time}</span>
                )}
            </div>

            {/* Teams */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                        <span className={cn("text-sm", homeWon ? "font-bold" : "font-medium text-foreground/80")}>
                            {match.home_team}
                        </span>
                    </div>
                    <span className={cn("text-sm font-bold tabular-nums shrink-0",
                        isLive ? "text-red-500" : homeWon ? "text-foreground" : "text-muted-foreground/50"
                    )}>
                        {match.home_goals ?? (isFinished ? "0" : "-")}
                    </span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-1">
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded bg-primary/10 border border-border/50 shrink-0 flex items-center justify-center text-[8px] font-bold text-primary">
                            {match.away_team?.charAt(0)}
                        </div>
                        <span className={cn("text-sm", awayWon ? "font-bold" : "font-medium text-foreground/80")}>
                            {match.away_team}
                        </span>
                    </div>
                    <span className={cn("text-sm font-bold tabular-nums shrink-0",
                        isLive ? "text-red-500" : awayWon ? "text-foreground" : "text-muted-foreground/50"
                    )}>
                        {match.away_goals ?? (isFinished ? "0" : "-")}
                    </span>
                </div>
            </div>

            {/* Hot badge */}
            {isHot && (
                <div className="flex items-center gap-1 shrink-0">
                    <Flame className="w-3.5 h-3.5 text-orange-500 flame-badge" />
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

    useEffect(() => {
        setLoading(true)
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
            .finally(() => setLoading(false))
    }, [date])

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
