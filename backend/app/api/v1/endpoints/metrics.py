"""Metrics endpoints for system monitoring.

This module provides endpoints for monitoring system metrics including
database connection pool statistics and other performance indicators.

Public Functions:
    database_metrics: Get database connection pool metrics

Features:
    - Database connection pool monitoring
    - Superuser-only access for security
    - Real-time metrics (no caching)
    - Comprehensive OpenAPI documentation
"""

import asyncio

from fastapi import APIRouter, status
from sqlalchemy.pool import QueuePool

from app.api.types import CurrentSuperuser
from app.database.connection import get_engine
from app.schemas.responses import get_common_responses

__all__ = ["router", "database_metrics"]

router = APIRouter(
    tags=["Metrics"],
    responses=get_common_responses(401, 403, 500),
)


@router.get(
    "/database",
    status_code=status.HTTP_200_OK,
    summary="Get Database Connection Pool Metrics",
    description=(
        "Retrieve real-time database connection pool statistics including "
        "pool size, checked in/out connections, overflow, and total connections. "
        "This endpoint is restricted to superusers only for security purposes."
    ),
    response_description="Database connection pool metrics",
    operation_id="getDatabaseMetrics",
    responses={
        200: {
            "description": "Database metrics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "pool_size": 10,
                        "checked_in": 7,
                        "checked_out": 3,
                        "overflow": 0,
                        "total_connections": 10,
                    }
                }
            },
        },
        **get_common_responses(401, 403, 500),
    },
)
async def database_metrics(
    current_superuser: CurrentSuperuser,
) -> dict[str, int]:
    """Get database connection pool metrics.

    This endpoint provides real-time statistics about the database connection
    pool, which is useful for monitoring database connectivity and identifying
    potential connection issues or bottlenecks.

    Args:
        current_superuser (User): Current authenticated superuser

    Returns:
        dict[str, int]: Dictionary containing:
            - pool_size: Maximum number of connections in the pool
            - checked_in: Number of connections currently available in the pool
            - checked_out: Number of connections currently in use
            - overflow: Number of connections beyond pool_size
            - total_connections: Total connections (pool_size + overflow)
    """
    engine = get_engine()
    sync_pool = engine.sync_engine.pool  # Access the underlying sync pool

    # Assert that it's a QueuePool (which supports the metrics methods)
    assert isinstance(sync_pool, QueuePool), "Expected QueuePool for metrics"

    pool_size = await asyncio.to_thread(sync_pool.size)
    checked_in = await asyncio.to_thread(sync_pool.checkedin)
    checked_out = await asyncio.to_thread(sync_pool.checkedout)
    overflow = await asyncio.to_thread(sync_pool.overflow)

    return {
        "pool_size": pool_size,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "overflow": overflow,
        "total_connections": pool_size + overflow,
    }
