-- Migration 015: Best Bets Tracking for "Paris du Soir" feature
-- Tracks the 5 best football + 5 best NHL bets per night with WIN/LOSS/VOID/PENDING results

CREATE TABLE IF NOT EXISTS best_bets (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    sport       TEXT NOT NULL CHECK (sport IN ('football', 'nhl')),
    bet_label   TEXT NOT NULL,             -- "Nashville vs Boston — Over 5.5 Buts"
    market      TEXT NOT NULL,             -- "total_goals_over", "1x2_home", "player_goals", etc.
    odds        NUMERIC(5,2),              -- Indicative odds (implied from model proba)
    confidence  INTEGER CHECK (confidence BETWEEN 1 AND 10),
    proba_model NUMERIC(5,2),             -- Model probability %
    fixture_id  TEXT,                      -- Link to football fixture (nullable for NHL)
    player_name TEXT,                      -- For NHL player bets
    result      TEXT DEFAULT 'PENDING' CHECK (result IN ('WIN', 'LOSS', 'VOID', 'PENDING')),
    notes       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_best_bets_date ON best_bets(date);
CREATE INDEX IF NOT EXISTS idx_best_bets_sport ON best_bets(sport);
CREATE INDEX IF NOT EXISTS idx_best_bets_result ON best_bets(result);

-- RLS
ALTER TABLE best_bets ENABLE ROW LEVEL SECURITY;

-- Anyone authenticated can read
CREATE POLICY "Authenticated users can read best_bets"
    ON best_bets FOR SELECT
    TO authenticated
    USING (true);

-- Only service role can insert/update/delete
CREATE POLICY "Service role manages best_bets"
    ON best_bets FOR ALL
    TO service_role
    USING (true);
