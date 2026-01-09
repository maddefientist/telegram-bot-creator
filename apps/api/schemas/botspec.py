"""BotSpec schema - the core safe specification for bot behavior.

This schema defines the ONLY way bots can be configured. The AI generates
a BotSpec JSON, which is validated against this schema. The bot runner
then maps the spec to prebuilt modules - no arbitrary code execution.
"""
import re
from enum import Enum
from ipaddress import ip_address
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class ModuleType(str, Enum):
    """Available bot modules."""
    BASIC_COMMANDS = "basic_commands"  # /start, /help
    STATIC_REPLIES = "static_replies"  # Predefined command responses
    AI_CHAT = "ai_chat"  # OpenRouter-powered chat
    MODERATION = "moderation"  # Message filtering
    WEBHOOK_FORWARD = "webhook_forward"  # Forward events to webhook


class ResponseType(str, Enum):
    """Types of command responses."""
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"


class CommandConfig(BaseModel):
    """Configuration for a custom command."""

    command: Annotated[str, Field(
        min_length=1,
        max_length=32,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Command name without slash (e.g., 'help')",
    )]
    description: Annotated[str, Field(
        min_length=1,
        max_length=256,
        description="Command description for /help",
    )]
    response_type: ResponseType = ResponseType.TEXT
    response_payload: Annotated[str, Field(
        min_length=1,
        max_length=4096,
        description="Response text to send",
    )]

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        # Reserved commands
        reserved = {"start", "help", "settings", "stop", "admin"}
        if v.lower() in reserved:
            raise ValueError(f"Command '{v}' is reserved")
        return v.lower()


class AIChatConfig(BaseModel):
    """Configuration for AI-powered chat module."""

    enabled: bool = False
    system_prompt: Annotated[str, Field(
        max_length=2000,
        default="You are a helpful assistant.",
        description="System prompt for the AI",
    )]
    allowed_topics: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        max_length=20,
        description="Topics the bot can discuss (empty = all allowed)",
    )
    disallowed_topics: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        max_length=50,
        description="Topics the bot should refuse",
    )
    max_tokens: Annotated[int, Field(ge=50, le=2000)] = 500
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.7
    max_context_messages: Annotated[int, Field(ge=1, le=20)] = 10

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        # Block dangerous instructions in system prompt
        dangerous_patterns = [
            r"ignore.*previous.*instructions",
            r"disregard.*rules",
            r"act.*as.*if.*no.*restrictions",
            r"pretend.*you.*can",
            r"execute.*code",
            r"run.*command",
            r"access.*file",
            r"system.*shell",
        ]
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, v_lower):
                raise ValueError("System prompt contains disallowed content")
        return v


class ModerationConfig(BaseModel):
    """Configuration for message moderation module."""

    enabled: bool = False
    blocked_words: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list,
        max_length=500,
        description="Words to filter from messages",
    )
    block_links: bool = False
    block_forwards: bool = False
    warn_before_ban: Annotated[int, Field(ge=0, le=10)] = 3
    auto_delete_violations: bool = True


# Private/reserved IP ranges to block for webhooks
BLOCKED_IP_RANGES = [
    "127.0.0.0/8",      # Loopback
    "10.0.0.0/8",       # Private
    "172.16.0.0/12",    # Private
    "192.168.0.0/16",   # Private
    "169.254.0.0/16",   # Link-local
    "0.0.0.0/8",        # Current network
    "100.64.0.0/10",    # Shared address space
    "192.0.0.0/24",     # IETF Protocol
    "192.0.2.0/24",     # Documentation
    "198.51.100.0/24",  # Documentation
    "203.0.113.0/24",   # Documentation
    "224.0.0.0/4",      # Multicast
    "240.0.0.0/4",      # Reserved
]


