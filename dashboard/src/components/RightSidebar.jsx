import { TrendingUp, Trophy, ArrowRight } from "lucide-react"

export function RightSidebar() {
    return (
        <aside className="hidden lg:block w-[340px] shrink-0 space-y-6">

            {/* Widget: Match of the Day (Promo) */}
            <div className="rounded-xl overflow-hidden bg-gradient-to-br from-[#374df5] to-[#5b6ef7] text-white shadow-lg relative p-5">
                <div className="absolute top-0 right-0 p-3 opacity-20">
                    <Trophy className="w-24 h-24" />
                </div>
                <div className="relative z-10">
                    <h3 className="text-xs font-bold uppercase tracking-wider opacity-80 mb-2">Match à la Une</h3>
                    <div className="flex items-center justify-between mt-4 mb-4">
                        <div className="text-center">
                            <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center mb-2 font-bold">M</div>
                            <span className="text-sm font-bold">Man City</span>
                        </div>
                        <span className="text-xl font-black opacity-50">VS</span>
                        <div className="text-center">
                            <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center mb-2 font-bold">L</div>
                            <span className="text-sm font-bold">Liverpool</span>
                        </div>
                    </div>
                    <button className="w-full py-2 bg-white text-[#374df5] font-bold rounded-lg text-sm hover:bg-white/90 transition-colors">
                        Voir l'analyse
                    </button>
                </div>
            </div>

            {/* Widget: Value Bet */}
            <div className="rounded-xl border border-border bg-card shadow-sm p-4">
                <div className="flex items-center gap-2 mb-4">
                    <div className="p-1.5 bg-emerald-500/10 rounded-md">
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                    </div>
                    <h3 className="font-bold text-sm">Value Bet du Jour</h3>
                </div>

                <div className="space-y-3">
                    <div className="flex justify-between items-center text-sm border-b border-border/40 pb-2">
                        <span className="font-medium">Real Madrid - Barça</span>
                        <span className="font-bold text-emerald-500">@2.10</span>
                    </div>
                    <div className="flex justify-between items-center text-sm border-b border-border/40 pb-2">
                        <span className="font-medium">PSG - OM</span>
                        <span className="font-bold text-emerald-500">@1.85</span>
                    </div>
                </div>

                <button className="w-full mt-4 flex items-center justify-center gap-1 text-xs font-semibold text-muted-foreground hover:text-primary transition-colors">
                    Voir tous les value bets <ArrowRight className="w-3 h-3" />
                </button>
            </div>

            {/* Widget: Ad / Promo */}
            <div className="rounded-xl bg-accent/30 border border-transparent p-4 text-center">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Publicité</span>
                <div className="h-32 flex items-center justify-center text-muted-foreground/40 text-sm italic">
                    Espace Partenaire
                </div>
            </div>

        </aside>
    )
}
