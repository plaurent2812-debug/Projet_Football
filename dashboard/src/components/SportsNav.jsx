import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Trophy, Activity, Flag } from "lucide-react"

const SPORTS = [
    { id: "football", label: "Football", icon: <Trophy className="w-4 h-4" /> },
    { id: "basketball", label: "Basket", icon: <Activity className="w-4 h-4" />, disabled: true },
    { id: "tennis", label: "Tennis", icon: <Activity className="w-4 h-4" />, disabled: true },
    { id: "rugby", label: "Rugby", icon: <Flag className="w-4 h-4" />, disabled: true },
    { id: "cricket", label: "Cricket", icon: <Activity className="w-4 h-4" />, disabled: true },
    { id: "volleyball", label: "Volley", icon: <Activity className="w-4 h-4" />, disabled: true },
    { id: "handball", label: "Handball", icon: <Activity className="w-4 h-4" />, disabled: true },
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
                                disabled={sport.disabled}
                                onClick={() => !sport.disabled && onSportChange?.(sport.id)}
                                className={cn(
                                    "flex flex-col items-center justify-center gap-1 h-14 min-w-[70px] rounded-none border-b-2 transition-all hover:bg-white/10 hover:text-white",
                                    activeSport === sport.id
                                        ? "border-white bg-white/10 font-bold opacity-100"
                                        : "border-transparent opacity-70 hover:opacity-100",
                                    sport.disabled && "opacity-40 cursor-not-allowed"
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
