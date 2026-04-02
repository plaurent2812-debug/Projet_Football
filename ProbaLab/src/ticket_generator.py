from __future__ import annotations

"""
ticket_generator.py — Génération quotidienne des pronos SAFE + FUN.

Règles :
  SAFE (~cote 2.0) :
    - Foot : 2 matchs max — Double Chance + Over 1.5 (combos sûrs)
    - NHL  : 2 joueurs max — Point Over 0.5 (les plus probables)
    → Cote combinée cible : 1.80 – 2.50

  FUN (~cote 20+) :
    - Foot : libre — victoire + buts, buteur, combos audacieux
    - NHL  : buteur + passeur (joueurs spécifiques)
    → Cote combinée cible : 15 – 50

Sélection pilotée par les probabilités du modèle, filtrée par edge vs cotes réelles.
"""
from datetime import datetime

from src.config import logger, supabase


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def calculate_implied_odds(probability: float) -> float:
    """Implied odds from model probability with ~5% bookmaker margin."""
    if not probability or probability <= 0:
        return 0.0
    if probability > 100:
        logger.warning("Probability %.1f%% > 100%% in calculate_implied_odds, clamping", probability)
        probability = 100.0
    real_prob = max(0.01, probability / 100.0)
    return round((1 / real_prob) * 0.95, 2)


def get_market_odds(real_odds: dict, m_name: str, fallback_proba: float) -> float:
    """Get real odds from DB or fallback to estimate."""
    if not real_odds:
        return calculate_implied_odds(fallback_proba)

    mapping = {
        "1": "home_win_odds", "2": "away_win_odds", "N": "draw_odds",
        "1N": "dc_1x_odds", "N2": "dc_x2_odds",
        "+1.5": "over_15_odds", "+2.5": "over_25_odds", "BTTS": "btts_yes_odds",
    }
    val = real_odds.get(mapping.get(m_name, ""))
    return val if val else calculate_implied_odds(fallback_proba)


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL — SAFE (2 matchs, DC + Over 1.5)
# ═══════════════════════════════════════════════════════════════════


