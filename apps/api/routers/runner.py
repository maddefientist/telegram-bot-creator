"""Runner service routes - internal API for bot containers."""
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.auth import verify_runner_auth
from database import get_db
from models.bot import Bot, BotStatus
from services.bot_service import BotService

router = APIRouter(prefix="/runner", tags=["runner"])


@router.get("/bot/{bot_id}/spec")
async def get_bot_spec(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[bool, Depends(verify_runner_auth)],
) -> dict[str, Any]:
    """Get BotSpec for a running bot (called by runner container)."""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    return {
        "bot_id": str(bot.id),
        "name": bot.name,
        "spec": bot.spec_json,
    }


@router.post("/bot/{bot_id}/heartbeat")
async def report_heartbeat(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[bool, Depends(verify_runner_auth)],
) -> dict:
    """Report heartbeat from running bot."""
    service = BotService(db)
    success = await service.update_heartbeat(bot_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    return {"status": "ok"}


@router.post("/bot/{bot_id}/error")
async def report_error(
    bot_id: uuid.UUID,
    error: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[bool, Depends(verify_runner_auth)],
) -> dict:
    """Report error from running bot."""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    error_message = error.get("message", "Unknown error")
    bot.last_error = error_message[:1000]  # Truncate long errors
    bot.status = BotStatus.ERROR

    await db.commit()

    return {"status": "recorded"}


@router.get("/bot/{bot_id}/check-active")
async def check_bot_active(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[bool, Depends(verify_runner_auth)],
) -> dict:
    """Check if bot subscription is still active (called periodically by runner)."""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.subscription))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        return {"active": False, "reason": "Bot not found"}

    service = BotService(db)
    can_run = await service._can_start_bot(bot)

    return {
        "active": can_run,
        "reason": "Subscription valid" if can_run else "Subscription expired",
    }
