import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
    ArrowLeft, Flame, Lock, Trophy, Target, Zap,
    TrendingUp, Users, BrainCircuit, ChevronRight, ChevronLeft
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth"
import { fetchPredictionDetail, fetchPredictions } from "@/lib/api"
import { getStatValue, formatOdds } from "@/lib/statsHelper"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Skeleton } from "@/components/ui/skeleton"
import { Info } from "lucide-react"

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
function StatRow({ label, value, icon: Icon, tooltip }) {
    const display = value != null ? `${value}%` : "—%"
    return (
        <div className="flex items-center justify-between py-2.5 border-b border-border/30 last:border-0">
            <div className="flex items-center gap-2">
                {Icon && <Icon className="w-3.5 h-3.5 text-muted-foreground" />}
                {tooltip ? (
                    <TooltipProvider delayDuration={150}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <span className="text-sm text-foreground flex items-center gap-1.5 cursor-help underline decoration-dashed underline-offset-4 decoration-border">
                                    {label}
                                    <Info className="w-3.5 h-3.5 text-muted-foreground" />
                                </span>
                            </TooltipTrigger>
                            <TooltipContent>
                                <p className="w-[200px] text-xs leading-relaxed">{tooltip}</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                ) : (
                    <span className="text-sm text-foreground">{label}</span>
                )}
            </div>
            <span className={cn(
                "text-sm font-bold tabular-nums",
                value >= 60 ? "text-emerald-600 dark:text-emerald-400" :
                    value >= 40 ? "text-amber-600 dark:text-amber-400" :
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
    const [adjacent, setAdjacent] = useState({ prev: null, next: null })

    useEffect(() => {
        fetchPredictionDetail(id)
            .then(raw => {
                setData(raw)
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }, [id])

    useEffect(() => {
        if (!data?.fixture?.date) return
        const d = data.fixture.date.slice(0, 10)
        fetchPredictions(d).then(res => {
            const matches = res.matches || []
            const idx = matches.findIndex(m => String(m.id) === String(id))
            if (idx > -1) {
                setAdjacent({
                    prev: idx > 0 ? matches[idx - 1].id : null,
                    next: idx < matches.length - 1 ? matches[idx + 1].id : null
                })
            }
        }).catch(console.error)
    }, [data?.fixture?.date, id])

    if (loading) return (
        <div className="w-full mx-auto space-y-4 pb-12 px-3 pt-4">
            <div className="flex items-center justify-between">
                <Skeleton className="h-8 w-32" />
                <div className="flex gap-2">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <Skeleton className="h-10 w-10 rounded-full" />
                </div>
            </div>
            <Skeleton className="h-40 w-full rounded-xl" />
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <div className="grid grid-cols-3 gap-3">
                <Skeleton className="h-20 rounded-xl" />
                <Skeleton className="h-20 rounded-xl" />
                <Skeleton className="h-20 rounded-xl" />
            </div>
            <Skeleton className="h-48 w-full rounded-xl" />
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
    const time = fixture?.date?.slice(11, 16) || "—"
    const dateStr = fixture?.date ? new Date(fixture.date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) : ""

    // Stats via centralized helper (resolves stats_json vs top-level)
    const proba_over_05 = getStatValue(p, 'proba_over_05')
    const proba_over_15 = getStatValue(p, 'proba_over_15')
    const proba_over_25 = getStatValue(p, 'proba_over_25')
    const proba_over_35 = getStatValue(p, 'proba_over_35')
    const proba_btts = getStatValue(p, 'proba_btts')
    const proba_penalty = getStatValue(p, 'proba_penalty')
    const xg_home = getStatValue(p, 'xg_home')
    const xg_away = getStatValue(p, 'xg_away')

    // Scorers
    const sj = p?.stats_json || {}
    const scorers = p?.top_scorers || sj?.top_scorers || []

    return (
        <div className="w-full mx-auto space-y-4 animate-fade-in-up pb-12">

            {/* Back button & Navigation */}
            <div className="flex items-center justify-between mb-2">
                <button
                    onClick={() => navigate('/football')}
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Retour aux matchs
                </button>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-10 w-10 rounded-full bg-card"
                        disabled={!adjacent.prev}
                        onClick={() => adjacent.prev && navigate(`/football/match/${adjacent.prev}`)}
                        aria-label="Match précédent"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-10 w-10 rounded-full bg-card"
                        disabled={!adjacent.next}
                        onClick={() => adjacent.next && navigate(`/football/match/${adjacent.next}`)}
                        aria-label="Match suivant"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            {/* Match header */}
            <Card className="border-border/50 overflow-hidden">
                <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-5 py-4 border-b border-border/30">
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                            {fixture?.league_name || "Football"}
                        </span>
                        <div className="flex items-center gap-2">
                            {p?.model_version === "meta_v2" && (
                                <Badge variant="outline" className="border-primary/50 text-primary text-xs h-5 px-1.5 flex items-center gap-1 bg-primary/5">
                                    <BrainCircuit className="w-3 h-3" />
                                    Meta V2
                                </Badge>
                            )}
                            <span className="text-xs text-muted-foreground capitalize">{dateStr} · {time}</span>
                        </div>
                    </div>
                    <div className="flex items-center justify-between gap-4 mt-3">
                        <div className="flex-1 text-center">
                            {fixture?.home_logo && (
                                <img src={fixture.home_logo} alt="" role="presentation" className="w-10 h-10 mx-auto mb-1 object-contain" />
                            )}
                            <div className="flex items-center justify-center gap-1.5 flex-wrap">
                                <p
                                    className="text-xl font-black leading-tight cursor-pointer hover:underline hover:text-primary transition-colors"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        if (fixture?.home_team) navigate(`/equipe/${encodeURIComponent(fixture.home_team)}`)
                                    }}
                                >
                                    {fixture?.home_team}
                                </p>
                                {sj?.severe_fatigue_home && (
                                    <Badge variant="outline" className="text-xs px-1 py-0 h-4 border-red-500/30 text-red-500 whitespace-nowrap">
                                        ⚠️ Calendrier
                                    </Badge>
                                )}
                            </div>
                            {fixture?.home_goals != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.home_goals}</p>
                            )}
                        </div>
                        <div className="shrink-0 text-center">
                            {["1H", "2H", "HT", "ET", "P", "LIVE"].includes(fixture?.status) ? (
                                <Badge variant="destructive" className="text-xs px-2 py-1 animate-pulse">
                                    {fixture.status === "HT" ? "MI-TEMPS"
                                        : fixture.elapsed ? `${fixture.elapsed}'`
                                            : "LIVE"}
                                </Badge>
                            ) : ["FT", "AET", "PEN"].includes(fixture?.status) ? (
                                <Badge className="text-xs px-2 py-1 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-0">
                                    Terminé
                                </Badge>
                            ) : (
                                <span className="text-sm font-bold text-muted-foreground/40">VS</span>
                            )}
                        </div>
                        <div className="flex-1 text-center">
                            {fixture?.away_logo && (
                                <img src={fixture.away_logo} alt="" role="presentation" className="w-10 h-10 mx-auto mb-1 object-contain" />
                            )}
                            <div className="flex items-center justify-center gap-1.5 flex-wrap">
                                <p
                                    className="text-xl font-black leading-tight cursor-pointer hover:underline hover:text-primary transition-colors"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        if (fixture?.away_team) navigate(`/equipe/${encodeURIComponent(fixture.away_team)}`)
                                    }}
                                >
                                    {fixture?.away_team}
                                </p>
                                {sj?.severe_fatigue_away && (
                                    <Badge variant="outline" className="text-xs px-1 py-0 h-4 border-red-500/30 text-red-500 whitespace-nowrap">
                                        ⚠️ Calendrier
                                    </Badge>
                                )}
                            </div>
                            {fixture?.away_goals != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.away_goals}</p>
                            )}
                        </div>
                    </div>
                </div>

            </Card>

            {/* True Value Bet Banner (Football) */}
            {(() => {
                if (!p?.value_edges || Object.keys(p.value_edges).length === 0) return null;

                // Find highest edge
                const edges = p.value_edges;
                const odds = p.odds || fixture?.odds || {};
                let bestKey = null;
                let maxEdge = 0;

                for (const [k, v] of Object.entries(edges)) {
                    if (v > maxEdge) {
                        maxEdge = v;
                        bestKey = k;
                    }
                }

                if (!bestKey) return null;

                const nameMap = {
                    "home": `Victoire ${fixture?.home_team}`,
                    "away": `Victoire ${fixture?.away_team}`,
                    "draw": "Match Nul",
                    "over_25": "Plus de 2.5 Buts",
                    "under_25": "Moins de 2.5 Buts",
                    "btts_yes": "Les 2 équipes marquent : Oui",
                    "btts_no": "Les 2 équipes marquent : Non",
                };

                const oddMap = {
                    "home": odds.home_win_odds,
                    "away": odds.away_win_odds,
                    "draw": odds.draw_odds,
                    "over_25": odds.over_25_odds,
                    "under_25": odds.under_25_odds,
                    "btts_yes": odds.btts_yes_odds,
                    "btts_no": odds.btts_no_odds,
                };

                return (
                    <Card className="border-emerald-500/50 bg-emerald-500/10 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <CardHeader className="py-2.5 px-4 flex flex-row items-center justify-between border-b border-emerald-500/20">
                            <CardTitle className="text-[13px] uppercase tracking-wider font-bold flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                                <Target className="w-4 h-4" />
                                True Value Bet
                            </CardTitle>
                            <Badge className="border-emerald-500 text-emerald-700 bg-emerald-500/20 hover:bg-emerald-500/30">
                                Edge: +{maxEdge}%
                            </Badge>
                        </CardHeader>
                        <CardContent className="p-4 flex items-center justify-between">
                            <div>
                                <p className="text-base font-bold text-foreground">{nameMap[bestKey] || bestKey}</p>
                                <p className="text-xs text-muted-foreground mt-0.5">Avantage mathématique sur le bookmaker</p>
                            </div>
                            <div className="text-right">
                                <p className="text-xs uppercase font-bold text-muted-foreground mb-0.5">Cote Réelle</p>
                                <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                                    @ {formatOdds(oddMap[bestKey] ?? null)}
                                </span>
                            </div>
                        </CardContent>
                    </Card>
                )
            })()}

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

            {/* Match Events — Goals Timeline */}
            {(() => {
                const events = (fixture?.events_json || []).filter(e => {
                    if (!e.player) return false
                    if (e.comments === 'Penalty Shootout') return false
                    if (e.time >= 120 && !e.extra_time) return false
                    return true
                })
                if (!events.length) return null

                return (
                    <Card className="border-border/50">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                ⚽ Événements du match
                                <Badge className="ml-auto text-xs border-0 bg-muted text-muted-foreground">
                                    {events.length} but{events.length > 1 ? 's' : ''}
                                </Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-0">
                                {events.map((goal, idx) => {
                                    const isHome = goal.team === fixture?.home_team
                                    const timeStr = goal.extra_time
                                        ? `${goal.time}+${goal.extra_time}'`
                                        : `${goal.time}'`
                                    const typeLabel = goal.detail === "Penalty" ? " (P)"
                                        : goal.detail === "Own Goal" ? " (CSC)"
                                            : ""

                                    return (
                                        <div
                                            key={idx}
                                            className={cn(
                                                "flex items-start gap-3 py-2.5 border-b border-border/20 last:border-0",
                                                "pl-3 border-l-2",
                                                isHome ? "border-l-primary" : "border-l-blue-400"
                                            )}
                                        >
                                            <div className="w-10 shrink-0 text-center">
                                                <span className="text-xs font-bold text-muted-foreground">{timeStr}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p
                                                    className="text-sm font-bold truncate"
                                                >
                                                    ⚽ {goal.player || "Inconnu"}
                                                    <span className="text-muted-foreground font-normal text-xs">{typeLabel}</span>
                                                </p>
                                                {goal.assist && (
                                                    <p
                                                        className="text-xs text-muted-foreground truncate"
                                                    >
                                                        🎯 {goal.assist}
                                                    </p>
                                                )}
                                            </div>
                                            <span className="text-xs font-medium text-muted-foreground shrink-0">
                                                {goal.team}
                                            </span>
                                        </div>
                                    )
                                })}
                            </div>
                        </CardContent>
                    </Card>
                )
            })()}

            {/* Lineups — H-1 avant le match */}
            {(() => {
                const lineups = fixture?.stats_json?.lineups
                if (!lineups || (!lineups.home && !lineups.away)) return null
                const h = lineups.home || {}
                const a = lineups.away || {}

                return (
                    <Card className="border-border/50">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                🧤 Compositions officielles
                                {h.formation && a.formation && (
                                    <Badge variant="outline" className="ml-auto text-xs border-border/40 text-muted-foreground">
                                        {h.formation} — {a.formation}
                                    </Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 gap-3">
                                {[
                                    { side: h, label: fixture?.home_team, color: "text-primary" },
                                    { side: a, label: fixture?.away_team, color: "text-blue-500" }
                                ].map(({ side, label, color }, idx) => (
                                    <div key={idx}>
                                        <p className={`text-xs font-bold mb-1 truncate ${color}`}>{label}</p>
                                        {side.coach && (
                                            <p className="text-xs text-muted-foreground mb-2">👔 {side.coach}</p>
                                        )}
                                        <div className="space-y-1">
                                            {(side.starters || []).map((p, i) => (
                                                <div key={i} className="flex items-center gap-1.5">
                                                    <span className="text-xs w-5 text-right text-muted-foreground font-mono shrink-0">
                                                        {p.number}
                                                    </span>
                                                    <span
                                                        className="text-xs truncate"
                                                    >
                                                        {p.name}
                                                    </span>
                                                    {p.pos && (
                                                        <span className="text-xs text-muted-foreground shrink-0 ml-auto">
                                                            {p.pos}
                                                        </span>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )
            })()}

            {/* Live Match Stats */}
            {(() => {
                const ls = fixture?.live_stats_json
                if (!ls || (!ls.home && !ls.away)) return null
                const h = ls.home || {}
                const a = ls.away || {}

                const StatBar = ({ label, home, away, unit = "" }) => {
                    const hVal = home ?? 0
                    const aVal = away ?? 0
                    const total = hVal + aVal || 1
                    const hPct = (hVal / total) * 100
                    const aPct = (aVal / total) * 100
                    const hDisplay = unit ? `${home}${unit}` : home ?? "–"
                    const aDisplay = unit ? `${away}${unit}` : away ?? "–"
                    return (
                        <div className="py-2 border-b border-border/20 last:border-0">
                            <div className="flex justify-between text-xs font-bold mb-1">
                                <span>{hDisplay}</span>
                                <span className="text-muted-foreground text-xs font-medium">{label}</span>
                                <span>{aDisplay}</span>
                            </div>
                            <div className="flex gap-0.5 h-1.5 rounded-full overflow-hidden bg-muted/40">
                                <div className="bg-primary rounded-l-full transition-all" style={{ width: `${hPct}%` }} />
                                <div className="bg-blue-400 rounded-r-full transition-all" style={{ width: `${aPct}%` }} />
                            </div>
                        </div>
                    )
                }

                return (
                    <Card className="border-border/50">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                📊 Statistiques en direct
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-0">
                            <StatBar label="Possession" home={h.possession} away={a.possession} />
                            {(h.xg || a.xg) && <StatBar label="xG (Expected Goals)" home={h.xg} away={a.xg} />}
                            <StatBar label="Tirs (total)" home={h.shots_total} away={a.shots_total} />
                            <StatBar label="Tirs cadrés" home={h.shots_on} away={a.shots_on} />
                            <StatBar label="Corners" home={h.corners} away={a.corners} />
                            <StatBar label="Fautes" home={h.fouls} away={a.fouls} />
                            <StatBar label="Hors-jeu" home={h.offsides} away={a.offsides} />
                            {(h.yellow > 0 || a.yellow > 0) && (
                                <StatBar label="🟨 Cartons jaunes" home={h.yellow} away={a.yellow} />
                            )}
                            {(h.red > 0 || a.red > 0) && (
                                <StatBar label="🟥 Cartons rouges" home={h.red} away={a.red} />
                            )}
                        </CardContent>
                    </Card>
                )
            })()}

            {/* xG — PREMIUM (moved above Markets for better hierarchy) */}
            <PremiumSection title="Expected Goals (xG)" icon={TrendingUp}>
                <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-accent/30 rounded-xl">
                        <p className="text-xs text-muted-foreground mb-1">{fixture?.home_team}</p>
                        <p className="text-2xl font-black text-primary">{xg_home ?? "—"}</p>
                        <p className="text-xs text-muted-foreground">xG domicile</p>
                    </div>
                    <div className="text-center p-3 bg-accent/30 rounded-xl">
                        <p className="text-xs text-muted-foreground mb-1">{fixture?.away_team}</p>
                        <p className="text-2xl font-black text-primary">{xg_away ?? "—"}</p>
                        <p className="text-xs text-muted-foreground">xG extérieur</p>
                    </div>
                </div>
            </PremiumSection>

            {/* Marchés — PREMIUM */}
            <PremiumSection title="Marchés & Statistiques" icon={Target}>
                <div className="space-y-0">
                    <StatRow
                        label="Les deux équipes marquent (BTTS)"
                        value={proba_btts}
                        tooltip="Probabilité que l'équipe à domicile ET l'équipe à l'extérieur marquent au moins un but (Both Teams To Score)."
                    />
                    <StatRow
                        label="Plus de 0.5 buts"
                        value={proba_over_05}
                        tooltip="Probabilité d'avoir au moins 1 but au total dans le match."
                    />
                    <StatRow
                        label="Plus de 1.5 buts"
                        value={proba_over_15}
                        tooltip="Probabilité d'avoir au moins 2 buts au total dans le match."
                    />
                    <StatRow
                        label="Plus de 2.5 buts"
                        value={proba_over_25}
                        tooltip="Probabilité d'avoir au moins 3 buts au total dans le match. Souvent appelé 'Over 2.5'."
                    />
                    <StatRow
                        label="Plus de 3.5 buts"
                        value={proba_over_35}
                        tooltip="Probabilité d'avoir au moins 4 buts au total dans le match."
                    />
                </div>
            </PremiumSection>

            {/* Buteurs probables — PREMIUM */}
            <PremiumSection title="Buteurs probables" icon={Users}>
                {scorers.length > 0 ? (
                    <div className="space-y-2">
                        {scorers.slice(0, 3).map((s, i) => {
                            const regress = s.xg_regression || 1.0;
                            const broken = s.synergy_broken || false;

                            return (
                                <div
                                    key={i}
                                    className="flex items-center justify-between py-2 border-b border-border/30 last:border-0"
                                >
                                    <div className="flex items-center gap-3">
                                        {s.photo ? (
                                            <img src={s.photo} alt={s.name} className="w-8 h-8 rounded-full object-cover border border-border/50 shrink-0" />
                                        ) : (
                                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0 border border-border/50">
                                                {i + 1}
                                            </div>
                                        )}
                                        <div className="min-w-0">
                                            <p className="text-sm font-semibold leading-tight truncate">{s.player_name || s.name}</p>
                                            <div className="flex items-center gap-1.5 flex-wrap mt-0.5">
                                                {s.team && <p className="text-xs text-muted-foreground mr-1 shrink-0">{s.team}</p>}
                                                {regress > 1.05 && (
                                                    <Badge variant="outline" className="text-xs px-1 py-0 h-4 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                                                        🎯 Rebond xG
                                                    </Badge>
                                                )}
                                                {regress < 0.95 && (
                                                    <Badge variant="outline" className="text-xs px-1 py-0 h-4 border-red-500/30 text-red-500 whitespace-nowrap">
                                                        📉 Sur-régime
                                                    </Badge>
                                                )}
                                                {broken && (
                                                    <Badge variant="outline" className="text-xs px-1 py-0 h-4 border-amber-500/30 text-amber-600 dark:text-amber-400 whitespace-nowrap">
                                                        ⚡ Synergie Brisée
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <Badge className="bg-primary/10 text-primary border-0 font-bold ml-2 shrink-0">
                                        {s.probability ?? s.proba ?? s.prob ?? "—"}%
                                    </Badge>
                                </div>
                            )
                        })}
                        {scorers.length > 3 && (
                            <p className="text-xs text-muted-foreground text-center pt-1">
                                et {scorers.length - 3} autre{scorers.length - 3 > 1 ? "s" : ""} buteur{scorers.length - 3 > 1 ? "s" : ""} probable{scorers.length - 3 > 1 ? "s" : ""}
                            </p>
                        )}
                    </div>
                ) : (
                    <p className="text-sm text-muted-foreground text-center py-2">Données non disponibles</p>
                )}
            </PremiumSection>

            {/* Analyse approfondie — PREMIUM */}
            <PremiumSection title="Analyse approfondie" icon={BrainCircuit}>
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
