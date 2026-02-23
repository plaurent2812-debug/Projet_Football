"""
nhl_pipeline.py — Pipeline NHL complet (équivalent du Google Apps Script)

Fetches data from NHL public API (api-web.nhle.com/v1):
- Schedule du jour
- Standings (classements)
- Club-stats (rosters de joueurs + stats saison)
- Goalie form (5 derniers matchs)
- Back-to-back detection

Calcule les scores de probabilité pour chaque joueur (but, passe, point, tir)
avec ajustements: PP%, PK%, fatigue B2B, IA game context (Claude).
Push dans nhl_data_lake + nhl_fixtures dans Supabase.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import supabase, logger

NHL_API = "https://api-web.nhle.com/v1"

TEAM_NAMES = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montréal Canadiens",
    "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks", "SEA": "Seattle Kraken",
    "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Hockey Club", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals", "WPG": "Winnipeg Jets",
}


# ─── HTTP helpers ────────────────────────────────────────────────

def _fetch_json(endpoint: str) -> Optional[dict]:
    """Fetch JSON from NHL API with retries."""
    url = f"{NHL_API}{endpoint}"
    for attempt in range(3):
        try:
            resp = httpx.get(url, timeout=15.0)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1))
            else:
                logger.error(f"[NHL] HTTP {resp.status_code} on {endpoint}")
                return None
        except Exception as e:
            logger.error(f"[NHL] Error fetching {endpoint}: {e}")
            time.sleep(1.0 * (attempt + 1))
    return None


# ─── Data fetchers ───────────────────────────────────────────────

def fetch_schedule() -> list[dict]:
    """Fetch today's NHL games."""
    data = _fetch_json("/schedule/now")
    if not data or "gameWeek" not in data:
        return []

    today = datetime.utcnow().strftime("%Y-%m-%d")
    for day in data["gameWeek"]:
        if day["date"] == today:
            return day.get("games", [])
    for day in data["gameWeek"]:
        if day.get("games"):
            return day["games"]
    return []


def fetch_standings() -> dict:
    """Fetch current standings and return team stats dict."""
    data = _fetch_json("/standings/now")
    if not data or "standings" not in data:
        return {}

    team_stats = {}
    for t in data["standings"]:
        abbrev = t.get("teamAbbrev", {}).get("default", "")
        gp = max(1, t.get("gamesPlayed", 1))
        ga = t.get("goalAgainst", 0)
        gf = t.get("goalFor", 0)
        team_stats[abbrev] = {
            "gaa": round(ga / gp, 2),
            "gf_per_game": round(gf / gp, 2),
            "pp_pct": t.get("powerPlayPctg", 0.20),
            "pk_pct": t.get("penaltyKillPctg", 0.80),
            "l10_pts_pct": t.get("l10PtsPctg", 0.5),
            "wins": t.get("wins", 0),
            "losses": t.get("losses", 0),
            "points": t.get("points", 0),
        }
    return team_stats


def fetch_roster(team: str) -> list[dict]:
    """Fetch skater stats for a team."""
    data = _fetch_json(f"/club-stats/{team}/now")
    if not data:
        return []
    return data.get("skaters", [])


