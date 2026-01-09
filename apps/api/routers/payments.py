"""Payment routes."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from core.auth import get_current_active_user
from database import get_db
from models.user import User
from models.bot import Bot
from models.invoice import Invoice, InvoiceStatus
from schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    PaymentInfo,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from schemas.subscription import PricingConfig, DEFAULT_PRICING_TIERS
from services.bot_service import BotService

settings = get_settings()
router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/pricing", response_model=PricingConfig)
async def get_pricing() -> PricingConfig:
    """Get pricing configuration and tiers."""
    return PricingConfig(
        min_sol=settings.pricing_min_sol,
        max_sol=settings.pricing_max_sol,
        default_sol=settings.default_price_sol,
        tiers=DEFAULT_PRICING_TIERS,
    )


@router.post("/invoices", response_model=PaymentInfo, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: InvoiceCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentInfo:
    """Create a payment invoice for a bot subscription."""
    service = BotService(db)
    bot = await service.get_bot(request.bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    if not bot.subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot has no subscription",
        )

    try:
        invoice = await service.create_invoice(bot, request.months)

        # Build Solana Pay URL
        from urllib.parse import urlencode
        params = {
            "amount": str(invoice.amount_sol),
            "reference": invoice.reference,
            "label": "Bot Subscription",
            "message": f"Payment for {bot.name}",
        }
        solana_pay_url = f"solana:{invoice.treasury_address}?{urlencode(params)}"

        return PaymentInfo(
            invoice_id=invoice.id,
            amount_sol=float(invoice.amount_sol),
            recipient=invoice.treasury_address,
            reference=invoice.reference,
            expires_at=invoice.expires_at,
            solana_pay_url=solana_pay_url,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Invoice:
    """Get an invoice by ID."""
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.bot))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    # Check ownership
    if invoice.bot.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your invoice",
        )

    return invoice


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bot_id: uuid.UUID | None = None,
) -> list[Invoice]:
    """List invoices for the current user."""
    query = (
        select(Invoice)
        .join(Bot)
        .where(Bot.owner_id == current_user.id)
        .order_by(Invoice.created_at.desc())
    )

    if bot_id:
        query = query.where(Invoice.bot_id == bot_id)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VerifyPaymentResponse:
    """Manually trigger payment verification."""
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.bot))
        .where(Invoice.id == request.invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    # Check ownership
    if invoice.bot.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your invoice",
        )

    if invoice.status == InvoiceStatus.PAID:
        # Already paid - get subscription info
        sub = invoice.bot.subscription
        return VerifyPaymentResponse(
            invoice_id=invoice.id,
            status=invoice.status,
            message="Already paid",
            subscription_active_until=sub.active_until if sub else None,
        )

    service = BotService(db)
    is_paid, message = await service.verify_invoice_payment(invoice)

    await db.refresh(invoice)

    sub = invoice.bot.subscription
    return VerifyPaymentResponse(
        invoice_id=invoice.id,
        status=invoice.status,
        message=message,
        subscription_active_until=sub.active_until if sub and is_paid else None,
    )
