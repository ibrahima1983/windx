"""Rate limiting configuration and utilities.

This module provides rate limiting functionality using Redis with fastapi-limiter.
Protects API endpoints from abuse and ensures fair usage.

Public Functions:
    init_limiter: Initialize rate limiter
    close_limiter: Close limiter connections
    get_rate_limit_key: Get rate limit key for user

Features:
    - Redis-based rate limiting
    - Per-user and per-IP rate limits
    - Customizable rate limit rules
    - Automatic cleanup of expired limits
    - Integration with FastAPI
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from fastapi import Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis import asyncio as aioredis

from app.core.config import Settings, get_settings

__all__ = [
    "init_limiter",
    "close_limiter",
    "get_rate_limit_key",
    "RateLimiter",
    "rate_limit",
]


@lru_cache
def get_limiter_redis_client(settings: Settings | None = None) -> aioredis.Redis:
    """Get Redis client for rate limiter.

    Args:
        settings (Settings | None): Application settings

    Returns:
        aioredis.Redis: Redis client instance (cached singleton)
    """
    if settings is None:
        settings = get_settings()

    return aioredis.from_url(
        str(settings.limiter.redis_url),
        encoding="utf-8",
        decode_responses=True,
    )


async def init_limiter() -> None:
    """Initialize rate limiter.

    This function should be called on application startup to initialize
    the rate limiter with Redis backend.

    Example:
        @app.on_event("startup")
        async def startup():
            await init_limiter()
    """
    settings = get_settings()

    if not settings.limiter.enabled:
        print("[WARNING] Rate limiter disabled")
        # Initialize with a mock to prevent errors in endpoints
        from unittest.mock import AsyncMock

        # Create a no-op callback that does nothing
        async def noop_callback(*args, **kwargs):
            pass

        FastAPILimiter.redis = AsyncMock()
        FastAPILimiter.lua_sha = "mock_sha"
        FastAPILimiter.identifier = get_rate_limit_key
        FastAPILimiter.http_callback = noop_callback
        FastAPILimiter.ws_callback = noop_callback
        return

    try:
        redis = get_limiter_redis_client(settings)

        await FastAPILimiter.init(
            redis,
            prefix=settings.limiter.prefix,
            identifier=get_rate_limit_key,
        )

        print(f"[OK] Rate limiter initialized: Redis @ {settings.limiter.redis_host}")
    except Exception as e:
        print(f"[WARNING] Rate limiter initialization failed: {e}")
        print("[WARNING] Rate limiter will be disabled")
        # Initialize with a mock to prevent errors in endpoints
        from unittest.mock import AsyncMock

        # Create a no-op callback that does nothing
        async def noop_callback(*args, **kwargs):
            pass

        FastAPILimiter.redis = AsyncMock()
        FastAPILimiter.lua_sha = "mock_sha"
        FastAPILimiter.identifier = get_rate_limit_key
        FastAPILimiter.http_callback = noop_callback
        FastAPILimiter.ws_callback = noop_callback


async def close_limiter() -> None:
    """Close rate limiter connections.

    This function should be called on application shutdown to properly
    close all rate limiter connections.

    Example:
        @app.on_event("shutdown")
        async def shutdown():
            await close_limiter()
    """
    try:
        settings = get_settings()

        if not settings.limiter.enabled:
            return

        # Only close if FastAPILimiter was actually initialized with real Redis
        if FastAPILimiter.redis and not isinstance(FastAPILimiter.redis, type(None)):
            await FastAPILimiter.close()
            print("[OK] Rate limiter connections closed")
    except Exception as e:
        print(f"[WARNING] Error closing rate limiter connections: {e}")
    print("[OK] Rate limiter connections closed")


async def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key for request.

    This function generates a unique key for rate limiting based on
    the authenticated user or client IP address.

    Args:
        request (Request): FastAPI request object

    Returns:
        str: Rate limit key (user ID or IP address)

    Example:
        # Authenticated user
        # Returns: "user:123"

        # Anonymous user
        # Returns: "ip:192.168.1.1"
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)

    if user:
        return f"user:{user.id}"

    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def rate_limit(times: int = 10, seconds: int = 60) -> Callable:
    """Create rate limit dependency.

    Args:
        times (int): Number of requests allowed
        seconds (int): Time window in seconds

    Returns:
        Callable: Rate limiter dependency

    Example:
        @router.get("/endpoint", dependencies=[Depends(rate_limit(times=5, seconds=60))])
        async def endpoint():
            pass
    """
    return RateLimiter(times=times, seconds=seconds)
