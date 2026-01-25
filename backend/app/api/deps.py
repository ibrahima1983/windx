"""API dependencies for dependency injection.

This module provides FastAPI dependencies for authentication and
authorization using JWT tokens.

Public Functions:
    get_current_user: Get current authenticated user from JWT token
    get_current_active_superuser: Get current superuser

Features:
    - JWT token validation
    - User authentication
    - Superuser authorization
    - HTTP Bearer token support
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository

__all__ = ["get_current_user", "get_current_active_superuser"]

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token.

    Supports both Bearer token (API) and Cookie (Browser) authentication.

    Args:
        request (Request): FastAPI request object
        credentials (HTTPAuthorizationCredentials | None): HTTP bearer credentials
        db (AsyncSession): Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = None

    # 1. Try Bearer token from Authorization header
    if credentials:
        token = credentials.credentials

    # 2. Try Cookie if no Bearer token
    if not token:
        token = request.cookies.get("access_token")
        # Handle "Bearer " prefix in cookie if present
        if token and token.startswith("Bearer "):
            token = token.split(" ")[1]

    if not token:
        # Check if it's a browser request (HTML) -> Redirect to login
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            # For browser requests, we might want to redirect, but dependencies
            # usually raise exceptions. The exception handler or the endpoint
            # should handle the redirect. For now, we raise 401.
            # The admin endpoints can catch this or we can use a separate dependency for admin pages.
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if session is active
    from app.repositories.session import SessionRepository

    session_repo = SessionRepository(db)
    session = await session_repo.get_by_token(token)

    if session is None or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    user = await user_repo.get(int(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active superuser.

    Args:
        current_user (User): Current authenticated user

    Returns:
        User: Current superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def get_admin_context(
    request: Request,
    current_user: User,
    active_page: str = "dashboard",
    **extra: Any,
) -> dict[str, Any]:
    """Return a template context dictionary with common admin data.

    Includes the request, current_user, active_page, RBAC helpers, and the experimental feature flags.
    Additional keyword arguments are merged into the context.
    """
    from app.core.rbac_template_helpers import RBACHelper

    settings = get_settings()

    # Create RBAC helper for template context
    rbac_helper = RBACHelper(current_user)

    context: dict[str, Any] = {
        "request": request,
        "current_user": current_user,
        "active_page": active_page,
        "enable_customers": settings.windx.experimental_customers_page,
        "enable_orders": settings.windx.experimental_orders_page,
        # Add RBAC helpers
        "rbac": rbac_helper,
        "can": rbac_helper.can,
        "has": rbac_helper.has,
    }
    context.update(extra)
    return context
