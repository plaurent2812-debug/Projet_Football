import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import { ChevronDown, ChevronUp, Star, Flame, Brain, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { supabase } from "@/lib/auth"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "@/lib/toast"
import { useWatchlist } from "@/lib/useWatchlist"
import { fetchNHLMetaAnalysis } from "@/lib/api"

const LIVE_STATUSES = ["1P", "2P", "3P", "OT", "SO", "LIVE"]

/* ── Date Bar ──────────────────────────────────────────────── */
function DateBar({ date, setDate }) {
    const scrollRef = useRef(null)
    const today = new Date()

    const days = Array.from({ length: 10 }, (_, i) => {
        const d = addDays(subDays(today, 5), i)
        const dateStr = format(d, 'yyyy-MM-dd')
        return {
            date: d,
            dateStr,
            dayName: format(d, "EEE", { locale: fr }).toUpperCase().replace('.', ''),
            dayNum: format(d, "dd.MM."),
            isToday: dateStr === format(today, 'yyyy-MM-dd'),
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

/* ── DeepThink Meta-Analysis Card ──────────────────────────── */
function MetaAnalysisCard({ date }) {
    const [analysis, setAnalysis] = useState(null)
    const [loading, setLoading] = useState(true)
    const [expanded, setExpanded] = useState(false)

    useEffect(() => {
        setLoading(true)
        setAnalysis(null)
        fetchNHLMetaAnalysis(date)
            .then(data => {
                if (data?.ok && data.analysis) {
                    setAnalysis(data.analysis)
                }
            })
            .catch(() => console.warn("Impossible de charger la méta-analyse NHL"))
            .finally(() => setLoading(false))
    }, [date])

    if (loading) {
        return (
            <div className="mx-2 mb-3 rounded-xl border border-purple-500/20 bg-gradient-to-br from-purple-500/5 via-card to-blue-500/5 p-4">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-purple-500/20 animate-pulse" />
                    <Skeleton className="h-4 w-40" />
                </div>
                <Skeleton className="h-3 w-full mb-2" />
                <Skeleton className="h-3 w-3/4 mb-2" />
                <Skeleton className="h-3 w-5/6" />
            </div>
        )
    }

    if (!analysis) return null

    // Parse the markdown-like analysis into sections
    const lines = analysis.split('\n').filter(l => l.trim())

    return (
        <div className="mx-2 mb-3 rounded-xl border border-purple-500/20 bg-gradient-to-br from-purple-500/5 via-card to-blue-500/5 overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center gap-2.5 px-4 py-3 hover:bg-purple-500/5 transition-colors"
            >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shrink-0">
                    <Brain className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 text-left">
                    <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold">Analyse Stratégique</span>
                        <Sparkles className="w-3 h-3 text-purple-400" />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        Méta-analyse de la soirée — spots à haute value
                    </p>
                </div>
                {expanded ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                )}
            </button>

            {/* Content */}
            {expanded && (
                <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-2 duration-300">
                    <div className="border-t border-purple-500/10 pt-3 space-y-2 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
                        {lines.map((line, i) => {
                            // Title lines (starts with # or 🧠)
                            if (line.startsWith('# ') || line.startsWith('🧠')) {
                                return null // Skip — header already shown
                            }
                            // Horizontal rule (---)
                            if (line.match(/^-{3,}$/)) {
                                return <hr key={i} className="border-purple-500/10 my-2" />
                            }
                            // Spot headers (## or ### or bold **)
                            if (line.startsWith('## ') || line.startsWith('### ')) {
                                return (
                                    <h4 key={i} className="text-xs font-bold text-foreground pt-2 first:pt-0">
                                        {line.replace(/^#+\s*/, '')}
                                    </h4>
                                )
                            }
                            // Spot headers without markdown (e.g. "Spot 1 :", "Spot 2 :")
                            if (line.match(/^Spot\s*\d/i)) {
                                return (
                                    <h4 key={i} className="text-xs font-bold text-foreground pt-2">
                                        {line}
                                    </h4>
                                )
                            }
                            // Stars / confidence
                            if (line.includes('⭐')) {
                                return (
                                    <p key={i} className="text-xs text-amber-400 font-medium">
                                        {line}
                                    </p>
                                )
                            }
                            // Bold text (** markers)
                            if (line.startsWith('**') || line.includes('**')) {
                                const parts = line.split(/\*\*/)
                                return (
                                    <p key={i} className="text-xs text-muted-foreground leading-relaxed">
                                        {parts.map((part, j) =>
                                            j % 2 === 1 ? (
                                                <strong key={j} className="text-foreground font-semibold">{part}</strong>
                                            ) : (
                                                <span key={j}>{part}</span>
                                            )
                                        )}
                                    </p>
                                )
                            }
                            // Bullet points
                            if (line.startsWith('- ') || line.startsWith('• ')) {
                                return (
                                    <p key={i} className="text-xs text-muted-foreground leading-relaxed pl-3 border-l-2 border-purple-500/20">
                                        {line.replace(/^[-•]\s*/, '')}
                                    </p>
                                )
                            }
                            // Numbered items (1. 2. 3.)
                            if (line.match(/^\d+\.\s/)) {
                                return (
                                    <p key={i} className="text-xs text-muted-foreground leading-relaxed pl-3 border-l-2 border-blue-500/20">
                                        {line}
                                    </p>
                                )
                            }
                            // Regular text
                            return (
                                <p key={i} className="text-xs text-muted-foreground leading-relaxed">
                                    {line}
                                </p>
                            )
                        })}
                    </div>
                </div>
            )}
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
        "1P": "1ère", "2P": "2ème", "3P": "3ème",
        "OT": "Prol.", "SO": "TaB", "LIVE": "Live",
    }[match.status] || (isLive ? "Live" : match.status)

    const conf = match.confidence_score
    const isHot = conf >= 7 && !isFinished

    // Predictions
    const probaOver55 = match.proba_over_55
    const homeWinProba = match.home_win_proba
    const awayWinProba = match.away_win_proba

    // Build mini prediction text
    let miniPred = null
    if (!isFinished && (homeWinProba || awayWinProba || probaOver55 != null)) {
        const parts = []
        if (homeWinProba && awayWinProba) {
            // Extract short team name: last word, or full name if single word
            const shortName = (name) => { const parts = (name || "").split(' '); return parts.length > 1 ? parts.pop() : name || "?" }
            const fav = homeWinProba >= awayWinProba
                ? `${shortName(match.home_team)} ${Math.round(homeWinProba * 100)}%`
                : `${shortName(match.away_team)} ${Math.round(awayWinProba * 100)}%`
            parts.push(fav)
        }
        if (probaOver55 != null) {
            parts.push(probaOver55 >= 50 ? `O5.5 ${Math.round(probaOver55)}%` : `U5.5 ${Math.round(100 - probaOver55)}%`)
        }
        if (parts.length > 0) miniPred = parts.join(' · ')
    }

    return (
        <div
            className={cn(
                "fs-match-row",
                isHot && "bg-amber-500/[0.03] hover:bg-amber-500/[0.07]"
            )}
            onClick={() => navigate(`/nhl/match/${match.api_fixture_id || match.id}`)}
        >
            {/* Time */}
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">{periodLabel}</span>
                ) : isFinished ? (
                    <span className="text-xs font-semibold text-emerald-500">FT</span>
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

            {/* Tags & Prediction */}
            <div className="shrink-0 flex flex-col items-end gap-0.5 pl-2 min-w-[100px]">
                <div className="flex items-center gap-1.5">
                    {/* Match Style Tags */}
                    {probaOver55 != null && probaOver55 >= 57 && (
                        <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full bg-orange-500/15 text-orange-500 whitespace-nowrap">
                            🔥 Offensif
                        </span>
                    )}
                    {probaOver55 != null && probaOver55 <= 47 && (
                        <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full bg-slate-500/20 text-slate-400 whitespace-nowrap">
                            🛡️ Défensif
                        </span>
                    )}

                    {/* Confidence Score */}
                    {(!isFinished && conf != null) && (
                        <div className="flex items-center gap-1 ml-0.5">
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
                </div>

                {/* Mini prediction */}
                {miniPred && (
                    <span className="text-xs text-muted-foreground/70 font-medium">
                        {miniPred}
                    </span>
                )}
            </div>

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

        // Check if selected date is today
        const now = new Date()
        const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
        const isToday = date === todayStr

        const query = supabase
            .from('nhl_fixtures')
            .select('*')

        if (isToday) {
            // Today: show matches from today + any currently live matches (even from yesterday evening)
            const yesterdayStart = new Date(start)
            yesterdayStart.setHours(yesterdayStart.getHours() - 12)
            query
                .gte('date', yesterdayStart.toISOString())
                .lte('date', end.toISOString())
        } else {
            query
                .gte('date', start.toISOString())
                .lte('date', end.toISOString())
        }

        query
            .order('date', { ascending: true })
            .then(({ data }) => {
                if (isToday) {
                    // For today: show live matches + today's matches (filter out finished yesterday matches)
                    const liveStatuses = new Set(LIVE_STATUSES)
                    const filtered = (data || []).filter(m => {
                        const matchDate = new Date(m.date)
                        const isInToday = matchDate >= start && matchDate <= end
                        const isLive = liveStatuses.has(m.status)
                        return isInToday || isLive
                    })
                    setMatches(filtered)
                } else {
                    setMatches(data || [])
                }
            })
            .catch(err => {
                console.error(err)
                if (showLoading) toast.error("Impossible de charger les matchs NHL")
            })
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

            {/* DeepThink Meta-Analysis */}
            <MetaAnalysisCard date={date} />

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
                    <div className="text-center py-12">
                        <div className="text-4xl mb-3">🏒</div>
                        <h3 className="text-base font-bold text-foreground mb-1">Aucun match NHL programme</h3>
                        <p className="text-sm text-muted-foreground">
                            Pas de rencontres pour cette date. Essayez un autre jour ou consultez les pronos du jour.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}

