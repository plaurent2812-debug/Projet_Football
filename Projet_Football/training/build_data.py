from __future__ import annotations

"""
build_training_data.py — Construit le dataset d'entraînement ML.

VERSION OPTIMISÉE : pré-charge toutes les données en mémoire
pour éviter ~20 requêtes Supabase par match.

Pour chaque match terminé dans Supabase, calcule un vecteur de features
qui représente l'état des connaissances AVANT le match, et les targets
(résultats réels).
"""
from collections import defaultdict
from datetime import datetime, timedelta

from config import SEASON, logger, supabase

# ─────────────────────────────────────────────────────────────
#  CHARGEMENT GLOBAL EN MÉMOIRE (exécuté une seule fois)
# ─────────────────────────────────────────────────────────────


def _fetch_all(table: str, select: str = "*", **filters: str | int) -> list[dict]:
    """Fetch all rows from a Supabase table, paginating if needed.

    Args:
        table: Name of the Supabase table.
        select: Column selection expression (default ``"*"``).
        **filters: Equality filters applied via ``.eq()``.

    Returns:
        A list of row dicts (may be empty).
    """
    q = supabase.table(table).select(select, count="exact")
    for k, v in filters.items():
        q = q.eq(k, v)
    resp = q.limit(10000).execute()
    data: list[dict] = resp.data or []
    # Si > 10000 lignes, paginer
    total: int = resp.count or len(data)
    offset: int = len(data)
    while offset < total:
        q2 = supabase.table(table).select(select)
        for k, v in filters.items():
            q2 = q2.eq(k, v)
        page = q2.range(offset, offset + 9999).execute().data or []
        data.extend(page)
        offset += len(page)
        if not page:
            break
    return data


