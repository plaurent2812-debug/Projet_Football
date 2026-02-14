import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { fetchPredictionDetail } from "@/lib/api"
import { useParams, useNavigate } from "react-router-dom"
import { useState, useEffect } from "react"
import {
    ArrowLeft, Target, TrendingUp, Shield, Swords,
    BarChart3, Percent, AlertTriangle, Flame, BrainCircuit,
    Zap, Activity, MessageSquareText
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth"
import { Lock } from "lucide-react"

/* ── Premium Blur Component ────────────────────────────────── */
function PremiumBlur({ children, label = "Réservé aux membres Premium" }) {
    return (
        <div className="relative overflow-hidden rounded-xl border border-border/50 bg-card/30">
            <div className="filter blur-sm select-none pointer-events-none opacity-50">
                {children}
            </div>
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/10 backdrop-blur-[2px] z-10">
                <div className="p-3 rounded-full bg-primary/10 text-primary mb-2 ring-1 ring-primary/20">
                    <Lock className="w-5 h-5" />
                </div>
                <p className="text-sm font-bold text-foreground">{label}</p>
                <button className="mt-3 px-4 py-1.5 text-xs font-semibold bg-primary text-primary-foreground rounded-full hover:bg-primary/90 transition-colors">
                    Passer Premium
                </button>
            </div>
        </div>
    )
}


/* ── Stat row ──────────────────────────────────────────────── */
function StatRow({ label, value, icon: Icon, color }) {
    return (
        <div className="flex items-center justify-between py-2.5 border-b border-border/30 last:border-0">
            <div className="flex items-center gap-2.5 text-muted-foreground">
                {Icon && <Icon className={cn("w-4 h-4", color || "text-muted-foreground/60")} />}
                <span className="text-sm">{label}</span>
            </div>
            <span className="font-semibold text-sm">{value}</span>
        </div>
    )
}


/* ── Probability bar ───────────────────────────────────────── */
function ProbBar({ label, value, color = "bg-primary" }) {
    const pct = Math.min(value, 100)
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">{label}</span>
                <span className="font-bold tabular-nums">{value}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-secondary/60 overflow-hidden">
                <div
                    className={cn("h-full rounded-full transition-all duration-1000 ease-out", color)}
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    )
}


/* ── Scorer row ────────────────────────────────────────────── */
function ScorerRow({ player, rank }) {
    return (
        <div className="flex items-center gap-3 py-2 px-2 rounded-lg hover:bg-accent/30 transition-colors">
            <span className="text-xs font-bold text-muted-foreground/50 w-4 tabular-nums">{rank}</span>
            <img
                src={player.photo}
                alt={player.name}
                className="w-8 h-8 rounded-full object-cover bg-secondary ring-1 ring-border/50"
                onError={(e) => { e.target.style.display = 'none' }}
            />
            <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm truncate">{player.name}</p>
                <p className="text-[11px] text-muted-foreground">{player.apps} matchs</p>
            </div>
            <span className="text-sm font-bold tabular-nums text-primary">{player.goals} ⚽</span>
        </div>
    )
}


/* ═══════════════════════════════════════════════════════════
   Match Detail Page
   ═══════════════════════════════════════════════════════════ */
