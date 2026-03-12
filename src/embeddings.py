"""
embeddings.py — Gemini Embedding 2 integration for ProbaLab.

Provides shared utilities for:
  - Generating embeddings via Gemini Embedding 2 API (768-dim Matryoshka)
  - Cosine similarity calculations
  - Semantic search via Supabase pgvector RPC functions
  - Profile text builders for matches and players
"""

from __future__ import annotations

import math
import os
from typing import Any

from src.config import GEMINI_API_KEY, logger, supabase

# ── Gemini Client (lazy init) ────────────────────────────────────
_embed_client = None
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMS = 768


def _get_client():
    """Lazily initialize the Gemini client for embeddings."""
    global _embed_client
    if _embed_client is None:
        from google import genai

        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("[Embeddings] GEMINI_API_KEY missing")
            return None
        _embed_client = genai.Client(api_key=api_key)
    return _embed_client


# ═══════════════════════════════════════════════════════════════════
#  CORE EMBEDDING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


def get_embedding(text: str) -> list[float] | None:
    """Generate a 768-dim embedding for a single text using Gemini Embedding 2.

    Args:
        text: The text to embed. Truncated to ~7500 tokens if too long.

    Returns:
        List of 768 floats, or None on error.
    """
    client = _get_client()
    if not client:
        return None

    try:
        # Truncate very long texts to stay within 8192 token limit
        if len(text) > 30000:
            text = text[:30000]

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config={"output_dimensionality": EMBEDDING_DIMS},
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.warning(f"[Embeddings] Error generating embedding: {e}")
        return None


