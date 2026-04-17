# 09 — Produit & Positionnement

**Date** : 2026-04-17
**Auditeur** : auditeur produit senior
**Profondeur** : Deep
**Sources primaires** : `BP_ProbaLab_v2.pdf` (mars 2026), `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`, code `ProbaLab/dashboard/src/` et `ProbaLab/api/routers/stripe_webhook.py`.

---

## 1. Périmètre audité

Cette annexe couvre la **couche produit** de ProbaLab — tout ce qui détermine pourquoi un utilisateur choisit (ou pas) cette plateforme plutôt qu'une autre, et combien il paie pour ça :

- Value proposition (déclarée vs visible dans l'app)
- Segment cible et marché adressable
- Modèle de monétisation (plans, pricing, funnel de conversion)
- Analytics produit et capacité d'itération pilotée par la donnée
- Différenciation vs concurrence grand public, pro et tipster
- Cohérence entre le BP, le pivot en cours, et l'ambition "meilleure app du marché"

Le moteur ML, la qualité des prédictions et la stack technique sont traités dans les annexes 01-04 et ne sont abordés ici que sous l'angle produit.

---

## 2. État actuel

### 2.1 Value proposition actuelle

La value prop déclarée dans le BP (`BP_ProbaLab_v2.pdf` p.15, §6) est nette :

> « Le seul moteur de prédiction football + NHL en France qui publie ses probabilités calibrées, son Brier Score, et son CLV — sans conflit d'intérêt bookmaker. »

C'est une value prop **B2C niche, techniquement défendable, crédible**. Elle vise le "parieur informé" (BP p.12, §4.4) et s'appuie sur 5 piliers : probabilités calibrées, value bets identifiés, Kelly Criterion, track record vérifiable, module NHL unique en français.

**Problème n°1 : la value prop visible dans le produit ne correspond pas à celle du BP.**

- Dans `Premium.tsx:11-24`, la tabulation free/premium vend : "Value Bets illimités", "Kelly Criterion", "BTTS + O/U + Score exact", "xG", "Top buteurs", "Alertes Telegram", "Bankroll". **Aucune mention de Brier Score publié, de CLV, ou de "sans conflit d'intérêt"** — pourtant le cœur argumentaire du BP.
- Le PremiumTeaser (`PremiumTeaser.tsx:19-23`) met en avant "edge %", "odds", "bankroll %" — jargon value betting pur. Exactement ce que le pivot identifie comme repoussoir (design_pivot §1, ligne 17).

**Problème n°2 : le pivot en cours redéfinit la value prop sans que le BP soit aligné.**

Le pivot "Spécialiste en probabilités sportives" (design_pivot §2, lignes 21-30) repositionne autour de 3 catégories publiques (Safe / Fun / Value) avec tracking de bankroll virtuel, explicitement pour contrer le positionnement "trop étroit" du value betting actuel (ligne 16). Le BP v2 (mars 2026) décrit toujours le produit en termes de "value betting + Kelly + bankroll" (p.15, p.18). **Le BP et le pivot décrivent deux produits différents.**

**Problème n°3 : l'ambition "meilleure app du marché" n'est inscrite nulle part.**

Le BP fixe comme vision (§14.1, p.29) : « devenir la référence francophone de la prédiction sportive data-driven — l'héritier de FiveThirtyEight ». C'est une ambition de **niche éditoriale francophone**, pas de "meilleure app du marché". L'écart entre l'ambition stratégique déclarée par l'owner et la vision écrite dans le BP est significatif et doit être résolu avant toute décision GTM.

### 2.2 Segments utilisateur identifiés

Le BP identifie un unique segment cible (p.12, §4.4) :

> « Le parieur informé — celui qui cherche une edge statistique. 15-25 % des 4,9 M de parieurs actifs, soit 750 000 à 1,2 M de personnes en France. »

Profil (p.12, §4.3) : 85 % hommes, âge moyen 35 ans (73 % entre 18 et 34), 60 % CSP+, mobile > 70 % des mises, dépense 216-360 EUR/an. C'est un segment **clairement défini, mesurable et addressable**.

**Problème n°4 : le pivot introduit implicitement un second segment sans l'expliciter.**

La catégorie "Safe" (cote 1,80-2,20) et "Fun" (parlay 4 legs) du pivot (design_pivot §2, lignes 27-28) ne visent **pas** le parieur informé — elles visent le parieur occasionnel / loisir qui trouve value betting intimidant. C'est une ouverture de marché légitime, mais :
- Pas un seul mot dans le BP ne mentionne ce segment.
- Aucune persona documentée (usages, motivations, willingness to pay).
- Aucune métrique d'adoption différenciée par segment n'est prévue.

**Problème n°5 : aucune recherche utilisateur réelle n'étaie ces hypothèses.**

Le pivot est issu d'un brainstorming entre l'owner et Claude (design_pivot en-tête, ligne 4). Légitime pour démarrer, mais : **pas d'interviews, pas de sondage, pas d'A/B test préparatoire**. Les décisions D1-D8 (design_pivot §4) sont des paris produit basés sur l'intuition.

### 2.3 Monétisation (Stripe, plans, conversion)

**Architecture Stripe actuelle** (`ProbaLab/api/routers/stripe_webhook.py` + `Premium.tsx`) :

| Élément | État | Preuve |
|---|---|---|
| Webhook signé + idempotence | OK | `stripe_webhook.py:22-51` |
| Upgrade auto → role='premium' | OK | `stripe_webhook.py:106-131` |
| Email confirmation Resend | OK | `stripe_webhook.py:134-154` |
| Downgrade sur cancellation | OK | `stripe_webhook.py:157-176` |
| Log payment failed | Minimal, pas d'action user | `stripe_webhook.py:179-185` |
| **Création checkout session côté serveur** | **ABSENTE** | Aucun endpoint `/api/checkout` dans le repo — seul `VITE_STRIPE_PAYMENT_LINK` (Premium.tsx:8) redirige vers un Payment Link Stripe hébergé |
| **Endpoint Customer Portal** | **ABSENT** | L'utilisateur doit aller sur Stripe directement (Premium.tsx:36-38) |

**Problème n°6 : discordance de prix BP / UI / code.**

- BP §8.1 (p.18) : **14,99 EUR/mois**, 119 EUR/an, "prix de lancement 9,99 EUR le premier mois" (§7.3, p.16).
- `Premium.tsx:155` : affiche **"Puis 9,99€/mois"** en dur — pas 14,99.
- Aucune source unique de vérité sur le prix : il est défini dans Stripe Dashboard (hors repo), dans l'UI (hardcodé string), et dans le BP (document Word).

Risque concret : un upgrade "plan de lancement → plan standard" n'est ni documenté ni implémenté. Quand l'owner décidera de passer de 9,99 à 14,99, il devra modifier Stripe + modifier `Premium.tsx:155` + gérer les abonnés legacy.

**Problème n°7 : le funnel de conversion n'est pas mesurable.**

Chemin actuel : vue `/premium` → clic CTA → ouverture Stripe Payment Link en nouveau tab → (Stripe tunnel) → webhook → upgrade role. **Aucune étape n'émet d'événement trackable côté ProbaLab** :
- Pas de `page_viewed` sur `/premium`
- Pas de `checkout_clicked`
- Pas de `checkout_started` (impossible sans endpoint serveur)
- Pas de `upgrade_completed` (remonté par webhook mais pas exposé en analytics produit)

**Impossible de répondre aux questions basiques** : combien d'utilisateurs voient `/premium` par semaine ? Quel % clique ? Quel % paye ? Où dropent-ils ? Le BP cible "conversion > 3 %" (§11.3 p.25) — cette métrique n'est pas calculable aujourd'hui.

**Problème n°8 : contradiction entre le gating actuel et le pivot.**

- UI actuelle : `ParisDuSoir.tsx:84,99` et `PremiumLock.tsx` gatent les "Pronos du Jour" derrière premium.
- Pivot (design_pivot §3, ligne 37) : « Pas de monétisation premium sur les picks du jour (tout est public, leçon 55) ».

Le gating à casser représente **la principale surface de conversion visible aujourd'hui**. Le pivot supprime cette surface sans proposer de remplacement de valeur équivalente pour justifier l'abonnement. Question ouverte non traitée : **qu'est-ce qui reste premium après le pivot ?** Le plan Phase 4 (design_pivot §6) ne le définit pas.

**Unit economics (BP §8.4, p.19)** :
- ARPU 14,99 EUR/mois, LTV estimée 242-363 EUR, CAC cible 30-80 EUR, ratio LTV/CAC 4:1 à 6:1 → théoriquement sain.
- **MAIS** : ces chiffres supposent un churn mensuel de 5 % (§13.2 p.28). Non mesuré, non mesurable aujourd'hui. À confronter dès qu'il y aura 10+ abonnés.

### 2.4 Analytics et mesure produit

**Résultat de la recherche** : grep sur `dashboard/src/` pour `posthog|mixpanel|plausible|gtag|amplitude|analytics.track|google-analytics` → **0 résultat**.

> Aucun outil d'analytics produit n'est installé dans le dashboard React.

Conséquences directes :

| Question produit essentielle | Mesurable aujourd'hui ? |
|---|---|
| Combien de DAU/WAU/MAU ? | Non |
| Quelle page d'entrée la plus fréquente ? | Non |
| Funnel `/home → /match/X → /premium → paid` ? | Non |
| Rétention D1/D7/D30 ? | Non |
| Feature adoption (Kelly, value bets, NHL) ? | Non |
| Time-to-first-value ? | Non |
| Conversion free → premium par canal ? | Non |
| Churn driver (feature non utilisée) ? | Non |
| Clic sur bot Telegram depuis quelle page ? | Non |

**Le seul "analytics" implicite** : la table `best_bets` permet de mesurer la performance **des picks**, pas des **utilisateurs**. Tracker le Brier Score est nécessaire mais non suffisant — ça mesure le modèle, pas le produit.

**Problème n°9 : le BP lui-même définit des KPIs produit non instrumentés.**

Le BP fixe (§13.2 p.28) : abonnés Telegram, visiteurs dashboard/mois, users premium, MRR, churn mensuel < 5 %. Sur ces cinq KPIs :
- Abonnés Telegram : mesurable via l'API Telegram (non automatisé aujourd'hui).
- Visiteurs dashboard/mois : **non mesurable** sans analytics.
- Users premium / MRR : mesurable via Stripe Dashboard (manuel).
- Churn : calculable a posteriori via Stripe mais pas attribuable à une cause produit.