def fetch_goalie_form(teams: list[str]) -> dict:
    """Fetch goalie form (last 5 games GA) for each team."""
    goalie_stats = {}
    for team in set(teams):
        data = _fetch_json(f"/club-schedule-season/{team}/now")
        if not data or "games" not in data:
            goalie_stats[team] = {"form": 0, "reason": "Neutre"}
            continue

        finished = [
            g for g in data["games"]
            if g.get("gameState") in ("FINAL", "OFF")
            and datetime.fromisoformat(g["startTimeUTC"].replace("Z", "+00:00")) < datetime.now().astimezone()
        ]
        finished.sort(key=lambda g: g["startTimeUTC"], reverse=True)
        last5 = finished[:5]

        if not last5:
            goalie_stats[team] = {"form": 0, "reason": "Neutre"}
            continue

        total_ga = 0
        for g in last5:
            is_home = g.get("homeTeam", {}).get("abbrev") == team
            total_ga += g.get("awayTeam" if is_home else "homeTeam", {}).get("score", 0)

        avg_ga = total_ga / len(last5)
        form = 0
        if avg_ga < 2.0:
            form = 0.15
        elif avg_ga < 2.7:
            form = 0.08
        elif avg_ga > 4.2:
            form = -0.15
        elif avg_ga > 3.4:
            form = -0.08

        reason = "Neutre"
        if form > 0.1:
            reason = f"🧱 Mur ({avg_ga:.1f} GA/m L5)"
        elif form > 0:
            reason = f"🛡️ Solide ({avg_ga:.1f} GA/m)"
        elif form < -0.1:
            reason = f"🚨 Passoire ({avg_ga:.1f} GA/m L5)"
        elif form < 0:
            reason = f"⚠️ Friable ({avg_ga:.1f} GA/m)"

        goalie_stats[team] = {"form": form, "reason": reason}

    return goalie_stats


def detect_back_to_back(games: list[dict]) -> set[str]:
    """Detect teams playing back-to-back (played yesterday)."""
    tired_teams = set()
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    schedule_data = _fetch_json("/schedule/now")
    if not schedule_data or "gameWeek" not in schedule_data:
        return tired_teams

    for day in schedule_data["gameWeek"]:
        if day["date"] == yesterday:
            for g in day.get("games", []):
                if g.get("gameState") in ("FINAL", "OFF"):
                    tired_teams.add(g.get("homeTeam", {}).get("abbrev", ""))
                    tired_teams.add(g.get("awayTeam", {}).get("abbrev", ""))
            break

    today_teams = set()
    for g in games:
        today_teams.add(g.get("homeTeam", {}).get("abbrev", ""))
        today_teams.add(g.get("awayTeam", {}).get("abbrev", ""))

    return tired_teams & today_teams


# ─── Player Game Logs (L5 Form + H2H) ───────────────────────────

def fetch_player_game_log(player_id: str) -> list[dict]:
    """Fetch a player's game log for the current season."""
    data = _fetch_json(f"/player/{player_id}/game-log/now")
    if not data or "gameLog" not in data:
        return []
    return data["gameLog"]


def calculate_l5_form(game_log: list[dict]) -> dict:
    """Calculate last-5-games form factor from game log.

    Compares L5 per-game stats vs season average.
    Returns multipliers for goal, assist, point, shot.
    """
    if len(game_log) < 5:
        return {"goal": 1.0, "assist": 1.0, "point": 1.0, "shot": 1.0, "hot": False, "cold": False}

    # Last 5 games (game log is sorted newest first)
    last5 = game_log[:5]
    all_games = game_log

    season_gp = max(1, len(all_games))
    season_goals = sum(g.get("goals", 0) for g in all_games)
    season_assists = sum(g.get("assists", 0) for g in all_games)
    season_points = sum(g.get("points", 0) for g in all_games)
    season_shots = sum(g.get("shots", 0) for g in all_games)

    l5_goals = sum(g.get("goals", 0) for g in last5)
    l5_assists = sum(g.get("assists", 0) for g in last5)
    l5_points = sum(g.get("points", 0) for g in last5)
    l5_shots = sum(g.get("shots", 0) for g in last5)

    def _ratio(l5_val, season_val, n_games):
        """L5 per game / season per game ratio, clamped."""
        season_pg = season_val / season_gp if season_gp > 0 else 0
        l5_pg = l5_val / 5
        if season_pg < 0.05:  # Too low baseline
            return 1.0
        ratio = l5_pg / season_pg
        return max(0.7, min(ratio, 1.5))  # Clamp between 0.7x and 1.5x

    goal_factor = _ratio(l5_goals, season_goals, season_gp)
    assist_factor = _ratio(l5_assists, season_assists, season_gp)
    point_factor = _ratio(l5_points, season_points, season_gp)
    shot_factor = _ratio(l5_shots, season_shots, season_gp)

    is_hot = point_factor > 1.2
    is_cold = point_factor < 0.8

    return {
        "goal": round(goal_factor, 3),
        "assist": round(assist_factor, 3),
        "point": round(point_factor, 3),
        "shot": round(shot_factor, 3),
        "hot": is_hot,
        "cold": is_cold,
        "l5_pts": l5_points,
        "l5_goals": l5_goals,
        "l5_shots": l5_shots,
    }


