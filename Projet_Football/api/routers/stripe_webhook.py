import os
import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from config import supabase, logger

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/api/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_session(data_object)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data_object)
    else:
        logger.info(f"Unhandled Stripe event type: {event_type}")

    return {"status": "success"}


# ─── Helpers ────────────────────────────────────────────────────


def _find_user_id_by_email(email: str) -> str | None:
    """Look up a user id in profiles by email (best-effort fallback)."""
    try:
        result = (
            supabase.table("profiles")
            .select("id")
            .eq("email", email)
            .limit(1)
            .execute()
            .data
        )
        return result[0]["id"] if result else None
    except Exception as e:
        logger.warning(f"Could not look up profile by email {email}: {e}")
        return None


def _find_user_id_by_customer(customer_id: str) -> str | None:
    """Look up a user id in profiles by stripe_customer_id."""
    try:
        result = (
            supabase.table("profiles")
            .select("id")
            .eq("stripe_customer_id", customer_id)
            .limit(1)
            .execute()
            .data
        )
        return result[0]["id"] if result else None
    except Exception as e:
        logger.warning(f"Could not look up profile by customer_id {customer_id}: {e}")
        return None


def _update_profile(user_id: str, updates: dict) -> None:
    """Apply an update to a profile row."""
    try:
        supabase.table("profiles").update(updates).eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to update profile for {user_id}: {e}")


# ─── Event Handlers ─────────────────────────────────────────────


def _handle_checkout_session(session: dict) -> None:
    """Upgrade user to premium after successful checkout."""
    user_id = session.get("client_reference_id")
    customer_id = session.get("customer")

    if not user_id:
        email = session.get("customer_email")
        if email:
            user_id = _find_user_id_by_email(email)
        if not user_id:
            logger.warning(
                "Checkout completed but could not resolve user_id "
                f"(client_reference_id missing, email={session.get('customer_email')})"
            )
            return

    logger.info(f"Upgrading user {user_id} to PREMIUM")
    _update_profile(user_id, {
        "role": "premium",
        "stripe_customer_id": customer_id,
        "subscription_status": "active",
    })


def _handle_subscription_deleted(subscription: dict) -> None:
    """Downgrade user back to free when their subscription is cancelled."""
    customer_id = subscription.get("customer")
    if not customer_id:
        logger.warning("subscription.deleted event without customer id")
        return

    user_id = _find_user_id_by_customer(customer_id)
    if not user_id:
        logger.warning(f"subscription.deleted: no profile for customer {customer_id}")
        return

    logger.info(f"Downgrading user {user_id} to FREE (subscription cancelled)")
    _update_profile(user_id, {
        "role": "free",
        "subscription_status": "cancelled",
    })


def _handle_payment_failed(invoice: dict) -> None:
    """Log payment failure — can be extended to notify the user."""
    customer_id = invoice.get("customer")
    logger.warning(
        f"Payment failed for customer {customer_id}, "
        f"invoice {invoice.get('id')} — amount: {invoice.get('amount_due')}"
    )