def _build_football_safe(predictions: list, fixture_map: dict, odds_map: dict) -> dict | None:
    """2 matchs, meilleur marché adapté par match, cote combinée ~2.0.

    Pour chaque match, explore tous les marchés possibles et choisit celui
    avec le meilleur ratio proba/cote. Marchés considérés :
      - Double Chance (1N / N2) seul
      - Over 1.5 buts seul
      - BTTS Oui seul
      - DC + Over 1.5 combo (si les deux sont forts)
      - Victoire claire (si gros favori)
    """
    candidates = []

    for pred in predictions:
        fix = fixture_map.get(pred["fixture_id"])
        if not fix:
            continue

        real_odds = (odds_map or {}).get(pred["fixture_id"])
        ph = pred.get("proba_home") or 0
        pd = pred.get("proba_draw") or 0
        pa = pred.get("proba_away") or 0

        stats = pred.get("stats_json") or {}
        p15 = pred.get("proba_over_15") or stats.get("proba_over_15", 0)
        p25 = pred.get("proba_over_25") or stats.get("proba_over_25", 0)
        p_btts = pred.get("proba_btts") or stats.get("proba_btts", 0)

        match_label = f"{fix['home_team']} - {fix['away_team']}"
        time_str = fix["date"][11:16] if fix.get("date") else ""

        # Double Chance
        if ph >= pa:
            dc_name, dc_code, p_dc = "1N", "1N", ph + pd
        else:
            dc_name, dc_code, p_dc = "N2", "N2", pa + pd

        # Build all candidate markets for this match
        match_markets = []

        # 1. DC seul (quand très fort, >80%)
        if p_dc >= 80:
            o = get_market_odds(real_odds, dc_code, p_dc)
            if 1.10 <= o <= 1.50:
                match_markets.append({"pick": dc_name, "proba": p_dc, "odds": o})

        # 2. Over 1.5 seul
        if p15 >= 80:
            o = get_market_odds(real_odds, "+1.5", p15)
            if 1.10 <= o <= 1.50:
                match_markets.append({"pick": "+1.5 buts", "proba": p15, "odds": o})

        # 3. BTTS Oui
        if p_btts >= 70:
            o = get_market_odds(real_odds, "BTTS", p_btts)
            if 1.20 <= o <= 1.70:
                match_markets.append({"pick": "BTTS Oui", "proba": p_btts, "odds": o})

        # 4. Victoire claire (gros favori)
        p_fav = max(ph, pa)
        if p_fav >= 62:
            fav_name = f"Victoire {fix['home_team']}" if ph >= pa else f"Victoire {fix['away_team']}"
            m_code = "1" if ph >= pa else "2"
            o = get_market_odds(real_odds, m_code, p_fav)
            if 1.20 <= o <= 1.70:
                match_markets.append({"pick": fav_name, "proba": p_fav, "odds": o})

        # 5. DC + Over 1.5 combo (classique SAFE)
        if p_dc >= 70 and p15 >= 70:
            o_dc = get_market_odds(real_odds, dc_code, p_dc)
            o_15 = get_market_odds(real_odds, "+1.5", p15)
            # Corrélation discount: DC et Over ne sont pas indépendants (home win → more goals).
            # 0.85 = estimation empirique de la réduction de cote due à la corrélation positive.
            o_combo = round(o_dc * o_15 * 0.85, 2)
            p_combo = round((p_dc / 100) * (p15 / 100) * 1.10 * 100, 1)
            p_combo = min(p_combo, max(p_dc, p15))
            if p_combo >= 55 and 1.20 <= o_combo <= 1.80:
                match_markets.append({
                    "pick": f"{dc_name} & +1.5 buts",
                    "proba": p_combo,
                    "odds": o_combo,
                })

        # 6. DC + BTTS combo
        if p_dc >= 70 and p_btts >= 65:
            o_dc = get_market_odds(real_odds, dc_code, p_dc)
            o_btts = get_market_odds(real_odds, "BTTS", p_btts)
            # Corrélation discount: DC et BTTS partagent un signal (victoire implique au moins 1 but).
            # 0.85 = même facteur empirique que DC + Over 1.5.
            o_combo = round(o_dc * o_btts * 0.85, 2)
            p_combo = round((p_dc / 100) * (p_btts / 100) * 1.05 * 100, 1)
            if p_combo >= 50 and 1.30 <= o_combo <= 2.00:
                match_markets.append({
                    "pick": f"{dc_name} & BTTS Oui",
                    "proba": p_combo,
                    "odds": o_combo,
                })

        # Select the best market for this match (highest proba with decent odds)
        if match_markets:
            # Sort by proba descending, then odds ascending (prefer safer bets)
            match_markets.sort(key=lambda m: (m["proba"], -m["odds"]), reverse=True)
            best = match_markets[0]
            candidates.append({
                "match": match_label,
                "time": time_str,
                "pick": best["pick"],
                "proba": round(best["proba"], 1),
                "odds": best["odds"],
                "sport": "football",
            })

    candidates.sort(key=lambda x: x["proba"], reverse=True)

    if len(candidates) < 2:
        return None

    # Try to find the best pair that lands in the 1.80-2.50 target range
    best_pair = None
    best_score = 0
    for i in range(min(5, len(candidates))):
        for j in range(i + 1, min(8, len(candidates))):
            total = candidates[i]["odds"] * candidates[j]["odds"]
            if 1.75 <= total <= 3.00:
                # Score: prefer higher combined proba + closer to 2.0 odds
                proba_score = candidates[i]["proba"] + candidates[j]["proba"]
                odds_penalty = abs(total - 2.0) * 10
                score = proba_score - odds_penalty
                if score > best_score:
                    best_score = score
                    best_pair = [candidates[i], candidates[j]]

    if not best_pair:
        # No valid pair found in target range — skip SAFE ticket
        return None

    total_odds = round(best_pair[0]["odds"] * best_pair[1]["odds"], 2)
    if total_odds < 1.40 or total_odds > 3.50:
        return None

    return {"type": "SAFE", "sport": "football", "picks": best_pair, "total_odds": total_odds}


# ═══════════════════════════════════════════════════════════════════
#  NHL — SAFE (2 joueurs, Point Over 0.5)
# ═══════════════════════════════════════════════════════════════════


