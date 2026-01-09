"""Rate limiting middleware using Redis."""
import time
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm."""

    def __init__(
        self,
        app,
        redis_url: str,
        requests_per_minute: int = 100,
        burst_size: int = 20,
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_seconds = 60
        self._redis: redis.Redis | None = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    async def is_rate_limited(self, key: str) -> tuple[bool, int, int]:
        """
        Check if request should be rate limited.

        Returns:
            tuple: (is_limited, remaining_requests, reset_time)
        """
        try:
            r = await self.get_redis()
            now = time.time()
            window_start = now - self.window_seconds

            pipe = r.pipeline()

            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry on the key
            pipe.expire(key, self.window_seconds + 1)

            results = await pipe.execute()
            request_count = results[1]

            remaining = max(0, self.requests_per_minute - request_count - 1)
            reset_time = int(now + self.window_seconds)

            if request_count >= self.requests_per_minute:
                return True, 0, reset_time

            return False, remaining, reset_time

        except Exception as e:
            logger.warning("Rate limit check failed", error=str(e))
            # Fail open - allow request if Redis is down
            return False, self.requests_per_minute, int(time.time() + 60)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/metrics"]:
            return await call_next(request)

        # Skip for internal runner endpoints
        if request.url.path.startswith("/runner/"):
            return await call_next(request)

        client_ip = self.get_client_ip(request)
        rate_limit_key = f"rate_limit:{client_ip}"

        is_limited, remaining, reset_time = await self.is_rate_limited(rate_limit_key)

        if is_limited:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


class AuthenticatedRateLimiter:
    """Per-user rate limiting for authenticated endpoints."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def check_limit(
        self,
        user_id: str,
        action: str,
        limit: int,
        window_seconds: int = 3600,
    ) -> tuple[bool, int]:
        """
        Check rate limit for user action.

        Returns:
            tuple: (allowed, remaining)
        """
        try:
            r = await self.get_redis()
            key = f"user_limit:{user_id}:{action}"

            current = await r.get(key)

            if current is None:
                await r.setex(key, window_seconds, 1)
                return True, limit - 1

            count = int(current)
            if count >= limit:
                return False, 0

            await r.incr(key)
            return True, limit - count - 1

        except Exception as e:
            logger.warning("User rate limit check failed", error=str(e))
            return True, limit  # Fail open
