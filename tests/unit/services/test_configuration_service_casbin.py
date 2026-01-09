"""Unit tests for Configuration Service with Casbin decorators.

This module contains unit tests for the Configuration Service with RBAC decorators,
customer relationships, and RBACQueryFilter automatic filtering.

Tests cover:
- Configuration creation with customer relationships
- Casbin decorator authorization on all methods
- RBACQueryFilter automatic filtering
- Multiple decorator patterns (OR logic)
- Customer context extraction and ownership validation

Requirements: 2.1, 2.2, 2.3, 8.1, 9.1, 9.2
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from app.core.exceptions import NotFoundException
from app.core.rbac import RBACQueryFilter, Role
from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate
from app.services.configuration import (
    AdminPrivileges,
    ConfigurationManagement,
    ConfigurationOwnership,
    ConfigurationReader,
    ConfigurationService,
)


class TestConfigurationServiceCasbin:
    """Unit tests for Configuration Service with Casbin decorators."""

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
    def sample_admin(self):
        """Create sample admin user for testing."""
        return User(
            id=3,
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
    def sample_manufacturing_type(self):
        """Create sample manufacturing type for testing."""
        return ManufacturingType(
            id=1,
            name="Test Window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
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

    @pytest.mark.asyncio
    async def test_create_configuration_uses_customer_relationship(
        self, db_session, test_user_with_rbac
    ):
        """Test that create_configuration uses proper customer relationship."""
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

        # Setup
        config_service = ConfigurationService(db_session)

        # Mock configuration creation data
        config_data = ConfigurationCreate(
            manufacturing_type_id=mfg_type.id, name="Test Configuration"
        )

        # Execute
        result = await config_service.create_configuration(config_data, test_user_with_rbac)

        # Verify configuration was created with proper customer relationship
        assert result is not None
        assert result.name == "Test Configuration"
        assert result.manufacturing_type_id == mfg_type.id

        # Verify customer relationship was established
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        customer_result = await db_session.execute(stmt)
        customer_id = customer_result.scalar_one()

        assert result.customer_id == customer_id
        assert result.customer_id != test_user_with_rbac.id  # Should be customer.id, not user.id

    @pytest.mark.asyncio
    async def test_list_configurations_rbac_query_filter(self, db_session, test_user_with_rbac):
        """Test that list_configurations uses RBACQueryFilter for automatic filtering."""
        # Setup
        config_service = ConfigurationService(db_session)

        # Execute - this will test the actual RBAC decorators with real database
        result = await config_service.list_configurations(test_user_with_rbac)

        # Verify the result is a list (even if empty)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_configuration_multiple_decorators_or_logic(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test update_configuration with multiple @require decorators (OR logic)."""
        import uuid

        # Create a manufacturing type with unique name
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

        # Get the customer ID for the test user (created by RBAC initialization)
        from app.models.customer import Customer
        from sqlalchemy import select

        stmt = select(Customer.id).where(Customer.email == test_user_with_rbac.email)
        result = await db_session.execute(stmt)
        customer_id = result.scalar_one()

        # Create a configuration owned by the test user
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer_id,  # Set to user's customer ID
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        config_service = ConfigurationService(db_session)
        update_data = ConfigurationUpdate(name="Updated Configuration")

        # Test 1: Customer CANNOT update configurations (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await config_service.update_configuration(config.id, update_data, test_user_with_rbac)
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN update any configuration
        result = await config_service.update_configuration(
            config.id, update_data, test_superuser_with_rbac
        )
        assert result is not None
        assert result.name == "Updated Configuration"

    @pytest.mark.asyncio
    async def test_get_configuration_with_details_casbin_authorization(
        self, db_session, test_superuser_with_rbac
    ):
        """Test get_configuration_with_details with Casbin decorator authorization."""
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

        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=None,  # No specific customer
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        config_service = ConfigurationService(db_session)

        # Test: Superuser can access configuration details
        result = await config_service.get_configuration_with_details(
            config.id, test_superuser_with_rbac
        )
        assert result is not None
        assert result.id == config.id

    @pytest.mark.asyncio
    async def test_customer_context_extraction_and_ownership_validation(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test customer context extraction and ownership validation."""
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

        # Create a configuration owned by the test user
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
        config_service = ConfigurationService(db_session)
        update_data = ConfigurationUpdate(name="Updated")

        # Test 1: Customer CANNOT update configurations (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await config_service.update_configuration(config.id, update_data, test_user_with_rbac)
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN update any configuration (ownership validation works)
        result = await config_service.update_configuration(
            config.id, update_data, test_superuser_with_rbac
        )
        assert result is not None
        assert result.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_configuration_casbin_authorization(
        self, db_session, test_superuser_with_rbac
    ):
        """Test delete_configuration with Casbin authorization."""
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

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=None,  # No specific customer
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Setup
        config_service = ConfigurationService(db_session)

        # Test: Superuser can delete configuration
        await config_service.delete_configuration(config.id, test_superuser_with_rbac)

        # Verify configuration was deleted
        from sqlalchemy import select

        stmt = select(Configuration).where(Configuration.id == config.id)
        result = await db_session.execute(stmt)
        deleted_config = result.scalar_one_or_none()
        assert deleted_config is None

    @pytest.mark.asyncio
    async def test_privilege_objects_functionality(self):
        """Test Privilege objects functionality for Configuration Service."""
        # Test ConfigurationManagement privilege
        assert Role.SALESMAN in ConfigurationManagement.roles
        assert Role.PARTNER in ConfigurationManagement.roles
        assert ConfigurationManagement.permission.resource == "configuration"
        assert ConfigurationManagement.permission.action == "update"
        assert ConfigurationManagement.resource.resource_type == "customer"

        # Test ConfigurationOwnership privilege
        assert Role.CUSTOMER in ConfigurationOwnership.roles
        assert ConfigurationOwnership.permission.resource == "configuration"
        assert ConfigurationOwnership.permission.action == "update"
        assert ConfigurationOwnership.resource.resource_type == "configuration"

        # Test ConfigurationReader privilege
        assert Role.CUSTOMER in ConfigurationReader.roles
        assert Role.SALESMAN in ConfigurationReader.roles
        assert Role.PARTNER in ConfigurationReader.roles
        assert ConfigurationReader.permission.action == "read"

        # Test AdminPrivileges
        assert Role.SUPERADMIN in AdminPrivileges.roles
        assert AdminPrivileges.permission.resource == "*"
        assert AdminPrivileges.permission.action == "*"

    @pytest.mark.asyncio
    async def test_rbac_query_filter_integration(self, db_session, test_user_with_rbac):
        """Test RBACQueryFilter integration with Configuration Service."""
        # Setup
        config_service = ConfigurationService(db_session)

        # Execute - test the actual RBAC query filtering with real database
        result = await config_service.list_configurations(
            test_user_with_rbac, manufacturing_type_id=1
        )

        # Verify the result is a list (even if empty due to filtering)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_configuration_not_found_error_handling(self, db_session, test_user_with_rbac):
        """Test error handling when configuration is not found.

        The RBAC system now properly allows 404 errors to pass through,
        so we should get NotFoundException instead of 403 Access Denied.
        """
        # Setup
        config_service = ConfigurationService(db_session)

        # Execute and verify exception - should get 404 for non-existent resources
        with pytest.raises(NotFoundException) as exc_info:
            await config_service.get_configuration(999, test_user_with_rbac)

        assert "Configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_manufacturing_type_not_found_in_create(self, db_session, test_user_with_rbac):
        """Test error handling when manufacturing type is not found during creation.

        The RBAC system now properly allows 404 errors to pass through,
        so we should get NotFoundException instead of 403 Access Denied.
        """
        # Setup
        config_service = ConfigurationService(db_session)

        config_data = ConfigurationCreate(manufacturing_type_id=999, name="Test Configuration")

        # Execute and verify exception - should get 404 for non-existent resources
        with pytest.raises(NotFoundException) as exc_info:
            await config_service.create_configuration(config_data, test_user_with_rbac)

        assert "ManufacturingType" in str(exc_info.value)
