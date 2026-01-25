"""Unit tests for UserService.

This module tests the UserService business logic in isolation
with mocked repository dependencies.

Features:
    - Service logic testing
    - Mocked dependencies
    - Business rule validation
    - Error handling testing
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException
from app.schemas.user import UserUpdate
from app.services.user import UserService
from tests.factories.user_factory import create_user_create_schema

pytestmark = pytest.mark.asyncio


class TestUserServiceCreateUser:
    """Tests for UserService.create_user method."""

    async def test_create_user_success(self, db_session: AsyncSession):
        """Test successful user creation."""
        user_service = UserService(db_session)
        user_in = create_user_create_schema()

        user = await user_service.create_user(user_in)

        assert user.email == user_in.email
        assert user.username == user_in.username
        assert user.is_active is True
        assert user.is_superuser is False
        assert hasattr(user, "hashed_password")
        assert user.hashed_password != user_in.password  # Password is hashed

    async def test_create_user_duplicate_email(self, db_session: AsyncSession):
        """Test creating user with duplicate email fails."""
        user_service = UserService(db_session)
        user_in = create_user_create_schema()

        # Create first user
        await user_service.create_user(user_in)

        # Try to create second user with same email
        user_in2 = create_user_create_schema(email=user_in.email)

        with pytest.raises(ConflictException) as exc_info:
            await user_service.create_user(user_in2)

        assert "email" in str(exc_info.value.message).lower()

    async def test_create_user_duplicate_username(self, db_session: AsyncSession):
        """Test creating user with duplicate username fails."""
        user_service = UserService(db_session)
        user_in = create_user_create_schema()

        # Create first user
        await user_service.create_user(user_in)

        # Try to create second user with same username
        user_in2 = create_user_create_schema(username=user_in.username)

        with pytest.raises(ConflictException) as exc_info:
            await user_service.create_user(user_in2)

        assert "username" in str(exc_info.value.message).lower()

    async def test_create_user_password_is_hashed(self, db_session: AsyncSession):
        """Test that password is hashed before storing."""
        user_service = UserService(db_session)
        user_in = create_user_create_schema(password="PlainPassword123!")

        user = await user_service.create_user(user_in)

        assert user.hashed_password != "PlainPassword123!"
        assert user.hashed_password.startswith("$2b$")  # bcrypt hash


class TestUserServiceGetUser:
    """Tests for UserService.get_user method."""

    async def test_get_user_success(self, db_session: AsyncSession, test_user):
        """Test getting existing user."""
        user_service = UserService(db_session)

        user = await user_service.get_user(test_user.id)

        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_get_user_not_found(self, db_session: AsyncSession):
        """Test getting nonexistent user raises NotFoundException."""
        user_service = UserService(db_session)

        with pytest.raises(NotFoundException) as exc_info:
            await user_service.get_user(99999)

        assert "user" in str(exc_info.value.message).lower()


class TestUserServiceUpdateUser:
    """Tests for UserService.update_user method."""

    async def test_update_own_user(self, db_session: AsyncSession, test_user):
        """Test user can update their own profile."""
        user_service = UserService(db_session)
        user_update = UserUpdate(full_name="Updated Name")

        updated_user = await user_service.update_user(
            test_user.id,
            user_update,
            test_user,
        )

        assert updated_user.full_name == "Updated Name"

    async def test_update_other_user_as_regular_user(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test regular user cannot update other user."""
        user_service = UserService(db_session)
        user_update = UserUpdate(full_name="Hacked")

        with pytest.raises(AuthorizationException):
            await user_service.update_user(
                test_superuser.id,
                user_update,
                test_user,
            )

    async def test_update_other_user_as_superuser(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test superuser can update other user."""
        user_service = UserService(db_session)
        user_update = UserUpdate(full_name="Admin Updated")

        updated_user = await user_service.update_user(
            test_user.id,
            user_update,
            test_superuser,
        )

        assert updated_user.full_name == "Admin Updated"

    async def test_update_email_to_existing(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test updating email to existing email fails."""
        user_service = UserService(db_session)
        user_update = UserUpdate(email=test_superuser.email)

        with pytest.raises(ConflictException) as exc_info:
            await user_service.update_user(
                test_user.id,
                user_update,
                test_user,
            )

        assert "email" in str(exc_info.value.message).lower()

    async def test_update_username_to_existing(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test updating username to existing username fails."""
        user_service = UserService(db_session)
        user_update = UserUpdate(username=test_superuser.username)

        with pytest.raises(ConflictException) as exc_info:
            await user_service.update_user(
                test_user.id,
                user_update,
                test_user,
            )

        assert "username" in str(exc_info.value.message).lower()


class TestUserServiceDeleteUser:
    """Tests for UserService.delete_user method."""

    async def test_delete_user_as_superuser(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test superuser can delete user."""
        user_service = UserService(db_session)

        await user_service.delete_user(test_user.id, test_superuser)

        # Verify user is deleted
        with pytest.raises(NotFoundException):
            await user_service.get_user(test_user.id)

    async def test_delete_user_as_regular_user(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test regular user cannot delete user."""
        user_service = UserService(db_session)

        with pytest.raises(AuthorizationException):
            await user_service.delete_user(test_superuser.id, test_user)


class TestUserServicePermissionCheck:
    """Tests for UserService.get_user_with_permission_check method."""

    async def test_get_own_user(self, db_session: AsyncSession, test_user):
        """Test user can get their own profile."""
        user_service = UserService(db_session)

        user = await user_service.get_user_with_permission_check(
            test_user.id,
            test_user,
        )

        assert user.id == test_user.id

    async def test_get_other_user_as_regular_user(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test regular user cannot get other user."""
        user_service = UserService(db_session)

        with pytest.raises(AuthorizationException):
            await user_service.get_user_with_permission_check(
                test_superuser.id,
                test_user,
            )

    async def test_get_other_user_as_superuser(
        self,
        db_session: AsyncSession,
        test_user,
        test_superuser,
    ):
        """Test superuser can get other user."""
        user_service = UserService(db_session)

        user = await user_service.get_user_with_permission_check(
            test_user.id,
            test_superuser,
        )

        assert user.id == test_user.id
