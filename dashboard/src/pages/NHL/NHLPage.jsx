import { useState, useEffect } from "react"
import { Calendar, Search, Filter } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { format } from "date-fns"
import { fr } from "date-fns/locale"

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { supabase } from "@/lib/auth"

export default function NHLPage({ date, setDate }) {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)
    const navigate = useNavigate()

    useEffect(() => {
        fetchMatches()
    }, [date])

    const fetchMatches = async () => {
        setLoading(true)
        try {
            // Create date range for the selected day (UTC)
            const startDate = new Date(date)
            startDate.setHours(0, 0, 0, 0)
            const endDate = new Date(date)
            endDate.setHours(23, 59, 59, 999)

            const { data, error } = await supabase
                .from('nhl_fixtures')
                .select('*')
                .gte('date', startDate.toISOString())
                .lte('date', endDate.toISOString())
                .order('date', { ascending: true })

            if (error) throw error
            setMatches(data || [])
        } catch (error) {
            console.error("Error fetching NHL matches:", error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6 p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900">NHL Dashboard</h1>
                    <p className="text-muted-foreground mt-1">
                        Analyses et prédictions pour les matchs de hockey.
                    </p>
                </div>

                <div className="flex items-center gap-2 bg-white p-1 rounded-lg border shadow-sm">
                    <Button variant="ghost" size="icon" onClick={() => {
                        const d = new Date(date)
                        d.setDate(d.getDate() - 1)
                        setDate(d.toISOString().slice(0, 10))
                    }}>
                        {"<"}
                    </Button>
                    <div className="flex items-center gap-2 px-2 font-medium min-w-[140px] justify-center">
                        <Calendar className="w-4 h-4 text-primary" />
                        {format(new Date(date), "EEE d MMM", { locale: fr })}
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => {
                        const d = new Date(date)
                        d.setDate(d.getDate() + 1)
                        setDate(d.toISOString().slice(0, 10))
                    }}>
                        {">"}
                    </Button>
                </div>
            </div>

            {/* Main Content */}
            <Card>
                <CardHeader>
                    <CardTitle>Matchs du jour</CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="space-y-4">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" />)}
                        </div>
                    ) : matches.length === 0 ? (
                        <div className="text-center py-12 text-muted-foreground">
                            <p>Aucun match programmé pour cette date.</p>
                            <p className="text-sm mt-2">Essayez de changer de date ou revenez plus tard.</p>
                        </div>
                    ) : (
                        <div className="grid gap-4">
                            {matches.map(match => (
                                <div
                                    key={match.id}
                                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
                                    onClick={() => navigate(`/nhl/match/${match.api_fixture_id}`)}
                                >
                                    <div className="flex items-center gap-8">
                                        <div className="text-sm text-muted-foreground font-mono">
                                            {format(new Date(match.date), "HH:mm")}
                                        </div>
                                        <div className="flex flex-col gap-2 min-w-[200px]">
                                            <div className="flex justify-between items-center font-semibold">
                                                <span>{match.home_team}</span>
                                                <span className="text-lg">{match.home_score ?? "-"}</span>
                                            </div>
                                            <div className="flex justify-between items-center font-semibold">
                                                <span>{match.away_team}</span>
                                                <span className="text-lg">{match.away_score ?? "-"}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="hidden md:block">
                                        <Badge variant={match.status === 'NS' ? 'outline' : 'secondary'}>
                                            {match.status}
                                        </Badge>
                                    </div>
                                    <Button variant="ghost" size="sm">
                                        Analyses &gt;
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader><CardTitle>Top Buteurs (Cotes Value)</CardTitle></CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground">À venir...</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader><CardTitle>Tendances Récents (L10)</CardTitle></CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground">À venir...</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
