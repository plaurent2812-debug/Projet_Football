import { useState, useEffect } from "react"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import { Link } from "react-router-dom"
import {
    ChevronLeft, ChevronRight, Target,
    Sparkles, RefreshCw, Trophy, Lock
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth } from "@/lib/auth"
import { API_ROOT } from "@/lib/api"

import { BetCard } from "@/components/paris-du-soir/BetCard"
import { StatsDashboard } from "@/components/paris-du-soir/StatsDashboard"
import { ExpertPickCard } from "@/components/paris-du-soir/ExpertPickCard"
import { HistorySection } from "@/components/paris-du-soir/HistorySection"
import {
    fetchBestBets,
    fetchBestBetsStats,
    fetchExpertPicks,
} from "@/components/paris-du-soir/api"

// ── Bet Section ───────────────────────────────────────────────

interface BetSectionProps {
    sport: string
    betsArr: unknown[]
    emoji: string
    label: string
    accentColor: string
    loading: boolean
    isAdmin: boolean
    date: string
    onResultUpdate: () => void
}

function BetSection({ sport, betsArr, emoji, label, accentColor, loading, isAdmin, date, onResultUpdate }: BetSectionProps) {
    return (
        <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
                <span className="text-base">{emoji}</span>
                <h2 className={cn("text-sm font-bold", accentColor)}>{label}</h2>
                <span className="text-xs text-muted-foreground">— Value Bets (EV+)</span>
                {isAdmin && betsArr.length > 0 && (
                    <span className="ml-auto text-[9px] text-muted-foreground">
                        Boutons WIN/LOSS visibles (admin)
                    </span>
                )}
            </div>

            {loading ? (
                <div className="space-y-2">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
                </div>
            ) : betsArr.length > 0 ? (
                <div className="space-y-2.5">
                    {(betsArr as any[]).map((bet, i) => (
                        <BetCard
                            key={bet.fixture_id || i}
                            bet={bet}
                            sport={sport}
                            date={date}
                            isAdmin={isAdmin}
                            onResultUpdate={onResultUpdate}
                        />
                    ))}
                </div>
            ) : (
                <div className="text-center py-8 border border-dashed border-border/50 rounded-xl space-y-1">
                    <p className="text-xs text-muted-foreground">Aucun Value Bet {label} detecte pour cette date.</p>
                    <p className="text-xs text-muted-foreground/60">0 pari vaut mieux qu'un mauvais pari.</p>
                </div>
            )}
        </div>
    )
}

// ── Main Page ─────────────────────────────────────────────────

