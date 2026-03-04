import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
    Flame, BellRing, ShieldAlert,
    ChevronRight, Activity, Star, Trophy, Radio,
    ArrowRight, Newspaper, TrendingUp
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, fetchPerformance, fetchNews } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth, supabase } from "@/lib/auth"

/* ── Live Alert Banner ────────────────────────────────────────── */
function LiveAlertBanner({ alert }) {
    if (!alert) return null
    return (
        <div className="mx-3 mt-4 mb-2 rounded border border-red-500/30 bg-red-500/5 p-3 animate-fade-in-up">
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

/* ── Match Row (compact, for VIP spots) ───────────────────────── */
function MatchRow({ match, sport = "football" }) {
    const navigate = useNavigate()
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
            className="flex items-center gap-2 px-3 py-2.5 border-b border-border/20 last:border-0 hover:bg-accent/30 transition-colors group"
        >
            <span className="text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded shrink-0">
                {item.source}
            </span>
            <span className="text-xs font-medium text-foreground/80 group-hover:text-primary transition-colors line-clamp-2">
                {item.title}
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/30 shrink-0 ml-auto group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
        </a>
    )
}

/* ═══════════════════════════════════════════════════════════
   Home Page (Landing / Dashboard Hybrid)
   ═══════════════════════════════════════════════════════════ */
export default function HomePage() {
    const navigate = useNavigate()
    const { isAdmin } = useAuth()
    const [fbCount, setFbCount] = useState(0)
    const [fbLiveCount, setFbLiveCount] = useState(0)
    const [nhlCount, setNhlCount] = useState(0)
    const [vipSpots, setVipSpots] = useState([])
    const [perf, setPerf] = useState(null)
    const [news, setNews] = useState([])
    const [loading, setLoading] = useState(true)
    const [newsLoading, setNewsLoading] = useState(true)
    const [liveAlert, setLiveAlert] = useState(null)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)
        const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

        // Fetch football matches
        const fetchFB = Promise.all([fetchPredictions(today), fetchPredictions(tomorrow)])
            .then(([r1, r2]) => {
                const todayMatches = (r1.matches || []).map(m => ({ ...m, sport: 'football' }))
                const tomorrowMatches = (r2.matches || []).map(m => ({ ...m, sport: 'football' }))

                setFbCount(todayMatches.length)
                setFbLiveCount(todayMatches.filter(m => ["1H", "2H", "HT", "LIVE"].includes(m.status)).length)

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

        // Fetch NHL matches
        const start = new Date(today); start.setHours(0, 0, 0, 0)
        const end = new Date(today); end.setHours(23, 59, 59, 999)
        const fetchNHL = supabase
            .from('nhl_fixtures')
            .select('id, status')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .then(({ data }) => {
                setNhlCount(data?.length || 0)
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

    return (
        <div className="animate-fade-in-up pb-8 max-w-3xl mx-auto">

            {/* ── Hero / Intro Section ──────────────────────────────── */}
            <div className="px-4 py-8 text-center bg-gradient-to-b from-primary/10 to-transparent border-b border-border/30">
                <div className="inline-flex items-center justify-center space-x-2 bg-primary/20 text-primary px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest mb-4">
                    <Activity className="w-3 h-3" />
                    <span>Mode FlashScore activé</span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-black text-foreground mb-2 tracking-tight">
                    Proba<span className="text-primary">Lab</span>
                </h1>
                <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                    L'intelligence artificielle au service de vos analyses sportives. Prédictions, Live Tracking et Value Bets en un coup d'œil.
                </p>
            </div>

            {/* Live Alert */}
            {liveAlert && <LiveAlertBanner alert={liveAlert} />}

            {/* ── Performance Stats (Trust building) ──────────────── */}
            <div className="mx-3 mt-4 mb-4 rounded border border-border/50 bg-card overflow-hidden">
                <div className="fs-summary-bar border-b border-border/50 bg-muted/20">
                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-bold uppercase tracking-wider">Performance Globale</span>
                    <span className="fs-summary-badge bg-muted text-muted-foreground ml-auto">30 Derniers Jours</span>
                </div>
                <div className="grid grid-cols-3 divide-x divide-border/30">
                    <div className="p-3 text-center bg-card hover:bg-accent/10 transition-colors">
                        <div className="text-xs text-muted-foreground font-semibold mb-1">1X2</div>
                        <div className="text-lg font-black text-emerald-500 tabular-nums">
                            {perf ? `${perf.accuracy_1x2}%` : "—"}
                        </div>
                    </div>
                    <div className="p-3 text-center bg-card hover:bg-accent/10 transition-colors">
                        <div className="text-xs text-muted-foreground font-semibold mb-1">BTTS</div>
                        <div className="text-lg font-black text-blue-500 tabular-nums">
                            {perf ? `${perf.accuracy_btts}%` : "—"}
                        </div>
                    </div>
                    <div className="p-3 text-center bg-card hover:bg-accent/10 transition-colors">
                        <div className="text-xs text-muted-foreground font-semibold mb-1">Over 2.5</div>
                        <div className="text-lg font-black text-purple-500 tabular-nums">
                            {perf ? `${perf.accuracy_over_25}%` : "—"}
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Main Shortcuts (Navigation) ─────────────────────── */}
            <div className="px-3 mb-6 grid grid-cols-2 gap-3">
                {/* Football Card */}
                <div
                    onClick={() => navigate("/football")}
                    className="relative overflow-hidden rounded-xl border border-border/50 bg-card p-4 cursor-pointer hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all group"
                >
                    <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 group-hover:scale-110 transition-all">
                        <span className="text-6xl">⚽</span>
                    </div>
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-black text-foreground uppercase tracking-wide">Football</span>
                            {fbLiveCount > 0 && (
                                <span className="flex h-2 w-2 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                                </span>
                            )}
                        </div>
                        <div className="text-2xl font-black text-primary tabular-nums mb-1">
                            {loading ? <Skeleton className="w-8 h-8" /> : fbCount}
                        </div>
                        <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-3">
                            Matchs Aujourd'hui
                        </div>
                        <div className="text-[10px] font-bold text-primary group-hover:translate-x-1 transition-transform flex items-center">
                            VOIR LES MATCHS <ArrowRight className="w-3 h-3 ml-1" />
                        </div>
                    </div>
                </div>

                {/* NHL Card */}
                <div
                    onClick={() => navigate("/nhl")}
                    className="relative overflow-hidden rounded-xl border border-border/50 bg-card p-4 cursor-pointer hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/5 transition-all group"
                >
                    <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 group-hover:scale-110 transition-all">
                        <span className="text-6xl">🏒</span>
                    </div>
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-black text-foreground uppercase tracking-wide">NHL</span>
                        </div>
                        <div className="text-2xl font-black text-blue-500 tabular-nums mb-1">
                            {loading ? <Skeleton className="w-8 h-8" /> : nhlCount}
                        </div>
                        <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider mb-3">
                            Matchs Aujourd'hui
                        </div>
                        <div className="text-[10px] font-bold text-blue-500 group-hover:translate-x-1 transition-transform flex items-center">
                            VOIR LES MATCHS <ArrowRight className="w-3 h-3 ml-1" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Quick Links Row */}
            <div className="px-3 mb-6 grid grid-cols-2 gap-2">
                <button
                    onClick={() => navigate("/watchlist")}
                    className="flex items-center justify-center gap-2 py-2.5 rounded-lg border border-border/50 bg-card text-foreground text-xs font-bold hover:bg-accent/50 hover:border-amber-500/50 transition-colors"
                >
                    <Star className="w-3.5 h-3.5 text-amber-500" /> Vos Favoris
                </button>
                <button
                    onClick={() => navigate("/premium")}
                    className="flex items-center justify-center gap-2 py-2.5 rounded-lg border border-border/50 bg-card text-foreground text-xs font-bold hover:bg-accent/50 hover:border-emerald-500/50 transition-colors"
                >
                    <Trophy className="w-3.5 h-3.5 text-emerald-500" /> Stats Premium
                </button>
            </div>

            {/* ── VIP Spots (Quick preview) ────────────────────────── */}
            <div className="mx-3 mb-6 bg-card border border-border/50 rounded-lg overflow-hidden shadow-sm">
                <div className="fs-league-header bg-amber-500/5 border-b border-border/50">
                    <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0" />
                    <div>
                        <div className="fs-league-name font-black">🔥 Spots Premium du Jour</div>
                        <div className="fs-league-country">Haute confiance & Edge identifié</div>
                    </div>
                    <span className="fs-league-count bg-amber-500/20 text-amber-600">{vipSpots.length}</span>
                </div>

                {loading ? (
                    <div>
                        {[1, 2, 3].map(i => (
                            <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-border/20">
                                <Skeleton className="h-4 w-10 shrink-0" />
                                <Skeleton className="h-4 flex-1" />
                                <Skeleton className="h-5 w-12" />
                            </div>
                        ))}
                    </div>
                ) : vipSpots.length > 0 ? (
                    <>
                        {vipSpots.slice(0, 5).map(m => <MatchRow key={m.id} match={m} sport={m.sport} />)}
                        {vipSpots.length > 5 && (
                            <button
                                onClick={() => navigate("/premium")}
                                className="w-full py-2.5 text-xs font-bold text-amber-600 bg-amber-500/5 hover:bg-amber-500/10 transition-colors border-t border-border/30 flex items-center justify-center"
                            >
                                Voir les {vipSpots.length} Spots VIP <ArrowRight className="w-3 h-3 ml-1" />
                            </button>
                        )}
                    </>
                ) : (
                    <div className="text-center py-6 text-xs text-muted-foreground flex flex-col items-center">
                        <Activity className="w-6 h-6 text-muted-foreground/30 mb-2" />
                        Aucun Spot VIP détecté pour l'instant.
                    </div>
                )}
            </div>

            {/* ── News Section ───────────────────────────────────── */}
            <div className="mx-3 bg-card border border-border/50 rounded-lg overflow-hidden shadow-sm">
                <div className="fs-league-header bg-accent/30 border-b border-border/50">
                    <Newspaper className="w-4 h-4 text-primary shrink-0" />
                    <div className="fs-league-name font-black">Actualités Sportives</div>
                    <span className="fs-league-count">{news.length}</span>
                </div>

                {newsLoading ? (
                    <div className="p-3 space-y-3">
                        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-5 w-full" />)}
                    </div>
                ) : news.length > 0 ? (
                    <div className="divide-y divide-border/20">
                        {news.slice(0, 10).map((item, i) => <NewsRow key={i} item={item} />)}
                    </div>
                ) : (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                        Actualités indisponibles actuellement.
                    </div>
                )}

                <button
                    onClick={() => {
                        window.scrollTo({ top: 0, behavior: 'smooth' })
                    }}
                    className="w-full py-2.5 text-[10px] font-bold text-muted-foreground hover:bg-accent/50 uppercase tracking-widest transition-colors flex items-center justify-center bg-muted/10"
                >
                    Haut de page
                </button>
            </div>
        </div>
    )
}
