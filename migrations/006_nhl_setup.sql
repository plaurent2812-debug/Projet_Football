-- =============================================================================
-- PROBALAB - NHL Integration
-- 006_nhl_setup.sql
-- =============================================================================

-- 1. nhl_data_lake
CREATE TABLE IF NOT EXISTS nhl_data_lake (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    date DATE NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT,
    team TEXT,
    opp TEXT,
    algo_score_goal INTEGER,
    algo_score_shot INTEGER,
    is_home INTEGER,
    python_prob REAL,
    python_vol REAL,
    result_goal TEXT,
    result_shot TEXT
);
CREATE INDEX IF NOT EXISTS idx_nhl_data_lake_date ON nhl_data_lake(date);
CREATE INDEX IF NOT EXISTS idx_nhl_data_lake_player ON nhl_data_lake(player_id);


-- 2. nhl_suivi_algo_clean
CREATE TABLE IF NOT EXISTS nhl_suivi_algo_clean (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    date DATE NOT NULL,
    match TEXT,
    type TEXT,
    joueur TEXT,
    pari TEXT,
    cote REAL,
    "résultat" TEXT,
    score_reel TEXT DEFAULT '',
    diagnostic_ia TEXT DEFAULT '',
    analyse_postmortem TEXT DEFAULT '',
    id_ref TEXT DEFAULT '',
    proba_predite REAL,
    python_prob REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_nhl_suivi_algo_unique ON nhl_suivi_algo_clean(date, match, type, joueur, pari);


-- 3. nhl_ml_training_history
CREATE TABLE IF NOT EXISTS nhl_ml_training_history (
    id BIGSERIAL PRIMARY KEY,
    market TEXT NOT NULL,
    training_date TIMESTAMPTZ DEFAULT NOW(),
    accuracy REAL,
    roc_auc REAL,
    log_loss REAL,
    brier_score REAL,
    f1_score REAL,
    cv_auc_mean REAL,
    cv_auc_std REAL,
    n_samples INTEGER,
    n_features INTEGER,
    features_used TEXT,
    top_features TEXT
);
CREATE INDEX IF NOT EXISTS idx_nhl_ml_training_market_date 
ON nhl_ml_training_history(market, training_date DESC);


-- 4. nhl_daily_analysis
CREATE TABLE IF NOT EXISTS nhl_daily_analysis (
    id BIGSERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    match TEXT,
    joueur TEXT,
    pari TEXT,
    resultat TEXT,
    proba_predite REAL,
    score_reel TEXT,
    analyse_ia TEXT,
    market TEXT,
    cote REAL
);
CREATE INDEX IF NOT EXISTS idx_nhl_daily_analysis_date 
ON nhl_daily_analysis(analysis_date DESC);


-- 5. nhl_daily_performance
CREATE TABLE IF NOT EXISTS nhl_daily_performance (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_bets INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    accuracy REAL DEFAULT 0,
    avg_odds REAL DEFAULT 0,
    roi REAL DEFAULT 0,
    
    goal_bets INTEGER DEFAULT 0,
    goal_wins INTEGER DEFAULT 0,
    goal_accuracy REAL DEFAULT 0,
    
    shot_bets INTEGER DEFAULT 0,
    shot_wins INTEGER DEFAULT 0,
    shot_accuracy REAL DEFAULT 0,
    
    point_bets INTEGER DEFAULT 0,
    point_wins INTEGER DEFAULT 0,
    point_accuracy REAL DEFAULT 0,
    
    assist_bets INTEGER DEFAULT 0,
    assist_wins INTEGER DEFAULT 0,
    assist_accuracy REAL DEFAULT 0,
    
    winner_bets INTEGER DEFAULT 0,
    winner_wins INTEGER DEFAULT 0,
    winner_accuracy REAL DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_nhl_daily_performance_date 
ON nhl_daily_performance(date DESC);


-- 6. VIEWS

CREATE OR REPLACE VIEW nhl_v_performance_summary AS
SELECT 
    COUNT(*) as total_bets,
    SUM(CASE WHEN "résultat" ILIKE '%GAGNÉ%' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN "résultat" ILIKE '%PERDU%' THEN 1 ELSE 0 END) as losses,
    ROUND(
        SUM(CASE WHEN "résultat" ILIKE '%GAGNÉ%' THEN 1 ELSE 0 END)::NUMERIC / 
        NULLIF(COUNT(*), 0) * 100, 1
    ) as accuracy_pct,
    ROUND(AVG(cote)::NUMERIC, 2) as avg_odds,
    MIN(date) as first_date,
    MAX(date) as last_date,
    COUNT(DISTINCT date) as n_dates
FROM nhl_suivi_algo_clean
WHERE "résultat" ILIKE '%GAGNÉ%' OR "résultat" ILIKE '%PERDU%';


CREATE OR REPLACE VIEW nhl_v_performance_by_market AS
SELECT 
    CASE 
        WHEN pari ILIKE '%point%' THEN 'POINT'
        WHEN pari ILIKE '%buteur%' OR pari ILIKE '%but%' OR pari ILIKE '%goal%' THEN 'GOAL'
        WHEN pari ILIKE '%passeur%' OR pari ILIKE '%assist%' OR pari ILIKE '%passe%' THEN 'ASSIST'
        WHEN pari ILIKE '%tir%' OR pari ILIKE '%shot%' THEN 'SHOT'
        WHEN pari ILIKE '%vainqueur%' OR pari ILIKE '%victoire%' OR pari ILIKE '%winner%' THEN 'WINNER'
        ELSE 'OTHER'
    END as market,
    COUNT(*) as total,
    SUM(CASE WHEN "résultat" ILIKE '%GAGNÉ%' THEN 1 ELSE 0 END) as wins,
    ROUND(
        SUM(CASE WHEN "résultat" ILIKE '%GAGNÉ%' THEN 1 ELSE 0 END)::NUMERIC / 
        NULLIF(COUNT(*), 0) * 100, 1
    ) as accuracy_pct,
    ROUND(AVG(cote)::NUMERIC, 2) as avg_odds
FROM nhl_suivi_algo_clean
WHERE "résultat" ILIKE '%GAGNÉ%' OR "résultat" ILIKE '%PERDU%'
GROUP BY market
ORDER BY total DESC;


CREATE OR REPLACE VIEW nhl_v_ml_latest AS
SELECT DISTINCT ON (market)
    market,
    training_date,
    accuracy,
    roc_auc,
    brier_score,
    cv_auc_mean,
    n_samples,
    n_features,
    top_features
FROM nhl_ml_training_history
ORDER BY market, training_date DESC;