def calculate_h2h_factor(game_log: list[dict], opponent: str) -> dict:
    """Calculate head-to-head factor vs specific opponent.

    If a player historically performs well against this opponent, boost the scores.
    """
    h2h_games = [g for g in game_log if g.get("opponentAbbrev", "") == opponent]

    if len(h2h_games) < 2:
        return {"goal": 1.0, "point": 1.0, "shot": 1.0, "games": 0}

    all_gp = max(1, len(game_log))
    h2h_gp = len(h2h_games)

    # Per-game rates: H2H vs season
    season_ppg = sum(g.get("points", 0) for g in game_log) / all_gp
    h2h_ppg = sum(g.get("points", 0) for g in h2h_games) / h2h_gp

    season_gpg = sum(g.get("goals", 0) for g in game_log) / all_gp
    h2h_gpg = sum(g.get("goals", 0) for g in h2h_games) / h2h_gp

    season_spg = sum(g.get("shots", 0) for g in game_log) / all_gp
    h2h_spg = sum(g.get("shots", 0) for g in h2h_games) / h2h_gp

    def _h2h_ratio(h2h_val, season_val):
        if season_val < 0.05:
            return 1.0
        ratio = h2h_val / season_val
        return max(0.8, min(ratio, 1.4))  # Clamp: don't over-weight H2H

    return {
        "goal": round(_h2h_ratio(h2h_gpg, season_gpg), 3),
        "point": round(_h2h_ratio(h2h_ppg, season_ppg), 3),
        "shot": round(_h2h_ratio(h2h_spg, season_spg), 3),
        "games": h2h_gp,
    }


# ─── AI Game Context (Claude) ───────────────────────────────────

def get_ai_game_context(games: list[dict], standings: dict) -> dict:
    """Use Claude to analyze game context and get offensive factors per team.

    Returns dict like {"EDM": 1.4, "TOR": 1.0, ...}
    - 0.7 = Defensive game
    - 1.0 = Standard
    - 1.3 = Open game
    - 1.5+ = Offensive festival
    """
    try:
        from brain import ask_claude
    except ImportError:
        logger.warning("[NHL] brain.ask_claude not available — skipping AI context")
        return {}

    games_desc = []
    for g in games:
        h = g.get("homeTeam", {}).get("abbrev", "")
        a = g.get("awayTeam", {}).get("abbrev", "")
        h_stats = standings.get(h, {})
        a_stats = standings.get(a, {})
        games_desc.append(
            f"- {TEAM_NAMES.get(h, h)} (GF/m: {h_stats.get('gf_per_game', '?')}, GAA: {h_stats.get('gaa', '?')}, "
            f"PP: {round(h_stats.get('pp_pct', 0) * 100)}%, L10: {round(h_stats.get('l10_pts_pct', 0) * 100)}%)"
            f" vs "
            f"{TEAM_NAMES.get(a, a)} (GF/m: {a_stats.get('gf_per_game', '?')}, GAA: {a_stats.get('gaa', '?')}, "
            f"PP: {round(a_stats.get('pp_pct', 0) * 100)}%, L10: {round(a_stats.get('l10_pts_pct', 0) * 100)}%)"
        )

    system_prompt = (
        "Tu es un expert en analyse NHL. Pour chaque match, donne un OFFENSIVE_FACTOR "
        "multiplicateur pour chaque équipe.\n"
        "- 0.7 = Match fermé/Défensif\n- 1.0 = Standard\n- 1.3 = Match ouvert\n- 1.5+ = Festival offensif\n\n"
        "Réponds UNIQUEMENT avec un JSON valide: {\"EDM\": 1.4, \"TOR\": 1.0, ...}\n"
        "Pas d'explication, juste le JSON."
    )

    user_prompt = f"Analyse ces matchs NHL ce soir:\n" + "\n".join(games_desc)

    try:
        response = ask_claude(system_prompt, user_prompt)
        if response:
            import json
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"[NHL] AI context parsing failed: {e}")

    return {}


