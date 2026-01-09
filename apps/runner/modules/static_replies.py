"""Static replies module - predefined command responses."""
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from spec import BotSpec, CommandConfig


class StaticRepliesModule:
    """Handles predefined command responses."""

    def __init__(self, spec: BotSpec):
        self.spec = spec

    def create_handler(
        self,
        cmd: CommandConfig,
    ) -> Callable:
        """Create a handler function for a command."""

        async def handler(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
        ) -> None:
            if not update.message:
                return

            # Send response based on type
            if cmd.response_type == "markdown":
                await update.message.reply_text(
                    cmd.response_payload,
                    parse_mode="Markdown",
                )
            elif cmd.response_type == "html":
                await update.message.reply_text(
                    cmd.response_payload,
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_text(cmd.response_payload)

        return handler
