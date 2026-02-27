import { useState, useEffect } from "react"
import { useNavigate, Link } from "react-router-dom"
import { Star, Search, X, ChevronRight, Trophy, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { useWatchlist } from "@/lib/useWatchlist"
import { fetchPredictions } from "@/lib/api"
import { supabase } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function MiniMatchCard({ match, isStarred, onToggleStar, sport = "football" }) {
    const navigate = useNavigate()
    const isFinished = ["FT", "AET", "PEN", "Final", "FINAL", "OFF"].includes(match.status)
    const isLive = ["1H", "2H", "HT", "ET", "P", "LIVE", "1P", "2P", "3P", "OT", "SO"].includes(match.status)
    const pred = match.prediction
    const time = match.date ? new Date(match.date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : "--:--"
    const homeGoals = sport === "nhl" ? match.home_score : match.home_goals
    const awayGoals = sport === "nhl" ? match.away_score : match.away_goals

    return (
        <div
            className="flex items-center gap-3 py-2.5 px-3 hover:bg-accent/40 cursor-pointer border-b border-border/20 last:border-0 transition-colors group"
            onClick={() => navigate(sport === "nhl"
                ? `/nhl/match/${match.api_fixture_id || match.id}`
                : `/football/match/${match.id}`
            )}
        >
            {/* Status */}
            <div className="w-12 shrink-0 text-center">
                {isLive ? (
                    <Badge variant="destructive" className="text-[10px] px-1.5 h-5 animate-pulse">LIVE</Badge>
                ) : isFinished ? (
                    <Badge className="text-[10px] px-1.5 h-5 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-0">FT</Badge>
                ) : (
                    <span className="text-xs font-bold tabular-nums text-foreground/80">{time}</span>
                )}
            </div>

            {/* Teams */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium truncate">{match.home_team}</span>
                    {(isFinished || isLive) ? (
                        <span className={cn(
                            "text-sm font-black tabular-nums px-1.5 py-0.5 rounded shrink-0",
                            isLive ? "text-red-500 bg-red-500/10" : "text-foreground bg-muted/60"
                        )}>
                            {homeGoals ?? "—"} – {awayGoals ?? "—"}
                        </span>
                    ) : (
                        <span className="text-xs text-muted-foreground shrink-0">vs</span>
                    )}
                    <span className="text-sm font-medium truncate text-right">{match.away_team}</span>
                </div>
                {pred?.recommended_bet && !isFinished && (
                    <p className="text-[10px] text-primary/70 mt-0.5">💡 {pred.recommended_bet}</p>
                )}
            </div>

            {/* Star + chevron */}
            <button
                className="shrink-0 p-1 rounded-full hover:bg-amber-500/10 transition-colors"
                onClick={(e) => { e.stopPropagation(); onToggleStar(match.id) }}
            >
                <Star className={cn("w-4 h-4", isStarred ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30")} />
            </button>
            <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-muted-foreground/60 shrink-0" />
        </div>
    )
}

function SportSection({ title, emoji, starredList, favTeamMatches, loading, toggleMatch, isStarred, sport }) {
    const hasContent = starredList.length > 0 || favTeamMatches.length > 0
    return (
        <Card className="border-border/50">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <span>{emoji}</span>
                    {title}
                    {starredList.length > 0 && (
                        <Badge variant="outline" className="ml-auto text-[10px]">{starredList.length} étoilé{starredList.length > 1 ? "s" : ""}</Badge>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                {loading ? (
                    <div className="py-8 text-center">
                        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" />
                    </div>
                ) : !hasContent ? (
                    <div className="py-8 text-center text-muted-foreground px-4">
                        <Star className="w-7 h-7 mx-auto mb-2 opacity-20" />
                        <p className="text-sm">Aucun match {title.toLowerCase()} étoilé aujourd'hui</p>
                    </div>
                ) : (
                    <>
                        {starredList.length > 0 && (
                            <div>
                                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-3 pt-3 pb-1.5 flex items-center gap-1">
                                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" /> Matchs étoilés
                                </p>
                                {starredList.map(m => (
                                    <MiniMatchCard key={m.id} match={m} isStarred={true} onToggleStar={toggleMatch} sport={sport} />
                                ))}
                            </div>
                        )}
                        {favTeamMatches.length > 0 && (
                            <div>
                                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-3 pt-3 pb-1.5 flex items-center gap-1">
                                    <Zap className="w-3 h-3" /> Matchs de mes équipes favorites
                                </p>
                                {favTeamMatches.map(m => (
                                    <MiniMatchCard key={m.id} match={m} isStarred={isStarred(m.id)} onToggleStar={toggleMatch} sport={sport} />
                                ))}
                            </div>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    )
}

export default function WatchlistPage() {
    const { starredMatches, favTeams, toggleMatch, toggleTeam, isStarred } = useWatchlist()
    const [footMatches, setFootMatches] = useState([])
    const [nhlMatches, setNhlMatches] = useState([])
    const [teamSearch, setTeamSearch] = useState("")
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const today = new Date().toISOString().slice(0, 10)
        setLoading(true)

        // Fetch football + NHL in parallel
        Promise.all([
            fetchPredictions(today).then(r => r.matches || []).catch(() => []),
            (() => {
                const start = new Date(today); start.setHours(0, 0, 0, 0)
                const end = new Date(today); end.setHours(23, 59, 59, 999)
                return supabase.from('nhl_fixtures').select('*')
                    .gte('date', start.toISOString())
                    .lte('date', end.toISOString())
                    .order('date', { ascending: true })
                    .then(({ data }) => data || [])
                    .catch(() => [])
            })()
        ]).then(([foot, nhl]) => {
            setFootMatches(foot)
            setNhlMatches(nhl)
        }).finally(() => setLoading(false))
    }, [])

    // Football splits
    const starredFoot = footMatches.filter(m => isStarred(m.id))
    const favFoot = footMatches.filter(m => !isStarred(m.id) && (favTeams.has(m.home_team) || favTeams.has(m.away_team)))

    // NHL splits
    const starredNHL = nhlMatches.filter(m => isStarred(m.id))
    const favNHL = nhlMatches.filter(m => !isStarred(m.id) && (favTeams.has(m.home_team) || favTeams.has(m.away_team)))

    // Autocomplete — all teams from both sports
    const allTeams = [...new Set([
        ...footMatches.flatMap(m => [m.home_team, m.away_team]),
        ...nhlMatches.flatMap(m => [m.home_team, m.away_team]),
    ])].filter(t => t && t.toLowerCase().includes(teamSearch.toLowerCase()) && !favTeams.has(t)).slice(0, 8)

    return (
        <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-xl font-black flex items-center gap-2">
                    <Star className="w-5 h-5 fill-amber-400 text-amber-400" />
                    Mes Favoris
                </h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                    Matchs étoilés et équipes favorites du jour
                </p>
            </div>

            {/* Football section */}
            <SportSection
                title="Football"
                emoji="⚽"
                starredList={starredFoot}
                favTeamMatches={favFoot}
                loading={loading}
                toggleMatch={toggleMatch}
                isStarred={isStarred}
                sport="football"
            />

            {/* NHL section */}
            <SportSection
                title="NHL"
                emoji="🏒"
                starredList={starredNHL}
                favTeamMatches={favNHL}
                loading={loading}
                toggleMatch={toggleMatch}
                isStarred={isStarred}
                sport="nhl"
            />

            {/* Teams favorites */}
            <Card className="border-border/50">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <Trophy className="w-4 h-4 text-primary" />
                        Équipes favorites
                        {favTeams.size > 0 && (
                            <Badge variant="outline" className="ml-auto text-[10px]">{favTeams.size}</Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Chips */}
                    {favTeams.size > 0 && (
                        <div className="flex flex-wrap gap-2">
                            {[...favTeams].map(team => (
                                <span key={team} className="flex items-center gap-1.5 text-xs font-semibold bg-primary/10 text-primary px-2.5 py-1 rounded-full">
                                    {team}
                                    <button onClick={() => toggleTeam(team)} className="hover:text-red-500 transition-colors">
                                        <X className="w-3 h-3" />
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Search */}
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                        <input
                            className="w-full text-sm bg-muted/40 border border-border/50 rounded-lg pl-8 pr-3 py-2 outline-none focus:ring-1 focus:ring-primary/30 placeholder:text-muted-foreground"
                            placeholder="Rechercher une équipe (foot ou NHL)..."
                            value={teamSearch}
                            onChange={e => setTeamSearch(e.target.value)}
                        />
                    </div>
                    {teamSearch && allTeams.length > 0 && (
                        <div className="border border-border/50 rounded-lg overflow-hidden">
                            {allTeams.map(team => (
                                <button key={team} className="w-full text-left text-sm px-3 py-2 hover:bg-accent/60 border-b border-border/20 last:border-0 transition-colors"
                                    onClick={() => { toggleTeam(team); setTeamSearch("") }}>
                                    + {team}
                                </button>
                            ))}
                        </div>
                    )}
                    {teamSearch && allTeams.length === 0 && (
                        <p className="text-xs text-muted-foreground text-center py-2">Aucune équipe trouvée</p>
                    )}
                    {favTeams.size === 0 && !teamSearch && (
                        <p className="text-xs text-muted-foreground text-center py-2">Recherche une équipe pour l'ajouter à tes favoris</p>
                    )}
                </CardContent>
            </Card>

            {/* CTAs */}
            <div className="flex justify-center gap-3">
                <Button variant="outline" size="sm" asChild>
                    <Link to="/football">⚽ Matchs Football</Link>
                </Button>
                <Button variant="outline" size="sm" asChild>
                    <Link to="/nhl">🏒 Matchs NHL</Link>
                </Button>
            </div>
        </div>
    )
}
