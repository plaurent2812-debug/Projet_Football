import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MoveRight, TrendingUp, Award } from "lucide-react"

export function RightSidebar() {
    return (
        <aside className="hidden lg:flex w-[340px] shrink-0 flex-col gap-6 sticky top-0 py-6">

            {/* Widget: Match of the Day (Promo) */}
            <Card className="border-none bg-gradient-to-br from-[#374df5] to-[#5b6ef7] text-white shadow-lg overflow-hidden relative">
                <div className="absolute top-0 right-0 p-3 opacity-10 pointer-events-none">
                    <Award className="w-24 h-24" />
                </div>
                <CardHeader className="pb-2 relative z-10">
                    <div className="flex justify-between items-center">
                        <Badge variant="secondary" className="bg-white/20 text-white hover:bg-white/30 border-none">
                            MATCH À LA UNE
                        </Badge>
                        <span className="text-[10px] font-medium opacity-80">21:00</span>
                    </div>
                </CardHeader>
                <CardContent className="relative z-10 pb-6">
                    <div className="flex items-center justify-between text-center mt-2">
                        <div className="flex flex-col items-center gap-1">
                            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center font-bold text-sm ring-2 ring-white/20">M</div>
                            <span className="text-sm font-bold leading-tight">Man City</span>
                        </div>
                        <div className="flex flex-col items-center">
                            <span className="text-2xl font-black">VS</span>
                        </div>
                        <div className="flex flex-col items-center gap-1">
                            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center font-bold text-sm ring-2 ring-white/20">L</div>
                            <span className="text-sm font-bold leading-tight">Liverpool</span>
                        </div>
                    </div>
                    <Button variant="secondary" className="w-full mt-6 bg-white text-[#374df5] hover:bg-white/90 font-bold border-none">
                        Voir l'analyse
                    </Button>
                </CardContent>
            </Card>

            {/* Widget: Value Bet */}
            <Card>
                <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                    <div className="flex items-center gap-2 text-emerald-500">
                        <TrendingUp className="w-5 h-5" />
                        <CardTitle className="text-base">Value Bet du Jour</CardTitle>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                    <div className="flex items-center justify-between py-2 border-b border-border/50">
                        <div className="flex flex-col">
                            <span className="text-sm font-semibold">Real Madrid - Barcam</span>
                            <span className="text-xs text-muted-foreground">La Liga • 20:00</span>
                        </div>
                        <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50">
                            @2.10
                        </Badge>
                    </div>
                    <div className="flex items-center justify-between py-2">
                        <div className="flex flex-col">
                            <span className="text-sm font-semibold">PSG - OM</span>
                            <span className="text-xs text-muted-foreground">Ligue 1 • 21:00</span>
                        </div>
                        <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50">
                            @1.85
                        </Badge>
                    </div>
                    <Button variant="ghost" className="w-full text-xs text-muted-foreground h-8 mt-2">
                        Voir tous les value bets <MoveRight className="w-3 h-3 ml-1" />
                    </Button>
                </CardContent>
            </Card>

            {/* Widget: Ad / Promo */}
            <div className="rounded-xl bg-accent/30 border border-transparent p-8 text-center">
                <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold block mb-2">Publicité</span>
                <p className="text-sm text-muted-foreground italic">Espace Partenaire</p>
            </div>

        </aside>
    )
}
