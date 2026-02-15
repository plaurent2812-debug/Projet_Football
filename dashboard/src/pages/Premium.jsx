import { Check, Star, Trophy, Zap, Shield, Crown } from "lucide-react"
import { cn } from "@/lib/utils"

export default function PremiumPage() {
    const benefits = [
        {
            icon: Zap,
            title: "Prédictions IA Avancées",
            description: "Accès à toutes les prédictions détaillées (Score exact, Buteurs, Corners)."
        },
        {
            icon: Trophy,
            title: "Value Bets",
            description: "Détection automatique des cotes mal ajustées par les bookmakers."
        },
        {
            icon: Star,
            title: "Confiance & indices",
            description: "Voir l'indice de confiance et le Kelly Criterion pour gérer vos mises."
        },
        {
            icon: Shield,
            title: "Zéro Publicité",
            description: "Une expérience fluide et sans distraction pour vos analyses."
        }
    ]

    return (
        <div className="max-w-4xl mx-auto space-y-12 py-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

            {/* Header */}
            <div className="text-center space-y-4">
                <div className="inline-flex items-center justify-center p-3 bg-amber-500/10 rounded-2xl mb-4 ring-1 ring-amber-500/20 shadow-lg shadow-amber-500/10">
                    <Crown className="w-10 h-10 text-amber-500" />
                </div>
                <h1 className="text-4xl md:text-5xl font-black tracking-tight">
                    Devenez membre <span className="text-amber-500">Premium</span>
                </h1>
                <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                    Débloquez la puissance totale de l'IA et maximisez vos gains avec nos outils d'analyse professionnels.
                </p>
            </div>

            {/* Pricing Card */}
            <div className="relative max-w-md mx-auto">
                <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 to-orange-600 rounded-2xl blur opacity-30 animate-pulse" />
                <div className="relative bg-card border border-amber-500/30 rounded-xl p-8 shadow-2xl">
                    <div className="absolute top-0 right-0 transform translate-x-2 -translate-y-2">
                        <span className="bg-gradient-to-r from-amber-500 to-orange-600 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg uppercase tracking-wider">
                            Offre Limitée
                        </span>
                    </div>

                    <div className="text-center space-y-2 mb-8">
                        <h3 className="text-lg font-medium text-muted-foreground">Abonnement Mensuel</h3>
                        <div className="flex items-baseline justify-center gap-2">
                            <span className="text-5xl font-black">2€</span>
                            <span className="text-xl text-muted-foreground line-through decoration-destructive/50">10€</span>
                        </div>
                        <p className="text-sm font-medium text-emerald-500">
                            Pendant 2 mois, puis 10€/mois
                        </p>
                    </div>

                    <ul className="space-y-4 mb-8">
                        {benefits.map((benefit, i) => (
                            <li key={i} className="flex items-start gap-3">
                                <div className="mt-1 bg-amber-500/10 p-1 rounded-full">
                                    <Check className="w-3 h-3 text-amber-500" />
                                </div>
                                <span className="text-sm font-medium">{benefit.title}</span>
                            </li>
                        ))}
                    </ul>

                    <a
                        href={import.meta.env.VITE_STRIPE_PAYMENT_LINK || '#'}
                        target="_blank"
                        rel="noreferrer"
                        className="block w-full py-4 text-center font-bold text-white bg-gradient-to-r from-amber-500 to-orange-600 rounded-lg hover:brightness-110 transition-all shadow-lg shadow-amber-500/20 active:scale-[0.98]"
                    >
                        Profiter de l'offre maintenant
                    </a>
                    <p className="text-xs text-center text-muted-foreground mt-4">
                        Sans engagement • Annulation à tout moment
                    </p>
                </div>
            </div>

            {/* Detailed Benefits Grid */}
            <div className="grid md:grid-cols-2 gap-6">
                {benefits.map((b, i) => (
                    <div key={i} className="flex gap-4 p-6 rounded-xl bg-card/50 border border-border/50 hover:bg-card hover:border-amber-500/20 transition-all duration-300 group">
                        <div className="shrink-0 w-12 h-12 rounded-lg bg-secondary flex items-center justify-center group-hover:bg-amber-500/10 group-hover:scale-110 transition-all duration-300">
                            <b.icon className="w-6 h-6 text-muted-foreground group-hover:text-amber-500 transition-colors" />
                        </div>
                        <div>
                            <h3 className="font-bold text-lg mb-1 group-hover:text-amber-500 transition-colors">{b.title}</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {b.description}
                            </p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
