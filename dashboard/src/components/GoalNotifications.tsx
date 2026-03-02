/**
 * GoalNotifications - polls live scores every 60s and shows toast
 * when a goal is scored in a starred/favorite-team match.
 * Toasts are clickable and navigate to the match page.
 */
import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWatchlist } from "@/lib/useWatchlist"
import { fetchPredictions } from "@/lib/api"

const POLL_INTERVAL = 60_000  // 1 minute

function GoalToast({ toast, onDismiss }) {
    const navigate = useNavigate()
    const [exiting, setExiting] = useState(false)

    const dismiss = useCallback(() => {
        setExiting(true)
        setTimeout(() => onDismiss(toast.id), 300)
    }, [toast.id, onDismiss])

    // Auto-dismiss after 12s
    useEffect(() => {
        const t = setTimeout(dismiss, 12_000)
        return () => clearTimeout(t)
    }, [dismiss])

    return (
        <div
            className={cn(
                "flex items-start gap-3 bg-card border border-border/60 rounded-xl shadow-xl p-3.5 cursor-pointer",
                "transition-all duration-300 w-[300px] max-w-[90vw]",
                exiting ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
            )}
            onClick={() => {
                dismiss()
                navigate(`/football/match/${toast.matchId}`)
            }}
        >
            {/* Icon */}
            <div className="text-2xl shrink-0 mt-0.5">⚽</div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-primary">BUT !</p>
                <p className="text-sm font-semibold truncate">
                    {toast.homeTeam} <span className="text-emerald-500 font-black">{toast.homeGoals} – {toast.awayGoals}</span> {toast.awayTeam}
                </p>
                {toast.scorer && (
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                        ⚽ {toast.scorer} {toast.minute ? `(${toast.minute}')` : ""}
                    </p>
                )}
                <p className="text-[10px] text-primary/60 mt-1">Cliquer pour voir le match →</p>
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

export default function GoalNotifications() {
    const { starredMatches, favTeams } = useWatchlist()
    const [toasts, setToasts] = useState([])
    // Track scores per match to detect goals: { matchId: { home: N, away: N } }
    const prevScores = useRef({})
    const toastIdRef = useRef(0)

    const dismissToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }, [])

    const checkForGoals = useCallback(async () => {
        // Only run if there are starred matches or fav teams
        if (starredMatches.size === 0 && favTeams.size === 0) return

        try {
            const today = new Date().toISOString().slice(0, 10)
            const data = await fetchPredictions(today)
            const liveMatches = (data.matches || []).filter(m =>
                ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(m.status)
            )

            for (const match of liveMatches) {
                const isWatched = starredMatches.has(match.id) ||
                    favTeams.has(match.home_team) ||
                    favTeams.has(match.away_team)

                if (!isWatched) continue

                const hg = match.home_goals ?? 0
                const ag = match.away_goals ?? 0
                const prev = prevScores.current[match.id]

                if (prev) {
                    const homeGoal = hg > prev.home
                    const awayGoal = ag > prev.away

                    if (homeGoal || awayGoal) {
                        // Find scorer from events_json
                        const events = match.events_json || []
                        const latestGoal = [...events]
                            .reverse()
                            .find(e => e.player && e.type !== "Card")

                        const newToast = {
                            id: ++toastIdRef.current,
                            matchId: match.id,
                            homeTeam: match.home_team,
                            awayTeam: match.away_team,
                            homeGoals: hg,
                            awayGoals: ag,
                            scorer: latestGoal?.player || null,
                            minute: latestGoal?.time || null,
                        }
                        setToasts(prev => [newToast, ...prev].slice(0, 3)) // max 3 toasts
                    }
                }

                // Always update stored score
                prevScores.current[match.id] = { home: hg, away: ag }
            }
        } catch {
            // Silent fail — don't disrupt the UX
        }
    }, [starredMatches, favTeams])

    useEffect(() => {
        // Initial population of scores (no toasts on first load)
        const init = async () => {
            try {
                const today = new Date().toISOString().slice(0, 10)
                const data = await fetchPredictions(today)
                const liveMatches = (data.matches || []).filter(m =>
                    ["1H", "2H", "HT", "ET", "P", "LIVE"].includes(m.status)
                )
                for (const match of liveMatches) {
                    prevScores.current[match.id] = {
                        home: match.home_goals ?? 0,
                        away: match.away_goals ?? 0
                    }
                }
            } catch { }
        }
        init()

        const interval = setInterval(checkForGoals, POLL_INTERVAL)
        return () => clearInterval(interval)
    }, [checkForGoals])

    if (toasts.length === 0) return null

    return (
        <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 items-end">
            {toasts.map(toast => (
                <GoalToast key={toast.id} toast={toast} onDismiss={dismissToast} />
            ))}
        </div>
    )
}
