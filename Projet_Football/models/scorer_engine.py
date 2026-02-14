"""
scorer_engine.py — Prédiction des buteurs les plus probables (v2).

Facteurs pris en compte :
  1. Buts/90 min cette saison (volume offensif de base)
  2. Forme récente : buts sur les 5 derniers matchs vs moyenne saison
  3. Anomalie statistique : beaucoup de tirs cadrés mais peu de buts = rebond attendu
  4. Qualité défensive adverse (buts encaissés/90 de l'adversaire)
  5. Gardien adverse (save rate, buts encaissés/90)
  6. Historique contre cet adversaire (buts vs cette équipe)
  7. Synergie buteur-passeur (paires fréquentes)
  8. Tireur de penalty attitré
  9. Titularisation (% de titularisations récentes)
  10. xG-based : probabilité Poisson basée sur le xG de l'équipe
"""

from __future__ import annotations

import math

from config import SEASON, supabase
from constants import (
    ANOMALY_CONVERSION_BOOST,
    ANOMALY_MUTE_BOOST,
    DEFENSE_FACTOR_CEIL,
    DEFENSE_FACTOR_FLOOR,
    EXPECTED_CONVERSION_RATE,
    GK_AVG_CONCEDED_PER_90,
    GK_AVG_SAVE_RATE,
    GK_FACTOR_CEIL,
    GK_FACTOR_FLOOR,
    LEAGUE_AVG_GA_PER_MATCH,
    MIN_SHOTS_ON_FOR_ANOMALY,
    MUTE_MIN_MATCHES,
    SHOTS_ON_PER_90_THRESHOLD,
    W_FORM,
    W_GOALS_PER_90,
    W_PENALTY_TAKER,
    W_STARTER,
    W_SYNERGY,
    W_VS_OPPONENT,
)

# ═══════════════════════════════════════════════════════════════════
#  CACHE GLOBAL
# ═══════════════════════════════════════════════════════════════════

_team_name_cache = {}
_team_id_cache = {}


def get_team_name(team_api_id: int) -> str:
    """Return the team name for a given API identifier.

    Lazily loads and caches the full team-name mapping on first call.

    Args:
        team_api_id: Unique API identifier of the team.

    Returns:
        The team name, or ``"Unknown"`` if the identifier is not found.
    """
    if not _team_name_cache:
        teams = supabase.table("teams").select("api_id, name").execute().data
        for t in teams:
            _team_name_cache[t["api_id"]] = t["name"]
            _team_id_cache[t["name"]] = t["api_id"]
    return _team_name_cache.get(team_api_id, "Unknown")


def get_team_id(team_name: str) -> int | None:
    """Return the API identifier for a given team name.

    Forces a cache load via :func:`get_team_name` if the cache is empty.

    Args:
        team_name: Exact display name of the team (e.g. ``"Paris Saint Germain"``).

    Returns:
        The team API id, or ``None`` if the name is not found.
    """
    if not _team_id_cache:
        get_team_name(0)  # force le chargement
    return _team_id_cache.get(team_name)


# ═══════════════════════════════════════════════════════════════════
#  1. STATS SAISON DU JOUEUR
# ═══════════════════════════════════════════════════════════════════


def get_scoring_rate(player_api_id: int) -> dict | None:
    """Compute per-90-minute offensive statistics for a player.

    Aggregates data across all competitions for the current season.

    Args:
        player_api_id: Unique API identifier of the player.

    Returns:
        A dict containing keys such as ``goals_per_90``, ``assists_per_90``,
        ``shots_per_90``, ``shots_on_per_90``, ``total_goals``, ``total_assists``,
        ``conversion_rate``, ``is_penalty_taker``, etc.  Returns ``None`` if the
        player has fewer than 90 minutes played or no stats are found.
    """
    stats = (
        supabase.table("player_season_stats")
        .select(
            "goals, assists, shots_total, shots_on_target, minutes_played, "
            "penalty_scored, penalty_missed, appearances"
        )
        .eq("player_api_id", player_api_id)
        .eq("season", SEASON)
        .execute()
        .data
    )

    if not stats:
        return None

    # Agréger toutes les compétitions
    total = {
        "goals": 0,
        "assists": 0,
        "shots_total": 0,
        "shots_on": 0,
        "mins": 0,
        "pen_scored": 0,
        "pen_missed": 0,
        "apps": 0,
    }
    for s in stats:
        total["goals"] += s.get("goals") or 0
        total["assists"] += s.get("assists") or 0
        total["shots_total"] += s.get("shots_total") or 0
        total["shots_on"] += s.get("shots_on_target") or 0
        total["mins"] += s.get("minutes_played") or 0
        total["pen_scored"] += s.get("penalty_scored") or 0
        total["pen_missed"] += s.get("penalty_missed") or 0
        total["apps"] += s.get("appearances") or 0

    if total["mins"] < 90:
        return None

    per90 = 90 / max(total["mins"], 1)
    return {
        "goals_per_90": round(total["goals"] * per90, 3),
        "assists_per_90": round(total["assists"] * per90, 3),
        "shots_per_90": round(total["shots_total"] * per90, 3),
        "shots_on_per_90": round(total["shots_on"] * per90, 3),
        "total_goals": total["goals"],
        "total_assists": total["assists"],
        "total_shots_on": total["shots_on"],
        "minutes": total["mins"],
        "appearances": total["apps"],
        "penalty_scored": total["pen_scored"],
        "penalty_missed": total["pen_missed"],
        "is_penalty_taker": (total["pen_scored"] + total["pen_missed"]) >= 2,
        # Ratio conversion : buts / tirs cadrés (détection anomalie)
        "conversion_rate": total["goals"] / max(total["shots_on"], 1),
    }


