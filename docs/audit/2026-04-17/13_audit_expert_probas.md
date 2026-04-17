# 13 — Audit Expert Probabilités Sportives

> **Auteur** : Claude Opus 4.7 (expert mode)
> **Date** : 2026-04-17
> **Objectif** : Challenger le système de calcul de probabilités ProbaLab avec un regard externe d'expert en modélisation sportive, comparer à l'état de l'art (Pinnacle, Dixon-Coles, ELO, FiveThirtyEight SPI), et répondre à la question owner : _"est-ce que mon modèle vaut quelque chose ou je vends du vent ?"_

---

## Executive summary

- **Le modèle stats (Dixon-Coles + ELO + contexte) est solide sur le papier** : implémentation académiquement correcte, fixes appliqués (rho continu, draw calibration itérative, grid=10, leçons 1-4, 49-54). On est en ligne avec la littérature (Dixon & Coles 1997, Koopman & Lit 2015).
- **Mais le pipeline est contaminé par le marché** : les cotes sont utilisées à la fois comme benchmark (OK) *et* comme feature dans XGBoost (`market_home_prob`, `market_draw_prob`, `market_away_prob`, etc. dans `FEATURE_COLS` ligne 394-399). C'est un mélange qui crée un *circular reasoning* partiel — l'ensemble ML apprend le marché, le blend stats le réintègre à 20-60 %, puis vous comparez au marché pour détecter des value bets. Mathématiquement vous ne pouvez pas beaucoup le battre.
- **Trois bugs documentés affaiblissent les métriques reportées** : eval_set leakage (corrigé récemment), sample_weight CV ignoré (corrigé leçon 50), Bayesian shrinkage degenerate (corrigé leçon 49). La leçon 53 révèle un problème plus grave et **toujours actif** : _"le signal bookmaker (52-55 % accuracy) ne pèse que 21 % du résultat final"_ — mais les poids par défaut dans `constants.py` n'ont pas changé (`WEIGHT_MARKET = 0.20`).
- **Aucun CLV mesuré publiquement** : `backtest_clv.py` existe mais n'est pas en cron, pas de timeline persistée. Impossible aujourd'hui de dire "ProbaLab a +1.5 % CLV vs Pinnacle closing". Sans CLV > 0, vendre 14,99 €/mois = promettre un edge que vous ne pouvez pas prouver.
- **Verdict global** : produit sérieusement construit techniquement, **mais à la date de l'audit, il n'y a aucune preuve chiffrée qu'il bat le marché**. C'est un modèle "honnête" avec des pipelines défendables, pas un modèle avec un edge démontré. Le SaaS est viable si vous ajustez le pitch marketing (transparence + pédagogie + bankroll mgmt > "picks gagnants") ou si vous fixez 5 choses prioritaires listées en §6.

**Score global : 5.5/10**. Détail en §7.

---

## 1. Architecture globale — cartographie et état de l'art

### 1.1 Ce qui est réellement branché

Le système annoncé "70 % stats / 30 % IA" est **faux dans le code actuel** — c'est du marketing. En pratique :

1. **Couche statistique** (`src/models/stats_engine.py:2039-2756` — `analyze_match`)
   - Dixon-Coles Poisson (rho continu calibré par ligue, grid 10×10)
   - ELO interne (K-factor par ligue, home advantage par ligue, decay exponentiel)
   - 50+ features contextuelles (forme courte+longue, repos, congestion, stakes, H2H, injuries VORP, arbitre, météo)
   - Blend adaptatif Poisson/ELO/Market : `(0.55, 0.25, 0.20)` par défaut, `(0.25, 0.15, 0.60)` si has_odds + has_ml (`stats_engine.py:130-142` — `_get_blend_weights`)

2. **Couche ML XGBoost** (`src/models/ml_predictor.py`)
   - 9 modèles : xgb_1x2, xgb_btts, xgb_over05/15/25, xgb_total_goals, ensemble_1x2/btts/over25 (stacking XGB+LGBM+LogReg)
   - Calibration isotonic per-class post-training (`train.py:419-434`)
   - Features : 43 colonnes dont **6 features marché** (`constants.py:394-399`)
   - Blend final après stats : `final = 0.5 * stats + 0.5 * ML` (`stats_engine.py:2458-2464`)

