import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
    ArrowLeft, Flame, Lock, Trophy, Target, Zap,
    TrendingUp, Users, BrainCircuit, ChevronRight
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth"
import { fetchPredictionDetail } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

/* ── Probability bar ───────────────────────────────────────── */
function ProbBar({ label, value, color = "bg-primary" }) {
    const pct = value ?? 0
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-muted-foreground">{label}</span>
                <span className="text-sm font-bold tabular-nums">{pct}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                    className={cn("h-full rounded-full prob-bar-fill", color)}
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    )
}

/* ── Stat row ──────────────────────────────────────────────── */
function StatRow({ label, value, icon: Icon }) {
    const display = value != null ? `${value}%` : "—%"
    return (
        <div className="flex items-center justify-between py-2.5 border-b border-border/30 last:border-0">
            <div className="flex items-center gap-2">
                {Icon && <Icon className="w-3.5 h-3.5 text-muted-foreground" />}
                <span className="text-sm text-foreground">{label}</span>
            </div>
            <span className={cn(
                "text-sm font-bold tabular-nums",
                value >= 70 ? "text-emerald-600 dark:text-emerald-400" :
                    value >= 50 ? "text-amber-600 dark:text-amber-400" :
                        "text-foreground"
            )}>
                {display}
            </span>
        </div>
    )
}

