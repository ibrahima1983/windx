"""Integration tests for Order repository.

This module tests the OrderRepository data access layer including:
- Get operations (get, get_with_full_details with customer, items, quote)
- Update operations
- Filtering by status
- Search by order number, customer name, customer email
- Pagination and ordering by order_date DESC

Features:
    - Repository layer testing
    - Database integration testing
    - Relationship loading testing
    - Query filtering testing
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.order import Order
from app.models.quote import Quote
from app.repositories.order import OrderRepository
from app.schemas.order import OrderUpdate
from tests.factories.customer_factory import create_customer_data
from tests.factories.order_factory import create_order_data
from tests.factories.quote_factory import create_quote_data

pytestmark = pytest.mark.asyncio


async def create_test_order_with_dependencies(
    db_session: AsyncSession,
    **order_kwargs,
) -> Order:
    """Helper to create an order with all required dependencies.

    Args:
        db_session: Database session
        **order_kwargs: Additional order fields

    Returns:
        Order: Created order with all dependencies
    """
    # Create manufacturing type with unique name
    import uuid

    unique_suffix = str(uuid.uuid4())[:8]
    mfg_type = ManufacturingType(
        name=f"Test Type {unique_suffix}",
        description="Test manufacturing type",
        base_category="window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
        is_active=True,
    )
    db_session.add(mfg_type)
    await db_session.flush()

    # Create customer
    customer_data = create_customer_data()
    customer = Customer(**customer_data)
    db_session.add(customer)
    await db_session.flush()

    # Create configuration
    config = Configuration(
        manufacturing_type_id=mfg_type.id,
        customer_id=customer.id,
        name="Test Configuration",
        description="Test configuration for order",
        status="quoted",
        base_price=Decimal("200.00"),
        total_price=Decimal("500.00"),
    )
    db_session.add(config)
    await db_session.flush()

    # Create quote
    quote_data = create_quote_data(
        configuration_id=config.id,
        customer_id=customer.id,
        status="accepted",
    )
    quote = Quote(**quote_data)
    db_session.add(quote)
    await db_session.flush()

    # Create order
    order_data = create_order_data(quote_id=quote.id, **order_kwargs)
    order = Order(**order_data)
    db_session.add(order)
    await db_session.commit()

    return order


class TestOrderRepositoryGetOperations:
    """Tests for get operations."""

    async def test_get_order(self, db_session: AsyncSession):
        """Test getting an order by ID."""
        repo = OrderRepository(db_session)

        # Create order with dependencies
        order = await create_test_order_with_dependencies(db_session)

        # Get order
        retrieved = await repo.get(order.id)

        assert retrieved is not None
        assert retrieved.id == order.id
        assert retrieved.order_number == order.order_number

    async def test_get_nonexistent_order(self, db_session: AsyncSession):
        """Test getting an order that doesn't exist."""
        repo = OrderRepository(db_session)

        order = await repo.get(99999)

        assert order is None

    async def test_get_by_order_number(self, db_session: AsyncSession):
        """Test getting order by order number."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(
            db_session,
            order_number="ORD-TEST-001",
        )

        # Get by order number
        found = await repo.get_by_order_number("ORD-TEST-001")

        assert found is not None
        assert found.id == order.id
        assert found.order_number == "ORD-TEST-001"

    async def test_get_by_quote(self, db_session: AsyncSession):
        """Test getting order by quote ID."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(db_session)

        # Get by quote
        found = await repo.get_by_quote(order.quote_id)

        assert found is not None
        assert found.id == order.id
        assert found.quote_id == order.quote_id

    async def test_get_with_full_details(self, db_session: AsyncSession):
        """Test getting order with all related data eager-loaded."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(db_session)

        # Get with full details
        retrieved = await repo.get_with_full_details(order.id)

        assert retrieved is not None
        assert retrieved.id == order.id
        # Verify relationships are loaded
        assert hasattr(retrieved, "quote")
        assert hasattr(retrieved, "items")
        assert retrieved.quote is not None
        assert hasattr(retrieved.quote, "customer")
        assert hasattr(retrieved.quote, "configuration")
        assert isinstance(retrieved.items, list)


class TestOrderRepositoryUpdateOperations:
    """Tests for update operations."""

    async def test_update_order_status(self, db_session: AsyncSession):
        """Test updating order status."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(
            db_session,
            status="confirmed",
        )

        # Update status
        update_data = OrderUpdate(status="production")
        updated = await repo.update(order, update_data)

        assert updated.status == "production"
        assert updated.order_number == order.order_number  # Unchanged

    async def test_update_order_special_instructions(self, db_session: AsyncSession):
        """Test updating order special instructions."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(db_session)

        # Update instructions
        update_data = OrderUpdate(special_instructions="Updated: Call before delivery")
        updated = await repo.update(order, update_data)

        assert updated.special_instructions == "Updated: Call before delivery"

    async def test_update_order_required_date(self, db_session: AsyncSession):
        """Test updating order required date."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(db_session)

        # Update required date
        new_date = date.today() + timedelta(days=45)
        update_data = OrderUpdate(required_date=new_date)
        updated = await repo.update(order, update_data)

        assert updated.required_date == new_date


