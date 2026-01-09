"""Background worker for payment verification."""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db_context
from models.invoice import Invoice, InvoiceStatus
from models.subscription import Subscription, SubscriptionState
from services.payment_service import PaymentService
from services.bot_service import BotService
from core.logging import get_logger

logger = get_logger(__name__)

POLL_INTERVAL = 30  # seconds


async def verify_pending_invoices():
    """Check all pending invoices for payments."""
    payment_service = PaymentService()

    async with get_db_context() as db:
        # Get pending invoices that haven't expired
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Invoice)
            .options(selectinload(Invoice.bot).selectinload(Subscription))
            .where(Invoice.status == InvoiceStatus.PENDING)
            .where(Invoice.expires_at > now)
        )
        invoices = result.scalars().all()

        logger.info(f"Checking {len(invoices)} pending invoices")

        for invoice in invoices:
            try:
                is_paid, tx_signature, message = await payment_service.verify_payment(
                    invoice.reference,
                    float(invoice.amount_sol),
                )

                if is_paid:
                    invoice.status = InvoiceStatus.PAID
                    invoice.tx_signature = tx_signature
                    invoice.paid_at = datetime.now(timezone.utc)

                    # Activate subscription using BotService
                    bot_service = BotService(db)
                    await bot_service._activate_subscription(invoice)

                    logger.info(
                        "Payment confirmed",
                        invoice_id=str(invoice.id),
                        tx_signature=tx_signature,
                    )

            except Exception as e:
                logger.error(
                    "Payment verification error",
                    invoice_id=str(invoice.id),
                    error=str(e),
                )

        await db.commit()


async def expire_old_invoices():
    """Mark expired invoices."""
    async with get_db_context() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Invoice)
            .where(Invoice.status == InvoiceStatus.PENDING)
            .where(Invoice.expires_at <= now)
        )
        invoices = result.scalars().all()

        for invoice in invoices:
            invoice.status = InvoiceStatus.EXPIRED
            logger.info("Invoice expired", invoice_id=str(invoice.id))

        if invoices:
            await db.commit()
            logger.info(f"Expired {len(invoices)} invoices")


async def check_subscriptions():
    """Update expired subscriptions."""
    async with get_db_context() as db:
        bot_service = BotService(db)
        updated = await bot_service.check_expired_subscriptions()
        if updated:
            logger.info(f"Updated {updated} subscriptions")


async def run_worker():
    """Main worker loop."""
    logger.info("Starting payment worker")

    while True:
        try:
            await verify_pending_invoices()
            await expire_old_invoices()
            await check_subscriptions()
        except Exception as e:
            logger.error("Worker error", error=str(e))

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())
