import { useState, useEffect } from "react"
import { toast } from "@/lib/toast"
import { X, AlertCircle, CheckCircle2, Info } from "lucide-react"
import { cn } from "@/lib/utils"

const icons = {
    error: AlertCircle,
    success: CheckCircle2,
    info: Info,
}

const styles = {
    error: "bg-red-950/90 border-red-500/30 text-red-200",
    success: "bg-emerald-950/90 border-emerald-500/30 text-emerald-200",
    info: "bg-blue-950/90 border-blue-500/30 text-blue-200",
}

export default function Toaster() {
    const [toasts, setToasts] = useState<ReturnType<typeof toast.getToasts>>([])

    useEffect(() => toast.subscribe(setToasts), [])

    if (toasts.length === 0) return null

    return (
        <div className="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-[200] flex flex-col gap-2 w-[90%] max-w-sm pointer-events-none">
            {toasts.map(t => {
                const Icon = icons[t.type]
                return (
                    <div
                        key={t.id}
                        role="alert"
                        aria-live="polite"
                        className={cn(
                            "flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl backdrop-blur-sm pointer-events-auto",
                            "animate-in slide-in-from-bottom-2 fade-in duration-200",
                            styles[t.type]
                        )}
                    >
                        <Icon className="w-4 h-4 shrink-0" />
                        <p className="text-xs font-medium flex-1">{t.message}</p>
                        <button
                            onClick={() => toast.dismiss(t.id)}
                            className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                    </div>
                )
            })}
        </div>
    )
}