def load_all_data() -> dict:
    """Load every table required for feature building into memory.

    Returns:
        A dict whose keys are lookup structures (e.g. ``"elo_map"``,
        ``"fixtures_by_team"``, ``"standings_by_league"``, …).
    """
    logger.info("  📦 Chargement des données en mémoire...")

    data: dict = {}

    # Teams
    teams_raw = _fetch_all("teams", "api_id, name")
    data["name_to_id"] = {t["name"]: t["api_id"] for t in teams_raw}
    data["id_to_name"] = {t["api_id"]: t["name"] for t in teams_raw}
    logger.info(f"    ✓ {len(teams_raw)} équipes")

    # ELO
    elos_raw = _fetch_all("team_elo", "team_api_id, elo_rating")
    data["elo_map"] = {e["team_api_id"]: e["elo_rating"] for e in elos_raw}
    logger.info(f"    ✓ {len(elos_raw)} ratings ELO")

    # Standings (force d'équipe)
    standings_raw = _fetch_all("team_standings", "*")
    data["standings_by_league"] = defaultdict(list)
    for s in standings_raw:
        key = (s["league_id"], s.get("season", SEASON))
        data["standings_by_league"][key].append(s)
    logger.info(f"    ✓ {len(standings_raw)} classements")

    # Fixtures terminées (pour forme, repos)
    fixtures_raw = _fetch_all(
        "fixtures",
        "api_fixture_id, home_team, away_team, home_goals, away_goals, date, status, league_id, referee_name, stats_json",
    )
    data["all_fixtures"] = fixtures_raw
    # Index par date pour lookup rapide
    data["fixtures_by_team"] = defaultdict(list)
    for f in fixtures_raw:
        if f["status"] == "FT" and f.get("home_goals") is not None:
            data["fixtures_by_team"][f["home_team"]].append(f)
            data["fixtures_by_team"][f["away_team"]].append(f)
    # Trier par date pour chaque équipe
    for team in data["fixtures_by_team"]:
        data["fixtures_by_team"][team].sort(key=lambda x: x["date"])
    logger.info(f"    ✓ {len(fixtures_raw)} fixtures")

    # H2H cache
    h2h_raw = _fetch_all("h2h_cache", "*")
    data["h2h_map"] = {}
    for h in h2h_raw:
        pair = (h["team_a_api_id"], h["team_b_api_id"])
        data["h2h_map"][pair] = h
    logger.info(f"    ✓ {len(h2h_raw)} confrontations H2H")

    # Referees
    refs_raw = _fetch_all("referees", "*")
    data["referee_map"] = {r["name"]: r for r in refs_raw}
    logger.info(f"    ✓ {len(refs_raw)} arbitres")

    # Odds
    odds_raw = _fetch_all("fixture_odds", "fixture_api_id, home_win_odds, draw_odds, away_win_odds")
    data["odds_map"] = {o["fixture_api_id"]: o for o in odds_raw}
    logger.info(f"    ✓ {len(odds_raw)} cotes")

    # Injuries (actuelles)
    inj_raw = _fetch_all("injuries", "team_api_id, player_api_id, player_name, reason, type")
    data["injuries_by_team"] = defaultdict(list)
    for inj in inj_raw:
        data["injuries_by_team"][inj["team_api_id"]].append(inj)
    logger.info(f"    ✓ {len(inj_raw)} blessures")

    # Players + stats
    players_raw = _fetch_all("players", "api_id, name, position, team_api_id, is_injured")
    data["player_map"] = {p["api_id"]: p for p in players_raw}
    data["injured_flag_by_team"] = defaultdict(list)
    for p in players_raw:
        if p.get("is_injured"):
            data["injured_flag_by_team"][p["team_api_id"]].append(p)
    logger.info(f"    ✓ {len(players_raw)} joueurs")

    pstats_raw = _fetch_all(
        "player_season_stats",
        "player_api_id, team_api_id, season, rating, goals, assists, minutes_played, "
        "goals_conceded, saves, clean_sheets, shots_on_target, passes_key, "
        "penalty_scored, penalty_missed",
    )
    data["pstats_by_player"] = defaultdict(list)
    data["pstats_by_team"] = defaultdict(list)
    for ps in pstats_raw:
        data["pstats_by_player"][ps["player_api_id"]].append(ps)
        data["pstats_by_team"][(ps["team_api_id"], ps.get("season", SEASON))].append(ps)
    logger.info(f"    ✓ {len(pstats_raw)} stats joueurs")

    logger.info("  ✅ Toutes les données chargées !")
    return data


# ─────────────────────────────────────────────────────────────
#  CALCULS DE FEATURES (100% en mémoire, zéro requête)
# ─────────────────────────────────────────────────────────────


def _team_strengths_from_mem(data: dict, league_id: int, season: int = SEASON) -> dict | None:
    """Compute attack/defence strength ratings for every team in a league.

    Uses home/away goals for/against from standings to derive Poisson-style
    strength indices relative to the league average.

    Args:
        data: The global in-memory data store.
        league_id: API league identifier.
        season: Season year (defaults to the current ``SEASON``).

    Returns:
        A dict with ``"strengths"`` (per-team) and league averages, or
        ``None`` when standings are unavailable or too sparse.
    """
    standings = data["standings_by_league"].get((league_id, season), [])
    if not standings or len(standings) < 4:
        return None

    total_home_for = sum(s["home_goals_for"] for s in standings)
    total_home_against = sum(s["home_goals_against"] for s in standings)
    total_away_for = sum(s["away_goals_for"] for s in standings)
    total_away_against = sum(s["away_goals_against"] for s in standings)
    total_home_played = max(sum(s["home_played"] for s in standings), 1)
    total_away_played = max(sum(s["away_played"] for s in standings), 1)

    league_avg_home: float = total_home_for / total_home_played
    league_avg_away: float = total_away_for / total_away_played
    league_avg_home_conc: float = total_home_against / total_home_played
    league_avg_away_conc: float = total_away_against / total_away_played

    strengths: dict[int, dict[str, float]] = {}
    for s in standings:
        tid = s["team_api_id"]
        hp = max(s["home_played"], 1)
        ap = max(s["away_played"], 1)
        strengths[tid] = {
            "home_attack": (s["home_goals_for"] / hp) / max(league_avg_home, 0.5),
            "home_defense": (s["home_goals_against"] / hp) / max(league_avg_home_conc, 0.5),
            "away_attack": (s["away_goals_for"] / ap) / max(league_avg_away, 0.5),
            "away_defense": (s["away_goals_against"] / ap) / max(league_avg_away_conc, 0.5),
        }

    return {
        "strengths": strengths,
        "league_avg_home": league_avg_home,
        "league_avg_away": league_avg_away,
    }


