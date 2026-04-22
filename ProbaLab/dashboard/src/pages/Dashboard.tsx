import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import { motion, AnimatePresence } from "framer-motion"
import {
    Trophy, ChevronDown, ChevronUp, Star,
    Activity, Zap, Filter
} from "lucide-react"
import { cn } from "@/lib/utils"
import { usePredictions } from "@/lib/queries"
import { Skeleton } from "@/components/ui/skeleton"
import { useWatchlist } from "@/lib/useWatchlist"

/* ── FlashScore Date Bar ───────────────────────────────────── */
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
                <motion.button
                    key={d.dateStr}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setDate(d.dateStr)}
                    className={cn("fs-date-item", d.dateStr === date && "active")}
                >
                    <span className="date-day">{d.isToday ? "AJD" : d.dayName}</span>
                    <span className="date-num">{d.dayNum}</span>
                </motion.button>
            ))}
        </div>
    )
}

/* ── Match Row (FlashScore-style) ──────────────────────────── */
function MatchRow({ match, isStarred, onToggleStar, index = 0 }) {
    const navigate = useNavigate()
    const pred = match.prediction
    const isFinished = ["FT", "AET", "PEN"].includes(match.status)
    const isLive = ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(match.status)
    const homeWon = isFinished && match.home_goals > match.away_goals
    const awayWon = isFinished && match.away_goals > match.home_goals
    const time = match.date?.slice(11, 16) || "--:--"
    const hasScore = isFinished || isLive
    const isValue = !!match.best_value

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: Math.min(index * 0.03, 0.4) }}
            className={cn("fs-match-row group relative", isValue && "has-value")}
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/football/match/${match.id}`)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(`/football/match/${match.id}`) } }}
        >
            {/* Value bet indicator strip */}
            {isValue && (
                <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-emerald-500/60 rounded-r" />
            )}

            {/* Time / Status */}
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">
                        {match.elapsed ? `${match.elapsed}'` : "LIVE"}
                    </span>
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
                    {match.home_logo ? (
                        <img src={match.home_logo} alt="" role="presentation" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                    )}
                </div>

                <div className={cn("fs-score-box", isLive && "live")}>
                    {hasScore ? (
                        <>
                            <span className={cn("score-val", homeWon && "winner")}>{match.home_goals ?? 0}</span>
                            <span className={cn("score-val", awayWon && "winner")}>{match.away_goals ?? 0}</span>
                        </>
                    ) : (
                        <span className="text-xs font-medium text-muted-foreground/50">vs</span>
                    )}
                </div>

                <div className="flex-1 flex items-center gap-1.5 min-w-0">
                    {match.away_logo ? (
                        <img src={match.away_logo} alt="" role="presentation" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
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
                        {isValue && (
                            <motion.span
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                className="text-xs font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 whitespace-nowrap"
                                title={`${match.best_value.market} @ ${match.best_value.odds}`}
                            >
                                VALUE +{match.best_value.edge.toFixed(0)}%
                            </motion.span>
                        )}
                    </>
                )}
            </div>

            {/* Star */}
            <motion.button
                whileTap={{ scale: 1.3 }}
                className="fs-star-btn"
                onClick={(e) => { e.stopPropagation(); onToggleStar(match.id) }}
            >
                <Star className={cn(
                    "w-3.5 h-3.5 transition-colors",
                    isStarred ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30 hover:text-amber-400"
                )} />
            </motion.button>
        </motion.div>
    )
}

