-- =============================================================================
-- PROBALAB - NHL Fixtures
-- 007_nhl_fixtures.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS nhl_fixtures (
    id BIGSERIAL PRIMARY KEY,
    api_fixture_id INTEGER UNIQUE NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    status VARCHAR(50),
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INTEGER,
    away_score INTEGER,
    season INTEGER,
    round VARCHAR(100),
    venue VARCHAR(100),
    
    -- Odds JSON for storing market odds
    odds_json JSONB DEFAULT '{}'::jsonb,
    
    -- Stats JSON for storing advanced stats (e.g. from API-Football)
    stats_json JSONB DEFAULT '{}'::jsonb,
    
    -- Predictions JSON for storing pre-calculated probabilities
    predictions_json JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nhl_fixtures_date ON nhl_fixtures(date);
CREATE INDEX IF NOT EXISTS idx_nhl_fixtures_status ON nhl_fixtures(status);
CREATE INDEX IF NOT EXISTS idx_nhl_fixtures_api_id ON nhl_fixtures(api_fixture_id);