def get_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Generate embeddings for multiple texts.

    Processes texts individually with error isolation so one failure
    doesn't block others.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embeddings (or None for failed items).
    """
    results = []
    for text in texts:
        results.append(get_embedding(text))
    return results


# ═══════════════════════════════════════════════════════════════════
#  SIMILARITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector (must be same length).

    Returns:
        Cosine similarity in [-1.0, 1.0]. Returns 0.0 if either vector is zero.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ═══════════════════════════════════════════════════════════════════
#  SUPABASE PGVECTOR SEARCH (RPC)
# ═══════════════════════════════════════════════════════════════════


def search_learnings(
    query_text: str,
    sport: str = "football",
    limit: int = 5,
    threshold: float = 0.3,
) -> list[dict]:
    """Search ai_learnings by semantic similarity.

    Args:
        query_text: Natural language query to match learnings against.
        sport: Sport filter ('football' or 'nhl').
        limit: Max number of results.
        threshold: Minimum similarity score (0-1).

    Returns:
        List of dicts with keys: id, learning_text, context_tags, similarity.
    """
    embedding = get_embedding(query_text)
    if not embedding:
        return []

    try:
        result = supabase.rpc(
            "match_learnings",
            {
                "query_embedding": embedding,
                "match_sport": sport,
                "match_limit": limit,
                "match_threshold": threshold,
            },
        ).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"[Embeddings] search_learnings RPC failed: {e}")
        return []


def search_predictions(
    query_text: str,
    limit: int = 10,
    threshold: float = 0.3,
) -> list[dict]:
    """Search predictions by semantic similarity on analysis_text.

    Args:
        query_text: Natural language query.
        limit: Max results.
        threshold: Minimum similarity.

    Returns:
        List of dicts with keys: id, fixture_id, analysis_text, proba_*, similarity.
    """
    embedding = get_embedding(query_text)
    if not embedding:
        return []

    try:
        result = supabase.rpc(
            "match_predictions",
            {
                "query_embedding": embedding,
                "match_limit": limit,
                "match_threshold": threshold,
            },
        ).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"[Embeddings] search_predictions RPC failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
#  PROFILE TEXT BUILDERS
# ═══════════════════════════════════════════════════════════════════


def build_match_profile_text(fixture: dict, stats: dict) -> str:
    """Serialize a match's context into a text string for embedding.

    Captures the key quantitative and qualitative features of a match
    so that similar matches can be found via vector search.

    Args:
        fixture: Dict with home_team, away_team, league_id, date.
        stats: Output of analyze_match() with xG, probas, context.

    Returns:
        Structured text string suitable for embedding.
    """
    ctx = stats.get("context", {})

    parts = [
        f"Match: {fixture.get('home_team', '?')} vs {fixture.get('away_team', '?')}",
        f"League: {fixture.get('league_id', '?')}",
        f"xG: {stats.get('xg_home', '?')}-{stats.get('xg_away', '?')}",
        f"Probabilities: Home {stats.get('proba_home', '?')}% Draw {stats.get('proba_draw', '?')}% Away {stats.get('proba_away', '?')}%",
        f"BTTS: {stats.get('proba_btts', '?')}% Over2.5: {stats.get('proba_over_25', '?')}%",
    ]

    # ELO
    elo_h = ctx.get("elo_home")
    elo_a = ctx.get("elo_away")
    if elo_h and elo_a:
        parts.append(f"ELO: {elo_h} vs {elo_a} (gap: {elo_h - elo_a})")

    # Form
    form_h = ctx.get("form_home")
    form_a = ctx.get("form_away")
    if form_h:
        parts.append(f"Home form: {form_h}")
    if form_a:
        parts.append(f"Away form: {form_a}")

    # Rest
    rest_h = ctx.get("rest_days_home")
    rest_a = ctx.get("rest_days_away")
    if rest_h is not None:
        parts.append(f"Rest: Home {rest_h}d, Away {rest_a}d")

    # Congestion
    cong_h = ctx.get("congestion_home")
    cong_a = ctx.get("congestion_away")
    if cong_h is not None:
        parts.append(f"Congestion 30d: Home {cong_h} matches, Away {cong_a} matches")

    # Stakes
    stakes_h = ctx.get("stakes_home")
    stakes_a = ctx.get("stakes_away")
    if stakes_h:
        parts.append(f"Stakes: Home={stakes_h}, Away={stakes_a}")

    # Injuries
    inj_h = ctx.get("injuries_home_details", [])
    inj_a = ctx.get("injuries_away_details", [])
    parts.append(f"Injuries: Home {len(inj_h)}, Away {len(inj_a)}")

    # H2H
    h2h = ctx.get("h2h")
    if h2h:
        parts.append(
            f"H2H: {h2h.get('team_a_wins', 0)}W-{h2h.get('draws', 0)}D-{h2h.get('team_b_wins', 0)}L "
            f"over {h2h.get('total_matches', 0)} matches"
        )

    # Weather
    weather = ctx.get("weather")
    if weather:
        parts.append(
            f"Weather: {weather.get('description', '?')} {weather.get('temp', '?')}°C "
            f"wind {weather.get('wind_speed', '?')}km/h rain {weather.get('rain_mm', 0)}mm"
        )

    return " | ".join(parts)


def build_player_profile_text(player: dict) -> str:
    """Serialize an NHL player's stats into text for embedding.

    Args:
        player: Dict with player stats (player_name, team, ppg,
                prob_goal, prob_assist, shots, etc.)

    Returns:
        Structured text string suitable for embedding.
    """
    parts = [
        f"Player: {player.get('player_name', player.get('name', '?'))}",
        f"Team: {player.get('team', '?')}",
        f"Opponent: {player.get('opp', '?')}",
        f"Home: {'Yes' if player.get('is_home') else 'No'}",
        f"PPG: {player.get('points_per_game', player.get('ppg', '?'))}",
        f"Goals/game: {player.get('goals_per_game', '?')}",
        f"Assists/game: {player.get('assists_per_game', '?')}",
        f"Shots/game: {player.get('shots_per_game', '?')}",
    ]

    # Probability features
    prob_goal = player.get("prob_goal")
    if prob_goal is not None:
        parts.append(f"P(Goal): {prob_goal}%")

    prob_assist = player.get("prob_assist")
    if prob_assist is not None:
        parts.append(f"P(Assist): {prob_assist}%")

    return " | ".join(parts)


# ═══════════════════════════════════════════════════════════════════
#  MATCH CLUSTERING — FIND SIMILAR MATCHES
# ═══════════════════════════════════════════════════════════════════


def find_similar_matches(
    fixture: dict,
    stats: dict,
    limit: int = 3,
) -> list[dict]:
    """Find historically similar matches using embedding similarity.

    Args:
        fixture: Current fixture dict.
        stats: Current match stats from analyze_match().
        limit: Number of similar matches to return.

    Returns:
        List of similar prediction dicts with similarity scores.
    """
    profile_text = build_match_profile_text(fixture, stats)
    return search_predictions(profile_text, limit=limit, threshold=0.4)


# ═══════════════════════════════════════════════════════════════════
#  NHL — FIND SIMILAR PLAYERS (IN-MEMORY)
# ═══════════════════════════════════════════════════════════════════


def find_similar_players(
    target_player: dict,
    all_players: list[dict],
    limit: int = 3,
) -> list[dict]:
    """Find players with similar profiles from today's batch.

    Uses in-memory cosine similarity (no pgvector needed since NHL
    players are ephemeral daily data).

    Args:
        target_player: The player to find similarities for.
        all_players: All players in today's batch.
        limit: Number of similar players to return.

    Returns:
        List of (player_dict, similarity) tuples.
    """
    target_text = build_player_profile_text(target_player)
    target_emb = get_embedding(target_text)
    if not target_emb:
        return []

    # Build embeddings for all other players
    similarities = []
    target_name = target_player.get("player_name", target_player.get("name", ""))

    for player in all_players:
        name = player.get("player_name", player.get("name", ""))
        if name == target_name:
            continue

        player_text = build_player_profile_text(player)
        player_emb = get_embedding(player_text)
        if not player_emb:
            continue

        sim = cosine_similarity(target_emb, player_emb)
        similarities.append({**player, "similarity": round(sim, 4)})

    # Sort by similarity descending
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:limit]


# ═══════════════════════════════════════════════════════════════════
#  TICKET CORRELATION CHECK
# ═══════════════════════════════════════════════════════════════════


def check_ticket_correlation(
    matches: list[dict],
    stats_map: dict[str, dict],
    fixtures_map: dict[str, dict],
    threshold: float = 0.85,
) -> list[tuple[int, int, float]]:
    """Find pairs of correlated matches in a ticket.

    Computes pairwise embedding similarity between match profiles.
    Returns pairs exceeding the threshold.

    Args:
        matches: List of ticket match dicts (with fixture_id).
        stats_map: Map of fixture_id -> stats dict.
        fixtures_map: Map of fixture_id -> fixture dict.
        threshold: Similarity threshold to flag as correlated.

    Returns:
        List of (idx_a, idx_b, similarity) tuples for correlated pairs.
    """
    # Build embeddings for each match
    embeddings = []
    for m in matches:
        fix_id = m.get("fixture_id")
        fix = fixtures_map.get(fix_id, {})
        stats = stats_map.get(fix_id, {})

        if fix and stats:
            text = build_match_profile_text(fix, stats)
            emb = get_embedding(text)
        else:
            # Fallback: embed the match label
            emb = get_embedding(m.get("match", m.get("pick", "")))

        embeddings.append(emb)

    # Pairwise comparison
    correlated = []
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            if embeddings[i] and embeddings[j]:
                sim = cosine_similarity(embeddings[i], embeddings[j])
                if sim > threshold:
                    correlated.append((i, j, round(sim, 4)))

    return correlated
