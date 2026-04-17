import { useState } from "react"
import { CheckCircle2, XCircle, Minus } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatOdds, formatProba } from "@/lib/statsHelper"
import { ResultBadge, MarketBadge } from "./badges"
import { saveBet, updateBetResult } from "./api"

interface Bet {
    id?: string | number
    label: string
    market: string
    odds: number
    proba_model: number
    proba_bookmaker?: number | null
    confidence: number
    ev?: number | null
    edge_pct?: number | null
    bookmaker?: string | null
    is_value?: boolean
    fixture_id?: string | number
    result?: string
}

interface BetCardProps {
    bet: Bet
    sport: string
    date: string
    isAdmin: boolean
    onResultUpdate?: () => void
}

export function BetCard({ bet, sport, date, isAdmin, onResultUpdate }: BetCardProps) {
    const [updating, setUpdating] = useState(false)
    const [localResult, setLocalResult] = useState(bet.result || "PENDING")
    const [betId, setBetId] = useState<string | number | undefined>(bet.id)
    const [saving, setSaving] = useState(false)

    async function handleSave() {
        setSaving(true)
        try {
            const resp = await saveBet(bet as Record<string, unknown>, sport, date)
            if (resp.id) {
                setBetId(resp.id)
                setLocalResult("PENDING")
            }
        } finally { setSaving(false) }
    }

    async function handleResult(result: string) {
        if (!betId) {
            setSaving(true)
            try {
                const resp = await saveBet(bet as Record<string, unknown>, sport, date)
                if (resp.id) {
                    setBetId(resp.id)
                    setUpdating(true)
                    await updateBetResult(resp.id, result)
                    setLocalResult(result)
                    onResultUpdate?.()
                }
            } finally { setSaving(false); setUpdating(false) }
            return
        }
        setUpdating(true)
        try {
            await updateBetResult(betId, result)
            setLocalResult(result)
            onResultUpdate?.()
        } finally { setUpdating(false) }
    }

    const isTracked = !!betId
    const edgePct = bet.edge_pct ?? (
        bet.proba_model != null && bet.odds > 1
            ? Math.round((bet.proba_model / 100 - 1 / bet.odds) * 1000) / 10
            : 0
    )

    // Kelly criterion: fraction = edge / (odds - 1), capped at 5% (half-Kelly for safety)
    const kellyRaw = bet.odds > 1 && edgePct > 0
        ? (edgePct / 100) / (bet.odds - 1) * 100
        : 0
    const kellyPct = Math.min(kellyRaw, 5) // Cap at 5% max

    return (
        <div className={cn(
            "rounded-xl border p-4 transition-all duration-200",
            localResult === "WIN" && "border-emerald-500/30 bg-emerald-500/5",
            localResult === "LOSS" && "border-red-500/20 bg-red-500/5",
            localResult === "PENDING" && edgePct > 10
                ? "border-emerald-500/40 bg-emerald-500/5 hover:border-emerald-500/60"
                : localResult === "PENDING" && edgePct > 5
                    ? "border-emerald-500/25 bg-emerald-500/3 hover:border-emerald-500/40"
                    : localResult === "PENDING"
                        ? "border-emerald-500/15 bg-card hover:border-emerald-500/30"
                        : "",
            localResult === "VOID" && "border-slate-500/20 bg-slate-500/5",
        )}>
            <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground leading-tight">{bet.label}</p>
                    <div className="flex items-center flex-wrap gap-1.5 mt-1.5">
                        <MarketBadge market={bet.market} />
                        {bet.bookmaker && (
                            <span className="text-xs text-muted-foreground opacity-60 capitalize">
                                {bet.bookmaker}
                            </span>
                        )}
                    </div>
                </div>
                <ResultBadge result={localResult} betDate={date} />
            </div>

            <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-4">
                    {/* Edge — hero metric */}
                    <div className="flex items-center gap-1.5">
                        <span className={cn(
                            "text-lg font-black",
                            edgePct >= 10 ? "text-emerald-400" : edgePct >= 5 ? "text-emerald-500" : "text-emerald-600"
                        )}>
                            +{edgePct.toFixed(1)}%
                        </span>
                        <span className="text-xs text-muted-foreground uppercase font-bold">Edge</span>
                    </div>

                    {/* Odds */}
                    <span className="font-mono font-bold text-foreground text-base">
                        {formatOdds(bet.odds)}
                    </span>

                    {/* Model vs Book */}
                    <div className="flex flex-col text-sm text-muted-foreground">
                        <span>{formatProba(bet.proba_model)} modele</span>
                        {bet.proba_bookmaker != null && (
                            <span>
                                vs {formatProba(bet.proba_bookmaker)} book
                            </span>
                        )}
                    </div>

                    {/* Kelly stake recommendation */}
                    {kellyPct > 0 && localResult === "PENDING" && (
                        <div className="flex flex-col items-center">
                            <span className="text-xs font-bold text-primary">{kellyPct.toFixed(1)}%</span>
                            <span className="text-xs text-muted-foreground">bankroll</span>
                        </div>
                    )}
                </div>

                {isAdmin && (
                    <div className="flex items-center gap-1">
                        {!isTracked && localResult === "PENDING" && (
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="px-3 py-1.5 rounded text-xs font-bold bg-primary/15 text-primary hover:bg-primary/25 transition-colors disabled:opacity-50"
                            >
                                {saving ? "..." : "Tracker"}
                            </button>
                        )}
                        {(isTracked || localResult !== "PENDING") && (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => handleResult("WIN")}
                                    disabled={updating}
                                    className="w-10 h-10 rounded flex items-center justify-center bg-emerald-500/15 hover:bg-emerald-500/30 transition-colors text-emerald-400 disabled:opacity-50"
                                    title="WIN"
                                >
                                    <CheckCircle2 className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => handleResult("LOSS")}
                                    disabled={updating}
                                    className="w-10 h-10 rounded flex items-center justify-center bg-red-500/15 hover:bg-red-500/30 transition-colors text-red-400 disabled:opacity-50"
                                    title="LOSS"
                                >
                                    <XCircle className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => handleResult("VOID")}
                                    disabled={updating}
                                    className="w-10 h-10 rounded flex items-center justify-center bg-slate-500/15 hover:bg-slate-500/30 transition-colors text-slate-400 disabled:opacity-50"
                                    title="NUL/VOID"
                                >
                                    <Minus className="w-4 h-4" />
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
