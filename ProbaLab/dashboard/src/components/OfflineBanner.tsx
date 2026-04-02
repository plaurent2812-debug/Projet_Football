import { useState, useEffect } from "react"
import { WifiOff } from "lucide-react"

export default function OfflineBanner() {
    const [offline, setOffline] = useState(!navigator.onLine)

    useEffect(() => {
        const goOffline = () => setOffline(true)
        const goOnline = () => setOffline(false)
        window.addEventListener("offline", goOffline)
        window.addEventListener("online", goOnline)
        return () => {
            window.removeEventListener("offline", goOffline)
            window.removeEventListener("online", goOnline)
        }
    }, [])

    if (!offline) return null

    return (
        <div role="alert" aria-live="assertive" className="fixed top-11 left-0 right-0 z-[60] bg-amber-950/95 border-b border-amber-500/30 px-4 py-2 flex items-center justify-center gap-2 text-amber-200 text-xs font-medium backdrop-blur-sm animate-in slide-in-from-top duration-200">
            <WifiOff className="w-3.5 h-3.5" />
            Connexion perdue — les données affichées peuvent être obsolètes
        </div>
    )
}
