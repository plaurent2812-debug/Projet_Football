import { useState } from "react"
import { CheckCircle2, XCircle, Clock, Minus, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatOdds } from "@/lib/statsHelper"
import { deleteExpertPick } from "./api"

interface Selection {
    match?: string
    market?: string
    player_name?: string | null
    bet_raw?: string
    is_mymatch?: boolean
}

interface ExpertPick {
    id: string | number
    result?: string
    selections?: Selection[]
    expert_note?: string
    is_combine?: boolean
    has_mymatch?: boolean
    match_label?: string
    market?: string
    player_name?: string | null
    odds?: number | string | null
    confidence?: number
    date?: string
}

interface ExpertPickCardProps {
    pick: ExpertPick
    isAdmin?: boolean
    onDelete?: (id: string | number) => void
}

const RESULT_CFG: Record<string, { icon: React.ElementType; label: string; cls: string }> = {
    WIN: { icon: CheckCircle2, label: "WIN", cls: "text-emerald-400 bg-emerald-500/15 border-emerald-500/30" },
    LOSS: { icon: XCircle, label: "LOSS", cls: "text-red-400 bg-red-500/15 border-red-500/30" },
    VOID: { icon: Minus, label: "NUL", cls: "text-slate-400 bg-slate-500/15 border-slate-500/30" },
    PENDING: { icon: Clock, label: "En cours", cls: "text-amber-400 bg-amber-500/15 border-amber-500/30" },
}

