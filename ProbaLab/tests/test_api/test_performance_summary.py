"""Contract test for GET /api/performance/summary.

The frontend hook `usePerformanceSummary` expects the following shape exactly:
    {
      roi30d:   {value: number, deltaVs7d: number},
      accuracy: {value: number, deltaVs7d: number},
      brier7d:  {value: number, deltaVs7d: number},
      bankroll: {value: number, currency: "EUR"},
    }

Schema drift = frontend crash, so this test pins the contract.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.routers import performance as _perf_router


@pytest.fixture(autouse=True)
def _reset_summary_cache():
    _perf_router._SUMMARY_CACHE.clear()
    yield
    _perf_router._SUMMARY_CACHE.clear()


def test_performance_summary_returns_expected_shape(client: TestClient):
    res = client.get("/api/performance/summary", params={"window": 30})
    assert res.status_code == 200, res.text
    body = res.json()

    for key in ("roi30d", "accuracy", "brier7d", "bankroll"):
        assert key in body, f"missing top-level key {key!r}"

    for key in ("roi30d", "accuracy", "brier7d"):
        assert "value" in body[key], f"{key}.value missing"
        assert "deltaVs7d" in body[key], f"{key}.deltaVs7d missing"
        assert isinstance(body[key]["value"], (int, float))
        assert isinstance(body[key]["deltaVs7d"], (int, float))

    assert isinstance(body["bankroll"]["value"], (int, float))
    assert body["bankroll"]["currency"] == "EUR"


def test_performance_summary_accepts_window_7_30_90(client: TestClient):
    for window in (7, 30, 90):
        res = client.get("/api/performance/summary", params={"window": window})
        assert res.status_code == 200, f"window={window} got {res.status_code}: {res.text}"


def test_performance_summary_rejects_invalid_window(client: TestClient):
    res = client.get("/api/performance/summary", params={"window": 500})
    assert res.status_code == 422


def test_performance_summary_returns_zeros_when_db_empty(client: TestClient, monkeypatch):
    """Even with no finished fixtures, the endpoint must return well-typed zeros,
    never 500 or a partial payload. This is what unblocks the landing when the
    DB is seeded from scratch (lesson 60)."""
    from api.routers import performance as perf_router

    def _empty(*_a, **_kw):
        return {
            "roi_value": 0.0,
            "roi_delta": 0.0,
            "accuracy_value": 0.0,
            "accuracy_delta": 0.0,
            "brier_value": 0.0,
            "brier_delta": 0.0,
            "bankroll_value": 0.0,
        }

    # Reset cache before testing (module-level state).
    perf_router._SUMMARY_CACHE.clear()
    monkeypatch.setattr(perf_router, "_compute_performance_summary", _empty)
    res = client.get("/api/performance/summary", params={"window": 30})
    assert res.status_code == 200
    body = res.json()
    assert body["roi30d"] == {"value": 0.0, "deltaVs7d": 0.0}
    assert body["bankroll"] == {"value": 0.0, "currency": "EUR"}


def test_performance_summary_rejects_window_15(client: TestClient):
    """Window must be one of 7, 30, 90 — not arbitrary values in [7, 90]."""
    res = client.get("/api/performance/summary", params={"window": 15})
    assert res.status_code == 422