def _form_from_mem(
    data: dict,
    team_name: str,
    match_date: str,
    home_only: bool | None = None,
    n: int = 6,
    decay: float = 0.82,
) -> float:
    """Compute recent form for a team before a given match date.

    Uses an exponential-decay weighting over the last *n* fixtures.

    Args:
        data: The global in-memory data store.
        team_name: Full team name as stored in fixtures.
        match_date: ISO-formatted date string of the upcoming match.
        home_only: If ``True`` keep only home games; if ``False`` only
            away games; if ``None`` keep all.
        n: Maximum number of recent matches to consider.
        decay: Decay factor per match (0 < decay < 1).

    Returns:
        A float between 0.0 and 1.0 representing recent form (0.5 as
        the neutral default when no history is available).
    """
    team_fixtures = data["fixtures_by_team"].get(team_name, [])
    # Filtrer les matchs AVANT cette date
    recent = [f for f in team_fixtures if f["date"] < match_date]

    if home_only is True:
        recent = [f for f in recent if f["home_team"] == team_name]
    elif home_only is False:
        recent = [f for f in recent if f["away_team"] == team_name]

    # Prendre les n plus récents
    recent = recent[-n:] if len(recent) > n else recent
    recent.reverse()  # Plus récent en premier

    if not recent:
        return 0.5

    form_score: float = 0
    total_weight: float = 0
    for i, r in enumerate(recent):
        weight = decay**i
        is_home = r["home_team"] == team_name
        gf = r["home_goals"] if is_home else r["away_goals"]
        ga = r["away_goals"] if is_home else r["home_goals"]
        if gf is None or ga is None:
            continue
        if gf > ga:
            form_score += 3 * weight
        elif gf == ga:
            form_score += 1 * weight
        total_weight += 3 * weight

    return form_score / total_weight if total_weight > 0 else 0.5


def _rest_from_mem(data: dict, team_name: str, match_date: str) -> tuple[int, int]:
    """Compute rest days and 30-day fixture congestion before a match.

    Args:
        data: The global in-memory data store.
        team_name: Full team name.
        match_date: ISO-formatted date of the upcoming match.

    Returns:
        A tuple ``(rest_days, congestion_30d)``.
    """
    team_fixtures = data["fixtures_by_team"].get(team_name, [])
    # Matchs AVANT cette date
    before = [f for f in team_fixtures if f["date"] < match_date]

    rest_days: int = 7
    if before:
        try:
            match_dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
            last_dt = datetime.fromisoformat(before[-1]["date"].replace("Z", "+00:00"))
            rest_days = max(1, (match_dt - last_dt).days)
        except Exception:
            rest_days = 7  # Fallback: assume standard rest

    # Congestion 30 jours
    congestion: int
    try:
        match_dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
        thirty_days_ago = match_dt - timedelta(days=30)
        congestion = sum(
            1
            for f in before
            if datetime.fromisoformat(f["date"].replace("Z", "+00:00")) >= thirty_days_ago
        )
    except Exception:
        congestion = 4  # Fallback: assume average congestion

    return rest_days, congestion


