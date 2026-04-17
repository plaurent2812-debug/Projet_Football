import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import {
    Flame, BellRing, ShieldAlert,
    ChevronRight, Activity, Star, Trophy,
    ArrowRight, TrendingUp, CheckCircle2, XCircle, Target
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, API_ROOT } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { useAuth, supabase } from "@/lib/auth"
import { NeuralCortex } from "@/components/visuals/NeuralCortex"
import { ValueBetExplainer } from "@/components/ValueBetExplainer"

/* ── Live Alert Banner ────────────────────────────────────────── */
function LiveAlertBanner({ alert }) {
    if (!alert) return null
    return (
        <div className="mx-3 mt-4 mb-2 rounded border border-red-500/30 bg-red-500/5 p-3 animate-fade-in-up">
            <div className="flex items-start gap-2">
                <BellRing className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-xs font-bold text-red-500 uppercase bg-red-500/10 px-1.5 py-0.5 rounded">
                            🔥 Alerte Mi-Temps
                        </span>
                        <span className="text-xs font-bold">
                            {alert.fixtures?.home_team} vs {alert.fixtures?.away_team}
                        </span>
                    </div>
                    <p className="text-xs text-foreground/80">{alert.analysis_text}</p>
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
        <button
            type="button"
            className="fs-match-row w-full text-left"
            onClick={() => navigate(link)}
            aria-label={`${match.home_team} vs ${match.away_team}`}
        >
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">{match.elapsed ? `${match.elapsed}'` : "LIVE"}</span>
                ) : isFinished ? (
                    <span className="text-xs font-semibold text-emerald-500">FT</span>
                ) : (
                    <span>{time}</span>
                )}
            </div>

            <div className="fs-match-teams">
                <div className="flex-1 flex items-center gap-1.5 min-w-0 justify-end">
                    <span className={cn("fs-team-name text-right", homeWon && "winner")}>{match.home_team}</span>
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
                        <img src={match.away_logo} alt="" role="presentation" className="w-4 h-4 shrink-0 object-contain" loading="lazy" />
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
        </button>
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
    const [betStats, setBetStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [liveAlert, setLiveAlert] = useState(null)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)

        // Fetch football matches (today only)
        const fetchFB = fetchPredictions(today)
            .then((r1) => {
                const todayMatches = (r1.matches || []).map(m => ({ ...m, sport: 'football' }))

                setFbCount(todayMatches.length)
                setFbLiveCount(todayMatches.filter(m => ["1H", "2H", "HT", "LIVE"].includes(m.status)).length)

                // VIP = today, not finished, has prediction, sorted by confidence
                const upcoming = todayMatches.filter(m => {
                    if (["FT", "AET", "PEN"].includes(m.status) || !m.prediction) return false
                    return (m.prediction.confidence_score || 0) >= 1
                }).sort((a, b) => (b.prediction?.confidence_score || 0) - (a.prediction?.confidence_score || 0))
                // Show top 5 matches by confidence (always show something if matches exist)
                setVipSpots(upcoming.slice(0, 5))
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

        // Fetch bet stats (ROI, streak, etc.)
        fetch(`${API_ROOT}/api/best-bets/stats`)
            .then(r => r.json())
            .then(setBetStats)
            .catch(() => console.warn("Impossible de charger les stats de paris"))

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

    const g = betStats?.global || {}

    return (
        <div className="animate-fade-in-up pb-8 w-full mx-auto">

            {/* ── Hero (Neural Cortex) ───────────────────────────────── */}
            <div className="relative px-4 py-10 border-b border-primary/10 overflow-hidden">
                {/* Neural network background */}
                <NeuralCortex nodeCount={60} pulseSpeed={0.012} />

                {/* Content — centered */}
                <div className="relative z-10 text-center">
                    <h1 className="text-3xl sm:text-4xl font-black text-foreground mb-1 tracking-tighter flex justify-center">
                        <span className="logo-container !px-5 !py-1.5 !text-3xl sm:!text-4xl" style={{ boxShadow: '0 0 20px rgba(16,185,129,0.12), 0 0 4px rgba(16,185,129,0.08)' }}>
                            <svg className="logo-border" viewBox="0 0 280 64" preserveAspectRatio="none">
                                <defs><filter id="hero-blur"><feGaussianBlur stdDeviation="4"/></filter></defs>
                                <rect x="1" y="1" width="278" height="62" rx="10" ry="10" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary/30" />
                                <rect x="1" y="1" width="278" height="62" rx="10" ry="10" fill="none" stroke="currentColor" strokeWidth="6" strokeDasharray="50 630" strokeLinecap="round" className="text-primary/20 logo-energy" filter="url(#hero-blur)" />
                            </svg>
                            <span className="tracking-tighter">proba</span>
                            <span className="inline-block w-[2px] h-7 sm:h-8 bg-primary/70 mx-1.5" />
                            <span className="tracking-tighter text-primary">lab</span>
                        </span>
                    </h1>
                    <p className="text-[0.6rem] font-semibold text-primary/60 uppercase tracking-[0.2em] mb-3">
                        Smart Betting Assistant
                    </p>
                    <p className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed mb-5">
                        Nos experts, assist&eacute;s par l'IA, d&eacute;tectent les cotes sous-&eacute;valu&eacute;es en temps r&eacute;el.
                    </p>
                    <Link
                        to="/paris-du-soir"
                        className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all hover:scale-105 glow-value"
                    >
                        <Target className="w-4 h-4" />
                        Value Bets du jour
                    </Link>
                </div>
            </div>

            {/* ── Value Bets card + social proof counter ────────────── */}
            <div className="px-3 mt-4 space-y-3">
                <Link to="/paris-du-soir">
                    <Card className="border-primary/30 bg-primary/5 hover:bg-primary/10 transition-all cursor-pointer">
                        <CardContent className="p-5 flex items-center justify-between">
                            <div>
                                <h2 className="text-base font-bold flex items-center gap-2">
                                    <Target className="w-5 h-5 text-primary" />
                                    Value Bets du jour
                                </h2>
                                <p className="text-sm text-muted-foreground mt-1">
                                    Edges d&eacute;tect&eacute;s automatiquement — Football &amp; NHL
                                </p>
                            </div>
                            <ChevronRight className="w-5 h-5 text-muted-foreground" />
                        </CardContent>
                    </Card>
                </Link>

                {/* Social proof counter — volume only, never show bad metrics */}
                <div className="flex items-center justify-center gap-3 py-2">
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                        <span className="text-xs text-muted-foreground">
                            <strong className="text-foreground tabular-nums">
                                {betStats?.global?.total || "—"}
                            </strong> value bets analys&eacute;s ce mois
                        </span>
                    </div>
                    {betStats?.global?.roi_singles_pct > 0 && (
                        <>
                            <span className="text-border">&middot;</span>
                            <span className="text-xs text-muted-foreground">
                                <strong className="text-primary tabular-nums">
                                    +{betStats.global.roi_singles_pct}%
                                </strong> ROI
                            </span>
                        </>
                    )}
                </div>

                {/* Value Bet explainer */}
                <ValueBetExplainer />
            </div>

            {/* Live Alert */}
            {liveAlert && <LiveAlertBanner alert={liveAlert} />}

            {/* ── ROI + Streak (Trust building) ───────────────────── */}
            {(() => {
                const monthNames = ["Janvier", "F\u00e9vrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Ao\u00fbt", "Septembre", "Octobre", "Novembre", "D\u00e9cembre"]
                const currentMonth = monthNames[new Date().getMonth()]
                const vowels = ["A", "O"]
                const monthPrefix = vowels.includes(currentMonth.charAt(0)) ? "d'" : "de "
                const roiIsGood = (g.roi_singles_pct || 0) >= -2
                const bestOdds = betStats?.best_pick?.odds
                const maxStreak = betStats?.max_streak || 0

                return (
                    <div className="mx-3 mt-4 mb-4 rounded border border-border/50 bg-card overflow-hidden">
                        <div className="fs-summary-bar border-b border-border/50 bg-muted/20">
                            <TrendingUp className="w-4 h-4 text-emerald-500" />
                            <span className="text-xs font-bold uppercase tracking-wider">Bilan {monthPrefix}{currentMonth}</span>
                        </div>

                        {/* Main metrics — only show what builds trust */}
                        <div className={cn(
                            "grid divide-x divide-border/30",
                            (g.roi_singles_pct || 0) > 0 ? "grid-cols-3" : "grid-cols-2"
                        )}>
                            {/* ROI — only if positive */}
                            {(g.roi_singles_pct || 0) > 0 && (
                                <div className="p-3 text-center bg-card">
                                    <div className="text-xs text-muted-foreground font-semibold mb-1">ROI</div>
                                    <div className="text-lg font-black text-emerald-500 tabular-nums">
                                        +{g.roi_singles_pct}%
                                    </div>
                                </div>
                            )}
                            {/* Total picks analyzed */}
                            <div className="p-3 text-center bg-card">
                                <div className="text-xs text-muted-foreground font-semibold mb-1">Picks analys&eacute;s</div>
                                <div className="text-lg font-black text-foreground tabular-nums">
                                    {g.total != null ? g.total : "—"}
                                </div>
                            </div>
                            {/* Best win or max streak */}
                            <div className="p-3 text-center bg-card">
                                {maxStreak >= 3 ? (
                                    <>
                                        <div className="text-xs text-muted-foreground font-semibold mb-1">Meilleure s&eacute;rie</div>
                                        <div className="text-lg font-black text-primary tabular-nums">
                                            {maxStreak}W
                                        </div>
                                    </>
                                ) : bestOdds ? (
                                    <>
                                        <div className="text-xs text-muted-foreground font-semibold mb-1">Plus grosse cote</div>
                                        <div className="text-lg font-black text-amber-500 tabular-nums">
                                            @{bestOdds.toFixed(2)}
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div className="text-xs text-muted-foreground font-semibold mb-1">Edge moyen</div>
                                        <div className="text-lg font-black text-primary tabular-nums">—</div>
                                    </>
                                )}
                            </div>
                        </div>


                    </div>
                )
            })()}

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
                        <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider mb-3">
                            Matchs Aujourd'hui
                        </div>
                        <div className="text-xs font-bold text-primary group-hover:translate-x-1 transition-transform flex items-center">
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
                        <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider mb-3">
                            Matchs Aujourd'hui
                        </div>
                        <div className="text-xs font-bold text-blue-500 group-hover:translate-x-1 transition-transform flex items-center">
                            VOIR LES MATCHS <ArrowRight className="w-3 h-3 ml-1" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Quick Links (Segmented Style) */}
            <div className="px-4 mb-6">
                <div className="flex p-1 bg-muted/30 rounded-xl border border-border/50">
                    <button
                        onClick={() => navigate("/watchlist")}
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-foreground text-xs font-bold hover:bg-background/80 transition-all active:scale-[0.98]"
                    >
                        <Star className="w-3.5 h-3.5 text-amber-500" /> Vos Favoris
                    </button>
                    <div className="w-[1px] bg-border/30 my-2" />
                    <button
                        onClick={() => navigate("/premium")}
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-foreground text-xs font-bold hover:bg-background/80 transition-all active:scale-[0.98]"
                    >
                        <Trophy className="w-3.5 h-3.5 text-emerald-500" /> Stats Premium
                    </button>
                </div>
            </div>

            {/* ── VIP Spots (Quick preview) ────────────────────────── */}
            <div className="mx-3 mb-6 bg-card border border-border/50 rounded-lg overflow-hidden shadow-sm">
                <div className="fs-league-header bg-amber-500/5 border-b border-border/50">
                    <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0" />
                    <div>
                        <div className="fs-league-name font-black">⚡ Matchs du jour</div>
                        <div className="fs-league-country">Analyses ProbaLab par confiance</div>
                    </div>
                    {vipSpots.length > 0 && (
                        <span className="fs-league-count bg-amber-500/20 text-amber-600">{vipSpots.length}</span>
                    )}
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
                    <div className="p-4 space-y-4">
                        {/* Recent value bets results */}
                        {betStats?.last_10 && betStats.last_10.length > 0 && (
                            <div>
                                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                                    Derniers Value Bets
                                </p>
                                <div className="space-y-1.5">
                                    {betStats.last_10.slice(0, 5).map((bet: any, i: number) => (
                                        <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded-lg bg-muted/20 text-xs">
                                            <div className="flex items-center gap-2 min-w-0 flex-1">
                                                <span className={cn(
                                                    "w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
                                                    bet.result === "WIN" ? "bg-emerald-500/20 text-emerald-400" :
                                                    bet.result === "LOSS" ? "bg-red-500/20 text-red-400" :
                                                    "bg-muted text-muted-foreground"
                                                )}>
                                                    {bet.result === "WIN" ? "W" : bet.result === "LOSS" ? "L" : "·"}
                                                </span>
                                                <span className="truncate text-foreground/80">{bet.label || bet.bet_label}</span>
                                            </div>
                                            <span className="font-mono font-bold text-foreground/60 shrink-0 ml-2">
                                                @{(bet.odds || 0).toFixed(2)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* CTA to next matches */}
                        <div className="text-center pt-2">
                            <p className="text-xs text-muted-foreground mb-3">
                                Pas de match aujourd'hui — les prochaines analyses arrivent bient&ocirc;t.
                            </p>
                            <div className="flex gap-2 justify-center">
                                <Link to="/football" className="text-xs font-bold text-primary hover:underline">
                                    ⚽ Prochains matchs
                                </Link>
                                <span className="text-border">·</span>
                                <Link to="/nhl" className="text-xs font-bold text-primary hover:underline">
                                    🏒 NHL ce soir
                                </Link>
                            </div>
                        </div>
                    </div>
                )}
            </div>

        </div>
    )
}
