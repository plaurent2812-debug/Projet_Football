import { NavLink } from "react-router-dom"
import { ChevronLeft } from "lucide-react"

export default function Confidentialite() {
    return (
        <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
            <NavLink to="/" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-4">
                <ChevronLeft className="w-3 h-3" /> Retour
            </NavLink>

            <h1 className="text-2xl font-black">Politique de Confidentialité</h1>
            <p className="text-xs text-muted-foreground">Dernière mise à jour : mars 2026</p>

            <section className="space-y-3 text-sm text-foreground/80 leading-relaxed">
                <h2 className="text-base font-bold text-foreground">1. Données collectées</h2>
                <p>
                    ProbaLab collecte les données suivantes lors de votre utilisation :
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                    <li>Adresse email (inscription)</li>
                    <li>Données de navigation (pages consultées, préférences)</li>
                    <li>Données de paiement (traitées par Stripe, non stockées par ProbaLab)</li>
                    <li>Abonnement aux notifications push (endpoint technique uniquement)</li>
                </ul>

                <h2 className="text-base font-bold text-foreground">2. Utilisation des données</h2>
                <p>
                    Vos données sont utilisées exclusivement pour :
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                    <li>Gérer votre compte et votre abonnement</li>
                    <li>Personnaliser votre expérience (matchs favoris, préférences)</li>
                    <li>Envoyer des notifications (si autorisées)</li>
                    <li>Améliorer nos services et modèles de prédiction</li>
                </ul>

                <h2 className="text-base font-bold text-foreground">3. Protection des données</h2>
                <p>
                    Les données sont stockées sur des serveurs sécurisés (Supabase, hébergement UE).
                    Les mots de passe sont chiffrés. Les données de paiement sont traitées par Stripe
                    (certifié PCI DSS).
                </p>

                <h2 className="text-base font-bold text-foreground">4. Vos droits (RGPD)</h2>
                <p>
                    Conformément au RGPD, vous disposez des droits suivants :
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                    <li><strong>Accès :</strong> obtenir une copie de vos données personnelles</li>
                    <li><strong>Rectification :</strong> corriger vos données inexactes</li>
                    <li><strong>Suppression :</strong> demander la suppression de votre compte et données</li>
                    <li><strong>Portabilité :</strong> recevoir vos données dans un format standard</li>
                    <li><strong>Opposition :</strong> vous opposer au traitement de vos données</li>
                </ul>
                <p>
                    Pour exercer ces droits, contactez-nous à privacy@probalab.fr
                </p>

                <h2 className="text-base font-bold text-foreground">5. Cookies</h2>
                <p>
                    ProbaLab utilise des cookies techniques nécessaires au fonctionnement du service
                    (authentification, préférences de thème). Aucun cookie publicitaire ou de tracking
                    tiers n'est utilisé.
                </p>

                <h2 className="text-base font-bold text-foreground">6. Conservation</h2>
                <p>
                    Vos données sont conservées pendant la durée de votre compte.
                    Après suppression du compte, les données sont effacées sous 30 jours.
                </p>
            </section>

            <p className="text-xs text-muted-foreground pt-4 border-t border-border/40">
                Pour toute question relative à vos données personnelles : privacy@probalab.fr
            </p>
        </div>
    )
}
