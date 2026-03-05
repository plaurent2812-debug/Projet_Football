-- ================================================================
-- FOOTBALL IA - Migration 003 : Suivi de performance + ML
-- A exécuter dans Supabase SQL Editor
-- ================================================================

-- ────────────────────────────────────────────────────────────────
-- 1. PREDICTION_RESULTS — Croisement prédiction vs résultat réel
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prediction_results (
    id                  BIGSERIAL PRIMARY KEY,
    fixture_id          BIGINT NOT NULL,
    prediction_id       BIGINT,
    league_id           INTEGER,
    season              INTEGER DEFAULT 2025,

    -- Prédictions du modèle
    pred_home           INTEGER,      -- % victoire dom prédit
    pred_draw           INTEGER,      -- % nul prédit
    pred_away           INTEGER,      -- % victoire ext prédit
    pred_btts           INTEGER,      -- % BTTS prédit
    pred_over_05        INTEGER,
    pred_over_15        INTEGER,
    pred_over_25        INTEGER,
    pred_correct_score  TEXT,
    pred_likely_scorer  TEXT,
    pred_penalty        INTEGER,
    pred_recommended    TEXT,
    pred_confidence     INTEGER,
    model_version       TEXT,

    -- Résultats réels
    actual_home_goals   INTEGER,
    actual_away_goals   INTEGER,
    actual_result       TEXT,          -- 'H', 'D', 'A'
    actual_btts         BOOLEAN,
    actual_over_05      BOOLEAN,
    actual_over_15      BOOLEAN,
    actual_over_25      BOOLEAN,
    actual_correct_score BOOLEAN,
    actual_had_penalty  BOOLEAN,
    actual_scorers      TEXT[],        -- Liste des buteurs réels

    -- Évaluation
    result_1x2_ok       BOOLEAN,      -- La proba max correspondait au résultat ?
    btts_ok             BOOLEAN,
    over_05_ok          BOOLEAN,
    over_15_ok          BOOLEAN,
    over_25_ok          BOOLEAN,
    correct_score_ok    BOOLEAN,
    penalty_ok          BOOLEAN,      -- Penalty prédit >= 30% et il y en a eu un (ou inverse)
    scorer_ok           BOOLEAN,      -- Le buteur prédit a marqué ?
    recommended_bet_ok  BOOLEAN,      -- Le pari recommandé était-il gagnant ?

    -- Analyse post-match
    post_analysis       TEXT,         -- Explication de pourquoi ça a marché / raté

    -- Calibration ML
    brier_score_1x2     REAL,         -- Brier score pour 1X2 (mesure de calibration)
    log_loss            REAL,         -- Log loss pour évaluer la qualité des probas

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fixture_id)
);
CREATE INDEX IF NOT EXISTS idx_pred_results_league ON prediction_results(league_id);
CREATE INDEX IF NOT EXISTS idx_pred_results_season ON prediction_results(season);

-- ────────────────────────────────────────────────────────────────
-- 2. CALIBRATION — Paramètres ML sauvegardés
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calibration (
    id                  BIGSERIAL PRIMARY KEY,
    bet_type            TEXT NOT NULL,     -- '1x2_home', '1x2_draw', '1x2_away', 'btts', 'over25', etc.
    league_id           INTEGER,           -- NULL = global, sinon par ligue
    -- Paramètres Platt scaling : calibrated = sigmoid(a * raw + b)
    platt_a             REAL DEFAULT 1.0,
    platt_b             REAL DEFAULT 0.0,
    -- Biais observé
    bias                REAL DEFAULT 0.0,  -- Notre modèle surestime (+) ou sous-estime (-)
    sample_size         INTEGER DEFAULT 0,
    accuracy            REAL,              -- Taux de réussite observé
    brier_score         REAL,              -- Score de calibration moyen
    last_calibrated     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bet_type, league_id)
);

-- ================================================================
-- FIN DE LA MIGRATION
-- ================================================================
