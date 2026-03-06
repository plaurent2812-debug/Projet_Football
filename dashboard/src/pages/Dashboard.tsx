import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    Flame, Trophy, ChevronDown, ChevronUp, Star,
    Activity, Target, BrainCircuit, Brain, Sparkles
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, fetchFootballMetaAnalysis } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useWatchlist } from "@/lib/useWatchlist"

/* ── FlashScore Date Bar ───────────────────────────────────── */
function DateBar({ date, setDate }) {
    const scrollRef = useRef(null)
    const today = new Date()

    // Build 10 days: 5 past + today + 4 future
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

    // Scroll to active on mount
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
function FootballMetaAnalysisCard({ date }) {
    const [analysis, setAnalysis] = useState(null)
    const [loading, setLoading] = useState(true)
    const [expanded, setExpanded] = useState(true)

    useEffect(() => {
        setLoading(true)
        setAnalysis(null)
        fetchFootballMetaAnalysis(date)
            .then(data => {
                if (data?.ok && data.analysis) {
                    setAnalysis(data.analysis)
                }
            })
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [date])

    if (loading) {
        return (
            <div className="mx-2 mb-3 rounded-xl border border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 via-card to-blue-500/5 p-4">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/20 animate-pulse" />
                    <Skeleton className="h-4 w-40" />
                </div>
                <Skeleton className="h-3 w-full mb-2" />
                <Skeleton className="h-3 w-3/4 mb-2" />
                <Skeleton className="h-3 w-5/6" />
            </div>
        )
    }

    if (!analysis) return null

    const lines = analysis.split('\n').filter(l => l.trim())

    return (
        <div className="mx-2 mb-3 rounded-xl border border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 via-card to-blue-500/5 overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center gap-2.5 px-4 py-3 hover:bg-emerald-500/5 transition-colors"
            >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-500 flex items-center justify-center shrink-0">
                    <Brain className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 text-left">
                    <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold">Analyse Stratégique</span>
                        <Sparkles className="w-3 h-3 text-emerald-400" />
                        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 uppercase tracking-wider">
                            DeepThink
                        </span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                        Méta-analyse IA de la journée — spots à haute value
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
                    <div className="border-t border-emerald-500/10 pt-3 space-y-2 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
                        {lines.map((line, i) => {
                            if (line.startsWith('# ') || line.startsWith('⚽ Analyse')) return null
                            if (line.match(/^-{3,}$/)) return <hr key={i} className="border-emerald-500/10 my-2" />
                            if (line.startsWith('## ') || line.startsWith('### ')) {
                                return <h4 key={i} className="text-xs font-bold text-foreground pt-2 first:pt-0">{line.replace(/^#+\s*/, '')}</h4>
                            }
                            if (line.match(/^Spot\s*\d/i)) {
                                return <h4 key={i} className="text-xs font-bold text-foreground pt-2">{line}</h4>
                            }
                            if (line.includes('⭐')) {
                                return <p key={i} className="text-xs text-amber-400 font-medium">{line}</p>
                            }
                            if (line.includes('**')) {
                                const parts = line.split(/\*\*/)
                                return (
                                    <p key={i} className="text-xs text-muted-foreground leading-relaxed">
                                        {parts.map((part, j) =>
                                            j % 2 === 1 ? <strong key={j} className="text-foreground font-semibold">{part}</strong> : <span key={j}>{part}</span>
                                        )}
                                    </p>
                                )
                            }
                            if (line.startsWith('- ') || line.startsWith('• ')) {
                                return <p key={i} className="text-xs text-muted-foreground leading-relaxed pl-3 border-l-2 border-emerald-500/20">{line.replace(/^[-•]\s*/, '')}</p>
                            }
                            if (line.match(/^\d+\.\s/)) {
                                return <p key={i} className="text-xs text-muted-foreground leading-relaxed pl-3 border-l-2 border-blue-500/20">{line}</p>
                            }
                            return <p key={i} className="text-xs text-muted-foreground leading-relaxed">{line}</p>
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}

/* ── Match Row (FlashScore-style) ──────────────────────────── */
function MatchRow({ match, isStarred, onToggleStar }) {
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
            className="fs-match-row"
            onClick={() => navigate(`/football/match/${match.id}`)}
        >
            {/* Time / Status */}
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">
                        {match.elapsed ? `${match.elapsed}'` : "LIVE"}
                    </span>
                ) : isFinished ? (
                    <span className="text-[10px] font-semibold text-emerald-500">FT</span>
                ) : (
                    <span>{time}</span>
                )}
            </div>

            {/* Teams + Score */}
            <div className="fs-match-teams">
                {/* Home */}
                <div className="flex-1 flex items-center gap-1.5 min-w-0 justify-end">
                    <span className={cn("fs-team-name text-right", homeWon && "winner")}>
                        {match.home_team}
                    </span>
                    {match.home_logo ? (
                        <img src={match.home_logo} alt="" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                    )}
                </div>

                {/* Score */}
                <div className={cn("fs-score-box", isLive && "live")}>
                    {hasScore ? (
                        <>
                            <span className={cn("score-val", homeWon && "winner")}>{match.home_goals ?? 0}</span>
                            <span className={cn("score-val", awayWon && "winner")}>{match.away_goals ?? 0}</span>
                        </>
                    ) : (
                        <>
                            <span className="score-val text-muted-foreground/40">-</span>
                            <span className="score-val text-muted-foreground/40">-</span>
                        </>
                    )}
                </div>

                {/* Away */}
                <div className="flex-1 flex items-center gap-1.5 min-w-0">
                    {match.away_logo ? (
                        <img src={match.away_logo} alt="" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                            {match.away_team?.charAt(0)}
                        </div>
                    )}
                    <span className={cn("fs-team-name", awayWon && "winner")}>
                        {match.away_team}
                    </span>
                </div>
            </div>

            {/* Prediction chips */}
            <div className="shrink-0 w-[110px] flex items-center gap-1.5 pl-2 justify-end">
                {(!isFinished && pred) && (
                    <>
                        {/* Match Style Tags */}
                        {(() => {
                            const probaOver25 = pred?.proba_over_25 ?? pred?.proba_over_2_5
                            if (probaOver25 != null && probaOver25 >= 58) {
                                return (
                                    <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-orange-500/15 text-orange-500 flex items-center gap-1">
                                        <Flame className="w-2.5 h-2.5" />
                                        Offensif
                                    </span>
                                )
                            }
                            if (probaOver25 != null && probaOver25 <= 42) {
                                return (
                                    <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-slate-500/20 text-slate-400">
                                        Défensif
                                    </span>
                                )
                            }
                            return null
                        })()}

                        <div className="flex items-center gap-1 ml-0.5">
                            {pred?.model_version === "meta_v2" && (
                                <div className="flex items-center gap-1 bg-primary/10 px-1.5 py-0.5 rounded text-[10px] font-bold text-primary mr-1">
                                    <BrainCircuit className="w-3 h-3" />
                                    V2
                                </div>
                            )}
                            {isHot && (
                                <Flame className="w-3 h-3 text-orange-500 flame-badge" />
                            )}
                            {pred?.confidence_score != null && (
                                <span className={cn(
                                    "fs-pred-chip",
                                    pred.confidence_score >= 8 ? "bg-emerald-500/15 text-emerald-500" :
                                        pred.confidence_score >= 6 ? "bg-amber-500/15 text-amber-500" :
                                            "bg-muted text-muted-foreground"
                                )}>
                                    {pred.confidence_score}/10
                                </span>
                            )}
                        </div>
                    </>
                )}
            </div>

            {/* Star */}
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

/* ── League Section (collapsible) ──────────────────────────── */
function LeagueSection({ leagueName, leagueId, countryName, matches, isStarred, onToggleStar }) {
    const [collapsed, setCollapsed] = useState(false)
    if (!matches?.length) return null

    const liveCount = matches.filter(m => ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(m.status)).length

    return (
        <div>
            <div
                className="fs-league-header"
                onClick={() => setCollapsed(c => !c)}
            >
                {/* Country flag placeholder */}
                <div className="w-5 h-4 rounded-sm bg-muted/60 flex items-center justify-center shrink-0">
                    <Trophy className="w-2.5 h-2.5 text-muted-foreground" />
                </div>
                <div className="min-w-0">
                    {countryName && <div className="fs-league-country">{countryName}</div>}
                    <div className="fs-league-name">{leagueName}</div>
                </div>
                {liveCount > 0 && (
                    <span className="fs-summary-badge bg-red-500/15 text-red-500 text-[10px]">{liveCount}</span>
                )}
                <span className={cn("fs-league-count", liveCount > 0 && "has-live")}>
                    {matches.length}
                </span>
                {collapsed
                    ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                    : <ChevronUp className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                }
            </div>
            {!collapsed && (
                <div>
                    {matches.map(m => (
                        <MatchRow key={m.id} match={m} isStarred={isStarred(m.id)} onToggleStar={onToggleStar} />
                    ))}
                </div>
            )}
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════
   Football Dashboard Page (FlashScore-style)
   ═══════════════════════════════════════════════════════════ */
export default function FootballPage({ date, setDate, selectedLeague, setSelectedLeague }) {
    const navigate = useNavigate()
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)
    const [minConfidence, setMinConfidence] = useState(0)
    const { isStarred, toggleMatch } = useWatchlist()

    useEffect(() => {
        setLoading(true)
        fetchPredictions(date)
            .then(r => setMatches(r.matches || []))
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [date])

    // Filter matches
    const filteredMatches = matches.filter(m => {
        const conf = m.prediction?.confidence_score || 0
        if (conf < minConfidence) return false
        return true
    })

    // Build league groups
    const byLeague = {}
    filteredMatches.forEach(m => {
        const key = m.league_id || "other"
        if (!byLeague[key]) byLeague[key] = { name: m.league_name || "Autres", id: key, countryName: m.country_name, matches: [] }
        byLeague[key].matches.push(m)
    })
    const leagues = Object.values(byLeague).sort((a, b) => a.name.localeCompare(b.name))

    const totalMatches = filteredMatches.length
    const liveCount = filteredMatches.filter(m => ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(m.status)).length

    return (
        <div className="animate-fade-in-up">
            {/* Date Bar */}
            <DateBar date={date} setDate={setDate} />

            {/* Summary bar */}
            <div className="fs-summary-bar">
                <span className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-muted-foreground" />
                    Tous les matchs
                </span>
                {liveCount > 0 && (
                    <span className="fs-summary-badge bg-red-500/15 text-red-500">{liveCount}</span>
                )}
                <span className="fs-summary-badge bg-muted text-muted-foreground ml-auto">{totalMatches}</span>

                {/* Compact confidence filter */}
                <select
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(Number(e.target.value))}
                    className="ml-2 text-[10px] font-semibold bg-transparent border border-border/50 rounded px-1.5 py-0.5 text-muted-foreground focus:outline-none cursor-pointer"
                >
                    <option value={0}>Tous</option>
                    <option value={6}>6+</option>
                    <option value={7}>7+ Hot</option>
                    <option value={8}>8+ Safe</option>
                </select>
            </div>

            {/* DeepThink Meta-Analysis */}
            <FootballMetaAnalysisCard date={date} />

            {/* Content */}
            <div className="bg-card border-x border-b border-border/50 rounded-b">
                {loading ? (
                    <div className="animate-in fade-in duration-500">
                        {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                            <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-border/20">
                                <Skeleton className="h-4 w-10 shrink-0" />
                                <Skeleton className="h-4 flex-1" />
                                <Skeleton className="h-5 w-12" />
                                <Skeleton className="h-4 flex-1" />
                            </div>
                        ))}
                    </div>
                ) : leagues.length > 0 ? (
                    leagues.map(league => (
                        <LeagueSection
                            key={league.id}
                            leagueName={league.name}
                            leagueId={league.id}
                            countryName={league.countryName}
                            matches={league.matches}
                            isStarred={isStarred}
                            onToggleStar={toggleMatch}
                        />
                    ))
                ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                            <span className="text-2xl">⚽</span>
                        </div>
                        <h3 className="font-bold text-sm mb-1">Aucun match programmé</h3>
                        <p className="text-xs text-muted-foreground max-w-[220px]">
                            Pas de rencontres pour cette date.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}
