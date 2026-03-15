/**
 * ExpertPickNotifications — polls /api/expert-picks/latest every 30s
 * and shows a toast when a new expert pick is published from Telegram.
 */
import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { X, Target } from "lucide-react"
import { cn } from "@/lib/utils"

const API_BASE = import.meta.env.VITE_API_URL || ""
const POLL_INTERVAL = 30_000 // 30 seconds

function ExpertPickToast({ toast, onDismiss }) {
    const navigate = useNavigate()
    const [exiting, setExiting] = useState(false)

    const dismiss = useCallback(() => {
        setExiting(true)
        setTimeout(() => onDismiss(toast.id), 300)
    }, [toast.id, onDismiss])

    // Auto-dismiss after 10s
    useEffect(() => {
        const t = setTimeout(dismiss, 10_000)
        return () => clearTimeout(t)
    }, [dismiss])

    return (
        <div
            className={cn(
                "flex items-start gap-3 bg-card border border-amber-500/30 rounded-xl shadow-xl p-3.5 cursor-pointer",
                "transition-all duration-300 w-[320px] max-w-[90vw]",
                exiting ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
            )}
            onClick={() => {
                dismiss()
                navigate("/paris-du-soir")
            }}
        >
            {/* Icon */}
            <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center shrink-0 mt-0.5">
                <Target className="w-4 h-4 text-amber-500" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-amber-500">🎯 Nouveau Prono !</p>
                <p className="text-sm font-semibold truncate mt-0.5">
                    {toast.market}
                </p>
                {toast.matchLabel && (
                    <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                        {toast.matchLabel}
                    </p>
                )}
                {toast.odds && (
                    <p className="text-[11px] font-bold text-emerald-500 mt-0.5">
                        Cote : {toast.odds}
                    </p>
                )}
                <p className="text-[10px] text-amber-500/60 mt-1">Cliquer pour voir →</p>
            </div>

            {/* Close */}
            <button
                className="shrink-0 p-0.5 rounded hover:bg-accent transition-colors"
                onClick={(e) => { e.stopPropagation(); dismiss() }}
            >
                <X className="w-3.5 h-3.5 text-muted-foreground" />
            </button>
        </div>
    )
}

export default function ExpertPickNotifications() {
    const [toasts, setToasts] = useState([])
    const lastSeenId = useRef(null)
    const initialized = useRef(false)
    const toastIdRef = useRef(0)

    const dismissToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }, [])

    const checkForNewPick = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/expert-picks/latest`)
            if (!res.ok) return
            const data = await res.json()
            const pick = data?.pick
            if (!pick) return

            // First load — just store the ID, don't show toast
            if (!initialized.current) {
                lastSeenId.current = pick.id
                initialized.current = true
                return
            }

            // New pick detected
            if (pick.id !== lastSeenId.current) {
                lastSeenId.current = pick.id

                const newToast = {
                    id: ++toastIdRef.current,
                    market: pick.market || "Nouveau pari",
                    matchLabel: pick.match_label,
                    odds: pick.odds,
                    sport: pick.sport,
                }
                setToasts(prev => [newToast, ...prev].slice(0, 2)) // max 2 toasts
            }
        } catch {
            // Silent fail
        }
    }, [])

    useEffect(() => {
        // Initial check (populate lastSeenId without showing toast)
        checkForNewPick()
        const interval = setInterval(checkForNewPick, POLL_INTERVAL)
        return () => clearInterval(interval)
    }, [checkForNewPick])

    if (toasts.length === 0) return null

    return (
        <div className="fixed bottom-4 left-4 z-[100] flex flex-col gap-2 items-start">
            {toasts.map(toast => (
                <ExpertPickToast key={toast.id} toast={toast} onDismiss={dismissToast} />
            ))}
        </div>
    )
}
