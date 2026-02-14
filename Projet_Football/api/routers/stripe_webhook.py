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

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_session(session)

    return {"status": "success"}

def handle_checkout_session(session):
    """Update user profile to premium after successful payment."""
    user_id = session.get("client_reference_id")
    customer_id = session.get("customer")
    
    if not user_id:
        # If user_id wasn't passed, try to find by email
        email = session.get("customer_email")
        if email:
            # Find user by email (this is weak, client_reference_id is better)
            # In Supabase, we can't easily query auth.users, but we can query public.profiles
            pass 
        logger.warning("No client_reference_id in session")
        return

    logger.info(f"Upgrading user {user_id} to PREMIUM")
    
    try:
        # Update profile
        supabase.table("profiles").update({
            "role": "premium",
            "stripe_customer_id": customer_id,
            "subscription_status": "active"
        }).eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to update profile for {user_id}: {e}")
