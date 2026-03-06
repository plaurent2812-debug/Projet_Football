import { useState, useEffect } from "react"
import { format, addDays, subDays } from "date-fns"
import { fr } from "date-fns/locale"
import {
    ChevronLeft, ChevronRight, Target, Trophy, Lock,
    CheckCircle2, XCircle, Clock, Minus, TrendingUp,
    BarChart3, Star, Sparkles, RefreshCw
} from "lucide-react"
import { cn } from "@/lib/utils"
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

// ── Result Badge ──────────────────────────────────────────────
function ResultBadge({ result }) {
    const cfg = {
        WIN: { icon: CheckCircle2, label: "WIN", cls: "text-emerald-400 bg-emerald-500/15" },
        LOSS: { icon: XCircle, label: "LOSS", cls: "text-red-400 bg-red-500/15" },
        VOID: { icon: Minus, label: "NUL", cls: "text-slate-400 bg-slate-500/15" },
        PENDING: { icon: Clock, label: "En cours", cls: "text-amber-400 bg-amber-500/15" },
    }
    const { icon: Icon, label, cls } = cfg[result] || cfg.PENDING
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
                <ResultBadge result={localResult} />
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
            <div className={cn("rounded-xl border p-4", color)}>
                <p className="text-xs text-muted-foreground mb-2">{label}</p>
                <div className="flex items-end gap-2">
                    <span className="text-2xl font-black">{data.win_rate}%</span>
                    <span className="text-xs text-muted-foreground mb-0.5">réussite</span>
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                    <span className="text-emerald-400 font-semibold">{data.wins}W</span>
                    <span className="text-red-400 font-semibold">{data.losses}L</span>
                    {data.voids > 0 && <span className="text-slate-400">{data.voids} nul</span>}
                    <span className={cn("font-bold ml-auto", data.roi_pct >= 0 ? "text-emerald-400" : "text-red-400")}>
                        ROI {data.roi_pct >= 0 ? "+" : ""}{data.roi_pct}%
                    </span>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-border/40 overflow-hidden">
                    <div
                        className="h-full bg-emerald-500 rounded-full transition-all duration-700"
                        style={{ width: `${data.win_rate}%` }}
                    />
                </div>
            </div>
        )
    }

    // Market name display
    const marketLabels = {
        "Victoire domicile": "Victoire domicile",
        "Victoire extérieur": "Victoire extérieur",
        "Match nul": "Match nul",
        "BTTS — Les deux équipes marquent": "BTTS",
        "Over 2.5 buts": "Over 2.5 buts",
        "Over 1.5 buts": "Over 1.5 buts",
        "Over 3.5 buts": "Over 3.5 buts",
        "player_points_over_0.5": "Over 0.5 Pts (NHL)",
    }

    const byMarket = stats.by_market || {}
    const sortedMarkets = Object.entries(byMarket).sort((a, b) => b[1].total - a[1].total)

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
                Les <strong>Paris du Soir</strong> — sélection quotidienne des 5 meilleurs paris ⚽ + 🏒 —
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
                    <span className="text-xs text-muted-foreground">— 5 meilleurs paris</span>
                    {isAdmin && betsArr.length > 0 && (
                        <span className="ml-auto text-[9px] text-muted-foreground">
                            Boutons WIN/LOSS visibles (admin)
                        </span>
                    )}
                </div>
                {loading ? (
                    <div className="space-y-3">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="h-24 rounded-xl bg-card border border-border/40 animate-pulse" />
                        ))}
                    </div>
                ) : betsArr.length === 0 ? (
                    <div className="rounded-xl border border-border/40 bg-card p-6 text-center text-sm text-muted-foreground">
                        Aucun pari sélectionné pour cette date / ce filtre.
                    </div>
                ) : (
                    <div className="space-y-3">
                        {betsArr.map((bet, i) => (
                            <BetCard
                                key={i}
                                bet={bet}
                                sport={sport}
                                date={date}
                                isAdmin={isAdmin}
                                onResultUpdate={() => setRefreshKey(k => k + 1)}
                            />
                        ))}
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto px-3 pb-24 pt-4">
            {/* Header */}
            <div className="mb-5">
                <div className="flex items-center gap-2 mb-1">
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                        <Target className="w-3.5 h-3.5 text-white" />
                    </div>
                    <h1 className="text-base font-black">Paris du Soir</h1>
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 uppercase tracking-wider">
                        Premium
                    </span>
                </div>
                <p className="text-xs text-muted-foreground pl-9">
                    Sélection quotidienne · cotes cibles 1.75 – 2.20 · gestion 1% bankroll
                </p>
            </div>

            {/* Date bar */}
            <div className="flex items-center justify-between bg-card border border-border/60 rounded-xl px-4 py-2.5 mb-4">
                <button
                    onClick={() => setDate(subDays(dateObj, 1).toISOString().slice(0, 10))}
                    className="p-1 rounded hover:bg-accent/60 transition-colors"
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="text-center">
                    <p className="text-xs font-bold capitalize">{formattedDate}</p>
                    <p className="text-[10px] text-muted-foreground font-mono">{date}</p>
                </div>
                <button
                    onClick={() => setDate(addDays(dateObj, 1).toISOString().slice(0, 10))}
                    className="p-1 rounded hover:bg-accent/60 transition-colors"
                >
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>

            {/* Sport filter */}
            <div className="flex gap-1.5 mb-5">
                {[
                    { v: "both", label: "Tous" },
                    { v: "football", label: "⚽ Football" },
                    { v: "nhl", label: "🏒 NHL" },
                ].map(({ v, label }) => (
                    <button
                        key={v}
                        onClick={() => setSportFilter(v)}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                            sportFilter === v
                                ? "bg-primary text-primary-foreground"
                                : "bg-card border border-border/60 text-muted-foreground hover:text-foreground"
                        )}
                    >
                        {label}
                    </button>
                ))}
                <button
                    onClick={() => setRefreshKey(k => k + 1)}
                    className="ml-auto p-1.5 rounded-lg bg-card border border-border/60 text-muted-foreground hover:text-foreground transition-colors"
                    title="Rafraîchir"
                >
                    <RefreshCw className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Strategy reminder */}
            <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 mb-5 flex items-center gap-3">
                <Sparkles className="w-4 h-4 text-primary shrink-0" />
                <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">Stratégie :</strong>{" "}
                    Simples 90% (cotes 1.75–2.20) · Doubles 10% (~2.00) · Mise 1% bankroll · Max 5 paris/soir
                </p>
            </div>

            {/* Football bets */}
            {(sportFilter === "both" || sportFilter === "football") && (
                <BetSection
                    sport="football"
                    betsArr={footballBets}
                    emoji="⚽"
                    label="Football"
                    accentColor="text-emerald-400"
                />
            )}

            {/* NHL bets */}
            {(sportFilter === "both" || sportFilter === "nhl") && (
                <BetSection
                    sport="nhl"
                    betsArr={nhlBets}
                    emoji="🏒"
                    label="NHL"
                    accentColor="text-cyan-400"
                />
            )}

            {/* NHL fallback note */}
            {bets?.nhl_note && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/8 px-3 py-2 mb-3 flex items-start gap-2">
                    <span className="text-amber-400 text-xs shrink-0">⚠️</span>
                    <p className="text-[10px] text-amber-400/80">{bets.nhl_note}</p>
                </div>
            )}

            {/* Stats — admin only */}
            <StatsDashboard stats={stats} isAdmin={isAdmin} />
        </div>
    )
}