export function ExpertPickCard({ pick, isAdmin = false, onDelete }: ExpertPickCardProps) {
    const [deleting, setDeleting] = useState(false)

    const r = pick.result || "PENDING"
    const { icon: StatusIcon, label: statusLabel, cls: statusCls } = RESULT_CFG[r] || RESULT_CFG.PENDING

    // Use enriched selections from API, fallback to parsing expert_note
    let selections: Selection[] = pick.selections || []
    if (selections.length === 0) {
        try {
            if (pick.expert_note && pick.expert_note.startsWith("[")) {
                const parsed = JSON.parse(pick.expert_note)
                if (Array.isArray(parsed)) {
                    selections = parsed.map((s: Record<string, string>) => ({
                        match: s.match || "",
                        market: s.bet || "",
                        player_name: null,
                        bet_raw: s.bet || "",
                        is_mymatch: false,
                    }))
                }
            }
        } catch { /* malformed expert_note JSON */ }
    }

    if (selections.length === 0) {
        selections = [{
            match: pick.match_label || "",
            market: pick.market || "",
            player_name: pick.player_name,
            bet_raw: pick.market || "",
            is_mymatch: false,
        }]
    }

    const matchCounts: Record<string, number> = {}
    selections.forEach(s => {
        const key = (s.match || "").toLowerCase().trim()
        if (key) matchCounts[key] = (matchCounts[key] || 0) + 1
    })

    async function handleDelete() {
        if (!confirm("Supprimer ce pick expert ?")) return
        setDeleting(true)
        const ok = await deleteExpertPick(pick.id)
        if (ok) onDelete?.(pick.id)
        else setDeleting(false)
    }

    const cardGlow =
        r === "WIN" ? "shadow-emerald-500/10 border-emerald-500/20" :
        r === "LOSS" ? "shadow-red-500/10 border-red-500/20" :
        "shadow-black/20 border-border/30"

    return (
        <div className={cn(
            "rounded-2xl overflow-hidden transition-all duration-300 shadow-lg",
            "bg-[#1a1f2e] border",
            cardGlow,
        )}>
            {/* Header bar */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-[#151928] border-b border-white/5">
                <div className="flex items-center gap-2">
                    <span className="text-sm">🎯</span>
                    <span className="text-xs font-bold text-white/90 uppercase tracking-wider">
                        Paris Expert
                    </span>
                    {pick.is_combine && (
                        <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/20">
                            Combine {selections.length}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className={cn(
                        "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border",
                        statusCls
                    )}>
                        <StatusIcon className="w-3 h-3" />
                        {statusLabel}
                    </span>
                    {isAdmin && (
                        <button
                            onClick={handleDelete}
                            disabled={deleting}
                            className="w-6 h-6 rounded-full flex items-center justify-center bg-red-500/10 hover:bg-red-500/25 transition-colors text-red-400 disabled:opacity-40"
                            title="Supprimer"
                        >
                            <Trash2 className="w-3 h-3" />
                        </button>
                    )}
                </div>
            </div>

            {/* Selections */}
            <div className="px-4 py-3">
                {selections.map((sel, i) => {
                    const matchKey = (sel.match || "").toLowerCase().trim()
                    const isMymatch = sel.is_mymatch || (matchCounts[matchKey] > 1)

                    const prevMatch = i > 0 ? (selections[i - 1].match || "").toLowerCase().trim() : ""
                    const isSameMatchAsPrev = matchKey && matchKey === prevMatch

                    return (
                        <div key={i}>
                            {i > 0 && !isSameMatchAsPrev && (
                                <div className="border-t border-white/5 my-2.5" />
                            )}
                            {i > 0 && isSameMatchAsPrev && (
                                <div className="flex items-center gap-2.5 pl-1 py-0.5">
                                    <div className="w-0.5 h-4 bg-white/10 ml-[5px]" />
                                </div>
                            )}

                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                    {!isSameMatchAsPrev && (
                                        <div className="mb-1">
                                            <p className="text-[12px] font-medium text-white/50 leading-tight">
                                                {sel.match || pick.match_label || ""}
                                            </p>
                                            {isMymatch && (
                                                <span className="inline-flex items-center gap-0.5 mt-0.5 text-xs font-black tracking-wider text-amber-400 uppercase">
                                                    <span className="w-1 h-1 rounded-full bg-amber-400 inline-block" />
                                                    MYMATCH
                                                </span>
                                            )}
                                        </div>
                                    )}
                                    <div className="flex items-center gap-1.5">
                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400/60 shrink-0 mt-0.5" />
                                        <p className="text-[13px] font-semibold text-white/90 leading-snug">
                                            {sel.player_name ? (
                                                <><span className="font-bold">{sel.player_name}</span> — {sel.market || sel.bet_raw}</>
                                            ) : (
                                                sel.market || sel.bet_raw || pick.market || ""
                                            )}
                                        </p>
                                    </div>
                                </div>

                                {selections.length === 1 && pick.odds && (
                                    <div className="shrink-0">
                                        <span className="inline-flex items-center justify-center min-w-[48px] px-2.5 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 text-sm font-bold font-mono">
                                            {formatOdds(pick.odds != null ? Number(pick.odds) : null)}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-[#151928] border-t border-white/5">
                <div className="flex items-center gap-3">
                    {pick.odds && selections.length > 1 && (
                        <div className="flex items-center gap-1.5">
                            <span className="text-xs text-white/40 uppercase font-medium">Cote totale</span>
                            <span className="px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 text-sm font-bold font-mono">
                                {formatOdds(pick.odds != null ? Number(pick.odds) : null)}
                            </span>
                        </div>
                    )}
                    {pick.confidence && (
                        <span className="text-amber-400 text-xs">
                            {"⭐".repeat(pick.confidence >= 8 ? 3 : pick.confidence >= 6 ? 2 : 1)}
                        </span>
                    )}
                </div>
                <span className="text-xs text-white/30 tabular-nums">
                    📅 {pick.date}
                </span>
            </div>

            {/* Expert note */}
            {pick.expert_note && !pick.expert_note.startsWith("[") && !pick.expert_note.startsWith("[odds=") && (
                <div className="px-4 pb-3 -mt-1">
                    <p className="text-xs text-amber-400/60 italic">&ldquo;{pick.expert_note}&rdquo;</p>
                </div>
            )}
        </div>
    )
}
