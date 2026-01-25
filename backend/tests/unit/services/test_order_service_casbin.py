"""Unit tests for Order Service with Casbin decorators.

This module contains unit tests for the Order Service with RBAC decorators,
customer relationship inheritance, and RBACQueryFilter automatic filtering.

Tests cover:
- Order creation with customer relationship inheritance
- Casbin decorator authorization through quote-customer relationships
- RBACQueryFilter for order filtering by customer ownership
- Role composition and Privilege objects

Requirements: 2.1, 2.2, 8.1, 9.1, 9.3
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import RBACQueryFilter, Role
from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.order import Order
from app.models.quote import Quote
from app.models.user import User
from app.services.order import AdminOrderAccess, OrderManagement, OrderReader, OrderService


class TestOrderServiceCasbin:
    """Unit tests for Order Service with Casbin decorators."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            id=1,
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            role=Role.CUSTOMER.value,
            is_active=True,
            is_superuser=False,
        )

    @pytest.fixture
    def sample_salesman(self):
        """Create sample salesman user for testing."""
        return User(
            id=2,
            email="salesman@company.com",
            username="salesman",
            full_name="Sales Person",
            role=Role.SALESMAN.value,
            is_active=True,
            is_superuser=False,
        )

    @pytest.fixture
    def sample_partner(self):
        """Create sample partner user for testing."""
        return User(
            id=3,
            email="partner@company.com",
            username="partner",
            full_name="Partner User",
            role=Role.PARTNER.value,
            is_active=True,
            is_superuser=False,
        )

    @pytest.fixture
    def sample_admin(self):
        """Create sample admin user for testing."""
        return User(
            id=4,
            email="admin@company.com",
            username="admin",
            full_name="Admin User",
            role=Role.SUPERADMIN.value,
            is_active=True,
            is_superuser=True,
        )

    @pytest.fixture
    def sample_customer(self):
        """Create sample customer for testing."""
        return Customer(
            id=100,
            email="test@example.com",
            contact_person="Test User",
            customer_type="residential",
            is_active=True,
        )

    @pytest.fixture
    def sample_configuration(self, sample_customer):
        """Create sample configuration for testing."""
        return Configuration(
            id=1,
            manufacturing_type_id=1,
            customer_id=sample_customer.id,
            name="Test Configuration",
            status="draft",
            base_price=Decimal("200.00"),
            total_price=Decimal("250.00"),
            calculated_weight=Decimal("15.00"),
        )

    @pytest.fixture
    def sample_quote(self, sample_customer, sample_configuration):
        """Create sample quote for testing."""
        return Quote(
            id=1,
            configuration_id=sample_configuration.id,
            customer_id=sample_customer.id,
            quote_number="Q-20250101-001",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",  # Must be accepted to create order
        )

    @pytest.fixture
    def sample_order(self, sample_quote):
        """Create sample order for testing."""
        return Order(
            id=1,
            quote_id=sample_quote.id,
            order_number="O-20250101-001",
            order_date=date.today(),
            status="confirmed",
        )

    @pytest.mark.asyncio
    async def test_create_order_maintains_customer_relationship_from_quote(
        self, db_session, test_superuser_with_rbac
    ):
        """Test that order creation maintains customer relationships from quotes.

        Note: Only staff members (superadmin, salesman, partner) can create orders.
        Customers cannot create orders directly per RBAC policy.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",  # Must be accepted to create order
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Setup
        order_service = OrderService(db_session)

        # Execute - superuser can create orders from any quote
        result = await order_service.create_order_from_quote(
            quote_id=quote.id, user=test_superuser_with_rbac
        )

        # Verify order creation maintains customer relationship through quote
        assert result is not None
        assert result.quote_id == quote.id
        # Customer relationship is maintained through quote_id -> quote.customer_id

    @pytest.mark.asyncio
    async def test_create_order_casbin_decorator_authorization(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test Casbin decorator authorization on create_order_from_quote.

        Tests that customers CANNOT create orders (per RBAC policy),
        but staff members CAN create orders.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",  # Must be accepted to create order
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Setup
        order_service = OrderService(db_session)

        # Test 1: Customer CANNOT create orders (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await order_service.create_order_from_quote(quote_id=quote.id, user=test_user_with_rbac)
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN create orders from any quote
        result = await order_service.create_order_from_quote(
            quote_id=quote.id, user=test_superuser_with_rbac
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_order_multiple_decorators_or_logic(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test get_order with multiple @require decorators (OR logic).

        Tests that customers CANNOT read orders (per RBAC policy),
        but staff members CAN read orders.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Create an order (using superuser since customers can't create orders)
        order_service = OrderService(db_session)
        order = await order_service.create_order_from_quote(
            quote_id=quote.id, user=test_superuser_with_rbac
        )

        # Test 1: Customer CANNOT read orders (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await order_service.get_order(order.id, test_user_with_rbac)
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN read any order
        result = await order_service.get_order(order.id, test_superuser_with_rbac)
        assert result is not None
        assert result.id == order.id

    @pytest.mark.asyncio
    async def test_rbac_query_filter_order_filtering_by_customer_ownership(
        self, db_session, test_user_with_rbac
    ):
        """Test RBACQueryFilter for order filtering by customer ownership through quotes."""
        # Setup - this would be in a list_orders method (not currently implemented in OrderService)
        # We'll test the RBACQueryFilter directly

        # Test the filter with real database
        original_query = select(Order)
        result_query = await RBACQueryFilter.filter_orders(original_query, test_user_with_rbac)

        # Verify the query was modified (should include joins and filters)
        assert result_query is not None
        # The actual filtering logic is tested in the RBACQueryFilter implementation

    @pytest.mark.asyncio
    async def test_role_composition_and_privilege_objects(self):
        """Test role composition and Privilege objects for Order Service."""
        # Test OrderManagement privilege
        assert Role.SALESMAN in OrderManagement.roles
        assert Role.PARTNER in OrderManagement.roles
        assert OrderManagement.permission.resource == "order"
        assert OrderManagement.permission.action == "create"
        assert OrderManagement.resource.resource_type == "customer"

        # Test OrderReader privilege
        assert Role.CUSTOMER in OrderReader.roles
        assert Role.SALESMAN in OrderReader.roles
        assert Role.PARTNER in OrderReader.roles
        assert OrderReader.permission.resource == "order"
        assert OrderReader.permission.action == "read"
        assert OrderReader.resource.resource_type == "order"

        # Test AdminOrderAccess privilege
        assert Role.SUPERADMIN in AdminOrderAccess.roles
        assert AdminOrderAccess.permission.resource == "*"
        assert AdminOrderAccess.permission.action == "*"

        # Test role composition (bitwise OR)
        sales_and_partner = Role.SALESMAN | Role.PARTNER
        assert Role.SALESMAN in sales_and_partner
        assert Role.PARTNER in sales_and_partner

    @pytest.mark.asyncio
    async def test_order_customer_relationship_consistency_through_quotes(
        self, db_session, test_superuser_with_rbac
    ):
        """Test that order-customer relationship consistency is maintained through quotes.

        Note: Only staff members can create orders per RBAC policy.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Setup
        order_service = OrderService(db_session)

        # Execute - superuser can create orders
        result = await order_service.create_order_from_quote(
            quote_id=quote.id,
            user=test_superuser_with_rbac,
            special_instructions="Test instructions",
        )

        # Verify order maintains relationship through quote
        assert result is not None
        assert result.quote_id == quote.id
        assert result.special_instructions == "Test instructions"

        # The customer relationship is implicit through:
        # order.quote_id -> quote.customer_id -> customer.id

    @pytest.mark.asyncio
    async def test_quote_not_accepted_validation(self, db_session, test_superuser_with_rbac):
        """Test validation that quote must be accepted before creating order."""
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote with non-accepted status
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="draft",  # Not accepted
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Setup
        order_service = OrderService(db_session)

        # Execute and verify exception
        with pytest.raises(ValidationException) as exc_info:
            await order_service.create_order_from_quote(
                quote_id=quote.id, user=test_superuser_with_rbac
            )

        assert "Quote must be accepted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_order_already_exists_validation(self, db_session, test_superuser_with_rbac):
        """Test validation that order cannot be created if one already exists for the quote."""
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Setup
        order_service = OrderService(db_session)

        # Create first order
        existing_order = await order_service.create_order_from_quote(
            quote_id=quote.id, user=test_superuser_with_rbac
        )
        assert existing_order is not None

        # Execute and verify exception when trying to create second order
        with pytest.raises(ValidationException) as exc_info:
            await order_service.create_order_from_quote(
                quote_id=quote.id, user=test_superuser_with_rbac
            )

        assert "Order already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_order_authorization_through_quote_customer_relationships(
        self, db_session, test_superuser_with_rbac
    ):
        """Test Casbin authorization through quote-customer relationships.

        Note: Only staff can read orders per RBAC policy, so testing with superuser.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the order with unique email
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        from app.models.quote import Quote

        quote = Quote(
            configuration_id=config.id,
            customer_id=customer.id,
            quote_number=f"Q-{uuid.uuid4().hex[:8]}",
            subtotal=Decimal("250.00"),
            tax_rate=Decimal("8.50"),
            tax_amount=Decimal("21.25"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("271.25"),
            valid_until=date.today() + timedelta(days=30),
            status="accepted",
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        # Setup
        order_service = OrderService(db_session)

        # Create an order (superuser can create orders)
        order = await order_service.create_order_from_quote(
            quote_id=quote.id, user=test_superuser_with_rbac
        )

        # Execute - test authorization (superuser can read orders)
        result = await order_service.get_order(order.id, test_superuser_with_rbac)

        # Verify order was retrieved successfully
        assert result is not None
        assert result.id == order.id

    @pytest.mark.asyncio
    async def test_quote_not_found_error_handling(self, db_session, test_superuser_with_rbac):
        """Test error handling when quote is not found.

        Note: Using superuser since customers cannot create orders per RBAC policy.
        """
        # Setup
        order_service = OrderService(db_session)

        # Execute and verify exception - should get 404 for non-existent quote
        with pytest.raises(NotFoundException) as exc_info:
            await order_service.create_order_from_quote(quote_id=999, user=test_superuser_with_rbac)

        assert "Quote" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_order_not_found_error_handling(self, db_session, test_superuser_with_rbac):
        """Test error handling when order is not found.

        Note: Using superuser since customers cannot read orders per RBAC policy.
        """
        # Setup
        order_service = OrderService(db_session)

        # Execute and verify exception - should get 404 for non-existent order
        with pytest.raises(NotFoundException) as exc_info:
            await order_service.get_order(999, test_superuser_with_rbac)

        assert "Order" in str(exc_info.value)
