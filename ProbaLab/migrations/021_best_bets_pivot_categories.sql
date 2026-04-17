-- 021_best_bets_pivot_categories.sql
-- Pivot vers 3 catégories de picks quotidiens (safe / fun / value_bet)
-- × 2 sports (football / nhl) avec tracking sur bankroll virtuel.
--
-- Cf. tasks/design_pivot_probas_sportives_2026-04-11.md section 5.2

BEGIN;

-- Ajout des colonnes nécessaires au nouveau modèle
ALTER TABLE best_bets
  ADD COLUMN IF NOT EXISTS category text
    CHECK (category IN ('safe', 'fun', 'value_bet')),
  ADD COLUMN IF NOT EXISTS virtual_stake numeric DEFAULT 10,
  ADD COLUMN IF NOT EXISTS is_auto boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS match_label text;

-- Backfill des picks existants :
--   - notes non vide → pick auto historique, classé value_bet par défaut
--   - notes vide → pick manuel user, catégorie laissée NULL
UPDATE best_bets
SET
  category = 'value_bet',
  is_auto = true,
  virtual_stake = COALESCE(virtual_stake, 10)
WHERE notes IS NOT NULL
  AND notes <> ''
  AND category IS NULL;

-- Index pour requêtes Performance page
CREATE INDEX IF NOT EXISTS idx_best_bets_cat_sport_date
  ON best_bets (category, sport, date DESC)
  WHERE is_auto = true;

-- Index secondaire pour les fetches "picks du jour" par is_auto
CREATE INDEX IF NOT EXISTS idx_best_bets_date_isauto
  ON best_bets (date DESC, is_auto)
  WHERE is_auto = true;

COMMIT;