3. **"Couche IA Gemini 30 %"** → **désactivée en prod**
   - `prediction_blender.py:137` : `if not META_LEARNER_ENABLED or WEIGHT_AI <= 0: return False`
   - `constants.py:212` : `META_LEARNER_ENABLED: bool = False`
   - `prediction_blender.py:288` : `logger.debug("Phase 2 meta-learner inactive — using pure stats")`
   - Gemini produit du texte narratif (`analysis_text`) et des features qualitatives stockées pour entraînement futur, mais **n'influence pas les probas**
   - **Verdict** : le 30 % IA n'existe pas dans les probabilités vendues. C'est de l'habillage narratif.

### 1.2 Cohérence avec l'état de l'art

| Composant | Implémentation | Conformité littérature |
|---|---|---|
| Dixon-Coles rho | Continu, per-league, re-scalé par xG total (`stats_engine.py:203-217`) | ✓ Conforme DC 1997, amélioration DC (rho adaptif pas dans l'original mais documenté Constantinou & Fenton 2012) |
| Team strengths | Itération bayésienne 10 passes avec prior weight=3 (`stats_engine.py:428-470`) | ✓ Approche Maher/Dixon-Coles avec smoothing bayésien — correct |
| ELO | Logistic standard + log(goal_diff) multiplier (`stats_engine.py:746`) | ✓ Équivalent FiveThirtyEight SPI / eloratings.net |
| Draw calibration itérative | 3 passes, ±20 % cap, convergence à 0.5 % (`stats_engine.py:244-255`) | ✓ Améliore Dixon-Coles (connu pour sous-prédire les nuls en Serie A/CL) |
| Injuries VORP | Position-aware replacement-level baseline (`src/models/injury_vorp.py`) | ✓ Approche sport analytics moderne (basketball VORP adapté) |
| Form with SOS | Exponential decay + opponent ELO multiplier (`stats_engine.py:912-993`) | ✓ Correct — correspond à l'approche Constantinou |
| Calibration | Bayesian shrinkage n<200 + Platt 100+ + Isotonic 500+ (`calibrate.py`) | ✓ Best practice — Platt (1999) + Isotonic (Zadrozny & Elkan 2002) |

**Verdict §1** : l'architecture statistique est de qualité **académique**. Le code de `stats_engine.py` (2756 lignes) est long, documenté, vectorisé (numpy outer + tril/triu) et implémente correctement Dixon-Coles adapté. **C'est la partie honorable du système.**

---

## 2. Qualité des probabilités

### 2.1 Features utilisées

`FEATURE_COLS` (`constants.py:374-432`) contient **43 features**. C'est dans la moyenne (Pinnacle utilise 150+, FiveThirtyEight SPI ~30 exposées, publications Koopman 40-80).

**Forces** :
- xG par équipe (`xg_home`, `xg_away`) + `xg_per_shot` (qualité du tir, très prédictif)
- ELO + elo_diff + `elo_diff_squared` (non-linéarité capturée)
- Forme courte 6 matchs + longue 12 matchs + `form_diff` (interaction explicite — best practice)
- Stakes, H2H_total_matches, injury_count, congestion_30d — contextuelles
- Taux historiques de ligue (`league_avg_btts_rate`, `league_avg_over25_rate`)

**Faiblesses** (features absentes mais standards dans la littérature) :
- **xG against** par équipe (seulement xG_for/shot) — manque symétrie défensive
- **Shots against per game** (métrique Pinnacle) — absent
- **Set pieces conversion rate** — non modélisé
- **Pace / tempo** (duels, pressing, PPDA) — absent
- **Starting XI signal** — le VORP injuries capture une partie mais pas la rotation tactique
- **Referee bias** (par équipe, pas seulement penalty_bias global)
- **Travel distance / altitude** — absent (pertinent UCL)
- **Transfer window / new signing adaptation** — absent

**Features suspectes** :
- `home_stakes`, `away_stakes` : multiplicateur calculé *dans* stats_engine puis réinjecté dans FEATURE_COLS. Circularité interne acceptable mais le ML va apprendre à l'amplifier.
- **`market_home_prob`, `market_draw_prob`, `market_away_prob`, `market_btts_prob`, `market_over25_prob`, `market_over15_prob`** : **6 features qui sont les cotes transformées** (voir §3).

### 2.2 Calibration

État du code :
- **Platt scaling** (`calibrate.py:101-140`) : activé si n ≥ 100, paramètres `(a, b)` stockés en DB, sanity check (|a|>20 ou |b|>20 → skip).
- **Isotonic regression** (`calibrate.py:142-176`, `427-488`) : activé si n ≥ 500, cache mémoire TTL 1 h, re-fit à la volée.
- **Bayesian shrinkage 1X2** (`calibrate.py:517-573`) : conditionnel n<200, shrinkage `= n/(n+50)`. **Corrigé leçon 49** — le bug précédent tirait les probas vers 45/27/28 même avec 400+ samples.
- **Post-training XGBoost** (`train.py:419-456`) : isotonic per class sur un calibration set (20 % du train), test log_loss avant/après, discard si dégradation.

C'est **au niveau industrie** (Platt + Isotonic + shrinkage + per-class, avec guard anti-overwrite). Points à améliorer :
- Pas de **Beta calibration** (Kull et al. 2017 — meilleure alternative à Platt pour sparse data).
- Pas de **conformal prediction** (intervalles de confiance) — standard émergent dans MLOps 2024-2026.
- Calibration **globale** sauf pour Isotonic — pas de per-league par défaut ce qui laisse le biais Serie A non corrigé même avec beaucoup de samples.

### 2.3 Règles de blending

**Couche 1** : Poisson + ELO + Market (`stats_engine.py:108-142`, `2272-2321`) — `_get_blend_weights` :
- Defaults : `(Poisson=0.55, ELO=0.25, Market=0.20)` (`constants.py:196-198`)
- Si has_odds + has_ml : `(0.25, 0.15, 0.60)` — le marché reprend dominance
- Si has_odds only : `(0.35, 0.20, 0.45)`
- Sans market : `(0.65, 0.35, 0.0)`

**Couche 2** : stats ⊕ ML (`stats_engine.py:2458-2464`) :
- `final = 0.5 * (blend L1) + 0.5 * ML_prediction`
- `WEIGHT_STATS_VS_ML = 0.50, WEIGHT_ML = 0.50` (`constants.py:215-216`)

**Couche 3** : stats ⊕ AI Gemini :
- **Désactivée** (`META_LEARNER_ENABLED = False`). Le 30 % annoncé n'existe pas.

**Justification des 70/30 stats/IA ?** Aucune. C'est un ratio marketing qui ne correspond à aucun test A/B documenté. Le code montre qu'en production, c'est 100 % stats (+ ML qui utilise le market). Leçon 35 :
> _"The current meta-learner only uses 5 Gemini AI features which tend to be very similar across matches, producing near-identical probabilities."_

C'est un artefact d'ingénierie avancé mais inactif. **Honnêteté marketing recommandée : annoncer "100 % modèle statistique + analyse IA narrative" plutôt que "70 % stats, 30 % IA".**

### 2.4 Normalisation

- **1X2 normalisé à 100 %** : `p_away = 100 - p_home - p_draw` (`stats_engine.py:299-301, 2578-2580`). Force sum=100 par design (leçon 2 corrigée).
- **Overround removal** : oui, `odds_to_probs` (`stats_engine.py:1491-1540`) divise chaque proba implicite par `overround` pour retirer le vig.
- **Clamping post-pipeline** (`clamp_probabilities`, ligne 1951-2036) : floors/ceils [5, 72] sur 1X2, redistribution itérative (3 passes), monotonicité Over lines forcée (O3.5 ≤ O2.5 ≤ O1.5 ≤ O0.5), cohérence BTTS ≤ Over 1.5.

C'est propre. Mieux que beaucoup de tippers amateurs.

### 2.5 Anti data leakage

- `tests/test_train_no_leakage.py` : **test AST** qui grep les appels `.fit(eval_set=...)` et refuse `X_test`. Excellent pattern de régression. Confirme que leçon 10 (eval_set leakage corrigé) est protégée.
- `tests/test_train_sample_weight.py` : **test AST** qui vérifie que `cross_val_score` ne reçoit pas `params={"sample_weight": ...}` (bug leçon 50). Excellent.
- `train.py:327-330` : imputer fit sur train split seulement (leçon 12). OK.

**Autre leakage potentiel non détecté** :
- `teams_stats` et league strengths (`stats_engine.py:334-492`) sont calculés sur **toute la saison FT** — y compris les matchs futurs par rapport à un match en train. C'est un leakage temporel subtil : quand on entraîne sur la saison 2024-25 et qu'on backtest le match de septembre, les forces d'équipe incluent l'info de mai 2025. **À vérifier en priorité**. Indicateur : si le Brier CV sur train paraît irréaliste (< 0.18 sur 1X2), c'est le symptôme.

---

## 3. Le rôle des cotes bookmakers — la question qui fâche

### 3.1 Verdict net : **usage hybride, et c'est un problème**

Les cotes sont utilisées **simultanément à trois niveaux** :

**A. Comme BENCHMARK** (bonne pratique) :
- `backtest_clv.py` compare model prob vs closing line implied prob
- `apply_calibration` utilise prediction_results (résultats réels) pour calibrer
- **Usage sain** — c'est ce que fait Pinnacle/RebelBetting

**B. Comme FEATURE d'entrée du ML** (circular reasoning) :
- `FEATURE_COLS` lignes 394-399 (`constants.py`) :
  ```python
  "market_home_prob", "market_draw_prob", "market_away_prob",
  "market_btts_prob", "market_over25_prob", "market_over15_prob",
  ```
- Injectées dans `build_feature_vector` (`ml_predictor.py:164-185`)
- Construction dans `build_data.py:795-806` à partir de `fixture_odds`
- Fallback à 33.0 quand manquant (`ml_predictor.py:229-230`) — c'est même un prior uniforme

**C. Comme TERME DU BLEND LINÉAIRE** (`stats_engine.py:2294-2309`) :
- `final = w_poisson * P_poisson + w_elo * P_elo + w_market * P_market`
- avec `w_market = 0.20` par défaut, jusqu'à `0.60` quand has_odds+has_ml

### 3.2 Analyse des trois usages

- Usage A (benchmark) : **sain**.
- Usage C (blend) : **défendable** si les poids sont corrects. Mais 20 % par défaut, c'est trop peu (cf. leçon 53). Paradoxe : constants.py n'a pas été mis à jour malgré la leçon documentée.
- Usage B (feature ML) : **dangereux**. Deux effets :
  1. **Feature importance dominée par market_*** (risque documenté dans `feature_audit.py:82-88` : _"CRITICAL_LEAKAGE si market_share > 50 %"_). Le module existe pour détecter ce cas, mais n'est pas branché en cron.
  2. **Circularité d'évaluation** : votre ML apprend à reproduire le marché, votre blend le combine à Poisson, puis vous comparez au marché pour trouver du value. Résultat : les "value bets" que vous détectez sont majoritairement dans les cas où Poisson diverge fortement du marché — mais Poisson seul n'a aucun edge vs Pinnacle. Vos alertes value sont essentiellement du bruit de modèle stats vs efficient market.

### 3.3 Ce que font les modèles professionnels

- **Pinnacle** : N'utilise PAS les cotes concurrentes dans son modèle. Leur "market" c'est le flux de mises agrégé. Ils fabriquent la cote.
- **RebelBetting** : utilise la closing line de Pinnacle comme **ground truth** post-hoc pour mesurer CLV, **jamais comme feature**. Ils construisent indépendamment, puis arbitrent.
- **FiveThirtyEight SPI** : feature set 100 % stats + résultats, zéro cote bookmaker.
- **Koopman & Lit 2015, Constantinou 2019** : modèles purement statistiques, cotes utilisées uniquement pour backtest.

### 3.4 Recommandation §3

**Retirer les 6 features market_*** du ML entraînement, ou au minimum **entraîner deux modèles parallèles** :
- `xgb_1x2_pure` : sans features market
- `xgb_1x2_market` : avec features market

Comparer les Brier sur un holdout. Si `xgb_1x2_pure` est proche (±0.005), **migrer en prod** — il aura un vrai CLV. Sinon, c'est la preuve que votre modèle n'apprend rien d'indépendant, et le pitch "modèle propriétaire" devient du vent.

**Garder l'usage C (blend)** mais monter `WEIGHT_MARKET` à 0.35-0.45 par défaut (leçon 53 documentée, non appliquée).

---

## 4. Benchmark vs concurrence

### 4.1 Comparaison conceptuelle

| Critère | ProbaLab | Pinnacle closing | Dixon-Coles pur | ELO pur | FiveThirtyEight SPI |
|---|---|---|---|---|---|
| Brier 1X2 attendu | **0.21-0.23** (estimation) | ~0.185 | ~0.22 | ~0.23 | ~0.20 |
| Log Loss | ~1.00 (estimation) | ~0.95 | ~1.03 | ~1.06 | ~0.99 |
| ECE | <0.05 si calibration active | <0.02 | ~0.06 | ~0.08 | ~0.04 |
| CLV vs Pinnacle closing | **Inconnu** (non mesuré) | 0 (référence) | négatif | négatif | légèrement négatif |
| Feature count | 43 | 150+ | 4-8 | 2-3 | ~30 |
| Calibration | Platt + Isotonic + Shrinkage | Propriétaire (agrégat mises) | Rien | Rien | Isotonic |
| Retraining | Manuel / cron weekly | Continuous | N/A | Continuous | Weekly |

### 4.2 Lecture honnête

Vous êtes **à peu près au niveau Dixon-Coles académique + 10-15 %** grâce au blending ML + calibration. C'est légitime et respectable. **Vous êtes loin de Pinnacle** — mais personne ne bat Pinnacle closing, c'est le gold standard "unbeatable" en dehors de quelques pros ayant des features alternatives (xG scraping propriétaire, CHAOS models, etc.).

**Le vrai benchmark pour un SaaS à 14,99 €** : battre **l'opening line** (pas la closing) sur les matchs de fin de semaine en ligues majeures, avec CLV mesuré rigoureusement. Personne ne sait aujourd'hui si vous faites ça parce que `backtest_clv.py` n'est pas branché en cron et aucune timeline CLV n'est persistée (audit §3 `03_monitoring_ml.md`).

### 4.3 Métriques actuellement dans le code

Lisez `brier_monitor.py:30-34` :
```python
BRIER_THRESHOLDS = {
    "1x2": {"excellent": 0.19, "good": 0.21, "acceptable": 0.23},
    "binary": {"excellent": 0.20, "good": 0.22, "acceptable": 0.25},
}
```

Les seuils sont **corrects vs la littérature**. Reste à mesurer où vous tombez réellement. **Il faut lancer `python -m src.monitoring.brier_monitor` en prod et extraire les valeurs**. Sans ces chiffres, le reste de l'audit reste spéculatif.

---

## 5. Test critique : "mâcher le travail avec les cotes"

### 5.1 L'hypothèse naïve

> _"Je prends les cotes Pinnacle, je convertis en proba implicite, je retire l'overround, j'ai déjà 100 % du travail fait."_

**Mathématiquement, c'est VRAI pour 95 % des matchs.** Les cotes Pinnacle closing sont empiriquement la meilleure estimation disponible (Levitt 2004, Forrest & Simmons 2005, Spann & Skiera 2009). Les tentatives de battre ce signal systématiquement ont échoué dans la littérature académique.

### 5.2 Pourquoi c'est FAUX comme stratégie marketing

Si vous vendez "nos probabilités ≈ overround-removed Pinnacle closing", trois problèmes :
1. **Aucun edge value** — votre ROI attendu net de vig et de frais plateforme est négatif (≈ -3 % sur soft books, -2 % sur Pinnacle).
2. **Aucune différenciation** — l'utilisateur peut ouvrir Oddsportal gratuitement.
3. **Pas défendable à 14,99 €/mois** — c'est un info produit, pas un edge produit.

### 5.3 Pourquoi c'est IMPORTANT d'avoir un modèle indépendant

Le **seul** intérêt mathématique d'un modèle indépendant c'est d'identifier **les inefficiences ponctuelles** :
- Marché "soft" (bookmakers tier-2/3) qui n'ont pas la liquidité Pinnacle → edge 1-4 %
- Matchs mineurs (L2, coupes) où le marché Pinnacle est moins "sharp"
- Réactions émotionnelles du public (matchs de gala, derbys, effet nom)
- Blessures tardives pas encore intégrées dans la ligne
- Conditions météo extrêmes sous-pondérées

Pour détecter ça, il faut **strictement**:
1. Un modèle qui ne voit PAS les cotes (sinon il apprend le marché et perd l'edge).
2. Un backtest CLV positif sur 500+ matchs.
3. Un filtre EV+ dynamique (edge > 3-5 %, Kelly fractional).

**ProbaLab fait (3) bien** (`stats_engine.py:1748-1775` — fractional Kelly, MIN_VALUE_EDGE=0.05). **Ne fait pas vraiment (1)** (les 6 features market_*). **Ne peut pas documenter (2)** sans brancher backtest_clv.

### 5.4 Références académiques

- **Levitt, S. (2004)** — _Why are gambling markets organised so differently?_ — montre que les bookmakers ne sont pas des market-makers neutres, ils exploitent les biais.
- **Forrest, D., Goddard, J., Simmons, R. (2005)** — _Odds-setters as forecasters: The case of English football_ — même avec vig, les cotes surperforment les modèles experts sur le long terme.
- **Koopman & Lit (2015)** — _A dynamic bivariate Poisson model for analysing and forecasting match results in the English Premier League_ — un modèle purement statistique bien fait n'atteint pas la closing line mais s'en rapproche à <2 %.
- **Constantinou & Fenton (2012, 2013)** — Bayesian networks pour football forecasting, avec comparaison explicite vs bookmakers.

### 5.5 Stratégie recommandée

**Pitch honnête qui tient debout** :
> _"Nous construisons un modèle Dixon-Coles étendu, calibré, indépendant du marché, qui identifie les 2-5 % de matchs par semaine où une cote bookmaker soft diverge de notre estimation d'au moins 5 %. Nous mesurons notre CLV vs Pinnacle closing en continu et publions cette métrique. ROI moyen utilisateur discipliné : +2 à +5 % par saison sur bankroll. Pas de miracle."_

Ça **peut** justifier 14,99 €/mois **si** :
- CLV > 0 documenté (pas encore le cas).
- Transparence totale sur la méthodo.
- Bankroll management + Kelly fractional en feature produit (c'est déjà le cas).

---

## 6. Recommandations concrètes

Classées par ratio impact/effort.

### Quick wins (< 1 semaine)

**[Q1] Mesurer le CLV réel sur 90 jours — 4 heures, impact CRITIQUE**
- Brancher `backtest_clv.run()` en cron quotidien (`worker.py`).
- Créer `model_health_log` avec clv_best_mean, brier_1x2, ece_1x2 par jour.
- Ajouter tab "Santé du modèle" sur le dashboard admin.
- **Sans cette donnée, toute discussion produit est spéculative**. C'est le #1 sine qua non.

**[Q2] Monter `WEIGHT_MARKET` et rebalancer — 2 heures, impact ÉLEVÉ**
- `constants.py:196-198` : passer à `(Poisson=0.40, ELO=0.20, Market=0.40)`.
- Rerun backtest_clv, comparer vs ancien blend.
- Appliquer leçon 53 qui est documentée depuis 10+ jours sans action.

**[Q3] Brancher `feature_audit.py` en cron — 2 heures, impact MOYEN**
- Vérifier que `market_share_pct` reste < 30 % par modèle.
- Alerte Telegram si CRITICAL_LEAKAGE.
- Permet de voir objectivement si vos XGBoost "apprennent" le marché ou autre chose.

**[Q4] Documenter honnêtement le "70 % stats / 30 % IA" — 1 heure, impact RÉPUTATION**
- Le 30 % IA n'existe pas (`META_LEARNER_ENABLED=False`). Marketing mensonger à terme.
- Remplacer par "Modèle statistique Dixon-Coles étendu + analyse narrative IA" sur le site.

### Moyen terme (1 mois)

**[M1] Modèle XGBoost pure sans features market — 2 jours, impact CRITIQUE pour l'edge**
- Fork de `FEATURE_COLS` sans les 6 features market_*.
- Entraîner `xgb_1x2_pure`, comparer Brier / CLV vs actuel.
- Si gap < 0.005 Brier, **migrer en prod**. Sinon, vous tenez la preuve que votre ML ne peut pas fonctionner sans marché, et c'est une info produit capitale (downgrade du pitch).

**[M2] Calibration per-league systématique — 3 jours, impact MOYEN**
- Aujourd'hui calibration globale par défaut. Forcer per-league pour les 8 ligues foot principales dès que n_league ≥ 200.
- Serie A, CL notoirement sous-prédites en nuls — calibration per-league corrige.

**[M3] Feature drift KS test — 2 jours, impact MOYEN**
- `scipy.stats.ks_2samp` sur chaque feature training vs derniers 30 jours prod.
- Alerte si > 3 features avec p < 0.01.
- Mitige le risque que vos fetchers introduisent un biais silencieux (cf. leçon 68 API-Sports).

**[M4] Ajouter xG against, shots against, pace — 5 jours, impact ÉLEVÉ**
- Ces features sont dans `match_team_stats` mais pas dans FEATURE_COLS.
- Augmenter de 43 → 55-60 features.
- Refit XGBoost, mesurer delta Brier. Attendu : -0.003 à -0.008.

### Long terme (3 mois)

**[L1] Benchmark rigoureux vs baselines — 2 semaines, impact PRODUIT**
- Dataset 5 saisons (2020-2025), 8 ligues, ~20 000 matchs.
- Implémenter 4 baselines : DC pur, ELO pur, FTE-like SPI, Market-closing.
- Tableau Brier/LogLoss/ECE/CLV sur holdout 2024-2025 (split temporel strict).
- Publier les résultats **sur le site et le dashboard utilisateur**. C'est ce qui justifie 14,99 €.

**[L2] Model registry + versioning — 1 semaine, impact RISQUE**
- Hash SHA256 + git SHA + timestamp sur chaque modèle ml_models.
- Rollback endpoint `POST /api/admin/rollback-model`.

**[L3] Bayesian Network / DBN pour causal inference — 4 semaines, impact LONG TERME**
- Approche Constantinou & Fenton 2012 : DAG explicite (forme → morale → résultat) plutôt que XGBoost black box.
- Permet d'exploiter des signaux que le marché n'intègre pas (transferts tardifs, crises internes).
- C'est le seul path réaliste pour un edge durable > 2 % vs closing line.
- Haut risque, haute récompense.

---

## 7. Score global et justification

### 7.1 Score : **5.5 / 10**

| Dimension | Note | Commentaire |
|---|---|---|
| Architecture statistique | 8/10 | Dixon-Coles correct, ELO propre, 43 features, calibration Platt+Isotonic+Shrinkage. Solide. |
| Indépendance vs marché | 3/10 | 6 features market_* dans XGBoost. Le blend ultime contient 20-60 % de marché. Pas un modèle "propriétaire". |
| Qualité ML pipeline | 6/10 | TimeSeriesSplit ✓, sample_weight corrigé ✓, calibration post-training ✓. Manque: model versioning, feature drift, modèle pure sans market. |
| Calibration et probas | 8/10 | Platt + Isotonic + Bayesian shrinkage + clamping + normalisation = best practice. |
| Monitoring prod | 4/10 | Modules écrits (brier_monitor, backtest_clv, feature_audit) mais **non branchés en cron**. Le gaspillage le plus triste du projet. |
| Honnêteté du pitch | 3/10 | "70 % stats / 30 % IA" est faux (`META_LEARNER_ENABLED=False`). Pas de CLV publié. |
| Tests anti-leakage | 7/10 | Tests AST pour eval_set et sample_weight, excellent. Leakage subtil (team strengths future-leak) non couvert. |
| Ensemble design | 6/10 | Stacking 3 learners + meta LogReg = conforme littérature. Mais `WEIGHT_ML = 0.50` sans ablation study. |
| Potentiel / évolutivité | 7/10 | Codebase propre, CLAUDE.md clair, 30+ leçons documentées, pyproject propre. Bonne fondation. |

**Moyenne pondérée** (selon importance pour un SaaS de prédictions) ≈ **5.5/10**.

### 7.2 Verdict synthétique en 2 phrases

**ProbaLab est un modèle de prédiction sportive construit avec sérieux académique mais dont l'indépendance vs marché est compromise par 6 features bookmaker dans XGBoost et par l'absence de mesure CLV en production.** Pour justifier 14,99 €/mois, deux options : (a) prouver un CLV > 0 en branchant le monitoring et en retirant les features market (effort 2-4 semaines, résultat incertain mais honnête), ou (b) pivoter le pitch vers _"meilleur outil de calibration + bankroll mgmt grand public"_ plutôt que _"picks gagnants"_ (effort marketing, résultat sûr mais volume limité).

### 7.3 Tableau final Pinnacle / DC / ELO / ProbaLab

| Métrique | Pinnacle closing | Dixon-Coles pur | ELO pur | **ProbaLab actuel** | ProbaLab post-fix |
|---|---|---|---|---|---|
| Brier 1X2 estimé | 0.185 | 0.22 | 0.23 | 0.21-0.23 | 0.20-0.215 |
| Log Loss 1X2 | 0.95 | 1.03 | 1.06 | ~1.00 | 0.97-0.99 |
| ECE | <0.02 | 0.06 | 0.08 | 0.03-0.05 | 0.02-0.04 |
| CLV vs closing | 0 (ref) | -2 % | -3 % | Inconnu | Objectif +0.5 à +1.5 % |
| Feature count | 150+ | 4-8 | 2-3 | 43 | 55-60 (post-M4) |
| Independent from odds | N/A | Oui | Oui | **Non** | Oui (post-M1) |
| Monitoring prod | N/A | N/A | N/A | Partiel | Complet (post-Q1) |

---

## Annexe — extraits de code parlants

### A. Les features suspectes (circularité marché)

`src/constants.py:374-432` — **les 6 lignes qui changent tout** :
```python
FEATURE_COLS: list[str] = [
    # [...]
    "market_home_prob",    # ligne 394
    "market_draw_prob",    # ligne 395
    "market_away_prob",    # ligne 396
    "market_btts_prob",    # ligne 397
    "market_over25_prob",  # ligne 398
    "market_over15_prob",  # ligne 399
    # [...]
]
```

### B. Le blend final (poids contestables)

`src/constants.py:196-216` :
```python
WEIGHT_POISSON: float = 0.55
WEIGHT_ELO: float = 0.25
WEIGHT_MARKET: float = 0.20    # Leçon 53 dit "devrait être dominant", pas fait
# [...]
WEIGHT_STATS: float = 0.70
WEIGHT_AI: float = 0.30
META_LEARNER_ENABLED: bool = False  # → le 30% IA n'existe pas
```

### C. Le bon design — clamp_probabilities

`src/models/stats_engine.py:1951-2036` — gestion propre des floors/ceils/redistribution/monotonicité. À souligner, c'est rare de voir ce niveau de rigueur dans un produit SaaS.

### D. Le vrai test anti-leakage

`tests/test_train_no_leakage.py:30-39` — le test AST qui refuse `X_test` dans `eval_set`. **Pattern à garder et étendre**.

### E. Le monitoring qui dort

`src/monitoring/brier_monitor.py:281-379` — code complet, seuils corrects, reliability diagrams, drift detection. **Tout est écrit. Rien n'est branché en cron** (voir audit `03_monitoring_ml.md` §2.2 P0).

### F. Le fallback Poisson silencieux (leçon 72)

`src/nhl/ml_models.py:81-139` — après leçon 72, la loaded flag est bien gérée. Pattern à appliquer aussi aux modèles foot.

---

**Dernier mot brutal** : vous avez la matière première d'un bon produit. Le code stats est de qualité. Mais tant que Q1 (mesure CLV réelle) n'est pas fait, vous vendez un produit dont **personne — ni vous ni le client — ne peut démontrer qu'il a un edge**. C'est la première chose à régler. Tout le reste est secondaire.
