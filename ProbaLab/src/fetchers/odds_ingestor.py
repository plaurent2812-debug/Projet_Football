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
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from src.config import supabase
from src.fetchers.bookmaker_registry import (
    BOOKMAKERS_FR,
    ODDS_API_KEY_BY_BOOKMAKER,
    SPORT_KEYS,
    get_bookmaker_from_api_key,
    teams_match,
)

logger = logging.getLogger("football_ia.odds_ingestor")


def _resolve_fixture_id(
    sport: str,
    home_team: str,
    away_team: str,
    match_start_utc: datetime,
) -> str | None:
    """Résout (home_team, away_team, kickoff) → fixtures.id interne.

    Returns str(fixtures.id) pour compat avec closing_odds.fixture_id TEXT,
    ou None si aucun match trouvé dans ±24h. Fallback lesson 69 via teams_match.
    """
    window_start = (match_start_utc - timedelta(days=1)).isoformat()
    window_end = (match_start_utc + timedelta(days=1)).isoformat()

    table = "fixtures" if sport == "football" else "nhl_fixtures"
    date_col = "date" if sport == "football" else "game_date"
    id_col = "id" if sport == "football" else "game_id"

    try:
        rows = (
            supabase.table(table)
            .select(f"{id_col},home_team,away_team,{date_col}")
            .gte(date_col, window_start)
            .lt(date_col, window_end)
            .execute()
            .data
        ) or []
    except Exception:
        logger.exception(
            "[_resolve_fixture_id] load failed sport=%s home=%s away=%s",
            sport, home_team, away_team,
        )
        return None

    for row in rows:
        db_home = row.get("home_team", "")
        db_away = row.get("away_team", "")
        if teams_match(home_team, db_home) and teams_match(away_team, db_away):
            return str(row[id_col])

    return None


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
    """Retourne [(selection, odds), ...] pour un marché h2h (1X2 foot).

    Matching tolérant via teams_match pour robustesse cross-provider (lesson 69).
    """
    out: list[tuple[str, float]] = []
    for o in outcomes:
        name = o.get("name", "")
        price = float(o["price"])
        if teams_match(name, home_team):
            out.append(("home", price))
        elif teams_match(name, away_team):
            out.append(("away", price))
        elif name.strip().lower() == "draw":
            out.append(("draw", price))
    return out


def _build_row(
    sport: str,
    fixture_id: str,
    match_start: datetime,
    bookmaker: str,
    market: str,
    selection: str,
    line: float | None,
    odds: float,
    overround: float,
    snapshot_type: str,
    source_request_id: str,
) -> dict:
    return {
        "sport": sport,
        "fixture_id": fixture_id,
        "match_start": match_start,
        "bookmaker": bookmaker,
        "market": market,
        "selection": selection,
        "line": line,
        "odds": odds,
        "implied_prob": to_implied_prob(odds),
        "overround": overround,
        "snapshot_type": snapshot_type,
        "source_request_id": source_request_id,
    }


