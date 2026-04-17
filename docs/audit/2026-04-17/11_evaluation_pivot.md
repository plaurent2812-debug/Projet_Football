# 11 — Évaluation du pivot "Spécialiste en probabilités sportives"

> Date : 2026-04-17
> Auditeur : auditeur produit/stratégie senior
> Profondeur : Deep, adversarial
> Sources : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`, `ProbaLab/tasks/plan_pivot_probas_sportives.md`, annexes 01 à 10, `BP_ProbaLab_v2.pdf`.

---

## 1. Rappel du pivot (3-4 phrases)

ProbaLab abandonne le positionnement "value betting" pur pour devenir "Spécialiste en probabilités sportives foot + NHL", avec un home dashboard unifié et un bandeau sticky "Paris du Jour" cross-page. Trois catégories publiques sont générées quotidiennement par sport : Safe (cote 1.80-2.20, 3 picks), Fun (parlay 4 legs, total ~19.4), Value bet (0-5 picks à EV > 3%). Tout est tracké sur une bankroll virtuelle 10€/pick (WIN/LOSS/ROI par catégorie), les picks deviennent **publics**, et la feature principale ("Paris du Soir", aujourd'hui 4e onglet) remonte en home pour corriger la leçon 55. Coût annoncé : 13-20 jours de dev sur 4 phases (backend → observation silencieuse → UI → polish).

---

## 2. Forces du pivot

1. **Correction ciblée de la leçon 55** (feature principale enfouie). Le bandeau sticky + HomeDashboard répondent directement au problème majeur remonté par l'annexe 07 : aujourd'hui l'utilisateur doit atteindre le 4e onglet pour voir les picks (annexe 07 §2.2.3). La solution est la bonne.

2. **Positionnement occupé par personne sur le marché francophone.** L'annexe 10 §5.3 identifie précisément cette zone blanche : *"Il n'existe pas de produit grand public européen qui expose EV + Kelly de façon lisible."* Le tryptique Safe/Fun/Value vulgarise une mécanique aujourd'hui réservée aux abonnés RebelBetting à 99-199€/mois. La gradation "Safe (rassurant) → Value (mathématique) → Fun (émotion)" est pédagogique et a du potentiel de rétention.

3. **Architecture data-first propre.** Le design (§5.3) impose des fonctions pures pour les 6 générateurs + wrapper impur `save_daily_picks` — c'est la bonne application de la leçon 62 (déjà validée par `best_bets_logic.py`, voir annexe 05 §2.1). Testabilité prévue à 85%, ce qui adresserait l'un des problèmes de l'annexe 08 (0% cov sur `ticket_generator.py`).

4. **Idempotence scheduler explicite** (`delete-before-insert`, `max_instances=1`, `coalesce=True`). Adresse le R6 du design, conforme aux patterns APScheduler déjà en place (annexe 05 §2.1).

5. **Phase 2 "observation silencieuse" correctement placée** (5-7 jours DB-only avant exposition UI). Filet de sécurité raisonnable, même s'il est insuffisant sur le plan monitoring (voir §5).

6. **Tracking bankroll virtuel + ROI public** est exactement la "transparence radicale" identifiée en zone blanche par l'annexe 10 §5.1. Bien exécuté, c'est un différenciateur commercial majeur.

---

## 3. Faiblesses du pivot

1. **Le pivot suppose un NHL en L3+ alors qu'il est L3 borderline bas.** L'annexe 04 est catégorique : *"Le NHL n'est pas prêt pour le pivot tel que spécifié"* (verdict final). Trois bloquants structurels :
   - Player props market gap : The Odds API ne renvoie que `player_goals` en plan accessible. `player_points` et `player_assists` (marchés Safe NHL du pivot, design §5 D5) n'ont **pas de vraies cotes** — le design le sait (D6, R2) et propose un "fallback cotes implicites" qui **détruit la crédibilité** du tracking (voir §4).
   - Calibration sous-alimentée : < 50 samples sur ASSIST/SHOT (annexe 04 §2.2). Les Safe NHL seraient servis sur des probabilités à variance élevée pendant des mois.
   - Fallback ML silencieux (annexe 04 §2.2 P0) : ~40% des requêtes SHOT/ASSIST tombent en Poisson sans log WARNING. Brier 0.24 vs XGBoost 0.18 — les picks NHL afficheraient des probas 30% moins précises que promis.

2. **Aucune persistance du monitoring, qui serait justement l'épine dorsale de la Phase 2.** L'annexe 03 est sans appel : *"Pipeline monitoring désactivée en prod"* (P0 critique), pas de `model_health_log`, Brier recalculé puis jeté à chaque appel API. Comment décider "go/no-go" après 5-7 jours d'observation sans timeline persistée du Brier par catégorie ? Le gate Phase 2 du plan est **purement qualitatif** alors qu'il devrait être quantitatif.

3. **Bugs ML P0 non-adressés par le plan.** L'annexe 02 identifie 3 bugs bloquants que le pivot ignore :
   - Data leakage `eval_set=(X_test, y_test)` (train.py:393, 564) → métriques optimistes de 2-5%
   - `sample_weight` silencieusement ignoré dans `cross_val_score` (train.py:369-372)
   - `WEIGHT_MARKET=0.20` sous-dominant (leçon 52) → le signal le plus informatif est dilué
   
   Le pivot va multiplier l'exposition de ces probas biaisées : un pick Safe publié = un pick dont la proba est calibrée sur un test set vu pendant l'entraînement. C'est **un problème de crédibilité** si un utilisateur backteste indépendamment.

4. **Prérequis économique The Odds API Pro non budgété ni confirmé.** Le plan mentionne "upgrade Pro" comme Task 1.2 mais ne dit ni le prix (~500$/mois selon annexe 04 §5 P0-1), ni la validation qu'il couvre effectivement `player_points` + `player_assists`. Si la réponse est "non" (très probable à 500$/mois, l'enterprise plan est bien au-delà), le pivot NHL est **non-livrable tel que spécifié**.

5. **Non-goals problématiques.** Le design §3 exclut :
   - "Pas de feature Kelly Criterion user-facing" → or le BP v2 §6 positionne Kelly comme pilier premium. Contradiction (voir §4).
   - "Pas de monétisation premium sur les picks du jour (tout est public)" → supprime la principale surface de conversion actuelle (annexe 09 §2.3 P8) sans proposer de remplacement. **Aucun plan de re-gating premium v2.**
   - "Pas de refonte du moteur" → OK, mais ne fixe pas le walk-forward validation manquant (annexe 01 §5 P0-1). Sans ça, les chiffres Brier affichés dans le tracking public restent non-trustworthy.

6. **13-20 jours d'effort manifestement sous-estimés.** Détail du sous-dimensionnement au §5 (R8 + prérequis cachés).

7. **Pivot UI livré sans fix des 154 violations de leçon 54** (annexe 07 §2.2.1) et sans tests UI (annexe 07 §2.3.4). Les `PickCard.tsx` / `PicksDuJourSticky.tsx` du plan Task 8-9 utilisent `text-xs`/`text-sm` correctement mais seront mêlés à un dashboard où 26 fichiers violent encore `text-[9-11px]` — incohérence visuelle.

---

## 4. Angles morts / assumptions non validées

Les assumptions A1-A4 du design §4 :

| # | Assumption | Statut | Commentaire |
|---|---|---|---|
| A1 | Backfill existants → `value_bet` (sauf `notes LIKE 'Auto — Fun%'` → `fun`) | OK mécaniquement | Le commit 044ff60 a déjà appliqué cette migration |
| A2 | Picks admin trackés séparément via `is_auto=false` | OK | Déjà en prod |
| A3 | Page Performance publique (non gated) | **DISCUTABLE** | Contredit BP v2 §6 qui liste "track record vérifiable" comme pilier premium. Le gating doit être tranché |
| A4 | Mise virtuelle 10€/pick | OK | Neutre |

**Angles morts non listés dans le design** :

1. **Contradiction frontale BP v2 vs pivot** (annexe 09 §2.1 P2) : le BP vise "value betting premium 14,99€/mois" avec gating, le pivot rend tout public à 9,99€ (prix UI actuel) en supprimant la surface de gating. **L'owner doit trancher** : posture A (spécialiste pro 14,99), B (grand public 4,99-7,99 freemium), ou C (hybride). Le pivot ressemble à C mais n'assume rien (annexe 09 §7).

2. **Le BP vient d'être rédigé en mars 2026** (moins de 6 semaines avant le pivot) et définit un produit différent. Les investisseurs/partenaires qui l'ont lu ont une représentation produit **incompatible** avec ce qui sera livré.

3. **Les fenêtres temporelles des générateurs ne gèrent pas les timezones explicitement.** Tasks 4 Step 6 : `datetime.now(timezone.utc).strftime("%Y-%m-%d")` — OK côté scheduler, mais les 40+ occurrences `datetime.now()` naïves documentées par annexe 05 §2.2 restent. Les matchs NHL à cheval UTC sont précisément le bug de la leçon 65 qui a déjà coûté.

4. **Génération quotidienne = bankroll virtuelle va diverger de la réalité utilisateur rapidement.** Avec 6 picks Safe + 2 Fun + 0-10 Value par jour × 10€ = jusqu'à 180€/jour de "virtuel misé". Sur 90 jours d'historique : 16 000€ virtuels. Un utilisateur qui bet réellement 5€/pick sur 2 picks/jour aura une bankroll réelle 100× plus petite que l'affichage — **contre-productif pour "rigueur" et "track record vérifiable"**.

5. **Aucun plan de communication du pivot**. Le §9 liste des décisions open mineures mais ne traite pas : quid des premium actuels qui ont payé pour "value betting exclusif" ? Leur plan est grandfathered ? Refunded ? Dégradé ?

6. **Aucune définition de "picks de mauvaise qualité" ≡ seuil de go/no-go Phase 2**. Design §6 P1→P2 gate : "48h crons verts, tests CI verts, picks en DB bien catégorisés" — c'est un gate **d'ingénierie**, pas de **qualité**. Quel Brier ? Quel ROI virtuel ? Quelle diversité minimum de marchés ? Non défini.

---

## 5. Risques non mitigés (depuis design doc §7)

| # | Risque design | Statut réel selon audit | Commentaire |
|---|---|---|---|
| R1 | Générateurs sortent picks mauvaise qualité | **NON mitigé** | Phase 2 observation sans persistance Brier (annexe 03 P0) = observation aveugle |
| R2 | The Odds API Pro player props NHL incomplets | **NON mitigé** | "Fallback cotes implicites" n'est pas une mitigation : il fait passer le pivot en mode dégradé silencieux (annexe 04 §2.2 P0-1) |
| R3 | Ancien UI cassé pendant transition | Mitigé | Approche 3 OK |
| R4 | Users existants perdent Kelly/bankroll perso | Mitigé techniquement | Mais contradiction BP §6 non résolue (annexe 09 §2.1 P2) |
| R5 | Page Performance lente | Mitigé | Index `idx_best_bets_cat_sport_date` OK (commit 044ff60) |
| R6 | Duplicate picks 23h re-run | Mitigé | Delete-before-insert OK |
| R7 | Backfill `fun` mal détecté | Mitigé | Commit 044ff60 validé |
| R8 | NHL ML blend bug non fixé → Phase 2 inutile | **PARTIELLEMENT mitigé** | Commit 293e743 a fixé `.ubj + .pkl` loader, mais le fallback ML silencieux (annexe 04 §2.2 P0) reste — le cas où "le modèle se charge mais ne prédit rien" non traité |
| R9 | NHL Top 3 `KeyError: 'model'` | Partiellement mitigé | Idem R8 |

**Risques supplémentaires non identifiés dans le design** :

| # | Risque ajouté | Sévérité | Source |
|---|---|---|---|
| R10 | Data leakage eval_set → Brier affiché optimiste → ROI virtuel faux | **Haute** | Annexe 02 §2.2 BUG CRITIQUE |
| R11 | Poids bookmaker 0.20 → picks Value subotimaux face au marché | Haute | Annexe 02 §2.2 / Leçon 52 |
| R12 | Pas d'analytics → pivot livré, impossible de savoir s'il convertit | **Critique** | Annexe 09 §2.4 — 0 outil analytics installé |
| R13 | 154 violations typographie leçon 54 non adressées avant pivot | Haute | Annexe 07 §2.2.1 |
| R14 | `/api/admin/update-scores` sans auth = exploitable pour DoS quota API-Football | Haute | Annexe 06 §2.2 R1 |
| R15 | Aucune page méthodologie publique → différenciateur invisible | Haute | Annexe 09 §2.5 |
| R16 | Budget The Odds API Pro ~500$/mois non validé, non budgété | Haute | Annexe 04 §5 P0-1 |
| R17 | Prix UI 9,99 vs BP 14,99 non résolu | Moyenne | Annexe 09 §2.3 P6 |
| R18 | Suppression du gating premium sans définir le nouveau gating v2 | **Critique** | Annexe 09 §2.3 P8 — zéro plan monétisation post-pivot |

---

## 6. Alignement avec les findings de l'audit (annexes 01-09)

- **Annexe 01 (moteur probabilités, L3)** — *Le pivot ignore le walk-forward validation manquant.* Les 3 catégories Safe/Fun/Value seront affichées avec des probas dont le Brier réel n'est pas validé sur test set séparé. Le claim "52-55% accuracy" reste non-trustworthy, or le pivot va **augmenter l'exposition** de ces probas (public, tracking, ROI affiché). Le pivot n'aggrave pas, mais ne résout rien et aggrave l'exposition au risque.

- **Annexe 02 (ML, L2)** — *Le pivot expose les 3 bugs P0 sans les fixer.* eval_set leakage + sample_weight CV + WEIGHT_MARKET sous-dominant. Les picks Value affichés seront sous-optimaux face au marché (poids 0.20 vs 0.60 chez Pinnacle). **Nuisible** : en rendant les probas publiques, ces bugs deviennent visibles backtestable par un utilisateur averti.

- **Annexe 03 (monitoring, L2)** — *Le pivot dépend d'un monitoring qui ne tourne pas en prod.* Phase 2 "observation silencieuse" suppose une timeline Brier persistée, qui n'existe pas (annexe 03 §2.2 P0 critique). **Le gate Phase 2 est inopérant tel que conçu**. Il faut activer `run_monitoring_alerts()` en cron + créer `model_health_log` **avant** la Phase 2, sinon la décision go/no-go sera à l'intuition.

- **Annexe 04 (NHL, L3-)** — *Le pivot est en frontale collision avec l'état du NHL.* Player props market gap + calibration sous-alimentée + fallback silencieux = les Safe NHL sont **non-livrables** tels que spécifiés. Le pivot doit soit attendre l'upgrade Odds API Pro (~500$/mois + 2 semaines), soit restreindre le scope Safe NHL à `player_goals` uniquement (et assumer publiquement le scope réduit).

- **Annexe 05 (architecture, L2 quasi-L3)** — *Neutre à légèrement positif.* Les 6 générateurs purs respectent la leçon 62 (pattern `best_bets_logic.py`). Par contre, le pivot n'aide pas à résoudre la dualité scheduler APScheduler / Trigger.dev (commentaire faux `api/main.py:15`), ni les 40+ `datetime.now()` naïfs. Pas d'aggravation, pas de gain.

- **Annexe 06 (sécurité, L3-)** — *Neutre.* Le pivot ajoute 4 endpoints publics (`/api/picks/daily`, `/api/picks/performance`, `/api/matches/foot-today`, `/api/nhl/daily-top3`) sans rate limit différencié (annexe 06 §2.2 P6), sans `response_model` systématique (annexe 05 §2.3), et sans `extra="forbid"` sur les schemas (annexe 06 §2.2.1). **Il faut que ces 4 endpoints soient rate-limités et typés dès le premier commit**, sinon ils ajoutent 4 surfaces d'attaque.

- **Annexe 07 (UI/UX, L2)** — *Adressage partiel.* Le pivot corrige la leçon 55 (feature principale à 1 clic) mais **laisse** les 154 violations typographie, l'absence d'accessibilité clavier, les `<div onClick>` à la place de `<button>`, l'absence de types API partagés. Le verdict 07 §7.1 est explicite : *"le pivot ne doit pas être mergé tant que les 5 P0 ne sont pas livrés"*. Cette condition n'est pas portée par le plan pivot.

- **Annexe 08 (tests/CI, L2)** — *Positif ciblé mais faible.* Le plan Task 6 prévoit des tests pour les 6 générateurs (correct) mais n'adresse pas : Makefile obsolète, `daily-pipeline.yml` vise legacy `Projet_Football/`, `--cov-fail-under=21` inchangé, scripts `src/test_*.py` non déplacés, pas de test e2e pipeline (coverage_gaps.md §Phase 1.5 planifié jamais fait). Le pivot augmente la surface testée mais dans un environnement CI fragile.

- **Annexe 09 (produit/positionnement, L2)** — *Le cœur du problème.* Zéro analytics → pivot livré aveugle (R12). BP vs pivot non réconciliés (P2). Valeur prop invisible (P5) reste invisible après pivot. Prix non aligné (P6). Gating premium supprimé sans remplacement (P8). **Le pivot ne résout aucun des 10 problèmes produit identifiés** — il en crée même 2 nouveaux (bankroll virtuelle fictive + suppression surface conversion).

- **Annexe 10 (benchmark, transverse)** — *Positif stratégiquement.* Le positionnement "Safe/Fun/Value lisible grand public" occupe précisément la zone blanche §5.3. L'ambition "rigueur + pédagogie + francophone foot+NHL" décrite §6 est parfaitement alignée avec le pivot. Mais **tout dépend de l'exécution** : si les proofs (Brier, CLV) ne sont pas publiés, le pivot ressemblera à un tipster Forebet-like amélioré, pas à un "spécialiste probabilités".

---

## 7. Alignement avec le benchmark concurrentiel (annexe 10)

Le positionnement proposé **"Spécialiste en probabilités sportives"** est distinctif dans le paysage :

| Concurrent | Zone occupée | ProbaLab après pivot |
|---|---|---|
| Forebet / PredictZ / Infogol | Tipsters gratuits opaques | ProbaLab = tipster **transparent + tracking public** |
| RebelBetting | Pro value betting 99-199€/mois | ProbaLab = value betting **grand public + pédagogique** |
| SofaScore / OneFootball | UX mobile sans prédictions | ProbaLab = **prédictions + UX** (si leçon 54 fixée) |
| Action Network | US multi-books experts | ProbaLab = **foot UE + NHL algo** (non-substituable en EU) |
| MoneyPuck | NHL xG desktop gratuit | ProbaLab = **NHL xG + EV + mobile** (seulement si Odds Pro) |

**Le pivot occupe un espace réel, défendable et vide.** L'annexe 10 §5.3 confirme : *"Il n'existe pas de produit grand public européen qui expose EV + Kelly de façon lisible."* Le pivot est une application directe et correcte de cette insight.

**Contre qui ProbaLab se bat après pivot ?**
1. **RebelBetting** côté value (prix 10× plus bas, accessible, grand public)
2. **Action Network** si jamais il arrive en Europe (moins probable à court terme)
3. **Forebet/PredictZ** côté tipsters (par la transparence + tracking)
4. **SofaScore/OneFootball** si un jour ils lancent des prédictions (menace existentielle)

**Défense possible** : capitaliser sur les zones blanches §5.1 (transparence radicale), §5.2 (explainability narrative), §5.5 (éducation probabiliste embarquée). Ce sont les amendements qui transforment le pivot d'un "tipster de plus" en "première plateforme probabiliste francophone crédible".

---

## 8. Verdict

> **Recommandation : GO avec amendements forts**

Justification en 5 phrases. Le pivot adresse un vrai problème produit (leçon 55 visible, value prop étroite) et occupe une zone blanche marché réelle (annexe 10 §5.3) — stratégiquement c'est la bonne direction. Mais tel que spécifié, il **dépend de prérequis techniques non remplis** (monitoring persistant, NHL player props, walk-forward validation, fix bugs ML P0) et **supprime la principale surface de conversion** sans plan de remplacement. Le livrer en l'état, c'est risquer de transformer un positionnement gagnant en exposition publique de 3 bugs ML et d'un NHL sous-dimensionné. La phase 2 "observation silencieuse" est un bon garde-fou conceptuel, mais elle est **inopérante** sans persistance du monitoring. **Partir, mais avec 8 amendements obligatoires et 5 prérequis bloquants fixés avant la Phase 1.**

---

## 9. Amendements proposés

1. **Amendement #1 — Gating Phase 2 quantitatif, pas qualitatif.** Avant de démarrer le pivot, définir des seuils objectifs : Brier moyen par catégorie < 0.21, ROI virtuel 30 jours > -5%, coverage picks > 80% des jours, ≥ 3 marchés distincts dans Safe foot. Sans ces chiffres atteints, **no-go UI switch** automatique.

2. **Amendement #2 — Scope NHL restreint publiquement.** Si l'upgrade Odds API Pro n'est pas confirmé budgétairement **avant** la Phase 1, restreindre le scope Safe/Fun NHL au seul marché `player_goals` (vraies cotes disponibles). Documenter clairement dans l'UI : "NHL — butaires uniquement" pour éviter le "mode dégradé silencieux".

3. **Amendement #3 — Désactiver le tracking public des picks NHL jusqu'à Brier validé.** Les picks NHL doivent rester en mode "staff view" pendant 4 semaines de collecte pré-pivot (allongement Phase 2 à 4 semaines NHL-only), pour avoir ≥ 100 picks résolus avant de publier ROI sur NHL.

4. **Amendement #4 — Ajouter une Task 1.0 : fixer les 3 bugs ML P0 avant tout générateur.** eval_set leakage, sample_weight CV, WEIGHT_MARKET. Sinon les probas exposées publiquement sont biaisées et mesurables — et le différenciateur "transparence" retourne contre ProbaLab.

5. **Amendement #5 — Ajouter une Task 1.5 : brancher `run_monitoring_alerts()` en cron + créer `model_health_log`.** C'est le prérequis technique de la Phase 2. Sans cette table et sans cron réel, la décision go/no-go sera à l'intuition.

6. **Amendement #6 — Définir explicitement le gating premium v2 dans le design doc.** Options à traiter : historique étendu > 30j, alertes push, NHL player props détaillés, API access, exports CSV, mode "power user" avec Kelly personnalisable. Décision tranchée **avant** la Phase 3 UI.

7. **Amendement #7 — Installer Plausible (ou PostHog) en Task 0 de la Phase 1.** Non négociable : livrer le pivot sans analytics = livrer à l'aveugle. 1 journée de travail, coût 9€/mois Plausible.

8. **Amendement #8 — Réconcilier BP v2 ↔ pivot avant merge.** Document 1 page co-signé par l'owner qui explicite la posture (A/B/C selon annexe 09 §7). Sans ça, partenaires/investisseurs ayant lu le BP découvriront un produit différent. Mettre à jour `BP_ProbaLab_v2.pdf` en v2.1.

---

## 10. Conditions préalables avant démarrage Phase 1

Checklist des correctifs P0 obligatoires **avant** de lancer la Task 1 du plan actuel :

- [ ] **PR1 — Fix eval_set leakage** (`train.py:393, 564`, validation split séparé). Réestimer Brier (probable -2-5% vs valeurs affichées). Ref : annexe 02 §5 P0-1.
- [ ] **PR2 — Fix `sample_weight` CV** (`train.py:369-372`, `params` → `fit_params`). Ref : annexe 02 §5 P0-2.
- [ ] **PR3 — Rééquilibrer WEIGHT_MARKET** à 0.45-0.50 (constants.py:196-198) + backtest 12 mois. Ref : annexe 02 §5 P0-3.
- [ ] **PR4 — Fix fallback ML NHL silencieux** (annexe 04 §5 P0-2) : init en 2 étapes, log WARNING à chaque fallback Poisson, exposer `ml_fallback_used` dans les response.
- [ ] **PR5 — Brancher `run_monitoring_alerts()` en cron** + créer table `model_health_log` (Amendement #5). Ref : annexe 03 §5 P0-1/P0-2.
- [ ] **PR6 — Fermer `/api/admin/update-scores`** à tout appel sans auth (header interne ou CRON_SECRET). Ref : annexe 06 §5 P0-3.
- [ ] **PR7 — Décision budget Odds API Pro confirmée** (ou scope NHL restreint à `player_goals` assumé). Ref : annexe 04 §5 P0-1.
- [ ] **PR8 — Installer Plausible sur le dashboard** + 6 événements funnel (`landing_viewed`, `signup_started`, `signup_completed`, `premium_viewed`, `checkout_clicked`, `checkout_completed`). Ref : annexe 09 §7 Sprint 1.
- [ ] **PR9 — Document "BP vs pivot" résolu** : 1 page signée owner, posture A/B/C tranchée, gating premium v2 défini. Ref : annexe 09 §7 + Amendement #6/#8.
- [ ] **PR10 — Aligner prix UI ↔ BP** (9,99 ou 14,99 tranché, Stripe + `Premium.tsx:155` + BP §8.1). Ref : annexe 09 §2.3 P6.
- [ ] **PR11 — Makefile + `daily-pipeline.yml`** : cibler `ProbaLab/` au lieu de `Projet_Football/`. 1h de travail, bloque la régression CI. Ref : annexe 08 §5 P0-1.
- [ ] **PR12 — 154 violations `text-[9-11px]`** remplacées par `text-xs`/`text-sm`. Non négociable avant pivot UI (annexe 07 §7.1). Ajouter lint CI.
- [ ] **PR13 — Créer page `/methodology` publique** avec Brier 90j live + CLV + schéma Dixon-Coles. Le différenciateur doit être visible **avant** le pivot qui l'exploite. Ref : annexe 09 §7 Sprint 2.

**Effort estimé des prérequis** : 3-4 semaines de dev à temps plein (PR1-PR7 : 10j, PR8-PR13 : 10j). Ce qui reclasse le pivot de "13-20 jours" à **"13-20 jours + 15-20 jours de prérequis = 5-8 semaines au total"**. C'est la vraie durée à communiquer.

**Coût mensuel récurrent** : Plausible 9€ + (potentiel) The Odds API Pro ~500$/mois = ~510€/mois à prévoir si le pivot NHL est maintenu full-scope.

---

## Synthèse une ligne

Le pivot est stratégiquement juste (zone blanche marché réelle, correction leçon 55 majeure, positionnement défendable) **et** techniquement prématuré (NHL non prêt, monitoring non persistant, 3 bugs ML critiques exposés publiquement, zéro analytics) — **GO conditionné à 13 prérequis P0 fixés avant Phase 1**, sinon risque de transformer un positionnement gagnant en signal de perte de crédibilité.

---

*Fin annexe 11. Verdict final : **GO avec amendements forts**. 8 amendements + 13 prérequis bloquants documentés ci-dessus.*
