-- Migration: Create football_meta_analysis table for DeepThink strategic analysis
-- 

CREATE TABLE IF NOT EXISTS football_meta_analysis (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    analysis TEXT NOT NULL DEFAULT '',
    n_matches INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS but allow service role full access
ALTER TABLE football_meta_analysis ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read
CREATE POLICY "Allow authenticated read" ON football_meta_analysis
    FOR SELECT TO authenticated USING (true);

-- Allow service role to manage
CREATE POLICY "Allow service role manage" ON football_meta_analysis
    FOR ALL TO service_role USING (true);

-- Index on date for fast lookups
CREATE INDEX IF NOT EXISTS idx_football_meta_analysis_date ON football_meta_analysis(date);
