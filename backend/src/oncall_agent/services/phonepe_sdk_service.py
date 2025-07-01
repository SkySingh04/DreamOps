"""PhonePe Payment Gateway Integration using Official SDK"""
import uuid
from typing import Any

# Try to import PhonePe SDK, fall back to mock if not available
try:
    from phonepe.sdk.pg.common.exceptions import PhonePeException
    from phonepe.sdk.pg.env import Env
    from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import (
        StandardCheckoutPayRequest,
    )
    from phonepe.sdk.pg.payments.v2.standard_checkout_client import (
        StandardCheckoutClient,
    )
    PHONEPE_SDK_AVAILABLE = True
except ImportError:
    # SDK not available, we'll use the mock service
    PHONEPE_SDK_AVAILABLE = False
    # Define dummy classes to prevent errors
    class PhonePeException(Exception):
        def __init__(self, message="", code=None, http_status_code=None):
            super().__init__(message)
            self.message = message
            self.code = code
            self.http_status_code = http_status_code
    class Env:
        PRODUCTION = "PRODUCTION"
        TEST = "TEST"
    class StandardCheckoutPayRequest:
        pass
    class StandardCheckoutClient:
        _instance = None

        @classmethod
        def get_instance(cls, **kwargs):
            return cls()

        def pay(self, request):
            pass

        def get_order_status(self, **kwargs):
            pass

        def validate_callback(self, **kwargs):
            pass

