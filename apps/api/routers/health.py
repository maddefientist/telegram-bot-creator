"""Health check routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from database import get_db
from config import get_settings

settings = get_settings()
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "api",
        "version": "1.0.0",
    }


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Readiness check - verifies database and Redis connectivity."""
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    is_ready = db_status == "healthy" and redis_status == "healthy"

    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db_status,
            "redis": redis_status,
        },
    }


@router.get("/metrics")
async def metrics(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Basic metrics endpoint."""
    from sqlalchemy import select, func
    from models.bot import Bot, BotStatus
    from models.user import User

    # Count bots by status
    bots_result = await db.execute(
        select(Bot.status, func.count(Bot.id))
        .group_by(Bot.status)
    )
    bots_by_status = {row[0].value: row[1] for row in bots_result}

    # Total users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bots": {
            "total": sum(bots_by_status.values()),
            "by_status": bots_by_status,
        },
        "users": {
            "total": total_users,
        },
    }
