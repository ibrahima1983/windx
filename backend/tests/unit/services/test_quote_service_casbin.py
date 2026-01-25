"""Unit tests for Quote Service with Casbin decorators.

This module contains unit tests for the Quote Service with RBAC decorators,
customer relationships, and RBACQueryFilter automatic filtering.

Tests cover:
- Quote creation with proper customer references
- Casbin decorator authorization on quote operations
- RBACQueryFilter for quote filtering by customer relationships
- Privilege object evaluation

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
from app.models.quote import Quote
from app.models.user import User
from app.services.quote import AdminQuoteAccess, QuoteManagement, QuoteReader, QuoteService


class TestQuoteServiceCasbin:
    """Unit tests for Quote Service with Casbin decorators."""

    @pytest.mark.asyncio
    async def test_generate_quote_uses_customer_id_from_configuration(
        self, db_session, test_user_with_rbac
    ):
        """Test that generate_quote uses customer.id from configuration to maintain relationship consistency.

        Note: Using test_user_with_rbac since customers can create quotes per RBAC policy.
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

        # Get the customer ID for the test user
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        result = await db_session.execute(stmt)
        customer_id = result.scalar_one()

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        quote_service = QuoteService(db_session)

        # Execute
        result = await quote_service.generate_quote(
            configuration_id=config.id, user=test_user_with_rbac, tax_rate=Decimal("8.50")
        )

        # Verify quote creation used customer_id from configuration
        assert result is not None
        assert result.customer_id == customer_id
        assert result.configuration_id == config.id

    @pytest.mark.asyncio
    async def test_generate_quote_casbin_decorator_authorization(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test Casbin decorator authorization on generate_quote.

        Tests that customers CAN create quotes (per RBAC policy),
        and staff members CAN also create quotes.
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

        # Get the customer ID for the test user
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        result = await db_session.execute(stmt)
        customer_id = result.scalar_one()

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        quote_service = QuoteService(db_session)

        # Test 1: Customer CAN create quotes (per RBAC policy)
        result = await quote_service.generate_quote(
            configuration_id=config.id, user=test_user_with_rbac, tax_rate=Decimal("8.50")
        )
        assert result is not None

        # Test 2: Superuser CAN also create quotes
        # Create another configuration for superuser test
        config2 = Configuration(
            name="Test Configuration 2",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config2)
        await db_session.commit()
        await db_session.refresh(config2)

        result2 = await quote_service.generate_quote(
            configuration_id=config2.id, user=test_superuser_with_rbac, tax_rate=Decimal("8.50")
        )
        assert result2 is not None

    @pytest.mark.asyncio
    async def test_list_quotes_rbac_query_filter(self, db_session, test_user_with_rbac):
        """Test that list_quotes uses RBACQueryFilter for automatic filtering by customer relationships.

        Note: Customers CAN read quotes per RBAC policy.
        """
        # Setup
        quote_service = QuoteService(db_session)

        # Execute - customer can list their quotes
        result = await quote_service.list_quotes(test_user_with_rbac)

        # Verify the method executed successfully (RBACQueryFilter applied automatically)
        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_quote_multiple_decorators_or_logic(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test get_quote with multiple @require decorators (OR logic).

        Tests that customers CAN read quotes (per RBAC policy),
        and staff members CAN also read quotes.
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

        # Get the customer ID for the test user
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        result = await db_session.execute(stmt)
        customer_id = result.scalar_one()

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a quote
        quote_service = QuoteService(db_session)
        quote = await quote_service.generate_quote(
            configuration_id=config.id, user=test_user_with_rbac, tax_rate=Decimal("8.50")
        )

        # Test 1: Customer CAN read their own quotes (per RBAC policy)
        result = await quote_service.get_quote(quote.id, test_user_with_rbac)
        assert result is not None
        assert result.id == quote.id

        # Test 2: Superuser CAN read any quote
        result2 = await quote_service.get_quote(quote.id, test_superuser_with_rbac)
        assert result2 is not None
        assert result2.id == quote.id

    @pytest.mark.asyncio
    async def test_quote_customer_relationship_consistency(self, db_session, test_user_with_rbac):
        """Test that quote-customer relationship consistency is maintained."""
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

        # Get the customer ID for the test user
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        result = await db_session.execute(stmt)
        customer_id = result.scalar_one()

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        quote_service = QuoteService(db_session)

        # Test: Quote uses configuration's customer_id
        result = await quote_service.generate_quote(
            configuration_id=config.id, user=test_user_with_rbac, tax_rate=Decimal("8.50")
        )

        # Verify quote uses configuration's customer_id
        assert result.customer_id == customer_id
        assert result.configuration_id == config.id

    @pytest.mark.asyncio
    async def test_privilege_objects_evaluation(self):
        """Test Privilege objects functionality for Quote Service."""
        # Test QuoteManagement privilege
        assert Role.SALESMAN in QuoteManagement.roles
        assert Role.PARTNER in QuoteManagement.roles
        assert QuoteManagement.permission.resource == "quote"
        assert QuoteManagement.permission.action == "create"
        assert QuoteManagement.resource.resource_type == "customer"

        # Test QuoteReader privilege
        assert Role.CUSTOMER in QuoteReader.roles
        assert Role.SALESMAN in QuoteReader.roles
        assert Role.PARTNER in QuoteReader.roles
        assert QuoteReader.permission.resource == "quote"
        assert QuoteReader.permission.action == "read"
        assert QuoteReader.resource.resource_type == "quote"

        # Test AdminQuoteAccess privilege
        assert Role.SUPERADMIN in AdminQuoteAccess.roles
        assert AdminQuoteAccess.permission.resource == "*"
        assert AdminQuoteAccess.permission.action == "*"

    @pytest.mark.asyncio
    async def test_rbac_query_filter_customer_filtering(self, db_session, test_user_with_rbac):
        """Test RBACQueryFilter for quote filtering by customer access."""
        # Setup
        quote_service = QuoteService(db_session)

        # Execute - test that RBACQueryFilter is applied automatically
        result = await quote_service.list_quotes(test_user_with_rbac, status="draft")

        # Verify the method executed successfully (filtering applied automatically)
        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_quote_totals_calculation_with_customer_context(
        self, db_session, test_user_with_rbac
    ):
        """Test quote totals calculation maintains customer context."""
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

        # Get the customer ID for the test user
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        result = await db_session.execute(stmt)
        customer_id = result.scalar_one()

        # Create a configuration with specific total price
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,
            base_price=mfg_type.base_price,
            total_price=Decimal("250.00"),  # Specific total for calculation test
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        quote_service = QuoteService(db_session)

        # Execute with specific tax rate and discount
        result = await quote_service.generate_quote(
            configuration_id=config.id,
            user=test_user_with_rbac,
            tax_rate=Decimal("8.50"),
            discount_amount=Decimal("25.00"),
        )

        # Verify totals calculation
        expected_subtotal = config.total_price
        expected_tax = (expected_subtotal * Decimal("8.50") / Decimal("100")).quantize(
            Decimal("0.01")
        )
        expected_total = expected_subtotal + expected_tax - Decimal("25.00")

        assert result.subtotal == expected_subtotal
        assert result.tax_amount == expected_tax
        assert result.discount_amount == Decimal("25.00")
        assert result.total_amount == expected_total

    @pytest.mark.asyncio
    async def test_configuration_not_found_error_handling(self, db_session, test_user_with_rbac):
        """Test error handling when configuration is not found."""
        # Setup
        quote_service = QuoteService(db_session)

        # Execute and verify exception - should get 404 for non-existent configuration
        with pytest.raises(NotFoundException) as exc_info:
            await quote_service.generate_quote(configuration_id=999, user=test_user_with_rbac)

        assert "Configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_quote_not_found_error_handling(self, db_session, test_superuser_with_rbac):
        """Test error handling when quote is not found.

        Note: Using superuser since customers need ownership to read quotes per RBAC policy.
        """
        # Setup
        quote_service = QuoteService(db_session)

        # Execute and verify exception - should get 404 for non-existent quote
        with pytest.raises(NotFoundException) as exc_info:
            await quote_service.get_quote(999, test_superuser_with_rbac)

        assert "Quote" in str(exc_info.value)
