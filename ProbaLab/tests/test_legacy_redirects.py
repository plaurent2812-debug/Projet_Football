"""Backend legacy URL redirects — Lot 6 Bloc A (Task 4).

Legacy routes (used by the V1 SPA) must return HTTP 301 + Location header
pointing to the V2 equivalent, so bookmarks, crawlers, curl, Slack/Discord
unfurlers follow the new URLs without needing JS.

Source of truth for the redirect table : shared with
`dashboard/src/app/v2/redirects.ts` — any change to either must be mirrored.
"""

from __future__ import annotations

from urllib.parse import parse_qsl

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, follow_redirects=False)


# ─── Exhaustive static redirect table (source of truth) ────────────
# Format : (legacy_path, expected_target_location)
# Note : query merging is validated separately (see test_query_params_preserved).

STATIC_REDIRECTS: list[tuple[str, str]] = [
    ("/paris-du-soir", "/matchs?signal=value"),
    ("/paris-du-soir/football", "/matchs?sport=foot&signal=value"),
    ("/football", "/matchs?sport=foot"),
    ("/nhl", "/matchs?sport=nhl"),
    ("/watchlist", "/compte/bankroll"),
    ("/hero-showcase", "/"),
]


DYNAMIC_REDIRECTS: list[tuple[str, str]] = [
    ("/football/match/12345", "/matchs/12345"),
    ("/football/match/abc-def", "/matchs/abc-def"),
    ("/nhl/match/98765", "/matchs/98765"),
    ("/nhl/match/fx-xyz-1", "/matchs/fx-xyz-1"),
]


# ─── Static routes ─────────────────────────────────────────────────


@pytest.mark.parametrize("source,target", STATIC_REDIRECTS)
def test_legacy_static_returns_301(source: str, target: str) -> None:
    resp = client.get(source)
    assert resp.status_code == 301, f"{source} should return 301, got {resp.status_code}"
    assert resp.headers["location"] == target, (
        f"{source} should redirect to {target}, got {resp.headers['location']}"
    )


# ─── Dynamic :id routes ────────────────────────────────────────────


@pytest.mark.parametrize("source,target", DYNAMIC_REDIRECTS)
def test_legacy_dynamic_returns_301(source: str, target: str) -> None:
    resp = client.get(source)
    assert resp.status_code == 301
    assert resp.headers["location"] == target


# ─── Query param preservation ──────────────────────────────────────


def test_query_params_preserved_on_static_route() -> None:
    resp = client.get("/football?team=PSG&date=2026-04-21")
    assert resp.status_code == 301
    loc = resp.headers["location"]
    assert loc.startswith("/matchs?"), loc
    params = dict(parse_qsl(loc.split("?", 1)[1]))
    assert params.get("sport") == "foot"
    assert params.get("team") == "PSG"
    assert params.get("date") == "2026-04-21"


def test_query_params_preserved_on_dynamic_route() -> None:
    resp = client.get("/football/match/fx-42?tab=stats")
    assert resp.status_code == 301
    loc = resp.headers["location"]
    assert loc.startswith("/matchs/fx-42?"), loc
    params = dict(parse_qsl(loc.split("?", 1)[1]))
    assert params.get("tab") == "stats"


def test_hero_showcase_drops_incoming_query() -> None:
    # preserveQuery=false for /hero-showcase
    resp = client.get("/hero-showcase?utm_source=twitter")
    assert resp.status_code == 301
    assert resp.headers["location"] == "/"


def test_incoming_query_wins_on_key_collision() -> None:
    # /football redirects to /matchs?sport=foot. If the user already supplies
    # sport=nhl we respect their choice (same semantics as the React helper).
    resp = client.get("/football?sport=nhl")
    assert resp.status_code == 301
    loc = resp.headers["location"]
    params = dict(parse_qsl(loc.split("?", 1)[1]))
    assert params.get("sport") == "nhl"


# ─── Negative cases ────────────────────────────────────────────────


def test_non_legacy_route_not_redirected() -> None:
    # /matchs is a V2 route handled by a real router — must NOT be redirected.
    # We don't assert on 200 because /matchs returns 401 without auth, but
    # whatever it returns it should not be a 3xx to another legacy target.
    resp = client.get("/matchs")
    assert resp.status_code != 301


def test_health_endpoint_not_redirected() -> None:
    resp = client.get("/health")
    assert resp.status_code != 301


def test_trailing_path_on_legacy_static_does_not_match() -> None:
    # /paris-du-soir/extra is NOT a documented legacy route. Must NOT redirect.
    resp = client.get("/paris-du-soir/something-else")
    assert resp.status_code != 301
