-- Migration 003 : Table de suivi du bankroll
-- Exécuter dans Supabase SQL Editor

CREATE TABLE IF NOT EXISTS bankroll_tracking (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticket_type TEXT CHECK (ticket_type IN ('safe', 'fun', 'jackpot', 'single')),
    bet_description TEXT,
    stake NUMERIC(10,2) NOT NULL,
    odds NUMERIC(8,3),
    potential_gain NUMERIC(10,2),
    actual_gain NUMERIC(10,2) DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'won', 'lost', 'void')),
    roi NUMERIC(8,4),
    bankroll_before NUMERIC(10,2),
    bankroll_after NUMERIC(10,2),
    model_version TEXT DEFAULT 'hybrid_v3',
    fixture_ids INTEGER[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_bankroll_date ON bankroll_tracking(date DESC);
CREATE INDEX IF NOT EXISTS idx_bankroll_status ON bankroll_tracking(status);
CREATE INDEX IF NOT EXISTS idx_bankroll_type ON bankroll_tracking(ticket_type);

-- Vue : résumé par type de ticket
CREATE OR REPLACE VIEW bankroll_summary AS
SELECT
    ticket_type,
    COUNT(*) AS total_bets,
    COUNT(*) FILTER (WHERE status = 'won') AS wins,
    COUNT(*) FILTER (WHERE status = 'lost') AS losses,
    ROUND(COUNT(*) FILTER (WHERE status = 'won')::numeric / NULLIF(COUNT(*) FILTER (WHERE status IN ('won','lost')), 0) * 100, 1) AS win_rate,
    ROUND(SUM(stake), 2) AS total_staked,
    ROUND(SUM(actual_gain), 2) AS total_gain,
    ROUND(SUM(actual_gain) / NULLIF(SUM(stake), 0) * 100, 2) AS roi_pct
FROM bankroll_tracking
WHERE status IN ('won', 'lost')
GROUP BY ticket_type
ORDER BY ticket_type;
