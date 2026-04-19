-- ═══════════════════════════════════════════════════════════════════
--  H2-SS1 — Migrations consolidées 051 + 052 + 053
--  À coller dans Supabase SQL Editor et exécuter en UNE fois
--  Idempotent : toutes les opérations utilisent IF NOT EXISTS
--  Rollback : voir fin du fichier (commenté)
-- ═══════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────
-- 051_closing_odds.sql
-- Table des snapshots de cotes (opening, closing, intraday)
-- Source : The Odds API Dev (foot 8 ligues + NHL)
-- Utilisation : calcul CLV + détection value bets multi-bookmakers
-- ─────────────────────────────────────────────────────────────────────

create table if not exists closing_odds (
  id bigserial primary key,
  sport text not null check (sport in ('football','nhl')),
  fixture_id text not null,
  league_id int,
  match_start timestamptz not null,
  bookmaker text not null
    check (bookmaker in ('pinnacle','betclic','winamax','unibet','zebet')),
  market text not null
    check (market in (
      '1x2','btts','over_1_5','over_2_5','over_3_5',
      'moneyline','totals_nhl','player_goals','player_assists','player_points','player_shots'
    )),
  selection text not null,
  line numeric,
  odds numeric not null check (odds >= 1.01),
  implied_prob numeric not null check (implied_prob > 0 and implied_prob <= 1),
  overround numeric,
  snapshot_type text not null check (snapshot_type in ('opening','closing','intraday')),
  snapshot_at timestamptz not null default now(),
  source_request_id text,
  constraint closing_odds_unique
    unique nulls not distinct (fixture_id, bookmaker, market, selection, line, snapshot_type)
);

create index if not exists idx_closing_odds_fixture
  on closing_odds (fixture_id);
create index if not exists idx_closing_odds_snapshot_at
  on closing_odds (snapshot_at desc);
create index if not exists idx_closing_odds_bookmaker_market
  on closing_odds (bookmaker, market);
create index if not exists idx_closing_odds_match_start
  on closing_odds (match_start);

alter table closing_odds enable row level security;

-- create policy n'est pas idempotent par défaut : drop explicite pour safe re-run
drop policy if exists "service_role_all_closing_odds" on closing_odds;

create policy "service_role_all_closing_odds"
  on closing_odds for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- ─────────────────────────────────────────────────────────────────────
-- 052_model_health_log_clv.sql
-- Extension model_health_log pour CLV par marché + bookmaker + drift features
-- Parent : 050_model_health_log.sql
-- ─────────────────────────────────────────────────────────────────────

alter table model_health_log
  add column if not exists clv_vs_pinnacle_1x2 numeric,
  add column if not exists clv_vs_pinnacle_btts numeric,
  add column if not exists clv_vs_pinnacle_over25 numeric,
  add column if not exists clv_vs_pinnacle_nhl_ml numeric,
  add column if not exists clv_vs_pinnacle_nhl_goals numeric,
  add column if not exists clv_vs_fr_avg_1x2 numeric,
  add column if not exists clv_vs_fr_avg_btts numeric,
  add column if not exists clv_vs_fr_avg_over25 numeric,
  add column if not exists n_matches_clv integer,
  add column if not exists feature_drift_ks jsonb,
  add column if not exists variant_id text;

create index if not exists idx_model_health_log_variant
  on model_health_log (variant_id, recorded_at desc);

-- ─────────────────────────────────────────────────────────────────────
-- 053_advanced_features.sql
-- Nouvelles features pour Étage 2 variantes ML
-- xg_against, shots_against, pace_index, set_pieces_rate stockés dans
-- training_data (colonnes computées au build-time par build_data.py).
-- ─────────────────────────────────────────────────────────────────────

alter table training_data
  add column if not exists xg_against_home numeric,
  add column if not exists xg_against_away numeric,
  add column if not exists shots_against_home numeric,
  add column if not exists shots_against_away numeric,
  add column if not exists pace_index_home numeric,
  add column if not exists pace_index_away numeric,
  add column if not exists set_pieces_rate_home numeric,
  add column if not exists set_pieces_rate_away numeric,
  add column if not exists opponent_xg_against numeric,
  add column if not exists form_vs_weighted numeric,
  add column if not exists home_away_form_split numeric,
  add column if not exists market_volatility numeric;

-- ═══════════════════════════════════════════════════════════════════
--  VERIFICATION QUERIES (à exécuter séparément après le bloc ci-dessus)
-- ═══════════════════════════════════════════════════════════════════

-- 1. closing_odds existe avec les bonnes colonnes
-- select column_name, data_type from information_schema.columns
-- where table_name = 'closing_odds' order by ordinal_position;

-- 2. model_health_log a gagné 11 colonnes CLV
-- select column_name from information_schema.columns
-- where table_name = 'model_health_log'
--   and column_name in ('clv_vs_pinnacle_1x2','clv_vs_fr_avg_1x2',
--                       'n_matches_clv','feature_drift_ks','variant_id');

-- 3. training_data a gagné 12 colonnes de features avancées
-- select count(*) from information_schema.columns
-- where table_name = 'training_data'
--   and column_name in (
--     'xg_against_home','xg_against_away','shots_against_home',
--     'shots_against_away','pace_index_home','pace_index_away',
--     'set_pieces_rate_home','set_pieces_rate_away','opponent_xg_against',
--     'form_vs_weighted','home_away_form_split','market_volatility'
--   );
-- Expected: 12

-- 4. RLS activée sur closing_odds
-- select relname, relrowsecurity from pg_class
-- where relname = 'closing_odds';
-- Expected: relrowsecurity = true

-- 5. Policy service_role en place
-- select polname from pg_policy
-- where polrelid = 'closing_odds'::regclass;
-- Expected: service_role_all_closing_odds

-- ═══════════════════════════════════════════════════════════════════
--  ROLLBACK (à exécuter UNIQUEMENT si problème — DESTRUCTIF)
-- ═══════════════════════════════════════════════════════════════════

-- drop policy if exists "service_role_all_closing_odds" on closing_odds;
-- drop index if exists idx_closing_odds_fixture;
-- drop index if exists idx_closing_odds_snapshot_at;
-- drop index if exists idx_closing_odds_bookmaker_market;
-- drop index if exists idx_closing_odds_match_start;
-- drop table if exists closing_odds;
--
-- drop index if exists idx_model_health_log_variant;
-- alter table model_health_log
--   drop column if exists clv_vs_pinnacle_1x2,
--   drop column if exists clv_vs_pinnacle_btts,
--   drop column if exists clv_vs_pinnacle_over25,
--   drop column if exists clv_vs_pinnacle_nhl_ml,
--   drop column if exists clv_vs_pinnacle_nhl_goals,
--   drop column if exists clv_vs_fr_avg_1x2,
--   drop column if exists clv_vs_fr_avg_btts,
--   drop column if exists clv_vs_fr_avg_over25,
--   drop column if exists n_matches_clv,
--   drop column if exists feature_drift_ks,
--   drop column if exists variant_id;
--
-- alter table training_data
--   drop column if exists xg_against_home,
--   drop column if exists xg_against_away,
--   drop column if exists shots_against_home,
--   drop column if exists shots_against_away,
--   drop column if exists pace_index_home,
--   drop column if exists pace_index_away,
--   drop column if exists set_pieces_rate_home,
--   drop column if exists set_pieces_rate_away,
--   drop column if exists opponent_xg_against,
--   drop column if exists form_vs_weighted,
--   drop column if exists home_away_form_split,
--   drop column if exists market_volatility;
