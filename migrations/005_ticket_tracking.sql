-- ================================================================
-- FOOTBALL IA - Migration 005 : Suivi des tickets SAFE/FUN/JACKPOT
-- A exécuter dans Supabase SQL Editor
-- ================================================================

-- ────────────────────────────────────────────────────────────────
-- 1. TICKET_PICKS — Stockage des picks de chaque ticket
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ticket_picks (
    id                  BIGSERIAL PRIMARY KEY,

    -- Identifiant du ticket
    ticket_type         TEXT NOT NULL,         -- 'SAFE', 'FUN', 'JACKPOT'
    ticket_date         DATE NOT NULL,         -- Date de génération du ticket

    -- Match concerné
    fixture_id          BIGINT NOT NULL,
    home_team           TEXT,
    away_team           TEXT,
    match_date          TIMESTAMPTZ,

    -- Détail du pick
    bet_type            TEXT NOT NULL,         -- 'Victoire Dom.', 'Victoire Ext.', 'BTTS Oui', '+2.5 buts'
    confidence          INTEGER,               -- Confiance en %
    odds_est            REAL,                  -- Cote estimée (100 / confiance)

    -- Résultat (rempli lors de l'évaluation post-match)
    is_won              BOOLEAN,               -- NULL = pas encore évalué, TRUE/FALSE après évaluation
    evaluated_at        TIMESTAMPTZ,           -- Date de l'évaluation

    created_at          TIMESTAMPTZ DEFAULT NOW(),

    -- Un seul pick par type de ticket / date / match / pari
    UNIQUE(ticket_type, ticket_date, fixture_id, bet_type)
);

CREATE INDEX IF NOT EXISTS idx_ticket_picks_type ON ticket_picks(ticket_type);
CREATE INDEX IF NOT EXISTS idx_ticket_picks_date ON ticket_picks(ticket_date);
CREATE INDEX IF NOT EXISTS idx_ticket_picks_fixture ON ticket_picks(fixture_id);
CREATE INDEX IF NOT EXISTS idx_ticket_picks_evaluated ON ticket_picks(is_won) WHERE is_won IS NULL;

-- ────────────────────────────────────────────────────────────────
-- 2. TICKET_RESULTS — Résumé par ticket (agrégé)
-- Vue matérialisée pour le dashboard
-- ────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW ticket_results_view AS
SELECT
    ticket_type,
    ticket_date,
    COUNT(*)                                          AS total_picks,
    COUNT(*) FILTER (WHERE is_won IS NOT NULL)        AS evaluated_picks,
    COUNT(*) FILTER (WHERE is_won = TRUE)             AS won_picks,
    COUNT(*) FILTER (WHERE is_won = FALSE)            AS lost_picks,
    -- Un ticket est gagné si TOUS ses picks sont gagnés
    CASE
        WHEN COUNT(*) FILTER (WHERE is_won IS NULL) > 0 THEN NULL     -- Pas encore complet
        WHEN COUNT(*) FILTER (WHERE is_won = FALSE) = 0 THEN TRUE     -- Tout gagné
        ELSE FALSE                                                      -- Au moins 1 perdu
    END                                               AS ticket_won,
    ROUND(AVG(confidence)::numeric, 1)                AS avg_confidence,
    ROUND(EXP(SUM(LN(GREATEST(odds_est, 1.01))))::numeric, 2) AS combined_odds
FROM ticket_picks
GROUP BY ticket_type, ticket_date
ORDER BY ticket_date DESC;

-- ================================================================
-- FIN DE LA MIGRATION
-- ================================================================
