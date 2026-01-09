"""Basic commands module - /start and /help."""
from telegram import Update
from telegram.ext import ContextTypes

from spec import BotSpec


class BasicCommandsModule:
    """Handles /start and /help commands."""

    def __init__(self, spec: BotSpec):
        self.spec = spec

    async def start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start command."""
        if not update.message:
            return

        await update.message.reply_text(self.spec.welcome_message)

    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /help command."""
        if not update.message:
            return

        # Build help text
        lines = [f"*{self.spec.name}*"]

        if self.spec.description:
            lines.append(f"_{self.spec.description}_")

        lines.append("")
        lines.append("*Available Commands:*")
        lines.append("/start - Start the bot")
        lines.append("/help - Show this help message")

        # Add custom commands
        for cmd in self.spec.commands:
            lines.append(f"/{cmd.command} - {cmd.description}")

        # Add AI chat info if enabled
        if self.spec.ai_chat.enabled:
            lines.append("")
            lines.append("_Send any message to chat with AI_")

        # Add footer
        if self.spec.help_footer:
            lines.append("")
            lines.append(self.spec.help_footer)

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
        )
