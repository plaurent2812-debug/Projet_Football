import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import { ChevronDown, ChevronUp, Star, Flame } from "lucide-react"
import { cn } from "@/lib/utils"
import { supabase } from "@/lib/auth"
import { Skeleton } from "@/components/ui/skeleton"
import { useWatchlist } from "@/lib/useWatchlist"

const LIVE_STATUSES = ["1P", "2P", "3P", "OT", "SO", "LIVE"]

/* ── Date Bar ──────────────────────────────────────────────── */
function DateBar({ date, setDate }) {
    const scrollRef = useRef(null)
    const today = new Date()

    const days = Array.from({ length: 10 }, (_, i) => {
        const d = addDays(subDays(today, 5), i)
        return {
            date: d,
            dateStr: d.toISOString().slice(0, 10),
            dayName: format(d, "EEE", { locale: fr }).toUpperCase().replace('.', ''),
            dayNum: format(d, "dd.MM."),
            isToday: d.toISOString().slice(0, 10) === today.toISOString().slice(0, 10),
        }
    })

    useEffect(() => {
        const el = scrollRef.current?.querySelector('.active')
        if (el) el.scrollIntoView({ inline: 'center', block: 'nearest' })
    }, [])

    return (
        <div className="fs-date-bar" ref={scrollRef}>
            {days.map(d => (
                <button
                    key={d.dateStr}
                    onClick={() => setDate(d.dateStr)}
                    className={cn("fs-date-item", d.dateStr === date && "active")}
                >
                    <span className="date-day">{d.isToday ? "AJD" : d.dayName}</span>
                    <span className="date-num">{d.dayNum}</span>
                </button>
            ))}
        </div>
    )
}

/* ── NHL Match Row ─────────────────────────────────────────── */
function NHLMatchRow({ match, isStarred, onToggleStar }) {
    const navigate = useNavigate()
    const time = match.date ? new Date(match.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : "--:--"
    const isFinished = ["FT", "Final", "FINAL", "OFF"].includes(match.status)
    const isLive = LIVE_STATUSES.includes(match.status)
    const homeWon = isFinished && match.home_score > match.away_score
    const awayWon = isFinished && match.away_score > match.home_score
    const hasScore = isFinished || isLive

    const periodLabel = {
        "1P": "1P", "2P": "2P", "3P": "3P",
        "OT": "OT", "SO": "SO", "LIVE": "LIVE",
    }[match.status] || "Live"

    const conf = match.confidence_score
    const isHot = conf >= 7 && !isFinished

    return (
        <div
            className="fs-match-row"
            onClick={() => navigate(`/nhl/match/${match.api_fixture_id || match.id}`)}
        >
            {/* Time */}
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">{periodLabel}</span>
                ) : isFinished ? (
                    <span className="text-[10px] font-semibold text-emerald-500">FT</span>
                ) : (
                    <span>{time}</span>
                )}
            </div>

            {/* Teams + Score */}
            <div className="fs-match-teams">
                <div className="flex-1 flex items-center gap-1.5 min-w-0 justify-end">
                    <span className={cn("fs-team-name text-right", homeWon && "winner")}>
                        {match.home_team}
                    </span>
                    <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                        {match.home_team?.charAt(0)}
                    </div>
                </div>

                <div className={cn("fs-score-box", isLive && "live")}>
                    {hasScore ? (
                        <>
                            <span className={cn("score-val", homeWon && "winner")}>{match.home_score ?? 0}</span>
                            <span className={cn("score-val", awayWon && "winner")}>{match.away_score ?? 0}</span>
                        </>
                    ) : (
                        <>
                            <span className="score-val text-muted-foreground/40">-</span>
                            <span className="score-val text-muted-foreground/40">-</span>
                        </>
                    )}
                </div>

                <div className="flex-1 flex items-center gap-1.5 min-w-0">
                    <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                        {match.away_team?.charAt(0)}
                    </div>
                    <span className={cn("fs-team-name", awayWon && "winner")}>
                        {match.away_team}
                    </span>
                </div>
            </div>

            {/* Prediction */}
            {(!isFinished && conf != null) && (
                <div className="shrink-0 flex items-center gap-1 pl-1">
                    {isHot && <Flame className="w-3 h-3 text-orange-500 flame-badge" />}
                    <span className={cn(
                        "fs-pred-chip",
                        conf >= 8 ? "bg-emerald-500/15 text-emerald-500" :
                            conf >= 6 ? "bg-amber-500/15 text-amber-500" :
                                "bg-muted text-muted-foreground"
                    )}>
                        {conf}/10
                    </span>
                </div>
            )}

            <button
                className="fs-star-btn"
                onClick={(e) => { e.stopPropagation(); onToggleStar(match.id) }}
            >
                <Star className={cn(
                    "w-3.5 h-3.5 transition-colors",
                    isStarred ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30 hover:text-amber-400"
                )} />
            </button>
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════
   NHL Page (FlashScore-style)
   ═══════════════════════════════════════════════════════════ */
export default function NHLPage({ date, setDate }) {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)
    const { isStarred, toggleMatch } = useWatchlist()

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

    useEffect(() => { fetchMatches(true) }, [fetchMatches])

    // Auto-refresh when live
    useEffect(() => {
        const hasLive = matches.some(m => LIVE_STATUSES.includes(m.status))
        if (!hasLive) return
        const interval = setInterval(() => fetchMatches(false), 30_000)
        return () => clearInterval(interval)
    }, [matches, fetchMatches])

    const liveCount = matches.filter(m => LIVE_STATUSES.includes(m.status)).length

    return (
        <div className="animate-fade-in-up">
            {/* Date Bar */}
            <DateBar date={date} setDate={setDate} />

            {/* Summary */}
            <div className="fs-summary-bar">
                <span className="text-base">🏒</span>
                <span>NHL</span>
                {liveCount > 0 && (
                    <span className="fs-summary-badge bg-red-500/15 text-red-500">{liveCount}</span>
                )}
                <span className="fs-summary-badge bg-muted text-muted-foreground ml-auto">{matches.length}</span>
            </div>

            {/* Content */}
            <div className="bg-card border-x border-b border-border/50 rounded-b">
                {loading ? (
                    <div className="animate-in fade-in duration-500">
                        {[1, 2, 3, 4, 5].map(i => (
                            <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-border/20">
                                <Skeleton className="h-4 w-10 shrink-0" />
                                <Skeleton className="h-4 flex-1" />
                                <Skeleton className="h-5 w-12" />
                                <Skeleton className="h-4 flex-1" />
                            </div>
                        ))}
                    </div>
                ) : matches.length > 0 ? (
                    matches.map(m => (
                        <NHLMatchRow key={m.id} match={m} isStarred={isStarred(m.id)} onToggleStar={toggleMatch} />
                    ))
                ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                        <span className="text-3xl mb-3">🏒</span>
                        <h3 className="font-bold text-sm mb-1">Aucun match NHL</h3>
                        <p className="text-xs text-muted-foreground max-w-[220px]">
                            Pas de rencontres NHL pour cette date.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}
