import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
    Flame, BellRing, ShieldAlert,
    ChevronRight, Activity, Star, Trophy
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, fetchPerformance, fetchNews } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth, supabase } from "@/lib/auth"

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

/* ── VIP Match Row (compact) ──────────────────────────────────── */
function VIPMatchRow({ match }) {
    const navigate = useNavigate()
    const pred = match.prediction
    const time = match.date?.slice(11, 16) || "—"
    const isHot = pred?.confidence_score >= 7
    const link = match.sport === 'nhl' ? `/nhl/match/${match.id}` : `/football/match/${match.id}`
    const sj = pred?.stats_json || {}
    const edge = pred?.kelly_edge || sj.kelly_edge
    const sportEmoji = match.sport === 'nhl' ? '🏒' : '⚽'

    return (
        <div
            onClick={() => navigate(link)}
            className="fs-match-row group"
        >
            <div className="fs-match-time flex flex-col items-center">
                <span className="text-[9px] text-muted-foreground">{sportEmoji}</span>
                <span>{time}</span>
            </div>

            <div className="fs-match-teams">
                <span className="fs-team-name text-right">{match.home_team}</span>
                <div className="fs-score-box">
                    <span className="score-val text-muted-foreground/40">-</span>
                    <span className="score-val text-muted-foreground/40">-</span>
                </div>
                <span className="fs-team-name">{match.away_team}</span>
            </div>

            <div className="shrink-0 flex items-center gap-1 pl-1">
                {isHot && <Flame className="w-3 h-3 text-orange-500 flame-badge" />}
                {pred?.recommended_bet && (
                    <span className="fs-pred-chip bg-primary/10 text-primary hidden sm:inline-flex truncate max-w-[80px]">
                        {pred.recommended_bet}
                    </span>
                )}
                {edge >= 4 && (
                    <span className="fs-pred-chip bg-emerald-500/10 text-emerald-500">
                        +{edge}%
                    </span>
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

            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/20 group-hover:text-muted-foreground/50 shrink-0" />
        </div>
    )
}

/* ── News Row (compact, one-line) ──────────────────────────────── */
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
   Home Page (FlashScore-style)
   ═══════════════════════════════════════════════════════════ */
export default function HomePage() {
    const navigate = useNavigate()
    const { isAdmin } = useAuth()
    const [topMatches, setTopMatches] = useState([])
    const [totalCount, setTotalCount] = useState(0)
    const [perf, setPerf] = useState(null)
    const [news, setNews] = useState([])
    const [loading, setLoading] = useState(true)
    const [newsLoading, setNewsLoading] = useState(true)
    const [liveAlert, setLiveAlert] = useState(null)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)
        const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

        const fetchFB = Promise.all([fetchPredictions(today), fetchPredictions(tomorrow)])
            .then(([r1, r2]) => {
                const arr = [...(r1.matches || []), ...(r2.matches || [])]
                return arr.map(m => ({ ...m, sport: 'football' }))
            })

        const start = new Date(today); start.setHours(0, 0, 0, 0)
        const end = new Date(tomorrow); end.setHours(23, 59, 59, 999)
        const fetchNHL = supabase
            .from('nhl_fixtures')
            .select('*')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .then(({ data }) => (data || []).map(m => ({ ...m, sport: 'nhl' })))

        Promise.all([fetchFB, fetchNHL])
            .then(([fbMatches, nhlMatches]) => {
                const all = [...fbMatches, ...nhlMatches]
                setTotalCount(all.length)

                const vipSpots = all.filter(m => {
                    if (m.status === "FT" || !m.prediction) return false
                    const c = m.prediction.confidence_score || 0
                    const sj = m.prediction.stats_json || {}
                    const edge = m.prediction.kelly_edge || sj.kelly_edge || 0
                    return c >= 8 || edge >= 4
                }).sort((a, b) => (b.prediction?.confidence_score || 0) - (a.prediction?.confidence_score || 0))

                setTopMatches(vipSpots)
            })
            .catch(console.error)
            .finally(() => setLoading(false))

        fetchPerformance(30).then(setPerf).catch(() => { })
        fetchNews().then(r => setNews(r.news || [])).catch(() => { }).finally(() => setNewsLoading(false))

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
                    <span className="fs-summary-badge bg-muted text-muted-foreground">{totalCount}</span>
                </div>
            </div>

            {/* VIP Spots Section */}
            <div className="bg-card border-x border-border/50">
                <div className="fs-league-header">
                    <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0" />
                    <div>
                        <div className="fs-league-name">Spots Premium du jour</div>
                        <div className="fs-league-country">Confiance 8+ ou Edge fort</div>
                    </div>
                    <span className="fs-league-count">{topMatches.length}</span>
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
                ) : topMatches.length > 0 ? (
                    topMatches.map((m, i) => <VIPMatchRow key={i} match={m} />)
                ) : (
                    <div className="text-center py-10 text-xs text-muted-foreground">
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
                    ⚽ Football
                    <ChevronRight className="w-3 h-3" />
                </button>
                <button
                    onClick={() => navigate("/nhl")}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded bg-primary/10 text-primary text-xs font-bold hover:bg-primary/20 transition-colors"
                >
                    🏒 NHL
                    <ChevronRight className="w-3 h-3" />
                </button>
                <button
                    onClick={() => navigate("/watchlist")}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded bg-amber-500/10 text-amber-500 text-xs font-bold hover:bg-amber-500/20 transition-colors"
                >
                    <Star className="w-3 h-3" />
                    Favoris
                </button>
            </div>

            {/* News Section */}
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
                    news.slice(0, 8).map((item, i) => <NewsRow key={i} item={item} />)
                ) : (
                    <div className="text-center py-6 text-xs text-muted-foreground">
                        Actualités indisponibles
                    </div>
                )}
            </div>
        </div>
    )
}