# ═══════════════════════════════════════════════════════════════════
#  2. FORME RÉCENTE (5 derniers matchs)
# ═══════════════════════════════════════════════════════════════════


def get_recent_form(player_api_id: int, team_api_id: int, n: int = 5) -> dict:
    """Analyse recent form of a player over the last *n* matches.

    Compares the player's recent goal output to their season average to
    derive a ``form_factor`` (clamped between 0.5 and 2.0).

    Args:
        player_api_id: Unique API identifier of the player.
        team_api_id: Unique API identifier of the player's team.
        n: Number of recent matches to consider.

    Returns:
        A dict with keys ``goals``, ``matches_played``, ``started``, and
        ``form_factor``.
    """
    team_name = get_team_name(team_api_id)

    # Derniers matchs terminés de l'équipe (par date desc)
    recent_fixtures = (
        supabase.table("fixtures")
        .select("api_fixture_id, date, home_team, away_team")
        .eq("status", "FT")
        .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
        .order("date", desc=True)
        .limit(n)
        .execute()
        .data
    )

    if not recent_fixtures:
        return {"goals": 0, "matches_played": 0, "form_factor": 1.0, "started": 0}

    fixture_ids = [f["api_fixture_id"] for f in recent_fixtures]

    # Buts du joueur dans ces matchs
    goals_events = (
        supabase.table("match_events")
        .select("fixture_api_id")
        .eq("player_api_id", player_api_id)
        .eq("event_type", "Goal")
        .in_("fixture_api_id", fixture_ids)
        .execute()
        .data
    )

    goals_last_n = len(goals_events)

    # Titularisations dans ces matchs
    lineups = (
        supabase.table("match_lineups")
        .select("fixture_api_id, is_substitute")
        .eq("player_api_id", player_api_id)
        .in_("fixture_api_id", fixture_ids)
        .execute()
        .data
    )

    matches_played = len(lineups)
    started = sum(1 for l in lineups if not l.get("is_substitute", True))

    # Form factor : compare buts récents vs attendus (saison)
    rate = get_scoring_rate(player_api_id)
    if rate and matches_played > 0:
        expected = rate["goals_per_90"] * matches_played  # ~1 match = 90 min approx
        if expected > 0:
            raw_form = goals_last_n / expected
            # Borner entre 0.5 et 2.0
            form_factor = min(2.0, max(0.5, raw_form))
        else:
            form_factor = 1.0 if goals_last_n == 0 else 1.5
    else:
        form_factor = 1.0

    return {
        "goals": goals_last_n,
        "matches_played": matches_played,
        "started": started,
        "form_factor": round(form_factor, 2),
    }


# ═══════════════════════════════════════════════════════════════════
#  3. ANOMALIE STATISTIQUE (tirs élevés, buts faibles = rebond)
# ═══════════════════════════════════════════════════════════════════


