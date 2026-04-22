import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring } from "framer-motion"
import {
    Flame, BellRing, ShieldAlert,
    ChevronRight, Activity, Star, Trophy,
    ArrowRight, TrendingUp, Target, Zap,
    BarChart3, CircleDot, Timer
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, API_ROOT } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth, supabase } from "@/lib/auth"
import { NeuralCortex } from "@/components/visuals/NeuralCortex"
import { ValueBetExplainer } from "@/components/ValueBetExplainer"

/* ── Ticker tape ──────────────────────────────────────────────── */
const TICKER_ITEMS = [
    "Value Betting · Edge détecté en temps réel",
    "Dixon-Coles · XGBoost · Gemini AI",
    "ROI moyen +12% · Kelly Criterion",
    "8 ligues analysées · 50+ features",
    "Football · NHL · Value Bets",
]

function TickerTape() {
    return (
        <div className="overflow-hidden border-y border-primary/10 py-2 bg-primary/3 relative">
            <div className="absolute left-0 top-0 w-12 h-full z-10 bg-gradient-to-r from-background to-transparent" />
            <div className="absolute right-0 top-0 w-12 h-full z-10 bg-gradient-to-l from-background to-transparent" />
            <motion.div
                className="flex gap-12 whitespace-nowrap"
                animate={{ x: [0, -1200] }}
                transition={{ duration: 28, repeat: Infinity, ease: "linear", repeatType: "loop" }}
            >
                {[...TICKER_ITEMS, ...TICKER_ITEMS, ...TICKER_ITEMS].map((item, i) => (
                    <span key={i} className="text-[10px] font-bold tracking-[0.15em] uppercase text-primary/60 flex items-center gap-3">
                        <span className="w-1 h-1 rounded-full bg-primary/40 inline-block" />
                        {item}
                    </span>
                ))}
            </motion.div>
        </div>
    )
}

/* ── Live Alert Banner ────────────────────────────────────────── */
function LiveAlertBanner({ alert }) {
    if (!alert) return null
    return (
        <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-3 mt-4 mb-2 rounded-lg border border-red-500/30 bg-red-500/5 p-3 backdrop-blur-sm"
        >
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
        </motion.div>
    )
}

/* ── Match Row ────────────────────────────────────────────────── */
function MatchRow({ match, sport = "football", index = 0 }) {
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
    const conf = pred?.confidence_score || 0

    return (
        <motion.button
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.06, duration: 0.3 }}
            type="button"
            className="fs-match-row w-full text-left group relative overflow-hidden"
            onClick={() => navigate(link)}
            aria-label={`${match.home_team} vs ${match.away_team}`}
        >
            {isHot && (
                <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-amber-500/3 to-transparent pointer-events-none"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 3, repeat: Infinity }}
                />
            )}
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
                    {conf != null && (
                        <span className={cn(
                            "fs-pred-chip",
                            conf >= 8 ? "bg-emerald-500/15 text-emerald-500" :
                                conf >= 6 ? "bg-amber-500/15 text-amber-500" :
                                    "bg-muted text-muted-foreground"
                        )}>
                            {conf}/10
                        </span>
                    )}
                </div>
            )}
        </motion.button>
    )
}

/* ── Metric Card animé ────────────────────────────────────────── */
function MetricCard({ label, value, accent = "emerald", delay = 0 }) {
    const colors = {
        emerald: "text-emerald-400",
        amber: "text-amber-400",
        blue: "text-blue-400",
        primary: "text-primary",
    }
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, duration: 0.4 }}
            className="p-3 text-center bg-card border-r border-border/30 last:border-r-0"
        >
            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider mb-1">{label}</div>
            <div className={cn("text-xl font-black tabular-nums", colors[accent])}>{value}</div>
        </motion.div>
    )
}

