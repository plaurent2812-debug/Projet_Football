import { useState } from "react"
import { CheckCircle2, XCircle, Clock, Calendar } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { formatOdds } from "@/lib/statsHelper"

interface HistoryPick {
    id: string | number
    source?: string
    result?: string
    bet_label?: string
    player_name?: string
    date?: string
    sport?: string
    market?: string
    odds?: string | number | null
}

interface HistoryStats {
    total: number
    resolved: number
    wins: number
    losses: number
    total_pl: number
    win_rate: number
    odds_estimated?: number
}

// ── Paginated History Table ────────────────────────────────────

const PAGE_SIZE = 30

function HistoryTable({ filteredHistory, filteredHistoryStats }: {
    filteredHistory: HistoryPick[]
    filteredHistoryStats: HistoryStats
}) {
    const [page, setPage] = useState(0)
    const totalPages = Math.ceil(filteredHistory.length / PAGE_SIZE)
    const pageItems = filteredHistory.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

    return (
        <>
            {/* Summary header */}
            <div className="flex items-center justify-between px-3 py-2.5 rounded-xl border border-border/50 bg-card">
                <div className="flex items-center gap-3 text-xs">
                    <span className="text-muted-foreground">{filteredHistoryStats.resolved} resolus / {filteredHistoryStats.total} total</span>
                    {filteredHistoryStats.resolved > 0 && (
                        <span className={cn(
                            "font-bold px-1.5 py-0.5 rounded text-xs",
                            filteredHistoryStats.win_rate >= 60 ? "bg-emerald-500/15 text-emerald-400" :
                                filteredHistoryStats.win_rate >= 45 ? "bg-amber-500/15 text-amber-400" :
                                    "bg-red-500/15 text-red-400"
                        )}>
                            {filteredHistoryStats.win_rate}% reussite · {filteredHistoryStats.wins}W {filteredHistoryStats.losses}L
                        </span>
                    )}
                </div>
                <span className={cn(
                    "text-sm font-black",
                    filteredHistoryStats.total_pl >= 0 ? "text-emerald-500" : "text-red-500"
                )}>
                    P&L : {filteredHistoryStats.total_pl >= 0 ? "+" : ""}{filteredHistoryStats.total_pl} u
                </span>
            </div>

            {/* Picks table */}
            <div className="rounded-xl border border-border/50 bg-card overflow-hidden">
                <div className="divide-y divide-border/30">
                    {pageItems.map((pick) => {
                        const isWin = pick.result === "WIN"
                        const isLoss = pick.result === "LOSS"
                        const isPending = pick.result === "PENDING"
                        const isExpert = pick.source === "expert"
                        return (
                            <div key={`${pick.source}-${pick.id}`} className="flex items-center gap-2 px-3 py-2.5">
                                {/* Result icon */}
                                <div className="shrink-0">
                                    {isWin ? (
                                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                    ) : isLoss ? (
                                        <XCircle className="w-4 h-4 text-red-500" />
                                    ) : (
                                        <Clock className="w-4 h-4 text-amber-500" />
                                    )}
                                </div>

                                {/* Match + market */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex flex-col sm:flex-row sm:items-start gap-1.5">
                                        <span className="text-xs font-medium leading-relaxed">
                                            {pick.bet_label || pick.player_name || "—"}
                                        </span>
                                        {isExpert && (
                                            <span className="shrink-0 self-start px-1.5 py-0.5 rounded text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/20 mt-0.5">
                                                🎯 Expert
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1.5 mt-1">
                                        <span className="text-xs text-muted-foreground">{pick.date}</span>
                                        <span className="text-xs px-1 py-0.5 rounded bg-muted text-muted-foreground">
                                            {pick.sport === "nhl" ? "🏒" : "⚽"} {pick.market || "—"}
                                        </span>
                                    </div>
                                </div>

                                {/* Odds + P&L */}
                                <div className="shrink-0 text-right">
                                    <div className="text-xs font-bold tabular-nums">
                                        @{formatOdds(pick.odds ? parseFloat(String(pick.odds)) : null)}
                                    </div>
                                    <div className={cn(
                                        "text-xs font-semibold tabular-nums",
                                        isWin ? "text-emerald-500" :
                                            isLoss ? "text-red-500" :
                                                "text-muted-foreground"
                                    )}>
                                        {isWin ? `+${formatOdds(pick.odds ? parseFloat(String(pick.odds)) - 1 : null)}u` :
                                            isLoss ? "-1.00u" :
                                                isPending ? "⏳" : "—"}
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between px-1 pt-2">
                    <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-muted/50 hover:bg-muted text-muted-foreground disabled:opacity-30 transition-colors"
                    >
                        Precedent
                    </button>
                    <span className="text-xs text-muted-foreground">
                        Page {page + 1} / {totalPages}
                    </span>
                    <button
                        onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-muted/50 hover:bg-muted text-muted-foreground disabled:opacity-30 transition-colors"
                    >
                        Suivant
                    </button>
                </div>
            )}
        </>
    )
}

// ── History Section (date filters + source filter + table) ─────

interface HistorySectionProps {
    historyLoading: boolean
    filteredHistory: HistoryPick[]
    filteredHistoryStats: HistoryStats
    historyDateFrom: string
    historyDateTo: string
    historySourceFilter: string
    onDateFromChange: (v: string) => void
    onDateToChange: (v: string) => void
    onSourceFilterChange: (v: string) => void
    onResetDates: () => void
}

export function HistorySection({
    historyLoading,
    filteredHistory,
    filteredHistoryStats,
    historyDateFrom,
    historyDateTo,
    historySourceFilter,
    onDateFromChange,
    onDateToChange,
    onSourceFilterChange,
    onResetDates,
}: HistorySectionProps) {
    return (
        <div className="space-y-3">
            {/* Date filter */}
            <div className="rounded-xl border border-border/50 bg-card p-3">
                <div className="flex items-center gap-2 mb-2.5">
                    <Calendar className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-semibold">Filtrer par date</span>
                </div>
                <div className="flex gap-2">
                    <div className="flex-1">
                        <label className="text-xs text-muted-foreground mb-0.5 block">Du</label>
                        <input
                            type="date"
                            value={historyDateFrom}
                            onChange={e => onDateFromChange(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg bg-muted/50 border border-border/50 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                        />
                    </div>
                    <div className="flex-1">
                        <label className="text-xs text-muted-foreground mb-0.5 block">Au</label>
                        <input
                            type="date"
                            value={historyDateTo}
                            onChange={e => onDateToChange(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg bg-muted/50 border border-border/50 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                        />
                    </div>
                    {(historyDateFrom || historyDateTo) && (
                        <button
                            onClick={onResetDates}
                            className="self-end px-2 py-1.5 rounded-lg text-xs font-bold text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted transition-colors"
                        >
                            Reset
                        </button>
                    )}
                </div>
            </div>

            {/* Source filter tabs */}
            <div className="flex gap-1">
                {[
                    { key: "all", label: "Tous", emoji: "📊" },
                    { key: "expert", label: "Expert", emoji: "🎯" },
                    { key: "model", label: "Algo", emoji: "📊" },
                ].map(({ key, label, emoji }) => (
                    <button
                        key={key}
                        onClick={() => onSourceFilterChange(key)}
                        className={cn(
                            "flex-1 py-1.5 rounded-lg text-xs font-bold transition-all",
                            historySourceFilter === key
                                ? "bg-card shadow-sm text-foreground border border-border/60"
                                : "bg-muted/50 text-muted-foreground hover:text-foreground"
                        )}
                    >
                        {emoji} {label}
                    </button>
                ))}
            </div>

            {historyLoading ? (
                <div className="space-y-2">
                    {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
                </div>
            ) : filteredHistory.length > 0 ? (
                <HistoryTable filteredHistory={filteredHistory} filteredHistoryStats={filteredHistoryStats} />
            ) : (
                <div className="text-center py-12 text-xs text-muted-foreground border border-dashed border-border/50 rounded-xl">
                    Aucun historique disponible.
                </div>
            )}
        </div>
    )
}
