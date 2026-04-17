"""
Regression tests for admin auth: /api/admin/update-scores must not be
callable without a valid CRON_SECRET (Bearer or X-Cron-Secret) or admin
JWT. Previously the endpoint was open on the internal network, exposing
the paid API-Football quota to DoS.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

# ── Env vars required before any project import (same pattern as
#    tests/test_api/conftest.py) ───────────────────────────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("CRON_SECRET", "test-cron-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient


def _make_supabase_mock():
    mock = MagicMock()
    chain = MagicMock()
    exec_res = MagicMock()
    exec_res.data = []
    exec_res.count = 0
    chain.execute.return_value = exec_res
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
    mock.table.return_value = chain
    mock.rpc.return_value = chain
    mock.auth = MagicMock()
    return mock


@pytest.fixture(scope="module")
def client():
    mock = _make_supabase_mock()
    with (
        patch("supabase.create_client", return_value=mock),
        patch("src.config.supabase", mock),
        patch("api.auth.supabase", mock),
    ):
        from api.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_update_scores_rejects_unauth(client):
    r = client.post("/api/admin/update-scores")
    assert r.status_code in (401, 403), (
        f"Expected 401/403 without auth, got {r.status_code} — "
        f"endpoint is exposed to DoS on paid API quota"
    )


def test_update_scores_accepts_cron_secret(client):
    r = client.post(
        "/api/admin/update-scores",
        headers={"X-Cron-Secret": "wrong"},
    )
    assert r.status_code in (401, 403)
