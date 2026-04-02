# PROMPT D'AUDIT — Système de Probabilités Football

> **Objectif** : Audit exhaustif de la cohérence mathématique, de la qualité probabiliste et de la robustesse du pipeline de prédiction. Zéro approximation. Zéro hallucination. Chaque constat doit être prouvé par le code source.

---

## CONTEXTE POUR L'AUDITEUR

Tu audites un système de prédiction football hybride composé de :
- **Poisson Dixon-Coles** (per-league ρ + draw calibration)
- **ELO dynamique** (K-factor par ligue, decay temporel)
- **Ensemble ML** (XGBoost + LightGBM + LogReg stacking)
- **Ajustements contextuels** (forme, repos, enjeux, blessures, arbitre, météo, H2H)
- **Calibration** (Platt / Isotonic)
- **Gemini AI** (narratif, 30% du blend final)
- **Kelly Criterion** (gestion bankroll)

Pipeline complet :
```
xG brut → ajustements contextuels → xG ajusté
→ Poisson(55%) + ELO(25%) + Market(20%) = Blend 1
→ Blend 1(60%) + ML(40%) = Blend 2
→ + Stakes draw boost + Euro draw boost
→ Soft cap 80% → Calibration BTTS/Over → Clamping
→ Stats(70%) + Gemini(30%) = Proba finale
```

**Fichiers clés** :
- `src/models/stats_engine.py` — Moteur principal
- `src/models/calibrate.py` — Calibration Platt/Isotonic
- `src/models/ml_predictor.py` — Prédictions ML
- `src/models/ensemble.py` — Stacking ensemble
- `src/training/train.py` — Entraînement
- `src/constants.py` — Hyperparamètres
- `src/brain.py` — Orchestration Gemini
- `src/bankroll.py` — Kelly + bankroll

---

## PARTIE 1 — COHÉRENCE MATHÉMATIQUE FONDAMENTALE

### 1.1 Normalisation des probabilités

**Vérifie rigoureusement que la somme P(H) + P(D) + P(A) = 100% à CHAQUE étape du pipeline**, pas seulement à la fin. Points de contrôle obligatoires :

1. **Sortie de `poisson_grid()`** : Après la correction Dixon-Coles et la draw calibration, la grille est-elle bien renormalisée ? Le `grid /= grid.sum()` après draw calibration garantit-il que `proba_home + proba_draw + proba_away == 100` exactement, ou y a-t-il une erreur d'arrondi accumulée par les `round()` ?

2. **Sortie de `get_elo_probs()`** : La formule redistribue `draw_prob` depuis `p_home` et `p_away` proportionnellement. Mais `p_home` est calculé via `elo_expected(home_elo + 65, away_elo)` et `p_away = 1 - p_home`. Ensuite `remaining = 1 - draw_prob` puis multiplication. Vérifie que `round(p_home*100) + round(draw*100) + round(p_away*100)` peut donner 99 ou 101 à cause des arrondis. Comment c'est géré ?

3. **Blend Poisson+ELO+Market** : Après la pondération 55/25/20, la normalisation `total = H+D+A; H = round(H/total*100)` puis `A = 100 - H - D` force la cohérence. Mais est-ce que `final_away` peut devenir négatif dans des cas extrêmes (ex: H=72, D=30 → A=-2) ?

4. **Blend Stats+ML (60/40)** : Même question — après le blend, y a-t-il une renormalisation explicite ? Ou seulement `A = 100 - H - D` ?

5. **Stakes draw boost + Euro draw boost** : Le boost ajoute des points au draw et les retire proportionnellement de H et A. Vérifie qu'après deux boosts successifs, les probas restent dans [0, 100] et somment à 100.

6. **Soft cap 80%** : Si `final_home > 80`, l'excès est distribué 40% au draw et 60% implicitement à away. Vérifie que la redistribution maintient la somme à 100 et que aucune proba ne devient négative.

7. **Blend Stats(70%)+Gemini(30%)** : Comment Gemini retourne-t-il ses probas ? Sous quel format ? Y a-t-il une validation que les probas Gemini somment à 100 avant le blend ?

### 1.2 Grille de Poisson — Rigueur mathématique

