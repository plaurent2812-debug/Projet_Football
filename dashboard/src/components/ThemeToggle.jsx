import { useState, useEffect } from "react"
import { Moon, Sun } from "lucide-react"

export default function ThemeToggle() {
    const [theme, setTheme] = useState(() => {
        // Check local storage or system preference
        if (typeof window !== "undefined" && localStorage.getItem("theme")) {
            return localStorage.getItem("theme")
        }
        return "dark" // Default to dark
    })

    useEffect(() => {
        const root = window.document.documentElement

        // Remove both classes to start fresh
        root.classList.remove("light", "dark")

        // Add the current theme class
        root.classList.add(theme)

        // Persist to local storage
        localStorage.setItem("theme", theme)
    }, [theme])

    const toggleTheme = () => {
        setTheme(prev => (prev === "dark" ? "light" : "dark"))
    }

    return (
        <button
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-secondary/50 hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            title={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
            aria-label="Changer le thème"
        >
            {theme === "dark" ? (
                <Sun className="w-4 h-4" />
            ) : (
                <Moon className="w-4 h-4" />
            )}
        </button>
    )
}
