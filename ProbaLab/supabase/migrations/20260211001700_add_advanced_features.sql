-- ================================================================
-- Migration: Ajout des colonnes features avancées Phase 5
-- Momentum, Fatigue, Goal Diff Avg, Result Variance, Clean Sheet Rate
-- ================================================================

ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_momentum REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_momentum REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_fatigue_index INTEGER DEFAULT 0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_fatigue_index INTEGER DEFAULT 0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_goal_diff_avg REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_goal_diff_avg REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_result_variance REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_result_variance REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_clean_sheet_rate REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_clean_sheet_rate REAL DEFAULT 0.0;
