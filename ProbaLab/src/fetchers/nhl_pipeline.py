from __future__ import annotations

"""
nhl_pipeline.py — Pipeline NHL complet (équivalent du Google Apps Script)

Fetches data from NHL public API (api-web.nhle.com/v1):
- Schedule du jour
- Standings (classements)
- Club-stats (rosters de joueurs + stats saison)
- Goalie form (5 derniers matchs)
- Back-to-back detection

Calcule les scores de probabilité pour chaque joueur (but, passe, point, tir)
avec ajustements: PP%, PK%, fatigue B2B, IA game context (Gemini).
Push dans nhl_data_lake + nhl_fixtures dans Supabase.
"""

import math
import time
from datetime import datetime, timedelta, timezone

import httpx

from src.config import logger, supabase
from src.nhl.constants import NHL_TEAM_NAMES as TEAM_NAMES
from src.nhl.constants import get_nhl_season_id

try:
    from src.nhl.ml_models import load_all_models
    from src.nhl.nhl_ml_predictor import is_available as nhl_ml_available
    from src.nhl.nhl_ml_predictor import predict_nhl_match as predict_nhl_match_ml

    ML_MODELS = load_all_models()
except ImportError:
    logger.warning("[NHL] nhl.ml_models not available.")
    ML_MODELS = {}
    def nhl_ml_available(): return False

NHL_API = "https://api-web.nhle.com/v1"

# ─── HTTP helpers ────────────────────────────────────────────────


def _fetch_json(endpoint: str) -> dict | None:
    """Fetch JSON from NHL API with retries."""
    url = f"{NHL_API}{endpoint}"
    for attempt in range(3):
        try:
            resp = httpx.get(url, timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1))
            else:
                logger.error(f"[NHL] HTTP {resp.status_code} on {endpoint}")
                return None
        except Exception:
            logger.warning("[NHL] Error fetching %s (attempt %d)", endpoint, attempt + 1, exc_info=True)
            time.sleep(1.0 * (attempt + 1))
    return None


# ─── Data fetchers ───────────────────────────────────────────────


def fetch_schedule() -> tuple[list[dict], str]:
    """Fetch today's NHL games.
    
    Returns:
        A tuple of (games_list, schedule_date_str).
        schedule_date_str is the NHL "hockey day" date (YYYY-MM-DD),
        which corresponds to the North American date, NOT UTC.
    """
    data = _fetch_json("/schedule/now")
    if not data or "gameWeek" not in data:
        return [], datetime.now(timezone.utc).strftime("%Y-%m-%d")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # 1. Préfère today s'il a effectivement des matchs
    for day in data["gameWeek"]:
        if day["date"] == today and day.get("games"):
            return day["games"], day["date"]
    # 2. Sinon, prochain jour avec matchs (fin de saison, jours off,
    #    ou edge case timezone où "today" UTC est déjà "hier" côté NHL)
    for day in data["gameWeek"]:
        if day.get("games"):
            return day["games"], day["date"]
    return [], today


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
        l10_gp = max(1, t.get("l10GamesPlayed", 10))
        l10_ga = t.get("l10GoalsAgainst", 0)
        team_stats[abbrev] = {
            "gaa": round(ga / gp, 2),
            "gf_per_game": round(gf / gp, 2),
            "pp_pct": t.get("powerPlayPctg", 0.20),
            "pk_pct": t.get("penaltyKillPctg", 0.80),
            "l10_pts_pct": t.get("l10PtsPctg", 0.5),
            "pk_pct": t.get("pkPctg", 80.0) / 100.0,
            "l10_gaa": round(l10_ga / l10_gp, 2),
            "wins": t.get("wins", 0),
            "losses": t.get("losses", 0),
            "points": t.get("points", 0),
            "shots_against_per_game": t.get("shotsAgainstPerGame", 30.0),
        }
    return team_stats


