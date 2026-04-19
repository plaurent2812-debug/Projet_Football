"""Tests pour odds_ingestor — client The Odds API Dev."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.fetchers.odds_ingestor import (
    OddsAPIQuotaExhausted,
    parse_odds_response,
    to_implied_prob,
)
from src.fetchers.odds_ingestor import (
    _resolve_fixture_id as _real_resolve_fixture_id,
)

# Save the real resolver reference BEFORE any monkeypatching so the dedicated
# resolver tests can exercise the actual implementation.


@pytest.fixture(autouse=True)
def _patch_resolver(monkeypatch):
    """Auto-patch _resolve_fixture_id with a deterministic fake for all tests.

    Tests that need to exercise the real resolver (or a different fake) can
    re-patch inside their body — monkeypatch is LIFO, so the later setattr wins.
    Tests that assert `fixture_id` values should use the resolved pattern
    `resolved-<home[:3]>-<away[:3]>`.
    """
    from src.fetchers import odds_ingestor
    monkeypatch.setattr(
        odds_ingestor, "_resolve_fixture_id",
        lambda sport, h, a, ms: f"resolved-{(h or '')[:3]}-{(a or '')[:3]}",
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
    # fixture_id is now the resolved internal ID, not the Odds API event UUID
    assert home_row["fixture_id"] == "resolved-Par-Oly"
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


def test_parse_nhl_team_name_divergence_matches_via_normalization():
    """Lesson 69 regression — 'St. Louis Blues' vs 'St Louis Blues'."""
    sample = [
        {
            "id": "nhl_div",
            "sport_key": "icehockey_nhl",
            "commence_time": "2026-04-20T23:00:00Z",
            "home_team": "St. Louis Blues",  # point, spaces
            "away_team": "Utah Mammoth",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "St Louis Blues", "price": 1.70},  # no point
                                {"name": "Utah Hockey Club", "price": 2.20},  # old name
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(sample, sport="nhl", snapshot_type="opening",
                               source_request_id="req-div")
    ml = [r for r in rows if r["market"] == "moneyline"]
    assert len(ml) == 2, (
        "Both NHL teams must match despite provider name divergence"
    )
    home_row = next(r for r in ml if r["selection"] == "home")
    away_row = next(r for r in ml if r["selection"] == "away")
    assert home_row["odds"] == 1.70
    assert away_row["odds"] == 2.20


def test_parse_totals_skips_outcomes_without_point():
    """I2 regression — missing 'point' field must not produce line=0 rows."""
    sample = [
        {
            "id": "nhl_no_point",
            "sport_key": "icehockey_nhl",
            "commence_time": "2026-04-20T23:00:00Z",
            "home_team": "A",
            "away_team": "B",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "markets": [
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": 1.95},   # no point!
                                {"name": "Under", "price": 1.90},  # no point!
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    rows = parse_odds_response(sample, sport="nhl", snapshot_type="opening",
                               source_request_id="req-nopoint")
    totals = [r for r in rows if r["market"] == "totals_nhl"]
    assert totals == [], (
        "Outcomes without 'point' must be skipped to avoid line=0 garbage rows"
    )


def test_upsert_odds_calls_supabase_with_on_conflict_ignore(monkeypatch):
    from src.fetchers import odds_ingestor

    inserted_batches: list[list[dict]] = []

    class FakeTable:
        def upsert(self, rows, on_conflict=None, ignore_duplicates=None):
            inserted_batches.append(rows)
            return self

        def execute(self):
            return MagicMock(data=inserted_batches[-1])

    class FakeSupabase:
        def table(self, name):
            assert name == "closing_odds"
            return FakeTable()

    monkeypatch.setattr(odds_ingestor, "supabase", FakeSupabase())

    rows = [
        {
            "sport": "football", "fixture_id": "fx1",
            "match_start": datetime(2026, 4, 20, 15, tzinfo=timezone.utc),
            "bookmaker": "pinnacle", "market": "1x2", "selection": "home",
            "line": None, "odds": 1.50, "implied_prob": 0.6667,
            "overround": 1.05, "snapshot_type": "opening",
            "source_request_id": "req-upsert",
        }
    ]
    n = odds_ingestor.upsert_odds(rows)
    assert n == 1
    assert len(inserted_batches) == 1
    # match_start doit être sérialisé en ISO 8601 pour Supabase
    assert isinstance(inserted_batches[0][0]["match_start"], str)


def test_upsert_odds_empty_list_is_noop(monkeypatch):
    from src.fetchers import odds_ingestor

    called = []

    class FakeSupabase:
        def table(self, name):
            called.append(name)
            raise AssertionError("should not be called")

    monkeypatch.setattr(odds_ingestor, "supabase", FakeSupabase())
    assert odds_ingestor.upsert_odds([]) == 0
    assert called == []


def test_run_snapshot_iterates_all_sports(monkeypatch):
    from src.fetchers import odds_ingestor

    fetched_calls: list[tuple[str, str]] = []
    upserted: list[int] = []

    def fake_fetch(sport_key, markets, api_key, bookmakers=None, regions="eu",
                   odds_format="decimal"):
        fetched_calls.append((sport_key, markets))
        return []

    def fake_upsert(rows):
        upserted.append(len(rows))
        return len(rows)

    monkeypatch.setattr(odds_ingestor, "fetch_odds", fake_fetch)
    monkeypatch.setattr(odds_ingestor, "upsert_odds", fake_upsert)
    monkeypatch.setattr(odds_ingestor, "_get_api_key", lambda: "FAKE")

    n = odds_ingestor.run_snapshot(snapshot_type="opening")
    # 8 ligues foot + 1 NHL = 9 sport keys × N markets
    assert len(fetched_calls) >= 9
    sport_keys_called = {c[0] for c in fetched_calls}
    assert "soccer_france_ligue_one" in sport_keys_called
    assert "icehockey_nhl" in sport_keys_called
    assert n == 0  # rien à upsert (fake retourne [])


def test_run_snapshot_skips_sports_on_quota(monkeypatch):
    """Quand OddsAPIQuotaExhausted est levé, on arrête proprement."""
    from src.fetchers import odds_ingestor

    def fake_fetch(sport_key, markets, api_key, **_):
        raise OddsAPIQuotaExhausted("quota")

    monkeypatch.setattr(odds_ingestor, "fetch_odds", fake_fetch)
    monkeypatch.setattr(odds_ingestor, "upsert_odds", lambda rows: 0)
    monkeypatch.setattr(odds_ingestor, "_get_api_key", lambda: "FAKE")
    monkeypatch.setattr(odds_ingestor, "_try_send_telegram", lambda msg: None)

    # Doit attraper l'exception, logger, et retourner 0 (pas re-raise)
    n = odds_ingestor.run_snapshot(snapshot_type="opening")
    assert n == 0


def test_run_snapshot_raises_if_all_sport_keys_fail(monkeypatch):
    """I2 regression — if ALL sport_keys throw non-quota errors, raise RuntimeError."""
    from src.fetchers import odds_ingestor

    def fake_fetch(sport_key, markets, api_key, **_):
        raise RuntimeError("API 500")

    monkeypatch.setattr(odds_ingestor, "fetch_odds", fake_fetch)
    monkeypatch.setattr(odds_ingestor, "upsert_odds", lambda rows: 0)
    monkeypatch.setattr(odds_ingestor, "_get_api_key", lambda: "FAKE")
    monkeypatch.setattr(odds_ingestor, "_try_send_telegram", lambda msg: None)

    with pytest.raises(RuntimeError, match="failed on all"):
        odds_ingestor.run_snapshot(snapshot_type="opening")


def test_run_snapshot_succeeds_if_at_least_one_sport_key_works(monkeypatch):
    """Partial failure (some sport_keys OK, some fail) must not raise."""
    from src.fetchers import odds_ingestor

    call_count = {"n": 0}

    def fake_fetch(sport_key, markets, api_key, **_):
        call_count["n"] += 1
        if call_count["n"] % 2 == 0:
            raise RuntimeError("transient")
        return []  # success with empty payload

    monkeypatch.setattr(odds_ingestor, "fetch_odds", fake_fetch)
    monkeypatch.setattr(odds_ingestor, "upsert_odds", lambda rows: 0)
    monkeypatch.setattr(odds_ingestor, "_get_api_key", lambda: "FAKE")
    monkeypatch.setattr(odds_ingestor, "_try_send_telegram", lambda msg: None)

    # Should not raise — at least some sport_keys succeeded
    n = odds_ingestor.run_snapshot(snapshot_type="opening")
    assert n == 0


def test_run_snapshot_for_fixtures_filters_events(monkeypatch):
    from src.fetchers import odds_ingestor

    upserted_rows: list[list[dict]] = []

    def fake_fetch(sport_key, markets, api_key, **_):
        return [
            {
                "id": "target_fx",
                "sport_key": sport_key,
                "commence_time": "2026-04-20T19:00:00Z",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "bookmakers": [
                    {
                        "key": "pinnacle",
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
            },
            {
                "id": "other_fx",
                "sport_key": sport_key,
                "commence_time": "2026-04-20T19:00:00Z",
                "home_team": "A",
                "away_team": "B",
                "bookmakers": [],
            },
        ]

    def fake_upsert(rows):
        upserted_rows.append(rows)
        return len(rows)

    monkeypatch.setattr(odds_ingestor, "fetch_odds", fake_fetch)
    monkeypatch.setattr(odds_ingestor, "upsert_odds", fake_upsert)
    monkeypatch.setattr(odds_ingestor, "_get_api_key", lambda: "FAKE")

    # After C1 fix: filter is applied on the resolved internal fixture_id, not
    # the Odds API event UUID. The autouse resolver returns resolved-<h[:3]>-<a[:3]>.
    n = odds_ingestor.run_snapshot_for_fixtures(["resolved-Ars-Che"])
    assert n > 0
    # All upserted rows should belong to the Arsenal/Chelsea resolved id
    for batch in upserted_rows:
        for row in batch:
            assert row["fixture_id"] == "resolved-Ars-Che"
            assert row["snapshot_type"] == "closing"


def test_run_snapshot_for_fixtures_empty_list_noop(monkeypatch):
    from src.fetchers import odds_ingestor

    called = []
    monkeypatch.setattr(odds_ingestor, "fetch_odds",
                        lambda **kw: called.append(1) or [])

    n = odds_ingestor.run_snapshot_for_fixtures([])
    assert n == 0
    assert called == []


def test_schedule_closing_snapshots_registers_date_triggers(monkeypatch):
    from datetime import timedelta

    from src.fetchers import odds_ingestor

    now = datetime.now(timezone.utc)
    fixtures = [
        {"fixture_id": "fx1", "kickoff_utc": now + timedelta(hours=6)},
        {"fixture_id": "fx2", "kickoff_utc": now + timedelta(hours=8)},
        {"fixture_id": "fx_past", "kickoff_utc": now - timedelta(hours=1)},
    ]
    monkeypatch.setattr(odds_ingestor, "_load_today_fixtures_for_closing",
                        lambda: fixtures)

    scheduled = []

    class FakeScheduler:
        def add_job(self, func, *, trigger, run_date, args, id, replace_existing,
                    misfire_grace_time):
            scheduled.append({"id": id, "run_date": run_date, "args": args})

    n = odds_ingestor.schedule_closing_snapshots_for_today(FakeScheduler())
    assert n == 2
    ids = {s["id"] for s in scheduled}
    assert "closing_fx1" in ids
    assert "closing_fx2" in ids
    assert "closing_fx_past" not in ids
    # Verify run_dates are kickoff - 30min
    for s in scheduled:
        fx_id = s["id"].replace("closing_", "")
        expected_fx = next(fx for fx in fixtures if fx["fixture_id"] == fx_id)
        assert s["run_date"] == expected_fx["kickoff_utc"] - timedelta(minutes=30)


def test_load_today_fixtures_uses_internal_id_for_football(monkeypatch):
    """Regression C1 downstream — load_today_fixtures must return fixtures.id (internal)
    so the ID matches closing_odds.fixture_id after the resolver fix."""
    from datetime import timedelta

    from src.fetchers import odds_ingestor

    future = datetime.now(timezone.utc) + timedelta(hours=6)

    football_rows = [
        {"id": 999888, "date": future.isoformat()},
    ]
    nhl_rows = [
        {"game_id": 2026020500, "game_date": future.isoformat()},
    ]

    call_order = []

    class FakeTable:
        def __init__(self, name):
            self.name = name

        def select(self, _cols):
            return self

        def gte(self, _col, _val):
            return self

        def lt(self, _col, _val):
            return self

        def execute(self):
            call_order.append(self.name)
            data = football_rows if self.name == "fixtures" else nhl_rows
            return MagicMock(data=data)

    class FakeSupabase:
        def table(self, name):
            return FakeTable(name)

    monkeypatch.setattr(odds_ingestor, "supabase", FakeSupabase())

    fixtures = odds_ingestor._load_today_fixtures_for_closing()
    assert len(fixtures) == 2
    football = next(f for f in fixtures if f["fixture_id"] == "999888")
    nhl = next(f for f in fixtures if f["fixture_id"] == "2026020500")
    # football.fixture_id is str(id), NOT str(api_fixture_id)
    assert football["fixture_id"] == "999888"
    assert nhl["fixture_id"] == "2026020500"


# ---------------------------------------------------------------------------
# C1 regression — _resolve_fixture_id maps Odds API teams/kickoff → fixtures.id
# ---------------------------------------------------------------------------


def test_resolve_fixture_id_matches_by_teams_and_date(monkeypatch):
    from src.fetchers import odds_ingestor

    class FakeTable:
        def select(self, _cols):
            return self

        def gte(self, _col, _val):
            return self

        def lt(self, _col, _val):
            return self

        def execute(self):
            return MagicMock(data=[
                {"id": 42, "home_team": "Arsenal", "away_team": "Chelsea",
                 "date": "2026-04-20T15:00:00Z"},
                {"id": 43, "home_team": "Tottenham", "away_team": "Fulham",
                 "date": "2026-04-20T15:30:00Z"},
            ])

    class FakeSupabase:
        def table(self, name):
            assert name == "fixtures"
            return FakeTable()

    monkeypatch.setattr(odds_ingestor, "supabase", FakeSupabase())

    # Call the real resolver directly (autouse fixture patches the module attribute)
    resolved = _real_resolve_fixture_id(
        "football", "Arsenal", "Chelsea",
        datetime(2026, 4, 20, 15, 0, tzinfo=timezone.utc),
    )
    assert resolved == "42"


def test_resolve_fixture_id_returns_none_when_no_match(monkeypatch):
    from src.fetchers import odds_ingestor

    class FakeTable:
        def select(self, _cols):
            return self

        def gte(self, _col, _val):
            return self

        def lt(self, _col, _val):
            return self

        def execute(self):
            return MagicMock(data=[])

    class FakeSupabase:
        def table(self, _name):
            return FakeTable()

    monkeypatch.setattr(odds_ingestor, "supabase", FakeSupabase())

    resolved = _real_resolve_fixture_id(
        "football", "NoMatch FC", "NeverHeardOf",
        datetime(2026, 4, 20, 15, 0, tzinfo=timezone.utc),
    )
    assert resolved is None


def test_resolve_fixture_id_uses_teams_match_normalization(monkeypatch):
    """Lesson 69 — 'St. Louis Blues' in API resolves to 'St Louis Blues' in DB."""
    from src.fetchers import odds_ingestor

    class FakeTable:
        def select(self, _cols):
            return self

        def gte(self, _col, _val):
            return self

        def lt(self, _col, _val):
            return self

        def execute(self):
            return MagicMock(data=[
                {"game_id": 2026020500, "home_team": "St Louis Blues",
                 "away_team": "Utah Mammoth",
                 "game_date": "2026-04-20T23:00:00Z"},
            ])

    class FakeSupabase:
        def table(self, name):
            assert name == "nhl_fixtures"
            return FakeTable()

    monkeypatch.setattr(odds_ingestor, "supabase", FakeSupabase())

    resolved = _real_resolve_fixture_id(
        "nhl", "St. Louis Blues", "Utah Hockey Club",
        datetime(2026, 4, 20, 23, 0, tzinfo=timezone.utc),
    )
    assert resolved == "2026020500"


def test_parse_skips_event_when_fixture_not_resolved(monkeypatch):
    """Si le résolveur renvoie None, l'event doit être skip (pas inséré)."""
    from src.fetchers import odds_ingestor

    # Override the autouse patch to simulate a failed resolution
    monkeypatch.setattr(
        odds_ingestor, "_resolve_fixture_id",
        lambda sport, h, a, ms: None,
    )

    sample = [
        {
            "id": "unresolvable_event",
            "sport_key": "soccer_epl",
            "commence_time": "2026-04-20T15:00:00Z",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "bookmakers": [
                {
                    "key": "pinnacle",
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
    rows = odds_ingestor.parse_odds_response(
        sample, sport="football", snapshot_type="opening",
        source_request_id="req-skip",
    )
    assert rows == []
