-- FOOTBALL IA - Migration 013 : Feature Engineering (Phase 2)
-- A exécuter dans Supabase SQL Editor

-- Ajout des nouvelles features au dataset d'entraînement ML
ALTER TABLE training_data 
    -- 1. Météo et conditions de jeu
    ADD COLUMN IF NOT EXISTS temp_celsius REAL,
    ADD COLUMN IF NOT EXISTS is_raining BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_snowing BOOLEAN DEFAULT FALSE,
    
    -- 2. Dynamique Offensive (xG per shot)
    ADD COLUMN IF NOT EXISTS home_xg_per_shot REAL,
    ADD COLUMN IF NOT EXISTS away_xg_per_shot REAL,
    
    -- 3. Momentum & Pressing (Basé sur les expected goals récents)
    ADD COLUMN IF NOT EXISTS home_xg_momentum REAL,
    ADD COLUMN IF NOT EXISTS away_xg_momentum REAL,
    
    -- 4. Taux de clean sheets récent
    ADD COLUMN IF NOT EXISTS home_clean_sheet_rate REAL,
    ADD COLUMN IF NOT EXISTS away_clean_sheet_rate REAL,
    
    -- 5. Value over Replacement (Absence de joueurs clés)
    ADD COLUMN IF NOT EXISTS home_key_player_missing BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS away_key_player_missing BOOLEAN DEFAULT FALSE;
