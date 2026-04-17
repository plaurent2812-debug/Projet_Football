"""
api/auth.py — Centralized authentication helpers for API routes.

Shared by main.py and all routers to avoid circular imports.
"""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException

from src.config import supabase

logger = logging.getLogger(__name__)

CRON_SECRET = os.getenv("CRON_SECRET", "")


def verify_cron_auth(authorization: str | None) -> None:
    """Verify Bearer token matches CRON_SECRET. Raises 401 on failure."""
    if not CRON_SECRET:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured")
    expected = f"Bearer {CRON_SECRET}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def verify_internal_auth(
    authorization: str | None = None,
    x_cron_secret: str | None = None,
) -> None:
    """
    Verify the request comes from CRON_SECRET or an admin JWT.

    Accepts either:
      - ``Authorization: Bearer <CRON_SECRET>`` (or an admin Supabase JWT), or
      - ``X-Cron-Secret: <CRON_SECRET>`` (convenience header for schedulers).

    Raises HTTPException(401/403) on failure.
    """
    # Accept the dedicated cron header even when Authorization is missing.
    if x_cron_secret:
        if CRON_SECRET and hmac.compare_digest(x_cron_secret.strip(), CRON_SECRET):
            logger.info(
                "ADMIN_AUTH_OK: source=cron-header, token=%s...",
                x_cron_secret[:8],
            )
            return
        logger.warning("ADMIN_AUTH_FAIL: invalid X-Cron-Secret")
        raise HTTPException(status_code=401, detail="Invalid token")

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    # Check CRON secret first
    if CRON_SECRET and hmac.compare_digest(token, CRON_SECRET):
        logger.info("ADMIN_AUTH_OK: source=cron, token=%s...", token[:8])
        return
    # Fall back to admin JWT
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise ValueError("Invalid JWT")
        user_id = user_res.user.id
        db_user = supabase.table("profiles").select("role").eq("id", user_id).execute().data
        if not db_user or db_user[0].get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: Admin only")
        logger.info("ADMIN_AUTH_OK: source=jwt, user=%s", user_id)
    except HTTPException:
        raise
    except Exception:
        logger.warning("ADMIN_AUTH_FAIL: invalid token=%s...", token[:8])
        raise HTTPException(status_code=401, detail="Invalid token")
