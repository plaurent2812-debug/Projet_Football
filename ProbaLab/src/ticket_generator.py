from __future__ import annotations

"""
ticket_generator.py — Génération quotidienne des pronos.

Stratégie :
  SINGLES (90%) — cotes 1.75–2.20, edge >= 5%, max 4/sport
  DOUBLE  (10%) — combiné 2 legs (~1.40 chacun → ~2.00), 1 max/sport
  FUN     (1/j)  — combo 3-5 legs, cote 15-50, si opportunité

  Football : max 5 paris/soir (4 singles + 1 double)
  NHL      : max 5 paris/soir (4 singles + 1 double)
  Mise     : 1% bankroll (singles/doubles), 0.5% (fun)
"""
from datetime import datetime, timezone

from src.config import logger, supabase

# ═══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════

SINGLE_ODDS_MIN = 1.50
SINGLE_ODDS_MAX = 3.00
MIN_EDGE = 0.05  # 5% edge minimum
MAX_EDGE = 0.25  # 25% edge max — above this the model is likely wrong
MAX_SINGLES = 4
DOUBLE_ODDS_MIN = 1.80
DOUBLE_ODDS_MAX = 2.50
DOUBLE_LEG_ODDS_MIN = 1.20
DOUBLE_LEG_ODDS_MAX = 1.55


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def calculate_implied_odds(probability: float) -> float:
    """Implied odds from model probability with ~5% bookmaker margin."""
    if not probability or probability <= 0:
        return 0.0
    if probability > 100:
        logger.warning(
            "Probability %.1f%% > 100%% in calculate_implied_odds, clamping", probability
        )
        probability = 100.0
    real_prob = max(0.01, probability / 100.0)
    return round((1 / real_prob) * 0.95, 2)


def get_market_odds(real_odds: dict, m_name: str, fallback_proba: float) -> float:
    """Get real odds from DB or fallback to estimate."""
    if not real_odds:
        return calculate_implied_odds(fallback_proba)

    mapping = {
        "1": "home_win_odds",
        "2": "away_win_odds",
        "N": "draw_odds",
        "1N": "dc_1x_odds",
        "N2": "dc_x2_odds",
        "+1.5": "over_15_odds",
        "+2.5": "over_25_odds",
        "BTTS": "btts_yes_odds",
    }
    val = real_odds.get(mapping.get(m_name, ""))
    return val if val else calculate_implied_odds(fallback_proba)


def _compute_edge(proba_model: float, odds: float) -> float:
    """Edge = model implied probability - bookmaker implied probability."""
    if odds <= 1.0 or proba_model <= 0:
        return 0.0
    return (proba_model / 100.0) - (1.0 / odds)


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL — SINGLES (cotes 1.75–2.20, edge >= 5%)
# ═══════════════════════════════════════════════════════════════════


