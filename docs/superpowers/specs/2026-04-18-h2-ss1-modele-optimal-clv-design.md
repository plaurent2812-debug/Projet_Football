# H2 — SS1 : Modèle Optimal & Pipeline CLV — Design

> **Parent project** : H2 "Prouver l'Edge" (décomposé en 3 sous-projets SS1/SS2/SS3)
> **This spec** : **SS1 uniquement** — modèle ML optimal + pipeline CLV automatisé
> **Next specs** : SS2 (dashboard admin perf), SS3 (refonte UX user) — hors scope

---

## Contexte

Issu de l'audit expert 2026-04-17 (`docs/audit/2026-04-17/13_audit_expert_probas.md`, score 5.5/10) qui a identifié 3 problèmes majeurs :

1. **Aucune mesure CLV** en production → aucune preuve que le modèle bat le marché
2. **6 features `market_*`** dans `FEATURE_COLS` → ML apprend le marché, circular reasoning
3. **Poids `WEIGHT_MARKET = 0.20`** trop faible (leçon 53 documentée mais pas appliquée)

La question centrale que SS1 doit trancher : **est-ce que ProbaLab bat le marché, oui ou non ?**

---

## 1. Vue d'ensemble

**Nom** : H2-SS1 — Modèle Optimal & Pipeline CLV

**Objectif** : Entraîner et déployer la meilleure variante du modèle de probas foot + NHL, avec un pipeline CLV automatisé qui prouve (ou infirme) qu'il bat le marché.

**Success criteria (mesurable en 3-4 semaines)** :
1. The Odds API Dev (30$/mois) intégré, cotes Pinnacle + Betclic + Winamax + Unibet + ZEbet fetchées 2× par jour (opening + closing) pour foot top-5 + NHL
2. Tables `closing_odds` créée + `model_health_log` étendue, populées quotidiennement
3. Job cron `job_daily_clv_snapshot` mesure CLV par jour/ligue/marché vs Pinnacle ET vs moyenne FR
4. 4 variantes ML entraînées sur holdout strict (6 derniers mois) : `baseline` (actuel), `rebalanced` (`WEIGHT_MARKET=0.40`), `pure` (sans features `market_*`), `pure_rebalanced`
5. Variante gagnante déployée en prod (critère : meilleur Brier **ET** CLV ≥ baseline)
6. Ajout 8+ features manquantes : `xg_against`, `shots_against`, `pace_index`, `set_pieces_rate`, `opponent_xg_against`, `form_vs_weighted`, `home_away_form_split`, `market_volatility`
7. Feature drift KS test quotidien + alerte Telegram si dérive
8. Endpoint `GET /api/value-bets` opérationnel (consommé par SS3 plus tard) avec badge "value bet ≥ 5%" calculé sur meilleure cote dispo entre 5 bookmakers

**Non-objectifs (explicitement hors scope)** :
- Dashboard admin CLV visuel → **SS2**
- Refonte UX user (homepage, page match) → **SS3**
- Scraping player_points/assists/shots → impossible, tracké en accuracy only
- Page publique `/methodology` enrichie → décision owner transparence C (reportée)
- Calibration per-league — reporté à plus tard (pas dans ce spec)
- NBA, tennis, autres sports

---

## 2. Décisions owner figées (brainstorming 2026-04-17/18)