1. **Troncature à MAX_GOALS_GRID=7** : La distribution de Poisson a un support infini. Tronquer à 7 buts crée une perte de masse. Quantifie cette perte pour différents xG :
   - xG=0.8 : perte ≈ 0.0001% (négligeable)
   - xG=2.5 : perte ≈ 0.2%
   - xG=4.0 (XG_CEIL) : perte ≈ 2.3%
   La renormalisation `grid /= grid.sum()` compense, mais vérifie que pour xG=4.0 la correction ne distord pas significativement la forme de la distribution (les ratios entre cellules changent-ils ?).

2. **Dixon-Coles correction — Positivité** : La correction `1 - λ_h × λ_a × ρ` pour la cellule (0,0) peut-elle devenir négative ? Avec ρ=-0.17 (CL) et xG_h=4.0, xG_a=4.0 : `1 - 4 × 4 × (-0.17) = 1 + 2.72 = 3.72`. OK, positif. Mais avec le scaling dynamique `rho × 0.7` pour xG>3.5, ρ devient -0.119, correction = 1 + 1.904 = 2.904. Toujours positif. Vérifie néanmoins tous les cas limites, en particulier cellule (1,0) : `1 + λ_a × ρ`. Si ρ=-0.17×1.3=-0.221 et xG_a=4.0 : `1 + 4 × (-0.221) = 0.116`. Positif mais très bas — est-ce réaliste ?

3. **Draw calibration — Boucle de rétroaction** : La correction draw utilise `target_draw / predicted_draw` bornée à [0.85, 1.15]. Si la draw calibration corrige fortement la diagonale, puis la renormalisation redistribue la masse, le draw rate final peut différer du target. Vérifie si une seule passe suffit ou s'il faudrait itérer.

4. **Scaling dynamique du ρ** : La transition linéaire entre xG<2.0 (×1.3) et xG>3.5 (×0.7) est-elle continue ? Y a-t-il un saut ou une discontinuité aux bornes ? Vérifie la formule d'interpolation exacte.

### 1.3 Modèle ELO — Exactitude

1. **Home advantage fixe à +65** : Ce bonus est identique pour toutes les ligues. Or l'avantage domicile varie fortement : ~60% en Turquie, ~52% en Bundesliga. Faut-il un `HOME_ADVANTAGE_BY_LEAGUE` ?

2. **Draw decay** : `draw_prob = base_draw × exp(-0.002 × elo_gap)`. Pour un écart ELO de 400 (typique Real Madrid vs promoted team) : `0.28 × exp(-0.8) = 0.28 × 0.449 = 0.126 = 12.6%`. Le clamp à 15% minimum s'active. Est-ce cohérent avec la réalité ? (Les matchs avec 400+ d'écart ELO ont environ 10-15% de draws historiquement.)

3. **Goal diff multiplier** : `log(|gd| + 1) + 1`. Pour gd=0 (draw) : log(1)+1 = 1.0. Pour gd=5 : log(6)+1 = 2.79. Vérifie que ce multiplicateur ne surestime pas les updates après des scores fleuves (peut déstabiliser les ratings).

4. **Decay temporel** : `exp(-0.001 × days)`. Pour 30 jours : facteur = 0.970. Pour 90 jours (intersaison) : 0.914. Pour 180 jours : 0.835. L'ELO perd 16.5% de son écart à 1500 après 6 mois d'inactivité. Est-ce approprié pour les équipes qui jouent peu (coupes nationales) ?

---

## PARTIE 2 — AJUSTEMENTS CONTEXTUELS

### 2.1 Multiplicateurs et effet composé

Les ajustements contextuels sont des **multiplicateurs** sur le xG :
```
xG_adj = xG_base × form × rest × h2h × weather × atk_injury × def_injury_adverse
```

**Problème potentiel critique** : L'effet composé. Si une équipe a :
- Mauvaise forme (0.85)
- Peu de repos (0.92)
- Blessures offensives (0.70)
- Pluie forte (0.93)
- H2H défavorable (0.94)

xG_adj = xG × 0.85 × 0.92 × 0.70 × 0.93 × 0.94 = xG × **0.450**

