-- Migration 017: Table nhl_odds — vraies cotes bookmaker pour player props NHL
-- Source: The Odds API (the-odds-api.com)
-- Exécuter dans Supabase Dashboard → SQL Editor

CREATE TABLE IF NOT EXISTS nhl_odds (
    id              BIGSERIAL PRIMARY KEY,
    game_id         TEXT NOT NULL,          -- The Odds API event ID
    game_date       DATE NOT NULL,
    home_team       TEXT,
    away_team       TEXT,
    player_name     TEXT NOT NULL,
    bookmaker       TEXT NOT NULL,          -- ex: 'draftkings'
    market          TEXT NOT NULL DEFAULT 'player_points',
    line            NUMERIC DEFAULT 0.5,    -- Over 0.5 points
    over_odds       NUMERIC NOT NULL,       -- cote décimale ex: 1.54
    under_odds      NUMERIC,
    fetched_at      TIMESTAMPTZ DEFAULT now()
);

-- Index unique pour éviter les doublons lors des re-fetch
CREATE UNIQUE INDEX IF NOT EXISTS nhl_odds_unique 
    ON nhl_odds (game_id, player_name, bookmaker, market);

-- Index pour accélérer les lookups par date
CREATE INDEX IF NOT EXISTS nhl_odds_game_date_idx ON nhl_odds (game_date);

-- RLS — lecture publique, écriture via service_role uniquement
ALTER TABLE nhl_odds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "nhl_odds_read_all" ON nhl_odds
    FOR SELECT USING (true);
