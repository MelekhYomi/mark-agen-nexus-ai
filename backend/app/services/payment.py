"""
Payment Service - Stripe Integration
Handles subscription management, one-time payments, invoices, and webhooks.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import stripe

from app.config import settings

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = "2024-06-20"


class PaymentService:
    """
    Stripe payment service for subscriptions, one-time payments, and invoices.
    """
    
    # Product/Price IDs (replace with your actual Stripe IDs)
    PRICES = {
        'starter_monthly': 'price_starter_monthly',
        'pro_monthly': 'price_pro_monthly',
        'business_monthly': 'price_business_monthly',
        'starter_yearly': 'price_starter_yearly',
        'pro_yearly': 'price_pro_yearly',
        'business_yearly': 'price_business_yearly',
    }
    
    @staticmethod
    async def create_customer(
        email: str,
        name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata
        
        Returns:
            Customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            
            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {str(e)}")
            raise
    
    @staticmethod
    async def get_customer(customer_id: str) -> Dict:
        """Get customer details"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'created': customer.created,
                'metadata': customer.metadata
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get customer: {str(e)}")
            raise
    
    @staticmethod
    async def create_subscription(
        customer_id: str,
        price_id: str,
        trial_days: int = 14,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a new subscription with optional trial period.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Free trial period in days
            metadata: Additional metadata
        
        Returns:
            Subscription details with client secret for frontend
        """
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                trial_period_days=trial_days if trial_days > 0 else None,
                payment_behavior='default_incomplete',
                payment_settings={
                    'save_default_payment_method': 'on_subscription'
                },
                expand=['latest_invoice.payment_intent'],
                metadata=metadata or {}
            )
            
            logger.info(f"Created subscription: {subscription.id} for customer {customer_id}")
            
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'trial_end': subscription.trial_end,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None,
                'hosted_invoice_url': subscription.latest_invoice.hosted_invoice_url if subscription.latest_invoice else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise
    
    @staticmethod
    async def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> Dict:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period
        
        Returns:
            Cancellation details
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Cancelled subscription: {subscription_id}")
            
            return {
                'subscription_id': subscription_id,
                'status': subscription.status,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            raise
    
    @staticmethod
    async def get_subscription(subscription_id: str) -> Dict:
        """Get subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'items': [{
                    'price_id': item.price.id,
                    'amount': item.price.unit_amount,
                    'currency': item.price.currency
                } for item in subscription.items.data]
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription: {str(e)}")
            raise
    
    @staticmethod
    async def create_payment_intent(
        amount: int,
        currency: str,
        customer_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a one-time payment intent.
        
        Args:
            amount: Amount in cents
            currency: Currency code (e.g., 'usd')
            customer_id: Stripe customer ID
            metadata: Additional metadata
        
        Returns:
            Payment intent with client secret
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'
                },
                metadata=metadata or {}
            )
            
            logger.info(f"Created payment intent: {intent.id} for {amount} {currency}")
            
            return {
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency,
                'status': intent.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment intent: {str(e)}")
            raise
    
    @staticmethod
    async def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = 'subscription'
    ) -> Dict:
        """
        Create a Stripe Checkout session.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancellation
            mode: 'subscription' or 'payment'
        
        Returns:
            Checkout session with URL
        """
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode=mode,
                line_items=[{
                    'price': price_id,
                    'quantity': 1
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                automatic_tax={'enabled': False},
                metadata={'customer_id': customer_id}
            )
            
            logger.info(f"Created checkout session: {session.id}")
            
            return {
                'session_id': session.id,
                'url': session.url,
                'expires_at': session.expires_at
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {str(e)}")
            raise
    
    @staticmethod
    async def handle_webhook(payload: bytes, sig_header: str) -> Dict:
        """
        Handle Stripe webhook events.
        
        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header
        
        Returns:
            Event type and data
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            
            event_type = event.type
            event_data = event.data.object
            
            logger.info(f"Received Stripe webhook: {event_type}")
            
            # Handle different event types
            if event_type == 'checkout.session.completed':
                return await PaymentService._handle_checkout_completed(event_data)
            
            elif event_type == 'invoice.payment_succeeded':
                return await PaymentService._handle_invoice_succeeded(event_data)
            
            elif event_type == 'invoice.payment_failed':
                return await PaymentService._handle_invoice_failed(event_data)
            
            elif event_type == 'customer.subscription.updated':
                return await PaymentService._handle_subscription_updated(event_data)
            
            elif event_type == 'customer.subscription.deleted':
                return await PaymentService._handle_subscription_deleted(event_data)
            
            else:
                logger.info(f"Unhandled event type: {event_type}")
                return {'status': 'ignored', 'event_type': event_type}
            
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            raise
    
    @staticmethod
    async def _handle_checkout_completed(session: Dict) -> Dict:
        """Handle successful checkout completion"""
        logger.info(f"Checkout completed: {session.id}")
        return {
            'status': 'success',
            'event': 'checkout.session.completed',
            'session_id': session.id,
            'customer_id': session.customer,
            'amount': session.amount_total,
            'currency': session.currency
        }
    
    @staticmethod
    async def _handle_invoice_succeeded(invoice: Dict) -> Dict:
        """Handle successful invoice payment"""
        logger.info(f"Invoice payment succeeded: {invoice.id}")
        return {
            'status': 'success',
            'event': 'invoice.payment_succeeded',
            'invoice_id': invoice.id,
            'subscription_id': invoice.subscription,
            'amount': invoice.amount_paid
        }
    
    @staticmethod
    async def _handle_invoice_failed(invoice: Dict) -> Dict:
        """Handle failed invoice payment"""
        logger.warning(f"Invoice payment failed: {invoice.id}")
        return {
            'status': 'failed',
            'event': 'invoice.payment_failed',
            'invoice_id': invoice.id,
            'subscription_id': invoice.subscription,
            'amount': invoice.amount_due
        }
    
    @staticmethod
    async def _handle_subscription_updated(subscription: Dict) -> Dict:
        """Handle subscription update"""
        logger.info(f"Subscription updated: {subscription.id}")
        return {
            'status': 'updated',
            'event': 'customer.subscription.updated',
            'subscription_id': subscription.id,
            'status': subscription.status
        }
    
    @staticmethod
    async def _handle_subscription_deleted(subscription: Dict) -> Dict:
        """Handle subscription cancellation"""
        logger.info(f"Subscription deleted: {subscription.id}")
        return {
            'status': 'cancelled',
            'event': 'customer.subscription.deleted',
            'subscription_id': subscription.id
        }
    
    @staticmethod
    async def get_invoices(customer_id: str, limit: int = 10) -> List[Dict]:
        """Get customer invoices"""
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            
            return [{
                'id': inv.id,
                'amount': inv.amount_paid,
                'currency': inv.currency,
                'status': inv.status,
                'created': inv.created,
                'hosted_invoice_url': inv.hosted_invoice_url
            } for inv in invoices.data]
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get invoices: {str(e)}")
            raise
    
    @staticmethod
    async def update_subscription_payment_method(
        subscription_id: str,
        payment_method_id: str
    ) -> Dict:
        """Update subscription payment method"""
        try:
            stripe.Subscription.modify(
                subscription_id,
                default_payment_method=payment_method_id
            )
            
            logger.info(f"Updated payment method for subscription: {subscription_id}")
            
            return {
                'subscription_id': subscription_id,
                'payment_method_id': payment_method_id,
                'status': 'updated'
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update payment method: {str(e)}")
            raise


# Singleton instance
payment_service = PaymentService()