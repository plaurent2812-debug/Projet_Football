-- =============================================================================
-- Add events_json (goals, cards, subs) to fixtures table
-- =============================================================================

ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS events_json JSONB DEFAULT '[]'::jsonb;
ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS elapsed INTEGER;
