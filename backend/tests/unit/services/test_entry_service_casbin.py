"""Unit tests for Entry Service with Casbin decorators.

This module contains unit tests for the Entry Service with RBAC decorators,
customer auto-creation, and Privilege object evaluation.

Tests cover:
- Customer auto-creation with various user data
- Casbin decorator authorization on Entry Service methods
- Privilege object evaluation
- Customer lookup by email
- Error handling for duplicate emails and constraint violations
- Customer data mapping from user fields

Requirements: 1.1, 1.3, 1.4, 8.1, 8.2, 9.3
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DatabaseException, NotFoundException, CustomerCreationException
from app.core.rbac import Role
from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import AdminAccess, ConfigurationCreator, ConfigurationViewer, EntryService
from app.services.rbac import RBACService


class TestEntryServiceCasbin:
    """Unit tests for Entry Service with Casbin decorators."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()  # Use MagicMock for synchronous methods
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
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
    def sample_customer(self):
        """Create sample customer for testing."""
        return Customer(
            id=100,
            email="test@example.com",
            contact_person="Test User",
            customer_type="residential",
            is_active=True,
            notes="Auto-created from user: testuser",
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
    def sample_profile_data(self):
        """Create sample profile entry data for testing."""
        return ProfileEntryData(
            manufacturing_type_id=1,
            name="Test Configuration",
            type="window",
            material="Aluminum",  # Required field
            opening_system="Casement",  # Required field
            system_series="Series100",  # Required field
        )

    @pytest.mark.asyncio
    async def test_customer_auto_creation_with_full_name(self, mock_db, sample_user):
        """Test customer auto-creation with user having full name."""
        # Setup
        rbac_service = RBACService(mock_db)

        # Mock no existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(
            return_value=None
        )  # Use MagicMock, not AsyncMock
        mock_db.execute.return_value = mock_result

        # Mock service methods instead of db methods
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        # Mock refresh to set the ID
        async def mock_refresh_side_effect(obj):
            if isinstance(obj, Customer):
                obj.id = 100

        rbac_service.refresh.side_effect = mock_refresh_side_effect

        # Execute
        customer = await rbac_service.get_or_create_customer_for_user(sample_user)

        # Verify customer creation
        mock_db.add.assert_called_once()
        added_customer = mock_db.add.call_args[0][0]

        assert added_customer.email == sample_user.email
        assert added_customer.contact_person == sample_user.full_name
        assert added_customer.customer_type == "residential"
        assert added_customer.is_active is True
        assert "Auto-created from user:" in added_customer.notes

        # Verify service methods were called
        rbac_service.commit.assert_called_once()
        rbac_service.refresh.assert_called_once_with(added_customer)

    @pytest.mark.asyncio
    async def test_customer_auto_creation_with_username_fallback(self, mock_db):
        """Test customer auto-creation when user has no full name."""
        # Setup user without full name
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            full_name=None,  # No full name
            role=Role.CUSTOMER.value,
            is_active=True,
        )

        rbac_service = RBACService(mock_db)

        # Mock no existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(
            return_value=None
        )  # Use MagicMock, not AsyncMock
        mock_db.execute.return_value = mock_result

        # Mock service methods
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        # Execute
        customer = await rbac_service.get_or_create_customer_for_user(user)

        # Verify fallback to username
        mock_db.add.assert_called_once()
        added_customer = mock_db.add.call_args[0][0]

        assert added_customer.contact_person == user.username

    @pytest.mark.asyncio
    async def test_customer_lookup_by_email_existing(self, mock_db, sample_user, sample_customer):
        """Test customer lookup when customer already exists."""
        # Setup
        rbac_service = RBACService(mock_db)

        # Mock existing customer found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(
            return_value=sample_customer
        )  # Use MagicMock, not AsyncMock
        mock_db.execute.return_value = mock_result

        # Execute
        customer = await rbac_service.get_or_create_customer_for_user(sample_user)

        # Verify existing customer returned
        assert customer == sample_customer
        mock_db.add.assert_not_called()  # Should not create new customer

    @pytest.mark.asyncio
    async def test_customer_creation_integrity_error_race_condition(
        self, mock_db, sample_user, sample_customer
    ):
        """Test handling of race condition during customer creation."""
        # Setup
        rbac_service = RBACService(mock_db)

        # Mock the _find_customer_by_email method directly to simulate race condition
        # First call returns None, second call (after IntegrityError) returns customer
        rbac_service._find_customer_by_email = AsyncMock(
            side_effect=[
                None,  # First call - no customer found
                sample_customer,  # Second call (in exception handler) - customer found
            ]
        )

        # Mock service methods - commit fails with IntegrityError (unique constraint)
        rbac_service.commit = AsyncMock(
            side_effect=IntegrityError("unique constraint email", None, None)
        )
        rbac_service.rollback = AsyncMock()

        # Execute
        customer = await rbac_service.get_or_create_customer_for_user(sample_user)

        # Verify race condition handled gracefully
        assert customer == sample_customer
        rbac_service.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_customer_creation_integrity_error_no_recovery(self, mock_db, sample_user):
        """Test handling of IntegrityError when customer still not found after rollback."""
        # Setup
        rbac_service = RBACService(mock_db)

        # Mock the _find_customer_by_email method to always return None (no recovery)
        rbac_service._find_customer_by_email = AsyncMock(return_value=None)

        # Mock service methods - commit fails with IntegrityError
        rbac_service.commit = AsyncMock(side_effect=IntegrityError("some other error", None, None))
        rbac_service.rollback = AsyncMock()

        # Execute and verify exception
        with pytest.raises(CustomerCreationException):
            await rbac_service.get_or_create_customer_for_user(sample_user)

        rbac_service.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_profile_configuration_casbin_decorator_authorization(
        self, mock_db, sample_user, sample_customer, sample_manufacturing_type, sample_profile_data
    ):
        """Test save_profile_configuration method (decorators currently commented out)."""
        # Setup
        entry_service = EntryService(mock_db)

        # Mock RBAC service
        mock_rbac_service = AsyncMock()
        mock_rbac_service.get_or_create_customer_for_user.return_value = sample_customer
        entry_service.rbac_service = mock_rbac_service

        # Mock manufacturing type query and attribute nodes query
        # First call returns manufacturing type, second call returns attribute nodes
        mock_result_1 = AsyncMock()
        mock_result_1.scalar_one_or_none = MagicMock(return_value=sample_manufacturing_type)

        mock_result_2 = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])  # Empty list of attribute nodes
        mock_result_2.scalars = MagicMock(return_value=mock_scalars)

        mock_db.execute.side_effect = [mock_result_1, mock_result_2]

        # Mock validation
        entry_service.validate_profile_data = AsyncMock()

        # Execute (decorators are currently commented out, so no authorization check)
        result = await entry_service.save_profile_configuration(sample_profile_data, sample_user)

        # Verify configuration was created
        assert result is not None
        assert result.name == sample_profile_data.name
        assert result.customer_id == sample_customer.id

    @pytest.mark.asyncio
    async def test_save_profile_configuration_uses_customer_id(
        self, mock_db, sample_user, sample_customer, sample_manufacturing_type, sample_profile_data
    ):
        """Test that save_profile_configuration uses customer.id instead of user.id."""
        # Setup
        entry_service = EntryService(mock_db)

        # Mock RBAC service
        mock_rbac_service = AsyncMock()
        mock_rbac_service.get_or_create_customer_for_user.return_value = sample_customer
        entry_service.rbac_service = mock_rbac_service

        # Mock manufacturing type query and attribute nodes query
        # First call returns manufacturing type, second call returns attribute nodes
        mock_result_1 = AsyncMock()
        mock_result_1.scalar_one_or_none = MagicMock(return_value=sample_manufacturing_type)

        mock_result_2 = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])  # Empty list of attribute nodes
        mock_result_2.scalars = MagicMock(return_value=mock_scalars)

        mock_db.execute.side_effect = [mock_result_1, mock_result_2]

        # Mock validation
        entry_service.validate_profile_data = AsyncMock()

        # Execute
        await entry_service.save_profile_configuration(sample_profile_data, sample_user)

        # Verify configuration uses customer.id, not user.id
        mock_db.add.assert_called()
        added_config = mock_db.add.call_args_list[0][0][0]  # First call, first arg

        assert isinstance(added_config, Configuration)
        assert added_config.customer_id == sample_customer.id
        assert added_config.customer_id != sample_user.id

    @pytest.mark.asyncio
    async def test_generate_preview_data_multiple_decorators(self, mock_db, test_user_with_rbac):
        """Test generate_preview_data with multiple @require decorators (OR logic)."""
        from datetime import datetime
        from app.schemas.entry import PreviewTable

        # Setup
        entry_service = EntryService(mock_db)

        # Mock the configuration query that the method makes directly
        mock_config = Configuration(
            id=1, customer_id=195, name="Test Config", manufacturing_type_id=1
        )
        mock_config.selections = []
        mock_config.updated_at = datetime.now()  # Add required datetime field
        mock_result_config = AsyncMock()
        mock_result_config.scalar_one_or_none = MagicMock(return_value=mock_config)
        mock_db.execute.return_value = mock_result_config

        # Mock the RBAC ownership check to return True (user owns the configuration)
        with patch(
            "app.services.rbac.RBACService.check_resource_ownership", new_callable=AsyncMock
        ) as mock_ownership:
            mock_ownership.return_value = True

            # Mock the generate_preview_table method to return a proper PreviewTable
            mock_preview_table = PreviewTable(
                headers=["Name", "Value"], rows=[{"Name": "Test Config", "Value": "Test Value"}]
            )
            entry_service.generate_preview_table = MagicMock(return_value=mock_preview_table)

            # Execute
            result = await entry_service.generate_preview_data(1, test_user_with_rbac)

            # Verify method executed successfully
            assert result is not None
            assert result.configuration_id == 1
            assert result.table == mock_preview_table

            # Verify ownership check was called
            mock_ownership.assert_called_once_with(test_user_with_rbac, "configuration", 1)

    @pytest.mark.asyncio
    async def test_privilege_object_evaluation(self):
        """Test Privilege object functionality."""
        # Test ConfigurationCreator privilege
        assert Role.CUSTOMER in ConfigurationCreator.roles
        assert Role.SALESMAN in ConfigurationCreator.roles
        assert Role.PARTNER in ConfigurationCreator.roles
        assert ConfigurationCreator.permission.resource == "configuration"
        assert ConfigurationCreator.permission.action == "create"

        # Test ConfigurationViewer privilege
        assert ConfigurationViewer.resource is not None
        assert ConfigurationViewer.resource.resource_type == "configuration"

        # Test AdminAccess privilege
        assert Role.SUPERADMIN in AdminAccess.roles
        assert AdminAccess.permission.resource == "*"
        assert AdminAccess.permission.action == "*"

    @pytest.mark.asyncio
    async def test_manufacturing_type_not_found_error(
        self, mock_db, sample_user, sample_profile_data
    ):
        """Test error handling when manufacturing type is not found."""
        # Setup
        entry_service = EntryService(mock_db)

        # Mock manufacturing type not found (should raise exception before second query)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Mock validation
        entry_service.validate_profile_data = AsyncMock()

        # Execute and verify exception
        with pytest.raises(NotFoundException) as exc_info:
            await entry_service.save_profile_configuration(sample_profile_data, sample_user)

        assert "Manufacturing type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_customer_data_mapping_from_user_fields(self, mock_db):
        """Test that customer data is correctly mapped from user fields."""
        # Setup user with various field combinations
        user = User(
            id=1,
            email="user@company.com",
            username="companyuser",
            full_name="Company User Name",
            role=Role.CUSTOMER.value,
            is_active=True,
        )

        rbac_service = RBACService(mock_db)

        # Mock no existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Mock service methods
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        # Execute
        customer = await rbac_service.get_or_create_customer_for_user(user)

        # Verify correct field mapping
        mock_db.add.assert_called_once()
        added_customer = mock_db.add.call_args[0][0]

        assert added_customer.email == user.email
        assert (
            added_customer.contact_person == user.full_name
        )  # Should use full_name when available
        assert added_customer.customer_type == "residential"  # Default for entry page users
        assert added_customer.is_active is True
        assert user.username in added_customer.notes