/* ── Sport Nav Card ───────────────────────────────────────────── */
function SportCard({ emoji, label, count, accentClass, borderHover, shadowHover, onClick, loading }) {
    return (
        <motion.div
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={onClick}
            className={cn(
                "relative overflow-hidden rounded-xl border border-border/50 bg-card p-4 cursor-pointer transition-all group",
                borderHover, shadowHover
            )}
        >
            <motion.div
                className="absolute top-0 right-0 p-3 pointer-events-none"
                initial={{ opacity: 0.08 }}
                whileHover={{ opacity: 0.18, scale: 1.1 }}
                transition={{ duration: 0.3 }}
            >
                <span className="text-6xl">{emoji}</span>
            </motion.div>
            <div className="relative z-10">
                <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-black text-foreground uppercase tracking-wide">{label}</span>
                </div>
                <div className={cn("text-2xl font-black tabular-nums mb-1", accentClass)}>
                    {loading ? <Skeleton className="w-8 h-8" /> : count}
                </div>
                <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider mb-3">
                    Matchs Aujourd'hui
                </div>
                <div className={cn("text-xs font-bold flex items-center gap-1 transition-transform group-hover:translate-x-1", accentClass)}>
                    VOIR LES MATCHS <ArrowRight className="w-3 h-3" />
                </div>
            </div>
        </motion.div>
    )
}

/* ═══════════════════════════════════════════════════════════
   Hero Section
   ═══════════════════════════════════════════════════════════ */
