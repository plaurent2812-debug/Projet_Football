-- ================================================================
-- FOOTBALL IA - Migration 002 : Colonnes value betting
-- A exécuter dans Supabase SQL Editor (Dashboard > SQL Editor)
-- ================================================================

-- Nouvelles colonnes pour Over 0.5 et probabilité de penalty
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_over_05') THEN
        ALTER TABLE predictions ADD COLUMN proba_over_05 INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_penalty') THEN
        ALTER TABLE predictions ADD COLUMN proba_penalty INTEGER;
    END IF;
END $$;

-- ================================================================
-- FIN DE LA MIGRATION
-- ================================================================
