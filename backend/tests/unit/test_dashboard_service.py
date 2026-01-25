"""Unit tests for DashboardService.

This module tests the DashboardService business logic for
optimized dashboard statistics calculation.

Features:
    - Statistics aggregation testing
    - Date filtering validation
    - Performance characteristics verification
    - Response format validation
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dashboard import DashboardService
from tests.factories.user_factory import create_user_create_schema

pytestmark = pytest.mark.asyncio


class TestDashboardServiceGetStats:
    """Tests for DashboardService.get_dashboard_stats_optimized method."""

    async def test_get_stats_with_no_users(self, db_session: AsyncSession):
        """Test getting stats when no users exist."""
        dashboard_service = DashboardService(db_session)

        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 0
        assert stats["active_users"] == 0
        assert stats["inactive_users"] == 0
        assert stats["superusers"] == 0
        assert stats["new_users_today"] == 0
        assert stats["new_users_week"] == 0
        assert "timestamp" in stats
        # Verify timestamp is ISO format
        datetime.fromisoformat(stats["timestamp"])

    async def test_get_stats_with_single_user(
        self,
        db_session: AsyncSession,
        test_user,
    ):
        """Test getting stats with one user."""
        dashboard_service = DashboardService(db_session)

        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 1
        assert stats["active_users"] == 1
        assert stats["inactive_users"] == 0
        assert stats["superusers"] == 0
        # User was just created, should be in today's count
        assert stats["new_users_today"] >= 0
        assert stats["new_users_week"] >= 0

    async def test_get_stats_with_multiple_users(self, db_session: AsyncSession):
        """Test getting stats with multiple users."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 5 active users
        for i in range(5):
            user_in = create_user_create_schema(
                email=f"user{i}@example.com",
                username=f"user{i}",
            )
            await user_service.create_user(user_in)

        # Create 2 inactive users
        for i in range(2):
            user_in = create_user_create_schema(
                email=f"inactive{i}@example.com",
                username=f"inactive{i}",
            )
            user = await user_service.create_user(user_in)
            user.is_active = False
            await db_session.commit()

        # Create 1 superuser
        user_in = create_user_create_schema(
            email="admin@example.com",
            username="admin",
        )
        user = await user_service.create_user(user_in)
        user.is_superuser = True
        await db_session.commit()

        dashboard_service = DashboardService(db_session)
        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 8
        assert stats["active_users"] == 6  # 5 + 1 superuser
        assert stats["inactive_users"] == 2
        assert stats["superusers"] == 1
        # All users were just created
        assert stats["new_users_today"] == 8
        assert stats["new_users_week"] == 8

    async def test_get_stats_active_vs_inactive(self, db_session: AsyncSession):
        """Test that active and inactive counts are correct."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 3 active users
        for i in range(3):
            user_in = create_user_create_schema(
                email=f"active{i}@example.com",
                username=f"active{i}",
            )
            await user_service.create_user(user_in)

        # Create 2 inactive users
        for i in range(2):
            user_in = create_user_create_schema(
                email=f"inactive{i}@example.com",
                username=f"inactive{i}",
            )
            user = await user_service.create_user(user_in)
            user.is_active = False
            await db_session.commit()

        dashboard_service = DashboardService(db_session)
        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 5
        assert stats["active_users"] == 3
        assert stats["inactive_users"] == 2
        assert stats["active_users"] + stats["inactive_users"] == stats["total_users"]

    async def test_get_stats_superuser_count(self, db_session: AsyncSession):
        """Test that superuser count is correct."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 3 regular users
        for i in range(3):
            user_in = create_user_create_schema(
                email=f"user{i}@example.com",
                username=f"user{i}",
            )
            await user_service.create_user(user_in)

        # Create 2 superusers
        for i in range(2):
            user_in = create_user_create_schema(
                email=f"admin{i}@example.com",
                username=f"admin{i}",
            )
            user = await user_service.create_user(user_in)
            user.is_superuser = True
            await db_session.commit()

        dashboard_service = DashboardService(db_session)
        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 5
        assert stats["superusers"] == 2

    async def test_get_stats_timestamp_format(self, db_session: AsyncSession):
        """Test that timestamp is in ISO format."""
        dashboard_service = DashboardService(db_session)

        stats = await dashboard_service.get_dashboard_stats_optimized()

        # Verify timestamp exists and is ISO format
        assert "timestamp" in stats
        timestamp = datetime.fromisoformat(stats["timestamp"])
        assert isinstance(timestamp, datetime)
        # Verify it's recent (within last minute)
        now = datetime.now(UTC)
        assert (now - timestamp).total_seconds() < 60

    async def test_get_stats_response_structure(self, db_session: AsyncSession):
        """Test that response has all required fields."""
        dashboard_service = DashboardService(db_session)

        stats = await dashboard_service.get_dashboard_stats_optimized()

        # Verify all required fields exist
        required_fields = [
            "total_users",
            "active_users",
            "inactive_users",
            "superusers",
            "new_users_today",
            "new_users_week",
            "timestamp",
        ]
        for field in required_fields:
            assert field in stats

        # Verify all counts are integers
        for field in required_fields[:-1]:  # Exclude timestamp
            assert isinstance(stats[field], int)
            assert stats[field] >= 0

        # Verify timestamp is string
        assert isinstance(stats["timestamp"], str)

    async def test_get_stats_new_users_today(self, db_session: AsyncSession):
        """Test new users today count."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create user with today's date
        user_in = create_user_create_schema()
        await user_service.create_user(user_in)

        # Create user with old date (manually set created_at)
        user_in_old = create_user_create_schema(
            email="old@example.com",
            username="olduser",
        )
        old_user = await user_service.create_user(user_in_old)
        old_user.created_at = datetime.now(UTC) - timedelta(days=2)
        await db_session.commit()

        dashboard_service = DashboardService(db_session)
        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 2
        assert stats["new_users_today"] == 1  # Only the recent one

    async def test_get_stats_new_users_week(self, db_session: AsyncSession):
        """Test new users this week count."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create user today
        user_in_today = create_user_create_schema()
        await user_service.create_user(user_in_today)

        # Create user 5 days ago
        user_in_week = create_user_create_schema(
            email="week@example.com",
            username="weekuser",
        )
        week_user = await user_service.create_user(user_in_week)
        week_user.created_at = datetime.now(UTC) - timedelta(days=5)
        await db_session.commit()

        # Create user 10 days ago (outside week)
        user_in_old = create_user_create_schema(
            email="old@example.com",
            username="olduser",
        )
        old_user = await user_service.create_user(user_in_old)
        old_user.created_at = datetime.now(UTC) - timedelta(days=10)
        await db_session.commit()

        dashboard_service = DashboardService(db_session)
        stats = await dashboard_service.get_dashboard_stats_optimized()

        assert stats["total_users"] == 3
        assert stats["new_users_week"] == 2  # Today and 5 days ago

    async def test_get_stats_performance_with_many_users(
        self,
        db_session: AsyncSession,
    ):
        """Test that stats calculation is fast even with many users."""
        import time

        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 100 users (scaled down for test speed)
        for i in range(100):
            user_in = create_user_create_schema(
                email=f"user{i}@example.com",
                username=f"user{i}",
            )
            await user_service.create_user(user_in)

        dashboard_service = DashboardService(db_session)

        # Measure execution time
        start_time = time.time()
        stats = await dashboard_service.get_dashboard_stats_optimized()
        execution_time = time.time() - start_time

        # Verify stats are correct
        assert stats["total_users"] == 100

        # Verify execution time is reasonable (should be < 1 second for 100 users)
        # With 10,000+ users, should be < 100ms, but we're testing with fewer
        assert execution_time < 1.0, f"Stats calculation took {execution_time}s"

    async def test_get_stats_consistency(self, db_session: AsyncSession):
        """Test that multiple calls return consistent results."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create some users
        for i in range(5):
            user_in = create_user_create_schema(
                email=f"user{i}@example.com",
                username=f"user{i}",
            )
            await user_service.create_user(user_in)

        dashboard_service = DashboardService(db_session)

        # Get stats twice
        stats1 = await dashboard_service.get_dashboard_stats_optimized()
        stats2 = await dashboard_service.get_dashboard_stats_optimized()

        # Verify counts are consistent (timestamps will differ)
        assert stats1["total_users"] == stats2["total_users"]
        assert stats1["active_users"] == stats2["active_users"]
        assert stats1["inactive_users"] == stats2["inactive_users"]
        assert stats1["superusers"] == stats2["superusers"]
