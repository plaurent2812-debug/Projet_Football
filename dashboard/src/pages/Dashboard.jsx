import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    Calendar as CalendarIcon,
    ChevronLeft,
    ChevronRight,
    Star,
    TrendingUp,
    Clock,
    Trophy
} from "lucide-react"

import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth"
import { fetchPredictions } from "@/lib/api"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"

/* ── Confidence indicator ──────────────────────────────────── */
function ConfidenceBadge({ score }) {
    if (score == null) return null

    let variant = "secondary"
    let className = "bg-zinc-100 text-zinc-600"

    if (score >= 8) {
        className = "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
    } else if (score >= 6) {
        className = "bg-amber-100 text-amber-700 hover:bg-amber-100"
    }

    return (
        <Badge variant={variant} className={cn("h-5 px-1.5 text-[10px] tabular-nums pointer-events-none", className)}>
            {score}/10
        </Badge>
    )
}

/* ── Match Row ─────────────────────────────────────────────── */
function MatchRow({ match }) {
    const navigate = useNavigate()
    const { isPremium } = useAuth()
    const pred = match.prediction

    // Status Logic
    const isFinished = match.status === "FT" || match.status === "AET" || match.status === "PEN"
    const isLive = ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(match.status)
    const isPostponed = match.status === "PST"

    // Winner Logic
    const homeWon = isFinished && match.home_goals > match.away_goals
    const awayWon = isFinished && match.away_goals > match.home_goals

    const time = match.date ? match.date.slice(11, 16) : "--:--"

    return (
        <TableRow
            className="cursor-pointer hover:bg-muted/50 transition-colors border-b border-border/40 group"
            onClick={() => navigate(`/match/${match.id}`)}
        >
            {/* Time / Status */}
            <TableCell className="w-[80px] py-3 pl-4 pr-2 font-medium text-xs text-muted-foreground">
                <div className="flex flex-col items-center justify-center gap-1">
                    {isLive ? (
                        <Badge variant="destructive" className="h-5 px-1.5 text-[10px] animate-pulse">LIVE</Badge>
                    ) : isFinished ? (
                        <span className="text-[10px] font-bold opacity-70">FIN</span>
                    ) : (
                        <span className="tabular-nums font-semibold text-foreground/80">{time}</span>
                    )}
                </div>
            </TableCell>

            {/* Teams */}
            <TableCell className="py-3 px-2">
                <div className="flex flex-col gap-1.5">
                    {/* Home */}
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 overflow-hidden">
                            {/* Placeholder Logo */}
                            <div className="w-5 h-5 rounded-full bg-muted shrink-0 flex items-center justify-center text-[8px] font-bold text-muted-foreground/50 border">
                                {match.home_team.charAt(0)}
                            </div>
                            <span className={cn(
                                "text-sm truncate transition-colors",
                                homeWon ? "font-bold text-foreground" : "font-medium text-foreground/70",
                                isLive && "text-foreground"
                            )}>
                                {match.home_team}
                            </span>
                        </div>
                        <span className={cn(
                            "text-sm font-bold tabular-nums min-w-[20px] text-center",
                            isLive && "text-red-500",
                            homeWon ? "text-foreground" : "text-muted-foreground/60"
                        )}>
                            {match.home_goals ?? "-"}
                        </span>
                    </div>

                    {/* Away */}
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 overflow-hidden">
                            {/* Placeholder Logo */}
                            <div className="w-5 h-5 rounded-full bg-muted shrink-0 flex items-center justify-center text-[8px] font-bold text-muted-foreground/50 border">
                                {match.away_team.charAt(0)}
                            </div>
                            <span className={cn(
                                "text-sm truncate transition-colors",
                                awayWon ? "font-bold text-foreground" : "font-medium text-foreground/70",
                                isLive && "text-foreground"
                            )}>
                                {match.away_team}
                            </span>
                        </div>
                        <span className={cn(
                            "text-sm font-bold tabular-nums min-w-[20px] text-center",
                            isLive && "text-red-500",
                            awayWon ? "text-foreground" : "text-muted-foreground/60"
                        )}>
                            {match.away_goals ?? "-"}
                        </span>
                    </div>
                </div>
            </TableCell>

            {/* Prediction / Value */}
            <TableCell className="w-[120px] py-3 px-2 text-right hidden sm:table-cell">
                <div className="flex flex-col items-end gap-1.5">
                    {pred?.value_bet && isPremium && (
                        <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-200 bg-emerald-50 h-5 px-1.5 gap-1">
                            <TrendingUp className="w-3 h-3" />
                            VALUE
                        </Badge>
                    )}
                    {pred && (
                        <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                            {/* Show quick prediction hint on hover */}
                            <span className="text-[10px] text-muted-foreground font-medium uppercase min-w-[30px] text-right">
                                {pred.recommended_bet?.split(' ')[0] || "1N2"}
                            </span>
                            <ConfidenceBadge score={pred.confidence_score} />
                        </div>
                    )}
                </div>
            </TableCell>

            {/* Mobile Arrow */}
            <TableCell className="w-8 py-3 pr-4 pl-0 text-right sm:hidden">
                <ChevronRight className="w-4 h-4 text-muted-foreground/30" />
            </TableCell>
        </TableRow>
    )
}

