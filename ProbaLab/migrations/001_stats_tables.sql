-- ================================================================
-- FOOTBALL IA - Migration 001 : Tables statistiques avancées
-- A exécuter dans Supabase SQL Editor (Dashboard > SQL Editor)
-- ================================================================

-- ────────────────────────────────────────────────────────────────
-- 1. TEAMS — Équipes de chaque ligue
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teams (
    id          BIGSERIAL PRIMARY KEY,
    api_id      INTEGER UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    league_id   INTEGER,
    logo_url    TEXT,
    venue_name  TEXT,
    venue_city  TEXT,
    country     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- 2. PLAYERS — Tous les joueurs des effectifs
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS players (
    id          BIGSERIAL PRIMARY KEY,
    api_id      INTEGER UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    team_api_id INTEGER,
    position    TEXT,          -- Goalkeeper, Defender, Midfielder, Attacker
    nationality TEXT,
    age         INTEGER,
    height_cm   REAL,
    weight_kg   REAL,
    photo_url   TEXT,
    is_injured  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- 3. PLAYER_SEASON_STATS — Stats saison complètes par joueur
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS player_season_stats (
    id                  BIGSERIAL PRIMARY KEY,
    player_api_id       INTEGER NOT NULL,
    team_api_id         INTEGER,
    league_id           INTEGER,
    season              INTEGER NOT NULL,
    -- Jeu
    appearances         INTEGER DEFAULT 0,
    minutes_played      INTEGER DEFAULT 0,
    rating              REAL,
    -- Buts & Passes décisives
    goals               INTEGER DEFAULT 0,
    assists             INTEGER DEFAULT 0,
    goals_conceded      INTEGER DEFAULT 0,   -- Gardiens
    saves               INTEGER DEFAULT 0,   -- Gardiens
    clean_sheets        INTEGER DEFAULT 0,   -- Gardiens
    -- Tirs
    shots_total         INTEGER DEFAULT 0,
    shots_on_target     INTEGER DEFAULT 0,
    -- Passes
    passes_total        INTEGER DEFAULT 0,
    passes_key          INTEGER DEFAULT 0,
    passes_accuracy     INTEGER DEFAULT 0,   -- Pourcentage
    -- Dribbles
    dribbles_attempts   INTEGER DEFAULT 0,
    dribbles_success    INTEGER DEFAULT 0,
    -- Défense
    tackles_total       INTEGER DEFAULT 0,
    interceptions       INTEGER DEFAULT 0,
    duels_total         INTEGER DEFAULT 0,
    duels_won           INTEGER DEFAULT 0,
    -- Fautes
    fouls_drawn         INTEGER DEFAULT 0,
    fouls_committed     INTEGER DEFAULT 0,
    -- Discipline
    yellow_cards        INTEGER DEFAULT 0,
    red_cards           INTEGER DEFAULT 0,
    -- Penalties
    penalty_scored      INTEGER DEFAULT 0,
    penalty_missed      INTEGER DEFAULT 0,
    penalty_saved       INTEGER DEFAULT 0,   -- Gardiens
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_api_id, league_id, season)
);

-- ────────────────────────────────────────────────────────────────
-- 4. MATCH_EVENTS — Buts, passes D, cartons de chaque match
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS match_events (
    id                      BIGSERIAL PRIMARY KEY,
    fixture_api_id          INTEGER NOT NULL,
    team_api_id             INTEGER,
    player_api_id           INTEGER,
    player_name             TEXT,
    assist_player_api_id    INTEGER,
    assist_player_name      TEXT,
    event_type              TEXT NOT NULL,    -- Goal, Card, subst, Var
    event_detail            TEXT,             -- Normal Goal, Penalty, Own Goal, Yellow Card, Red Card, etc.
    minute                  INTEGER,
    extra_minute            INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_match_events_fixture ON match_events(fixture_api_id);
CREATE INDEX IF NOT EXISTS idx_match_events_player ON match_events(player_api_id);

-- ────────────────────────────────────────────────────────────────
-- 5. MATCH_LINEUPS — Compositions de chaque match
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS match_lineups (
    id                  BIGSERIAL PRIMARY KEY,
    fixture_api_id      INTEGER NOT NULL,
    team_api_id         INTEGER NOT NULL,
    player_api_id       INTEGER NOT NULL,
    player_name         TEXT,
    position            TEXT,            -- G, D, M, F
    grid_position       TEXT,            -- ex: "1:1", "3:4"
    is_substitute       BOOLEAN DEFAULT FALSE,
    minutes_played      INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fixture_api_id, team_api_id, player_api_id)
);
CREATE INDEX IF NOT EXISTS idx_match_lineups_fixture ON match_lineups(fixture_api_id);

-- ────────────────────────────────────────────────────────────────
-- 6. MATCH_TEAM_STATS — Stats d'équipe par match (possession, tirs, etc.)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS match_team_stats (
    id                  BIGSERIAL PRIMARY KEY,
    fixture_api_id      INTEGER NOT NULL,
    team_api_id         INTEGER NOT NULL,
    possession          REAL,
    shots_total         INTEGER DEFAULT 0,
    shots_on_target     INTEGER DEFAULT 0,
    shots_off_target    INTEGER DEFAULT 0,
    blocked_shots       INTEGER DEFAULT 0,
    corners             INTEGER DEFAULT 0,
    offsides            INTEGER DEFAULT 0,
    fouls               INTEGER DEFAULT 0,
    yellow_cards        INTEGER DEFAULT 0,
    red_cards           INTEGER DEFAULT 0,
    passes_total        INTEGER DEFAULT 0,
    passes_accurate     INTEGER DEFAULT 0,
    passes_pct          REAL,
    expected_goals      REAL,              -- xG si dispo dans l'API
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fixture_api_id, team_api_id)
);

