"""
schemas.py — Pydantic validation models for API-Football responses.

Validates the structure of external API responses to catch upstream
schema changes early, before they cause silent data corruption.

Usage:
    from models.schemas import validate_fixture_response
    data = api_get("fixtures", {"id": 12345})
    validated = validate_fixture_response(data)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from config import logger


# ═══════════════════════════════════════════════════════════════════
#  API-Football Response Schemas
# ═══════════════════════════════════════════════════════════════════


class APITeamRef(BaseModel):
    """Minimal team reference in an API response."""
    id: int
    name: str
    logo: Optional[str] = None


class APIFixtureInfo(BaseModel):
    """Fixture metadata from the API."""
    id: int
    date: str
    status: Optional[Dict[str, Any]] = None
    venue: Optional[Dict[str, Any]] = None
    referee: Optional[str] = None


class APIGoals(BaseModel):
    """Goals sub-object."""
    home: Optional[int] = None
    away: Optional[int] = None


class APIFixtureItem(BaseModel):
    """A single fixture item from /fixtures endpoint."""
    fixture: APIFixtureInfo
    league: Dict[str, Any]
    teams: Dict[str, APITeamRef]
    goals: APIGoals
    score: Optional[Dict[str, Any]] = None


class APIFixtureResponse(BaseModel):
    """Top-level response from /fixtures."""
    results: Optional[int] = None
    response: List[APIFixtureItem] = Field(default_factory=list)


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
    goals: Dict[str, int] = Field(default_factory=dict)


class APIStandingRow(BaseModel):
    """A single row in a league standing."""
    rank: int
    team: APIStandingTeam
    points: int = 0
    goalsDiff: int = Field(default=0, alias="goalsDiff")
    all: Optional[APIStandingAll] = None
    home: Optional[APIStandingAll] = None
    away: Optional[APIStandingAll] = None

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
    id: Optional[int] = None
    name: str
    values: List[APIOddValue] = Field(default_factory=list)


class APIOddBookmaker(BaseModel):
    """A bookmaker with its bets."""
    id: Optional[int] = None
    name: str
    bets: List[APIOddBet] = Field(default_factory=list)


class APIOddItem(BaseModel):
    """A single odds response item."""
    league: Optional[Dict[str, Any]] = None
    fixture: Optional[Dict[str, Any]] = None
    bookmakers: List[APIOddBookmaker] = Field(default_factory=list)


class APIOddsResponse(BaseModel):
    """Top-level response from /odds."""
    results: Optional[int] = None
    response: List[APIOddItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
#  Injuries
# ═══════════════════════════════════════════════════════════════════


class APIInjuryPlayer(BaseModel):
    """Player info within an injury report."""
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    reason: Optional[str] = None


class APIInjuryItem(BaseModel):
    """A single injury response item."""
    player: APIInjuryPlayer
    team: Dict[str, Any]
    fixture: Dict[str, Any]


class APIInjuryResponse(BaseModel):
    """Top-level response from /injuries."""
    results: Optional[int] = None
    response: List[APIInjuryItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
#  Validation Helpers
# ═══════════════════════════════════════════════════════════════════


def validate_fixture_response(data: Optional[dict]) -> Optional[APIFixtureResponse]:
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


def validate_odds_response(data: Optional[dict]) -> Optional[APIOddsResponse]:
    """Validate an API-Football /odds response."""
    if not data:
        return None
    try:
        return APIOddsResponse(**data)
    except ValidationError as e:
        logger.warning("Odds response validation failed: %s", e.error_count())
        return None


def validate_injury_response(data: Optional[dict]) -> Optional[APIInjuryResponse]:
    """Validate an API-Football /injuries response."""
    if not data:
        return None
    try:
        return APIInjuryResponse(**data)
    except ValidationError as e:
        logger.warning("Injury response validation failed: %s", e.error_count())
        return None