def get_anomaly_boost(rate: dict | None, recent_form: dict) -> float:
    """Detect a statistical anomaly and return a scoring-boost multiplier.

    When a player generates many shots on target but converts at a rate
    well below the expected average, a rebound is likely — the multiplier
    will be > 1.0.

    Args:
        rate: Season stats dict as returned by :func:`get_scoring_rate`, or
            ``None`` if the player has insufficient data.
        recent_form: Recent-form dict (must contain ``goals`` and
            ``matches_played`` keys).

    Returns:
        A float multiplier (>= 1.0). Values above 1.0 indicate an
        expected scoring rebound.
    """
    if not rate or rate["total_shots_on"] < MIN_SHOTS_ON_FOR_ANOMALY:
        return 1.0

    # Taux de conversion attendu (~20-25% pour un attaquant moyen)
    season_conversion = rate["conversion_rate"]
    expected_conversion = EXPECTED_CONVERSION_RATE

    # Si le joueur a un bon volume de tirs mais conversion basse → boost
    if (
        rate["shots_on_per_90"] >= SHOTS_ON_PER_90_THRESHOLD
        and season_conversion < expected_conversion * 0.7
    ):
        return ANOMALY_CONVERSION_BOOST  # Rebond probable

    # Si le joueur a un bon volume mais 0 but récent malgré tirs → boost
    if recent_form["matches_played"] >= MUTE_MIN_MATCHES and recent_form["goals"] == 0:
        if rate["shots_on_per_90"] >= SHOTS_ON_PER_90_THRESHOLD:
            return ANOMALY_MUTE_BOOST  # Muet mais actif = anomalie

    return 1.0


# ═══════════════════════════════════════════════════════════════════
#  4. QUALITÉ DÉFENSIVE ADVERSE
# ═══════════════════════════════════════════════════════════════════


def get_defense_quality(opponent_team_id: int, is_opponent_home: bool) -> tuple[float, dict | None]:
    """Evaluate the defensive quality of the opponent.

    Computes a multiplier based on goals conceded per match relative to
    the league average. A value > 1.0 indicates a leaky defence, while
    < 1.0 signals a strong one.

    Args:
        opponent_team_id: API identifier of the opposing team.
        is_opponent_home: ``True`` if the opponent is playing at home (uses
            home-specific stats), ``False`` for away stats.

    Returns:
        A tuple of ``(factor, detail_dict)``.  ``detail_dict`` contains
        ``goals_against_pm`` and ``context_ga_pm``, or is ``None`` when
        insufficient data is available.
    """
    standings = (
        supabase.table("team_standings")
        .select(
            "goals_against, played, home_goals_against, home_played, "
            "away_goals_against, away_played"
        )
        .eq("team_api_id", opponent_team_id)
        .eq("season", SEASON)
        .execute()
        .data
    )

    if not standings:
        return 1.0, None

    st = standings[0]
    played = st.get("played") or 0

    if played < 3:
        return 1.0, None

    # Buts encaissés/match (globaux)
    goals_against_pm = (st.get("goals_against") or 0) / max(played, 1)

    # Buts encaissés dom/ext selon le contexte
    if is_opponent_home:
        ha_played = st.get("home_played") or 0
        ha_goals = st.get("home_goals_against") or 0
    else:
        ha_played = st.get("away_played") or 0
        ha_goals = st.get("away_goals_against") or 0

    context_ga_pm = ha_goals / max(ha_played, 1) if ha_played > 2 else goals_against_pm

    # Moyenne de ligue ~1.25 buts encaissés/match
    league_avg = LEAGUE_AVG_GA_PER_MATCH
    factor = context_ga_pm / league_avg

    # Borner entre 0.6 (mur) et 1.6 (passoire)
    factor = min(DEFENSE_FACTOR_CEIL, max(DEFENSE_FACTOR_FLOOR, factor))

    return round(factor, 2), {
        "goals_against_pm": round(goals_against_pm, 2),
        "context_ga_pm": round(context_ga_pm, 2),
    }


# ═══════════════════════════════════════════════════════════════════
#  5. GARDIEN ADVERSE
# ═══════════════════════════════════════════════════════════════════