Un xG initial de 1.8 tomberait à 0.81. Avec le floor à 0.3, ça passe, mais la compression est MASSIVE. Vérifie :
1. Que le produit des multiplicateurs est borné de manière raisonnable (ex: jamais < 0.50 en produit total)
2. Que le XG_FLOOR (0.3) et XG_CEIL (4.0) ne masquent pas des déséquilibres importants
3. Qu'il n'y a pas de double comptage : la forme intègre-t-elle déjà les blessures récentes ? Le repos intègre-t-il déjà la congestion ?

### 2.2 Forme — Méthodologie

1. **Blending 70/30** (6 matchs / 12 matchs) : Le blend est-il appliqué AVANT ou APRÈS la conversion en multiplicateur ? Si c'est après : `factor = 0.70 × factor_short + 0.30 × factor_long`. Si c'est avant : `form_score = 0.70 × score_short + 0.30 × score_long` puis conversion en factor. La différence est non-triviale (composition non-linéaire).

2. **Strength of Schedule** : `sos_multiplier = opponent_elo / 1500`. Si un adversaire a 1200 ELO, son poids est 0.8. Si 1800, c'est 1.2. Cette correction est-elle suffisante ? 3 victoires contre des adversaires à 1200 (sos×0.8) donnent un form_score bien plus bas que 3 victoires à 1800 (sos×1.2), ce qui est correct.

3. **Plage de sortie** : `FORM_RANGE_LOW=0.85, FORM_RANGE_HIGH=0.30`. Le form_score [0,1] est mappé à un multiplicateur dans [0.85, 1.15]. Vérifie la formule de mapping exacte et qu'elle est bien linéaire.

### 2.3 Blessures — Impact

1. **Facteur d'attaque 0.70** minimum : Si un attaquant clé manque (>30% des buts), l'attaque de l'équipe est multipliée par 0.70. C'est ÉNORME — un xG de 2.0 tombe à 1.4. Vérifie si c'est empiriquement justifié ou si c'est trop sévère.

2. **Facteur de défense 1.35** maximum : L'adversaire bénéficie d'un boost de 35% sur son xG. Combiné avec d'autres facteurs favorables, ça peut exploser.

3. **Pas de distinction titulaire/remplaçant** : Un joueur blessé qui joue 5 min/match a-t-il le même impact qu'un titulaire indiscutable ?

### 2.4 Arbitre et météo

1. **Biais de pénalty par arbitre** : Comment est-ce intégré dans le xG ? Est-ce que ça affecte le xG global ou seulement la proba de penalty ?
2. **Météo** : Les facteurs (pluie 0.93, vent 0.95) s'appliquent-ils aux deux équipes ou seulement à une ? Si aux deux, ça réduit les deux xG de manière symétrique → plus de draws. Est-ce l'effet recherché ?

---

## PARTIE 3 — ENSEMBLE ML

### 3.1 Data leakage

**Question critique** : Les features ML incluent `market_home`, `market_draw`, `market_away`. Les cotes de marché reflètent déjà une probabilité quasi-optimale. Le ML risque de simplement apprendre à copier le marché. Vérifie :
1. L'importance des features market dans le modèle XGBoost (SHAP values ou `feature_importances_`)
2. Si le modèle sans features market performe significativement moins bien
3. En production, les cotes de marché sont-elles toujours disponibles au moment de la prédiction ? Sinon, les NaN sont imputés — comment ?

### 3.2 Target leakage temporelle

Le `TimeSeriesSplit` est utilisé dans l'ensemble stacking. Mais :
1. Les features incluent `home_elo` et `away_elo` qui sont calculés à partir de résultats passés. Si l'ELO est recalculé APRÈS le split (i.e., avec des données du test set), il y a leakage. Vérifie l'ordre des opérations.
2. `home_form` et `away_form` : même question — la forme est-elle calculée uniquement sur des matchs antérieurs à la date de prédiction ?

### 3.3 Imputation des NaN

