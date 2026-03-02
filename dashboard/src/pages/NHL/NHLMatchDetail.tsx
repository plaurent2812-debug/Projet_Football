import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
    ArrowLeft, Lock, Trophy, BrainCircuit,
    Target, Users, Zap, Star, ChevronLeft, ChevronRight
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth"
import { fetchNHLMatchTopPlayers } from "@/lib/api"
import { supabase } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

/* ── Player Row ────────────────────────────────────────────── */
function PlayerRow({ rank, player }) {
    // Sharp Analytics Indicators
    const reliance = player.pp_reliance || 0
    const fatigue = player.fatigue_penalty || 1.0
    const regress = player.sh_pct_regression || 1.0

    return (
        <div className="flex items-center gap-3 py-2.5 border-b border-border/30 last:border-0">
            <div className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0",
                rank === 1 ? "bg-amber-500/20 text-amber-600 dark:text-amber-400" :
                    rank === 2 ? "bg-slate-400/20 text-slate-600 dark:text-slate-400" :
                        rank === 3 ? "bg-orange-700/20 text-orange-700 dark:text-orange-400" :
                            "bg-muted text-muted-foreground"
            )}>
                {rank}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{player.player_name}</p>
                <div className="flex items-center gap-1.5 flex-wrap mt-0.5">
                    <p className="text-[10px] text-muted-foreground">{player.team}</p>
                    {reliance > 0.35 && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-amber-500/30 text-amber-600 dark:text-amber-400">
                            ⚡ PP1
                        </Badge>
                    )}
                    {fatigue < 1.0 && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-red-500/30 text-red-500">
                            {fatigue < 0.90 ? "⚠️ 3-in-4" : "⚠️ B2B"}
                        </Badge>
                    )}
                    {regress > 1.05 && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                            🎯 Due
                        </Badge>
                    )}
                    {regress < 0.95 && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-red-500/30 text-red-500">
                            📉 Sur-régime
                        </Badge>
                    )}
                </div>
            </div>
            <Badge className="bg-primary/10 text-primary border-0 font-bold shrink-0">
                {player.prob}%
            </Badge>
        </div>
    )
}

