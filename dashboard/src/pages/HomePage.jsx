import { cn } from "@/lib/utils"
import { fetchPredictions } from "@/lib/api"
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
    Zap, ChevronRight, BrainCircuit, BarChart3,
    Shield, TrendingUp, Sparkles, ArrowRight, Clock,
    Target, Activity
} from "lucide-react"


/* ── Animated gradient orb (background decoration) ─────────── */
function GlowOrb({ className }) {
    return (
        <div className={cn(
            "absolute rounded-full blur-3xl opacity-20 pointer-events-none",
            className
        )} />
    )
}


/* ── Feature card ──────────────────────────────────────────── */
function FeatureCard({ icon: Icon, title, description, accent }) {
    return (
        <div className="group relative rounded-xl border border-border/40 bg-card/30 p-5 hover:border-primary/30 hover:bg-card/50 transition-all duration-300">
            <div className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center mb-3",
                accent || "bg-primary/10"
            )}>
                <Icon className="w-5 h-5 text-primary" />
            </div>
            <h3 className="font-bold text-sm mb-1">{title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </div>
    )
}


/* ── Featured match card (top 3) ───────────────────────────── */
function FeaturedMatch({ match, rank }) {
    const navigate = useNavigate()
    const pred = match.prediction
    const time = match.date?.slice(11, 16) || "—"
    const dateStr = match.date?.slice(5, 10)?.replace("-", "/") || ""

    const confidenceColor = pred?.confidence_score >= 8
        ? "from-emerald-500/20 to-emerald-500/5 border-emerald-500/20"
        : pred?.confidence_score >= 6
            ? "from-amber-500/15 to-amber-500/5 border-amber-500/15"
            : "from-indigo-500/15 to-indigo-500/5 border-indigo-500/15"

    return (
        <div
            onClick={() => navigate(`/match/${match.id}`)}
            className={cn(
                "group relative rounded-xl border bg-gradient-to-b p-5 cursor-pointer",
                "hover:scale-[1.02] hover:shadow-xl hover:shadow-primary/5 transition-all duration-300",
                confidenceColor
            )}
        >
            {/* Rank badge */}
            <div className="absolute -top-2.5 -left-2 w-7 h-7 rounded-full bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
                <span className="text-xs font-black text-primary-foreground">{rank}</span>
            </div>

            {/* League & Time */}
            <div className="flex items-center justify-between mb-4">
                <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                    {match.league_name || "Ligue"}
                </span>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    <span className="text-xs font-medium">{dateStr} · {time}</span>
                </div>
            </div>

            {/* Teams */}
            <div className="flex items-center justify-between gap-4 mb-4">
                <div className="flex-1 text-center">
                    <p className="font-black text-base leading-tight">{match.home_team}</p>
                </div>
                <div className="shrink-0 px-3">
                    <span className="text-xs font-bold text-muted-foreground/50">VS</span>
                </div>
                <div className="flex-1 text-center">
                    <p className="font-black text-base leading-tight">{match.away_team}</p>
                </div>
            </div>

            {/* Quick stats row */}
            {pred && (
                <div className="flex items-center justify-between pt-3 border-t border-border/30">
                    <div className="flex items-center gap-3">
                        <div className="text-center">
                            <span className="text-[10px] text-muted-foreground block">Dom</span>
                            <span className="text-sm font-bold tabular-nums">{pred.proba_home}%</span>
                        </div>
                        <div className="text-center">
                            <span className="text-[10px] text-muted-foreground block">Nul</span>
                            <span className="text-sm font-bold tabular-nums text-muted-foreground">{pred.proba_draw}%</span>
                        </div>
                        <div className="text-center">
                            <span className="text-[10px] text-muted-foreground block">Ext</span>
                            <span className="text-sm font-bold tabular-nums">{pred.proba_away}%</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {pred.value_bet && (
                            <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full ring-1 ring-emerald-500/20">
                                VALUE
                            </span>
                        )}
                        <span className={cn(
                            "text-xs font-bold px-2 py-0.5 rounded-full ring-1",
                            pred.confidence_score >= 8
                                ? "text-emerald-400 ring-emerald-500/30"
                                : pred.confidence_score >= 6
                                    ? "text-amber-400 ring-amber-500/30"
                                    : "text-zinc-400 ring-zinc-500/30"
                        )}>
                            {pred.confidence_score}/10
                        </span>
                    </div>
                </div>
            )}

            {/* Hover arrow */}
            <ChevronRight className="absolute top-1/2 right-3 -translate-y-1/2 w-4 h-4 text-muted-foreground/0 group-hover:text-muted-foreground/50 transition-all" />
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════
   Home Page
   ═══════════════════════════════════════════════════════════ */
export default function HomePage() {
    const navigate = useNavigate()
    const [topMatches, setTopMatches] = useState([])
    const [totalCount, setTotalCount] = useState(0)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)
        const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

        Promise.all([
            fetchPredictions(today),
            fetchPredictions(tomorrow)
        ]).then(([res1, res2]) => {
            const all = [...(res1.matches || []), ...(res2.matches || [])]
            setTotalCount(all.length)

            // Top 3: highest confidence score among upcoming (non-FT) matches
            const upcoming = all
                .filter(m => m.prediction && m.status !== "FT")
                .sort((a, b) => (b.prediction?.confidence_score || 0) - (a.prediction?.confidence_score || 0))
                .slice(0, 3)

            setTopMatches(upcoming)
        }).catch(console.error)
            .finally(() => setLoading(false))
    }, [])

    return (
        <div className="space-y-16 pb-16">

            {/* ── Hero Section ──────────────────────────────── */}
            <section className="relative pt-12 sm:pt-20 pb-8 overflow-hidden">
                {/* Background orbs */}
                <GlowOrb className="w-96 h-96 bg-indigo-500 -top-20 -left-40" />
                <GlowOrb className="w-72 h-72 bg-purple-500 top-10 right-0" />

                <div className="relative text-center max-w-2xl mx-auto">
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 ring-1 ring-primary/20 mb-6">
                        <Zap className="w-3.5 h-3.5 text-primary" />
                        <span className="text-xs font-semibold text-primary">
                            Propulsé par l'intelligence artificielle
                        </span>
                    </div>

                    {/* Title */}
                    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter leading-[1.1]">
                        Prédictions football{" "}
                        <span className="gradient-text">augmentées par l'IA</span>
                    </h1>

                    {/* Subtitle */}
                    <p className="text-base sm:text-lg text-muted-foreground mt-5 leading-relaxed max-w-lg mx-auto">
                        Modèles statistiques avancés, apprentissage automatique et analyse Claude AI
                        combinés pour des prédictions de matchs précises et exploitables.
                    </p>

                    {/* CTA buttons */}
                    <div className="flex items-center justify-center gap-3 mt-8">
                        <button
                            onClick={() => navigate("/matchs")}
                            className="group flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-primary/25"
                        >
                            Voir les matchs
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                        <button
                            onClick={() => navigate("/performance")}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-secondary/50 ring-1 ring-border/50 text-foreground font-semibold text-sm hover:bg-secondary transition-colors"
                        >
                            Performance
                        </button>
                    </div>
                </div>
            </section>


            {/* ── Features Grid ─────────────────────────────── */}
            <section>
                <div className="text-center mb-8">
                    <h2 className="text-xl font-bold tracking-tight">Comment ça marche</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                        Une approche multi-modèle pour des prédictions fiables
                    </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <FeatureCard
                        icon={Activity}
                        title="Modèle Poisson"
                        description="Distribution de probabilités des buts basée sur les expected goals (xG) et la correction Dixon-Coles."
                        accent="bg-indigo-500/10"
                    />
                    <FeatureCard
                        icon={BarChart3}
                        title="Machine Learning"
                        description="Ensemble XGBoost + LightGBM + Régression logistique entraîné sur 48 features par match."
                        accent="bg-purple-500/10"
                    />
                    <FeatureCard
                        icon={BrainCircuit}
                        title="Analyse Claude AI"
                        description="Intelligence artificielle qui rédige une analyse contextuelle de chaque match : forme, blessures, enjeux."
                        accent="bg-cyan-500/10"
                    />
                    <FeatureCard
                        icon={Target}
                        title="Value Betting"
                        description="Détection automatique des paris à valeur positive via le critère de Kelly fractionnel (¼)."
                        accent="bg-emerald-500/10"
                    />
                </div>
            </section>


            {/* ── Top 3 Affiches ────────────────────────────── */}
            <section>
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-primary" />
                            Affiches du moment
                        </h2>
                        <p className="text-sm text-muted-foreground mt-0.5">
                            Top 3 des matchs à plus haute confiance — J+0 et J+1
                        </p>
                    </div>
                    <button
                        onClick={() => navigate("/matchs")}
                        className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline underline-offset-4"
                    >
                        Tous les matchs
                        <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                    </div>
                ) : topMatches.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                        {topMatches.map((match, i) => (
                            <FeaturedMatch key={match.id} match={match} rank={i + 1} />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 rounded-xl border border-dashed border-border/50 bg-card/20">
                        <p className="text-sm text-muted-foreground">Aucun match à venir pour le moment</p>
                    </div>
                )}
            </section>


            {/* ── Stats strip ───────────────────────────────── */}
            <section className="rounded-xl border border-border/40 bg-card/30 p-6">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                    <div className="text-center">
                        <p className="text-3xl font-black tabular-nums gradient-text">{totalCount}</p>
                        <p className="text-xs text-muted-foreground mt-1">Matchs analysés (48h)</p>
                    </div>
                    <div className="text-center">
                        <p className="text-3xl font-black tabular-nums gradient-text">6</p>
                        <p className="text-xs text-muted-foreground mt-1">Championnats couverts</p>
                    </div>
                    <div className="text-center">
                        <p className="text-3xl font-black tabular-nums gradient-text">48</p>
                        <p className="text-xs text-muted-foreground mt-1">Features par match</p>
                    </div>
                    <div className="text-center">
                        <p className="text-3xl font-black tabular-nums gradient-text">3</p>
                        <p className="text-xs text-muted-foreground mt-1">Modèles ML combinés</p>
                    </div>
                </div>
            </section>


            {/* ── Footer note ───────────────────────────────── */}
            <div className="text-center">
                <p className="text-[11px] text-muted-foreground/50 max-w-md mx-auto">
                    CortexAI est un outil d'analyse statistique expérimental. Les prédictions sont fournies à titre informatif
                    et ne constituent pas des conseils de paris.
                </p>
            </div>
        </div>
    )
}
