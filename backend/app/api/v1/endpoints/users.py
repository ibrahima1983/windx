"""User management endpoints.

This module provides REST API endpoints for user management including
listing, retrieving, updating, and deleting users.

Public Variables:
    router: FastAPI router for user endpoints

Features:
    - List all users with pagination (superuser only)
    - Get user by ID with caching
    - Update user information
    - Delete user (superuser only)
    - Permission-based access control
    - Rate limiting on all endpoints
    - Caching for read operations
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi_cache.decorator import cache
from pydantic import PositiveInt

from app.api.types import CurrentSuperuser, CurrentUser, DBSession
from app.core.limiter import rate_limit
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.user import User
from app.schemas.responses import get_common_responses
from app.schemas.user import User as UserSchema
from app.schemas.user import UserCreate, UserUpdate

# Add pagination params dependency
PaginationParams = Annotated[PaginationParams, Depends(create_pagination_params)]

__all__ = ["router"]

router = APIRouter(
    tags=["Users"],
    responses=get_common_responses(401, 403, 500),
)


@router.get(
    "/",
    response_model=Page[UserSchema],
    summary="List Users with Filters",
    description="List all users with optional filtering by active status, superuser status, and search term. Supports sorting by created_at, username, or email.",
    response_description="Paginated list of users matching the filters",
    operation_id="listUsers",
    responses={
        200: {
            "description": "Successfully retrieved users",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "email": "user@example.com",
                                "username": "john_doe",
                                "full_name": "John Doe",
                                "is_active": True,
                                "is_superuser": False,
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z",
                            }
                        ],
                        "total": 100,
                        "page": 1,
                        "size": 50,
                        "pages": 2,
                    }
                }
            },
        },
        **get_common_responses(401, 403, 500),
    },
)
async def list_users(
    current_superuser: CurrentSuperuser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true=active, false=inactive, null=all)"),
    ] = None,
    is_superuser: Annotated[
        bool | None,
        Query(
            description="Filter by superuser status (true=superusers, false=regular users, null=all)"
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Search term for username, email, or full name (case-insensitive)",
        ),
    ] = None,
    sort_by: Annotated[
        Literal["created_at", "username", "email"],
        Query(description="Column to sort by"),
    ] = "created_at",
    sort_order: Annotated[
        Literal["asc", "desc"],
        Query(description="Sort direction (asc=ascending, desc=descending)"),
    ] = "desc",
) -> Page[User]:
    """List all users with filtering and sorting (superuser only).

    Provides comprehensive user listing with optional filters for active status,
    superuser status, and text search. Results can be sorted by creation date,
    username, or email in ascending or descending order.

    Args:
        current_superuser (User): Current superuser
        params (PaginationParams): Pagination parameters (page, size)
        db (AsyncSession): Database session
        is_active (bool | None): Filter by active status (None = no filter)
        is_superuser (bool | None): Filter by superuser status (None = no filter)
        search (str | None): Search term for username, email, or full_name
        sort_by (Literal): Column to sort by (created_at, username, email)
        sort_order (Literal): Sort direction (asc, desc)

    Returns:
        Page[User]: Paginated list of users matching the filters

    Example:
        GET /api/v1/users?is_active=true&search=john&sort_by=username&sort_order=asc

    Note:
        - All filters are optional and can be combined
        - Search is case-insensitive and matches username, email, or full_name
        - Default sorting is by created_at in descending order (newest first)
    """
    from app.core.pagination import paginate
    from app.repositories.user import UserRepository

    user_repo = UserRepository(db)

    # Build filtered query using repository method
    query = user_repo.get_filtered_users(
        is_active=is_active,
        is_superuser=is_superuser,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Paginate the query
    return await paginate(db, query, params)


@router.get(
    "/{user_id}",
    response_model=UserSchema,
    dependencies=[Depends(rate_limit(times=20, seconds=60))],
)
@cache(expire=300)  # Cache for 5 minutes
async def get_user(
    user_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> User:
    """Get user by ID with caching.

    Rate limit: 20 requests per minute.
    Cache TTL: 5 minutes.

    Args:
        user_id (PositiveInt): User ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        User: User data

    Raises:
        AuthorizationException: If user lacks permission
        NotFoundException: If user not found
    """
    from app.services.user import UserService

    user_service = UserService(db)
    return await user_service.get_user_with_permission_check(user_id, current_user)


@router.patch(
    "/{user_id}",
    response_model=UserSchema,
    dependencies=[Depends(rate_limit(times=10, seconds=60))],
)
async def update_user(
    user_id: PositiveInt,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> User:
    """Update user information.

    Args:
        user_id (PositiveInt): User ID
        user_update (UserUpdate): User update data
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        User: Updated user data

    Raises:
        AuthorizationException: If user lacks permission
        NotFoundException: If user not found
        ConflictException: If email/username conflicts
    """
    from app.services.user import UserService

    user_service = UserService(db)
    updated_user = await user_service.update_user(user_id, user_update, current_user)

    # Invalidate cache for this user
    from app.core.cache import invalidate_cache

    await invalidate_cache(f"*get_user*{user_id}*")

    return updated_user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit(times=5, seconds=60))],
)
async def delete_user(
    user_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> None:
    """Delete user (superuser only).

    Args:
        user_id (PositiveInt): User ID
        current_superuser (User): Current superuser
        db (AsyncSession): Database session

    Raises:
        NotFoundException: If user not found
        AuthorizationException: If user is not superuser
    """
    from app.services.user import UserService

    user_service = UserService(db)
    await user_service.delete_user(user_id, current_superuser)


@router.post(
    "/bulk",
    response_model=list[UserSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Multiple Users in Bulk",
    description=(
        "Create multiple users in a single atomic transaction. "
        "If any user creation fails, the entire transaction is rolled back "
        "and no users are created. This endpoint is restricted to superusers only."
    ),
    response_description="List of successfully created users",
    operation_id="createUsersBulk",
    responses={
        201: {
            "description": "Users successfully created",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "email": "user1@example.com",
                            "username": "user1",
                            "full_name": "User One",
                            "is_active": True,
                            "is_superuser": False,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                        },
                        {
                            "id": 2,
                            "email": "user2@example.com",
                            "username": "user2",
                            "full_name": "User Two",
                            "is_active": True,
                            "is_superuser": False,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                        },
                    ]
                }
            },
        },
        409: {
            "description": "Email or username already exists",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Email already registered",
                        "details": [
                            {
                                "detail": "Email is already in use",
                                "field": "email",
                            }
                        ],
                    }
                }
            },
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def create_users_bulk(
    users_in: list[UserCreate],
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> list[User]:
    """Create multiple users in a single transaction (superuser only).

    This endpoint creates multiple users atomically. If any user creation fails
    due to validation errors or conflicts (duplicate email/username), the entire
    transaction is rolled back and no users are created.

    Args:
        users_in (list[UserCreate]): List of user creation data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        list[User]: List of created user instances

    Raises:
        ConflictException: If any email or username already exists
        DatabaseException: If transaction fails
        ValidationError: If any user data is invalid

    Example:
        POST /api/v1/users/bulk
        [
            {
                "email": "user1@example.com",
                "username": "user1",
                "password": "SecurePass123!",
                "full_name": "User One"
            },
            {
                "email": "user2@example.com",
                "username": "user2",
                "password": "SecurePass456!",
                "full_name": "User Two"
            }
        ]

    Note:
        - All users are created in a single database transaction
        - If any user fails validation or conflicts, no users are created
        - Each user must have a unique email and username
        - All passwords are hashed before storage
    """
    from app.services.user import UserService

    user_service = UserService(db)
    return await user_service.create_users_bulk(users_in)
