"""Client The Odds API Dev — ingestion cotes bookmakers FR + Pinnacle.

Responsabilités :
    - fetch /v4/sports/{sport}/odds avec retry + circuit breaker
    - parsing JSON → rows canoniques (one row par bookmaker × marché × selection)
    - dedup via UNIQUE constraint on closing_odds
    - quota tracking (x-requests-remaining header)

Module pur (parsing + helpers) + fonctions I/O (fetch, upsert).
Les fonctions I/O utilisent supabase + httpx ; les helpers sont testables sans réseau.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from src.fetchers.bookmaker_registry import get_bookmaker_from_api_key

logger = logging.getLogger("football_ia.odds_ingestor")


class OddsAPIQuotaExhausted(Exception):  # noqa: N818 — nom contractuel (cf. spec H2-SS1)
    """Levée quand The Odds API signale le quota mensuel dépassé."""


def to_implied_prob(odds: float) -> float:
    """Décimal → proba implicite (sans retrait overround)."""
    if odds < 1.01:
        raise ValueError(f"Invalid decimal odds: {odds} (must be >= 1.01)")
    return 1.0 / odds


def _parse_h2h_market(
    outcomes: list[dict], home_team: str, away_team: str
) -> list[tuple[str, float]]:
    """Retourne [(selection, odds), ...] pour un marché h2h (1X2 foot)."""
    out: list[tuple[str, float]] = []
    for o in outcomes:
        name = o["name"]
        price = float(o["price"])
        if name == home_team:
            out.append(("home", price))
        elif name == away_team:
            out.append(("away", price))
        elif name.lower() == "draw":
            out.append(("draw", price))
    return out


def parse_odds_response(
    events: list[dict],
    *,
    sport: str,
    snapshot_type: str,
    source_request_id: str,
) -> list[dict]:
    """Parse la réponse JSON The Odds API → rows canoniques pour closing_odds.

    Args:
        events: liste d'events telle que retournée par /v4/sports/{sport}/odds
        sport: "football" | "nhl"
        snapshot_type: "opening" | "closing" | "intraday"
        source_request_id: identifiant idempotent (UUID ou composite)

    Returns:
        Liste de dicts insérables dans closing_odds. Bookmakers inconnus sont skippés.
    """
    rows: list[dict] = []
    for event in events:
        fixture_id = str(event["id"])
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        raw_commence = event["commence_time"]
        parsed_commence = datetime.fromisoformat(raw_commence.replace("Z", "+00:00"))
        if parsed_commence.tzinfo is None:
            raise ValueError(
                f"commence_time must be timezone-aware: {raw_commence!r}"
            )
        match_start = parsed_commence.astimezone(timezone.utc)

        for bk_block in event.get("bookmakers", []):
            bk = get_bookmaker_from_api_key(bk_block["key"])
            if bk is None:
                continue  # skip bookmakers hors registre
            for market_block in bk_block.get("markets", []):
                mkey = market_block["key"]
                outcomes = market_block.get("outcomes", [])
                if mkey == "h2h" and sport == "football":
                    parsed = _parse_h2h_market(outcomes, home_team, away_team)
                    if len(parsed) != 3:
                        continue
                    overround = sum(to_implied_prob(p) for _, p in parsed)
                    for selection, odds in parsed:
                        rows.append(
                            {
                                "sport": sport,
                                "fixture_id": fixture_id,
                                "match_start": match_start,
                                "bookmaker": bk,
                                "market": "1x2",
                                "selection": selection,
                                "line": None,
                                "odds": odds,
                                "implied_prob": to_implied_prob(odds),
                                "overround": overround,
                                "snapshot_type": snapshot_type,
                                "source_request_id": source_request_id,
                            }
                        )
                # Marchés BTTS / Over / NHL seront ajoutés Task 5.
    return rows


ODDS_API_BASE = "https://api.the-odds-api.com/v4"
_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]
_HTTP_TIMEOUT = 30.0

assert len(_RETRY_DELAYS) >= _MAX_RETRIES, (
    "_RETRY_DELAYS must have at least _MAX_RETRIES entries"
)


def fetch_odds(
    *,
    sport_key: str,
    markets: str,
    api_key: str,
    bookmakers: str | None = None,
    regions: str = "eu",
    odds_format: str = "decimal",
) -> list[dict]:
    """Fetch /v4/sports/{sport_key}/odds avec retry exponential.

    Raises:
        OddsAPIQuotaExhausted: si 429 ou header x-requests-remaining=0
        RuntimeError: après _MAX_RETRIES échecs consécutifs
    """
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params: dict[str, Any] = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = httpx.get(url, params=params, timeout=_HTTP_TIMEOUT)
        except Exception as exc:
            last_error = exc
            logger.warning("fetch_odds attempt %d exception: %s", attempt + 1, exc)
            time.sleep(_RETRY_DELAYS[attempt])
            continue

        if resp.status_code == 429:
            raise OddsAPIQuotaExhausted(
                f"The Odds API quota exhausted for sport={sport_key}"
            )

        if resp.status_code >= 500:
            last_error = RuntimeError(f"HTTP {resp.status_code}")
            logger.warning(
                "fetch_odds attempt %d got %d, retrying",
                attempt + 1,
                resp.status_code,
            )
            time.sleep(_RETRY_DELAYS[attempt])
            continue

        # remaining-header check runs only on 2xx/4xx responses to avoid
        # CDN-stale 0-quota headers on 5xx turning transient errors fatal.
        remaining_header = resp.headers.get("x-requests-remaining")
        if remaining_header is not None and str(remaining_header) == "0":
            raise OddsAPIQuotaExhausted(
                f"x-requests-remaining=0 for sport={sport_key}"
            )

        resp.raise_for_status()
        if remaining_header is not None:
            # defensive: logger misconfig must not fail the happy path
            try:
                logger.info(
                    "The Odds API quota remaining=%s for sport=%s",
                    remaining_header,
                    sport_key,
                )
            except Exception:
                pass
        return resp.json()

    raise RuntimeError(
        f"fetch_odds exhausted retries for sport={sport_key}: {last_error}"
    )
