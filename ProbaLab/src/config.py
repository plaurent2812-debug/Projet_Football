from __future__ import annotations

"""
Configuration partagée pour tous les scripts du projet Football IA.
"""
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from supabase import Client, create_client


# ── Logging structuré ────────────────────────────────────────────
def setup_logger(name: str = "football_ia", level: int = logging.INFO) -> logging.Logger:
    """Create (or retrieve) a timestamped console logger.

    If the logger already has handlers attached, no new handler is added
    so that duplicate output is avoided when called multiple times.

    Args:
        name: Logger name passed to :func:`logging.getLogger`.
        level: Logging level (e.g. ``logging.INFO``, ``logging.DEBUG``).

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    log: logging.Logger = logging.getLogger(name)
    if not log.handlers:
        handler: logging.StreamHandler = logging.StreamHandler()
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.setLevel(level)
    return log


logger: logging.Logger = setup_logger()

# ── Chargement .env ──────────────────────────────────────────────
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
API_FOOTBALL_KEY: str | None = os.getenv("API_FOOTBALL_KEY")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# ── Client Supabase ──────────────────────────────────────────────
supabase: Client = create_client(SUPABASE_URL or "", SUPABASE_KEY or "")

# ── Moteur V2 (A/B Testing) ──────────────────────────────────────
USE_V2_STACK: bool = True

# ── Ligues suivies ───────────────────────────────────────────────
LEAGUES: list[dict[str, int | str]] = [
    {"id": 61, "name": "Ligue 1", "country": "France"},
    {"id": 62, "name": "Ligue 2", "country": "France"},
    {"id": 39, "name": "Premier League", "country": "England"},
    {"id": 140, "name": "La Liga", "country": "Spain"},
    {"id": 135, "name": "Serie A", "country": "Italy"},
    {"id": 78, "name": "Bundesliga", "country": "Germany"},
    {"id": 2, "name": "Champions League", "country": "World"},
    {"id": 3, "name": "Europa League", "country": "World"},
    # Coupes nationales
    {"id": 66, "name": "Coupe de France", "country": "France"},
    {"id": 45, "name": "FA Cup", "country": "England"},
    {"id": 143, "name": "Copa del Rey", "country": "Spain"},
    {"id": 137, "name": "Coppa Italia", "country": "Italy"},
    {"id": 81, "name": "DFB-Pokal", "country": "Germany"},
]


def _get_current_season() -> int:
    """Determine the current football season year.

    Most European leagues start in August. The season year is the
    calendar year the season started in (e.g. 2025 for 2025-26).
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return now.year if now.month >= 8 else now.year - 1


SEASON: int = int(os.getenv("FOOTBALL_SEASON", str(_get_current_season())))

# ── API-Football ─────────────────────────────────────────────────
API_BASE_URL: str = "https://v3.football.api-sports.io"
API_HEADERS: dict[str, str | None] = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_FOOTBALL_KEY,
}

# Compteur de requêtes pour monitoring
_request_count: int = 0


# Retry configuration
API_MAX_RETRIES: int = 3
API_BACKOFF_DELAYS: list[float] = [1.0, 3.0, 10.0]


