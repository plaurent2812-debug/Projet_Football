import pandas as pd

from src.config import logger, supabase


def extract_meta_dataset() -> pd.DataFrame:
    """
    Extrait l'historique des prédictions (modèles de base + features IA)
    et les joint aux résultats réels (fixtures) pour l'entraînement du XGBoost.

    Version optimisée sans `!inner` join pour éviter les Timeouts Supabase.
    """
    logger.info("📦 Extraction du dataset Meta-Modèle depuis Supabase...")

    # 1. Fetch finished fixtures
    logger.info("📡 Fetching fixtures (pagination)...")
    fixtures = {}
    page_size = 1000
    offset = 0
    while True:
        fix_res = (
            supabase.table("fixtures")
            .select("id, status, home_goals, away_goals")
            .in_("status", ["FT", "AET", "PEN"])
            .range(offset, offset + page_size - 1)
            .execute()
        )
        data = fix_res.data or []
        for f in data:
            fixtures[f["id"]] = f
        if len(data) < page_size:
            break
        offset += page_size
    logger.info(f"✅ {len(fixtures)} Finished Fixtures trouvées.")

    if not fixtures:
        logger.warning("Aucune fixture terminée trouvée.")
        return pd.DataFrame()

    # 2. Fetch predictions (Pagination)
    logger.info("📡 Fetching predictions (pagination)...")
    predictions = []
    page_size = 1000
    offset = 0

    while True:
        res = (
            supabase.table("predictions")
            .select(
                "fixture_id, proba_home, proba_draw, proba_away, proba_btts, proba_over_15, proba_over_2_5, ai_features"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )

        data = res.data or []
        predictions.extend(data)
        if len(data) < page_size:
            break
        offset += page_size
        logger.info(f"  ... fetched {len(predictions)} predictions so far")

    if not predictions:
        logger.warning("Aucune prédiction trouvée.")
        return pd.DataFrame()

    # 3. Build Dataset en joignant manuellement en Python
    logger.info("⚙️  Fusion Fixtures + Predictions en cours...")
    rows = []
    for p in predictions:
        fixture_id = p.get("fixture_id")
        if not fixture_id or fixture_id not in fixtures:
            continue

        fix = fixtures[fixture_id]
        if fix.get("home_goals") is None or fix.get("away_goals") is None:
            continue

        hg = fix["home_goals"]
        ag = fix["away_goals"]

        # Cibles
        target_1x2 = 2 if hg > ag else (1 if hg == ag else 0)
        target_btts = int(hg > 0 and ag > 0)
        target_over_15 = int((hg + ag) > 1)
        target_over_25 = int((hg + ag) > 2)

        # Base Model Probas
        row = {
            "fixture_id": fixture_id,
            "proba_home": p.get("proba_home", 0.33),
            "proba_draw": p.get("proba_draw", 0.33),
            "proba_away": p.get("proba_away", 0.33),
            "proba_btts": p.get("proba_btts", 0.0),
            "proba_over_15": p.get("proba_over_15", 0.0),
            "proba_over_25": p.get("proba_over_2_5", 0.0) or p.get("proba_over_25", 0.0),
            # Target
            "target_1x2": target_1x2,
            "target_btts": target_btts,
            "target_over_15": target_over_15,
            "target_over_25": target_over_25,
            "home_goals": hg,
            "away_goals": ag,
        }

        # Extract AI Features if available (Phase 1 structure)
        ai_feats = p.get("ai_features") or {}
        row["ai_motivation"] = ai_feats.get("motivation_score", 0.0)
        row["ai_media_pressure"] = ai_feats.get("media_pressure", 0.0)
        row["ai_injury_impact"] = ai_feats.get("injury_tactical_impact", 0.0)
        row["ai_cohesion"] = ai_feats.get("cohesion_score", 0.0)
        row["ai_style_risk"] = ai_feats.get("style_risk", 0.0)

        rows.append(row)

    df = pd.DataFrame(rows)
    # Remplacer d'éventuels nans par 0
    df.fillna(0, inplace=True)

    logger.info(f"✅ Dataset extrait: {len(df)} lignes, {len(df.columns)} colonnes.")
    return df


if __name__ == "__main__":
    df = extract_meta_dataset()
    if not df.empty:
        df.to_csv("meta_dataset.csv", index=False)
        logger.info("Dataset sauvegardé sous meta_dataset.csv pour inspection.")
