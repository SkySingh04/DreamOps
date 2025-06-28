"""PhonePe Payment Gateway Integration using PhonePe API"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging
from phonepe import PhonePe

from ..config import get_config
from ..utils.logger import get_logger
from ..api.payment_models import (
    PaymentRequest, PaymentResponse, PaymentStatus,
    PaymentCheckStatusResponse, SubscriptionPlan
)


logger = get_logger(__name__)


class PhonePeSDKService:
    """PhonePe payment gateway service using PhonePe API"""
    
    def __init__(self):
        config = get_config()
        
        # PhonePe API configuration
        self.merchant_id = config.phonepe_merchant_id or "MERCHANTUAT"
        self.salt_key = config.phonepe_salt_key or "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399"
        
        # Environment URLs
        self.is_production = config.environment != "development"
        
        # URLs
        self.redirect_url = config.phonepe_redirect_url
        self.callback_url = config.phonepe_callback_url
        
        # Initialize PhonePe client
        self._client = PhonePe(
            merchant_id=self.merchant_id,
            salt_key=self.salt_key,
            production=self.is_production
        )
    
    
    async def initiate_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Initiate a payment with PhonePe API"""
        try:
            # Generate unique order ID
            merchant_order_id = f"ORDER_{uuid.uuid4().hex[:12].upper()}"
            
            # Create redirect URL with transaction ID
            ui_redirect_url = f"{self.redirect_url}?transaction_id={merchant_order_id}"
            
            logger.info(f"Initiating PhonePe payment for order: {merchant_order_id}")
            logger.debug(f"Amount: {payment_request.amount} paise")
            logger.debug(f"Redirect URL: {ui_redirect_url}")
            
            # Create order using PhonePe API
            order_data = {
                'merchantOrderId': merchant_order_id,
                'amount': payment_request.amount,  # Amount in paise
                'redirectUrl': ui_redirect_url,
                'callbackUrl': self.callback_url
            }
            
            # Create order
            response = self._client.create_order(order_data)
            
            if response and response.get('success') and response.get('data', {}).get('redirectUrl'):
                redirect_url = response['data']['redirectUrl']
                transaction_id = response['data'].get('transactionId', merchant_order_id)
                
                logger.info(f"Payment initiated successfully. Order ID: {merchant_order_id}")
                
                # Store transaction in database (implement based on your DB)
                await self._store_transaction(
                    merchant_order_id=merchant_order_id,
                    phonepe_order_id=transaction_id,
                    team_id=payment_request.team_id,
                    amount=payment_request.amount,
                    plan=payment_request.plan,
                    status=PaymentStatus.INITIATED
                )
                
                return PaymentResponse(
                    success=True,
                    payment_id=merchant_order_id,
                    transaction_id=transaction_id,
                    status=PaymentStatus.INITIATED,
                    redirect_url=redirect_url,
                    message="Payment initiated successfully"
                )
            else:
                error_msg = response.get('message', 'Failed to get payment URL')
                logger.error(f"No redirect URL received from PhonePe: {error_msg}")
                return PaymentResponse(
                    success=False,
                    payment_id=merchant_order_id,
                    transaction_id="",
                    status=PaymentStatus.FAILED,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error initiating PhonePe payment: {e}")
            return PaymentResponse(
                success=False,
                payment_id="",
                transaction_id="",
                status=PaymentStatus.FAILED,
                error=str(e)
            )
    
    async def check_payment_status(self, merchant_order_id: str) -> PaymentCheckStatusResponse:
        """Check payment status from PhonePe"""
        try:
            logger.info(f"Checking payment status for order: {merchant_order_id}")
            
            # Check transaction status
            response = self._client.check_txn_status(merchant_order_id)
            
            if response and response.get('success'):
                data = response.get('data', {})
                state = data.get('state', 'PENDING')
                
                # Map PhonePe state to our status
                state_map = {
                    "COMPLETED": PaymentStatus.SUCCESS,
                    "FAILED": PaymentStatus.FAILED,
                    "PENDING": PaymentStatus.PENDING,
                }
                
                payment_status = state_map.get(state, PaymentStatus.PENDING)
                
                return PaymentCheckStatusResponse(
                    success=True,
                    payment_status=payment_status,
                    transaction_details={
                        "order_id": data.get('transactionId', merchant_order_id),
                        "state": state,
                        "amount": data.get('amount'),
                        "payment_method": data.get('paymentMethod'),
                        "merchant_order_id": merchant_order_id
                    },
                    message=f"Order state: {state}"
                )
            else:
                error_msg = response.get('message', 'Failed to check status')
                logger.error(f"Error checking payment status: {error_msg}")
                return PaymentCheckStatusResponse(
                    success=False,
                    payment_status=PaymentStatus.FAILED,
                    message=error_msg
                )
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return PaymentCheckStatusResponse(
                success=False,
                payment_status=PaymentStatus.FAILED,
                message=str(e)
            )
    
    async def validate_callback(self, x_verify_header: str, callback_body: str) -> Dict[str, Any]:
        """Validate PhonePe callback"""
        try:
            # Verify webhook checksum
            is_valid = self._client.verify_webhook_checksum(
                x_verify_header=x_verify_header,
                callback_body=callback_body
            )
            
            if is_valid:
                import json
                callback_data = json.loads(callback_body)
                
                # Extract transaction data
                response_data = callback_data.get('response', {})
                state = response_data.get('state', 'UNKNOWN')
                
                if state == "COMPLETED":
                    return {
                        "success": True,
                        "type": "order_completed",
                        "order_id": response_data.get('transactionId'),
                        "merchant_order_id": response_data.get('merchantOrderId'),
                        "state": state,
                        "amount": response_data.get('amount')
                    }
                elif state == "FAILED":
                    return {
                        "success": False,
                        "type": "order_failed",
                        "order_id": response_data.get('transactionId'),
                        "merchant_order_id": response_data.get('merchantOrderId'),
                        "error_code": response_data.get('code'),
                        "message": response_data.get('message')
                    }
                else:
                    return {
                        "success": True,
                        "type": "order_status_update",
                        "state": state,
                        "data": response_data
                    }
            else:
                logger.error("Invalid webhook checksum")
                return {"success": False, "error": "Invalid callback signature"}
                
        except Exception as e:
            logger.error(f"Error validating callback: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_transaction(self, **kwargs):
        """Store transaction in database - implement based on your DB"""
        # TODO: Implement database storage
        logger.info(f"Storing transaction: {kwargs}")
    
    async def _update_transaction_status(self, **kwargs):
        """Update transaction status in database - implement based on your DB"""
        # TODO: Implement database update
        logger.info(f"Updating transaction status: {kwargs}")


# Singleton instance
_phonepe_sdk_service: Optional[PhonePeSDKService] = None


def get_phonepe_sdk_service() -> PhonePeSDKService:
    """Get PhonePe SDK service singleton instance"""
    global _phonepe_sdk_service
    if _phonepe_sdk_service is None:
        _phonepe_sdk_service = PhonePeSDKService()
    return _phonepe_sdk_service