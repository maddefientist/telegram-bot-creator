"""Bot management service."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from core.logging import get_logger
from core.security import encrypt_token, decrypt_token
from models.bot import Bot, BotStatus
from models.subscription import Subscription, SubscriptionState
from models.invoice import Invoice, InvoiceStatus
from schemas.botspec import BotSpec
from services.docker_service import DockerService
from services.payment_service import PaymentService

settings = get_settings()
logger = get_logger(__name__)


class BotService:
    """Service for managing bots."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.docker = DockerService()
        self.payment = PaymentService()

    async def create_bot(
        self,
        owner_id: uuid.UUID,
        name: str,
        telegram_token: str,
        description: str,
        price_per_month_sol: float,
    ) -> Bot:
        """Create a new bot."""
        # Validate pricing
        if price_per_month_sol < settings.pricing_min_sol:
            raise ValueError(f"Price must be at least {settings.pricing_min_sol} SOL")
        if price_per_month_sol > settings.pricing_max_sol:
            raise ValueError(f"Price cannot exceed {settings.pricing_max_sol} SOL")

        # Validate Telegram token
        telegram_username = await self._validate_telegram_token(telegram_token)

        # Encrypt token for storage
        encrypted_token = encrypt_token(telegram_token)

        # Create default BotSpec
        default_spec = BotSpec(
            name=name,
            description=description,
        )

        # Create bot
        bot = Bot(
            owner_id=owner_id,
            name=name,
            telegram_token_encrypted=encrypted_token,
            telegram_username=telegram_username,
            spec_json=default_spec.model_dump(),
            status=BotStatus.STOPPED,
        )

        self.db.add(bot)
        await self.db.flush()

        # Create subscription in pending state
        subscription = Subscription(
            bot_id=bot.id,
            price_per_month_sol=price_per_month_sol,
            state=SubscriptionState.PENDING,
        )

        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(bot)

        logger.info(
            "Bot created",
            bot_id=str(bot.id),
            owner_id=str(owner_id),
            name=name,
        )

        return bot

    async def get_bot(
        self,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID | None = None,
    ) -> Bot | None:
        """Get a bot by ID, optionally filtering by owner."""
        query = (
            select(Bot)
            .options(selectinload(Bot.subscription))
            .where(Bot.id == bot_id)
            .where(Bot.status != BotStatus.DELETED)
        )

        if owner_id:
            query = query.where(Bot.owner_id == owner_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_bots(self, owner_id: uuid.UUID) -> list[Bot]:
        """Get all bots for a user."""
        query = (
            select(Bot)
            .options(selectinload(Bot.subscription))
            .where(Bot.owner_id == owner_id)
            .where(Bot.status != BotStatus.DELETED)
            .order_by(Bot.created_at.desc())
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_bot_spec(
        self,
        bot: Bot,
        spec_dict: dict[str, Any],
    ) -> Bot:
        """Update a bot's spec."""
        # Validate spec
        try:
            validated = BotSpec.model_validate(spec_dict)
        except Exception as e:
            raise ValueError(f"Invalid BotSpec: {str(e)}")

        bot.spec_json = validated.model_dump()
        bot.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(bot)

        logger.info("Bot spec updated", bot_id=str(bot.id))

        # If bot is running, restart to apply changes
        if bot.status == BotStatus.RUNNING:
            await self.restart_bot(bot)

        return bot

    async def start_bot(self, bot: Bot) -> tuple[bool, str]:
        """Start a bot."""
        # Check subscription
        if not await self._can_start_bot(bot):
            return False, "Subscription not active or in grace period"

        if bot.status == BotStatus.RUNNING:
            return True, "Bot already running"

        # Update status
        bot.status = BotStatus.STARTING
        await self.db.commit()

        # Decrypt token
        telegram_token = decrypt_token(bot.telegram_token_encrypted)

        # Start container
        api_url = settings.api_base_url
        success, container_id, message = await self.docker.start_bot(
            bot.id,
            telegram_token,
            api_url,
        )

        if success:
            bot.status = BotStatus.RUNNING
            bot.container_id = container_id
            bot.last_error = None
        else:
            bot.status = BotStatus.ERROR
            bot.last_error = message

        await self.db.commit()
        await self.db.refresh(bot)

        logger.info(
            "Bot start attempt",
            bot_id=str(bot.id),
            success=success,
            message=message,
        )

        return success, message

    async def stop_bot(self, bot: Bot) -> tuple[bool, str]:
        """Stop a bot."""
        if bot.status == BotStatus.STOPPED:
            return True, "Bot already stopped"

        bot.status = BotStatus.STOPPING
        await self.db.commit()

        success, message = await self.docker.stop_bot(bot.id)

        bot.status = BotStatus.STOPPED if success else BotStatus.ERROR
        if not success:
            bot.last_error = message

        await self.db.commit()
        await self.db.refresh(bot)

        logger.info(
            "Bot stop attempt",
            bot_id=str(bot.id),
            success=success,
        )

        return success, message

    async def restart_bot(self, bot: Bot) -> tuple[bool, str]:
        """Restart a bot."""
        # Check subscription
        if not await self._can_start_bot(bot):
            return False, "Subscription not active or in grace period"

        telegram_token = decrypt_token(bot.telegram_token_encrypted)
        api_url = settings.api_base_url

        success, container_id, message = await self.docker.restart_bot(
            bot.id,
            telegram_token,
            api_url,
        )

        if success:
            bot.status = BotStatus.RUNNING
            bot.container_id = container_id
            bot.last_error = None
        else:
            bot.status = BotStatus.ERROR
            bot.last_error = message

        await self.db.commit()
        await self.db.refresh(bot)

        return success, message

    async def delete_bot(self, bot: Bot) -> bool:
        """Soft delete a bot."""
        # Stop if running
        if bot.status in (BotStatus.RUNNING, BotStatus.STARTING):
            await self.stop_bot(bot)

        bot.status = BotStatus.DELETED
        await self.db.commit()

        logger.info("Bot deleted", bot_id=str(bot.id))
        return True

    async def get_bot_logs(
        self,
        bot: Bot,
        tail: int = 100,
    ) -> list[str]:
        """Get logs for a bot."""
        return await self.docker.get_bot_logs(bot.id, tail)

    async def update_heartbeat(self, bot_id: uuid.UUID) -> bool:
        """Update bot heartbeat (called by runner)."""
        result = await self.db.execute(
            select(Bot).where(Bot.id == bot_id)
        )
        bot = result.scalar_one_or_none()

        if bot:
            bot.last_heartbeat = datetime.now(timezone.utc)
            await self.db.commit()
            return True

        return False

    async def create_invoice(
        self,
        bot: Bot,
        months: int = 1,
    ) -> Invoice:
        """Create a payment invoice for a bot."""
        if not bot.subscription:
            raise ValueError("Bot has no subscription")

        amount = float(bot.subscription.price_per_month_sol) * months

        # Create invoice data with reference
        invoice_data = self.payment.create_invoice_data(amount, bot.name)

        invoice = Invoice(
            bot_id=bot.id,
            amount_sol=amount,
            treasury_address=invoice_data["treasury_address"],
            reference=invoice_data["reference"],
            status=InvoiceStatus.PENDING,
            expires_at=invoice_data["expires_at"],
        )

        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)

        logger.info(
            "Invoice created",
            invoice_id=str(invoice.id),
            bot_id=str(bot.id),
            amount=amount,
        )

        return invoice

    async def verify_invoice_payment(
        self,
        invoice: Invoice,
    ) -> tuple[bool, str]:
        """Verify payment for an invoice."""
        if invoice.status == InvoiceStatus.PAID:
            return True, "Already paid"

        if invoice.status == InvoiceStatus.EXPIRED:
            return False, "Invoice expired"

        # Check if expired
        if datetime.now(timezone.utc) > invoice.expires_at:
            invoice.status = InvoiceStatus.EXPIRED
            await self.db.commit()
            return False, "Invoice expired"

        # Verify on-chain
        is_paid, tx_signature, message = await self.payment.verify_payment(
            invoice.reference,
            float(invoice.amount_sol),
        )

        if is_paid:
            invoice.status = InvoiceStatus.PAID
            invoice.tx_signature = tx_signature
            invoice.paid_at = datetime.now(timezone.utc)

            # Activate subscription
            await self._activate_subscription(invoice)

            await self.db.commit()
            return True, message

        return False, message

    async def _can_start_bot(self, bot: Bot) -> bool:
        """Check if bot can be started based on subscription."""
        if not bot.subscription:
            return False

        sub = bot.subscription
        now = datetime.now(timezone.utc)

        if sub.state == SubscriptionState.ACTIVE:
            if sub.active_until and sub.active_until > now:
                return True

        if sub.state == SubscriptionState.GRACE:
            if sub.grace_until and sub.grace_until > now:
                return True

        return False

    async def _activate_subscription(self, invoice: Invoice) -> None:
        """Activate subscription after successful payment."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.bot_id == invoice.bot_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        now = datetime.now(timezone.utc)

        # Calculate subscription period (amount / price_per_month = months)
        months = float(invoice.amount_sol) / float(subscription.price_per_month_sol)

        # If already active, extend from current end date
        if subscription.active_until and subscription.active_until > now:
            subscription.active_until = subscription.active_until + timedelta(days=30 * months)
        else:
            subscription.active_until = now + timedelta(days=30 * months)

        subscription.grace_until = subscription.active_until + timedelta(days=settings.grace_days)
        subscription.state = SubscriptionState.ACTIVE

        logger.info(
            "Subscription activated",
            bot_id=str(invoice.bot_id),
            active_until=subscription.active_until.isoformat(),
        )

    async def _validate_telegram_token(self, token: str) -> str | None:
        """Validate a Telegram bot token and get username."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        return data["result"].get("username")

                raise ValueError("Invalid Telegram token")

        except httpx.TimeoutException:
            raise ValueError("Telegram API timeout")
        except Exception as e:
            raise ValueError(f"Failed to validate token: {str(e)}")

    async def check_expired_subscriptions(self) -> int:
        """Check and update expired subscriptions. Called by background worker."""
        now = datetime.now(timezone.utc)

        # Find subscriptions that need state update
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.state == SubscriptionState.ACTIVE)
            .where(Subscription.active_until < now)
        )
        subscriptions = result.scalars().all()

        updated = 0
        for sub in subscriptions:
            if sub.grace_until and sub.grace_until > now:
                sub.state = SubscriptionState.GRACE
            else:
                sub.state = SubscriptionState.EXPIRED
                # Stop the bot
                bot_result = await self.db.execute(
                    select(Bot).where(Bot.id == sub.bot_id)
                )
                bot = bot_result.scalar_one_or_none()
                if bot and bot.status == BotStatus.RUNNING:
                    await self.stop_bot(bot)

            updated += 1

        # Also check grace period expiry
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.state == SubscriptionState.GRACE)
            .where(Subscription.grace_until < now)
        )
        grace_expired = result.scalars().all()

        for sub in grace_expired:
            sub.state = SubscriptionState.EXPIRED
            bot_result = await self.db.execute(
                select(Bot).where(Bot.id == sub.bot_id)
            )
            bot = bot_result.scalar_one_or_none()
            if bot and bot.status == BotStatus.RUNNING:
                await self.stop_bot(bot)
            updated += 1

        if updated:
            await self.db.commit()
            logger.info(f"Updated {updated} subscription states")

        return updated
