-- Table des snapshots de cotes (opening, closing, intraday)
-- Source : The Odds API Dev (foot 8 ligues + NHL)
-- Utilisation : calcul CLV + détection value bets multi-bookmakers
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
    unique (fixture_id, bookmaker, market, selection, line, snapshot_type)
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

create policy "service_role_all_closing_odds"
  on closing_odds for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