| # | Sujet | Décision |
|---|---|---|
| 1 | Sous-projet prioritaire | A — Prouver l'edge (modèle + monitoring CLV) |
| 2 | Benchmark CLV | D — Pinnacle (benchmark interne) + moyenne bookmakers FR (pragmatique) |
| 3 | Source cotes | The Odds API Dev — **30$/mois budget validé** |
| 4 | Méthode | "A compressé" — 4 modèles en parallèle sur holdout commun, 4 semaines |
| 5 | Transparence | C — interne uniquement (dashboard admin, pas de page publique CLV) |
| 6 | Scope marchés | Foot 8 ligues (1X2, BTTS, O/U 1.5/2.5/3.5) + NHL (moneyline, totals, player goals/assists/points/shots) |
| 7 | Positionnement | Probas globales avec badge value bet ≥ 5%, Safe/Fun/Value relégué en feature premium secondaire |
| 8 | Seuil value bet | 5% user-facing, 3% admin/monitoring interne |
| 9 | Kelly fractional | 0.25 (conservateur) |
| 10 | CLV sur NHL | Tracké sur moneyline/totals/goals (cotes dispo). Points/assists/shots tracké en **Top-1/Top-3 accuracy** (pas de cotes dispo) |

**Contrainte budget** : 50 €/mois max externes. Répartition :
- The Odds API Dev : ~28 € (30 $)
- Marge : ~22 € (pour alertes, autres APIs futures)

---

## 3. Architecture

### 3.1 Pipeline en 4 étages

```
┌────────────────────────────────────────────────────────────────┐
│ Étage 1 — ODDS INGESTION (fetch + store)                       │
│   The Odds API Dev → closing_odds table                        │
│   2 snapshots/jour : opening (T-24h) + closing (T-30min)       │
├────────────────────────────────────────────────────────────────┤
│ Étage 2 — MODEL TRAINING (offline, reproductible)              │
│   4 variantes XGBoost sur même holdout                         │
│   Comparaison Brier / LogLoss / ECE / CLV                      │
│   Sélection du meilleur → export artifacts                     │
├────────────────────────────────────────────────────────────────┤
│ Étage 3 — CLV MEASUREMENT (daily cron)                         │
│   Join predictions + closing_odds + actual_results             │
│   Compute CLV per match / league / market / bookmaker          │
│   Upsert → model_health_log                                    │
├────────────────────────────────────────────────────────────────┤
│ Étage 4 — VALUE BET DETECTION (online, per-match)              │
│   For each match + market:                                     │
│     best_odds = max(bookmaker_odds across 5 books)             │
│     edge = (proba_model × best_odds) - 1                       │
│     if edge ≥ 5%: flag value_bet                               │
│   Expose via API endpoint → consumed by SS3 UI                 │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Composants par étage

**Étage 1 — Odds Ingestion** (nouveau module)
- `src/fetchers/odds_ingestor.py` — wrapper The Odds API Dev (quota tracking, retry, dedup, idempotence via `source_request_id`)
- `src/fetchers/bookmaker_registry.py` — registre bookmakers ciblés (Pinnacle, Betclic, Winamax, Unibet, ZEbet) avec mapping The Odds API keys
- Jobs cron :
  - `job_odds_opening_snapshot` à 08:00 UTC (fetch cotes matchs J+1)
  - `job_odds_closing_snapshot` triggered T-30min avant kickoff (via APScheduler ad-hoc scheduling)

**Étage 2 — Model Training** (extend existing)
- `src/training/train.py` — modifié pour accepter paramètre `variant` (baseline | rebalanced | pure | pure_rebalanced)
- `src/training/variants.py` (nouveau) — définit `FEATURE_COLS` et config par variante
- `src/training/backtest_variants.py` (nouveau) — orchestre les 4 entraînements sur holdout commun, produit rapport `reports/variants_YYYY-MM-DD.md`
- Nouvelles features (ajoutées à `constants.py`) :
  - `xg_against_home`, `xg_against_away`
  - `shots_against_home`, `shots_against_away`
  - `pace_index_home`, `pace_index_away` (tempo/pressing proxy)
  - `set_pieces_rate_home`, `set_pieces_rate_away`
  - `opponent_xg_against` (crossed feature)
  - `form_vs_weighted` (forme × SOS)
  - `home_away_form_split` (forme domicile seulement vs extérieur seulement)
  - `market_volatility` (écart-type cotes entre bookmakers — **utilisé uniquement dans variantes `*_market`**, pas dans `pure`)

**Étage 3 — CLV Measurement** (extend monitoring)
- `src/monitoring/clv_engine.py` (nouveau) — calcul CLV rigoureux (overround removal per-market, EV calculation, Kelly fractional)
- `src/monitoring/alerting.py` — ajout alertes :
  - CLV < -1% sur 7 jours glissants → WARNING
  - CLV < -3% sur 7 jours glissants → CRITICAL
  - Feature drift KS p < 0.01 sur > 5 features → CRITICAL
- `src/monitoring/feature_drift.py` (nouveau) — KS test training vs last 30d prod
- Job cron :
  - `job_daily_clv_snapshot` à 09:00 UTC (après résultats FT)
  - `job_feature_drift_check` à 09:30 UTC

**Étage 4 — Value Bet Detection** (nouveau module)
- `src/models/value_detector.py` (nouveau) — logique edge calculation multi-bookmakers, Kelly fractional 0.25 (réutilise code existant `stats_engine.py:1748-1775`)
- `api/routers/value_bets.py` (nouveau) — endpoint `GET /api/value-bets?date=YYYY-MM-DD` pour SS3
- Intègre clamping existant et calibration de `stats_engine.py`

### 3.3 Isolation & interfaces

Chaque étage expose une **interface stable**, les autres ne dépendent pas de son implémentation interne :

| De | Vers | Interface |
|---|---|---|
| Étage 1 | Étages 2/3/4 | Table `closing_odds` (schéma stable section 4.1) |
| Étage 2 | Étages 3/4 | Artifact ML (`.ubj` + `.pkl` metadata, format existant) |
| Étage 3 | SS2 dashboard | Table `model_health_log` (schéma stable section 4.2) |
| Étage 4 | SS3 UI | Endpoint REST `GET /api/value-bets` (contrat JSON section 4.3) |

**Conséquence** : SS2 et SS3 peuvent démarrer leur dev dès que les interfaces sont stables (pas besoin d'attendre que tout SS1 soit fini).

### 3.4 Data flow quotidien

```
07:00 UTC — job_data_pipeline (existant, inchangé)
  ↓ fetch results FT + fixtures à venir

