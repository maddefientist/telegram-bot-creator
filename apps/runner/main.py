"""Telegram Bot Runner - Executes bots based on BotSpec."""
import asyncio
import os
import signal
import sys
from datetime import datetime, timezone

import httpx
import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import Settings
from modules import (
    BasicCommandsModule,
    StaticRepliesModule,
    AIChatModule,
    ModerationModule,
    WebhookForwardModule,
)
from spec import BotSpec, load_spec_from_api

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


class BotRunner:
    """Main bot runner that orchestrates modules based on BotSpec."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.spec: BotSpec | None = None
        self.application: Application | None = None
        self.running = False

        # Modules
        self.basic_commands: BasicCommandsModule | None = None
        self.static_replies: StaticRepliesModule | None = None
        self.ai_chat: AIChatModule | None = None
        self.moderation: ModerationModule | None = None
        self.webhook_forward: WebhookForwardModule | None = None

    async def load_spec(self) -> bool:
        """Load BotSpec from API."""
        try:
            self.spec = await load_spec_from_api(
                self.settings.api_url,
                self.settings.bot_id,
                self.settings.runner_secret,
            )
            logger.info("BotSpec loaded", name=self.spec.name)
            return True
        except Exception as e:
            logger.error("Failed to load BotSpec", error=str(e))
            return False

    def setup_modules(self) -> None:
        """Initialize modules based on BotSpec."""
        if not self.spec:
            return

        # Always set up basic commands
        self.basic_commands = BasicCommandsModule(self.spec)

        # Static replies
        if "static_replies" in self.spec.enabled_modules:
            self.static_replies = StaticRepliesModule(self.spec)

        # AI Chat
        if "ai_chat" in self.spec.enabled_modules and self.spec.ai_chat.enabled:
            self.ai_chat = AIChatModule(
                self.spec,
                self.settings.openrouter_api_key,
                self.settings.openrouter_model,
            )

        # Moderation
        if "moderation" in self.spec.enabled_modules and self.spec.moderation.enabled:
            self.moderation = ModerationModule(self.spec)

        # Webhook forward
        if "webhook_forward" in self.spec.enabled_modules and self.spec.webhook.enabled:
            self.webhook_forward = WebhookForwardModule(self.spec)

    def setup_handlers(self, app: Application) -> None:
        """Set up Telegram handlers."""
        if not self.spec:
            return

        # Basic commands (always)
        app.add_handler(CommandHandler("start", self.basic_commands.start_command))
        app.add_handler(CommandHandler("help", self.basic_commands.help_command))

        # Static reply commands
        if self.static_replies:
            for cmd in self.spec.commands:
                app.add_handler(
                    CommandHandler(
                        cmd.command,
                        self.static_replies.create_handler(cmd),
                    )
                )

        # Message handler for AI chat and moderation
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message,
            )
        )

        # Error handler
        app.add_error_handler(self.error_handler)

    async def handle_message(self, update: Update, context) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id if update.effective_user else 0
        chat_id = update.effective_chat.id if update.effective_chat else 0

        # Apply moderation first
        if self.moderation:
            should_block, reason = await self.moderation.check_message(
                update.message.text,
                user_id,
                chat_id,
            )
            if should_block:
                if self.spec.moderation.auto_delete_violations:
                    try:
                        await update.message.delete()
                    except Exception:
                        pass
                logger.info(
                    "Message blocked by moderation",
                    user_id=user_id,
                    reason=reason,
                )
                return

        # Forward to webhook if enabled
        if self.webhook_forward:
            await self.webhook_forward.forward_event(
                "message",
                {
                    "message_id": update.message.message_id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "text": update.message.text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # AI Chat response
        if self.ai_chat:
            response = await self.ai_chat.generate_response(
                update.message.text,
                user_id,
                chat_id,
                context,
            )
            if response:
                await update.message.reply_text(response)

    async def error_handler(self, update: Update, context) -> None:
        """Handle errors."""
        logger.error(
            "Telegram error",
            error=str(context.error),
            update=str(update) if update else None,
        )

        # Report error to API
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.settings.api_url}/runner/bot/{self.settings.bot_id}/error",
                    headers={"X-Runner-Secret": self.settings.runner_secret},
                    json={"message": str(context.error)},
                    timeout=10.0,
                )
        except Exception:
            pass

    async def send_heartbeat(self) -> None:
        """Send heartbeat to API."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.settings.api_url}/runner/bot/{self.settings.bot_id}/heartbeat",
                    headers={"X-Runner-Secret": self.settings.runner_secret},
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning("Heartbeat failed", error=str(e))

    async def check_subscription(self) -> bool:
        """Check if subscription is still active."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.settings.api_url}/runner/bot/{self.settings.bot_id}/check-active",
                    headers={"X-Runner-Secret": self.settings.runner_secret},
                    timeout=10.0,
                )
                data = response.json()
                return data.get("active", False)
        except Exception as e:
            logger.warning("Subscription check failed", error=str(e))
            return True  # Assume active on error to avoid false stops

    async def background_tasks(self) -> None:
        """Run background tasks (heartbeat, subscription check)."""
        while self.running:
            await self.send_heartbeat()

            # Check subscription every 5 minutes
            if not await self.check_subscription():
                logger.warning("Subscription expired, stopping bot")
                self.running = False
                if self.application:
                    await self.application.stop()
                break

            await asyncio.sleep(60)  # Heartbeat every minute

    async def run(self) -> None:
        """Run the bot."""
        # Load spec
        if not await self.load_spec():
            logger.error("Cannot start without BotSpec")
            sys.exit(1)

        # Setup modules
        self.setup_modules()

        # Create application
        self.application = (
            Application.builder()
            .token(self.settings.telegram_token)
            .build()
        )

        # Setup handlers
        self.setup_handlers(self.application)

        # Start
        self.running = True
        logger.info("Starting bot", name=self.spec.name)

        # Start background tasks
        background_task = asyncio.create_task(self.background_tasks())

        try:
            # Run polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)

            # Wait for stop signal
            stop_event = asyncio.Event()

            def signal_handler():
                stop_event.set()

            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)

            await stop_event.wait()

        except Exception as e:
            logger.error("Bot error", error=str(e))
        finally:
            self.running = False
            background_task.cancel()

            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

            logger.info("Bot stopped")


def main():
    """Entry point."""
    settings = Settings()

    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN not set")
        sys.exit(1)

    if not settings.bot_id:
        logger.error("BOT_ID not set")
        sys.exit(1)

    runner = BotRunner(settings)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
