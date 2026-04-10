# Coverage gaps — Phase 1 analysis

## Fonctions critiques imbriquées à extraire avant de pouvoir les tester

### `api/routers/best_bets.py`

**Dans `resolve_best_bets` (lignes 839-1158) :**

| Fonction imbriquée | Lignes | Rôle | Pureté |
|---|---|---|---|
| `_evaluate_single_football_market(market, h, a)` | 892-913 | Détermine WIN/LOSS pour un marché football simple | Pure ✓ |
| Logique combo football | 957-986 | Résout un combo N legs football (WIN/LOSS/VOID) | Quasi pure (à extraire) |
| Logique résolution NHL player | 1110-1119 | Détermine WIN/LOSS pour un marché NHL joueur | Quasi pure (à extraire) |

**Dans `get_best_bets_stats` (lignes 1161-1498) :**

| Fonction imbriquée | Lignes | Rôle | Pureté |
|---|---|---|---|
| `calc_stats(raw_bets)` | 1170-1268 | Calcule win_rate, ROI, ROI singles, combos | Pure ✓ |
| `normalize_market(raw, bet_label)` | 1290-1304 | Normalise les noms de marché (BTTS, Double Chance, NHL) | Pure ✓ |
| `build_market_breakdown(rows)` | 1306-1319 | Regroupe les paris par marché normalisé et calcule les stats | Pure ✓ |

**Markets couverts par `_evaluate_single_football_market` :**
- `Victoire domicile`, `Victoire extérieur`, `Match nul`
- `Double Chance 1N` / `Double Chance 1X` / `Double Chance X2`
- `Over 1.5 / 2.5 / 3.5 buts`
- `BTTS` / `BTTS Oui` / `BTTS — Les deux équipes marquent`

**Markets NHL à couvrir :**
- `player_points_over_0.5` → points ≥ 1
- `player_goals_over_0.5` → goals ≥ 1
- `player_assists_over_0.5` → assists ≥ 1
- `player_shots_over_2.5` → shots ≥ 3

## Fonctions déjà testables au niveau module

### `src/bankroll.py` — 77% déjà couvert
- `get_current_bankroll` ✓
- `place_bet` (partiel)
- `resolve_bet` ✓
- `get_pnl_summary` ✓
- Tests existants : `tests/test_bankroll.py` (10 tests)

Gap : `place_bet` RPC atomic path, `_place_bet_legacy` non couverts. `get_bankroll_history` non testé.

### `src/prediction_blender.py` — 55% déjà couvert
- `_build_fallback_analysis`
- `_try_meta_blend`
- `blend_predictions`

Gap : lignes 123-171, 208-210, 227, 254-258 non couvertes (branches méta-blend, validation).

## Plan d'action Phase 1.2 — refactoring + tests best_bets

**Étape A — Refactoring (sans changer le comportement)**
1. Créer `api/routers/best_bets_logic.py` (module privé même package)
2. Y déplacer :
   - `evaluate_single_football_market(market, h, a) -> str | None`
   - `evaluate_football_combo(combo_market, h, a) -> str | None` (WIN/LOSS/VOID/None)
   - `evaluate_nhl_player_market(market, stats) -> str` (WIN/LOSS)
   - `calc_stats(raw_bets) -> dict` (pour les stats)
   - `normalize_market(raw, bet_label) -> str` (pour les stats)
   - `build_market_breakdown(rows) -> dict` (pour les stats)
3. `best_bets.py` importe depuis `best_bets_logic`
4. Lancer la suite existante → doit rester verte

**Étape B — Tests unitaires purs (100% du nouveau module)**
- `tests/test_best_bets_logic.py`
- Couvrir tous les marchés listés ci-dessus
- Couvrir combos 2-3 legs (all WIN, 1 LOSS, mix VOID)
- Couvrir `calc_stats` sur fixtures variées
- Couvrir `normalize_market` sur tous les cas listés dans `MARKET_NORMALIZE`
- Couvrir `build_market_breakdown` sur fixtures multi-marchés

**Étape C — Tests d'intégration avec mock Supabase**
- `tests/test_best_bets_router.py`
- Mocker supabase via le pattern de `conftest.py::MockSupabaseQuery`
- Tester `resolve_best_bets` end-to-end sur un fixture finished + bets pending

## Phase 1.3 — Gap bankroll à combler

Tests à ajouter à `tests/test_bankroll.py` :
- `place_bet` RPC atomic path (mock `supabase.rpc`)
- `_place_bet_legacy` fallback
- `get_bankroll_history`
- `place_bet` avec stake < 0.50€ (edge case)

## Phase 1.4 — Gap prediction_blender

Tests à ajouter à `tests/test_prediction_blender.py` (ou créer) :
- `blend_predictions` cas nominal 70/30
- `blend_predictions` avec `ai_result=None` → 100% stats
- `blend_predictions` avec stats vide → erreur explicite
- `_try_meta_blend` avec meta-learner activé
- Somme probas = 100 après blend (cf leçon 2026-03-19)
- Normalisation `edge` vs `EV` (cf leçon 2026-04-05)

## Phase 1.5 — E2E pipeline

`tests/test_pipeline_e2e.py` marqué `@pytest.mark.integration` :
- Seed : 2 fixtures future + 2 predictions + 3 best_bets pending
- Step 1 : update fixtures avec scores (FT / AET)
- Step 2 : appeler `resolve_best_bets` → vérifier updates en DB
- Step 3 : appeler `get_best_bets_stats` → vérifier ROI cohérent
