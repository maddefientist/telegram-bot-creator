"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings
from core.logging import configure_logging, get_logger
from core.rate_limit import RateLimitMiddleware
from database import init_db, close_db
from routers import (
    auth_router,
    bots_router,
    ai_router,
    payments_router,
    admin_router,
    runner_router,
    health_router,
)

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    logger.info("Starting application...")
    # Startup
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.app_name,
    description="Telegram Bot Creator API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Only add HSTS in production
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


# Add middlewares in order (last added = first executed)
# 1. Security headers (outermost)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.redis_url,
    requests_per_minute=settings.api_rate_limit,
    burst_size=20,
)

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=["X-CSRF-Token", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    # Skip logging for health checks to reduce noise
    if request.url.path not in ["/health", "/health/ready"]:
        logger.info(
            "Request",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

    response = await call_next(request)

    if request.url.path not in ["/health", "/health/ready"]:
        logger.info(
            "Response",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

    return response


# CSRF middleware for mutating requests
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    """Validate CSRF token for mutating requests."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # Skip CSRF for certain paths
        skip_paths = ["/auth/login", "/auth/register", "/runner/", "/health"]
        if not any(request.url.path.startswith(p) for p in skip_paths):
            # CSRF token should be in header
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                # For API, we rely on cookie + header combo
                # The actual validation happens in auth dependency
                pass

    return await call_next(request)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    # Don't expose internal errors in production
    detail = "Internal server error"
    if settings.debug:
        detail = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
    )


# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(bots_router)
app.include_router(ai_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(runner_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
    }