-- ────────────────────────────────────────────────────────────────
-- 7. TEAM_ELO — Ratings ELO maintenus en interne
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_elo (
    id              BIGSERIAL PRIMARY KEY,
    team_api_id     INTEGER UNIQUE NOT NULL,
    team_name       TEXT,
    league_id       INTEGER,
    elo_rating      REAL DEFAULT 1500.0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- 8. TEAM_STANDINGS — Classement (mis à jour via API)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_standings (
    id              BIGSERIAL PRIMARY KEY,
    team_api_id     INTEGER NOT NULL,
    league_id       INTEGER NOT NULL,
    season          INTEGER NOT NULL,
    rank            INTEGER,
    points          INTEGER DEFAULT 0,
    goal_diff       INTEGER DEFAULT 0,
    form            TEXT,                  -- ex: "WWDLW"
    played          INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    draws           INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    goals_for       INTEGER DEFAULT 0,
    goals_against   INTEGER DEFAULT 0,
    -- Splits domicile / extérieur
    home_played     INTEGER DEFAULT 0,
    home_wins       INTEGER DEFAULT 0,
    home_draws      INTEGER DEFAULT 0,
    home_losses     INTEGER DEFAULT 0,
    home_goals_for  INTEGER DEFAULT 0,
    home_goals_against INTEGER DEFAULT 0,
    away_played     INTEGER DEFAULT 0,
    away_wins       INTEGER DEFAULT 0,
    away_draws      INTEGER DEFAULT 0,
    away_losses     INTEGER DEFAULT 0,
    away_goals_for  INTEGER DEFAULT 0,
    away_goals_against INTEGER DEFAULT 0,
    -- Timestamps
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_api_id, league_id, season)
);