def get_opponent_gk_factor(opponent_team_id: int) -> tuple[float, dict | None]:
    """Evaluate the quality of the opponent's main goalkeeper.

    A weaker goalkeeper yields a factor > 1.0 (boost for attackers),
    while a stronger one yields < 1.0.

    Args:
        opponent_team_id: API identifier of the opposing team.

    Returns:
        A tuple of ``(factor, detail_dict)``.  ``detail_dict`` contains
        ``conceded_per_90``, ``save_rate``, and ``rating``, or is ``None``
        when no goalkeeper data is available.
    """
    gk_ids = (
        supabase.table("players")
        .select("api_id")
        .eq("team_api_id", opponent_team_id)
        .eq("position", "Goalkeeper")
        .execute()
        .data
    )
    gk_id_set = {g["api_id"] for g in gk_ids}

    if not gk_id_set:
        return 1.0, None

    gk_stats = (
        supabase.table("player_season_stats")
        .select("player_api_id, goals_conceded, saves, minutes_played, rating")
        .eq("team_api_id", opponent_team_id)
        .eq("season", SEASON)
        .execute()
        .data
    )

    gk_candidates = [
        s for s in gk_stats if s["player_api_id"] in gk_id_set and s.get("minutes_played", 0) > 200
    ]

    if not gk_candidates:
        return 1.0, None

    main_gk = max(gk_candidates, key=lambda g: g["minutes_played"])
    mins = max(main_gk["minutes_played"], 1)

    conceded_per_90 = (main_gk["goals_conceded"] or 0) * 90 / mins
    total_faced = (main_gk["saves"] or 0) + (main_gk["goals_conceded"] or 0)
    save_rate = (main_gk["saves"] or 0) / max(total_faced, 1)

    # Moyenne ~1.1 buts encaissés/90 et ~70% save rate
    gk_factor = (conceded_per_90 / GK_AVG_CONCEDED_PER_90) * 0.6 + (
        (1.0 - save_rate) / (1.0 - GK_AVG_SAVE_RATE)
    ) * 0.4

    return round(min(GK_FACTOR_CEIL, max(GK_FACTOR_FLOOR, gk_factor)), 2), {
        "conceded_per_90": round(conceded_per_90, 2),
        "save_rate": round(save_rate * 100),
        "rating": main_gk.get("rating"),
    }


# ═══════════════════════════════════════════════════════════════════
#  6. HISTORIQUE CONTRE L'ADVERSAIRE
# ═══════════════════════════════════════════════════════════════════


def get_goals_vs_team(player_api_id: int, opponent_team_id: int) -> tuple[int, int]:
    """Count goals scored by a player against a specific opponent.

    Args:
        player_api_id: Unique API identifier of the player.
        opponent_team_id: API identifier of the opposing team.

    Returns:
        A tuple of ``(goals_scored, matches_played)`` against the opponent.
    """
    opp_name = get_team_name(opponent_team_id)

    fixtures_home = (
        supabase.table("fixtures")
        .select("api_fixture_id")
        .eq("home_team", opp_name)
        .eq("status", "FT")
        .execute()
        .data
    )

    fixtures_away = (
        supabase.table("fixtures")
        .select("api_fixture_id")
        .eq("away_team", opp_name)
        .eq("status", "FT")
        .execute()
        .data
    )

    fixture_ids = [f["api_fixture_id"] for f in fixtures_home + fixtures_away]
    if not fixture_ids:
        return 0, 0

    goals = (
        supabase.table("match_events")
        .select("id", count="exact")
        .eq("player_api_id", player_api_id)
        .eq("event_type", "Goal")
        .in_("fixture_api_id", fixture_ids)
        .execute()
    )

    return goals.count or 0, len(fixture_ids)


# ═══════════════════════════════════════════════════════════════════
#  7. SYNERGIES BUTEUR-PASSEUR
# ═══════════════════════════════════════════════════════════════════


def get_player_synergies(team_api_id: int) -> list[dict]:
    """Build the scorer-assister synergy graph for a team.

    Aggregates all goal events where an assist was recorded and counts
    how many times each (assister, scorer) pair connected.

    Args:
        team_api_id: API identifier of the team.

    Returns:
        A list of dicts sorted by ``count`` (descending).  Each dict
        contains ``assister_id``, ``assister_name``, ``scorer_id``,
        ``scorer_name``, and ``count``.
    """
    events = (
        supabase.table("match_events")
        .select("player_api_id, player_name, assist_player_api_id, assist_player_name")
        .eq("team_api_id", team_api_id)
        .eq("event_type", "Goal")
        .filter("assist_player_api_id", "not.is", "null")
        .execute()
        .data
    )

    pairs = {}
    for ev in events:
        scorer_id = ev["player_api_id"]
        assister_id = ev["assist_player_api_id"]
        if not scorer_id or not assister_id:
            continue

        key = (assister_id, scorer_id)
        if key not in pairs:
            pairs[key] = {
                "assister_id": assister_id,
                "assister_name": ev.get("assist_player_name", "?"),
                "scorer_id": scorer_id,
                "scorer_name": ev.get("player_name", "?"),
                "count": 0,
            }
        pairs[key]["count"] += 1

    return sorted(pairs.values(), key=lambda x: x["count"], reverse=True)


