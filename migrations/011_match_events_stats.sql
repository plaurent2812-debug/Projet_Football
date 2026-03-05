-- ==============================================================================
-- Migration 011: Relationnel Évènements et Statistiques Live (Phase 3)
-- Objectif: Supprimer l'usage intensif de JSON blobs pour permettre l'indexation 
-- et l'analyse décisionnelle SQL.
-- ==============================================================================

-- 1. TABLE DES ÉVÉNEMENTS DE MATCH
CREATE TABLE IF NOT EXISTS public.live_match_events (
    id SERIAL PRIMARY KEY,
    fixture_id UUID NOT NULL REFERENCES public.fixtures(id) ON DELETE CASCADE,
    team_name TEXT NOT NULL,
    player_name TEXT,
    player_id INTEGER,
    assist_name TEXT,
    assist_id INTEGER,
    event_type TEXT NOT NULL, -- 'Goal', 'Card', 'Sub', etc.
    event_detail TEXT,        -- 'Normal Goal', 'Yellow Card', etc.
    time_elapsed INTEGER NOT NULL,
    extra_time INTEGER,
    half TEXT,                -- '1H', '2H', 'ET'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_match_events_fixture ON public.live_match_events(fixture_id);
CREATE INDEX IF NOT EXISTS idx_live_match_events_team ON public.live_match_events(team_name);
CREATE INDEX IF NOT EXISTS idx_live_match_events_player ON public.live_match_events(player_id);

-- 2. TABLE DES STATISTIQUES LIVE
CREATE TABLE IF NOT EXISTS public.live_match_stats (
    id SERIAL PRIMARY KEY,
    fixture_id UUID NOT NULL REFERENCES public.fixtures(id) ON DELETE CASCADE,
    side TEXT CHECK (side IN ('home', 'away')),
    team_name TEXT NOT NULL,
    shots_total INTEGER DEFAULT 0,
    shots_on INTEGER DEFAULT 0,
    possession_pct INTEGER DEFAULT 0,
    corners INTEGER DEFAULT 0,
    fouls INTEGER DEFAULT 0,
    offsides INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    xg NUMERIC(5,2),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fixture_id, side)
);

CREATE INDEX IF NOT EXISTS idx_live_match_stats_fixture ON public.live_match_stats(fixture_id);

-- Active RLS
ALTER TABLE public.live_match_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.live_match_stats ENABLE ROW LEVEL SECURITY;

-- Les données sont écrites par le backend (Service Role) et lues publiquement ou par auth users
CREATE POLICY "Public events are viewable by everyone" ON live_match_events FOR SELECT USING (true);
CREATE POLICY "Public stats are viewable by everyone" ON live_match_stats FOR SELECT USING (true);

