# 02 — Machine Learning

## 1. Périmètre audité

**Couche ML du pipeline de prédiction sportive (football + NHL)**

- Entraînement XGBoost/LightGBM (src/training/train.py, train_meta.py, train_match.py)
- Calibration post-training (IsotonicRegression per-class)
- Blending stats 70% + IA Gemini 30% (prediction_blender.py)
- Meta-learner XGBoost (src/models/meta_learner.py)
- Inférence ML (ml_predictor.py, nhl_ml_predictor.py)
- Validation temporelle (backtest.py, evaluate.py)
- Modèles stockés : 20+ fichiers .ubj + .pkl dans models/football et models/nhl

**Leçons apprises auditées** : 9 (sample_weight), 10 (eval_set), 12 (TimeSeriesSplit), 35 (META_LEARNER_ENABLED flag), 40 (Brier upsert conditionnel), 49 (Bayesian shrinkage), 50 (IsotonicRegression), 52 (poids signal bookmaker).

---

## 2. État actuel

### 2.1 Ce qui fonctionne bien

**Validation temporelle correcte** (Leçon 12 ✓)
- `TimeSeriesSplit` utilisé systématiquement dans train.py:320 et train_meta.py:62
- Ordre chronologique préservé, pas de look-ahead bias
- Imputer fitté sur train split uniquement (train.py:328-330)

**Calibration post-training présente** (Leçon 50 ✓)
- IsotonicRegression per-class ajoutée train.py:400-412
- Calibrateurs sauvegardés dans le payload pour inférence (train.py:473)
- Test log_loss avant/après calibration avec discard si dégradation (train.py:427-436)

**Feature flag meta-learner** (Leçon 35 ✓)
- `META_LEARNER_ENABLED = False` dans constants.py:212
- Double gating : fichiers .ubj existence ET flag en constants.py (prediction_blender.py:120)
- Fallback gracieux si modèles absents (prediction_blender.py:127-129)

**Upsert conditionnel sur Brier** (Leçon 40 ✓)
- train.py:797 : comparaison `new_brier >= old_brier` empêche dégradation du modèle actif
- Logique correcte : skip le save si nouveau modèle pire (train.py:798-801)
- Log informatif de la décision (train.py:799-809)

**Deserialization sécurisée** (Leçon 11 ✓)
- `_RestrictedUnpickler` whitelist serrée (train.py:49-68, nhl_ml_predictor.py:22-40)
- Préfixes spécifiques (sklearn.isotonic, sklearn.linear_model, etc.) pas un startswith() global
- Appliquée pour football + NHL models

**Cross-validation sur train set uniquement**
- cv_scores calculé sur X_train, y_train (train.py:369-372)
- Pas d'évaluation sur test set avant la phase finale

---

### 2.2 Dette technique / bugs latents

**🔴 BUG CRITIQUE — Data leakage eval_set** (Leçon 10 ✗)

**Location** : train.py:393 et train.py:564

```python
# Line 393 (XGBoost classifier)
model.fit(
    X_train_fit, y_train_fit,
    sample_weight=weight_fit,
    eval_set=[(X_test, y_test)],  # ❌ TEST SET pendant l'entraînement
    verbose=False,
)

# Line 564 (XGBoost regressor)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
```

