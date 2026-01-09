"""Bot management routes."""
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_active_user
from database import get_db
from models.user import User
from models.bot import BotStatus
from schemas.bot import (
    BotCreate,
    BotResponse,
    BotListResponse,
    BotStatusResponse,
    BotLogsResponse,
    ValidateBotSpecRequest,
    ValidateBotSpecResponse,
)
from services.bot_service import BotService
from services.ai_service import AIService

router = APIRouter(prefix="/bots", tags=["bots"])


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    bot_data: BotCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Create a new bot."""
    service = BotService(db)

    try:
        bot = await service.create_bot(
            owner_id=current_user.id,
            name=bot_data.name,
            telegram_token=bot_data.telegram_token,
            description=bot_data.description,
            price_per_month_sol=bot_data.price_per_month_sol,
        )
        return bot
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=list[BotListResponse])
async def list_bots(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """List all bots for the current user."""
    service = BotService(db)
    return await service.get_user_bots(current_user.id)


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get a specific bot."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    return bot


@router.put("/{bot_id}/spec", response_model=BotResponse)
async def update_bot_spec(
    bot_id: uuid.UUID,
    spec_data: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Update a bot's specification."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    try:
        bot = await service.update_bot_spec(bot, spec_data)
        return bot
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Start a bot."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    success, message = await service.start_bot(bot)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {"message": message, "status": bot.status.value}


@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Stop a bot."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    success, message = await service.stop_bot(bot)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {"message": message, "status": bot.status.value}


@router.post("/{bot_id}/restart")
async def restart_bot(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Restart a bot."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    success, message = await service.restart_bot(bot)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {"message": message, "status": bot.status.value}


@router.get("/{bot_id}/status", response_model=BotStatusResponse)
async def get_bot_status(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get bot status including recent logs."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    logs = await service.get_bot_logs(bot, tail=50)

    return BotStatusResponse(
        id=bot.id,
        status=bot.status,
        last_heartbeat=bot.last_heartbeat,
        last_error=bot.last_error,
        container_id=bot.container_id,
        logs=logs,
    )


@router.get("/{bot_id}/logs", response_model=BotLogsResponse)
async def get_bot_logs(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tail: int = 100,
) -> Any:
    """Get bot logs."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    logs = await service.get_bot_logs(bot, tail=tail)

    return BotLogsResponse(
        bot_id=bot.id,
        logs=logs,
        since=None,
    )


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a bot."""
    service = BotService(db)
    bot = await service.get_bot(bot_id, current_user.id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    await service.delete_bot(bot)


@router.post("/validate-spec", response_model=ValidateBotSpecResponse)
async def validate_spec(
    request: ValidateBotSpecRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ValidateBotSpecResponse:
    """Validate a BotSpec without saving."""
    ai_service = AIService()
    valid, errors = ai_service.validate_spec(request.spec)

    return ValidateBotSpecResponse(
        valid=valid,
        errors=errors,
        validated_spec=request.spec if valid else None,
    )
