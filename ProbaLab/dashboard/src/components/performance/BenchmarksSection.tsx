import { ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { InfoTooltip } from "./ui"
import { formatWilson } from "./utils"

interface BenchmarkEntry {
    accuracy: number
    total: number
    note?: string
}

interface BenchmarksSectionProps {
    benchmarks: {
        always_home: BenchmarkEntry
        bookmaker_implied: BenchmarkEntry
        model: BenchmarkEntry
    }
    modelAccuracy: number
}

export function BenchmarksSection({ benchmarks, modelAccuracy }: BenchmarksSectionProps) {
    const items = [
        {
            key: "always_home",
            label: "Toujours Domicile",
            description: "Strategie naive : predire victoire domicile systematiquement",
            accuracy: benchmarks.always_home.accuracy,
            total: benchmarks.always_home.total,
            isModel: false,
        },
        {
            key: "bookmaker",
            label: "Odds Bookmaker",
            description: benchmarks.bookmaker_implied.note ?? "Prediction implicite des cotes bookmaker",
            accuracy: benchmarks.bookmaker_implied.accuracy,
            total: benchmarks.bookmaker_implied.total,
            isModel: false,
        },
        {
            key: "model",
            label: "Notre Modele",
            description: "XGBoost ensemble + Dixon-Coles + IA Gemini",
            accuracy: modelAccuracy,
            total: benchmarks.model.total,
            isModel: true,
        },
    ]

    const maxAccuracy = Math.max(...items.map(i => i.accuracy), 1)

    return (
        <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                    <ShieldCheck className="w-4 h-4 text-primary" />
                    Benchmarks 1X2
                    <InfoTooltip content={
                        <>
                            <strong className="text-foreground block mb-1">Comparaison de references</strong>
                            Compare notre modele a des strategies simples pour mesurer la valeur ajoutee reelle.
                            <br /><br />
                            L'intervalle de confiance Wilson a 95% est affiche entre parentheses.
                        </>
                    } />
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                {items.map(({ key, label, description, accuracy, total, isModel }) => {
                    const barWidth = maxAccuracy > 0 ? (accuracy / maxAccuracy) * 100 : 0
                    const wilsonLabel = total > 0 ? formatWilson(accuracy, total) : `${accuracy}%`

                    return (
                        <div key={key} className={cn(
                            "p-3.5 rounded-xl border transition-colors",
                            isModel
                                ? "bg-primary/5 border-primary/30 ring-1 ring-primary/20"
                                : "bg-card/30 border-border/30"
                        )}>
                            <div className="flex items-center justify-between mb-2">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className={cn("text-sm font-semibold", isModel ? "text-primary" : "text-muted-foreground")}>
                                            {label}
                                        </span>
                                        {isModel && (
                                            <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-semibold">
                                                Modele
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground/70 mt-0.5">{description}</p>
                                </div>
                                <div className="text-right shrink-0 ml-3">
                                    <p className={cn("text-xl font-black tabular-nums", isModel ? "text-primary" : "text-foreground")}>
                                        {accuracy}%
                                    </p>
                                    <p className="text-xs text-muted-foreground tabular-nums">{total} matchs</p>
                                </div>
                            </div>
                            <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                                <div
                                    className={cn(
                                        "h-full rounded-full transition-all duration-700",
                                        isModel ? "bg-primary" : "bg-muted-foreground/30"
                                    )}
                                    style={{ width: `${barWidth}%` }}
                                />
                            </div>
                            <p className="text-xs text-muted-foreground/60 mt-1 tabular-nums">{wilsonLabel}</p>
                        </div>
                    )
                })}
            </CardContent>
        </Card>
    )
}
