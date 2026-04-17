# 03 — Monitoring ML en production

## 1. Périmètre audité

**Modules inspectés** (`ProbaLab/src/monitoring/`, ~1 400 LOC total) :
- `brier_monitor.py` (366 LOC) — Brier/Log Loss/ECE + reliability diagram + rolling drift
- `drift_detector.py` (169 LOC) — Comparaison Brier 7j vs 30j
- `alerting.py` (176 LOC) — Alertes Telegram (Brier drift, data completeness, prediction volume)
- `data_quality.py` (287 LOC) — Coverage predictions/odds/events, null proba detection
- `feature_audit.py` (152 LOC) — Détection data leakage (market features dominance XGBoost)
- `backtest_clv.py` (260 LOC) — Closing Line Value with overround removal
- `__main__.py` (153 LOC) — CLI `python -m src.monitoring [--clv|--brier|--features|--quality|--alerts]`

**Branchement runtime inspecté** :
- `worker.py:187-203` — APScheduler jobs
- `run_pipeline.py:120-137` — pipeline orchestration
- `api/routers/trigger.py` (1687 LOC) — endpoints cron
- `api/routers/monitoring.py` — endpoints santé publique
- `api/routers/admin.py` — dashboard admin (cherché)
- `dashboard/src/pages/` — page `Admin.tsx` / `ModelHealth.tsx` (cherchée)

**Inclus** : Monitoring ML en production (Brier, drift, calibration, alerting, dashboard, persistence).
**Exclus** : Qualité du modèle ML lui-même (voir annexe 02), data pipeline (voir annexe 05).

---

## 2. État actuel

### 2.1 Ce qui fonctionne bien

1. **Modules monitoring bien conçus** (`src/monitoring/`)
   - Métriques complètes : Brier 1X2, Log Loss, ECE, reliability diagram, CLV, feature audit, data quality
   - Seuils documentés : `Brier < 0.19 = EXCELLENT`, `0.19-0.21 = GOOD`, `0.21-0.23 = ACCEPTABLE`, `≥ 0.23 = DEGRADED`
   - Type hints complets (`from __future__ import annotations`)
   - Error handling try/except partout
   - Telegram HTML escaping (`_html.escape`) — leçon 17 appliquée

2. **Drift detection Brier en cron** ✅
   - `worker.py:187-203` — `job_drift_check()` quotidien à 09:00
   - Compare Brier 7j vs 30j, seuil configurable `DRIFT_THRESHOLD = 0.02`
   - Alerte Telegram déclenchée automatiquement
   - **Seul module monitoring réellement branché en cron**

3. **CLI de debug disponible**
   - `python -m src.monitoring [flag]` — report consolidé 0-10 health score
   - Utile pour investigation manuelle

4. **Table `prediction_results` présente**
   - Migration `003_performance_tracking.sql`
   - Colonnes : `brier_score_1x2`, `log_loss`, `pred_*`, `actual_*`, `result_1x2_ok`, `btts_ok`, `over_*_ok`
   - Base de données prête pour monitoring persistence (mais non utilisée en écriture monitoring)

### 2.2 Dette technique / bugs latents

**🔴 P0 CRITIQUE — Pipeline monitoring désactivée en prod**

`run_monitoring_alerts()` existe dans `run_pipeline.py:120-137` mais **n'est jamais exécuté automatiquement** :

```python
# run_pipeline.py ligne 156-159
if mode in ("full", "all"):
    run_data_pipeline()
    run_analysis()
    run_monitoring_alerts()  # ← JAMAIS EXÉCUTÉ en cron
```

```python
# worker.py ligne 107-114
def job_data_pipeline() -> None:
    from run_pipeline import run_data_pipeline
    run_data_pipeline()  # ← SEULEMENT data, pas monitoring
```

`job_data_pipeline()` (07:00) appelle `run_data_pipeline()` seulement. Aucun job cron ne déclenche `run_pipeline.py full`. Conséquence : `check_and_alert()` (Brier drift détaillé, data completeness, prediction volume) ne tourne jamais.

**🔴 P0 CRITIQUE — Aucune persistance des métriques**

Brier, ECE, CLV sont **recalculés à chaque appel** API `/api/monitoring` (cache 5-10 min) puis discardés. Aucune table `model_health_log` ou équivalent. Impossible de :
- Tracer dégradation progressive sur 90j
- Implémenter le dashboard admin (todo.md Phase 2.5)
- Détecter drift lent sur plusieurs semaines

La table `prediction_results` contient Brier par prédiction mais n'est pas queryée pour générer une timeline quotidienne.

**🟡 P1 — Feature drift (KS test) absent**

Aucun module `ks_2samp` ou équivalent dans `src/monitoring/`. Todo.md Phase 2.3 l'identifie comme manquant. Conséquence : divergence distribution training vs prod non détectée.

**🟡 P1 — Alerting incomplet**

`alerting.py` couvre 3 checks :
1. Brier drift (7j > 30j)
2. Data completeness (< 80% fixtures)
3. Prediction volume (zéro today)

