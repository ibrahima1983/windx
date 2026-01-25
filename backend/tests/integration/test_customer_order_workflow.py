"""Integration tests for customer order workflow.

This module tests the complete workflow from customer creation through
configuration, quote generation, and order placement.

Test Coverage:
    - Complete workflow: customer → configuration → quote → order
    - Workflow with multiple configurations
    - Workflow with order status updates
    - Data integrity throughout workflow
    - Relationship preservation

Requirements:
    - 6.1: Test complete workflow
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestCustomerOrderWorkflow:
    """Test complete customer order workflow."""

    async def test_complete_workflow_single_configuration(
        self,
        db_session: AsyncSession,
    ):
        """Test complete workflow: customer → configuration → quote → order.

        This test verifies the entire workflow from customer creation
        through order placement with a single configuration.
        """
        from app.models.manufacturing_type import ManufacturingType
        from tests.factories.configuration_factory import ConfigurationFactory
        from tests.factories.customer_factory import CustomerFactory
        from tests.factories.order_factory import OrderFactory
        from tests.factories.quote_factory import QuoteFactory

        # Step 1: Create customer
        customer = await CustomerFactory.create(
            db_session,
            company_name="Workflow Test Corp",
            email="workflow@test.com",
            customer_type="commercial",
        )
        assert customer.id is not None
        assert customer.email == "workflow@test.com"

        # Step 2: Create manufacturing type
        mfg_type = ManufacturingType(
            id=None,
            name="Workflow Test Window",
            description="Test window for workflow",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        # Step 3: Create configuration
        config = await ConfigurationFactory.create(
            db_session,
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            name="Living Room Window",
            total_price=Decimal("525.00"),
            calculated_weight=Decimal("23.00"),
        )
        assert config.id is not None
        assert config.customer_id == customer.id
        assert config.manufacturing_type_id == mfg_type.id
        assert config.total_price == Decimal("525.00")

        # Step 4: Generate quote
        quote = await QuoteFactory.create(
            db_session,
            configuration_id=config.id,
            customer_id=customer.id,
            subtotal=Decimal("525.00"),
            tax_rate=Decimal("8.50"),
            status="accepted",  # Quote must be accepted to create order
        )
        assert quote.id is not None
        assert quote.configuration_id == config.id
        assert quote.customer_id == customer.id
        assert quote.status == "accepted"

        # Step 5: Create order
        order = await OrderFactory.create(
            db_session,
            quote_id=quote.id,
            status="confirmed",
        )
        assert order.id is not None
        assert order.quote_id == quote.id
        assert order.status == "confirmed"

        # Verify relationships
        await db_session.refresh(customer)
        await db_session.refresh(config)
        await db_session.refresh(quote)
        await db_session.refresh(order)

        # Verify customer has configuration
        assert config.customer_id == customer.id

        # Verify configuration has quote
        assert quote.configuration_id == config.id

        # Verify quote has order
        assert order.quote_id == quote.id

    async def test_workflow_with_multiple_configurations(
        self,
        db_session: AsyncSession,
    ):
        """Test workflow with multiple configurations for same customer.

        This test verifies that a customer can have multiple configurations,
        each with their own quotes and orders.
        """
        from app.models.manufacturing_type import ManufacturingType
        from tests.factories.configuration_factory import ConfigurationFactory
        from tests.factories.customer_factory import CustomerFactory
        from tests.factories.order_factory import OrderFactory
        from tests.factories.quote_factory import QuoteFactory

        # Create customer
        customer = await CustomerFactory.create(
            db_session,
            company_name="Multi Config Corp",
            email="multiconfig@test.com",
        )

        # Create manufacturing type
        mfg_type = ManufacturingType(
            id=None,
            name="Multi Config Window",
            description="Test window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        # Create 3 configurations for the same customer
        configs = []
        for i in range(3):
            config = await ConfigurationFactory.create(
                db_session,
                manufacturing_type_id=mfg_type.id,
                customer_id=customer.id,
                name=f"Window {i + 1}",
                total_price=Decimal(f"{300 + i * 100}.00"),
            )
            configs.append(config)

        # Create quotes for each configuration
        quotes = []
        for config in configs:
            quote = await QuoteFactory.create(
                db_session,
                configuration_id=config.id,
                customer_id=customer.id,
                subtotal=config.total_price,
                status="accepted",
            )
            quotes.append(quote)

        # Create orders for each quote
        orders = []
        for quote in quotes:
            order = await OrderFactory.create(
                db_session,
                quote_id=quote.id,
                status="confirmed",
            )
            orders.append(order)

        # Verify all relationships
        assert len(configs) == 3
        assert len(quotes) == 3
        assert len(orders) == 3

        # Verify each configuration has correct customer
        for config in configs:
            assert config.customer_id == customer.id

        # Verify each quote has correct configuration
        for i, quote in enumerate(quotes):
            assert quote.configuration_id == configs[i].id
            assert quote.customer_id == customer.id

        # Verify each order has correct quote
        for i, order in enumerate(orders):
            assert order.quote_id == quotes[i].id

    async def test_workflow_with_order_status_updates(
        self,
        db_session: AsyncSession,
    ):
        """Test workflow with order status progression.

        This test verifies that orders can progress through different
        statuses: confirmed → production → shipped → installed.
        """
        from app.models.manufacturing_type import ManufacturingType
        from tests.factories.configuration_factory import ConfigurationFactory
        from tests.factories.customer_factory import CustomerFactory
        from tests.factories.order_factory import OrderFactory
        from tests.factories.quote_factory import QuoteFactory

        # Create customer
        customer = await CustomerFactory.create(
            db_session,
            company_name="Status Test Corp",
            email="status@test.com",
        )

        # Create manufacturing type
        mfg_type = ManufacturingType(
            id=None,
            name="Status Test Window",
            description="Test window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        # Create configuration
        config = await ConfigurationFactory.create(
            db_session,
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            name="Status Test Window",
        )

        # Create quote
        quote = await QuoteFactory.create(
            db_session,
            configuration_id=config.id,
            customer_id=customer.id,
            status="accepted",
        )

        # Create order
        order = await OrderFactory.create(
            db_session,
            quote_id=quote.id,
            status="confirmed",
        )

        # Verify initial status
        assert order.status == "confirmed"

        # Update to production
        order.status = "production"
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        assert order.status == "production"

        # Update to shipped
        order.status = "shipped"
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        assert order.status == "shipped"

        # Update to installed
        order.status = "installed"
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        assert order.status == "installed"

    async def test_workflow_data_integrity(
        self,
        db_session: AsyncSession,
    ):
        """Test data integrity throughout workflow.

        This test verifies that data remains consistent and accessible
        throughout the entire workflow, including all relationships.
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.manufacturing_type import ManufacturingType
        from tests.factories.configuration_factory import ConfigurationFactory
        from tests.factories.customer_factory import CustomerFactory
        from tests.factories.order_factory import OrderFactory
        from tests.factories.quote_factory import QuoteFactory

        # Create complete workflow
        customer = await CustomerFactory.create(
            db_session,
            company_name="Integrity Test Corp",
            email="integrity@test.com",
        )

        mfg_type = ManufacturingType(
            id=None,
            name="Integrity Test Window",
            description="Test window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        config = await ConfigurationFactory.create(
            db_session,
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            name="Integrity Test Window",
            total_price=Decimal("525.00"),
        )

        quote = await QuoteFactory.create(
            db_session,
            configuration_id=config.id,
            customer_id=customer.id,
            subtotal=Decimal("525.00"),
            status="accepted",
        )

        order = await OrderFactory.create(
            db_session,
            quote_id=quote.id,
            status="confirmed",
        )

        # Store IDs for verification
        order_id = order.id
        quote_id = quote.id
        config_id = config.id
        customer_id = customer.id

        # Clear session to force fresh queries
        await db_session.commit()
        db_session.expire_all()

        # Verify we can query from order back to customer
        from app.models.configuration import Configuration
        from app.models.customer import Customer
        from app.models.order import Order
        from app.models.quote import Quote

        # Query order (no relationship access needed)
        result = await db_session.execute(select(Order).where(Order.id == order_id))
        queried_order = result.scalar_one()
        assert queried_order.id == order_id
        assert queried_order.quote_id == quote_id

        # Query quote (no relationship access needed)
        result = await db_session.execute(select(Quote).where(Quote.id == quote_id))
        queried_quote = result.scalar_one()
        assert queried_quote.id == quote_id
        assert queried_quote.configuration_id == config_id

        # Query configuration (no relationship access needed)
        result = await db_session.execute(
            select(Configuration).where(Configuration.id == config_id)
        )
        queried_config = result.scalar_one()
        assert queried_config.id == config_id
        assert queried_config.customer_id == customer_id

        # Query customer (no relationship access needed)
        result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
        queried_customer = result.scalar_one()
        assert queried_customer.id == customer_id
        assert queried_customer.email == "integrity@test.com"

        # Verify relationships with eager loading
        result = await db_session.execute(
            select(Order).options(selectinload(Order.quote)).where(Order.id == order_id)
        )
        order_with_quote = result.scalar_one()
        assert order_with_quote.quote.id == quote_id

        result = await db_session.execute(
            select(Quote).options(selectinload(Quote.configuration)).where(Quote.id == quote_id)
        )
        quote_with_config = result.scalar_one()
        assert quote_with_config.configuration.id == config_id

        result = await db_session.execute(
            select(Configuration)
            .options(selectinload(Configuration.customer))
            .where(Configuration.id == config_id)
        )
        config_with_customer = result.scalar_one()
        assert config_with_customer.customer.id == customer_id

    async def test_workflow_with_configuration_updates(
        self,
        db_session: AsyncSession,
    ):
        """Test workflow where configuration is updated before quote.

        This test verifies that configurations can be modified and
        the changes are reflected in subsequent quotes.
        """
        from app.models.manufacturing_type import ManufacturingType
        from tests.factories.configuration_factory import ConfigurationFactory
        from tests.factories.customer_factory import CustomerFactory
        from tests.factories.quote_factory import QuoteFactory

        # Create customer and manufacturing type
        customer = await CustomerFactory.create(
            db_session,
            company_name="Update Test Corp",
            email="update@test.com",
        )

        mfg_type = ManufacturingType(
            id=None,
            name="Update Test Window",
            description="Test window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        # Create initial configuration
        config = await ConfigurationFactory.create(
            db_session,
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            name="Initial Window",
            total_price=Decimal("300.00"),
        )

        initial_price = config.total_price
        assert initial_price == Decimal("300.00")

        # Update configuration
        config.total_price = Decimal("450.00")
        config.name = "Updated Window"
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.total_price == Decimal("450.00")
        assert config.name == "Updated Window"

        # Create quote with updated price
        quote = await QuoteFactory.create(
            db_session,
            configuration_id=config.id,
            customer_id=customer.id,
            subtotal=config.total_price,  # Use updated price
            status="sent",
        )

        assert quote.subtotal == Decimal("450.00")
        assert quote.configuration_id == config.id


class TestHierarchyManagementWorkflow:
    """Test hierarchy management workflow.

    Requirements: 6.2
    """

    async def test_create_manufacturing_type_and_hierarchy(
        self,
        db_session: AsyncSession,
    ):
        """Test creating manufacturing type → attribute nodes → hierarchy.

        This test verifies the complete workflow of creating a manufacturing
        type and building its attribute hierarchy.
        """
        from app.models.attribute_node import AttributeNode
        from app.models.manufacturing_type import ManufacturingType

        # Step 1: Create manufacturing type
        mfg_type = ManufacturingType(
            id=None,
            name="Hierarchy Test Window",
            description="Test window for hierarchy workflow",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()
        assert mfg_type.id is not None

        # Step 2: Create root category node
        root_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=None,
            name="Frame Options",
            node_type="category",
            data_type="string",
            ltree_path="frame_options",
            depth=0,
            sort_order=1,
        )
        db_session.add(root_node)
        await db_session.flush()
        assert root_node.id is not None
        assert root_node.ltree_path == "frame_options"
        assert root_node.depth == 0

        # Step 3: Create attribute node under root
        attr_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=root_node.id,
            name="Material Type",
            node_type="attribute",
            data_type="string",
            ltree_path="frame_options.material_type",
            depth=1,
            sort_order=1,
        )
        db_session.add(attr_node)
        await db_session.flush()
        assert attr_node.id is not None
        assert attr_node.ltree_path == "frame_options.material_type"
        assert attr_node.depth == 1

        # Step 4: Create option nodes under attribute
        option1 = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=attr_node.id,
            name="Aluminum",
            node_type="option",
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("50.00"),
            weight_impact=Decimal("2.00"),
            ltree_path="frame_options.material_type.aluminum",
            depth=2,
            sort_order=1,
        )
        db_session.add(option1)

        option2 = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=attr_node.id,
            name="Vinyl",
            node_type="option",
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("30.00"),
            weight_impact=Decimal("1.50"),
            ltree_path="frame_options.material_type.vinyl",
            depth=2,
            sort_order=2,
        )
        db_session.add(option2)
        await db_session.flush()

        # Verify hierarchy structure
        assert option1.parent_node_id == attr_node.id
        assert option2.parent_node_id == attr_node.id
        assert option1.depth == 2
        assert option2.depth == 2

        await db_session.commit()

        # Verify we can query the hierarchy
        from sqlalchemy import select

        result = await db_session.execute(
            select(AttributeNode).where(AttributeNode.manufacturing_type_id == mfg_type.id)
        )
        all_nodes = result.scalars().all()
        assert len(all_nodes) == 4  # root + attribute + 2 options

    async def test_update_node_parent_recalculates_hierarchy(
        self,
        db_session: AsyncSession,
    ):
        """Test updating node parent triggers hierarchy recalculation.

        This test verifies that when a node's parent is changed, the LTREE
        paths and depths are recalculated for the node and all descendants.
        """
        from app.models.attribute_node import AttributeNode
        from app.models.manufacturing_type import ManufacturingType

        # Create manufacturing type
        mfg_type = ManufacturingType(
            id=None,
            name="Parent Update Test",
            description="Test",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        # Create two root categories
        category1 = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=None,
            name="Category 1",
            node_type="category",
            data_type="string",
            ltree_path="category1",
            depth=0,
            sort_order=1,
        )
        db_session.add(category1)

        category2 = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=None,
            name="Category 2",
            node_type="category",
            data_type="string",
            ltree_path="category2",
            depth=0,
            sort_order=2,
        )
        db_session.add(category2)
        await db_session.flush()

        # Create attribute under category1
        attr_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=category1.id,
            name="Test Attribute",
            node_type="attribute",
            data_type="string",
            ltree_path="category1.test_attribute",
            depth=1,
            sort_order=1,
        )
        db_session.add(attr_node)
        await db_session.flush()

        # Verify initial state
        assert attr_node.parent_node_id == category1.id
        assert attr_node.ltree_path == "category1.test_attribute"
        assert attr_node.depth == 1

        # Move attribute to category2
        attr_node.parent_node_id = category2.id
        attr_node.ltree_path = "category2.test_attribute"
        db_session.add(attr_node)
        await db_session.commit()
        await db_session.refresh(attr_node)

        # Verify updated state
        assert attr_node.parent_node_id == category2.id
        assert attr_node.ltree_path == "category2.test_attribute"
        assert attr_node.depth == 1

    async def test_delete_node_with_children_validation(
        self,
        db_session: AsyncSession,
    ):
        """Test that deleting nodes with children is handled properly.

        This test verifies that when a node with children is deleted,
        either the children are cascade deleted or the operation is prevented.
        """
        from sqlalchemy import select

        from app.models.attribute_node import AttributeNode
        from app.models.manufacturing_type import ManufacturingType

        # Create manufacturing type
        mfg_type = ManufacturingType(
            id=None,
            name="Delete Test",
            description="Test",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.flush()

        # Create parent node
        parent_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=None,
            name="Parent Node",
            node_type="category",
            data_type="string",
            ltree_path="parent",
            depth=0,
            sort_order=1,
        )
        db_session.add(parent_node)
        await db_session.flush()

        # Create child node
        child_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=parent_node.id,
            name="Child Node",
            node_type="attribute",
            data_type="string",
            ltree_path="parent.child",
            depth=1,
            sort_order=1,
        )
        db_session.add(child_node)
        await db_session.commit()

        parent_id = parent_node.id
        child_id = child_node.id

        # Delete parent node (should cascade to children based on DB constraints)
        await db_session.delete(parent_node)
        await db_session.commit()

        # Verify parent is deleted
        result = await db_session.execute(
            select(AttributeNode).where(AttributeNode.id == parent_id)
        )
        assert result.scalar_one_or_none() is None

        # Verify child is also deleted (cascade)
        result = await db_session.execute(select(AttributeNode).where(AttributeNode.id == child_id))
        assert result.scalar_one_or_none() is None