def get_scorer_synergy_boost(
    player_api_id: int, team_api_id: int
) -> tuple[int, str | None, int | None]:
    """Check whether the scorer's best provider is in the active squad.

    Looks up the top assister for the given scorer within the team's
    synergy graph.

    Args:
        player_api_id: API identifier of the scorer.
        team_api_id: API identifier of the team.

    Returns:
        A tuple of ``(assist_count, assister_name, assister_id)``.
        Returns ``(0, None, None)`` when no significant synergy exists.
    """
    synergies = get_player_synergies(team_api_id)
    for s in synergies:
        if s["scorer_id"] == player_api_id and s["count"] >= 2:
            return s["count"], s["assister_name"], s["assister_id"]
    return 0, None, None


# ═══════════════════════════════════════════════════════════════════
#  8. BLESSURES
# ═══════════════════════════════════════════════════════════════════


def _get_injured_ids(team_api_id: int) -> set[int]:
    """Retrieve API ids of players currently injured or unavailable.

    Combines two sources: injuries linked to upcoming fixtures (status
    ``NS``) and the ``is_injured`` flag on the players table.  Fails
    silently on database errors as this data is non-critical.

    Args:
        team_api_id: API identifier of the team.

    Returns:
        A set of player API ids that should be excluded from predictions.
    """
    injured_ids = set()

    try:
        # Récupérer les fixture_ids des prochains matchs NS
        team_name = get_team_name(team_api_id)
        upcoming = (
            supabase.table("fixtures")
            .select("api_fixture_id")
            .eq("status", "NS")
            .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
            .order("date", desc=False)
            .limit(3)
            .execute()
            .data
        )
        upcoming_ids = [f["api_fixture_id"] for f in upcoming]

        if upcoming_ids:
            inj = (
                supabase.table("injuries")
                .select("player_api_id")
                .eq("team_api_id", team_api_id)
                .in_("fixture_api_id", upcoming_ids)
                .execute()
                .data
            )
            for i in inj:
                if i.get("player_api_id"):
                    injured_ids.add(i["player_api_id"])
    except Exception:
        pass  # Fail silently: non-critical data

    # Flag is_injured sur players (toujours valide)
    try:
        inj2 = (
            supabase.table("players")
            .select("api_id")
            .eq("team_api_id", team_api_id)
            .eq("is_injured", True)
            .execute()
            .data
        )
        for i in inj2:
            if i.get("api_id"):
                injured_ids.add(i["api_id"])
    except Exception:
        pass  # Fail silently: non-critical data

    return injured_ids


# ═══════════════════════════════════════════════════════════════════
#  MOTEUR PRINCIPAL : CLASSEMENT DES BUTEURS
# ═══════════════════════════════════════════════════════════════════