export default function MatchDetailPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const { hasAccess, isPremium, isAdmin } = useAuth()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchPredictionDetail(id)
            .then(setData)
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [id])

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32">
                <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            </div>
        )
    }

    if (!data?.fixture) {
        return (
            <div className="text-center py-32">
                <AlertTriangle className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
                <p className="text-muted-foreground">Match introuvable</p>
            </div>
        )
    }

    const f = data.fixture
    const p = data.prediction
    const time = f.date?.slice(11, 16) || ""
    const dateStr = f.date?.slice(0, 10) || ""

    return (
        <div className="space-y-5 max-w-4xl mx-auto pb-12">
            {/* Back button */}
            <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm group"
            >
                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                Retour
            </button>

            {/* ── Match header ──────────────────────────────── */}
            <div className="rounded-xl border border-border/50 bg-card/50 overflow-hidden">
                <div className="relative px-6 py-8">
                    <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/5 via-transparent to-purple-500/5" />

                    <div className="relative flex items-center justify-between">
                        <div className="flex-1 text-center">
                            <p className="text-xl sm:text-2xl font-black leading-tight">{f.home_team}</p>
                            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mt-1.5 inline-block">
                                Domicile
                            </span>
                        </div>

                        <div className="px-6 text-center shrink-0">
                            {f.status === "FT" ? (
                                <div>
                                    <p className="text-4xl sm:text-5xl font-black tabular-nums tracking-tight">
                                        {f.home_goals} <span className="text-muted-foreground/40">-</span> {f.away_goals}
                                    </p>
                                    <span className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-wider">
                                        Terminé
                                    </span>
                                </div>
                            ) : (
                                <div>
                                    <p className="text-2xl font-bold text-muted-foreground/50">VS</p>
                                    <div className="mt-2 flex items-center gap-1.5 justify-center text-muted-foreground">
                                        <span className="text-xs font-medium">{dateStr}</span>
                                        <span className="text-muted-foreground/30">•</span>
                                        <span className="text-sm font-bold text-foreground">{time}</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="flex-1 text-center">
                            <p className="text-xl sm:text-2xl font-black leading-tight">{f.away_team}</p>
                            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mt-1.5 inline-block">
                                Extérieur
                            </span>
                        </div>
                    </div>
                </div>

                {p && (
                    <div className="border-t border-border/30 px-6 py-2.5 flex items-center justify-between bg-accent/20">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Zap className="w-3.5 h-3.5 text-primary" />
                            <span className="font-medium">{p.recommended_bet || "Analyse disponible"}</span>
                        </div>
                        <div className={cn(
                            "text-xs font-bold px-2.5 py-1 rounded-full ring-1",
                            p.confidence_score >= 7
                                ? "bg-emerald-500/15 text-emerald-400 ring-emerald-500/20"
                                : p.confidence_score >= 5
                                    ? "bg-amber-500/15 text-amber-400 ring-amber-500/20"
                                    : "bg-zinc-500/15 text-zinc-400 ring-zinc-500/20"
                        )}>
                            Confiance {p.confidence_score}/10
                        </div>
                    </div>
                )}
            </div>

            {/* No prediction */}
            {!p && (
                <div className="rounded-xl border border-dashed border-border/50 bg-card/30 p-8 text-center">
                    <AlertTriangle className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
                    <p className="text-muted-foreground text-sm">Pas de prédiction disponible</p>
                </div>
            )}

            {/* ── Prediction panels ────────────────────────── */}
            {p && (
                <div className="space-y-4">
                    {/* Row 1: 1X2 + Markets */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* 1X2 - Visible for Free+ */}
                        <Card className="bg-card/50 border-border/50">
                            <CardHeader className="pb-3">
                                <CardTitle className="flex items-center gap-2 text-sm">
                                    <Swords className="w-4 h-4 text-primary" />
                                    Résultat 1X2
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3.5">
                                <ProbBar label="Domicile" value={p.proba_home || 0} color="bg-indigo-500" />
                                <ProbBar label="Nul" value={p.proba_draw || 0} color="bg-zinc-500" />
                                <ProbBar label="Extérieur" value={p.proba_away || 0} color="bg-purple-500" />
                            </CardContent>
                        </Card>

                        {/* Markets - Premium Only */}
                        {hasAccess('premium') ? (
                            <Card className="bg-card/50 border-border/50">
                                <CardHeader className="pb-3">
                                    <CardTitle className="flex items-center gap-2 text-sm">
                                        <BarChart3 className="w-4 h-4 text-primary" />
                                        Marchés
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <StatRow label="But des 2 équipes" value={`${p.proba_btts || "—"}%`} icon={Percent} color="text-emerald-400" />
                                    <StatRow label="Plus de 0.5" value={`${p.proba_over_05 || "—"}%`} icon={TrendingUp} color="text-blue-400" />
                                    <StatRow label="Plus de 1.5" value={`${p.proba_over_15 || "—"}%`} icon={TrendingUp} color="text-blue-400" />
                                    <StatRow label="Plus de 2.5" value={`${p.proba_over_25 || p.proba_over_2_5 || "—"}%`} icon={TrendingUp} color="text-amber-400" />
                                    <StatRow label="Plus de 3.5" value={`${p.proba_over_35 || "—"}%`} icon={TrendingUp} color="text-orange-400" />
                                    <StatRow label="Score exact" value={p.correct_score || "—"} icon={Target} color="text-purple-400" />
                                </CardContent>
                            </Card>
                        ) : (
                            <PremiumBlur label="Stats avancées (Premium)">
                                <Card className="h-full">
                                    <CardHeader className="pb-3"><CardTitle>Marchés</CardTitle></CardHeader>
                                    <CardContent>
                                        <StatRow label="But des 2 équipes" value="65%" />
                                        <StatRow label="Plus de 1.5" value="80%" />
                                        <StatRow label="Plus de 2.5" value="55%" />
                                        <StatRow label="Score exact" value="2-1" />
                                    </CardContent>
                                </Card>
                            </PremiumBlur>
                        )}
                    </div>

                    {/* Row 2: Recommendation + Expected Goals */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Recommendation - Premium Only */}
                        {hasAccess('premium') ? (
                            p.recommended_bet && (
                                <Card className="bg-card/50 border-border/50">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="flex items-center gap-2 text-sm">
                                            <Target className="w-4 h-4 text-primary" />
                                            Recommandation
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm text-muted-foreground">Pari recommandé</span>
                                            <Badge className="bg-primary/15 text-primary hover:bg-primary/20 border-0">
                                                {p.recommended_bet}
                                            </Badge>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm text-muted-foreground">Confiance</span>
                                            <span className="text-base font-bold tabular-nums">{p.confidence_score}/10</span>
                                        </div>
                                        {p.kelly_edge != null && (
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm text-muted-foreground">Avantage Kelly</span>
                                                <span className={cn(
                                                    "font-bold tabular-nums text-sm",
                                                    p.kelly_edge > 0 ? "text-emerald-400" : "text-red-400"
                                                )}>
                                                    {p.kelly_edge > 0 ? "+" : ""}{(p.kelly_edge * 100).toFixed(1)}%
                                                </span>
                                            </div>
                                        )}
                                        {p.value_bet && (
                                            <div className="mt-2 p-2.5 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20 text-center">
                                                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                                                    🎯 Pari Value détecté
                                                </span>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            )
                        ) : (
                            <PremiumBlur label="Recommandations & Value (Premium)">
                                <Card className="h-full">
                                    <CardHeader className="pb-3"><CardTitle>Recommandation</CardTitle></CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="flex justify-between"><span className="text-sm">Pari</span><Badge>Premium</Badge></div>
                                        <div className="flex justify-between"><span className="text-sm">Confiance</span><span>8/10</span></div>
                                    </CardContent>
                                </Card>
                            </PremiumBlur>
                        )}

                        {/* Expected Goals - Premium Only */}
                        {hasAccess('premium') ? (
                            <Card className="bg-card/50 border-border/50">
                                <CardHeader className="pb-3">
                                    <CardTitle className="flex items-center gap-2 text-sm">
                                        <Activity className="w-4 h-4 text-primary" />
                                        Expected Goals
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        {/* xG Home */}
                                        <div className="space-y-1.5">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-muted-foreground">{f.home_team}</span>
                                                <span className="font-bold tabular-nums">{p.stats_json?.xg_home || "—"}</span>
                                            </div>
                                            {p.stats_json?.xg_home && (
                                                <div className="h-2 w-full rounded-full bg-secondary/60 overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full bg-indigo-500 transition-all duration-1000"
                                                        style={{ width: `${Math.min((p.stats_json.xg_home / 4) * 100, 100)}%` }}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                        {/* xG Away */}
                                        <div className="space-y-1.5">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-muted-foreground">{f.away_team}</span>
                                                <span className="font-bold tabular-nums">{p.stats_json?.xg_away || "—"}</span>
                                            </div>
                                            {p.stats_json?.xg_away && (
                                                <div className="h-2 w-full rounded-full bg-secondary/60 overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full bg-purple-500 transition-all duration-1000"
                                                        style={{ width: `${Math.min((p.stats_json.xg_away / 4) * 100, 100)}%` }}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ) : (
                            <PremiumBlur label="Expected Goals (Premium)">
                                <Card className="h-full"><CardHeader><CardTitle>xG</CardTitle></CardHeader></Card>
                            </PremiumBlur>
                        )}
                    </div>
                    {/* Scorer Prediction */}
                    {/* Scorer Prediction - Free+ Only */}
                    {
                        hasAccess('free') && p.likely_scorer && (
                            <Card className="bg-card/50 border-border/50">
                                <CardHeader className="pb-3">
                                    <CardTitle className="flex items-center gap-2 text-sm">
                                        <Target className="w-4 h-4 text-primary" />
                                        Buteur Probable
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-lg ring-1 ring-primary/20">
                                                ⚽
                                            </div>
                                            <div>
                                                <p className="font-bold text-sm">{p.likely_scorer}</p>
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-xs text-muted-foreground">Probabilité IA</span>
                                                    <span className="text-xs font-bold text-primary">{p.likely_scorer_proba}%</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    {p.likely_scorer_reason && (
                                        <div className="text-xs text-muted-foreground bg-accent/20 p-3 rounded-lg border border-border/30 leading-relaxed">
                                            <BrainCircuit className="w-3 h-3 inline mr-1.5 text-primary/70 -mt-0.5" />
                                            {p.likely_scorer_reason}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )
                    }


                    {/* Row 3: AI Analysis — full width, prominent */}
                    {/* Row 3: AI Analysis — Premium Only */}
                    {
                        hasAccess('premium') ? (
                            p.analysis_text && (
                                <Card className="bg-card/50 border-border/50 glow-primary">
                                    <CardHeader className="pb-3">
                                        <CardTitle className="flex items-center gap-2 text-sm">
                                            <BrainCircuit className="w-4 h-4 text-primary" />
                                            Analyse du match
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="relative rounded-lg bg-accent/20 ring-1 ring-border/30 p-5">
                                            {/* Subtle gradient accent */}
                                            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
                                            <div className="flex gap-3">
                                                <MessageSquareText className="w-5 h-5 text-primary/60 shrink-0 mt-0.5" />
                                                <p className="text-sm leading-relaxed text-foreground/85 whitespace-pre-line">
                                                    {p.analysis_text.replace(/[#*]/g, '')}
                                                </p>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            )
                        ) : (
                            <PremiumBlur label="Analyse IA complète (Premium)">
                                <Card className="bg-card/50">
                                    <CardHeader><CardTitle>Analyse du match</CardTitle></CardHeader>
                                    <CardContent>
                                        <p className="blur-sm text-sm">
                                            Le match s'annonce serré avec un avantage léger pour l'équipe à domicile en raison de leur forme récente...
                                        </p>
                                    </CardContent>
                                </Card>
                            </PremiumBlur>
                        )
                    }

                    {/* Row 4: Top Scorers */}
                    {
                        (data.home_scorers?.length > 0 || data.away_scorers?.length > 0) && (
                            <Card className="bg-card/50 border-border/50">
                                <CardHeader className="pb-3">
                                    <CardTitle className="flex items-center gap-2 text-sm">
                                        <Flame className="w-4 h-4 text-orange-400" />
                                        Meilleurs Buteurs
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <h4
                                            onClick={() => navigate(`/equipe/${encodeURIComponent(f.home_team)}`)}
                                            className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 text-center hover:text-primary cursor-pointer transition-colors"
                                        >
                                            {f.home_team}
                                        </h4>
                                        <div className="space-y-0.5">
                                            {data.home_scorers?.map((scorer, i) => (
                                                <ScorerRow key={i} player={scorer} rank={i + 1} />
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <h4
                                            onClick={() => navigate(`/equipe/${encodeURIComponent(f.away_team)}`)}
                                            className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 text-center hover:text-primary cursor-pointer transition-colors"
                                        >
                                            {f.away_team}
                                        </h4>
                                        <div className="space-y-0.5">
                                            {data.away_scorers?.map((scorer, i) => (
                                                <ScorerRow key={i} player={scorer} rank={i + 1} />
                                            ))}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )
                    }
                </div>
            )}
        </div>
    )
}
