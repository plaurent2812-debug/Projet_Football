import { NavLink } from "react-router-dom"
import { ChevronLeft } from "lucide-react"

export default function CGU() {
    return (
        <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
            <NavLink to="/" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-4">
                <ChevronLeft className="w-3 h-3" /> Retour
            </NavLink>

            <h1 className="text-2xl font-black">Conditions Générales d'Utilisation</h1>
            <p className="text-xs text-muted-foreground">Dernière mise à jour : mars 2026</p>

            <section className="space-y-3 text-sm text-foreground/80 leading-relaxed">
                <h2 className="text-base font-bold text-foreground">1. Objet</h2>
                <p>
                    ProbaLab est une plateforme d'analyses statistiques sportives à titre informatif.
                    Les informations fournies ne constituent en aucun cas des conseils en paris sportifs
                    ni des incitations à parier.
                </p>

                <h2 className="text-base font-bold text-foreground">2. Accès au service</h2>
                <p>
                    L'accès à ProbaLab est réservé aux personnes majeures (18 ans et plus).
                    L'utilisateur s'engage à fournir des informations exactes lors de son inscription.
                    L'accès aux fonctionnalités Premium nécessite un abonnement payant.
                </p>

                <h2 className="text-base font-bold text-foreground">3. Responsabilité</h2>
                <p>
                    ProbaLab ne garantit pas l'exactitude des prédictions et analyses.
                    Les modèles statistiques sont fournis à titre informatif uniquement.
                    L'utilisateur est seul responsable de l'utilisation qu'il fait des informations fournies.
                    ProbaLab décline toute responsabilité en cas de pertes financières liées aux paris sportifs.
                </p>

                <h2 className="text-base font-bold text-foreground">4. Propriété intellectuelle</h2>
                <p>
                    L'ensemble du contenu de ProbaLab (algorithmes, analyses, design) est protégé par le droit
                    d'auteur. Toute reproduction ou utilisation non autorisée est interdite.
                </p>

                <h2 className="text-base font-bold text-foreground">5. Abonnement et résiliation</h2>
                <p>
                    L'abonnement Premium est géré via Stripe. L'utilisateur peut résilier à tout moment
                    depuis son espace personnel. La résiliation prend effet à la fin de la période en cours.
                </p>

                <h2 className="text-base font-bold text-foreground">6. Jeu responsable</h2>
                <p>
                    Les paris sportifs comportent des risques. Ne pariez que ce que vous pouvez vous permettre de perdre.
                    Si vous pensez avoir un problème de jeu, contactez Joueurs Info Service au 09 74 75 13 13
                    (appel non surtaxé).
                </p>
            </section>

            <p className="text-xs text-muted-foreground pt-4 border-t border-border/40">
                Pour toute question, contactez-nous à support@probalab.fr
            </p>
        </div>
    )
}