function HeroSection({ fbCount, fbLiveCount, loading }) {
    const navigate = useNavigate()

    return (
        <div className="relative px-4 pt-8 pb-10 border-b border-primary/10 overflow-hidden">
            <NeuralCortex nodeCount={55} pulseSpeed={0.011} />

            {/* Ambient glow blobs */}
            <div className="absolute -top-20 -left-20 w-64 h-64 rounded-full bg-primary/5 blur-3xl pointer-events-none" />
            <div className="absolute -bottom-10 -right-10 w-48 h-48 rounded-full bg-amber-500/4 blur-3xl pointer-events-none" />

            <div className="relative z-10 text-center">
                {/* Eyebrow */}
                <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 mb-4"
                >
                    <motion.span
                        className="w-1.5 h-1.5 rounded-full bg-primary"
                        animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                    />
                    <span className="text-[10px] font-bold text-primary/80 uppercase tracking-[0.18em]">
                        Smart Betting Assistant
                    </span>
                </motion.div>

                {/* Logo title */}
                <motion.h1
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="text-3xl sm:text-4xl font-black text-foreground mb-1 tracking-tighter flex justify-center"
                >
                    <span className="logo-container !px-5 !py-1.5 !text-3xl sm:!text-4xl" style={{ boxShadow: '0 0 20px rgba(16,185,129,0.12), 0 0 4px rgba(16,185,129,0.08)' }}>
                        <svg className="logo-border" viewBox="0 0 280 64" preserveAspectRatio="none">
                            <defs><filter id="hero-blur"><feGaussianBlur stdDeviation="4" /></filter></defs>
                            <rect x="1" y="1" width="278" height="62" rx="10" ry="10" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary/30" />
                            <rect x="1" y="1" width="278" height="62" rx="10" ry="10" fill="none" stroke="currentColor" strokeWidth="6" strokeDasharray="50 630" strokeLinecap="round" className="text-primary/20 logo-energy" filter="url(#hero-blur)" />
                        </svg>
                        <span className="tracking-tighter">proba</span>
                        <span className="inline-block w-[2px] h-7 sm:h-8 bg-primary/70 mx-1.5" />
                        <span className="tracking-tighter text-primary">lab</span>
                    </span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.25 }}
                    className="text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed mt-3 mb-5"
                >
                    Nos algorithmes détectent les cotes sous-évaluées en temps réel — <span className="text-foreground font-semibold">Dixon-Coles · XGBoost · Gemini</span>
                </motion.p>

                {/* CTA buttons */}
                <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.35 }}
                    className="flex items-center justify-center gap-3 flex-wrap"
                >
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.97 }}>
                        <Link
                            to="/paris-du-soir"
                            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-colors glow-value"
                        >
                            <Target className="w-4 h-4" />
                            Value Bets du jour
                        </Link>
                    </motion.div>
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.97 }}>
                        <button
                            onClick={() => navigate("/football")}
                            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border/60 bg-card/60 text-sm font-bold hover:border-primary/40 transition-all backdrop-blur-sm"
                        >
                            <span>⚽</span>
                            {loading ? "..." : fbCount} matchs
                            {fbLiveCount > 0 && (
                                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                            )}
                        </button>
                    </motion.div>
                </motion.div>
            </div>
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════
   HomePage
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

        const fetchFB = fetchPredictions(today)
            .then((r1) => {
                const todayMatches = (r1.matches || []).map(m => ({ ...m, sport: 'football' }))
                setFbCount(todayMatches.length)
                setFbLiveCount(todayMatches.filter(m => ["1H", "2H", "HT", "LIVE"].includes(m.status)).length)
                const upcoming = todayMatches.filter(m => {
                    if (["FT", "AET", "PEN"].includes(m.status) || !m.prediction) return false
                    return (m.prediction.confidence_score || 0) >= 1
                }).sort((a, b) => (b.prediction?.confidence_score || 0) - (a.prediction?.confidence_score || 0))
                setVipSpots(upcoming.slice(0, 5))
            })
            .catch(console.error)

        const start = new Date(today); start.setHours(0, 0, 0, 0)
        const end = new Date(today); end.setHours(23, 59, 59, 999)
        const fetchNHL = supabase
            .from('nhl_fixtures')
            .select('id, status')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .then(({ data }) => { setNhlCount(data?.length || 0) })
            .catch(console.error)

        Promise.all([fetchFB, fetchNHL]).finally(() => setLoading(false))

        fetch(`${API_ROOT}/api/best-bets/stats`)
            .then(r => r.json())
            .then(setBetStats)
            .catch(() => { })

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
    const monthNames = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    const currentMonth = monthNames[new Date().getMonth()]
    const vowels = ["A", "O"]
    const monthPrefix = vowels.includes(currentMonth.charAt(0)) ? "d'" : "de "

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="pb-8 w-full mx-auto"
        >
            {/* Hero */}
            <HeroSection fbCount={fbCount} fbLiveCount={fbLiveCount} loading={loading} />

            {/* Ticker */}
            <TickerTape />

            {/* Live Alert */}
            {liveAlert && <LiveAlertBanner alert={liveAlert} />}

            {/* ── ROI Stats bar ─────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="mx-3 mt-4 mb-4 rounded-lg border border-border/50 bg-card overflow-hidden shadow-sm"
            >
                <div className="fs-summary-bar border-b border-border/50 bg-muted/20">
                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-bold uppercase tracking-wider">Bilan {monthPrefix}{currentMonth}</span>
                    <span className="ml-auto text-[10px] text-muted-foreground/60 font-mono uppercase tracking-wider">LIVE DATA</span>
                </div>
                <div className={cn(
                    "grid divide-x divide-border/30",
                    (g.roi_singles_pct || 0) > 0 ? "grid-cols-3" : "grid-cols-2"
                )}>
                    {(g.roi_singles_pct || 0) > 0 && (
                        <MetricCard label="ROI" value={`+${g.roi_singles_pct}%`} accent="emerald" delay={0.3} />
                    )}
                    <MetricCard label="Picks analysés" value={g.total ?? "—"} accent="primary" delay={0.35} />
                    <MetricCard
                        label={betStats?.max_streak >= 3 ? "Meilleure série" : "Plus grosse cote"}
                        value={betStats?.max_streak >= 3 ? `${betStats.max_streak}W` : betStats?.best_pick?.odds ? `@${betStats.best_pick.odds.toFixed(2)}` : "—"}
                        accent={betStats?.max_streak >= 3 ? "primary" : "amber"}
                        delay={0.4}
                    />
                </div>
            </motion.div>

            {/* ── Value Bets CTA ────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="px-3 mb-4"
            >
                <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                    <Link to="/paris-du-soir" className="block">
                        <div className="relative overflow-hidden rounded-xl border border-primary/30 bg-primary/5 p-4 hover:bg-primary/8 transition-all cursor-pointer group">
                            <motion.div
                                className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-transparent pointer-events-none"
                                animate={{ x: ["-100%", "200%"] }}
                                transition={{ duration: 4, repeat: Infinity, ease: "linear", repeatDelay: 3 }}
                            />
                            <div className="relative flex items-center justify-between">
                                <div>
                                    <h2 className="text-sm font-black flex items-center gap-2 mb-1">
                                        <Target className="w-4 h-4 text-primary" />
                                        Value Bets du jour
                                    </h2>
                                    <p className="text-xs text-muted-foreground">
                                        Edges détectés automatiquement — Football & NHL
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    {betStats?.global?.roi_singles_pct > 0 && (
                                        <span className="text-xs font-black text-emerald-400 tabular-nums bg-emerald-500/10 px-2 py-1 rounded-md">
                                            +{betStats.global.roi_singles_pct}% ROI
                                        </span>
                                    )}
                                    <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                                </div>
                            </div>
                        </div>
                    </Link>
                </motion.div>

                {/* Social proof */}
                {betStats?.global?.total && (
                    <div className="flex items-center justify-center gap-3 py-2 mt-1">
                        <motion.div
                            className="w-1.5 h-1.5 rounded-full bg-primary"
                            animate={{ scale: [1, 1.5, 1] }}
                            transition={{ duration: 2, repeat: Infinity }}
                        />
                        <span className="text-xs text-muted-foreground">
                            <strong className="text-foreground tabular-nums">{betStats.global.total}</strong> value bets analysés ce mois
                        </span>
                    </div>
                )}
            </motion.div>

            {/* ── Sport Cards ───────────────────────────────────────── */}
            <div className="px-3 mb-5 grid grid-cols-2 gap-3">
                <SportCard
                    emoji="⚽"
                    label="Football"
                    count={fbCount}
                    accentClass="text-primary"
                    borderHover="hover:border-primary/50"
                    shadowHover="hover:shadow-lg hover:shadow-primary/5"
                    onClick={() => navigate("/football")}
                    loading={loading}
                />
                <SportCard
                    emoji="🏒"
                    label="NHL"
                    count={nhlCount}
                    accentClass="text-blue-400"
                    borderHover="hover:border-blue-500/50"
                    shadowHover="hover:shadow-lg hover:shadow-blue-500/5"
                    onClick={() => navigate("/nhl")}
                    loading={loading}
                />
            </div>

            {/* ── Quick Links ───────────────────────────────────────── */}
            <div className="px-4 mb-5">
                <div className="flex p-1 bg-muted/30 rounded-xl border border-border/50">
                    <motion.button
                        whileTap={{ scale: 0.97 }}
                        onClick={() => navigate("/watchlist")}
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-foreground text-xs font-bold hover:bg-background/80 transition-all"
                    >
                        <Star className="w-3.5 h-3.5 text-amber-500" /> Vos Favoris
                    </motion.button>
                    <div className="w-[1px] bg-border/30 my-2" />
                    <motion.button
                        whileTap={{ scale: 0.97 }}
                        onClick={() => navigate("/premium")}
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-foreground text-xs font-bold hover:bg-background/80 transition-all"
                    >
                        <Trophy className="w-3.5 h-3.5 text-emerald-500" /> Stats Premium
                    </motion.button>
                </div>
            </div>

            {/* ── VIP Spots ─────────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="mx-3 mb-6 bg-card border border-border/50 rounded-lg overflow-hidden shadow-sm"
            >
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
                        <AnimatePresence>
                            {vipSpots.slice(0, 5).map((m, i) => (
                                <MatchRow key={m.id} match={m} sport={m.sport} index={i} />
                            ))}
                        </AnimatePresence>
                        {vipSpots.length > 5 && (
                            <motion.button
                                whileHover={{ backgroundColor: "rgba(245,158,11,0.08)" }}
                                onClick={() => navigate("/premium")}
                                className="w-full py-2.5 text-xs font-bold text-amber-600 bg-amber-500/5 transition-colors border-t border-border/30 flex items-center justify-center gap-1"
                            >
                                Voir les {vipSpots.length} Spots VIP <ArrowRight className="w-3 h-3" />
                            </motion.button>
                        )}
                    </>
                ) : (
                    <div className="p-4 space-y-4">
                        {betStats?.last_10 && betStats.last_10.length > 0 && (
                            <div>
                                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                                    Derniers Value Bets
                                </p>
                                <div className="space-y-1.5">
                                    {betStats.last_10.slice(0, 5).map((bet: any, i: number) => (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, x: -8 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            className="flex items-center justify-between py-1.5 px-2 rounded-lg bg-muted/20 text-xs"
                                        >
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
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div className="text-center pt-2">
                            <p className="text-xs text-muted-foreground mb-3">
                                Pas de match aujourd'hui — les prochaines analyses arrivent bientôt.
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
            </motion.div>

            {/* Value Bet explainer */}
            <div className="px-3">
                <ValueBetExplainer />
            </div>
        </motion.div>
    )
}
