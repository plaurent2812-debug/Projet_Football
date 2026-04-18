-- Nouvelles features pour Étage 2 variantes ML
-- xg_against, shots_against, pace_index, set_pieces_rate stockés dans
-- training_data (colonnes computées au build-time par build_data.py).
-- Cette migration garantit leur existence si la table le permet.

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
