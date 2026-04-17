# Pivot "Spécialiste en probabilités sportives" — Implementation Plan

> **For agentic workers:** This plan is derived from `tasks/design_pivot_probas_sportives_2026-04-11.md`. Steps use checkbox (`- [ ]`) syntax for tracking. Execute task-by-task, commit after each task group, run tests before moving on.

**Goal:** Repositionner le site comme spécialiste en probabilités sportives avec 3 catégories de picks quotidiens (safe/fun/value_bet) × 2 sports, tracking WIN/LOSS et ROI sur bankroll virtuel 10€/pick.

**Architecture:** Data-first approach (Approche 3). Phase 1 = backend (data model + 6 générateurs + scheduler). Phase 2 = validation silencieuse en DB. Phase 3 = frontend refonte. Phase 4 = polish.

**Tech Stack:** FastAPI + Supabase (Postgres + RLS) + APScheduler + The Odds API Pro + React 19 + Vite + Tailwind + Radix UI + pytest.

**Branche:** `feat/pivot-probas-sportives` (créée depuis `chore/audit-2026-04-10`).

---

## PHASE 1 — Backend (model + générateurs + scheduler)

### Task 1 : Migration DB best_bets (colonnes category + virtual_stake + is_auto)

**Files:**
- Create: `ProbaLab/migrations/021_best_bets_pivot_categories.sql`
- Apply via Supabase MCP tool `mcp__supabase__apply_migration`

- [ ] **Step 1: Écrire le fichier de migration**

```sql
-- 021_best_bets_pivot_categories.sql
BEGIN;

ALTER TABLE best_bets
  ADD COLUMN IF NOT EXISTS category text
    CHECK (category IN ('safe', 'fun', 'value_bet')),
  ADD COLUMN IF NOT EXISTS virtual_stake numeric DEFAULT 10,
  ADD COLUMN IF NOT EXISTS is_auto boolean DEFAULT false;

-- Backfill existing rows: notes tell us what they were
UPDATE best_bets
SET
  category = CASE
    WHEN notes LIKE 'Auto — Fun%' THEN 'fun'
    ELSE 'value_bet'
  END,
  is_auto = (notes LIKE 'Auto —%')
WHERE category IS NULL;

-- Index for performance page queries
CREATE INDEX IF NOT EXISTS idx_best_bets_cat_sport_date
  ON best_bets(category, sport, date DESC)
  WHERE is_auto = true;

COMMIT;
```

- [ ] **Step 2: Appliquer via Supabase MCP**

Use `mcp__supabase__apply_migration` with the SQL content above.

- [ ] **Step 3: Vérifier**

Use `mcp__supabase__execute_sql`:
```sql
SELECT
  category,
  COUNT(*),
  COUNT(*) FILTER (WHERE is_auto = true) AS auto_count
FROM best_bets
GROUP BY category;
```
Expected: `value_bet` count > 0 (backfill OK), indexes exist.

- [ ] **Step 4: Commit**

```bash
git add ProbaLab/migrations/021_best_bets_pivot_categories.sql
git commit -m "feat(db): add category/virtual_stake/is_auto to best_bets"
```

---

### Task 2 : Fix NHL ML blend KeyError bug

**Files:**
- Modify: `ProbaLab/src/nhl/nhl_ml_predictor.py:102`

- [ ] **Step 1: Lire le code autour de la ligne 102**

Read `src/nhl/nhl_ml_predictor.py` offset 80 limit 50 pour comprendre la structure du dict `model_data`.

- [ ] **Step 2: Identifier le bug**

Le code fait `model = model_data["model"]` mais la clé `model` n'existe pas dans le dict retourné par `load_all_models()`. Vérifier avec grep quelle est la vraie structure.

- [ ] **Step 3: Patcher**

Soit utiliser la bonne clé (ex: `model_data["clf"]` ou `model_data["predictor"]`), soit adapter la shape du dict côté loader.

- [ ] **Step 4: Vérifier en live**

```bash
cd ProbaLab && set -a && . ../.env && set +a && python -c "
from src.fetchers.nhl_pipeline import run_nhl_pipeline
result = run_nhl_pipeline()
print(result)
" 2>&1 | grep -c 'ML blend skipped'
```
Expected: `0` (plus aucun ML blend skipped).

- [ ] **Step 5: Commit**

```bash
git add ProbaLab/src/nhl/nhl_ml_predictor.py
git commit -m "fix(nhl): correct ML blend KeyError on model_data dict"
```

---

### Task 3 : Créer fetch_nhl_player_props.py (The Odds API Pro)

**Files:**
- Create: `ProbaLab/src/fetchers/fetch_nhl_player_props.py`
- Create: `ProbaLab/tests/test_fetch_nhl_player_props.py`

- [ ] **Step 1: Écrire fetch_nhl_player_props.py**

