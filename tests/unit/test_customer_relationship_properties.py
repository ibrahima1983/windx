"""Property-based tests for Customer Relationship system.

This module contains property-based tests that validate the core behaviors
of the Customer Relationship system using Hypothesis for comprehensive test coverage.

**Feature: entry-page-customer-rbac-fix, Property 1: Customer relationship integrity**
**Validates: Requirements 1.2, 1.5**

**Feature: entry-page-customer-rbac-fix, Property 2: User-customer mapping consistency**
**Validates: Requirements 1.1, 1.3, 1.4**

**Feature: entry-page-customer-rbac-fix, Property 4: Customer auto-creation idempotency**
**Validates: Requirements 1.4, 5.3**

**Feature: entry-page-customer-rbac-fix, Property 3: Authorization customer ownership with Casbin**
**Validates: Requirements 2.3, 7.1, 9.1**
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.rbac import Role
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import EntryService
from app.services.rbac import RBACService


# Hypothesis strategies for generating test data
@st.composite
def user_data(draw):
    """Generate valid user data for testing."""
    return {
        "id": draw(st.integers(min_value=1, max_value=10000)),
        "email": draw(st.emails()),
        "username": draw(
            st.text(
                min_size=3,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            )
        ),
        "full_name": draw(st.text(min_size=1, max_size=100)),
        "role": draw(st.sampled_from([role.value for role in Role])),
        "is_active": True,
        "is_superuser": draw(st.booleans()),
    }


@st.composite
def manufacturing_type_data(draw):
    """Generate valid manufacturing type data for testing."""
    return {
        "id": draw(st.integers(min_value=1, max_value=1000)),
        "name": draw(st.text(min_size=1, max_size=200)),
        "base_price": draw(
            st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2)
        ),
        "base_weight": draw(
            st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00"), places=2)
        ),
        "is_active": True,
    }


@st.composite
def profile_entry_data(draw):
    """Generate valid profile entry data for testing."""
    return ProfileEntryData(
        manufacturing_type_id=draw(st.integers(min_value=1, max_value=1000)),
        name=draw(st.text(min_size=1, max_size=200)),
        type=draw(st.text(min_size=1, max_size=50)),
        material=draw(st.sampled_from(["Aluminum", "Vinyl", "Wood"])),
        opening_system=draw(st.sampled_from(["Casement", "Sliding", "Double-hung"])),
        system_series=draw(st.sampled_from(["Kom800", "Series100", "Premium"])),
    )


class TestCustomerRelationshipProperties:
    """Property-based tests for Customer Relationship system correctness."""

    @pytest.mark.asyncio
    @given(
        user_data=user_data(),
        manufacturing_type_data=manufacturing_type_data(),
        profile_data=profile_entry_data(),
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_1_customer_relationship_integrity(
        self, user_data, manufacturing_type_data, profile_data
    ):
        """Property 1: Customer relationship integrity

        For any configuration created through the entry service, the customer_id field
        should reference a valid customer record, not a user record.

        **Validates: Requirements 1.2, 1.5**
        """
        # Create mock user
        user = User(**user_data)

        # Create mock manufacturing type
        manufacturing_type = ManufacturingType(**manufacturing_type_data)

        # Create mock customer that will be returned by RBAC service
        customer_data = {
            "id": user_data["id"] + 10000,  # Ensure customer.id != user.id
            "email": user_data["email"],
            "contact_person": user_data["full_name"] or user_data["username"],
            "customer_type": "residential",
            "is_active": True,
        }
        customer = Customer(**customer_data)

        # Mock database and services
        mock_db = AsyncMock()
        with patch("app.services.entry.select") as mock_select:
            # Setup mocks
            mock_db.execute = AsyncMock()
            mock_db.add = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock manufacturing type query (first call)
            mock_result_1 = AsyncMock()
            mock_result_1.scalar_one_or_none = MagicMock(return_value=manufacturing_type)

            # Mock attribute nodes query (second call)
            mock_result_2 = AsyncMock()
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=[])  # Empty list of attribute nodes
            mock_result_2.scalars = MagicMock(return_value=mock_scalars)

            # Set up side_effect for multiple database calls
            mock_db.execute.side_effect = [mock_result_1, mock_result_2]

            # Mock RBAC service
            mock_rbac_service = AsyncMock()
            mock_rbac_service.get_or_create_customer_for_user.return_value = customer

            # Create entry service
            entry_service = EntryService(mock_db)
            entry_service.rbac_service = mock_rbac_service

            # Mock validation to pass
            entry_service.validate_profile_data = AsyncMock()

            # Execute the method
            result = await entry_service.save_profile_configuration(profile_data, user)

            # Verify customer relationship integrity
            # The configuration should use customer.id, not user.id
            mock_db.add.assert_called_once()
            added_config = mock_db.add.call_args[0][0]

            # Property assertion: customer_id should reference customer record, not user record
            assert added_config.customer_id == customer.id
            assert added_config.customer_id != user.id

            # Verify RBAC service was called to get/create customer
            mock_rbac_service.get_or_create_customer_for_user.assert_called_once_with(user)

    @pytest.mark.asyncio
    @given(user_data=user_data())
    @settings(max_examples=100, deadline=None)
    async def test_property_2_user_customer_mapping_consistency(self, user_data):
        """Property 2: User-customer mapping consistency

        For any user who creates configurations, there should exist exactly one
        associated customer record with matching email.

        **Validates: Requirements 1.1, 1.3, 1.4**
        """
        # Create mock user
        user = User(**user_data)

        # Mock database
        mock_db = AsyncMock()

        # Create RBAC service
        rbac_service = RBACService(mock_db)

        # Mock database queries for customer lookup
        mock_result = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Test case 1: No existing customer - should create one
        mock_result.scalar_one_or_none = MagicMock(return_value=None)  # Use MagicMock

        customer = await rbac_service.get_or_create_customer_for_user(user)

        # Property assertion: Customer should be created with matching email
        mock_db.add.assert_called_once()
        created_customer = mock_db.add.call_args[0][0]
        assert created_customer.email == user.email
        assert created_customer.contact_person == (user.full_name or user.username)

        # Reset mocks for second test
        mock_db.reset_mock()

        # Test case 2: Existing customer - should return existing
        existing_customer = Customer(
            id=999,
            email=user.email,
            contact_person=user.full_name or user.username,
            customer_type="residential",
            is_active=True,
        )
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_customer)  # Use MagicMock

        customer = await rbac_service.get_or_create_customer_for_user(user)

        # Property assertion: Should return existing customer, not create new one
        assert customer == existing_customer
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    @given(user_data=user_data())
    @settings(max_examples=100, deadline=None)
    async def test_property_4_customer_auto_creation_idempotency(self, user_data):
        """Property 4: Customer auto-creation idempotency

        For any user, calling get_or_create_customer_for_user multiple times
        should return the same customer record.

        **Validates: Requirements 1.4, 5.3**
        """
        # Create mock user
        user = User(**user_data)

        # Mock database
        mock_db = AsyncMock()

        # Create RBAC service
        rbac_service = RBACService(mock_db)

        # Mock database queries
        mock_result = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create a customer that will be "found" on subsequent calls
        customer_data = {
            "id": 123,
            "email": user.email,
            "contact_person": user.full_name or user.username,
            "customer_type": "residential",
            "is_active": True,
        }
        customer = Customer(**customer_data)

        # First call: No existing customer, should create one
        mock_result.scalar_one_or_none = MagicMock(return_value=None)  # Use MagicMock

        # Mock the refresh to set the customer ID
        async def mock_refresh_side_effect(obj):
            if isinstance(obj, Customer):
                obj.id = 123

        mock_db.refresh.side_effect = mock_refresh_side_effect

        customer1 = await rbac_service.get_or_create_customer_for_user(user)

        # Verify customer was created
        mock_db.add.assert_called_once()

        # Reset mocks and setup for second call
        mock_db.reset_mock()
        mock_result.scalar_one_or_none = MagicMock(return_value=customer)  # Use MagicMock

        # Second call: Should find existing customer
        customer2 = await rbac_service.get_or_create_customer_for_user(user)

        # Property assertion: Idempotency - same customer returned
        assert customer2.email == customer1.email
        assert customer2.contact_person == customer1.contact_person

        # Should not create a new customer on second call
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    @given(user_data=user_data())
    @settings(max_examples=100, deadline=None)
    async def test_property_3_authorization_customer_ownership_with_casbin(self, user_data):
        """Property 3: Authorization customer ownership with Casbin

        For any configuration access attempt by a non-superuser, the user's
        associated customer should own the configuration.

        **Validates: Requirements 2.3, 7.1, 9.1**
        """
        # Create mock user (ensure not superuser for this test)
        user_data["role"] = Role.CUSTOMER.value
        user_data["is_superuser"] = False
        user = User(**user_data)

        # Mock database
        mock_db = AsyncMock()

        # Create RBAC service
        rbac_service = RBACService(mock_db)

        # Mock accessible customers
        customer_ids = [100, 200, 300]  # User has access to these customers
        rbac_service.get_accessible_customers = AsyncMock(return_value=customer_ids)

        # Test case 1: User owns the configuration (through customer relationship)
        config_customer_id = 100  # One of the accessible customers

        # Mock configuration lookup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=config_customer_id)  # Use MagicMock
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Check ownership
        has_access = await rbac_service.check_resource_ownership(user, "configuration", 123)

        # Property assertion: User should have access to configurations owned by their customers
        assert has_access is True

        # Test case 2: User does not own the configuration
        config_customer_id = 999  # Not in accessible customers
        mock_result.scalar_one_or_none = MagicMock(return_value=config_customer_id)  # Use MagicMock

        has_access = await rbac_service.check_resource_ownership(user, "configuration", 456)

        # Property assertion: User should not have access to configurations owned by other customers
        assert has_access is False

        # Test case 3: Superuser should have access to everything
        user.role = Role.SUPERADMIN.value
        user.is_superuser = True

        has_access = await rbac_service.check_resource_ownership(user, "configuration", 789)

        # Property assertion: Superuser should have access to all configurations
        assert has_access is True
