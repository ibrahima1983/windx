"""Integration tests for enhanced health check endpoint.

This module tests the enhanced health check endpoint with focus on:
- Database connectivity verification
- Redis cache connectivity verification
- Redis rate limiter connectivity verification
- Overall health status determination
- Error handling and reporting

Features:
    - Full dependency verification testing
    - Failure scenario testing
    - Response format validation
    - Service availability testing
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthCheckEndpoint:
    """Tests for GET /health endpoint."""

    async def test_health_check_all_services_healthy(
        self,
        client: AsyncClient,
        test_settings,
    ):
        """Test health check when all services are healthy."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "app_name" in data
        assert "version" in data
        assert "checks" in data

        # Verify overall status
        assert data["status"] == "healthy"

        # Verify app info
        assert data["app_name"] == test_settings.app_name
        assert data["version"] == test_settings.app_version

        # Verify checks structure
        checks = data["checks"]
        assert "database" in checks

        # Database check should be healthy
        assert checks["database"]["status"] == "healthy"
        assert "provider" in checks["database"]
        assert checks["database"]["provider"] in ["supabase", "postgresql"]

    async def test_health_check_response_format(
        self,
        client: AsyncClient,
    ):
        """Test that health check response has correct format."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify required top-level fields
        required_fields = ["status", "app_name", "version", "checks"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify checks is a dict
        assert isinstance(data["checks"], dict)

        # Verify database check structure
        db_check = data["checks"]["database"]
        assert "status" in db_check
        assert "provider" in db_check

    async def test_health_check_database_connectivity(
        self,
        client: AsyncClient,
    ):
        """Test that health check verifies database connectivity."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Database should be checked
        assert "database" in data["checks"]
        db_check = data["checks"]["database"]

        # Should have status and provider
        assert db_check["status"] == "healthy"
        assert db_check["provider"] in ["supabase", "postgresql"]

        # Should not have error field when healthy
        assert "error" not in db_check

    async def test_health_check_with_database_failure(
        self,
        client: AsyncClient,
    ):
        """Test health check when database connection fails."""
        # Mock database execute to raise exception
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")

            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"

            # Database check should show failure
            db_check = data["checks"]["database"]
            assert db_check["status"] == "unhealthy"
            assert "error" in db_check
            assert "Database connection failed" in db_check["error"]

    @pytest.mark.redis
    async def test_health_check_cache_when_enabled(
        self,
        client: AsyncClient,
        redis_test_settings,
    ):
        """Test health check includes cache check when cache is enabled."""
        # Only run if cache is enabled in test settings
        if not redis_test_settings.cache.enabled:
            pytest.skip("Cache not enabled in test settings")

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Cache check should be present
        assert "cache" in data["checks"]
        cache_check = data["checks"]["cache"]

        # Should have status
        assert "status" in cache_check
        # In tests, cache uses in-memory backend, so should be healthy
        assert cache_check["status"] == "healthy"

    @pytest.mark.redis
    async def test_health_check_rate_limiter_when_enabled(
        self,
        client: AsyncClient,
        redis_test_settings,
    ):
        """Test health check includes rate limiter check when enabled."""
        # Only run if rate limiter is enabled in test settings
        if not redis_test_settings.limiter.enabled:
            pytest.skip("Rate limiter not enabled in test settings")

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Rate limiter check should be present
        assert "rate_limiter" in data["checks"]
        limiter_check = data["checks"]["rate_limiter"]

        # Should have status
        assert "status" in limiter_check

    @pytest.mark.redis
    async def test_health_check_redis_cache_failure(
        self,
        client: AsyncClient,
        redis_test_settings,
    ):
        """Test health check when Redis cache connection fails."""
        # Only run if cache is enabled
        if not redis_test_settings.cache.enabled:
            pytest.skip("Cache not enabled in test settings")

        # Mock Redis ping to fail
        with patch("redis.asyncio.Redis.ping") as mock_ping:
            mock_ping.side_effect = Exception("Redis connection failed")

            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"

            # Cache check should show failure
            if "cache" in data["checks"]:
                cache_check = data["checks"]["cache"]
                assert cache_check["status"] == "unhealthy"
                assert "error" in cache_check

    @pytest.mark.redis
    async def test_health_check_redis_limiter_failure(
        self,
        client: AsyncClient,
        redis_test_settings,
    ):
        """Test health check when Redis rate limiter connection fails."""
        # Only run if rate limiter is enabled
        if not redis_test_settings.limiter.enabled:
            pytest.skip("Rate limiter not enabled in test settings")

        # Mock Redis ping to fail
        with patch("redis.asyncio.Redis.ping") as mock_ping:
            mock_ping.side_effect = Exception("Redis connection failed")

            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"

            # Rate limiter check should show failure
            if "rate_limiter" in data["checks"]:
                limiter_check = data["checks"]["rate_limiter"]
                assert limiter_check["status"] == "unhealthy"
                assert "error" in limiter_check

    async def test_health_check_multiple_failures(
        self,
        client: AsyncClient,
    ):
        """Test health check when multiple services fail."""
        # Mock both database and Redis to fail
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_db:
            mock_db.side_effect = Exception("Database failed")

            with patch("redis.asyncio.Redis.ping") as mock_redis:
                mock_redis.side_effect = Exception("Redis failed")

                response = await client.get("/health")

                assert response.status_code == 200
                data = response.json()

                # Overall status should be unhealthy
                assert data["status"] == "unhealthy"

                # Database should show failure
                db_check = data["checks"]["database"]
                assert db_check["status"] == "unhealthy"
                assert "error" in db_check

    async def test_health_check_no_authentication_required(
        self,
        client: AsyncClient,
    ):
        """Test that health check does not require authentication."""
        # Call without any auth headers
        response = await client.get("/health")

        # Should succeed without authentication
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    async def test_health_check_idempotent(
        self,
        client: AsyncClient,
        test_settings,
    ):
        """Test that health check is idempotent."""
        # Call multiple times
        responses = []
        for _ in range(3):
            response = await client.get("/health")
            assert response.status_code == 200
            responses.append(response.json())

        # All responses should have same structure
        for resp in responses:
            assert resp["status"] == "healthy"
            assert resp["app_name"] == test_settings.app_name
            assert "database" in resp["checks"]

    @pytest.mark.redis
    async def test_health_check_redis_connection_cleanup(
        self,
        client: AsyncClient,
        redis_test_settings,
    ):
        """Test that health check properly closes Redis connections."""
        # Only run if cache or limiter is enabled
        if not (redis_test_settings.cache.enabled or redis_test_settings.limiter.enabled):
            pytest.skip("Neither cache nor limiter enabled")

        # Mock Redis client to track close calls
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis

            response = await client.get("/health")

            assert response.status_code == 200

            # Verify close was called on Redis clients
            # Should be called at least once (for cache or limiter)
            assert mock_redis.close.called

    async def test_health_check_performance(
        self,
        client: AsyncClient,
    ):
        """Test that health check responds quickly."""
        import time

        start_time = time.time()
        response = await client.get("/health")
        response_time = time.time() - start_time

        assert response.status_code == 200

        # Health check should be fast (< 1 second)
        assert response_time < 1.0, f"Health check took {response_time}s"

    async def test_health_check_consistent_format(
        self,
        client: AsyncClient,
    ):
        """Test that health check always returns consistent format."""
        # Call multiple times
        for _ in range(5):
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Verify consistent structure
            assert isinstance(data["status"], str)
            assert isinstance(data["app_name"], str)
            assert isinstance(data["version"], str)
            assert isinstance(data["checks"], dict)

            # Verify status is valid
            assert data["status"] in ["healthy", "unhealthy"]

            # Verify checks have proper structure
            for _check_name, check_data in data["checks"].items():
                assert isinstance(check_data, dict)
                assert "status" in check_data
                assert check_data["status"] in ["healthy", "unhealthy"]
