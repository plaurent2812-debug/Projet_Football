"""tests/test_user_bankroll_settings.py — GET + PUT /api/user/bankroll/settings
(Lot 2 · T06).

Covers both the Pydantic strict payload contract (extra forbidden, range
bounds) and the Supabase wiring (upsert on user_id, defaults fallback for GET).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from api.routers.v2.user_bankroll import (
    BankrollSettings,
    get_bankroll_settings,
    put_bankroll_settings,
)


# ──────────────────────────────────────────────────────────────────────
# Pydantic contract
# ──────────────────────────────────────────────────────────────────────


def test_payload_accepts_valid_values():
    """Canonical values from the plan build a valid payload."""
    payload = BankrollSettings(
        stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=0.05
    )
    assert payload.stake_initial == 100.0
    assert payload.kelly_fraction == 0.25
    assert payload.stake_cap_pct == 0.05


def test_payload_rejects_invalid_fraction():
    """kelly_fraction > 1 must fail validation."""
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=100.0, kelly_fraction=1.5, stake_cap_pct=0.05)


def test_payload_rejects_zero_fraction():
    """kelly_fraction must be strictly positive (gt=0)."""
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=100.0, kelly_fraction=0.0, stake_cap_pct=0.05)


def test_payload_rejects_negative_stake_initial():
    """stake_initial must be >= 0."""
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=-1.0, kelly_fraction=0.25, stake_cap_pct=0.05)


def test_payload_rejects_invalid_stake_cap():
    """stake_cap_pct must be ∈ (0, 1]."""
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=0.0)
    with pytest.raises(ValidationError):
        BankrollSettings(stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=1.5)


def test_payload_rejects_extra_fields():
    """ConfigDict(extra='forbid') must reject unknown keys."""
    with pytest.raises(ValidationError):
        BankrollSettings(
            stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=0.05, foo="bar"
        )


# ──────────────────────────────────────────────────────────────────────
# PUT route
# ──────────────────────────────────────────────────────────────────────


def test_put_settings_upserts(mock_supabase, fake_user):
    """PUT upserts into user_bankroll_settings with user_id from auth context."""
    payload = BankrollSettings(
        stake_initial=250.0, kelly_fraction=0.25, stake_cap_pct=0.05
    )

    out = put_bankroll_settings.__wrapped__(
        request=MagicMock(), payload=payload, user=fake_user
    )

    assert out["stake_initial"] == 250.0
    assert out["kelly_fraction"] == 0.25
    assert out["stake_cap_pct"] == 0.05
    mock_supabase.table.assert_any_call("user_bankroll_settings")
    mock_supabase.upsert.assert_called_once()

    # The record uploaded to Supabase must carry user_id from the auth user,
    # never from the body — guards against privilege escalation.
    upsert_payload = mock_supabase.upsert.call_args.args[0]
    assert upsert_payload["user_id"] == fake_user["id"]
    assert upsert_payload["stake_initial"] == 250.0


def test_put_settings_user_id_from_auth_not_body(mock_supabase, fake_user):
    """Even if a client tampered with the body, only the auth user_id survives.

    The ``BankrollSettings`` schema forbids ``user_id`` so the upsert helper
    injects it from the authenticated context.
    """
    payload = BankrollSettings(
        stake_initial=100.0, kelly_fraction=0.25, stake_cap_pct=0.05
    )

    put_bankroll_settings.__wrapped__(
        request=MagicMock(), payload=payload, user=fake_user
    )

    record = mock_supabase.upsert.call_args.args[0]
    assert record["user_id"] == fake_user["id"]


# ──────────────────────────────────────────────────────────────────────
# GET route
# ──────────────────────────────────────────────────────────────────────


def test_get_settings_returns_defaults_when_no_row(mock_supabase, fake_user):
    """A first-time user with no row in the table → defaults, not a 500."""
    mock_supabase.execute.return_value = MagicMock(data=[])

    out = get_bankroll_settings.__wrapped__(request=MagicMock(), user=fake_user)

    assert out["stake_initial"] == 100.0
    assert out["kelly_fraction"] == 0.25
    assert out["stake_cap_pct"] == 0.05


def test_get_settings_returns_persisted_row(mock_supabase, fake_user):
    """When a row exists, its values are returned (coerced to float)."""
    mock_supabase.execute.return_value = MagicMock(
        data=[
            {
                "stake_initial": 500,
                "kelly_fraction": 0.5,
                "stake_cap_pct": 0.08,
            }
        ]
    )

    out = get_bankroll_settings.__wrapped__(request=MagicMock(), user=fake_user)

    assert out["stake_initial"] == 500.0
    assert out["kelly_fraction"] == 0.5
    assert out["stake_cap_pct"] == 0.08


def test_get_settings_queries_user_bankroll_settings(mock_supabase, fake_user):
    """Route targets ``user_bankroll_settings`` filtered on current user_id."""
    mock_supabase.execute.return_value = MagicMock(data=[])

    get_bankroll_settings.__wrapped__(request=MagicMock(), user=fake_user)

    table_calls = [c.args[0] for c in mock_supabase.table.call_args_list if c.args]
    assert "user_bankroll_settings" in table_calls

    eq_calls = mock_supabase.eq.call_args_list
    assert any(
        call.args and call.args[0] == "user_id" and call.args[1] == fake_user["id"]
        for call in eq_calls
    )