def _totals_football_market(line: float) -> str | None:
    mapping = {1.5: "over_1_5", 2.5: "over_2_5", 3.5: "over_3_5"}
    return mapping.get(line)


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
        odds_api_event_id = str(event["id"])
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        raw_commence = event["commence_time"]
        parsed_commence = datetime.fromisoformat(raw_commence.replace("Z", "+00:00"))
        if parsed_commence.tzinfo is None:
            raise ValueError(
                f"commence_time must be timezone-aware: {raw_commence!r}"
            )
        match_start = parsed_commence.astimezone(timezone.utc)

        fixture_id = _resolve_fixture_id(sport, home_team, away_team, match_start)
        if fixture_id is None:
            logger.debug(
                "[parse_odds_response] unresolved event=%s home=%s away=%s kickoff=%s",
                odds_api_event_id, home_team, away_team, match_start.isoformat(),
            )
            continue

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
                        rows.append(_build_row(
                            sport, fixture_id, match_start, bk, "1x2",
                            selection, None, odds, overround, snapshot_type,
                            source_request_id,
                        ))

                elif mkey == "h2h" and sport == "nhl":
                    parsed_nhl: list[tuple[str, float]] = []
                    for o in outcomes:
                        nm = o.get("name", "")
                        if teams_match(nm, home_team):
                            parsed_nhl.append(("home", float(o["price"])))
                        elif teams_match(nm, away_team):
                            parsed_nhl.append(("away", float(o["price"])))
                    if len(parsed_nhl) != 2:
                        continue
                    overround = sum(to_implied_prob(p) for _, p in parsed_nhl)
                    for selection, odds in parsed_nhl:
                        rows.append(_build_row(
                            sport, fixture_id, match_start, bk, "moneyline",
                            selection, None, odds, overround, snapshot_type,
                            source_request_id,
                        ))

                elif mkey == "btts":
                    btts_parsed = []
                    for o in outcomes:
                        nm = o["name"].lower()
                        if nm in ("yes", "no"):
                            btts_parsed.append((nm, float(o["price"])))
                    if len(btts_parsed) != 2:
                        continue
                    overround = sum(to_implied_prob(p) for _, p in btts_parsed)
                    for selection, odds in btts_parsed:
                        rows.append(_build_row(
                            sport, fixture_id, match_start, bk, "btts",
                            selection, None, odds, overround, snapshot_type,
                            source_request_id,
                        ))

                elif mkey == "totals":
                    by_line: dict[float, list[tuple[str, float]]] = {}
                    for o in outcomes:
                        nm = o["name"].lower()
                        if nm not in ("over", "under"):
                            continue
                        raw_point = o.get("point")
                        if raw_point is None:
                            continue
                        point = float(raw_point)
                        if point <= 0:
                            continue
                        by_line.setdefault(point, []).append((nm, float(o["price"])))
                    for line, pair in by_line.items():
                        if len(pair) != 2:
                            continue
                        overround = sum(to_implied_prob(p) for _, p in pair)
                        if sport == "football":
                            market_name = _totals_football_market(line)
                            if market_name is None:
                                continue
                        else:
                            market_name = "totals_nhl"
                        for selection, odds in pair:
                            rows.append(_build_row(
                                sport, fixture_id, match_start, bk, market_name,
                                selection, line, odds, overround, snapshot_type,
                                source_request_id,
                            ))
    return rows


ODDS_API_BASE = "https://api.the-odds-api.com/v4"
_MAX_RETRIES = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]
_HTTP_TIMEOUT = 30.0
_UPSERT_CHUNK = 500

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


def upsert_odds(rows: list[dict]) -> int:
    """Insert rows in closing_odds avec ON CONFLICT DO NOTHING.

    Retourne le nombre de rows soumis (pas le nombre d'inserts réussis —
    Supabase ne renvoie pas le count pour ignore_duplicates=True).
    """
    if not rows:
        return 0

    # Sérialiser datetimes en ISO 8601
    serialized: list[dict] = []
    for r in rows:
        copy = dict(r)
        ms = copy.get("match_start")
        if isinstance(ms, datetime):
            copy["match_start"] = ms.isoformat()
        serialized.append(copy)

    # Each chunk is its own transaction. Partial failures are safe because
    # ignore_duplicates=True makes re-runs idempotent.
    total = 0
    for i in range(0, len(serialized), _UPSERT_CHUNK):
        chunk = serialized[i : i + _UPSERT_CHUNK]
        chunk_idx = i // _UPSERT_CHUNK
        (
            supabase.table("closing_odds")
            .upsert(
                chunk,
                on_conflict="fixture_id,bookmaker,market,selection,line,snapshot_type",
                ignore_duplicates=True,
            )
            .execute()
        )
        logger.debug(
            "upsert_odds chunk=%d rows=%d", chunk_idx, len(chunk)
        )
        total += len(chunk)
    return total


_FOOT_MARKETS = "h2h,btts,totals"
_NHL_MARKETS = "h2h,totals"


def _try_send_telegram(message: str) -> None:
    """Envoi Telegram tolérant (ne bloque jamais le flow principal)."""
    try:
        from src.notifications import send_telegram
        send_telegram(message)
    except Exception:
        logger.exception("[_try_send_telegram] failed to send alert")


