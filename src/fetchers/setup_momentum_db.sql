-- Table pour stocker l'historique glissant des statistiques en direct (Momentum Tracker)
CREATE TABLE public.football_momentum_cache (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    api_fixture_id BIGINT UNIQUE NOT NULL,
    stats_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_updated TIMESTAMPTZ DEFAULT now()
);

-- Ajouter des index pour la performance (on va requêter par api_fixture_id très souvent)
CREATE INDEX idx_football_momentum_cache_fixture_id ON public.football_momentum_cache(api_fixture_id);

-- Gérer les permissions (RLS) pour ne pas bloquer l'API
ALTER TABLE public.football_momentum_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read/write for all" 
ON public.football_momentum_cache 
FOR ALL 
USING (true) 
WITH CHECK (true);
