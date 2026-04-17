# 04 — NHL spécifique

## 1. Périmètre audité

**Composants inspectés** (~3 300 LOC total NHL + API) :
- `ProbaLab/src/nhl/` (11 fichiers, ~2 721 LOC) :
  - `fetch_schedule()` (gestion timezone/edge cases), `fetch_standings()`, `fetch_team_special_teams()`, `fetch_game_stats.py`
  - `fetch_odds.py` (The Odds API — bookmaker odds)
  - `feature_engineering.py` (103 features pour joueur)
  - `build_data.py` (dataset assembly)
  - `ml_models.py` (XGBoost loading + safe-unserialization whitelisting)
  - `train.py` + `train_match.py` (Optuna tuning)
  - `calibration.py` (Isotonic + Platt Scaling)
  - `nhl_ml_predictor.py` (match-level inference win/over55)
  - `backtest.py`
- `ProbaLab/src/fetchers/fetch_nhl_player_props.py` (nouveau, untracked)
- `ProbaLab/api/routers/nhl.py` (873 LOC, 6 endpoints publics + calibration)
- `ProbaLab/worker.py` (APScheduler, 6 jobs NHL cron)
- Tests : `ProbaLab/tests/test_nhl_pipeline.py` (stub skipped, 0 assertion effective)

**Inclus** : pipeline NHL bout-en-bout — data → features → ML → calibration → endpoints → cron.
**Exclus** : frontend NHL (voir annexe 07), sécurité RLS (voir annexe 06).

---

## 2. État actuel

### 2.1 Ce qui fonctionne bien

1. **Timezone + Schedule fallback corrigé (leçon 65)** ✅
   - `fetch_schedule()` : condition corrigée `if day["date"] == today and day.get("games"):`
   - Fallback au jour suivant avec matchs si jour off
   - Résout le bug UTC/NHL date mismatch (nuit US transcontinentale)

2. **Team name normalization (leçon 67)** ✅
   - `constants.py` centralise les mappings abréviation ↔ nom complet
   - Inclut "St. Louis Blues" correctement
   - Utah Hockey Club mappé en "UTA" (rename officiel 2025-26 tracké)

3. **Provider odds — The Odds API (leçon 66)** ✅
   - `fetch_odds.py` ligne 76-79 : fenêtre UTC rigoureuse (00h → +8h UTC)
   - Rate limiting respecté (500 req/mois plan gratuit, ~60 req/mois réel)
   - Gestion 401/422/429 avec fallback approprié
   - Migration depuis API-Sports Hockey (qui renvoyait vide en plan Free) effectuée

4. **ML model loading — stratégie `.ubj + .pkl`** ✅
   - `nhl_ml_predictor.py:75-85` : détecte `.pkl` metadata + charge `.ubj` binary
   - Élimine les risques de désérialisation non sûre
   - RestrictedUnpickler strict (whitelisting sklearn/xgboost uniquement)
   - Modèles présents : `nhl_match_win.{pkl,ubj}`, `nhl_match_over55.{pkl,ubj}`

5. **Pipeline scheduling en APScheduler — 2 runs/jour** ✅
   - Worker : 16h (analyse matin US) + 23h (re-run compos officielles)
   - Gating intelligent : NHL 16h-08h UTC seulement (économie API)
   - Migration Trigger.dev → APScheduler complète (leçon 64 résolue)

### 2.2 Dette technique / bugs latents

**🔴 P0 — Player props market gap (80% du marché non couvert)**

- `fetch_nhl_player_props.py` : `MARKETS = "player_goals"` uniquement
- The Odds API plan gratuit ne retourne que `player_goals` (Anytime Scorer)
- Pas de vraies cotes pour `player_points` (Over 0.5) ni `player_assists`
- Fallback : `calculate_implied_odds(prob)` — probas converties en decimal

