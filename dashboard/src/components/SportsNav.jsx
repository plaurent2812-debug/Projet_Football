import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Trophy, Activity } from "lucide-react"

// Custom Hockey Stick Icon
function HockeyStick(props) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M16 3v13a4 4 0 0 1-4 4H4" />
        </svg>
    )
}

const SPORTS = [
    { id: "football", label: "Football", icon: <Trophy className="w-4 h-4" /> },
    { id: "nhl", label: "NHL", icon: <HockeyStick className="w-4 h-4" /> },
]

export function SportsNav({ activeSport = "football", onSportChange }) {
    return (
        <div className="w-full bg-[#374df5] text-white border-b border-white/10">
            <div className="max-w-[1400px] mx-auto">
                <ScrollArea className="w-full whitespace-nowrap">
                    <div className="flex w-max space-x-2 p-1 px-4">
                        {SPORTS.map((sport) => (
                            <Button
                                key={sport.id}
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    onSportChange?.(sport.id)
                                    // Simple navigation logic based on sport ID
                                    if (sport.id === 'nhl') {
                                        window.location.href = '/nhl' // Using href for full reload/clear clarity or navigate if available
                                        // But wait, SportsNav is inside Router in App.jsx? Yes.
                                        // Ideally we should use useNavigate, but SportsNav might need it passed or hook
                                    } else {
                                        window.location.href = '/matchs'
                                    }
                                }}
                                className={cn(
                                    "flex flex-col items-center justify-center gap-1 h-14 min-w-[70px] rounded-none border-b-2 transition-all hover:bg-white/10 hover:text-white",
                                    activeSport === sport.id
                                        ? "border-white bg-white/10 font-bold opacity-100"
                                        : "border-transparent opacity-70 hover:opacity-100"
                                )}
                            >
                                {sport.icon}
                                <span className="text-[10px] uppercase tracking-wide">{sport.label}</span>
                            </Button>
                        ))}
                    </div>
                    <ScrollBar orientation="horizontal" className="invisible" />
                </ScrollArea>
            </div>
        </div>
    )
}