def _get_api_key() -> str:
    key = os.getenv("THE_ODDS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("THE_ODDS_API_KEY env var missing")
    return key


def run_snapshot(*, snapshot_type: str) -> int:
    """Fetch + persist cotes pour tous sports/ligues configurés.

    Args:
        snapshot_type: "opening" | "closing" | "intraday"

    Returns:
        Nombre total de rows soumis à upsert (≠ inserts réussis).
    """
    api_key = _get_api_key()
    bookmakers_param = ",".join(
        ODDS_API_KEY_BY_BOOKMAKER[b] for b in BOOKMAKERS_FR
    )
    request_id = f"{snapshot_type}-{uuid.uuid4().hex[:12]}"
    total_rows = 0

    total_sport_keys_attempted = 0
    failures = 0
    for sport, sport_keys in SPORT_KEYS.items():
        markets = _FOOT_MARKETS if sport == "football" else _NHL_MARKETS
        for sport_key in sport_keys:
            total_sport_keys_attempted += 1
            try:
                events = fetch_odds(
                    sport_key=sport_key,
                    markets=markets,
                    api_key=api_key,
                    bookmakers=bookmakers_param,
                )
            except OddsAPIQuotaExhausted as exc:
                logger.critical(
                    "[odds_ingestor] Quota exhausted, stopping snapshot: %s", exc
                )
                _try_send_telegram(
                    f"\U0001f534 <b>CRITICAL — The Odds API quota exhausted</b>\n"
                    f"snapshot_type={snapshot_type}\n"
                    f"Arrêt de l'ingestion jusqu'au prochain cycle mensuel."
                )
                return total_rows
            except Exception as exc:
                failures += 1
                logger.exception(
                    "[odds_ingestor] fetch failed sport_key=%s err=%s",
                    sport_key, exc,
                )
                continue

            rows = parse_odds_response(
                events,
                sport=sport,
                snapshot_type=snapshot_type,
                source_request_id=request_id,
            )
            if rows:
                upsert_odds(rows)
                total_rows += len(rows)
                logger.info(
                    "[odds_ingestor] sport_key=%s rows=%d", sport_key, len(rows)
                )

    if total_sport_keys_attempted > 0 and failures == total_sport_keys_attempted:
        _try_send_telegram(
            f"\U0001f534 <b>CRITICAL — Odds snapshot total failure</b>\n"
            f"snapshot_type={snapshot_type}\n"
            f"All {total_sport_keys_attempted} sport_keys failed. Check logs."
        )
        raise RuntimeError(
            f"run_snapshot failed on all {total_sport_keys_attempted} sport_keys"
        )
    return total_rows


def run_snapshot_for_fixtures(fixture_ids: list[str]) -> int:
    """Closing snapshot ciblé sur une liste de fixture_ids (appelé par date trigger).

    Ne capture que les cotes dont l'event id est dans fixture_ids.
    Utilise `snapshot_type='closing'` et marque les rows.
    """
    if not fixture_ids:
        return 0

    api_key = _get_api_key()
    bookmakers_param = ",".join(
        ODDS_API_KEY_BY_BOOKMAKER[b] for b in BOOKMAKERS_FR
    )
    request_id = f"closing-{uuid.uuid4().hex[:12]}"
    fixture_ids_set = {str(f) for f in fixture_ids}
    total_rows = 0

    for sport, sport_keys in SPORT_KEYS.items():
        markets = _FOOT_MARKETS if sport == "football" else _NHL_MARKETS
        for sport_key in sport_keys:
            try:
                events = fetch_odds(
                    sport_key=sport_key,
                    markets=markets,
                    api_key=api_key,
                    bookmakers=bookmakers_param,
                )
            except OddsAPIQuotaExhausted as exc:
                logger.critical(
                    "[odds_ingestor] closing quota exhausted: %s", exc
                )
                _try_send_telegram(
                    f"\U0001f534 <b>CRITICAL — Quota exhausted on closing snapshot</b>\n{exc}"
                )
                return total_rows
            except Exception as exc:
                logger.exception(
                    "[odds_ingestor] closing fetch failed sport_key=%s err=%s",
                    sport_key, exc,
                )
                continue

            # Parse first, then filter by resolved internal fixture_id.
            # The Odds API event UUID != fixtures.id, so filtering on e["id"]
            # would never match the internal IDs passed to this function.
            rows = parse_odds_response(
                events,
                sport=sport,
                snapshot_type="closing",
                source_request_id=request_id,
            )
            rows = [r for r in rows if r["fixture_id"] in fixture_ids_set]
            if not rows:
                continue

            upsert_odds(rows)
            total_rows += len(rows)
            logger.info(
                "[odds_ingestor] closing sport_key=%s rows=%d",
                sport_key, len(rows),
            )
    return total_rows


def _load_today_fixtures_for_closing() -> list[dict]:
    """Charge les fixtures (foot + NHL) dont kickoff est dans les prochaines 24h UTC.

    Retourne [{fixture_id: str, kickoff_utc: datetime}, ...].
    """
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=24)

    out: list[dict] = []
    # Football fixtures — utilise fixtures.id (interne) pour matcher closing_odds.fixture_id
    try:
        rows = (
            supabase.table("fixtures")
            .select("id,date")
            .gte("date", now.isoformat())
            .lt("date", horizon.isoformat())
            .execute()
            .data
        ) or []
        for r in rows:
            if not r.get("date") or not r.get("id"):
                continue
            k = datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00"))
            if k.tzinfo is None:
                continue
            out.append({
                "fixture_id": str(r["id"]),
                "kickoff_utc": k.astimezone(timezone.utc),
            })
    except Exception:
        logger.exception("[_load_today_fixtures_for_closing] football load failed")

    # NHL fixtures — utilise game_id (matche le resolver _resolve_fixture_id)
    try:
        rows = (
            supabase.table("nhl_fixtures")
            .select("game_id,game_date")
            .gte("game_date", now.isoformat())
            .lt("game_date", horizon.isoformat())
            .execute()
            .data
        ) or []
        for r in rows:
            if not r.get("game_date") or not r.get("game_id"):
                continue
            k = datetime.fromisoformat(str(r["game_date"]).replace("Z", "+00:00"))
            if k.tzinfo is None:
                continue
            out.append({
                "fixture_id": str(r["game_id"]),
                "kickoff_utc": k.astimezone(timezone.utc),
            })
    except Exception:
        logger.exception("[_load_today_fixtures_for_closing] nhl load failed")

    return out