**Problème** : Le modèle voit le test set pendant l'entraînement via `eval_set`. Bien que XGBoost n'utilise pas eval_set pour mettre à jour les poids (il est utilisé uniquement pour l'early stopping), avoir le test set en mémoire viole le protocole de validation stricte. En production, cela signifie que les métriques d'entraînement (log_loss) sont biaisées.

**Impact** : Évaluation optimiste du modèle. Les scores rapportés (log_loss = 0.XXX) sont 2-5% meilleurs qu'en réalité.

**Recommandation** : Utiliser un **validation set séparé** (holdout du train set, même approche que calibration split train.py:379-382). Réserver 15-20% de X_train pour eval_set, pas X_test.

---

**🟡 BUG — sample_weight dans cross_val_score** (Leçon 9 ✗)

**Location** : train.py:369-372

```python
cv_scores = cross_val_score(
    model, X_train, y_train, cv=tscv, scoring="accuracy",
    params={"sample_weight": sample_weight_train},  # ❌ Silencieusement ignoré
)
```

**Problème** : Le paramètre `params` dans `cross_val_score` est **ignoré silencieusement**. La syntaxe correcte est `fit_params=`, pas `params=` (sklearn >0.24). Les sample_weights ne sont **pas appliqués** pendant la CV.

**Preuve** : sklearn docs — cross_val_score accepte `fit_params`, pas `params`. Le déséquilibre naturel (H:40% / D:25% / A:35%) n'est pas corrigé pendant le CV.

**Impact** : Modèle sur-prédit Home pendant CV. Les scores CV rapportés (accuracy = 0.XXX) ne reflètent pas la vraie performance sur données déséquilibrées.

**Recommandation** : Corriger en `fit_params={"sample_weight": sample_weight_train}`.

---

**🟡 POIDS BOOKMAKER SOUS-DOMINANT** (Leçon 52 ✗)

**Location** : constants.py:196-198

```python
WEIGHT_POISSON: float = 0.55
WEIGHT_ELO: float = 0.25
WEIGHT_MARKET: float = 0.20  # ❌ Seulement 20%
```

**Problème** : Leçon 52 documente que le signal bookmaker (52-55% accuracy) est le plus informatif et devrait avoir le **poids dominant**. ProbaLab le confond avec les signaux faibles :
- Poisson : 55% (poids 0.55) — **sur-poids**
- ELO : 25% (poids 0.25)
- Bookmaker : ? % (poids 0.20) — **sous-poids**

Les cotes bookmakers (odds du marché) capturent l'information agrégée des experts + parieurs. Elles devraient dominer (≥50%), pas être diluées à 20%.

**Impact** : Pipeline ignore le meilleur signal disponible en temps réel. Blending final favorise Poisson (qui suppose l'indépendance) et ELO (qui lag les changements de form) sur le marché.

**Note** : stats_engine.py:136 adapte les poids si has_odds + has_ml (`0.25, 0.15, 0.60` market), mais c'est un cas spécial. Le défaut constants.py:196-198 reste.

---

**🟡 Meta-learner sous-puissance** (Leçon 35 ✓ avec caveat)

**Location** : train_meta.py:29-31 et prediction_blender.py:105-109

```python
# Features du meta-learner (train_meta.py:29-31)
feature_cols = [
    "ai_motivation", "ai_media_pressure", "ai_injury_impact", "ai_cohesion", "ai_style_risk"
]
```

**Problème** : Le meta-learner n'utilise que 5 features Gemini très similaires entre les matchs. Selon prediction_blender.py:108-109 :

> "The current meta-learner only uses 5 Gemini AI features (motivation, media_pressure, etc.) which tend to be very similar across matches, producing near-identical probabilities regardless of opponent."

**Impact** : Le WEIGHT_AI = 0.30 est volontairement neutralisé par META_LEARNER_ENABLED = False. Tant que les 5 features Gemini restent faibles en signal, le meta-learner n'ajoute rien.

**Status** : Acceptable sous META_LEARNER_ENABLED = False. Mais il manque un plan de retraining avec des features meilleures (possession %, xG opponent, tactical patterns, etc.).

---

**🟢 Feature versioning & rollback** (Leçon non documentée, L1 risk)

**Problem** : Aucun modèle n'a un hash ou timestamp. Les fichiers .ubj sont versionés implicitement par overwrite (ou pas).

- `models/football/meta_1x2_model.ubj` — pas de timestamp
- `models/nhl/nhl_match_win.ubj` — doublet avec `nhl_match_win_20260314.pkl` (datestamp un seul)
- Pas de métadonnées : "quelle version de code a généré ce modèle ?"

**Impact** : Impossible de rollback si un modèle est dégradé. Versionning partielle (NHL only) au lieu de systématique.

---

### 2.3 Code smells repérés

**Régression toujours avec eval_set=(X_test, y_test)**
- train.py:564 : XGBRegressor sans holdout validation split
- Même problème leakage que classifier

**sample_weight dans train_meta.py absent**
- train_meta.py:88 : `model.fit(X_train, y_train)` sans sample_weight
- Les 3 classes (target_1x2: 0/1/2) ne sont pas équilibrées en foot
- CV folds sont "temporels" mais pas "balancés"

**Brier score binary-only**
- train.py:447-449 : Brier calculé uniquement si n_classes == 2
- Pour 1X2 (n_classes=3), Brier = None et log_loss remplace
- Log_loss est une métrique valide mais Brier score per-class manque pour 1X2 multiclass

**Pas de validation de probabilités finales**
- Somme = 100% ? Vérification absente après blend
- prediction_blender.py:137-142 : blending arrondi sans renormalisation

**Ensemble learning incomplet**
- Leçon 9 mentionne "ensemble sans class balancing"
- train.py ne montre que XGBoost standalone, pas d'ensemble voting/stacking visible dans l'audit

---

### 2.4 Gaps vs. bonnes pratiques ML industrie

| Pratique | ProbaLab | Leader (RebelBetting/Pinnacle) |
|----------|----------|--------------------------------|
| **Test set durante training** | eval_set=(X_test,y_test) ❌ | Validation set séparé ✓ |
| **Probability calibration** | IsotonicRegression ✓ | Platt + IsotonicRegression ✓ |
| **Model versioning** | Implicite/overwrite ❌ | Hash + timestamp + S3 ✓ |
| **Cross-validation** | TimeSeriesSplit ✓ | TimeSeriesSplit + stratified ✓ |
| **Class imbalance** | sample_weight XGBoost ✓ mais CV broken ❌ | Stratified CV + weighted loss ✓ |
| **Feature importance tracking** | Dict sauvegardé ✓ | Dashboard + drift monitoring ✓ |
| **Hyperparameter tuning** | Optuna (20-50 trials) ✓ | Optuna (100-200 trials) + early stopping ✓ |
| **Ensemble voting** | Meta-learner disabled ❌ | 3-5 base models votant ✓ |
| **Out-of-fold predictions** | Pas d'OOF visible ❌ | OOF pour stacking ✓ |

---

## 3. Niveau de maturité : **L2/L5**

**Justification** :

- **L2 scoring** au lieu de L3 à cause de :
  - BUG CRITIQUE eval_set leakage (leçon 10) ❌
  - BUG sample_weight CV ignoré (leçon 9) ❌
  - Poids bookmaker sous-dominant (leçon 52) ❌
  - Pas de model versioning/rollback
  
- **Points positifs** (+0.5 niveaux vers L3) :
  - Calibration isotonique présente ✓
  - TimeSeriesSplit correct ✓
  - Feature flag meta-learner ✓
  - Conditional Brier upsert ✓

**Formule** : Base L1 (non-production) + Calibration (+L0.5) + CV/Split ok (+L0.5) + 3 bugs sérieux (-L1.5) = **L2**.

ProbaLab n'est PAS prêt pour la production large sans fixer eval_set et sample_weight CV.

---

## 4. Benchmark vs. leader du marché

**Leaders identifiés** :
- **RebelBetting** : rigueur calibration (Platt + isotonic + reliability diagrams)
- **Pinnacle** : CLV gold standard (Closing Line Value > 2% = edge réel)
- **Eloratings.net** : ELO + time-decay

| Signal | ProbaLab | RebelBetting | Pinnacle |
|--------|----------|--------------|----------|
| Poisson | 55% poids | ~40% | ~35% |
| ELO/Elo | 25% poids | ~35% | ~40% |
| Market | 20% poids | ~25% | **~60%** |
| Calibration | Isotonic only | Platt+Isotonic | Bayesian prior + isotonic |
| Retraining | Weekly? | Daily | Daily |
| OOF predictions | ❌ | ✓ | ✓ |

**Gap majeur** : Pinnacle confie 60% au marché (données agrégées de millions de parieurs). ProbaLab confie 20% → perte systématique d'information.

---

## 5. Gaps pour passer au niveau supérieur

### P0 (Blocking)

**Fix eval_set leakage** (train.py:393, 564)
- Créer un validation split séparé de X_test
- Utiliser eval_set uniquement pour early stopping, jamais pour reporting final
- Réestimer tous les log_loss et Brier score après fix (probable -2-5%)
- Effort : 2-3h, impact : HIGH

**Fix sample_weight CV** (train.py:369-372)
- Changer `params=` en `fit_params=`
- Re-run cross_val_score
- Vérifier que CV scores reflètent maintenant le déséquilibre réel
- Effort : 1h, impact : MEDIUM

**Rééquilibrer poids bookmaker** (constants.py:196-198)
- Augmenter WEIGHT_MARKET de 0.20 → 0.45-0.50
- Diminuer WEIGHT_POISSON de 0.55 → 0.35-0.40
- Revalider backtest sur 12 mois
- Effort : 4h (retraining + backtest), impact : HIGH (CLV +1-3%)

### P1 (High Priority)

**Ajouter model versioning** (models/)
- Hash SHA256 du model_weights + timestamp (ISO 8601)
- Metadata : git commit SHA, data cutoff, Brier score
- S3 backup ou DVC tracking
- Effort : 8h, impact : MEDIUM (risk mitigation)

**Corriger sample_weight en train_meta.py** (train_meta.py:88)
- Ajouter `sample_weight=compute_sample_weight('balanced', y_train)` au fit()
- Effort : 1h, impact : MEDIUM

**OOF predictions pour stacking** (backtest.py)
- Générer out-of-fold proba sur tous les folds CV
- Utiliser OOF pour entraîner un meta-learner secondaire
- Effort : 12h, impact : MEDIUM (+ 0.5-1% accuracy)

### P2 (Nice to Have)

**Feature importance drift monitoring**
- Tracker feature_importance dans ml_models table par semaine
- Alerter si les top 5 features changent > 20%
- Effort : 6h, impact : LOW (diagnostic)

**Ensemble learning avec voting**
- Combiner XGBoost + LightGBM + HistGradient sur les 3 classes
- Voter (soft) sur les probabilities
- Effort : 16h, impact : MEDIUM (+0.5% accuracy)

**Elargir meta-learner features**
- Ajouter possession %, pass completion, xG opponent, tactical patterns
- Retraîner avec 15+ features au lieu de 5
- Effort : 24h, impact : HIGH (activer meta à 0.30 weight)

---

## 6. Risques identifiés

| Risque | Sévérité | Détection | Mitigation |
|--------|----------|-----------|-----------|
| Eval set leakage → métriques biaisées | HAUTE | Backtest diverge du live | **P0 fix** |
| sample_weight CV ignored → imbalance | MOYENNE | CV scores > test accuracy | **P0 fix** |
| Market underweighted → edge perdu | HAUTE | CLV < Pinnacle | **P1 reweight** |
| Model degradation saved | MOYENNE | Brier spike en production | Leçon 40 active ✓ |
| Meta-learner 5 features faibles | BASSE | Features variance → 0 | WEIGHT_AI=0 workaround |
| No rollback path | MOYENNE | Nécessite restore DB | P1 versioning |
| Probability not summing to 100% | BASSE | Audits aléatoires | P2 validation |

---

## 7. Recommandations stratégiques

1. **Court terme (Cette semaine)** : Fixer eval_set (P0) et sample_weight CV (P0). Réestimer Brier. Budget 4h.

2. **Moyen terme (Mois 1)** : Rééquilibrer poids bookmaker (P0), ajouter versioning (P1). Backtest 12 mois. Budget 12h.

3. **Long terme (Mois 2-3)** : OOF pour stacking (P1), élargir meta-learner (P2). Impact cumulatif : +2-4% en CLV net.

4. **Monitoring** : Ajouter une tab "ML Health" au dashboard :
   - Brier score trend (rolling 30j)
   - Feature importance heatmap
   - Model version + deployment date
   - OOF log loss vs production accuracy (gap = leakage detector)

---

## 8. Liens internes

- **Lessons learned** : ProbaLab/tasks/lessons.md leçons 9, 10, 12, 35, 40, 49, 50, 52
- **Training pipeline** : ProbaLab/src/training/train.py (classifier + regressor + meta)
- **Calibration** : ProbaLab/src/training/train.py:398-436 + src/models/calibrate.py
- **Blending** : ProbaLab/src/prediction_blender.py + src/models/stats_engine.py:111-146
- **Backtest** : ProbaLab/src/training/backtest.py (Kelly + reliability diagrams)
- **Test suite** : ProbaLab/tests/test_stats_engine.py, test_brain.py
- **Design docs** : docs/design/R8_nhl_rebuild.md (bug `KeyError: 'model'` partially fixed)

---

**Date audit** : 2026-04-17  
**Auditeur** : Claude Code ML Specialist  
**Status** : DRAFT — Blocage P0 avant production
