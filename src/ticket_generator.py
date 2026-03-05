from datetime import datetime

from src.config import logger, supabase


def calculate_implied_odds(probability: float) -> float:
    """Calculates the implied odds for a given probability with an assumed bookmaker margin.

    Returns:
        float: Estimated odds (e.g., 2.10). Returns 1.01 if calculation fails.
    """
    if not probability or probability <= 0:
        return 0.0

    # Typical bookmaker margin is roughly 5% to 8%, so we take 0.95
    real_prob = probability / 100.0
    # Avoid division by zero
    if real_prob < 0.01:
        real_prob = 0.01

    estimated_odds = (1 / real_prob) * 0.95
    return round(estimated_odds, 2)


def generate_daily_tickets():
    """Fetches today's fixtures and generates Safe and Fun tickets according to specific rules."""
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Fetch today's fixtures
    start_of_day = f"{today}T00:00:00Z"
    end_of_day = f"{today}T23:59:59Z"

    fixtures_resp = (
        supabase.table("fixtures")
        .select("id, api_fixture_id, home_team, away_team, date, league_id")
        .gte("date", start_of_day)
        .lte("date", end_of_day)
        .neq("status", "PST")
        .neq("status", "CANC")
        .execute()
    )

    if not fixtures_resp or not fixtures_resp.data:
        logger.info("Aucun match trouvé pour aujourd'hui.")
        return None, None

    fixtures = fixtures_resp.data
    todays_fixture_ids = [f["id"] for f in fixtures]
    api_to_fix_id = {f["api_fixture_id"]: f["id"] for f in fixtures}
    fixture_map = {f["id"]: f for f in fixtures}

    # 2. Fetch predictions
    preds_resp = (
        supabase.table("predictions").select("*").in_("fixture_id", todays_fixture_ids).execute()
    )

    if not preds_resp or not preds_resp.data:
        logger.info("Aucune prédiction générée pour aujourd'hui.")
        return None, None

    predictions = preds_resp.data

    # 3. Fetch real odds
    api_fids = [f["api_fixture_id"] for f in fixtures]
    odds_resp = supabase.table("fixture_odds").select("*").in_("fixture_api_id", api_fids).execute()

    odds_map = {}
    if odds_resp and odds_resp.data:
        for o in odds_resp.data:
            fix_id = api_to_fix_id.get(o["fixture_api_id"])
            if fix_id:
                odds_map[fix_id] = o

    return build_safe_ticket(predictions, fixture_map, odds_map), build_fun_ticket(
        predictions, fixture_map, odds_map
    )


def get_market_odds(real_odds: dict, m_name: str, fallback_proba: float) -> float:
    """Helper to get real odds from DB or fallback to estimate."""
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