def _stakes_from_mem(data: dict, team_api_id: int, league_id: int, season: int = SEASON) -> float:
    """Compute a motivation/stakes multiplier for a team.

    Based on league standings proximity to the title, Champions League
    spots, or relegation zone.

    Args:
        data: The global in-memory data store.
        team_api_id: API identifier of the team.
        league_id: API league identifier.
        season: Season year.

    Returns:
        A float multiplier (1.0 = normal, >1.0 = high stakes,
        <1.0 = low stakes).
    """
    standings = data["standings_by_league"].get((league_id, season), [])
    if not standings:
        return 1.0

    standings_sorted = sorted(standings, key=lambda s: s.get("rank", 99))
    team_standing: dict | None = None
    for s in standings_sorted:
        if s["team_api_id"] == team_api_id:
            team_standing = s
            break

    if not team_standing:
        return 1.0

    rank: int = team_standing["rank"]
    total_teams: int = len(standings_sorted)
    points: int = team_standing["points"]
    leader_pts: int = standings_sorted[0]["points"]
    relegation_rank: int = max(total_teams - 3, 1)
    relegation_pts: int = standings_sorted[min(relegation_rank, len(standings_sorted) - 1)][
        "points"
    ]

    pts_from_top: int = leader_pts - points
    pts_from_cl: int = (
        (standings_sorted[min(3, len(standings_sorted) - 1)]["points"] - points)
        if len(standings_sorted) > 3
        else 0
    )
    pts_from_relegation: int = points - relegation_pts

    if pts_from_top <= 3:
        return 1.08
    elif pts_from_cl <= 3 and rank <= 6:
        return 1.05
    elif pts_from_relegation <= 3 and rank >= total_teams - 5:
        return 1.06
    elif rank > total_teams // 3 and rank < 2 * total_teams // 3:
        return 0.97
    else:
        return 1.0


def _h2h_from_mem(data: dict, home_id: int, away_id: int) -> tuple[float, int]:
    """Retrieve head-to-head win rate from the in-memory cache.

    Args:
        data: The global in-memory data store.
        home_id: API team id of the home side.
        away_id: API team id of the away side.

    Returns:
        A tuple ``(home_win_rate, total_matches)``.
    """
    pair = tuple(sorted([home_id, away_id]))
    h = data["h2h_map"].get(pair)
    if not h:
        return 0.33, 0

    total: int = max(h["total_matches"], 1)
    if h["team_a_api_id"] == home_id:
        home_wr = h["team_a_wins"] / total
    else:
        home_wr = h["team_b_wins"] / total

    return round(home_wr, 3), total


def _referee_from_mem(data: dict, referee_name: str | None) -> float:
    """Retrieve referee penalty-bias factor from the in-memory cache.

    Args:
        data: The global in-memory data store.
        referee_name: Name of the referee (may be ``None``).

    Returns:
        A float multiplier (1.0 = neutral).
    """
    if not referee_name:
        return 1.0
    r = data["referee_map"].get(referee_name)
    if not r or not r.get("avg_penalties_per_match"):
        return 1.0
    return round(r["avg_penalties_per_match"] / 0.3, 2)


def _odds_from_mem(data: dict, fixture_api_id: int | None) -> dict | None:
    """Convert bookmaker odds into normalised probabilities.

    Args:
        data: The global in-memory data store.
        fixture_api_id: API fixture identifier.

    Returns:
        A dict with ``"market_home"``, ``"market_draw"``,
        ``"market_away"`` expressed as rounded percentages, or
        ``None`` when odds are unavailable.
    """
    o = data["odds_map"].get(fixture_api_id)
    if not o or not o.get("home_win_odds"):
        return None
    raw_h: float = 1 / o["home_win_odds"]
    raw_d: float = 1 / o["draw_odds"] if o.get("draw_odds") else 0.25
    raw_a: float = 1 / o["away_win_odds"]
    overround: float = raw_h + raw_d + raw_a
    return {
        "market_home": round(raw_h / overround * 100),
        "market_draw": round(raw_d / overround * 100),
        "market_away": round(raw_a / overround * 100),
    }


