"""Tests pour GET /api/value-bets?date=YYYY-MM-DD."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from api import main

    return TestClient(main.app)


def test_value_bets_returns_empty_when_no_predictions(client, monkeypatch):
    from api.routers import value_bets

    monkeypatch.setattr(value_bets, "_load_day_matches", lambda d: [])

    resp = client.get("/api/value-bets?date=2026-04-20")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"date": "2026-04-20", "matches": []}


def test_value_bets_returns_shape_from_spec(client, monkeypatch):
    from api.routers import value_bets

    match = {
        "fixture_id": "fx123",
        "sport": "football",
        "league": "Ligue 1",
        "home_team": "PSG",
        "away_team": "Marseille",
        "kickoff": "2026-04-20T19:00:00Z",
        "probabilities": {
            "1x2": {"home": 62.3, "draw": 22.1, "away": 15.6},
        },
        "best_odds": {
            "1x2.home": {"bookmaker": "winamax", "odds": 1.48, "implied": 67.6},
            "1x2.draw": {"bookmaker": "betclic", "odds": 4.80, "implied": 20.8},
            "1x2.away": {"bookmaker": "unibet", "odds": 7.20, "implied": 13.9},
        },
        "value_bets": [
            {
                "market": "1x2",
                "selection": "draw",
                "proba_model": 22.1,
                "best_odds": 4.80,
                "bookmaker": "betclic",
                "edge_pct": 6.08,
                "kelly_fractional": 0.015,
            }
        ],
    }
    monkeypatch.setattr(value_bets, "_load_day_matches", lambda d: [match])

    resp = client.get("/api/value-bets?date=2026-04-20")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-04-20"
    assert len(body["matches"]) == 1
    m = body["matches"][0]
    assert m["fixture_id"] == "fx123"
    assert "probabilities" in m
    assert "best_odds" in m
    assert "value_bets" in m


def test_value_bets_rejects_bad_date_format(client):
    resp = client.get("/api/value-bets?date=not-a-date")
    assert resp.status_code == 422 or resp.status_code == 400


def test_value_bets_requires_date_param(client):
    resp = client.get("/api/value-bets")
    assert resp.status_code in (400, 422)
