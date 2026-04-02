-- ================================================================
-- Migration 019 : Fonction RPC atomique pour place_bet
-- Élimine les race conditions du read-then-write non atomique
-- A exécuter dans Supabase SQL Editor
-- ================================================================

CREATE OR REPLACE FUNCTION place_bet_atomic(
    p_ticket_type TEXT,
    p_stake NUMERIC,
    p_odds NUMERIC,
    p_description TEXT DEFAULT '',
    p_fixture_ids INTEGER[] DEFAULT '{}',
    p_model_version TEXT DEFAULT 'hybrid_v3'
) RETURNS JSON AS $$
DECLARE
    v_current_bankroll NUMERIC;
    v_new_bankroll NUMERIC;
    v_row_id INTEGER;
    v_potential_gain NUMERIC;
BEGIN
    -- Lock the latest bankroll row to prevent concurrent reads
    SELECT bankroll_after INTO v_current_bankroll
    FROM bankroll_tracking
    ORDER BY created_at DESC
    LIMIT 1
    FOR UPDATE;

    -- Default starting bankroll if no rows exist
    IF v_current_bankroll IS NULL THEN
        v_current_bankroll := 500.0;
    END IF;

    -- Reject if stake exceeds bankroll
    IF p_stake > v_current_bankroll THEN
        RETURN json_build_object(
            'error', 'Stake exceeds bankroll',
            'current_bankroll', v_current_bankroll
        );
    END IF;

    v_new_bankroll := ROUND(v_current_bankroll - p_stake, 2);
    v_potential_gain := ROUND(p_stake * p_odds, 2);

    INSERT INTO bankroll_tracking (
        date, ticket_type, bet_description, stake, odds,
        potential_gain, actual_gain, status,
        bankroll_before, bankroll_after,
        model_version, fixture_ids
    ) VALUES (
        CURRENT_DATE,
        p_ticket_type,
        p_description,
        ROUND(p_stake, 2),
        ROUND(p_odds, 3),
        v_potential_gain,
        0,
        'pending',
        ROUND(v_current_bankroll, 2),
        v_new_bankroll,
        p_model_version,
        p_fixture_ids
    ) RETURNING id INTO v_row_id;

    RETURN json_build_object(
        'id', v_row_id,
        'status', 'pending',
        'bankroll_before', ROUND(v_current_bankroll, 2),
        'bankroll_after', v_new_bankroll,
        'stake', ROUND(p_stake, 2),
        'odds', ROUND(p_odds, 3),
        'potential_gain', v_potential_gain,
        'ticket_type', p_ticket_type
    );
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- FIN DE LA MIGRATION
-- ================================================================
