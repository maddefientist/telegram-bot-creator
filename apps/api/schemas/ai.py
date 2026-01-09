"""AI generation schemas."""
from typing import Any

from pydantic import BaseModel, Field

from schemas.botspec import ModuleType


class GenerateBotSpecRequest(BaseModel):
    """Schema for AI bot spec generation request."""

    description: str = Field(
        min_length=10,
        max_length=2000,
        description="Natural language description of desired bot behavior",
    )
    bot_name: str = Field(
        min_length=1,
        max_length=64,
        description="Name for the bot",
    )
    enabled_modules: list[ModuleType] = Field(
        default_factory=lambda: [ModuleType.BASIC_COMMANDS],
        description="Modules to enable",
    )
    constraints: str = Field(
        default="",
        max_length=1000,
        description="Additional constraints or requirements",
    )


class GenerateBotSpecResponse(BaseModel):
    """Schema for AI bot spec generation response."""

    success: bool
    spec: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    retries: int = 0


class RegenerateBotSpecRequest(BaseModel):
    """Schema for regenerating a bot spec."""

    bot_id: str
    description: str = Field(
        min_length=10,
        max_length=2000,
    )
    current_spec: dict[str, Any] | None = None
    changes_requested: str = Field(
        default="",
        max_length=1000,
        description="Specific changes to make",
    )


class BotSpecDiff(BaseModel):
    """Schema for showing spec differences."""

    field: str
    old_value: Any
    new_value: Any
