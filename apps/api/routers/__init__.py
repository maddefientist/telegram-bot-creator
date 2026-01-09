"""API routers."""
from routers.auth import router as auth_router
from routers.bots import router as bots_router
from routers.ai import router as ai_router
from routers.payments import router as payments_router
from routers.admin import router as admin_router
from routers.runner import router as runner_router
from routers.health import router as health_router

__all__ = [
    "auth_router",
    "bots_router",
    "ai_router",
    "payments_router",
    "admin_router",
    "runner_router",
    "health_router",
]
