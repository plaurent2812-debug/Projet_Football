-- ==============================================================================
-- Migration 010: Sécurisation Ultra (Phase 1 et 2)
-- - Prévention de l'escalade de privilèges (IDOR sur profiles)
-- - Idempotence des événements Stripe
-- - Idempotence des alertes Live
-- ==============================================================================

-- 1. PRÉVENTION D'ESCALADE DE PRIVILÈGES SUR PROFILES
CREATE OR REPLACE FUNCTION public.protect_profile_escalation()
RETURNS TRIGGER AS $$
BEGIN
    -- Si ce n'est pas le service role (admin backend) qui effectue la mise à jour
    -- On force la réinitialisation des champs sensibles à leur ancienne valeur
    IF auth.role() != 'service_role' THEN
        NEW.role = OLD.role;
        NEW.stripe_customer_id = OLD.stripe_customer_id;
        NEW.subscription_status = OLD.subscription_status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS tr_protect_profile_escalation ON public.profiles;

CREATE TRIGGER tr_protect_profile_escalation
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_profile_escalation();

-- 2. TABLE D'IDEMPOTENCE POUR LES WEBHOOKS (Stripe, etc.)
CREATE TABLE IF NOT EXISTS public.processed_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Active RLS sur processed_events (Backend access only)
ALTER TABLE public.processed_events ENABLE ROW LEVEL SECURITY;

-- 3. UNIQUE CONSTRAINT SUR live_alerts
-- Empêche qu'une course (race condition) ou un retry insère 2 alertes Live pour le même match
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'live_alerts') THEN
        ALTER TABLE public.live_alerts DROP CONSTRAINT IF EXISTS live_alerts_fixture_id_key;
        ALTER TABLE public.live_alerts ADD CONSTRAINT live_alerts_fixture_id_key UNIQUE (fixture_id);
    END IF;
END $$;
