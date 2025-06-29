"""PhonePe Payment API Router"""
import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ...config import get_config
from ...services.phonepe_mock_service import get_phonepe_mock_service

# Try to import SDK service, but don't fail if it's not available
try:
    from ...services.phonepe_sdk_service import get_phonepe_sdk_service
    PHONEPE_SDK_AVAILABLE = True
except ImportError:
    PHONEPE_SDK_AVAILABLE = False
    get_phonepe_sdk_service = None

from ..payment_models import (
    PaymentCheckStatusRequest,
    PaymentCheckStatusResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


def get_payment_service():
    """Get the appropriate payment service based on environment"""
    import os

    # Force mock service for development - check multiple environment indicators
    use_mock = (
        os.getenv("NODE_ENV") == "development" or
        os.getenv("ENVIRONMENT") == "local" or
        os.getenv("ENVIRONMENT") == "development" or
        os.getenv("USE_MOCK_PAYMENTS", "").lower() == "true"
    )

    if use_mock:
        logger.info("Using PhonePe Mock Service for testing")
        return get_phonepe_mock_service()
    else:
        # Check if SDK is available
        if not PHONEPE_SDK_AVAILABLE:
            logger.warning("PhonePe SDK not available. Using mock service instead.")
            return get_phonepe_mock_service()
        
        # Try to use SDK service, fall back to mock if initialization fails
        try:
            logger.info("Attempting to use PhonePe SDK Service")
            return get_phonepe_sdk_service()
        except Exception as e:
            logger.warning(f"Failed to initialize PhonePe SDK: {e}. Using mock service instead.")
            return get_phonepe_mock_service()


@router.post("/initiate", response_model=PaymentResponse)
async def initiate_payment(
    request: Request,
    current_user: dict | None = None  # Make optional for testing
):
    """Initiate a new payment with PhonePe"""
    try:
        # Get JSON body directly
        body = await request.json()
        payment_request = PaymentRequest(**body)

        # For testing, allow without authentication
        if current_user and payment_request.user_id != str(current_user.get("id", "")):
            raise HTTPException(status_code=403, detail="Unauthorized user access")

        phonepe_service = get_payment_service()
        response = await phonepe_service.initiate_payment(payment_request)

        if not response.success:
            raise HTTPException(status_code=400, detail=response.error)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback")
async def payment_callback(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle PhonePe S2S callback"""
    try:
        # Get request body
        body = await request.json()

        phonepe_service = get_payment_service()
        result = await phonepe_service.validate_callback(
            username="test_username",
            password="test_password",
            authorization_header=request.headers.get("authorization", ""),
            callback_body=str(body)
        )

        if result["success"]:
            # Extract payment details
            transaction_id = result.get("transaction_id")
            payment_details = result.get("payment_details", {})
            amount = payment_details.get("amount", 0) / 100  # Convert from paise

            # Parse user_id from transaction_id or metadata
            # In production, this would be stored properly
            user_id = "1"  # Default for testing

            # Determine plan based on amount
            plan_id = "free"
            if amount == 999:
                plan_id = "starter"
            elif amount == 2999:
                plan_id = "pro"
            elif amount == 9999:
                plan_id = "enterprise"

            # Upgrade the user plan
            background_tasks.add_task(
                upgrade_user_plan_async,
                user_id=user_id,
                plan_id=plan_id,
                transaction_id=transaction_id
            )

            # Send notification
            background_tasks.add_task(
                send_payment_notification,
                transaction_id=transaction_id,
                status="success"
            )

        # PhonePe expects 200 OK response
        return JSONResponse(
            status_code=200,
            content={"success": True}
        )

    except Exception as e:
        logger.error(f"Error processing payment callback: {e}")
        # Still return 200 to PhonePe to avoid retries
        return JSONResponse(
            status_code=200,
            content={"success": False, "error": str(e)}
        )


@router.get("/redirect")
async def payment_redirect(
    transaction_id: str,
    code: str = None,
    checksum: str = None
):
    """Handle PhonePe redirect after payment"""
    try:
        phonepe_service = get_payment_service()

        # Check payment status
        status_response = await phonepe_service.check_payment_status(transaction_id)

        # Redirect to appropriate frontend page
        if status_response.success and status_response.payment_status == PaymentStatus.SUCCESS:
            return RedirectResponse(
                url=f"/payment/success?transaction_id={transaction_id}",
                status_code=302
            )
        else:
            return RedirectResponse(
                url=f"/payment/failed?transaction_id={transaction_id}&reason={status_response.message}",
                status_code=302
            )

    except Exception as e:
        logger.error(f"Error handling payment redirect: {e}")
        return RedirectResponse(
            url=f"/payment/error?message={str(e)}",
            status_code=302
        )


@router.post("/status", response_model=PaymentCheckStatusResponse)
async def check_payment_status(
    status_request: PaymentCheckStatusRequest,
    current_user: dict | None = None  # Make optional for testing
):
    """Check payment status from PhonePe"""
    try:
        phonepe_service = get_payment_service()
        response = await phonepe_service.check_payment_status(
            status_request.merchant_transaction_id
        )

        return response

    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans with pricing"""
    plans = {
        "FREE": {
            "name": "Free",
            "price": 0,
            "currency": "INR",
            "features": [
                "5 incidents per month",
                "Basic integrations",
                "Community support",
                "7-day data retention"
            ],
            "limits": {
                "incidents_per_month": 5,
                "team_members": 3,
                "integrations": ["kubernetes", "github"],
                "data_retention_days": 7
            }
        },
        "STARTER": {
            "name": "Starter",
            "price": 999,  # ₹999/month
            "currency": "INR",
            "features": [
                "50 incidents per month",
                "All integrations",
                "Email support",
                "30-day data retention",
                "Custom alert rules"
            ],
            "limits": {
                "incidents_per_month": 50,
                "team_members": 10,
                "integrations": "all",
                "data_retention_days": 30
            }
        },
        "PROFESSIONAL": {
            "name": "Professional",
            "price": 4999,  # ₹4999/month
            "currency": "INR",
            "features": [
                "Unlimited incidents",
                "All integrations",
                "Priority support",
                "90-day data retention",
                "Advanced analytics",
                "Custom workflows"
            ],
            "limits": {
                "incidents_per_month": -1,  # unlimited
                "team_members": 50,
                "integrations": "all",
                "data_retention_days": 90
            }
        },
        "ENTERPRISE": {
            "name": "Enterprise",
            "price": "custom",
            "currency": "INR",
            "features": [
                "Everything in Professional",
                "Unlimited team members",
                "365-day data retention",
                "24/7 phone support",
                "Custom integrations",
                "SLA guarantees",
                "On-premise deployment option"
            ],
            "limits": {
                "incidents_per_month": -1,
                "team_members": -1,
                "integrations": "all",
                "data_retention_days": 365
            }
        }
    }

    return plans


@router.post("/test/mock-payment")
async def test_mock_payment():
    """Test endpoint to create a mock payment for development"""
    try:
        # Create a test payment request
        test_payment = PaymentRequest(
            user_id="1",
            amount=99900,  # ₹999 in paise
            plan="STARTER"
        )

        mock_service = get_phonepe_mock_service()
        response = await mock_service.initiate_payment(test_payment)

        return {
            "success": True,
            "message": "Test payment created successfully",
            "payment_details": response,
            "instructions": "This is a mock payment for testing. Use the returned payment_id to check status."
        }

    except Exception as e:
        logger.error(f"Error creating test payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/complete-mock/{payment_id}")
async def complete_mock_payment(payment_id: str):
    """Test endpoint to manually complete a mock payment"""
    try:
        mock_service = get_phonepe_mock_service()
        success = mock_service.complete_mock_payment(payment_id)

        if success:
            return {
                "success": True,
                "message": f"Mock payment {payment_id} marked as completed",
                "payment_id": payment_id
            }
        else:
            raise HTTPException(status_code=404, detail="Payment not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing mock payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/mock-transactions")
async def get_mock_transactions():
    """Test endpoint to view all mock transactions"""
    try:
        mock_service = get_phonepe_mock_service()
        transactions = mock_service.get_all_mock_transactions()

        return {
            "success": True,
            "transactions": transactions,
            "count": len(transactions)
        }

    except Exception as e:
        logger.error(f"Error getting mock transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/environment")
async def debug_environment():
    """Debug endpoint to check environment configuration"""
    config = get_config()
    return {
        "environment": config.environment,
        "using_mock_service": config.environment in ["development", "local"],
        "phonepe_merchant_id": config.phonepe_merchant_id,
        "api_host": config.api_host,
        "api_port": config.api_port
    }


async def send_payment_notification(transaction_id: str, status: str):
    """Send payment notification - implement based on your notification system"""
    logger.info(f"Payment notification: Transaction {transaction_id} - Status: {status}")
    # TODO: Implement email/slack/webhook notifications


async def upgrade_user_plan_async(user_id: str, plan_id: str, transaction_id: str):
    """Async helper to upgrade user plan after successful payment"""
    try:
        # Make HTTP request to alert tracking service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/alert-tracking/upgrade-plan",
                params={
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "transaction_id": transaction_id
                }
            )

            if response.status_code == 200:
                logger.info(f"Successfully upgraded user {user_id} to plan {plan_id}")
            else:
                logger.error(f"Failed to upgrade user plan: {response.text}")
    except Exception as e:
        logger.error(f"Error upgrading user plan: {e}")
