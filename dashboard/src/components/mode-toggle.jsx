import { Moon, Sun, Monitor } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "@/components/theme-provider"

export function ModeToggle() {
    const { theme, setTheme } = useTheme()

    const cycleTheme = () => {
        if (theme === "light") setTheme("dark")
        else if (theme === "dark") setTheme("system")
        else setTheme("light")
    }

    const getIcon = () => {
        if (theme === "light") return <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all" />
        if (theme === "dark") return <Moon className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all" />
        return <Monitor className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all" />
    }

    const getLabel = () => {
        if (theme === "light") return "Light"
        if (theme === "dark") return "Dark"
        return "Auto"
    }

    return (
        <Button variant="ghost" size="icon" onClick={cycleTheme} title={`Thème : ${getLabel()}`}>
            {getIcon()}
            <span className="sr-only">Changer le thème</span>
        </Button>
    )
}
