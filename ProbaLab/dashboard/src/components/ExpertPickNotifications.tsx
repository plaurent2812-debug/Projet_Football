/**
 * ExpertPickNotifications — polls /api/expert-picks/latest every 30s
 * and shows a toast when a new expert pick is published from Telegram.
 * Also provides a push notification subscribe button.
 */
import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { X, Target, Bell, BellOff } from "lucide-react"
import { cn } from "@/lib/utils"
import { isPushSupported, getPushPermission, subscribeToPush, isSubscribedToPush } from "@/lib/pushSubscription"
import { API_ROOT } from "@/lib/api"
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
                "flex items-start gap-3 bg-[#1a1f2e] border border-amber-500/20 rounded-xl shadow-xl p-3.5 cursor-pointer",
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
                <p className="text-sm font-semibold text-white/90 truncate mt-0.5">
                    {toast.market}
                </p>
                {toast.matchLabel && (
                    <p className="text-xs text-white/40 truncate mt-0.5">
                        {toast.matchLabel}
                    </p>
                )}
                {toast.odds && (
                    <p className="text-xs font-bold text-emerald-400 mt-0.5">
                        Cote : {toast.odds}
                    </p>
                )}
                <p className="text-xs text-amber-500/60 mt-1">Cliquer pour voir →</p>
            </div>

            {/* Close */}
            <button
                className="shrink-0 p-0.5 rounded hover:bg-white/5 transition-colors"
                onClick={(e) => { e.stopPropagation(); dismiss() }}
            >
                <X className="w-3.5 h-3.5 text-white/40" />
            </button>
        </div>
    )
}

function PushToggle() {
    const [supported, setSupported] = useState(false)
    const [subscribed, setSubscribed] = useState(false)
    const [loading, setLoading] = useState(false)
    const [showBanner, setShowBanner] = useState(false)

    useEffect(() => {
        const check = async () => {
            const sup = isPushSupported()
            setSupported(sup)
            if (sup) {
                const sub = await isSubscribedToPush()
                setSubscribed(sub)
                // Show banner only if not subscribed and never dismissed
                if (!sub && !sessionStorage.getItem("push_banner_dismissed")) {
                    setShowBanner(true)
                }
            }
        }
        check()
    }, [])

    async function handleSubscribe() {
        setLoading(true)
        try {
            const ok = await subscribeToPush()
            setSubscribed(ok)
            if (ok) setShowBanner(false)
        } finally {
            setLoading(false)
        }
    }

    function handleDismiss() {
        setShowBanner(false)
        sessionStorage.setItem("push_banner_dismissed", "1")
    }

    if (!supported || subscribed || !showBanner) return null

    return (
        <div className="fixed bottom-4 left-4 z-[99] w-[320px] max-w-[90vw]">
            <div className="bg-[#1a1f2e] border border-primary/20 rounded-xl shadow-xl p-3.5">
                <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center shrink-0">
                        <Bell className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold text-white/90">Notifications push 🔔</p>
                        <p className="text-xs text-white/50 mt-0.5">
                            Reçois une alerte dès qu'un nouveau prono expert est publié !
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                            <button
                                onClick={handleSubscribe}
                                disabled={loading}
                                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-primary text-white hover:bg-primary/90 transition-colors disabled:opacity-50"
                            >
                                {loading ? "..." : "Activer"}
                            </button>
                            <button
                                onClick={handleDismiss}
                                className="px-3 py-1.5 rounded-lg text-xs font-medium text-white/40 hover:text-white/60 hover:bg-white/5 transition-colors"
                            >
                                Plus tard
                            </button>
                        </div>
                    </div>
                    <button
                        onClick={handleDismiss}
                        className="shrink-0 p-0.5 rounded hover:bg-white/5 transition-colors"
                    >
                        <X className="w-3.5 h-3.5 text-white/30" />
                    </button>
                </div>
            </div>
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
            const res = await fetch(`${API_ROOT}/api/expert-picks/latest`)
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
        } catch (err) {
            console.warn("Expert picks polling failed:", err)
        }
    }, [])

    useEffect(() => {
        // Initial check (populate lastSeenId without showing toast)
        checkForNewPick()
        const interval = setInterval(checkForNewPick, POLL_INTERVAL)
        return () => clearInterval(interval)
    }, [checkForNewPick])

    return (
        <>
            {/* Push notification banner */}
            <PushToggle />

            {/* In-app toasts */}
            {toasts.length > 0 && (
                <div className="fixed bottom-4 left-4 z-[100] flex flex-col gap-2 items-start">
                    {toasts.map(toast => (
                        <ExpertPickToast key={toast.id} toast={toast} onDismiss={dismissToast} />
                    ))}
                </div>
            )}
        </>
    )
}
