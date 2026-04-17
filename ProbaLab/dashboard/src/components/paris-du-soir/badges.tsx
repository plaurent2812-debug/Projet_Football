import { CheckCircle2, XCircle, Clock, Minus } from "lucide-react"
import { cn } from "@/lib/utils"

// ── Result Badge ──────────────────────────────────────────────
export function ResultBadge({ result, betDate }: { result?: string; betDate?: string }) {
    const cfg: Record<string, { icon: React.ElementType; label: string; cls: string }> = {
        WIN: { icon: CheckCircle2, label: "WIN", cls: "text-emerald-400 bg-emerald-500/15" },
        LOSS: { icon: XCircle, label: "LOSS", cls: "text-red-400 bg-red-500/15" },
        VOID: { icon: Minus, label: "NUL", cls: "text-slate-400 bg-slate-500/15" },
        PENDING: { icon: Clock, label: "En cours", cls: "text-amber-400 bg-amber-500/15" },
    }
    let effectiveResult = result || "PENDING"
    if (effectiveResult === "PENDING" && betDate) {
        const now = new Date()
        const matchDay = new Date(betDate + "T23:30:00")
        if (now > matchDay) {
            effectiveResult = "_DONE"
        }
    }
    if (effectiveResult === "_DONE") {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold text-blue-400 bg-blue-500/15">
                <Clock className="w-3 h-3" />
                Termine
            </span>
        )
    }
    const { icon: Icon, label, cls } = cfg[effectiveResult] || cfg.PENDING
    return (
        <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold", cls)}>
            <Icon className="w-3 h-3" />
            {label}
        </span>
    )
}

// ── Confidence Stars ──────────────────────────────────────────
export function ConfStars({ conf }: { conf: number }) {
    const stars = conf >= 8 ? 3 : conf >= 6 ? 2 : 1
    return (
        <span className="text-amber-400 text-xs">
            {"⭐".repeat(stars)}
        </span>
    )
}

// ── Market Badge ──────────────────────────────────────────────
const MARKET_COLORS: Record<string, string> = {
    "Victoire domicile": "bg-blue-500/15 text-blue-400",
    "Victoire exterieur": "bg-purple-500/15 text-purple-400",
    "Match nul": "bg-slate-500/15 text-slate-400",
    "Double Chance 1X": "bg-blue-500/15 text-blue-400",
    "Double Chance X2": "bg-purple-500/15 text-purple-400",
    "BTTS — Les deux equipes marquent": "bg-pink-500/15 text-pink-400",
    "BTTS Oui": "bg-pink-500/15 text-pink-400",
    "Over 2.5 buts": "bg-orange-500/15 text-orange-400",
    "Over 1.5 buts": "bg-emerald-500/15 text-emerald-400",
    "Over 3.5 buts": "bg-red-500/15 text-red-400",
    "player_points_over_0.5": "bg-cyan-500/15 text-cyan-400",
    "player_assists_over_0.5": "bg-cyan-500/15 text-cyan-400",
    "player_goals_over_0.5": "bg-cyan-500/15 text-cyan-400",
    "player_shots_over_2.5": "bg-cyan-500/15 text-cyan-400",
}

const MARKET_LABEL_MAP: Record<string, string> = {
    "player_points_over_0.5": "Over 0.5 Points",
    "player_assists_over_0.5": "Over 0.5 Assists",
    "player_goals_over_0.5": "Over 0.5 Goals",
    "player_shots_over_2.5": "Over 2.5 Tirs",
}

export function MarketBadge({ market }: { market: string }) {
    const label = MARKET_LABEL_MAP[market] || market
    return (
        <span className={cn("px-2 py-0.5 rounded text-xs font-semibold", MARKET_COLORS[market] || "bg-primary/15 text-primary")}>
            {label}
        </span>
    )
}
