"""
Crypto Payment Service - Coinbase Commerce Integration
Handles cryptocurrency payments including Bitcoin, Ethereum, and USDC.
"""
import logging
import hashlib
import hmac
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CryptoPaymentService:
    """
    Coinbase Commerce integration for cryptocurrency payments.
    Supports Bitcoin, Ethereum, USDC, and other cryptocurrencies.
    """
    
    BASE_URL = "https://api.commerce.coinbase.com"
    
    def __init__(self):
        self.api_key = settings.COINBASE_API_KEY
        self.webhook_secret = settings.COINBASE_WEBHOOK_SECRET
        self.headers = {
            "X-CC-Api-Key": self.api_key,
            "X-CC-Version": "2018-03-22",
            "Content-Type": "application/json"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Coinbase Commerce API"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    async def create_charge(
        self,
        amount: float,
        currency: str,
        customer_email: str,
        customer_name: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict] = None,
        redirect_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict:
        """
        Create a cryptocurrency charge.
        
        Args:
            amount: Payment amount
            currency: Fiat currency (USD, EUR, etc.)
            customer_email: Customer email
            customer_name: Customer name
            description: Charge description
            metadata: Additional metadata
            redirect_url: URL to redirect after payment
            cancel_url: URL to redirect on cancellation
        
        Returns:
            Charge details with hosted URL
        """
        try:
            charge_data = {
                "name": f"Nexus AI Payment - {description or 'Subscription'}",
                "description": description or "Payment for Nexus AI services",
                "local_price": {
                    "amount": str(amount),
                    "currency": currency
                },
                "pricing_type": "fixed_price",
                "metadata": metadata or {},
                "redirect_url": redirect_url or f"{settings.FRONTEND_URL}/payment/success",
                "cancel_url": cancel_url or f"{settings.FRONTEND_URL}/payment/cancel"
            }
            
            if customer_email:
                charge_data["customer_email"] = customer_email
            
            if customer_name:
                charge_data["customer_name"] = customer_name
            
            result = await self._request("POST", "charges", data=charge_data)
            
            logger.info(f"Created crypto charge: {result['data']['id']} for {amount} {currency}")
            
            return {
                'charge_id': result['data']['id'],
                'hosted_url': result['data']['hosted_url'],
                'amount': amount,
                'currency': currency,
                'status': result['data']['timeline'][0]['status'] if result['data'].get('timeline') else 'NEW',
                'created_at': result['data']['created_at']
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create charge: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create charge: {str(e)}")
            raise
    
    async def get_charge(self, charge_id: str) -> Dict:
        """Get charge details"""
        try:
            result = await self._request("GET", f"charges/{charge_id}")
            return result['data']
        except Exception as e:
            logger.error(f"Failed to get charge: {str(e)}")
            raise
    
    async def list_charges(self, limit: int = 10) -> List[Dict]:
        """List recent charges"""
        try:
            result = await self._request("GET", f"charges?limit={limit}")
            return result['data']
        except Exception as e:
            logger.error(f"Failed to list charges: {str(e)}")
            raise
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Verify Coinbase Commerce webhook signature.
        
        Args:
            payload: Raw request body
            signature: X-CC-Webhook-Signature header
        
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Failed to verify webhook: {str(e)}")
            return False
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Coinbase Commerce webhook events.
        
        Args:
            payload: Raw request body
            signature: X-CC-Webhook-Signature header
        
        Returns:
            Event type and data
        """
        # Verify signature
        if not self.verify_webhook(payload, signature):
            logger.error("Invalid webhook signature")
            raise ValueError("Invalid signature")
        
        import json
        event_data = json.loads(payload)
        
        event_type = event_data.get('event', {}).get('type')
        event = event_data.get('event', {}).get('data', {})
        
        logger.info(f"Received Coinbase webhook: {event_type}")
        
        # Handle different event types
        if event_type == 'charge:confirmed':
            return await self._handle_charge_confirmed(event)
        
        elif event_type == 'charge:failed':
            return await self._handle_charge_failed(event)
        
        elif event_type == 'charge:delayed':
            return await self._handle_charge_delayed(event)
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {'status': 'ignored', 'event_type': event_type}
    
    async def _handle_charge_confirmed(self, charge: Dict) -> Dict:
        """Handle confirmed charge"""
        logger.info(f"Charge confirmed: {charge['id']}")
        return {
            'status': 'confirmed',
            'event': 'charge:confirmed',
            'charge_id': charge['id'],
            'amount': charge['pricing']['local']['amount'],
            'currency': charge['pricing']['local']['currency'],
            'crypto_amount': charge['pricing']['bitcoin']['amount'] if 'bitcoin' in charge['pricing'] else None
        }
    
    async def _handle_charge_failed(self, charge: Dict) -> Dict:
        """Handle failed charge"""
        logger.warning(f"Charge failed: {charge['id']}")
        return {
            'status': 'failed',
            'event': 'charge:failed',
            'charge_id': charge['id'],
            'amount': charge['pricing']['local']['amount'],
            'currency': charge['pricing']['local']['currency']
        }
    
    async def _handle_charge_delayed(self, charge: Dict) -> Dict:
        """Handle delayed charge"""
        logger.info(f"Charge delayed: {charge['id']}")
        return {
            'status': 'delayed',
            'event': 'charge:delayed',
            'charge_id': charge['id']
        }
    
    async def create_checkout(
        self,
        amount: float,
        currency: str,
        customer_email: str,
        product_name: str,
        redirect_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict:
        """
        Create a Coinbase Commerce checkout (alternative to charge).
        
        Args:
            amount: Payment amount
            currency: Fiat currency
            customer_email: Customer email
            product_name: Product name
            redirect_url: Success redirect URL
            cancel_url: Cancel redirect URL
        
        Returns:
            Checkout details with hosted URL
        """
        try:
            checkout_data = {
                "name": product_name,
                "description": f"Payment for {product_name}",
                "local_price": {
                    "amount": str(amount),
                    "currency": currency
                },
                "pricing_type": "fixed_price",
                "redirect_url": redirect_url or f"{settings.FRONTEND_URL}/payment/success",
                "cancel_url": cancel_url or f"{settings.FRONTEND_URL}/payment/cancel"
            }
            
            result = await self._request("POST", "checkouts", data=checkout_data)
            
            logger.info(f"Created checkout: {result['data']['id']}")
            
            return {
                'checkout_id': result['data']['id'],
                'hosted_url': result['data']['hosted_url'],
                'amount': amount,
                'currency': currency
            }
            
        except Exception as e:
            logger.error(f"Failed to create checkout: {str(e)}")
            raise
    
    async def get_supported_currencies(self) -> List[str]:
        """Get list of supported cryptocurrencies"""
        try:
            result = await self._request("GET", "currencies")
            return result['data']
        except Exception as e:
            logger.error(f"Failed to get currencies: {str(e)}")
            return []
    
    async def get_exchange_rates(self, currency: str = 'USD') -> Dict:
        """Get current exchange rates"""
        try:
            result = await self._request("GET", f"exchange-rates?currency={currency}")
            return result['data']
        except Exception as e:
            logger.error(f"Failed to get exchange rates: {str(e)}")
            raise


# Singleton instance
crypto_payment_service = CryptoPaymentService()