Manquent :
- Odds staleness (fixture_odds pas mis à jour depuis 12h)
- Model version mismatch (predictions utilisant un ancien modèle)
- Result evaluation lag (FT matches non évalués après 6h)
- Calibration drift ECE (seul Brier est tracké)

**🟡 P1 — Pas de retry/dédup alerting**

`send_telegram()` dans `alerting.py:76-99` :
- Pas de retry si Telegram fail (leçon 16 violée)
- Pas de déduplication (même alerte envoyée 2x si check runs 2x)
- Pas d'escalation (email si Telegram down)
- Pas d'ack tracking

**🟡 P1 — Dashboard admin absent**

Recherche confirme absence de :
- Endpoint `GET /api/admin/model-health` (todo.md Phase 2.5)
- Page React `ModelHealth.tsx` ou section dans `Admin.tsx`

### 2.3 Code smells repérés

1. **Code mort potentiel** — `backtest_clv.py` (260 LOC), `feature_audit.py` (152 LOC), `data_quality.py` (287 LOC) jamais appelés en cron, seulement via CLI manuel ou endpoint à la demande. Risque : évolution non testée, désynchronisation silencieuse.

2. **Endpoint `/api/monitoring` tout-en-un** — recompute CLV + Brier à chaque hit, cache TTL 5-10 min. Coûteux, pas idempotent.

3. **CLI disjoint du cron** — `__main__.py` expose des capacités via flags mais zéro orchestration automatique.

### 2.4 Gaps vs. bonnes pratiques MLOps industrie

| Aspect | ProbaLab | Standard (Evidently AI / Arize / WhyLabs) |
|--------|----------|------------------------------------------|
| Calibration monitoring | Brier + ECE ✅ | Brier, ECE, MCE, Reliability diag |
| Drift detection (pred) | Brier 7j vs 30j | Rolling window + statistical test |
| Drift detection (feature) | ❌ | KS test + Wasserstein |
| Data quality | Basic (coverage) | Advanced (missing %, cardinality, min/max drift) |
| CLV/ROI tracking | ✅ | Spécifique betting |
| Persistence historique | ❌ | Obligatoire |
| Dashboards | API endpoints only | Dashboards natifs |
| Alert integration | Telegram only | Slack, PagerDuty, Email, SMS |
| Latency monitoring | ❌ | Standard |
| Model rollback auto | ❌ | Standard MLOps |

---

## 3. Niveau de maturité : **L2/L5**

**Justification** (curseur strict) :

- ✅ L1 dépassé : métriques implémentées proprement, modules pensés.
- ✅ L2 atteint : drift check Brier quotidien fonctionne, alerte Telegram branchée.
- ❌ L3 bloqué par : pipeline monitoring désactivée en prod, aucune persistance historique, dashboard admin absent.
- ❌ L4 hors d'atteinte : feature drift inexistant, alerting minimaliste, pas de rollback automatique.

**Paradoxe clé** : l'infrastructure du code (6 modules de qualité, ~1 400 LOC) est de niveau L3/L4, mais le **branchement production est L1-L2**. Du code bien écrit mais inactif donne un faux sentiment de sécurité — c'est plus dangereux qu'une absence totale, car l'owner peut croire que le monitoring protège la prod alors que 60% des checks ne tournent jamais.

---

## 4. Benchmark vs. standard industrie

**Références** :
- **Evidently AI / Arize / WhyLabs** : plateformes MLOps mainstream (pas des concurrents ProbaLab directs, mais standard que tout système ML sérieux doit rejoindre).
- **RebelBetting / Pinnacle** : pour le CLV tracking, référence betting — ils ont des dashboards CLV par période et par marché en temps réel.

**Ce qu'ils font mieux** :
- Persistence automatique (time-series DB type Prometheus / InfluxDB)
- Feature drift tracking par défaut (KS, Wasserstein, JS divergence)
- Alertes multi-canal avec retry/dedup/escalation
- Rollback automatique sur seuils SLO
- Dashboards avec timelines par métrique × segment

**Ce qu'ils font moins bien** :
- Pas de métriques domain-specific (CLV, overround removal) — ProbaLab a ici un atout métier, même s'il n'est pas automatisé.

**Écart mesurable** :
- Couverture automatique en cron : ProbaLab ~20% (1 des 5 checks) vs. industrie standard 100%.
- Rétention historique : 0 jour vs. 90+ jours.
- Nombre de types d'alerte : 3 vs. 15+.

---

## 5. Gaps pour passer au niveau supérieur

### P0 — Bloquants pour devenir L3 (effort : 2-5j)

1. **Restaurer le pipeline monitoring en cron** (1j)
   - Ajouter dans `worker.py` un job `job_run_full_pipeline_monitoring` à 08:30
   - Il appelle `run_pipeline.py` en mode `full` (ou directement `run_monitoring_alerts()`)
   - Le timing 08:30 est post-évaluation et pré-prédiction du jour

2. **Persistance des métriques** (1-2j)
   - Créer table `model_health_log` (timestamp, brier_7d, brier_30d, ece, clv_best_mean, drift_detected, alert_count)
   - Upsert quotidien dans `run_monitoring_alerts()`
   - Rendre cette table queryable pour le dashboard admin

