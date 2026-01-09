"""Subscription-related schemas."""
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from models.subscription import SubscriptionState


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""

    id: uuid.UUID
    bot_id: uuid.UUID
    price_per_month_sol: float
    state: SubscriptionState
    active_until: datetime | None
    grace_until: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionUpdate(BaseModel):
    """Schema for updating subscription (admin only for most fields)."""

    price_per_month_sol: float | None = Field(default=None, gt=0)
    state: SubscriptionState | None = None
    active_until: datetime | None = None


class PricingTier(BaseModel):
    """Schema for pricing tiers."""

    id: str
    name: str
    description: str
    price_sol: Annotated[float, Field(gt=0)]
    features: list[str]
    recommended: bool = False


class PricingConfig(BaseModel):
    """Schema for pricing configuration."""

    min_sol: float
    max_sol: float
    default_sol: float
    tiers: list[PricingTier]


# Default pricing tiers
DEFAULT_PRICING_TIERS = [
    PricingTier(
        id="starter",
        name="Starter",
        description="Basic bot hosting",
        price_sol=0.05,
        features=[
            "Basic commands",
            "Static replies",
            "Community support",
        ],
    ),
    PricingTier(
        id="standard",
        name="Standard",
        description="Full-featured bot",
        price_sol=0.1,
        features=[
            "All Starter features",
            "AI chat (100 msg/day)",
            "Moderation",
            "Email support",
        ],
        recommended=True,
    ),
    PricingTier(
        id="pro",
        name="Pro",
        description="High-volume bot",
        price_sol=0.25,
        features=[
            "All Standard features",
            "AI chat (500 msg/day)",
            "Webhook forwarding",
            "Priority support",
        ],
    ),
]
