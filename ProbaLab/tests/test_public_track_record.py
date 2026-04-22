"""Tests for the public live track-record endpoint (Lot 2 · T01)."""

from __future__ import annotations

from unittest.mock import MagicMock

from api.routers.v2.public_track_record import _CACHE, get_track_record_live


def test_track_record_live_shape(mock_supabase):
    """The endpoint must expose the expected shape with 5 top-level keys and a curve list."""
    _CACHE.clear()  # the route caches 5 min in-process; isolate the test
    mock_supabase.execute.side_effect = [
        MagicMock(data=[{"clv_pct": 3.1}, {"clv_pct": 4.2}]),  # model_health_log
        MagicMock(data=[{"roi_pct": 12.5, "n_bets": 140}]),    # best_bets aggregated
        MagicMock(data=[{"brier": 0.201, "n": 500}]),          # predictions_results
        MagicMock(data=[{"safe_rate": 0.68, "n": 90}]),        # safe picks 90d
        MagicMock(
            data=[
                {"d": "2026-01-22", "cum_roi": 0.0},
                {"d": "2026-04-21", "cum_roi": 12.5},
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
    assert out["roi_curve_90d"][0]["date"] == "2026-01-22"
