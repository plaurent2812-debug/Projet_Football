import { cn } from "@/lib/utils"

const SPORTS = [
    { id: "football", label: "Football", icon: "⚽" },
    { id: "basketball", label: "Basket", icon: "🏀", disabled: true },
    { id: "tennis", label: "Tennis", icon: "🎾", disabled: true },
    { id: "rugby", label: "Rugby", icon: "🏉", disabled: true },
]

export function SportsNav({ activeSport = "football", onSportChange }) {
    return (
        <nav className="flex items-center gap-1 overflow-x-auto pb-2 scrollbar-none border-b border-border/40 mb-6">
            {SPORTS.map((sport) => (
                <button
                    key={sport.id}
                    disabled={sport.disabled}
                    onClick={() => !sport.disabled && onSportChange?.(sport.id)}
                    className={cn(
                        "flex items-center gap-2 px-4 py-2.5 text-sm font-bold uppercase tracking-wide rounded-t-lg transition-all border-b-2",
                        activeSport === sport.id
                            ? "border-primary text-primary bg-primary/5"
                            : "border-transparent text-muted-foreground hover:text-foreground hover:bg-accent/30",
                        sport.disabled && "opacity-50 cursor-not-allowed hover:bg-transparent hover:text-muted-foreground"
                    )}
                >
                    <span className="text-lg">{sport.icon}</span>
                    {sport.label}
                </button>
            ))}
        </nav>
    )
}