def build_safe_ticket(predictions: list, fixture_map: dict, odds_map: dict) -> dict:
    """
    Rule Safe:
    - 2 matches precisely.
    - Market: Double Chance (1N or N2) + Plus de 1.5 buts.
    - Select 2 with highest combined probability.
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

        # Fallback to stats_json if top-level columns are None
        stats = pred.get("stats_json") or {}
        p15 = pred.get("proba_over_15")
        if p15 is None:
            p15 = stats.get("proba_over_15", 0)

        # Decide which side is more likely
        if ph >= pa:
            pick_name = "Victoire Domicile ou Nul"
            m_code = "1N"
            p_dc = ph + pd
        else:
            pick_name = "Nul ou Victoire Extérieur"
            m_code = "N2"
            p_dc = pa + pd

        # Check combo proba (rough estimate P(A & B) = P(A)*P(B)*1.1 because of positive correlation)
        # Note: If P(1N) is high and P(+1.5) is high, the combo is very safe.
        p_combo = (p_dc / 100.0) * (p15 / 100.0) * 1.10 * 100.0
        p_combo = min(p_combo, max(p_dc, p15))  # Ceiling

        # Estimate combo odds
        o_dc = get_market_odds(real_odds, m_code, p_dc)
        o_15 = get_market_odds(real_odds, "+1.5", p15)
        # Bookmaker combo odds are usually slightly less than product
        o_combo = o_dc * o_15 * 0.85

        if p_combo > 50 and o_combo >= 1.30:
            candidates.append(
                {
                    "match": f"{fix['home_team']} - {fix['away_team']}",
                    "time": fix["date"][11:16],
                    "pick": f"{pick_name} & +1.5 buts",
                    "proba": p_combo,
                    "odds": round(o_combo, 2),
                }
            )

    # Sort by probability descending
    candidates.sort(key=lambda x: x["proba"], reverse=True)

    # Pick top 2
    if len(candidates) < 2:
        return None

    matches = candidates[:2]
    total_odds = matches[0]["odds"] * matches[1]["odds"]

    return {"type": "SAFE", "matches": matches, "total_odds": round(total_odds, 2)}


def build_fun_ticket(predictions: list, fixture_map: dict, odds_map: dict) -> dict:
    """
    Rule Fun:
    - 5 to 8 matches.
    - Market: Winner (Home or Away) + Goals.
    - Goals rule: +2.5 if proba > 70%, else +1.5 if proba > 75%, else skip match.
    - Never +0.5.
    - Select most probable winners among matches meeting goal criteria.
    """
    candidates = []

    for pred in predictions:
        fix = fixture_map.get(pred["fixture_id"])
        if not fix:
            continue

        real_odds = (odds_map or {}).get(pred["fixture_id"])

        ph = pred.get("proba_home") or 0
        pa = pred.get("proba_away") or 0

        # Fallback to stats_json if top-level columns are None
        stats = pred.get("stats_json") or {}
        p15 = pred.get("proba_over_15")
        if p15 is None:
            p15 = stats.get("proba_over_15", 0)
        p25 = pred.get("proba_over_25")
        if p25 is None:
            # If 2.5 is missing, try to estimate from 1.5 and 3.5
            p35 = stats.get("proba_over_35", 0)
            if p35 > 0:
                p25 = (p15 + p35) / 2
            else:
                p25 = p15 * 0.7  # Conservative estimate

        # Goals criteria
        goal_pick = None
        p_goal = 0
        if p25 > 70:
            goal_pick = "+2.5 buts"
            m_goal = "+2.5"
            p_goal = p25
        elif p15 > 75:
            goal_pick = "+1.5 buts"
            m_goal = "+1.5"
            p_goal = p15
        else:
            # Match doesn't meet goal criteria for FUN ticket
            continue

        # Winner selection
        if ph >= pa:
            winner_name = f"Victoire {fix['home_team']}"
            m_win = "1"
            p_win = ph
        else:
            winner_name = f"Victoire {fix['away_team']}"
            m_win = "2"
            p_win = pa

        # Combo proba
        p_combo = (p_win / 100.0) * (p_goal / 100.0) * 1.15 * 100.0
        p_combo = min(p_combo, p_win)  # Winner is usually the limiting factor

        # Odds
        o_win = get_market_odds(real_odds, m_win, p_win)
        o_goal = get_market_odds(real_odds, m_goal, p_goal)
        o_combo = o_win * o_goal * 0.90

        candidates.append(
            {
                "match": f"{fix['home_team']} - {fix['away_team']}",
                "time": fix["date"][11:16],
                "pick": f"{winner_name} & {goal_pick}",
                "proba": p_combo,
                "odds": round(o_combo, 2),
            }
        )

    # Filter out very low odds if any
    candidates = [c for c in candidates if c["odds"] >= 1.30]

    # Sort by proba
    candidates.sort(key=lambda x: x["proba"], reverse=True)

    # Select 5 to 8
    target_count = min(max(5, len(candidates)), 8)
    if len(candidates) < 5:
        # If we don't have enough, maybe we take what we have or nothing
        if len(candidates) < 3:
            return None
        target_count = len(candidates)

    matches = candidates[:target_count]
    total_odds = 1.0
    for m in matches:
        total_odds *= m["odds"]

    return {"type": "FUN", "matches": matches, "total_odds": round(total_odds, 2)}


def format_telegram_message(safe_ticket: dict, fun_ticket: dict) -> str:
    """Formats the tickets into HTML for Telegram"""

    msg = "🏆 <b>LES PRONOS VIP DU JOUR</b> 🏆\n"
    msg += f"<i>Généré par ProbaLab IA - {datetime.now().strftime('%d/%m/%Y')}</i>\n\n"

    if safe_ticket:
        msg += "🛡 <b>TICKET SAFE (2 Matchs)</b>\n"
        for m in safe_ticket["matches"]:
            msg += f"• <code>{m['time']}</code> | {m['match']}\n"
            msg += f"  👉 <b>{m['pick']}</b> <i>(Cote: {m['odds']})</i>\n"
        msg += f"\n📊 <b>Cote Totale ~ {safe_ticket['total_odds']}</b>\n\n"
    else:
        msg += (
            "🛡 <i>Pas de Ticket Safe disponible avec nos critères de sécurité aujourd'hui.</i>\n\n"
        )

    if fun_ticket:
        msg += "🔥 <b>TICKET FUN (Grosse Cote)</b>\n"
        for m in fun_ticket["matches"]:
            msg += f"• <code>{m['time']}</code> | {m['match']}\n"
            msg += f"  👉 <b>{m['pick']}</b> <i>(Cote: {m['odds']})</i>\n"
        msg += f"\n🚀 <b>Cote Totale ~ {fun_ticket['total_odds']}</b>\n\n"
    else:
        msg += "🔥 <i>Pas de Ticket Fun disponible aujourd'hui.</i>\n\n"

    msg += "<i>⚠️ Jouez uniquement ce que vous pouvez vous permettre de perdre. Les cotes sont des estimations basées sur les données.</i>"
    return msg


if __name__ == "__main__":
    from src.telegram_bot import send_telegram_message

    safe, fun = generate_daily_tickets()
    if not safe and not fun:
        print("Aucun ticket généré.")
    else:
        message = format_telegram_message(safe, fun)
        print(message)

        # Test the send module
        from src.telegram_bot import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS:
            send_telegram_message(message)
        else:
            print("Configuration Telegram manquante.")