**L'owner ne peut pas piloter son produit avec les KPIs qu'il s'est fixé.** C'est la principale lacune du niveau de maturité produit.

**Problème n°10 : pas de mécanisme de feedback utilisateur.**

- Pas de NPS in-app
- Pas de form de feedback contextuel
- Pas de canal support explicite dans le produit (le seul contact est implicite via Telegram)
- Pas de session recording (type Hotjar)

L'itération produit repose intégralement sur l'intuition de l'owner.

### 2.5 Différenciation réelle vs perçue

**Différenciation revendiquée (BP §5.4, p.14)** :

| Capacité | ProbaLab | Forebet | DeepBetting | Sportytrader |
|---|---|---|---|---|
| Dixon-Coles + ELO + ML ensemble | OUI | NON | NON | NON |
| Calibration bayésienne | OUI | NON | NON | NON |
| Brier Score publié | OUI | NON | NON | NON |
| CLV tracking | OUI | NON | NON | NON |
| Zéro conflit d'intérêt bookmaker | OUI | NON | OUI | NON |
| Module NHL algorithmique FR | OUI | NON | Partiel | NON |

**Ces différenciateurs sont réels techniquement, mais invisibles côté utilisateur.**

- Un parieur qui arrive sur `/premium` voit une liste de features (Premium.tsx:11-24). **Aucune** ne mentionne Dixon-Coles, calibration, Brier, CLV ou "sans conflit d'intérêt".
- Aucune page "Méthodologie" publique dans le dashboard (`pages/` listées : Admin, CGU, Confidentialite, Dashboard, Hero, Home, Login, Match, NHL, ParisDuSoir, Performance, Premium, Profile, Team, UpdatePassword, Watchlist — pas de /methodologie).
- Le "track record vérifiable" (BP p.15) n'a pas de page dédiée grand public montrant Brier/CLV dans le temps ; la page `Performance.tsx` existe mais le pivot doit la refondre et elle n'est pas affichée en home.

