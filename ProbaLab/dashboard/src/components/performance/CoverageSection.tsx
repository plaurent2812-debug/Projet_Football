import { Eye, XCircle, CheckCircle2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { InfoTooltip } from "./ui"

interface CoverageSectionProps {
    totalMatches: number
    totalFinished: number
    skippedNullProbas: number
    skippedTies: number
    coverage: Record<string, number>
}

const MARKET_COVERAGE = [
    { label: "1X2", key: "total_1x2_countable", color: "bg-indigo-500" },
    { label: "BTTS", key: "total_btts", color: "bg-emerald-500" },
    { label: "O/U 0.5", key: "total_over_05", color: "bg-blue-400" },
    { label: "O/U 1.5", key: "total_over_15", color: "bg-blue-500" },
    { label: "O/U 2.5", key: "total_over_25", color: "bg-amber-400" },
    { label: "O/U 3.5", key: "total_over_35", color: "bg-orange-400" },
]

export function CoverageSection({
    totalMatches,
    totalFinished,
    skippedNullProbas,
    skippedTies,
    coverage,
}: CoverageSectionProps) {
    const coveragePct = totalFinished > 0
        ? Math.round((totalMatches / totalFinished) * 100)
        : 0

    return (
        <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                    <Eye className="w-4 h-4 text-primary" />
                    Couverture des predictions
                    <InfoTooltip content={
                        <>
                            <strong className="text-foreground block mb-1">Couverture</strong>
                            Proportion de matchs termines pour lesquels une prediction valide existe.
                            Les matchs sans probabilites (null) ou avec egalite de probas sont exclus de l'accuracy.
                        </>
                    } />
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
                {/* Global coverage */}
                <div className="flex items-center gap-4">
                    <div className="flex-1">
                        <div className="flex justify-between text-xs font-medium mb-1.5">
                            <span>Matchs avec prediction valide</span>
                            <span className="tabular-nums text-foreground font-bold">{totalMatches}/{totalFinished} ({coveragePct}%)</span>
                        </div>
                        <div className="h-2 rounded-full bg-secondary overflow-hidden">
                            <div
                                className="h-full rounded-full bg-primary transition-all duration-700"
                                style={{ width: `${coveragePct}%` }}
                            />
                        </div>
                    </div>
                </div>

                {/* Skip reasons */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2.5 p-3 rounded-lg bg-secondary/30 border border-border/30">
                        <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                        <div>
                            <p className="text-xs text-muted-foreground">Probas manquantes</p>
                            <p className="text-sm font-bold tabular-nums">{skippedNullProbas}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2.5 p-3 rounded-lg bg-secondary/30 border border-border/30">
                        <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0" />
                        <div>
                            <p className="text-xs text-muted-foreground">Egalites de probas</p>
                            <p className="text-sm font-bold tabular-nums">{skippedTies}</p>
                        </div>
                    </div>
                </div>

                {/* Per-market coverage bars */}
                <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Par marche</p>
                    <div className="space-y-2">
                        {MARKET_COVERAGE.map(({ label, key, color }) => {
                            const count = coverage[key] ?? 0
                            const pct = totalFinished > 0 ? Math.round((count / totalFinished) * 100) : 0
                            return (
                                <div key={key} className="flex items-center gap-3">
                                    <span className="text-xs text-muted-foreground w-14 shrink-0">{label}</span>
                                    <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
                                        <div
                                            className={cn("h-full rounded-full transition-all duration-700", color)}
                                            style={{ width: `${pct}%` }}
                                        />
                                    </div>
                                    <span className="text-xs tabular-nums text-muted-foreground w-16 text-right shrink-0">
                                        {count} ({pct}%)
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
