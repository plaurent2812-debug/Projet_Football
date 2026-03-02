import { useNavigate } from "react-router-dom"
import { Check, X, Trophy, Zap, ArrowRight } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const STRIPE_PAYMENT_LINK = import.meta.env.VITE_STRIPE_PAYMENT_LINK || "#"
const TELEGRAM_VIP_LINK = import.meta.env.VITE_TELEGRAM_VIP_LINK || "#"

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
    { label: "Pronostics VIP Quotidiens (Telegram)", free: false, premium: true },
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
                <div className="space-y-4">
                    <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                        <Check className="w-5 h-5 text-emerald-500 shrink-0" />
                        <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                            Vous avez déjà accès à toutes les fonctionnalités Premium !
                        </p>
                    </div>

                    {/* Telegram VIP Box */}
                    <Card className="border-amber-500/30 bg-amber-500/5 shadow-lg shadow-amber-500/10 overflow-hidden">
                        <CardContent className="p-6">
                            <div className="flex flex-col md:flex-row items-center gap-6">
                                <div className="p-4 rounded-2xl bg-amber-500/10 text-amber-500">
                                    <Zap className="w-8 h-8 fill-current" />
                                </div>
                                <div className="flex-1 text-center md:text-left space-y-2">
                                    <h3 className="text-xl font-black tracking-tight">Le Canal Telegram VIP est prêt !</h3>
                                    <p className="text-sm text-muted-foreground">
                                        Rejoignez notre canal privé pour recevoir chaque matin vos 2 tickets de paris (Safe & Fun) directement sur votre téléphone.
                                    </p>
                                </div>
                                <Button
                                    className="bg-[#229ED9] hover:bg-[#229ED9]/90 text-white font-bold px-6 py-6 h-auto"
                                    onClick={() => window.open(TELEGRAM_VIP_LINK, '_blank')}
                                >
                                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M11.944 0C5.344 0 0 5.344 0 11.944c0 6.6 5.344 11.944 11.944 11.944 6.6 0 11.944-5.344 11.944-11.944C23.888 5.344 18.544 0 11.944 0zM18.384 8.243c-.183 1.941-1.025 6.944-1.45 9.208-.18.96-.54 1.282-.88 1.314-.741.071-1.303-.489-2.022-.96-1.125-.736-1.759-1.196-2.854-1.916-1.264-.834-.445-1.291.277-2.04.189-.196 3.473-3.184 3.536-3.454.008-.035.015-.164-.061-.233-.076-.068-.19-.046-.271-.027-.116.027-1.968 1.251-5.548 3.674-.524.36-.998.536-1.421.527-.468-.011-1.368-.266-2.037-.483-.821-.266-1.472-.407-1.415-.86.03-.236.353-.478.966-.726 3.778-1.644 6.297-2.729 7.555-3.256 3.596-1.498 4.342-1.758 4.829-1.767.108-.002.348.026.505.153.131.107.167.251.182.353.015.102.033.23.018.358z" />
                                    </svg>
                                    Rejoindre le VIP
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
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
