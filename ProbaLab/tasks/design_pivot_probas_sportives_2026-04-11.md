# Design — Pivot "Spécialiste en probabilités sportives"

**Date** : 2026-04-11
**Auteur** : Claude Opus 4.6 (brainstormé avec l'owner)
**Status** : ready for plan
**Branche cible** : `feat/pivot-probas-sportives` (à créer depuis `main` après merge de `chore/audit-2026-04-10`)

---

## 1. Contexte et problème

Le site ProbaLab est aujourd'hui positionné comme une plateforme de **value betting** (EV+, Kelly, ROI). La feature principale est "Paris du Soir" qui affiche les meilleures opportunités value bet du jour avec edge calculé.

**Problème identifié par l'owner** :

1. Le positionnement value betting est trop étroit et ne reflète pas la richesse du moteur de probabilités (Poisson + ELO + ML + Gemini + 50+ features)
2. Les users qui ne sont pas des bettors avancés sont rebutés par le jargon (edge, Kelly, bankroll)
3. La feature "Paris du Soir" est enfouie au 4e onglet (cf leçon 55)
4. Il manque des paris "accessibles" (cotes proches de 2) et des paris "fun" (cotes élevées, coups de cœur)

## 2. Objectifs

1. **Repositionner** le site comme spécialiste en probabilités sportives foot + NHL
2. **Dashboard home unifié** : probas foot + Top 3 NHL + bandeau sticky "Paris du Jour"
3. **3 catégories de picks quotidiens** avec tracking WIN/LOSS et ROI :
   - Safe : 3 foot + 3 NHL, cote ∈ [1.80, 2.20]
   - Fun : 1 parlay foot (4 legs) + 1 parlay NHL (4 legs), total ~19.4
   - Value bet : 0-5 par sport, seuil EV > 3%
4. **Badge discret "💎 Value"** sur les cartes de match quand max edge > 5%
5. **Tracking uniforme** : bankroll virtuel 10€/pick, win rate + ROI par catégorie, historique complet

## 3. Non-goals (scope exclu explicitement)

- Pas de feature "Kelly Criterion user-facing" (reste en backend pour les value_bet mais non affiché sur la home)
- Pas de refonte du moteur de probabilité (on garde Poisson/ELO/ML/Gemini tels quels)
- Pas de nouveau sport (foot + NHL seulement)
- Pas de monétisation premium sur les picks du jour (tout est public, leçon 55)
- Pas de migration de schéma lourde (seulement ajout de colonnes à `best_bets`)
- Pas de refactor de `api/routers/best_bets.py` au-delà du strict nécessaire (il vient d'être nettoyé en avril)

## 4. Décisions de design (brainstormées avec l'owner)

| # | Décision |
|---|---|
| D1 | Fusion : réutiliser `best_bets` comme table centrale, avec `category ∈ {safe, fun, value_bet}` |
| D2 | Value bet quantité variable : 0-5 par sport, seuil EV > 3% (pas de floor, "aucune opportunité" est acceptable) |
| D3 | Safe : range stricte cote ∈ [1.80, 2.20], classement par proba modèle desc |
| D4 | Fun : parlay 4 legs, chaque leg à cote ~2.10, total ~19.4 (format uniforme foot+NHL) |
| D5 | Foot safe = multi-marchés libre (1X2 + DC + BTTS + O/U 2.5) ; NHL safe = player props "1+ Point" et "1+ Passe décisive" |
| D6 | Tracking = bankroll virtuel 10€/pick uniforme foot+NHL, historique complet jamais reset (nécessite upgrade The Odds API Pro pour vraies cotes NHL player props) |
| D7 | Home = dashboard unifié scrollable, sticky top "Paris du Jour" |
| D8 | Badge value bet discret `💎 Value` sans chiffre, seuil edge > 5% |

**Assumptions (taken as defaults en l'absence de réponse explicite)** :
- A1 : Backfill des `best_bets` existants → `category='value_bet'` (sauf ceux dont `notes LIKE 'Auto — Fun%'` qui deviennent `category='fun'`)
- A2 : Picks manuels admin sont gardés avec `is_auto=false`, trackés séparément du tracking public
- A3 : Page Performance est publique (non gated premium)
- A4 : Mise virtuelle par défaut = 10€/pick (stockée dans `best_bets.virtual_stake`, modifiable par l'admin)

## 5. Architecture

### 5.1 Vue d'ensemble

```
┌─ COLLECTE (inchangé sauf +1 fetcher) ────────────────┐
│ APScheduler worker.py                                │
│                                                      │
│  07:00  job_data_pipeline        (foot data)         │
│  07:45  job_fetch_odds           (foot odds)         │
│  10:00  job_brain                (foot probas)       │
│  16:00  job_nhl_pipeline         (NHL probas)        │
│  16:15  job_nhl_fetch_odds       (NHL h2h+totals)    │
│  16:20  job_nhl_fetch_player_props ← NOUVEAU         │
│  23:00  job_nhl_pipeline         (re-run compos)     │
│  23:15  job_nhl_fetch_odds                           │
│  23:20  job_nhl_fetch_player_props ← NOUVEAU         │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ GÉNÉRATION (refactor) ──────────────────────────────┐
│ src/ticket_generator.py                              │
│                                                      │
│  12:00  job_generate_daily_picks_foot                │
│         ├─ generate_safe_foot(date)   → 3 picks      │
│         ├─ generate_fun_foot(date)    → 1 parlay     │
│         └─ generate_value_foot(date)  → 0-5 picks    │
│                                                      │
│  17:00  job_generate_daily_picks_nhl                 │
│  23:30  (2e run post-compos)                         │
│         ├─ generate_safe_nhl(date)    → 3 picks      │
│         ├─ generate_fun_nhl(date)     → 1 parlay     │
│         └─ generate_value_nhl(date)   → 0-5 picks    │
│                                                      │
│  Chaque générateur :                                 │
│    DELETE WHERE date+sport+category+is_auto=true     │
│    INSERT avec is_auto=true, virtual_stake=10        │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ STOCKAGE ───────────────────────────────────────────┐
│ Supabase: best_bets (existante, 3 colonnes ajoutées) │
│ Supabase: nhl_fixtures, nhl_odds (existantes)        │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ RÉSOLUTION (adapté) ────────────────────────────────┐
│  06:00  job_resolve_bets                             │
│    → lit nhl_data_lake pour player props NHL        │
│    → lit fixtures pour foot                          │
│    → update best_bets.result + roi_cents             │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ SERVICE API (nouveaux endpoints) ───────────────────┐
│  GET /api/picks/daily?date=X                         │
│  GET /api/picks/performance?days=30                  │
│  GET /api/matches/foot-today  (avec value_bet_edge)  │
│  GET /api/nhl/daily-top3                             │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ FRONTEND (refonte home + Performance) ──────────────┐
│  HomeDashboard.tsx (remplace ParisDuSoir.tsx)        │
│  ├─ PicksDuJourSticky.tsx                            │
│  ├─ MatchCardWithBadge.tsx (foot)                    │
│  └─ NHLCardTop3.tsx                                  │
│                                                      │
│  Performance.tsx (refondue, par catégorie)           │
└──────────────────────────────────────────────────────┘
```

### 5.2 Data model

**Migration Supabase** :

```sql
-- Phase 1.1 : extend best_bets
ALTER TABLE best_bets
  ADD COLUMN IF NOT EXISTS category text
    CHECK (category IN ('safe', 'fun', 'value_bet')),
  ADD COLUMN IF NOT EXISTS virtual_stake numeric DEFAULT 10,
  ADD COLUMN IF NOT EXISTS is_auto boolean DEFAULT false;

-- Backfill existing auto picks
UPDATE best_bets
SET category = CASE
    WHEN notes LIKE 'Auto — Fun%' THEN 'fun'
    ELSE 'value_bet'
  END,
  is_auto = (notes LIKE 'Auto —%')
WHERE category IS NULL;

-- Index for perf page queries
CREATE INDEX IF NOT EXISTS idx_best_bets_cat_sport_date
  ON best_bets(category, sport, date DESC)
  WHERE is_auto = true;
```

### 5.3 Générateurs (signature + comportement)

Tous les générateurs vivent dans `src/ticket_generator.py` comme fonctions pures, testables isolément. Chacun :

1. Charge les données nécessaires (délègue à helpers `_load_foot_data` / `_load_nhl_data` existants)
2. Applique ses filtres spécifiques
3. Retourne une `list[dict]` ou `dict` (pour fun = parlay)
4. N'écrit **jamais** directement en DB (séparation pure/impure)

La fonction impure `save_daily_picks(date, sport)` appelle les 3 générateurs et fait le delete-then-insert idempotent.

#### generate_safe_foot(date: str) → list[dict]

```python
def generate_safe_foot(date: str) -> list[dict]:
    """3 picks foot safe, cote ∈ [1.80, 2.20], tri par proba modèle desc.

    Markets autorisés : 1X2, Double Chance, BTTS, Over/Under 2.5.
    Stratégie : pour chaque match, on regarde tous les marchés, on garde
    les picks dont la cote est dans la range, puis on trie par proba
    modèle et on prend le top 3 (1 pick max par match).
    """
```

#### generate_fun_foot(date: str) → dict | None

```python
def generate_fun_foot(date: str) -> dict | None:
    """1 parlay foot 4 legs, total ~19.4.

    Stratégie : sélectionner 4 picks sur matchs différents avec
    cote ∈ [1.95, 2.25] chacun et proba modèle >= 55% pour chaque
    leg. Retourne dict avec legs + total_odds, ou None si pas assez
    de candidats.
    """
```

#### generate_value_foot(date: str) → list[dict]

```python
def generate_value_foot(date: str) -> list[dict]:
    """0-5 picks foot avec EV > 3%, cap 5, tri par edge desc.

    Reuse la logique EV existante (best_bets_logic), mais avec les
    seuils de la nouvelle stratégie : MIN_EDGE=0.03, MAX_EDGE=0.30.
    """
```

Les 3 NHL suivent le même pattern avec adaptations :
- `generate_safe_nhl` : lit `top_players` dans `nhl_fixtures.stats_json`, filtre sur `prob_point >= 50 OR prob_assist >= 35`, cote (réelle si dispo, sinon implicite) ∈ [1.80, 2.20]
- `generate_fun_nhl` : 4 legs de type goal/assist mélangés, joueurs différents, cote ~2.10 chacun
- `generate_value_nhl` : EV > 3% sur tous marchés player props

### 5.4 Endpoints API

| Endpoint | Method | Auth | Retour (JSON simplifié) |
|---|---|---|---|
| `/api/picks/daily` | GET | public | `{date, sports: {football: {safe:[], fun:{}, value_bet:[]}, nhl: {...}}}` |
| `/api/picks/performance` | GET | public | `{days, by_category: {...}, by_day: [...], bankroll_virtuel: 10}` |
| `/api/matches/foot-today` | GET | public | `[{match, probas:{}, markets:{}, max_value_edge: 0.083}, ...]` |
| `/api/nhl/daily-top3` | GET | public | `[{match, probas, top_3_players: [...]}, ...]` |
| `/api/admin/picks-preview` | GET | admin | payload complet avec debug info (phase 2) |

### 5.5 Frontend structure

```
dashboard/src/
├── pages/
│   ├── HomeDashboard.tsx          [NEW - remplace ParisDuSoir]
│   ├── Performance.tsx            [REFACTOR - new structure]
│   └── NHL/
│       └── NHLPage.tsx            [REFACTOR - Top 5 → Top 3]
├── components/
│   ├── paris-du-jour/
│   │   ├── PicksDuJourSticky.tsx  [NEW]
│   │   ├── PickCard.tsx           [NEW]
│   │   └── PerfGlobalBadge.tsx    [NEW]
│   ├── match/
│   │   └── MatchCardWithBadge.tsx [NEW - extend existing]
│   └── nhl/
│       └── NHLCardTop3.tsx        [NEW]
└── lib/
    └── queries.ts                  [EXTEND - add new query hooks]
```

Navigation update : `/paris-du-soir` retiré du router (redirect 301 → `/`), home `/` = `HomeDashboard`.

## 6. Phase breakdown (Approche 3 - Data-first)

| Phase | Durée | Livrable | Gate de sortie |
|---|---|---|---|
| **P1** | 3-5j | Backend + migrations + générateurs + fix ML blend + player props fetcher | 48h crons verts, tests CI verts, picks en DB bien catégorisés |
| **P2** | 5-7j | Observation silencieuse + tracking admin-only + calibration endpoints | Décision go/no-go sur la qualité des picks |
| **P3** | 3-5j | HomeDashboard + PicksDuJourSticky + Performance refonte + NHL Top 3 + badges | QA mobile/desktop OK, ancien Paris du Soir retiré |
| **P4** | 2-3j | Copy pivot + SEO + alerting `/api/health/picks` + doc | Site rebrand complet |

**Total estimé** : 13-20 jours de dev (2-3 semaines calendaires).

## 7. Risques et mitigations

| # | Risque | Sévérité | Mitigation |
|---|---|---|---|
| R1 | Générateurs sortent des picks de mauvaise qualité (probas mal calibrées) | Haute | Phase 2 = 5-7 jours observation silencieuse avant UI switch |
| R2 | The Odds API Pro player props NHL incomplets | Moyenne | Test immédiat dès upgrade (étape 1.2), fallback sur cotes implicites |
| R3 | Ancien UI cassé pendant transition | Haute | Approche 3 garde l'ancien intact jusqu'à P3 |
| R4 | Users existants perdent value betting avancé (Kelly, bankroll perso) | Faible | Logique reste en backend, accessible via `/admin` |
| R5 | Page Performance lente sur gros historique | Faible | Pagination + default 30j + index dédié |
| R6 | Duplicate picks sur re-run 23h | Moyenne | Delete-before-insert idempotent dans chaque générateur |
| R7 | Backfill des anciens `best_bets` en `value_bet` incorrect (les anciens "fun" deviennent "value_bet") | Moyenne | Check `notes LIKE 'Auto — Fun%'` pour les backfill en `'fun'` |
| R8 | NHL ML blend bug non fixé → phase 2 inutile | Haute | Fix en étape 1.4, blocker de phase 2 |
| R9 | NHL Top 3 ML predictor `KeyError: 'model'` affecte aussi la qualité des générateurs | Haute | Même fix que R8 |

## 8. Testing strategy

### Tests unitaires

Target : **85% coverage sur `src/ticket_generator.py`** après refactor.

- 6 × générateurs, chacun :
  - 1 test nominal (data OK, returns expected count)
  - 1 test edge case `no_data` (returns 0 picks / None pour fun)
  - 1 test edge case `filters_exclude_all` (aucun pick ne passe les critères)
  - 1 test idempotence (appel 2× ne duplique pas en DB)
- Helpers internes : `_compute_fun_parlay`, `_rank_by_proba`, `_apply_odds_range`

### Tests d'intégration

- `test_scheduler_picks_generation.py` : instancie `job_generate_daily_picks_foot` avec Supabase mocké, vérifie que les 3 générateurs sont appelés dans l'ordre et que les inserts ont bien le format attendu
- `test_resolve_new_categories.py` : vérifie que `job_resolve_bets` gère correctement les 3 nouvelles `category` values

### Tests E2E (marqué `@pytest.mark.integration`)

- `test_full_pipeline_foot.py` : seed fixtures → fetch mock odds → generate → resolve → verify `GET /api/picks/performance` cohérent

### Manual QA (phase 2)

SQL checklist quotidienne :
```sql
-- 1. Count par catégorie
SELECT sport, category, COUNT(*)
FROM best_bets
WHERE date = CURRENT_DATE AND is_auto = true
GROUP BY sport, category;

-- 2. Vérification cote range pour safe
SELECT pick, odds FROM best_bets
WHERE category = 'safe' AND date = CURRENT_DATE
  AND (odds < 1.80 OR odds > 2.20);  -- doit être vide

-- 3. Vérification EV pour value bets
SELECT pick, edge FROM best_bets
WHERE category = 'value_bet' AND date = CURRENT_DATE
  AND edge < 0.03;  -- doit être vide

-- 4. Fun parlay total odds
SELECT stake, odds, notes FROM best_bets
WHERE category = 'fun' AND date = CURRENT_DATE;  -- total ~19.4
```

### CI

- `--cov-fail-under=40` (seuil actuel, baseline conservateur)
- Progressif vers 50 après P1 (les tests des nouveaux générateurs viennent s'ajouter)

## 9. Décisions open (à trancher pendant l'implémentation)

1. **Affichage du parlay Fun** : 1 carte avec les 4 legs listés, ou 1 par leg avec group header ?
2. **Retour sur investissement "réel"** : on affiche juste le ROI virtuel (10€/pick), ou on permet à l'user de définir sa propre mise et on recalcule en live ?
3. **Export CSV** de la performance : optionnel pour phase 4 ?
4. **Notifications push** pour les nouveaux picks du jour : laisser pour une phase 5 ou prévoir déjà le webhook ?

## 10. Ordre d'implémentation (high-level)

Le writing-plans skill va décomposer en tâches atomiques. High-level :

1. **Créer branche** `feat/pivot-probas-sportives` depuis main après merge de `chore/audit-2026-04-10`
2. **P1.1** migration DB
3. **P1.4** fix ML blend NHL (bloquant)
4. **P1.2** upgrade ODDS_API_KEY Pro + verification
5. **P1.5** fetcher player props NHL
6. **P1.6-1.7** scheduler wiring
7. **P1.3** refactor ticket_generator (6 générateurs)
8. **P1.8** tests unitaires
9. **P1.9** deploy + monitoring 48h
10. **P2** observation + endpoints admin-only
11. **P3** frontend (peut être parallélisé par composants)
12. **P4** polish + cleanup

---

## Annexes

### A. Liens

- Leçon 55 (feature principale à 1 clic max) : `tasks/lessons.md:55`
- Leçon 58 (backend service_role) : `tasks/lessons.md:58`
- Leçon 62 (pure logic extraction) : `tasks/lessons.md:62`
- Bug ML blend : `src/nhl/nhl_ml_predictor.py:102`
- The Odds API docs : https://the-odds-api.com/liveapi/guides/v4/

### B. Glossaire

- **EV** (Expected Value) : `proba_modèle × cote - 1`, exprimé en %
- **Edge** : même chose que EV mais parfois exprimé autrement dans le code. Dans ce projet, `edge == EV` (cf leçon 57)
- **Safe** : pick où la proba modèle est élevée et la cote raisonnable (proche de 2)
- **Fun** : parlay 4 legs à cote totale ~19.4
- **Value bet** : pick où EV > 3% (la plus-value statistique est significative)
- **Pick auto** : généré par le scheduler, `is_auto=true`
- **Pick manuel** : créé par l'admin ou l'user, `is_auto=false`
