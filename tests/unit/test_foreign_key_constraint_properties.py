"""Property-based tests for foreign key constraint satisfaction.

This module contains property-based tests that verify foreign key constraints
are satisfied when configurations are created through the entry service.

Property 5: Foreign key constraint satisfaction
- For any configuration saved through the entry service, the customer_id should
  satisfy database foreign key constraints

Requirements: 1.5, 2.1
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite
from sqlalchemy.exc import IntegrityError

from app.core.rbac import Role
from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import EntryService


@composite
def user_data(draw):
    """Generate valid user data for testing."""
    return User(
        id=draw(st.integers(min_value=1, max_value=1000)),
        email=draw(st.emails()),
        username=draw(
            st.text(
                min_size=3,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            )
        ),
        full_name=draw(st.text(min_size=1, max_size=50)),
        role=draw(st.sampled_from([Role.CUSTOMER.value, Role.SALESMAN.value, Role.PARTNER.value])),
        is_active=True,
        is_superuser=False,
    )


@composite
def customer_data(draw):
    """Generate valid customer data for testing."""
    return Customer(
        id=draw(st.integers(min_value=1, max_value=1000)),
        email=draw(st.emails()),
        contact_person=draw(st.text(min_size=1, max_size=100)),
        customer_type=draw(st.sampled_from(["residential", "commercial", "contractor"])),
        is_active=True,
    )


@composite
def manufacturing_type_data(draw):
    """Generate valid manufacturing type data for testing."""
    return ManufacturingType(
        id=draw(st.integers(min_value=1, max_value=100)),
        name=draw(st.text(min_size=1, max_size=100)),
        base_price=draw(
            st.decimals(min_value=Decimal("1.00"), max_value=Decimal("10000.00"), places=2)
        ),
        base_weight=draw(
            st.decimals(min_value=Decimal("0.1"), max_value=Decimal("1000.0"), places=2)
        ),
        is_active=True,
    )


@composite
def profile_entry_data(draw, manufacturing_type_id):
    """Generate valid profile entry data for testing."""
    return ProfileEntryData(
        manufacturing_type_id=manufacturing_type_id,
        name=draw(st.text(min_size=1, max_size=100)),
        type=draw(st.text(min_size=1, max_size=50)),
        material=draw(st.text(min_size=1, max_size=50)),
        opening_system=draw(st.text(min_size=1, max_size=50)),
        system_series=draw(st.text(min_size=1, max_size=50)),
    )


class TestForeignKeyConstraintProperties:
    """Property-based tests for foreign key constraint satisfaction."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @given(user=user_data(), customer=customer_data(), manufacturing_type=manufacturing_type_data())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_foreign_key_constraint_satisfaction(
        self, mock_db, user: User, customer: Customer, manufacturing_type: ManufacturingType
    ):
        """
        **Feature: entry-page-customer-rbac-fix, Property 5: Foreign key constraint satisfaction**

        Property: For any configuration saved through the entry service,
        the customer_id should satisfy database foreign key constraints.

        This property ensures that all configurations created through the entry service
        reference valid customer records, maintaining referential integrity.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock RBAC service customer auto-creation to return valid customer
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=customer
        )

        # Mock database queries for manufacturing type
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock service methods
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()
        mock_db.add = MagicMock()

        # Generate profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=manufacturing_type.id,
            name=f"Test Configuration {user.id}",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Test Series",
        )

        # Act
        result = await entry_service.save_profile_configuration(profile_data, user)

        # Assert - Verify customer relationship is used
        entry_service.rbac_service.get_or_create_customer_for_user.assert_called_once_with(user)

        # Verify configuration was added to database with proper customer_id
        mock_db.add.assert_called()

        # Get the configuration that was added
        added_config = mock_db.add.call_args[0][0]
        assert isinstance(added_config, Configuration)
        assert added_config.customer_id == customer.id
        assert added_config.customer_id is not None
        assert isinstance(added_config.customer_id, int)
        assert added_config.customer_id > 0

    @given(user=user_data(), manufacturing_type=manufacturing_type_data())
    @settings(
        max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_foreign_key_constraint_violation_handling(
        self, mock_db, user: User, manufacturing_type: ManufacturingType
    ):
        """
        Property: When foreign key constraints are violated, the entry service
        should handle the error gracefully and provide meaningful feedback.

        This ensures the system doesn't crash on constraint violations and
        provides proper error handling.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock customer auto-creation to return None (simulating constraint violation)
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(return_value=None)

        # Mock manufacturing type database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Generate profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=manufacturing_type.id,
            name=f"Test Configuration {user.id}",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Test Series",
        )

        # Act & Assert - Should handle None customer gracefully
        with pytest.raises(Exception):  # Should raise appropriate exception
            await entry_service.save_profile_configuration(profile_data, user)

    @given(user=user_data(), customer=customer_data(), manufacturing_type=manufacturing_type_data())
    @settings(
        max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_database_integrity_error_handling(
        self, mock_db, user: User, customer: Customer, manufacturing_type: ManufacturingType
    ):
        """
        Property: When database integrity errors occur during configuration creation,
        the entry service should handle them appropriately and not leave the system
        in an inconsistent state.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock customer auto-creation
        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=customer
        )

        # Mock manufacturing type lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
        mock_db.execute = MagicMock(return_value=mock_result)

        # Mock service methods
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()
        mock_db.add = MagicMock()

        # Mock database commit to raise IntegrityError
        mock_db.commit = AsyncMock(
            side_effect=IntegrityError("Foreign key constraint violation", None, None)
        )

        # Generate profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=manufacturing_type.id,
            name=f"Test Configuration {user.id}",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Test Series",
        )

        # Act & Assert - Should handle IntegrityError gracefully
        with pytest.raises(IntegrityError):
            await entry_service.save_profile_configuration(profile_data, user)

        # Verify customer lookup was still performed
        entry_service.rbac_service.get_or_create_customer_for_user.assert_called_once_with(user)

    @given(
        users=st.lists(user_data(), min_size=1, max_size=10),
        customer=customer_data(),
        manufacturing_type=manufacturing_type_data(),
    )
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_multiple_users_same_customer_constraint_satisfaction(
        self, mock_db, users: list[User], customer: Customer, manufacturing_type: ManufacturingType
    ):
        """
        Property: When multiple users are associated with the same customer,
        all their configurations should reference the same valid customer_id,
        maintaining foreign key constraint satisfaction.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock customer auto-creation to return same customer for all users
        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=customer
        )

        # Mock manufacturing type lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock service methods
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()
        mock_db.add = MagicMock()

        # Track configurations added
        added_configs = []
        mock_db.add = MagicMock(side_effect=lambda obj: added_configs.append(obj))

        # Act - Create configurations for all users
        for i, user in enumerate(users):
            profile_data = ProfileEntryData(
                manufacturing_type_id=manufacturing_type.id,
                name=f"Test Configuration {user.id}-{i}",
                type="Frame",
                material="Aluminum",
                opening_system="Casement",
                system_series="Test Series",
            )

            await entry_service.save_profile_configuration(profile_data, user)

        # Assert - All configurations should use the same valid customer_id
        assert len(added_configs) == len(users)

        for config in added_configs:
            assert isinstance(config, Configuration)
            assert config.customer_id == customer.id
            assert config.customer_id is not None
            assert isinstance(config.customer_id, int)

    @given(
        user=user_data(),
        customer=customer_data(),
        manufacturing_types=st.lists(manufacturing_type_data(), min_size=1, max_size=5),
    )
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_multiple_manufacturing_types_constraint_satisfaction(
        self, mock_db, user: User, customer: Customer, manufacturing_types: list[ManufacturingType]
    ):
        """
        Property: When configurations are created for different manufacturing types,
        all should maintain proper foreign key relationships to both customer and
        manufacturing_type tables.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock customer auto-creation
        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=customer
        )

        # Mock service methods
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()

        # Track configurations added
        added_configs = []
        mock_db.add = MagicMock(side_effect=lambda obj: added_configs.append(obj))

        # Act - Create configurations for different manufacturing types
        for i, mfg_type in enumerate(manufacturing_types):
            # Mock manufacturing type lookup for this specific type
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mfg_type)
            mock_db.execute = AsyncMock(return_value=mock_result)

            profile_data = ProfileEntryData(
                manufacturing_type_id=mfg_type.id,
                name=f"Test Configuration {mfg_type.id}-{i}",
                type="Frame",
                material="Aluminum",
                opening_system="Casement",
                system_series="Test Series",
            )

            await entry_service.save_profile_configuration(profile_data, user)

        # Assert - All configurations should have valid foreign key references
        assert len(added_configs) == len(manufacturing_types)

        for i, config in enumerate(added_configs):
            assert isinstance(config, Configuration)

            # Verify customer foreign key
            assert config.customer_id == customer.id
            assert config.customer_id is not None

            # Verify manufacturing type foreign key
            assert config.manufacturing_type_id == manufacturing_types[i].id
            assert config.manufacturing_type_id is not None