def _build_football_singles(
    predictions: list,
    fixture_map: dict,
    odds_map: dict,
) -> list[dict]:
    """Evaluate all markets for each match, return top singles by edge."""
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
        p25 = (
            pred.get("proba_over_25") or pred.get("proba_over_2_5") or stats.get("proba_over_25", 0)
        )
        p_btts = pred.get("proba_btts") or stats.get("proba_btts", 0)

        match_label = f"{fix['home_team']} - {fix['away_team']}"
        time_str = fix["date"][11:16] if fix.get("date") else ""
        fid = pred.get("fixture_id")

        # Evaluate all single markets
        markets = []

        # 1. Victoire domicile
        if ph >= 55:
            o = get_market_odds(real_odds, "1", ph)
            markets.append(("Victoire domicile", ph, o, f"Victoire {fix['home_team']}"))

        # 2. Victoire extérieur
        if pa >= 55:
            o = get_market_odds(real_odds, "2", pa)
            markets.append(("Victoire extérieur", pa, o, f"Victoire {fix['away_team']}"))

        # 3. Double Chance 1N
        dc_1n = ph + pd
        if dc_1n >= 65:
            o = get_market_odds(real_odds, "1N", dc_1n)
            markets.append(("Double chance 1N", dc_1n, o, "1N"))

        # 4. Double Chance N2
        dc_n2 = pa + pd
        if dc_n2 >= 65:
            o = get_market_odds(real_odds, "N2", dc_n2)
            markets.append(("Double chance N2", dc_n2, o, "N2"))

        # 5. Over 2.5 buts
        if p25 >= 55:
            o = get_market_odds(real_odds, "+2.5", p25)
            markets.append(("Over 2.5 buts", p25, o, "+2.5 buts"))

        # 6. BTTS Oui
        if p_btts >= 55:
            o = get_market_odds(real_odds, "BTTS", p_btts)
            markets.append(("BTTS", p_btts, o, "BTTS Oui"))

        # 7. Over 1.5 buts
        if p15 >= 70:
            o = get_market_odds(real_odds, "+1.5", p15)
            markets.append(("Over 1.5 buts", p15, o, "+1.5 buts"))

        # Filter: odds in range + edge in [5%, 25%]
        for market_name, proba, odds, pick_label in markets:
            if not (SINGLE_ODDS_MIN <= odds <= SINGLE_ODDS_MAX):
                continue
            edge = _compute_edge(proba, odds)
            if edge < MIN_EDGE or edge > MAX_EDGE:
                continue
            candidates.append(
                {
                    "match": match_label,
                    "time": time_str,
                    "pick": pick_label,
                    "proba": round(proba, 1),
                    "odds": round(odds, 2),
                    "edge": round(edge, 4),
                    "sport": "football",
                    "fixture_id": fid,
                    "market_name": market_name,
                }
            )

    # Deduplicate: 1 pick max per match (best edge)
    by_match: dict[str, dict] = {}
    candidates.sort(key=lambda x: x["edge"], reverse=True)
    for c in candidates:
        if c["match"] not in by_match:
            by_match[c["match"]] = c

    singles = sorted(by_match.values(), key=lambda x: x["edge"], reverse=True)
    return singles[:MAX_SINGLES]


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL — DOUBLE (combiné 2 legs, cote ~2.00)
# ═══════════════════════════════════════════════════════════════════


def _build_football_double(
    predictions: list,
    fixture_map: dict,
    odds_map: dict,
    exclude_matches: set[str],
) -> dict | None:
    """Find best 2-leg combo from remaining candidates, target odds ~2.00."""
    candidates = []

    for pred in predictions:
        fix = fixture_map.get(pred["fixture_id"])
        if not fix:
            continue
        match_label = f"{fix['home_team']} - {fix['away_team']}"
        if match_label in exclude_matches:
            continue

        real_odds = (odds_map or {}).get(pred["fixture_id"])
        ph = pred.get("proba_home") or 0
        pd = pred.get("proba_draw") or 0
        pa = pred.get("proba_away") or 0
        stats = pred.get("stats_json") or {}
        p15 = pred.get("proba_over_15") or stats.get("proba_over_15", 0)
        p_btts = pred.get("proba_btts") or stats.get("proba_btts", 0)

        time_str = fix["date"][11:16] if fix.get("date") else ""
        fid = pred.get("fixture_id")

        # Markets with lower odds suitable for doubles (1.20-1.55)
        markets = []
        dc_1n = ph + pd
        dc_n2 = pa + pd
        if dc_1n >= 75:
            o = get_market_odds(real_odds, "1N", dc_1n)
            if DOUBLE_LEG_ODDS_MIN <= o <= DOUBLE_LEG_ODDS_MAX:
                markets.append(("1N", dc_1n, o))
        if dc_n2 >= 75:
            o = get_market_odds(real_odds, "N2", dc_n2)
            if DOUBLE_LEG_ODDS_MIN <= o <= DOUBLE_LEG_ODDS_MAX:
                markets.append(("N2", dc_n2, o))
        if p15 >= 80:
            o = get_market_odds(real_odds, "+1.5", p15)
            if DOUBLE_LEG_ODDS_MIN <= o <= DOUBLE_LEG_ODDS_MAX:
                markets.append(("+1.5 buts", p15, o))
        if p_btts >= 70:
            o = get_market_odds(real_odds, "BTTS", p_btts)
            if DOUBLE_LEG_ODDS_MIN <= o <= DOUBLE_LEG_ODDS_MAX:
                markets.append(("BTTS Oui", p_btts, o))

        if markets:
            best = max(markets, key=lambda m: m[1])  # highest proba
            candidates.append(
                {
                    "match": match_label,
                    "time": time_str,
                    "pick": best[0],
                    "proba": round(best[1], 1),
                    "odds": round(best[2], 2),
                    "sport": "football",
                    "fixture_id": fid,
                }
            )

    if len(candidates) < 2:
        return None

    # Find best pair with combined odds in target range
    best_pair = None
    best_score = 0
    for i in range(min(6, len(candidates))):
        for j in range(i + 1, min(8, len(candidates))):
            total = candidates[i]["odds"] * candidates[j]["odds"]
            if DOUBLE_ODDS_MIN <= total <= DOUBLE_ODDS_MAX:
                proba_score = candidates[i]["proba"] + candidates[j]["proba"]
                odds_penalty = abs(total - 2.0) * 10
                score = proba_score - odds_penalty
                if score > best_score:
                    best_score = score
                    best_pair = [candidates[i], candidates[j]]

    if not best_pair:
        return None

    total_odds = round(best_pair[0]["odds"] * best_pair[1]["odds"], 2)
    return {"type": "DOUBLE", "sport": "football", "picks": best_pair, "total_odds": total_odds}