def fetch_team_special_teams() -> dict[str, dict]:
    """Fetch advanced special teams stats from the NHL stats REST API.

    Returns a dict mapping team_full_name -> {
        pk_pct, pk_pct_l10_est, tsh_per_game,
        pp_pct, pp_toi_seconds, pp_opportunities_per_game,
        shots_against_per_game
    }.

    For L10 PK%, we estimate using L10 goals-against from standings
    relative to season GAA as a modifier on season PK%.
    """
    NHL_STATS_API = "https://api.nhle.com/stats/rest/en"
    stats = {}

    # 1. Penalty Kill stats (season)
    try:
        resp = httpx.get(
            f"{NHL_STATS_API}/team/penaltykill",
            params={"cayenneExp": f"seasonId={get_nhl_season_id()} and gameTypeId=2"},
            timeout=15.0,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            for t in resp.json().get("data", []):
                name = t.get("teamFullName", "")
                stats[name] = {
                    "pk_pct": t.get("penaltyKillPct", 0.80),
                    "tsh_per_game": t.get("timesShorthandedPerGame", 3.0),
                    "pk_toi_per_game": t.get("pkTimeOnIcePerGame", 240),
                }
    except Exception:
        logger.warning("[NHL] Failed to fetch PK stats", exc_info=True)

    # 2. Power Play stats (season)
    try:
        resp = httpx.get(
            f"{NHL_STATS_API}/team/powerplay",
            params={"cayenneExp": f"seasonId={get_nhl_season_id()} and gameTypeId=2"},
            timeout=15.0,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            for t in resp.json().get("data", []):
                name = t.get("teamFullName", "")
                if name not in stats:
                    stats[name] = {}
                stats[name]["pp_pct"] = t.get("powerPlayPct", 0.20)
                stats[name]["pp_toi_seconds"] = t.get("ppTimeOnIcePerGame", 240)
                stats[name]["pp_opportunities_per_game"] = t.get(
                    "ppOpportunitiesPerGame", 3.0
                )
    except Exception:
        logger.warning("[NHL] Failed to fetch PP stats", exc_info=True)

    # 3. Summary stats (season) for shots against
    try:
        resp = httpx.get(
            f"{NHL_STATS_API}/team/summary",
            params={"cayenneExp": f"seasonId={get_nhl_season_id()} and gameTypeId=2"},
            timeout=15.0,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            for t in resp.json().get("data", []):
                name = t.get("teamFullName", "")
                if name not in stats:
                    stats[name] = {}
                stats[name]["shots_against_per_game"] = t.get(
                    "shotsAgainstPerGame", 30.0
                )
    except Exception:
        logger.warning("[NHL] Failed to fetch summary stats", exc_info=True)

    logger.info(f"[NHL] Special teams stats loaded for {len(stats)} teams")

    # Convert full team names to abbreviations for compatibility
    name_to_abbrev = {v: k for k, v in TEAM_NAMES.items()}
    result = {}
    for name, data in stats.items():
        abbrev = name_to_abbrev.get(name)
        if abbrev:
            result[abbrev] = data

    return result


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
            g
            for g in data["games"]
            if g.get("gameState") in ("FINAL", "OFF")
            and datetime.fromisoformat(g["startTimeUTC"].replace("Z", "+00:00"))
            < datetime.now(timezone.utc).astimezone()
        ]
        finished.sort(key=lambda g: g["startTimeUTC"], reverse=True)
        last5 = finished[:5]

        if not last5:
            goalie_stats[team] = {"form": 0, "reason": "Neutre"}
            continue

        total_ga = 0
        total_sa = 0
        for g in last5:
            is_home = g.get("homeTeam", {}).get("abbrev") == team
            opp_team_key = "awayTeam" if is_home else "homeTeam"
            my_team_key = "homeTeam" if is_home else "awayTeam"

            ga = g.get(opp_team_key, {}).get("score", 0)
            total_ga += ga

            # Optionally attempt to extract shots if API provides it in `shots` or `sog` fields
            sa = g.get(opp_team_key, {}).get("sog", 30)  # fallback 30 shots if missing
            total_sa += sa

        avg_ga = total_ga / len(last5)
        sv_pct = 1 - (total_ga / max(1, total_sa))

        form = 0
        if sv_pct > 0.930:
            form = 0.20
        elif sv_pct > 0.915:
            form = 0.10
        elif sv_pct < 0.880:
            form = -0.20
        elif sv_pct < 0.895:
            form = -0.10
        else:
            # Fallback to GA logic if SV% is purely estimated (SV% around .900)
            if avg_ga < 2.0:
                form = 0.15
            elif avg_ga < 2.7:
                form = 0.08
            elif avg_ga > 4.2:
                form = -0.15
            elif avg_ga > 3.4:
                form = -0.08

        reason = "Neutre"
        sv_str = f"{sv_pct:.3f}"[1:]  # .925 format
        if form > 0.15:
            reason = f"🧱 Mur ({sv_str} SV%)"
        elif form > 0:
            reason = f"🛡️ Solide ({sv_str} SV%)"
        elif form < -0.15:
            reason = f"🚨 Passoire ({sv_str} SV%)"
        elif form < 0:
            reason = f"⚠️ Friable ({sv_str} SV%)"

        goalie_stats[team] = {"form": form, "reason": reason, "sv_pct": round(sv_pct, 4)}

    return goalie_stats


def detect_fatigue(games: list[dict]) -> dict[str, float]:
    """Detect advanced schedule fatigue (B2B and 3-in-4) for teams playing today.
    Returns a dict mapping team_abbrev to a fatigue multiplier (< 1.0 = tired).
    """
    fatigue_modifiers = {}

    today_teams = set()
    for g in games:
        today_teams.add(g.get("homeTeam", {}).get("abbrev", ""))
        today_teams.add(g.get("awayTeam", {}).get("abbrev", ""))

    if not today_teams:
        return fatigue_modifiers

    # We need the last 3 days to check for 3-in-4 (Today + 3 previous days)
    past_dates = [(datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 4)]
    yesterday_str = past_dates[0]

    schedule_data = _fetch_json("/schedule/now")
    if not schedule_data or "gameWeek" not in schedule_data:
        return fatigue_modifiers

    # Count games played in the last 3 days for teams playing today
    games_played_past_3_days = dict.fromkeys(today_teams, 0)
    played_yesterday = set()

    for day in schedule_data["gameWeek"]:
        date_str = day["date"]
        if date_str in past_dates:
            for g in day.get("games", []):
                if g.get("gameState") in ("FINAL", "OFF"):
                    h = g.get("homeTeam", {}).get("abbrev", "")
                    a = g.get("awayTeam", {}).get("abbrev", "")
                    if h in today_teams:
                        games_played_past_3_days[h] += 1
                        if date_str == yesterday_str:
                            played_yesterday.add(h)
                    if a in today_teams:
                        games_played_past_3_days[a] += 1
                        if date_str == yesterday_str:
                            played_yesterday.add(a)

    for team in today_teams:
        games_past_3 = games_played_past_3_days[team]
        is_b2b = team in played_yesterday

        # Base multiplier is 1.0 (rested)
        mod = 1.0
        if games_past_3 >= 2:
            # Playing 3rd game in 4 nights
            mod = 0.86
        elif is_b2b:
            # Standard Back-to-Back
            mod = 0.92

        if mod < 1.0:
            fatigue_modifiers[team] = mod

    # Ajustement contextuel : si les deux équipes sont fatiguées, l'impact est réduit
    for g in games:
        h = g.get("homeTeam", {}).get("abbrev", "")
        a = g.get("awayTeam", {}).get("abbrev", "")
        if h in fatigue_modifiers and a in fatigue_modifiers:
            # Les deux jouent en B2B/3-in-4, on réduit l'impact de moitié
            h_mod = fatigue_modifiers[h]
            a_mod = fatigue_modifiers[a]
            fatigue_modifiers[h] = h_mod + (1.0 - h_mod) * 0.5
            fatigue_modifiers[a] = a_mod + (1.0 - a_mod) * 0.5

    return fatigue_modifiers


# ─── Player Game Logs (L5 Form + H2H) ───────────────────────────


def fetch_player_game_log(player_id: str) -> list[dict]:
    """Fetch a player's game log for the current season."""
    data = _fetch_json(f"/player/{player_id}/game-log/now")
    if not data or "gameLog" not in data:
        return []
    return data["gameLog"]


def calculate_recent_form(game_log: list[dict]) -> dict:
    """Calculate recent form factors (L5/L10/L20) from game log.

    Compares L5 per-game stats vs season average.
    Implements:
    - M5 vs M10 regression (+15% if L5 points < L10 average)
    - Max Gap Pattern (Flags "due" if current pointless streak >= max pointless streak in L20)
    - Hard TOI Drop Filter (Massive penalty if L3 TOI < L20 TOI - 1.5 mins)
    """
    if len(game_log) < 5:
        return {"goal": 1.0, "assist": 1.0, "point": 1.0, "shot": 1.0, "hot": False, "cold": False, "m5_m10_regression": 1.0, "max_gap_surge": 1.0, "toi_drop_penalty": 1.0}

    # Slices
    last5 = game_log[:5]
    last10 = game_log[:10]
    last20 = game_log[:20]
    last3 = game_log[:3]
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

    # 1. M5 vs M10 Regression
    l10_points = sum(g.get("points", 0) for g in last10)
    l10_pg = l10_points / max(1, len(last10))
    l5_pg = l5_points / 5
    # If standard is decent, but recent is bad => positive regression
    m5_m10_regression = 1.0
    if l10_pg >= 0.5 and l5_pg < l10_pg:
        m5_m10_regression = 1.08  # +8% boost (was 15% — too aggressive per backtest)

    # 2. Max Gap Pattern (Pointless streaks)
    current_streak = 0
    max_streak = 0
    current_count = 0
    # Calculate max streak in L20
    for g in last20:
        if g.get("points", 0) == 0:
            current_count += 1
            if current_count > max_streak:
                max_streak = current_count
        else:
            current_count = 0
    # Calculate current ongoing streak
    for g in game_log:
        if g.get("points", 0) == 0:
            current_streak += 1
        else:
            break

    max_gap_surge = 1.0
    # Removed Gambler's Fallacy: a player being "due" for a goal has no statistical basis.
    # Previous: +30% if current pointless streak matches max streak.
    # Backtest showed this inflated probas for struggling players without improving accuracy.

    days_since_last_game = 999
    if all_games and "gameDate" in all_games[0]:
        try:
            from datetime import datetime, timezone
            last_date = datetime.strptime(all_games[0]["gameDate"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_since_last_game = (datetime.now(timezone.utc) - last_date).days
        except Exception:
            pass

    def _parse_toi(toi_str):
        try:
            parts = str(toi_str).split(":")
            if len(parts) >= 2:
                return int(parts[0]) + int(parts[1]) / 60.0
        except Exception:
            pass
        return 0.0

    # 3. Hard TOI Drop Filter (L3 vs L20)
    l3_toi = sum(_parse_toi(g.get("toi", "00:00")) for g in last3) / max(1, len(last3))
    l20_toi = sum(_parse_toi(g.get("toi", "00:00")) for g in last20) / max(1, len(last20))

    toi_drop_penalty = 1.0
    # If dropped by more than 1.5 minutes recently => severe penalty
    if l20_toi > 12.0 and l3_toi < (l20_toi - 1.5):
        toi_drop_penalty = 0.5  # -50% penalty (Hard constraint)

    # Shooting % Regression
    sh_pct_regression = 1.0
    if season_shots >= 20 and l5_shots >= 5:
        season_pct = season_goals / season_shots
        l5_pct = l5_goals / l5_shots
        diff = season_pct - l5_pct
        if abs(diff) > 0.05:  # Trigger on significant deviation
            impact = max(-0.25, min(0.25, diff))
            weight = min(1.0, l5_shots / 20.0)
            sh_pct_regression = 1.0 + (impact * weight)

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
        "days_since_last_game": days_since_last_game,
        "m5_m10_regression": round(m5_m10_regression, 3),
        "max_gap_surge": round(max_gap_surge, 3),
        "toi_drop_penalty": round(toi_drop_penalty, 3),
        "sh_pct_regression": round(sh_pct_regression, 3),
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


# ─── AI Game Context (Gemini) ───────────────────────────────────


def get_ai_game_context(games: list[dict], standings: dict) -> dict:
    """Use Gemini to analyze game context and get offensive factors per team.

    Returns dict like {"EDM": 1.4, "TOR": 1.0, ...}
    - 0.7 = Defensive game
    - 1.0 = Standard
    - 1.3 = Open game
    - 1.5+ = Offensive festival
    """
    try:
        from src.brain import ask_gemini
    except ImportError:
        logger.warning("[NHL] brain.ask_gemini not available — skipping AI context")
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
        'Réponds UNIQUEMENT avec un JSON valide: {"EDM": 1.4, "TOR": 1.0, ...}\n'
        "Pas d'explication, juste le JSON."
    )

    user_prompt = "Analyse ces matchs NHL ce soir:\n" + "\n".join(games_desc)

    try:
        response = ask_gemini(system_prompt, user_prompt)
        if response:
            import json

            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
    except Exception:
        logger.warning("[NHL] AI context parsing failed", exc_info=True)

    return {}


def get_gemini_nhl_analysis(
    home_team: str, away_team: str, top_players: list[dict], ai_factors: dict,
    injured_info: dict | None = None,
) -> str:
    """Use Gemini to generate a detailed, player-centric NHL match analysis."""
    try:
        from google import genai
        from google.genai import types

        from src.brain import get_active_learnings, get_gemini_client

        client = get_gemini_client()
        if not client:
            return f"{home_team} vs {away_team} : Client Gemini non initialisé."
    except ImportError:
        return f"{home_team} vs {away_team} : Analyse indisponible."

    h_ai = ai_factors.get(home_team, 1.0)
    a_ai = ai_factors.get(away_team, 1.0)

    # Préparez les données des joueurs pour le prompt
    players_data = []
    for p in top_players[:10]:  # Top 10 des joueurs du match
        goal_prob = p.get("prob_goal", 0)
        point_prob = p.get("prob_point", 0)
        assist_prob = p.get("prob_assist", 0)

        # Stats saison (per game)
        gpg = p.get("goals_per_game", 0)
        apg = p.get("assists_per_game", 0)
        ppg = p.get("points_per_game", 0)

        form_tag = (
            "🔥"
            if p.get("l5_form", {}).get("hot")
            else "🥶"
            if p.get("l5_form", {}).get("cold")
            else ""
        )

        players_data.append(
            f"- {p['player_name']} ({p['team']}) {form_tag}: "
            f"Saison: {ppg} pts/m, {gpg} b/m. "
            f"Modèle: But: {goal_prob}%, Point: {point_prob}%"
        )
    players_str = "\n".join(players_data)

    learnings = get_active_learnings("nhl")
    learnings_block = ""
    if learnings:
        learnings_block = "\n\n--- LEÇONS D'AUTO-CORRECTION ---\nPrends en compte tes erreurs passées :\n"
        for i, l in enumerate(learnings, 1):
            learnings_block += f"{i}. {l}\n"
    system_prompt = f"""Tu es un analyste expert de la NHL. 
Ta mission est de fournir une synthèse narrative très courte et percutante (- de 60 mots) qui explique le contexte du match et justifie les notes (sur 10) des joueurs calculées par notre modèle.
{learnings_block}"""

    # Build injury block for prompt
    injury_block = ""
    if injured_info:
        injury_lines = []
        for team_name, names in injured_info.items():
            injury_lines.append(f"  {team_name}: {', '.join(names)} (absent(s))")
        injury_block = "\nJoueurs blessés/absents :\n" + "\n".join(injury_lines) + "\n"

    user_prompt = f"""Match : {home_team} vs {away_team}
Contexte IA d'équipe (Fatigue/Statuts) : Domicile={h_ai:.2f}, Extérieur={a_ai:.2f} (1.0 = Neutre. >1.0 = Avantage, <1.0 = Désavantage)
{injury_block}
Top joueurs (selon modèle) :
{players_str}

Rédige l'analyse."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
        )
        return response.text or "Analyse non disponible."
    except Exception:
        logger.warning("[NHL] AI analysis failed for %s vs %s", home_team, away_team, exc_info=True)
        return f"Échec de l'analyse IA pour {home_team} vs {away_team}."


# ─── Player scoring ─────────────────────────────────────────────


def _score_player(
    skater: dict,
    team: str,
    opp: str,
    my_stats: dict,
    opp_stats: dict,
    is_home: bool,
    goalie_form: dict,
    fatigue_dict: dict,
    ai_factors: dict,
    game_script_mult: float = 1.0,
    l5_form: dict = None,
    h2h: dict = None,
    special_teams: dict = None,
) -> dict:
    """Score a single player for goal, assist, point, shot probabilities.

    Uses: per-game rates, TOI, opponent GAA, goalie form, PP%, PK%,
    back-to-back fatigue, AI offensive factor.
    """
    name = (
        skater.get("firstName", {}).get("default", "")
        + " "
        + skater.get("lastName", {}).get("default", "")
    )
    player_id = str(skater.get("playerId", ""))

    gp = max(1, skater.get("gamesPlayed", 1))
    goals = skater.get("goals", 0)
    assists = skater.get("assists", 0)
    points = skater.get("points", 0)
    pp_goals = skater.get("powerPlayGoals", 0)
    pp_points = skater.get("powerPlayPoints", 0)
    toi_per_game = skater.get("avgToi", "00:00")
    position_code = skater.get("positionCode", "F")  # F (Forward) or D (Defense)

    # Parse TOI
    try:
        parts = str(toi_per_game).split(":")
        toi_minutes = int(parts[0]) + int(parts[1]) / 60 if len(parts) == 2 else 0
    except (ValueError, IndexError):
        toi_minutes = 0

    # ─── Hard Filter Limits ───
    # Bottom-6 / Bottom-Pairing filter
    line_penalty = 1.0
    if position_code == "D" and toi_minutes < 17.5:
        line_penalty = 0.3  # Bottom-Pairing Defenseman
    elif position_code != "D" and toi_minutes < 13.0:
        line_penalty = 0.3  # Bottom-6 Forward

    # Milestone Boost (Psychological advantage near career/season thresholds)
    milestone_boost = 1.0
    if points % 100 == 99 or points == 49 or points == 99:
        milestone_boost = 1.10

    # ─── Volume smoothing (penalize low GP) ───
    volume_factor = min(1.0, (gp + 5) / 20.0)

    # Per-game rates
    gpg = (goals / gp) * volume_factor
    apg = (assists / gp) * volume_factor
    ppg = (points / gp) * volume_factor

    # Calculate shots per game
    shooting_pct = skater.get("shootingPctg", 0)
    shots_per_game = (
        (goals / max(0.01, shooting_pct)) / gp if shooting_pct > 0 else 2.0
    ) * volume_factor

    # ─── Adjustment factors ───
    opp_gaa = opp_stats.get("gaa", 3.0) if opp_stats else 3.0
    defense_factor = opp_gaa / 3.0  # >1 = weak defense

    # Shots Allowed Adjustment (High volume defense -> more expected shots & goals)
    opp_shots_allowed = opp_stats.get("shots_against_per_game", 30.0) if opp_stats else 30.0
    shot_volume_factor = max(0.85, min(1.3, opp_shots_allowed / 30.0))

    goalie_adj = goalie_form.get(opp, {}).get("form", 0)

    # ─── Special Teams Data ───
    st = special_teams or {}
    my_st = st.get(team, {})
    opp_st = st.get(opp, {})

    # Power Play boost: good PP% of own team + bad PK% of opponent
    my_pp = my_st.get("pp_pct", my_stats.get("pp_pct", 0.20) if my_stats else 0.20)

    # FEATURE 1: L10 PK% estimate — use L10 goals data to adjust season PK%
    # If opponent's L10 GAA is worse than season GAA, their recent PK is likely worse too
    opp_pk_season = opp_st.get("pk_pct", opp_stats.get("pk_pct", 0.80) if opp_stats else 0.80)
    l10_gaa = opp_stats.get("l10_gaa", 0) if opp_stats else 0
    season_gaa = opp_stats.get("gaa", 3.0) if opp_stats else 3.0
    if l10_gaa > 0 and season_gaa > 0:
        # If L10 GAA is 20% worse than season, estimate PK is proportionally worse
        gaa_drift = l10_gaa / season_gaa  # >1 = defense worse recently
        # Scale PK% inversely: worse defense = worse PK (clamped)
        pk_l10_modifier = max(0.85, min(1.15, 2.0 - gaa_drift))
        opp_pk = max(0.60, min(0.95, opp_pk_season * pk_l10_modifier))
    else:
        opp_pk = opp_pk_season

    team_pp_advantage = (my_pp - 0.20) * 0.5 + (0.80 - opp_pk) * 0.5  # Raw advantage

    # FEATURE 2: PP TOI Share — fraction of team's PP time this player gets
    # Uses PP points as proxy for PP1 involvement
    pp_reliance = pp_points / max(1, points)
    # Calculate share: player PP points / team total PP goals gives PP1 status
    team_pp_goals = my_st.get("pp_pct", 0.20) * my_st.get("pp_opportunities_per_game", 3.0)
    if team_pp_goals > 0 and gp > 10:
        # Estimate player's share of team's PP production
        player_pp_rate = pp_goals / gp
        pp_share = min(1.0, player_pp_rate / max(0.01, team_pp_goals))
    else:
        pp_share = min(1.0, pp_reliance / 0.30)

    # FEATURE 3: Opponent Penalties Conceded (TSH per game)
    # More penalties by opponent = more PP opportunities = bigger PP boost
    opp_tsh_per_game = opp_st.get("tsh_per_game", 3.0)
    # Average is ~3.0 TSH/game. Scale the PP boost by how undisciplined the opponent is
    opp_penalty_volume = max(0.8, min(1.4, opp_tsh_per_game / 3.0))

    # PP1 Discipline Target (Bonus si PP1 vs Equipe Indisciplinée)
    pp1_discipline_boost = 1.0
    if pp_share > 0.60 and opp_tsh_per_game >= 3.5:
        pp1_discipline_boost = 1.20

    # Final PP boost: team advantage × player share × opponent penalty volume × PP1 Target
    pp_boost = 1.0 + (
        team_pp_advantage * max(0.1, pp_share) * 2.0 * opp_penalty_volume
    ) * pp1_discipline_boost

    # Back-to-back & 3-in-4 fatigue penalty
    b2b_penalty = fatigue_dict.get(team, 1.0)

    # AI offensive factor
    ai_factor = ai_factors.get(team, 1.0)

    # L5 form + H2H adjustments
    l5 = l5_form or {
        "goal": 1.0,
        "assist": 1.0,
        "point": 1.0,
        "shot": 1.0,
        "toi_drop_factor": 1.0,
        "sh_pct_regression": 1.0,
    }
    h2h_adj = h2h or {"goal": 1.0, "point": 1.0, "shot": 1.0}
    toi_drop = l5.get("toi_drop_factor", 1.0)
    sh_regress = l5.get("sh_pct_regression", 1.0)

    # Apply shot volume to expected shots
    exp_shots_base = (
        shots_per_game
        * b2b_penalty
        * ai_factor
        * l5["shot"]
        * h2h_adj["shot"]
        * toi_drop
        * game_script_mult
    )
    exp_shots = exp_shots_base * shot_volume_factor

    # Apply shot volume marginally to goals (more shots = more goal chances)
    # The game script directly applies to goals too, trailing teams score a bit more trying, leading teams score a bit less turtling.
    goal_volume_boost = 1.0 + ((shot_volume_factor - 1.0) * 0.5)
    script_goal_boost = 1.0 + ((game_script_mult - 1.0) * 0.5)

    # ─── Expected Values (Lambda for Poisson) ───
    exp_goals = (
        gpg
        * defense_factor
        * goal_volume_boost
        * script_goal_boost
        * (1 + goalie_adj)
        * pp_boost
        * b2b_penalty
        * ai_factor
        * l5["goal"]
        * h2h_adj["goal"]
        * l5.get("toi_drop_penalty", 1.0)
        * l5.get("m5_m10_regression", 1.0)
        * l5.get("max_gap_surge", 1.0)
        * sh_regress
        * milestone_boost
        * line_penalty
    )
    exp_assists = (
        apg
        * defense_factor
        * goal_volume_boost
        * script_goal_boost
        * pp_boost
        * b2b_penalty
        * ai_factor
        * l5["assist"]
        * l5.get("toi_drop_penalty", 1.0)
        * l5.get("m5_m10_regression", 1.0)
        * l5.get("max_gap_surge", 1.0)
        * milestone_boost
        * line_penalty
    )
    exp_points = (
        ppg
        * defense_factor
        * goal_volume_boost
        * script_goal_boost
        * (1 + goalie_adj * 0.5)
        * pp_boost
        * b2b_penalty
        * ai_factor
        * l5["point"]
        * h2h_adj["point"]
        * l5.get("toi_drop_penalty", 1.0)
        * l5.get("m5_m10_regression", 1.0)
        * l5.get("max_gap_surge", 1.0)
        * sh_regress
        * milestone_boost
        * line_penalty
    )

    # ─── Home & TOI adjustments ───
    if is_home:
        exp_goals *= 1.05
        exp_assists *= 1.03
        exp_points *= 1.05
        exp_shots *= 1.03

    if toi_minutes > 20:
        exp_goals *= 1.10
    elif toi_minutes > 18:
        exp_goals *= 1.05

    if toi_minutes > 19:
        exp_assists *= 1.08
        exp_shots *= 1.15

    # ─── Lambda clamping (prevents 15-multiplier stacking from producing extremes) ───
    # A player scoring > 0.8 goals/game is unrealistic even for McDavid (~0.55).
    # Similarly, no skater realistically has > 5 expected shots.
    exp_goals = max(0.02, min(0.80, exp_goals))
    exp_assists = max(0.02, min(1.0, exp_assists))
    exp_points = max(0.05, min(1.5, exp_points))
    exp_shots = max(0.5, min(6.0, exp_shots))

    # ─── Zero-Inflated Poisson (ZIP) Probabilities ───
    # Calculate theta_zero: the structural probability of producing a "zero"
    # regardless of talent (due to bottom-line assignments or defensive roles).
    # Recalibrated march 2026: backtest showed avg predicted > actual hit rate,
    # meaning theta_zero values were slightly too aggressive for middle tiers.
    theta_zero = 0.04  # Base structural zero (injury mid-game, bad luck)

    if position_code == "D":
        if toi_minutes < 18.0:
            theta_zero = 0.40  # Bottom pairing D-men (was 0.45)
        elif toi_minutes < 22.0:
            theta_zero = 0.15  # Top 4 D-men (was 0.20)
        else:
            theta_zero = 0.08  # Elite offensive D-men (was 0.10)
    else:  # Forwards
        if toi_minutes < 13.0:
            theta_zero = 0.35  # 4th line (was 0.40)
        elif toi_minutes < 15.5:
            theta_zero = 0.15  # 3rd line (was 0.20)
        elif toi_minutes < 18.0:
            theta_zero = 0.06  # 2nd line (was 0.08)
        else:
            theta_zero = 0.03  # 1st line stars (was 0.04)

    # ZIP formula for P(X >= 1) = (1 - theta_zero) * (1 - e^(-lambda))
    prob_goal = (1.0 - theta_zero) * (1 - math.exp(-max(0, exp_goals))) * 100
    prob_assist = (1.0 - theta_zero) * (1 - math.exp(-max(0, exp_assists))) * 100
    prob_point = (1.0 - theta_zero) * (1 - math.exp(-max(0, exp_points))) * 100

    # For shots (Over 2.5), we apply a smaller structural zero
    # since even 4th liners can occasionally throw pucks on net.
    theta_zero_shots = theta_zero * 0.5
    l_s = max(0, exp_shots)
    p0 = math.exp(-l_s)
    p1 = p0 * l_s
    p2 = p1 * l_s / 2
    # ZIP formula for P(X >= 3)
    zip_p0 = theta_zero_shots + (1 - theta_zero_shots) * p0
    zip_p1 = (1 - theta_zero_shots) * p1
    zip_p2 = (1 - theta_zero_shots) * p2
    prob_shot = (1.0 - (zip_p0 + zip_p1 + zip_p2)) * 100

    res = {
        "player_id": player_id,
        "player_name": name.strip(),
        "team": team,
        "opp": opp,
        "is_home": 1 if is_home else 0,
        "prob_goal": min(95.0, round(prob_goal, 1)),
        "prob_assist": min(95.0, round(prob_assist, 1)),
        "prob_point": min(99.0, round(prob_point, 1)),
        "prob_shot": min(95.0, round(prob_shot, 1)),
        "algo_score_goal": int(min(100, prob_goal)),
        "algo_score_shot": int(min(100, prob_shot)),
        "goals_per_game": round(gpg, 3),
        "assists_per_game": round(apg, 3),
        "points_per_game": round(ppg, 3),
        "shots_per_game": round(shots_per_game, 1),
        "toi_minutes": round(toi_minutes, 1),
        "games_played": gp,
        "ai_factor": ai_factor,
        "b2b": fatigue_dict.get(team, 1.0) < 1.0,
        "pp_boost": round(pp_boost, 3),
        "pp_reliance": round(pp_reliance, 2),
        "pp_share": round(pp_share, 3),
        "opp_pk_l10_est": round(opp_pk, 4),
        "opp_tsh_per_game": round(opp_tsh_per_game, 2),
        "opp_penalty_volume": round(opp_penalty_volume, 3),
        "fatigue_penalty": round(b2b_penalty, 2),
        "sh_pct_regression": round(sh_regress, 2),
        "l5_form": l5,
        "h2h": h2h_adj,
        "opp_sv_pct": round(goalie_form.get(opp, {}).get("sv_pct", 0.903), 3),
    }

    # ─── Machine Learning Predictions ───
    if "GOAL" in ML_MODELS:
        res["ml_prob_goal"] = round(ML_MODELS["GOAL"].predict_proba(res) * 100, 1)
    if "ASSIST" in ML_MODELS:
        res["ml_prob_assist"] = round(ML_MODELS["ASSIST"].predict_proba(res) * 100, 1)
    if "POINT" in ML_MODELS:
        res["ml_prob_point"] = round(ML_MODELS["POINT"].predict_proba(res) * 100, 1)
    if "SHOT" in ML_MODELS:
        res["ml_prob_shot"] = round(ML_MODELS["SHOT"].predict_proba(res) * 100, 1)

    return res


# ─── Win probability ────────────────────────────────────────────


def calculate_win_prob(home: str, away: str, standings: dict, fatigue_dict: dict) -> dict:
    """Calculate win probability and Over 5.5 using a team-level Poisson model."""
    h = standings.get(home, {})
    a = standings.get(away, {})

    # Per-game goals scored & conceded (already computed by fetch_standings)
    h_gf = float(h.get("gf_per_game", 3.1))  # goals scored per game
    h_ga = float(h.get("gaa", 3.1))            # goals conceded per game
    a_gf = float(a.get("gf_per_game", 3.1))
    a_ga = float(a.get("gaa", 3.1))

    league_gf = 3.1  # Moyenne historique NHL

    h_atk = max(0.5, h_gf / league_gf)
    h_def = max(0.5, h_ga / league_gf)
    a_atk = max(0.5, a_gf / league_gf)
    a_def = max(0.5, a_ga / league_gf)

    # Base xG avec léger avantage domicile
    h_xg = h_atk * a_def * league_gf * 1.05
    a_xg = a_atk * h_def * league_gf * 0.95

    # Ajustement forme récente (L10)
    h_form = h.get("l10_pts_pct", 0.5)
    a_form = a.get("l10_pts_pct", 0.5)

    h_xg *= 0.9 + 0.2 * h_form
    a_xg *= 0.9 + 0.2 * a_form

    # Ajustement PP/PK (special teams edge)
    h_pp = h.get("pp_pct", 0.20)
    a_pk = a.get("pk_pct", 0.80)
    a_pp = a.get("pp_pct", 0.20)
    h_pk = h.get("pk_pct", 0.80)
    # A strong PP vs weak PK = slight xG boost
    h_xg *= 1.0 + 0.1 * (h_pp - (1.0 - a_pk))
    a_xg *= 1.0 + 0.1 * (a_pp - (1.0 - h_pk))

    # Fatigue
    h_xg *= fatigue_dict.get(home, 1.0)
    a_xg *= fatigue_dict.get(away, 1.0)

    # Clamp xG to reasonable range
    h_xg = max(1.5, min(5.5, h_xg))
    a_xg = max(1.5, min(5.5, a_xg))

    # Grille Poisson pour prédire le vainqueur et l'Over
    import numpy as np
    from scipy.stats import poisson

    max_goals = 15
    goals = np.arange(max_goals)
    pmf_home = poisson.pmf(goals, h_xg)
    pmf_away = poisson.pmf(goals, a_xg)
    grid = np.outer(pmf_home, pmf_away)

    home_win_reg = float(np.tril(grid, k=-1).sum())
    away_win_reg = float(np.triu(grid, k=1).sum())
    draw_reg = float(np.trace(grid))

    # Répartition du nul (Prolongation / Tirs au but)
    ot_home_share = (
        home_win_reg / (home_win_reg + away_win_reg) if (home_win_reg + away_win_reg) > 0 else 0.5
    )
    home_win_total = home_win_reg + draw_reg * ot_home_share
    away_win_total = away_win_reg + draw_reg * (1.0 - ot_home_share)

    home_pct = round(home_win_total * 100)
    away_pct = round(away_win_total * 100)

    # Prédiction Over 5.5
    total_goals_grid = goals[:, None] + goals[None, :]
    over_55 = float(grid[total_goals_grid > 5].sum())

    return {"home": home_pct, "away": away_pct, "over_55": round(over_55 * 100)}


# ─── Main Pipeline ──────────────────────────────────────────────


def run_nhl_pipeline() -> dict:
    """Run the full NHL pipeline: fetch data, score players, save to Supabase."""
    logger.info("=" * 60)
    logger.info("🏒 NHL PIPELINE — Collecte + Analyse + IA")
    logger.info("=" * 60)

    # 1. Fetch schedule
    games, schedule_date = fetch_schedule()
    if not games:
        logger.info("[NHL] Aucun match aujourd'hui.")
        return {"status": "no_games", "matches": 0}
    logger.info(f"[NHL] Date du schedule NHL : {schedule_date}")

    future_games = [
        g
        for g in games
        if datetime.fromisoformat(g["startTimeUTC"].replace("Z", "+00:00"))
        > datetime.now(timezone.utc).astimezone()
    ]

    if not future_games:
        future_games = games  # If all started, analyze all anyway

    logger.info(f"[NHL] {len(games)} matchs trouvés ({len(future_games)} à analyser)")

    # 2. Fetch standings
    standings = fetch_standings()
    logger.info(f"[NHL] Standings chargés pour {len(standings)} équipes")

    # 2b. Fetch special teams stats (PK%, PP%, PIM, shots against)
    special_teams = fetch_team_special_teams()
    # Enrich standings with special teams data (shots_against, pk_pct, pp_pct)
    for abbrev, st_data in special_teams.items():
        if abbrev in standings:
            if "shots_against_per_game" in st_data:
                standings[abbrev]["shots_against_per_game"] = st_data["shots_against_per_game"]
            if "pk_pct" in st_data:
                standings[abbrev]["pk_pct"] = st_data["pk_pct"]
            if "pp_pct" in st_data:
                standings[abbrev]["pp_pct"] = st_data["pp_pct"]

    # 3. Detect schedule fatigue (B2B and 3-in-4)
    fatigue_dict = detect_fatigue(future_games)
    if fatigue_dict:
        tired_str = []
        for t, m in fatigue_dict.items():
            if m < 0.90:
                tired_str.append(f"{t} (3-in-4)")
            else:
                tired_str.append(f"{t} (B2B)")
        logger.info(f"[NHL] ⚠️ Fatigue détectée: {', '.join(tired_str)}")

    # 4. Fetch goalie form
    all_teams = []
    for g in future_games:
        all_teams.append(g.get("homeTeam", {}).get("abbrev", ""))
        all_teams.append(g.get("awayTeam", {}).get("abbrev", ""))
    goalie_form = fetch_goalie_form(all_teams)

    # 5. 🧠 AI Game Context (Gemini)
    logger.info("[NHL] 🧠 Analyse IA du contexte des matchs...")
    ai_factors = get_ai_game_context(future_games, standings)
    if ai_factors:
        logger.info(f"[NHL] 🧠 AI factors: {ai_factors}")
    else:
        logger.info("[NHL] 🧠 AI factors: aucun (fallback = 1.0)")

    # 6. Analyze each game
    today = schedule_date  # Use the NHL schedule date, not UTC
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
        h_fatigue = fatigue_dict.get(home_abbrev, 1.0)
        a_fatigue = fatigue_dict.get(away_abbrev, 1.0)

        if h_fatigue < 1.0:
            tag = "3-in-4" if h_fatigue < 0.90 else "B2B"
            b2b_tag += f" ⚠️{home_abbrev} {tag}"
        if a_fatigue < 1.0:
            tag = "3-in-4" if a_fatigue < 0.90 else "B2B"
            b2b_tag += f" ⚠️{away_abbrev} {tag}"

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

        # Calculate Game Script (Trailing/Leading Volume Adjustments)
        # If Home is massive favorite (h_ai 1.3 vs a_ai 0.8), Away will likely trail and take more shots (1.10). Home will turtle (0.90)
        ai_diff = h_ai - a_ai
        home_script_mult = 1.0
        away_script_mult = 1.0

        if ai_diff > 0.4:
            # Home heavy favorite
            home_script_mult = 0.92
            away_script_mult = 1.08
        elif ai_diff < -0.4:
            # Away heavy favorite
            home_script_mult = 1.08
            away_script_mult = 0.92

        # Score players — PASS 1: base scoring (no game logs)
        match_players = []
        for skater in home_roster:
            if skater.get("gamesPlayed", 0) < 10:
                continue
            player = _score_player(
                skater,
                home_abbrev,
                away_abbrev,
                h_stats,
                a_stats,
                True,
                goalie_form,
                fatigue_dict,
                ai_factors,
                home_script_mult,
                special_teams=special_teams,
            )
            if player["prob_goal"] > 5 or player["prob_shot"] > 15:
                player["_skater"] = skater  # Keep reference for pass 2
                match_players.append(player)

        for skater in away_roster:
            if skater.get("gamesPlayed", 0) < 10:
                continue
            player = _score_player(
                skater,
                away_abbrev,
                home_abbrev,
                a_stats,
                h_stats,
                False,
                goalie_form,
                fatigue_dict,
                ai_factors,
                away_script_mult,
                special_teams=special_teams,
            )
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

            l5 = calculate_recent_form(game_log)
            h2h = calculate_h2h_factor(game_log, opp_abbrev)

            # Re-score with L5 + H2H
            skater = player.pop("_skater", None)
            if skater:
                team = player["team"]
                opp = player["opp"]
                is_home = player["is_home"] == 1
                my_s = standings.get(team, {})
                opp_s = standings.get(opp, {})
                p_script_mult = home_script_mult if is_home else away_script_mult
                enhanced = _score_player(
                    skater,
                    team,
                    opp,
                    my_s,
                    opp_s,
                    is_home,
                    goalie_form,
                    fatigue_dict,
                    ai_factors,
                    p_script_mult,
                    l5_form=l5,
                    h2h=h2h,
                    special_teams=special_teams,
                )
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

        # ─── PASS 3: Injury detection (absent from last 10 days) ───
        injured = set()
        injured_by_team = {home_abbrev: [], away_abbrev: []}
        for p in match_players:
            l5 = p.get("l5_form", {})
            pid = p["player_id"]
            if not pid or pid == "0":
                continue

            # If we fetched game logs, check `days_since_last_game`
            if l5 and "days_since_last_game" in l5:
                if l5["days_since_last_game"] > 10:
                    injured.add(pid)
                    injured_by_team.setdefault(p["team"], []).append(p["player_name"])
                    logger.info(
                        f"[NHL]   🏥 {p['player_name']} enlevé (absent depuis {l5['days_since_last_game']}j)"
                    )
                continue

            # For players without game logs, if they have very few GP overall
            if p.get("games_played", 0) == 0:
                injured.add(pid)

        # Also detect missing players by checking game logs for top scorers
        # who weren't in the L5 pass
        teams_in_match = {home_abbrev, away_abbrev}
        for team in teams_in_match:
            team_players = [p for p in match_players if p["team"] == team]
            team_players.sort(key=lambda p: p["prob_point"], reverse=True)
            for p in team_players[:10]:
                pid = p["player_id"]
                if pid in injured or not pid or pid == "0":
                    continue
                if p.get("l5_form", {}).get("days_since_last_game") is not None:
                    continue  # Already checked

                game_log = fetch_player_game_log(pid)
                if game_log:
                    # Check if last game was more than 10 days ago
                    try:
                        last_game_date = game_log[0].get("gameDate", "")
                        if last_game_date:
                            last_dt = datetime.strptime(last_game_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                            days_since = (datetime.now(timezone.utc) - last_dt).days
                            if days_since > 10:
                                injured.add(pid)
                                injured_by_team.setdefault(team, []).append(p["player_name"])
                                logger.info(
                                    f"[NHL]   🏥 {p['player_name']} ({team}) enlevé (absent depuis {days_since}j)"
                                )
                    except Exception:
                        pass
                else:
                    injured.add(pid)

        # Filter injured players
        if injured:
            before = len(match_players)
            match_players = [p for p in match_players if p["player_id"] not in injured]
            removed = before - len(match_players)
            if removed:
                logger.info(f"[NHL]   🏥 {removed} joueurs absents retirés")

        # ─── PASS 4: Synergy penalty (top passer absent → reduce goal probas) ───
        for team in teams_in_match:
            team_players = [p for p in match_players if p["team"] == team]
            # Find the team's top assist player
            team_players_sorted = sorted(team_players, key=lambda p: p["prob_assist"], reverse=True)
            if not team_players_sorted:
                continue

            top_passer = team_players_sorted[0]
            # Check if any top assist player from this team was injured
            team_injured_passers = [
                p
                for p in all_players  # Check from original pool before filtering
                if p["team"] == team and p["player_id"] in injured
            ]

            # Also check: is the team's best regular passer much lower than expected?
            # We estimate this by checking if the top assist player from src.nhl_data_lake
            # (previous days) is missing from today's roster
            if team_injured_passers:
                # Apply synergy penalty to remaining teammates' goal probabilities
                penalty = 0.88  # -12% goal probability for teammates
                for p in match_players:
                    if p["team"] == team:
                        p["prob_goal"] = round(p["prob_goal"] * penalty, 1)
                        p["prob_point"] = round(p["prob_point"] * (penalty + 0.04), 1)  # -8% point
                        p["algo_score_goal"] = int(p["prob_goal"])

                injured_names = [p["player_name"] for p in team_injured_passers]
                logger.info(
                    f"[NHL]   ⛓️ Synergy penalty {team}: {', '.join(injured_names)} absent → -12% buts coéquipiers"
                )

        all_players.extend(match_players)

        # ─── PASS 5: Recommended Bet (Player-based: Point, Goal, Assist) ───
        rec_bet = "Analyse en cours..."
        conf = 3

        # Calculate team win probabilities for fallback and insertion
        win_prob = calculate_win_prob(home_abbrev, away_abbrev, standings, fatigue_dict)
        ph = win_prob["home"]
        pa = win_prob["away"]
        po55 = win_prob.get("over_55", 50)

        # ─── Injury-adjusted probabilities ───
        home_injured_count = len(injured_by_team.get(home_abbrev, []))
        away_injured_count = len(injured_by_team.get(away_abbrev, []))
        if home_injured_count > 0 or away_injured_count > 0:
            # Each injured star reduces team win% by ~3pts (capped at 15pts)
            home_penalty = min(15, home_injured_count * 3)
            away_penalty = min(15, away_injured_count * 3)
            # Transfer from injured team to opponent
            ph = max(15, ph - home_penalty + away_penalty)
            pa = max(15, pa - away_penalty + home_penalty)
            # Normalize to 100%
            total = ph + pa
            ph = round(ph * 100 / total)
            pa = 100 - ph
            # Reduce Over 5.5 if key players are out
            total_injuries = home_injured_count + away_injured_count
            po55 = max(20, po55 - total_injuries * 2)
            logger.info(
                f"[NHL]   🏥 Injury-adjusted: {home_abbrev}={ph}% ({home_injured_count} out), "
                f"{away_abbrev}={pa}% ({away_injured_count} out), O5.5={po55}%"
            )

        # ─── ML Blend (60% Poisson + 40% XGBoost) ───
        try:
            if nhl_ml_available():
                ml_features = {
                    "proba_home": ph,
                    "proba_away": pa,
                    "proba_over_55": po55,
                    "ai_home_factor": h_ai,
                    "ai_away_factor": a_ai,
                }
                ml_preds = predict_nhl_match_ml(ml_features)
                if ml_preds.get("ml_home_win") is not None:
                    ml_home = ml_preds["ml_home_win"]
                    ml_away = 100 - ml_home
                    ph = round(0.6 * ph + 0.4 * ml_home)
                    pa = round(0.6 * pa + 0.4 * ml_away)
                    logger.info(f"[NHL]   🧠 ML blend: home={ph}% away={pa}% (ML raw: {ml_home}%)")
                if ml_preds.get("ml_over_55") is not None:
                    po55 = round(0.6 * po55 + 0.4 * ml_preds["ml_over_55"])
        except Exception:
            logger.warning("[NHL] ML blend skipped", exc_info=True)

        # Sort match players to find the best bet
        # Priorities: Point > 50%, Goal > 30%, Assist > 35%
        best_p_points = sorted(match_players, key=lambda p: p["prob_point"], reverse=True)
        best_p_goals = sorted(match_players, key=lambda p: p["prob_goal"], reverse=True)
        best_p_assists = sorted(match_players, key=lambda p: p["prob_assist"], reverse=True)

        if best_p_goals and best_p_goals[0].get("prob_goal", 0) > 35:
            p = best_p_goals[0]
            rec_bet = f"{p['player_name']} ({p['team']}) : Buteur"
            # Scale probability strictly out of 10. (e.g., 65% -> 6.5 -> 7/10)
            conf = min(10, max(1, round(p["prob_goal"] / 10)))
        elif best_p_points and best_p_points[0].get("prob_point", 0) > 55:
            p = best_p_points[0]
            rec_bet = f"{p['player_name']} ({p['team']}) : +0.5 Point"
            conf = min(10, max(1, round(p["prob_point"] / 10)))
        elif best_p_assists and best_p_assists[0].get("prob_assist", 0) > 40:
            p = best_p_assists[0]
            rec_bet = f"{p['player_name']} ({p['team']}) : Passeur décisif"
            conf = min(10, max(1, round(p["prob_assist"] / 10)))
        else:
            # Fallback to team win if no strong player bet
            if ph >= pa:
                rec_bet = f"Victoire {home_name} (incl. OT)"
                conf = min(10, max(1, round(ph / 10)))
            else:
                rec_bet = f"Victoire {away_name} (incl. OT)"
                conf = min(10, max(1, round(pa / 10)))

        # ─── PASS 6: AI Detailed Analysis ───
        logger.info(
            f"[NHL]   🧠 Génération analyse détaillée pour {home_abbrev} vs {away_abbrev}..."
        )
        # Build injury context for Gemini
        injury_context = {}
        for team_abbr in [home_abbrev, away_abbrev]:
            names = injured_by_team.get(team_abbr, [])
            if names:
                team_full = TEAM_NAMES.get(team_abbr, team_abbr)
                injury_context[team_full] = names
        analysis_text = get_gemini_nhl_analysis(
            home_name, away_name, match_players, ai_factors, injured_info=injury_context
        )

        # Win probabilities for fixtures_data (saved to Supabase)


        fixtures_data.append(
            {
                "api_fixture_id": game_id,
                "date": start_time,  # startTimeUTC — frontend handles timezone display
                "status": "NS",
                "home_team": home_name,
                "away_team": away_name,
                "proba_home": ph,
                "proba_away": pa,
                "proba_over_55": po55,
                "ai_home_factor": h_ai,
                "ai_away_factor": a_ai,
                "recommended_bet": rec_bet,
                "confidence_score": conf,
                "analysis_text": analysis_text,
                "stats_json": {"top_players": match_players},
            }
        )

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
                supabase.table("nhl_data_lake").insert(rows[i : i + 500]).execute()
            except Exception:
                logger.exception("[NHL] Error inserting data_lake batch")

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
                "proba_over_55": f.get("proba_over_55", 50),
                "ai_home_factor": f.get("ai_home_factor", 1.0),
                "ai_away_factor": f.get("ai_away_factor", 1.0),
            }
            if existing:
                supabase.table("nhl_fixtures").update(
                    {
                        "date": f["date"],
                        "status": f["status"],
                        "home_team": f["home_team"],
                        "away_team": f["away_team"],
                        "model_version": "v1",
                        "predictions_json": predictions,
                        "proba_home": f["proba_home"],
                        "proba_away": f["proba_away"],
                        "proba_over_55": f.get("proba_over_55", 50),
                        "ai_home_factor": f.get("ai_home_factor", 1.0),
                        "ai_away_factor": f.get("ai_away_factor", 1.0),
                        "stats_json": f.get("stats_json", {}),
                        "recommended_bet": f["recommended_bet"],
                        "confidence_score": f["confidence_score"],
                        "analysis_text": f["analysis_text"],
                    }
                ).eq("api_fixture_id", f["api_fixture_id"]).execute()
            else:
                supabase.table("nhl_fixtures").insert(
                    {
                        "api_fixture_id": f["api_fixture_id"],
                        "date": f["date"],
                        "status": f["status"],
                        "home_team": f["home_team"],
                        "away_team": f["away_team"],
                        "model_version": "v1",
                        "predictions_json": predictions,
                        "proba_home": f["proba_home"],
                        "proba_away": f["proba_away"],
                        "proba_over_55": f.get("proba_over_55", 50),
                        "ai_home_factor": f.get("ai_home_factor", 1.0),
                        "ai_away_factor": f.get("ai_away_factor", 1.0),
                        "stats_json": f.get("stats_json", {}),
                        "recommended_bet": f["recommended_bet"],
                        "confidence_score": f["confidence_score"],
                        "analysis_text": f["analysis_text"],
                    }
                ).execute()
        except Exception:
            logger.exception("[NHL] Error upserting fixture %s vs %s", f.get("home_team"), f.get("away_team"))

    logger.info(f"[NHL] ✅ {len(fixtures_data)} matchs insérés dans nhl_fixtures")

    # 9. 🧠 DeepThink Strategic Meta-Analysis (ONE call per pipeline run)
    #    Cover next 24h: today's fixtures + tomorrow until 20:00 UTC (21:00 Paris)
    if fixtures_data and all_players:
        # Fetch tomorrow's already-stored fixtures from DB to include in DeepThink
        extended_fixtures = list(fixtures_data)
        try:
            from datetime import datetime as dt, timezone
            from datetime import timedelta
            tomorrow = (dt.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
            cutoff_str = (dt.now(timezone.utc) + timedelta(days=1)).replace(hour=20, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
            tmrw_data = (
                supabase.table("nhl_fixtures")
                .select("*")
                .eq("status", "NS")
                .gte("date", f"{tomorrow}T00:00:00Z")
                .lt("date", cutoff_str)
                .execute()
                .data or []
            )
            if tmrw_data:
                for tf in tmrw_data:
                    # Only add if not already in today's fixtures
                    existing_ids = {f.get("api_fixture_id") for f in extended_fixtures}
                    if tf.get("api_fixture_id") not in existing_ids:
                        extended_fixtures.append({
                            "home_team": tf["home_team"],
                            "away_team": tf["away_team"],
                            "date": tf["date"],
                            "status": tf["status"],
                            "proba_home": tf.get("proba_home", 50),
                            "proba_away": tf.get("proba_away", 50),
                            "proba_over_55": tf.get("proba_over_55", 50),
                            "ai_home_factor": tf.get("ai_home_factor", 1.0),
                            "ai_away_factor": tf.get("ai_away_factor", 1.0),
                            "recommended_bet": tf.get("recommended_bet", ""),
                            "confidence_score": tf.get("confidence_score", 5),
                            "api_fixture_id": tf.get("api_fixture_id"),
                            "stats_json": tf.get("stats_json", {}),
                        })
                logger.info(f"[NHL] DeepThink: added {len(tmrw_data)} tomorrow fixtures (total: {len(extended_fixtures)})")
        except Exception:
            logger.warning("[NHL] Could not fetch tomorrow's fixtures for DeepThink", exc_info=True)

        try:
            meta_analysis = generate_deepthink_meta_analysis(
                extended_fixtures, all_players, standings, fatigue_dict, special_teams
            )
            if meta_analysis:
                # Store as special row in nhl_data_lake
                try:
                    supabase.table("nhl_data_lake").delete().eq(
                        "player_id", "META_ANALYSIS"
                    ).eq("date", today).execute()
                except Exception:
                    pass
                try:
                    # Try with dedicated meta_analysis column first
                    supabase.table("nhl_data_lake").insert(
                        {
                            "date": today,
                            "player_id": "META_ANALYSIS",
                            "player_name": "DeepThink Analysis",
                            "team": "NHL",
                            "opp": "ALL",
                            "algo_score_goal": 0,
                            "algo_score_shot": 0,
                            "is_home": 0,
                            "python_prob": 0,
                            "python_vol": 0,
                            "meta_analysis": meta_analysis,
                        }
                    ).execute()
                    logger.info("[NHL] ✅ DeepThink meta-analysis saved")
                except Exception:
                    # Fallback: store in player_name field if meta_analysis column doesn't exist
                    logger.warning("[NHL] meta_analysis column insert failed, trying fallback...", exc_info=True)
                    try:
                        supabase.table("nhl_data_lake").insert(
                            {
                                "date": today,
                                "player_id": "META_ANALYSIS",
                                "player_name": meta_analysis,
                                "team": "NHL",
                                "opp": "ALL",
                                "algo_score_goal": 0,
                                "algo_score_shot": 0,
                                "is_home": 0,
                                "python_prob": 0,
                                "python_vol": 0,
                            }
                        ).execute()
                        logger.info("[NHL] ✅ DeepThink meta-analysis saved (fallback)")
                    except Exception:
                        logger.exception("[NHL] Error saving meta-analysis")
        except Exception:
            logger.warning("[NHL] DeepThink meta-analysis failed", exc_info=True)

    return {
        "status": "ok",
        "matches": len(fixtures_data),
        "players_analyzed": len(all_players),
        "tired_teams": list(fatigue_dict.keys()),
        "ai_factors": ai_factors,
        "fixtures": [
            {
                "match": f"{f['home_team']} vs {f['away_team']}",
                "home_pct": f["proba_home"],
                "away_pct": f["proba_away"],
                "ai": "🔥"
                if f.get("ai_home_factor", 1) > 1.15 or f.get("ai_away_factor", 1) > 1.15
                else "",
            }
            for f in fixtures_data
        ],
    }


def generate_deepthink_meta_analysis(
    fixtures_data: list[dict],
    all_players: list[dict],
    standings: dict,
    fatigue_dict: dict,
    special_teams: dict,
) -> str | None:
    """Generate a strategic meta-analysis of the entire NHL evening using DeepThink.

    Uses Gemini with extended thinking for deep reasoning across all matches.
    Returns a markdown-formatted analysis string, or None on failure.
    """
    try:
        from google import genai
        from google.genai import types

        from src.config import GEMINI_API_KEY

        if not GEMINI_API_KEY:
            return None

        gclient = genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        logger.warning("[NHL] google-genai not available for DeepThink")
        return None

    # Build comprehensive data summary for DeepThink
    matches_summary = []
    for f in fixtures_data:
        home = f["home_team"]
        away = f["away_team"]
        h_abbrev = next((k for k, v in TEAM_NAMES.items() if v == home), "")
        a_abbrev = next((k for k, v in TEAM_NAMES.items() if v == away), "")

        # Get special teams data
        h_st = special_teams.get(h_abbrev, {})
        a_st = special_teams.get(a_abbrev, {})
        h_stand = standings.get(h_abbrev, {})
        a_stand = standings.get(a_abbrev, {})

        h_fatigue = fatigue_dict.get(h_abbrev, 1.0)
        a_fatigue = fatigue_dict.get(a_abbrev, 1.0)

        # Top players for this match
        match_top = [
            p for p in all_players
            if p["team"] in (h_abbrev, a_abbrev)
        ]
        match_top.sort(key=lambda p: p.get("prob_point", 0), reverse=True)
        top5 = match_top[:5]

        players_str = "\n".join([
            f"    - {p['player_name']} ({p['team']}): "
            f"Point {p.get('prob_point', 0):.0f}%, But {p.get('prob_goal', 0):.0f}%, "
            f"Tirs {p.get('shots_per_game', 0):.1f}/m, "
            f"PP boost {p.get('pp_boost', 1.0):.2f}, "
            f"PP share {p.get('pp_share', 0):.1%}, "
            f"{'🔥 HOT' if p.get('l5_form', {}).get('hot') else '🥶 COLD' if p.get('l5_form', {}).get('cold') else ''}"
            for p in top5
        ])

        fatigue_tag = ""
        if h_fatigue < 1.0:
            fatigue_tag += f" ⚠️ {h_abbrev} B2B ({h_fatigue:.2f})"
        if a_fatigue < 1.0:
            fatigue_tag += f" ⚠️ {a_abbrev} B2B ({a_fatigue:.2f})"

        matches_summary.append(
            f"### {home} vs {away}\n"
            f"  Win%: {home} {f.get('proba_home', 50)}% — {away} {f.get('proba_away', 50)}%\n"
            f"  Over 5.5: {f.get('proba_over_55', 50)}%\n"
            f"  {home}: PP {h_st.get('pp_pct', 0.20):.1%}, L10 GAA {h_stand.get('l10_gaa', 0)}\n"
            f"  {away}: PK {a_st.get('pk_pct', 0.80):.1%}, TSH/gm {a_st.get('tsh_per_game', 3.0):.1f}, "
            f"SA/gm {a_st.get('shots_against_per_game', 30):.1f}\n"
            f"  {away}: PP {a_st.get('pp_pct', 0.20):.1%}, L10 GAA {a_stand.get('l10_gaa', 0)}\n"
            f"  {home}: PK {h_st.get('pk_pct', 0.80):.1%}, TSH/gm {h_st.get('tsh_per_game', 3.0):.1f}, "
            f"SA/gm {h_st.get('shots_against_per_game', 30):.1f}\n"
            f"  Fatigue:{fatigue_tag or ' Aucune'}\n"
            f"  AI factors: {home} {f.get('ai_home_factor', 1.0)}, {away} {f.get('ai_away_factor', 1.0)}\n"
            f"  Top joueurs:\n{players_str}"
        )

    system_prompt = (
        "Tu es un expert analytique NHL de niveau élite. Tu t'adresses à des parieurs avertis.\n\n"
        "**MISSION** : Analyse en profondeur TOUS les matchs de la soirée. "
        "Identifie les 3 MEILLEURS SPOTS (opportunités à haute value) en croisant les données.\n\n"
        "**Données fournies** : Probabilités calculées par le modèle Poisson, "
        "PP%/PK% des équipes, fatigue B2B, PK L10 estimé, pénalités concédées adverses, "
        "Tirs concédés, forme récente (L5), PP share des joueurs.\n\n"
        "**MARCHÉS AUTORISÉS (uniquement ceux calculés par notre modèle)** :\n"
        "- Joueur But O/U 0.5 (Buteur)\n"
        "- Joueur Point O/U 0.5 (+0.5 Point)\n"
        "- Joueur Assist O/U 0.5 (Passeur décisif)\n"
        "- Victoire équipe (incl. OT)\n"
        "- Over/Under 5.5 buts\n"
        "⚠️ NE JAMAIS recommander de handicap, de tirs O/U, ou de marché non listé ci-dessus.\n\n"
        "**RAISONNEMENT ATTENDU** : Pour chaque spot identifié, tu dois :\n"
        "1. Expliquer POURQUOI c'est un bon spot (croisement de plusieurs facteurs)\n"
        "2. Identifier le MARCHÉ cible (parmi la liste ci-dessus uniquement)\n"
        "3. Donner un niveau de CONFIANCE (⭐ à ⭐⭐⭐)\n"
        "4. Mentionner les RISQUES potentiels\n\n"
        "**FORMAT** : Rédige en français, style direct de parieur expert. "
        "Commence par un titre '🧠 Analyse Stratégique' puis les 3 spots. "
        "Termine par un bref résumé de la soirée (1-2 phrases).\n"
        "Max 500 mots total. Sois percutant et précis.\n"
        "⚠️ Ne dis JAMAIS 'mon modèle', 'mon analyse', 'je'. Utilise 'notre analyse', 'nos experts', 'le modèle'."
    )

    user_prompt = (
        f"Soirée NHL du {datetime.now(timezone.utc).strftime('%d/%m/%Y')} — "
        f"{len(fixtures_data)} matchs à analyser :\n\n"
        + "\n\n".join(matches_summary)
    )

    try:
        logger.info("[NHL] 🧠 DeepThink: Generating strategic meta-analysis...")
        response = gclient.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )
        # Robuste: extraire le texte de la réponse
        result = ""
        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    result += part.text
        if not result:
            result = getattr(response, "text", "") or ""

        if result and len(result) > 50:
            logger.info(f"[NHL] 🧠 DeepThink analysis generated ({len(result)} chars)")
            return result
        else:
            logger.warning("[NHL] DeepThink returned empty/short response")
            return None
    except Exception:
        logger.warning("[NHL] DeepThink generation failed", exc_info=True)
        return None

