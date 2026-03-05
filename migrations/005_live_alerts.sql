-- Migration 005 : Ajout de la table live_alerts pour le "Half-Time Sniper" via Trigger.dev

CREATE TABLE IF NOT EXISTS public.live_alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    fixture_id UUID REFERENCES public.fixtures(id) ON DELETE CASCADE,
    analysis_text TEXT NOT NULL,
    recommended_bet TEXT NOT NULL,
    confidence_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index pour accélérer les requêtes récentes
CREATE INDEX IF NOT EXISTS idx_live_alerts_created_at ON public.live_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_alerts_fixture_id ON public.live_alerts(fixture_id);

-- Row Level Security (RLS)
ALTER TABLE public.live_alerts ENABLE ROW LEVEL SECURITY;

-- Autoriser la lecture des alertes à tous (le filtre Frontend peut s'occuper du Freemium)
-- ou réserver aux premiums. Ici on garde ouvert en lecture pour tous.
DROP POLICY IF EXISTS "Enable read access for all users on live_alerts" ON public.live_alerts;
CREATE POLICY "Enable read access for all users on live_alerts"
    ON public.live_alerts FOR SELECT
    USING (true);

-- L'insertion se fait via le backend service role, donc pas besoin de policy d'insertion publique.
