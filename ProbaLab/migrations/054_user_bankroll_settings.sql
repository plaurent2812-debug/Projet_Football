-- 054_user_bankroll_settings.sql
-- Persistance des reglages de bankroll par user (Kelly fraction, stake cap, stake initial).
-- Lot 2 V1 refonte frontend — T12 (migration support pour T06 GET+PUT settings).

CREATE TABLE IF NOT EXISTS public.user_bankroll_settings (
    user_id        UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    stake_initial  NUMERIC(12, 2) NOT NULL DEFAULT 100.00 CHECK (stake_initial >= 0),
    kelly_fraction NUMERIC(4, 3)  NOT NULL DEFAULT 0.250 CHECK (kelly_fraction > 0 AND kelly_fraction <= 1),
    stake_cap_pct  NUMERIC(4, 3)  NOT NULL DEFAULT 0.050 CHECK (stake_cap_pct  > 0 AND stake_cap_pct  <= 1),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.user_bankroll_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all ON public.user_bankroll_settings;
CREATE POLICY service_role_all ON public.user_bankroll_settings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS authenticated_own_rows ON public.user_bankroll_settings;
CREATE POLICY authenticated_own_rows ON public.user_bankroll_settings
    FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.tg_user_bankroll_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_bankroll_settings_updated_at ON public.user_bankroll_settings;
CREATE TRIGGER trg_user_bankroll_settings_updated_at
    BEFORE UPDATE ON public.user_bankroll_settings
    FOR EACH ROW EXECUTE FUNCTION public.tg_user_bankroll_settings_updated_at();