def _rank_scorers(
    team_api_id: int, opponent_team_id: int, team_xg: float, is_opponent_home: bool
) -> list[dict]:
    """Rank a team's outfield players by probability of scoring.

    Combines multiple factors (goals/90, recent form, anomaly boost,
    opponent defence, opponent GK, synergies, penalty duties, starter
    status) into a raw score, then converts to a Poisson-based
    probability using the team's expected goals (*team_xg*).

    Args:
        team_api_id: API identifier of the team whose players are ranked.
        opponent_team_id: API identifier of the opposing team.
        team_xg: Expected goals for the team in this match.
        is_opponent_home: ``True`` when the opponent is the home side.

    Returns:
        A list of scorer dicts (up to 8), sorted by ``raw_score``
        descending.  Each dict contains player info, scoring factors,
        and a ``proba`` field (percent chance of scoring at least one goal).
    """
    players = (
        supabase.table("players")
        .select("api_id, name, position")
        .eq("team_api_id", team_api_id)
        .execute()
        .data
    )

    injured_ids = _get_injured_ids(team_api_id)
    team_name = get_team_name(team_api_id)

    # Facteurs de contexte (calculés une seule fois par équipe)
    defense_factor, defense_info = get_defense_quality(opponent_team_id, is_opponent_home)
    gk_factor, gk_info = get_opponent_gk_factor(opponent_team_id)

    # Pré-charger les synergies une seule fois
    synergies = get_player_synergies(team_api_id)
    synergy_map = {}
    for s in synergies:
        if s["count"] >= 2 and s["scorer_id"] not in synergy_map:
            synergy_map[s["scorer_id"]] = (s["count"], s["assister_name"])

    # Pré-charger l'historique vs adversaire (fixtures de l'adversaire)
    opp_name = get_team_name(opponent_team_id)
    opp_fixture_ids = []
    goals_vs_map = {}  # player_api_id -> nombre de buts vs adversaire
    try:
        fx_h = (
            supabase.table("fixtures")
            .select("api_fixture_id")
            .eq("home_team", opp_name)
            .eq("status", "FT")
            .execute()
            .data
        )
        fx_a = (
            supabase.table("fixtures")
            .select("api_fixture_id")
            .eq("away_team", opp_name)
            .eq("status", "FT")
            .execute()
            .data
        )
        opp_fixture_ids = [f["api_fixture_id"] for f in fx_h + fx_a]

        # Pré-charger TOUS les buts contre cet adversaire (une seule requête)
        if opp_fixture_ids:
            all_vs_goals = (
                supabase.table("match_events")
                .select("player_api_id")
                .eq("event_type", "Goal")
                .eq("team_api_id", team_api_id)
                .in_("fixture_api_id", opp_fixture_ids)
                .execute()
                .data
            )
            for g in all_vs_goals:
                pid = g["player_api_id"]
                goals_vs_map[pid] = goals_vs_map.get(pid, 0) + 1
    except Exception:
        pass  # Fail silently: non-critical data

    # Pré-charger la forme récente (fixtures de l'équipe)
    try:
        recent_fix = (
            supabase.table("fixtures")
            .select("api_fixture_id, date")
            .eq("status", "FT")
            .or_(f"home_team.eq.{team_name},away_team.eq.{team_name}")
            .order("date", desc=True)
            .limit(5)
            .execute()
            .data
        )
        recent_fids = [f["api_fixture_id"] for f in recent_fix]
    except Exception:
        recent_fids = []  # Fail silently: non-critical data

    # Pré-charger tous les buts récents de l'équipe
    recent_goals_all = {}
    recent_lineups_all = {}
    if recent_fids:
        try:
            all_goals = (
                supabase.table("match_events")
                .select("player_api_id, fixture_api_id")
                .eq("event_type", "Goal")
                .in_("fixture_api_id", recent_fids)
                .execute()
                .data
            )
            for g in all_goals:
                pid = g["player_api_id"]
                recent_goals_all.setdefault(pid, []).append(g["fixture_api_id"])
        except Exception:
            pass  # Fail silently: non-critical data
        try:
            all_lineups = (
                supabase.table("match_lineups")
                .select("player_api_id, is_substitute")
                .in_("fixture_api_id", recent_fids)
                .execute()
                .data
            )
            for l in all_lineups:
                pid = l["player_api_id"]
                recent_lineups_all.setdefault(pid, []).append(l)
        except Exception:
            pass  # Fail silently: non-critical data

    scorers = []

    for p in players:
        if p["position"] == "Goalkeeper":
            continue
        if p["api_id"] in injured_ids:
            continue

        try:
            rate = get_scoring_rate(p["api_id"])
            if not rate or rate["minutes"] < 180:
                continue

            pid = p["api_id"]

            # ── Score brut : rendement offensif ──
            score = 0

            # 1. Buts/90 (facteur principal)
            score += rate["goals_per_90"] * W_GOALS_PER_90 * 10

            # 2. Forme récente (depuis les données pré-chargées)
            player_recent_goals = len(recent_goals_all.get(pid, []))
            player_lineups = recent_lineups_all.get(pid, [])
            matches_played = len(player_lineups)
            started = sum(1 for l in player_lineups if not l.get("is_substitute", True))

            # Form factor
            if matches_played > 0 and rate["goals_per_90"] > 0:
                expected = rate["goals_per_90"] * matches_played
                form_factor = min(2.0, max(0.5, player_recent_goals / expected))
            else:
                form_factor = 1.0 if player_recent_goals == 0 else 1.5

            # Anomalie statistique
            anomaly = get_anomaly_boost(
                rate, {"goals": player_recent_goals, "matches_played": matches_played}
            )
            form_factor *= anomaly

            score += (form_factor - 1.0) * W_FORM * 5  # Bonus/malus forme (réduit)

            # 3. Tirs cadrés/90 (volume offensif)
            score += rate["shots_on_per_90"] * 0.05 * 3

            # 4. Historique vs adversaire (pré-chargé)
            goals_vs = goals_vs_map.get(pid, 0)
            matches_vs = len(opp_fixture_ids)
            if matches_vs > 0 and goals_vs > 0:
                score += (goals_vs / matches_vs) * W_VS_OPPONENT * 10

            # 5. Synergie buteur-passeur (pré-chargée)
            syn_data = synergy_map.get(pid)
            syn_name = syn_data[1] if syn_data else None
            syn_count = syn_data[0] if syn_data else 0
            score += min(syn_count * 0.5, 2) * W_SYNERGY

            # 6. Tireur de penalty
            if rate["is_penalty_taker"]:
                score += W_PENALTY_TAKER * 3

            # 7. Titularisation
            if started >= 3:
                score += W_STARTER * 2
            elif matches_played == 0:
                score *= 0.5

            # ── Facteurs contextuels ──
            score *= defense_factor
            score *= gk_factor

            # Minimum score = 0 (pas de négatif)
            score = max(0, score)

            scorers.append(
                {
                    "player_id": pid,
                    "name": p["name"],
                    "team": team_name,
                    "position": p["position"],
                    "raw_score": round(score, 4),
                    "goals_90": rate["goals_per_90"],
                    "shots_90": rate["shots_on_per_90"],
                    "total_goals": rate["total_goals"],
                    "total_assists": rate["total_assists"],
                    "penalty_taker": rate["is_penalty_taker"],
                    "synergy": syn_name,
                    "goals_vs": goals_vs,
                    "matches_vs": matches_vs,
                    "form_goals": player_recent_goals,
                    "form_matches": matches_played,
                    "form_factor": round(form_factor, 2),
                    "defense_factor": defense_factor,
                    "gk_factor": gk_factor,
                    "conversion_rate": rate["conversion_rate"],
                }
            )
        except Exception:
            # Ne pas bloquer si un joueur pose problème
            continue

    # Trier par score brut
    scorers.sort(key=lambda x: x["raw_score"], reverse=True)

    # Convertir en probabilité Poisson basée sur le xG de l'équipe
    # Seuls les scores > 0 participent à la distribution du xG
    positive_scorers = [s for s in scorers if s["raw_score"] > 0]
    total_raw = sum(s["raw_score"] for s in positive_scorers) or 1

    for s in scorers:
        if s["raw_score"] > 0:
            player_share = s["raw_score"] / total_raw
            player_xg = team_xg * player_share
            # P(marquer >= 1 but) = 1 - P(0 but) = 1 - e^(-xG)
            proba = (1 - math.exp(-player_xg)) * 100
            s["proba"] = round(max(3, min(45, proba)))
        else:
            s["proba"] = 3
            player_xg = 0
        s["player_xg"] = round(player_xg, 3)
        s["score"] = s["raw_score"]

    return scorers[:8]


