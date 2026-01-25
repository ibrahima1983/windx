"""Unit tests for BaseRepository methods.

Tests the new utility methods added to BaseRepository:
- get_by_field: Get record by any field name
- exists: Check if record exists by ID
- count: Count records with optional filters
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.base import BaseRepository


@pytest.mark.asyncio
class TestBaseRepositoryGetByField:
    """Test get_by_field method."""

    async def test_get_by_field_finds_existing_record(self, db_session: AsyncSession):
        """Test get_by_field returns record when it exists."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)
        unique_id = uuid.uuid4().hex[:8]
        user = User(
            email=f"test1_{unique_id}@example.com",
            username=f"testuser1_{unique_id}",
            hashed_password=get_password_hash("test_password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Act
        found = await repo.get_by_field("email", f"test1_{unique_id}@example.com")

        # Assert
        assert found is not None
        assert found.email == f"test1_{unique_id}@example.com"
        assert found.username == f"testuser1_{unique_id}"

    async def test_get_by_field_returns_none_when_not_found(self, db_session: AsyncSession):
        """Test get_by_field returns None when record doesn't exist."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act
        found = await repo.get_by_field("email", "nonexistent@example.com")

        # Assert
        assert found is None

    async def test_get_by_field_with_username(self, db_session: AsyncSession):
        """Test get_by_field works with different field names."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)
        unique_id = uuid.uuid4().hex[:8]
        user = User(
            email=f"test2_{unique_id}@example.com",
            username=f"uniqueuser2_{unique_id}",
            hashed_password=get_password_hash("test_password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Act
        found = await repo.get_by_field("username", f"uniqueuser2_{unique_id}")

        # Assert
        assert found is not None
        assert found.username == f"uniqueuser2_{unique_id}"

    async def test_get_by_field_raises_error_for_invalid_field(self, db_session: AsyncSession):
        """Test get_by_field raises ValueError for invalid field name."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid field name: nonexistent_field"):
            await repo.get_by_field("nonexistent_field", "value")


@pytest.mark.asyncio
class TestBaseRepositoryExists:
    """Test exists method."""

    async def test_exists_returns_true_for_existing_id(self, db_session: AsyncSession):
        """Test exists returns True when record exists."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)
        unique_id = uuid.uuid4().hex[:8]
        user = User(
            email=f"test3_{unique_id}@example.com",
            username=f"testuser3_{unique_id}",
            hashed_password=get_password_hash("test_password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Act
        result = await repo.exists(user.id)

        # Assert
        assert result is True

    async def test_exists_returns_false_for_nonexistent_id(self, db_session: AsyncSession):
        """Test exists returns False when record doesn't exist."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act
        result = await repo.exists(99999)

        # Assert
        assert result is False


@pytest.mark.asyncio
class TestBaseRepositoryCount:
    """Test count method."""

    async def test_count_returns_total_without_filters(self, db_session: AsyncSession):
        """Test count returns total count when no filters provided."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)

        # Get initial count
        initial_count = await repo.count()

        unique_id = uuid.uuid4().hex[:8]
        user1 = User(
            email=f"user4_{unique_id}@example.com",
            username=f"user4_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=True,
        )
        user2 = User(
            email=f"user5_{unique_id}@example.com",
            username=f"user5_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=False,
        )
        db_session.add_all([user1, user2])
        await db_session.commit()

        # Act
        final_count = await repo.count()

        # Assert - check that count increased by 2
        assert final_count == initial_count + 2

    async def test_count_with_single_filter(self, db_session: AsyncSession):
        """Test count returns correct count with single filter."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)

        # Get initial count of active users
        initial_active_count = await repo.count({"is_active": True})

        unique_id = uuid.uuid4().hex[:8]
        user1 = User(
            email=f"user6_{unique_id}@example.com",
            username=f"user6_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=True,
        )
        user2 = User(
            email=f"user7_{unique_id}@example.com",
            username=f"user7_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=False,
        )
        db_session.add_all([user1, user2])
        await db_session.commit()

        # Act
        final_active_count = await repo.count({"is_active": True})

        # Assert - check that active count increased by 1
        assert final_active_count == initial_active_count + 1

    async def test_count_with_multiple_filters(self, db_session: AsyncSession):
        """Test count returns correct count with multiple filters."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)

        # Get initial count of active superusers
        initial_count = await repo.count({"is_active": True, "is_superuser": True})

        unique_id = uuid.uuid4().hex[:8]
        user1 = User(
            email=f"user8_{unique_id}@example.com",
            username=f"user8_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=True,
            is_superuser=True,
        )
        user2 = User(
            email=f"user9_{unique_id}@example.com",
            username=f"user9_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=True,
            is_superuser=False,
        )
        user3 = User(
            email=f"user10_{unique_id}@example.com",
            username=f"user10_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=False,
            is_superuser=True,
        )
        db_session.add_all([user1, user2, user3])
        await db_session.commit()

        # Act
        final_count = await repo.count({"is_active": True, "is_superuser": True})

        # Assert - check that count increased by 1 (only user1 matches both filters)
        assert final_count == initial_count + 1

    async def test_count_returns_zero_when_no_matches(self, db_session: AsyncSession):
        """Test count returns 0 when no records match filters."""
        import uuid

        # Arrange
        repo = BaseRepository(User, db_session)
        unique_id = uuid.uuid4().hex[:8]

        # Create a user with a unique username pattern
        user = User(
            email=f"user11_{unique_id}@example.com",
            username=f"user11_{unique_id}",
            hashed_password=get_password_hash("test_password"),
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Act - search for a username that doesn't exist
        count = await repo.count({"username": f"nonexistent_{unique_id}"})

        # Assert
        assert count == 0

    async def test_count_raises_error_for_invalid_field(self, db_session: AsyncSession):
        """Test count raises ValueError for invalid field name."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid field name: nonexistent_field"):
            await repo.count({"nonexistent_field": "value"})
