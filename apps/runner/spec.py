"""BotSpec model and loader."""
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class CommandConfig:
    """Command configuration."""
    command: str
    description: str
    response_type: str = "text"
    response_payload: str = ""


@dataclass
class AIChatConfig:
    """AI chat configuration."""
    enabled: bool = False
    system_prompt: str = "You are a helpful assistant."
    allowed_topics: list[str] = field(default_factory=list)
    disallowed_topics: list[str] = field(default_factory=list)
    max_tokens: int = 500
    temperature: float = 0.7
    max_context_messages: int = 10


@dataclass
class ModerationConfig:
    """Moderation configuration."""
    enabled: bool = False
    blocked_words: list[str] = field(default_factory=list)
    block_links: bool = False
    block_forwards: bool = False
    warn_before_ban: int = 3
    auto_delete_violations: bool = True


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    enabled: bool = False
    url: str = ""
    secret: str = ""
    events: list[str] = field(default_factory=lambda: ["message"])


@dataclass
class LimitsConfig:
    """Rate limits configuration."""
    max_messages_per_user_per_minute: int = 10
    max_messages_per_chat_per_minute: int = 30
    max_ai_requests_per_user_per_day: int = 20
    cooldown_seconds: int = 1


@dataclass
class BotSpec:
    """Bot specification model."""
    name: str
    description: str = ""
    enabled_modules: list[str] = field(default_factory=lambda: ["basic_commands"])
    commands: list[CommandConfig] = field(default_factory=list)
    ai_chat: AIChatConfig = field(default_factory=AIChatConfig)
    moderation: ModerationConfig = field(default_factory=ModerationConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    welcome_message: str = "Welcome! Type /help to see available commands."
    help_footer: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BotSpec":
        """Create BotSpec from dictionary."""
        commands = [
            CommandConfig(**cmd) for cmd in data.get("commands", [])
        ]

        ai_chat_data = data.get("ai_chat", {})
        ai_chat = AIChatConfig(
            enabled=ai_chat_data.get("enabled", False),
            system_prompt=ai_chat_data.get("system_prompt", "You are a helpful assistant."),
            allowed_topics=ai_chat_data.get("allowed_topics", []),
            disallowed_topics=ai_chat_data.get("disallowed_topics", []),
            max_tokens=ai_chat_data.get("max_tokens", 500),
            temperature=ai_chat_data.get("temperature", 0.7),
            max_context_messages=ai_chat_data.get("max_context_messages", 10),
        )

        moderation_data = data.get("moderation", {})
        moderation = ModerationConfig(
            enabled=moderation_data.get("enabled", False),
            blocked_words=moderation_data.get("blocked_words", []),
            block_links=moderation_data.get("block_links", False),
            block_forwards=moderation_data.get("block_forwards", False),
            warn_before_ban=moderation_data.get("warn_before_ban", 3),
            auto_delete_violations=moderation_data.get("auto_delete_violations", True),
        )

        webhook_data = data.get("webhook", {})
        webhook = WebhookConfig(
            enabled=webhook_data.get("enabled", False),
            url=webhook_data.get("url", ""),
            secret=webhook_data.get("secret", ""),
            events=webhook_data.get("events", ["message"]),
        )

        limits_data = data.get("limits", {})
        limits = LimitsConfig(
            max_messages_per_user_per_minute=limits_data.get("max_messages_per_user_per_minute", 10),
            max_messages_per_chat_per_minute=limits_data.get("max_messages_per_chat_per_minute", 30),
            max_ai_requests_per_user_per_day=limits_data.get("max_ai_requests_per_user_per_day", 20),
            cooldown_seconds=limits_data.get("cooldown_seconds", 1),
        )

        return cls(
            name=data.get("name", "Bot"),
            description=data.get("description", ""),
            enabled_modules=data.get("enabled_modules", ["basic_commands"]),
            commands=commands,
            ai_chat=ai_chat,
            moderation=moderation,
            webhook=webhook,
            limits=limits,
            welcome_message=data.get("welcome_message", "Welcome! Type /help to see available commands."),
            help_footer=data.get("help_footer", ""),
        )


async def load_spec_from_api(
    api_url: str,
    bot_id: str,
    runner_secret: str,
) -> BotSpec:
    """Load BotSpec from API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_url}/runner/bot/{bot_id}/spec",
            headers={"X-Runner-Secret": runner_secret},
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        return BotSpec.from_dict(data.get("spec", {}))
