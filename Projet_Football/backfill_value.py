from __future__ import annotations

"""
backfill_value.py — Met à jour les prédictions existantes avec :
  - proba_over_05 (calculé via Poisson)
  - proba_penalty (calculé via le moteur statistique)

Ne consomme PAS de crédits Claude.
"""
import time

from config import logger, supabase
from models.stats_engine import (
    calculate_penalty_proba,
    get_referee_impact,
    poisson_grid,
)

logger.info("=" * 60)
logger.info("  🔄 BACKFILL : Over 0.5 + Penalty sur prédictions existantes")
logger.info("=" * 60)

# 1. Charger les prédictions hybrid_v1
preds = (
    supabase.table("predictions")
    .select("id, fixture_id, stats_json")
    .eq("model_version", "hybrid_v1")
    .execute()
    .data
)
logger.info(f"{len(preds)} prédictions à enrichir")

# 2. Charger les fixtures
fixtures = supabase.table("fixtures").select("*").eq("status", "NS").execute().data
fix_map = {f["id"]: f for f in fixtures}

# 3. Charger les mappings
teams = supabase.table("teams").select("api_id, name").execute().data
name_to_id = {t["name"]: t["api_id"] for t in teams}

updated = 0
errors = 0

for i, pred in enumerate(preds):
    fix = fix_map.get(pred["fixture_id"])
    if not fix:
        continue

    try:
        # Récupérer les xG depuis stats_json (déjà calculés)
        sj = pred.get("stats_json") or {}
        xg_h = sj.get("xg_home", 1.3)
        xg_a = sj.get("xg_away", 1.1)

        # Recalculer la grille Poisson pour Over 0.5
        grid = poisson_grid(xg_h, xg_a)
        proba_over_05 = grid["proba_over_05"]

        # Calculer proba penalty
        home_id = name_to_id.get(fix["home_team"])
        away_id = name_to_id.get(fix["away_team"])
        ref_impact = get_referee_impact(fix.get("referee_name"))

        # Récupérer les enjeux depuis le contexte sauvegardé
        ctx = sj.get("context", {})
        stakes_home = 1.0
        stakes_away = 1.0
        stakes_label_h = ctx.get("stakes_home", "normal")
        stakes_label_a = ctx.get("stakes_away", "normal")
        # Convertir labels en facteurs
        stakes_map = {
            "titre": 1.08,
            "qualification CL/EL": 1.05,
            "relégation": 1.06,
            "milieu de tableau": 0.97,
            "normal": 1.0,
        }
        stakes_home = stakes_map.get(stakes_label_h, 1.0)
        stakes_away = stakes_map.get(stakes_label_a, 1.0)

        pen_proba, _, _ = calculate_penalty_proba(
            fix,
            referee_impact=ref_impact,
            stakes_home=stakes_home,
            stakes_away=stakes_away,
            home_id=home_id,
            away_id=away_id,
        )

        # Mettre à jour
        supabase.table("predictions").update(
            {
                "proba_over_05": proba_over_05,
                "proba_penalty": pen_proba,
            }
        ).eq("id", pred["id"]).execute()

        updated += 1
        if (i + 1) % 10 == 0:
            logger.info(f"  {i + 1}/{len(preds)}... ({updated} mis à jour)")

    except Exception as e:
        errors += 1
        if errors <= 5:
            fix_name = f"{fix['home_team']} vs {fix['away_team']}" if fix else "?"
            logger.warning(f"  ⚠️ Erreur {fix_name}: {e}")

    time.sleep(0.1)

logger.info(f"{'=' * 60}")
logger.info(f"  ✅ {updated}/{len(preds)} prédictions enrichies ({errors} erreurs)")
logger.info(f"{'=' * 60}")
