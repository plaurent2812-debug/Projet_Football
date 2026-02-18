import { useNavigate } from "react-router-dom"
import { Check, X, Trophy, Zap, ArrowRight } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const STRIPE_PAYMENT_LINK = import.meta.env.VITE_STRIPE_PAYMENT_LINK || "#"

const features = [
    { label: "Voir les matchs Football & NHL", free: true, premium: true },
    { label: "Probabilités 1X2", free: true, premium: true },
    { label: "Pari recommandé", free: true, premium: true },
    { label: "Top 5 Points NHL", free: true, premium: true },
    { label: "BTTS (les deux équipes marquent)", free: false, premium: true },
    { label: "Over 0.5 / 1.5 / 2.5 / 3.5 buts", free: false, premium: true },
    { label: "But sur penalty", free: false, premium: true },
    { label: "Score exact probable", free: false, premium: true },
    { label: "Expected Goals (xG)", free: false, premium: true },
    { label: "Top 2 buteurs probables (Football)", free: false, premium: true },
    { label: "Top 5 Buteurs NHL", free: false, premium: true },
    { label: "Top 5 Passeurs NHL", free: false, premium: true },
    { label: "Top 5 Tirs (SOG) NHL", free: false, premium: true },
    { label: "Analyse IA complète de chaque match", free: false, premium: true },
    { label: "Page Performance du modèle", free: true, premium: true },
]

const faqs = [
    {
        q: "Comment fonctionne l'abonnement Premium ?",
        a: "Après paiement via Stripe, votre compte est automatiquement mis à niveau. Vous accédez immédiatement à toutes les fonctionnalités Premium."
    },
    {
        q: "Les probabilités sont-elles des conseils de paris ?",
        a: "Non. ProbaLab fournit des analyses statistiques à titre informatif uniquement. Nos modèles calculent des probabilités basées sur des données historiques et des algorithmes ML."
    },
    {
        q: "Puis-je annuler mon abonnement ?",
        a: "Oui, à tout moment depuis votre espace Stripe. L'accès Premium reste actif jusqu'à la fin de la période payée."
    },
]

export default function PremiumPage() {
    const { user, isPremium, isAdmin } = useAuth()
    const navigate = useNavigate()

    const handleUpgrade = () => {
        if (!user) { navigate('/login'); return }
        // Stripe payment link with client_reference_id for user tracking
        const url = `${STRIPE_PAYMENT_LINK}?client_reference_id=${user.id}`
        window.open(url, '_blank')
    }

    return (
        <div className="max-w-3xl mx-auto space-y-10 py-8 animate-fade-in-up">

            {/* Header */}
            <div className="text-center">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 mb-4">
                    <Trophy className="w-3.5 h-3.5 text-amber-500" />
                    <span className="text-xs font-bold text-amber-600 dark:text-amber-400">ProbaLab Premium</span>
                </div>
                <h1 className="text-3xl font-black tracking-tight mb-3">
                    Débloquez toutes les analyses
                </h1>
                <p className="text-muted-foreground max-w-md mx-auto">
                    Accédez aux statistiques avancées, aux buteurs probables et aux analyses IA complètes pour chaque match.
                </p>
            </div>

            {/* Already premium */}
            {(isPremium || isAdmin) && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <Check className="w-5 h-5 text-emerald-500 shrink-0" />
                    <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                        Vous avez déjà accès à toutes les fonctionnalités Premium !
                    </p>
                </div>
            )}

            {/* Comparison table */}
            <Card className="border-border/50 overflow-hidden">
                <div className="grid grid-cols-3 bg-accent/30 border-b border-border/40">
                    <div className="p-4 text-sm font-bold text-muted-foreground">Fonctionnalité</div>
                    <div className="p-4 text-center">
                        <span className="text-sm font-bold">Gratuit</span>
                    </div>
                    <div className="p-4 text-center bg-primary/5 border-l border-primary/10">
                        <div className="flex items-center justify-center gap-1.5">
                            <Trophy className="w-4 h-4 text-amber-500" />
                            <span className="text-sm font-bold text-primary">Premium</span>
                        </div>
                    </div>
                </div>
                {features.map((f, i) => (
                    <div key={i} className={`grid grid-cols-3 border-b border-border/30 last:border-0 ${i % 2 === 0 ? '' : 'bg-accent/10'}`}>
                        <div className="p-3 text-sm text-foreground/80">{f.label}</div>
                        <div className="p-3 flex items-center justify-center">
                            {f.free
                                ? <Check className="w-4 h-4 text-emerald-500" />
                                : <X className="w-4 h-4 text-muted-foreground/40" />
                            }
                        </div>
                        <div className="p-3 flex items-center justify-center bg-primary/3 border-l border-primary/10">
                            <Check className="w-4 h-4 text-emerald-500" />
                        </div>
                    </div>
                ))}
            </Card>

            {/* CTA */}
            {!isPremium && !isAdmin && (
                <div className="text-center space-y-4">
                    <Button
                        size="lg"
                        className="bg-amber-500 hover:bg-amber-600 text-white border-0 shadow-xl shadow-amber-500/25 px-8 py-6 text-base font-bold"
                        onClick={handleUpgrade}
                    >
                        <Trophy className="w-5 h-5 mr-2" />
                        Passer Premium
                        <ArrowRight className="w-5 h-5 ml-2" />
                    </Button>
                    <p className="text-xs text-muted-foreground">
                        Paiement sécurisé via Stripe · Annulation à tout moment
                    </p>
                </div>
            )}

            {/* FAQ */}
            <div className="space-y-4">
                <h2 className="text-lg font-bold tracking-tight">Questions fréquentes</h2>
                {faqs.map((faq, i) => (
                    <Card key={i} className="border-border/50">
                        <CardContent className="p-4">
                            <p className="text-sm font-bold mb-1.5">{faq.q}</p>
                            <p className="text-sm text-muted-foreground leading-relaxed">{faq.a}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Legal */}
            <p className="disclaimer-text text-center">
                ProbaLab fournit des analyses statistiques à titre informatif uniquement.
                Ce site ne constitue pas un conseil en paris sportifs. Jouez de manière responsable. 18+
            </p>
        </div>
    )
}
