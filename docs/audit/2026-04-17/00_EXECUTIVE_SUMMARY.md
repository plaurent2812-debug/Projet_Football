# Executive Summary — Audit ProbaLab 2026-04-17

> Audit 360° stratégique de ProbaLab (plateforme de prédictions sportives foot + NHL) pour devenir la meilleure app du marché.
> Spec : `docs/superpowers/specs/2026-04-17-audit-360-probalab-design.md`
> Livrable complet : `docs/audit/2026-04-17/` (12 documents)

---

## 1. Verdict en une phrase

ProbaLab est un produit **L2/L3 techniquement solide mais commercialement muet**, positionné sur une zone blanche marché réelle (transparence probabiliste francophone foot + NHL) — à **5-8 semaines** de l'état "pivot livrable crédible" et à **12-18 mois** de "meilleure app francophone spécialiste" si les 22 P0 et les zones blanches L5 sont exécutés dans l'ordre.

---

## 2. Scoring global

| Domaine | Niveau | Leader ref | Gap principal | Effort L+1 |
|---------|--------|------------|---------------|------------|
| Moteur probabilités | **L3** | Infogol (xG Opta) | Walk-forward validation absent, pas de confidence intervals | 5-8j |
| Machine Learning | **L2** | RebelBetting + Pinnacle (CLV) | 3 bugs P0 (eval_set leakage, sample_weight CV, WEIGHT_MARKET=0.20) | 4-6j |
| Monitoring ML | **L2** | Evidently / Arize / WhyLabs | Pipeline monitoring désactivée en cron, 0 persistance historique | 3-5j |
| NHL spécifique | **L3-** | MoneyPuck (xG public) | Player props market gap, calibration < 50 samples, fallback silencieux | 3-6 sem |
| Architecture backend | **L2 quasi-L3** | FastAPI SaaS standard | 2 god-routers (3 115 LOC), dualité scheduler, 40+ `datetime.now()` nus | 2-3 sem |
| Sécurité | **L3-** | OWASP / Drata-level | `extra="forbid"` absent, update-scores sans auth, audit log partiel | 1-3j P0 |
| UI/UX frontend | **L2** | SofaScore | 154 violations typo < 12px, a11y clavier quasi nulle, light mode suspect | 2 sem |
| Tests & CI/CD | **L2** | SaaS early-stage | Couverture 21%, Makefile/daily-pipeline ciblent legacy, mypy non bloquant | 1-2 sem P0 |
| Produit | **L2** | Action Network | 0 analytics, BP ≠ pivot, value prop invisible, funnel non mesurable | 1 sem P0 |

**Moyenne : L2 avec 2-3 domaines en L3.** La force technique ne se transfère pas sur les couches produit, monitoring opéré, et CI/CD. Le socle ML est solide (Poisson/Dixon-Coles/ELO calibrés), mais les bugs P0 rendent les claims "52-55% accuracy" non-trustworthy (voir §5 annexe 01, §5 annexe 02).

---

## 3. Top 5 forces de ProbaLab

1. **Moteur stats 3-couches documenté et testé** — Poisson + Dixon-Coles avec rho adaptatif continu, ELO par ligue, 50+ features, calibration isotonique/Platt/Bayesian shrinkage conditionnelle. 7 leçons majeures (rho scaling, normalisation 1X2, MAX_GOALS_GRID, euro_boost) toutes fixées (voir §2.1 annexe 01).
2. **Sécurité au-dessus de la moyenne startup** — RLS posée sur 40+ tables, `hmac.compare_digest` partout, Stripe webhook idempotent et atomique, désérialisation restreinte, trigger anti-escalade profil. L3- atteint à 85% (voir §3 annexe 06).
3. **Architecture backend en consolidation réelle** — `sys.path.insert` éradiqué, `best_bets_logic.py` exemplaire (365 LOC pur, 87 tests), middlewares LIFO corrects, Prometheus exposé. Deux dettes lourdes identifiées (trigger.py 1687 LOC, best_bets.py 1428 LOC) mais pattern de sortie prouvé (voir §2.1 annexe 05).
4. **Positionnement marché dans une zone blanche réelle** — aucun produit grand public européen ne combine EV+Kelly lisible, transparence Brier/CLV publique, et NHL européen. Le pivot Safe/Fun/Value occupe précisément cette zone (voir §5.1 et §5.3 annexe 10).
5. **Infrastructure de monitoring bien conçue (en code)** — 6 modules propres, ~1 400 LOC, métriques Brier/ECE/CLV/feature audit/data quality correctement implémentées. Il "suffit" de la brancher en cron et de persister (voir §2.1 annexe 03).