def _build_nhl_safe(nhl_fixtures: list) -> dict | None:
    """2 joueurs les plus probables de marquer 1+ point, cote combinée ~2.0."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Load today's odds from nhl_odds
    try:
        odds_rows = (
            supabase.table("nhl_odds")
            .select("player_name, over_odds, bookmaker")
            .eq("game_date", today)
            .execute().data
        ) or []
    except Exception:
        odds_rows = []

    # Best odds per player
    odds_map: dict[str, float] = {}
    for r in odds_rows:
        name = (r.get("player_name") or "").strip()
        price = r.get("over_odds")
        if name and price:
            price = float(price)
            if name not in odds_map or price < odds_map[name]:
                odds_map[name] = price

    # Collect all player predictions from today's fixtures
    candidates = []
    for fix in nhl_fixtures:
        stats_json = fix.get("stats_json") or {}
        players = stats_json.get("top_players") or []
        match_str = f"{fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"

        for p in players:
            prob_point = p.get("ml_prob_point") or p.get("prob_point") or 0
            name = p.get("player_name", "")
            if not name or prob_point < 45:
                continue

            real_odds = odds_map.get(name, 0)
            est_odds = calculate_implied_odds(prob_point) if not real_odds else real_odds

            if est_odds < 1.15 or est_odds > 1.60:
                continue

            candidates.append({
                "match": match_str,
                "time": "",
                "pick": f"{name} — 1+ Point",
                "proba": round(float(prob_point), 1),
                "odds": round(est_odds, 2),
                "sport": "nhl",
            })

    candidates.sort(key=lambda x: x["proba"], reverse=True)

    if len(candidates) < 2:
        return None

    picks = candidates[:2]
    total_odds = round(picks[0]["odds"] * picks[1]["odds"], 2)

    if total_odds < 1.50 or total_odds > 3.00:
        return None

    return {"type": "SAFE", "sport": "nhl", "picks": picks, "total_odds": total_odds}


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL — FUN (cote 20+, victoires + buts)
# ═══════════════════════════════════════════════════════════════════


def _build_football_fun(predictions: list, fixture_map: dict, odds_map: dict) -> dict | None:
    """3-5 sélections variées, cote cible 15-50.

    Explore plusieurs types de marchés par match et choisit les plus
    intéressants (meilleur ratio proba/cote). Marchés possibles :
      - Victoire + Over 2.5
      - Victoire + BTTS
      - BTTS + Over 2.5 (match ouvert sans favori clair)
      - Score exact (très gros favori)
      - Victoire seule (si cote élevée)
    """
    candidates = []

    for pred in predictions:
        fix = fixture_map.get(pred["fixture_id"])
        if not fix:
            continue

        real_odds = (odds_map or {}).get(pred["fixture_id"])
        ph = pred.get("proba_home") or 0
        pd = pred.get("proba_draw") or 0
        pa = pred.get("proba_away") or 0
        stats = pred.get("stats_json") or {}
        p25 = pred.get("proba_over_25") or stats.get("proba_over_25", 0)
        p15 = pred.get("proba_over_15") or stats.get("proba_over_15", 0)
        p_btts = pred.get("proba_btts") or stats.get("proba_btts", 0)

        match_label = f"{fix['home_team']} - {fix['away_team']}"
        time_str = fix["date"][11:16] if fix.get("date") else ""
        p_fav = max(ph, pa)

        if ph >= pa:
            fav_name = f"Victoire {fix['home_team']}"
            m_win, p_win = "1", ph
        else:
            fav_name = f"Victoire {fix['away_team']}"
            m_win, p_win = "2", pa

        match_options = []

        # 1. Victoire + Over 2.5 (classique FUN)
        if p_fav >= 50 and p25 >= 55:
            o_win = get_market_odds(real_odds, m_win, p_win)
            o_25 = get_market_odds(real_odds, "+2.5", p25)
            # Corrélation discount: victoire + buts sont positivement corrélés.
            # 0.90 = discount plus léger que SAFE (0.85) car les marchés FUN tolèrent plus de variance.
            o = round(o_win * o_25 * 0.90, 2)
            p = round((p_win / 100) * (p25 / 100) * 100, 1)
            if o >= 2.0:
                match_options.append({"pick": f"{fav_name} & +2.5 buts", "proba": p, "odds": o})

        # 2. Victoire + BTTS
        if p_fav >= 50 and p_btts >= 55:
            o_win = get_market_odds(real_odds, m_win, p_win)
            o_btts = get_market_odds(real_odds, "BTTS", p_btts)
            # Corrélation discount: victoire implique >= 1 but, corrélation positive avec BTTS.
            o = round(o_win * o_btts * 0.90, 2)
            p = round((p_win / 100) * (p_btts / 100) * 100, 1)
            if o >= 2.0:
                match_options.append({"pick": f"{fav_name} & BTTS", "proba": p, "odds": o})

        # 3. Victoire + Over 1.5 (plus safe mais cote plus basse)
        if p_fav >= 50 and p15 >= 70:
            o_win = get_market_odds(real_odds, m_win, p_win)
            o_15 = get_market_odds(real_odds, "+1.5", p15)
            # Corrélation discount: victoire + Over 1.5 fortement liés (gagner implique marquer).
            o = round(o_win * o_15 * 0.90, 2)
            p = round((p_win / 100) * (p15 / 100) * 1.1 * 100, 1)
            if o >= 1.80:
                match_options.append({"pick": f"{fav_name} & +1.5 buts", "proba": min(p, p_win), "odds": o})

        # 4. BTTS + Over 2.5 (match ouvert, pas besoin de favori)
        if p_btts >= 60 and p25 >= 55:
            o_btts = get_market_odds(real_odds, "BTTS", p_btts)
            o_25 = get_market_odds(real_odds, "+2.5", p25)
            # Corrélation discount: BTTS et Over 2.5 très corrélés (BTTS implique >= 2 buts).
            # 0.85 = discount fort car la dépendance est élevée entre ces deux marchés.
            o = round(o_btts * o_25 * 0.85, 2)
            p = round((p_btts / 100) * (p25 / 100) * 1.15 * 100, 1)
            if o >= 1.80:
                match_options.append({"pick": "BTTS & +2.5 buts", "proba": p, "odds": o})

        # 5. Victoire seule (si la cote est déjà élevée — outsider)
        if 35 <= p_fav <= 55:
            o = get_market_odds(real_odds, m_win, p_win)
            if o >= 2.50:
                match_options.append({"pick": fav_name, "proba": p_fav, "odds": o})

        # 6. Score exact (très gros favori, grosse cote)
        correct_score = stats.get("correct_score", "")
        p_cs = stats.get("proba_correct_score", 0)
        if correct_score and p_cs >= 12 and p_fav >= 60:
            o_cs = calculate_implied_odds(p_cs)
            if o_cs >= 5.0:
                match_options.append({
                    "pick": f"Score exact {correct_score}",
                    "proba": p_cs,
                    "odds": o_cs,
                })

        # Pick the best option for this match: highest EV (proba × odds)
        # This favors picks with real edge, not just high odds
        if match_options:
            match_options.sort(key=lambda m: (m["proba"] / 100) * m["odds"], reverse=True)
            best = match_options[0]
            candidates.append({
                "match": match_label,
                "time": time_str,
                "pick": best["pick"],
                "proba": round(best["proba"], 1),
                "odds": best["odds"],
                "sport": "football",
            })

    # Sort by PROBA descending — prioritize picks most likely to hit
    candidates.sort(key=lambda x: x["proba"], reverse=True)

    if len(candidates) < 3:
        return None

    # Select 3-5 picks targeting combined odds ~20
    # Strategy: take highest-proba picks first, aim for 20x but accept 12x+
    # if adding more picks would tank the combined proba too much
    picks = []
    running_odds = 1.0
    for c in candidates:
        if running_odds * c["odds"] > 40:
            continue
        # If we already have 3+ picks at 12x+ and adding this pick
        # would drop combined proba below 2%, stop here
        if len(picks) >= 3 and running_odds >= 12:
            combined_proba = 1.0
            for p in picks:
                combined_proba *= p["proba"] / 100
            next_proba = combined_proba * (c["proba"] / 100)
            if next_proba < 0.02:  # < 2% combined proba = too risky
                break
        picks.append(c)
        running_odds *= c["odds"]
        if running_odds >= 20 and len(picks) >= 3:
            break
        if len(picks) >= 5:
            break

    if running_odds < 8 or len(picks) < 3:
        return None

    return {"type": "FUN", "sport": "football", "picks": picks, "total_odds": round(running_odds, 2)}


# ═══════════════════════════════════════════════════════════════════
#  NHL — FUN (buteur + passeur, cote 20+)
# ═══════════════════════════════════════════════════════════════════


def _build_nhl_fun(nhl_fixtures: list) -> dict | None:
    """2-4 sélections joueurs NHL, cote cible 15-50.

    Explore plusieurs marchés par joueur :
      - Buteur (≥1 goal) — cote ~3-5
      - Passeur (≥1 assist) — cote ~2.5-4
      - 2+ points — cote ~5-8 (stars uniquement)
      - 3+ tirs cadrés — cote ~2.5-4

    Combine les meilleurs picks de différents matchs et joueurs.
    """
    all_picks = []

    for fix in nhl_fixtures:
        stats_json = fix.get("stats_json") or {}
        players = stats_json.get("top_players") or []
        match_str = f"{fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"

        for p in players:
            name = p.get("player_name", "")
            if not name:
                continue

            prob_goal = float(p.get("ml_prob_goal") or p.get("prob_goal") or 0)
            prob_assist = float(p.get("ml_prob_assist") or p.get("prob_assist") or 0)
            prob_point = float(p.get("ml_prob_point") or p.get("prob_point") or 0)
            prob_shot = float(p.get("ml_prob_shot") or p.get("prob_shot") or 0)

            # Buteur (cote ~3-5)
            if prob_goal >= 25:
                o = calculate_implied_odds(prob_goal)
                if o >= 2.5:
                    all_picks.append({
                        "match": match_str, "pick": f"{name} — Buteur",
                        "proba": round(prob_goal, 1), "odds": round(o, 2),
                        "sport": "nhl", "player": name, "market": "goal",
                    })

            # Passeur (cote ~2.5-4)
            if prob_assist >= 28:
                o = calculate_implied_odds(prob_assist)
                if o >= 2.0:
                    all_picks.append({
                        "match": match_str, "pick": f"{name} — Passeur",
                        "proba": round(prob_assist, 1), "odds": round(o, 2),
                        "sport": "nhl", "player": name, "market": "assist",
                    })

            # 3+ Tirs cadrés (cote ~2.5-4)
            if prob_shot >= 30:
                o = calculate_implied_odds(prob_shot)
                if o >= 2.0:
                    all_picks.append({
                        "match": match_str, "pick": f"{name} — 3+ Tirs",
                        "proba": round(prob_shot, 1), "odds": round(o, 2),
                        "sport": "nhl", "player": name, "market": "shot",
                    })

    if len(all_picks) < 2:
        return None

    # Sort by odds descending (audacious picks for FUN)
    all_picks.sort(key=lambda x: x["odds"], reverse=True)

    # Greedy selection: pick diverse players & markets, target 15-50 odds
    picks = []
    used_players: set[str] = set()
    running_odds = 1.0

    # First pass: prioritize 1 goal + 1 assist (different players)
    goals = [p for p in all_picks if p["market"] == "goal"]
    assists = [p for p in all_picks if p["market"] == "assist"]

    if goals:
        picks.append(goals[0])
        used_players.add(goals[0]["player"])
        running_odds *= goals[0]["odds"]

    for a in assists:
        if a["player"] not in used_players:
            picks.append(a)
            used_players.add(a["player"])
            running_odds *= a["odds"]
            break

    # Second pass: add more picks to reach target odds
    for p in all_picks:
        if running_odds >= 50:
            break
        if len(picks) >= 4:
            break
        if p["player"] in used_players:
            continue
        if running_odds * p["odds"] > 60:
            continue
        picks.append(p)
        used_players.add(p["player"])
        running_odds *= p["odds"]

    if running_odds < 8 or len(picks) < 2:
        return None

    # Clean up internal keys
    for p in picks:
        p.pop("player", None)
        p.pop("market", None)

    return {"type": "FUN", "sport": "nhl", "picks": picks, "total_odds": round(running_odds, 2)}


# ═══════════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════


def generate_daily_tickets() -> tuple[dict | None, dict | None]:
    """Generate daily SAFE and FUN tickets combining Football + NHL.

    Returns (safe_ticket, fun_ticket) where each is a dict with
    'football' and 'nhl' sub-tickets, or None if insufficient data.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    start_of_day = f"{today}T00:00:00Z"
    end_of_day = f"{today}T23:59:59Z"

    # ── Football data ────────────────────────────────────────────
    try:
        fixtures_resp = (
            supabase.table("fixtures")
            .select("id, api_fixture_id, home_team, away_team, date, league_id")
            .gte("date", start_of_day).lte("date", end_of_day)
            .neq("status", "PST").neq("status", "CANC")
            .execute()
        )
        football_fixtures = fixtures_resp.data or []
    except Exception:
        football_fixtures = []

    fixture_map = {f["id"]: f for f in football_fixtures}
    api_to_fix = {f["api_fixture_id"]: f["id"] for f in football_fixtures}

    predictions = []
    odds_map = {}
    if football_fixtures:
        try:
            preds_resp = supabase.table("predictions").select("*").in_(
                "fixture_id", [f["id"] for f in football_fixtures]
            ).execute()
            predictions = preds_resp.data or []
        except Exception:
            pass

        try:
            odds_resp = supabase.table("fixture_odds").select("*").in_(
                "fixture_api_id", [f["api_fixture_id"] for f in football_fixtures]
            ).execute()
            for o in (odds_resp.data or []):
                fid = api_to_fix.get(o.get("fixture_api_id"))
                if fid:
                    odds_map[fid] = o
        except Exception:
            pass

    # ── NHL data ─────────────────────────────────────────────────
    try:
        nhl_resp = (
            supabase.table("nhl_fixtures")
            .select("id, api_fixture_id, home_team, away_team, date, stats_json, status")
            .gte("date", start_of_day).lte("date", end_of_day)
            .eq("status", "NS")
            .execute()
        )
        nhl_fixtures = nhl_resp.data or []
    except Exception:
        nhl_fixtures = []

    logger.info(f"[Tickets] {len(football_fixtures)} matchs foot, {len(nhl_fixtures)} matchs NHL")

    # ── Build tickets ────────────────────────────────────────────
    foot_safe = _build_football_safe(predictions, fixture_map, odds_map) if predictions else None
    nhl_safe = _build_nhl_safe(nhl_fixtures) if nhl_fixtures else None
    foot_fun = _build_football_fun(predictions, fixture_map, odds_map) if predictions else None
    nhl_fun = _build_nhl_fun(nhl_fixtures) if nhl_fixtures else None

    safe_ticket = {
        "type": "SAFE",
        "football": foot_safe,
        "nhl": nhl_safe,
    } if foot_safe or nhl_safe else None

    fun_ticket = {
        "type": "FUN",
        "football": foot_fun,
        "nhl": nhl_fun,
    } if foot_fun or nhl_fun else None

    # ── Save picks to best_bets for auto-resolution & tracking ───
    _save_picks_to_best_bets(today, safe_ticket, fun_ticket)

    return safe_ticket, fun_ticket


