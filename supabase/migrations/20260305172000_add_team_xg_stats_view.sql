-- Create a materialised view or normal view to calculate team xG stats
-- This view aggregates xG_for and xG_against for each team in the current season
CREATE OR REPLACE VIEW public.team_xg_stats AS
SELECT
    mts.team_api_id,
    f.league_id,
    l.season,
    COUNT(mts.fixture_api_id) AS matches_played,
    SUM(mts.expected_goals) AS xg_for_total,
    SUM(mts_opp.expected_goals) AS xg_against_total,
    AVG(mts.expected_goals) AS xg_for_avg,
    AVG(mts_opp.expected_goals) AS xg_against_avg
FROM match_team_stats mts
JOIN fixtures f ON f.api_fixture_id = mts.fixture_api_id
JOIN leagues l ON l.api_id = f.league_id
-- Join to get the opponent's stats
LEFT JOIN match_team_stats mts_opp ON mts_opp.fixture_api_id = mts.fixture_api_id AND mts_opp.team_api_id != mts.team_api_id
WHERE f.status IN ('FT', 'AET', 'PEN')
GROUP BY mts.team_api_id, f.league_id, l.season;

-- Grant permissions
GRANT SELECT ON public.team_xg_stats TO authenticated, anon;
