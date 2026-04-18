-- Extension model_health_log pour CLV par marché + bookmaker + drift features
-- Parent : 050_model_health_log.sql

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

-- Index utile pour les dashboards de SS2
create index if not exists idx_model_health_log_variant
  on model_health_log (variant_id, recorded_at desc);
