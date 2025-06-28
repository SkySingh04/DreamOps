"""PhonePe Payment Models and Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


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
    team_id: str
    amount: int = Field(..., description="Amount in paise (INR smallest unit)")
    plan: SubscriptionPlan
    payment_method: Optional[PaymentMethod] = None
    mobile_number: Optional[str] = Field(None, pattern="^[6-9]\\d{9}$")
    email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PhonePePaymentRequest(BaseModel):
    """PhonePe API payment request structure"""
    merchantId: str
    merchantTransactionId: str
    merchantUserId: str
    amount: int
    redirectUrl: str
    redirectMode: Literal["POST", "GET", "REDIRECT"] = "REDIRECT"
    callbackUrl: str
    mobileNumber: Optional[str] = None
    paymentInstrument: Dict[str, Any] = Field(default={"type": "PAY_PAGE"})


class PaymentResponse(BaseModel):
    """Payment response model"""
    success: bool
    payment_id: str
    transaction_id: str
    status: PaymentStatus
    redirect_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PhonePeCallback(BaseModel):
    """PhonePe S2S callback model"""
    success: bool
    code: str
    message: str
    data: Optional[Dict[str, Any]] = None


class PaymentTransaction(BaseModel):
    """Payment transaction record"""
    id: str
    team_id: str
    merchant_transaction_id: str
    phonepe_transaction_id: Optional[str] = None
    amount: int
    status: PaymentStatus
    plan: SubscriptionPlan
    payment_method: Optional[PaymentMethod] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    callback_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SubscriptionUpdate(BaseModel):
    """Subscription update model"""
    team_id: str
    plan: SubscriptionPlan
    transaction_id: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool = True
    features: Optional[Dict[str, Any]] = None


class PaymentCheckStatusRequest(BaseModel):
    """Payment status check request"""
    merchant_transaction_id: str
    

class PaymentCheckStatusResponse(BaseModel):
    """Payment status check response"""
    success: bool
    payment_status: PaymentStatus
    transaction_details: Optional[Dict[str, Any]] = None
    message: Optional[str] = None