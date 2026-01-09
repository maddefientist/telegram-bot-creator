"""Bot-related schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.bot import BotStatus
from schemas.botspec import BotSpec
from schemas.subscription import SubscriptionResponse


class BotCreate(BaseModel):
    """Schema for creating a new bot."""

    name: str = Field(min_length=1, max_length=100)
    telegram_token: str = Field(min_length=40, max_length=100)
    description: str = Field(default="", max_length=500)
    price_per_month_sol: float = Field(gt=0)


class BotUpdate(BaseModel):
    """Schema for updating a bot."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    spec_json: dict[str, Any] | None = None


class BotResponse(BaseModel):
    """Schema for bot response."""

    id: uuid.UUID
    name: str
    telegram_username: str | None
    spec_json: dict[str, Any]
    status: BotStatus
    last_heartbeat: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    subscription: SubscriptionResponse | None = None

    model_config = {"from_attributes": True}


class BotListResponse(BaseModel):
    """Schema for listing bots."""

    id: uuid.UUID
    name: str
    telegram_username: str | None
    status: BotStatus
    last_heartbeat: datetime | None
    last_error: str | None
    created_at: datetime
    subscription: SubscriptionResponse | None = None

    model_config = {"from_attributes": True}


class BotStatusResponse(BaseModel):
    """Schema for bot status response."""

    id: uuid.UUID
    status: BotStatus
    last_heartbeat: datetime | None
    last_error: str | None
    container_id: str | None
    logs: list[str] = Field(default_factory=list)


class BotLogsResponse(BaseModel):
    """Schema for bot logs response."""

    bot_id: uuid.UUID
    logs: list[str]
    since: datetime | None


class ValidateBotSpecRequest(BaseModel):
    """Schema for validating a BotSpec."""

    spec: dict[str, Any]


class ValidateBotSpecResponse(BaseModel):
    """Schema for BotSpec validation response."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    validated_spec: dict[str, Any] | None = None
