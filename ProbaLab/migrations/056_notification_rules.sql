-- 056_notification_rules.sql
-- Lot 2 V1 refonte frontend — T07-T10 (notification rules CRUD).
--
-- Per-user notification rules. Each rule carries 1..3 conditions, an AND/OR
-- logic, one or more channels (telegram|email|push), optional secondary
-- actions, and an enabled flag. The max-3 conditions constraint is enforced
-- at the app layer (Pydantic); the DB only ensures the JSON shape is an array.
--
-- RLS is strict:
--   * service_role has full access (backend workers using the service key).
--   * authenticated users can only read/write their own rows.
--
-- NOTE: migration 055 is skipped on purpose — the conditional user_bets
-- patch was deemed unnecessary since the table already ships with the
-- relevant columns in production.

CREATE TABLE IF NOT EXISTS public.notification_rules (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name               TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 100),
    conditions         JSONB NOT NULL DEFAULT '[]'::jsonb,
    logic              TEXT NOT NULL DEFAULT 'and' CHECK (logic IN ('and', 'or')),
    channels           JSONB NOT NULL DEFAULT '[]'::jsonb,
    secondary_actions  JSONB NOT NULL DEFAULT '[]'::jsonb,
    enabled            BOOLEAN NOT NULL DEFAULT true,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT channels_are_array          CHECK (jsonb_typeof(channels) = 'array'),
    CONSTRAINT conditions_are_array        CHECK (jsonb_typeof(conditions) = 'array'),
    CONSTRAINT secondary_actions_are_array CHECK (jsonb_typeof(secondary_actions) = 'array')
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_user_id
    ON public.notification_rules(user_id);

CREATE INDEX IF NOT EXISTS idx_notification_rules_enabled
    ON public.notification_rules(enabled) WHERE enabled = true;

ALTER TABLE public.notification_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_role_all_notification_rules ON public.notification_rules;
CREATE POLICY service_role_all_notification_rules
    ON public.notification_rules
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS users_own_notification_rules ON public.notification_rules;
CREATE POLICY users_own_notification_rules
    ON public.notification_rules
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ``trigger_set_timestamp`` isn't a shared helper in this project, so we
-- inline the updated_at trigger function (matching the pattern used by
-- migration 054 for ``user_bankroll_settings``).
CREATE OR REPLACE FUNCTION public.tg_notification_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notification_rules_updated_at ON public.notification_rules;
CREATE TRIGGER trg_notification_rules_updated_at
    BEFORE UPDATE ON public.notification_rules
    FOR EACH ROW EXECUTE FUNCTION public.tg_notification_rules_updated_at();
