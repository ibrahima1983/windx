"""User repository for database operations.

This module implements the repository pattern for User model with
custom query methods for user management.

Public Classes:
    UserRepository: Repository for User CRUD operations

Features:
    - User lookup by email and username
    - Active user filtering
    - Inherits base CRUD operations
    - Type-safe async operations
"""

from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate

__all__ = ["UserRepository"]


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user repository.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email (str): User email address

        Returns:
            User | None: User instance or None if not found
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username (str): Username

        Returns:
            User | None: User instance or None if not found
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate user by username and password.

        Args:
            username (str): Username
            password (str): Plain text password

        Returns:
            User | None: User instance if authentication successful, None otherwise
        """
        from app.core.security import verify_password

        user = await self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users.

        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return

        Returns:
            list[User]: List of active users
        """
        result = await self.db.execute(
            select(User).where(User.is_active == True).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    def get_filtered_users(
        self,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Select:
        """Build filtered query for users.

        Creates a SQLAlchemy Select statement with dynamic filters and sorting.
        This method returns a Select statement that can be used with pagination
        or executed directly.

        Args:
            is_active (bool | None): Filter by active status (None = no filter)
            is_superuser (bool | None): Filter by superuser status (None = no filter)
            search (str | None): Search term for username, email, or full_name (case-insensitive)
            sort_by (str): Column name to sort by (default: "created_at")
            sort_order (str): Sort direction "asc" or "desc" (default: "desc")

        Returns:
            Select: SQLAlchemy select statement with filters and sorting applied

        Example:
            >>> query = repo.get_filtered_users(is_active=True, search="john")
            >>> result = await db.execute(query)
            >>> users = result.scalars().all()

        Note:
            The returned Select statement can be passed to fastapi-pagination's
            paginate() function for automatic pagination support.
        """
        # Start with base query
        query = select(User)

        # Apply is_active filter
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Apply is_superuser filter
        if is_superuser is not None:
            query = query.where(User.is_superuser == is_superuser)

        # Apply search filter (case-insensitive search across username, email, full_name)
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                )
            )

        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        return query