Quand une feature est manquante (`context.get(col)` retourne None) :
1. Comment l'imputer gère les NaN ? Moyenne ? Médiane ? Valeur par défaut ?
2. Si 10 features sur 45 sont NaN (ex: pas de market, pas de H2H, pas de referee), la prédiction ML est-elle encore fiable ?
3. Y a-t-il un seuil de features manquantes au-delà duquel le ML devrait être désactivé ?

### 3.4 Stacking — Overfitting

1. **Meta-learner LogReg sur 12 features** : 9 probas de base + max_prob + agreement + entropy. Avec 5-fold TimeSeriesSplit, le train set du meta-learner a ~80% des données. C'est suffisant si le dataset est large, mais risqué si < 500 samples.
2. **Régularisation** : Le meta-learner utilise `C=1.0`. C'est-il optimal ? Un C plus petit (plus de régularisation) serait-il plus robuste ?
3. **Out-of-fold predictions** : Vérifie que les OOF predictions sont bien générées sans voir le test fold (sinon, overfitting garanti).

### 3.5 Class imbalance

Le `compute_sample_weight(class_weight="balanced")` compense le déséquilibre ~40/25/35 (H/D/A). Vérifie :
1. Que le sample_weight est bien passé à `cross_val_score` via `fit_params`
2. Que le LightGBM et LogReg dans l'ensemble ont aussi une compensation
3. Que la calibration post-training ne réintroduit pas le biais

---

## PARTIE 4 — CALIBRATION

### 4.1 Calibration 1X2 désactivée

Le code indique que la calibration 1X2 est **désactivée** (Mars 2026) car seulement 74 samples → paramètres Platt dégénérés. C'est une décision correcte, mais :
1. Quel est le plan pour la réactiver ? À 100 samples ? 200 ?
2. Sans calibration, les probas 1X2 sont-elles systématiquement biaisées ? Mesure le Brier score et le diagramme de fiabilité sur les 74 samples disponibles.
3. L'Isotonic regression à 500+ samples est-elle réaliste à court terme ?

### 4.2 Calibration binaire (BTTS, Over)

1. **Platt scaling** : Les paramètres `platt_a` et `platt_b` sont-ils recalculés régulièrement ou figés ? Si figés, ils dérivent avec le temps (concept drift).
2. **Isotonic** : La fonction en escalier est non-paramétrique. Avec 500 samples, elle a ~20-50 marches. Est-ce assez lisse pour généraliser ?
3. **Overflow protection** : `z = max(-10, min(10, z))` dans l'application Platt. Vérifie que `platt_a` ne peut pas être aberrant (ex: a=50, b=-25 → sigmoid quasi-binaire).
4. **Cache** : `_isotonic_cache` garde le modèle en mémoire. Est-il invalidé quand de nouvelles données arrivent ? `clear_cache()` est-il appelé au bon moment ?

### 4.3 Métriques de calibration

Pour chaque marché calibré, vérifie :
1. **Brier score** avant/après calibration — la calibration améliore-t-elle réellement ?
2. **Reliability diagram** : Les bins de confiance (0-10%, 10-20%, ..., 90-100%) correspondent-ils aux fréquences observées ?
3. **Log loss** : Plus sensible aux probabilités extrêmes que le Brier score
4. **Expected Calibration Error (ECE)** : Moyenne pondérée des écarts par bin

---

## PARTIE 5 — BLEND FINAL ET COHÉRENCE

### 5.1 Pondération stats/ML/AI

Le pipeline a **trois niveaux de blend** :
1. Poisson(55%) + ELO(25%) + Market(20%) → Stats blend
2. Stats(60%) + ML(40%) → Combined blend
3. Combined(70%) + Gemini(30%) → Final

**Calcul de contribution effective** d'un signal à la proba finale :
- Poisson : 55% × 60% × 70% = **23.1%**
- ELO : 25% × 60% × 70% = **10.5%**
- Market : 20% × 60% × 70% = **8.4%**
- ML : 40% × 70% = **28.0%**
- Gemini : **30.0%**

**Constat** : Le ML (28%) pèse plus que le Poisson (23.1%) dans le résultat final. Le Gemini (30%) pèse plus que tout modèle statistique individuel. **Est-ce voulu ?** Le ML est-il suffisamment robuste pour justifier 28% du signal ? Le Gemini 30% est-il justifié mathématiquement ou c'est du narratif ?