# ═══════════════════════════════════════════════════════════════════
#  NHL — SINGLES (cotes 1.75–2.20, edge >= 5%)
# ═══════════════════════════════════════════════════════════════════


def _build_nhl_singles(nhl_fixtures: list, odds_map: dict) -> list[dict]:
    """Top NHL player prop singles by edge."""
    candidates = []

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

            # Use real odds if available, otherwise estimate
            real_odds_player = odds_map.get(name, 0)

            props = [
                (prob_goal, "Buteur", "player_goals_over_0.5", 30),
                (prob_point, "1+ Point", "player_points_over_0.5", 50),
                (prob_assist, "Passeur", "player_assists_over_0.5", 35),
                (prob_shot, "3+ Tirs", "player_shots_over_2.5", 35),
            ]

            for prob, label, market, min_prob in props:
                if prob < min_prob:
                    continue
                o = (
                    real_odds_player
                    if real_odds_player and label == "Buteur"
                    else calculate_implied_odds(prob)
                )
                if not (SINGLE_ODDS_MIN <= o <= SINGLE_ODDS_MAX):
                    continue
                edge = _compute_edge(prob, o)
                if edge < MIN_EDGE or edge > MAX_EDGE:
                    continue
                candidates.append(
                    {
                        "match": match_str,
                        "time": "",
                        "pick": f"{name} — {label}",
                        "proba": round(prob, 1),
                        "odds": round(o, 2),
                        "edge": round(edge, 4),
                        "sport": "nhl",
                        "player_name": name,
                        "market_name": market,
                    }
                )

    # Deduplicate: 1 pick max per player (best edge)
    by_player: dict[str, dict] = {}
    candidates.sort(key=lambda x: x["edge"], reverse=True)
    for c in candidates:
        if c["player_name"] not in by_player:
            by_player[c["player_name"]] = c

    singles = sorted(by_player.values(), key=lambda x: x["edge"], reverse=True)
    return singles[:MAX_SINGLES]


# ═══════════════════════════════════════════════════════════════════
#  NHL — DOUBLE (combiné 2 legs, cote ~2.00)
# ═══════════════════════════════════════════════════════════════════


def _build_nhl_double(nhl_fixtures: list, odds_map: dict, exclude_players: set[str]) -> dict | None:
    """Find best 2-player combo, target odds ~2.00."""
    candidates = []

    for fix in nhl_fixtures:
        stats_json = fix.get("stats_json") or {}
        players = stats_json.get("top_players") or []
        match_str = f"{fix.get('home_team', '?')} vs {fix.get('away_team', '?')}"

        for p in players:
            name = p.get("player_name", "")
            if not name or name in exclude_players:
                continue
            prob_point = float(p.get("ml_prob_point") or p.get("prob_point") or 0)
            if prob_point < 50:
                continue
            real = odds_map.get(name, 0)
            o = real if real else calculate_implied_odds(prob_point)
            if DOUBLE_LEG_ODDS_MIN <= o <= DOUBLE_LEG_ODDS_MAX:
                candidates.append(
                    {
                        "match": match_str,
                        "time": "",
                        "pick": f"{name} — 1+ Point",
                        "proba": round(prob_point, 1),
                        "odds": round(o, 2),
                        "sport": "nhl",
                        "player_name": name,
                    }
                )

    if len(candidates) < 2:
        return None

    # Best pair targeting ~2.00
    best_pair = None
    best_score = 0
    for i in range(min(5, len(candidates))):
        for j in range(i + 1, min(8, len(candidates))):
            total = candidates[i]["odds"] * candidates[j]["odds"]
            if DOUBLE_ODDS_MIN <= total <= DOUBLE_ODDS_MAX:
                score = candidates[i]["proba"] + candidates[j]["proba"] - abs(total - 2.0) * 10
                if score > best_score:
                    best_score = score
                    best_pair = [candidates[i], candidates[j]]

    if not best_pair:
        return None
    total_odds = round(best_pair[0]["odds"] * best_pair[1]["odds"], 2)
    return {"type": "DOUBLE", "sport": "nhl", "picks": best_pair, "total_odds": total_odds}