-- ────────────────────────────────────────────────────────────────
-- 9. REFEREES — Arbitres et leurs tendances
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS referees (
    id                      BIGSERIAL PRIMARY KEY,
    name                    TEXT UNIQUE NOT NULL,
    matches_officiated      INTEGER DEFAULT 0,
    total_yellows           INTEGER DEFAULT 0,
    total_reds              INTEGER DEFAULT 0,
    total_penalties         INTEGER DEFAULT 0,
    total_fouls             INTEGER DEFAULT 0,
    avg_yellows_per_match   REAL DEFAULT 0,
    avg_reds_per_match      REAL DEFAULT 0,
    avg_penalties_per_match REAL DEFAULT 0,
    avg_fouls_per_match     REAL DEFAULT 0,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- 10. INJURIES — Joueurs blessés / suspendus
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS injuries (
    id              BIGSERIAL PRIMARY KEY,
    player_api_id   INTEGER NOT NULL,
    player_name     TEXT,
    team_api_id     INTEGER,
    league_id       INTEGER,
    fixture_api_id  INTEGER,
    type            TEXT,          -- Missing Fixture, Questionable, Doubtful
    reason          TEXT,          -- Knee Injury, Suspended, Muscle Injury...
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_injuries_fixture ON injuries(fixture_api_id);

-- ────────────────────────────────────────────────────────────────
-- 11. FIXTURE_ODDS — Cotes bookmakers par match
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fixture_odds (
    id                  BIGSERIAL PRIMARY KEY,
    fixture_api_id      INTEGER UNIQUE NOT NULL,
    bookmaker           TEXT,
    -- 1X2
    home_win_odds       REAL,
    draw_odds           REAL,
    away_win_odds       REAL,
    -- BTTS
    btts_yes_odds       REAL,
    btts_no_odds        REAL,
    -- Over/Under 2.5
    over_25_odds        REAL,
    under_25_odds       REAL,
    -- Over/Under 1.5 & 3.5
    over_15_odds        REAL,
    under_15_odds       REAL,
    over_35_odds        REAL,
    under_35_odds       REAL,
    -- Double Chance
    dc_1x_odds          REAL,
    dc_x2_odds          REAL,
    dc_12_odds          REAL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- 12. H2H_CACHE — Cache des confrontations directes
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS h2h_cache (
    id                  BIGSERIAL PRIMARY KEY,
    team_a_api_id       INTEGER NOT NULL,
    team_b_api_id       INTEGER NOT NULL,
    total_matches       INTEGER DEFAULT 0,
    team_a_wins         INTEGER DEFAULT 0,
    draws               INTEGER DEFAULT 0,
    team_b_wins         INTEGER DEFAULT 0,
    team_a_goals        INTEGER DEFAULT 0,
    team_b_goals        INTEGER DEFAULT 0,
    last_matches_json   JSONB,           -- Détail des 10 derniers matchs
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_a_api_id, team_b_api_id)
);

-- ────────────────────────────────────────────────────────────────
-- 13. ALTER FIXTURES — Ajouter referee + weather
-- ────────────────────────────────────────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fixtures' AND column_name='referee_name') THEN
        ALTER TABLE fixtures ADD COLUMN referee_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fixtures' AND column_name='weather_json') THEN
        ALTER TABLE fixtures ADD COLUMN weather_json JSONB;
    END IF;
END $$;

-- ────────────────────────────────────────────────────────────────
-- 14. ALTER PREDICTIONS — Nouvelles colonnes enrichies
-- ────────────────────────────────────────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='likely_scorer') THEN
        ALTER TABLE predictions ADD COLUMN likely_scorer TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='likely_scorer_proba') THEN
        ALTER TABLE predictions ADD COLUMN likely_scorer_proba INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='correct_score') THEN
        ALTER TABLE predictions ADD COLUMN correct_score TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_correct_score') THEN
        ALTER TABLE predictions ADD COLUMN proba_correct_score INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_over_15') THEN
        ALTER TABLE predictions ADD COLUMN proba_over_15 INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_over_35') THEN
        ALTER TABLE predictions ADD COLUMN proba_over_35 INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_dc_1x') THEN
        ALTER TABLE predictions ADD COLUMN proba_dc_1x INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_dc_x2') THEN
        ALTER TABLE predictions ADD COLUMN proba_dc_x2 INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='proba_dc_12') THEN
        ALTER TABLE predictions ADD COLUMN proba_dc_12 INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='model_version') THEN
        ALTER TABLE predictions ADD COLUMN model_version TEXT DEFAULT 'ai_only_v1';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='predictions' AND column_name='stats_json') THEN
        ALTER TABLE predictions ADD COLUMN stats_json JSONB;
    END IF;
END $$;

-- ────────────────────────────────────────────────────────────────
-- 15. ENABLE RLS (optionnel mais recommandé)
-- ────────────────────────────────────────────────────────────────
-- Si tu veux accéder aux données via la clé anon, active les policies :
-- ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Allow anon read" ON teams FOR SELECT USING (true);
-- (Répéter pour chaque table)

-- ================================================================
-- FIN DE LA MIGRATION
-- Copie ce fichier dans Supabase Dashboard > SQL Editor > New Query
-- puis clique "Run"
-- ================================================================