### 5.2 Double comptage des nuls

Le draw reçoit des boosts à TROIS endroits :
1. **Draw calibration dans poisson_grid** : correction diagonale ±15%
2. **Stakes draw boost** : +3% si les deux équipes ont des enjeux
3. **Euro draw boost** : +2-4% pour CL/EL

Dans un match de CL à enjeux, le draw peut recevoir 15% + 3% + 4% = **22% de boost cumulé**. C'est-à-dire qu'un draw de base à 25% pourrait monter à ~30%. Est-ce excessif ? Vérifie les taux historiques de draws en CL avec enjeux.

### 5.3 Clamping et information perdue

Les clamps multiples (XG_FLOOR=0.3, XG_CEIL=4.0, PROB_FLOOR=5%, PROB_CEIL=72%, soft cap 80%) effacent de l'information aux extrêmes. Quantifie :
1. Combien de matchs par saison touchent le XG_FLOOR ou XG_CEIL ?
2. Combien de probas sont clampées par le floor/ceil ?
3. Le soft cap 80% est-il atteint souvent ? Si oui, ça signifie que le modèle est très confiant mais qu'on le bride artificiellement.

### 5.4 Incohérence entre marchés

Vérifie les relations logiques obligatoires :
1. `P(Home) + P(Draw) + P(Away) = 100%` ✓ (forcé)
2. `P(DC 1X) = P(Home) + P(Draw)` — est-ce calculé directement ou dérivé du blend ?
3. `P(Over 2.5) ≤ P(Over 1.5) ≤ P(Over 0.5)` — toujours vérifié ?
4. `P(BTTS) ≤ 1 - P(score 0-X) - P(score X-0)` — cohérent avec la grille ?
5. Les Asian Handicaps sont-ils cohérents avec les 1X2 ? (ex: si Home est à 70%, le -1.5 AH devrait être > 50%)
6. Après calibration de BTTS et Over, les relations 3 et 4 tiennent-elles encore ? La calibration peut violer les contraintes logiques inter-marchés.

---

## PARTIE 6 — SÉCURITÉ ET DETTE TECHNIQUE

### 6.1 Injection et données externes

1. **Pickle deserialization** : `pickle.loads(base64.b64decode(weights_b64))` dans `ml_predictor.py`. C'est une **faille de sécurité critique**. Un modèle malveillant dans Supabase peut exécuter du code arbitraire. Recommandation : utiliser `safetensors` ou valider le payload.
2. **API-Football data** : Les données xG/stats sont-elles validées avant utilisation ? Un xG de -5 ou 999 passerait-il les guards ?
3. **Gemini prompt injection** : Si les noms d'équipes ou de joueurs contiennent des instructions malveillantes, le prompt Gemini pourrait être détourné.

### 6.2 Race conditions

1. **ELO updates** : Si deux matchs de la même équipe sont résolus simultanément, l'ELO peut être incorrect (read-update-write sans lock).
2. **Bankroll** : `get_current_bankroll()` puis `bankroll_after = current - stake` — entre les deux, un autre bet peut être placé → solde incorrect.
3. **Cache calibration** : `_isotonic_cache` n'a pas de TTL. Si des données arrivent pendant une prédiction, le cache peut être stale.

### 6.3 Dette technique

1. **Pas de versioning des modèles** : Si un modèle ML est mis à jour, les anciennes prédictions ne sont plus reproductibles. Y a-t-il un `model_version` dans les résultats ?
2. **Constants hardcodés** : 50+ constantes dans `constants.py`. Certaines sont interdépendantes (FORM_WEIGHT_SHORT + FORM_WEIGHT_LONG = 1.0). Y a-t-il des assertions pour garantir la cohérence ?
3. **Pas de monitoring** : Les Brier scores sont-ils trackés dans le temps ? Y a-t-il une alerte si la performance se dégrade (concept drift) ?
4. **Tests** : 381 tests dont 18 failures pré-existantes. Ces 18 failures cachent-elles des régressions réelles ?

---

## PARTIE 7 — BENCHMARKS ET VALIDATION