# ─── Player scoring ─────────────────────────────────────────────

def _score_player(skater: dict, team: str, opp: str, my_stats: dict, opp_stats: dict,
                  is_home: bool, goalie_form: dict, tired_teams: set,
                  ai_factors: dict, l5_form: dict = None, h2h: dict = None) -> dict:
    """Score a single player for goal, assist, point, shot probabilities.

    Uses: per-game rates, TOI, opponent GAA, goalie form, PP%, PK%,
    back-to-back fatigue, AI offensive factor.
    """
    name = skater.get("firstName", {}).get("default", "") + " " + skater.get("lastName", {}).get("default", "")
    player_id = str(skater.get("playerId", ""))

    gp = max(1, skater.get("gamesPlayed", 1))
    goals = skater.get("goals", 0)
    assists = skater.get("assists", 0)
    points = skater.get("points", 0)
    toi_per_game = skater.get("avgToi", "00:00")

    # Parse TOI
    try:
        parts = str(toi_per_game).split(":")
        toi_minutes = int(parts[0]) + int(parts[1]) / 60 if len(parts) == 2 else 0
    except (ValueError, IndexError):
        toi_minutes = 0

    # Per-game rates
    gpg = goals / gp
    apg = assists / gp
    ppg = points / gp

    # Calculate shots per game
    shooting_pct = skater.get("shootingPctg", 0)
    shots_per_game = (goals / max(0.01, shooting_pct)) / gp if shooting_pct > 0 else 2.0

    # ─── Adjustment factors ───
    opp_gaa = opp_stats.get("gaa", 3.0) if opp_stats else 3.0
    defense_factor = opp_gaa / 3.0  # >1 = weak defense

    goalie_adj = goalie_form.get(opp, {}).get("form", 0)

    # Power Play boost: good PP% of own team + bad PK% of opponent
    my_pp = my_stats.get("pp_pct", 0.20) if my_stats else 0.20
    opp_pk = opp_stats.get("pk_pct", 0.80) if opp_stats else 0.80
    pp_boost = 1.0 + (my_pp - 0.20) * 0.5 + (0.80 - opp_pk) * 0.5  # Boost if strong PP vs weak PK

    # Back-to-back fatigue penalty
    b2b_penalty = 0.92 if team in tired_teams else 1.0

    # AI offensive factor
    ai_factor = ai_factors.get(team, 1.0)

    # L5 form + H2H adjustments
    l5 = l5_form or {"goal": 1.0, "assist": 1.0, "point": 1.0, "shot": 1.0}
    h2h_adj = h2h or {"goal": 1.0, "point": 1.0, "shot": 1.0}

    # ─── Goal probability ───
    base_goal_prob = min(gpg * 100, 60)
    base_goal_prob *= defense_factor * (1 + goalie_adj) * pp_boost * b2b_penalty * ai_factor
    base_goal_prob *= l5["goal"] * h2h_adj["goal"]  # L5 + H2H
    if is_home:
        base_goal_prob *= 1.05
    if toi_minutes > 20:
        base_goal_prob *= 1.10
    elif toi_minutes > 18:
        base_goal_prob *= 1.05

    # ─── Assist probability ───
    base_assist_prob = min(apg * 100, 60)
    base_assist_prob *= defense_factor * pp_boost * b2b_penalty * ai_factor
    base_assist_prob *= l5["assist"]  # L5 form
    if is_home:
        base_assist_prob *= 1.03
    if toi_minutes > 19:
        base_assist_prob *= 1.08

    # ─── Point probability ───
    base_point_prob = min(ppg * 100, 80)
    base_point_prob *= defense_factor * (1 + goalie_adj * 0.5) * pp_boost * b2b_penalty * ai_factor
    base_point_prob *= l5["point"] * h2h_adj["point"]  # L5 + H2H
    if is_home:
        base_point_prob *= 1.05

    # ─── Shot probability (2.5+ SOG) ───
    base_shot_prob = min(shots_per_game / 2.5 * 50, 90)
    base_shot_prob *= b2b_penalty * ai_factor * l5["shot"] * h2h_adj["shot"]  # L5 + H2H
    if toi_minutes > 19:
        base_shot_prob *= 1.15
    if is_home:
        base_shot_prob *= 1.03

    return {
        "player_id": player_id,
        "player_name": name.strip(),
        "team": team,
        "opp": opp,
        "is_home": 1 if is_home else 0,
        "prob_goal": round(min(base_goal_prob, 65), 1),
        "prob_assist": round(min(base_assist_prob, 65), 1),
        "prob_point": round(min(base_point_prob, 80), 1),
        "prob_shot": round(min(base_shot_prob, 95), 1),
        "algo_score_goal": int(min(base_goal_prob, 100)),
        "algo_score_shot": int(min(base_shot_prob, 100)),
        "goals_per_game": round(gpg, 3),
        "assists_per_game": round(apg, 3),
        "shots_per_game": round(shots_per_game, 1),
        "toi_minutes": round(toi_minutes, 1),
        "games_played": gp,
        "ai_factor": ai_factor,
        "b2b": team in tired_teams,
        "pp_boost": round(pp_boost, 3),
        "l5_form": l5,
        "h2h": h2h_adj,
    }


