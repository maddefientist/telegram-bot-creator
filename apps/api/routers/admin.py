"""Admin routes."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import get_admin_user
from database import get_db
from models.user import User
from models.bot import Bot, BotStatus
from models.subscription import Subscription, SubscriptionState
from models.invoice import Invoice, InvoiceStatus
from models.audit_log import AuditLog
from schemas.admin import (
    AdminSettings,
    AdminUserResponse,
    AdminBotResponse,
    AdminInvoiceResponse,
    AdminOverrideRequest,
    AdminStatsResponse,
)
from services.bot_service import BotService
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminStatsResponse:
    """Get admin dashboard statistics."""
    # Total users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0

    # Total bots
    bots_result = await db.execute(
        select(func.count(Bot.id)).where(Bot.status != BotStatus.DELETED)
    )
    total_bots = bots_result.scalar() or 0

    # Active bots
    active_result = await db.execute(
        select(func.count(Bot.id)).where(Bot.status == BotStatus.RUNNING)
    )
    active_bots = active_result.scalar() or 0

    # Total invoices
    invoices_result = await db.execute(select(func.count(Invoice.id)))
    total_invoices = invoices_result.scalar() or 0

    # Paid invoices
    paid_result = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.PAID)
    )
    paid_invoices = paid_result.scalar() or 0

    # Total revenue
    revenue_result = await db.execute(
        select(func.sum(Invoice.amount_sol)).where(Invoice.status == InvoiceStatus.PAID)
    )
    total_revenue = float(revenue_result.scalar() or 0)

    # Active subscriptions
    active_subs_result = await db.execute(
        select(func.count(Subscription.id)).where(
            Subscription.state.in_([SubscriptionState.ACTIVE, SubscriptionState.GRACE])
        )
    )
    active_subscriptions = active_subs_result.scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        total_bots=total_bots,
        active_bots=active_bots,
        total_invoices=total_invoices,
        paid_invoices=paid_invoices,
        total_revenue_sol=total_revenue,
        active_subscriptions=active_subscriptions,
    )


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
    offset: int = 0,
) -> list[AdminUserResponse]:
    """List all users with stats."""
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    users = result.scalars().all()

    user_responses = []
    for user in users:
        # Get bot count
        bots_result = await db.execute(
            select(func.count(Bot.id))
            .where(Bot.owner_id == user.id)
            .where(Bot.status != BotStatus.DELETED)
        )
        bots_count = bots_result.scalar() or 0

        # Get total paid
        paid_result = await db.execute(
            select(func.sum(Invoice.amount_sol))
            .join(Bot)
            .where(Bot.owner_id == user.id)
            .where(Invoice.status == InvoiceStatus.PAID)
        )
        total_paid = float(paid_result.scalar() or 0)

        user_responses.append(
            AdminUserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                bots_count=bots_count,
                total_paid_sol=total_paid,
            )
        )

    return user_responses


@router.get("/bots", response_model=list[AdminBotResponse])
async def list_all_bots(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
    offset: int = 0,
) -> list[AdminBotResponse]:
    """List all bots with owner info."""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.owner), selectinload(Bot.subscription))
        .where(Bot.status != BotStatus.DELETED)
        .order_by(Bot.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    bots = result.scalars().all()

    return [
        AdminBotResponse(
            id=bot.id,
            owner_id=bot.owner_id,
            owner_email=bot.owner.email,
            name=bot.name,
            telegram_username=bot.telegram_username,
            status=bot.status,
            subscription_state=bot.subscription.state if bot.subscription else None,
            subscription_active_until=bot.subscription.active_until if bot.subscription else None,
            created_at=bot.created_at,
        )
        for bot in bots
    ]


@router.get("/invoices", response_model=list[AdminInvoiceResponse])
async def list_all_invoices(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: InvoiceStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AdminInvoiceResponse]:
    """List all invoices."""
    query = (
        select(Invoice)
        .options(selectinload(Invoice.bot).selectinload(Bot.owner))
        .order_by(Invoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter:
        query = query.where(Invoice.status == status_filter)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return [
        AdminInvoiceResponse(
            id=inv.id,
            bot_id=inv.bot_id,
            bot_name=inv.bot.name,
            owner_email=inv.bot.owner.email,
            amount_sol=float(inv.amount_sol),
            status=inv.status,
            tx_signature=inv.tx_signature,
            created_at=inv.created_at,
            expires_at=inv.expires_at,
            paid_at=inv.paid_at,
        )
        for inv in invoices
    ]


@router.post("/bots/{bot_id}/override")
async def override_bot_state(
    bot_id: uuid.UUID,
    request: AdminOverrideRequest,
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Admin override for bot/subscription state."""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.subscription))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    service = BotService(db)
    message = ""

    if request.action == "activate":
        if bot.subscription:
            now = datetime.now(timezone.utc)
            bot.subscription.state = SubscriptionState.ACTIVE
            if not bot.subscription.active_until or bot.subscription.active_until < now:
                bot.subscription.active_until = now + timedelta(days=30)
            bot.subscription.grace_until = bot.subscription.active_until + timedelta(
                days=settings.grace_days
            )
            message = "Subscription activated"

    elif request.action == "deactivate":
        if bot.subscription:
            bot.subscription.state = SubscriptionState.EXPIRED
            message = "Subscription deactivated"
        if bot.status == BotStatus.RUNNING:
            await service.stop_bot(bot)
            message += ", bot stopped"

    elif request.action == "extend":
        if bot.subscription and request.extend_days:
            if bot.subscription.active_until:
                bot.subscription.active_until += timedelta(days=request.extend_days)
            else:
                bot.subscription.active_until = datetime.now(timezone.utc) + timedelta(
                    days=request.extend_days
                )
            bot.subscription.grace_until = bot.subscription.active_until + timedelta(
                days=settings.grace_days
            )
            bot.subscription.state = SubscriptionState.ACTIVE
            message = f"Extended by {request.extend_days} days"

    elif request.action == "cancel":
        if bot.subscription:
            bot.subscription.state = SubscriptionState.CANCELLED
            message = "Subscription cancelled"
        if bot.status == BotStatus.RUNNING:
            await service.stop_bot(bot)
            message += ", bot stopped"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {request.action}",
        )

    # Create audit log
    audit = AuditLog(
        user_id=admin.id,
        action=f"admin_override_{request.action}",
        resource_type="bot",
        resource_id=str(bot_id),
        details={"reason": request.reason, "extend_days": request.extend_days},
    )
    db.add(audit)

    await db.commit()

    return {"message": message, "action": request.action}


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tx_signature: str | None = None,
) -> dict:
    """Manually mark an invoice as paid (admin override)."""
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.bot).selectinload(Bot.subscription))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if invoice.status == InvoiceStatus.PAID:
        return {"message": "Invoice already paid"}

    # Mark as paid
    invoice.status = InvoiceStatus.PAID
    invoice.tx_signature = tx_signature or "ADMIN_OVERRIDE"
    invoice.paid_at = datetime.now(timezone.utc)

    # Activate subscription
    if invoice.bot.subscription:
        sub = invoice.bot.subscription
        now = datetime.now(timezone.utc)
        months = float(invoice.amount_sol) / float(sub.price_per_month_sol)

        if sub.active_until and sub.active_until > now:
            sub.active_until = sub.active_until + timedelta(days=30 * months)
        else:
            sub.active_until = now + timedelta(days=30 * months)

        sub.grace_until = sub.active_until + timedelta(days=settings.grace_days)
        sub.state = SubscriptionState.ACTIVE

    # Audit log
    audit = AuditLog(
        user_id=admin.id,
        action="admin_mark_paid",
        resource_type="invoice",
        resource_id=str(invoice_id),
        details={"tx_signature": tx_signature},
    )
    db.add(audit)

    await db.commit()

    return {"message": "Invoice marked as paid", "active_until": str(invoice.bot.subscription.active_until)}