def schedule_closing_snapshots_for_today(scheduler) -> int:
    """Enregistre des date-triggers T-30min pour chaque fixture de la journée.

    Appelé par job_schedule_closing_snapshots à 10:15 UTC après job_brain.
    Dedup via id='closing_<fixture_id>' + replace_existing=True.

    Returns: nombre de jobs planifiés.
    """
    fixtures = _load_today_fixtures_for_closing()
    if not fixtures:
        logger.info("[schedule_closing_snapshots] no fixtures in next 24h")
        return 0

    now = datetime.now(timezone.utc)
    scheduled = 0
    for fx in fixtures:
        trigger_at = fx["kickoff_utc"] - timedelta(minutes=30)
        if trigger_at <= now:
            # Match already started / very close; skip
            logger.debug(
                "[schedule_closing_snapshots] skip past trigger fixture=%s kickoff=%s",
                fx["fixture_id"], fx["kickoff_utc"],
            )
            continue
        job_id = f"closing_{fx['fixture_id']}"
        try:
            scheduler.add_job(
                run_snapshot_for_fixtures,
                trigger="date",
                run_date=trigger_at,
                args=[[fx["fixture_id"]]],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=120,
            )
            scheduled += 1
        except Exception:
            logger.exception(
                "[schedule_closing_snapshots] failed to add job for fixture=%s",
                fx["fixture_id"],
            )
    logger.info(
        "[schedule_closing_snapshots] scheduled=%d over %d fixtures",
        scheduled, len(fixtures),
    )
    return scheduled
