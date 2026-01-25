"""Unit tests for TimeoutMiddleware.

This module tests the TimeoutMiddleware functionality including:
- Timeout enforcement
- Error response format
- Normal request handling
- Configuration

Features:
    - Timeout behavior testing
    - Error response validation
    - Performance testing
    - Edge case handling
"""

import asyncio

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.middleware import TimeoutMiddleware

pytestmark = pytest.mark.asyncio


@pytest.fixture
def timeout_app():
    """Create test FastAPI app with TimeoutMiddleware."""
    app = FastAPI()

    # Add timeout middleware with short timeout for testing
    # noinspection PyTypeChecker
    app.add_middleware(TimeoutMiddleware, timeout=1.0)

    @app.get("/fast")
    async def fast_endpoint():
        """Fast endpoint that completes quickly."""
        return {"message": "success"}

    @app.get("/slow")
    async def slow_endpoint():
        """Slow endpoint that exceeds timeout."""
        await asyncio.sleep(2.0)  # Sleep longer than timeout
        return {"message": "should not reach here"}

    @app.get("/medium")
    async def medium_endpoint():
        """Endpoint that takes time but within timeout."""
        await asyncio.sleep(0.5)  # Sleep less than timeout
        return {"message": "completed"}

    @app.get("/error")
    async def error_endpoint():
        """Endpoint that raises an error."""
        raise ValueError("Test error")

    return app


# noinspection PyTypeChecker
class TestTimeoutMiddleware:
    """Tests for TimeoutMiddleware functionality."""

    async def test_fast_request_completes(self, timeout_app):
        """Test that fast requests complete successfully."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/fast")

            assert response.status_code == 200
            assert response.json() == {"message": "success"}

    async def test_slow_request_times_out(self, timeout_app):
        """Test that slow requests timeout."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/slow")

            assert response.status_code == 504
            data = response.json()
            assert data["error"] == "request_timeout"
            assert "timeout" in data["message"].lower()
            assert "1.0" in data["message"]  # Timeout duration

    async def test_medium_request_completes(self, timeout_app):
        """Test that requests within timeout complete."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/medium")

            assert response.status_code == 200
            assert response.json() == {"message": "completed"}

    async def test_timeout_error_response_format(self, timeout_app):
        """Test that timeout error response has correct format."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/slow")

            assert response.status_code == 504
            data = response.json()

            # Verify error response structure
            assert "error" in data
            assert "message" in data
            assert "details" in data
            assert "request_id" in data

            # Verify error details
            assert data["error"] == "request_timeout"
            assert isinstance(data["details"], list)
            assert len(data["details"]) > 0

            # Verify detail structure
            detail = data["details"][0]
            assert "type" in detail
            assert "message" in detail
            assert detail["type"] == "request_timeout"

    async def test_timeout_includes_duration(self, timeout_app):
        """Test that timeout error includes timeout duration."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/slow")

            assert response.status_code == 504
            data = response.json()

            # Verify timeout duration is in message
            assert "1.0" in data["message"]
            assert "timeout" in data["message"].lower()

    async def test_timeout_includes_request_id(self, timeout_app):
        """Test that timeout error includes request ID."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/slow")

            assert response.status_code == 504
            data = response.json()

            # Verify request_id exists
            assert "request_id" in data
            # In tests without RequestIDMiddleware, it will be "unknown"
            assert isinstance(data["request_id"], str)

    async def test_custom_timeout_configuration(self):
        """Test TimeoutMiddleware with custom timeout."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=0.5)

        @app.get("/test")
        async def test_endpoint():
            await asyncio.sleep(0.7)  # Longer than custom timeout
            return {"message": "should timeout"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

            assert response.status_code == 504
            data = response.json()
            assert "0.5" in data["message"]  # Custom timeout duration

    async def test_default_timeout_configuration(self):
        """Test TimeoutMiddleware with default timeout."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware)  # Use default timeout

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

            assert response.status_code == 200

    async def test_multiple_fast_requests(self, timeout_app):
        """Test that multiple fast requests all complete."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            # Make 10 fast requests
            responses = []
            for _ in range(10):
                response = await client.get("/fast")
                responses.append(response)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                assert response.json() == {"message": "success"}

    async def test_multiple_slow_requests(self, timeout_app):
        """Test that multiple slow requests all timeout."""
        async with AsyncClient(
            transport=ASGITransport(app=timeout_app),
            base_url="http://test",
        ) as client:
            # Make 3 slow requests (fewer to keep test fast)
            responses = []
            for _ in range(3):
                response = await client.get("/slow")
                responses.append(response)

            # All should timeout
            for response in responses:
                assert response.status_code == 504
                assert response.json()["error"] == "request_timeout"

    async def test_timeout_with_post_request(self):
        """Test timeout works with POST requests."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=1.0)

        @app.post("/slow-post")
        async def slow_post_endpoint(data: dict):
            await asyncio.sleep(2.0)
            return {"message": "should timeout"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/slow-post", json={"test": "data"})

            assert response.status_code == 504
            assert response.json()["error"] == "request_timeout"

    async def test_timeout_boundary_condition(self):
        """Test request that completes right at timeout boundary."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=1.0)

        @app.get("/boundary")
        async def boundary_endpoint():
            # Sleep for slightly less than timeout
            await asyncio.sleep(0.95)
            return {"message": "completed"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/boundary")

            # Should complete successfully
            assert response.status_code == 200
            assert response.json() == {"message": "completed"}

    async def test_timeout_preserves_other_middleware(self):
        """Test that timeout middleware works with other middleware."""
        from starlette.middleware.base import BaseHTTPMiddleware

        class TestMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                response = await call_next(request)
                response.headers["X-Test"] = "value"
                return response

        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=1.0)
        app.add_middleware(TestMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

            assert response.status_code == 200
            assert response.headers["X-Test"] == "value"

    async def test_very_long_timeout(self):
        """Test middleware with very long timeout."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=300.0)  # 5 minutes

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

            assert response.status_code == 200

    async def test_very_short_timeout(self):
        """Test middleware with very short timeout."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=0.1)  # 100ms

        @app.get("/test")
        async def test_endpoint():
            await asyncio.sleep(0.2)  # 200ms
            return {"message": "should timeout"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

            assert response.status_code == 504
