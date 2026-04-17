import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    Trophy, ChevronDown, ChevronUp, Star,
    Activity
} from "lucide-react"
import { cn } from "@/lib/utils"
import { usePredictions } from "@/lib/queries"
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
                    <span className="text-xs font-semibold text-emerald-500">FT</span>
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
                        <img src={match.home_logo} alt="" role="presentation" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
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
                            <span className="text-xs font-medium text-muted-foreground/50">vs</span>
                        </>
                    )}
                </div>

                {/* Away */}
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
                        {/* Value Bet Badge */}
                        {match.best_value && (
                            <span className="text-xs font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 whitespace-nowrap" title={`${match.best_value.market} @ ${match.best_value.odds}`}>
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
                    <span className="fs-summary-badge bg-red-500/15 text-red-500 text-xs">{liveCount}</span>
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
    const [minConfidence, setMinConfidence] = useState(0)
    const [valueOnly, setValueOnly] = useState(false)
    const { isStarred, toggleMatch } = useWatchlist()

    const { data, isLoading: loading } = usePredictions(date)
    const matches = data?.matches ?? []

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
                            "ml-2 text-xs font-bold px-2 py-0.5 rounded-full border transition-colors",
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
                    <div className="text-center py-12">
                        <div className="text-4xl mb-3">⚽</div>
                        <h3 className="text-base font-bold text-foreground mb-1">Aucun match programme</h3>
                        <p className="text-sm text-muted-foreground">
                            Pas de rencontres pour cette date. Essayez un autre jour ou consultez les pronos du jour.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}