def _injury_count_from_mem(data: dict, team_api_id: int) -> int:
    """Count distinct injured players for a team.

    Merges the ``injuries`` table entries with the ``is_injured`` flag
    on the ``players`` table to avoid double-counting.

    Args:
        data: The global in-memory data store.
        team_api_id: API team identifier.

    Returns:
        The number of distinct injured player IDs.
    """
    inj = data["injuries_by_team"].get(team_api_id, [])
    flagged = data["injured_flag_by_team"].get(team_api_id, [])
    # Dédupliquer
    ids: set[int] = set()
    for i in inj:
        if i.get("player_api_id"):
            ids.add(i["player_api_id"])
    for p in flagged:
        if p.get("api_id"):
            ids.add(p["api_id"])
    return len(ids)


def _advanced_features_from_mem(
    data: dict, home_team: str, away_team: str, match_date: str
) -> dict:
    """Compute advanced features: momentum, fatigue, variance, clean sheets.

    Args:
        data: The global in-memory data store.
        home_team: Home team name.
        away_team: Away team name.
        match_date: ISO-formatted match date.

    Returns:
        Dictionary of advanced feature values.
    """
    result: dict = {}

    for prefix, team in [("home", home_team), ("away", away_team)]:
        team_fixtures = data["fixtures_by_team"].get(team, [])
        recent = [f for f in team_fixtures if f["date"] < match_date]
        recent_10 = recent[-10:] if len(recent) > 10 else recent
        recent_10.reverse()  # Plus récent en premier

        # Extraire les résultats (points: W=3, D=1, L=0)
        points: list[float] = []
        goal_diffs: list[float] = []
        clean_sheets = 0
        total_matches = 0

        for r in recent_10:
            is_home = r["home_team"] == team
            gf = r["home_goals"] if is_home else r["away_goals"]
            ga = r["away_goals"] if is_home else r["home_goals"]
            if gf is None or ga is None:
                continue
            total_matches += 1
            goal_diffs.append(gf - ga)
            if ga == 0:
                clean_sheets += 1
            if gf > ga:
                points.append(3.0)
            elif gf == ga:
                points.append(1.0)
            else:
                points.append(0.0)

        # Momentum : forme 3 derniers - forme 6 derniers
        if len(points) >= 6:
            form_3 = sum(points[:3]) / 9  # Normalise sur 0-1
            form_6 = sum(points[:6]) / 18
            result[f"{prefix}_momentum"] = round(form_3 - form_6, 3)
        else:
            result[f"{prefix}_momentum"] = 0.0

        # Fatigue index (matchs joues dans les 14 derniers jours)
        try:
            from datetime import datetime

            d = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
            recent_14d = [
                f
                for f in recent
                if (d - datetime.fromisoformat(f["date"].replace("Z", "+00:00"))).days <= 14
            ]
            result[f"{prefix}_fatigue_index"] = len(recent_14d)
        except Exception:
            result[f"{prefix}_fatigue_index"] = 0

        # Goal difference average
        if goal_diffs:
            result[f"{prefix}_goal_diff_avg"] = round(sum(goal_diffs) / len(goal_diffs), 3)
        else:
            result[f"{prefix}_goal_diff_avg"] = 0.0

        # Result variance (unpredictability)
        if len(points) >= 3:
            mean_pts = sum(points) / len(points)
            variance = sum((p - mean_pts) ** 2 for p in points) / len(points)
            result[f"{prefix}_result_variance"] = round(variance, 3)
        else:
            result[f"{prefix}_result_variance"] = 0.0

        # Clean sheet rate
        if total_matches > 0:
            result[f"{prefix}_clean_sheet_rate"] = round(clean_sheets / total_matches, 3)
        else:
            result[f"{prefix}_clean_sheet_rate"] = 0.0

        # ── NEW Phase A2 features ────────────────────────────────

        # Points per game (last 5) — key form indicator
        recent_5 = points[:5] if len(points) >= 5 else points
        if recent_5:
            result[f"{prefix}_ppg_last5"] = round(sum(recent_5) / len(recent_5), 3)
        else:
            result[f"{prefix}_ppg_last5"] = 1.0  # neutral

        # BTTS rate (last 10)
        btts_count = 0
        btts_total = 0
        for r in recent_10:
            is_home = r["home_team"] == team
            gf = r["home_goals"] if is_home else r["away_goals"]
            ga = r["away_goals"] if is_home else r["home_goals"]
            if gf is not None and ga is not None:
                btts_total += 1
                if gf > 0 and ga > 0:
                    btts_count += 1
        if btts_total > 0:
            result[f"{prefix}_btts_rate_last10"] = round(btts_count / btts_total, 3)
        else:
            result[f"{prefix}_btts_rate_last10"] = 0.5

        # Over 2.5 rate (last 10)
        o25_count = 0
        o25_total = 0
        for r in recent_10:
            is_home = r["home_team"] == team
            gf = r["home_goals"] if is_home else r["away_goals"]
            ga = r["away_goals"] if is_home else r["home_goals"]
            if gf is not None and ga is not None:
                o25_total += 1
                if gf + ga > 2:
                    o25_count += 1
        if o25_total > 0:
            result[f"{prefix}_over25_rate_last10"] = round(o25_count / o25_total, 3)
        else:
            result[f"{prefix}_over25_rate_last10"] = 0.5

        # xG per shot efficiency (shots on target from stats_json)
        shots_total = 0
        goals_total = 0
        for r in recent_10:
            is_home = r["home_team"] == team
            gf = r["home_goals"] if is_home else r["away_goals"]
            if gf is not None:
                goals_total += gf
            # Use stats_json if available for shots
            sj = r.get("stats_json")
            if sj and isinstance(sj, dict):
                side = "home" if is_home else "away"
                shots_total += sj.get(f"{side}_shots_on_target", 0) or 0
        if shots_total > 0:
            result[f"{prefix}_xg_per_shot"] = round(goals_total / shots_total, 3)
        else:
            result[f"{prefix}_xg_per_shot"] = 0.3  # neutral avg

    # ── League-level features ────────────────────────────────
    # League average BTTS + Over 2.5 rates (from all finished matches)
    all_league_fixes = []
    for t in [home_team, away_team]:
        for f in data["fixtures_by_team"].get(t, []):
            if f["date"] < match_date and f.get("home_goals") is not None:
                all_league_fixes.append(f)
    # Deduplicate by api_fixture_id
    seen_ids: set = set()
    unique_fixes: list = []
    for f in all_league_fixes:
        fid = f.get("api_fixture_id")
        if fid and fid not in seen_ids:
            seen_ids.add(fid)
            unique_fixes.append(f)

    if len(unique_fixes) >= 10:
        league_btts = sum(1 for f in unique_fixes if f["home_goals"] > 0 and f["away_goals"] > 0)
        league_o25 = sum(1 for f in unique_fixes if f["home_goals"] + f["away_goals"] > 2)
        result["league_avg_btts_rate"] = round(league_btts / len(unique_fixes), 3)
        result["league_avg_over25_rate"] = round(league_o25 / len(unique_fixes), 3)
    else:
        result["league_avg_btts_rate"] = 0.5
        result["league_avg_over25_rate"] = 0.5

    return result


