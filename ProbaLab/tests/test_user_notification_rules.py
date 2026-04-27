"""tests/test_user_notification_rules.py — Notification rules CRUD (Lot 2 · T07–T10).

Covers the strict Pydantic contract (discriminated union on ``type``, max 3
conditions, at least 1 channel, extras forbidden) and the four route handlers
(list/create/update/delete). Everything is sync (lesson 64) and reached via
``__wrapped__`` to bypass the slowapi decorator.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.routers.v2.user_notifications import (
    NotificationRuleCreate,
    RuleConditionBankrollDrawdown,
    RuleConditionConfidence,
    RuleConditionEdgeMin,
    RuleConditionKickoffWithin,
    RuleConditionLeagueIn,
    RuleConditionSport,
    create_rule,
    delete_rule,
    list_rules,
    update_rule,
)

# ═══════════════════════════════════════════════════════════════════
#  Pydantic contract — individual condition types
# ═══════════════════════════════════════════════════════════════════


def test_condition_edge_min_valid():
    cond = RuleConditionEdgeMin(type="edge_min", min_pct=5.0)
    assert cond.min_pct == 5.0


def test_condition_edge_min_rejects_out_of_range():
    with pytest.raises(ValidationError):
        RuleConditionEdgeMin(type="edge_min", min_pct=150.0)
    with pytest.raises(ValidationError):
        RuleConditionEdgeMin(type="edge_min", min_pct=-1.0)


def test_condition_league_in_valid():
    cond = RuleConditionLeagueIn(type="league_in", leagues=["L1", "PL", "UCL"])
    assert cond.leagues == ["L1", "PL", "UCL"]


def test_condition_sport_valid():
    assert RuleConditionSport(type="sport", sport="football").sport == "football"
    assert RuleConditionSport(type="sport", sport="nhl").sport == "nhl"


def test_condition_sport_rejects_unknown():
    with pytest.raises(ValidationError):
        RuleConditionSport(type="sport", sport="tennis")


def test_condition_confidence_valid():
    assert RuleConditionConfidence(type="confidence", level="high").level == "high"


def test_condition_confidence_rejects_invalid_level():
    with pytest.raises(ValidationError):
        RuleConditionConfidence(type="confidence", level="medium-high")


def test_condition_kickoff_within_valid():
    cond = RuleConditionKickoffWithin(type="kickoff_within", minutes=60)
    assert cond.minutes == 60


def test_condition_kickoff_within_enforces_bounds():
    with pytest.raises(ValidationError):
        RuleConditionKickoffWithin(type="kickoff_within", minutes=0)
    with pytest.raises(ValidationError):
        RuleConditionKickoffWithin(type="kickoff_within", minutes=1441)


def test_condition_bankroll_drawdown_valid():
    cond = RuleConditionBankrollDrawdown(type="bankroll_drawdown", pct=10.0, days=7)
    assert cond.pct == 10.0
    assert cond.days == 7


def test_condition_bankroll_drawdown_rejects_zero_pct():
    # pct must be strictly positive (gt=0)
    with pytest.raises(ValidationError):
        RuleConditionBankrollDrawdown(type="bankroll_drawdown", pct=0.0, days=7)


# ═══════════════════════════════════════════════════════════════════
#  Pydantic contract — NotificationRuleCreate
# ═══════════════════════════════════════════════════════════════════


def _valid_payload(**overrides):
    base = {
        "name": "Value foot",
        "conditions": [{"type": "edge_min", "min_pct": 5.0}],
        "logic": "and",
        "channels": ["telegram"],
        "secondary_actions": [],
        "enabled": True,
    }
    base.update(overrides)
    return NotificationRuleCreate(**base)


def test_create_payload_accepts_valid():
    payload = _valid_payload()
    assert payload.name == "Value foot"
    assert len(payload.conditions) == 1
    assert payload.conditions[0].type == "edge_min"


def test_create_payload_requires_at_least_one_condition():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x",
            conditions=[],
            channels=["telegram"],
        )


def test_create_payload_rejects_more_than_3_conditions():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x",
            conditions=[
                {"type": "edge_min", "min_pct": 1.0},
                {"type": "sport", "sport": "football"},
                {"type": "confidence", "level": "high"},
                {"type": "kickoff_within", "minutes": 60},
            ],
            channels=["telegram"],
        )


def test_create_payload_requires_at_least_one_channel():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x",
            conditions=[{"type": "edge_min", "min_pct": 1.0}],
            channels=[],
        )


def test_create_payload_rejects_invalid_channel():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x",
            conditions=[{"type": "edge_min", "min_pct": 1.0}],
            channels=["sms"],
        )


def test_create_payload_rejects_extra_fields():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x",
            conditions=[{"type": "edge_min", "min_pct": 1.0}],
            channels=["telegram"],
            foo="bar",
        )


def test_create_payload_rejects_name_over_100():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x" * 101,
            conditions=[{"type": "edge_min", "min_pct": 1.0}],
            channels=["telegram"],
        )


def test_create_payload_rejects_unknown_condition_type():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="x",
            conditions=[{"type": "nope", "foo": "bar"}],
            channels=["telegram"],
        )


def test_create_payload_discriminator_routes_to_correct_shape():
    """The Union discriminator must validate against the right model."""
    payload = NotificationRuleCreate(
        name="multi",
        conditions=[
            {"type": "edge_min", "min_pct": 3.0},
            {"type": "sport", "sport": "nhl"},
            {"type": "league_in", "leagues": ["UCL"]},
        ],
        channels=["telegram", "email"],
    )
    assert payload.conditions[0].type == "edge_min"
    assert payload.conditions[1].type == "sport"
    assert payload.conditions[2].type == "league_in"


# ═══════════════════════════════════════════════════════════════════
#  GET /rules
# ═══════════════════════════════════════════════════════════════════


def test_list_rules_returns_user_rules(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(
        data=[
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "user_id": fake_user["id"],
                "name": "Value foot",
                "conditions": [],
                "logic": "and",
                "channels": ["telegram"],
                "secondary_actions": [],
                "enabled": True,
                "created_at": "2026-04-21T00:00:00+00:00",
                "updated_at": "2026-04-21T00:00:00+00:00",
            }
        ]
    )

    out = list_rules.__wrapped__(request=MagicMock(), user=fake_user)

    assert len(out["rules"]) == 1
    assert out["rules"][0]["name"] == "Value foot"
    # Route must scope the query to the authenticated user.
    eq_args = [c.args for c in mock_supabase.eq.call_args_list if c.args]
    assert any(a and a[0] == "user_id" and a[1] == fake_user["id"] for a in eq_args)


def test_list_rules_returns_empty_when_no_rows(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[])
    out = list_rules.__wrapped__(request=MagicMock(), user=fake_user)
    assert out == {"rules": []}


# ═══════════════════════════════════════════════════════════════════
#  POST /rules
# ═══════════════════════════════════════════════════════════════════


def test_create_rule_inserts_and_injects_user_id(mock_supabase, fake_user):
    """Insert row; ``user_id`` injected from the auth context, not the body."""
    inserted = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": fake_user["id"],
        "name": "Safe alerts",
        "conditions": [{"type": "edge_min", "min_pct": 5.0}],
        "logic": "and",
        "channels": ["telegram"],
        "secondary_actions": [],
        "enabled": True,
        "created_at": "2026-04-21T00:00:00+00:00",
        "updated_at": "2026-04-21T00:00:00+00:00",
    }

    # Sequence: count (0), then insert response.
    mock_supabase.execute.side_effect = [
        MagicMock(data=[], count=0),  # max-20 check
        MagicMock(data=[inserted]),  # insert
    ]

    payload = NotificationRuleCreate(
        name="Safe alerts",
        conditions=[{"type": "edge_min", "min_pct": 5.0}],
        channels=["telegram"],
    )

    out = create_rule.__wrapped__(request=MagicMock(), payload=payload, user=fake_user)

    assert out["id"] == "11111111-1111-1111-1111-111111111111"
    mock_supabase.insert.assert_called_once()
    record = mock_supabase.insert.call_args.args[0]
    assert record["user_id"] == fake_user["id"]
    assert record["name"] == "Safe alerts"


def test_create_rule_enforces_max_20_per_user(mock_supabase, fake_user):
    """Users are capped at 20 rules; 21st attempt → 409."""
    mock_supabase.execute.return_value = MagicMock(data=[], count=20)

    payload = NotificationRuleCreate(
        name="overflow",
        conditions=[{"type": "edge_min", "min_pct": 1.0}],
        channels=["telegram"],
    )

    with pytest.raises(HTTPException) as exc:
        create_rule.__wrapped__(request=MagicMock(), payload=payload, user=fake_user)
    assert exc.value.status_code == 409


# ═══════════════════════════════════════════════════════════════════
#  PUT /rules/{rule_id}
# ═══════════════════════════════════════════════════════════════════


def test_update_rule_returns_updated_row(mock_supabase, fake_user):
    updated = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": fake_user["id"],
        "name": "Renamed",
        "conditions": [{"type": "edge_min", "min_pct": 10.0}],
        "logic": "and",
        "channels": ["email"],
        "secondary_actions": [],
        "enabled": True,
        "created_at": "2026-04-21T00:00:00+00:00",
        "updated_at": "2026-04-21T00:00:00+00:00",
    }
    mock_supabase.execute.return_value = MagicMock(data=[updated])

    payload = NotificationRuleCreate(
        name="Renamed",
        conditions=[{"type": "edge_min", "min_pct": 10.0}],
        channels=["email"],
    )

    out = update_rule.__wrapped__(
        request=MagicMock(),
        rule_id=UUID("11111111-1111-1111-1111-111111111111"),
        payload=payload,
        user=fake_user,
    )

    assert out["name"] == "Renamed"
    # Update must be scoped to both id AND user_id (RLS belt-and-suspenders).
    eq_args = [c.args for c in mock_supabase.eq.call_args_list if c.args]
    assert any(a and a[0] == "user_id" and a[1] == fake_user["id"] for a in eq_args)
    assert any(a and a[0] == "id" for a in eq_args)


def test_update_rule_404_when_not_owned(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[])

    payload = NotificationRuleCreate(
        name="X",
        conditions=[{"type": "edge_min", "min_pct": 1.0}],
        channels=["telegram"],
    )

    with pytest.raises(HTTPException) as exc:
        update_rule.__wrapped__(
            request=MagicMock(),
            rule_id=UUID("22222222-2222-2222-2222-222222222222"),
            payload=payload,
            user=fake_user,
        )
    assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════
#  DELETE /rules/{rule_id}
# ═══════════════════════════════════════════════════════════════════


def test_delete_rule_happy_returns_none(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(
        data=[{"id": "11111111-1111-1111-1111-111111111111"}]
    )
    out = delete_rule.__wrapped__(
        request=MagicMock(),
        rule_id=UUID("11111111-1111-1111-1111-111111111111"),
        user=fake_user,
    )
    assert out is None
    # Scoped to user_id.
    eq_args = [c.args for c in mock_supabase.eq.call_args_list if c.args]
    assert any(a and a[0] == "user_id" and a[1] == fake_user["id"] for a in eq_args)


def test_delete_rule_404_when_missing(mock_supabase, fake_user):
    mock_supabase.execute.return_value = MagicMock(data=[])
    with pytest.raises(HTTPException) as exc:
        delete_rule.__wrapped__(
            request=MagicMock(),
            rule_id=UUID("33333333-3333-3333-3333-333333333333"),
            user=fake_user,
        )
    assert exc.value.status_code == 404
