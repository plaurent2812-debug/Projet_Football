-- ================================================================
-- FOOTBALL IA - Migration 004 : ML Training Pipeline
-- A exécuter dans Supabase SQL Editor
-- ================================================================

-- ────────────────────────────────────────────────────────────────
-- 1. TRAINING_DATA — Feature vectors + résultats pour chaque match
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS training_data (
    id                      BIGSERIAL PRIMARY KEY,
    fixture_api_id          INTEGER UNIQUE NOT NULL,
    league_id               INTEGER,
    season                  INTEGER,
    match_date              TIMESTAMPTZ,

    -- Features (input du modèle ML)
    home_attack_strength    REAL,
    home_defense_strength   REAL,
    away_attack_strength    REAL,
    away_defense_strength   REAL,
    home_elo                REAL,
    away_elo                REAL,
    elo_diff                REAL,
    home_form               REAL,      -- 0.0 à 1.0
    away_form               REAL,
    home_rest_days          INTEGER,
    away_rest_days          INTEGER,
    home_congestion_30d     INTEGER,
    away_congestion_30d     INTEGER,
    home_stakes             REAL,      -- Facteur enjeu
    away_stakes             REAL,
    h2h_home_winrate        REAL,
    h2h_total_matches       INTEGER,
    home_injury_count       INTEGER DEFAULT 0,
    away_injury_count       INTEGER DEFAULT 0,
    home_injury_attack_factor  REAL DEFAULT 1.0,
    home_injury_defense_factor REAL DEFAULT 1.0,
    away_injury_attack_factor  REAL DEFAULT 1.0,
    away_injury_defense_factor REAL DEFAULT 1.0,
    referee_penalty_bias    REAL,
    market_home_prob        REAL,      -- Probabilité implicite bookmaker
    market_draw_prob        REAL,
    market_away_prob        REAL,
    xg_home                 REAL,
    xg_away                 REAL,
    league_avg_home_goals   REAL,
    league_avg_away_goals   REAL,

    -- Targets (ce qu'on veut prédire)
    home_goals              INTEGER,
    away_goals              INTEGER,
    result                  TEXT,      -- 'H', 'D', 'A'
    btts                    BOOLEAN,
    over_05                 BOOLEAN,
    over_15                 BOOLEAN,
    over_25                 BOOLEAN,
    over_35                 BOOLEAN,
    total_goals             INTEGER,

    created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_training_league ON training_data(league_id);
CREATE INDEX IF NOT EXISTS idx_training_season ON training_data(season);

-- ────────────────────────────────────────────────────────────────
-- 2. ML_MODELS — Modèles entraînés (sérialisés en JSON)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_models (
    id                  BIGSERIAL PRIMARY KEY,
    model_name          TEXT NOT NULL,       -- 'xgb_1x2', 'xgb_btts', 'xgb_over25', etc.
    model_type          TEXT NOT NULL,       -- 'xgboost', 'random_forest', 'logistic'
    target              TEXT NOT NULL,       -- 'result', 'btts', 'over25', etc.
    -- Performance
    accuracy            REAL,
    f1_score            REAL,
    brier_score         REAL,
    log_loss_val        REAL,
    -- Feature importance (JSON)
    feature_importance  JSONB,
    -- Paramètres du modèle sérialisés
    model_params        JSONB,              -- Hyperparamètres
    model_weights       TEXT,               -- Base64-encoded pickle (pour chargement)
    -- Metadata
    training_samples    INTEGER,
    feature_names       TEXT[],
    trained_at          TIMESTAMPTZ DEFAULT NOW(),
    is_active           BOOLEAN DEFAULT TRUE,
    UNIQUE(model_name)
);

-- ================================================================
-- FIN DE LA MIGRATION
-- ================================================================
