-- Migration: Create football_players table for detailed profiles
CREATE TABLE IF NOT EXISTS public.football_players (
    player_id INTEGER PRIMARY KEY,
    name TEXT,
    firstname TEXT,
    lastname TEXT,
    age INTEGER,
    nationality TEXT,
    height TEXT,
    weight TEXT,
    photo TEXT,
    team_id INTEGER,
    team_name TEXT,
    team_logo TEXT,
    position TEXT,
    stats_json JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index for quickly finding players by team
CREATE INDEX IF NOT EXISTS idx_football_players_team_id ON public.football_players(team_id);
