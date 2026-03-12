-- ================================================================
-- Migration: Ajout colonnes Phase A2 + features long-forme
-- Phase A2 : ppg_last5, btts_rate_last10, over25_rate_last10,
--            xg_per_shot, league_avg_btts/over25, elo_diff_squared,
--            form_diff
-- Long-form : home/away_form_long (12 matchs), form_long_diff
-- Injury factors : home/away_injury_attack/defense_factor
-- ================================================================

-- Phase A2 features
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_ppg_last5 REAL DEFAULT 1.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_ppg_last5 REAL DEFAULT 1.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_btts_rate_last10 REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_btts_rate_last10 REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_over25_rate_last10 REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_over25_rate_last10 REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_xg_per_shot REAL DEFAULT 0.3;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_xg_per_shot REAL DEFAULT 0.3;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS league_avg_btts_rate REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS league_avg_over25_rate REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS elo_diff_squared REAL DEFAULT 0.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS form_diff REAL DEFAULT 0.0;

-- Injury impact factors (from get_injury_impact — set to neutral when not available)
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_injury_attack_factor REAL DEFAULT 1.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_injury_defense_factor REAL DEFAULT 1.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_injury_attack_factor REAL DEFAULT 1.0;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_injury_defense_factor REAL DEFAULT 1.0;

-- Long-term form features (12 matches, decay=0.90)
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS home_form_long REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS away_form_long REAL DEFAULT 0.5;
ALTER TABLE training_data ADD COLUMN IF NOT EXISTS form_long_diff REAL DEFAULT 0.0;