def api_get(endpoint: str, params: dict | None = None) -> dict | None:
    """Perform a GET request against the API-Football v3 endpoint.

    Includes automatic rate-limiting (0.25 s sleep after each call) to
    stay within the 300 req/min quota of the Pro plan, retries with
    exponential backoff on 429/5xx errors and network failures, and logs
    HTTP or API-level errors.

    Args:
        endpoint: API path appended to :data:`API_BASE_URL`
            (e.g. ``"fixtures"``).
        params: Optional query-string parameters forwarded to
            :func:`requests.get`.

    Returns:
        Parsed JSON response as a dict, or ``None`` on error.
    """
    global _request_count
    url: str = f"{API_BASE_URL}/{endpoint}"

    for attempt in range(API_MAX_RETRIES + 1):
        try:
            request_params = params or {}

            resp: requests.Response = requests.get(
                url, headers=API_HEADERS, params=request_params, timeout=15
            )
            _request_count += 1

            # Retry on rate limit
            if resp.status_code == 429:
                if attempt < API_MAX_RETRIES:
                    delay = API_BACKOFF_DELAYS[min(attempt, len(API_BACKOFF_DELAYS) - 1)]
                    logger.warning(
                        "Rate limited (429) on %s, retrying in %.0fs...", endpoint, delay
                    )
                    time.sleep(delay)
                    continue
                logger.error("Rate limited (429) on %s after %d retries", endpoint, API_MAX_RETRIES)
                return None

            # Retry on server error
            if resp.status_code >= 500:
                if attempt < API_MAX_RETRIES:
                    delay = API_BACKOFF_DELAYS[min(attempt, len(API_BACKOFF_DELAYS) - 1)]
                    logger.warning(
                        "Server error %d on %s, retrying in %.0fs...",
                        resp.status_code,
                        endpoint,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                logger.error(
                    "Server error %d on %s after %d retries",
                    resp.status_code,
                    endpoint,
                    API_MAX_RETRIES,
                )
                return None

            # Non-retryable HTTP error
            if resp.status_code != 200:
                logger.error("HTTP %d sur %s", resp.status_code, endpoint)
                return None

            data: dict = resp.json()

            # Check API-level errors
            if "errors" in data and data["errors"]:
                errors = data["errors"]
                if isinstance(errors, dict) and errors or isinstance(errors, list) and errors:
                    logger.error("API-Football: %s", errors)
                    return None

            # Rate limiting : ~5 req/sec max pour rester safe
            time.sleep(0.25)
            return data

        except requests.exceptions.RequestException as e:
            if attempt < API_MAX_RETRIES:
                delay = API_BACKOFF_DELAYS[min(attempt, len(API_BACKOFF_DELAYS) - 1)]
                logger.warning("Request error on %s: %s, retrying in %.0fs...", endpoint, e, delay)
                time.sleep(delay)
            else:
                logger.error(
                    "Request failed on %s after %d retries: %s", endpoint, API_MAX_RETRIES, e
                )
                return None

    return None  # Should not reach here


def api_get_with_retry(
    endpoint: str, params: dict, max_retries: int = 2, label: str = ""
) -> dict | None:
    """Wrapper around api_get with additional retry for empty responses.

    api_get already handles HTTP 429/5xx retries and network errors.
    This adds a second retry layer for cases where the API returns a
    successful HTTP 200 but with an empty ``response`` list — common
    for events, lineups, odds, and h2h endpoints during data propagation
    delays on the API-Football side.

    Args:
        endpoint: API path (e.g. ``"fixtures/events"``).
        params: Query-string parameters.
        max_retries: Number of additional attempts on empty response.
        label: Human-readable label for log messages.

    Returns:
        Parsed JSON dict, or the last (possibly empty) response on failure.
    """
    for attempt in range(max_retries + 1):
        data = api_get(endpoint, params)
        if data and data.get("response"):
            return data
        if attempt < max_retries:
            delay = 2 ** attempt  # 1s, 2s
            logger.warning(
                "Empty response for %s (attempt %d/%d), retrying in %ds...",
                label or endpoint,
                attempt + 1,
                max_retries + 1,
                delay,
            )
            time.sleep(delay)
    logger.error("All %d attempts failed for %s", max_retries + 1, label or endpoint)
    return data  # Return last response (even if empty)


def get_request_count() -> int:
    """Return the cumulative number of API-Football requests made.

    Returns:
        Request count since the last :func:`reset_request_count` call
        (or since module import).
    """
    return _request_count


def reset_request_count() -> None:
    """Reset the API-Football request counter to zero.

    Returns:
        None.
    """
    global _request_count
    _request_count = 0