# ═══════════════════════════════════════════════════════════════════
#  FOOTBALL — FUN (cote 15-50, 3-5 legs)
# ═══════════════════════════════════════════════════════════════════


def _build_football_fun(predictions: list, fixture_map: dict, odds_map: dict) -> dict | None:
    """3-5 sélections variées, cote cible 15-50."""
    candidates = []

    for pred in predictions:
        fix = fixture_map.get(pred["fixture_id"])
        if not fix:
            continue

        real_odds = (odds_map or {}).get(pred["fixture_id"])
        ph = pred.get("proba_home") or 0
        pa = pred.get("proba_away") or 0
        stats = pred.get("stats_json") or {}
        p25 = pred.get("proba_over_25") or stats.get("proba_over_25", 0)
        p_btts = pred.get("proba_btts") or stats.get("proba_btts", 0)

        match_label = f"{fix['home_team']} - {fix['away_team']}"
        time_str = fix["date"][11:16] if fix.get("date") else ""
        p_fav = max(ph, pa)

        if ph >= pa:
            fav_name, m_win, p_win = f"Victoire {fix['home_team']}", "1", ph
        else:
            fav_name, m_win, p_win = f"Victoire {fix['away_team']}", "2", pa

        match_options = []

        # Victoire + Over 2.5
        if p_fav >= 50 and p25 >= 55:
            o_win = get_market_odds(real_odds, m_win, p_win)
            o_25 = get_market_odds(real_odds, "+2.5", p25)
            o = round(o_win * o_25 * 0.90, 2)
            p = round((p_win / 100) * (p25 / 100) * 100, 1)
            if o >= 2.0:
                match_options.append({"pick": f"{fav_name} & +2.5 buts", "proba": p, "odds": o})

        # Victoire + BTTS
        if p_fav >= 50 and p_btts >= 55:
            o_win = get_market_odds(real_odds, m_win, p_win)
            o_btts = get_market_odds(real_odds, "BTTS", p_btts)
            o = round(o_win * o_btts * 0.90, 2)
            p = round((p_win / 100) * (p_btts / 100) * 100, 1)
            if o >= 2.0:
                match_options.append({"pick": f"{fav_name} & BTTS", "proba": p, "odds": o})

        # BTTS + Over 2.5
        if p_btts >= 60 and p25 >= 55:
            o_btts = get_market_odds(real_odds, "BTTS", p_btts)
            o_25 = get_market_odds(real_odds, "+2.5", p25)
            o = round(o_btts * o_25 * 0.85, 2)
            p = round((p_btts / 100) * (p25 / 100) * 1.15 * 100, 1)
            if o >= 1.80:
                match_options.append({"pick": "BTTS & +2.5 buts", "proba": p, "odds": o})

        # Victoire seule (outsider)
        if 35 <= p_fav <= 55:
            o = get_market_odds(real_odds, m_win, p_win)
            if o >= 2.50:
                match_options.append({"pick": fav_name, "proba": p_fav, "odds": o})

        # Score exact
        correct_score = stats.get("correct_score", "")
        p_cs = stats.get("proba_correct_score", 0)
        if correct_score and p_cs >= 12 and p_fav >= 60:
            o_cs = calculate_implied_odds(p_cs)
            if o_cs >= 5.0:
                match_options.append(
                    {"pick": f"Score exact {correct_score}", "proba": p_cs, "odds": o_cs}
                )

        if match_options:
            match_options.sort(key=lambda m: (m["proba"] / 100) * m["odds"], reverse=True)
            best = match_options[0]
            candidates.append(
                {
                    "match": match_label,
                    "time": time_str,
                    "pick": best["pick"],
                    "proba": round(best["proba"], 1),
                    "odds": best["odds"],
                    "sport": "football",
                }
            )

    candidates.sort(key=lambda x: x["proba"], reverse=True)
    if len(candidates) < 3:
        return None

    picks = []
    running_odds = 1.0
    for c in candidates:
        if running_odds * c["odds"] > 40:
            continue
        if len(picks) >= 3 and running_odds >= 12:
            combined_proba = 1.0
            for p in picks:
                combined_proba *= p["proba"] / 100
            if combined_proba * (c["proba"] / 100) < 0.02:
                break
        picks.append(c)
        running_odds *= c["odds"]
        if running_odds >= 20 and len(picks) >= 3:
            break
        if len(picks) >= 5:
            break

    if running_odds < 8 or len(picks) < 3:
        return None
    return {
        "type": "FUN",
        "sport": "football",
        "picks": picks,
        "total_odds": round(running_odds, 2),
    }


