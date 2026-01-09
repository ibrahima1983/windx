"""User service for business logic.

This module implements business logic for user management including
user creation, updates, validation, and complex operations.

Public Classes:
    UserService: User management business logic

Features:
    - User creation with validation
    - User updates with business rules
    - User deletion with cleanup
    - Complex user queries
    - Password management
"""

from __future__ import annotations

from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import BaseService

__all__ = ["UserService"]


class UserService(BaseService):
    """User service for business logic.

    Handles user management operations including creation, updates,
    deletion, and complex business logic.

    Attributes:
        db: Database session
        user_repo: User repository for data access
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.user_repo = UserRepository(db)

    async def create_user(self, user_in: UserCreate) -> User:
        """Create new user with validation.

        Validates that email and username are unique before creating user.
        Hashes password before storing.

        Args:
            user_in (UserCreate): User creation data

        Returns:
            User: Created user instance

        Raises:
            ConflictException: If email or username already exists
        """
        # Check if email already exists
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ConflictException(
                message="Email already registered",
                details={"email": user_in.email},
            )

        # Check if username already exists
        existing_user = await self.user_repo.get_by_username(user_in.username)
        if existing_user:
            raise ConflictException(
                message="Username already taken",
                details={"username": user_in.username},
            )

        # Hash password
        hashed_password = get_password_hash(user_in.password)

        # Create user model instance directly (type-safe approach)
        # We bypass the repository's create() because we need to add hashed_password
        # which is not in the UserCreate schema
        user_data = user_in.model_dump(exclude={"password"})
        user = User(
            **user_data,
            hashed_password=hashed_password,
        )

        self.user_repo.db.add(user)
        await self.commit()
        await self.refresh(user)

        return user

    async def get_user(self, user_id: PositiveInt) -> User:
        """Get user by ID.

        Args:
            user_id (PositiveInt): User ID

        Returns:
            User: User instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundException(
                resource="User",
                details={"user_id": user_id},
            )
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email (str): User email

        Returns:
            User | None: User instance or None if not found
        """
        return await self.user_repo.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username (str): Username

        Returns:
            User | None: User instance or None if not found
        """
        return await self.user_repo.get_by_username(username)

    async def update_user(
        self,
        user_id: PositiveInt,
        user_update: UserUpdate,
        current_user: User,
    ) -> User:
        """Update user with validation.

        Validates permissions and uniqueness constraints before updating.

        Args:
            user_id (PositiveInt): User ID to update
            user_update (UserUpdate): Update data
            current_user (User): Current authenticated user

        Returns:
            User: Updated user instance

        Raises:
            NotFoundException: If user not found
            ConflictException: If email or username conflicts
            AuthorizationException: If user lacks permission
        """
        from app.core.exceptions import AuthorizationException

        # Get user
        user = await self.get_user(user_id)

        # Check permissions (users can only update themselves unless superuser)
        if user.id != current_user.id and not current_user.is_superuser:
            raise AuthorizationException(
                message="You can only update your own profile",
                details={"user_id": user_id, "current_user_id": current_user.id},
            )

        # Validate email uniqueness if changing
        if user_update.email and user_update.email != user.email:
            existing_user = await self.user_repo.get_by_email(user_update.email)
            if existing_user:
                raise ConflictException(
                    message="Email already registered",
                    details={"email": user_update.email},
                )

        # Validate username uniqueness if changing
        if user_update.username and user_update.username != user.username:
            existing_user = await self.user_repo.get_by_username(user_update.username)
            if existing_user:
                raise ConflictException(
                    message="Username already taken",
                    details={"username": user_update.username},
                )

        # Hash password if provided
        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        # Update user
        updated_user = await self.user_repo.update(user, update_data)
        await self.commit()
        await self.refresh(updated_user)

        return updated_user

    async def delete_user(
        self,
        user_id: PositiveInt,
        current_user: User,
    ) -> None:
        """Delete user with validation.

        Only superusers can delete users. Performs cleanup of related data.

        Args:
            user_id (PositiveInt): User ID to delete
            current_user (User): Current authenticated user

        Raises:
            NotFoundException: If user not found
            AuthorizationException: If user is not superuser
        """
        from app.core.exceptions import AuthorizationException

        # Check permissions (only superusers can delete)
        if not current_user.is_superuser:
            raise AuthorizationException(
                message="Only superusers can delete users",
                details={"current_user_id": current_user.id},
            )

        # Get user
        user = await self.get_user(user_id)

        # Delete user (cascade will handle sessions)
        await self.user_repo.delete(user.id)
        await self.commit()

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
    ) -> list[User]:
        """List users with pagination.

        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            active_only (bool): Only return active users

        Returns:
            list[User]: List of users
        """
        if active_only:
            return await self.user_repo.get_active_users(skip=skip, limit=limit)
        return await self.user_repo.get_multi(skip=skip, limit=limit)

    async def activate_user(self, user_id: PositiveInt) -> User:
        """Activate user account.

        Args:
            user_id (PositiveInt): User ID

        Returns:
            User: Updated user instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user(user_id)
        user.is_active = True
        await self.commit()
        await self.refresh(user)
        return user

    async def deactivate_user(self, user_id: PositiveInt) -> User:
        """Deactivate user account.

        Args:
            user_id (PositiveInt): User ID

        Returns:
            User: Updated user instance

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user(user_id)
        user.is_active = False
        await self.commit()
        await self.refresh(user)
        return user

    async def get_user_with_permission_check(
        self,
        user_id: PositiveInt,
        current_user: User,
    ) -> User:
        """Get user by ID with permission check.

        Users can only view their own profile unless they're superuser.

        Args:
            user_id (PositiveInt): User ID to retrieve
            current_user (User): Current authenticated user

        Returns:
            User: User instance

        Raises:
            AuthorizationException: If user lacks permission
            NotFoundException: If user not found
        """
        from app.core.exceptions import AuthorizationException

        # Check permissions
        if user_id != current_user.id and not current_user.is_superuser:
            raise AuthorizationException(
                message="You can only view your own profile",
                details={"user_id": user_id, "current_user_id": current_user.id},
            )

        return await self.get_user(user_id)

    async def create_users_bulk(self, users_in: list[UserCreate]) -> list[User]:
        """Create multiple users in a single transaction.

        This method creates multiple users atomically - if any user creation
        fails, the entire transaction is rolled back and no users are created.
        Each user is validated individually for email and username uniqueness.

        Args:
            users_in (list[UserCreate]): List of user creation data

        Returns:
            list[User]: List of created user instances

        Raises:
            ConflictException: If any email or username already exists
            DatabaseException: If transaction fails
        """
        from app.core.exceptions import DatabaseException
        from sqlalchemy.exc import IntegrityError

        created_users: list[User] = []

        try:
            # Check for duplicates within the batch first
            emails_in_batch = [user.email for user in users_in]
            usernames_in_batch = [user.username for user in users_in]

            # Check for duplicate emails within batch
            if len(emails_in_batch) != len(set(emails_in_batch)):
                duplicate_emails = [
                    email for email in set(emails_in_batch) if emails_in_batch.count(email) > 1
                ]
                raise ConflictException(
                    message="Duplicate emails found within batch",
                    details={"duplicate_emails": duplicate_emails},
                )

            # Check for duplicate usernames within batch
            if len(usernames_in_batch) != len(set(usernames_in_batch)):
                duplicate_usernames = [
                    username
                    for username in set(usernames_in_batch)
                    if usernames_in_batch.count(username) > 1
                ]
                raise ConflictException(
                    message="Duplicate usernames found within batch",
                    details={"duplicate_usernames": duplicate_usernames},
                )

            # Create each user using the existing create_user logic
            # This ensures all validation and business rules are applied
            for user_in in users_in:
                # Check if email already exists in database
                existing_user = await self.user_repo.get_by_email(user_in.email)
                if existing_user:
                    raise ConflictException(
                        message="Email already registered",
                        details={"email": user_in.email},
                    )

                # Check if username already exists in database
                existing_user = await self.user_repo.get_by_username(user_in.username)
                if existing_user:
                    raise ConflictException(
                        message="Username already taken",
                        details={"username": user_in.username},
                    )

                # Hash password
                hashed_password = get_password_hash(user_in.password)

                # Create user model instance
                user_data = user_in.model_dump(exclude={"password"})
                user = User(
                    **user_data,
                    hashed_password=hashed_password,
                )

                self.user_repo.db.add(user)
                created_users.append(user)

            # Commit all users at once
            await self.commit()

            # Refresh all users to get their IDs and updated fields
            for user in created_users:
                await self.refresh(user)

            return created_users

        except ConflictException:
            # Re-raise conflict exceptions (validation errors)
            await self.rollback()
            raise
        except IntegrityError as e:
            # Handle database constraint violations
            await self.rollback()
            # Convert IntegrityError to ConflictException for consistency
            if "duplicate key value violates unique constraint" in str(e):
                if "ix_users_email" in str(e):
                    raise ConflictException(
                        message="Email already registered",
                        details={"error": "Database constraint violation on email"},
                    ) from e
                elif "ix_users_username" in str(e):
                    raise ConflictException(
                        message="Username already taken",
                        details={"error": "Database constraint violation on username"},
                    ) from e
            # Re-raise as DatabaseException if not a known constraint
            raise DatabaseException(
                message="Failed to create users in bulk",
                details={"error": str(e), "users_count": len(users_in)},
            ) from e
        except Exception as e:
            # Rollback transaction on any failure
            await self.rollback()
            raise DatabaseException(
                message="Failed to create users in bulk",
                details={"error": str(e), "users_count": len(users_in)},
            ) from e
