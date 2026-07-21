"""
Billing Router
Handles subscription management, payments, invoices, and billing history.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tenant, User
from app.auth.dependencies import get_current_user, CurrentUser
from app.services.payment import PaymentService
from app.services.crypto import CryptoPaymentService
from app.services.email import EmailService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ============================================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================================

@router.get("/subscription")
async def get_subscription(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription details.
    """
    # In production, would fetch from Stripe
    return {
        "status": "success",
        "subscription": {
            "plan": "Pro",
            "status": "active",
            "current_period_start": "2026-06-01",
            "current_period_end": "2026-07-01",
            "amount": 9900,
            "currency": "usd",
            "cancel_at_period_end": False
        }
    }


@router.post("/create-checkout")
async def create_checkout_session(
    price_id: str = Query(..., description="Stripe price ID"),
    success_url: Optional[str] = Query(None),
    cancel_url: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription or one-time payment.
    """
    # Get or create customer
    customer_id = await PaymentService.create_customer(
        email=current.user_id,  # Would use actual email
        name="User"
    )
    
    # Create checkout session
    result = await PaymentService.create_checkout_session(
        customer_id=customer_id,
        price_id=price_id,
        success_url=success_url or f"{settings.FRONTEND_URL}/billing/success",
        cancel_url=cancel_url or f"{settings.FRONTEND_URL}/billing/cancel",
        mode="subscription"
    )
    
    return {
        "status": "success",
        "checkout_url": result["url"],
        "session_id": result["session_id"]
    }


@router.post("/cancel-subscription")
async def cancel_subscription(
    subscription_id: str = Query(...),
    at_period_end: bool = Query(True),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel subscription.
    """
    result = await PaymentService.cancel_subscription(
        subscription_id=subscription_id,
        at_period_end=at_period_end
    )
    
    return {
        "status": "success",
        "subscription_id": subscription_id,
        "cancel_at_period_end": at_period_end
    }


@router.post("/update-payment-method")
async def update_payment_method(
    subscription_id: str = Query(...),
    payment_method_id: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update subscription payment method.
    """
    result = await PaymentService.update_subscription_payment_method(
        subscription_id=subscription_id,
        payment_method_id=payment_method_id
    )
    
    return {
        "status": "success",
        "updated": result
    }


# ============================================================================
# ONE-TIME PAYMENT ENDPOINTS
# ============================================================================

@router.post("/create-payment-intent")
async def create_payment_intent(
    amount: int = Query(..., description="Amount in cents"),
    currency: str = Query("usd"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a one-time payment intent.
    """
    customer_id = await PaymentService.create_customer(
        email=current.user_id,
        name="User"
    )
    
    result = await PaymentService.create_payment_intent(
        amount=amount,
        currency=currency,
        customer_id=customer_id
    )
    
    return {
        "status": "success",
        "client_secret": result["client_secret"],
        "payment_intent_id": result["payment_intent_id"]
    }


# ============================================================================
# CRYPTO PAYMENT ENDPOINTS
# ============================================================================

@router.post("/crypto/charge")
async def create_crypto_charge(
    amount: float = Query(..., description="Amount in fiat currency"),
    currency: str = Query("USD"),
    description: str = Query("Nexus AI Payment"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a cryptocurrency charge via Coinbase Commerce.
    """
    crypto_service = CryptoPaymentService()
    
    result = await crypto_service.create_charge(
        amount=amount,
        currency=currency,
        customer_email=current.user_id,
        description=description
    )
    
    return {
        "status": "success",
        "charge_id": result["charge_id"],
        "hosted_url": result["hosted_url"],
        "amount": result["amount"],
        "currency": result["currency"]
    }


@router.get("/crypto/currencies")
async def get_supported_currencies():
    """
    Get list of supported cryptocurrencies.
    """
    crypto_service = CryptoPaymentService()
    currencies = await crypto_service.get_supported_currencies()
    
    return {
        "status": "success",
        "currencies": currencies
    }


# ============================================================================
# INVOICE ENDPOINTS
# ============================================================================

@router.get("/invoices")
async def get_invoices(
    limit: int = Query(10, ge=1, le=50),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice history.
    """
    # In production, would fetch from Stripe
    return {
        "status": "success",
        "invoices": []
    }


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(400, "Missing stripe-signature header")
    
    try:
        result = await PaymentService.handle_webhook(payload, sig_header)
        
        # Handle different event types
        event_type = result.get("event")
        
        if event_type == "checkout.session.completed":
            # Send confirmation email
            await EmailService().send_payment_confirmation(
                to_email="user@example.com",
                user_name="User",
                amount=result.get("amount", 0) / 100,
                currency=result.get("currency", "usd"),
                invoice_id=result.get("session_id", "")
            )
        
        return {"status": "success", "event": event_type}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(400, str(e))


@router.post("/webhook/crypto")
async def crypto_webhook(request: Request):
    """
    Handle Coinbase Commerce webhook events.
    """
    payload = await request.body()
    signature = request.headers.get("x-cc-webhook-signature")
    
    if not signature:
        raise HTTPException(400, "Missing webhook signature")
    
    try:
        crypto_service = CryptoPaymentService()
        result = await crypto_service.handle_webhook(payload, signature)
        
        return {"status": "success", "event": result.get("event")}
        
    except Exception as e:
        logger.error(f"Crypto webhook error: {e}")
        raise HTTPException(400, str(e))


# ============================================================================
# PRICING ENDPOINTS
# ============================================================================

@router.get("/plans")
async def get_pricing_plans():
    """
    Get available pricing plans.
    """
    return {
        "status": "success",
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price": 0,
                "period": "forever",
                "features": [
                    "1 workspace",
                    "5 AI agents",
                    "$500 ad budget",
                    "Basic analytics"
                ]
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 99,
                "period": "month",
                "features": [
                    "Unlimited workspaces",
                    "5 AI agents",
                    "$1000 ad budget",
                    "Advanced analytics",
                    "Priority support"
                ],
                "popular": True
            },
            {
                "id": "business",
                "name": "Business",
                "price": 299,
                "period": "month",
                "features": [
                    "Everything in Pro",
                    "Team members",
                    "Unlimited ad budget",
                    "White-label reports",
                    "Dedicated manager"
                ]
            }
        ]
    }