---

## 4. Top 5 faiblesses critiques (hiérarchisées par impact × effort)

1. **3 bugs ML P0 exposés publiquement après pivot** (impact critique, effort 1-2j cumulés) — `eval_set=(X_test, y_test)` leakage (train.py:393,564), `sample_weight` CV silencieusement ignoré (train.py:369), `WEIGHT_MARKET=0.20` sous-dominant vs 0.60 chez Pinnacle. Métriques biaisées de 2-5%, signal marché dilué. Un utilisateur avisé pourra backtester et détecter l'écart. Voir §2.2 annexe 02.
2. **Monitoring désactivé en prod + zéro persistance** (impact critique, effort 2-3j) — `run_monitoring_alerts()` jamais appelé en cron, aucune table `model_health_log`, Brier recalculé et jeté à chaque appel API. Rend le gate Phase 2 du pivot **inopérant** (décision go/no-go à l'intuition). Voir §2.2 P0 annexe 03.
3. **0 analytics produit installé** (impact critique, effort 1j) — aucun Plausible/PostHog/Amplitude sur le dashboard. Aucun KPI du BP (§13.2) n'est mesurable : DAU, funnel conversion, rétention D7/D30, churn driver. Pilotage produit impossible. Voir §2.4 annexe 09.
4. **NHL non prêt pour le pivot tel que spécifié** (impact haut, effort 3-6 sem + ~500$/mois) — Safe NHL "1+ Point"/"1+ Passe décisive" n'ont pas de vraies cotes bookmaker (The Odds API plan accessible limité à `player_goals`), calibration < 50 samples sur ASSIST/SHOT, fallback Poisson silencieux ~40% des requêtes. Voir verdict §9 annexe 04.
5. **UI/UX en dessous de L3** (impact haut, effort 2 sem) — 154 occurrences de `text-[9-11px]` dans 26 fichiers malgré leçon 54 (2026-04-05), a11y WCAG 2.1 AA en échec sur 1.3.1/2.1.1/2.4.7/4.1.2 (100 `<div onClick>` non-focus, ~8 `alt=` sur des dizaines de logos), light mode probablement cassé silencieusement. Voir §2.2 annexe 07.

---

## 5. Top 10 quick wins (P0 transversaux à fort ratio impact/effort)

| # | Action | Impact | Effort | Domaine | Fichier |
|---|--------|--------|--------|---------|---------|
| 1 | Fix `eval_set` data leakage (split validation séparé) | H | 0.5j | ML | `ProbaLab/src/training/train.py:393,564` |
| 2 | Fix `sample_weight` CV (`params=` → `fit_params=`) | M | 0.5j | ML | `ProbaLab/src/training/train.py:369` |
| 3 | Rééquilibrer `WEIGHT_MARKET` 0.20 → 0.45 + backtest 12 mois | H | 1j | ML | `ProbaLab/src/constants.py:196-198` |
| 4 | Installer Plausible + 6 événements funnel | C | 1j | Produit | `dashboard/index.html` + pages |
| 5 | Brancher `run_monitoring_alerts()` en cron + table `model_health_log` | C | 1-2j | Monitoring | `ProbaLab/worker.py` + migration |
| 6 | Fermer `/api/admin/update-scores` sans auth | H | 0.5j | Sécurité | `ProbaLab/api/routers/admin.py:234-269` |
| 7 | Nettoyer legacy `Projet_Football/` (Makefile, daily-pipeline.yml, ruff.toml) | H | 1j | CI/CD | `Makefile:5-8`, `.github/workflows/daily-pipeline.yml:34` |
| 8 | Corriger `railway.toml` (2 services, un seul `[services.deploy]`) + harmoniser Python 3.11 | H | 1j | CI/CD | `ProbaLab/railway.toml:4-22` |
| 9 | Fix fallback ML NHL silencieux (init 2 étapes + log WARNING + `ml_fallback_used` exposé) | H | 1j | NHL | `ProbaLab/api/routers/nhl.py:311-336` |
| 10 | `extra="forbid"` + retirer `detail=str(e)` résiduel (players.py:162) | M | 0.5j | Sécurité | `api/schemas.py`, `api/routers/players.py:162` |

**Total 10 quick wins : ~8-10j dev, impact cumulé massif** (débloque pivot, ferme 5 leçons, coupe DoS possible, pose analytics).

---

## 6. Menaces stratégiques

### Techniques
- **Drift silencieux APScheduler ↔ endpoints `/api/trigger/*`** — commentaire `api/main.py:15` ("APScheduler removed") contredit `worker.py:289`. Déjà coûté avec la leçon 64 (bug NHL schedule). Probabilité élevée de récidive.
- **Upgrade silencieux de dépendances majeures** — `fastapi>=0.109.0`, `xgboost>=2.0.0`, `supabase>=2.0.0` en `>=` ouvert, pas de lockfile. Une rebuild Railway peut introduire un breaking change.
- **Modèles ML sans versioning** — aucun hash/timestamp. Rollback impossible sans restauration DB (voir §2.2 annexe 02).

### Produit
- **Pivot livré aveugle sans analytics** — impossible de mesurer si Safe/Fun/Value convertit. Tracking bankroll virtuelle à 180€/jour × 90j = 16 000€ virtuels qui divergeront radicalement de la réalité user (contre-productif à la "rigueur").
- **Suppression du gating premium sans remplacement** — le pivot rend les picks publics mais ne définit pas le gating premium v2. Principale surface de conversion actuelle détruite (voir §2.3 P8 annexe 09, §4 angle mort #5 annexe 11).
- **BP v2 (mars 2026) ≠ pivot (avril 2026)** — deux produits incompatibles décrits. Partenaires/investisseurs qui ont lu le BP découvriront un produit différent.

### Marché
- **SofaScore / OneFootball lancent des prédictions** — menace existentielle. Ils ont les données live, l'UX best-in-class, l'audience ~10M DAU. ProbaLab ne joue pas sur ce terrain.
- **Action Network arrive en Europe** — tracker multi-books + expert picks déjà prouvés US, exportation plausible.
- **RebelBetting descend en gamme** — si leur 99€/mois devient 19€/mois accessible grand public, le pivot ProbaLab perd son angle "value betting pédagogique".

---

## 7. Opportunités différenciantes (comment passer L5)

Issues des zones blanches identifiées en §5 annexe 10, validées par convergence avec §7 annexe 11.

1. **Transparence radicale (zone blanche §5.1)** — aucun concurrent grand public ne publie Brier, log-loss, CLV vs Pinnacle en continu. ProbaLab a déjà XGBoost + Optuna + `brier_monitor.py` en code ; il suffit d'exposer publiquement (dashboard Brier 90j, leaderboard picks historique). Devient "le site qui ne triche pas". Soutenu par §5.1 annexe 10 + P0-22 annexe 12.
2. **Explainability narrative (zone blanche §5.2)** — chaque pick affiche les 3 features ML dominantes (SHAP-like), le narratif Gemini structuré (forme/blessures/enjeu), et la divergence ML vs marché. Le blending 70/30 stats+Gemini existe déjà — il faut structurer l'output. Killer feature IA 2026 sur laquelle personne n'investit. Soutenu par §5.2 annexe 10.
3. **Éducation probabiliste embarquée francophone (zone blanche §5.5)** — tooltips contextuels EV/Kelly/CLV/value sur chaque pick, onboarding interactif gamifié. Angle francophone presque vide (Pinnacle le fait en EN/hors parcours, personne en FR/in-product). Coût : pur UI + rédactionnel, aucun investissement infra. Soutenu par §5.5 annexe 10 + P2-25 annexe 12.

Ces 3 angles combinés forment le positionnement `§6 annexe 10` : *"le premier spécialiste francophone des probabilités sportives grand public, rigoureux comme un pro et pédagogique comme une app mainstream"*.

---

## 8. Évaluation du pivot en cours

Le pivot "Spécialiste en probabilités sportives" (design `2026-04-11`) adresse un vrai problème (leçon 55 : feature principale enfouie) et occupe une zone blanche marché réelle. Stratégiquement c'est la bonne direction. Mais tel que spécifié, il dépend de prérequis techniques non remplis (monitoring persistant, NHL player props, walk-forward validation, 3 bugs ML P0) et supprime la principale surface de conversion sans plan de remplacement. Livrer en l'état = transformer un positionnement gagnant en exposition publique de 3 bugs ML et d'un NHL sous-dimensionné. Effort réel = **13-20j dev + 15-20j prérequis P0 = 5-8 semaines**, pas 13-20 jours.

> **Recommandation : GO avec amendements forts**

Top 3 prérequis bloquants avant démarrage Phase 1 :
1. **Fix bugs ML P0 + walk-forward validation** (PR1-PR3 + P0-11 annexe 12) — sinon les probas publiées du pivot sont biaisées et backtestables, et le différenciateur "transparence" se retourne contre ProbaLab. Effort : ~3j.
2. **Brancher le monitoring en cron + table `model_health_log`** (PR5 annexe 11, P0-4 annexe 12) — sans persistance du Brier, la Phase 2 "observation silencieuse" du pivot est inopérante, décision go/no-go à l'intuition. Effort : ~2j.
3. **Décider budget Odds API Pro (~500$/mois) OU restreindre scope Safe NHL à `player_goals`** (PR7 annexe 11, P0-10 annexe 12) + installer Plausible + réconcilier BP vs pivot (posture A/B/C tranchée). Effort : 1j décision + 1j analytics + 1j doc = 3j.

Voir le verdict détaillé et les 8 amendements dans annexe 11, §8-§10.

---

## 9. Roadmap haut niveau (3 horizons)

- **H1 (0-4 sem) — Stabilisation** :
  - Fixer 22 items P0 (bugs ML, monitoring cron, sécurité, infra, analytics, UI foundation, /methodology publique, décision NHL budget).
  - Réconcilier BP v2.1 avec pivot (posture A/B/C tranchée, prix aligné 9,99 ou 14,99, gating premium v2 défini).
  - Poser la page `/methodology` avec Brier 90j live — le différenciateur devient visible avant le pivot qui l'exploite.
  - Fin H1 = feu vert Phase 1 pivot, aucun des 13 prérequis de l'annexe 11 ouvert.

- **H2 (1-3 mois) — Pivot + L3+** :
  - Livrer le pivot (4 phases) avec gating Phase 2 **quantitatif** (Brier < 0.21, ROI virtuel 30j > -5%, coverage ≥ 80%, ≥ 3 marchés Safe).
  - Découper `trigger.py` et `best_bets.py` en packages ; ML meta-learner retrained avec 50+ features ; NHL L4 pilote (si budget Odds Pro confirmé) ou scope restreint assumé.
  - Sécurité L4 pilote (MFA admin, CSP, audit log structuré, pip-audit+bandit+gitleaks CI).
  - Couverture tests ≥ 60%, tests e2e pipeline, mypy strict sur modules stables.
  - Produit L3 : checkout serveur, Customer Portal, NPS in-app, dashboard KPIs, 8-10 interviews user research.

- **H3 (3-12 mois) — Différenciation L5** :
  - Livrer 2-3 dimensions L5 des zones blanches annexe 10 §5 : transparence radicale (dashboard Brier/CLV public + leaderboard picks), explainability narrative (SHAP + Gemini structuré par pick), éducation probabiliste embarquée.
  - i18n EN/ES = marché x5. SEO pilier 2 articles/mois. App mobile PWA avancée. A/B testing framework.
  - MLOps L5 : Sentry, logs centralisés, rotation secrets auto, pen test trimestriel, WAF.
  - Cible : "héritier francophone de FiveThirtyEight pour les paris sportifs", posture clarifiée.

---

## 10. Chiffres clés

| KPI | Actuel | Objectif 3 mois | Objectif 12 mois |
|-----|--------|------------------|-------------------|
| Niveau moyen domaines | L2 (9 domaines : 1 L3, 1 L3-, 1 L3 moteur, 6 L2) | L3+ sur 7/9 | L4 sur 2-3 domaines, L5 sur 2-3 zones blanches |
| Brier foot | non publié (estimé 0.21-0.23) | < 0.21 (publié, validé walk-forward) | < 0.19 |
| Brier NHL | ~0.22 (estimé, non publié) | < 0.23 | < 0.21 |
| Couverture tests | 21% (mesuré 2026-04-17) | 40% | 75% |
| Lighthouse mobile | non mesuré | > 70 | > 90 |
| Endpoints sans Pydantic strict (`extra="forbid"`) | ~40 POST | 0 | 0 |
| `datetime.now()` nus | 54 occurrences | 0 (+ pre-commit rule) | 0 |
| Bugs P0 leçons non résolus | 22 (voir annexe 12 §2) | 0 | 0 |
| Analytics événements produit | 0 | 6+ (funnel core) | 20+ (adoption + cohortes) |
| Violations typographie < 12px | 154 (26 fichiers) | 0 (+ lint CI) | 0 |
| DAU / MAU | non mesurable | mesuré hebdo | croissance MoM > 10% |
| Taux conversion free→premium | non mesurable | mesuré | > 3% |
| Churn mensuel premium | non mesurable | mesuré | < 5% |

---

## 11. Décisions à trancher par l'owner (urgent)

1. **Budget The Odds API Pro (~500$/mois) : GO / NO-GO / scope restreint** — si NO-GO, assumer publiquement le scope Safe NHL restreint au marché `player_goals` uniquement (§5 annexe 04, prérequis PR7 annexe 11). Sans décision, le scope NHL reste flottant et le pivot risque le "mode dégradé silencieux" (cotes implicites pour `player_points`/`player_assists`).
2. **Posture produit A / B / C (annexe 09 §7)** — (A) Spécialiste pro 14,99€ niche rigoureuse, (B) Grand public 4,99-7,99€ freemium concurrence Sportytrader, (C) Hybride "scientifique accessible". Le pivot ressemble à C mais n'est pas nommé. Sans cette décision, BP v2 et pivot décrivent deux produits différents. Décision à prendre **avant** Phase 3 UI du pivot.
3. **Prix abonnement : 9,99€ (UI actuelle `Premium.tsx:155`) OU 14,99€ (BP §8.1)** — doit être aligné Stripe + UI + BP v2.1. À coupler à la décision (1) et (2). 30 min de décision, 30 min d'implémentation.
4. **Gating premium v2 post-pivot** — quand les picks du jour deviennent publics, qu'est-ce qui reste premium ? Options à arbitrer : historique étendu > 30j, alertes push, NHL player props détaillés, API access, exports CSV, mode "power user" avec Kelly personnalisable. Décision nécessaire avant Phase 3 UI.
5. **Rythme d'exécution (4h/sem solopreneur vs full-time) et capacité d'investissement H1** — la roadmap H1 "4 semaines" suppose ~40h/semaine. À ~5h/semaine, H1 prend 11-14 semaines calendaires. Décider : embaucher ponctuellement, sprinter 4 semaines à temps plein, ou étaler et communiquer honnêtement le calendrier pivot (Q3 2026 au lieu de mai 2026).

---

## 12. Prochaine étape

Relire cet audit (15-20 min), valider les 5 décisions §11 (~2h de réflexion + 1 réunion si co-décideur), puis invoquer `writing-plans` sur `12_roadmap_meilleure_app.md` pour produire un plan d'exécution détaillé du H1 (22 items P0, dépendances, jalons hebdo, affectations). Le H1 est le chemin critique : tant qu'il n'est pas fait, le pivot et la différenciation L5 restent bloqués.

---

*Audit réalisé le 2026-04-17 par un auditeur senior. 12 annexes sectorielles (~160 pages cumulées) dans `docs/audit/2026-04-17/`. Relecture suggérée trimestrielle.*