from ..api.payment_models import (
    PaymentCheckStatusResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
)
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PhonePeSDKService:
    """PhonePe payment gateway service using official SDK"""

    def __init__(self):
        if not PHONEPE_SDK_AVAILABLE:
            raise ImportError(
                "PhonePe SDK is not available. Please install it or use the mock service. "
                "The SDK may need to be installed from a private repository."
            )

        config = get_config()

        # PhonePe SDK configuration - Use proper test credentials
        self.client_id = config.phonepe_merchant_id or "MERCHANTUAT"
        self.client_secret = config.phonepe_salt_key or "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399"
        self.client_version = 1

        # Set environment
        self.env = Env.SANDBOX if config.environment == "development" else Env.PRODUCTION
        self.should_publish_events = False

        # URLs
        self.redirect_url = config.phonepe_redirect_url
        self.callback_url = config.phonepe_callback_url

        # Initialize client
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize PhonePe SDK client"""
        try:
            self._client = StandardCheckoutClient.get_instance(
                client_id=self.client_id,
                client_secret=self.client_secret,
                client_version=self.client_version,
                env=self.env,
                should_publish_events=self.should_publish_events
            )
            logger.info("PhonePe SDK client initialized successfully")
        except PhonePeException as e:
            logger.error(f"Failed to initialize PhonePe SDK: {e.message}")
            # Try to reset and reinitialize
            StandardCheckoutClient._instance = None
            try:
                self._client = StandardCheckoutClient.get_instance(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    client_version=self.client_version,
                    env=self.env,
                    should_publish_events=self.should_publish_events
                )
            except Exception as e:
                logger.error(f"Failed to reinitialize PhonePe SDK: {e}")
                raise

    async def initiate_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Initiate a payment with PhonePe SDK"""
        try:
            # Generate unique order ID
            merchant_order_id = f"ORDER_{uuid.uuid4().hex[:12].upper()}"

            # Create redirect URL with transaction ID
            ui_redirect_url = f"{self.redirect_url}?transaction_id={merchant_order_id}"

            logger.info(f"Initiating PhonePe payment for order: {merchant_order_id}")
            logger.debug(f"Amount: {payment_request.amount} paise")
            logger.debug(f"Redirect URL: {ui_redirect_url}")

            # Build payment request using SDK
            standard_pay_request = StandardCheckoutPayRequest.build_request(
                merchant_order_id=merchant_order_id,
                amount=payment_request.amount,  # Amount in paise
                redirect_url=ui_redirect_url
            )

            # Initiate payment
            standard_pay_response = self._client.pay(standard_pay_request)

            if standard_pay_response and standard_pay_response.redirect_url:
                logger.info(f"Payment initiated successfully. Order ID: {standard_pay_response.order_id}")

                # Store transaction in database (implement based on your DB)
                await self._store_transaction(
                    merchant_order_id=merchant_order_id,
                    phonepe_order_id=standard_pay_response.order_id,
                    team_id=payment_request.team_id,
                    amount=payment_request.amount,
                    plan=payment_request.plan,
                    status=PaymentStatus.INITIATED,
                    expire_at=standard_pay_response.expire_at
                )

                return PaymentResponse(
                    success=True,
                    payment_id=merchant_order_id,
                    transaction_id=standard_pay_response.order_id,
                    status=PaymentStatus.INITIATED,
                    redirect_url=standard_pay_response.redirect_url,
                    message="Payment initiated successfully"
                )
            else:
                logger.error("No redirect URL received from PhonePe")
                return PaymentResponse(
                    success=False,
                    payment_id=merchant_order_id,
                    transaction_id="",
                    status=PaymentStatus.FAILED,
                    error="Failed to get payment URL"
                )

        except PhonePeException as e:
            logger.error(f"PhonePe SDK error: Code={e.code}, Message={e.message}, HTTP Status={e.http_status_code}")
            return PaymentResponse(
                success=False,
                payment_id="",
                transaction_id="",
                status=PaymentStatus.FAILED,
                error=f"PhonePe error: {e.message}"
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

            # Get order status
            order_status_response = self._client.get_order_status(
                merchant_order_id=merchant_order_id,
                details=True  # Get all payment details
            )

            # Map PhonePe state to our status
            state_map = {
                "COMPLETED": PaymentStatus.SUCCESS,
                "FAILED": PaymentStatus.FAILED,
                "PENDING": PaymentStatus.PENDING,
            }

            payment_status = state_map.get(order_status_response.state, PaymentStatus.PENDING)

            # Get latest payment details
            payment_details = None
            if order_status_response.payment_details:
                latest_payment = order_status_response.payment_details[-1]  # Get latest attempt
                payment_details = {
                    "payment_mode": latest_payment.payment_mode,
                    "transaction_id": latest_payment.transaction_id,
                    "state": latest_payment.state,
                    "error_code": getattr(latest_payment, 'error_code', None),
                    "detailed_error_code": getattr(latest_payment, 'detailed_error_code', None)
                }

            return PaymentCheckStatusResponse(
                success=True,
                payment_status=payment_status,
                transaction_details={
                    "order_id": order_status_response.order_id,
                    "state": order_status_response.state,
                    "amount": order_status_response.amount,
                    "expire_at": order_status_response.expire_at,
                    "payment_details": payment_details
                },
                message=f"Order state: {order_status_response.state}"
            )

        except PhonePeException as e:
            logger.error(f"PhonePe SDK error checking status: {e.message}")
            return PaymentCheckStatusResponse(
                success=False,
                payment_status=PaymentStatus.FAILED,
                message=f"Error: {e.message}"
            )
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return PaymentCheckStatusResponse(
                success=False,
                payment_status=PaymentStatus.FAILED,
                message=str(e)
            )

    async def validate_callback(self, username: str, password: str,
                              authorization_header: str, callback_body: str) -> dict[str, Any]:
        """Validate PhonePe callback"""
        try:
            callback_response = self._client.validate_callback(
                username=username,
                password=password,
                callback_header_data=authorization_header,
                callback_response_data=callback_body
            )

            # Process callback based on type
            if callback_response.callback_type == "CHECKOUT_ORDER_COMPLETED":
                return {
                    "success": True,
                    "type": "order_completed",
                    "order_id": callback_response.callback_data.order_id,
                    "merchant_order_id": callback_response.callback_data.merchant_order_id,
                    "state": callback_response.callback_data.state,
                    "amount": callback_response.callback_data.amount
                }
            elif callback_response.callback_type == "CHECKOUT_ORDER_FAILED":
                return {
                    "success": False,
                    "type": "order_failed",
                    "order_id": callback_response.callback_data.order_id,
                    "merchant_order_id": callback_response.callback_data.merchant_order_id,
                    "error_code": callback_response.callback_data.error_code,
                    "detailed_error_code": callback_response.callback_data.detailed_error_code
                }
            else:
                return {
                    "success": True,
                    "type": callback_response.callback_type,
                    "data": callback_response.callback_data
                }

        except PhonePeException as e:
            logger.error(f"Invalid callback: {e.message}")
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
_phonepe_sdk_service: PhonePeSDKService | None = None


def get_phonepe_sdk_service() -> PhonePeSDKService:
    """Get PhonePe SDK service singleton instance"""
    global _phonepe_sdk_service
    if _phonepe_sdk_service is None:
        _phonepe_sdk_service = PhonePeSDKService()
    return _phonepe_sdk_service