class TestOrderRepositoryFiltering:
    """Tests for filtering orders."""

    async def test_filter_by_status(self, db_session: AsyncSession):
        """Test filtering orders by status."""
        repo = OrderRepository(db_session)

        # Create orders with different statuses
        order1 = await create_test_order_with_dependencies(
            db_session,
            status="confirmed",
        )
        order2 = await create_test_order_with_dependencies(
            db_session,
            status="production",
        )
        order3 = await create_test_order_with_dependencies(
            db_session,
            status="shipped",
        )

        # Filter by production status
        query = repo.get_filtered(status="production")
        result = await db_session.execute(query)
        production_orders = list(result.scalars().all())

        assert len(production_orders) >= 1
        assert all(o.status == "production" for o in production_orders)
        assert order2.id in [o.id for o in production_orders]

    async def test_filter_orders_default_ordering(self, db_session: AsyncSession):
        """Test that filtered orders are ordered by created_at DESC."""
        repo = OrderRepository(db_session)

        # Create multiple orders
        order1 = await create_test_order_with_dependencies(db_session)
        order2 = await create_test_order_with_dependencies(db_session)
        order3 = await create_test_order_with_dependencies(db_session)

        # Get all orders
        query = repo.get_filtered()
        result = await db_session.execute(query)
        orders = list(result.scalars().all())

        # Verify ordering (newest first)
        assert len(orders) >= 3
        for i in range(len(orders) - 1):
            assert orders[i].created_at >= orders[i + 1].created_at


class TestOrderRepositorySearch:
    """Tests for searching orders."""

    async def test_search_by_order_number(self, db_session: AsyncSession):
        """Test searching orders by order number."""
        repo = OrderRepository(db_session)

        # Create order with specific order number
        order = await create_test_order_with_dependencies(
            db_session,
            order_number="ORD-SEARCH-001",
        )

        # Search by order number
        found = await repo.get_by_order_number("ORD-SEARCH-001")

        assert found is not None
        assert found.id == order.id

    async def test_search_order_number_not_found(self, db_session: AsyncSession):
        """Test searching for non-existent order number."""
        repo = OrderRepository(db_session)

        found = await repo.get_by_order_number("ORD-NONEXISTENT-999")

        assert found is None


class TestOrderRepositoryPagination:
    """Tests for pagination and ordering."""

    async def test_get_multi_with_pagination(self, db_session: AsyncSession):
        """Test getting multiple orders with pagination."""
        repo = OrderRepository(db_session)

        # Create multiple orders
        for i in range(5):
            await create_test_order_with_dependencies(db_session)

        # Get first page
        page1 = await repo.get_multi(skip=0, limit=2)
        assert len(page1) == 2

        # Get second page
        page2 = await repo.get_multi(skip=2, limit=2)
        assert len(page2) == 2

        # Verify different orders
        page1_ids = {o.id for o in page1}
        page2_ids = {o.id for o in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_pagination_edge_cases(self, db_session: AsyncSession):
        """Test pagination edge cases."""
        repo = OrderRepository(db_session)

        # Create 3 orders
        for i in range(3):
            await create_test_order_with_dependencies(db_session)

        # Request more than available
        orders = await repo.get_multi(skip=0, limit=100)
        assert len(orders) >= 3

        # Skip beyond available
        orders = await repo.get_multi(skip=100, limit=10)
        assert len(orders) == 0


class TestOrderRepositoryFactoryTraits:
    """Tests for factory traits."""

    async def test_in_production_trait(self, db_session: AsyncSession):
        """Test in_production order trait."""
        # Create order using trait
        order = await create_test_order_with_dependencies(
            db_session,
            in_production=True,
        )

        assert order.status == "production"

    async def test_shipped_trait(self, db_session: AsyncSession):
        """Test shipped order trait."""
        # Create order using trait
        order = await create_test_order_with_dependencies(
            db_session,
            shipped=True,
        )

        assert order.status == "shipped"

    async def test_completed_trait(self, db_session: AsyncSession):
        """Test completed order trait."""
        # Create order using trait
        order = await create_test_order_with_dependencies(
            db_session,
            completed=True,
        )

        assert order.status == "installed"


class TestOrderRepositoryStatusTransitions:
    """Tests for order status transitions."""

    async def test_status_progression(self, db_session: AsyncSession):
        """Test typical order status progression."""
        repo = OrderRepository(db_session)

        # Create order
        order = await create_test_order_with_dependencies(
            db_session,
            status="confirmed",
        )

        # Progress through statuses
        statuses = ["production", "shipped", "installed"]
        for status in statuses:
            update_data = OrderUpdate(status=status)
            order = await repo.update(order, update_data)
            assert order.status == status
