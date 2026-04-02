-- Migration 016: NHL Player Game Stats
-- Stocke les stats réelles post-match par joueur pour auto-résolution des paris
-- Alimenté par le pipeline NHL du matin après chaque nuit de matchs

CREATE TABLE IF NOT EXISTS nhl_player_game_stats (
    id              BIGSERIAL PRIMARY KEY,
    game_id         BIGINT        NOT NULL,          -- api_fixture_id NHL
    game_date       DATE          NOT NULL,
    player_id       TEXT          NOT NULL,          -- NHL player ID
    player_name     TEXT          NOT NULL,
    team            TEXT          NOT NULL,          -- abbreviation e.g. EDM
    goals           INT           DEFAULT 0,
    assists         INT           DEFAULT 0,
    points          INT           DEFAULT 0,         -- goals + assists
    shots           INT           DEFAULT 0,
    toi             TEXT,                            -- time on ice e.g. "18:42"
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    UNIQUE(game_id, player_id)                       -- no duplicates per game
);

-- Index for nightly resolve queries
CREATE INDEX IF NOT EXISTS idx_nhl_pgs_date   ON nhl_player_game_stats(game_date);
CREATE INDEX IF NOT EXISTS idx_nhl_pgs_player ON nhl_player_game_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_nhl_pgs_team   ON nhl_player_game_stats(team);
CREATE INDEX IF NOT EXISTS idx_nhl_pgs_pid    ON nhl_player_game_stats(player_id);

-- RLS: public read (needed for resolution), service role write
ALTER TABLE nhl_player_game_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "nhl_pgs_read" ON nhl_player_game_stats
    FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'anon');

CREATE POLICY "nhl_pgs_service_write" ON nhl_player_game_stats
    FOR ALL USING (auth.role() = 'service_role');
