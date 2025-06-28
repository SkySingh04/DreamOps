"""Mock PhonePe Payment Gateway for Testing"""
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from ..api.payment_models import (
    PaymentCheckStatusResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PhonePeMockService:
    """Mock PhonePe payment gateway service for testing"""

    def __init__(self):
        # Mock configuration
        self.client_id = "MOCK_TEST_CLIENT"
        self.redirect_url = "http://localhost:3000/payment/callback"
        self.callback_url = "http://localhost:8000/api/v1/payments/callback"

        # In-memory storage for mock transactions
        self._transactions = {}

        logger.info("PhonePe Mock Service initialized for testing")

    async def initiate_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Mock payment initiation"""
        try:
            # Generate unique order ID
            merchant_order_id = f"MOCK_ORDER_{uuid.uuid4().hex[:12].upper()}"
            phonepe_order_id = f"PHONEPE_{uuid.uuid4().hex[:8].upper()}"

            # Create mock redirect URL
            mock_payment_url = f"http://localhost:3000/mock-payment?order_id={merchant_order_id}&amount={payment_request.amount}"

            logger.info(f"Mock: Initiating PhonePe payment for order: {merchant_order_id}")
            logger.info(f"Mock: Amount: {payment_request.amount} paise (₹{payment_request.amount/100})")

            # Store mock transaction
            expire_at = int((datetime.now() + timedelta(minutes=15)).timestamp())
            self._transactions[merchant_order_id] = {
                "merchant_order_id": merchant_order_id,
                "phonepe_order_id": phonepe_order_id,
                "user_id": payment_request.user_id,
                "amount": payment_request.amount,
                "plan": payment_request.plan,
                "status": PaymentStatus.INITIATED,
                "expire_at": expire_at,
                "created_at": datetime.now().isoformat(),
                "payment_mode": "UPI_INTENT"  # Mock payment mode
            }

            return PaymentResponse(
                success=True,
                payment_id=merchant_order_id,
                transaction_id=phonepe_order_id,
                status=PaymentStatus.INITIATED,
                redirect_url=mock_payment_url,
                message="Mock payment initiated successfully - This is a test transaction"
            )

        except Exception as e:
            logger.error(f"Error in mock payment initiation: {e}")
            return PaymentResponse(
                success=False,
                payment_id="",
                transaction_id="",
                status=PaymentStatus.FAILED,
                error=f"Mock payment error: {str(e)}"
            )

    async def check_payment_status(self, merchant_order_id: str) -> PaymentCheckStatusResponse:
        """Mock payment status check"""
        try:
            logger.info(f"Mock: Checking payment status for order: {merchant_order_id}")

            # Get mock transaction
            transaction = self._transactions.get(merchant_order_id)
            if not transaction:
                return PaymentCheckStatusResponse(
                    success=False,
                    payment_status=PaymentStatus.FAILED,
                    message="Mock: Order not found"
                )

            # Simulate payment progression for demo
            # 70% chance of success, 20% pending, 10% failed
            random_outcome = random.randint(1, 100)

            if random_outcome <= 70:
                # Mock successful payment
                payment_status = PaymentStatus.SUCCESS
                state = "COMPLETED"
                self._transactions[merchant_order_id]["status"] = PaymentStatus.SUCCESS
            elif random_outcome <= 90:
                # Mock pending payment
                payment_status = PaymentStatus.PENDING
                state = "PENDING"
            else:
                # Mock failed payment
                payment_status = PaymentStatus.FAILED
                state = "FAILED"
                self._transactions[merchant_order_id]["status"] = PaymentStatus.FAILED

            # Mock payment details
            payment_details = {
                "payment_mode": transaction.get("payment_mode", "UPI_INTENT"),
                "transaction_id": transaction["phonepe_order_id"],
                "state": state,
                "error_code": None if payment_status != PaymentStatus.FAILED else "MOCK_ERROR",
                "detailed_error_code": None if payment_status != PaymentStatus.FAILED else "MOCK_PAYMENT_DECLINED"
            }

            return PaymentCheckStatusResponse(
                success=True,
                payment_status=payment_status,
                transaction_details={
                    "order_id": transaction["phonepe_order_id"],
                    "state": state,
                    "amount": transaction["amount"],
                    "expire_at": transaction["expire_at"],
                    "payment_details": payment_details,
                    "mock_mode": True
                },
                message=f"Mock: Order state: {state}"
            )

        except Exception as e:
            logger.error(f"Error in mock payment status check: {e}")
            return PaymentCheckStatusResponse(
                success=False,
                payment_status=PaymentStatus.FAILED,
                message=f"Mock error: {str(e)}"
            )

    async def validate_callback(self, username: str, password: str,
                              authorization_header: str, callback_body: str) -> dict[str, Any]:
        """Mock callback validation"""
        try:
            logger.info("Mock: Validating PhonePe callback")

            # Mock successful callback validation
            return {
                "success": True,
                "type": "order_completed",
                "order_id": f"PHONEPE_{uuid.uuid4().hex[:8].upper()}",
                "merchant_order_id": f"MOCK_ORDER_{uuid.uuid4().hex[:12].upper()}",
                "state": "COMPLETED",
                "amount": 10000,  # Mock amount in paise
                "mock_mode": True
            }

        except Exception as e:
            logger.error(f"Error in mock callback validation: {e}")
            return {"success": False, "error": f"Mock error: {str(e)}"}

    def complete_mock_payment(self, merchant_order_id: str) -> bool:
        """Manually complete a mock payment for testing"""
        try:
            if merchant_order_id in self._transactions:
                self._transactions[merchant_order_id]["status"] = PaymentStatus.SUCCESS
                logger.info(f"Mock: Payment {merchant_order_id} marked as completed")
                return True
            return False
        except Exception as e:
            logger.error(f"Error completing mock payment: {e}")
            return False

    def fail_mock_payment(self, merchant_order_id: str) -> bool:
        """Manually fail a mock payment for testing"""
        try:
            if merchant_order_id in self._transactions:
                self._transactions[merchant_order_id]["status"] = PaymentStatus.FAILED
                logger.info(f"Mock: Payment {merchant_order_id} marked as failed")
                return True
            return False
        except Exception as e:
            logger.error(f"Error failing mock payment: {e}")
            return False

    def get_all_mock_transactions(self) -> dict[str, Any]:
        """Get all mock transactions for debugging"""
        return self._transactions


# Singleton instance for mock service
_phonepe_mock_service: PhonePeMockService | None = None


def get_phonepe_mock_service() -> PhonePeMockService:
    """Get PhonePe Mock service singleton instance"""
    global _phonepe_mock_service
    if _phonepe_mock_service is None:
        _phonepe_mock_service = PhonePeMockService()
    return _phonepe_mock_service
