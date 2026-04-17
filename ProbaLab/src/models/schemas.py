from __future__ import annotations

"""
schemas.py — Pydantic validation models for API-Football responses.

Validates the structure of external API responses to catch upstream
schema changes early, before they cause silent data corruption.

Usage:
    from src.models.schemas import validate_fixture_response
    data = api_get("fixtures", {"id": 12345})
    validated = validate_fixture_response(data)
"""


from typing import Any

from pydantic import BaseModel, Field, ValidationError

from src.config import logger

# ═══════════════════════════════════════════════════════════════════
#  API-Football Response Schemas
# ═══════════════════════════════════════════════════════════════════


class APITeamRef(BaseModel):
    """Minimal team reference in an API response."""

    id: int
    name: str
    logo: str | None = None


class APIFixtureInfo(BaseModel):
    """Fixture metadata from the API."""

    id: int
    date: str
    status: dict[str, Any] | None = None
    venue: dict[str, Any] | None = None
    referee: str | None = None


class APIGoals(BaseModel):
    """Goals sub-object."""

    home: int | None = None
    away: int | None = None


class APIFixtureItem(BaseModel):
    """A single fixture item from /fixtures endpoint."""

    fixture: APIFixtureInfo
    league: dict[str, Any]
    teams: dict[str, APITeamRef]
    goals: APIGoals
    score: dict[str, Any] | None = None


class APIFixtureResponse(BaseModel):
    """Top-level response from /fixtures."""

    results: int | None = None
    response: list[APIFixtureItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
#  Standings
# ═══════════════════════════════════════════════════════════════════


class APIStandingTeam(BaseModel):
    """Team data within a standings row."""

    id: int
    name: str


class APIStandingAll(BaseModel):
    """Aggregated stats for a standing entry."""

    played: int = 0
    win: int = 0
    draw: int = 0
    lose: int = 0
    goals: dict[str, int] = Field(default_factory=dict)


class APIStandingRow(BaseModel):
    """A single row in a league standing."""

    rank: int
    team: APIStandingTeam
    points: int = 0
    goalsDiff: int = Field(default=0, alias="goalsDiff")  # noqa: N815 — matches API-Football field name
    all: APIStandingAll | None = None
    home: APIStandingAll | None = None
    away: APIStandingAll | None = None

    class Config:
        populate_by_name = True


# ═══════════════════════════════════════════════════════════════════
#  Odds
# ═══════════════════════════════════════════════════════════════════


class APIOddValue(BaseModel):
    """A single odd value (e.g. Home: 1.85)."""

    value: str
    odd: str


class APIOddBet(BaseModel):
    """A bet type with its values."""

    id: int | None = None
    name: str
    values: list[APIOddValue] = Field(default_factory=list)


class APIOddBookmaker(BaseModel):
    """A bookmaker with its bets."""

    id: int | None = None
    name: str
    bets: list[APIOddBet] = Field(default_factory=list)


class APIOddItem(BaseModel):
    """A single odds response item."""

    league: dict[str, Any] | None = None
    fixture: dict[str, Any] | None = None
    bookmakers: list[APIOddBookmaker] = Field(default_factory=list)


class APIOddsResponse(BaseModel):
    """Top-level response from /odds."""

    results: int | None = None
    response: list[APIOddItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
#  Injuries
# ═══════════════════════════════════════════════════════════════════


class APIInjuryPlayer(BaseModel):
    """Player info within an injury report."""

    id: int | None = None
    name: str | None = None
    type: str | None = None
    reason: str | None = None


class APIInjuryItem(BaseModel):
    """A single injury response item."""

    player: APIInjuryPlayer
    team: dict[str, Any]
    fixture: dict[str, Any]


class APIInjuryResponse(BaseModel):
    """Top-level response from /injuries."""

    results: int | None = None
    response: list[APIInjuryItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
#  Validation Helpers
# ═══════════════════════════════════════════════════════════════════


def validate_fixture_response(data: dict | None) -> APIFixtureResponse | None:
    """Validate an API-Football /fixtures response.

    Returns the validated model or ``None`` if validation fails.
    Logs validation errors but does not raise.
    """
    if not data:
        return None
    try:
        return APIFixtureResponse(**data)
    except ValidationError as e:
        logger.warning("Fixture response validation failed: %s", e.error_count())
        return None


def validate_odds_response(data: dict | None) -> APIOddsResponse | None:
    """Validate an API-Football /odds response."""
    if not data:
        return None
    try:
        return APIOddsResponse(**data)
    except ValidationError as e:
        logger.warning("Odds response validation failed: %s", e.error_count())
        return None


def validate_injury_response(data: dict | None) -> APIInjuryResponse | None:
    """Validate an API-Football /injuries response."""
    if not data:
        return None
    try:
        return APIInjuryResponse(**data)
    except ValidationError as e:
        logger.warning("Injury response validation failed: %s", e.error_count())
        return None
