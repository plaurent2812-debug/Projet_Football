"""Tests for the public live track-record endpoint (Lot 2 · T01).

Columns verified against real Supabase schema:
  model_health_log : clv_best_mean_30d, brier_30d, recorded_at
  best_bets        : result, odds, market, created_at
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.routers.v2.public_track_record import _CACHE, get_track_record_live


def test_track_record_live_shape(mock_supabase):
    """The endpoint must expose the expected shape with 5 top-level keys and a curve list."""
    _CACHE.clear()  # the route caches 5 min in-process; isolate the test

    # Query 1 : model_health_log CLV (clv_best_mean_30d, recorded_at)
    # Query 2 : model_health_log Brier (brier_30d, recorded_at)
    # Query 3 : best_bets 90d resolved (result, odds, market, created_at)
    mock_supabase.execute.side_effect = [
        MagicMock(data=[{"clv_best_mean_30d": 3.1}, {"clv_best_mean_30d": 4.2}]),
        MagicMock(data=[{"brier_30d": 0.201}, {"brier_30d": 0.198}]),
        MagicMock(
            data=[
                {
                    "result": "WIN",
                    "odds": 2.10,
                    "market": "safe_football",
                    "created_at": "2026-01-22T14:00:00Z",
                },
                {
                    "result": "LOSS",
                    "odds": 2.00,
                    "market": "safe_football",
                    "created_at": "2026-04-21T14:00:00Z",
                },
                {
                    "result": "WIN",
                    "odds": 1.95,
                    "market": "fun_football",
                    "created_at": "2026-04-21T18:00:00Z",
                },
            ]
        ),
    ]

    out = get_track_record_live.__wrapped__(request=MagicMock())

    assert set(out.keys()) == {
        "clv_30d",
        "roi_90d",
        "brier_30d",
        "safe_rate_90d",
        "roi_curve_90d",
    }
    assert isinstance(out["roi_curve_90d"], list)

    # CLV: avg(3.1, 4.2) = 3.65
    assert out["clv_30d"] == 3.65

    # Brier: avg(0.201, 0.198) = 0.2 (rounded to 3 digits)
    assert abs(out["brier_30d"] - 0.2) < 0.001

    # 3 resolved bets: staked=3, returned=2.10+1.95=4.05
    # roi_90d = (4.05 - 3) / 3 * 100 = 35.0
    assert abs(out["roi_90d"] - 35.0) < 0.1

    # safe_rate: 2 safe bets (WIN + LOSS), 1 win → 0.5
    assert out["safe_rate_90d"] == 0.5

    # ROI curve: 2 days
    assert len(out["roi_curve_90d"]) == 2
    assert out["roi_curve_90d"][0]["date"] == "2026-01-22"


def test_track_record_live_empty_tables(mock_supabase):
    """Empty tables must return zeros and an empty curve without raising exceptions."""
    _CACHE.clear()

    mock_supabase.execute.side_effect = [
        MagicMock(data=[]),  # model_health_log CLV — empty
        MagicMock(data=[]),  # model_health_log Brier — empty
        MagicMock(data=[]),  # best_bets — empty
    ]

    out = get_track_record_live.__wrapped__(request=MagicMock())

    assert out["clv_30d"] == 0.0
    assert out["roi_90d"] == 0.0
    assert out["brier_30d"] == 0.0
    assert out["safe_rate_90d"] == 0.0
    assert out["roi_curve_90d"] == []


def test_track_record_live_null_clv(mock_supabase):
    """NULL clv_best_mean_30d values must be skipped gracefully."""
    _CACHE.clear()

    mock_supabase.execute.side_effect = [
        MagicMock(data=[{"clv_best_mean_30d": None}, {"clv_best_mean_30d": 5.0}]),
        MagicMock(data=[]),
        MagicMock(data=[]),
    ]

    out = get_track_record_live.__wrapped__(request=MagicMock())
    assert out["clv_30d"] == 5.0
