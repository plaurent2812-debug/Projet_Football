"""
Fixtures for API endpoint tests.

Strategy: src/config.py calls create_client() at module-import time (line 50).
We must patch supabase.create_client BEFORE src.config is ever imported.
We achieve this by:
  1. Setting env vars before any import.
  2. Patching supabase.create_client at the top of this module so that when
     src.config is imported (triggered by the `client` fixture), it receives
     our mock instead of making a real network call.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

# ── Step 1: set env vars before any project import ───────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("CRON_SECRET", "test-cron-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient

# ─── Chainable Supabase mock ──────────────────────────────────────


def _make_chain(data=None, count=0):
    """Return a fully chainable MagicMock that ends in .execute()."""
    chain = MagicMock()
    execute_result = MagicMock()
    execute_result.data = data if data is not None else []
    execute_result.count = count
    chain.execute.return_value = execute_result

    # Every chaining method returns itself so calls can be composed freely.
    for method in (
        "select",
        "eq",
        "neq",
        "gte",
        "lte",
        "gt",
        "lt",
        "in_",
        "or_",
        "order",
        "limit",
        "range",
        "insert",
        "upsert",
        "update",
        "delete",
        "filter",
        "single",
        "desc",
    ):
        getattr(chain, method).return_value = chain

    return chain


def _make_supabase_mock():
    """Build a complete Supabase client mock with chainable query builder."""
    mock = MagicMock()
    chain = _make_chain()
    mock.table.return_value = chain
    mock.rpc.return_value = chain
    # auth sub-mock (used in _require_admin and verify_internal_auth)
    mock.auth = MagicMock()
    return mock


# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def mock_supabase():
    """A reusable Supabase mock shared across the session."""
    return _make_supabase_mock()


@pytest.fixture(scope="session")
def client(mock_supabase):
    """
    TestClient with Supabase mocked out at the module level.

    We patch supabase.create_client (the library function) so that
    src.config — which calls it at import time — receives our mock.
    We also patch src.config.supabase directly to cover routers that
    have already imported the symbol before the test session starts.
    """
    # Patch the library-level factory and the already-imported module attr.
    with (
        patch("supabase.create_client", return_value=mock_supabase),
        patch("src.config.supabase", mock_supabase),
        patch("api.auth.supabase", mock_supabase),
    ):
        from api.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture
def auth_headers():
    """Bearer token that matches CRON_SECRET."""
    return {"Authorization": "Bearer test-cron-secret"}


@pytest.fixture
def bad_auth_headers():
    """Bearer token that does NOT match CRON_SECRET."""
    return {"Authorization": "Bearer wrong-secret"}


@pytest.fixture
def admin_headers(mock_supabase):
    """
    Headers that pass _require_admin() via a mocked Supabase JWT check.

    _require_admin does:
      1. supabase.auth.get_user(token) → user_resp.user.id
      2. supabase.table("profiles").select("role").eq(...).single().execute().data
         → must return {"role": "admin"}

    We configure the mock before yielding so any test using this fixture
    gets a valid admin token accepted by the endpoint.
    """
    user_mock = MagicMock()
    user_mock.user.id = "admin-uuid-1234"
    mock_supabase.auth.get_user.return_value = user_mock

    profile_chain = _make_chain(data={"role": "admin"})
    mock_supabase.table.return_value = profile_chain

    return {"Authorization": "Bearer fake-admin-jwt"}
