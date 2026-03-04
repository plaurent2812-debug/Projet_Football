import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
    Flame, BellRing, ShieldAlert, ChevronDown, ChevronUp,
    ChevronRight, Activity, Star, Trophy, Radio
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, fetchPerformance, fetchNews } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth, supabase } from "@/lib/auth"
import { useWatchlist } from "@/lib/useWatchlist"

/* ── Live Alert Banner ────────────────────────────────────────── */
function LiveAlertBanner({ alert }) {
    if (!alert) return null
    return (
        <div className="mx-3 mt-2 rounded border border-red-500/30 bg-red-500/5 p-3">
            <div className="flex items-start gap-2">
                <BellRing className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-[10px] font-bold text-red-500 uppercase bg-red-500/10 px-1.5 py-0.5 rounded">
                            🔥 Alerte Mi-Temps
                        </span>
                        <span className="text-xs font-bold">
                            {alert.fixtures?.home_team} vs {alert.fixtures?.away_team}
                        </span>
                    </div>
                    <p className="text-xs text-foreground/80">{alert.analysis_text}</p>
                    <p className="text-xs font-bold text-orange-500 mt-0.5">Pari: {alert.recommended_bet}</p>
                </div>
            </div>
        </div>
    )
}

/* ── Match Row (compact, reusable) ─────────────────────────────── */
function MatchRow({ match, sport = "football" }) {
    const navigate = useNavigate()
    const { isStarred, toggleMatch } = useWatchlist()
    const pred = match.prediction
    const isFinished = ["FT", "AET", "PEN", "Final", "FINAL", "OFF"].includes(match.status)
    const isLive = ["1H", "2H", "HT", "ET", "P", "LIVE", "1P", "2P", "3P", "OT", "SO"].includes(match.status)
    const homeGoals = sport === "nhl" ? match.home_score : match.home_goals
    const awayGoals = sport === "nhl" ? match.away_score : match.away_goals
    const homeWon = isFinished && homeGoals > awayGoals
    const awayWon = isFinished && awayGoals > homeGoals
    const hasScore = isFinished || isLive
    const time = match.date ? new Date(match.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : "--:--"
    const isHot = pred?.confidence_score >= 7 && !isFinished
    const link = sport === "nhl" ? `/nhl/match/${match.api_fixture_id || match.id}` : `/football/match/${match.id}`

    return (
        <div className="fs-match-row" onClick={() => navigate(link)}>
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">{match.elapsed ? `${match.elapsed}'` : "LIVE"}</span>
                ) : isFinished ? (
                    <span className="text-[10px] font-semibold text-emerald-500">FT</span>
                ) : (
                    <span>{time}</span>
                )}
            </div>

            <div className="fs-match-teams">
                <div className="flex-1 flex items-center gap-1.5 min-w-0 justify-end">
                    <span className={cn("fs-team-name text-right", homeWon && "winner")}>{match.home_team}</span>
                    {match.home_logo ? (
                        <img src={match.home_logo} alt="" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                            {match.home_team?.charAt(0)}
                        </div>
                    )}
                </div>

                <div className={cn("fs-score-box", isLive && "live")}>
                    {hasScore ? (
                        <>
                            <span className={cn("score-val", homeWon && "winner")}>{homeGoals ?? 0}</span>
                            <span className={cn("score-val", awayWon && "winner")}>{awayGoals ?? 0}</span>
                        </>
                    ) : (
                        <>
                            <span className="score-val text-muted-foreground/40">-</span>
                            <span className="score-val text-muted-foreground/40">-</span>
                        </>
                    )}
                </div>

                <div className="flex-1 flex items-center gap-1.5 min-w-0">
                    {match.away_logo ? (
                        <img src={match.away_logo} alt="" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
                    ) : (
                        <div className="w-4 h-4 rounded-sm bg-primary/10 shrink-0 flex items-center justify-center text-[7px] font-bold text-primary">
                            {match.away_team?.charAt(0)}
                        </div>
                    )}
                    <span className={cn("fs-team-name", awayWon && "winner")}>{match.away_team}</span>
                </div>
            </div>

            {(!isFinished && pred) && (
                <div className="shrink-0 flex items-center gap-1 pl-1">
                    {isHot && <Flame className="w-3 h-3 text-orange-500 flame-badge" />}
                    {pred.recommended_bet && (
                        <span className="fs-pred-chip bg-primary/10 text-primary hidden sm:inline-flex truncate max-w-[80px]">
                            {pred.recommended_bet}
                        </span>
                    )}
                    {pred.confidence_score != null && (
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
            )}

            <button
                className="fs-star-btn"
                onClick={(e) => { e.stopPropagation(); toggleMatch(match.id) }}
            >
                <Star className={cn(
                    "w-3.5 h-3.5 transition-colors",
                    isStarred(match.id) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30 hover:text-amber-400"
                )} />
            </button>
        </div>
    )
}

/* ── League Section (collapsible) ──────────────────────────────── */
function LeagueSection({ leagueName, countryName, matches, sport }) {
    const [collapsed, setCollapsed] = useState(false)
    if (!matches?.length) return null

    const liveCount = matches.filter(m => ["1H", "2H", "HT", "ET", "P", "LIVE", "1P", "2P", "3P", "OT", "SO"].includes(m.status)).length

    return (
        <div>
            <div className="fs-league-header" onClick={() => setCollapsed(c => !c)}>
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
                <span className={cn("fs-league-count", liveCount > 0 && "has-live")}>{matches.length}</span>
                {collapsed
                    ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                    : <ChevronUp className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                }
            </div>
            {!collapsed && matches.map(m => <MatchRow key={m.id} match={m} sport={sport} />)}
        </div>
    )
}

/* ── News Row ──────────────────────────────────────────────────── */
function NewsRow({ item }) {
    return (
        <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 border-b border-border/20 last:border-0 hover:bg-accent/30 transition-colors group"
        >
            <span className="text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded shrink-0">
                {item.source}
            </span>
            <span className="text-xs font-medium text-foreground/80 truncate group-hover:text-primary transition-colors">
                {item.title}
            </span>
        </a>
    )
}

/* ═══════════════════════════════════════════════════════════
   Home Page (FlashScore-style — RICH content)
   ═══════════════════════════════════════════════════════════ */
export default function HomePage() {
    const navigate = useNavigate()
    const { isAdmin } = useAuth()
    const [todayFBMatches, setTodayFBMatches] = useState([])
    const [todayNHLMatches, setTodayNHLMatches] = useState([])
    const [vipSpots, setVipSpots] = useState([])
    const [perf, setPerf] = useState(null)
    const [news, setNews] = useState([])
    const [loading, setLoading] = useState(true)
    const [newsLoading, setNewsLoading] = useState(true)
    const [liveAlert, setLiveAlert] = useState(null)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)
        const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

        // Fetch football matches (today + tomorrow for VIP spots)
        const fetchFB = Promise.all([fetchPredictions(today), fetchPredictions(tomorrow)])
            .then(([r1, r2]) => {
                const todayMatches = (r1.matches || []).map(m => ({ ...m, sport: 'football' }))
                const tomorrowMatches = (r2.matches || []).map(m => ({ ...m, sport: 'football' }))
                setTodayFBMatches(todayMatches)

                // VIP = from today+tomorrow, high confidence or edge
                const all = [...todayMatches, ...tomorrowMatches]
                const vip = all.filter(m => {
                    if (["FT", "AET", "PEN"].includes(m.status) || !m.prediction) return false
                    const c = m.prediction.confidence_score || 0
                    const sj = m.prediction.stats_json || {}
                    const edge = m.prediction.kelly_edge || sj.kelly_edge || 0
                    return c >= 8 || edge >= 4
                }).sort((a, b) => (b.prediction?.confidence_score || 0) - (a.prediction?.confidence_score || 0))
                setVipSpots(vip)
            })
            .catch(console.error)

        // Fetch NHL matches (today)
        const start = new Date(today); start.setHours(0, 0, 0, 0)
        const end = new Date(today); end.setHours(23, 59, 59, 999)
        const fetchNHL = supabase
            .from('nhl_fixtures')
            .select('*')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .order('date', { ascending: true })
            .then(({ data }) => {
                setTodayNHLMatches((data || []).map(m => ({ ...m, sport: 'nhl' })))
            })
            .catch(console.error)

        Promise.all([fetchFB, fetchNHL]).finally(() => setLoading(false))

        fetchPerformance(30).then(setPerf).catch(() => { })
        fetchNews().then(r => setNews(r.news || [])).catch(() => { }).finally(() => setNewsLoading(false))

        // Live alert
        const thirtyMinsAgo = new Date(Date.now() - 30 * 60000).toISOString()
        supabase
            .from("live_alerts")
            .select("*, fixtures(home_team, away_team)")
            .gte("created_at", thirtyMinsAgo)
            .order("created_at", { ascending: false })
            .limit(1)
            .then(({ data }) => { if (data?.length > 0) setLiveAlert(data[0]) })
            .catch(console.error)
    }, [])

    // Build league groups for today's football
    const byLeague = {}
    todayFBMatches.forEach(m => {
        const key = m.league_id || "other"
        if (!byLeague[key]) byLeague[key] = { name: m.league_name || "Autres", id: key, countryName: m.country_name, matches: [] }
        byLeague[key].matches.push(m)
    })
    const leagues = Object.values(byLeague).sort((a, b) => {
        // Live leagues first, then alphabetical
        const aLive = a.matches.some(m => ["1H", "2H", "HT", "LIVE"].includes(m.status))
        const bLive = b.matches.some(m => ["1H", "2H", "HT", "LIVE"].includes(m.status))
        if (aLive && !bLive) return -1
        if (!aLive && bLive) return 1
        return a.name.localeCompare(b.name)
    })

    const liveMatches = [...todayFBMatches, ...todayNHLMatches].filter(m =>
        ["1H", "2H", "HT", "ET", "P", "LIVE", "1P", "2P", "3P", "OT", "SO"].includes(m.status)
    )
    const totalMatches = todayFBMatches.length + todayNHLMatches.length

    return (
        <div className="animate-fade-in-up pb-4">
            {/* Live Alert */}
            {liveAlert && <LiveAlertBanner alert={liveAlert} />}

            {/* Performance Stats (compact bar) */}
            <div className="fs-summary-bar flex-wrap">
                <Activity className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs font-bold">Performance 30j</span>
                <div className="flex items-center gap-3 ml-auto">
                    <div className="text-center">
                        <span className="text-xs font-black text-emerald-500 tabular-nums">{perf ? `${perf.accuracy_1x2}%` : "—"}</span>
                        <span className="text-[9px] text-muted-foreground ml-1">1X2</span>
                    </div>
                    <div className="text-center">
                        <span className="text-xs font-black text-blue-500 tabular-nums">{perf ? `${perf.accuracy_btts}%` : "—"}</span>
                        <span className="text-[9px] text-muted-foreground ml-1">BTTS</span>
                    </div>
                    <div className="text-center">
                        <span className="text-xs font-black text-purple-500 tabular-nums">{perf ? `${perf.accuracy_over_25}%` : "—"}</span>
                        <span className="text-[9px] text-muted-foreground ml-1">O2.5</span>
                    </div>
                    <span className="fs-summary-badge bg-muted text-muted-foreground">{totalMatches}</span>
                </div>
            </div>

            {/* ── LIVE Section (if live matches) ─────────────────── */}
            {liveMatches.length > 0 && (
                <div className="bg-card border-x border-b border-border/50">
                    <div className="fs-league-header bg-red-500/5 border-l-2 border-l-red-500">
                        <Radio className="w-4 h-4 text-red-500 animate-pulse shrink-0" />
                        <div className="fs-league-name text-red-500">EN DIRECT</div>
                        <span className="fs-summary-badge bg-red-500/15 text-red-500">{liveMatches.length}</span>
                    </div>
                    {liveMatches.map(m => <MatchRow key={m.id} match={m} sport={m.sport} />)}
                </div>
            )}

            {/* ── VIP Spots ──────────────────────────────────────── */}
            <div className="bg-card border-x border-b border-border/50">
                <div className="fs-league-header">
                    <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0" />
                    <div>
                        <div className="fs-league-name">🔥 Spots Premium</div>
                        <div className="fs-league-country">Confiance 8+ ou Edge fort</div>
                    </div>
                    <span className="fs-league-count">{vipSpots.length}</span>
                </div>

                {loading ? (
                    <div>
                        {[1, 2, 3].map(i => (
                            <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-border/20">
                                <Skeleton className="h-4 w-10" />
                                <Skeleton className="h-4 flex-1" />
                                <Skeleton className="h-5 w-12" />
                                <Skeleton className="h-4 flex-1" />
                            </div>
                        ))}
                    </div>
                ) : vipSpots.length > 0 ? (
                    vipSpots.slice(0, 5).map(m => <MatchRow key={m.id} match={m} sport={m.sport} />)
                ) : (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                        Aucun Spot VIP détecté pour le moment.
                    </div>
                )}
            </div>

            {/* Quick Navigation */}
            <div className="flex items-center gap-2 px-3 py-3 bg-card border-x border-b border-border/50">
                <button
                    onClick={() => navigate("/football")}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded bg-primary/10 text-primary text-xs font-bold hover:bg-primary/20 transition-colors"
                >
                    ⚽ Football <ChevronRight className="w-3 h-3" />
                </button>
                <button
                    onClick={() => navigate("/nhl")}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded bg-primary/10 text-primary text-xs font-bold hover:bg-primary/20 transition-colors"
                >
                    🏒 NHL <ChevronRight className="w-3 h-3" />
                </button>
                <button
                    onClick={() => navigate("/watchlist")}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded bg-amber-500/10 text-amber-500 text-xs font-bold hover:bg-amber-500/20 transition-colors"
                >
                    <Star className="w-3 h-3" /> Favoris
                </button>
            </div>

            {/* ── Today's Football (FULL, grouped by league) ────── */}
            <div className="bg-card border-x border-border/50 mt-2">
                <div className="fs-summary-bar border-b border-border/50">
                    <span className="text-sm">⚽</span>
                    <span className="text-xs font-bold">Football aujourd'hui</span>
                    <span className="fs-summary-badge bg-muted text-muted-foreground ml-auto">{todayFBMatches.length}</span>
                </div>

                {loading ? (
                    <div>
                        {[1, 2, 3, 4, 5, 6].map(i => (
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
                            countryName={league.countryName}
                            matches={league.matches}
                            sport="football"
                        />
                    ))
                ) : (
                    <div className="text-center py-8 text-xs text-muted-foreground">
                        Aucun match de football aujourd'hui.
                    </div>
                )}

                {todayFBMatches.length > 0 && (
                    <button
                        onClick={() => navigate("/football")}
                        className="w-full py-2.5 text-xs font-bold text-primary hover:bg-primary/5 transition-colors border-t border-border/30"
                    >
                        Voir tous les matchs Football →
                    </button>
                )}
            </div>

            {/* ── Today's NHL ────────────────────────────────────── */}
            {(loading || todayNHLMatches.length > 0) && (
                <div className="bg-card border-x border-b border-border/50">
                    <div className="fs-summary-bar border-b border-border/50">
                        <span className="text-sm">🏒</span>
                        <span className="text-xs font-bold">NHL aujourd'hui</span>
                        <span className="fs-summary-badge bg-muted text-muted-foreground ml-auto">{todayNHLMatches.length}</span>
                    </div>

                    {loading ? (
                        <div>
                            {[1, 2, 3].map(i => (
                                <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-border/20">
                                    <Skeleton className="h-4 w-10 shrink-0" />
                                    <Skeleton className="h-4 flex-1" />
                                    <Skeleton className="h-5 w-12" />
                                    <Skeleton className="h-4 flex-1" />
                                </div>
                            ))}
                        </div>
                    ) : (
                        todayNHLMatches.map(m => <MatchRow key={m.id} match={m} sport="nhl" />)
                    )}

                    {todayNHLMatches.length > 0 && (
                        <button
                            onClick={() => navigate("/nhl")}
                            className="w-full py-2.5 text-xs font-bold text-primary hover:bg-primary/5 transition-colors border-t border-border/30"
                        >
                            Voir tous les matchs NHL →
                        </button>
                    )}
                </div>
            )}

            {/* ── News Section ───────────────────────────────────── */}
            <div className="bg-card border-x border-b border-border/50 rounded-b mt-2">
                <div className="fs-league-header">
                    <span className="text-sm">📰</span>
                    <div className="fs-league-name">Actualités</div>
                    <span className="fs-league-count">{news.length}</span>
                </div>
                {newsLoading ? (
                    <div className="p-3 space-y-2">
                        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-5 w-full" />)}
                    </div>
                ) : news.length > 0 ? (
                    news.slice(0, 10).map((item, i) => <NewsRow key={i} item={item} />)
                ) : (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                        Actualités indisponibles
                    </div>
                )}
            </div>
        </div>
    )
}