# ─── Win probability ────────────────────────────────────────────

def calculate_win_prob(home: str, away: str, standings: dict, tired_teams: set) -> dict:
    """Calculate win probability based on standings, PP/PK, and fatigue."""
    h = standings.get(home, {})
    a = standings.get(away, {})

    h_pts = h.get("l10_pts_pct", 0.5)
    a_pts = a.get("l10_pts_pct", 0.5)

    # Power index: L10 form + offensive/defensive balance
    h_power = h_pts * 1.05  # Home ice advantage
    h_power += (h.get("pp_pct", 0.20) - 0.20) * 0.15  # PP bonus
    h_power += (h.get("pk_pct", 0.80) - 0.80) * 0.10  # PK bonus

    a_power = a_pts
    a_power += (a.get("pp_pct", 0.20) - 0.20) * 0.15
    a_power += (a.get("pk_pct", 0.80) - 0.80) * 0.10

    # Back-to-back fatigue
    if home in tired_teams:
        h_power *= 0.95
    if away in tired_teams:
        a_power *= 0.95

    total = h_power + a_power
    if total == 0:
        return {"home": 50, "away": 50}

    home_pct = round(h_power / total * 100)
    away_pct = 100 - home_pct

    return {"home": home_pct, "away": away_pct}


# ─── Main Pipeline ──────────────────────────────────────────────

