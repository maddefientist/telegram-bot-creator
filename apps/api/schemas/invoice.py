"""Invoice-related schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.invoice import InvoiceStatus


class InvoiceCreate(BaseModel):
    """Schema for creating a new invoice."""

    bot_id: uuid.UUID
    months: int = Field(default=1, ge=1, le=12)


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""

    id: uuid.UUID
    bot_id: uuid.UUID
    amount_sol: float
    treasury_address: str
    reference: str
    status: InvoiceStatus
    tx_signature: str | None
    paid_at: datetime | None
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentInfo(BaseModel):
    """Schema for payment information shown to user."""

    invoice_id: uuid.UUID
    amount_sol: float
    recipient: str
    reference: str
    expires_at: datetime
    solana_pay_url: str
    qr_data: str | None = None


class VerifyPaymentRequest(BaseModel):
    """Schema for manual payment verification request."""

    invoice_id: uuid.UUID
    tx_signature: str | None = None  # Optional: provide tx to speed up verification


class VerifyPaymentResponse(BaseModel):
    """Schema for payment verification response."""

    invoice_id: uuid.UUID
    status: InvoiceStatus
    message: str
    subscription_active_until: datetime | None = None
