"""Tests pour odds_ingestor — client The Odds API Dev."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from src.fetchers.odds_ingestor import (
    OddsAPIQuotaExhausted,
    parse_odds_response,
    to_implied_prob,
)


def test_to_implied_prob_basic():
    assert to_implied_prob(2.0) == 0.5
    assert to_implied_prob(1.50) == pytest.approx(0.6667, abs=1e-3)


def test_to_implied_prob_rejects_sub_unity():
    with pytest.raises(ValueError):
        to_implied_prob(0.95)


def test_parse_1x2_response_returns_rows():
    """Sample 1X2 extrait de la doc v4 The Odds API."""
    sample = [
        {
            "id": "event_abc123",
            "sport_key": "soccer_france_ligue_one",
            "commence_time": "2026-04-20T19:00:00Z",
            "home_team": "Paris Saint-Germain",
            "away_team": "Olympique de Marseille",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-04-19T10:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Paris Saint-Germain", "price": 1.50},
                                {"name": "Olympique de Marseille", "price": 7.00},
                                {"name": "Draw", "price": 4.50},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(
        sample,
        sport="football",
        snapshot_type="opening",
        source_request_id="req-1",
    )
    assert len(rows) == 3
    # Row canonique : sport, fixture_id, bookmaker, market, selection, odds, implied_prob
    home_row = next(r for r in rows if r["selection"] == "home")
    assert home_row["bookmaker"] == "pinnacle"
    assert home_row["market"] == "1x2"
    assert home_row["odds"] == 1.50
    assert home_row["implied_prob"] == pytest.approx(0.6667, abs=1e-3)
    assert home_row["sport"] == "football"
    assert home_row["fixture_id"] == "event_abc123"
    assert home_row["snapshot_type"] == "opening"
    assert home_row["source_request_id"] == "req-1"
    assert isinstance(home_row["match_start"], datetime)
    assert home_row["match_start"].tzinfo == timezone.utc
    # Overround présent et > 1
    assert home_row["overround"] > 1.0


def test_parse_skips_unknown_bookmakers():
    sample = [
        {
            "id": "event_xxx",
            "sport_key": "soccer_epl",
            "commence_time": "2026-04-20T15:00:00Z",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "bookmakers": [
                {
                    "key": "random_book_not_in_registry",
                    "title": "Random",
                    "last_update": "2026-04-19T10:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Arsenal", "price": 1.80},
                                {"name": "Chelsea", "price": 4.50},
                                {"name": "Draw", "price": 3.60},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(sample, sport="football", snapshot_type="opening",
                               source_request_id="req-2")
    assert rows == []


def test_parse_raises_on_naive_commence_time():
    """Defense against silent timezone drift if Odds API returns naive ISO."""
    sample = [
        {
            "id": "event_naive",
            "sport_key": "soccer_epl",
            "commence_time": "2026-04-20T19:00:00",  # no Z, no offset
            "home_team": "A",
            "away_team": "B",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-04-19T10:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "A", "price": 1.80},
                                {"name": "B", "price": 4.50},
                                {"name": "Draw", "price": 3.60},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_odds_response(
            sample, sport="football", snapshot_type="opening",
            source_request_id="req-naive",
        )


def test_quota_exhausted_is_an_exception():
    assert issubclass(OddsAPIQuotaExhausted, Exception)


class _FakeResp:
    def __init__(self, status_code: int, json_data: Any = None,
                 headers: dict | None = None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_odds_retries_on_500(monkeypatch):
    """3 retries sur 500, succès au 3e try."""
    from src.fetchers import odds_ingestor

    attempts: list[int] = []

    def fake_get(url, params=None, timeout=None):
        attempts.append(1)
        if len(attempts) < 3:
            return _FakeResp(500)
        return _FakeResp(
            200,
            json_data=[],
            headers={"x-requests-remaining": "19000"},
        )

    monkeypatch.setattr(odds_ingestor.httpx, "get", fake_get)
    monkeypatch.setattr(odds_ingestor.time, "sleep", lambda s: None)

    result = odds_ingestor.fetch_odds(
        sport_key="soccer_epl",
        markets="h2h",
        api_key="FAKE",
    )
    assert result == []
    assert len(attempts) == 3


def test_fetch_odds_raises_quota_exhausted_on_429(monkeypatch):
    from src.fetchers import odds_ingestor

    def fake_get(url, params=None, timeout=None):
        return _FakeResp(429, headers={"x-requests-remaining": "0"})

    monkeypatch.setattr(odds_ingestor.httpx, "get", fake_get)
    monkeypatch.setattr(odds_ingestor.time, "sleep", lambda s: None)

    with pytest.raises(OddsAPIQuotaExhausted):
        odds_ingestor.fetch_odds(
            sport_key="soccer_epl", markets="h2h", api_key="FAKE"
        )


def test_fetch_odds_gives_up_after_max_retries(monkeypatch):
    """3 échecs 500 consécutifs → RuntimeError (pas OddsAPIQuotaExhausted)."""
    from src.fetchers import odds_ingestor

    def fake_get(url, params=None, timeout=None):
        return _FakeResp(500)

    monkeypatch.setattr(odds_ingestor.httpx, "get", fake_get)
    monkeypatch.setattr(odds_ingestor.time, "sleep", lambda s: None)

    with pytest.raises(RuntimeError):
        odds_ingestor.fetch_odds(
            sport_key="soccer_epl", markets="h2h", api_key="FAKE"
        )


def test_fetch_odds_retries_on_5xx_even_if_remaining_header_zero(monkeypatch):
    """CDN-stale x-requests-remaining:0 on a 502 must not short-circuit retry.

    Regression for I1 of H2-SS1 Task 4 code review.
    """
    from src.fetchers import odds_ingestor

    attempts: list[int] = []

    def fake_get(url, params=None, timeout=None):
        attempts.append(1)
        if len(attempts) < 3:
            return _FakeResp(
                502, headers={"x-requests-remaining": "0"}
            )
        return _FakeResp(
            200,
            json_data=[],
            headers={"x-requests-remaining": "19000"},
        )

    monkeypatch.setattr(odds_ingestor.httpx, "get", fake_get)
    monkeypatch.setattr(odds_ingestor.time, "sleep", lambda s: None)

    result = odds_ingestor.fetch_odds(
        sport_key="soccer_epl", markets="h2h", api_key="FAKE"
    )
    assert result == []
    assert len(attempts) == 3


def test_parse_btts_market():
    sample = [
        {
            "id": "fx1",
            "sport_key": "soccer_epl",
            "commence_time": "2026-04-20T15:00:00Z",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-04-19T10:00:00Z",
                    "markets": [
                        {
                            "key": "btts",
                            "outcomes": [
                                {"name": "Yes", "price": 1.65},
                                {"name": "No", "price": 2.30},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(sample, sport="football", snapshot_type="opening",
                               source_request_id="req-btts")
    assert len(rows) == 2
    yes_row = next(r for r in rows if r["selection"] == "yes")
    assert yes_row["market"] == "btts"
    assert yes_row["odds"] == 1.65


def test_parse_totals_over_2_5():
    sample = [
        {
            "id": "fx2",
            "sport_key": "soccer_epl",
            "commence_time": "2026-04-20T15:00:00Z",
            "home_team": "A",
            "away_team": "B",
            "bookmakers": [
                {
                    "key": "betclic",
                    "markets": [
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": 1.85, "point": 2.5},
                                {"name": "Under", "price": 1.95, "point": 2.5},
                                {"name": "Over", "price": 1.45, "point": 1.5},
                                {"name": "Under", "price": 2.60, "point": 1.5},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(sample, sport="football", snapshot_type="opening",
                               source_request_id="req-totals")
    over_25 = [r for r in rows if r["market"] == "over_2_5" and r["selection"] == "over"]
    assert len(over_25) == 1
    assert over_25[0]["line"] == 2.5
    assert over_25[0]["odds"] == 1.85
    # Over 1.5 aussi
    over_15 = [r for r in rows if r["market"] == "over_1_5"]
    assert len(over_15) == 2  # over + under


def test_parse_nhl_moneyline_and_totals():
    sample = [
        {
            "id": "nhl1",
            "sport_key": "icehockey_nhl",
            "commence_time": "2026-04-20T23:00:00Z",
            "home_team": "Boston Bruins",
            "away_team": "Montreal Canadiens",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Boston Bruins", "price": 1.70},
                                {"name": "Montreal Canadiens", "price": 2.20},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": 1.95, "point": 6.5},
                                {"name": "Under", "price": 1.90, "point": 6.5},
                            ],
                        },
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(sample, sport="nhl", snapshot_type="opening",
                               source_request_id="req-nhl")
    ml = [r for r in rows if r["market"] == "moneyline"]
    assert len(ml) == 2
    tot = [r for r in rows if r["market"] == "totals_nhl"]
    assert len(tot) == 2
    over_row = next(r for r in tot if r["selection"] == "over")
    assert over_row["line"] == 6.5