### 7.1 Métriques à calculer

Pour chaque marché (1X2, BTTS, Over 2.5, Over 1.5), calcule sur tes données historiques :

| Métrique | Cible "10/10" | Acceptable | Alarme |
|----------|---------------|------------|--------|
| Brier Score (1X2) | < 0.19 | < 0.21 | > 0.23 |
| Log Loss (1X2) | < 0.95 | < 1.00 | > 1.05 |
| Accuracy (1X2) | > 55% | > 50% | < 48% |
| Brier Score (binaire) | < 0.20 | < 0.22 | > 0.25 |
| ROI sur value bets | > +5% | > 0% | < -5% |
| ECE | < 0.03 | < 0.05 | > 0.08 |
| Closing Line Value | > 0% | ≥ 0% | < -2% |

### 7.2 Tests de cohérence

1. **Test de symétrie** : `analyze_match(A vs B domicile) vs analyze_match(B vs A domicile)`. Les probas doivent être cohérentes (pas identiques à cause du home advantage, mais la somme des home% des deux scénarios devrait être ~100% + 2×home_bias).

2. **Test de monotonie** : Si ELO_A augmente de 100 (toutes choses égales), P(Home) doit augmenter. Vérifie que c'est le cas à travers tout le pipeline (les non-linéarités des clamps peuvent violer la monotonie).

3. **Test de sensibilité** : Varie chaque input de ±10% et mesure l'impact sur la proba finale. Identifie quels inputs ont le plus/moins d'influence. Le ranking d'influence correspond-il à l'intuition ?

4. **Test de calibration par bin** : Regroupe toutes les prédictions où P(Home)∈[60%,70%]. Le taux de victoire domicile observé dans ce bin doit être ~65%. Fais ça pour chaque bin de 10%.

5. **Test de stress** : Matchs extrêmes :
   - xG 4.0 vs 0.3 (gros favori)
   - ELO 2000 vs 1200 (écart massif)
   - Tous les multiplicateurs défavorables simultanément
   - Toutes les données manquantes (pas de market, pas de H2H, pas de referee, pas de weather)

### 7.3 Comparison avec les closing lines

Le **Closing Line Value (CLV)** est le gold standard. Si tes probas sont meilleures que les cotes de clôture des bookmakers, tu bats le marché. Mesure :
```
CLV = (ta_proba_implicite / closing_odds_implicite) - 1
```
Un CLV moyen > 0 sur 500+ matchs est exceptionnel. Un CLV moyen < 0 signifie que le marché est plus précis que ton modèle.

---

## PARTIE 8 — RECOMMANDATIONS PRIORITAIRES

Pour atteindre un **10/10**, classe chaque finding par :
- **Impact** (1-5) : À quel point ça affecte la qualité des probas
- **Effort** (1-5) : Complexité de la correction
- **Risque** (1-5) : Risque si non corrigé

Présente tes findings dans un tableau trié par Impact décroissant :

| # | Finding | Impact | Effort | Risque | Recommandation |
|---|---------|--------|--------|--------|----------------|
| 1 | ... | 5 | 2 | 5 | ... |

---

## INSTRUCTIONS POUR L'AUDITEUR

1. **Lis chaque fichier source intégralement** avant de commenter. Pas d'hypothèses.
2. **Cite le code exact** (fichier:ligne) pour chaque constat.
3. **Quantifie** tout — pas de "ça pourrait être un problème", mais "pour xG=3.5 et ρ=-0.17, la correction vaut X, ce qui implique Y".
4. **Distingue** les bugs (erreur mathématique → fix obligatoire) des améliorations (choix suboptimal → recommandation).
5. **Teste** les cas limites : valeurs extrêmes, données manquantes, matchs atypiques.
6. **Ne touche pas** au code sans validation explicite. Cet audit est en lecture seule.
7. **Vérifie la sécurité** : pickle, injections, race conditions, validation d'input.
8. **Propose des correctifs concrets** avec le code exact pour chaque bug identifié.
9. **Priorise** : on veut les quick wins à fort impact d'abord.
10. **Zéro complaisance** : si le système est bon, dis-le. S'il est cassé, dis-le aussi.