# ─────────────────────────────────────────────────────────────
#  BUILD FEATURES (un seul match)
# ─────────────────────────────────────────────────────────────


def build_features_fast(fixture: dict, data: dict, league_cache: dict) -> dict | None:
    """Build the full feature vector for a single finished match.

    All computations happen in memory (zero Supabase queries).

    Args:
        fixture: A fixture row dict (must include ``home_goals`` and
            ``away_goals``).
        data: The global in-memory data store returned by
            :func:`load_all_data`.
        league_cache: A mutable dict used to cache per-league team
            strength computations across calls.

    Returns:
        A feature dict ready for insertion into ``training_data``, or
        ``None`` when essential data (goals, team IDs) is missing.
    """
    home_team: str = fixture["home_team"]
    away_team: str = fixture["away_team"]
    league_id: int = fixture["league_id"]
    match_date: str = fixture["date"]
    fixture_api_id: int | None = fixture.get("api_fixture_id")
    referee_name: str | None = fixture.get("referee_name")
    hg: int | None = fixture.get("home_goals")
    ag: int | None = fixture.get("away_goals")

    if hg is None or ag is None:
        return None

    home_id = data["name_to_id"].get(home_team)
    away_id = data["name_to_id"].get(away_team)
    if not home_id or not away_id:
        return None

    features: dict = {
        "fixture_api_id": fixture_api_id,
        "league_id": league_id,
        "season": SEASON,
        "match_date": match_date,
    }

    # 1. Force d'équipe
    if league_id not in league_cache:
        league_cache[league_id] = _team_strengths_from_mem(data, league_id)
    league_data = league_cache[league_id]

    if league_data and league_data["strengths"]:
        hs = league_data["strengths"].get(home_id)
        as_ = league_data["strengths"].get(away_id)
        if hs:
            features["home_attack_strength"] = round(hs["home_attack"], 3)
            features["home_defense_strength"] = round(hs["home_defense"], 3)
        if as_:
            features["away_attack_strength"] = round(as_["away_attack"], 3)
            features["away_defense_strength"] = round(as_["away_defense"], 3)
        features["league_avg_home_goals"] = round(league_data["league_avg_home"], 3)
        features["league_avg_away_goals"] = round(league_data["league_avg_away"], 3)

    # 2. ELO
    h_elo = data["elo_map"].get(home_id, 1500)
    a_elo = data["elo_map"].get(away_id, 1500)
    features["home_elo"] = round(h_elo, 1)
    features["away_elo"] = round(a_elo, 1)
    features["elo_diff"] = round(h_elo - a_elo, 1)

    # 3. Forme
    features["home_form"] = round(_form_from_mem(data, home_team, match_date, home_only=True), 3)
    features["away_form"] = round(_form_from_mem(data, away_team, match_date, home_only=False), 3)

    # 4. Repos
    rest_h, cong_h = _rest_from_mem(data, home_team, match_date)
    rest_a, cong_a = _rest_from_mem(data, away_team, match_date)
    features["home_rest_days"] = rest_h
    features["away_rest_days"] = rest_a
    features["home_congestion_30d"] = cong_h
    features["away_congestion_30d"] = cong_a

    # 5. Enjeu
    features["home_stakes"] = _stakes_from_mem(data, home_id, league_id)
    features["away_stakes"] = _stakes_from_mem(data, away_id, league_id)

    # 6. H2H
    h2h_wr, h2h_total = _h2h_from_mem(data, home_id, away_id)
    features["h2h_home_winrate"] = h2h_wr
    features["h2h_total_matches"] = h2h_total

    # 7. Blessures (count simplifié — on n'a pas l'historique des blessures par date)
    features["home_injury_count"] = _injury_count_from_mem(data, home_id)
    features["away_injury_count"] = _injury_count_from_mem(data, away_id)

    # 8. Arbitre
    features["referee_penalty_bias"] = _referee_from_mem(data, referee_name)

    # 9. Cotes bookmaker
    market = _odds_from_mem(data, fixture_api_id)
    if market:
        features["market_home_prob"] = market["market_home"]
        features["market_draw_prob"] = market["market_draw"]
        features["market_away_prob"] = market["market_away"]

    # 10. xG Poisson (calculé en mémoire)
    if league_data and league_data["strengths"]:
        hs = league_data["strengths"].get(home_id)
        as_ = league_data["strengths"].get(away_id)
        if hs and as_:
            xg_h = hs["home_attack"] * as_["away_defense"] * league_data["league_avg_home"] * 1.12
            xg_a = as_["away_attack"] * hs["home_defense"] * league_data["league_avg_away"]
            xg_h = max(0.3, min(xg_h, 4.0))
            xg_a = max(0.3, min(xg_a, 4.0))
            features["xg_home"] = round(xg_h, 3)
            features["xg_away"] = round(xg_a, 3)

    # 11. Features avancées Phase 5 + Phase A2
    adv = _advanced_features_from_mem(data, home_team, away_team, match_date)
    features.update(adv)

    # 12. Interaction features (Phase A2)
    elo_diff = features.get("elo_diff", 0)
    features["elo_diff_squared"] = round(elo_diff ** 2 / 1000, 3)  # Scaled
    features["form_diff"] = round(
        features.get("home_form", 0.5) - features.get("away_form", 0.5), 3
    )

    # ── TARGETS ───────────────────────────────────────────────
    total: int = hg + ag
    features["home_goals"] = hg
    features["away_goals"] = ag
    features["total_goals"] = total
    features["result"] = "H" if hg > ag else ("D" if hg == ag else "A")
    features["btts"] = hg > 0 and ag > 0
    features["over_05"] = total > 0
    features["over_15"] = total > 1
    features["over_25"] = total > 2
    features["over_35"] = total > 3

    return features