# ═══════════════════════════════════════════════════════════════════
#  SAVE TO BEST_BETS (auto-tracking + auto-resolution)
# ═══════════════════════════════════════════════════════════════════

# Market mapping for auto-resolution (must match api/main.py resolve logic)
_MARKET_MAP = {
    "1N": "Double chance 1N",
    "N2": "Double chance N2",
    "+1.5 buts": "Over 1.5 buts",
    "+2.5 buts": "Over 2.5 buts",
    "BTTS Oui": "BTTS",
    "BTTS": "BTTS",
    "BTTS & +2.5 buts": "BTTS + Over 2.5",
}


def _pick_to_market(pick_str: str) -> str:
    """Extract a standardized market name from a pick description."""
    p = pick_str.lower()
    if "victoire" in p and "btts" in p:
        return "Victoire + BTTS"
    if "victoire" in p and "+2.5" in p:
        return "Victoire + Over 2.5"
    if "victoire" in p and "+1.5" in p:
        return "Victoire + Over 1.5"
    if "victoire" in p:
        if "domicile" in p or "dom" in p:
            return "Victoire domicile"
        return "Victoire extérieur" if "ext" in p else "Victoire"
    if "score exact" in p:
        return "Score exact"
    if "btts" in p and "+2.5" in p:
        return "BTTS + Over 2.5"
    if "btts" in p:
        return "BTTS"
    if "+2.5" in p:
        return "Over 2.5 buts"
    if "+1.5" in p:
        return "Over 1.5 buts"
    if "1n" in p:
        return "Double chance 1N"
    if "n2" in p:
        return "Double chance N2"
    # NHL markets
    if "buteur" in p:
        return "player_goals_over_0.5"
    if "passeur" in p:
        return "player_assists_over_0.5"
    if "point" in p:
        return "player_points_over_0.5"
    if "tir" in p or "shot" in p:
        return "player_shots_over_2.5"
    return pick_str


