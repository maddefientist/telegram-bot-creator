"""AI generation routes."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import get_current_active_user
from database import get_db
from models.user import User
from models.ai_usage import AIUsage
from schemas.ai import GenerateBotSpecRequest, GenerateBotSpecResponse
from services.ai_service import AIService

settings = get_settings()
router = APIRouter(prefix="/ai", tags=["ai"])


async def check_rate_limit(user_id, db: AsyncSession) -> bool:
    """Check if user has exceeded AI generation rate limit."""
    # Get current hour window
    now = datetime.now(timezone.utc)
    hour_start = now.replace(minute=0, second=0, microsecond=0)

    # Count requests in current hour
    result = await db.execute(
        select(func.sum(AIUsage.requests_count))
        .where(AIUsage.user_id == user_id)
        .where(AIUsage.period_start >= hour_start)
    )
    count = result.scalar() or 0

    return count < settings.ai_generation_rate_limit


async def record_usage(
    user_id,
    tokens: int,
    db: AsyncSession,
    bot_id=None,
) -> None:
    """Record AI usage for rate limiting."""
    now = datetime.now(timezone.utc)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    # Find or create usage record for this hour
    result = await db.execute(
        select(AIUsage)
        .where(AIUsage.user_id == user_id)
        .where(AIUsage.period_start == hour_start)
    )
    usage = result.scalar_one_or_none()

    if usage:
        usage.tokens_used += tokens
        usage.requests_count += 1
    else:
        usage = AIUsage(
            user_id=user_id,
            bot_id=bot_id,
            tokens_used=tokens,
            requests_count=1,
            period_start=hour_start,
            period_end=hour_end,
        )
        db.add(usage)

    await db.commit()


@router.post("/generate-botspec", response_model=GenerateBotSpecResponse)
async def generate_botspec(
    request: GenerateBotSpecRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenerateBotSpecResponse:
    """Generate a BotSpec using AI."""
    # Check rate limit
    if not await check_rate_limit(current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {settings.ai_generation_rate_limit} generations per hour.",
        )

    ai_service = AIService()

    try:
        spec, errors, tokens, retries = await ai_service.generate_botspec(
            description=request.description,
            bot_name=request.bot_name,
            enabled_modules=request.enabled_modules,
            constraints=request.constraints,
        )

        # Record usage
        await record_usage(current_user.id, tokens, db)

        if errors:
            return GenerateBotSpecResponse(
                success=False,
                errors=errors,
                tokens_used=tokens,
                retries=retries,
            )

        return GenerateBotSpecResponse(
            success=True,
            spec=spec,
            tokens_used=tokens,
            retries=retries,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {str(e)}",
        )