def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private/blocked IP."""
    try:
        ip = ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast
    except ValueError:
        # Not an IP address, assume it's a hostname
        # Block common internal hostnames
        blocked_hostnames = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "host.docker.internal",
            "metadata.google.internal",
            "169.254.169.254",  # Cloud metadata
        ]
        return hostname.lower() in blocked_hostnames


class WebhookConfig(BaseModel):
    """Configuration for webhook forwarding module."""

    enabled: bool = False
    url: Annotated[str, Field(
        max_length=500,
        default="",
        description="HTTPS URL to forward events to",
    )]
    secret: Annotated[str, Field(
        max_length=100,
        default="",
        description="HMAC secret for signing payloads",
    )]
    events: list[str] = Field(
        default_factory=lambda: ["message"],
        description="Events to forward",
    )

    @field_validator("url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        if not v:
            return v

        try:
            parsed = urlparse(v)
        except Exception:
            raise ValueError("Invalid URL format")

        # Must be HTTPS
        if parsed.scheme != "https":
            raise ValueError("Webhook URL must use HTTPS")

        # Check for private IPs
        hostname = parsed.hostname or ""
        if is_private_ip(hostname):
            raise ValueError("Webhook URL cannot point to private/internal addresses")

        # Block common cloud metadata endpoints
        if "metadata" in hostname.lower() or "169.254" in hostname:
            raise ValueError("Webhook URL cannot point to metadata endpoints")

        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        allowed_events = {
            "message", "edited_message", "command", "callback_query",
            "inline_query", "member_joined", "member_left",
        }
        for event in v:
            if event not in allowed_events:
                raise ValueError(f"Unknown event type: {event}")
        return v


class LimitsConfig(BaseModel):
    """Rate limiting configuration."""

    max_messages_per_user_per_minute: Annotated[int, Field(ge=1, le=60)] = 10
    max_messages_per_chat_per_minute: Annotated[int, Field(ge=1, le=120)] = 30
    max_ai_requests_per_user_per_day: Annotated[int, Field(ge=1, le=100)] = 20
    cooldown_seconds: Annotated[int, Field(ge=0, le=60)] = 1


class BotSpec(BaseModel):
    """
    Complete bot specification schema.

    This is the ONLY interface for defining bot behavior. The AI generates
    this JSON, it's validated here, and the runner maps it to prebuilt modules.

    Security: This schema enforces strict validation and rejects unknown fields.
    """

    name: Annotated[str, Field(
        min_length=1,
        max_length=64,
        description="Bot display name",
    )]
    description: Annotated[str, Field(
        max_length=500,
        default="",
        description="Bot description",
    )]
    enabled_modules: list[ModuleType] = Field(
        default_factory=lambda: [ModuleType.BASIC_COMMANDS],
        description="Active modules",
    )
    commands: list[CommandConfig] = Field(
        default_factory=list,
        max_length=50,
        description="Custom command configurations",
    )
    ai_chat: AIChatConfig = Field(
        default_factory=AIChatConfig,
        description="AI chat module configuration",
    )
    moderation: ModerationConfig = Field(
        default_factory=ModerationConfig,
        description="Moderation module configuration",
    )
    webhook: WebhookConfig = Field(
        default_factory=WebhookConfig,
        description="Webhook module configuration",
    )
    limits: LimitsConfig = Field(
        default_factory=LimitsConfig,
        description="Rate limiting configuration",
    )
    welcome_message: Annotated[str, Field(
        max_length=1000,
        default="Welcome! Type /help to see available commands.",
    )]
    help_footer: Annotated[str, Field(
        max_length=500,
        default="",
        description="Additional text for /help command",
    )]

    model_config = {
        "extra": "forbid",  # Reject unknown fields
        "json_schema_extra": {
            "examples": [
                {
                    "name": "My Support Bot",
                    "description": "A helpful customer support bot",
                    "enabled_modules": ["basic_commands", "ai_chat", "moderation"],
                    "commands": [
                        {
                            "command": "faq",
                            "description": "Show frequently asked questions",
                            "response_type": "markdown",
                            "response_payload": "## FAQ\n\n1. **Q:** How do I...?\n   **A:** You can..."
                        }
                    ],
                    "ai_chat": {
                        "enabled": True,
                        "system_prompt": "You are a helpful support assistant for our product.",
                        "max_tokens": 500,
                        "temperature": 0.7
                    },
                    "moderation": {
                        "enabled": True,
                        "blocked_words": ["spam"],
                        "block_links": True
                    },
                    "limits": {
                        "max_messages_per_user_per_minute": 10,
                        "max_ai_requests_per_user_per_day": 20
                    }
                }
            ]
        }
    }

    @model_validator(mode="after")
    def validate_modules_config(self) -> "BotSpec":
        """Ensure enabled modules have proper configuration."""
        if ModuleType.AI_CHAT in self.enabled_modules:
            if not self.ai_chat.enabled:
                # Auto-enable if module is listed
                object.__setattr__(self.ai_chat, "enabled", True)

        if ModuleType.MODERATION in self.enabled_modules:
            if not self.moderation.enabled:
                object.__setattr__(self.moderation, "enabled", True)

        if ModuleType.WEBHOOK_FORWARD in self.enabled_modules:
            if not self.webhook.enabled:
                object.__setattr__(self.webhook, "enabled", True)
            if not self.webhook.url:
                raise ValueError("Webhook URL required when webhook module is enabled")

        if ModuleType.STATIC_REPLIES in self.enabled_modules:
            if not self.commands:
                raise ValueError("At least one command required for static_replies module")

        return self

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Block potentially malicious names
        if any(c in v for c in ["<", ">", "&", '"', "'"]):
            raise ValueError("Name contains invalid characters")
        return v.strip()


# Export JSON schema for documentation and AI prompts
BOTSPEC_JSON_SCHEMA = BotSpec.model_json_schema()