# ─────────────────────────────────────────────────────────────
#  PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────


def run(rebuild: bool = False) -> None:
    """Execute the full training-data build pipeline.

    Loads all reference data, iterates over finished fixtures not yet
    present in ``training_data``, computes feature vectors, and upserts
    them in batches of 200.

    Args:
        rebuild: If True, recompute features for ALL matches (including
                 those already in training_data). Useful after adding
                 new feature columns.

    Returns:
        None.
    """
    logger.info("=" * 60)
    logger.info("  🔧 CONSTRUCTION DU DATASET D'ENTRAÎNEMENT ML")
    if rebuild:
        logger.info("  🔄 MODE REBUILD — recalcul de TOUTES les features")
    logger.info("=" * 60)

    # 1. Charger TOUT en mémoire
    data = load_all_data()

    # 2. Filtrer les matchs FT
    finished = [
        f for f in data["all_fixtures"] if f["status"] == "FT" and f.get("home_goals") is not None
    ]
    finished.sort(key=lambda x: x["date"])

    # 3. Vérifier ce qui est déjà dans training_data
    existing = _fetch_all("training_data", "fixture_api_id")
    existing_ids = {r["fixture_api_id"] for r in existing}

    if rebuild:
        to_process = finished
    else:
        to_process = [f for f in finished if f.get("api_fixture_id") not in existing_ids]
    logger.info(f"  {len(finished)} matchs FT en base")
    logger.info(f"  {len(existing_ids)} déjà dans training_data")
    logger.info(f"  {len(to_process)} matchs à traiter")

    if not to_process:
        logger.info("  ✅ Rien de nouveau à traiter.")
        return

    # 4. Construire les features
    league_cache: dict = {}  # Cache des team_strengths par league_id
    ok: int = 0
    errors: int = 0
    batch: list[dict] = []
    BATCH_SIZE: int = 200

    for i, fix in enumerate(to_process):
        if (i + 1) % 200 == 0 or i == 0:
            logger.info(
                f"  [{i + 1}/{len(to_process)}] {fix['home_team']} vs {fix['away_team']}..."
            )

        try:
            features = build_features_fast(fix, data, league_cache)
            if features:
                batch.append(features)
                ok += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning(f"    ⚠️ Erreur: {e}")

        # Flush batch
        if len(batch) >= BATCH_SIZE:
            logger.info(f"    💾 Upsert batch de {len(batch)}...")
            supabase.table("training_data").upsert(batch, on_conflict="fixture_api_id").execute()
            batch = []

    # Dernier batch
    if batch:
        logger.info(f"    💾 Upsert batch final de {len(batch)}...")
        supabase.table("training_data").upsert(batch, on_conflict="fixture_api_id").execute()

    logger.info(f"  ✅ {ok} feature vectors créés ({errors} erreurs)")
    logger.info("⏭️  Prochaine étape : python train_model.py")


if __name__ == "__main__":
    import sys

    rebuild_mode = "--rebuild" in sys.argv
    run(rebuild=rebuild_mode)
