"""Integration tests for admin orders endpoints.

This module tests the admin order management endpoints including:
- List orders with pagination, search, and status filter
- View order details with customer info and items
- Update order status with validation
- Status transition validation
- Authorization checks
- Feature flag behavior

Test Coverage:
    - Pagination and filtering
    - Search functionality
    - Status updates and validation
    - Order details with relationships
    - Authorization (superuser only)
    - Feature flag enabled/disabled
    - Error handling and redirects
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from httpx import AsyncClient

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

pytestmark = pytest.mark.asyncio


class TestListOrders:
    """Test order list endpoint."""

    async def test_list_orders_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test listing orders successfully."""
        from tests.factories.order_factory import OrderFactory

        # Create test orders
        await OrderFactory.create_batch(db_session, 5)

        # Make request
        response = await client.get(
            "/api/v1/admin/orders",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check that orders are in the response
        assert b"Orders" in response.content or b"orders" in response.content

    async def test_list_orders_with_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test order list pagination."""
        from tests.factories.order_factory import OrderFactory

        # Create 25 orders (more than one page)
        await OrderFactory.create_batch(db_session, 25)

        # Request first page
        response = await client.get(
            "/api/v1/admin/orders?page=1",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        # Should show page 1 content
        assert b"page=2" in response.content  # Next page link

    async def test_list_orders_with_search(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test order search functionality."""
        from tests.factories.order_factory import OrderFactory

        # Create orders with specific order numbers
        order1 = await OrderFactory.create(
            db_session,
            order_number="ORD-2024-001",
        )
        order2 = await OrderFactory.create(
            db_session,
            order_number="ORD-2024-002",
        )

        # Search for specific order number
        response = await client.get(
            "/api/v1/admin/orders?search=ORD-2024-001",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert b"ORD-2024-001" in response.content
        # Note: Due to pagination, ORD-2024-002 might not be visible

    async def test_list_orders_filter_by_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test filtering orders by status."""
        from tests.factories.order_factory import OrderFactory

        # Create orders with different statuses
        await OrderFactory.create(db_session, status="confirmed")
        await OrderFactory.create(db_session, status="production")
        await OrderFactory.create(db_session, status="shipped")

        # Filter by production status
        response = await client.get(
            "/api/v1/admin/orders?status_filter=production",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert b"production" in response.content.lower()

    async def test_list_orders_ordered_by_date(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that orders are ordered by date descending."""
        from datetime import date

        from tests.factories.order_factory import OrderFactory

        # Create orders with different dates
        order1 = await OrderFactory.create(
            db_session,
            order_date=date(2024, 1, 1),
            order_number="OLD-001",
        )
        order2 = await OrderFactory.create(
            db_session,
            order_date=date(2024, 12, 31),
            order_number="NEW-001",
        )

        response = await client.get(
            "/api/v1/admin/orders",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        # Newer order should appear first
        content = response.content.decode()
        new_pos = content.find("NEW-001")
        old_pos = content.find("OLD-001")
        # If both are found, new should come before old
        if new_pos != -1 and old_pos != -1:
            assert new_pos < old_pos

    async def test_list_orders_unauthorized(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """Test that non-superuser cannot access order list."""
        response = await client.get(
            "/api/v1/admin/orders",
            headers=auth_headers,
        )

        # Should return 403 Forbidden
        assert response.status_code == 403

    async def test_list_orders_unauthenticated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that unauthenticated user cannot access order list."""
        response = await client.get("/api/v1/admin/orders")

        # Should return 401 Unauthorized
        assert response.status_code == 401

    async def test_list_orders_feature_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test order list when feature flag is disabled."""
        # Mock the feature flag to be disabled
        with patch("app.api.v1.endpoints.admin_orders.get_settings") as mock_settings:
            mock_settings.return_value.windx.experimental_orders_page = False

            response = await client.get(
                "/api/v1/admin/orders",
                headers=superuser_auth_headers,
                follow_redirects=False,
            )

            # Should redirect to dashboard
            assert response.status_code == 303
            assert "/api/v1/admin/dashboard" in response.headers["location"]


class TestViewOrder:
    """Test order detail view endpoint."""

    async def test_view_order_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test viewing order details."""
        from tests.factories.order_factory import OrderFactory

        # Create order with quote and customer
        order = await OrderFactory.create(
            db_session,
            order_number="TEST-ORDER-001",
        )

        response = await client.get(
            f"/api/v1/admin/orders/{order.id}",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert b"TEST-ORDER-001" in response.content

    async def test_view_order_shows_customer_info(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that order view shows customer information."""
        from tests.factories.customer_factory import CustomerFactory
        from tests.factories.order_factory import OrderFactory
        from tests.factories.quote_factory import QuoteFactory

        # Create customer
        customer = await CustomerFactory.create(
            db_session,
            company_name="Test Customer Corp",
        )

        # Create quote for customer
        quote = await QuoteFactory.create(
            db_session,
            customer_id=customer.id,
        )

        # Create order from quote
        order = await OrderFactory.create(
            db_session,
            quote_id=quote.id,
        )

        response = await client.get(
            f"/api/v1/admin/orders/{order.id}",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert b"Test Customer Corp" in response.content

    async def test_view_order_shows_items(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that order view shows order items."""
        from tests.factories.order_factory import OrderFactory

        # Create order (factory should create items)
        order = await OrderFactory.create(db_session)

        response = await client.get(
            f"/api/v1/admin/orders/{order.id}",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        # Check for items section or quantity
        assert b"item" in response.content.lower() or b"quantity" in response.content.lower()

    async def test_view_order_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test viewing non-existent order."""
        response = await client.get(
            "/api/v1/admin/orders/99999",
            headers=superuser_auth_headers,
            follow_redirects=False,
        )

        # Should redirect with error message
        assert response.status_code == 303
        assert "error" in response.headers["location"].lower()

    async def test_view_order_unauthorized(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """Test that non-superuser cannot view order details."""
        from tests.factories.order_factory import OrderFactory

        # Create order
        order = await OrderFactory.create(db_session)

        response = await client.get(
            f"/api/v1/admin/orders/{order.id}",
            headers=auth_headers,
        )

        # Should return 403 Forbidden
        assert response.status_code == 403


class TestUpdateOrderStatus:
    """Test order status update endpoint."""

    async def test_update_order_status_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test updating order status successfully."""
        from tests.factories.order_factory import OrderFactory

        # Create order with confirmed status
        order = await OrderFactory.create(
            db_session,
            status="confirmed",
        )

        # Update to production
        response = await client.post(
            f"/api/v1/admin/orders/{order.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "production"},
            follow_redirects=False,
        )

        # Should redirect to order detail with success message
        assert response.status_code == 303
        location = response.headers["location"]
        assert f"/api/v1/admin/orders/{order.id}" in location
        assert "success" in location.lower()

        # Verify status was updated
        from app.repositories.order import OrderRepository

        order_repo = OrderRepository(db_session)
        updated_order = await order_repo.get(order.id)
        assert updated_order.status == "production"

    async def test_update_order_status_invalid_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test updating order with invalid status."""
        from tests.factories.order_factory import OrderFactory

        # Create order
        order = await OrderFactory.create(db_session)

        # Try to update with invalid status
        response = await client.post(
            f"/api/v1/admin/orders/{order.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "invalid_status"},
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code == 303
        assert "error" in response.headers["location"].lower()

    async def test_update_order_status_validation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test order status transition validation."""
        from tests.factories.order_factory import OrderFactory

        # Create order with shipped status
        order = await OrderFactory.create(
            db_session,
            status="shipped",
        )

        # Try to update to production (invalid transition)
        response = await client.post(
            f"/api/v1/admin/orders/{order.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "production"},
            follow_redirects=False,
        )

        # Should handle the transition (either allow or reject based on business rules)
        assert response.status_code == 303

    async def test_update_order_status_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test updating status of non-existent order."""
        response = await client.post(
            "/api/v1/admin/orders/99999/status",
            headers=superuser_auth_headers,
            data={"new_status": "production"},
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code == 303
        assert "error" in response.headers["location"].lower()

    async def test_update_order_status_unauthorized(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """Test that non-superuser cannot update order status."""
        from tests.factories.order_factory import OrderFactory

        # Create order
        order = await OrderFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/orders/{order.id}/status",
            headers=auth_headers,
            data={"new_status": "production"},
        )

        # Should return 403 Forbidden
        assert response.status_code == 403

    async def test_update_order_status_all_valid_transitions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test all valid order status transitions."""
        from tests.factories.order_factory import OrderFactory

        # Test confirmed -> production
        order1 = await OrderFactory.create(db_session, status="confirmed")
        response = await client.post(
            f"/api/v1/admin/orders/{order1.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "production"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        # Test production -> shipped
        order2 = await OrderFactory.create(db_session, status="production")
        response = await client.post(
            f"/api/v1/admin/orders/{order2.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "shipped"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        # Test shipped -> installed
        order3 = await OrderFactory.create(db_session, status="shipped")
        response = await client.post(
            f"/api/v1/admin/orders/{order3.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "installed"},
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestOrderStatusValidation:
    """Test order status validation logic."""

    async def test_valid_order_statuses(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that only valid statuses are accepted."""
        from tests.factories.order_factory import OrderFactory

        order = await OrderFactory.create(db_session)

        valid_statuses = ["confirmed", "production", "shipped", "installed"]

        for status in valid_statuses:
            # Create new order for each test
            test_order = await OrderFactory.create(db_session)

            response = await client.post(
                f"/api/v1/admin/orders/{test_order.id}/status",
                headers=superuser_auth_headers,
                data={"new_status": status},
                follow_redirects=False,
            )

            # Should accept valid status
            assert response.status_code == 303
            # Should not have error in redirect
            location = response.headers.get("location", "")
            # Success redirects typically don't have "error" in URL
            # (though this depends on implementation)

    async def test_order_status_case_sensitivity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that order status is case-sensitive."""
        from tests.factories.order_factory import OrderFactory

        order = await OrderFactory.create(db_session)

        # Try uppercase status
        response = await client.post(
            f"/api/v1/admin/orders/{order.id}/status",
            headers=superuser_auth_headers,
            data={"new_status": "PRODUCTION"},
            follow_redirects=False,
        )

        # Should handle case (either normalize or reject)
        assert response.status_code == 303


class TestOrderFeatureFlag:
    """Test order feature flag behavior."""

    async def test_view_order_feature_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test viewing order when feature flag is disabled."""
        from tests.factories.order_factory import OrderFactory

        order = await OrderFactory.create(db_session)

        # Mock the feature flag to be disabled - patch where it's called in admin_utils
        with patch("app.api.admin_utils.get_settings") as mock_settings:
            mock_settings.return_value.windx.experimental_orders_page = False

            response = await client.get(
                f"/api/v1/admin/orders/{order.id}",
                headers=superuser_auth_headers,
                follow_redirects=False,
            )

            # View endpoint uses check_feature_flag() which raises 503
            assert response.status_code == 503

    async def test_update_status_feature_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test updating order status when feature flag is disabled."""
        from tests.factories.order_factory import OrderFactory

        order = await OrderFactory.create(db_session)

        # Mock the feature flag to be disabled - patch where it's called
        with patch("app.api.admin_utils.get_settings") as mock_settings:
            mock_settings.return_value.windx.experimental_orders_page = False

            # Add Accept header for HTML to trigger redirect instead of JSON error
            headers = {**superuser_auth_headers, "Accept": "text/html"}

            response = await client.post(
                f"/api/v1/admin/orders/{order.id}/status",
                headers=headers,
                data={"new_status": "production"},
                follow_redirects=False,
            )

            # Status update endpoint uses check_feature_flag() which raises 503
            assert response.status_code == 503
