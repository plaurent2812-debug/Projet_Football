import { useState } from "react"
import { Star, ChevronDown, ChevronRight, Trophy, Shield } from "lucide-react"
import { cn } from "@/lib/utils"
import { useNavigate } from "react-router-dom"

const PINNED_LEAGUES = [
    { name: "Premier League", country: "Angleterre", id: "PL" },
    { name: "Ligue 1", country: "France", id: "L1" },
    { name: "La Liga", country: "Espagne", id: "LL" },
    { name: "Serie A", country: "Italie", id: "SA" },
    { name: "Bundesliga", country: "Allemagne", id: "BL" },
    { name: "Champions League", country: "Europe", id: "UCL" },
]

export function Sidebar({ className }) {
    const navigate = useNavigate()
    const [myTeamsOpen, setMyTeamsOpen] = useState(true)

    return (
        <aside className={cn("hidden md:block w-[240px] shrink-0 space-y-6", className)}>

            {/* Pinned Leagues */}
            <div className="space-y-1">
                <h3 className="px-3 text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                    Ligues Épinglées
                </h3>
                {PINNED_LEAGUES.map((league) => (
                    <button
                        key={league.id}
                        onClick={() => {
                            // Ideally navigate to a league page or filter dashboard
                            // For now, just a placeholder action or filter
                            console.log("Filter by", league.name)
                        }}
                        className="w-full flex items-center gap-3 px-3 py-1.5 text-sm font-medium text-foreground/80 hover:text-primary hover:bg-accent/50 rounded-lg transition-colors group"
                    >
                        <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                        <span className="truncate">{league.name}</span>
                    </button>
                ))}
            </div>

            {/* My Teams (Placeholder for now) */}
            <div className="space-y-1">
                <button
                    onClick={() => setMyTeamsOpen(!myTeamsOpen)}
                    className="w-full flex items-center justify-between px-3 text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors"
                >
                    <span>Mes Équipes</span>
                    {myTeamsOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </button>

                {myTeamsOpen && (
                    <div className="space-y-0.5">
                        {/* Placeholder Items */}
                        <div className="px-3 py-2 text-xs text-muted-foreground/60 italic">
                            Aucune équipe favorite
                        </div>
                        {/* Example Item */}
                        {/* 
                        <button className="w-full flex items-center gap-3 px-3 py-1.5 text-sm font-medium text-foreground/80 hover:text-primary hover:bg-accent/50 rounded-lg transition-colors">
                            <img src="..." className="w-4 h-4" />
                            <span>PSG</span>
                        </button> 
                        */}
                    </div>
                )}
            </div>

            {/* Countries List (Foldable) */}
            <div className="space-y-1 pt-4 border-t border-border/40">
                <h3 className="px-3 text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                    Pays
                </h3>
                {/* Just a few examples for visual feel */}
                {["Angleterre", "France", "Espagne", "Italie", "Allemagne", "Portugal", "Pays-Bas"].map(country => (
                    <button
                        key={country}
                        className="w-full flex items-center justify-between px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded-lg transition-colors group"
                    >
                        <span>{country}</span>
                        <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
                    </button>
                ))}
            </div>

        </aside>
    )
}