# ═══════════════════════════════════════════════════════════════════
#  NHL — FUN (buteur + passeur, cote 15-50)
# ═══════════════════════════════════════════════════════════════════


def _build_nhl_fun(nhl_fixtures: list) -> dict | None:
    """2-4 sélections joueurs NHL, cote cible 15-50."""
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
            prob_shot = float(p.get("ml_prob_shot") or p.get("prob_shot") or 0)

            if prob_goal >= 25:
                o = calculate_implied_odds(prob_goal)
                if o >= 2.5:
                    all_picks.append(
                        {
                            "match": match_str,
                            "pick": f"{name} — Buteur",
                            "proba": round(prob_goal, 1),
                            "odds": round(o, 2),
                            "sport": "nhl",
                            "player": name,
                            "market": "goal",
                        }
                    )
            if prob_assist >= 28:
                o = calculate_implied_odds(prob_assist)
                if o >= 2.0:
                    all_picks.append(
                        {
                            "match": match_str,
                            "pick": f"{name} — Passeur",
                            "proba": round(prob_assist, 1),
                            "odds": round(o, 2),
                            "sport": "nhl",
                            "player": name,
                            "market": "assist",
                        }
                    )
            if prob_shot >= 30:
                o = calculate_implied_odds(prob_shot)
                if o >= 2.0:
                    all_picks.append(
                        {
                            "match": match_str,
                            "pick": f"{name} — 3+ Tirs",
                            "proba": round(prob_shot, 1),
                            "odds": round(o, 2),
                            "sport": "nhl",
                            "player": name,
                            "market": "shot",
                        }
                    )

    if len(all_picks) < 2:
        return None

    all_picks.sort(key=lambda x: x["odds"], reverse=True)
    picks = []
    used_players: set[str] = set()
    running_odds = 1.0

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

    for p in all_picks:
        if running_odds >= 50 or len(picks) >= 4:
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

    for p in picks:
        p.pop("player", None)
        p.pop("market", None)
    return {"type": "FUN", "sport": "nhl", "picks": picks, "total_odds": round(running_odds, 2)}


# ═══════════════════════════════════════════════════════════════════
#  DATA LOADERS
# ═══════════════════════════════════════════════════════════════════


def _load_football_data(date: str) -> tuple[list, dict, dict]:
    """Load fixtures, predictions, odds for a given date."""
    start = f"{date}T00:00:00Z"
    end = f"{date}T23:59:59Z"

    try:
        fixtures = (
            supabase.table("fixtures")
            .select("id, api_fixture_id, home_team, away_team, date, league_id")
            .gte("date", start)
            .lte("date", end)
            .neq("status", "PST")
            .neq("status", "CANC")
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "_load_football_data: fixtures fetch failed for date=%s",
            locals().get("start"),
            exc_info=True,
        )
        return [], {}, {}

    fixture_map = {f["id"]: f for f in fixtures}
    api_to_fix = {f["api_fixture_id"]: f["id"] for f in fixtures}

    predictions = []
    odds_map = {}
    if fixtures:
        try:
            predictions = (
                supabase.table("predictions")
                .select("*")
                .in_("fixture_id", [f["id"] for f in fixtures])
                .execute()
            ).data or []
        except Exception:
            logger.warning("_load_football_data: predictions fetch failed", exc_info=True)
        try:
            odds_rows = (
                supabase.table("fixture_odds")
                .select("*")
                .in_("fixture_api_id", [f["api_fixture_id"] for f in fixtures])
                .execute()
            ).data or []
            for o in odds_rows:
                fid = api_to_fix.get(o.get("fixture_api_id"))
                if fid:
                    odds_map[fid] = o
        except Exception:
            logger.warning("_load_football_data: odds fetch failed", exc_info=True)

    return predictions, fixture_map, odds_map


