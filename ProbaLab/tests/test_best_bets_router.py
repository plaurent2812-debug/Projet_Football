"""
Integration tests for api/routers/best_bets.py — exercise the endpoints
with a mocked Supabase client so we cover the DB read/write code paths
without touching a real database.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════
#  Helper: route-aware Supabase mock
# ═══════════════════════════════════════════════════════════════════


class RouteAwareQuery:
    """Chainable Supabase query that records filters and returns staged data.

    Unlike the basic MockSupabaseQuery in conftest, this one actually
    inspects `eq` / `in_` calls so different tables in the same test
    can return different data depending on the filter applied.
    """

    def __init__(self, table_name: str, staged: dict):
        self.table_name = table_name
        self.staged = staged  # {filter_key: filter_value} → list[dict]
        self._filters: dict = {}
        self._default_data: list[dict] = staged.get("__default__", [])
        self._update_payload: dict | None = None
        self._update_captured: list[tuple[dict, dict]] = staged.setdefault("__updates__", [])

    # ── chainable selectors (no-op) ───────────────────────────────
    def select(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def gt(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def or_(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    # ── filters that influence the returned payload ──────────────
    def eq(self, col, val):
        self._filters[col] = val
        return self

    def in_(self, col, values):
        self._filters[f"{col}__in"] = values
        return self

    # ── mutations (captured, not actually persisted) ─────────────
    def insert(self, payload):
        self._filters["__insert__"] = payload
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def delete(self):
        return self

    def upsert(self, payload):
        self._filters["__upsert__"] = payload
        return self

    def execute(self):
        # Capture update calls for assertions
        if self._update_payload is not None:
            self._update_captured.append((dict(self._filters), self._update_payload))
            result = MagicMock()
            result.data = [{"id": self._filters.get("id", 0), **self._update_payload}]
            return result

        # Staged routing: pick the list whose key matches the active filters.
        # Keys come in two shapes:
        #   - str ("__default__", "__updates__") → bookkeeping, skipped here
        #   - tuple (filter_col, expected_value) → actual routes
        for route_key, data in self.staged.items():
            if isinstance(route_key, str):
                continue
            col, expected = route_key
            if self._filters.get(col) == expected:
                result = MagicMock()
                result.data = data
                return result

        result = MagicMock()
        result.data = self._default_data
        return result


class RouteAwareSupabase:
    """Supabase client mock that dispatches per-table."""

    def __init__(self):
        self._tables: dict[str, dict] = {}

    def stage(self, table: str, staged: dict):
        self._tables[table] = staged

    def updates_for(self, table: str) -> list[tuple[dict, dict]]:
        return self._tables.get(table, {}).get("__updates__", [])

    def table(self, name):
        return RouteAwareQuery(name, self._tables.get(name, {}))

    # Minimal RPC shim for completeness
    def rpc(self, *args, **kwargs):
        stub = MagicMock()
        stub.execute.return_value = MagicMock(data=None)
        return stub


# ═══════════════════════════════════════════════════════════════════
#  resolve_best_bets — football path
# ═══════════════════════════════════════════════════════════════════


class TestResolveBestBetsFootball:
    """Exercise the football branch of /api/best-bets/resolve."""

    def _make_body(self, date="2026-04-01", sport="football"):
        from api.schemas import ResolveBetsRequest

        return ResolveBetsRequest(date=date, sport=sport)

    def test_no_pending_bets_returns_early(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [],  # no bets pending
                "__default__": [],
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["ok"] is True
        assert result["resolved"] == 0
        assert result["message"] == "No pending bets"

    def test_football_win_single_bet(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        # One pending bet on a home win
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 1,
                        "bet_label": "PSG vs Lyon — Victoire domicile",
                        "market": "Victoire domicile",
                        "fixture_id": 100,
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        # Finished fixture with a home win 3-1
        sb.stage(
            "fixtures",
            {
                "__default__": [
                    {
                        "id": 100,
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "home_goals": 3,
                        "away_goals": 1,
                        "status": "FT",
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["ok"] is True
        assert result["resolved_count"] == 1
        assert result["resolved"][0]["result"] == "WIN"
        assert result["resolved"][0]["score"] == "3-1"

        # The update call must have set result="WIN"
        updates = sb.updates_for("best_bets")
        assert len(updates) == 1
        filters, payload = updates[0]
        assert filters["id"] == 1
        assert payload["result"] == "WIN"
        assert "3-1" in payload["notes"]

    def test_football_loss_single_bet(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 2,
                        "bet_label": "PSG vs Lyon — Over 2.5 buts",
                        "market": "Over 2.5 buts",
                        "fixture_id": 100,
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        # 1-0 final → Over 2.5 = LOSS
        sb.stage(
            "fixtures",
            {
                "__default__": [
                    {
                        "id": 100,
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "home_goals": 1,
                        "away_goals": 0,
                        "status": "FT",
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 1
        assert result["resolved"][0]["result"] == "LOSS"

    def test_football_category_market_extracts_from_label(self):
        """When market is 'safe_football', the actual market is after '—' in the label."""
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 3,
                        "bet_label": "PSG vs Lyon — BTTS Oui",
                        "market": "safe_football",
                        "fixture_id": 100,
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        # 2-1 final → BTTS = WIN
        sb.stage(
            "fixtures",
            {
                "__default__": [
                    {
                        "id": 100,
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "home_goals": 2,
                        "away_goals": 1,
                        "status": "FT",
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved"][0]["result"] == "WIN"

    def test_football_combo_bet(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 4,
                        "bet_label": "PSG vs Lyon — Victoire domicile + Over 1.5 buts",
                        "market": "Victoire domicile + Over 1.5 buts",
                        "fixture_id": 100,
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        # 2-0 → V.dom WIN + Over 1.5 WIN → combo WIN
        sb.stage(
            "fixtures",
            {
                "__default__": [
                    {
                        "id": 100,
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "home_goals": 2,
                        "away_goals": 0,
                        "status": "FT",
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 1
        assert result["resolved"][0]["result"] == "WIN"

    def test_football_pending_when_fixture_not_finished(self):
        """If we can't find a finished fixture, the bet stays PENDING."""
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 5,
                        "bet_label": "PSG vs Lyon — Victoire domicile",
                        "market": "Victoire domicile",
                        "fixture_id": 999,  # fixture not in the finished list
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        # Return a fixture for a different match so by-teams lookup also misses
        sb.stage("fixtures", {"__default__": []})

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 0
        assert sb.updates_for("best_bets") == []

    def test_football_fixture_found_by_label_when_no_id(self):
        """If fixture_id is missing, fall back to matching 'Home vs Away' from the label."""
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 6,
                        "bet_label": "PSG vs Lyon — Over 2.5 buts",
                        "market": "Over 2.5 buts",
                        "fixture_id": None,
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        sb.stage(
            "fixtures",
            {
                "__default__": [
                    {
                        "id": 100,
                        "home_team": "PSG",
                        "away_team": "Lyon",
                        "home_goals": 3,
                        "away_goals": 1,
                        "status": "FT",
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 1
        assert result["resolved"][0]["result"] == "WIN"


# ═══════════════════════════════════════════════════════════════════
#  resolve_best_bets — NHL path
# ═══════════════════════════════════════════════════════════════════


class TestResolveBestBetsNHL:
    """Exercise the NHL player props branch."""

    def _make_body(self, date="2026-04-01"):
        from api.schemas import ResolveBetsRequest

        return ResolveBetsRequest(date=date, sport="nhl")

    def test_nhl_points_over_05_win(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 10,
                        "bet_label": "Connor McDavid Over 0.5 Points — EDM vs CAR",
                        "market": "player_points_over_0.5",
                        "player_name": "Connor McDavid",
                        "team": "EDM",
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        sb.stage(
            "nhl_fixtures",
            {
                "__default__": [
                    {
                        "id": 50,
                        "home_team": "Edmonton Oilers",
                        "away_team": "Carolina Hurricanes",
                        "home_score": 4,
                        "away_score": 2,
                        "status": "FINAL",
                    }
                ]
            },
        )
        sb.stage(
            "nhl_player_game_stats",
            {
                "__default__": [
                    {
                        "player_name": "Connor McDavid",
                        "team": "EDM",
                        "goals": 1,
                        "assists": 2,
                        "points": 3,
                        "shots": 5,
                        "game_id": 50,
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 1
        assert result["resolved"][0]["result"] == "WIN"
        assert result["resolved"][0]["points"] == 3

    def test_nhl_points_loss_on_zero(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 11,
                        "bet_label": "Player Over 0.5 Points — XXX vs YYY",
                        "market": "player_points_over_0.5",
                        "player_name": "Mystery Player",
                        "team": "XXX",
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        sb.stage("nhl_fixtures", {"__default__": []})
        sb.stage(
            "nhl_player_game_stats",
            {
                "__default__": [
                    {
                        "player_name": "Mystery Player",
                        "team": "XXX",
                        "goals": 0,
                        "assists": 0,
                        "points": 0,
                        "shots": 2,
                        "game_id": 51,
                    }
                ]
            },
        )

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 1
        assert result["resolved"][0]["result"] == "LOSS"

    def test_nhl_no_stats_yet_skipped(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 12,
                        "bet_label": "Player Over 0.5 Points — XXX vs YYY",
                        "market": "player_points_over_0.5",
                        "player_name": "No Stats Yet",
                        "team": "XXX",
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        sb.stage("nhl_fixtures", {"__default__": []})
        sb.stage("nhl_player_game_stats", {"__default__": []})

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        # No stats → skipped (not resolved)
        assert result["resolved_count"] == 0

    def test_nhl_missing_player_name_errors(self):
        from api.routers import best_bets as bb_module

        sb = RouteAwareSupabase()
        sb.stage(
            "best_bets",
            {
                ("date", "2026-04-01"): [
                    {
                        "id": 13,
                        # Empty label + empty player_name → cannot extract
                        "bet_label": "",
                        "market": "player_points_over_0.5",
                        "player_name": "",
                        "team": "XXX",
                        "result": "PENDING",
                    }
                ],
                "__default__": [],
            },
        )
        sb.stage("nhl_fixtures", {"__default__": []})
        sb.stage("nhl_player_game_stats", {"__default__": []})

        with patch.object(bb_module, "supabase", sb), patch.object(bb_module, "verify_cron_auth"):
            result = bb_module.resolve_best_bets.__wrapped__(
                body=self._make_body(),
                request=MagicMock(),
                authorization="Bearer test",
            )

        assert result["resolved_count"] == 0
        assert len(result["errors"]) == 1
        assert "Cannot extract player name" in result["errors"][0]["error"]


# ═══════════════════════════════════════════════════════════════════
#  resolve_best_bets — validation errors
# ═══════════════════════════════════════════════════════════════════


class TestResolveBestBetsValidation:
    def test_invalid_sport_rejected(self):

        from pydantic import ValidationError

        from api.schemas import ResolveBetsRequest

        # pydantic won't even accept this, so we bypass the schema layer
        # by manually constructing a body with a valid sport then tampering.
        # Actually, pydantic will reject at construction, so we test via body.
        with pytest.raises(ValidationError):
            ResolveBetsRequest(date="2026-04-01", sport="basketball")  # type: ignore[arg-type]

    def test_missing_data_raises_400(self):
        from api.routers import best_bets as bb_module

        # Build a request-like object where date is empty to hit the 400 branch.
        # The endpoint still runs the pydantic check upstream, but the manual
        # check `if not date or sport not in ("football", "nhl")` is reached
        # when date is an empty string (pydantic allows it only via our
        # pattern — so we patch the object to bypass validation).
        class FakeBody:
            date = ""
            sport = "football"

        from fastapi import HTTPException

        with patch.object(bb_module, "verify_cron_auth"), pytest.raises(HTTPException) as exc:
            bb_module.resolve_best_bets.__wrapped__(
                body=FakeBody(),  # type: ignore[arg-type]
                request=MagicMock(),
                authorization="Bearer test",
            )
        assert exc.value.status_code == 400