export default function ParisDuSoir() {
    const { hasAccess, isAdmin } = useAuth()
    const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
    const [sportFilter, setSportFilter] = useState("both")
    const [bets, setBets] = useState<any>(null)
    const [stats, setStats] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)
    const [showHistory, setShowHistory] = useState(false)
    const [history, setHistory] = useState<any>(null)
    const [historyLoading, setHistoryLoading] = useState(false)
    const [expertPicks, setExpertPicks] = useState<any[]>([])
    const [historyDateFrom, setHistoryDateFrom] = useState("")
    const [historyDateTo, setHistoryDateTo] = useState("")
    const [historySourceFilter, setHistorySourceFilter] = useState("all")

    const canAccess = hasAccess("premium")

    useEffect(() => {
        setLoading(true)
        setBets(null)
        fetchBestBets(date, sportFilter === "both" ? null : sportFilter)
            .then(setBets)
            .finally(() => setLoading(false))
    }, [date, sportFilter, refreshKey])

    useEffect(() => {
        if (!canAccess) return
        fetchBestBetsStats().then(setStats)
    }, [canAccess, refreshKey])

    useEffect(() => {
        if (!canAccess) return
        fetchExpertPicks(date, sportFilter).then(setExpertPicks)
    }, [date, sportFilter, canAccess, refreshKey])

    useEffect(() => {
        if (!showHistory || !canAccess) return
        setHistoryLoading(true)
        const params = new URLSearchParams()
        if (historyDateFrom) {
            params.set("date_from", historyDateFrom)
        } else {
            params.set("days", "90")
        }
        if (historyDateTo) params.set("date_to", historyDateTo)
        const sportParam = sportFilter === "both" ? "" : sportFilter
        if (sportParam) params.set("sport", sportParam)
        if (historySourceFilter && historySourceFilter !== "all") {
            params.set("source", historySourceFilter)
        }

        fetch(`${API_ROOT}/api/best-bets/history?${params}`)
            .then(r => r.json())
            .then(setHistory)
            .catch(() => console.warn("Impossible de charger l'historique des paris"))
            .finally(() => setHistoryLoading(false))
    }, [showHistory, sportFilter, canAccess, historyDateFrom, historyDateTo, historySourceFilter])

    if (!canAccess) {
        const dateObj = new Date(date + "T12:00:00")
        const formattedDate = format(dateObj, "EEEE d MMMM", { locale: fr })
        const footballBets = bets?.football || []
        const previewBets = footballBets.slice(0, 2)
        const totalBets = footballBets.length + (bets?.nhl || []).length

        return (
            <div className="animate-fade-in-up px-3 pt-4 pb-8 w-full mx-auto">
                {/* Header */}
                <div className="mb-3">
                    <h1 className="text-lg font-black tracking-tight">Smart Betting Assistant</h1>
                    <p className="text-xs text-muted-foreground">Edges d&eacute;tect&eacute;s automatiquement — ne pariez que quand le march&eacute; se trompe</p>
                </div>
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <Target className="w-5 h-5 text-primary" />
                        <h2 className="text-sm font-bold capitalize">{formattedDate}</h2>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <button
                            onClick={() => setDate(subDays(dateObj, 1).toISOString().slice(0, 10))}
                            className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setDate(addDays(dateObj, 1).toISOString().slice(0, 10))}
                            className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Strategy reminder */}
                <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 mb-5 flex items-center gap-3">
                    <Sparkles className="w-4 h-4 text-primary shrink-0" />
                    <p className="text-xs text-muted-foreground">
                        <strong className="text-foreground">Strategie :</strong>{" "}
                        Uniquement des Value Bets (EV+) · Notre modele bat le bookmaker · Edge = avantage mathematique
                    </p>
                </div>

                {/* Summary stat line */}
                {!loading && (
                    <div className="mb-4 px-1">
                        <p className="text-xs text-muted-foreground">
                            {totalBets > 0 ? (
                                <>
                                    <strong className="text-foreground">{totalBets} value bet{totalBets > 1 ? "s" : ""}</strong>{" "}
                                    detecte{totalBets > 1 ? "s" : ""} aujourd'hui
                                </>
                            ) : (
                                "Aucun value bet detecte pour cette date."
                            )}
                        </p>
                    </div>
                )}

                {/* Free preview: first 2 football bets */}
                <div className="mb-4">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-base">⚽</span>
                        <h2 className="text-sm font-bold text-emerald-500">Football</h2>
                        <span className="text-xs text-muted-foreground">— Apercu gratuit</span>
                    </div>

                    {loading ? (
                        <div className="space-y-2">
                            {[1, 2].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
                        </div>
                    ) : previewBets.length > 0 ? (
                        <div className="space-y-2.5">
                            {previewBets.map((bet: any, i: number) => (
                                <BetCard
                                    key={bet.fixture_id || i}
                                    bet={bet}
                                    sport="football"
                                    date={date}
                                    isAdmin={false}
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-xs text-muted-foreground border border-dashed border-border/50 rounded-xl">
                            Aucun Value Bet Football detecte pour cette date.
                        </div>
                    )}
                </div>

                {/* Blurred overflow if more bets exist */}
                {!loading && footballBets.length > 2 && (
                    <div className="relative mb-4">
                        <div className="space-y-2.5 blur-sm pointer-events-none select-none" aria-hidden="true">
                            {footballBets.slice(2, 4).map((bet: any, i: number) => (
                                <BetCard
                                    key={`blur-${i}`}
                                    bet={bet}
                                    sport="football"
                                    date={date}
                                    isAdmin={false}
                                />
                            ))}
                        </div>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="flex items-center gap-2 bg-card/90 border border-border/60 rounded-lg px-4 py-2 shadow-lg backdrop-blur-sm">
                                <Lock className="w-3.5 h-3.5 text-amber-500" />
                                <span className="text-xs font-bold text-foreground">
                                    +{footballBets.length - 2} paris masques
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Premium CTA */}
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5 text-center">
                    <Trophy className="w-8 h-8 text-amber-500 mx-auto mb-3" />
                    <h3 className="text-sm font-black text-foreground mb-1">
                        Debloque tous les pronos
                    </h3>
                    <p className="text-xs text-muted-foreground mb-4 max-w-[260px] mx-auto leading-relaxed">
                        Acces illimite aux Value Bets Football & NHL, picks experts, historique complet et statistiques.
                    </p>
                    <Link
                        to="/premium"
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-black transition-colors"
                    >
                        <Trophy className="w-4 h-4" />
                        Passer Premium
                    </Link>
                </div>
            </div>
        )
    }

    const dateObj = new Date(date + "T12:00:00")
    const formattedDate = format(dateObj, "EEEE d MMMM", { locale: fr })

    const footballBets = bets?.football || []
    const nhlBets = bets?.nhl || []

    const filteredHistory = history?.picks || []
    const filteredHistoryStats = history?.stats || {
        total: 0,
        resolved: 0,
        wins: 0,
        losses: 0,
        total_pl: 0,
        win_rate: 0,
        odds_estimated: 0,
    }

    return (
        <div className="animate-fade-in-up px-3 pt-4 pb-8 w-full mx-auto">
            {/* Header */}
            <div className="mb-3">
                <h1 className="text-lg font-black tracking-tight">Smart Betting Assistant</h1>
                <p className="text-xs text-muted-foreground">Edges d&eacute;tect&eacute;s automatiquement — ne pariez que quand le march&eacute; se trompe</p>
            </div>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-primary" />
                    <h2 className="text-sm font-bold capitalize">{formattedDate}</h2>
                </div>
                <div className="flex items-center gap-1.5">
                    <button
                        onClick={() => setDate(subDays(dateObj, 1).toISOString().slice(0, 10))}
                        className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setDate(addDays(dateObj, 1).toISOString().slice(0, 10))}
                        className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setRefreshKey(k => k + 1)}
                        className="p-1.5 rounded-lg hover:bg-accent transition-colors text-muted-foreground"
                        title="Rafraichir"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Strategy reminder */}
            <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 mb-5 flex items-center gap-3">
                <Sparkles className="w-4 h-4 text-primary shrink-0" />
                <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">Strategie :</strong>{" "}
                    Uniquement des Value Bets (EV+) · Notre modele bat le bookmaker · Edge = avantage mathematique · Plus l'edge est haut, plus le pari a de valeur
                </p>
            </div>

            {/* Expert Picks section — hidden for Smart Betting Assistant pivot (keep code for later) */}
            {false && !showHistory && (
                <div className="mb-5">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-base">🎯</span>
                        <h2 className="text-sm font-bold text-amber-400">Paris de l'Expert</h2>
                    </div>
                    {expertPicks.length > 0 ? (
                        <div className="space-y-2.5">
                            {expertPicks.map((pick) => (
                                <ExpertPickCard
                                    key={pick.id}
                                    pick={pick}
                                    isAdmin={isAdmin}
                                    onDelete={(id) => setExpertPicks(prev => prev.filter(p => p.id !== id))}
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="rounded-xl border border-dashed border-border/50 bg-muted/20 px-4 py-6 text-center">
                            <p className="text-xs text-muted-foreground">📡 Pas de pick expert ce soir — notre algorithme continue l'analyse en continu</p>
                        </div>
                    )}
                </div>
            )}

            {/* View toggle: Historique */}
            <div className="flex gap-1 mb-5">
                <button
                    onClick={() => setShowHistory(!showHistory)}
                    className={cn(
                        "flex-1 py-2 rounded-lg text-xs font-bold transition-all",
                        showHistory ? "bg-card shadow-sm text-foreground border border-border/60" : "bg-muted/50 text-muted-foreground hover:text-foreground"
                    )}
                >
                    📊 Historique complet
                </button>
            </div>

            {!showHistory ? (
                <>
                    {/* Sport filter tabs */}
                    <div className="flex gap-1 mb-5">
                        {[
                            { key: "both", label: "Tous", emoji: "🎯" },
                            { key: "football", label: "Football", emoji: "⚽" },
                            { key: "nhl", label: "NHL", emoji: "🏒" },
                        ].map(({ key, label, emoji }) => (
                            <button
                                key={key}
                                onClick={() => setSportFilter(key)}
                                className={cn(
                                    "flex-1 py-2 rounded-lg text-xs font-bold transition-all",
                                    sportFilter === key
                                        ? "bg-card shadow-sm text-foreground border border-border/60"
                                        : "bg-muted/50 text-muted-foreground hover:text-foreground"
                                )}
                            >
                                {emoji} {label}
                            </button>
                        ))}
                    </div>

                    {/* Football bets */}
                    {(sportFilter === "both" || sportFilter === "football") && (
                        <BetSection
                            sport="football"
                            betsArr={footballBets}
                            emoji="⚽"
                            label="Football"
                            accentColor="text-emerald-500"
                            loading={loading}
                            isAdmin={isAdmin}
                            date={date}
                            onResultUpdate={() => setRefreshKey(k => k + 1)}
                        />
                    )}

                    {/* NHL bets */}
                    {(sportFilter === "both" || sportFilter === "nhl") && (
                        <BetSection
                            sport="nhl"
                            betsArr={nhlBets}
                            emoji="🏒"
                            label="NHL"
                            accentColor="text-cyan-500"
                            loading={loading}
                            isAdmin={isAdmin}
                            date={date}
                            onResultUpdate={() => setRefreshKey(k => k + 1)}
                        />
                    )}

                    {/* Stats — admin only */}
                    <StatsDashboard stats={stats} isAdmin={isAdmin} />
                </>
            ) : (
                <HistorySection
                    historyLoading={historyLoading}
                    filteredHistory={filteredHistory}
                    filteredHistoryStats={filteredHistoryStats}
                    historyDateFrom={historyDateFrom}
                    historyDateTo={historyDateTo}
                    historySourceFilter={historySourceFilter}
                    onDateFromChange={setHistoryDateFrom}
                    onDateToChange={setHistoryDateTo}
                    onSourceFilterChange={setHistorySourceFilter}
                    onResetDates={() => { setHistoryDateFrom(""); setHistoryDateTo("") }}
                />
            )}
        </div>
    )
}
