import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
    ArrowLeft, Lock, Trophy, BrainCircuit,
    Target, Users, Zap, Star
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
                <p className="text-[10px] text-muted-foreground">{player.team}</p>
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

    return (
        <div className="max-w-2xl mx-auto space-y-4 animate-fade-in-up pb-12">

            {/* Back */}
            <button
                onClick={() => navigate('/nhl')}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Retour aux matchs NHL
            </button>

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
                            {fixture?.home_goals != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.home_goals}</p>
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
                            {fixture?.away_goals != null && (
                                <p className="text-3xl font-black text-primary mt-1">{fixture.away_goals}</p>
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
