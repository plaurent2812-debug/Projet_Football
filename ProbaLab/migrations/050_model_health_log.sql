-- Persistence des métriques monitoring quotidiennes
create table if not exists model_health_log (
    id bigserial primary key,
    recorded_at timestamptz not null default now(),
    sport text not null check (sport in ('football','nhl')),
    brier_7d numeric,
    brier_30d numeric,
    log_loss_30d numeric,
    ece_30d numeric,
    clv_best_mean_30d numeric,
    drift_detected boolean default false,
    data_completeness_pct numeric,
    prediction_volume_today integer,
    alert_count integer default 0,
    ml_fallback_rate numeric,
    notes text
);

create index if not exists idx_model_health_log_recorded_at
    on model_health_log(recorded_at desc);
create index if not exists idx_model_health_log_sport_date
    on model_health_log(sport, recorded_at desc);

-- RLS : seul le service_role peut écrire/lire
alter table model_health_log enable row level security;

create policy "service_role_all_model_health_log"
    on model_health_log for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
