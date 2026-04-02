import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { Star, Search, X, ChevronRight, Trophy } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWatchlist } from "@/lib/useWatchlist"
import { fetchPredictions } from "@/lib/api"
import { supabase } from "@/lib/auth"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Flame } from "lucide-react"
import { toast } from "@/lib/toast"

/* ── Mini Match Row (FlashScore-style) ─────────────────────── */
function MiniMatchRow({ match, isStarred, onToggleStar, sport = "football" }) {
    const navigate = useNavigate()
    const isFinished = ["FT", "AET", "PEN", "Final", "FINAL", "OFF"].includes(match.status)
    const isLive = ["1H", "2H", "HT", "ET", "P", "LIVE", "1P", "2P", "3P", "OT", "SO"].includes(match.status)
    const pred = match.prediction
    const time = match.date ? new Date(match.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : "--:--"
    const homeGoals = sport === "nhl" ? match.home_score : match.home_goals
    const awayGoals = sport === "nhl" ? match.away_score : match.away_goals
    const homeWon = isFinished && homeGoals > awayGoals
    const awayWon = isFinished && awayGoals > homeGoals
    const hasScore = isFinished || isLive

    // Day label
    const matchDate = match.date ? new Date(match.date) : null
    const todayStr = new Date().toISOString().slice(0, 10)
    const tomorrowStr = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
    const matchDayStr = matchDate?.toISOString().slice(0, 10)
    const dayLabel = matchDayStr === todayStr ? "Auj."
        : matchDayStr === tomorrowStr ? "Dem."
            : matchDate ? matchDate.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric' })
                : null

    return (
        <div
            className="fs-match-row"
            onClick={() => navigate(sport === "nhl"
                ? `/nhl/match/${match.api_fixture_id || match.id}`
                : `/football/match/${match.id}`
            )}
        >
            {/* Time */}
            <div className="fs-match-time">
                {isLive ? (
                    <span className="fs-live-badge">LIVE</span>
                ) : isFinished ? (
                    <span className="text-[10px] font-semibold text-emerald-500">FT</span>
                ) : (
                    <div className="flex flex-col items-center">
                        <span>{time}</span>
                        {dayLabel && <span className="text-[8px] text-muted-foreground/60">{dayLabel}</span>}
                    </div>
                )}
            </div>

            {/* Teams */}
            <div className="fs-match-teams">
                <span className={cn("fs-team-name text-right", homeWon && "winner")}>{match.home_team}</span>
                <div className={cn("fs-score-box", isLive && "live")}>
                    {hasScore ? (
                        <>
                            <span className={cn("score-val", homeWon && "winner")}>{homeGoals ?? "-"}</span>
                            <span className={cn("score-val", awayWon && "winner")}>{awayGoals ?? "-"}</span>
                        </>
                    ) : (
                        <>
                            <span className="score-val text-muted-foreground/40">-</span>
                            <span className="score-val text-muted-foreground/40">-</span>
                        </>
                    )}
                </div>
                <span className={cn("fs-team-name", awayWon && "winner")}>{match.away_team}</span>
            </div>

            {/* Prediction */}
            {pred?.recommended_bet && !isFinished && (
                <span className="fs-pred-chip bg-primary/10 text-primary hidden sm:inline-flex truncate max-w-[80px]">
                    {pred.recommended_bet}
                </span>
            )}

            {/* Star */}
            <button
                className="fs-star-btn"
                onClick={(e) => { e.stopPropagation(); onToggleStar(match.id) }}
            >
                <Star className={cn(
                    "w-3.5 h-3.5 transition-colors",
                    isStarred ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30 hover:text-amber-400"
                )} />
            </button>
        </div>
    )
}

/* ── Sport Section ─────────────────────────────────────────── */
function SportSection({ title, emoji, starredList, favTeamMatches, loading, toggleMatch, isStarred, sport }) {
    const hasContent = starredList.length > 0 || favTeamMatches.length > 0
    return (
        <div className="bg-card border-x border-b border-border/50">
            <div className="fs-league-header">
                <span className="text-sm">{emoji}</span>
                <div className="fs-league-name">{title}</div>
                {starredList.length > 0 && (
                    <span className="fs-league-count">{starredList.length}</span>
                )}
            </div>
            {loading ? (
                <div className="p-3 space-y-2">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full" />)}
                </div>
            ) : !hasContent ? (
                <div className="flex flex-col items-center justify-center py-12 text-center px-4">
                    <Star className="w-5 h-5 text-muted-foreground/30 mb-2" />
                    <p className="text-xs text-muted-foreground">
                        Aucun favori {title.toLowerCase()}. Cliquez sur l'étoile d'un match pour l'ajouter ici.
                    </p>
                </div>
            ) : (
                <>
                    {starredList.length > 0 && (
                        <div>
                            <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground px-3 pt-2 pb-1 flex items-center gap-1">
                                <Star className="w-2.5 h-2.5 fill-amber-400 text-amber-400" /> Étoilés
                            </p>
                            {starredList.map(m => (
                                <MiniMatchRow key={m.id} match={m} isStarred={true} onToggleStar={toggleMatch} sport={sport} />
                            ))}
                        </div>
                    )}
                    {favTeamMatches.length > 0 && (
                        <div>
                            <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground px-3 pt-2 pb-1 flex items-center gap-1">
                                <Trophy className="w-2.5 h-2.5" /> Équipes favorites
                            </p>
                            {favTeamMatches.map(m => (
                                <MiniMatchRow key={m.id} match={m} isStarred={isStarred(m.id)} onToggleStar={toggleMatch} sport={sport} />
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════
   Watchlist Page (FlashScore-style)
   ═══════════════════════════════════════════════════════════ */
export default function WatchlistPage() {
    const { starredMatches, favTeams, toggleMatch, toggleTeam, isStarred } = useWatchlist()
    const [footMatches, setFootMatches] = useState([])
    const [nhlMatches, setNhlMatches] = useState([])
    const [teamSearch, setTeamSearch] = useState("")
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        const days = Array.from({ length: 7 }, (_, i) => {
            const d = new Date(); d.setDate(d.getDate() + i)
            return d.toISOString().slice(0, 10)
        })

        const footPromise = Promise.all(
            days.map(day => fetchPredictions(day).then(r => r.matches || []).catch(() => {
                toast.error("Erreur de chargement des matchs football")
                return []
            }))
        ).then(results => results.flat())

        const start = new Date(); start.setHours(0, 0, 0, 0)
        const end = new Date(); end.setDate(end.getDate() + 7); end.setHours(23, 59, 59, 999)
        const nhlPromise = supabase.from('nhl_fixtures').select('*')
            .gte('date', start.toISOString())
            .lte('date', end.toISOString())
            .order('date', { ascending: true })
            .then(({ data }) => data || [])
            .catch(() => {
                toast.error("Erreur de chargement des matchs NHL")
                return []
            })

        Promise.all([footPromise, nhlPromise]).then(([foot, nhl]) => {
            foot.sort((a, b) => new Date(a.date) - new Date(b.date))
            setFootMatches(foot)
            setNhlMatches(nhl)
        }).finally(() => setLoading(false))
    }, [])

    const starredFoot = footMatches.filter(m => isStarred(m.id))
    const favFoot = footMatches.filter(m => !isStarred(m.id) && (favTeams.has(m.home_team) || favTeams.has(m.away_team)))
    const starredNHL = nhlMatches.filter(m => isStarred(m.id))
    const favNHL = nhlMatches.filter(m => !isStarred(m.id) && (favTeams.has(m.home_team) || favTeams.has(m.away_team)))

    const allTeams = [...new Set([
        ...footMatches.flatMap(m => [m.home_team, m.away_team]),
        ...nhlMatches.flatMap(m => [m.home_team, m.away_team]),
    ])].filter(t => t && t.toLowerCase().includes(teamSearch.toLowerCase()) && !favTeams.has(t)).slice(0, 8)

    return (
        <div className="animate-fade-in-up pb-4">
            {/* Header */}
            <div className="fs-summary-bar">
                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                <span className="font-bold">Mes Favoris</span>
                <span className="text-[10px] text-muted-foreground ml-1">7 prochains jours</span>
            </div>

            {/* Football */}
            <SportSection title="Football" emoji="⚽"
                starredList={starredFoot} favTeamMatches={favFoot}
                loading={loading} toggleMatch={toggleMatch} isStarred={isStarred} sport="football" />

            {/* NHL */}
            <SportSection title="NHL" emoji="🏒"
                starredList={starredNHL} favTeamMatches={favNHL}
                loading={loading} toggleMatch={toggleMatch} isStarred={isStarred} sport="nhl" />

            {/* Team favorites management */}
            <div className="bg-card border-x border-b border-border/50 rounded-b px-3 py-3 space-y-3">
                <div className="flex items-center gap-2">
                    <Trophy className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-bold">Équipes favorites</span>
                    {favTeams.size > 0 && (
                        <Badge variant="outline" className="ml-auto text-[10px]">{favTeams.size}</Badge>
                    )}
                </div>

                {/* Chips */}
                {favTeams.size > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                        {[...favTeams].map(team => (
                            <span key={team} className="flex items-center gap-1 text-[10px] font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded">
                                {team}
                                <button onClick={() => toggleTeam(team)} className="hover:text-red-500 transition-colors">
                                    <X className="w-2.5 h-2.5" />
                                </button>
                            </span>
                        ))}
                    </div>
                )}

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                    <input
                        className="w-full text-xs bg-muted/40 border border-border/50 rounded pl-7 pr-3 py-1.5 outline-none focus:ring-1 focus:ring-primary/30 placeholder:text-muted-foreground"
                        placeholder="Rechercher une équipe..."
                        value={teamSearch}
                        onChange={e => setTeamSearch(e.target.value)}
                    />
                </div>

                {teamSearch && allTeams.length > 0 && (
                    <div className="border border-border/50 rounded overflow-hidden">
                        {allTeams.map(team => (
                            <button key={team}
                                className="w-full text-left text-xs px-3 py-1.5 hover:bg-accent/60 border-b border-border/20 last:border-0 transition-colors"
                                onClick={() => { toggleTeam(team); setTeamSearch(""); toast.success(`${team} ajoutée aux favoris`) }}
                            >
                                + {team}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
