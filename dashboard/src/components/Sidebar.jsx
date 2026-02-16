import { useState } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight } from "lucide-react"

const PINNED_LEAGUES = [
    { id: 39, name: "Premier League", country: "Angleterre", icon: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    { id: 61, name: "Ligue 1", country: "France", icon: "🇫🇷" },
    { id: 140, name: "La Liga", country: "Espagne", icon: "🇪🇸" },
    { id: 135, name: "Serie A", country: "Italie", icon: "🇮🇹" },
    { id: 78, name: "Bundesliga", country: "Allemagne", icon: "🇩🇪" },
    { id: 2, name: "Champions League", country: "Europe", icon: "🇪🇺" },
]

export function Sidebar({ className, selectedLeague, onLeagueSelect }) {
    const [myTeamsOpen, setMyTeamsOpen] = useState(true)
    const navigate = useNavigate()
    const location = useLocation()

    const handleLeagueClick = (leagueId) => {
        const newValue = selectedLeague === leagueId ? null : leagueId
        onLeagueSelect?.(newValue)
        if (location.pathname !== "/matchs") {
            navigate("/matchs")
        }
    }

    return (
        <aside className={cn("hidden md:flex flex-col w-[240px] shrink-0 border-r bg-background", className)}>
            <ScrollArea className="h-[calc(100vh-8rem)]">
                <div className="p-4 space-y-6">

                    {/* Pinned Leagues */}
                    <div>
                        <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3 px-2">
                            Ligues Épinglées
                        </h3>
                        <div className="space-y-1">
                            {PINNED_LEAGUES.map((league) => (
                                <Button
                                    key={league.id}
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleLeagueClick(league.id)}
                                    className={cn(
                                        "w-full justify-start gap-3 h-9 font-normal text-sm transition-all",
                                        selectedLeague === league.id
                                            ? "bg-primary/10 text-primary font-semibold ring-1 ring-primary/20"
                                            : "hover:bg-muted"
                                    )}
                                >
                                    <span className="text-base leading-none">{league.icon}</span>
                                    <span className="truncate">{league.name}</span>
                                </Button>
                            ))}
                        </div>
                    </div>

                    <Separator />

                    {/* My Teams */}
                    <div>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-between hover:bg-transparent px-2 mb-1 h-auto py-1"
                            onClick={() => setMyTeamsOpen(!myTeamsOpen)}
                        >
                            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                Mes Équipes
                            </h3>
                            {myTeamsOpen ? <ChevronDown className="w-3 h-3 text-muted-foreground" /> : <ChevronRight className="w-3 h-3 text-muted-foreground" />}
                        </Button>

                        {myTeamsOpen && (
                            <div className="px-2 py-4 text-center border-2 border-dashed border-muted rounded-lg mx-2 mt-2">
                                <p className="text-[10px] text-muted-foreground italic">Aucune équipe favorite</p>
                            </div>
                        )}
                    </div>
                </div>
            </ScrollArea>
        </aside>
    )
}
