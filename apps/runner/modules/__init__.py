"""Bot modules."""
from modules.basic_commands import BasicCommandsModule
from modules.static_replies import StaticRepliesModule
from modules.ai_chat import AIChatModule
from modules.moderation import ModerationModule
from modules.webhook_forward import WebhookForwardModule

__all__ = [
    "BasicCommandsModule",
    "StaticRepliesModule",
    "AIChatModule",
    "ModerationModule",
    "WebhookForwardModule",
]