**Conclusion de différenciation** : ProbaLab est un produit **techniquement différencié mais marketing-muet**. Un utilisateur moyen ne peut pas distinguer ProbaLab de Forebet en 30 secondes de navigation. La différenciation est enfouie dans le code, pas matérialisée dans le parcours utilisateur.

---

## 3. Niveau de maturité : **L2 / L5**

Échelle utilisée :

| Niveau | Caractéristiques |
|---|---|
| L1 | POC technique, pas d'utilisateurs réels |
| L2 | MVP en production, monétisation branchée, mais produit non instrumenté |
| L3 | Analytics en place, funnel mesuré, cycles d'itération hebdomadaires data-driven |
| L4 | Cohortes, expérimentation A/B, user research structuré, segments valides |
| L5 | PMF prouvé, NPS > 40, rétention 30d > 30 %, moat mesuré |

**ProbaLab est L2.** Les 381 tests, CI/CD, monitoring ML et stack de qualité sont L4 côté technique mais ça **ne transfère pas sur la couche produit**. Pour passer L3 : installer analytics, définir 3-5 KPIs mesurables en continu, ouvrir une boucle feedback. Pour prétendre à "meilleure app du marché", il faut au minimum L4.

---

## 4. Benchmark vs. leader du marché

### Grand public (audience massive)

