import { Calendar } from "lucide-react"
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Cell
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartTooltip } from "./ui"

interface DailyDataPoint {
    date?: string
    date_short?: string
    total: number
    correct: number
    accuracy?: number
}

interface DailyChartProps {
    chartData: DailyDataPoint[]
}

export function DailyChart({ chartData }: DailyChartProps) {
    if (chartData.length === 0) return null

    return (
        <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                    <Calendar className="w-4 h-4 text-primary" />
                    Resultats jour par jour
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} barGap={2}>
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="oklch(0.25 0.008 260)"
                                vertical={false}
                            />
                            <XAxis
                                dataKey="date_short"
                                tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <YAxis
                                tick={{ fontSize: 11, fill: "oklch(0.6 0.01 260)" }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip content={<ChartTooltip />} cursor={{ fill: "oklch(0.25 0.008 260 / 0.3)" }} />
                            <Bar
                                dataKey="total"
                                name="Analyses"
                                radius={[4, 4, 0, 0]}
                                maxBarSize={32}
                            >
                                {chartData.map((_: DailyDataPoint, i: number) => (
                                    <Cell
                                        key={i}
                                        fill="oklch(0.35 0.01 260)"
                                    />
                                ))}
                            </Bar>
                            <Bar
                                dataKey="correct"
                                name="Corrects"
                                radius={[4, 4, 0, 0]}
                                maxBarSize={32}
                            >
                                {chartData.map((entry: DailyDataPoint, i: number) => {
                                    const acc = entry.total > 0 ? entry.correct / entry.total : 0
                                    return (
                                        <Cell
                                            key={i}
                                            fill={acc >= 0.6
                                                ? "oklch(0.7 0.18 155)"
                                                : acc >= 0.4
                                                    ? "oklch(0.75 0.16 85)"
                                                    : "oklch(0.65 0.2 260)"
                                            }
                                        />
                                    )
                                })}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
                {/* Legend */}
                <div className="flex items-center justify-center gap-6 mt-3">
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-sm" style={{ background: "oklch(0.35 0.01 260)" }} />
                        <span className="text-xs text-muted-foreground">Matchs analyses</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-sm" style={{ background: "oklch(0.7 0.18 155)" }} />
                        <span className="text-xs text-muted-foreground">Corrects</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