# ═══════════════════════════════════════════════════════════════════
#  PRÉDICTION FINALE : TOP BUTEURS DU MATCH
# ═══════════════════════════════════════════════════════════════════


def predict_scorers(
    home_team_name: str,
    away_team_name: str,
    xg_home: float = 1.3,
    xg_away: float = 1.1,
    top_n: int = 3,
) -> dict | None:
    """Predict the most likely scorers for a given match.

    Ensures at least one scorer from each team is represented in the
    top results (when data is available).

    Args:
        home_team_name: Display name of the home team.
        away_team_name: Display name of the away team.
        xg_home: Expected goals for the home team.
        xg_away: Expected goals for the away team.
        top_n: Maximum number of top scorers to include in the summary.

    Returns:
        A dict containing ``home_scorers``, ``away_scorers``,
        ``top_synergies_home``, ``top_synergies_away``, ``top_scorers``,
        and backward-compatible keys (``likely_scorer``, etc.).
        Returns ``None`` if either team name cannot be resolved.
    """
    teams = supabase.table("teams").select("api_id, name").execute().data
    name_to_id = {t["name"]: t["api_id"] for t in teams}

    home_id = name_to_id.get(home_team_name)
    away_id = name_to_id.get(away_team_name)

    if not home_id or not away_id:
        return None

    home_scorers = _rank_scorers(home_id, away_id, xg_home, is_opponent_home=False)
    away_scorers = _rank_scorers(away_id, home_id, xg_away, is_opponent_home=True)

    results = {
        "home_scorers": home_scorers,
        "away_scorers": away_scorers,
        "top_synergies_home": get_player_synergies(home_id)[:3],
        "top_synergies_away": get_player_synergies(away_id)[:3],
    }

    # ── Top 3 global avec ÉQUILIBRE entre les 2 équipes ──
    # Garantir au moins 1 joueur de chaque équipe
    top_scorers = []

    # Meilleur de chaque équipe en premier
    best_home = home_scorers[0] if home_scorers else None
    best_away = away_scorers[0] if away_scorers else None

    # Tous les candidats restants
    remaining_home = home_scorers[1:] if home_scorers else []
    remaining_away = away_scorers[1:] if away_scorers else []
    all_remaining = remaining_home + remaining_away
    all_remaining.sort(key=lambda x: x["raw_score"], reverse=True)

    # Construire le top 3 : au moins 1 de chaque
    candidates = []
    if best_home and best_away:
        if best_home["raw_score"] >= best_away["raw_score"]:
            candidates = [best_home, best_away]
        else:
            candidates = [best_away, best_home]
        # 3ème = meilleur restant
        if all_remaining:
            candidates.append(all_remaining[0])
    elif best_home:
        candidates = [best_home]
        candidates.extend(remaining_home[:2])
    elif best_away:
        candidates = [best_away]
        candidates.extend(remaining_away[:2])

    for s in candidates[:top_n]:
        top_scorers.append(
            {
                "name": s["name"],
                "team": s["team"],
                "proba": s["proba"],
                "position": s["position"],
                "analysis": _build_scorer_analysis(s),
            }
        )

    results["top_scorers"] = top_scorers

    # Backward compat
    if top_scorers:
        results["likely_scorer"] = top_scorers[0]["name"]
        results["likely_scorer_team"] = top_scorers[0]["team"]
        results["likely_scorer_proba"] = top_scorers[0]["proba"]
    else:
        results["likely_scorer"] = None
        results["likely_scorer_proba"] = 0

    return results


