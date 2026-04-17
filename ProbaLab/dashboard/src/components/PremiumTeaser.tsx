import { Lock, Zap, ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"

/**
 * PremiumTeaser — Blurred value bet cards that tease premium content.
 *
 * Shows the SHAPE of what premium users see (edge %, odds, market)
 * but blurs the actual values. Creates FOMO and drives conversion.
 */

interface TeaserBet {
    label: string
    market: string
    edge: string
    odds: string
}

// Fake but realistic bets for the teaser
const TEASER_BETS: TeaserBet[] = [
    { label: "Arsenal vs Chelsea", market: "Over 2.5", edge: "+8.2%", odds: "2.05" },
    { label: "Barcelona vs Atletico", market: "BTTS Oui", edge: "+6.7%", odds: "1.95" },
    { label: "PSG vs Lyon", market: "1X2 Home", edge: "+5.1%", odds: "1.72" },
]

function BlurredBetCard({ bet, index }: { bet: TeaserBet; index: number }) {
    return (
        <div className="rounded-xl border border-border/30 p-4 relative overflow-hidden">
            {/* Blurred content */}
            <div className="blur-[6px] select-none pointer-events-none">
                <div className="flex items-start justify-between mb-2">
                    <div>
                        <p className="text-sm font-semibold text-foreground">{bet.label}</p>
                        <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
                            {bet.market}
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-4 mt-3">
                    <span className="text-lg font-black text-primary">{bet.edge}</span>
                    <span className="font-mono font-bold text-foreground">{bet.odds}</span>
                    <span className="text-xs text-muted-foreground">2.1% bankroll</span>
                </div>
            </div>

            {/* Lock overlay */}
            <div className="absolute inset-0 flex items-center justify-center bg-card/30 backdrop-blur-[1px]">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-card/90 border border-border/50 shadow-sm">
                    <Lock className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs font-semibold text-muted-foreground">Premium</span>
                </div>
            </div>
        </div>
    )
}

export function PremiumTeaser({ valueBetCount = 3 }: { valueBetCount?: number }) {
    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-500" />
                    <span className="text-sm font-bold text-foreground">
                        {valueBetCount} Value Bet{valueBetCount > 1 ? "s" : ""} detect&eacute;{valueBetCount > 1 ? "s" : ""} aujourd'hui
                    </span>
                </div>
            </div>

            {/* Blurred cards */}
            <div className="space-y-2">
                {TEASER_BETS.slice(0, Math.min(valueBetCount, 3)).map((bet, i) => (
                    <BlurredBetCard key={i} bet={bet} index={i} />
                ))}
            </div>

            {/* CTA */}
            <Link
                to="/premium"
                className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all hover:scale-[1.02] glow-value"
            >
                <Zap className="w-4 h-4" />
                D&eacute;bloquer les Value Bets — Essai 30 jours gratuit
                <ArrowRight className="w-4 h-4" />
            </Link>
        </div>
    )
}
