import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    Trophy, ChevronDown, ChevronUp, Star,
    Activity, Target, BrainCircuit, Brain, Sparkles
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, fetchFootballMetaAnalysis } from "@/lib/api"
import { getStatValue } from "@/lib/statsHelper"
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
        const dateStr = format(d, 'yyyy-MM-dd')
        return {
            date: d,
            dateStr,
            dayName: format(d, "EEE", { locale: fr }).toUpperCase().replace('.', ''),
            dayNum: format(d, "dd.MM."),
            isToday: dateStr === format(today, 'yyyy-MM-dd'),
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
    const [expanded, setExpanded] = useState(false)

    useEffect(() => {
        setLoading(true)
        setAnalysis(null)
        fetchFootballMetaAnalysis(date)
            .then(data => {
                if (data?.ok && data.analysis) {
                    setAnalysis(data.analysis)
                }
            })
            .catch(() => console.warn("Impossible de charger la méta-analyse football"))
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
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                        Méta-analyse de la journée — spots à haute value
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

/* ── Top 5 Markets Card ────────────────────────────────────── */
function TopMarketsCard({ matches }) {
    const [expanded, setExpanded] = useState(false)
    const [activeMarket, setActiveMarket] = useState('btts')
    const navigate = useNavigate()

    // Only NS matches with predictions (exclude finished/live)
    const nsMatches = (matches || []).filter(m =>
        m.status === "NS" && m.prediction
    )

    if (nsMatches.length === 0) return null

    const markets = [
        {
            key: 'btts',
            label: 'BTTS',
            emoji: '🔄',
            getProba: (m) => getStatValue(m.prediction, 'proba_btts'),
        },
        {
            key: 'over05',
            label: '+0.5',
            emoji: '⚽',
            getProba: (m) => getStatValue(m.prediction, 'proba_over_05'),
        },
        {
            key: 'over15',
            label: '+1.5',
            emoji: '🎯',
            getProba: (m) => getStatValue(m.prediction, 'proba_over_15'),
        },
        {
            key: 'over25',
            label: '+2.5',
            emoji: '🔥',
            getProba: (m) => getStatValue(m.prediction, 'proba_over_25'),
        },
        {
            key: 'over35',
            label: '+3.5',
            emoji: '💥',
            getProba: (m) => getStatValue(m.prediction, 'proba_over_35'),
        },
    ]

    const activeMarketData = markets.find(mk => mk.key === activeMarket)
    const ranked = nsMatches
        .map(m => ({
            match: m,
            proba: activeMarketData?.getProba(m) ?? null,
        }))
        .filter(r => r.proba != null && r.proba > 0)
        .sort((a, b) => b.proba - a.proba)
        .slice(0, 5)

    return (
        <div className="mx-2 mb-3 rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 via-card to-orange-500/5 overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center gap-2.5 px-4 py-3 hover:bg-amber-500/5 transition-colors"
            >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shrink-0">
                    <Trophy className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 text-left">
                    <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold">Top 5 Marchés</span>
                        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-500 uppercase tracking-wider">
                            Stats
                        </span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                        Meilleurs matchs par marché — BTTS, Over 0.5 à 3.5
                    </p>
                </div>
                {expanded ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                )}
            </button>

            {expanded && (
                <div className="px-4 pb-4 pt-1 space-y-3">
                    {/* Market tabs */}
                    <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
                        {markets.map(mk => (
                            <button
                                key={mk.key}
                                onClick={() => setActiveMarket(mk.key)}
                                className={cn(
                                    "flex items-center gap-1 px-3 py-1.5 rounded-full text-[11px] font-semibold whitespace-nowrap transition-all",
                                    activeMarket === mk.key
                                        ? "bg-amber-500/20 text-amber-500 shadow-sm"
                                        : "bg-muted/50 text-muted-foreground hover:bg-muted"
                                )}
                            >
                                <span>{mk.emoji}</span>
                                <span>{mk.label}</span>
                            </button>
                        ))}
                    </div>

                    {/* Ranked matches */}
                    <div className="space-y-1">
                        {ranked.length > 0 ? ranked.map((r, idx) => {
                            const m = r.match
                            return (
                                <div
                                    key={m.id}
                                    className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors"
                                    onClick={() => navigate(`/football/match/${m.id}`)}
                                >
                                    {/* Rank */}
                                    <span className={cn(
                                        "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0",
                                        idx === 0 ? "bg-amber-500/20 text-amber-500" :
                                            idx === 1 ? "bg-slate-300/20 text-slate-400" :
                                                idx === 2 ? "bg-orange-700/20 text-orange-600" :
                                                    "bg-muted text-muted-foreground"
                                    )}>
                                        {idx + 1}
                                    </span>

                                    {/* Teams */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-1 text-[11px] font-medium truncate">
                                            {m.home_logo && <img src={m.home_logo} alt="" className="w-3.5 h-3.5 object-contain" />}
                                            <span className="truncate">{m.home_team}</span>
                                            <span className="text-muted-foreground mx-0.5">-</span>
                                            {m.away_logo && <img src={m.away_logo} alt="" className="w-3.5 h-3.5 object-contain" />}
                                            <span className="truncate">{m.away_team}</span>
                                        </div>
                                        <span className="text-[9px] text-muted-foreground">{m.league_name}</span>
                                    </div>

                                    {/* Proba bar + value */}
                                    <div className="flex items-center gap-2 shrink-0">
                                        <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                                            <div
                                                className={cn(
                                                    "h-full rounded-full transition-all",
                                                    r.proba >= 75 ? "bg-emerald-500" :
                                                        r.proba >= 60 ? "bg-amber-500" :
                                                            "bg-orange-500"
                                                )}
                                                style={{ width: `${Math.min(r.proba, 100)}%` }}
                                            />
                                        </div>
                                        <span className={cn(
                                            "text-[11px] font-bold min-w-[32px] text-right",
                                            r.proba >= 75 ? "text-emerald-500" :
                                                r.proba >= 60 ? "text-amber-500" :
                                                    "text-orange-500"
                                        )}>
                                            {Math.round(r.proba)}%
                                        </span>
                                    </div>
                                </div>
                            )
                        }) : (
                            <p className="text-xs text-muted-foreground text-center py-4">
                                Aucune donnée disponible pour ce marché
                            </p>
                        )}
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
    const hasScore = isFinished || isLive

    return (
        <div
            className="fs-match-row"
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/football/match/${match.id}`)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(`/football/match/${match.id}`) } }}
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
                            <span className="text-[10px] font-medium text-muted-foreground/50">vs</span>
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
                        {/* Value Bet Badge */}
                        {match.best_value && (
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 whitespace-nowrap" title={`${match.best_value.market} @ ${match.best_value.odds}`}>
                                VALUE +{match.best_value.edge.toFixed(0)}%
                            </span>
                        )}

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
    const [valueOnly, setValueOnly] = useState(false)
    const { isStarred, toggleMatch } = useWatchlist()

    useEffect(() => {
        setLoading(true)
        fetchPredictions(date)
            .then(r => setMatches(r.matches || []))
            .catch(console.error)
            .finally(() => setLoading(false))

        // Auto-refresh every 30s for live matches (skip cache, only when tab visible)
        const interval = setInterval(() => {
            if (document.visibilityState === 'visible') {
                fetchPredictions(date, true)
                    .then(r => setMatches(r.matches || []))
                    .catch(console.error)
            }
        }, 30_000)

        return () => clearInterval(interval)
    }, [date])

    // Filter matches
    const filteredMatches = matches.filter(m => {
        const conf = m.prediction?.confidence_score || 0
        if (conf < minConfidence) return false
        if (valueOnly && !m.is_value_bet) return false
        return true
    })
    const valueBetCount = matches.filter(m => m.is_value_bet).length

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

                {/* Value bet filter */}
                {valueBetCount > 0 && (
                    <button
                        onClick={() => setValueOnly(v => !v)}
                        className={cn(
                            "ml-2 text-[10px] font-bold px-2 py-0.5 rounded-full border transition-colors",
                            valueOnly
                                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                : "bg-transparent text-muted-foreground border-border/50 hover:text-emerald-400"
                        )}
                    >
                        VALUE ({valueBetCount})
                    </button>
                )}

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

            {/* Top 5 Markets */}
            <TopMarketsCard matches={matches} />

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
