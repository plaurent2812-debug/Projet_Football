import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { ArrowLeft, Trophy, Activity, Target, Zap, Shield, Goal } from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchPlayerProfile } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function StatBox({ label, value, icon: Icon, highlight = false }) {
    return (
        <div className={cn(
            "p-3 rounded-xl flex flex-col justify-center items-center text-center",
            highlight ? "bg-primary/10 border border-primary/20" : "bg-card border border-border/50"
        )}>
            {Icon && <Icon className={cn("w-4 h-4 mb-2", highlight ? "text-primary" : "text-muted-foreground")} />}
            <span className={cn("text-xl font-black mb-1", highlight ? "text-primary" : "text-foreground")}>
                {value ?? "—"}
            </span>
            <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">{label}</span>
        </div>
    )
}

export default function PlayerProfile() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetchPlayerProfile(id)
            .then(res => setData(res.player))
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
            <p className="text-muted-foreground">Profil joueur introuvable</p>
            <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>
                Retour
            </Button>
        </div>
    )

    const comps = data.stats_json?.competitions || []

    // Aggrégats totaux
    let totalGoals = 0, totalAssists = 0, totalMatches = 0, totalMinutes = 0
    let totalShots = 0, totalShotsOn = 0, totalPenalties = 0

    comps.forEach(c => {
        totalGoals += c.goals || 0
        totalAssists += c.assists || 0
        totalMatches += c.appearances || 0
        totalMinutes += c.minutes || 0
        totalShots += c.shots_total || 0
        totalShotsOn += c.shots_on || 0
        totalPenalties += c.penalty_scored || 0
    })

    const isAttacker = data.position === "Attacker"
    const conversionRate = totalShots > 0 ? ((totalGoals / totalShots) * 100).toFixed(1) : "0"
    const minsPerGoal = totalGoals > 0 ? Math.round(totalMinutes / totalGoals) : "—"

    return (
        <div className="max-w-3xl mx-auto space-y-6 animate-fade-in-up pb-12">

            {/* Navigation */}
            <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
            >
                <ArrowLeft className="w-4 h-4" />
                Retour
            </button>

            {/* Hero Profile */}
            <Card className="border-border/50 overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/10 pointer-events-none" />
                <CardContent className="p-6 relative">
                    <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start text-center sm:text-left">
                        {data.photo ? (
                            <img src={data.photo} alt={data.name} className="w-24 h-24 rounded-full object-cover border-4 border-card shadow-lg shrink-0" />
                        ) : (
                            <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center text-3xl font-black text-primary border-4 border-card shadow-lg shrink-0">
                                {data.firstname?.[0]}{data.lastname?.[0]}
                            </div>
                        )}

                        <div className="flex-1 space-y-2">
                            <div className="flex flex-col sm:flex-row items-center gap-3">
                                <h1 className="text-3xl font-black leading-tight">{data.name}</h1>
                                <Badge variant="outline" className="bg-background text-xs">
                                    {data.position || "Joueur"}
                                </Badge>
                            </div>

                            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 xgap-4 text-sm text-muted-foreground mt-2">
                                {data.team_name && (
                                    <div className="flex items-center gap-1.5 text-foreground font-semibold">
                                        {data.team_logo && <img src={data.team_logo} className="w-4 h-4 object-contain" alt="" />}
                                        {data.team_name}
                                    </div>
                                )}
                                {data.nationality && <span>🌎 {data.nationality}</span>}
                                {data.age && <span>🎂 {data.age} ans</span>}
                                {data.height && <span>📏 {data.height}</span>}
                                {data.weight && <span>⚖️ {data.weight}</span>}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Statistiques Globales (Saison Courante) */}
            <div>
                <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                    <Zap className="w-5 h-5 text-amber-500" />
                    Saison globale
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <StatBox label="Matchs joués" value={totalMatches} icon={Activity} />
                    <StatBox label="Buts" value={totalGoals} icon={Goal} highlight={totalGoals > 0} />
                    <StatBox label="Passes dé." value={totalAssists} icon={Target} />
                    <StatBox label="Minutes" value={totalMinutes} icon={Clock} />
                </div>
            </div>

            {/* Insights Betting (Attacker focus) */}
            {isAttacker && totalMatches > 0 && (
                <Card className="border-emerald-500/20 bg-gradient-to-br from-card to-emerald-500/5">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <Shield className="w-4 h-4 text-emerald-500" />
                            Insights Betting
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="flex justify-between items-center sm:block sm:text-center p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold uppercase">Conversion tirs</span>
                                <span className="text-xl font-black text-emerald-700 dark:text-emerald-300 mt-1 block">{conversionRate}%</span>
                            </div>
                            <div className="flex justify-between items-center sm:block sm:text-center p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold uppercase">Tirs / Match</span>
                                <span className="text-xl font-black text-emerald-700 dark:text-emerald-300 mt-1 block">{(totalShots / totalMatches).toFixed(1)}</span>
                            </div>
                            <div className="flex justify-between items-center sm:block sm:text-center p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold uppercase">Penaltys marqués</span>
                                <span className="text-xl font-black text-emerald-700 dark:text-emerald-300 mt-1 block">{totalPenalties}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Par Compétition */}
            <div>
                <h2 className="text-lg font-bold mb-3 flex items-center gap-2 mt-8">
                    <Trophy className="w-5 h-5 text-primary" />
                    Par Compétition
                </h2>
                <div className="space-y-3">
                    {comps.map((c, i) => (
                        <Card key={i} className="border-border/50">
                            <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex items-center gap-3">
                                    {c.league_logo ? (
                                        <img src={c.league_logo} alt="" className="w-8 h-8 object-contain" />
                                    ) : (
                                        <div className="w-8 h-8 rounded bg-muted flex items-center justify-center text-xs">?</div>
                                    )}
                                    <div>
                                        <h3 className="font-bold text-sm">{c.league_name}</h3>
                                        <p className="text-xs text-muted-foreground">{c.team_name}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-6 sm:gap-8 justify-between sm:justify-end">
                                    <div className="text-center">
                                        <p className="text-lg font-bold leading-none">{c.appearances || 0}</p>
                                        <p className="text-[10px] text-muted-foreground uppercase pt-1 inline-block">Matchs</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-lg font-black leading-none text-primary">{c.goals || 0}</p>
                                        <p className="text-[10px] text-muted-foreground uppercase pt-1">Buts</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-lg font-bold leading-none">{c.assists || 0}</p>
                                        <p className="text-[10px] text-muted-foreground uppercase pt-1">Passes</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-lg font-bold leading-none text-amber-500">{c.yellow || 0}</p>
                                        <p className="text-[10px] text-muted-foreground uppercase pt-1">🟨</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>

        </div>
    )
}
