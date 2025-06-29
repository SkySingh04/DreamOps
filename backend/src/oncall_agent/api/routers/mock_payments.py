"""Mock PhonePe Payment Router for Testing"""
import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...config import get_config
from ..payment_models import PaymentResponse, PaymentStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mock-payments", tags=["mock-payments"])

# In-memory storage for mock transactions
MOCK_TRANSACTIONS: dict[str, dict[str, Any]] = {}

@router.post("/initiate")
async def mock_initiate_payment(request: Request):
    """Mock payment initiation for testing without PhonePe credentials"""
    body = await request.json()

    # Store payment data for later retrieval
    transaction_id = f"MOCK_TXN_{uuid.uuid4().hex[:12].upper()}"

    # Store transaction data in memory (in production, use database)
    MOCK_TRANSACTIONS[transaction_id] = {
        "user_id": body.get("user_id", "1"),
        "amount": body.get("amount", 0),
        "plan": body.get("plan", "starter"),
        "status": "initiated",
        "created_at": datetime.now().isoformat()
    }

    # Simulate PhonePe redirect URL with all necessary params
    redirect_url = f"http://localhost:8000/api/v1/mock-payments/simulate?txn={transaction_id}&amount={body.get('amount', 0)}&user_id={body.get('user_id', '1')}&plan={body.get('plan', 'starter')}"

    return PaymentResponse(
        success=True,
        payment_id=transaction_id,
        transaction_id=transaction_id,
        status=PaymentStatus.INITIATED,
        redirect_url=redirect_url,
        message="Mock payment initiated successfully"
    )

@router.get("/simulate", response_class=HTMLResponse)
async def simulate_payment_page(txn: str, amount: int):
    """Simulate PhonePe payment page"""
    config = get_config()
    # Extract base URL from the redirect URL (e.g., http://localhost:3000)
    redirect_url = config.phonepe_redirect_url or "http://localhost:3000/payment/redirect"
    base_url = redirect_url.replace("/payment/redirect", "")

    html_content = f"""
        <html>
        <head>
            <title>Mock PhonePe Payment</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
                .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h2 {{ color: #5B259F; margin-bottom: 20px; }}
                .amount {{ font-size: 36px; font-weight: bold; color: #333; margin: 20px 0; }}
                .buttons {{ display: flex; gap: 10px; margin-top: 30px; }}
                button {{ flex: 1; padding: 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; }}
                .success {{ background: #4CAF50; color: white; }}
                .success:hover {{ background: #45a049; }}
                .failure {{ background: #f44336; color: white; }}
                .failure:hover {{ background: #da190b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Mock PhonePe Payment</h2>
                <p>Transaction ID: {txn}</p>
                <div class="amount">₹{amount/100:.2f}</div>
                <p>This is a mock payment page for testing.</p>
                <div class="buttons">
                    <button class="success" onclick="window.location.href='{base_url}/payment/redirect?transaction_id={txn}&status=success'">
                        Pay Successfully
                    </button>
                    <button class="failure" onclick="window.location.href='{base_url}/payment/redirect?transaction_id={txn}&status=failed'">
                        Fail Payment
                    </button>
                </div>
            </div>
        </body>
        </html>
        """
    return HTMLResponse(content=html_content)


@router.post("/status")
async def mock_check_payment_status(request: Request):
    """Mock payment status check for testing"""
    body = await request.json()

    # Extract transaction ID from either format
    transaction_id = body.get("merchant_transaction_id") or body.get("transactionId")

    if not transaction_id:
        return {
            "success": False,
            "payment_status": PaymentStatus.FAILED,
            "message": "Transaction ID not provided"
        }

    # For mock payments, check if transaction ID starts with MOCK_
    if transaction_id.startswith("MOCK_"):
        # Get transaction data from memory
        txn_data = MOCK_TRANSACTIONS.get(transaction_id, {})

        # Use stored data or fallback to body/defaults
        user_id = txn_data.get("user_id") or body.get("user_id", "1")
        amount = txn_data.get("amount") or body.get("amount", 10000)
        plan = txn_data.get("plan") or body.get("plan", "starter")

        # Determine plan based on amount or explicit plan
        plan_id = plan.lower()
        
        # Map frontend plan names to backend plan IDs
        plan_mapping = {
            "starter": "starter",
            "professional": "pro",
            "pro": "pro",
            "enterprise": "enterprise"
        }
        
        # Use mapping if available, otherwise fallback to amount-based detection
        if plan_id in plan_mapping:
            plan_id = plan_mapping[plan_id]
        else:
            # Fallback to amount-based detection
            if amount == 99900:  # ₹999 in paise
                plan_id = "starter"
            elif amount == 299900 or amount == 499900:  # ₹2999 or ₹4999 in paise
                plan_id = "pro"
            elif amount == 999900:  # ₹9999 in paise
                plan_id = "enterprise"
            else:
                # Default to starter if amount doesn't match
                plan_id = "starter"

        # Auto-upgrade account for mock payments
        try:
            async with httpx.AsyncClient() as client:
                upgrade_response = await client.post(
                    f"http://localhost:8000/api/v1/alert-tracking/upgrade-plan?user_id={user_id}&plan_id={plan_id}&transaction_id={transaction_id}",
                    headers={"Content-Type": "application/json"}
                )
                if upgrade_response.status_code == 200:
                    logger.info(f"Mock payment: Successfully upgraded user {user_id} to {plan_id}")
                    # Update transaction status
                    if transaction_id in MOCK_TRANSACTIONS:
                        MOCK_TRANSACTIONS[transaction_id]["status"] = "completed"
                else:
                    logger.error(f"Failed to upgrade team: {upgrade_response.status_code} - {upgrade_response.text}")
        except Exception as e:
            logger.error(f"Failed to upgrade team during mock payment: {e}")

        # Simulate successful payment for mock transactions
        return {
            "success": True,
            "payment_status": PaymentStatus.SUCCESS,
            "transaction_details": {
                "transactionId": transaction_id,
                "amount": amount,
                "merchantTransactionId": transaction_id,
                "paymentState": "SUCCESS",
                "user_id": user_id,
                "plan_id": plan_id
            },
            "message": "Mock payment successful"
        }
    else:
        # For real transactions, return pending status
        return {
            "success": True,
            "payment_status": PaymentStatus.PENDING,
            "message": "Payment status pending - use mock payments for testing"
        }