/* ── Premium Blur Wrapper ──────────────────────────────────── */
function PremiumSection({ children, title, icon: Icon }) {
    const { isPremium, isAdmin } = useAuth()
    const navigate = useNavigate()

    if (isPremium || isAdmin) {
        return (
            <Card className="border-border/50">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        {Icon && <Icon className="w-4 h-4 text-primary" />}
                        {title}
                    </CardTitle>
                </CardHeader>
                <CardContent>{children}</CardContent>
            </Card>
        )
    }

    return (
        <Card className="border-amber-500/20 bg-gradient-to-b from-card to-amber-500/3 overflow-hidden">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                    {Icon && <Icon className="w-4 h-4 text-muted-foreground" />}
                    {title}
                    <Lock className="w-3.5 h-3.5 text-amber-500 ml-auto" />
                </CardTitle>
            </CardHeader>
            <CardContent className="relative">
                <div className="premium-blur select-none pointer-events-none">
                    {children}
                </div>
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-card/60 backdrop-blur-[2px] rounded-b-xl">
                    <Lock className="w-6 h-6 text-amber-500 mb-2" />
                    <p className="text-sm font-bold mb-3">Contenu Premium</p>
                    <Button
                        size="sm"
                        className="bg-amber-500 hover:bg-amber-600 text-white border-0 shadow-lg shadow-amber-500/20"
                        onClick={() => navigate('/premium')}
                    >
                        <Trophy className="w-3.5 h-3.5 mr-1.5" />
                        Passer Premium
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}

/* ═══════════════════════════════════════════════════════════
   Match Detail Page
   ═══════════════════════════════════════════════════════════ */
export default function MatchDetailPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const { isPremium, isAdmin } = useAuth()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetchPredictionDetail(id)
            .then(raw => {
                // Flatten stats_json keys to top-level for robust fallback
                if (raw?.prediction) {
                    const sj = raw.prediction.stats_json || {}
                    const merged = { ...sj, ...raw.prediction } // prediction wins over sj
                    // Also normalise over_2_5 vs over_25
                    if (!merged.proba_over_25) merged.proba_over_25 = merged.proba_over_2_5
                    raw = { ...raw, prediction: merged }
                }
                setData(raw)
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }, [id])

    if (loading) return (
        <div className="flex items-center justify-center py-32">
            <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
    )

    if (error || !data) return (
        <div className="text-center py-20">
            <p className="text-muted-foreground">Match introuvable</p>
            <Button variant="outline" className="mt-4" onClick={() => navigate('/football')}>
                Retour aux matchs
            </Button>
        </div>
    )

    const { fixture, prediction: p } = data
    const isHot = p?.confidence_score >= 7
    const time = fixture?.date?.slice(11, 16) || "—"
    const dateStr = fixture?.date ? new Date(fixture.date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) : ""

    // Stats from stats_json fallback
    const sj = p?.stats_json || {}
    const get = (key, alt) => p?.[key] ?? sj?.[key] ?? p?.[alt] ?? sj?.[alt] ?? null

    const proba_over_05 = get('proba_over_05')
    const proba_over_15 = get('proba_over_15')
    const proba_over_25 = get('proba_over_25') ?? get('proba_over_2_5')
    const proba_over_35 = get('proba_over_35')
    const proba_btts = get('proba_btts')
    const proba_penalty = get('proba_penalty')
    const xg_home = get('xg_home') ?? sj?.xg_home
    const xg_away = get('xg_away') ?? sj?.xg_away

    // Scorers
    const scorers = p?.top_scorers || sj?.top_scorers || []

    return (
        <div className="max-w-2xl mx-auto space-y-4 animate-fade-in-up pb-12">

            {/* Back button */}
            <button
                onClick={() => navigate('/football')}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Retour aux matchs
            </button>

            {/* Match header */}
            <Card className="border-border/50 overflow-hidden">
                <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-5 py-4 border-b border-border/30">
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                            {fixture?.league_name || "Football"}
                        </span>
                        <div className="flex items-center gap-2">
                            {isHot && (
                                <div className="flex items-center gap-1">
                                    <Flame className="w-3.5 h-3.5 text-orange-500 flame-badge" />
                                    <span className="text-[10px] font-bold text-orange-500">HOT</span>
                                </div>
                            )}
                            <span className="text-xs text-muted-foreground capitalize">{dateStr} · {time}</span>
                        </div>
                    </div>
                    <div className="flex items-center justify-between gap-4 mt-3">
                        <div className="flex-1 text-center">
                            {fixture?.home_logo && (
                                <img src={fixture.home_logo} alt="" className="w-10 h-10 mx-auto mb-1 object-contain" />
                            )}
                            <p className="text-xl font-black leading-tight">{fixture?.home_team}</p>
                            {fixture?.home_goals != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.home_goals}</p>
                            )}
                        </div>
                        <div className="shrink-0 text-center">
                            <span className="text-sm font-bold text-muted-foreground/40">VS</span>
                        </div>
                        <div className="flex-1 text-center">
                            {fixture?.away_logo && (
                                <img src={fixture.away_logo} alt="" className="w-10 h-10 mx-auto mb-1 object-contain" />
                            )}
                            <p className="text-xl font-black leading-tight">{fixture?.away_team}</p>
                            {fixture?.away_goals != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.away_goals}</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Pari recommandé + confiance — FREE */}
                {p && (
                    <CardContent className="p-4 space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Pari recommandé</p>
                                <p className="text-base font-bold text-primary">{p.recommended_bet || "—"}</p>
                            </div>
                            {p.confidence_score != null && (
                                <div className="text-center">
                                    <p className="text-xs text-muted-foreground mb-1">Confiance</p>
                                    <div className={cn(
                                        "text-2xl font-black tabular-nums",
                                        p.confidence_score >= 8 ? "text-emerald-600 dark:text-emerald-400" :
                                            p.confidence_score >= 6 ? "text-amber-600 dark:text-amber-400" :
                                                "text-foreground"
                                    )}>
                                        {p.confidence_score}<span className="text-sm text-muted-foreground font-normal">/10</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </CardContent>
                )}
            </Card>

            {/* Probabilités 1X2 — FREE */}
            {p && (
                <Card className="border-border/50">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <BarChart3Icon className="w-4 h-4 text-primary" />
                            Probabilités 1X2
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <ProbBar label={`Victoire ${fixture?.home_team}`} value={p.proba_home} color="bg-primary" />
                        <ProbBar label="Match nul" value={p.proba_draw} color="bg-slate-400" />
                        <ProbBar label={`Victoire ${fixture?.away_team}`} value={p.proba_away} color="bg-blue-400" />
                    </CardContent>
                </Card>
            )}

            {/* Marchés — PREMIUM */}
            <PremiumSection title="Marchés & Statistiques" icon={Target}>
                <div className="space-y-0">
                    <StatRow label="Les deux équipes marquent (BTTS)" value={proba_btts} />
                    <StatRow label="Plus de 0.5 buts" value={proba_over_05} />
                    <StatRow label="Plus de 1.5 buts" value={proba_over_15} />
                    <StatRow label="Plus de 2.5 buts" value={proba_over_25} />
                    <StatRow label="Plus de 3.5 buts" value={proba_over_35} />
                    <StatRow label="But sur penalty" value={proba_penalty} />
                    {p?.correct_score && (
                        <div className="flex items-center justify-between py-2.5">
                            <span className="text-sm">Score exact probable</span>
                            <span className="text-sm font-bold text-primary">{p.correct_score}</span>
                        </div>
                    )}
                </div>
            </PremiumSection>

            {/* xG — PREMIUM */}
            <PremiumSection title="Expected Goals (xG)" icon={TrendingUp}>
                <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-accent/30 rounded-xl">
                        <p className="text-xs text-muted-foreground mb-1">{fixture?.home_team}</p>
                        <p className="text-2xl font-black text-primary">{xg_home ?? "—"}</p>
                        <p className="text-[10px] text-muted-foreground">xG domicile</p>
                    </div>
                    <div className="text-center p-3 bg-accent/30 rounded-xl">
                        <p className="text-xs text-muted-foreground mb-1">{fixture?.away_team}</p>
                        <p className="text-2xl font-black text-primary">{xg_away ?? "—"}</p>
                        <p className="text-[10px] text-muted-foreground">xG extérieur</p>
                    </div>
                </div>
            </PremiumSection>

            {/* Buteurs probables — PREMIUM */}
            <PremiumSection title="Buteurs probables" icon={Users}>
                {scorers.length > 0 ? (
                    <div className="space-y-2">
                        {scorers.slice(0, 2).map((s, i) => (
                            <div key={i} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                                <div className="flex items-center gap-3">
                                    {s.photo ? (
                                        <img src={s.photo} alt={s.name} className="w-8 h-8 rounded-full object-cover border border-border/50 shrink-0" />
                                    ) : (
                                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0 border border-border/50">
                                            {i + 1}
                                        </div>
                                    )}
                                    <div>
                                        <p className="text-sm font-semibold leading-tight">{s.player_name || s.name}</p>
                                        {s.team && <p className="text-[10px] text-muted-foreground">{s.team}</p>}
                                    </div>
                                </div>
                                <Badge className="bg-primary/10 text-primary border-0 font-bold">
                                    {s.probability ?? s.prob ?? "—"}%
                                </Badge>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-sm text-muted-foreground text-center py-2">Données non disponibles</p>
                )}
            </PremiumSection>

            {/* Analyse IA — PREMIUM */}
            <PremiumSection title="Analyse IA" icon={BrainCircuit}>
                {p?.analysis_text ? (
                    <p className="text-sm text-foreground/80 leading-relaxed">{p.analysis_text}</p>
                ) : (
                    <p className="text-sm text-muted-foreground">Analyse en cours de génération...</p>
                )}
            </PremiumSection>

            {/* Disclaimer */}
            <p className="disclaimer-text text-center px-4">
                Les probabilités affichées sont calculées par des modèles statistiques à titre informatif uniquement.
                Elles ne constituent pas des conseils de paris. Jouez de manière responsable. 18+
            </p>
        </div>
    )
}

// Local icon component to avoid import issues
function BarChart3Icon({ className }) {
    return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
        </svg>
    )
}
