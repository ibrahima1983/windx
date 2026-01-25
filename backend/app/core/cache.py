"""Caching configuration and utilities.

This module provides caching functionality using Redis with fastapi-cache2.
Supports multiple cache backends and provides decorators for easy caching.

Public Functions:
    init_cache: Initialize cache backend
    close_cache: Close cache connections
    cache_key_builder: Custom cache key builder

Features:
    - Redis caching with fastapi-cache2
    - Custom cache key generation
    - TTL (Time To Live) support
    - Namespace support for cache isolation
    - Easy decorator-based caching
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Any

from fastapi import Request, Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.core.config import Settings, get_settings

__all__ = ["init_cache", "close_cache", "cache_key_builder", "get_redis_client"]


@lru_cache
def get_redis_client(settings: Settings | None = None) -> aioredis.Redis:
    """Get Redis client instance.

    Args:
        settings (Settings | None): Application settings

    Returns:
        aioredis.Redis: Redis client instance (cached singleton)
    """
    if settings is None:
        settings = get_settings()

    return aioredis.from_url(
        str(settings.cache.redis_url),
        encoding="utf-8",
        decode_responses=True,
    )


async def init_cache() -> None:
    """Initialize cache backend.

    This function should be called on application startup to initialize
    the cache backend (Redis).

    Example:
        @app.on_event("startup")
        async def startup():
            await init_cache()
    """
    settings = get_settings()

    if not settings.cache.enabled:
        print("[WARNING] Cache disabled")
        # Initialize with in-memory backend to prevent errors
        from fastapi_cache.backends.inmemory import InMemoryBackend

        FastAPICache.init(InMemoryBackend())
        return

    try:
        redis = get_redis_client(settings)

        FastAPICache.init(
            RedisBackend(redis),
            prefix=settings.cache.prefix,
            expire=settings.cache.default_ttl,
        )

        print(f"[OK] Cache initialized: Redis @ {settings.cache.redis_host}")
    except Exception as e:
        print(f"[WARNING] Cache initialization failed: {e}")
        print("[WARNING] Falling back to in-memory cache")
        # Fall back to in-memory cache
        from fastapi_cache.backends.inmemory import InMemoryBackend

        FastAPICache.init(InMemoryBackend())


async def close_cache() -> None:
    """Close cache connections.

    This function should be called on application shutdown to properly
    close all cache connections.

    Example:
        @app.on_event("shutdown")
        async def shutdown():
            await close_cache()
    """
    try:
        settings = get_settings()

        if not settings.cache.enabled:
            return

        redis = get_redis_client(settings)
        await redis.close()
        print("[OK] Cache connections closed")
    except Exception as e:
        print(f"[WARNING] Error closing cache connections: {e}")


def cache_key_builder(
    func: Callable,
    namespace: str = "",
    request: Request | None = None,
    response: Response | None = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """Build cache key from function and parameters.

    This function generates a unique cache key based on the function name,
    namespace, and parameters. Used by fastapi-cache2 for cache key generation.

    Args:
        func (Callable): Function being cached
        namespace (str): Cache namespace for isolation
        request (Request | None): FastAPI request object
        response (Response | None): FastAPI response object
        args (tuple | None): Function positional arguments
        kwargs (dict | None): Function keyword arguments

    Returns:
        str: Generated cache key

    Example:
        @cache(key_builder=cache_key_builder)
        async def get_user(user_id: int):
            pass
        # Cache key: "myapp:get_user:user_id=123"
    """
    settings = get_settings()
    prefix = settings.cache.prefix

    # Build key from function name
    # noinspection PyUnresolvedReferences
    cache_key = f"{prefix}:{namespace}:{func.__module__}:{func.__name__}"

    # Add request path if available
    if request:
        cache_key += f":{request.url.path}"

    # Add function arguments
    if args:
        cache_key += f":args={':'.join(str(arg) for arg in args)}"

    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        cache_key += f":kwargs={':'.join(f'{k}={v}' for k, v in sorted_kwargs)}"

    return cache_key


def get_cache_namespace(resource: str) -> str:
    """Get cache namespace for a resource.

    Args:
        resource (str): Resource name (e.g., "users", "products")

    Returns:
        str: Cache namespace

    Example:
        namespace = get_cache_namespace("users")
        # Returns: "users"
    """
    return resource


async def invalidate_cache(pattern: str) -> int:
    """Invalidate cache keys matching pattern.

    Args:
        pattern (str): Redis key pattern (e.g., "users:*")

    Returns:
        int: Number of keys deleted

    Example:
        # Invalidate all user caches
        await invalidate_cache("users:*")
    """
    settings = get_settings()

    if not settings.cache.enabled:
        return 0

    redis = get_redis_client(settings)
    keys = await redis.keys(f"{settings.cache.prefix}:{pattern}")

    if keys:
        return await redis.delete(*keys)

    return 0
