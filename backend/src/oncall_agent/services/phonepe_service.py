"""PhonePe Payment Gateway Integration Service"""
import base64
import hashlib
import json
import uuid
from typing import Any

import httpx

from ..api.payment_models import (
    PaymentCheckStatusResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
)
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PhonePeService:
    """PhonePe payment gateway service"""

    def __init__(self):
        config = get_config()
        self.merchant_id = config.phonepe_merchant_id
        self.salt_key = config.phonepe_salt_key
        self.salt_index = config.phonepe_salt_index or "1"
        self.base_url = config.phonepe_base_url or "https://api.phonepe.com/apis/hermes"
        self.redirect_url = config.phonepe_redirect_url
        self.callback_url = config.phonepe_callback_url

        # UAT/Testing URLs
        if config.environment == "development":
            self.base_url = "https://api-preprod.phonepe.com/apis/pg-sandbox"

    def _generate_checksum(self, base64_payload: str, endpoint: str) -> str:
        """Generate X-VERIFY checksum for PhonePe API"""
        string_to_hash = base64_payload + endpoint + self.salt_key
        sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
        return sha256_hash + "###" + self.salt_index

    def _generate_status_checksum(self, merchant_id: str, transaction_id: str) -> str:
        """Generate checksum for status check API"""
        string_to_hash = f"/pg/v1/status/{merchant_id}/{transaction_id}" + self.salt_key
        sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
        return sha256_hash + "###" + self.salt_index

    async def initiate_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Initiate a payment with PhonePe"""
        try:
            # Generate unique transaction ID
            merchant_transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"

            # Prepare PhonePe request payload according to official docs
            payload_dict = {
                "merchantId": self.merchant_id,
                "merchantTransactionId": merchant_transaction_id,
                "merchantUserId": payment_request.team_id,
                "amount": payment_request.amount,  # Amount in paise
                "redirectUrl": f"{self.redirect_url}?transaction_id={merchant_transaction_id}",
                "redirectMode": "REDIRECT",
                "callbackUrl": self.callback_url,
                "mobileNumber": payment_request.mobile_number or "9999999999",
                "paymentInstrument": {
                    "type": "PAY_PAGE"  # Using PAY_PAGE for web flow
                }
            }

            # Convert to JSON and base64 encode
            payload_json = json.dumps(payload_dict)
            base64_payload = base64.b64encode(payload_json.encode()).decode()

            # Generate checksum
            checksum = self._generate_checksum(base64_payload, "/pg/v1/pay")

            headers = {
                "Content-Type": "application/json",
                "X-VERIFY": checksum
            }

            request_body = {
                "request": base64_payload
            }

            logger.info(f"Initiating PhonePe payment for transaction: {merchant_transaction_id}")
            logger.debug(f"Request URL: {self.base_url}/pg/v1/pay")
            logger.debug(f"Request headers: {headers}")
            logger.debug(f"Request body: {request_body}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/pg/v1/pay",
                    json=request_body,
                    headers=headers,
                    timeout=30.0
                )

                logger.info(f"PhonePe API response status: {response.status_code}")
                logger.debug(f"PhonePe response: {response.text}")

                if response.status_code == 200:
                    data = response.json()

                    if data.get("success"):
                        # Extract redirect URL from the response
                        instrument_response = data.get("data", {}).get("instrumentResponse", {})
                        redirect_info = instrument_response.get("redirectInfo", {})
                        redirect_url = redirect_info.get("url")

                        if redirect_url:
                            # Store transaction in database (you'll need to implement this)
                            await self._store_transaction(
                                merchant_transaction_id=merchant_transaction_id,
                                team_id=payment_request.team_id,
                                amount=payment_request.amount,
                                plan=payment_request.plan,
                                status=PaymentStatus.INITIATED
                            )

                            return PaymentResponse(
                                success=True,
                                payment_id=merchant_transaction_id,
                                transaction_id=merchant_transaction_id,
                                status=PaymentStatus.INITIATED,
                                redirect_url=redirect_url,
                                message="Payment initiated successfully"
                            )
                        else:
                            logger.error("No redirect URL in PhonePe response")
                            return PaymentResponse(
                                success=False,
                                payment_id=merchant_transaction_id,
                                transaction_id=merchant_transaction_id,
                                status=PaymentStatus.FAILED,
                                error="No redirect URL received"
                            )
                    else:
                        logger.error(f"PhonePe payment initiation failed: {data}")
                        return PaymentResponse(
                            success=False,
                            payment_id=merchant_transaction_id,
                            transaction_id=merchant_transaction_id,
                            status=PaymentStatus.FAILED,
                            error=data.get("message", "Payment initiation failed")
                        )
                else:
                    logger.error(f"PhonePe API error: {response.status_code} - {response.text}")
                    return PaymentResponse(
                        success=False,
                        payment_id=merchant_transaction_id,
                        transaction_id=merchant_transaction_id,
                        status=PaymentStatus.FAILED,
                        error=f"API error: {response.status_code}"
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

    async def handle_callback(self, callback_data: dict[str, Any]) -> dict[str, Any]:
        """Handle PhonePe S2S callback"""
        try:
            # Decode base64 response
            response_data = base64.b64decode(callback_data.get("response", "")).decode()
            response_json = json.loads(response_data)

            # Verify checksum would go here - omitted for brevity

            # Process callback
            success = response_json.get("success", False)
            code = response_json.get("code", "")
            message = response_json.get("message", "")

            if success and code == "PAYMENT_SUCCESS":
                transaction_data = response_json.get("data", {})
                merchant_transaction_id = transaction_data.get("merchantTransactionId")
                phonepe_transaction_id = transaction_data.get("transactionId")
                amount = transaction_data.get("amount")

                # Update transaction status in database
                await self._update_transaction_status(
                    merchant_transaction_id=merchant_transaction_id,
                    status=PaymentStatus.SUCCESS,
                    phonepe_transaction_id=phonepe_transaction_id,
                    callback_data=response_json
                )

                # Update team subscription
                await self._update_team_subscription(merchant_transaction_id)

                return {
                    "success": True,
                    "transaction_id": merchant_transaction_id,
                    "phonepe_transaction_id": phonepe_transaction_id,
                    "amount": amount
                }
            else:
                # Payment failed
                transaction_data = response_json.get("data", {})
                merchant_transaction_id = transaction_data.get("merchantTransactionId")

                await self._update_transaction_status(
                    merchant_transaction_id=merchant_transaction_id,
                    status=PaymentStatus.FAILED,
                    callback_data=response_json,
                    error_message=message
                )

                return {
                    "success": False,
                    "transaction_id": merchant_transaction_id,
                    "error": message
                }

        except Exception as e:
            logger.error(f"Error processing PhonePe callback: {e}")
            return {"success": False, "error": str(e)}

    async def check_payment_status(self, merchant_transaction_id: str) -> PaymentCheckStatusResponse:
        """Check payment status from PhonePe"""
        try:
            checksum = self._generate_status_checksum(self.merchant_id, merchant_transaction_id)

            headers = {
                "Content-Type": "application/json",
                "X-VERIFY": checksum,
                "X-MERCHANT-ID": self.merchant_id
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/pg/v1/status/{self.merchant_id}/{merchant_transaction_id}",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    # Map PhonePe status to our status
                    phonepe_code = data.get("code", "")
                    status_map = {
                        "PAYMENT_SUCCESS": PaymentStatus.SUCCESS,
                        "PAYMENT_ERROR": PaymentStatus.FAILED,
                        "PAYMENT_PENDING": PaymentStatus.PENDING,
                        "PAYMENT_CANCELLED": PaymentStatus.CANCELLED,
                    }

                    payment_status = status_map.get(phonepe_code, PaymentStatus.PENDING)

                    return PaymentCheckStatusResponse(
                        success=data.get("success", False),
                        payment_status=payment_status,
                        transaction_details=data.get("data", {}),
                        message=data.get("message", "")
                    )
                else:
                    return PaymentCheckStatusResponse(
                        success=False,
                        payment_status=PaymentStatus.FAILED,
                        message=f"API error: {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return PaymentCheckStatusResponse(
                success=False,
                payment_status=PaymentStatus.FAILED,
                message=str(e)
            )

    async def _store_transaction(self, **kwargs):
        """Store transaction in database - implement based on your DB"""
        # TODO: Implement database storage
        logger.info(f"Storing transaction: {kwargs}")

    async def _update_transaction_status(self, **kwargs):
        """Update transaction status in database - implement based on your DB"""
        # TODO: Implement database update
        logger.info(f"Updating transaction status: {kwargs}")

    async def _update_team_subscription(self, merchant_transaction_id: str):
        """Update team subscription after successful payment - implement based on your DB"""
        # TODO: Implement subscription update logic
        logger.info(f"Updating team subscription for transaction: {merchant_transaction_id}")


# Singleton instance
_phonepe_service: PhonePeService | None = None


def get_phonepe_service() -> PhonePeService:
    """Get PhonePe service singleton instance"""
    global _phonepe_service
    if _phonepe_service is None:
        _phonepe_service = PhonePeService()
    return _phonepe_service
