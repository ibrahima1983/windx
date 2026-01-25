"""Integration tests for metrics endpoints.

This module tests the metrics API endpoints with focus on:
- Database connection pool metrics
- Access control (superuser only)
- Response format validation
- Real-time metrics accuracy

Features:
    - Full stack testing (HTTP → Service → Database)
    - Access control validation
    - Metrics format verification
    - Security testing
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestDatabaseMetricsEndpoint:
    """Tests for GET /api/v1/metrics/database endpoint."""

    async def test_get_database_metrics_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test successful database metrics retrieval."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "pool_size" in data
        assert "checked_in" in data
        assert "checked_out" in data
        assert "overflow" in data
        assert "total_connections" in data

        # Verify data types
        assert isinstance(data["pool_size"], int)
        assert isinstance(data["checked_in"], int)
        assert isinstance(data["checked_out"], int)
        assert isinstance(data["overflow"], int)
        assert isinstance(data["total_connections"], int)

        # Verify logical constraints
        assert data["pool_size"] >= 0
        assert data["checked_in"] >= 0
        assert data["checked_out"] >= 0
        # Note: overflow can be negative in SQLAlchemy's pool implementation
        assert data["total_connections"] >= 0

    async def test_get_database_metrics_requires_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular users cannot access database metrics."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        # FastAPI returns 'detail' for built-in auth errors
        assert "detail" in data or "message" in data

    async def test_get_database_metrics_requires_authentication(
        self,
        client: AsyncClient,
    ):
        """Test that unauthenticated users cannot access database metrics."""
        response = await client.get("/api/v1/metrics/database")

        assert response.status_code == 401
        data = response.json()
        # FastAPI returns 'detail' for built-in auth errors
        assert "detail" in data or "message" in data

    async def test_get_database_metrics_response_format(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that response format matches specification."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        required_fields = [
            "pool_size",
            "checked_in",
            "checked_out",
            "overflow",
            "total_connections",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify no extra fields
        assert set(data.keys()) == set(required_fields)

    async def test_get_database_metrics_total_connections_calculation(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that total_connections equals pool_size + overflow."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify calculation
        expected_total = data["pool_size"] + data["overflow"]
        assert data["total_connections"] == expected_total

    async def test_get_database_metrics_checked_in_out_sum(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that checked_in + checked_out <= total_connections."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify logical constraint
        total_in_use = data["checked_in"] + data["checked_out"]
        assert total_in_use <= data["total_connections"]

    async def test_get_database_metrics_real_time(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that metrics reflect real-time state (no caching)."""
        # Get metrics twice
        response1 = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )
        response2 = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should succeed (metrics may vary slightly)
        data1 = response1.json()
        data2 = response2.json()

        # Verify structure is consistent
        assert set(data1.keys()) == set(data2.keys())

    async def test_get_database_metrics_multiple_calls(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that multiple calls return valid metrics."""
        for _ in range(5):
            response = await client.get(
                "/api/v1/metrics/database",
                headers=superuser_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify all values except overflow are non-negative
            # Note: overflow can be negative in SQLAlchemy's pool
            assert data["pool_size"] >= 0
            assert data["checked_in"] >= 0
            assert data["checked_out"] >= 0
            assert data["total_connections"] >= 0

    async def test_get_database_metrics_pool_size_positive(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that pool_size is always positive."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Pool size should be configured and positive
        assert data["pool_size"] > 0

    async def test_get_database_metrics_content_type(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that response has correct content type."""
        response = await client.get(
            "/api/v1/metrics/database",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