| Critère | SofaScore | OneFootball | ProbaLab |
|---|---|---|---|
| DAU ordre de grandeur | ~10 M | ~10 M | < 100 (estim.) |
| Prédictions probabilistes publiques | Non | Non | Oui |
| UX mobile-first | Oui | Oui | Partiel (web responsive) |
| App native iOS/Android | Oui | Oui | Non (roadmap Année 2, BP §14.2 p.29) |
| Monétisation | Ads + premium léger | Ads + premium | Premium subscription |

Gap : l'audience. ProbaLab ne jouera jamais sur ce terrain à 5h/semaine en solopreneur.

### Pro value betting

| Critère | RebelBetting | Action Network | ProbaLab |
|---|---|---|---|
| Prix | 99-165 USD/mois | 8-40 USD/mois | 14,99 EUR/mois |
| Couverture sports | 20+ | Multiple US | Foot EU + NHL |
| Bookmakers trackés | 80+ | ~30 | 1 odds provider |
| Fonction killer | Surebet scanner | Expert picks + odds comparison | Probabilités calibrées FR |
| Audience | Bettors pros | US sport bettors | Parieurs informés FR |

Gap : ProbaLab est **30-90 % moins cher** mais offre **1/10 de la surface** (1 fournisseur d'odds, 2 sports). Acceptable pour la niche francophone si la profondeur est vraiment différenciante — pour l'instant elle ne l'est que techniquement, pas commercialement.

### Tipster foot (concurrents directs cités BP §5.1 p.13)

| Critère | Forebet | Infogol | PredictZ | ProbaLab |
|---|---|---|---|---|
| Trafic/mois | 10-18 M | ~2 M | ~3-5 M | < 1 k (estim.) |
| Modèle algo | Opaque | xG-based | Opaque | Transparent publié |
| Calibration publiée | Non | Non | Non | Oui |
| Monétisation | Pub + affiliation | Pub | Pub | Premium |

**Gap de différenciation** : ProbaLab a **la meilleure méthodologie**, **la pire audience**. Si la méthodologie ne se transforme pas en message marketing lisible (landing, page méthodo, preuves chiffrées publiques), elle restera invisible.

**Conclusion benchmark** : ProbaLab joue correctement sur un segment étroit mais défendable. "Meilleure app du marché" au sens grand public est hors de portée à court terme sans équipe ni capitaux. **"Meilleure app francophone pour parieur informé"** est atteignable en 12-18 mois si les gaps produit ci-dessous sont comblés.

---

## 5. Gaps pour passer au niveau supérieur (produit)

### P0 (bloquants pour sortir de L2)

| # | Gap | Pourquoi critique | Effort |
|---|---|---|---|
| P0-1 | **Aucun analytics produit installé** | Impossible de piloter, d'itérer, de mesurer la conversion. Invalide les KPIs BP §13.2. | 1 j (Plausible) à 3 j (PostHog) |
| P0-2 | **Value prop visible ≠ value prop BP** | Le différenciateur "Brier + CLV + no bookmaker conflict" n'apparaît nulle part dans Premium.tsx ni en home. | 2-3 j (copywriting + landing) |
| P0-3 | **Résolution BP vs pivot** | Deux produits incompatibles décrits dans deux documents récents. Doit être tranché avant P3 du pivot. | 1 j (décision owner) + MAJ BP |
| P0-4 | **Discordance prix BP/UI (14,99 vs 9,99)** | Risque de friction lors de l'upgrade standard, confusion commerciale. | 30 min (décider + aligner) |
| P0-5 | **Pas de page méthodologie publique** | Le différenciateur technique n'est pas démontrable par un visiteur non connecté. | 2-3 j (/methodology + schémas + Brier live) |

### P1 (nécessaires pour atteindre L3)

| # | Gap | Effort |
|---|---|---|
| P1-1 | Funnel conversion instrumenté (5 étapes minimum) | 2 j après P0-1 |
| P1-2 | Dashboard admin métriques produit (DAU, signups, upgrade, churn) | 3-4 j |
| P1-3 | Définir 3 personas documentées (informé / occasionnel / curieux) | 2 j |
| P1-4 | Endpoint `/api/create-checkout-session` serveur (vs Payment Link statique) | 1-2 j |
| P1-5 | Customer Portal Stripe intégré (self-serve cancellation/billing) | 1 j |
| P1-6 | NPS in-app (1 question mensuelle après 30 j d'activité) | 1 j |
| P1-7 | Clarifier ce qui reste premium après pivot (feature gating v2) | 2-3 j |
| P1-8 | Offre annuelle 119 EUR effectivement déployée (BP §7.4 p.16 — actuellement absente de l'UI) | 1 j |

### P2 (avance concurrentielle, L4)

| # | Gap | Effort |
|---|---|---|
| P2-1 | A/B testing framework (Growthbook ou flags custom) | 3-5 j |
| P2-2 | User research : 10 interviews de parieurs informés (avant pivot final) | 5 j étalés |
| P2-3 | Cohort analysis (rétention par mois d'inscription) | 2 j |
| P2-4 | Onboarding interactif (tour guidé, premier value bet expliqué) | 3-5 j |
| P2-5 | Notifications push web (pour rapprocher de l'app native) | 2-3 j |
| P2-6 | Content SEO pilier (10 articles méthodo long-tail, BP §7.4 p.16) | 10-15 j |
| P2-7 | Public leaderboard picks historique (renforce le moat "track record", BP §14.4) | 3-5 j |

---

## 6. Risques identifiés

| # | Risque | Probabilité | Impact | Preuve |
|---|---|---|---|---|
| R1 | Lancement premium mesurable à zéro : impossible de savoir si 14,99 EUR/mois se convertit | Haute | Critique | §2.4 |
| R2 | Pivot livré (5-7 j obs + 5-7 j UI) sans métriques pour valider l'hypothèse | Haute | Haut | §2.3 P8 + §2.4 |
| R3 | Churn invisible → LTV/CAC BP §8.4 reste théorique pendant 6+ mois après le lancement | Haute | Haut | BP §13.2 churn non mesuré |
| R4 | L'utilisateur ne distingue pas ProbaLab de Forebet faute de proof points in-product | Moyenne | Critique | §2.5 |
| R5 | Prix UI 9,99 vs BP 14,99 : changement tardif crée un ressentiment chez les early adopters | Moyenne | Moyen | §2.3 P6 |
| R6 | Value prop pivot "Safe/Fun" rapproche ProbaLab des canaux Telegram VIP (BP matrice §5.3 p.14) et dilue le différenciateur "scientifique" | Moyenne | Haut | design_pivot §2 vs BP §6 |
| R7 | Aucun feedback loop user → pivot P3 se fait sans signal externe sur la qualité perçue | Haute | Moyen | §2.4 P10 |
| R8 | Dépendance à un seul Payment Link statique (pas d'endpoint checkout serveur) bloque toute personnalisation tarifaire (coupons, trials dynamiques, plans différenciés) | Moyenne | Moyen | `Premium.tsx:8,50` |
| R9 | Segment "parieur occasionnel" introduit par le pivot sans être dans le BP → écart de positionnement non résolu côté investisseurs/partenaires | Moyenne | Moyen | §2.2 P4 |
| R10 | Ambition "meilleure app du marché" non écrite → pas de North Star, pas d'arbitrage priorités | Haute | Moyen | §2.1 P3 |

---

## 7. Recommandations stratégiques

### Sprint 1 (semaine 17 — cette semaine)

1. **Installer Plausible** (simple, RGPD-friendly, 9 EUR/mois) sur le dashboard. Coût : 1 jour. Sans ça, tout le reste reste aveugle.
2. **Trancher BP vs pivot** en 1 réunion owner + auditeur : le BP doit être mis à jour en v2.1 avec la nouvelle segmentation "parieur informé + parieur occasionnel curieux d'algo" ou le pivot doit être recentré pour rester dans la niche "parieur informé".
3. **Aligner le prix** : décider 9,99 ou 14,99, mettre à jour Stripe + `Premium.tsx:155` + BP §8.1.

### Sprint 2-3 (semaines 18-19)

4. **Créer `/methodology`** : page publique (non-authentifiée) avec schéma Dixon-Coles, courbe Brier 90 jours en temps réel tirée de `brier_monitor.py`, tableau CLV, comparaison visuelle "on vs Forebet/Sportytrader". C'est la page qui transforme le différenciateur technique en argument commercial.
5. **Instrumenter le funnel** : 6 événements (`landing_viewed`, `signup_started`, `signup_completed`, `premium_viewed`, `checkout_clicked`, `checkout_completed`). Dashboard Plausible ou Metabase sur la base Supabase.
6. **Endpoint `/api/create-checkout-session`** côté serveur + Customer Portal. Débloque les coupons, trials dynamiques et la tarification annuelle.

### Sprint 4-6 (semaines 20-22, avant livraison du pivot)

7. **User research** : 8-10 interviews de 30 min avec des parieurs foot francophones (recrutement Reddit `r/paris_sportifs`, Telegram publics, LinkedIn). Objectif : valider la pertinence des catégories Safe/Fun et la willingness to pay 14,99 EUR.
8. **Définir la feature gating v2** (post-pivot) : qu'est-ce qui reste premium quand les picks du jour deviennent publics ? Options à évaluer : historique étendu > 30 j, alertes temps réel, NHL player props détaillés, API access, exports.
9. **NPS in-app** à J+30 de l'inscription.

### Trimestre suivant (Q3 2026)

10. **A/B testing framework** sur au minimum 3 décisions produit majeures (landing headline, pricing display, CTA wording).
11. **Content SEO** : démarrer 2 articles méthodologie / mois. C'est le seul canal scalable pour "héritier francophone de FiveThirtyEight".
12. **Première itération app mobile PWA** si les analytics montrent > 60 % de trafic mobile (probable vu BP §4.3 p.12 : 70 % des mises via mobile).

### Arbitrage stratégique à expliciter

L'owner doit choisir entre **3 postures produit** — incompatibles à court terme :

| Posture | Cible primaire | Produit | Prix | Voie |
|---|---|---|---|---|
| **A. Spécialiste pro** | 100-500 parieurs informés | Transparence totale, Brier/CLV affichés, methodo publique | 14,99-19,99 | Défendable, niche, forte valeur perçue |
| **B. Produit grand public** | 10 000+ parieurs occasionnels | Picks Safe/Fun publics, UI accessible | Freemium + 4,99-7,99 premium | Concurrence frontale avec Sportytrader, nécessite ads |
| **C. Hybride "scientifique accessible"** | Les deux | Méthodo visible + picks vulgarisés | 14,99 standard + tier gratuit riche | Risque de diluer le différenciateur |

Le pivot en cours ressemble à C mais n'a pas été nommé comme tel. **Clarifier la posture est le prérequis #1 pour qu'aucun des 12 chantiers ci-dessus ne soit construit sur du sable.**

---

## 8. Liens internes

- Annexe 01 — Moteur probabilités : `docs/audit/2026-04-17/01_moteur_probabilites.md`
- Annexe 02 — Machine Learning : `docs/audit/2026-04-17/02_machine_learning.md`
- Annexe 03 — Monitoring ML : `docs/audit/2026-04-17/03_monitoring_ml.md`
- Annexe 04 — NHL spécifique : `docs/audit/2026-04-17/04_nhl_specifique.md`
- Business plan : `BP_ProbaLab_v2.pdf` (mars 2026)
- Design pivot : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`
- Stripe webhook : `ProbaLab/api/routers/stripe_webhook.py`
- Premium UI : `ProbaLab/dashboard/src/pages/Premium.tsx`
- Gating value bet : `ProbaLab/dashboard/src/components/paris-du-soir/PremiumLock.tsx`
- Teaser premium : `ProbaLab/dashboard/src/components/PremiumTeaser.tsx`
- Auth / role gating : `ProbaLab/dashboard/src/lib/auth.tsx:161,163`
