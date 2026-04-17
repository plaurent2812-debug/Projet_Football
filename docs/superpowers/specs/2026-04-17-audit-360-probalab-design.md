# Design — Audit 360° stratégique de ProbaLab

**Date** : 2026-04-17
**Auteur** : Claude Opus 4.7 (brainstormé avec l'owner)
**Status** : ready for plan
**Branche cible** : `feat/pivot-probas-sportives` (branche courante)
**Livrable** : dossier `docs/audit/2026-04-17/` contenant 12 documents
**Contexte déclencheur** : l'owner veut faire de ProbaLab "la meilleure application de prédiction sportive du marché en foot et en NHL" et demande un audit complet avant d'agir.

---

## 1. Contexte

ProbaLab est une plateforme de prédictions sportives mature :
- Stack : FastAPI + React 19 + Supabase + XGBoost/LightGBM + Gemini
- Périmètre métier : foot (8 ligues) + NHL, marchés 1X2/DC/BTTS/O-U/Handicaps/Score Exact/Buteurs
- En production, stabilisation active — 381 tests, 68 leçons documentées, 60+ fixes sécurité récents
- Un pivot stratégique majeur est en cours : repositionnement "Spécialiste en probabilités sportives" avec catégories Safe/Fun/Value (cf `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`)
- Plan d'actions correctives post-audit 2026-04-10 également en cours (cf `ProbaLab/tasks/todo.md`)

L'audit demandé tombe donc à un moment charnière : **avant ou pendant** le pivot, sur une base de code mature mais avec de la dette connue.

## 2. Objectif

Produire un audit 360° stratégique qui :

1. Photographie l'état actuel de ProbaLab sur 9 domaines techniques/produit (état courant, pré-pivot)
2. Évalue si le pivot en cours est la bonne cible et s'il est bien conçu
3. Trace une roadmap pour atteindre le statut "meilleure app de prédiction sportive du marché" sur foot + NHL
4. Alimente ensuite (après validation) un plan d'action exécutable via le skill `writing-plans`

## 3. Non-goals (scope exclu explicitement)

- ❌ Aucune modification de code pendant l'audit — lecture seule
- ❌ Pas de plan d'action exécutable détaillé dans l'audit (ça viendra dans une phase séparée via `writing-plans`)
- ❌ Pas de re-brainstorm du pivot en cours (l'audit l'évalue, ne le refait pas)
- ❌ Pas d'ajout de nouveaux sports au-delà de foot + NHL
- ❌ Pas de benchmark sur des apps de sports autres que ceux couverts
- ❌ Pas de mesure live des performances ML en production (dépend de ce qui est loggé)
- ❌ Pas de tests utilisateurs réels (pas de recherche utilisateur primaire)

## 4. Décisions de design (validées avec l'owner)

| # | Décision | Justification |
|---|---|---|
| D1 | **Angle d'audit : 360° stratégique (option C)** — photographie état actuel + évaluation pivot + roadmap meilleure app | L'enjeu "meilleure app du marché" dépasse le scope du pivot actuel |
| D2 | **9 domaines** : moteur probas, ML, monitoring, NHL, archi backend, sécurité, UI/UX, tests/CI, produit | Couvre "absolument tout" demandé par l'owner |
| D3 | **Profondeur variable** : 5 domaines Deep (probas, ML, monitoring, NHL, UI/UX, produit), 4 domaines Medium (archi, sécu, tests, backend) | Les Deep apportent de la nouveauté ; les Medium confirment/infirment les audits existants |
| D4 | **Benchmark concurrentiel multi-segment** : tipsters (Forebet, Infogol, PredictZ), pro value betting (RebelBetting, Pinnacle CLV, BetBurger), grand public (SofaScore, OneFootball, Action Network) | Le pivot ratisse large, benchmark idem |
| D5 | **Format livrable : exec summary + 11 annexes thématiques** | Modulaire, autoportant par annexe, cohérent avec les audits existants |
| D6 | **Scoring : échelle L1-L5 + gap explicite vs leader benchmark** | Curseur de maturité absolu + relatif, évite l'inflation |
| D7 | **Livraison par batches avec feedback utilisateur entre chaque** | Permet corrections en cours de route |
| D8 | **Audit = diagnostic pur, plan d'action séparé après via `writing-plans`** | Sépare clairement "quoi et pourquoi" (audit) de "comment et quand" (plan) |

## 5. Structure du livrable

```
docs/audit/2026-04-17/
├── 00_EXECUTIVE_SUMMARY.md        (8-10 pages, lecture standalone)
├── 01_moteur_probabilites.md      (Poisson, Dixon-Coles, ELO, features)
├── 02_machine_learning.md         (XGBoost, calibration, blending, meta)
├── 03_monitoring_ml.md            (Brier, drift, calibration prod)
├── 04_nhl_specifique.md           (player props, NHL pipeline, bugs récents)
├── 05_architecture_backend.md     (FastAPI, pipelines, schedulers)
├── 06_securite.md                 (RLS, auth, rate limit, secrets)
├── 07_ui_ux_frontend.md           (React, composants, mobile, a11y)
├── 08_tests_cicd.md               (couverture, qualité, Railway)
├── 09_produit_positionnement.md   (BP, value prop, monétisation)
├── 10_benchmark_concurrentiel.md  (Forebet, Infogol, RebelBetting, etc.)
├── 11_evaluation_pivot.md         (le pivot en cours est-il la bonne cible ?)
└── 12_roadmap_meilleure_app.md    (synthèse gaps P0/P1/P2 cross-domaines)
```

### Principes structurants

- `00_EXECUTIVE_SUMMARY` est **lisible seul** par un décideur sans avoir à ouvrir les annexes
- Chaque annexe est **autoportante** : elle peut être lue indépendamment, quitte à répéter un peu de contexte
- `10_benchmark` est une annexe transversale citée partout
- `11_evaluation_pivot` est un document stratégique : le pivot mérite-t-il d'être exécuté tel quel, amendé ou repensé ?
- `12_roadmap` n'est **pas un plan d'action exécutable** — c'est une cartographie des gaps priorisés cross-domaines, pour alimenter ensuite le plan via `writing-plans`

## 6. Template des annexes thématiques (01-09)

Chaque annexe suit ce template uniforme :

```markdown
# [Domaine]

## 1. Périmètre audité
- Fichiers/modules/endpoints inspectés
- Ce qui est inclus / exclu

## 2. État actuel
### 2.1 Ce qui fonctionne bien
### 2.2 Dette technique / bugs latents
### 2.3 Code smells repérés
### 2.4 Gaps vs. bonnes pratiques de l'industrie

## 3. Niveau de maturité : Lx/L5
Justification courte du niveau attribué (2-5 phrases).

## 4. Benchmark vs. leader du marché
- Leader identifié : [nom]
- Ce qu'il fait mieux : ...
- Ce qu'il fait moins bien : ...
- Écart mesurable : ...

## 5. Gaps pour passer au niveau supérieur
### P0 — Bloquants pour devenir L[x+1]
### P1 — Améliorations significatives
### P2 — Polish

## 6. Risques identifiés
- R1 : [description] — sévérité H/M/B — probabilité

## 7. Recommandations stratégiques
3-5 recommandations hautes-niveau, pas de détail d'implémentation.

## 8. Liens internes
- Fichiers clés : `path/to/file.py:ligne`
- Leçons pertinentes : `tasks/lessons.md:N`
- Issues liées (si GitHub)
```

### Règles de rédaction

- Citer systématiquement `fichier:ligne` pour navigation
- Section 5 (gaps P0/P1/P2) = le cœur actionnable, alimente le `12_roadmap`
- Section 7 = prise de recul stratégique (pas de "comment", uniquement "quoi et pourquoi")
- Aucune proposition d'implémentation détaillée dans l'audit

## 7. Échelle de maturité L1-L5

| Niveau | Nom | Caractéristiques |
|---|---|---|
| **L1** | MVP fragile | Tourne en happy path. Bugs fréquents, pas de tests sérieux, pas d'observabilité. |
| **L2** | Fonctionnel | Stable en nominal. Quelques tests et logs, edge cases non gérés, dette visible. |
| **L3** | Solide | Stable en prod, tests couvrants, observabilité de base, sécurité correcte. Niveau attendu d'un produit commercial sérieux. |
| **L4** | Best-in-class | Au niveau des meilleurs concurrents. Calibration rigoureuse, UX polie, monitoring proactif. Rien ne manque, rien de révolutionnaire. |
| **L5** | État de l'art | Dépasse les leaders sur ≥1 dimension. Apporte une innovation mesurable. Raison pour laquelle les users choisissent ProbaLab. |

### Règles anti-inflation

1. Pas de L4 si bugs connus non corrigés
2. Pas de L5 sans preuve chiffrée de supériorité (Brier mesuré, latence, conversion)
3. Scoring strict — l'exigence "meilleure app du marché" impose un curseur dur
4. Pour chaque score, indiquer explicitement ce qu'il faudrait pour monter d'un niveau

## 8. Méthodologie d'investigation par domaine

| # | Domaine | Méthode principale |
|---|---|---|
| 1 | Moteur probabilités | Lecture `brain.py`, `prediction_blender.py`, features foot/NHL. Vérifier continuité rho, masse Poisson, calibrations (leçons 1-7, 49-53). |
| 2 | ML | Lecture `src/training/`, `src/nhl/ml_models.py`, `nhl_ml_predictor.py`. Vérifier data leakage (12), sample_weight (9), calibration (50), meta-learner (35). |
| 3 | Monitoring ML | Lire `src/monitoring/` complet. Vérifier cron actif, dashboard admin, KS test drift. |
| 4 | NHL | Deep dive `src/nhl/`, `api/routers/nhl.py`, `fetch_nhl_player_props.py`. Vérifier team normalization (67), schedule fallback (65), provider (66), ML blend bug (R8 design pivot). |
| 5 | Architecture backend | Grep `sys.path.insert` (44), `datetime.now()` nu (22), read-then-write (23). Inspect `trigger.py`, `best_bets.py`. APScheduler. |
| 6 | Sécurité | Endpoints POST/DELETE : Pydantic `extra="forbid"` ? Rate limit par tier ? RLS via Supabase MCP. Secrets, webhooks fail-closed (37). Security headers. |
| 7 | UI/UX | `dashboard/src/pages/` et `components/`. Grep `text-[9px]` (54). Nav depth (55). Mobile via preview MCP. Lighthouse. Dark mode. A11y. |
| 8 | Tests & CI | `pytest --cov` baseline. `.github/workflows/`. Vérifier cov-fail-under vs réel (60). Tests orphelins (61). Ratio unit/integration. E2E présent ? |
| 9 | Produit | Lire `BP_ProbaLab_v2.pdf`, `AUDIT_COMPLET.md`, `Football_Stack_Audit.pdf`, `NHL_Stack_Audit.pdf`. Value prop vs pivot. Monétisation Stripe. Funnel. |

Pour le benchmark concurrentiel : WebFetch + WebSearch sur les sites concurrents identifiés, documentation de leur approche publique, comparaison point par point.

### Limites méthodologiques reconnues

- Pas de mesure live des performances ML en prod (dépend de ce qui est loggé)
- Pas de vrai test utilisateur frontend (preview MCP local uniquement)
- Benchmark concurrent = lecture publique uniquement (méthodes propriétaires non accessibles)
- Lecture seule : aucune modification de code pendant l'audit

## 9. Structure de l'Executive Summary (00)

```markdown
# Executive Summary — Audit ProbaLab 2026-04-17

## 1. Verdict en une phrase
## 2. Scoring global (tableau synthèse par domaine)
## 3. Top 5 forces de ProbaLab
## 4. Top 5 faiblesses critiques
## 5. Top 10 quick wins (P0 transversaux)
## 6. Menaces stratégiques (technique / produit / marché)
## 7. Opportunités différenciantes (comment passer L5)
## 8. Évaluation du pivot en cours (GO / GO amendé / PAUSE / STOP)
## 9. Roadmap haut niveau (3 horizons H1/H2/H3)
## 10. Chiffres clés (KPIs mesurables)
```

**Contraintes** :
- Lisible en 15-20 min
- Autoportant : pas besoin d'ouvrir les annexes pour décider
- Chaque affirmation pointée vers son annexe
- 8-10 pages max

## 10. Critères d'acceptation (Definition of Done)

L'audit est réussi si :

1. **Exhaustivité** — 12 documents produits, tous non-vides
2. **Actionnabilité** — `12_roadmap.md` contient un backlog P0/P1/P2 précis suffisant pour alimenter `writing-plans`
3. **Preuves** — chaque affirmation majeure sourcée (`fichier:ligne`, leçon `tasks/lessons.md:N`, ou URL concurrent)
4. **Scoring justifié** — chaque niveau Lx motivé en 2-5 phrases
5. **Pas de langue de bois** — faiblesses assumées, sans adoucissement
6. **Exec summary autoporteur** — décidable sans lire les annexes
7. **Verdict pivot** — `11_evaluation_pivot.md` rend un avis clair GO / GO-amendé / PAUSE / STOP avec justification

## 11. Timeline estimée

| Phase | Durée | Livrable |
|---|---|---|
| Investigation code (domaines 1-8) | ~2-3h | Notes internes |
| Benchmark concurrentiel | ~1h | `10_benchmark_concurrentiel.md` |
| Rédaction annexes 01-09 | ~3-4h | 9 fichiers |
| Évaluation pivot (11) | ~30 min | `11_evaluation_pivot.md` |
| Roadmap (12) | ~45 min | `12_roadmap.md` |
| Exec summary (00) | ~1h | `00_EXECUTIVE_SUMMARY.md` |
| **Total** | **~8-10h** | 12 documents |

## 12. Livraison par batches

L'audit sera livré en 3 batches avec point d'arrêt après chaque :

- **Batch 1** : domaines 1-4 (cœur métier — probas, ML, monitoring, NHL)
- **Batch 2** : domaines 5-9 (archi, sécu, UI/UX, tests, produit)
- **Batch 3** : benchmark (10) + évaluation pivot (11) + roadmap (12) + executive summary (00)

Entre chaque batch, l'owner peut donner un feedback pour ajuster le tir.

## 13. Après l'audit

Une fois les 12 documents livrés et validés par l'owner :
- Relecture complète par l'owner
- Décision : on enchaîne vers `writing-plans` ou on ajuste l'audit
- Si go : `writing-plans` prend `12_roadmap.md` comme input pour produire un plan d'action détaillé exécutable

---

## Annexes

### A. Liens internes

- Plan pivot en cours : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`
- Plan d'actions correctives : `ProbaLab/tasks/todo.md`
- Leçons : `ProbaLab/tasks/lessons.md`
- Audits existants : `ProbaLab/AUDIT_COMPLET.md`, `ProbaLab/AUDIT_PROMPT.md`, `ProbaLab/Football_Stack_Audit.pdf`, `ProbaLab/NHL_Stack_Audit.pdf`
- Business plan : `BP_ProbaLab_v2.pdf`

### B. Glossaire

- **L1-L5** : échelle de maturité (voir §7)
- **P0/P1/P2** : priorité (P0 = bloquant pour niveau cible, P1 = significatif, P2 = polish)
- **Gap vs leader** : écart mesuré entre ProbaLab et le concurrent de référence sur un domaine donné
- **Deep / Medium** : profondeur d'investigation (Deep = analyse approfondie, Medium = confirmation/infirmation rapide)
- **Pivot** : refonte en cours (`feat/pivot-probas-sportives`) — repositionnement "Spécialiste probabilités sportives" avec picks Safe/Fun/Value

### C. Concurrents cibles pour le benchmark

| Segment | Concurrents prioritaires |
|---|---|
| Tipsters foot | Forebet, Infogol (xG), PredictZ, StatArea |
| Pro value betting | RebelBetting, Trademate Sports, Pinnacle CLV, BetBurger |
| Grand public foot | SofaScore Predictions, OneFootball, Opta stats |
| US/NHL | Action Network, DraftKings Sportsbook predictions, MoneyPuck (NHL) |

### D. Risques de l'audit lui-même

| # | Risque | Mitigation |
|---|---|---|
| AR1 | Audit devient trop académique, pas actionnable | Section 5 P0/P1/P2 dans chaque annexe + roadmap synthétique |
| AR2 | Scoring trop généreux par complaisance | Règles anti-inflation §7 + comparaison explicite vs leader |
| AR3 | Benchmark biaisé par info publique limitée | Déclarer explicitement les limites §8 |
| AR4 | Audit long, owner perd le fil | Livraison par batches avec points d'arrêt |
| AR5 | Évaluation pivot influencée par l'existence du design doc | Chercher activement les angles morts, inclure option STOP/PAUSE |
