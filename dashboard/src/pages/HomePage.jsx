import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
    Zap, ArrowRight, ChevronRight, Flame, Clock,
    TrendingUp, BarChart3, BrainCircuit, Target,
    Activity, Newspaper, ExternalLink, Trophy
} from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPredictions, fetchPerformance, fetchNews } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

/* ── Stat card ─────────────────────────────────────────────── */
function StatCard({ label, value, sub, color = "text-primary" }) {
    return (
        <div className="text-center p-4">
            <p className={cn("text-3xl font-black tabular-nums", color)}>{value}</p>
            <p className="text-sm font-semibold text-foreground mt-1">{label}</p>
            {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
        </div>
    )
}

/* ── Feature card ──────────────────────────────────────────── */
function FeatureCard({ icon: Icon, title, description, color }) {
    return (
        <div className="group relative rounded-xl border border-border/50 bg-card p-5 hover:border-primary/30 hover:shadow-md hover:shadow-primary/5 transition-all duration-300 glow-card">
            <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center mb-4", color || "bg-primary/10")}>
                <Icon className="w-5 h-5 text-primary" />
            </div>
            <h3 className="font-bold text-sm mb-1.5">{title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </div>
    )
}

/* ── Featured match card ───────────────────────────────────── */
function FeaturedMatchCard({ match }) {
    const navigate = useNavigate()
    const pred = match.prediction
    const time = match.date?.slice(11, 16) || "—"
    const isHot = pred?.confidence_score >= 7

    return (
        <div
            onClick={() => navigate(`/football/match/${match.id}`)}
            className="match-card group relative rounded-xl border border-border/50 bg-card p-4 cursor-pointer hover:border-primary/40 glow-card"
        >
            {/* Hot badge */}
            {isHot && (
                <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-orange-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
                    <Flame className="w-3.5 h-3.5 text-white flame-badge" />
                </div>
            )}

            {/* League & time */}
            <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider truncate max-w-[120px]">
                    {match.league_name || "Football"}
                </span>
                <div className="flex items-center gap-1 text-muted-foreground shrink-0">
                    <Clock className="w-3 h-3" />
                    <span className="text-xs font-medium">{time}</span>
                </div>
            </div>

            {/* Teams */}
            <div className="flex items-center justify-between gap-2 mb-3">
                <p className="font-bold text-sm leading-tight flex-1 text-center">{match.home_team}</p>
                <span className="text-xs font-bold text-muted-foreground/40 shrink-0">VS</span>
                <p className="font-bold text-sm leading-tight flex-1 text-center">{match.away_team}</p>
            </div>

            {/* Probas */}
            {pred && (
                <div className="flex items-center justify-between pt-3 border-t border-border/40">
                    <div className="flex gap-3">
                        {[
                            { label: "Dom", val: pred.proba_home },
                            { label: "Nul", val: pred.proba_draw },
                            { label: "Ext", val: pred.proba_away },
                        ].map(({ label, val }) => (
                            <div key={label} className="text-center">
                                <span className="text-[10px] text-muted-foreground block">{label}</span>
                                <span className="text-sm font-bold tabular-nums">{val ?? "—"}%</span>
                            </div>
                        ))}
                    </div>
                    {pred.confidence_score != null && (
                        <Badge className={cn(
                            "text-[10px] font-bold border-0",
                            pred.confidence_score >= 8 ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" :
                                pred.confidence_score >= 6 ? "bg-amber-500/15 text-amber-600 dark:text-amber-400" :
                                    "bg-muted text-muted-foreground"
                        )}>
                            {pred.confidence_score}/10
                        </Badge>
                    )}
                </div>
            )}
        </div>
    )
}

/* ── News card ─────────────────────────────────────────────── */
function NewsCard({ item }) {
    return (
        <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors border border-transparent hover:border-border/50"
        >
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                <Newspaper className="w-4 h-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                    {item.title}
                </p>
                <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                        {item.source}
                    </span>
                    {item.pub_date && (
                        <span className="text-[10px] text-muted-foreground truncate">{item.pub_date.slice(0, 16)}</span>
                    )}
                </div>
            </div>
            <ExternalLink className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-primary/60 transition-colors shrink-0 mt-1" />
        </a>
    )
}

/* ═══════════════════════════════════════════════════════════
   Home Page
   ═══════════════════════════════════════════════════════════ */
export default function HomePage() {
    const navigate = useNavigate()
    const [topMatches, setTopMatches] = useState([])
    const [totalCount, setTotalCount] = useState(0)
    const [perf, setPerf] = useState(null)
    const [news, setNews] = useState([])
    const [loading, setLoading] = useState(true)
    const [newsLoading, setNewsLoading] = useState(true)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)
        const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

        Promise.all([fetchPredictions(today), fetchPredictions(tomorrow)])
            .then(([r1, r2]) => {
                const all = [...(r1.matches || []), ...(r2.matches || [])]
                setTotalCount(all.length)
                const upcoming = all
                    .filter(m => m.prediction && m.status !== "FT")
                    .sort((a, b) => (b.prediction?.confidence_score || 0) - (a.prediction?.confidence_score || 0))
                    .slice(0, 4)
                setTopMatches(upcoming)
            })
            .catch(console.error)
            .finally(() => setLoading(false))

        fetchPerformance(30)
            .then(setPerf)
            .catch(() => { })

        fetchNews()
            .then(r => setNews(r.news || []))
            .catch(() => { })
            .finally(() => setNewsLoading(false))
    }, [])

    return (
        <div className="space-y-10 pb-12 animate-fade-in-up">

            {/* ── Hero ──────────────────────────────────────── */}
            <section className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-primary to-blue-700 dark:from-primary/90 dark:to-blue-900 p-8 sm:p-12 text-white shadow-xl shadow-primary/20">
                {/* Decorative circles */}
                <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-white/5 -translate-y-1/2 translate-x-1/2" />
                <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-white/5 translate-y-1/2 -translate-x-1/2" />

                <div className="relative max-w-2xl">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 backdrop-blur-sm mb-5 text-sm font-semibold">
                        <Zap className="w-3.5 h-3.5" />
                        Analyses sportives augmentées par l'IA
                    </div>
                    <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight leading-[1.1] mb-4">
                        Probabilités & analyses<br />
                        <span className="text-blue-200">Football & NHL</span>
                    </h1>
                    <p className="text-base sm:text-lg text-blue-100 leading-relaxed mb-8 max-w-lg">
                        Modèles statistiques avancés, machine learning et analyse IA combinés
                        pour des prédictions précises sur chaque match.
                    </p>
                    <div className="flex flex-wrap gap-3">
                        <button
                            onClick={() => navigate("/football")}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-primary font-bold text-sm hover:bg-blue-50 transition-colors shadow-lg"
                        >
                            ⚽ Matchs Football
                            <ArrowRight className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => navigate("/nhl")}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/15 text-white font-bold text-sm hover:bg-white/25 transition-colors border border-white/20"
                        >
                            🏒 Matchs NHL
                        </button>
                    </div>
                </div>
            </section>

            {/* ── Stats du modèle ───────────────────────────── */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-bold tracking-tight">Performance du modèle</h2>
                    <button
                        onClick={() => navigate("/performance")}
                        className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline underline-offset-4"
                    >
                        Voir tout <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                        { label: "Matchs analysés (48h)", value: totalCount || "—", sub: "Football + NHL" },
                        { label: "Précision 1X2", value: perf ? `${perf.accuracy_1x2}%` : "—", sub: "30 derniers jours", color: "text-emerald-600 dark:text-emerald-400" },
                        { label: "Précision BTTS", value: perf ? `${perf.accuracy_btts}%` : "—", sub: "30 derniers jours", color: "text-blue-600 dark:text-blue-400" },
                        { label: "Précision Over 2.5", value: perf ? `${perf.accuracy_over_25}%` : "—", sub: "30 derniers jours", color: "text-purple-600 dark:text-purple-400" },
                    ].map((s, i) => (
                        <Card key={i} className="border-border/50 bg-card glow-card">
                            <CardContent className="p-0">
                                <StatCard {...s} />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </section>

            {/* ── Matchs à la une ───────────────────────────── */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-bold tracking-tight flex items-center gap-2">
                            <Flame className="w-5 h-5 text-orange-500" />
                            Matchs à la une
                        </h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            Top matchs avec le meilleur score de confiance — J+0 et J+1
                        </p>
                    </div>
                    <button
                        onClick={() => navigate("/football")}
                        className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline underline-offset-4"
                    >
                        Tous les matchs <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                </div>

                {loading ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="h-40 rounded-xl bg-muted/50 animate-pulse" />
                        ))}
                    </div>
                ) : topMatches.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {topMatches.map(m => <FeaturedMatchCard key={m.id} match={m} />)}
                    </div>
                ) : (
                    <div className="text-center py-12 rounded-xl border border-dashed border-border/50 bg-card/30">
                        <p className="text-sm text-muted-foreground">Aucun match à venir pour le moment</p>
                    </div>
                )}
            </section>

            {/* ── Comment ça marche ─────────────────────────── */}
            <section>
                <div className="text-center mb-6">
                    <h2 className="text-lg font-bold tracking-tight">Comment ça marche</h2>
                    <p className="text-sm text-muted-foreground mt-1">Une approche multi-modèle pour des prédictions fiables</p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <FeatureCard icon={Activity} title="Modèle Poisson" color="bg-indigo-500/10"
                        description="Distribution de probabilités des buts basée sur les expected goals (xG) et la correction Dixon-Coles." />
                    <FeatureCard icon={BarChart3} title="Machine Learning" color="bg-purple-500/10"
                        description="Ensemble XGBoost + LightGBM entraîné sur 48 features par match pour une précision maximale." />
                    <FeatureCard icon={BrainCircuit} title="Analyse Claude AI" color="bg-cyan-500/10"
                        description="L'IA rédige une analyse contextuelle : forme récente, blessures clés, enjeux du match." />
                    <FeatureCard icon={Target} title="Value Betting" color="bg-emerald-500/10"
                        description="Détection des opportunités à valeur positive via le critère de Kelly fractionnel (¼)." />
                </div>
            </section>

            {/* ── Actualités ────────────────────────────────── */}
            <section>
                <div className="flex items-center gap-2 mb-4">
                    <Newspaper className="w-5 h-5 text-primary" />
                    <h2 className="text-lg font-bold tracking-tight">Actualités sportives</h2>
                </div>
                <Card className="border-border/50">
                    <CardContent className="p-3 divide-y divide-border/40">
                        {newsLoading ? (
                            <div className="space-y-3 p-2">
                                {[1, 2, 3, 4, 5, 6].map(i => (
                                    <div key={i} className="flex gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-muted animate-pulse shrink-0" />
                                        <div className="flex-1 space-y-1.5">
                                            <div className="h-3 bg-muted animate-pulse rounded w-full" />
                                            <div className="h-3 bg-muted animate-pulse rounded w-3/4" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : news.length > 0 ? (
                            news.map((item, i) => <NewsCard key={i} item={item} />)
                        ) : (
                            <div className="text-center py-8 text-sm text-muted-foreground">
                                Actualités temporairement indisponibles
                            </div>
                        )}
                    </CardContent>
                </Card>
            </section>

            {/* ── CTA Premium ───────────────────────────────── */}
            <section className="rounded-2xl border border-amber-500/20 bg-gradient-to-r from-amber-500/5 to-orange-500/5 p-6 sm:p-8">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <Trophy className="w-5 h-5 text-amber-500" />
                            <h3 className="font-bold text-base">Passez Premium</h3>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Débloquez BTTS, Over/Under, buteurs probables, analyse IA complète et bien plus.
                        </p>
                    </div>
                    <button
                        onClick={() => navigate("/premium")}
                        className="shrink-0 flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 text-white font-bold text-sm hover:bg-amber-600 transition-colors shadow-lg shadow-amber-500/20"
                    >
                        Voir les offres <ArrowRight className="w-4 h-4" />
                    </button>
                </div>
            </section>
        </div>
    )
}
