"""Admin-related schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.bot import BotStatus
from models.invoice import InvoiceStatus
from models.subscription import SubscriptionState
from models.user import UserRole


class AdminSettings(BaseModel):
    """Schema for admin-configurable settings."""

    pricing_min_sol: float = Field(gt=0)
    pricing_max_sol: float = Field(gt=0)
    default_price_sol: float = Field(gt=0)
    grace_days: int = Field(ge=0, le=30)
    ai_generation_rate_limit: int = Field(ge=1, le=100)


class AdminUserResponse(BaseModel):
    """Schema for admin user view."""

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    bots_count: int
    total_paid_sol: float

    model_config = {"from_attributes": True}


class AdminBotResponse(BaseModel):
    """Schema for admin bot view."""

    id: uuid.UUID
    owner_id: uuid.UUID
    owner_email: str
    name: str
    telegram_username: str | None
    status: BotStatus
    subscription_state: SubscriptionState | None
    subscription_active_until: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminInvoiceResponse(BaseModel):
    """Schema for admin invoice view."""

    id: uuid.UUID
    bot_id: uuid.UUID
    bot_name: str
    owner_email: str
    amount_sol: float
    status: InvoiceStatus
    tx_signature: str | None
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None

    model_config = {"from_attributes": True}


class AdminOverrideRequest(BaseModel):
    """Schema for admin override actions."""

    action: str  # "activate", "deactivate", "extend", "cancel"
    reason: str = Field(min_length=1, max_length=500)
    extend_days: int | None = Field(default=None, ge=1, le=365)


class AdminStatsResponse(BaseModel):
    """Schema for admin dashboard stats."""

    total_users: int
    total_bots: int
    active_bots: int
    total_invoices: int
    paid_invoices: int
    total_revenue_sol: float
    active_subscriptions: int
