import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { fetchTeamHistory, fetchTeamRoster } from "@/lib/api"
import {
    ArrowLeft, Calendar, Trophy, TrendingUp, TrendingDown, Minus,
    Activity, MapPin, Shield, Users
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/lib/auth"
import { Lock } from "lucide-react"

/* ── Login Blur Component ──────────────────────────────────── */
function LoginBlur({ children }) {
    return (
        <div className="relative overflow-hidden rounded-xl border border-border/50 bg-card/30">
            <div className="filter blur-md select-none pointer-events-none opacity-50">
                {children}
            </div>
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/10 backdrop-blur-[2px] z-10">
                <div className="p-3 rounded-full bg-primary/10 text-primary mb-2 ring-1 ring-primary/20">
                    <Lock className="w-5 h-5" />
                </div>
                <p className="text-sm font-bold text-foreground">Connectez-vous pour voir l'historique</p>
                <button className="mt-3 px-4 py-1.5 text-xs font-semibold bg-primary text-primary-foreground rounded-full hover:bg-primary/90 transition-colors">
                    Se connecter
                </button>
            </div>
        </div>
    )
}

/* ── Result Badge ──────────────────────────────────────────── */
function ResultBadge({ result }) {
    const styles = {
        V: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
        N: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
        D: "bg-red-500/10 text-red-400 ring-red-500/20",
    }
    const labels = { V: "Victoire", N: "Nul", D: "Défaite" }

    return (
        <span className={cn(
            "inline-flex items-center justify-center w-8 h-8 rounded-full ring-1 text-xs font-black",
            styles[result] || "bg-zinc-500/10 text-zinc-400 ring-zinc-500/20"
        )}>
            {result}
        </span>
    )
}

/* ═══════════════════════════════════════════════════════════
   Team Profile Page
   ═══════════════════════════════════════════════════════════ */
export default function TeamProfile() {
    const { hasAccess } = useAuth()
    const { name } = useParams() // Team name from URL
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState("historique")
    const [data, setData] = useState(null)
    const [roster, setRoster] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        setLoading(true)
        Promise.all([
            fetchTeamHistory(name),
            fetchTeamRoster(name).catch(() => ({ roster: [] }))
        ])
            .then(([historyData, rosterData]) => {
                setData(historyData)
                setRoster(rosterData.roster || [])
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false))
    }, [name])

    if (loading) {
        return (
            <div className="flex items-center justify-center py-32">
                <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                <div className="p-4 rounded-full bg-red-500/10 text-red-400">
                    <Shield className="w-8 h-8" />
                </div>
                <h2 className="text-xl font-bold">Erreur</h2>
                <p className="text-muted-foreground">{error}</p>
                <button
                    onClick={() => navigate(-1)}
                    className="text-sm font-semibold text-primary hover:underline"
                >
                    Retour
                </button>
            </div>
        )
    }

    if (!data) return null

    const { summary, matches } = data

    return (
        <div className="space-y-8 pb-12">
            {/* Header */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => navigate(-1)}
                    className="p-2 rounded-lg hover:bg-card transition-colors"
                >
                    <ArrowLeft className="w-5 h-5 text-muted-foreground" />
                </button>
                <div>
                    <h1 className="text-3xl font-black tracking-tight">{data.team_name}</h1>
                    <p className="text-sm text-muted-foreground">
                        Saison {import.meta.env.VITE_API_SEASON || "2025-2026"}
                    </p>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-border/40 pb-px">
                <button
                    onClick={() => setActiveTab("historique")}
                    className={cn(
                        "px-4 py-2 text-sm font-bold border-b-2 transition-colors",
                        activeTab === "historique"
                            ? "border-primary text-foreground"
                            : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                    )}
                >
                    <Calendar className="w-4 h-4 inline-block mr-2" />
                    Historique
                </button>
                <button
                    onClick={() => setActiveTab("effectif")}
                    className={cn(
                        "px-4 py-2 text-sm font-bold border-b-2 transition-colors flex items-center gap-2",
                        activeTab === "effectif"
                            ? "border-primary text-foreground"
                            : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                    )}
                >
                    <Users className="w-4 h-4 inline-block" />
                    Effectif
                    {roster.length > 0 && (
                        <span className="text-[10px] bg-secondary text-secondary-foreground px-1.5 py-0.5 rounded-full">
                            {roster.length}
                        </span>
                    )}
                </button>
            </div>

            {/* Summary Stats & History - Protected */}
            {hasAccess('free') ? (
                <>
                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <Card className="bg-card/50 border-border/50">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                                    <Activity className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{summary.total}</p>
                                    <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Matchs</p>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="bg-card/50 border-border/50">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                                    <Trophy className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{summary.wins}</p>
                                    <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Victoires</p>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="bg-card/50 border-border/50">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                                    <Minus className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{summary.draws}</p>
                                    <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Nuls</p>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="bg-card/50 border-border/50">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
                                    <TrendingDown className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black tabular-nums">{summary.losses}</p>
                                    <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Défaites</p>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Current Streak */}


                    {/* Tab Content */}
                    {activeTab === "historique" && (
                        <div className="rounded-xl border border-border/40 overflow-hidden bg-card/30">
                            <div className="grid grid-cols-[auto_1fr_auto_auto] gap-4 p-3 bg-muted/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border/40">
                                <span className="pl-2">Résultat</span>
                                <span>Adversaire</span>
                                <span className="text-center">Score</span>
                                <span className="pr-2">Date</span>
                            </div>
                            <div className="divide-y divide-border/30">
                                {matches.map((m, i) => (
                                    <div
                                        key={i}
                                        className={cn(
                                            "grid grid-cols-[auto_1fr_auto_auto] items-center gap-4 p-3 transition-colors",
                                            m.fixture_id ? "cursor-pointer hover:bg-accent/40" : "hover:bg-card/50"
                                        )}
                                        onClick={() => m.fixture_id && navigate(`/football/match/${m.fixture_id}`)}
                                    >
                                        <div className="pl-2">
                                            <ResultBadge result={m.result} />
                                        </div>
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="font-bold text-sm truncate">{m.opponent}</span>
                                                <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-secondary text-muted-foreground font-medium">
                                                    {m.home_away === 'D' ? 'DOM' : 'EXT'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="font-mono font-bold text-sm tabular-nums text-center px-2">
                                            {m.score}
                                        </div>
                                        <div className="pr-2 text-xs text-muted-foreground tabular-nums flex items-center gap-1.5">
                                            <Calendar className="w-3 h-3" />
                                            {m.date}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeTab === "effectif" && (
                        <div className="space-y-4">
                            {!roster.length ? (
                                <div className="text-center py-12 border border-dashed rounded-xl border-border/60 bg-card/20 text-muted-foreground text-sm font-medium">
                                    Aucun effectif disponible pour le moment.
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {roster.map((player) => (
                                        <div
                                            key={player.id}
                                            className="flex items-center gap-3 p-3 rounded-lg border border-border/40 bg-card transition-all"
                                        >
                                            {player.photo ? (
                                                <img src={player.photo} alt={player.name} className="w-10 h-10 rounded-full object-cover border border-border bg-muted shrink-0" />
                                            ) : (
                                                <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-secondary-foreground font-bold shrink-0 text-sm">
                                                    {player.name.charAt(0)}
                                                </div>
                                            )}
                                            <div className="min-w-0 flex-1">
                                                <div className="font-bold text-sm truncate">{player.name}</div>
                                                <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                                                    <span className="font-medium text-foreground">{player.position || "Joueur"}</span>
                                                    {player.age && <span>• {player.age} ans</span>}
                                                    {player.number && <span>• N°{player.number}</span>}
                                                </div>
                                                <div className="text-[10px] text-muted-foreground mt-1.5 flex items-center gap-3 font-medium">
                                                    <span className="flex items-center gap-1">🏃‍♂️ {player.appearances || 0} matchs</span>
                                                    {(player.position === "Goalkeeper" || player.position === "Gardien") ? (
                                                        <>
                                                            <span className="flex items-center gap-1">🥅 {player.goals_conceded || 0} encaissés</span>
                                                            <span className="flex items-center gap-1">🎯 {player.assists || 0} passes</span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <span className="flex items-center gap-1">⚽ {player.goals || 0} buts</span>
                                                            <span className="flex items-center gap-1">🎯 {player.assists || 0} passes</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </>
            ) : (
                <LoginBlur>
                    <div className="space-y-4">
                        <div className="h-24 bg-card/50 rounded-xl" />
                        <div className="h-64 bg-card/50 rounded-xl" />
                    </div>
                </LoginBlur>
            )}
        </div>
    )
}