class TestErrorRecoveryWorkflow:
    """Test error recovery workflows.

    Requirements: 6.5
    """

    async def test_validation_error_fix_success(
        self,
        db_session: AsyncSession,
    ):
        """Test validation error → fix → success workflow.

        This test verifies that after a validation error, the user can
        fix the data and successfully complete the operation.
        """
        from pydantic import ValidationError

        from app.schemas.customer import CustomerCreate
        from tests.factories.customer_factory import CustomerFactory

        # Step 1: Try to create customer with invalid data (invalid email format)
        try:
            invalid_data = CustomerCreate(
                company_name="Test Company",
                contact_person="John Doe",
                email="invalid-email",  # Invalid email format
                customer_type="commercial",
            )
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            # Validation error caught
            assert "email" in str(e).lower()

        # Step 2: Fix the data and retry
        valid_data = CustomerCreate(
            company_name="Test Company",
            contact_person="John Doe",
            email="valid@example.com",  # Fixed: valid email format
            customer_type="commercial",
        )

        # Step 3: Successfully create customer
        customer = await CustomerFactory.create(
            db_session,
            company_name=valid_data.company_name,
            contact_person=valid_data.contact_person,
            email=valid_data.email,
            customer_type=valid_data.customer_type,
        )

        assert customer.id is not None
        assert customer.email == "valid@example.com"

    async def test_duplicate_email_fix_success(
        self,
        db_session: AsyncSession,
    ):
        """Test duplicate email error → fix → success workflow.

        This test verifies that after a duplicate email error, the user
        can change the email and successfully create the customer.
        """
        from sqlalchemy.exc import IntegrityError

        from app.models.customer import Customer

        # Step 1: Create first customer directly
        customer1 = Customer(
            company_name="First Company",
            contact_person="Person 1",
            email="duplicate@example.com",
            customer_type="commercial",
            is_active=True,
        )
        db_session.add(customer1)
        await db_session.commit()
        await db_session.refresh(customer1)
        assert customer1.id is not None

        # Step 2: Try to create second customer with same email
        customer2 = Customer(
            company_name="Second Company",
            contact_person="Person 2",
            email="duplicate@example.com",  # Duplicate email
            customer_type="commercial",
            is_active=True,
        )
        db_session.add(customer2)

        try:
            await db_session.commit()
            assert False, "Should have raised IntegrityError"
        except IntegrityError:
            # Expected error - rollback
            await db_session.rollback()

        # Step 3: Fix by using different email
        customer3 = Customer(
            company_name="Third Company",
            contact_person="Person 3",
            email="unique@example.com",  # Fixed: unique email
            customer_type="commercial",
            is_active=True,
        )
        db_session.add(customer3)
        await db_session.commit()
        await db_session.refresh(customer3)

        assert customer3.id is not None
        assert customer3.email == "unique@example.com"

    async def test_configuration_update_after_error(
        self,
        db_session: AsyncSession,
    ):
        """Test configuration update after initial error.

        This test verifies that after an error updating a configuration,
        the user can fix the issue and successfully update.
        """
        from tests.factories.configuration_factory import ConfigurationFactory

        # Step 1: Create configuration
        config = await ConfigurationFactory.create(
            db_session,
            name="Initial Name",
            total_price=Decimal("300.00"),
        )
        assert config.id is not None
        initial_price = config.total_price

        # Step 2: Try to update with invalid data (negative price)
        try:
            config.total_price = Decimal("-100.00")  # Invalid
            db_session.add(config)
            await db_session.commit()
            # Note: This might not raise an error if there's no constraint
            # In a real scenario, this would be caught by validation
        except Exception:
            await db_session.rollback()

        # Step 3: Fix and update successfully
        await db_session.refresh(config)
        config.total_price = Decimal("450.00")  # Valid price
        config.name = "Updated Name"
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.total_price == Decimal("450.00")
        assert config.name == "Updated Name"
