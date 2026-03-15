import { useState, useEffect } from "react"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    ChevronLeft, ChevronRight, Target, Trophy, Lock,
    CheckCircle2, XCircle, Clock, Minus, TrendingUp,
    BarChart3, Sparkles, RefreshCw, Trash2
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth } from "@/lib/auth"

const API_BASE = import.meta.env.VITE_API_URL || ""

// ── API helpers ───────────────────────────────────────────────
async function fetchBestBets(date, sport = null) {
    const params = new URLSearchParams({ date })
    if (sport) params.set("sport", sport)
    try {
        const res = await fetch(`${API_BASE}/api/best-bets?${params}`)
        if (!res.ok) return null
        return res.json()
    } catch { return null }
}

async function fetchBestBetsStats() {
    try {
        const res = await fetch(`${API_BASE}/api/best-bets/stats`)
        if (!res.ok) return null
        return res.json()
    } catch { return null }
}

async function updateBetResult(betId, result, notes = "") {
    const res = await fetch(`${API_BASE}/api/best-bets/${betId}/result`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result, notes }),
    })
    return res.json()
}

async function saveBet(bet, sport, date) {
    const res = await fetch(`${API_BASE}/api/best-bets/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...bet, sport, date }),
    })
    return res.json()
}

async function fetchExpertPicks(date, sport = null) {
    const params = new URLSearchParams({ date })
    if (sport && sport !== "both") params.set("sport", sport)
    try {
        const res = await fetch(`${API_BASE}/api/expert-picks?${params}`)
        if (!res.ok) return []
        const data = await res.json()
        return data.picks || []
    } catch { return [] }
}

async function deleteExpertPick(id) {
    try {
        const res = await fetch(`${API_BASE}/api/expert-picks/${id}`, { method: "DELETE" })
        return res.ok
    } catch { return false }
}

// ── Result Badge ──────────────────────────────────────────────
function ResultBadge({ result, betDate }) {
    const cfg = {
        WIN: { icon: CheckCircle2, label: "WIN", cls: "text-emerald-400 bg-emerald-500/15" },
        LOSS: { icon: XCircle, label: "LOSS", cls: "text-red-400 bg-red-500/15" },
        VOID: { icon: Minus, label: "NUL", cls: "text-slate-400 bg-slate-500/15" },
        PENDING: { icon: Clock, label: "En cours", cls: "text-amber-400 bg-amber-500/15" },
    }
    let effectiveResult = result || "PENDING"
    // If PENDING but match date is in the past → show "Terminé" instead of "En cours"
    if (effectiveResult === "PENDING" && betDate) {
        const now = new Date()
        const matchDay = new Date(betDate + "T23:30:00")
        if (now > matchDay) {
            effectiveResult = "_DONE"
        }
    }
    if (effectiveResult === "_DONE") {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold text-blue-400 bg-blue-500/15">
                <Clock className="w-3 h-3" />
                Terminé ⏳
            </span>
        )
    }
    const { icon: Icon, label, cls } = cfg[effectiveResult] || cfg.PENDING
    return (
        <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold", cls)}>
            <Icon className="w-3 h-3" />
            {label}
        </span>
    )
}

// ── Confidence Stars ──────────────────────────────────────────
function ConfStars({ conf }) {
    const stars = conf >= 8 ? 3 : conf >= 6 ? 2 : 1
    return (
        <span className="text-amber-400 text-xs">
            {"⭐".repeat(stars)}
        </span>
    )
}

// ── Market Badge ──────────────────────────────────────────────
function MarketBadge({ market }) {
    const colors = {
        "Victoire domicile": "bg-blue-500/15 text-blue-400",
        "Victoire extérieur": "bg-purple-500/15 text-purple-400",
        "Match nul": "bg-slate-500/15 text-slate-400",
        "BTTS — Les deux équipes marquent": "bg-pink-500/15 text-pink-400",
        "Over 2.5 buts": "bg-orange-500/15 text-orange-400",
        "Over 1.5 buts": "bg-emerald-500/15 text-emerald-400",
        "Over 3.5 buts": "bg-red-500/15 text-red-400",
        "player_points_over_0.5": "bg-cyan-500/15 text-cyan-400",
    }
    const label = market === "player_points_over_0.5" ? "Over 0.5 Points" : market
    return (
        <span className={cn("px-2 py-0.5 rounded text-[10px] font-semibold", colors[market] || "bg-primary/15 text-primary")}>
            {label}
        </span>
    )
}

// ── Bet Card ──────────────────────────────────────────────────
function BetCard({ bet, sport, date, isAdmin, onResultUpdate }) {
    const [updating, setUpdating] = useState(false)
    const [localResult, setLocalResult] = useState(bet.result || "PENDING")
    const [betId, setBetId] = useState(bet.id)
    const [saving, setSaving] = useState(false)

    async function handleSave() {
        setSaving(true)
        try {
            const resp = await saveBet(bet, sport, date)
            if (resp.id) {
                setBetId(resp.id)
                setLocalResult("PENDING")
            }
        } finally { setSaving(false) }
    }

    async function handleResult(result) {
        if (!betId) {
            // Save first, then update
            setSaving(true)
            try {
                const resp = await saveBet(bet, sport, date)
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
    const isBestOdds = bet.odds >= 1.75 && bet.odds <= 2.20

    return (
        <div className={cn(
            "rounded-xl border p-4 transition-all duration-200",
            localResult === "WIN" && "border-emerald-500/30 bg-emerald-500/5",
            localResult === "LOSS" && "border-red-500/20 bg-red-500/5",
            localResult === "PENDING" && "border-border/60 bg-card hover:border-border",
            localResult === "VOID" && "border-slate-500/20 bg-slate-500/5",
        )}>
            <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground leading-tight">{bet.label}</p>
                    <div className="flex items-center flex-wrap gap-1.5 mt-1.5">
                        <MarketBadge market={bet.market} />
                        {bet.is_value && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/15 text-amber-400 uppercase tracking-wider">
                                Value ✨
                            </span>
                        )}
                        {isBestOdds && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-400">
                                Cible 🎯
                            </span>
                        )}
                    </div>
                </div>
                <ResultBadge result={localResult} betDate={date} />
            </div>

            <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="font-mono font-bold text-foreground text-base">
                        {bet.odds?.toFixed(2)}
                    </span>
                    <div className="flex flex-col">
                        <span>{bet.proba_model?.toFixed(0)}% modèle</span>
                        {bet.proba_bookmaker != null && (
                            <span className="text-[10px] text-muted-foreground">
                                {bet.proba_bookmaker.toFixed(0)}% bookmaker
                            </span>
                        )}
                        <ConfStars conf={bet.confidence} />
                    </div>
                    {bet.ev != null && bet.ev > 0 && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-400">
                            EV +{(bet.ev * 100).toFixed(1)}%
                        </span>
                    )}
                    {bet.bookmaker && (
                        <span className="text-[9px] text-muted-foreground opacity-60 capitalize">
                            {bet.bookmaker}
                        </span>
                    )}
                </div>


                {isAdmin && (
                    <div className="flex items-center gap-1">
                        {!isTracked && localResult === "PENDING" && (
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="px-2 py-1 rounded text-[10px] font-bold bg-primary/15 text-primary hover:bg-primary/25 transition-colors disabled:opacity-50"
                            >
                                {saving ? "..." : "Tracker"}
                            </button>
                        )}
                        {(isTracked || localResult !== "PENDING") && (
                            <div className="flex gap-1">
                                <button
                                    onClick={() => handleResult("WIN")}
                                    disabled={updating}
                                    className="w-7 h-7 rounded flex items-center justify-center bg-emerald-500/15 hover:bg-emerald-500/30 transition-colors text-emerald-400 disabled:opacity-50"
                                    title="WIN"
                                >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => handleResult("LOSS")}
                                    disabled={updating}
                                    className="w-7 h-7 rounded flex items-center justify-center bg-red-500/15 hover:bg-red-500/30 transition-colors text-red-400 disabled:opacity-50"
                                    title="LOSS"
                                >
                                    <XCircle className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => handleResult("VOID")}
                                    disabled={updating}
                                    className="w-7 h-7 rounded flex items-center justify-center bg-slate-500/15 hover:bg-slate-500/30 transition-colors text-slate-400 disabled:opacity-50"
                                    title="NUL/VOID"
                                >
                                    <Minus className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

// ── Stats Dashboard (Admin only) ────────────────────────────
function StatsDashboard({ stats, isAdmin }) {
    if (!isAdmin) return null
    if (!stats || stats.error) return null

    const { global: g, football: f, nhl: n } = stats

    function StatCard({ label, data, color }) {
        if (!data || data.total === 0) return (
            <div className="rounded-xl border border-border/60 bg-card p-4 text-center">
                <p className="text-xs text-muted-foreground mb-1">{label}</p>
                <p className="text-muted-foreground text-sm">Aucun résultat</p>
            </div>
        )
        return (
            <div className={cn("rounded-xl border p-3 overflow-hidden", color)}>
                <p className="text-[10px] text-muted-foreground mb-1.5 truncate">{label}</p>
                <div className="flex items-end gap-1">
                    <span className="text-xl font-black leading-tight">{data.win_rate}%</span>
                    <span className="text-[9px] text-muted-foreground mb-0.5">réussite</span>
                </div>
                <div className="flex items-center gap-1.5 mt-1.5 text-[10px] text-muted-foreground flex-wrap">
                    <span className="text-emerald-400 font-semibold">{data.wins}W</span>
                    <span className="text-red-400 font-semibold">{data.losses}L</span>
                </div>
                <div className={cn("text-[10px] font-bold mt-1", data.roi_pct >= 0 ? "text-emerald-400" : "text-red-400")}>
                    ROI {data.roi_pct >= 0 ? "+" : ""}{data.roi_pct}%
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-border/40 overflow-hidden">
                    <div
                        className="h-full bg-emerald-500 rounded-full transition-all duration-700"
                        style={{ width: `${data.win_rate}%` }}
                    />
                </div>
            </div>
        )
    }

    // Market name display — rename internal algo names to user-friendly labels
    const marketLabels = {
        "Victoire domicile": "Victoire domicile",
        "Victoire extérieur": "Victoire extérieur",
        "Victoire": "Victoire",
        "Match nul": "Match nul",
        "BTTS — Les deux équipes marquent": "BTTS",
        "BTTS": "BTTS",
        "Over 2.5 buts": "Over 2.5 buts",
        "Over 1.5 buts": "Over 1.5 buts",
        "Over 3.5 buts": "Over 3.5 buts",
        "Double chance 1N": "Double Chance 1N",
        "player_points_over_0.5": "Over 0.5 Pts (NHL)",
        "fun_football": "Football IA",
        "fun_nhl": "NHL IA",
        "safe_football": "Football Safe",
        "safe_nhl": "NHL Safe",
        "Victoire + Over 1.5": "Victoire + Over 1.5",
    }

    const byMarket = stats.by_market || {}
    const sortedMarkets = Object.entries(byMarket)
        .filter(([, data]) => data.total >= 3)
        .sort((a, b) => b[1].total - a[1].total)

    return (
        <div className="mt-6">
            <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-bold">Performance ProbaLab</h2>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-primary/15 text-primary">Admin</span>
                <span className="text-[10px] text-muted-foreground ml-1">({g.total} paris résolus)</span>
            </div>

            {/* Global stats cards */}
            <div className="grid grid-cols-3 gap-3">
                <StatCard label="🌍 Global" data={g} color="border-primary/20 bg-primary/5" />
                <StatCard label="⚽ Football" data={f} color="border-emerald-500/20 bg-emerald-500/5" />
                <StatCard label="🏒 NHL" data={n} color="border-cyan-500/20 bg-cyan-500/5" />
            </div>

            {/* Market breakdown table */}
            {sortedMarkets.length > 0 && (
                <div className="mt-4 rounded-xl border border-border/60 bg-card overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-border/40">
                        <p className="text-xs font-semibold">Détail par type de pari</p>
                    </div>
                    <div className="divide-y divide-border/30">
                        {sortedMarkets.map(([market, data]) => (
                            <div key={market} className="flex items-center justify-between px-4 py-2.5">
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                    <span className="text-xs text-foreground font-medium truncate">
                                        {marketLabels[market] || market}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground shrink-0">
                                        {data.total} paris
                                    </span>
                                </div>
                                <div className="flex items-center gap-3 shrink-0">
                                    <span className="text-xs font-bold">{data.win_rate}%</span>
                                    <span className="text-[10px] text-emerald-400">{data.wins}W</span>
                                    <span className="text-[10px] text-red-400">{data.losses}L</span>
                                    <span className={cn(
                                        "text-[10px] font-semibold w-14 text-right",
                                        data.roi_pct >= 0 ? "text-emerald-400" : "text-red-400"
                                    )}>
                                        {data.roi_pct >= 0 ? "+" : ""}{data.roi_pct}%
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* 30-day timeline */}
            {stats.timeline?.length > 0 && (
                <div className="mt-4 rounded-xl border border-border/60 bg-card p-4">
                    <p className="text-xs text-muted-foreground mb-3">Historique 30 jours</p>
                    <div className="flex items-end gap-0.5 h-12">
                        {stats.timeline.map((d, i) => {
                            const total = d.wins + d.losses
                            const winPct = total ? d.wins / total : 0
                            return (
                                <div key={i} className="flex-1 flex flex-col gap-0.5 h-full justify-end" title={`${d.date}: ${d.wins}W ${d.losses}L`}>
                                    {d.losses > 0 && (
                                        <div
                                            className="w-full bg-red-500/40 rounded-sm"
                                            style={{ height: `${(d.losses / Math.max(total, 1)) * 100}%` }}
                                        />
                                    )}
                                    {d.wins > 0 && (
                                        <div
                                            className="w-full bg-emerald-500/60 rounded-sm"
                                            style={{ height: `${winPct * 100}%` }}
                                        />
                                    )}
                                </div>
                            )
                        })}
                    </div>
                    <div className="flex justify-between mt-1 text-[9px] text-muted-foreground">
                        <span>{stats.timeline[0]?.date}</span>
                        <span>{stats.timeline[stats.timeline.length - 1]?.date}</span>
                    </div>
                </div>
            )}

            {/* ── Model Prediction Accuracy (ProbaLab IA) ──────── */}
            {stats.model_by_market && Object.keys(stats.model_by_market).length > 0 && (
                <div className="mt-5">
                    <div className="flex items-center gap-2 mb-3">
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                        <span className="text-xs font-bold uppercase tracking-wider">Performance (30 J)</span>
                        <div className="ml-auto flex items-center gap-1.5">
                            <span className="text-[10px] font-bold text-muted-foreground uppercase bg-muted px-1.5 py-0.5 rounded">Experts + IA</span>
                        </div>
                    </div>

                    {/* Model global cards */}
                    <div className="grid grid-cols-2 gap-3 mb-3">
                        {stats.model_football?.total > 0 && (
                            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 overflow-hidden">
                                <p className="text-[10px] text-muted-foreground mb-1">⚽ Football IA</p>
                                <div className="flex items-end gap-1">
                                    <span className="text-xl font-black leading-tight">{stats.model_football.win_rate}%</span>
                                    <span className="text-[9px] text-muted-foreground mb-0.5">réussite</span>
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground">
                                    <span className="text-emerald-400 font-semibold">{stats.model_football.wins}W</span>
                                    <span className="text-red-400 font-semibold">{stats.model_football.losses}L</span>
                                </div>
                            </div>
                        )}
                        {stats.model_nhl?.total > 0 && (
                            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3 overflow-hidden">
                                <p className="text-[10px] text-muted-foreground mb-1">🏒 NHL IA</p>
                                <div className="flex items-end gap-1">
                                    <span className="text-xl font-black leading-tight">{stats.model_nhl.win_rate}%</span>
                                    <span className="text-[9px] text-muted-foreground mb-0.5">réussite</span>
                                </div>
                                <div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground">
                                    <span className="text-emerald-400 font-semibold">{stats.model_nhl.wins}W</span>
                                    <span className="text-red-400 font-semibold">{stats.model_nhl.losses}L</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Model market breakdown */}
                    <div className="rounded-xl border border-border/60 bg-card overflow-hidden">
                        <div className="px-4 py-2.5 border-b border-border/40">
                            <p className="text-xs font-semibold">Précision par type de prédiction</p>
                        </div>
                        <div className="divide-y divide-border/30">
                            {Object.entries(stats.model_by_market)
                                .filter(([, data]) => data.total >= 3)
                                .sort(([, a], [, b]) => b.total - a.total)
                                .map(([market, data]) => (
                                    <div key={market} className="flex items-center justify-between px-4 py-2.5">
                                        <div className="flex items-center gap-2 flex-1 min-w-0">
                                            <span className="text-xs text-foreground font-medium truncate">
                                                {marketLabels[market] || market}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground shrink-0">
                                                {data.total} paris
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3 shrink-0">
                                            <span className="text-xs font-bold">{data.win_rate}%</span>
                                            <span className="text-[10px] text-emerald-400">{data.wins}W</span>
                                            <span className="text-[10px] text-red-400">{data.losses}L</span>
                                        </div>
                                    </div>
                                ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

// ── Expert Pick Card ──────────────────────────────────────────
function ExpertPickCard({ pick, isAdmin = false, onDelete }) {
    const [deleting, setDeleting] = useState(false)
    const resultCfg = {
        WIN: { icon: CheckCircle2, label: "WIN", cls: "text-emerald-400 bg-emerald-500/15" },
        LOSS: { icon: XCircle, label: "LOSS", cls: "text-red-400 bg-red-500/15" },
        VOID: { icon: Minus, label: "NUL", cls: "text-slate-400 bg-slate-500/15" },
        PENDING: { icon: Clock, label: "En cours", cls: "text-amber-400 bg-amber-500/15" },
    }
    const { icon: Icon, label, cls } = resultCfg[pick.result || "PENDING"] || resultCfg.PENDING
    const sportEmoji = pick.sport === "nhl" ? "🏒" : "⚽"

    // Bet type styling
    const betTypeCfg = {
        SAFE: { label: "🛡 SAFE", cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
        FUN: { label: "🎲 FUN", cls: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
        EXPERT: { label: "🎯 Expert", cls: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
    }
    const betType = betTypeCfg[pick.bet_type] || betTypeCfg.EXPERT

    // Use enriched selections from API, fallback to parsing expert_note
    let selections = pick.selections || []
    if (selections.length === 0) {
        try {
            if (pick.expert_note && pick.expert_note.startsWith("[")) {
                const parsed = JSON.parse(pick.expert_note)
                if (Array.isArray(parsed)) {
                    selections = parsed.map(s => ({
                        match: s.match || "",
                        market: s.bet || "",
                        player_name: null,
                        bet_raw: s.bet || "",
                        is_mymatch: false,
                    }))
                }
            }
        } catch { }
    }

    async function handleDelete() {
        if (!confirm("Supprimer ce pick expert ?")) return
        setDeleting(true)
        const ok = await deleteExpertPick(pick.id)
        if (ok) onDelete?.(pick.id)
        else setDeleting(false)
    }

    // Card border color based on bet type
    const cardBorderCls =
        pick.bet_type === "SAFE" ? "border-emerald-500/30 bg-emerald-500/5" :
        pick.bet_type === "FUN" ? "border-purple-500/30 bg-purple-500/5" :
        "border-amber-500/30 bg-amber-500/5"

    return (
        <div className={cn("rounded-xl border p-4 transition-all duration-200", cardBorderCls)}>
            <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                    {/* Bet type + sport badge */}
                    <div className="flex items-center gap-1.5 mb-2">
                        <span className={cn("px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-wider border", betType.cls)}>
                            {betType.label}
                        </span>
                        <span className="text-[10px] text-muted-foreground">{sportEmoji} {pick.sport?.toUpperCase()}</span>
                        {pick.is_combine && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-500/15 text-blue-400">
                                Combiné {selections.length}
                            </span>
                        )}
                        {pick.has_mymatch && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-pink-500/15 text-pink-400 border border-pink-500/20">
                                MyMatch
                            </span>
                        )}
                    </div>

                    {/* Selections display */}
                    {selections.length > 0 ? (
                        <div className="space-y-1.5">
                            {selections.map((sel, i) => (
                                <div key={i} className="rounded-lg bg-background/40 px-3 py-1.5">
                                    {/* Match name */}
                                    <p className="text-[11px] text-muted-foreground leading-tight">
                                        {sel.match || pick.match_label || ""}
                                    </p>
                                    {/* Market type */}
                                    <p className="text-xs text-foreground/80 mt-0.5">
                                        {sel.market || sel.bet_raw || pick.market || ""}
                                    </p>
                                    {/* Player name in bold */}
                                    {sel.player_name && (
                                        <p className="text-sm font-bold text-foreground mt-0.5">
                                            {sel.player_name}
                                        </p>
                                    )}
                                    {/* MyMatch badge per selection */}
                                    {sel.is_mymatch && (
                                        <span className="inline-block mt-1 px-1 py-0.5 rounded text-[8px] font-bold bg-pink-500/10 text-pink-400">
                                            MYMATCH
                                        </span>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <>
                            <p className="text-sm font-semibold text-foreground leading-tight">
                                {pick.player_name
                                    ? `${pick.player_name} — ${pick.market}`
                                    : pick.market || pick.match_label || "Pick Expert"}
                            </p>
                            {pick.match_label && (
                                <p className="text-[11px] text-muted-foreground mt-0.5">{pick.match_label}</p>
                            )}
                        </>
                    )}

                    {/* Expert note (if not JSON) */}
                    {pick.expert_note && !pick.expert_note.startsWith("[") && !pick.expert_note.startsWith("[odds=") && (
                        <p className="text-[11px] text-amber-300/70 mt-1.5 italic">&ldquo;{pick.expert_note}&rdquo;</p>
                    )}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold", cls)}>
                        <Icon className="w-3 h-3" />
                        {label}
                    </span>
                    {isAdmin && (
                        <button
                            onClick={handleDelete}
                            disabled={deleting}
                            className="w-6 h-6 rounded flex items-center justify-center bg-red-500/15 hover:bg-red-500/30 transition-colors text-red-400 disabled:opacity-40"
                            title="Supprimer ce pick"
                        >
                            <Trash2 className="w-3 h-3" />
                        </button>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-4 mt-3 text-xs">
                {pick.odds && (
                    <span className="font-mono font-bold text-foreground text-base">
                        {Number(pick.odds).toFixed(2)}
                    </span>
                )}
                {pick.confidence && (
                    <span className="text-amber-400">{"⭐".repeat(pick.confidence >= 8 ? 3 : pick.confidence >= 6 ? 2 : 1)}</span>
                )}
                <span className="text-[10px] text-muted-foreground ml-auto">
                    📅 {pick.date}
                </span>
            </div>
        </div>
    )
}

// ── Premium Lock Screen ───────────────────────────────────────
function PremiumLock() {
    return (
        <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-amber-500/15 flex items-center justify-center mb-5 border border-amber-500/20">
                <Lock className="w-7 h-7 text-amber-400" />
            </div>
            <h2 className="text-lg font-bold mb-2">Accès Premium requis</h2>
            <p className="text-muted-foreground text-sm max-w-sm mb-6">
                Les <strong>Pronos du Jour</strong> — sélection quotidienne des 5 meilleurs pronos ⚽ + 🏒 —
                sont réservés aux abonnés Premium.
            </p>
            <a
                href="/premium"
                className="px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm transition-colors"
            >
                <Trophy className="w-4 h-4 inline mr-1.5" />
                Passer à Premium
            </a>
        </div>
    )
}

// ── Main Page ─────────────────────────────────────────────────
export default function ParisDuSoir() {
    const { hasAccess, isAdmin } = useAuth()
    const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
    const [sportFilter, setSportFilter] = useState("both") // "both" | "football" | "nhl"
    const [bets, setBets] = useState(null)
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)
    const [showHistory, setShowHistory] = useState(false)
    const [history, setHistory] = useState(null)
    const [historyLoading, setHistoryLoading] = useState(false)
    const [expertPicks, setExpertPicks] = useState([])

    const canAccess = hasAccess("premium")

    useEffect(() => {
        if (!canAccess) return
        setLoading(true)
        setBets(null)
        fetchBestBets(date, sportFilter === "both" ? null : sportFilter)
            .then(setBets)
            .finally(() => setLoading(false))
    }, [date, sportFilter, canAccess, refreshKey])

    useEffect(() => {
        if (!canAccess) return
        fetchBestBetsStats().then(setStats)
    }, [canAccess, refreshKey])

    // Fetch expert picks (Telegram bot)
    useEffect(() => {
        if (!canAccess) return
        fetchExpertPicks(date, sportFilter).then(setExpertPicks)
    }, [date, sportFilter, canAccess, refreshKey])

    // Fetch history when toggled on
    useEffect(() => {
        if (!showHistory || !canAccess) return
        setHistoryLoading(true)
        const sportParam = sportFilter === "both" ? "" : `&sport=${sportFilter}`
        fetch(`${API_BASE}/api/best-bets/history?days=60${sportParam}`)
            .then(r => r.json())
            .then(setHistory)
            .catch(() => { })
            .finally(() => setHistoryLoading(false))
    }, [showHistory, sportFilter, canAccess])

    if (!canAccess) return <PremiumLock />

    const dateObj = new Date(date + "T12:00:00")
    const formattedDate = format(dateObj, "EEEE d MMMM", { locale: fr })

    const footballBets = bets?.football || []
    const nhlBets = bets?.nhl || []

    function BetSection({ sport, betsArr, emoji, label, accentColor }) {
        return (
            <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">{emoji}</span>
                    <h2 className={cn("text-sm font-bold", accentColor)}>{label}</h2>
                    <span className="text-xs text-muted-foreground">— 5 meilleurs pronos</span>
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
                        {betsArr.map((bet, i) => (
                            <BetCard
                                key={bet.fixture_id || i}
                                bet={bet}
                                sport={sport}
                                date={date}
                                isAdmin={isAdmin}
                                onResultUpdate={() => setRefreshKey(k => k + 1)}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-xs text-muted-foreground border border-dashed border-border/50 rounded-xl">
                        Aucun prono {label} détecté pour cette date.
                    </div>
                )}
            </div>
        )
    }

    async function resolveBet(id, result) {
        if (!id) return
        try {
            await fetch(`${API_BASE}/api/best-bets/${id}/result`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ result }),
            })
            setRefreshKey(k => k + 1)
        } catch { }
    }

    return (
        <div className="animate-fade-in-up px-3 pt-4 pb-8 max-w-3xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-primary" />
                    <h1 className="text-base font-black capitalize">{formattedDate}</h1>
                </div>
                <div className="flex items-center gap-1.5">
                    {/* Date nav */}
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
                        title="Rafraîchir"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Strategy reminder */}
            <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 mb-5 flex items-center gap-3">
                <Sparkles className="w-4 h-4 text-primary shrink-0" />
                <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">Stratégie :</strong>{" "}
                    Simples 90% (cotes 1.75–2.20) · Doubles 10% (~2.00) · Mise 1% bankroll · Max 5 paris/soir · 1 Fun/jour si opportunité
                </p>
            </div>

            {/* Expert Picks section */}
            {!showHistory && (
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
                    {/* Stats — admin only */}
                    <StatsDashboard stats={stats} isAdmin={isAdmin} />
                </>
            ) : (
                /* ── History Table ──────────────────────────────────── */
                <div className="space-y-3">
                    {historyLoading ? (
                        <div className="space-y-2">
                            {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
                        </div>
                    ) : history?.picks?.length > 0 ? (
                        <>
                            {/* Summary header */}
                            <div className="flex items-center justify-between px-3 py-2.5 rounded-xl border border-border/50 bg-card">
                                <div className="flex items-center gap-4 text-xs">
                                    <span className="text-muted-foreground">{history.resolved} résolus / {history.total} total</span>
                                </div>
                                <span className={cn(
                                    "text-sm font-black",
                                    history.total_pl >= 0 ? "text-emerald-500" : "text-red-500"
                                )}>
                                    P&L : {history.total_pl >= 0 ? "+" : ""}{history.total_pl} u
                                </span>
                            </div>

                            {/* Picks table */}
                            <div className="rounded-xl border border-border/50 bg-card overflow-hidden">
                                <div className="divide-y divide-border/30">
                                    {history.picks.map((pick) => {
                                        const isWin = pick.result === "WIN"
                                        const isLoss = pick.result === "LOSS"
                                        const isPending = pick.result === "PENDING"
                                        return (
                                            <div key={pick.id} className="flex items-center gap-2 px-3 py-2.5">
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
                                                    <div className="text-xs font-medium truncate">
                                                        {pick.bet_label || pick.player_name || "—"}
                                                    </div>
                                                    <div className="flex items-center gap-1.5 mt-0.5">
                                                        <span className="text-[9px] text-muted-foreground">{pick.date}</span>
                                                        <span className="text-[9px] px-1 py-0.5 rounded bg-muted text-muted-foreground">
                                                            {pick.sport === "nhl" ? "🏒" : "⚽"} {pick.market || "—"}
                                                        </span>
                                                    </div>
                                                </div>

                                                {/* Odds + P&L */}
                                                <div className="shrink-0 text-right">
                                                    <div className="text-xs font-bold tabular-nums">
                                                        @{parseFloat(pick.odds || 0).toFixed(2)}
                                                    </div>
                                                    <div className={cn(
                                                        "text-[10px] font-semibold tabular-nums",
                                                        isWin ? "text-emerald-500" :
                                                            isLoss ? "text-red-500" :
                                                                "text-muted-foreground"
                                                    )}>
                                                        {isWin ? `+${(parseFloat(pick.odds || 0) - 1).toFixed(2)}u` :
                                                            isLoss ? "-1.00u" :
                                                                isPending ? "⏳" : "—"}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="text-center py-12 text-xs text-muted-foreground border border-dashed border-border/50 rounded-xl">
                            Aucun historique disponible.
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