def _load_nhl_data(date: str) -> tuple[list, dict]:
    """Load NHL fixtures and player odds for a given date."""
    start = f"{date}T00:00:00Z"
    end = f"{date}T23:59:59Z"

    try:
        nhl_fixtures = (
            supabase.table("nhl_fixtures")
            .select("id, api_fixture_id, home_team, away_team, date, stats_json, status")
            .gte("date", start)
            .lte("date", end)
            .eq("status", "NS")
            .execute()
        ).data or []
    except Exception:
        logger.warning("_load_nhl_data: nhl_fixtures fetch failed for date=%s", date, exc_info=True)
        nhl_fixtures = []

    # Load real player odds
    odds_map: dict[str, float] = {}
    try:
        odds_rows = (
            supabase.table("nhl_odds")
            .select("player_name, over_odds, bookmaker")
            .eq("game_date", date)
            .execute()
        ).data or []
        for r in odds_rows:
            name = (r.get("player_name") or "").strip()
            price = r.get("over_odds")
            if name and price:
                price = float(price)
                if name not in odds_map or price < odds_map[name]:
                    odds_map[name] = price
    except Exception:
        logger.warning("_load_nhl_data: nhl_odds fetch failed for date=%s", date, exc_info=True)

    return nhl_fixtures, odds_map


# ═══════════════════════════════════════════════════════════════════
#  MARKET MAPPING (for auto-resolution)
# ═══════════════════════════════════════════════════════════════════


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
    # NHL
    if "buteur" in p:
        return "player_goals_over_0.5"
    if "passeur" in p:
        return "player_assists_over_0.5"
    if "point" in p:
        return "player_points_over_0.5"
    if "tir" in p or "shot" in p:
        return "player_shots_over_2.5"
    return pick_str


# ═══════════════════════════════════════════════════════════════════
#  SAVE TO BEST_BETS
# ═══════════════════════════════════════════════════════════════════


def _save_to_best_bets(date: str, sport: str, picks: list[dict], bet_type: str) -> int:
    """Save picks to best_bets table. Returns count saved."""
    rows = []
    confidence = 7 if bet_type == "Single" else (6 if bet_type == "Double" else 5)

    for pick in picks:
        market = _pick_to_market(pick["pick"])
        player_name = ""
        if sport == "nhl":
            parts = pick["pick"].split(" — ")
            if len(parts) >= 2:
                player_name = parts[0].strip()

        proba = pick.get("proba", 0)
        odds_val = pick["odds"]
        edge = (
            round(((proba / 100.0) - (1.0 / odds_val)) * 100, 2)
            if odds_val > 1 and proba > 0
            else None
        )

        rows.append(
            {
                "date": date,
                "sport": sport,
                "bet_label": f"{pick['match']} — {pick['pick']}",
                "market": market,
                "odds": odds_val,
                "confidence": confidence,
                "proba_model": proba,
                "edge_pct": edge,
                "player_name": player_name or None,
                "fixture_id": str(pick.get("fixture_id", "")) or None,
                "result": "PENDING",
                "notes": f"Auto — {bet_type}",
            }
        )

    if not rows:
        return 0

    try:
        supabase.table("best_bets").insert(rows).execute()
        return len(rows)
    except Exception:
        logger.exception("[Tickets] Erreur sauvegarde best_bets")
        return 0


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC API — FOOTBALL PICKS
# ═══════════════════════════════════════════════════════════════════


