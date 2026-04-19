"""Tests end-to-end pour le daily CLV snapshot cron job."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock


def test_run_daily_clv_snapshot_upserts_model_health_log(monkeypatch):
    from src.monitoring import clv_engine

    target = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    # Fake predictions on 2 matches with closing Pinnacle + Betclic
    predictions = [
        {
            "fixture_id": "fx1",
            "sport": "football",
            "league_id": 61,
            "pred_home": 60.0,
            "pred_draw": 25.0,
            "pred_away": 15.0,
            "actual_result": "H",
        },
        {
            "fixture_id": "fx2",
            "sport": "football",
            "league_id": 61,
            "pred_home": 30.0,
            "pred_draw": 30.0,
            "pred_away": 40.0,
            "actual_result": "A",
        },
    ]
    closing_rows = [
        {
            "fixture_id": "fx1",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "home",
            "odds": 1.80,
            "line": None,
        },
        {
            "fixture_id": "fx1",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "draw",
            "odds": 3.60,
            "line": None,
        },
        {
            "fixture_id": "fx1",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "away",
            "odds": 4.80,
            "line": None,
        },
        {
            "fixture_id": "fx2",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "home",
            "odds": 3.00,
            "line": None,
        },
        {
            "fixture_id": "fx2",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "draw",
            "odds": 3.40,
            "line": None,
        },
        {
            "fixture_id": "fx2",
            "bookmaker": "pinnacle",
            "market": "1x2",
            "selection": "away",
            "odds": 2.50,
            "line": None,
        },
    ]

    monkeypatch.setattr(clv_engine, "_load_predictions_for_date", lambda d: predictions)
    monkeypatch.setattr(clv_engine, "_load_closing_odds_for_date", lambda d: closing_rows)

    upserted: list[dict] = []

    class _Exec:
        def __init__(self, store, row):
            self._store = store
            self._row = row

        def execute(self):
            self._store.append(self._row)
            return MagicMock(data=[self._row])

    class FakeSupabase:
        def table(self, name):
            assert name == "model_health_log"
            mock = MagicMock()
            mock.upsert = lambda row, on_conflict=None: _Exec(upserted, row)
            mock.insert = lambda row: _Exec(upserted, row)
            return mock

    monkeypatch.setattr(clv_engine, "supabase", FakeSupabase())

    out = clv_engine.run_daily_clv_snapshot(target_date=target)
    assert out["n_matches_clv"] > 0
    assert len(upserted) == 1
    row = upserted[0]
    assert row["sport"] == "football"
    assert row["variant_id"] is not None
    assert "clv_vs_pinnacle_1x2" in row


def test_run_daily_clv_snapshot_no_predictions_noop(monkeypatch):
    from src.monitoring import clv_engine

    monkeypatch.setattr(clv_engine, "_load_predictions_for_date", lambda d: [])
    monkeypatch.setattr(clv_engine, "_load_closing_odds_for_date", lambda d: [])

    called = []

    class FakeSupabase:
        def table(self, name):
            called.append(name)
            raise AssertionError("should not insert when no predictions")

    monkeypatch.setattr(clv_engine, "supabase", FakeSupabase())

    out = clv_engine.run_daily_clv_snapshot(target_date=date(2026, 4, 10))
    assert out["n_matches_clv"] == 0
    assert called == []


def test_load_predictions_for_date_uses_match_date_not_created_at(monkeypatch):
    """C3 regression — _load_predictions_for_date must filter by match date
    (fixtures.date), not prediction_results.created_at."""
    from src.monitoring import clv_engine

    target = date(2026, 4, 18)

    # Fake fixtures table: 2 matches on target date, 1 match on adjacent day
    football_rows = [
        {"id": 111},
        {"id": 222},
    ]
    nhl_rows = [
        {"game_id": 2026020500},
    ]
    prediction_rows = [
        {"fixture_id": 111, "pred_home": 60.0, "actual_result": "H"},
        {"fixture_id": 222, "pred_home": 40.0, "actual_result": "A"},
        {"fixture_id": 2026020500, "pred_home": 55.0, "actual_result": "H"},
    ]

    calls: list[tuple[str, str]] = []

    class FakeTable:
        def __init__(self, name):
            self.name = name
            self._filters = {}

        def select(self, _cols):
            return self

        def gte(self, col, val):
            self._filters[f"gte_{col}"] = val
            return self

        def lt(self, col, val):
            self._filters[f"lt_{col}"] = val
            return self

        def in_(self, col, vals):
            self._filters[f"in_{col}"] = list(vals)
            return self

        def eq(self, col, val):
            self._filters[f"eq_{col}"] = val
            return self

        def execute(self):
            calls.append((self.name, str(self._filters)))
            if self.name == "fixtures":
                return MagicMock(data=football_rows)
            if self.name == "nhl_fixtures":
                return MagicMock(data=nhl_rows)
            if self.name == "prediction_results":
                # Verify it's an .in_ filter by fixture_id
                assert "in_fixture_id" in self._filters
                ids_requested = self._filters["in_fixture_id"]
                return MagicMock(
                    data=[r for r in prediction_rows if str(r["fixture_id"]) in ids_requested]
                )
            return MagicMock(data=[])

    class FakeSupabase:
        def table(self, name):
            return FakeTable(name)

    monkeypatch.setattr(clv_engine, "supabase", FakeSupabase())

    result = clv_engine._load_predictions_for_date(target)

    # All 3 predictions should be returned (2 football + 1 NHL)
    assert len(result) == 3
    fixture_ids = {str(r["fixture_id"]) for r in result}
    assert fixture_ids == {"111", "222", "2026020500"}

    # Verify the fixtures+nhl_fixtures queries were made FIRST (before prediction_results)
    table_names = [c[0] for c in calls]
    assert "fixtures" in table_names
    assert "nhl_fixtures" in table_names
    assert "prediction_results" in table_names

    # Verify the fixtures query filtered by 'date' column (not 'created_at')
    foot_call = next(c for c in calls if c[0] == "fixtures")
    assert "gte_date" in foot_call[1]
    assert "lt_date" in foot_call[1]
    # Verify the NHL query filtered by 'game_date'
    nhl_call = next(c for c in calls if c[0] == "nhl_fixtures")
    assert "gte_game_date" in nhl_call[1]
    assert "lt_game_date" in nhl_call[1]


def test_load_predictions_for_date_returns_empty_when_no_fixtures(monkeypatch):
    """No fixtures in window → no DB query on prediction_results, return []."""
    from src.monitoring import clv_engine

    prediction_calls = []

    class FakeTable:
        def __init__(self, name):
            self.name = name

        def select(self, _cols):
            return self

        def gte(self, *a, **kw):
            return self

        def lt(self, *a, **kw):
            return self

        def in_(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def execute(self):
            if self.name == "prediction_results":
                prediction_calls.append(1)
            return MagicMock(data=[])

    class FakeSupabase:
        def table(self, name):
            return FakeTable(name)

    monkeypatch.setattr(clv_engine, "supabase", FakeSupabase())

    result = clv_engine._load_predictions_for_date(date(2026, 4, 18))

    assert result == []
    # prediction_results should NOT be queried when no fixtures match
    assert prediction_calls == []
