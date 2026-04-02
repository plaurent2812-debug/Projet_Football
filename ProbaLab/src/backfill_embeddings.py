"""
backfill_embeddings.py — Backfill Gemini Embedding 2 vectors for existing data.

Run with: python -m src.backfill_embeddings

Processes:
  1. ai_learnings without embeddings
  2. predictions with analysis_text but without embeddings
"""

from __future__ import annotations

import time

from src.config import logger, supabase
from src.embeddings import build_match_profile_text, get_embedding


def backfill_learnings() -> int:
    """Backfill embeddings for ai_learnings rows missing them."""
    logger.info("[Backfill] Fetching ai_learnings without embeddings...")

    # Supabase doesn't support .is_("embedding", None) for vector columns,
    # so we fetch all and filter in Python
    try:
        response = (
            supabase.table("ai_learnings")
            .select("id, learning_text, embedding")
            .eq("is_active", True)
            .execute()
        )
    except Exception as e:
        logger.error(f"[Backfill] Failed to fetch learnings: {e}")
        return 0

    rows = [r for r in (response.data or []) if not r.get("embedding")]
    logger.info(f"[Backfill] {len(rows)} learnings need embeddings")

    count = 0
    for i, row in enumerate(rows):
        text = row.get("learning_text", "")
        if not text:
            continue

        embedding = get_embedding(text)
        if not embedding:
            logger.warning(f"[Backfill] Failed to embed learning {row['id']}")
            continue

        try:
            supabase.table("ai_learnings").update(
                {"embedding": embedding}
            ).eq("id", row["id"]).execute()
            count += 1
            if (i + 1) % 10 == 0:
                logger.info(f"[Backfill] Learnings: {i + 1}/{len(rows)} processed")
        except Exception as e:
            logger.error(f"[Backfill] Failed to update learning {row['id']}: {e}")

        # Rate limit: ~4 req/sec to be safe
        time.sleep(0.25)

    logger.info(f"[Backfill] ✅ {count}/{len(rows)} learnings embedded")
    return count


def backfill_predictions(batch_size: int = 50) -> int:
    """Backfill embeddings for predictions with analysis_text but no embedding."""
    logger.info("[Backfill] Fetching predictions without embeddings...")

    try:
        response = (
            supabase.table("predictions")
            .select("id, fixture_id, analysis_text, proba_home, proba_draw, proba_away, embedding")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
    except Exception as e:
        logger.error(f"[Backfill] Failed to fetch predictions: {e}")
        return 0

    rows = [
        r for r in (response.data or [])
        if not r.get("embedding") and r.get("analysis_text")
    ]
    logger.info(f"[Backfill] {len(rows)} predictions need embeddings")

    # Fetch fixture info for profile builder
    fixture_ids = list({r["fixture_id"] for r in rows if r.get("fixture_id")})
    fixtures_map = {}
    if fixture_ids:
        try:
            # Process in batches to avoid query size limits
            for batch_start in range(0, len(fixture_ids), 50):
                batch_ids = fixture_ids[batch_start:batch_start + 50]
                fx_resp = (
                    supabase.table("fixtures")
                    .select("id, home_team, away_team, league_id, date")
                    .in_("id", batch_ids)
                    .execute()
                )
                for f in (fx_resp.data or []):
                    fixtures_map[f["id"]] = f
        except Exception as e:
            logger.warning(f"[Backfill] Could not fetch fixtures: {e}")

    count = 0
    for i, row in enumerate(rows):
        analysis = row.get("analysis_text", "")

        # Build enriched text: profile + analysis
        fix = fixtures_map.get(row.get("fixture_id"), {})
        if fix:
            # Build a lightweight profile (without full stats)
            profile = (
                f"Match: {fix.get('home_team', '?')} vs {fix.get('away_team', '?')} "
                f"| League: {fix.get('league_id', '?')} "
                f"| Probabilities: Home {row.get('proba_home', '?')}% "
                f"Draw {row.get('proba_draw', '?')}% "
                f"Away {row.get('proba_away', '?')}%"
            )
            embed_text = f"{profile} | {analysis}"
        else:
            embed_text = analysis

        embedding = get_embedding(embed_text)
        if not embedding:
            logger.warning(f"[Backfill] Failed to embed prediction {row['id']}")
            continue

        try:
            supabase.table("predictions").update(
                {"embedding": embedding}
            ).eq("id", row["id"]).execute()
            count += 1
            if (i + 1) % 10 == 0:
                logger.info(f"[Backfill] Predictions: {i + 1}/{len(rows)} processed")
        except Exception as e:
            logger.error(f"[Backfill] Failed to update prediction {row['id']}: {e}")

        # Rate limit
        time.sleep(0.25)

    logger.info(f"[Backfill] ✅ {count}/{len(rows)} predictions embedded")
    return count


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  🧠 GEMINI EMBEDDING 2 — Backfill Script")
    logger.info("=" * 60)

    n_learnings = backfill_learnings()
    n_predictions = backfill_predictions()

    logger.info("=" * 60)
    logger.info(f"  ✅ Backfill complete: {n_learnings} learnings, {n_predictions} predictions")
    logger.info("=" * 60)
