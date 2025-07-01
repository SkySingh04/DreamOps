"""Test PhonePe payment integration"""
import asyncio
import json

from src.oncall_agent.api.payment_models import PaymentRequest, SubscriptionPlan
from src.oncall_agent.services.phonepe_service import PhonePeService


async def test_payment_flow():
    """Test the payment initiation flow"""

    # Initialize PhonePe service
    service = PhonePeService()

    # Create a test payment request
    payment_request = PaymentRequest(
        team_id="test_team_123",
        amount=99900,  # ₹999 in paise
        plan=SubscriptionPlan.STARTER,
        mobile_number="9999999999",  # Test mobile number
        email="test@example.com",
        metadata={
            "test": True,
            "source": "integration_test"
        }
    )

    print("Initiating payment with PhonePe...")
    print(f"Amount: ₹{payment_request.amount / 100}")
    print(f"Plan: {payment_request.plan}")

    # Initiate payment
    response = await service.initiate_payment(payment_request)

    print("\nPayment Response:")
    print(f"Success: {response.success}")
    print(f"Transaction ID: {response.transaction_id}")
    print(f"Status: {response.status}")

    if response.success and response.redirect_url:
        print(f"\nRedirect URL: {response.redirect_url}")
        print("\nTo complete the payment, open the above URL in your browser")
    else:
        print(f"Error: {response.error}")

    return response


async def test_status_check(transaction_id: str):
    """Test payment status check"""
    service = PhonePeService()

    print(f"\nChecking status for transaction: {transaction_id}")

    status_response = await service.check_payment_status(transaction_id)

    print(f"Success: {status_response.success}")
    print(f"Payment Status: {status_response.payment_status}")
    print(f"Message: {status_response.message}")

    if status_response.transaction_details:
        print(f"Details: {json.dumps(status_response.transaction_details, indent=2)}")


if __name__ == "__main__":
    print("PhonePe Payment Integration Test")
    print("================================\n")

    # Test payment initiation
    response = asyncio.run(test_payment_flow())

    # If payment was initiated, check its status
    if response.success and response.transaction_id:
        print("\nPress Enter to check payment status...")
        input()
        asyncio.run(test_status_check(response.transaction_id))
