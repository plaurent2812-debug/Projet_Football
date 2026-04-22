"""api/routers/v2/user_notifications.py — Notification rules CRUD (Lot 2 · T07–T10).

Four user-scoped endpoints, all sync (lesson 64):

1. ``GET    /api/user/notifications/rules`` — list the current user's rules.
2. ``POST   /api/user/notifications/rules`` — create a rule (cap 20/user).
3. ``PUT    /api/user/notifications/rules/{rule_id}`` — update a rule.
4. ``DELETE /api/user/notifications/rules/{rule_id}`` — delete a rule.

Each rule is a collection of 1..3 discriminated conditions (``edge_min``,
``league_in``, ``sport``, ``confidence``, ``kickoff_within``,
``bankroll_drawdown``), one or more channels (``telegram|email|push``), and
an ``and``/``or`` logic. Persistence lives in ``notification_rules``
(migration 056) with strict RLS; the router also filters every query on
``user_id = current_user.id`` as a second line of defense.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal, Union
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from api.auth import current_user
from api.rate_limit import _rate_limit
from src.config import supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user/notifications", tags=["notifications"])


# ──────────────────────────────────────────────────────────────────────
# Condition shapes — discriminated union on ``type``
# ──────────────────────────────────────────────────────────────────────


class RuleConditionEdgeMin(BaseModel):
    """Fires when the bet's edge (in %) is at least ``min_pct``."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["edge_min"]
    min_pct: float = Field(..., ge=0, le=100)


class RuleConditionLeagueIn(BaseModel):
    """Fires when the bet's league code is in ``leagues`` (e.g. ``["L1","PL"]``)."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["league_in"]
    leagues: list[str] = Field(..., min_length=1)


class RuleConditionSport(BaseModel):
    """Restricts the rule to one sport."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["sport"]
    sport: Literal["football", "nhl"]


class RuleConditionConfidence(BaseModel):
    """Fires when the bet's confidence bucket matches ``level``."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["confidence"]
    level: Literal["low", "medium", "high"]


class RuleConditionKickoffWithin(BaseModel):
    """Fires when the bet's kickoff is within ``minutes`` from now (1..1440)."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["kickoff_within"]
    minutes: int = Field(..., ge=1, le=1440)


