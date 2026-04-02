"""
api/routers/push.py — Web Push notification endpoints.

Endpoints:
  POST /api/push/subscribe    — Store a push subscription
  POST /api/push/unsubscribe  — Remove a push subscription

Utility:
  send_push_to_all(title, body, url) — Send push to all subscribers
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.config import supabase

PUSH_API_KEY = os.getenv("PUSH_API_KEY", "")


def _verify_push_auth(x_api_key: str = Header(None, alias="X-Push-Key")):
    """Vérifie l'accès aux endpoints push. Fail-open si PUSH_API_KEY non configuré (dev)."""
    if PUSH_API_KEY and (not x_api_key or x_api_key != PUSH_API_KEY):
        raise HTTPException(status_code=403, detail="Forbidden")

logger = logging.getLogger("push_router")

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = os.getenv("VAPID_EMAIL", "mailto:contact@probalab.net")


class PushSubscriptionBody(BaseModel):
    endpoint: str
    keys: dict | None = None
    expirationTime: float | None = None


class UnsubscribeBody(BaseModel):
    endpoint: str


@router.post("/subscribe", dependencies=[Depends(_verify_push_auth)])
async def subscribe_push(body: PushSubscriptionBody):
    """Store a push subscription in Supabase."""
    try:
        # Upsert by endpoint (avoid duplicates)
        record = {
            "endpoint": body.endpoint,
            "keys_json": json.dumps(body.keys) if body.keys else "{}",
            "expiration_time": body.expirationTime,
        }
        # Check if already exists
        existing = (
            supabase.table("push_subscriptions")
            .select("id")
            .eq("endpoint", body.endpoint)
            .limit(1)
            .execute()
            .data
        )
        if existing:
            supabase.table("push_subscriptions").update(record).eq("endpoint", body.endpoint).execute()
        else:
            supabase.table("push_subscriptions").insert(record).execute()

        return {"ok": True}
    except Exception as e:
        logger.error("Push subscribe error: %s", e)
        return {"ok": False, "error": "subscription failed"}


@router.post("/unsubscribe", dependencies=[Depends(_verify_push_auth)])
async def unsubscribe_push(body: UnsubscribeBody):
    """Remove a push subscription."""
    try:
        supabase.table("push_subscriptions").delete().eq("endpoint", body.endpoint).execute()
        return {"ok": True}
    except Exception as e:
        logger.error("Push unsubscribe error: %s", e)
        return {"ok": False, "error": "unsubscribe failed"}


def send_push_to_all(title: str, body: str, url: str = "/paris-du-soir") -> int:
    """
    Send a push notification to ALL subscribers.
    Returns the number of successfully sent notifications.
    """
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY not set, skipping push notifications")
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed. Install with: pip install pywebpush")
        return 0

    try:
        subs = supabase.table("push_subscriptions").select("endpoint, keys_json").execute().data
    except Exception as e:
        logger.error("Failed to fetch push subscriptions: %s", e)
        return 0

    if not subs:
        return 0

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
    })

    sent = 0
    stale_endpoints = []

    for sub in subs:
        try:
            keys = json.loads(sub.get("keys_json", "{}"))
            subscription_info = {
                "endpoint": sub["endpoint"],
                "keys": keys,
            }
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_EMAIL},
            )
            sent += 1
        except Exception as e:
            error_str = str(e)
            # 410 Gone = subscription expired, clean up
            if "410" in error_str or "404" in error_str:
                stale_endpoints.append(sub["endpoint"])
            else:
                logger.warning("Push send failed for %s: %s", sub["endpoint"][:50], e)

    # Clean up stale subscriptions
    for endpoint in stale_endpoints:
        try:
            supabase.table("push_subscriptions").delete().eq("endpoint", endpoint).execute()
        except Exception as e:
            logger.warning("Failed to cleanup stale endpoint %s: %s", endpoint[:50], e)

    logger.info("Push sent to %d/%d subscribers (%d stale removed)", sent, len(subs), len(stale_endpoints))
    return sent