def run_nhl_pipeline() -> dict:
    """Run the full NHL pipeline: fetch data, score players, save to Supabase."""
    logger.info("=" * 60)
    logger.info("🏒 NHL PIPELINE — Collecte + Analyse + IA")
    logger.info("=" * 60)

    # 1. Fetch schedule
    games = fetch_schedule()
    if not games:
        logger.info("[NHL] Aucun match aujourd'hui.")
        return {"status": "no_games", "matches": 0}

    future_games = [g for g in games if datetime.fromisoformat(
        g["startTimeUTC"].replace("Z", "+00:00")) > datetime.now().astimezone()]

    if not future_games:
        future_games = games  # If all started, analyze all anyway

    logger.info(f"[NHL] {len(games)} matchs trouvés ({len(future_games)} à analyser)")

    # 2. Fetch standings
    standings = fetch_standings()
    logger.info(f"[NHL] Standings chargés pour {len(standings)} équipes")

    # 3. Detect back-to-back teams
    tired_teams = detect_back_to_back(future_games)
    if tired_teams:
        logger.info(f"[NHL] ⚠️ Back-to-back détecté: {', '.join(tired_teams)}")

    # 4. Fetch goalie form
    all_teams = []
    for g in future_games:
        all_teams.append(g.get("homeTeam", {}).get("abbrev", ""))
        all_teams.append(g.get("awayTeam", {}).get("abbrev", ""))
    goalie_form = fetch_goalie_form(all_teams)

    # 5. 🧠 AI Game Context (Claude)
    logger.info("[NHL] 🧠 Analyse IA du contexte des matchs...")
    ai_factors = get_ai_game_context(future_games, standings)
    if ai_factors:
        logger.info(f"[NHL] 🧠 AI factors: {ai_factors}")
    else:
        logger.info("[NHL] 🧠 AI factors: aucun (fallback = 1.0)")

    # 6. Analyze each game
    today = datetime.utcnow().strftime("%Y-%m-%d")
    all_players = []
    fixtures_data = []

    for game in future_games:
        home_abbrev = game.get("homeTeam", {}).get("abbrev", "")
        away_abbrev = game.get("awayTeam", {}).get("abbrev", "")
        game_id = game.get("id", 0)
        start_time = game.get("startTimeUTC", "")

        home_name = TEAM_NAMES.get(home_abbrev, home_abbrev)
        away_name = TEAM_NAMES.get(away_abbrev, away_abbrev)

        b2b_tag = ""
        if home_abbrev in tired_teams:
            b2b_tag += f" ⚠️{home_abbrev} B2B"
        if away_abbrev in tired_teams:
            b2b_tag += f" ⚠️{away_abbrev} B2B"

        ai_tag = ""
        h_ai = ai_factors.get(home_abbrev, 1.0)
        a_ai = ai_factors.get(away_abbrev, 1.0)
        if h_ai > 1.15 or a_ai > 1.15:
            ai_tag = " 🔥"

        logger.info(f"[NHL] Analyse: {home_name} vs {away_name}{b2b_tag}{ai_tag}")

        # Fetch rosters
        home_roster = fetch_roster(home_abbrev)
        away_roster = fetch_roster(away_abbrev)

        h_stats = standings.get(home_abbrev, {})
        a_stats = standings.get(away_abbrev, {})

        # Score players — PASS 1: base scoring (no game logs)
        match_players = []
        for skater in home_roster:
            player = _score_player(skater, home_abbrev, away_abbrev, h_stats, a_stats,
                                   True, goalie_form, tired_teams, ai_factors)
            if player["prob_goal"] > 5 or player["prob_shot"] > 15:
                player["_skater"] = skater  # Keep reference for pass 2
                match_players.append(player)

        for skater in away_roster:
            player = _score_player(skater, away_abbrev, home_abbrev, a_stats, h_stats,
                                   False, goalie_form, tired_teams, ai_factors)
            if player["prob_goal"] > 5 or player["prob_shot"] > 15:
                player["_skater"] = skater
                match_players.append(player)

        # PASS 2: Fetch game logs for top ~15 players per match (L5 form + H2H)
        match_players.sort(key=lambda p: p["prob_point"], reverse=True)
        top_players_for_logs = match_players[:15]
        enhanced_count = 0

        for player in top_players_for_logs:
            pid = player["player_id"]
            opp_abbrev = player["opp"]
            if not pid or pid == "0":
                continue

            game_log = fetch_player_game_log(pid)
            if not game_log:
                continue

            l5 = calculate_l5_form(game_log)
            h2h = calculate_h2h_factor(game_log, opp_abbrev)

            # Re-score with L5 + H2H
            skater = player.pop("_skater", None)
            if skater:
                team = player["team"]
                opp = player["opp"]
                is_home = player["is_home"] == 1
                my_s = standings.get(team, {})
                opp_s = standings.get(opp, {})
                enhanced = _score_player(skater, team, opp, my_s, opp_s,
                                         is_home, goalie_form, tired_teams, ai_factors,
                                         l5_form=l5, h2h=h2h)
                # Update in-place
                idx = match_players.index(player)
                match_players[idx] = enhanced
                enhanced_count += 1

                tag = ""
                if l5.get("hot"):
                    tag += " 🔥HOT"
                if l5.get("cold"):
                    tag += " 🥶COLD"
                if h2h.get("games", 0) >= 2:
                    tag += f" H2H:{h2h['games']}g"
                if tag:
                    logger.info(f"[NHL]   📊 {enhanced['player_name']} ({team}){tag}")

        # Remove internal refs
        for p in match_players:
            p.pop("_skater", None)

        if enhanced_count:
            logger.info(f"[NHL]   ✅ {enhanced_count} joueurs enrichis avec L5+H2H")

        all_players.extend(match_players)

        # Win probabilities
        win_prob = calculate_win_prob(home_abbrev, away_abbrev, standings, tired_teams)

        fixtures_data.append({
            "api_fixture_id": game_id,
            "date": start_time,
            "status": "NS",
            "home_team": home_name,
            "away_team": away_name,
            "proba_home": win_prob["home"],
            "proba_away": win_prob["away"],
            "ai_home_factor": h_ai,
            "ai_away_factor": a_ai,
        })

    # 7. Save to Supabase — nhl_data_lake
    if all_players:
        rows = [
            {
                "date": today,
                "player_id": p["player_id"],
                "player_name": p["player_name"],
                "team": p["team"],
                "opp": p["opp"],
                "algo_score_goal": p["algo_score_goal"],
                "algo_score_shot": p["algo_score_shot"],
                "is_home": p["is_home"],
                "python_prob": round(p["prob_goal"] / 100, 4),
                "python_vol": round(p["shots_per_game"], 2),
            }
            for p in all_players
        ]
        # Delete today's existing data first
        try:
            supabase.table("nhl_data_lake").delete().eq("date", today).execute()
        except Exception:
            pass

        # Insert in batches of 500
        for i in range(0, len(rows), 500):
            try:
                supabase.table("nhl_data_lake").insert(rows[i:i + 500]).execute()
            except Exception as e:
                logger.error(f"[NHL] Error inserting data_lake batch: {e}")

        logger.info(f"[NHL] ✅ {len(rows)} joueurs insérés dans nhl_data_lake")

    # 8. Save to Supabase — nhl_fixtures (upsert)
    for f in fixtures_data:
        try:
            existing = (
                supabase.table("nhl_fixtures")
                .select("id")
                .eq("api_fixture_id", f["api_fixture_id"])
                .execute()
                .data
            )
            predictions = {
                "proba_home": f["proba_home"],
                "proba_away": f["proba_away"],
                "ai_home_factor": f.get("ai_home_factor", 1.0),
                "ai_away_factor": f.get("ai_away_factor", 1.0),
            }
            if existing:
                supabase.table("nhl_fixtures").update({
                    "date": f["date"],
                    "status": f["status"],
                    "home_team": f["home_team"],
                    "away_team": f["away_team"],
                    "predictions_json": predictions,
                }).eq("api_fixture_id", f["api_fixture_id"]).execute()
            else:
                supabase.table("nhl_fixtures").insert({
                    "api_fixture_id": f["api_fixture_id"],
                    "date": f["date"],
                    "status": f["status"],
                    "home_team": f["home_team"],
                    "away_team": f["away_team"],
                    "predictions_json": predictions,
                }).execute()
        except Exception as e:
            logger.error(f"[NHL] Error upserting fixture {f['home_team']} vs {f['away_team']}: {e}")

    logger.info(f"[NHL] ✅ {len(fixtures_data)} matchs insérés dans nhl_fixtures")

    return {
        "status": "ok",
        "matches": len(fixtures_data),
        "players_analyzed": len(all_players),
        "tired_teams": list(tired_teams),
        "ai_factors": ai_factors,
        "fixtures": [
            {
                "match": f"{f['home_team']} vs {f['away_team']}",
                "home_pct": f["proba_home"],
                "away_pct": f["proba_away"],
                "ai": f"🔥" if f.get("ai_home_factor", 1) > 1.15 or f.get("ai_away_factor", 1) > 1.15 else "",
            }
            for f in fixtures_data
        ],
    }