/* ── Premium Tab Content ───────────────────────────────────── */
function PremiumTabContent({ players, emptyMsg }) {
    const { isPremium, isAdmin } = useAuth()
    const navigate = useNavigate()

    if (!isPremium && !isAdmin) {
        return (
            <div className="relative">
                <div className="premium-blur select-none pointer-events-none space-y-2 py-2">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="flex items-center gap-3 py-2.5">
                            <div className="w-7 h-7 rounded-full bg-muted" />
                            <div className="flex-1 space-y-1">
                                <div className="h-3 bg-muted rounded w-32" />
                                <div className="h-2 bg-muted rounded w-16" />
                            </div>
                            <div className="w-12 h-5 bg-muted rounded" />
                        </div>
                    ))}
                </div>
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-card/60 backdrop-blur-[2px] rounded-xl">
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
            </div>
        )
    }

    if (!players?.length) return <p className="text-sm text-muted-foreground text-center py-6">{emptyMsg}</p>

    return (
        <div>
            {players.map((p, i) => <PlayerRow key={p.player_id || i} rank={i + 1} player={p} />)}
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════
   NHL Match Detail Page
   ═══════════════════════════════════════════════════════════ */
export default function NHLMatchDetailPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const { isPremium, isAdmin } = useAuth()
    const [fixture, setFixture] = useState(null)
    const [topPlayers, setTopPlayers] = useState(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState("point")
    const [adjacent, setAdjacent] = useState({ prev: null, next: null })

    useEffect(() => {
        // Fetch fixture from Supabase
        supabase
            .from('nhl_fixtures')
            .select('*')
            .or(`api_fixture_id.eq.${id},id.eq.${id}`)
            .limit(1)
            .then(({ data }) => {
                if (data?.[0]) setFixture(data[0])
            })
            .catch(console.error)

        // Fetch top players
        fetchNHLMatchTopPlayers(id)
            .then(setTopPlayers)
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [id])

    useEffect(() => {
        if (!fixture?.date) return
        const d = new Date(fixture.date)
        const start = new Date(d); start.setHours(0, 0, 0, 0)
        const end = new Date(d); end.setHours(23, 59, 59, 999)

        supabase
            .from('nhl_fixtures')
            .select('id, api_fixture_id')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .order('date', { ascending: true })
            .then(({ data }) => {
                const matches = data || []
                // Find index by checking both id and api_fixture_id
                const idx = matches.findIndex(m =>
                    String(m.id) === String(id) || String(m.api_fixture_id) === String(id)
                )
                if (idx > -1) {
                    setAdjacent({
                        prev: idx > 0 ? matches[idx - 1].id : null,
                        next: idx < matches.length - 1 ? matches[idx + 1].id : null
                    })
                }
            })
            .catch(console.error)
    }, [fixture?.date, id])

    if (loading) return (
        <div className="flex items-center justify-center py-32">
            <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
    )

    const time = fixture?.date
        ? new Date(fixture.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
        : "—"
    const dateStr = fixture?.date
        ? new Date(fixture.date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
        : ""

    const players = topPlayers?.top_players || {}
    const homeProb = fixture?.home_win_prob ?? fixture?.proba_home
    const awayProb = fixture?.away_win_prob ?? fixture?.proba_away
    const confidence = fixture?.confidence_score
    const recommendedBet = fixture?.recommended_bet

    // Calculate Value Bet
    let valueBet = null
    if (fixture?.odds_json?.bookmakers) {
        let homeOdd = 0; let awayOdd = 0;
        for (const bm of fixture.odds_json.bookmakers) {
            for (const bet of (bm.bets || [])) {
                if ([1, 2].includes(bet.id) || ["Home/Away", "Match Winner"].includes(bet.name)) {
                    for (const val of (bet.values || [])) {
                        if (val.value === "Home") homeOdd = parseFloat(val.odd);
                        if (val.value === "Away") awayOdd = parseFloat(val.odd);
                    }
                }
            }
            if (homeOdd > 0) break;
        }

        if (homeOdd > 0 && homeProb > 0) {
            const edge = homeProb - (100 / homeOdd);
            if (edge >= 3) {
                valueBet = { team: fixture.home_team, type: "Victoire", odd: homeOdd, edge: edge.toFixed(1) }
            }
        }
        if (awayOdd > 0 && awayProb > 0) {
            const edge = awayProb - (100 / awayOdd);
            if (edge >= 3 && (!valueBet || edge > parseFloat(valueBet.edge))) {
                valueBet = { team: fixture.away_team, type: "Victoire", odd: awayOdd, edge: edge.toFixed(1) }
            }
        }
    }

    return (
        <div className="max-w-2xl mx-auto space-y-4 animate-fade-in-up pb-12">

            {/* Back & Navigation */}
            <div className="flex items-center justify-between mb-2">
                <button
                    onClick={() => navigate('/nhl')}
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Retour aux matchs NHL
                </button>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 rounded-full bg-card"
                        disabled={!adjacent.prev}
                        onClick={() => adjacent.prev && navigate(`/nhl/match/${adjacent.prev}`)}
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 rounded-full bg-card"
                        disabled={!adjacent.next}
                        onClick={() => adjacent.next && navigate(`/nhl/match/${adjacent.next}`)}
                    >
                        <ChevronRight className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            {/* Match header */}
            <Card className="border-border/50 overflow-hidden">
                <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-5 py-4 border-b border-border/30">
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">NHL</span>
                        <span className="text-xs text-muted-foreground capitalize">{dateStr} · {time}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4 mt-3">
                        <div className="flex-1 text-center">
                            <p className="text-xl font-black">{fixture?.home_team || "—"}</p>
                            {fixture?.home_score != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.home_score}</p>
                            )}
                            {homeProb != null && (
                                <p className="text-sm font-bold text-primary mt-1">{homeProb}%</p>
                            )}
                        </div>
                        <div className="shrink-0 text-center">
                            <span className="text-sm font-bold text-muted-foreground/40">VS</span>
                        </div>
                        <div className="flex-1 text-center">
                            <p className="text-xl font-black">{fixture?.away_team || "—"}</p>
                            {fixture?.away_score != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.away_score}</p>
                            )}
                            {awayProb != null && (
                                <p className="text-sm font-bold text-primary mt-1">{awayProb}%</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Pari recommandé + confiance — FREE */}
                <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-xs text-muted-foreground mb-1">Pari recommandé</p>
                            <p className="text-base font-bold text-primary">{recommendedBet || "—"}</p>
                        </div>
                        {confidence != null && (
                            <div className="text-center">
                                <p className="text-xs text-muted-foreground mb-1">Confiance</p>
                                <div className={cn(
                                    "text-2xl font-black",
                                    confidence >= 8 ? "text-emerald-600 dark:text-emerald-400" :
                                        confidence >= 6 ? "text-amber-600 dark:text-amber-400" :
                                            "text-foreground"
                                )}>
                                    {confidence}<span className="text-sm text-muted-foreground font-normal">/10</span>
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* True Value Bet Banner */}
            {valueBet && (
                <Card className="border-emerald-500/50 bg-emerald-500/10 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
                    <CardHeader className="py-2.5 px-4 flex flex-row items-center justify-between border-b border-emerald-500/20">
                        <CardTitle className="text-[13px] uppercase tracking-wider font-bold flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                            <Target className="w-4 h-4" />
                            True Value Bet
                        </CardTitle>
                        <Badge className="border-emerald-500 text-emerald-700 bg-emerald-500/20 hover:bg-emerald-500/30">
                            Edge: +{valueBet.edge}%
                        </Badge>
                    </CardHeader>
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <p className="text-base font-bold text-foreground">{valueBet.type} {valueBet.team}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">Avantage mathématique sur le bookmaker</p>
                        </div>
                        <div className="text-right">
                            <p className="text-[10px] uppercase font-bold text-muted-foreground mb-0.5">Cote Réelle</p>
                            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                                @ {valueBet.odd.toFixed(2)}
                            </span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Post-Match: Predictions vs Results */}
            {(() => {
                const isFinished = ["FT", "Final", "FINAL", "OFF"].includes(fixture?.status)
                if (!isFinished || fixture?.home_score == null) return null

                const hg = fixture.home_score
                const ag = fixture.away_score
                const predictions = fixture?.predictions_json || {}
                const predHome = homeProb ?? predictions.proba_home
                const predAway = awayProb ?? predictions.proba_away

                // Determine predicted and actual winner
                const predicted = predHome > predAway ? "home" : "away"
                const actual = hg > ag ? "home" : ag > hg ? "away" : "draw"
                const predCorrect = predicted === actual

                const predictedLabel = predicted === "home" ? fixture.home_team : fixture.away_team
                const actualLabel = actual === "home" ? fixture.home_team : actual === "away" ? fixture.away_team : "Match nul"

                return (
                    <Card className={cn(
                        "border overflow-hidden",
                        predCorrect ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"
                    )}>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                {predCorrect ? "✅" : "❌"} Bilan du Match
                                <Badge className={cn(
                                    "ml-auto text-[10px] border-0",
                                    predCorrect
                                        ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                                        : "bg-red-500/10 text-red-500"
                                )}>
                                    {predCorrect ? "Prédiction correcte" : "Prédiction incorrecte"}
                                </Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {/* Predicted vs Actual */}
                            <div className="grid grid-cols-2 gap-3">
                                <div className="p-3 rounded-lg bg-card border border-border/30">
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold mb-1">Prédit</p>
                                    <p className="text-sm font-bold">{predictedLabel}</p>
                                    {predHome != null && (
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {fixture.home_team} {predHome}% — {fixture.away_team} {predAway}%
                                        </p>
                                    )}
                                </div>
                                <div className="p-3 rounded-lg bg-card border border-border/30">
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold mb-1">Résultat</p>
                                    <p className="text-sm font-bold">{actualLabel}</p>
                                    <p className="text-lg font-black text-primary mt-0.5">
                                        {hg} - {ag}
                                    </p>
                                </div>
                            </div>

                            {/* Score breakdown */}
                            <div className="text-xs text-muted-foreground text-center pt-1 border-t border-border/30">
                                Score final: <span className="font-bold text-foreground">{fixture.home_team} {hg}</span> — <span className="font-bold text-foreground">{fixture.away_team} {ag}</span>
                            </div>
                        </CardContent>
                    </Card>
                )
            })()}

            {/* Match Events — Goals Timeline */}
            {(() => {
                const goals = fixture?.stats_json?.goals || []
                if (!goals.length) return null

                const periodMap = { "1": "1ère", "2": "2ème", "3": "3ème", "OT": "Prol.", "SO": "Tirs" }

                return (
                    <Card className="border-border/50">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                🏒 Événements du match
                                <Badge className="ml-auto text-[10px] border-0 bg-muted text-muted-foreground">
                                    {goals.length} but{goals.length > 1 ? 's' : ''}
                                </Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-0">
                                {goals.map((goal, idx) => {
                                    const isHome = goal.team?.toLowerCase().includes(fixture?.home_team?.split(' ').pop()?.toLowerCase())
                                    const periodStr = periodMap[goal.period] || goal.period || ""
                                    const timeStr = goal.minute ? `${goal.minute}'` : ""
                                    const typeLabel = goal.comment && goal.comment !== "" ? ` (${goal.comment})` : ""

                                    return (
                                        <div
                                            key={idx}
                                            className={cn(
                                                "flex items-start gap-3 py-2.5 border-b border-border/20 last:border-0",
                                                "pl-3 border-l-2",
                                                isHome ? "border-l-primary" : "border-l-red-500"
                                            )}
                                        >
                                            <div className="w-10 shrink-0 text-center">
                                                <span className="text-[10px] font-bold text-muted-foreground block">{periodStr}</span>
                                                {timeStr && <span className="text-[10px] text-muted-foreground/60">{timeStr}</span>}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-bold truncate">
                                                    ⚽ {goal.player || "Inconnu"}
                                                    <span className="text-muted-foreground font-normal text-xs">{typeLabel}</span>
                                                </p>
                                                {goal.assists?.length > 0 && (
                                                    <p className="text-[10px] text-muted-foreground truncate">
                                                        🎯 {goal.assists.join(', ')}
                                                    </p>
                                                )}
                                            </div>
                                            <span className="text-[10px] font-medium text-muted-foreground shrink-0">
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

            {/* Top Players — 4 tabs */}
            <Card className="border-border/50">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <Users className="w-4 h-4 text-primary" />
                        Top 5 Joueurs
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="grid grid-cols-4 h-9 mb-4">
                            <TabsTrigger value="point" className="text-xs">
                                <Star className="w-3 h-3 mr-1" />Points
                            </TabsTrigger>
                            <TabsTrigger value="goal" className="text-xs">
                                🥅 Buts
                            </TabsTrigger>
                            <TabsTrigger value="assist" className="text-xs">
                                🎯 Passes
                            </TabsTrigger>
                            <TabsTrigger value="sog" className="text-xs">
                                🏒 Tirs
                            </TabsTrigger>
                        </TabsList>

                        {/* Points — FREE */}
                        <TabsContent value="point">
                            {players.point?.length ? (
                                players.point.map((p, i) => <PlayerRow key={p.player_id || i} rank={i + 1} player={p} />)
                            ) : (
                                <p className="text-sm text-muted-foreground text-center py-6">Données non disponibles</p>
                            )}
                        </TabsContent>

                        {/* Buteurs — PREMIUM */}
                        <TabsContent value="goal">
                            <PremiumTabContent players={players.goal} emptyMsg="Données non disponibles" />
                        </TabsContent>

                        {/* Passeurs — PREMIUM */}
                        <TabsContent value="assist">
                            <PremiumTabContent players={players.assist} emptyMsg="Données non disponibles" />
                        </TabsContent>

                        {/* SOG — PREMIUM */}
                        <TabsContent value="sog">
                            <PremiumTabContent players={players.sog} emptyMsg="Données non disponibles" />
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>

            {/* Analyse IA — PREMIUM */}
            {(() => {
                const analysis = fixture?.analysis_text
                if (!isPremium && !isAdmin) {
                    return (
                        <Card className="border-amber-500/20 bg-gradient-to-b from-card to-amber-500/3 overflow-hidden">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-bold flex items-center gap-2">
                                    <BrainCircuit className="w-4 h-4 text-muted-foreground" />
                                    Analyse IA
                                    <Lock className="w-3.5 h-3.5 text-amber-500 ml-auto" />
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="relative">
                                <div className="premium-blur select-none pointer-events-none">
                                    <p className="text-sm text-foreground/80 leading-relaxed">
                                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
                                    </p>
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
                return (
                    <Card className="border-border/50">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-bold flex items-center gap-2">
                                <BrainCircuit className="w-4 h-4 text-primary" />
                                Analyse IA
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-sm text-foreground/80 leading-relaxed">
                                {analysis || "Analyse en cours de génération..."}
                            </p>
                        </CardContent>
                    </Card>
                )
            })()}

            {/* Disclaimer */}
            <p className="disclaimer-text text-center px-4">
                Les probabilités affichées sont calculées par des modèles statistiques à titre informatif uniquement.
                Elles ne constituent pas des conseils de paris. Jouez de manière responsable. 18+
            </p>
        </div>
    )
}