08:00 UTC — job_odds_opening_snapshot (NOUVEAU)
  ↓ fetch cotes matchs J+1 via The Odds API Dev
  ↓ insert closing_odds (snapshot_type='opening')

09:00 UTC — job_daily_clv_snapshot (NOUVEAU)
  ↓ read predictions J-1 + closing_odds J-1 + results J-1
  ↓ compute CLV per match/market/bookmaker
  ↓ upsert model_health_log
  ↓ alerte si CLV < seuils

09:30 UTC — job_feature_drift_check (NOUVEAU)
  ↓ KS test features last 30d vs training distribution
  ↓ alerte Telegram si dérive

10:00 UTC — job_brain (existant, augmenté)
  ↓ predict matchs J (avec variant gagnant déployé)
  ↓ call value_detector pour chaque match
  ↓ stocker value bets en DB (pour consommation API)

T-30min — job_odds_closing_snapshot (NOUVEAU, triggered)
  ↓ fetch cotes matchs dans les 30min
  ↓ insert closing_odds (snapshot_type='closing')
```

---

## 4. Data model

### 4.1 Nouvelle table `closing_odds`

```sql
CREATE TABLE closing_odds (
  id BIGSERIAL PRIMARY KEY,
  sport TEXT NOT NULL CHECK (sport IN ('football','nhl')),
  fixture_id TEXT NOT NULL,
  league_id INT,
  match_start TIMESTAMPTZ NOT NULL,
  bookmaker TEXT NOT NULL,
    -- 'pinnacle'|'betclic'|'winamax'|'unibet'|'zebet'
  market TEXT NOT NULL,
    -- '1x2'|'btts'|'over_1_5'|'over_2_5'|'over_3_5'
    -- |'moneyline'|'totals_nhl'|'player_goals'
  selection TEXT NOT NULL,
    -- 'home'|'draw'|'away'|'yes'|'no'|'over'|'under'|'<player_name>'
  line NUMERIC,
  odds NUMERIC NOT NULL,
  implied_prob NUMERIC NOT NULL,
  overround NUMERIC,
  snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('opening','closing','intraday')),
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_request_id TEXT,
  UNIQUE (fixture_id, bookmaker, market, selection, line, snapshot_type)
);