/* ── League Section ────────────────────────────────────────── */
function LeagueSection({ leagueName, matches }) {
    if (!matches || matches.length === 0) return null

    return (
        <Card className="border-none shadow-none bg-transparent mb-6">
            <div className="flex items-center gap-3 px-4 py-2 bg-gradient-to-r from-muted/50 to-transparent rounded-lg mb-2">
                <div className="w-6 h-6 rounded bg-white shadow-sm border flex items-center justify-center text-xs">
                    {/* Placeholder Flag */}
                    <Trophy className="w-3 h-3 text-muted-foreground" />
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-bold text-foreground tracking-tight">{leagueName}</span>
                    <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">{matches[0].country || "Monde"}</span>
                </div>
            </div>

            <CardContent className="p-0">
                <Table>
                    <TableBody>
                        {matches.map(match => (
                            <MatchRow key={match.id} match={match} />
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    )
}

/* ── Dashboard Page ────────────────────────────────────────── */
export default function DashboardPage({ date, setDate, selectedLeague, setSelectedLeague }) {
    const { isPremium } = useAuth()
    const [matches, setMatches] = useState([])
    const [activeTab, setActiveTab] = useState("all")
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        // Fetch 48h window to match "Match of the Day" logic roughly
        const d1 = date
        const d2 = addDays(new Date(date), 1).toISOString().slice(0, 10)

        Promise.all([
            fetchPredictions(d1),
            fetchPredictions(d2)
        ]).then(([res1, res2]) => {
            const combined = [...(res1.matches || []), ...(res2.matches || [])]
                // Deduplicate by ID just in case
                .filter((v, i, a) => a.findIndex(t => t.id === v.id) === i)
                .sort((a, b) => a.date.localeCompare(b.date))

            setMatches(combined)
        }).catch(err => {
            console.error("Failed to fetch matches:", err)
        }).finally(() => {
            setLoading(false)
        })
    }, [date])

    const handleDateChange = (days) => {
        const newDate = addDays(new Date(date), days).toISOString().slice(0, 10)
        setDate(newDate)
    }

    const filteredMatches = matches.filter(m => {
        if (activeTab === "live") return ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(m.status)
        if (activeTab === "value") return m.prediction?.value_bet
        if (selectedLeague) return m.league_id === selectedLeague
        return true
    })

    // Grouping
    const byLeague = {}
    filteredMatches.forEach(m => {
        const name = m.league_name || "Autres Compétitions"
        if (!byLeague[name]) byLeague[name] = []
        byLeague[name].push(m)
    })
    const leagues = Object.keys(byLeague).sort()

    return (
        <div className="space-y-6 pb-20">

            {/* Controls Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sticky top-14 z-30 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 py-2 border-b">

                {/* Tabs */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full sm:w-auto">
                    <TabsList className="grid w-full sm:w-auto grid-cols-3 h-9">
                        <TabsTrigger value="all" className="text-xs">Tous</TabsTrigger>
                        <TabsTrigger value="live" className="text-xs gap-1.5">
                            En Direct
                            <span className="flex h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                        </TabsTrigger>
                        <TabsTrigger value="value" disabled={!isPremium} className="text-xs gap-1.5">
                            Value
                            {isPremium && <TrendingUp className="w-3 h-3 text-emerald-500" />}
                        </TabsTrigger>
                    </TabsList>
                </Tabs>

                {/* Date Navigation */}
                <div className="flex items-center gap-2 bg-muted/50 p-1 rounded-md self-end sm:self-auto">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleDateChange(-1)}
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </Button>

                    <div className="flex items-center gap-2 px-2 min-w-[120px] justify-center">
                        <CalendarIcon className="w-3.5 h-3.5 text-muted-foreground" />
                        <span className="text-sm font-semibold tabular-nums capitalize">
                            {format(new Date(date), "EEE d MMM", { locale: fr })}
                        </span>
                    </div>

                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleDateChange(1)}
                    >
                        <ChevronRight className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            {/* Active League Filter Indicator */}
            {selectedLeague && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm">
                    <span className="text-muted-foreground">Filtre :</span>
                    <span className="font-semibold text-primary">
                        {filteredMatches.length > 0 ? byLeague[Object.keys(byLeague)[0]] && Object.keys(byLeague)[0] : "Ligue sélectionnée"}
                    </span>
                    <span className="text-muted-foreground">({filteredMatches.length} match{filteredMatches.length !== 1 ? "s" : ""})</span>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="ml-auto h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                        onClick={() => setSelectedLeague?.(null)}
                    >
                        Effacer le filtre
                    </Button>
                </div>
            )}

            {/* Content */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <div className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
                    <p className="text-xs text-muted-foreground font-medium animate-pulse">Chargement des matchs...</p>
                </div>
            ) : filteredMatches.length > 0 ? (
                <div className="space-y-1">
                    {leagues.map(league => (
                        <LeagueSection
                            key={league}
                            leagueName={league}
                            matches={byLeague[league]}
                        />
                    ))}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-24 text-center border-2 border-dashed rounded-xl bg-accent/10">
                    <div className="p-4 bg-muted rounded-full mb-4">
                        <CalendarIcon className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-lg font-bold">Aucun match trouvé</h3>
                    <p className="text-sm text-muted-foreground max-w-[250px] mt-2">
                        Essayez de changer de date ou de filtre pour voir plus de résultats.
                    </p>
                    <Button variant="outline" className="mt-6" onClick={() => setActiveTab("all")}>
                        Voir tous les matchs
                    </Button>
                </div>
            )}
        </div>
    )
}
