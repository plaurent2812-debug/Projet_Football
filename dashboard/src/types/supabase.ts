export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  public: {
    Tables: {
      calibration: {
        Row: {
          accuracy: number | null
          bet_type: string
          bias: number | null
          brier_score: number | null
          id: number
          last_calibrated: string | null
          league_id: number | null
          platt_a: number | null
          platt_b: number | null
          sample_size: number | null
        }
        Insert: {
          accuracy?: number | null
          bet_type: string
          bias?: number | null
          brier_score?: number | null
          id?: number
          last_calibrated?: string | null
          league_id?: number | null
          platt_a?: number | null
          platt_b?: number | null
          sample_size?: number | null
        }
        Update: {
          accuracy?: number | null
          bet_type?: string
          bias?: number | null
          brier_score?: number | null
          id?: number
          last_calibrated?: string | null
          league_id?: number | null
          platt_a?: number | null
          platt_b?: number | null
          sample_size?: number | null
        }
        Relationships: []
      }
      fixture_odds: {
        Row: {
          away_win_odds: number | null
          bookmaker: string | null
          btts_no_odds: number | null
          btts_yes_odds: number | null
          created_at: string | null
          dc_12_odds: number | null
          dc_1x_odds: number | null
          dc_x2_odds: number | null
          draw_odds: number | null
          fixture_api_id: number
          home_win_odds: number | null
          id: number
          over_15_odds: number | null
          over_25_odds: number | null
          over_35_odds: number | null
          under_15_odds: number | null
          under_25_odds: number | null
          under_35_odds: number | null
        }
        Insert: {
          away_win_odds?: number | null
          bookmaker?: string | null
          btts_no_odds?: number | null
          btts_yes_odds?: number | null
          created_at?: string | null
          dc_12_odds?: number | null
          dc_1x_odds?: number | null
          dc_x2_odds?: number | null
          draw_odds?: number | null
          fixture_api_id: number
          home_win_odds?: number | null
          id?: number
          over_15_odds?: number | null
          over_25_odds?: number | null
          over_35_odds?: number | null
          under_15_odds?: number | null
          under_25_odds?: number | null
          under_35_odds?: number | null
        }
        Update: {
          away_win_odds?: number | null
          bookmaker?: string | null
          btts_no_odds?: number | null
          btts_yes_odds?: number | null
          created_at?: string | null
          dc_12_odds?: number | null
          dc_1x_odds?: number | null
          dc_x2_odds?: number | null
          draw_odds?: number | null
          fixture_api_id?: number
          home_win_odds?: number | null
          id?: number
          over_15_odds?: number | null
          over_25_odds?: number | null
          over_35_odds?: number | null
          under_15_odds?: number | null
          under_25_odds?: number | null
          under_35_odds?: number | null
        }
        Relationships: []
      }
      fixtures: {
        Row: {
          api_fixture_id: number
          away_goals: number | null
          away_team: string
          created_at: string | null
          date: string
          elapsed: number | null
          events_json: Json | null
          home_goals: number | null
          home_team: string
          id: string
          league_id: number | null
          lineups_json: Json | null
          live_stats_json: Json | null
          referee_name: string | null
          stats_json: Json | null
          status: string | null
          weather_json: Json | null
        }
        Insert: {
          api_fixture_id: number
          away_goals?: number | null
          away_team: string
          created_at?: string | null
          date: string
          elapsed?: number | null
          events_json?: Json | null
          home_goals?: number | null
          home_team: string
          id?: string
          league_id?: number | null
          lineups_json?: Json | null
          live_stats_json?: Json | null
          referee_name?: string | null
          stats_json?: Json | null
          status?: string | null
          weather_json?: Json | null
        }
        Update: {
          api_fixture_id?: number
          away_goals?: number | null
          away_team?: string
          created_at?: string | null
          date?: string
          elapsed?: number | null
          events_json?: Json | null
          home_goals?: number | null
          home_team?: string
          id?: string
          league_id?: number | null
          lineups_json?: Json | null
          live_stats_json?: Json | null
          referee_name?: string | null
          stats_json?: Json | null
          status?: string | null
          weather_json?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "fixtures_league_id_fkey"
            columns: ["league_id"]
            isOneToOne: false
            referencedRelation: "leagues"
            referencedColumns: ["api_id"]
          },
        ]
      }
      football_momentum_cache: {
        Row: {
          api_fixture_id: number
          id: string
          last_updated: string | null
          stats_history: Json
        }
        Insert: {
          api_fixture_id: number
          id?: string
          last_updated?: string | null
          stats_history?: Json
        }
        Update: {
          api_fixture_id?: number
          id?: string
          last_updated?: string | null
          stats_history?: Json
        }
        Relationships: []
      }
      football_players: {
        Row: {
          age: number | null
          firstname: string | null
          height: string | null
          lastname: string | null
          name: string | null
          nationality: string | null
          photo: string | null
          player_id: number
          position: string | null
          stats_json: Json | null
          team_id: number | null
          team_logo: string | null
          team_name: string | null
          updated_at: string
          weight: string | null
        }
        Insert: {
          age?: number | null
          firstname?: string | null
          height?: string | null
          lastname?: string | null
          name?: string | null
          nationality?: string | null
          photo?: string | null
          player_id: number
          position?: string | null
          stats_json?: Json | null
          team_id?: number | null
          team_logo?: string | null
          team_name?: string | null
          updated_at?: string
          weight?: string | null
        }
        Update: {
          age?: number | null
          firstname?: string | null
          height?: string | null
          lastname?: string | null
          name?: string | null
          nationality?: string | null
          photo?: string | null
          player_id?: number
          position?: string | null
          stats_json?: Json | null
          team_id?: number | null
          team_logo?: string | null
          team_name?: string | null
          updated_at?: string
          weight?: string | null
        }
        Relationships: []
      }
      h2h_cache: {
        Row: {
          draws: number | null
          id: number
          last_matches_json: Json | null
          team_a_api_id: number
          team_a_goals: number | null
          team_a_wins: number | null
          team_b_api_id: number
          team_b_goals: number | null
          team_b_wins: number | null
          total_matches: number | null
          updated_at: string | null
        }
        Insert: {
          draws?: number | null
          id?: number
          last_matches_json?: Json | null
          team_a_api_id: number
          team_a_goals?: number | null
          team_a_wins?: number | null
          team_b_api_id: number
          team_b_goals?: number | null
          team_b_wins?: number | null
          total_matches?: number | null
          updated_at?: string | null
        }
        Update: {
          draws?: number | null
          id?: number
          last_matches_json?: Json | null
          team_a_api_id?: number
          team_a_goals?: number | null
          team_a_wins?: number | null
          team_b_api_id?: number
          team_b_goals?: number | null
          team_b_wins?: number | null
          total_matches?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      injuries: {
        Row: {
          created_at: string | null
          fixture_api_id: number | null
          id: number
          league_id: number | null
          player_api_id: number
          player_name: string | null
          reason: string | null
          team_api_id: number | null
          type: string | null
        }
        Insert: {
          created_at?: string | null
          fixture_api_id?: number | null
          id?: number
          league_id?: number | null
          player_api_id: number
          player_name?: string | null
          reason?: string | null
          team_api_id?: number | null
          type?: string | null
        }
        Update: {
          created_at?: string | null
          fixture_api_id?: number | null
          id?: number
          league_id?: number | null
          player_api_id?: number
          player_name?: string | null
          reason?: string | null
          team_api_id?: number | null
          type?: string | null
        }
        Relationships: []
      }
      leagues: {
        Row: {
          api_id: number
          country: string | null
          id: number
          name: string
          season: number | null
        }
        Insert: {
          api_id: number
          country?: string | null
          id?: number
          name: string
          season?: number | null
        }
        Update: {
          api_id?: number
          country?: string | null
          id?: number
          name?: string
          season?: number | null
        }
        Relationships: []
      }
      live_alerts: {
        Row: {
          analysis_text: string
          confidence_score: number | null
          created_at: string
          fixture_id: string | null
          id: string
          recommended_bet: string
        }
        Insert: {
          analysis_text: string
          confidence_score?: number | null
          created_at?: string
          fixture_id?: string | null
          id?: string
          recommended_bet: string
        }
        Update: {
          analysis_text?: string
          confidence_score?: number | null
          created_at?: string
          fixture_id?: string | null
          id?: string
          recommended_bet?: string
        }
        Relationships: [
          {
            foreignKeyName: "live_alerts_fixture_id_fkey"
            columns: ["fixture_id"]
            isOneToOne: true
            referencedRelation: "fixtures"
            referencedColumns: ["id"]
          },
        ]
      }
      live_match_events: {
        Row: {
          assist_id: number | null
          assist_name: string | null
          created_at: string | null
          event_detail: string | null
          event_type: string
          extra_time: number | null
          fixture_id: string
          half: string | null
          id: number
          player_id: number | null
          player_name: string | null
          team_name: string
          time_elapsed: number
        }
        Insert: {
          assist_id?: number | null
          assist_name?: string | null
          created_at?: string | null
          event_detail?: string | null
          event_type: string
          extra_time?: number | null
          fixture_id: string
          half?: string | null
          id?: number
          player_id?: number | null
          player_name?: string | null
          team_name: string
          time_elapsed: number
        }
        Update: {
          assist_id?: number | null
          assist_name?: string | null
          created_at?: string | null
          event_detail?: string | null
          event_type?: string
          extra_time?: number | null
          fixture_id?: string
          half?: string | null
          id?: number
          player_id?: number | null
          player_name?: string | null
          team_name?: string
          time_elapsed?: number
        }
        Relationships: [
          {
            foreignKeyName: "live_match_events_fixture_id_fkey"
            columns: ["fixture_id"]
            isOneToOne: false
            referencedRelation: "fixtures"
            referencedColumns: ["id"]
          },
        ]
      }
      live_match_stats: {
        Row: {
          corners: number | null
          fixture_id: string
          fouls: number | null
          id: number
          offsides: number | null
          possession_pct: number | null
          red_cards: number | null
          shots_on: number | null
          shots_total: number | null
          side: string | null
          team_name: string
          updated_at: string | null
          xg: number | null
          yellow_cards: number | null
        }
        Insert: {
          corners?: number | null
          fixture_id: string
          fouls?: number | null
          id?: number
          offsides?: number | null
          possession_pct?: number | null
          red_cards?: number | null
          shots_on?: number | null
          shots_total?: number | null
          side?: string | null
          team_name: string
          updated_at?: string | null
          xg?: number | null
          yellow_cards?: number | null
        }
        Update: {
          corners?: number | null
          fixture_id?: string
          fouls?: number | null
          id?: number
          offsides?: number | null
          possession_pct?: number | null
          red_cards?: number | null
          shots_on?: number | null
          shots_total?: number | null
          side?: string | null
          team_name?: string
          updated_at?: string | null
          xg?: number | null
          yellow_cards?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "live_match_stats_fixture_id_fkey"
            columns: ["fixture_id"]
            isOneToOne: false
            referencedRelation: "fixtures"
            referencedColumns: ["id"]
          },
        ]
      }
      market_odds: {
        Row: {
          away_win: number | null
          bookmaker: string | null
          btts_yes: number | null
          draw: number | null
          fixture_id: string | null
          home_win: number | null
          id: string
          over_2_5: number | null
          updated_at: string | null
        }
        Insert: {
          away_win?: number | null
          bookmaker?: string | null
          btts_yes?: number | null
          draw?: number | null
          fixture_id?: string | null
          home_win?: number | null
          id?: string
          over_2_5?: number | null
          updated_at?: string | null
        }
        Update: {
          away_win?: number | null
          bookmaker?: string | null
          btts_yes?: number | null
          draw?: number | null
          fixture_id?: string | null
          home_win?: number | null
          id?: string
          over_2_5?: number | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "market_odds_fixture_id_fkey"
            columns: ["fixture_id"]
            isOneToOne: false
            referencedRelation: "fixtures"
            referencedColumns: ["id"]
          },
        ]
      }
      match_events: {
        Row: {
          assist_player_api_id: number | null
          assist_player_name: string | null
          created_at: string | null
          event_detail: string | null
          event_type: string
          extra_minute: number | null
          fixture_api_id: number
          id: number
          minute: number | null
          player_api_id: number | null
          player_name: string | null
          team_api_id: number | null
        }
        Insert: {
          assist_player_api_id?: number | null
          assist_player_name?: string | null
          created_at?: string | null
          event_detail?: string | null
          event_type: string
          extra_minute?: number | null
          fixture_api_id: number
          id?: number
          minute?: number | null
          player_api_id?: number | null
          player_name?: string | null
          team_api_id?: number | null
        }
        Update: {
          assist_player_api_id?: number | null
          assist_player_name?: string | null
          created_at?: string | null
          event_detail?: string | null
          event_type?: string
          extra_minute?: number | null
          fixture_api_id?: number
          id?: number
          minute?: number | null
          player_api_id?: number | null
          player_name?: string | null
          team_api_id?: number | null
        }
        Relationships: []
      }
      match_lineups: {
        Row: {
          created_at: string | null
          fixture_api_id: number
          grid_position: string | null
          id: number
          is_substitute: boolean | null
          minutes_played: number | null
          player_api_id: number
          player_name: string | null
          position: string | null
          team_api_id: number
        }
        Insert: {
          created_at?: string | null
          fixture_api_id: number
          grid_position?: string | null
          id?: number
          is_substitute?: boolean | null
          minutes_played?: number | null
          player_api_id: number
          player_name?: string | null
          position?: string | null
          team_api_id: number
        }
        Update: {
          created_at?: string | null
          fixture_api_id?: number
          grid_position?: string | null
          id?: number
          is_substitute?: boolean | null
          minutes_played?: number | null
          player_api_id?: number
          player_name?: string | null
          position?: string | null
          team_api_id?: number
        }
        Relationships: []
      }
      match_team_stats: {
        Row: {
          blocked_shots: number | null
          corners: number | null
          created_at: string | null
          expected_goals: number | null
          fixture_api_id: number
          fouls: number | null
          id: number
          offsides: number | null
          passes_accurate: number | null
          passes_pct: number | null
          passes_total: number | null
          possession: number | null
          red_cards: number | null
          shots_off_target: number | null
          shots_on_target: number | null
          shots_total: number | null
          team_api_id: number
          yellow_cards: number | null
        }
        Insert: {
          blocked_shots?: number | null
          corners?: number | null
          created_at?: string | null
          expected_goals?: number | null
          fixture_api_id: number
          fouls?: number | null
          id?: number
          offsides?: number | null
          passes_accurate?: number | null
          passes_pct?: number | null
          passes_total?: number | null
          possession?: number | null
          red_cards?: number | null
          shots_off_target?: number | null
          shots_on_target?: number | null
          shots_total?: number | null
          team_api_id: number
          yellow_cards?: number | null
        }
        Update: {
          blocked_shots?: number | null
          corners?: number | null
          created_at?: string | null
          expected_goals?: number | null
          fixture_api_id?: number
          fouls?: number | null
          id?: number
          offsides?: number | null
          passes_accurate?: number | null
          passes_pct?: number | null
          passes_total?: number | null
          possession?: number | null
          red_cards?: number | null
          shots_off_target?: number | null
          shots_on_target?: number | null
          shots_total?: number | null
          team_api_id?: number
          yellow_cards?: number | null
        }
        Relationships: []
      }
      ml_models: {
        Row: {
          accuracy: number | null
          brier_score: number | null
          f1_score: number | null
          feature_importance: Json | null
          feature_names: string[] | null
          id: number
          is_active: boolean | null
          log_loss_val: number | null
          model_name: string
          model_params: Json | null
          model_type: string
          model_weights: string | null
          target: string
          trained_at: string | null
          training_samples: number | null
        }
        Insert: {
          accuracy?: number | null
          brier_score?: number | null
          f1_score?: number | null
          feature_importance?: Json | null
          feature_names?: string[] | null
          id?: number
          is_active?: boolean | null
          log_loss_val?: number | null
          model_name: string
          model_params?: Json | null
          model_type: string
          model_weights?: string | null
          target: string
          trained_at?: string | null
          training_samples?: number | null
        }
        Update: {
          accuracy?: number | null
          brier_score?: number | null
          f1_score?: number | null
          feature_importance?: Json | null
          feature_names?: string[] | null
          id?: number
          is_active?: boolean | null
          log_loss_val?: number | null
          model_name?: string
          model_params?: Json | null
          model_type?: string
          model_weights?: string | null
          target?: string
          trained_at?: string | null
          training_samples?: number | null
        }
        Relationships: []
      }
      nhl_daily_analysis: {
        Row: {
          analyse_ia: string | null
          analysis_date: string
          cote: number | null
          created_at: string | null
          id: number
          joueur: string | null
          market: string | null
          match: string | null
          pari: string | null
          proba_predite: number | null
          resultat: string | null
          score_reel: string | null
        }
        Insert: {
          analyse_ia?: string | null
          analysis_date: string
          cote?: number | null
          created_at?: string | null
          id?: number
          joueur?: string | null
          market?: string | null
          match?: string | null
          pari?: string | null
          proba_predite?: number | null
          resultat?: string | null
          score_reel?: string | null
        }
        Update: {
          analyse_ia?: string | null
          analysis_date?: string
          cote?: number | null
          created_at?: string | null
          id?: number
          joueur?: string | null
          market?: string | null
          match?: string | null
          pari?: string | null
          proba_predite?: number | null
          resultat?: string | null
          score_reel?: string | null
        }
        Relationships: []
      }
      nhl_daily_performance: {
        Row: {
          accuracy: number | null
          assist_accuracy: number | null
          assist_bets: number | null
          assist_wins: number | null
          avg_odds: number | null
          created_at: string | null
          date: string
          goal_accuracy: number | null
          goal_bets: number | null
          goal_wins: number | null
          id: number
          losses: number | null
          point_accuracy: number | null
          point_bets: number | null
          point_wins: number | null
          roi: number | null
          shot_accuracy: number | null
          shot_bets: number | null
          shot_wins: number | null
          total_bets: number | null
          winner_accuracy: number | null
          winner_bets: number | null
          winner_wins: number | null
          wins: number | null
        }
        Insert: {
          accuracy?: number | null
          assist_accuracy?: number | null
          assist_bets?: number | null
          assist_wins?: number | null
          avg_odds?: number | null
          created_at?: string | null
          date: string
          goal_accuracy?: number | null
          goal_bets?: number | null
          goal_wins?: number | null
          id?: number
          losses?: number | null
          point_accuracy?: number | null
          point_bets?: number | null
          point_wins?: number | null
          roi?: number | null
          shot_accuracy?: number | null
          shot_bets?: number | null
          shot_wins?: number | null
          total_bets?: number | null
          winner_accuracy?: number | null
          winner_bets?: number | null
          winner_wins?: number | null
          wins?: number | null
        }
        Update: {
          accuracy?: number | null
          assist_accuracy?: number | null
          assist_bets?: number | null
          assist_wins?: number | null
          avg_odds?: number | null
          created_at?: string | null
          date?: string
          goal_accuracy?: number | null
          goal_bets?: number | null
          goal_wins?: number | null
          id?: number
          losses?: number | null
          point_accuracy?: number | null
          point_bets?: number | null
          point_wins?: number | null
          roi?: number | null
          shot_accuracy?: number | null
          shot_bets?: number | null
          shot_wins?: number | null
          total_bets?: number | null
          winner_accuracy?: number | null
          winner_bets?: number | null
          winner_wins?: number | null
          wins?: number | null
        }
        Relationships: []
      }
      nhl_data_lake: {
        Row: {
          algo_score_goal: number | null
          algo_score_shot: number | null
          date: string
          id: number
          is_home: number | null
          opp: string | null
          player_id: string
          player_name: string | null
          python_prob: number | null
          python_vol: number | null
          result_goal: string | null
          result_shot: string | null
          team: string | null
          ts: string | null
        }
        Insert: {
          algo_score_goal?: number | null
          algo_score_shot?: number | null
          date: string
          id?: number
          is_home?: number | null
          opp?: string | null
          player_id: string
          player_name?: string | null
          python_prob?: number | null
          python_vol?: number | null
          result_goal?: string | null
          result_shot?: string | null
          team?: string | null
          ts?: string | null
        }
        Update: {
          algo_score_goal?: number | null
          algo_score_shot?: number | null
          date?: string
          id?: number
          is_home?: number | null
          opp?: string | null
          player_id?: string
          player_name?: string | null
          python_prob?: number | null
          python_vol?: number | null
          result_goal?: string | null
          result_shot?: string | null
          team?: string | null
          ts?: string | null
        }
        Relationships: []
      }
      nhl_fixtures: {
        Row: {
          analysis_text: string | null
          api_fixture_id: number
          away_score: number | null
          away_team: string | null
          confidence_score: number | null
          created_at: string | null
          date: string
          home_score: number | null
          home_team: string | null
          id: number
          odds_json: Json | null
          predictions_json: Json | null
          recommended_bet: string | null
          round: string | null
          season: number | null
          stats_json: Json | null
          status: string | null
          updated_at: string | null
          venue: string | null
        }
        Insert: {
          analysis_text?: string | null
          api_fixture_id: number
          away_score?: number | null
          away_team?: string | null
          confidence_score?: number | null
          created_at?: string | null
          date: string
          home_score?: number | null
          home_team?: string | null
          id?: number
          odds_json?: Json | null
          predictions_json?: Json | null
          recommended_bet?: string | null
          round?: string | null
          season?: number | null
          stats_json?: Json | null
          status?: string | null
          updated_at?: string | null
          venue?: string | null
        }
        Update: {
          analysis_text?: string | null
          api_fixture_id?: number
          away_score?: number | null
          away_team?: string | null
          confidence_score?: number | null
          created_at?: string | null
          date?: string
          home_score?: number | null
          home_team?: string | null
          id?: number
          odds_json?: Json | null
          predictions_json?: Json | null
          recommended_bet?: string | null
          round?: string | null
          season?: number | null
          stats_json?: Json | null
          status?: string | null
          updated_at?: string | null
          venue?: string | null
        }
        Relationships: []
      }
      nhl_ml_training_history: {
        Row: {
          accuracy: number | null
          brier_score: number | null
          cv_auc_mean: number | null
          cv_auc_std: number | null
          f1_score: number | null
          features_used: string | null
          id: number
          log_loss: number | null
          market: string
          n_features: number | null
          n_samples: number | null
          roc_auc: number | null
          top_features: string | null
          training_date: string | null
        }
        Insert: {
          accuracy?: number | null
          brier_score?: number | null
          cv_auc_mean?: number | null
          cv_auc_std?: number | null
          f1_score?: number | null
          features_used?: string | null
          id?: number
          log_loss?: number | null
          market: string
          n_features?: number | null
          n_samples?: number | null
          roc_auc?: number | null
          top_features?: string | null
          training_date?: string | null
        }
        Update: {
          accuracy?: number | null
          brier_score?: number | null
          cv_auc_mean?: number | null
          cv_auc_std?: number | null
          f1_score?: number | null
          features_used?: string | null
          id?: number
          log_loss?: number | null
          market?: string
          n_features?: number | null
          n_samples?: number | null
          roc_auc?: number | null
          top_features?: string | null
          training_date?: string | null
        }
        Relationships: []
      }
      nhl_suivi_algo_clean: {
        Row: {
          analyse_postmortem: string | null
          cote: number | null
          created_at: string | null
          date: string
          diagnostic_ia: string | null
          id: number
          id_ref: string | null
          joueur: string | null
          match: string | null
          pari: string | null
          proba_predite: number | null
          python_prob: number | null
          résultat: string | null
          score_reel: string | null
          type: string | null
        }
        Insert: {
          analyse_postmortem?: string | null
          cote?: number | null
          created_at?: string | null
          date: string
          diagnostic_ia?: string | null
          id?: number
          id_ref?: string | null
          joueur?: string | null
          match?: string | null
          pari?: string | null
          proba_predite?: number | null
          python_prob?: number | null
          résultat?: string | null
          score_reel?: string | null
          type?: string | null
        }
        Update: {
          analyse_postmortem?: string | null
          cote?: number | null
          created_at?: string | null
          date?: string
          diagnostic_ia?: string | null
          id?: number
          id_ref?: string | null
          joueur?: string | null
          match?: string | null
          pari?: string | null
          proba_predite?: number | null
          python_prob?: number | null
          résultat?: string | null
          score_reel?: string | null
          type?: string | null
        }
        Relationships: []
      }
      player_season_stats: {
        Row: {
          appearances: number | null
          assists: number | null
          clean_sheets: number | null
          created_at: string | null
          dribbles_attempts: number | null
          dribbles_success: number | null
          duels_total: number | null
          duels_won: number | null
          fouls_committed: number | null
          fouls_drawn: number | null
          goals: number | null
          goals_conceded: number | null
          id: number
          interceptions: number | null
          league_id: number | null
          minutes_played: number | null
          passes_accuracy: number | null
          passes_key: number | null
          passes_total: number | null
          penalty_missed: number | null
          penalty_saved: number | null
          penalty_scored: number | null
          player_api_id: number
          rating: number | null
          red_cards: number | null
          saves: number | null
          season: number
          shots_on_target: number | null
          shots_total: number | null
          tackles_total: number | null
          team_api_id: number | null
          updated_at: string | null
          yellow_cards: number | null
        }
        Insert: {
          appearances?: number | null
          assists?: number | null
          clean_sheets?: number | null
          created_at?: string | null
          dribbles_attempts?: number | null
          dribbles_success?: number | null
          duels_total?: number | null
          duels_won?: number | null
          fouls_committed?: number | null
          fouls_drawn?: number | null
          goals?: number | null
          goals_conceded?: number | null
          id?: number
          interceptions?: number | null
          league_id?: number | null
          minutes_played?: number | null
          passes_accuracy?: number | null
          passes_key?: number | null
          passes_total?: number | null
          penalty_missed?: number | null
          penalty_saved?: number | null
          penalty_scored?: number | null
          player_api_id: number
          rating?: number | null
          red_cards?: number | null
          saves?: number | null
          season: number
          shots_on_target?: number | null
          shots_total?: number | null
          tackles_total?: number | null
          team_api_id?: number | null
          updated_at?: string | null
          yellow_cards?: number | null
        }
        Update: {
          appearances?: number | null
          assists?: number | null
          clean_sheets?: number | null
          created_at?: string | null
          dribbles_attempts?: number | null
          dribbles_success?: number | null
          duels_total?: number | null
          duels_won?: number | null
          fouls_committed?: number | null
          fouls_drawn?: number | null
          goals?: number | null
          goals_conceded?: number | null
          id?: number
          interceptions?: number | null
          league_id?: number | null
          minutes_played?: number | null
          passes_accuracy?: number | null
          passes_key?: number | null
          passes_total?: number | null
          penalty_missed?: number | null
          penalty_saved?: number | null
          penalty_scored?: number | null
          player_api_id?: number
          rating?: number | null
          red_cards?: number | null
          saves?: number | null
          season?: number
          shots_on_target?: number | null
          shots_total?: number | null
          tackles_total?: number | null
          team_api_id?: number | null
          updated_at?: string | null
          yellow_cards?: number | null
        }
        Relationships: []
      }
      players: {
        Row: {
          age: number | null
          api_id: number
          created_at: string | null
          height_cm: number | null
          id: number
          is_injured: boolean | null
          name: string
          nationality: string | null
          photo_url: string | null
          position: string | null
          team_api_id: number | null
          updated_at: string | null
          weight_kg: number | null
        }
        Insert: {
          age?: number | null
          api_id: number
          created_at?: string | null
          height_cm?: number | null
          id?: number
          is_injured?: boolean | null
          name: string
          nationality?: string | null
          photo_url?: string | null
          position?: string | null
          team_api_id?: number | null
          updated_at?: string | null
          weight_kg?: number | null
        }
        Update: {
          age?: number | null
          api_id?: number
          created_at?: string | null
          height_cm?: number | null
          id?: number
          is_injured?: boolean | null
          name?: string
          nationality?: string | null
          photo_url?: string | null
          position?: string | null
          team_api_id?: number | null
          updated_at?: string | null
          weight_kg?: number | null
        }
        Relationships: []
      }
      prediction_results: {
        Row: {
          actual_away_goals: number | null
          actual_btts: boolean | null
          actual_correct_score: boolean | null
          actual_had_penalty: boolean | null
          actual_home_goals: number | null
          actual_over_05: boolean | null
          actual_over_15: boolean | null
          actual_over_25: boolean | null
          actual_result: string | null
          actual_scorers: string[] | null
          brier_score_1x2: number | null
          btts_ok: boolean | null
          correct_score_ok: boolean | null
          created_at: string | null
          fixture_id: number
          id: number
          league_id: number | null
          log_loss: number | null
          model_version: string | null
          over_05_ok: boolean | null
          over_15_ok: boolean | null
          over_25_ok: boolean | null
          penalty_ok: boolean | null
          post_analysis: string | null
          pred_away: number | null
          pred_btts: number | null
          pred_confidence: number | null
          pred_correct_score: string | null
          pred_draw: number | null
          pred_home: number | null
          pred_likely_scorer: string | null
          pred_over_05: number | null
          pred_over_15: number | null
          pred_over_25: number | null
          pred_penalty: number | null
          pred_recommended: string | null
          prediction_id: number | null
          recommended_bet_ok: boolean | null
          result_1x2_ok: boolean | null
          scorer_ok: boolean | null
          season: number | null
        }
        Insert: {
          actual_away_goals?: number | null
          actual_btts?: boolean | null
          actual_correct_score?: boolean | null
          actual_had_penalty?: boolean | null
          actual_home_goals?: number | null
          actual_over_05?: boolean | null
          actual_over_15?: boolean | null
          actual_over_25?: boolean | null
          actual_result?: string | null
          actual_scorers?: string[] | null
          brier_score_1x2?: number | null
          btts_ok?: boolean | null
          correct_score_ok?: boolean | null
          created_at?: string | null
          fixture_id: number
          id?: number
          league_id?: number | null
          log_loss?: number | null
          model_version?: string | null
          over_05_ok?: boolean | null
          over_15_ok?: boolean | null
          over_25_ok?: boolean | null
          penalty_ok?: boolean | null
          post_analysis?: string | null
          pred_away?: number | null
          pred_btts?: number | null
          pred_confidence?: number | null
          pred_correct_score?: string | null
          pred_draw?: number | null
          pred_home?: number | null
          pred_likely_scorer?: string | null
          pred_over_05?: number | null
          pred_over_15?: number | null
          pred_over_25?: number | null
          pred_penalty?: number | null
          pred_recommended?: string | null
          prediction_id?: number | null
          recommended_bet_ok?: boolean | null
          result_1x2_ok?: boolean | null
          scorer_ok?: boolean | null
          season?: number | null
        }
        Update: {
          actual_away_goals?: number | null
          actual_btts?: boolean | null
          actual_correct_score?: boolean | null
          actual_had_penalty?: boolean | null
          actual_home_goals?: number | null
          actual_over_05?: boolean | null
          actual_over_15?: boolean | null
          actual_over_25?: boolean | null
          actual_result?: string | null
          actual_scorers?: string[] | null
          brier_score_1x2?: number | null
          btts_ok?: boolean | null
          correct_score_ok?: boolean | null
          created_at?: string | null
          fixture_id?: number
          id?: number
          league_id?: number | null
          log_loss?: number | null
          model_version?: string | null
          over_05_ok?: boolean | null
          over_15_ok?: boolean | null
          over_25_ok?: boolean | null
          penalty_ok?: boolean | null
          post_analysis?: string | null
          pred_away?: number | null
          pred_btts?: number | null
          pred_confidence?: number | null
          pred_correct_score?: string | null
          pred_draw?: number | null
          pred_home?: number | null
          pred_likely_scorer?: string | null
          pred_over_05?: number | null
          pred_over_15?: number | null
          pred_over_25?: number | null
          pred_penalty?: number | null
          pred_recommended?: string | null
          prediction_id?: number | null
          recommended_bet_ok?: boolean | null
          result_1x2_ok?: boolean | null
          scorer_ok?: boolean | null
          season?: number | null
        }
        Relationships: []
      }
      predictions: {
        Row: {
          analysis_text: string | null
          confidence_score: number | null
          correct_score: string | null
          created_at: string | null
          fixture_id: string | null
          id: string
          is_value_bet: boolean | null
          likely_scorer: string | null
          likely_scorer_proba: number | null
          model_version: string | null
          proba_away: number | null
          proba_btts: number | null
          proba_correct_score: number | null
          proba_dc_12: number | null
          proba_dc_1x: number | null
          proba_dc_x2: number | null
          proba_draw: number | null
          proba_home: number | null
          proba_over_05: number | null
          proba_over_15: number | null
          proba_over_2_5: number | null
          proba_over_35: number | null
          proba_penalty: number | null
          recommended_bet: string | null
          stats_json: Json | null
        }
        Insert: {
          analysis_text?: string | null
          confidence_score?: number | null
          correct_score?: string | null
          created_at?: string | null
          fixture_id?: string | null
          id?: string
          is_value_bet?: boolean | null
          likely_scorer?: string | null
          likely_scorer_proba?: number | null
          model_version?: string | null
          proba_away?: number | null
          proba_btts?: number | null
          proba_correct_score?: number | null
          proba_dc_12?: number | null
          proba_dc_1x?: number | null
          proba_dc_x2?: number | null
          proba_draw?: number | null
          proba_home?: number | null
          proba_over_05?: number | null
          proba_over_15?: number | null
          proba_over_2_5?: number | null
          proba_over_35?: number | null
          proba_penalty?: number | null
          recommended_bet?: string | null
          stats_json?: Json | null
        }
        Update: {
          analysis_text?: string | null
          confidence_score?: number | null
          correct_score?: string | null
          created_at?: string | null
          fixture_id?: string | null
          id?: string
          is_value_bet?: boolean | null
          likely_scorer?: string | null
          likely_scorer_proba?: number | null
          model_version?: string | null
          proba_away?: number | null
          proba_btts?: number | null
          proba_correct_score?: number | null
          proba_dc_12?: number | null
          proba_dc_1x?: number | null
          proba_dc_x2?: number | null
          proba_draw?: number | null
          proba_home?: number | null
          proba_over_05?: number | null
          proba_over_15?: number | null
          proba_over_2_5?: number | null
          proba_over_35?: number | null
          proba_penalty?: number | null
          recommended_bet?: string | null
          stats_json?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "predictions_fixture_id_fkey"
            columns: ["fixture_id"]
            isOneToOne: false
            referencedRelation: "fixtures"
            referencedColumns: ["id"]
          },
        ]
      }
      processed_events: {
        Row: {
          created_at: string | null
          id: string
          source: string
        }
        Insert: {
          created_at?: string | null
          id: string
          source: string
        }
        Update: {
          created_at?: string | null
          id?: string
          source?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          created_at: string
          email: string | null
          id: string
          role: string | null
          stripe_customer_id: string | null
          subscription_status: string | null
        }
        Insert: {
          created_at?: string
          email?: string | null
          id: string
          role?: string | null
          stripe_customer_id?: string | null
          subscription_status?: string | null
        }
        Update: {
          created_at?: string
          email?: string | null
          id?: string
          role?: string | null
          stripe_customer_id?: string | null
          subscription_status?: string | null
        }
        Relationships: []
      }
      referees: {
        Row: {
          avg_fouls_per_match: number | null
          avg_penalties_per_match: number | null
          avg_reds_per_match: number | null
          avg_yellows_per_match: number | null
          id: number
          matches_officiated: number | null
          name: string
          total_fouls: number | null
          total_penalties: number | null
          total_reds: number | null
          total_yellows: number | null
          updated_at: string | null
        }
        Insert: {
          avg_fouls_per_match?: number | null
          avg_penalties_per_match?: number | null
          avg_reds_per_match?: number | null
          avg_yellows_per_match?: number | null
          id?: number
          matches_officiated?: number | null
          name: string
          total_fouls?: number | null
          total_penalties?: number | null
          total_reds?: number | null
          total_yellows?: number | null
          updated_at?: string | null
        }
        Update: {
          avg_fouls_per_match?: number | null
          avg_penalties_per_match?: number | null
          avg_reds_per_match?: number | null
          avg_yellows_per_match?: number | null
          id?: number
          matches_officiated?: number | null
          name?: string
          total_fouls?: number | null
          total_penalties?: number | null
          total_reds?: number | null
          total_yellows?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      team_elo: {
        Row: {
          elo_rating: number | null
          id: number
          last_updated: string | null
          league_id: number | null
          team_api_id: number
          team_name: string | null
        }
        Insert: {
          elo_rating?: number | null
          id?: number
          last_updated?: string | null
          league_id?: number | null
          team_api_id: number
          team_name?: string | null
        }
        Update: {
          elo_rating?: number | null
          id?: number
          last_updated?: string | null
          league_id?: number | null
          team_api_id?: number
          team_name?: string | null
        }
        Relationships: []
      }
      team_standings: {
        Row: {
          away_draws: number | null
          away_goals_against: number | null
          away_goals_for: number | null
          away_losses: number | null
          away_played: number | null
          away_wins: number | null
          draws: number | null
          form: string | null
          goal_diff: number | null
          goals_against: number | null
          goals_for: number | null
          home_draws: number | null
          home_goals_against: number | null
          home_goals_for: number | null
          home_losses: number | null
          home_played: number | null
          home_wins: number | null
          id: number
          league_id: number
          losses: number | null
          played: number | null
          points: number | null
          rank: number | null
          season: number
          team_api_id: number
          updated_at: string | null
          wins: number | null
        }
        Insert: {
          away_draws?: number | null
          away_goals_against?: number | null
          away_goals_for?: number | null
          away_losses?: number | null
          away_played?: number | null
          away_wins?: number | null
          draws?: number | null
          form?: string | null
          goal_diff?: number | null
          goals_against?: number | null
          goals_for?: number | null
          home_draws?: number | null
          home_goals_against?: number | null
          home_goals_for?: number | null
          home_losses?: number | null
          home_played?: number | null
          home_wins?: number | null
          id?: number
          league_id: number
          losses?: number | null
          played?: number | null
          points?: number | null
          rank?: number | null
          season: number
          team_api_id: number
          updated_at?: string | null
          wins?: number | null
        }
        Update: {
          away_draws?: number | null
          away_goals_against?: number | null
          away_goals_for?: number | null
          away_losses?: number | null
          away_played?: number | null
          away_wins?: number | null
          draws?: number | null
          form?: string | null
          goal_diff?: number | null
          goals_against?: number | null
          goals_for?: number | null
          home_draws?: number | null
          home_goals_against?: number | null
          home_goals_for?: number | null
          home_losses?: number | null
          home_played?: number | null
          home_wins?: number | null
          id?: number
          league_id?: number
          losses?: number | null
          played?: number | null
          points?: number | null
          rank?: number | null
          season?: number
          team_api_id?: number
          updated_at?: string | null
          wins?: number | null
        }
        Relationships: []
      }
      teams: {
        Row: {
          api_id: number
          country: string | null
          created_at: string | null
          id: number
          league_id: number | null
          logo_url: string | null
          name: string
          updated_at: string | null
          venue_city: string | null
          venue_name: string | null
        }
        Insert: {
          api_id: number
          country?: string | null
          created_at?: string | null
          id?: number
          league_id?: number | null
          logo_url?: string | null
          name: string
          updated_at?: string | null
          venue_city?: string | null
          venue_name?: string | null
        }
        Update: {
          api_id?: number
          country?: string | null
          created_at?: string | null
          id?: number
          league_id?: number | null
          logo_url?: string | null
          name?: string
          updated_at?: string | null
          venue_city?: string | null
          venue_name?: string | null
        }
        Relationships: []
      }
      ticket_picks: {
        Row: {
          away_team: string | null
          bet_type: string
          confidence: number | null
          created_at: string | null
          evaluated_at: string | null
          fixture_id: number
          home_team: string | null
          id: number
          is_won: boolean | null
          match_date: string | null
          odds_est: number | null
          ticket_date: string
          ticket_type: string
        }
        Insert: {
          away_team?: string | null
          bet_type: string
          confidence?: number | null
          created_at?: string | null
          evaluated_at?: string | null
          fixture_id: number
          home_team?: string | null
          id?: number
          is_won?: boolean | null
          match_date?: string | null
          odds_est?: number | null
          ticket_date: string
          ticket_type: string
        }
        Update: {
          away_team?: string | null
          bet_type?: string
          confidence?: number | null
          created_at?: string | null
          evaluated_at?: string | null
          fixture_id?: number
          home_team?: string | null
          id?: number
          is_won?: boolean | null
          match_date?: string | null
          odds_est?: number | null
          ticket_date?: string
          ticket_type?: string
        }
        Relationships: []
      }
      training_data: {
        Row: {
          away_attack_strength: number | null
          away_clean_sheet_rate: number | null
          away_congestion_30d: number | null
          away_defense_strength: number | null
          away_elo: number | null
          away_fatigue_index: number | null
          away_form: number | null
          away_goal_diff_avg: number | null
          away_goals: number | null
          away_injury_attack_factor: number | null
          away_injury_count: number | null
          away_injury_defense_factor: number | null
          away_momentum: number | null
          away_rest_days: number | null
          away_result_variance: number | null
          away_stakes: number | null
          btts: boolean | null
          created_at: string | null
          elo_diff: number | null
          fixture_api_id: number
          h2h_home_winrate: number | null
          h2h_total_matches: number | null
          home_attack_strength: number | null
          home_clean_sheet_rate: number | null
          home_congestion_30d: number | null
          home_defense_strength: number | null
          home_elo: number | null
          home_fatigue_index: number | null
          home_form: number | null
          home_goal_diff_avg: number | null
          home_goals: number | null
          home_injury_attack_factor: number | null
          home_injury_count: number | null
          home_injury_defense_factor: number | null
          home_momentum: number | null
          home_rest_days: number | null
          home_result_variance: number | null
          home_stakes: number | null
          id: number
          league_avg_away_goals: number | null
          league_avg_home_goals: number | null
          league_id: number | null
          market_away_prob: number | null
          market_draw_prob: number | null
          market_home_prob: number | null
          match_date: string | null
          over_05: boolean | null
          over_15: boolean | null
          over_25: boolean | null
          over_35: boolean | null
          referee_penalty_bias: number | null
          result: string | null
          season: number | null
          total_goals: number | null
          xg_away: number | null
          xg_home: number | null
        }
        Insert: {
          away_attack_strength?: number | null
          away_clean_sheet_rate?: number | null
          away_congestion_30d?: number | null
          away_defense_strength?: number | null
          away_elo?: number | null
          away_fatigue_index?: number | null
          away_form?: number | null
          away_goal_diff_avg?: number | null
          away_goals?: number | null
          away_injury_attack_factor?: number | null
          away_injury_count?: number | null
          away_injury_defense_factor?: number | null
          away_momentum?: number | null
          away_rest_days?: number | null
          away_result_variance?: number | null
          away_stakes?: number | null
          btts?: boolean | null
          created_at?: string | null
          elo_diff?: number | null
          fixture_api_id: number
          h2h_home_winrate?: number | null
          h2h_total_matches?: number | null
          home_attack_strength?: number | null
          home_clean_sheet_rate?: number | null
          home_congestion_30d?: number | null
          home_defense_strength?: number | null
          home_elo?: number | null
          home_fatigue_index?: number | null
          home_form?: number | null
          home_goal_diff_avg?: number | null
          home_goals?: number | null
          home_injury_attack_factor?: number | null
          home_injury_count?: number | null
          home_injury_defense_factor?: number | null
          home_momentum?: number | null
          home_rest_days?: number | null
          home_result_variance?: number | null
          home_stakes?: number | null
          id?: number
          league_avg_away_goals?: number | null
          league_avg_home_goals?: number | null
          league_id?: number | null
          market_away_prob?: number | null
          market_draw_prob?: number | null
          market_home_prob?: number | null
          match_date?: string | null
          over_05?: boolean | null
          over_15?: boolean | null
          over_25?: boolean | null
          over_35?: boolean | null
          referee_penalty_bias?: number | null
          result?: string | null
          season?: number | null
          total_goals?: number | null
          xg_away?: number | null
          xg_home?: number | null
        }
        Update: {
          away_attack_strength?: number | null
          away_clean_sheet_rate?: number | null
          away_congestion_30d?: number | null
          away_defense_strength?: number | null
          away_elo?: number | null
          away_fatigue_index?: number | null
          away_form?: number | null
          away_goal_diff_avg?: number | null
          away_goals?: number | null
          away_injury_attack_factor?: number | null
          away_injury_count?: number | null
          away_injury_defense_factor?: number | null
          away_momentum?: number | null
          away_rest_days?: number | null
          away_result_variance?: number | null
          away_stakes?: number | null
          btts?: boolean | null
          created_at?: string | null
          elo_diff?: number | null
          fixture_api_id?: number
          h2h_home_winrate?: number | null
          h2h_total_matches?: number | null
          home_attack_strength?: number | null
          home_clean_sheet_rate?: number | null
          home_congestion_30d?: number | null
          home_defense_strength?: number | null
          home_elo?: number | null
          home_fatigue_index?: number | null
          home_form?: number | null
          home_goal_diff_avg?: number | null
          home_goals?: number | null
          home_injury_attack_factor?: number | null
          home_injury_count?: number | null
          home_injury_defense_factor?: number | null
          home_momentum?: number | null
          home_rest_days?: number | null
          home_result_variance?: number | null
          home_stakes?: number | null
          id?: number
          league_avg_away_goals?: number | null
          league_avg_home_goals?: number | null
          league_id?: number | null
          market_away_prob?: number | null
          market_draw_prob?: number | null
          market_home_prob?: number | null
          match_date?: string | null
          over_05?: boolean | null
          over_15?: boolean | null
          over_25?: boolean | null
          over_35?: boolean | null
          referee_penalty_bias?: number | null
          result?: string | null
          season?: number | null
          total_goals?: number | null
          xg_away?: number | null
          xg_home?: number | null
        }
        Relationships: []
      }
    }
    Views: {
      nhl_v_ml_latest: {
        Row: {
          accuracy: number | null
          brier_score: number | null
          cv_auc_mean: number | null
          market: string | null
          n_features: number | null
          n_samples: number | null
          roc_auc: number | null
          top_features: string | null
          training_date: string | null
        }
        Relationships: []
      }
      nhl_v_performance_by_market: {
        Row: {
          accuracy_pct: number | null
          avg_odds: number | null
          market: string | null
          total: number | null
          wins: number | null
        }
        Relationships: []
      }
      nhl_v_performance_summary: {
        Row: {
          accuracy_pct: number | null
          avg_odds: number | null
          first_date: string | null
          last_date: string | null
          losses: number | null
          n_dates: number | null
          total_bets: number | null
          wins: number | null
        }
        Relationships: []
      }
      ticket_results_view: {
        Row: {
          avg_confidence: number | null
          combined_odds: number | null
          evaluated_picks: number | null
          lost_picks: number | null
          ticket_date: string | null
          ticket_type: string | null
          ticket_won: boolean | null
          total_picks: number | null
          won_picks: number | null
        }
        Relationships: []
      }
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