# ═══════════════════════════════════════════════════════════════════
#  ANALYSE TEXTUELLE DU BUTEUR
# ═══════════════════════════════════════════════════════════════════


def _build_scorer_analysis(scorer: dict) -> str:
    """Build a human-readable analysis string for a predicted scorer.

    Combines position, season stats, recent form, anomalies, penalty
    status, synergies, defensive/GK context, and shot volume into a
    single bullet-point summary.

    Args:
        scorer: A scorer dict as produced by :func:`_rank_scorers`.

    Returns:
        A ``" • "``-joined analysis string suitable for display.
    """
    parts = []

    # Position
    pos_label = {"Attacker": "Attaquant", "Midfielder": "Milieu", "Defender": "Défenseur"}.get(
        scorer["position"], scorer["position"]
    )
    parts.append(pos_label)

    # Rendement saison
    parts.append(f"{scorer['goals_90']} buts/90 min ({scorer['total_goals']} buts saison)")

    # Forme récente
    fg = scorer.get("form_goals", 0)
    fm = scorer.get("form_matches", 0)
    ff = scorer.get("form_factor", 1.0)
    if fm > 0:
        if ff >= 1.3:
            parts.append(f"🔥 en forme ({fg} but{'s' if fg > 1 else ''} sur {fm} matchs)")
        elif ff <= 0.7:
            parts.append(f"⚠️ muet ({fg} but sur {fm} matchs)")
        else:
            parts.append(f"{fg} but{'s' if fg > 1 else ''} sur {fm} derniers matchs")

    # Anomalie (tirs élevés, buts bas)
    cr = scorer.get("conversion_rate", 0)
    if cr < 0.15 and scorer.get("shots_90", 0) >= 1.0:
        parts.append("conversion basse → rebond probable")

    # Tireur de penalty
    if scorer.get("penalty_taker"):
        parts.append("tireur de pénalty attitré")

    # Synergie
    if scorer.get("synergy"):
        parts.append(f"synergie avec {scorer['synergy']}")

    # Defense adverse
    df = scorer.get("defense_factor", 1.0)
    if df >= 1.3:
        parts.append("défense adverse fragile")
    elif df <= 0.75:
        parts.append("défense adverse solide")

    # Gardien adverse
    gf = scorer.get("gk_factor", 1.0)
    if gf >= 1.3:
        parts.append("gardien adverse fébrile")

    # Historique vs adversaire
    gv = scorer.get("goals_vs", 0)
    mv = scorer.get("matches_vs", 0)
    if gv > 0 and mv > 0:
        parts.append(
            f"{gv} but{'s' if gv > 1 else ''} en {mv} match{'s' if mv > 1 else ''} vs adversaire"
        )

    # Tirs cadrés
    if scorer.get("shots_90", 0) >= 1.5:
        parts.append(f"{scorer['shots_90']} tirs cadrés/90")

    return " • ".join(parts)
