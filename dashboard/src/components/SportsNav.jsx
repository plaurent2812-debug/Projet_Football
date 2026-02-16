import { cn } from "@/lib/utils"

const SPORTS = [
    { id: "football", label: "Football", icon: "⚽" },
    { id: "basketball", label: "Basket", icon: "🏀", disabled: true },
    { id: "tennis", label: "Tennis", icon: "🎾", disabled: true },
    { id: "rugby", label: "Rugby", icon: "🏉", disabled: true },
]

export function SportsNav({ activeSport = "football", onSportChange }) {
    return (
        <nav className="w-full bg-[#374df5] text-white overflow-x-auto scrollbar-none shadow-md">
            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 flex items-center gap-1">
                {SPORTS.map((sport) => (
                    <button
                        key={sport.id}
                        disabled={sport.disabled}
                        onClick={() => !sport.disabled && onSportChange?.(sport.id)}
                        className={cn(
                            "flex flex-col items-center justify-center gap-0.5 px-3 py-2 text-[10px] font-bold uppercase tracking-wide transition-all h-14 min-w-[64px]",
                            activeSport === sport.id
                                ? "bg-white/10 opacity-100 border-b-2 border-white"
                                : "opacity-70 hover:opacity-100 hover:bg-white/5 border-b-2 border-transparent",
                            sport.disabled && "opacity-40 cursor-not-allowed hover:bg-transparent"
                        )}
                    >
                        <span className="text-lg leading-none mb-0.5">{sport.icon}</span>
                        <span className="leading-none">{sport.label}</span>
                    </button>
                ))}
            </div>
        </nav>
    )
}