/* ── League Section (collapsible) ──────────────────────────── */
function LeagueSection({ leagueName, leagueId, countryName, matches, isStarred, onToggleStar, sectionIndex = 0 }) {
    const [collapsed, setCollapsed] = useState(false)
    if (!matches?.length) return null

    const liveCount = matches.filter(m => ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(m.status)).length
    const valueCount = matches.filter(m => m.best_value).length

    return (
        <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: sectionIndex * 0.05, duration: 0.3 }}
        >
            <div
                className="fs-league-header cursor-pointer"
                onClick={() => setCollapsed(c => !c)}
            >
                <div className="w-5 h-4 rounded-sm bg-muted/60 flex items-center justify-center shrink-0">
                    <Trophy className="w-2.5 h-2.5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                    {countryName && <div className="fs-league-country">{countryName}</div>}
                    <div className="fs-league-name">{leagueName}</div>
                </div>
                {liveCount > 0 && (
                    <span className="fs-summary-badge bg-red-500/15 text-red-500 text-xs">{liveCount}</span>
                )}
                {valueCount > 0 && (
                    <span className="fs-summary-badge bg-emerald-500/15 text-emerald-500 text-xs">
                        <Zap className="w-2.5 h-2.5 inline mr-0.5" />{valueCount}
                    </span>
                )}
                <span className={cn("fs-league-count", liveCount > 0 && "has-live")}>
                    {matches.length}
                </span>
                <motion.div
                    animate={{ rotate: collapsed ? 0 : 180 }}
                    transition={{ duration: 0.2 }}
                >
                    <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                </motion.div>
            </div>
            <AnimatePresence initial={false}>
                {!collapsed && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.22, ease: "easeInOut" }}
                        style={{ overflow: "hidden" }}
                    >
                        {matches.map((m, i) => (
                            <MatchRow key={m.id} match={m} isStarred={isStarred(m.id)} onToggleStar={onToggleStar} index={i} />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}

/* ═══════════════════════════════════════════════════════════
   Football Dashboard Page
   ═══════════════════════════════════════════════════════════ */
export default function FootballPage({ date, setDate, selectedLeague, setSelectedLeague }) {
    const navigate = useNavigate()
    const [minConfidence, setMinConfidence] = useState(0)
    const [valueOnly, setValueOnly] = useState(false)
    const { isStarred, toggleMatch } = useWatchlist()

    const { data, isLoading: loading } = usePredictions(date)
    const matches = data?.matches ?? []

    const filteredMatches = matches.filter(m => {
        const conf = m.prediction?.confidence_score || 0
        if (conf < minConfidence) return false
        if (valueOnly && !m.is_value_bet) return false
        return true
    })
    const valueBetCount = matches.filter(m => m.is_value_bet).length

    const byLeague: Record<string, any> = {}
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
                    <motion.span
                        animate={{ opacity: [1, 0.5, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="fs-summary-badge bg-red-500/15 text-red-500"
                    >
                        {liveCount} LIVE
                    </motion.span>
                )}
                <span className="fs-summary-badge bg-muted text-muted-foreground ml-auto">{totalMatches}</span>

                {valueBetCount > 0 && (
                    <motion.button
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setValueOnly(v => !v)}
                        className={cn(
                            "ml-2 text-xs font-bold px-2 py-0.5 rounded-full border transition-colors",
                            valueOnly
                                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                : "bg-transparent text-muted-foreground border-border/50 hover:text-emerald-400"
                        )}
                    >
                        <Zap className="w-2.5 h-2.5 inline mr-0.5" />VALUE ({valueBetCount})
                    </motion.button>
                )}

                <select
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(Number(e.target.value))}
                    className="ml-2 text-xs font-semibold bg-transparent border border-border/50 rounded px-1.5 py-0.5 text-muted-foreground focus:outline-none cursor-pointer"
                >
                    <option value={0}>Tous</option>
                    <option value={6}>6+</option>
                    <option value={7}>7+ Hot</option>
                    <option value={8}>8+ Safe</option>
                </select>
            </div>

            {/* Content */}
            <div className="bg-card border-x border-b border-border/50 rounded-b">
                {loading ? (
                    <div>
                        {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: i * 0.04 }}
                                className="flex items-center gap-3 px-3 py-2.5 border-b border-border/20"
                            >
                                <Skeleton className="h-4 w-10 shrink-0" />
                                <Skeleton className="h-4 flex-1" />
                                <Skeleton className="h-5 w-12" />
                                <Skeleton className="h-4 flex-1" />
                            </motion.div>
                        ))}
                    </div>
                ) : leagues.length > 0 ? (
                    <AnimatePresence>
                        {leagues.map((league, i) => (
                            <LeagueSection
                                key={league.id}
                                leagueName={league.name}
                                leagueId={league.id}
                                countryName={league.countryName}
                                matches={league.matches}
                                isStarred={isStarred}
                                onToggleStar={toggleMatch}
                                sectionIndex={i}
                            />
                        ))}
                    </AnimatePresence>
                ) : (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center py-12"
                    >
                        <div className="text-4xl mb-3">⚽</div>
                        <h3 className="text-base font-bold text-foreground mb-1">Aucun match programmé</h3>
                        <p className="text-sm text-muted-foreground">
                            Pas de rencontres pour cette date. Essayez un autre jour ou consultez les pronos du jour.
                        </p>
                    </motion.div>
                )}
            </div>
        </div>
    )
}