def generate_football_picks(date: str | None = None) -> dict:
    """Generate daily football picks: singles + double + fun.

    Returns summary dict with counts and details.
    """
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    predictions, fixture_map, odds_map = _load_football_data(date)

    if not predictions:
        logger.info("[Picks Foot] Aucune prédiction pour %s", date)
        return {"date": date, "sport": "football", "singles": 0, "double": 0, "fun": 0}

    # Delete previous auto-picks for this date+sport (idempotent re-run)
    try:
        supabase.table("best_bets").delete().eq("date", date).eq("sport", "football").like(
            "notes", "Auto —%"
        ).execute()
    except Exception:
        logger.warning(
            "Failed to delete previous football auto-picks for date=%s", date, exc_info=True
        )

    # 1. Singles (max 4)
    singles = _build_football_singles(predictions, fixture_map, odds_map)
    n_singles = _save_to_best_bets(date, "football", singles, "Single")

    # 2. Double (1 max, exclude matches already in singles)
    used_matches = {s["match"] for s in singles}
    double = _build_football_double(predictions, fixture_map, odds_map, used_matches)
    n_double = 0
    if double:
        n_double = _save_to_best_bets(date, "football", double["picks"], "Double")

    # 3. Fun (1 max)
    fun = _build_football_fun(predictions, fixture_map, odds_map)
    n_fun = 0
    if fun:
        n_fun = _save_to_best_bets(date, "football", fun["picks"], "Fun")

    total = n_singles + n_double + n_fun
    logger.info(
        "[Picks Foot] %s: %d singles + %d double + %d fun = %d picks",
        date,
        n_singles,
        n_double,
        n_fun,
        total,
    )

    return {
        "date": date,
        "sport": "football",
        "singles": n_singles,
        "double": n_double,
        "fun": n_fun,
        "total": total,
        "singles_detail": singles,
        "double_detail": double,
        "fun_detail": fun,
    }


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC API — NHL PICKS
# ═══════════════════════════════════════════════════════════════════


def generate_nhl_picks(date: str | None = None) -> dict:
    """Generate daily NHL picks: singles + double + fun.

    Returns summary dict with counts and details.
    """
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nhl_fixtures, odds_map = _load_nhl_data(date)

    if not nhl_fixtures:
        logger.info("[Picks NHL] Aucun match NHL pour %s", date)
        return {"date": date, "sport": "nhl", "singles": 0, "double": 0, "fun": 0}

    # Delete previous auto-picks for this date+sport
    try:
        supabase.table("best_bets").delete().eq("date", date).eq("sport", "nhl").like(
            "notes", "Auto —%"
        ).execute()
    except Exception:
        logger.warning("Failed to delete previous NHL auto-picks for date=%s", date, exc_info=True)

    logger.info("[Picks NHL] %d matchs NHL trouvés pour %s", len(nhl_fixtures), date)

    # 1. Singles (max 4)
    singles = _build_nhl_singles(nhl_fixtures, odds_map)
    n_singles = _save_to_best_bets(date, "nhl", singles, "Single")

    # 2. Double (1 max, exclude players already in singles)
    used_players = {s.get("player_name", "") for s in singles}
    double = _build_nhl_double(nhl_fixtures, odds_map, used_players)
    n_double = 0
    if double:
        n_double = _save_to_best_bets(date, "nhl", double["picks"], "Double")

    # 3. Fun (1 max)
    fun = _build_nhl_fun(nhl_fixtures)
    n_fun = 0
    if fun:
        n_fun = _save_to_best_bets(date, "nhl", fun["picks"], "Fun")

    total = n_singles + n_double + n_fun
    logger.info(
        "[Picks NHL] %s: %d singles + %d double + %d fun = %d picks",
        date,
        n_singles,
        n_double,
        n_fun,
        total,
    )

    return {
        "date": date,
        "sport": "nhl",
        "singles": n_singles,
        "double": n_double,
        "fun": n_fun,
        "total": total,
        "singles_detail": singles,
        "double_detail": double,
        "fun_detail": fun,
    }


# ═══════════════════════════════════════════════════════════════════
#  LEGACY WRAPPER (backward compat)
# ═══════════════════════════════════════════════════════════════════


def generate_daily_tickets() -> tuple[dict | None, dict | None]:
    """Legacy wrapper — generates both football + NHL picks."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    foot = generate_football_picks(today)
    nhl = generate_nhl_picks(today)
    # Return in legacy format for any existing callers
    safe = {"type": "SAFE", "football": foot, "nhl": nhl}
    fun = None
    return safe, fun


if __name__ == "__main__":
    logger.info("=== Football Picks ===")
    result_foot = generate_football_picks()
    logger.info(
        "  Singles: %d, Double: %d, Fun: %d",
        result_foot["singles"],
        result_foot["double"],
        result_foot["fun"],
    )

    logger.info("=== NHL Picks ===")
    result_nhl = generate_nhl_picks()
    logger.info(
        "  Singles: %d, Double: %d, Fun: %d",
        result_nhl["singles"],
        result_nhl["double"],
        result_nhl["fun"],
    )