CREATE INDEX idx_closing_odds_fixture ON closing_odds (fixture_id);
CREATE INDEX idx_closing_odds_snapshot ON closing_odds (snapshot_at DESC);
CREATE INDEX idx_closing_odds_bookmaker_market ON closing_odds (bookmaker, market);

ALTER TABLE closing_odds ENABLE ROW LEVEL SECURITY;
CREATE POLICY "closing_odds_service_role" ON closing_odds
  FOR ALL TO service_role USING (true) WITH CHECK (true);
```

### 4.2 Extension `model_health_log` (migration 050 existante)

```sql
ALTER TABLE model_health_log
  ADD COLUMN IF NOT EXISTS clv_vs_pinnacle_1x2 NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_pinnacle_btts NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_pinnacle_over25 NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_pinnacle_nhl_ml NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_pinnacle_nhl_goals NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_fr_avg_1x2 NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_fr_avg_btts NUMERIC,
  ADD COLUMN IF NOT EXISTS clv_vs_fr_avg_over25 NUMERIC,
  ADD COLUMN IF NOT EXISTS n_matches_clv INT,
  ADD COLUMN IF NOT EXISTS feature_drift_ks JSONB,
  ADD COLUMN IF NOT EXISTS variant_id TEXT;
```

### 4.3 Contrat API `GET /api/value-bets`

```json
{
  "date": "2026-04-18",
  "matches": [
    {
      "fixture_id": "123456",
      "sport": "football",
      "league": "Ligue 1",
      "home_team": "PSG",
      "away_team": "Marseille",
      "kickoff": "2026-04-18T19:00:00Z",
      "probabilities": {
        "1x2": { "home": 62.3, "draw": 22.1, "away": 15.6 },
        "btts": { "yes": 58.4, "no": 41.6 },
        "over_2_5": { "over": 54.2, "under": 45.8 }
      },
      "best_odds": {
        "1x2.home": { "bookmaker": "winamax", "odds": 1.48, "implied": 67.6 },
        "1x2.draw": { "bookmaker": "betclic", "odds": 4.80, "implied": 20.8 },
        "1x2.away": { "bookmaker": "unibet", "odds": 7.20, "implied": 13.9 },
        "btts.yes": { "bookmaker": "winamax", "odds": 1.68, "implied": 59.5 },
        "over_2_5.over": { "bookmaker": "betclic", "odds": 1.82, "implied": 54.9 }
      },
      "value_bets": [
        {
          "market": "1x2",
          "selection": "draw",
          "proba_model": 22.1,
          "best_odds": 4.80,
          "bookmaker": "betclic",
          "edge_pct": 6.08,
          "kelly_fractional": 0.015
        }
      ]
    }
  ]
}
```

### 4.4 Dataset entraînement — holdout config

- **Train set** : toutes saisons ≤ 2025-03 (foot), ≤ 2026-03 (NHL)
- **Holdout test set** : 2025-04 → 2025-10 (6 mois foot), équivalent NHL
- Split temporel strict — aucune fuite
- Stocké comme fichiers parquet versionnés : `ProbaLab/data/backtests/train_YYYY.parquet`, `holdout_YYYY.parquet`
- Détection auto via tests `test_train_no_leakage.py` + `test_walk_forward.py` existants

---

## 5. Error handling

| Composant | Erreur | Stratégie |
|---|---|---|
| The Odds API | Timeout / 500 | Retry exponential (3x : 1s, 2s, 4s), timeout 30s |
| The Odds API | Quota mensuel dépassé | Log CRITICAL, alerte Telegram, arrêt ingestion jusqu'au mois suivant |
| The Odds API | 3 fails consécutifs | Circuit breaker (pause 1h), alerte Telegram |
| Odds ingestor | Duplicate insert | UNIQUE constraint ignore (ON CONFLICT DO NOTHING) |
| CLV compute | `closing_odds` manquant pour un bookmaker | Skip ce bookmaker (log warning), fallback opening si closing indispo avec flag dans metadata |
| Training variants | Variante échoue | Try/except isolé, rapport final liste succès/échecs, ne bloque pas les autres |
| Value bet detection | < 3 bookmakers dispos pour un marché | Skip value bet flagging (pas assez de données) |
| Feature drift | KS test fail > 5 features | Alerte Telegram CRITICAL, continue quand même (pas de blocage prod) |
| Rollback variante | Brier dégrade > 5% sur 7j glissants | Alerte CRITICAL, procédure manuelle documentée (pas d'auto-rollback) |

**Principe général** : fail-loud sur tous les composants critiques (leçon 41), retry sur I/O externes (leçon 16), jamais de fallback silencieux (leçon 72).

---

## 6. Testing strategy

### 6.1 Unit tests (obligatoires)
- `tests/test_odds_ingestor.py` — parsing The Odds API JSON, dedup logic, quota tracking
- `tests/test_bookmaker_registry.py` — mapping keys, aliases
- `tests/test_clv_engine.py` — CLV math (overround removal, EV calculation, edge cases)
- `tests/test_value_detector.py` — best odds selection, edge calculation, Kelly, < 3 bookmakers skip
- `tests/test_feature_drift.py` — KS test correct, threshold handling

### 6.2 Integration tests
- `tests/test_daily_clv_snapshot.py` — end-to-end job cron avec fixtures mockées (predictions + closing_odds + results)
- `tests/test_variants_training.py` — 4 variantes entraînées sur micro-dataset synthétique, rapport produit
- `tests/test_value_bets_endpoint.py` — endpoint API répond avec contrat JSON correct

### 6.3 Anti-leakage
- **Étendre** `tests/test_train_no_leakage.py` → bloquer aussi features futures :
  - Détecter `team_strengths` calculé sur full saison (future leak)
  - Assurer `match_team_stats` filtré à `match_date < fixture.date`
- Tests AST existants conservés (eval_set, sample_weight)

### 6.4 Property tests
- Probas 1X2 somment à 100 ±0.5 (existant, à maintenir)
- CLV dans [-100%, +100%]
- `best_odds` ≥ 1.01 (aucune cote négative)
- Kelly fractional dans [0, 0.25] (cap par 0.25)

### 6.5 Coverage targets
- Maintenir global ≥ 21% (CI actuel)
- Viser 70% sur `src/monitoring/clv_engine.py`, `src/monitoring/feature_drift.py`, `src/models/value_detector.py`

---

## 7. Budget, timing, infra

### 7.1 Budget externe

| Item | Coût mensuel |
|---|---|
| The Odds API Dev | ~28 € (30 $) |
| **Total engagé** | **~28 €** |
| **Marge budget 50 €** | **~22 €** |

### 7.2 Quota API

- Req théoriques/mois : ~9 600 (foot top-5 × 2 snapshots × 5 bookmakers × 4 marchés + NHL équivalent)
- Quota Dev : 20 000
- **Marge 2×** — confortable, on peut ajouter 1-2 bookmakers ou marchés plus tard sans upgrader

### 7.3 Storage Supabase

- `closing_odds` estimé : ~3M lignes/an × 150 bytes ≈ 450 MB/an
- Free tier Supabase : 500 MB DB → **suffit 1 an**, rotation ou archivage à prévoir après

### 7.4 Compute

| Job | Fréquence | Durée estimée |
|---|---|---|
| `job_odds_opening_snapshot` | Daily 08:00 UTC | ~2 min |
| `job_odds_closing_snapshot` | Triggered T-30min | ~30 sec par vague |
| `job_daily_clv_snapshot` | Daily 09:00 UTC | ~5 min |
| `job_feature_drift_check` | Daily 09:30 UTC | ~1 min |
| `backtest_variants` (4 variantes) | Manuel, one-shot | ~1 h total |

### 7.5 Calendar time

3-4 semaines × 5 h/sem solopreneur = **15-20 h dev actif**, livraison visée **mi-mai 2026**.

---

## 8. Risques identifiés

| # | Risque | Sévérité | Mitigation |
|---|---|---|---|
| R1 | The Odds API bookmakers FR non dispos comme attendu | Moyenne | Vérifier endpoint `/v4/sports/{sport}/odds` avec param `bookmakers=betclic,winamax,...` avant d'investir en dev |
| R2 | Variante `pure` (sans market features) dégrade Brier de > 1 point | Moyenne | Si dégradation, garder `market_volatility` seul (feature dérivée, pas directement prior marché), refit |
| R3 | CLV baseline négatif franc (-3% ou pire) | Basse mais impact CRITIQUE | Alerte Telegram + transparence interne, pivoter pitch produit vers "outil calibré + bankroll" plutôt que "edge" |
| R4 | Quota The Odds API dépassé mi-mois | Basse | Circuit breaker + réduction snapshots closing à top-3 ligues seulement en fallback |
| R5 | Fuite temporelle subtile dans features (team_strengths future-leak) | Haute | Test AST étendu + audit manuel `stats_engine.py:334-492` avant deploy |
| R6 | Variante gagnante change les probas user-visible → plaintes | Moyenne | Annonce préalable + option rollback manuel documentée |
| R7 | Feature drift non détecté → probas dégradent silencieusement | Haute | Alerte Telegram sur KS p-value + dashboard SS2 pour visibilité continue |

---

## 9. Dépendances

**Externes** :
- The Odds API Dev subscription actif (30 $/mois)
- Railway worker opérationnel (cron jobs)
- Supabase DB accessible en écriture (service_role key)

**Internes** :
- Sprint H1 mergé (monitoring_alerts, model_health_log, pré-requis datetime UTC) ✅
- `stats_engine.py` + `ml_predictor.py` + `calibrate.py` stables
- Tests CI verts (pytest 380+ tests passent)

**Pas de dépendance sur** :
- SS2 (dashboard admin — consomme mais ne produit pas)
- SS3 (refonte UX — consomme mais ne produit pas)

---

## 10. Cohérence avec décisions antérieures

- ✅ Cohérent avec **budget 50 €/mois max** (décision owner 2026-04-17)
- ✅ Cohérent avec **scope NHL = player_goals + moneyline/totals** (pivot) et nouveau scope **player_points/assists/shots** (décision owner 2026-04-18, mesurés en accuracy only)
- ✅ Cohérent avec **prix 14,99 €/mois** (pas impacté)
- ✅ Cohérent avec **transparence interne only** (pas de page publique CLV dans ce spec)
- ✅ Étend Sprint H1 (qui a posé les fondations : `model_health_log`, job monitoring, monitoring alerts)

---

## 11. Prochaine étape

**Demain (2026-04-19)** : invoquer `writing-plans` pour produire le plan d'exécution tâche-par-tâche de SS1 avec :
- Découpage en tasks 2-5 min chacun
- TDD systématique (test d'abord pour chaque composant)
- Exact file paths, code snippets complets, no placeholders
- Commits fréquents
- Parcours idéal : Étage 1 → Étage 3 → Étage 4 → Étage 2 (les étages 3 et 4 peuvent livrer valeur avec baseline, étage 2 vient en finalisation)

**Après SS1** : SS2 (dashboard admin perf) puis SS3 (refonte UX user).