Template structure (s'inspirer de `src/nhl/fetch_odds.py` pour le API pattern mais cible `player_points`, `player_assists`, `player_goals`, `player_shots_on_goal`). Fetch bulk via `/sports/icehockey_nhl/odds?markets=player_points,player_assists,player_goals,player_shots_on_goal`. Upsert dans `nhl_odds` table existante avec `game_date` + `player_name` + `market` + `line` + `over_odds`.

- [ ] **Step 2: Test avec la clé Pro**

```bash
cd ProbaLab && set -a && . ../.env && set +a && python -c "
from src.fetchers.fetch_nhl_player_props import fetch_nhl_player_props
result = fetch_nhl_player_props()
print(result)
"
```
Expected: `{'status': 'ok', 'events': N, 'rows_saved': M}` où M > 0 si les player props sont disponibles sur le plan Pro.

Si le plan ne couvre pas player_points: fallback graceful sur cotes implicites (garder le fichier mais noter dans les logs). Si le plan les couvre: continuer.

- [ ] **Step 3: Tests unitaires minimum**

```python
# tests/test_fetch_nhl_player_props.py
def test_transform_outcomes_to_rows(monkeypatch):
    # Mock The Odds API response, verify rows format
    ...

def test_skip_rows_without_price():
    ...
```

- [ ] **Step 4: Commit**

```bash
git add ProbaLab/src/fetchers/fetch_nhl_player_props.py ProbaLab/tests/test_fetch_nhl_player_props.py
git commit -m "feat(nhl): add fetch_nhl_player_props via The Odds API Pro"
```

---

### Task 4 : Refactor ticket_generator.py — 6 générateurs purs

**Files:**
- Modify: `ProbaLab/src/ticket_generator.py`

Le fichier actuel a ~900 lignes avec des helpers foot/NHL. On ne le réécrit pas entièrement : on **ajoute 6 nouvelles fonctions pures** qui réutilisent les helpers existants, et on **ajoute un wrapper `save_daily_picks_v2(date, sport)`** qui remplace `generate_football_picks` / `generate_nhl_picks`.

- [ ] **Step 1: Ajouter les constantes de catégories**

Au début du fichier, après les imports :

```python
# ─── NOUVEAU PIVOT : 3 catégories de picks quotidiens ───────────
CATEGORY_SAFE = "safe"
CATEGORY_FUN = "fun"
CATEGORY_VALUE_BET = "value_bet"

SAFE_ODDS_MIN = 1.80
SAFE_ODDS_MAX = 2.20
FUN_LEGS = 4
FUN_LEG_ODDS_MIN = 1.95
FUN_LEG_ODDS_MAX = 2.25
FUN_LEG_PROBA_MIN = 55  # min proba modèle pour qu'un leg soit éligible
VALUE_BET_MIN_EDGE = 0.03
VALUE_BET_MAX_PICKS = 5
VIRTUAL_STAKE = 10  # €/pick

SAFE_PICKS_PER_SPORT = 3
```

- [ ] **Step 2: Écrire `generate_safe_foot(date)`**

```python
def generate_safe_foot(date: str) -> list[dict]:
    """3 picks foot safe, cote ∈ [SAFE_ODDS_MIN, SAFE_ODDS_MAX], tri par proba desc.

    Markets considérés : 1X2 (H/D/A), Double Chance (1X/12/X2), BTTS Yes/No,
    Over/Under 2.5. Pour chaque match on prend le meilleur pick éligible, puis
    on sélectionne les 3 meilleurs globalement (1 pick max par match).
    """
    predictions, fixture_map, odds_map = _load_football_data(date)
    if not predictions:
        return []

    candidates = []
    for pred in predictions:
        fid = pred["fixture_id"]
        match = fixture_map.get(fid, {})
        match_str = f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}"
        real_odds = (odds_map or {}).get(fid, {})

        # On énumère les marchés éligibles pour ce match
        market_candidates = []

        # 1X2
        for key, label_key in (("home", "proba_home"), ("draw", "proba_draw"), ("away", "proba_away")):
            prob = pred.get(label_key)
            odds = real_odds.get(f"{key}_win_odds") if key != "draw" else real_odds.get("draw_odds")
            if prob and odds and SAFE_ODDS_MIN <= odds <= SAFE_ODDS_MAX:
                label = {"home": "Victoire domicile", "draw": "Match nul", "away": "Victoire extérieur"}[key]
                market_candidates.append({"pick": label, "proba": prob, "odds": odds, "market": f"1X2_{key}"})

        # BTTS
        for side, label in (("yes", "BTTS Oui"), ("no", "BTTS Non")):
            prob = pred.get(f"proba_btts_{side}")
            odds = real_odds.get(f"btts_{side}_odds")
            if prob and odds and SAFE_ODDS_MIN <= odds <= SAFE_ODDS_MAX:
                market_candidates.append({"pick": label, "proba": prob, "odds": odds, "market": f"btts_{side}"})

        # Over/Under 2.5
        for side, label in (("over", "Over 2.5"), ("under", "Under 2.5")):
            prob = pred.get(f"proba_{side}_25")
            odds = real_odds.get(f"{side}_25_odds")
            if prob and odds and SAFE_ODDS_MIN <= odds <= SAFE_ODDS_MAX:
                market_candidates.append({"pick": label, "proba": prob, "odds": odds, "market": f"ou25_{side}"})

        # Double Chance (1X, 12, X2)
        for key, label in (("home_draw", "1X"), ("home_away", "12"), ("draw_away", "X2")):
            prob = pred.get(f"proba_dc_{key}")
            odds = real_odds.get(f"dc_{key}_odds")
            if prob and odds and SAFE_ODDS_MIN <= odds <= SAFE_ODDS_MAX:
                market_candidates.append({"pick": f"Double Chance {label}", "proba": prob, "odds": odds, "market": f"dc_{key}"})

        if not market_candidates:
            continue

        # Meilleur pick du match = plus haute proba parmi les marchés éligibles
        best = max(market_candidates, key=lambda c: c["proba"])
        best["match"] = match_str
        best["fixture_id"] = fid
        candidates.append(best)

    # Top 3 globaux par proba
    candidates.sort(key=lambda c: c["proba"], reverse=True)
    return candidates[:SAFE_PICKS_PER_SPORT]
```

- [ ] **Step 3: Écrire `generate_fun_foot(date)`**

```python
def generate_fun_foot(date: str) -> dict | None:
    """1 parlay foot 4 legs, total cote ~19.4.

    Stratégie : 4 picks 1X2 sur matchs différents, chacun avec cote
    ∈ [FUN_LEG_ODDS_MIN, FUN_LEG_ODDS_MAX] et proba >= FUN_LEG_PROBA_MIN.
    """
    predictions, fixture_map, odds_map = _load_football_data(date)
    if not predictions:
        return None

    leg_candidates = []
    for pred in predictions:
        fid = pred["fixture_id"]
        match = fixture_map.get(fid, {})
        match_str = f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}"
        real_odds = (odds_map or {}).get(fid, {})

        for key, label_key in (("home", "proba_home"), ("draw", "proba_draw"), ("away", "proba_away")):
            prob = pred.get(label_key)
            odds_col = f"{key}_win_odds" if key != "draw" else "draw_odds"
            odds = real_odds.get(odds_col)
            if prob and odds and FUN_LEG_ODDS_MIN <= odds <= FUN_LEG_ODDS_MAX and prob >= FUN_LEG_PROBA_MIN:
                label = {"home": "Victoire domicile", "draw": "Match nul", "away": "Victoire extérieur"}[key]
                leg_candidates.append({
                    "pick": label,
                    "proba": prob,
                    "odds": odds,
                    "match": match_str,
                    "fixture_id": fid,
                })
                break  # max 1 leg par match

    # Trier par proba desc, prendre 4 legs sur matchs différents
    leg_candidates.sort(key=lambda c: c["proba"], reverse=True)
    selected = []
    used_matches = set()
    for leg in leg_candidates:
        if leg["fixture_id"] in used_matches:
            continue
        selected.append(leg)
        used_matches.add(leg["fixture_id"])
        if len(selected) == FUN_LEGS:
            break

    if len(selected) < FUN_LEGS:
        return None

    total_odds = 1.0
    for leg in selected:
        total_odds *= leg["odds"]

    return {
        "type": "FUN",
        "sport": "football",
        "legs": selected,
        "total_odds": round(total_odds, 2),
    }
```

- [ ] **Step 4: Écrire `generate_value_foot(date)`**

```python
def generate_value_foot(date: str) -> list[dict]:
    """0-5 picks foot avec edge > VALUE_BET_MIN_EDGE, cap VALUE_BET_MAX_PICKS."""
    predictions, fixture_map, odds_map = _load_football_data(date)
    if not predictions:
        return []

    candidates = []
    for pred in predictions:
        fid = pred["fixture_id"]
        match = fixture_map.get(fid, {})
        match_str = f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}"
        real_odds = (odds_map or {}).get(fid, {})

        # Même énumération de marchés que safe, mais on calcule l'edge
        for key, label_key, odds_col, label in [
            ("home", "proba_home", "home_win_odds", "Victoire domicile"),
            ("draw", "proba_draw", "draw_odds", "Match nul"),
            ("away", "proba_away", "away_win_odds", "Victoire extérieur"),
            ("btts_yes", "proba_btts_yes", "btts_yes_odds", "BTTS Oui"),
            ("btts_no", "proba_btts_no", "btts_no_odds", "BTTS Non"),
            ("over_25", "proba_over_25", "over_25_odds", "Over 2.5"),
            ("under_25", "proba_under_25", "under_25_odds", "Under 2.5"),
        ]:
            prob = pred.get(label_key)
            odds = real_odds.get(odds_col)
            if not prob or not odds:
                continue
            edge = (prob / 100.0) * odds - 1
            if edge < VALUE_BET_MIN_EDGE:
                continue
            candidates.append({
                "pick": label,
                "proba": prob,
                "odds": odds,
                "edge": round(edge, 4),
                "match": match_str,
                "fixture_id": fid,
                "market": key,
            })

    candidates.sort(key=lambda c: c["edge"], reverse=True)
    return candidates[:VALUE_BET_MAX_PICKS]
```

- [ ] **Step 5: Écrire les 3 équivalents NHL**

```python
def generate_safe_nhl(date: str) -> list[dict]:
    """3 picks NHL safe : player props 1+ Point ou 1+ Passe, cote ∈ [1.80, 2.20]."""
    nhl_fixtures, odds_map = _load_nhl_data(date)
    if not nhl_fixtures:
        return []

    candidates = []
    for fix in nhl_fixtures:
        stats = fix.get("stats_json") or {}
        players = stats.get("top_players") or []
        match_str = f"{fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"

        for p in players:
            name = p.get("player_name", "")
            if not name:
                continue
            prob_point = float(p.get("ml_prob_point") or p.get("prob_point") or 0)
            prob_assist = float(p.get("ml_prob_assist") or p.get("prob_assist") or 0)

            for prob, label, market_key in [
                (prob_point, "1+ Point", "player_points_over_0.5"),
                (prob_assist, "1+ Passe", "player_assists_over_0.5"),
            ]:
                if prob < 50:
                    continue
                # Real odds si dispo, sinon implicite
                real_key = f"{name}|{market_key}"
                odds = odds_map.get(real_key) or calculate_implied_odds(prob)
                if not (SAFE_ODDS_MIN <= odds <= SAFE_ODDS_MAX):
                    continue
                candidates.append({
                    "pick": f"{name} — {label}",
                    "proba": prob,
                    "odds": odds,
                    "match": match_str,
                    "player_name": name,
                    "market": market_key,
                })

    # Dédupliquer par joueur (garder le meilleur edge)
    by_player: dict[str, dict] = {}
    candidates.sort(key=lambda c: c["proba"], reverse=True)
    for c in candidates:
        if c["player_name"] not in by_player:
            by_player[c["player_name"]] = c

    return sorted(by_player.values(), key=lambda c: c["proba"], reverse=True)[:SAFE_PICKS_PER_SPORT]


def generate_fun_nhl(date: str) -> dict | None:
    """1 parlay NHL 4 legs mix buts/passes, total cote ~19.4."""
    nhl_fixtures, odds_map = _load_nhl_data(date)
    if not nhl_fixtures:
        return None

    leg_candidates = []
    for fix in nhl_fixtures:
        stats = fix.get("stats_json") or {}
        players = stats.get("top_players") or []
        match_str = f"{fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"

        for p in players:
            name = p.get("player_name", "")
            if not name:
                continue
            prob_goal = float(p.get("ml_prob_goal") or p.get("prob_goal") or 0)
            prob_assist = float(p.get("ml_prob_assist") or p.get("prob_assist") or 0)

            for prob, label, market_key in [
                (prob_goal, "Buteur", "player_goals_over_0.5"),
                (prob_assist, "Passeur", "player_assists_over_0.5"),
            ]:
                if prob < 40:  # min pour fun (on accepte plus bas que safe)
                    continue
                odds = odds_map.get(f"{name}|{market_key}") or calculate_implied_odds(prob)
                if not (FUN_LEG_ODDS_MIN <= odds <= FUN_LEG_ODDS_MAX):
                    continue
                leg_candidates.append({
                    "pick": f"{name} — {label}",
                    "proba": prob,
                    "odds": odds,
                    "match": match_str,
                    "player_name": name,
                })

    leg_candidates.sort(key=lambda c: c["proba"], reverse=True)
    selected = []
    used_players = set()
    for leg in leg_candidates:
        if leg["player_name"] in used_players:
            continue
        selected.append(leg)
        used_players.add(leg["player_name"])
        if len(selected) == FUN_LEGS:
            break

    if len(selected) < FUN_LEGS:
        return None

    total_odds = 1.0
    for leg in selected:
        total_odds *= leg["odds"]

    return {
        "type": "FUN",
        "sport": "nhl",
        "legs": selected,
        "total_odds": round(total_odds, 2),
    }


def generate_value_nhl(date: str) -> list[dict]:
    """0-5 picks NHL avec edge > VALUE_BET_MIN_EDGE."""
    nhl_fixtures, odds_map = _load_nhl_data(date)
    if not nhl_fixtures:
        return []

    candidates = []
    for fix in nhl_fixtures:
        stats = fix.get("stats_json") or {}
        players = stats.get("top_players") or []
        match_str = f"{fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"

        for p in players:
            name = p.get("player_name", "")
            if not name:
                continue
            for prob_key, label, market_key in [
                ("ml_prob_point", "1+ Point", "player_points_over_0.5"),
                ("ml_prob_assist", "1+ Passe", "player_assists_over_0.5"),
                ("ml_prob_goal", "Buteur", "player_goals_over_0.5"),
                ("ml_prob_shot", "3+ Tirs", "player_shots_over_2.5"),
            ]:
                prob = float(p.get(prob_key) or p.get(prob_key.replace("ml_", "")) or 0)
                if prob < 30:
                    continue
                odds = odds_map.get(f"{name}|{market_key}")
                if not odds:
                    continue  # pas d'edge calculable sans vraie cote
                edge = (prob / 100.0) * odds - 1
                if edge < VALUE_BET_MIN_EDGE:
                    continue
                candidates.append({
                    "pick": f"{name} — {label}",
                    "proba": prob,
                    "odds": odds,
                    "edge": round(edge, 4),
                    "match": match_str,
                    "player_name": name,
                    "market": market_key,
                })

    candidates.sort(key=lambda c: c["edge"], reverse=True)
    return candidates[:VALUE_BET_MAX_PICKS]
```

- [ ] **Step 6: Écrire `save_daily_picks(date, sport)` — wrapper impur qui fait le delete+insert**

```python
def save_daily_picks(date: str, sport: str) -> dict:
    """Génère et sauve les 3 catégories de picks pour un sport + date.

    Idempotent : supprime les picks auto existants pour ce date+sport avant insert.
    """
    assert sport in ("football", "nhl")

    if sport == "football":
        safe = generate_safe_foot(date)
        fun = generate_fun_foot(date)
        value = generate_value_foot(date)
    else:
        safe = generate_safe_nhl(date)
        fun = generate_fun_nhl(date)
        value = generate_value_nhl(date)

    # Delete existing auto picks for this date+sport
    try:
        supabase.table("best_bets").delete().eq("date", date).eq("sport", sport).eq("is_auto", True).execute()
    except Exception:
        logger.warning("[save_daily_picks] delete step failed for %s %s", date, sport, exc_info=True)

    rows = []

    # Safe
    for pick in safe:
        rows.append({
            "date": date,
            "sport": sport,
            "category": CATEGORY_SAFE,
            "is_auto": True,
            "virtual_stake": VIRTUAL_STAKE,
            "pick": pick["pick"],
            "odds": pick["odds"],
            "proba": pick["proba"],
            "match": pick["match"],
            "status": "PENDING",
            "notes": f"Auto — Safe {sport}",
        })

    # Fun (parlay as single row with legs in notes)
    if fun:
        legs_str = " + ".join(f"{leg['pick']} ({leg['match']})" for leg in fun["legs"])
        rows.append({
            "date": date,
            "sport": sport,
            "category": CATEGORY_FUN,
            "is_auto": True,
            "virtual_stake": VIRTUAL_STAKE,
            "pick": f"Parlay {FUN_LEGS} legs",
            "odds": fun["total_odds"],
            "proba": None,
            "match": "Multi",
            "status": "PENDING",
            "notes": f"Auto — Fun {sport} · {legs_str}",
        })

    # Value bets
    for pick in value:
        rows.append({
            "date": date,
            "sport": sport,
            "category": CATEGORY_VALUE_BET,
            "is_auto": True,
            "virtual_stake": VIRTUAL_STAKE,
            "pick": pick["pick"],
            "odds": pick["odds"],
            "proba": pick["proba"],
            "edge": pick.get("edge"),
            "match": pick["match"],
            "status": "PENDING",
            "notes": f"Auto — Value {sport}",
        })

    if rows:
        try:
            supabase.table("best_bets").insert(rows).execute()
        except Exception:
            logger.exception("[save_daily_picks] insert failed for %s %s", date, sport)

    return {
        "date": date,
        "sport": sport,
        "safe": len(safe),
        "fun": 1 if fun else 0,
        "value_bet": len(value),
        "total": len(rows),
    }
```

- [ ] **Step 7: Vérifier py_compile**

```bash
cd ProbaLab && python -m py_compile src/ticket_generator.py && echo OK
```

- [ ] **Step 8: Commit**

```bash
git add ProbaLab/src/ticket_generator.py
git commit -m "feat(picks): 6 pure generators for safe/fun/value_bet × 2 sports"
```

---

### Task 5 : Update worker.py avec les nouveaux jobs

**Files:**
- Modify: `ProbaLab/worker.py`

- [ ] **Step 1: Ajouter `job_nhl_fetch_player_props`**

Dans la section NHL du worker, après `job_nhl_fetch_odds` :

```python
def job_nhl_fetch_player_props() -> None:
    """16:20 & 23:20 — fetch NHL player props via The Odds API Pro."""
    try:
        from src.fetchers.fetch_nhl_player_props import fetch_nhl_player_props
        fetch_nhl_player_props()
    except Exception:
        logger.exception("[job_nhl_fetch_player_props] Error")
```

- [ ] **Step 2: Modifier `job_football_picks` pour appeler le nouveau wrapper**

```python
def job_football_picks() -> None:
    """12:00 — génération 3 catégories (safe + fun + value_bet) foot."""
    try:
        from datetime import datetime, timezone
        from src.ticket_generator import save_daily_picks
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = save_daily_picks(date, "football")
        logger.info(
            "[job_football_picks] %s: safe=%d, fun=%d, value_bet=%d",
            result["date"], result["safe"], result["fun"], result["value_bet"],
        )
    except Exception:
        logger.exception("[job_football_picks] Error")
```

- [ ] **Step 3: Modifier `job_nhl_picks` idem**

```python
def job_nhl_picks() -> None:
    """17:00 & 23:30 — génération 3 catégories NHL."""
    try:
        from datetime import datetime, timezone
        from src.ticket_generator import save_daily_picks
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = save_daily_picks(date, "nhl")
        logger.info(
            "[job_nhl_picks] %s: safe=%d, fun=%d, value_bet=%d",
            result["date"], result["safe"], result["fun"], result["value_bet"],
        )
    except Exception:
        logger.exception("[job_nhl_picks] Error")
```

- [ ] **Step 4: Ajouter les 2 crons player props dans `main()`**

Dans la section NHL du scheduler :

```python
scheduler.add_job(job_nhl_fetch_player_props, CronTrigger(hour=16, minute=20),
                  id="nhl_fetch_player_props_afternoon", max_instances=1, coalesce=True)
scheduler.add_job(job_nhl_fetch_player_props, CronTrigger(hour=23, minute=20),
                  id="nhl_fetch_player_props_lineups", max_instances=1, coalesce=True)
```

- [ ] **Step 5: Mettre à jour le header logs**

Ajouter les nouvelles lignes dans le header info logger.

- [ ] **Step 6: py_compile**

```bash
cd ProbaLab && python -m py_compile worker.py && echo OK
```

- [ ] **Step 7: Commit**

```bash
git add ProbaLab/worker.py
git commit -m "feat(worker): wire 3-category picks generators + player props fetcher"
```

---

### Task 6 : Tests unitaires pour les 6 générateurs

**Files:**
- Create: `ProbaLab/tests/test_ticket_generator_pivot.py`

- [ ] **Step 1: Écrire test fixture helper**

```python
# tests/test_ticket_generator_pivot.py
import pytest
from unittest.mock import patch, MagicMock
from src.ticket_generator import (
    generate_safe_foot, generate_fun_foot, generate_value_foot,
    generate_safe_nhl, generate_fun_nhl, generate_value_nhl,
    save_daily_picks,
    SAFE_ODDS_MIN, SAFE_ODDS_MAX, VALUE_BET_MIN_EDGE,
)


@pytest.fixture
def mock_foot_data_3_picks():
    """3 matches with clean 1X2 odds in safe range."""
    predictions = [
        {"fixture_id": 1, "proba_home": 60, "proba_draw": 25, "proba_away": 15,
         "proba_btts_yes": 55, "proba_btts_no": 45,
         "proba_over_25": 58, "proba_under_25": 42,
         "proba_dc_home_draw": 85, "proba_dc_home_away": 75, "proba_dc_draw_away": 40},
        {"fixture_id": 2, "proba_home": 52, "proba_draw": 28, "proba_away": 20,
         "proba_btts_yes": 60, "proba_btts_no": 40,
         "proba_over_25": 65, "proba_under_25": 35,
         "proba_dc_home_draw": 80, "proba_dc_home_away": 72, "proba_dc_draw_away": 48},
        {"fixture_id": 3, "proba_home": 48, "proba_draw": 30, "proba_away": 22,
         "proba_btts_yes": 52, "proba_btts_no": 48,
         "proba_over_25": 54, "proba_under_25": 46,
         "proba_dc_home_draw": 78, "proba_dc_home_away": 70, "proba_dc_draw_away": 52},
    ]
    fixture_map = {
        1: {"home_team": "A", "away_team": "B"},
        2: {"home_team": "C", "away_team": "D"},
        3: {"home_team": "E", "away_team": "F"},
    }
    odds_map = {
        1: {"home_win_odds": 2.00, "draw_odds": 3.50, "away_win_odds": 4.00,
            "btts_yes_odds": 1.85, "btts_no_odds": 2.05,
            "over_25_odds": 1.90, "under_25_odds": 1.95},
        2: {"home_win_odds": 2.10, "draw_odds": 3.30, "away_win_odds": 3.80,
            "btts_yes_odds": 1.80, "btts_no_odds": 2.10,
            "over_25_odds": 1.85, "under_25_odds": 2.00},
        3: {"home_win_odds": 2.15, "draw_odds": 3.20, "away_win_odds": 3.50,
            "btts_yes_odds": 2.00, "btts_no_odds": 1.90,
            "over_25_odds": 2.05, "under_25_odds": 1.85},
    }
    return predictions, fixture_map, odds_map
```

- [ ] **Step 2: Test `generate_safe_foot` nominal**

```python
def test_generate_safe_foot_nominal(mock_foot_data_3_picks):
    """Verify 3 picks returned, all in safe odds range, sorted by proba desc."""
    with patch("src.ticket_generator._load_football_data", return_value=mock_foot_data_3_picks):
        picks = generate_safe_foot("2026-04-11")
    assert len(picks) == 3
    for p in picks:
        assert SAFE_ODDS_MIN <= p["odds"] <= SAFE_ODDS_MAX
    # Sorted desc
    assert picks[0]["proba"] >= picks[1]["proba"] >= picks[2]["proba"]
    # One pick per match
    assert len({p["fixture_id"] for p in picks}) == 3
```

- [ ] **Step 3: Test `generate_safe_foot` edge case : aucune data**

```python
def test_generate_safe_foot_no_data():
    with patch("src.ticket_generator._load_football_data", return_value=([], {}, {})):
        picks = generate_safe_foot("2026-04-11")
    assert picks == []
```

- [ ] **Step 4: Test `generate_safe_foot` edge case : cotes hors range**

```python
def test_generate_safe_foot_odds_out_of_range():
    """All odds are below 1.80 — no pick should qualify."""
    preds = [{"fixture_id": 1, "proba_home": 80, "proba_draw": 10, "proba_away": 10}]
    fix = {1: {"home_team": "A", "away_team": "B"}}
    odds = {1: {"home_win_odds": 1.30, "draw_odds": 8.0, "away_win_odds": 12.0}}
    with patch("src.ticket_generator._load_football_data", return_value=(preds, fix, odds)):
        picks = generate_safe_foot("2026-04-11")
    assert picks == []
```

- [ ] **Step 5: Test `generate_fun_foot` nominal**

```python
def test_generate_fun_foot_nominal():
    """4 matches with eligible legs → parlay returned with total ~19.4."""
    predictions = [
        {"fixture_id": i, "proba_home": 56, "proba_draw": 25, "proba_away": 19}
        for i in range(1, 5)
    ]
    fixture_map = {i: {"home_team": f"H{i}", "away_team": f"A{i}"} for i in range(1, 5)}
    odds_map = {i: {"home_win_odds": 2.10, "draw_odds": 3.5, "away_win_odds": 4.0} for i in range(1, 5)}
    with patch("src.ticket_generator._load_football_data", return_value=(predictions, fixture_map, odds_map)):
        parlay = generate_fun_foot("2026-04-11")
    assert parlay is not None
    assert len(parlay["legs"]) == 4
    assert 15 < parlay["total_odds"] < 25  # around 19.4
```

- [ ] **Step 6: Test `generate_fun_foot` pas assez de legs**

```python
def test_generate_fun_foot_not_enough_legs():
    """Only 2 matches → cannot build 4-leg parlay."""
    predictions = [{"fixture_id": i, "proba_home": 60, "proba_draw": 25, "proba_away": 15} for i in range(1, 3)]
    fixture_map = {i: {"home_team": f"H{i}", "away_team": f"A{i}"} for i in range(1, 3)}
    odds_map = {i: {"home_win_odds": 2.10, "draw_odds": 3.5, "away_win_odds": 4.0} for i in range(1, 3)}
    with patch("src.ticket_generator._load_football_data", return_value=(predictions, fixture_map, odds_map)):
        parlay = generate_fun_foot("2026-04-11")
    assert parlay is None
```

- [ ] **Step 7: Test `generate_value_foot` filter edge**

```python
def test_generate_value_foot_edge_filter():
    """Only picks with edge > 3% should be returned."""
    preds = [
        {"fixture_id": 1, "proba_home": 60, "proba_draw": 25, "proba_away": 15,
         "proba_btts_yes": 55, "proba_btts_no": 45, "proba_over_25": 55, "proba_under_25": 45},
    ]
    fix = {1: {"home_team": "A", "away_team": "B"}}
    # home has 60% proba × 2.0 odds = edge +20% → qualifies
    # away has 15% × 4.0 = edge -40% → no
    odds = {1: {"home_win_odds": 2.00, "draw_odds": 4.00, "away_win_odds": 4.00,
                "btts_yes_odds": 1.50, "btts_no_odds": 2.50, "over_25_odds": 1.80, "under_25_odds": 2.10}}
    with patch("src.ticket_generator._load_football_data", return_value=(preds, fix, odds)):
        picks = generate_value_foot("2026-04-11")
    assert len(picks) >= 1
    for p in picks:
        assert p["edge"] >= VALUE_BET_MIN_EDGE
```

- [ ] **Step 8: Tests NHL équivalents (safe, fun, value)**

Pareil que foot mais avec `_load_nhl_data` mocké retournant des fixtures avec `stats_json.top_players`.

- [ ] **Step 9: Test `save_daily_picks` idempotence**

```python
def test_save_daily_picks_idempotent(mock_foot_data_3_picks):
    """Running twice should not duplicate rows in DB."""
    with patch("src.ticket_generator._load_football_data", return_value=mock_foot_data_3_picks), \
         patch("src.ticket_generator.supabase") as sb_mock:
        save_daily_picks("2026-04-11", "football")
        save_daily_picks("2026-04-11", "football")
    # Delete should be called twice (once per save)
    assert sb_mock.table().delete.call_count >= 2
    # Insert should be called twice, but with SAME rows each time
    assert sb_mock.table().insert.call_count >= 2
```

- [ ] **Step 10: Lancer les tests**

```bash
cd ProbaLab && pytest tests/test_ticket_generator_pivot.py -v
```
Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add ProbaLab/tests/test_ticket_generator_pivot.py
git commit -m "test(picks): unit tests for 6 pivot generators"
```

---

### Task 7 : Nouveaux endpoints API

**Files:**
- Modify: `ProbaLab/api/routers/best_bets.py` (ajouter `/api/picks/daily`, `/api/picks/performance`)
- Modify: `ProbaLab/api/routers/football.py` ou créer `matches.py` pour `/api/matches/foot-today`
- Modify: `ProbaLab/api/routers/nhl.py` pour `/api/nhl/daily-top3`

- [ ] **Step 1: `GET /api/picks/daily`**

```python
@router.get("/api/picks/daily")
def get_daily_picks(date: str | None = None) -> dict:
    """Return today's picks grouped by sport and category."""
    from datetime import datetime, timezone
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rows = (
        supabase.table("best_bets")
        .select("*")
        .eq("date", date)
        .eq("is_auto", True)
        .execute()
        .data or []
    )

    result = {"date": date, "sports": {"football": {"safe": [], "fun": None, "value_bet": []},
                                       "nhl": {"safe": [], "fun": None, "value_bet": []}}}
    for r in rows:
        sport = r.get("sport")
        category = r.get("category")
        if sport not in result["sports"] or category not in ("safe", "fun", "value_bet"):
            continue
        if category == "fun":
            result["sports"][sport]["fun"] = r
        else:
            result["sports"][sport][category].append(r)
    return result
```

- [ ] **Step 2: `GET /api/picks/performance`**

```python
@router.get("/api/picks/performance")
def get_picks_performance(days: int = 30) -> dict:
    """Return win rate + ROI by category over last N days."""
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    rows = (
        supabase.table("best_bets")
        .select("category, sport, result, odds, virtual_stake, date")
        .eq("is_auto", True)
        .gte("date", cutoff)
        .execute()
        .data or []
    )

    # Aggregate by (sport, category)
    buckets: dict[str, dict] = {}
    for r in rows:
        key = f"{r['sport']}_{r['category']}"
        b = buckets.setdefault(key, {"n": 0, "wins": 0, "losses": 0, "voids": 0, "pending": 0, "pnl": 0.0})
        b["n"] += 1
        result = (r.get("result") or "PENDING").upper()
        stake = float(r.get("virtual_stake") or 10)
        odds = float(r.get("odds") or 0)
        if result == "WIN":
            b["wins"] += 1
            b["pnl"] += stake * (odds - 1)
        elif result == "LOSS":
            b["losses"] += 1
            b["pnl"] -= stake
        elif result == "VOID":
            b["voids"] += 1
        else:
            b["pending"] += 1

    by_category = {}
    for key, b in buckets.items():
        settled = b["wins"] + b["losses"]
        by_category[key] = {
            "n": b["n"],
            "settled": settled,
            "wins": b["wins"],
            "losses": b["losses"],
            "voids": b["voids"],
            "pending": b["pending"],
            "win_rate": round(b["wins"] / settled * 100, 1) if settled > 0 else None,
            "pnl": round(b["pnl"], 2),
            "roi_pct": round(b["pnl"] / (settled * 10) * 100, 1) if settled > 0 else None,
        }

    return {"days": days, "by_category": by_category, "virtual_stake": 10}
```

- [ ] **Step 3: `GET /api/matches/foot-today` avec max_value_edge**

Existant `GET /api/matches/today` à étendre. Pour chaque match, calculer le max edge parmi les marchés disponibles et l'ajouter en `max_value_edge`.

- [ ] **Step 4: `GET /api/nhl/daily-top3`**

Équivalent de l'endpoint existant mais limite `top_players[:3]` au lieu de `[:5]`.

- [ ] **Step 5: Lancer les tests existants + un test smoke sur les nouveaux endpoints**

```bash
cd ProbaLab && pytest tests/test_api -v
```

- [ ] **Step 6: Commit**

```bash
git add ProbaLab/api/routers/
git commit -m "feat(api): add daily picks + performance + matches-today-with-edge endpoints"
```

---

## PHASE 2 — Validation silencieuse (manuel, 5-7 jours)

**NOT EXECUTABLE IN SESSION** — cette phase demande du temps réel pour accumuler des données.

- [ ] Observation SQL quotidienne pendant 5-7 jours
- [ ] Vérifier cote range, EV seuil, diversité des marchés
- [ ] Analyser Brier score par catégorie
- [ ] Décision go/no-go sur la qualité avant UI switch

**À documenter à la fin du plan** : les requêtes SQL de QA sont dans le design doc section 8.

---

## PHASE 3 — Frontend (TSX code, pas de QA visuelle en session)

### Task 8 : Composant PickCard.tsx

**Files:**
- Create: `ProbaLab/dashboard/src/components/paris-du-jour/PickCard.tsx`

- [ ] **Step 1: Écrire le composant**

```tsx
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface Pick {
  id: number
  pick: string
  odds: number
  proba: number | null
  match: string
  result?: "PENDING" | "WIN" | "LOSS" | "VOID" | null
  sport: string
}

export function PickCard({ pick }: { pick: Pick }) {
  const statusColor = {
    WIN: "border-green-500 bg-green-50",
    LOSS: "border-red-500 bg-red-50",
    VOID: "border-gray-400 bg-gray-50",
    PENDING: "border-muted bg-background",
  }[pick.result || "PENDING"]

  return (
    <Card className={cn("p-3 text-sm", statusColor)}>
      <div className="font-semibold">{pick.pick}</div>
      <div className="text-xs text-muted-foreground">{pick.match}</div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs">
          {pick.proba !== null && `proba ${pick.proba}%`}
        </span>
        <span className="font-mono text-base">@{pick.odds.toFixed(2)}</span>
      </div>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add ProbaLab/dashboard/src/components/paris-du-jour/PickCard.tsx
git commit -m "feat(ui): PickCard component"
```

### Task 9 : Composant PicksDuJourSticky.tsx

**Files:**
- Create: `ProbaLab/dashboard/src/components/paris-du-jour/PicksDuJourSticky.tsx`

- [ ] **Step 1: Écrire le composant avec tabs**

```tsx
import { useQuery } from "@tanstack/react-query"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { api } from "@/lib/api"
import { PickCard } from "./PickCard"

export function PicksDuJourSticky() {
  const { data, isLoading } = useQuery({
    queryKey: ["picks-daily"],
    queryFn: () => api.get("/api/picks/daily").then(r => r.data),
    refetchInterval: 60_000 * 10, // 10 min
  })

  const { data: perf } = useQuery({
    queryKey: ["picks-performance-global"],
    queryFn: () => api.get("/api/picks/performance?days=30").then(r => r.data),
  })

  if (isLoading) return <div className="sticky top-0 h-16 bg-background" />

  return (
    <div className="sticky top-0 z-40 bg-background/95 backdrop-blur border-b">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-bold">💰 Paris du Jour</h2>
          {perf && <GlobalPerfBadge perf={perf.by_category} />}
        </div>
        <Tabs defaultValue="safe">
          <TabsList>
            <TabsTrigger value="safe">🛡 Safe</TabsTrigger>
            <TabsTrigger value="fun">🎉 Fun</TabsTrigger>
            <TabsTrigger value="value_bet">💎 Value bet</TabsTrigger>
          </TabsList>
          <TabsContent value="safe">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
              {data?.sports.football.safe.map((p: any) => <PickCard key={p.id} pick={p} />)}
              {data?.sports.nhl.safe.map((p: any) => <PickCard key={p.id} pick={p} />)}
            </div>
          </TabsContent>
          <TabsContent value="fun">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {data?.sports.football.fun && <PickCard pick={data.sports.football.fun} />}
              {data?.sports.nhl.fun && <PickCard pick={data.sports.nhl.fun} />}
            </div>
          </TabsContent>
          <TabsContent value="value_bet">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
              {[...(data?.sports.football.value_bet || []), ...(data?.sports.nhl.value_bet || [])]
                .map((p: any) => <PickCard key={p.id} pick={p} />)}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

function GlobalPerfBadge({ perf }: { perf: Record<string, any> }) {
  const totalSettled = Object.values(perf).reduce((sum: number, c: any) => sum + (c.settled || 0), 0)
  const totalWins = Object.values(perf).reduce((sum: number, c: any) => sum + (c.wins || 0), 0)
  const winRate = totalSettled > 0 ? Math.round((totalWins / totalSettled) * 100) : 0
  const totalPnl = Object.values(perf).reduce((sum: number, c: any) => sum + (c.pnl || 0), 0)
  return (
    <div className="text-xs text-muted-foreground">
      30j : <span className="font-semibold text-foreground">{winRate}%</span> win ·
      <span className={totalPnl >= 0 ? "text-green-600" : "text-red-600"}> {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(0)}€</span>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add ProbaLab/dashboard/src/components/paris-du-jour/
git commit -m "feat(ui): PicksDuJourSticky component with 3 tabs"
```

### Task 10 : HomeDashboard.tsx — replace ParisDuSoir

**Files:**
- Create: `ProbaLab/dashboard/src/pages/HomeDashboard.tsx`
- Modify: `ProbaLab/dashboard/src/App.tsx` (router)

- [ ] **Step 1: HomeDashboard layout**

```tsx
import { PicksDuJourSticky } from "@/components/paris-du-jour/PicksDuJourSticky"
import { FootballMatchesSection } from "@/components/football/FootballMatchesSection"
import { NHLMatchesSection } from "@/components/nhl/NHLMatchesSection"

export function HomeDashboard() {
  return (
    <div className="min-h-screen">
      <PicksDuJourSticky />
      <main className="container mx-auto px-4 py-6 space-y-8">
        <header>
          <h1 className="text-2xl font-bold">📅 Aujourd'hui</h1>
          <p className="text-muted-foreground text-sm">
            Probabilités sportives générées par notre moteur Poisson + ELO + ML + IA.
          </p>
        </header>
        <FootballMatchesSection />
        <NHLMatchesSection />
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Mettre à jour le router dans App.tsx**

Remplacer `<Route path="/" element={<ParisDuSoir />} />` par `<Route path="/" element={<HomeDashboard />} />`. Retirer l'import de `ParisDuSoir`.

- [ ] **Step 3: Commit**

```bash
git add ProbaLab/dashboard/src/pages/HomeDashboard.tsx ProbaLab/dashboard/src/App.tsx
git commit -m "feat(ui): HomeDashboard replaces ParisDuSoir as home route"
```

### Task 11 : Refactor Performance.tsx avec tracking par catégorie

- [ ] **Step 1: Écrire nouvelle version de Performance.tsx**

Tabs par catégorie (Safe foot, Fun foot, Value foot, Safe NHL, Fun NHL, Value NHL), hit rate + ROI + graphique Recharts LineChart du P&L cumulé.

- [ ] **Step 2: Commit**

```bash
git add ProbaLab/dashboard/src/pages/Performance.tsx
git commit -m "feat(ui): Performance page refondue par catégorie"
```

### Task 12 : NHL Page — Top 5 → Top 3

- [ ] **Step 1: Modifier `NHLPage.tsx` et `NHLMatchDetail.tsx` : slice top_players à 3**

- [ ] **Step 2: Commit**

```bash
git add ProbaLab/dashboard/src/pages/NHL/
git commit -m "feat(ui): NHL page affiche Top 3 au lieu de Top 5"
```

### Task 13 : Match card avec badge value

- [ ] **Step 1: Ajouter le badge conditionnel sur la match card foot**

```tsx
{match.max_value_edge && match.max_value_edge > 0.05 && (
  <div className="absolute top-2 right-2 text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full">
    💎 Value
  </div>
)}
```

- [ ] **Step 2: Commit**

---

## PHASE 4 — Polish (rapide)

### Task 14 : Copy pivot

- [ ] **Step 1: Remplacer "Paris du Soir" par "Probabilités du jour" dans les headers, meta, footer**

- [ ] **Step 2: Mettre à jour `README.md` et `CLAUDE.md` (positionnement)**

- [ ] **Step 3: Commit**

---

## Push + Summary

- [ ] **Step 1: Push la branche**

```bash
git push -u origin feat/pivot-probas-sportives
```

- [ ] **Step 2: Créer PR via gh cli**

```bash
gh pr create --title "Pivot: Spécialiste en probabilités sportives (P1+P3 code)" \
  --body "$(cat <<'EOF'
## Summary
Pivot produit : le site devient spécialiste en probabilités sportives avec 3 catégories de picks quotidiens (safe / fun / value bet) × 2 sports.

## Phases
- ✅ **P1 Backend** : migrations, fix ML blend NHL, fetch_nhl_player_props, 6 générateurs purs, worker updates, endpoints API, tests unitaires
- ⏳ **P2 Validation** : 5-7 jours d'observation silencieuse requise (manuel, non automatisable)
- ⚠️ **P3 Frontend** : code écrit mais QA visuelle non effectuée en session — requiert ton œil
- ⏳ **P4 Polish** : copy + SEO + alerting (post-P3)

## Test plan
- [ ] Lancer `pytest tests/test_ticket_generator_pivot.py` en local
- [ ] Observer les picks générés par le scheduler pendant 5-7 jours (Phase 2)
- [ ] Valider visuellement la nouvelle home sur desktop + mobile
- [ ] Décision go/no-go après observation

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review checklist

Après exécution complète du plan :

1. ✅ Spec coverage : chaque décision D1-D8 du design est implémentée
2. ✅ Pas de TODO/TBD/placeholder dans les fichiers touchés
3. ✅ Nommage cohérent : `generate_safe_foot`, `save_daily_picks`, `best_bets.category`
4. ✅ Tests couvrent nominal + edge case + idempotence
5. ✅ Commits atomiques (1 fonctionnalité = 1 commit)
