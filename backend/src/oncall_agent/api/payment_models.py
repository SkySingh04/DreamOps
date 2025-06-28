"""PhonePe Payment Models and Schemas"""
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    """Supported payment methods"""
    UPI = "UPI"
    CARD = "CARD"
    NET_BANKING = "NET_BANKING"
    WALLET = "WALLET"


class SubscriptionPlan(str, Enum):
    """Available subscription plans"""
    FREE = "FREE"
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class PaymentRequest(BaseModel):
    """Payment initiation request"""
    user_id: str
    amount: int = Field(..., description="Amount in paise (INR smallest unit)")
    plan: SubscriptionPlan
    payment_method: PaymentMethod | None = None
    mobile_number: str | None = Field(None, pattern="^[6-9]\\d{9}$")
    email: str | None = None
    metadata: dict[str, Any] | None = None


class PhonePePaymentRequest(BaseModel):
    """PhonePe API payment request structure"""
    merchantId: str
    merchantTransactionId: str
    merchantUserId: str
    amount: int
    redirectUrl: str
    redirectMode: Literal["POST", "GET", "REDIRECT"] = "REDIRECT"
    callbackUrl: str
    mobileNumber: str | None = None
    paymentInstrument: dict[str, Any] = Field(default={"type": "PAY_PAGE"})


class PaymentResponse(BaseModel):
    """Payment response model"""
    success: bool
    payment_id: str
    transaction_id: str
    status: PaymentStatus
    redirect_url: str | None = None
    message: str | None = None
    error: str | None = None


class PhonePeCallback(BaseModel):
    """PhonePe S2S callback model"""
    success: bool
    code: str
    message: str
    data: dict[str, Any] | None = None


class PaymentTransaction(BaseModel):
    """Payment transaction record"""
    id: str
    user_id: str
    merchant_transaction_id: str
    phonepe_transaction_id: str | None = None
    amount: int
    status: PaymentStatus
    plan: SubscriptionPlan
    payment_method: PaymentMethod | None = None
    initiated_at: datetime
    completed_at: datetime | None = None
    callback_data: dict[str, Any] | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class SubscriptionUpdate(BaseModel):
    """Subscription update model"""
    user_id: str
    plan: SubscriptionPlan
    transaction_id: str
    valid_from: datetime
    valid_until: datetime | None = None
    is_active: bool = True
    features: dict[str, Any] | None = None


class PaymentCheckStatusRequest(BaseModel):
    """Payment status check request"""
    merchant_transaction_id: str


class PaymentCheckStatusResponse(BaseModel):
    """Payment status check response"""
    success: bool
    payment_status: PaymentStatus
    transaction_details: dict[str, Any] | None = None
    message: str | None = None