def _save_picks_to_best_bets(
    date: str,
    safe_ticket: dict | None,
    fun_ticket: dict | None,
) -> None:
    """Save generated picks into best_bets table for tracking & auto-resolution."""
    rows = []

    for ticket in [safe_ticket, fun_ticket]:
        if not ticket:
            continue
        ticket_type = ticket["type"]  # SAFE or FUN

        for sport_key in ["football", "nhl"]:
            sub = ticket.get(sport_key)
            if not sub or not sub.get("picks"):
                continue

            sport = sport_key
            for pick in sub["picks"]:
                market = _pick_to_market(pick["pick"])

                # Extract player name for NHL
                player_name = ""
                if sport == "nhl":
                    # Format: "Connor McDavid — Buteur"
                    parts = pick["pick"].split(" — ")
                    if len(parts) >= 2:
                        player_name = parts[0].strip()

                rows.append({
                    "date": date,
                    "sport": sport,
                    "bet_label": f"{pick['match']} — {pick['pick']}",
                    "market": market,
                    "odds": pick["odds"],
                    "confidence": 7 if ticket_type == "SAFE" else 5,
                    "proba_model": pick["proba"],
                    "player_name": player_name or None,
                    "result": "PENDING",
                    "notes": f"Auto-généré {ticket_type}",
                })

    if not rows:
        return

    # Delete today's auto-generated picks first (avoid duplicates on re-run)
    try:
        supabase.table("best_bets").delete().eq("date", date).like("notes", "Auto-généré%").execute()
    except Exception:
        pass

    # Insert new picks
    try:
        supabase.table("best_bets").insert(rows).execute()
        logger.info(f"[Tickets] {len(rows)} picks sauvegardés dans best_bets")
    except Exception as e:
        logger.error(f"[Tickets] Erreur sauvegarde best_bets: {e}")


