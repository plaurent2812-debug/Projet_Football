import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { fetchTeamHistory } from "@/lib/api"
import {
    ArrowLeft, Calendar, Trophy, TrendingUp, TrendingDown, Minus,
    Activity, MapPin, Shield
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
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        setLoading(true)
        fetchTeamHistory(name)
            .then(setData)
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
                        Historique des 20 derniers matchs
                    </p>
                </div>
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
                    {summary.streak.count > 0 && (
                        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-card border border-border/40 w-fit">
                            <span className="text-sm text-muted-foreground font-medium">Série en cours :</span>
                            <span className={cn(
                                "text-sm font-bold",
                                summary.streak.type === "V" ? "text-emerald-400" :
                                    summary.streak.type === "D" ? "text-red-400" : "text-amber-400"
                            )}>
                                {summary.streak.count} {summary.streak.type === "V" ? "Victoire" : summary.streak.type === "D" ? "Défaite" : "Nul"}{summary.streak.count > 1 ? "s" : ""}
                                {summary.streak.type === "V" && <TrendingUp className="w-4 h-4 inline ml-1.5" />}
                                {summary.streak.type === "D" && <TrendingDown className="w-4 h-4 inline ml-1.5" />}
                            </span>
                        </div>
                    )}

                    {/* Match History List */}
                    <div className="rounded-xl border border-border/40 overflow-hidden bg-card/30">
                        <div className="grid grid-cols-[auto_1fr_auto_auto] gap-4 p-3 bg-muted/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border/40">
                            <span className="pl-2">Résultat</span>
                            <span>Adversaire</span>
                            <span className="text-center">Score</span>
                            <span className="pr-2">Date</span>
                        </div>
                        <div className="divide-y divide-border/30">
                            {matches.map((m, i) => (
                                <div key={i} className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-4 p-3 hover:bg-card/50 transition-colors">
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
