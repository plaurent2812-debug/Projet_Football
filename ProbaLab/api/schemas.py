"""
api/schemas.py — Pydantic models for API request validation.

Replaces raw `dict` parameters with typed, validated models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ─── Email Endpoints ─────────────────────────────────────────────

class EmailPayload(BaseModel):
    email: str = Field(..., max_length=320, description="Recipient email address")
    name: str | None = Field(None, max_length=200, description="Recipient name (optional)")


# ─── Best Bets ───────────────────────────────────────────────────

class SaveBetRequest(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date YYYY-MM-DD")
    sport: Literal["football", "nhl"] = Field(..., description="'football' or 'nhl'")
    label: str = Field(..., max_length=500, description="Bet description label")
    market: str = Field(..., max_length=200, description="Bet market type")
    odds: float = Field(..., ge=1.0, le=10000.0, description="Decimal odds")
    confidence: int = Field(..., ge=1, le=10, description="Confidence score 1-10")
    proba_model: float = Field(..., ge=0, le=100, description="Model probability %")
    fixture_id: int | str | None = Field(None, description="Fixture ID (optional)")
    player_name: str | None = Field(None, max_length=200, description="Player name for props")


class UpdateBetResultRequest(BaseModel):
    result: Literal["WIN", "LOSS", "VOID", "PENDING"] = Field(..., description="WIN, LOSS, VOID, or PENDING")
    notes: str = Field("", max_length=1000, description="Optional notes")


# ─── CRON / Pipeline ─────────────────────────────────────────────

class DateRequest(BaseModel):
    date: str | None = Field(None, description="ISO date YYYY-MM-DD (defaults to today)")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                raise ValueError("date must match YYYY-MM-DD format")
        return v


class ResolveBetsRequest(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date YYYY-MM-DD")
    sport: Literal["football", "nhl"] = Field(..., description="'football' or 'nhl'")


class ResolveExpertPicksRequest(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date YYYY-MM-DD")
    sport: Literal["football", "nhl"] | None = Field(None, description="'football' or 'nhl' (optional)")


class RunPipelineRequest(BaseModel):
    mode: Literal["full", "data", "analyze", "results", "nhl"] = Field(
        "full", description="Pipeline mode: full, data, analyze, results, nhl"
    )