# ═══════════════════════════════════════════════════════════════════
#  TELEGRAM FORMATTING
# ═══════════════════════════════════════════════════════════════════


def format_telegram_message(safe_ticket: dict | None, fun_ticket: dict | None) -> str:
    """Format tickets as HTML for Telegram."""
    msg = "🏆 <b>PRONOS DU JOUR — ProbaLab IA</b> 🏆\n"
    msg += f"<i>{datetime.now().strftime('%d/%m/%Y')}</i>\n\n"

    if safe_ticket:
        msg += "🛡 <b>TICKET SAFE</b> <i>(cote ~2.0)</i>\n\n"

        for sport_key in ["football", "nhl"]:
            sub = safe_ticket.get(sport_key)
            if not sub:
                continue
            emoji = "⚽" if sport_key == "football" else "🏒"
            msg += f"{emoji} <b>{sport_key.upper()}</b>\n"
            for p in sub["picks"]:
                time_str = f"<code>{p['time']}</code> | " if p.get("time") else ""
                msg += f"  {time_str}{p['match']}\n"
                msg += f"  👉 <b>{p['pick']}</b> <i>(@{p['odds']})</i>\n"
            msg += f"  📊 Cote: <b>{sub['total_odds']}</b>\n\n"
    else:
        msg += "🛡 <i>Pas de Ticket Safe aujourd'hui.</i>\n\n"

    if fun_ticket:
        msg += "🔥 <b>TICKET FUN</b> <i>(cote 20+)</i>\n\n"

        for sport_key in ["football", "nhl"]:
            sub = fun_ticket.get(sport_key)
            if not sub:
                continue
            emoji = "⚽" if sport_key == "football" else "🏒"
            msg += f"{emoji} <b>{sport_key.upper()}</b>\n"
            for p in sub["picks"]:
                msg += f"  👉 <b>{p['pick']}</b> <i>(@{p['odds']})</i>\n"
                msg += f"     {p['match']}\n"
            msg += f"  🚀 Cote: <b>{sub['total_odds']}</b>\n\n"
    else:
        msg += "🔥 <i>Pas de Ticket Fun aujourd'hui.</i>\n\n"

    msg += "<i>⚠️ Jouez responsable. Cotes estimées par le modèle.</i>"
    return msg


if __name__ == "__main__":
    safe, fun = generate_daily_tickets()
    if not safe and not fun:
        print("Aucun ticket généré.")
    else:
        message = format_telegram_message(safe, fun)
        print(message)
