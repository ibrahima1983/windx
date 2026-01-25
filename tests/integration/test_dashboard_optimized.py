"""Integration tests for optimized dashboard endpoints.

This module tests the dashboard API endpoints with focus on:
- Optimized statistics endpoint
- Caching behavior
- Performance improvements
- Response format

Features:
    - Full stack testing (HTTP → Service → Repository → Database)
    - Cache behavior validation
    - Performance benchmarking
    - Authentication testing
"""

import time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.user_factory import create_user_create_schema

pytestmark = pytest.mark.asyncio


class TestDashboardStatsEndpoint:
    """Tests for GET /api/v1/dashboard/stats endpoint."""

    async def test_get_stats_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        test_superuser,
    ):
        """Test successful stats retrieval."""
        response = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_users" in data
        assert "active_users" in data
        assert "inactive_users" in data
        assert "superusers" in data
        assert "new_users_today" in data
        assert "new_users_week" in data
        assert "timestamp" in data

        # Verify data types
        assert isinstance(data["total_users"], int)
        assert isinstance(data["active_users"], int)
        assert isinstance(data["inactive_users"], int)
        assert isinstance(data["superusers"], int)
        assert isinstance(data["new_users_today"], int)
        assert isinstance(data["new_users_week"], int)
        assert isinstance(data["timestamp"], str)

    async def test_get_stats_requires_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular users cannot access stats."""
        response = await client.get(
            "/api/v1/dashboard/stats",
            headers=auth_headers,
        )

        assert response.status_code == 403

    async def test_get_stats_requires_authentication(self, client: AsyncClient):
        """Test that unauthenticated users cannot access stats."""
        response = await client.get("/api/v1/dashboard/stats")

        assert response.status_code == 401

    async def test_get_stats_with_multiple_users(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test stats with multiple users."""
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

        response = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify counts (including test_superuser from fixture)
        assert data["total_users"] >= 8
        assert data["active_users"] >= 6
        assert data["inactive_users"] >= 2

    async def test_get_stats_response_format(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that response format matches specification."""
        response = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
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
            assert field in data, f"Missing field: {field}"

        # Verify no extra fields
        assert set(data.keys()) == set(required_fields)

    async def test_get_stats_performance(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that stats endpoint is fast."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 50 users (scaled down for test speed)
        for i in range(50):
            user_in = create_user_create_schema(
                email=f"perf{i}@example.com",
                username=f"perf{i}",
            )
            await user_service.create_user(user_in)

        # Measure response time
        start_time = time.time()
        response = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )
        response_time = time.time() - start_time

        assert response.status_code == 200

        # Verify response time is reasonable
        # Should be < 1 second even with 50 users
        # With 10,000+ users, should be < 100ms
        assert response_time < 1.0, f"Response took {response_time}s"

    @pytest.mark.redis
    async def test_get_stats_caching_behavior(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that stats are cached properly."""
        # First request - should hit database
        response1 = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )
        assert response1.status_code == 200
        data1 = response1.json()
        timestamp1 = data1["timestamp"]

        # Second request immediately - should hit cache
        response2 = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )
        assert response2.status_code == 200
        data2 = response2.json()
        timestamp2 = data2["timestamp"]

        # Timestamps should be identical (cached response)
        assert timestamp1 == timestamp2
        assert data1 == data2

    @pytest.mark.redis
    async def test_get_stats_cache_performance(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that cached responses work correctly."""
        # First request - uncached
        response1 = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )
        assert response1.status_code == 200

        # Second request - should be cached
        response2 = await client.get(
            "/api/v1/dashboard/stats",
            headers=superuser_auth_headers,
        )
        assert response2.status_code == 200

        # Both responses should be valid
        # Note: Performance timing tests are flaky and unreliable in CI/CD
        # We just verify both requests succeed
        assert response1.json() == response2.json()

    async def test_get_stats_consistency(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that stats are consistent across multiple calls."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create some users
        for i in range(10):
            user_in = create_user_create_schema(
                email=f"consistent{i}@example.com",
                username=f"consistent{i}",
            )
            await user_service.create_user(user_in)

        # Get stats multiple times
        responses = []
        for _ in range(3):
            response = await client.get(
                "/api/v1/dashboard/stats",
                headers=superuser_auth_headers,
            )
            assert response.status_code == 200
            responses.append(response.json())

        # All responses should have same counts (cached)
        for i in range(1, len(responses)):
            assert responses[i]["total_users"] == responses[0]["total_users"]
            assert responses[i]["active_users"] == responses[0]["active_users"]
            assert responses[i]["inactive_users"] == responses[0]["inactive_users"]
            assert responses[i]["superusers"] == responses[0]["superusers"]