class RuleConditionBankrollDrawdown(BaseModel):
    """Fires when the user's bankroll is down ``pct`` % over the last ``days``."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["bankroll_drawdown"]
    pct: float = Field(..., gt=0, le=100)
    days: int = Field(..., ge=1, le=90)


RuleCondition = Annotated[
    Union[
        RuleConditionEdgeMin,
        RuleConditionLeagueIn,
        RuleConditionSport,
        RuleConditionConfidence,
        RuleConditionKickoffWithin,
        RuleConditionBankrollDrawdown,
    ],
    Field(discriminator="type"),
]


# ──────────────────────────────────────────────────────────────────────
# Rule payloads
# ──────────────────────────────────────────────────────────────────────


class NotificationRuleCreate(BaseModel):
    """Request body for POST and PUT.

    Invariants enforced at the model level:
    - ``name`` 1..100 chars.
    - ``conditions`` between 1 and 3 (max 3 enforced app-side; DB schema is
      unconstrained so adding a 4th via SQL is still blocked here).
    - ``channels`` at least one of ``telegram|email|push``.
    - ``extra="forbid"`` — unknown keys rejected.
    """

    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=100)
    conditions: list[RuleCondition] = Field(..., min_length=1, max_length=3)
    logic: Literal["and", "or"] = "and"
    channels: list[Literal["telegram", "email", "push"]] = Field(..., min_length=1)
    secondary_actions: list[str] = Field(default_factory=list)
    enabled: bool = True


class NotificationRuleOut(BaseModel):
    """Row shape returned by the route. Mirrors the table + generated columns."""

    model_config = ConfigDict(extra="allow")
    id: str
    user_id: str
    name: str
    conditions: list[dict[str, Any]]
    logic: Literal["and", "or"]
    channels: list[str]
    secondary_actions: list[str]
    enabled: bool
    created_at: str
    updated_at: str


class RulesListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[NotificationRuleOut]


# ──────────────────────────────────────────────────────────────────────
# Limits
# ──────────────────────────────────────────────────────────────────────

_MAX_RULES_PER_USER = 20


# ──────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/rules",
    response_model=RulesListResponse,
    summary="List the current user's notification rules (newest first).",
)
@_rate_limit("60/minute")
def list_rules(
    request: Request,
    user: dict = Depends(current_user),
) -> dict[str, list[dict[str, Any]]]:
    """Return every rule owned by ``current_user``, ordered by ``created_at DESC``."""
    try:
        rows = (
            supabase.table("notification_rules")
            .select("*")
            .eq("user_id", user["id"])
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("list_rules: lookup failed for user=%s", user.get("id"))
        rows = []

    return {"rules": rows}


@router.post(
    "/rules",
    response_model=NotificationRuleOut,
    status_code=201,
    summary="Create a notification rule (cap 20 per user).",
)
@_rate_limit("30/minute")
def create_rule(
    request: Request,
    payload: NotificationRuleCreate = Body(...),
    user: dict = Depends(current_user),
) -> dict[str, Any]:
    """Insert a new rule for ``current_user`` after enforcing the per-user cap.

    ``user_id`` is injected from the authenticated context, never read from
    the body. RLS (migration 056) repeats the same check in-DB.
    """
    # Per-user cap — fail fast with a 409 before touching the insert path.
    try:
        count_result = (
            supabase.table("notification_rules")
            .select("id", count="exact")
            .eq("user_id", user["id"])
            .execute()
        )
        current_count = getattr(count_result, "count", 0) or 0
    except Exception:
        logger.exception(
            "create_rule: count lookup failed for user=%s", user.get("id")
        )
        current_count = 0

    if current_count >= _MAX_RULES_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=f"Rule cap reached ({_MAX_RULES_PER_USER} per user)",
        )

    record = payload.model_dump()
    record["user_id"] = user["id"]

    try:
        res = supabase.table("notification_rules").insert(record).execute()
    except Exception:
        logger.exception("create_rule: insert failed for user=%s", user.get("id"))
        raise HTTPException(status_code=500, detail="rule_insert_failed")

    data = getattr(res, "data", None) or []
    if not data:
        raise HTTPException(status_code=500, detail="rule_insert_failed")

    return data[0]


@router.put(
    "/rules/{rule_id}",
    response_model=NotificationRuleOut,
    summary="Update a notification rule owned by the current user.",
)
@_rate_limit("30/minute")
def update_rule(
    request: Request,
    rule_id: UUID = Path(...),
    payload: NotificationRuleCreate = Body(...),
    user: dict = Depends(current_user),
) -> dict[str, Any]:
    """Replace a rule. Returns 404 if the row is missing or owned by someone else."""
    try:
        res = (
            supabase.table("notification_rules")
            .update(payload.model_dump())
            .eq("id", str(rule_id))
            .eq("user_id", user["id"])
            .execute()
        )
    except Exception:
        logger.exception("update_rule: update failed for user=%s", user.get("id"))
        raise HTTPException(status_code=500, detail="rule_update_failed")

    data = getattr(res, "data", None) or []
    if not data:
        raise HTTPException(status_code=404, detail="rule_not_found")

    return data[0]


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
    summary="Delete a notification rule owned by the current user.",
)
@_rate_limit("30/minute")
def delete_rule(
    request: Request,
    rule_id: UUID = Path(...),
    user: dict = Depends(current_user),
) -> None:
    """Delete a rule. Returns 204 on success, 404 if missing / foreign.

    We pair ``status_code=204`` with ``response_class=Response`` so FastAPI
    does not attempt to build a JSON body from the ``None`` return (which
    would violate the 204 contract).
    """
    try:
        res = (
            supabase.table("notification_rules")
            .delete()
            .eq("id", str(rule_id))
            .eq("user_id", user["id"])
            .execute()
        )
    except Exception:
        logger.exception("delete_rule: delete failed for user=%s", user.get("id"))
        raise HTTPException(status_code=500, detail="rule_delete_failed")

    data = getattr(res, "data", None) or []
    if not data:
        raise HTTPException(status_code=404, detail="rule_not_found")

    return None


__all__ = [
    "NotificationRuleCreate",
    "NotificationRuleOut",
    "RuleCondition",
    "RuleConditionBankrollDrawdown",
    "RuleConditionConfidence",
    "RuleConditionEdgeMin",
    "RuleConditionKickoffWithin",
    "RuleConditionLeagueIn",
    "RuleConditionSport",
    "RulesListResponse",
    "create_rule",
    "delete_rule",
    "list_rules",
    "router",
    "update_rule",
]