3. **Endpoint `/api/admin/model-health`** (1j)
   - Retourner 90j de timeline + état drift + features en dérive
   - Auth admin stricte (hmac.compare_digest)

4. **Fix alerting fail-silent** (0.5j)
   - Retry Telegram (leçon 16)
   - Dédup in-memory des alertes (TTL 1h)
   - Logger CRITICAL si Telegram indispo

### P1 — Améliorations significatives (effort : 5-10j)

5. **Feature drift KS test** (2-3j)
   - `check_feature_drift()` dans `drift_detector.py`
   - Distribution training vs derniers 30j de `predictions`
   - Alerte si > 3 features KS p-value < 0.01

6. **Dashboard admin React** (3j)
   - Page `dashboard/src/pages/Admin/ModelHealth.tsx`
   - Recharts timeline Brier/ECE
   - Tableau features driftées
   - Bouton "Relancer les checks"

7. **Model versioning + rollback** (3-4j)
   - Sauver modèle + hash + timestamp dans Supabase Storage post-training
   - Backtest 48h avant promotion, skip upsert si Brier pire (leçon 40 étendue)
   - Endpoint `POST /api/admin/rollback-model`

8. **Alerting étendu** (2j)
   - Odds staleness, model version mismatch, result evaluation lag, calibration drift ECE

### P2 — Polish (effort : 3-5j)

9. **CLV tracking en cron** — lancer `backtest_clv.run()` quotidien, persister
10. **Feature audit en cron** — détecter data leakage automatiquement (leçon 12)
11. **Latency monitoring** — tracker temps d'inférence par endpoint
12. **Alerting multi-canal** — Discord en backup de Telegram

---

## 6. Risques identifiés

| # | Risque | Sévérité | Probabilité | Impact |
|---|--------|----------|-------------|--------|
| R1 | Dégradation modèle non détectée pendant 24-48h | **CRITIQUE** | Haute | Picks mauvais envoyés publiquement, pertes utilisateurs |
| R2 | Modèle corrompu (data leakage réintroduit) non détecté | Haute | Moyenne | Faux sentiment de sécurité |
| R3 | Monitoring code évolue sans tester → drift silencieux | Moyenne | Moyenne | Modules devenus incorrects |
| R4 | Dashboard admin toujours absent → owner aveugle | Haute | Haute (actuel) | Décisions au feeling |
| R5 | Telegram indisponible → aucune alerte alternative | Moyenne | Basse | Angle mort temporaire |
| R6 | Feature drift introduit par nouveau fetcher sans alerte | Haute | Moyenne | Prédictions biaisées |
| R7 | Rollback manuel nécessaire sans procédure documentée | Moyenne | Haute | Délai de récupération long |

---

## 7. Recommandations stratégiques

1. **Traiter le monitoring comme un système de production à part entière**, pas comme un accessoire. Le code existe ; il faut le brancher, le tester, le persister. C'est la recommandation #1.

2. **Instaurer un principe fail-loud sur tout module de sécurité/qualité**. Les dépendances critiques absentes doivent logger CRITICAL au démarrage (leçon 41). S'applique aussi aux alertes : si Telegram indisponible, il faut le savoir.

3. **Créer un tableau de bord "health" public** (ou semi-public) qui affiche en continu le Brier rolling, la couverture, le CLV. Double effet : transparence utilisateur et pression interne pour maintenir la qualité. Les concurrents sérieux (MoneyPuck, RebelBetting) le font.

4. **Prérequis pour le pivot "Spécialiste en probabilités sportives"** : le monitoring DOIT être en L3 minimum avant d'activer les catégories Safe/Fun/Value en public. Sinon, un pick mauvais = trust brisé, et la data va dériver sans alerte.

5. **Documenter la procédure de rollback manuel** dès maintenant (runbook), même sans automatisation. Un runbook 1-pager bat une automatisation qui n'existe pas encore.

---

## 8. Liens internes

**Fichiers clés** :
- `ProbaLab/src/monitoring/brier_monitor.py` (366 LOC)
- `ProbaLab/src/monitoring/drift_detector.py:40-90`
- `ProbaLab/src/monitoring/alerting.py:76-99` (fail-silent Telegram)
- `ProbaLab/run_pipeline.py:120-137` (pipeline monitoring déconnecté)
- `ProbaLab/worker.py:187-203` (seul job monitoring en cron)
- `ProbaLab/api/routers/monitoring.py` (endpoints sans persistance)

**Leçons pertinentes** :
- `tasks/lessons.md:16` — appels API externes sans retry
- `tasks/lessons.md:17` — échappement HTML dans alertes
- `tasks/lessons.md:40` — ne pas upsert un modèle pire
- `tasks/lessons.md:41` — dépendances sécu/qualité fail-loud

**Documents liés** :
- `ProbaLab/tasks/todo.md` Phase 2 (Monitoring ML, 99-154)
- Migration DB : `003_performance_tracking.sql` — table `prediction_results`
- Annexe 02 de cet audit (Machine Learning) — findings data leakage et calibration