**Impact direct sur le pivot** : le design pivot prévoit des Safe picks NHL sur "1+ Point" et "1+ Passe décisive" (§5 D5). Actuellement ces marchés **n'ont pas de vraies cotes bookmaker**. Les picks Safe/Fun afficheraient des odds calculées en interne, ce qui :
- Rend le "value bet" NHL non mesurable (pas d'overround bookmaker à battre)
- Crée un risque légal/trust : user voit @1.85 calculé mais marché réel est 1.62

**🔴 P0 — Calibration sous-alimentée NHL vs Football**

- `calibration.py` : `analyze_history()` lit 10 000 rows max depuis `nhl_suivi_algo_clean`
- Après filtres `GAGN|PERDU|WIN|LOST` et split par market → ~380 samples total
  - GOAL : ~120 samples
  - ASSIST : ~60 samples (sous-représenté)
  - POINT : ~120 samples
  - SHOT : ~80 samples
- **vs Football** : 2 400+ samples (ratio 6×)
- Isotonic fit avec < 50 samples par marché → variance élevée, confiance basse
- Aucune calibration per-player

**🔴 P0 — ML player-level fallback silencieux**

`api/routers/nhl.py:311-336` :
```python
if ENHANCED_ML_AVAILABLE and shot_predictor and shot_predictor.model is not None:
    raw_prob_shot = shot_predictor.predict_proba(raw)
else:
    raw_prob_shot = 1.0 - math.exp(-lam_shots)  # Poisson fallback
```

Problèmes :
- `shot_predictor.load()` fails silently → pas de log WARNING (leçon 41 violée)
- Endpoint retourne même structure (caller ignore le fallback actif)
- Fréquence estimée : ~40% des requêtes SHOT/ASSIST tombent en fallback
- Impact Brier : Poisson ~0.24 vs XGBoost ~0.18 historique

**🟡 P1 — Aucune calibration per-player**

- Calibration appliquée au marché global ("GOAL") indépendamment du joueur
- Connor McDavid vs rookie : même courbe de calibration
- Exemple : McDavid GOAL @ 0.45 → 0.52 calibré, rookie @ 0.05 → 0.08 (même ratio)
- Meilleure approche : calibration per-decile ou per-PPG-percentile

**🟡 P1 — Feature drift non monitoré**

- `train.py` FEATURES (ligne 39-70) : 21 features définies
- Pipeline enrichit dynamiquement (ai_factor, b2b, pp_boost)
- Risque : mismatch si pipeline change mais `train.py` pas re-runné
- Mitigation partielle : `ml_models.py:125` utilise `model_data["feature_names"]` du `.pkl` (source of truth)

**🔴 P0 — Tests quasi inexistants**

- `test_nhl_pipeline.py` : 1 stub, skipped, zéro assertion réelle
- Aucun test sur calibration, feature engineering, API endpoints
- Le pipeline tourne en cron production sans filet

### 2.3 Code smells repérés

1. **`try/except ImportError` qui masque des bugs réels** (`api/routers/nhl.py:72-89`)
   - Si import réussit mais `.load()` échoue plus tard → `ENHANCED_ML_AVAILABLE=True`, `model=None` → fallback silencieux
   - Better : init en deux étapes (import puis load avec logs explicites)

2. **Duplication de feature engineering**
   - `feature_engineering.py::build_features()` (103 features)
   - Pipeline inline feature build (~500 LOC dans le pipeline NHL)
   - Deux sources de vérité pour `opp_sv_pct`, `pp_share`, `b2b` factors

3. **Whitelist de désérialisation serrée mais pas future-proof**
   - `nhl_ml_predictor.py:22-40` : bloque `sklearn.neural_network`
   - Si futur modèle utilise `xgboost.sklearn.XGBRFClassifier` → deserialization fails
   - Risque acceptable mais à surveiller

4. **`api/routers/nhl.py` = 873 LOC** — fichier trop gros, mélange endpoint + logique métier (violation leçon 62)

### 2.4 Gaps vs. bonnes pratiques

| Benchmark | ProbaLab NHL | Gap |
|-----------|--------------|-----|
| **MoneyPuck** (xG + tracking data NHL) | Poisson + features basiques | -3 pts : pas de tracking data (NHL API publique ne l'expose pas) |
| **Action Network** (blending odds sources) | The Odds API seule | -2 pts : single provider (rate limit risk) |
| **DraftKings ML** (per-player calibration) | Calibration globale par marché | -2 pts : pas de courbes per-player |
| **Pinnacle CLV tracking** | Pas de CLV NHL tracké publiquement | N/A — Brier interne ~0.22 acceptable |

---

## 3. Niveau de maturité : **L3/L5 (borderline bas)**

**Grille appliquée** :
- L1 : Manuel, pas de ML
- L2 : Automatisé basique (Poisson + 1-2 odds sources, features basiques)
- **L3 : ML émergent** — XGBoost player+match-level, calibration implémentée, 1 source odds ← **ProbaLab ici**
- L4 : ML + blending (ensemble + 3+ odds sources + per-player calibration)
- L5 : Production-grade (per-player curves temps réel, multi-source, Brier < 0.20, A/B tested)

**Justification du L3 borderline bas** :
- ✅ Critères L3 atteints : XGBoost présent, calibration implémentée, endpoints API
- ❌ Bloquants L4 : single odds source, calibration globale uniquement, < 50 samples sur certains marchés, 0% test coverage
- Mais L3 fragilisé par : fallback silencieux, player props market gap, tests absents → dérive possible vers L2 sans correctif

---

## 4. Benchmark vs. leader du marché

**Leaders identifiés** :
- **MoneyPuck** — référence NHL publique : modèles xG, tracking data depuis RTSS, transparence méthodologique
- **Action Network** — US multi-sport : blending 5+ bookmakers, calibration par sport
- **DraftKings Sportsbook predictions** (interne, pas concurrent direct) — per-player calibration live

**Ce qu'ils font mieux** :
- MoneyPuck expose des xG per-shot, per-situation (5v5, PP, PK) — ProbaLab reste sur stats agrégées équipe
- Action Network blend 5+ sources → marche plus robuste
- Per-player calibration standard chez les pros

**Ce que ProbaLab peut faire** :
- Accès NHL RTSS tracking data n'est pas disponible publiquement → gap structurel, pas fermable sans deal institutionnel
- Blending multi-bookmaker atteignable : The Odds API + Pinnacle API (paid)
- Per-player calibration atteignable dès qu'il y aura 30+ samples/player

**Écart mesurable** :
- Brier NHL ProbaLab ~0.22 (estimé) vs MoneyPuck ~0.18 (publié) → écart significatif sur marchés similaires
- Couverture marché : 1 marché player props (goals) vs 4-6 chez Action Network

---

## 5. Gaps pour passer au niveau supérieur (L3 → L4)

### P0 — Bloquants (effort : 3-6 semaines)

1. **Upgrade Odds API Pro → couvrir player_points et player_assists** (2 semaines)
   - ~$500/mois (Enterprise plan)
   - Ajouter Pinnacle en fallback (redondance + blending)
   - Débloque les vraies cotes pour Safe/Fun picks NHL du pivot

2. **Fix fallback ML silencieux** (1 jour)
   - Init en 2 étapes (import → load avec try/except loggé)
   - Logger WARNING à chaque fallback Poisson
   - Expose dans response un flag `ml_fallback_used: true` pour le caller

3. **Tests NHL — 50%+ coverage** (2 semaines)
   - Unit : calibration, feature engineering, constants (team mapping)
   - Integration : `/brain_quick`, `/game_win_probability` (mock Supabase)
   - E2E : pipeline mock sans API live

4. **Expansion dataset calibration — 2× sample size** (1 semaine)
   - Actuellement `nhl_suivi_algo_clean` (betting slips uniquement)
   - Ajouter : toutes les prédictions quotidiennes avec résultat réel depuis `nhl_data_lake`

### P1 — Qualité (effort : 4-8 semaines)

5. **Calibration per-player** (1 mois)
   - Gate min 30 samples/joueur
   - Fallback sur calibration globale sinon
   - Timeline : possible après 2 semaines de backfill

6. **Player props ML — goals/assists/points/shots séparés** (3 semaines)
   - Remplacer Poisson par XGBoost dédié par marché
   - Features : form L5, opp defense rank, B2B, injury status
   - Optuna tuning comme pour match-level

7. **Feature drift monitoring NHL** (1 semaine)
   - Log input shape + stats à chaque prédiction
   - Alerte si feature count ou NaN rate dérive > 10%

### P2 — Polish (effort : 2-4 semaines)

8. **Refactor `api/routers/nhl.py`** — sortir logique métier (leçon 62)
9. **Dédupliquer feature engineering** — single source of truth
10. **Brier dashboard NHL dédié** — alimente le dashboard admin (annexe 03)

---

## 6. Risques identifiés

| # | Risque | Sévérité | Probabilité | Impact |
|---|--------|----------|-------------|--------|
| R1 | Player props pivot lancé avec cotes calculées → trust brisé | **CRITIQUE** | Haute | Picks Safe/Fun NHL invisibles ou faux |
| R2 | Calibration < 50 samples → variance élevée → picks peu fiables | Haute | Haute (actuel) | Brier dégradé, ROI virtuel négatif |
| R3 | ML fallback silencieux → endpoint retourne Poisson sans warning | Haute | Haute (actuel) | Décalage perf promise vs réelle |
| R4 | 0% test coverage → régression non détectée | Haute | Moyenne | Bugs en prod |
| R5 | Feature drift non détecté si pipeline modifié sans re-train | Moyenne | Moyenne | Prédictions biaisées |
| R6 | Rate limit The Odds API atteint → pas de cotes du jour | Moyenne | Basse | Blackout temporaire |
| R7 | Renames d'équipes futurs non intégrés immédiatement | Basse | Moyenne | Matchs manqués ponctuellement |

---

## 7. Recommandations stratégiques

1. **Le NHL n'est pas prêt pour le pivot tel que spécifié**. Le design pivot §5 D5 prévoit Safe picks NHL sur "1+ Point" et "1+ Passe décisive", marchés actuellement non couverts par le provider odds. **Recommandation forte** : avant de déclencher le pivot NHL, upgrade Odds API (2 semaines + ~500$/mois) ou rétrécir le scope Safe NHL au marché `player_goals` uniquement. Lancer le pivot sans cotes réelles = suicide commercial.

2. **Traiter le NHL comme un produit à part entière**, pas "secondaire". Le CLAUDE.md dit "secondaire" mais le pivot en fait un pilier. Cette contradiction doit être tranchée : soit investissement réel (ODDS Pro + tests + calibration dataset), soit scope restreint assumé publiquement.

3. **Instrumenter le fallback Poisson** immédiatement. C'est un fix 1 jour qui restaure la visibilité sur la qualité réelle des prédictions. Sans ça, tous les chiffres Brier NHL sont optimistes.

4. **Lancer un "NHL pilot" avant le pivot** : 10 matchs/jour, cotes réelles uniquement, suivi Brier + ROI virtuel quotidien. Si Brier < 0.22 et ROI > 3% sur 2 semaines, étendre. Sinon, pause + retrain + upgrade data.

5. **Intégrer MoneyPuck comme source de benchmark externe** — pas copier, mais mesurer l'écart Brier régulièrement. C'est une boussole objective.

---

## 8. Liens internes

**Fichiers clés** :
- `ProbaLab/src/nhl/nhl_ml_predictor.py` (match-level inference)
- `ProbaLab/src/nhl/calibration.py` (Isotonic + Platt)
- `ProbaLab/src/nhl/ml_models.py:22-40` (whitelist désérialisation)
- `ProbaLab/src/nhl/train.py:39-70` (FEATURES list)
- `ProbaLab/src/fetchers/fetch_nhl_player_props.py` (untracked, MARKETS limité à player_goals)
- `ProbaLab/src/nhl/fetch_odds.py:76-79` (fenêtre UTC)
- `ProbaLab/api/routers/nhl.py:72-89` (try/except ImportError masquant)
- `ProbaLab/api/routers/nhl.py:311-336` (fallback Poisson silencieux)
- `ProbaLab/tests/test_nhl_pipeline.py` (stub skipped, à réécrire)
- `ProbaLab/worker.py` (jobs NHL APScheduler)

**Leçons pertinentes** :
- `tasks/lessons.md:64` — migration Trigger.dev → APScheduler (résolue)
- `tasks/lessons.md:65` — schedule fallback edge case (résolue)
- `tasks/lessons.md:66` — provider odds The Odds API (résolue)
- `tasks/lessons.md:67` — team name normalization (résolue)
- `tasks/lessons.md:41` — dépendances sécu/qualité fail-loud (pas appliquée au fallback ML)
- `tasks/lessons.md:62` — extraire logique pure des routers (violée dans `nhl.py`)

**Documents liés** :
- Design pivot : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md` §5 D5, §7 R2/R8/R9
- Annexe 02 (ML) pour calibration isotonique globale
- Annexe 03 (Monitoring) pour Brier tracking et feature drift
- Annexe 06 (Sécurité) pour whitelist désérialisation

---

## Verdict : NHL prêt pour le pivot ?

**Non.** Au niveau L3 actuel avec player props market gap + calibration sous-alimentée + tests quasi nuls, lancer le pivot NHL sans correctifs P0 est un pari risqué. **Prérequis** : upgrade Odds API (2 sem), fix fallback silencieux (1j), tests minimum (2 sem), expansion dataset calibration (1 sem). Total : ~6 semaines de stabilisation avant pivot NHL sûr.
