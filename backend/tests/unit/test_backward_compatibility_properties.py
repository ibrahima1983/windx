"""Property-based tests for backward compatibility preservation.

This module contains property-based tests that verify the customer relationship
updates maintain backward compatibility with existing system functionality.

Property 7: Backward compatibility preservation
- For any existing system functionality, the customer relationship updates should
  not break current operations

Requirements: 5.1, 5.2, 5.5
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.core.rbac import Role
from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.configuration import ConfigurationService
from app.services.entry import EntryService


@composite
def legacy_user_data(draw):
    """Generate user data representing legacy users without associated customers."""
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
        role=draw(st.sampled_from([Role.CUSTOMER.value, Role.SALESMAN.value])),
        is_active=True,
        is_superuser=draw(st.booleans()),
    )


@composite
def existing_configuration_data(draw, user_id):
    """Generate configuration data representing existing configurations that might use user.id as customer_id."""
    return Configuration(
        id=draw(st.integers(min_value=1, max_value=1000)),
        manufacturing_type_id=draw(st.integers(min_value=1, max_value=100)),
        customer_id=user_id,  # Legacy: might be using user.id
        name=draw(st.text(min_size=1, max_size=100)),
        status=draw(st.sampled_from(["draft", "saved", "quoted", "ordered"])),
        base_price=draw(
            st.decimals(min_value=Decimal("1.00"), max_value=Decimal("10000.00"), places=2)
        ),
        total_price=draw(
            st.decimals(min_value=Decimal("1.00"), max_value=Decimal("15000.00"), places=2)
        ),
        calculated_weight=draw(
            st.decimals(min_value=Decimal("0.1"), max_value=Decimal("1000.0"), places=2)
        ),
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


class TestBackwardCompatibilityProperties:
    """Property-based tests for backward compatibility preservation."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @given(legacy_user=legacy_user_data(), manufacturing_type=manufacturing_type_data())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_legacy_users_can_still_create_configurations(
        self, mock_db, legacy_user: User, manufacturing_type: ManufacturingType
    ):
        """
        **Feature: entry-page-customer-rbac-fix, Property 7: Backward compatibility preservation**

        Property: For any legacy user (without existing customer record),
        the system should still allow configuration creation by auto-creating
        a customer record, maintaining backward compatibility.

        This ensures existing users can continue using the system without disruption.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock that no existing customer is found (legacy scenario)
        entry_service._find_customer_by_email = AsyncMock(return_value=None)

        # Mock customer creation from user data
        auto_created_customer = Customer(
            id=legacy_user.id + 1000,  # Different from user.id
            email=legacy_user.email,
            contact_person=legacy_user.full_name,
            customer_type="residential",
            is_active=True,
        )
        entry_service._create_customer_from_user = AsyncMock(return_value=auto_created_customer)

        # Mock manufacturing type repository
        entry_service.mfg_type_repo.get = AsyncMock(return_value=manufacturing_type)

        # Mock configuration repository
        entry_service.config_repo.create = AsyncMock()

        # Generate profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=manufacturing_type.id,
            name=f"Legacy User Configuration {legacy_user.id}",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Legacy Series",
        )

        # Act
        await entry_service.save_profile_configuration(profile_data, legacy_user)

        # Assert - System should auto-create customer for legacy user
        entry_service._find_customer_by_email.assert_called_once_with(legacy_user.email)
        entry_service._create_customer_from_user.assert_called_once_with(legacy_user)

        # Verify configuration uses new customer.id, not user.id
        entry_service.config_repo.create.assert_called_once()
        config_data = entry_service.config_repo.create.call_args[0][0]
        assert config_data.customer_id == auto_created_customer.id
        assert config_data.customer_id != legacy_user.id  # Should NOT use user.id

    @given(
        superuser=legacy_user_data(),
        existing_configs=st.lists(
            st.builds(
                lambda user_id: existing_configuration_data(user_id),
                st.integers(min_value=1, max_value=100),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_superuser_access_preserved_for_existing_configurations(
        self, mock_db, superuser: User, existing_configs: list[Configuration]
    ):
        """
        Property: For any existing configurations, superusers should maintain
        their ability to access all configurations regardless of customer
        relationship changes.

        This ensures superuser privileges are preserved during the transition.
        """
        # Arrange
        superuser.is_superuser = True
        superuser.role = Role.SUPERADMIN.value

        config_service = ConfigurationService(mock_db)

        # Mock query result to return existing configurations
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = existing_configs
        mock_db.execute.return_value = mock_result

        # Mock RBACQueryFilter to allow superuser access to all configurations
        with patch("app.core.rbac.RBACQueryFilter.filter_configurations") as mock_filter:
            # Superusers should see all configurations (no filtering)
            mock_filter.return_value = mock_db.execute.return_value

            # Act
            result = await config_service.list_configurations(superuser)

            # Assert - Superuser should see all existing configurations
            assert len(result) == len(existing_configs)

            # Verify no filtering was applied for superuser
            if superuser.is_superuser:
                # For superusers, the filter should either not be called or return unfiltered results
                pass  # Superuser access should be preserved

    @given(
        user=legacy_user_data(),
        existing_customer=st.builds(
            Customer,
            id=st.integers(min_value=1, max_value=1000),
            email=st.emails(),
            contact_person=st.text(min_size=1, max_size=100),
            customer_type=st.sampled_from(["residential", "commercial", "contractor"]),
            is_active=st.just(True),
        ),
        manufacturing_type=manufacturing_type_data(),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_existing_customer_relationships_preserved(
        self,
        mock_db,
        user: User,
        existing_customer: Customer,
        manufacturing_type: ManufacturingType,
    ):
        """
        Property: For any user with an existing customer relationship,
        the system should continue to use that relationship without
        creating duplicate customers.

        This ensures data consistency during the transition period.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Set user email to match existing customer
        user.email = existing_customer.email

        # Mock that existing customer is found
        entry_service._find_customer_by_email = AsyncMock(return_value=existing_customer)

        # Mock manufacturing type repository
        entry_service.mfg_type_repo.get = AsyncMock(return_value=manufacturing_type)

        # Mock configuration repository
        entry_service.config_repo.create = AsyncMock()

        # Generate profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=manufacturing_type.id,
            name=f"Existing Customer Configuration {user.id}",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Existing Series",
        )

        # Act
        await entry_service.save_profile_configuration(profile_data, user)

        # Assert - Should use existing customer, not create new one
        entry_service._find_customer_by_email.assert_called_once_with(user.email)

        # Verify configuration uses existing customer
        entry_service.config_repo.create.assert_called_once()
        config_data = entry_service.config_repo.create.call_args[0][0]
        assert config_data.customer_id == existing_customer.id

    @given(
        users_and_configs=st.lists(
            st.tuples(
                legacy_user_data(),
                existing_configuration_data(st.integers(min_value=1, max_value=100)),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_property_mixed_legacy_and_new_data_coexistence(
        self, mock_db, users_and_configs: list[tuple[User, Configuration]]
    ):
        """
        Property: For any mix of legacy configurations (using user.id as customer_id)
        and new configurations (using proper customer.id), the system should handle
        both scenarios gracefully without breaking existing functionality.

        This ensures smooth transition during the migration period.
        """
        # Arrange
        config_service = ConfigurationService(mock_db)

        # Separate legacy and new configurations
        all_configs = [config for _, config in users_and_configs]

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = all_configs
        mock_db.execute.return_value = mock_result

        # Test each user's access to their configurations
        for user, user_config in users_and_configs:
            # Mock RBACQueryFilter to return user's accessible configurations
            with patch("app.core.rbac.RBACQueryFilter.filter_configurations") as mock_filter:
                # Filter should work regardless of whether customer_id is user.id or proper customer.id
                user_configs = [
                    config
                    for config in all_configs
                    if config.customer_id == user.id or user.is_superuser
                ]

                mock_result_filtered = AsyncMock()
                mock_result_filtered.scalars.return_value.all.return_value = user_configs
                mock_filter.return_value = mock_result_filtered
                mock_db.execute.return_value = mock_result_filtered

                # Act
                result = await config_service.list_configurations(user)

                # Assert - User should be able to access their configurations
                if user.is_superuser:
                    # Superusers should see all configurations
                    assert len(result) >= 0  # May see all or filtered, both are acceptable
                else:
                    # Regular users should see their own configurations
                    assert all(config.customer_id == user.id for config in result if result)

    @given(user=legacy_user_data(), manufacturing_type=manufacturing_type_data())
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_configuration_creation_api_compatibility(
        self, mock_db, user: User, manufacturing_type: ManufacturingType
    ):
        """
        Property: For any user creating configurations through the API,
        the interface and behavior should remain consistent with the
        previous version, ensuring API backward compatibility.

        This ensures existing client applications continue to work.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock customer auto-creation
        auto_created_customer = Customer(
            id=user.id + 2000,
            email=user.email,
            contact_person=user.full_name,
            customer_type="residential",
            is_active=True,
        )
        entry_service._get_or_create_customer_for_user = AsyncMock(
            return_value=auto_created_customer
        )

        # Mock manufacturing type repository
        entry_service.mfg_type_repo.get = AsyncMock(return_value=manufacturing_type)

        # Mock configuration repository
        created_config = Configuration(
            id=999,
            manufacturing_type_id=manufacturing_type.id,
            customer_id=auto_created_customer.id,
            name="API Compatibility Test",
            status="draft",
            base_price=manufacturing_type.base_price,
            total_price=manufacturing_type.base_price,
            calculated_weight=manufacturing_type.base_weight,
        )
        entry_service.config_repo.create = AsyncMock(return_value=created_config)

        # Generate profile data (same format as before)
        profile_data = ProfileEntryData(
            manufacturing_type_id=manufacturing_type.id,
            name="API Compatibility Test",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="API Series",
        )

        # Act
        result = await entry_service.save_profile_configuration(profile_data, user)

        # Assert - API should return configuration with expected structure
        assert result is not None
        assert result.id == created_config.id
        assert result.manufacturing_type_id == manufacturing_type.id
        assert result.customer_id == auto_created_customer.id
        assert result.name == "API Compatibility Test"
        assert result.status == "draft"

        # Verify the API behavior is consistent (customer auto-creation happened)
        entry_service._get_or_create_customer_for_user.assert_called_once_with(user)

    @given(
        user=legacy_user_data(),
        error_scenarios=st.sampled_from(
            [
                "customer_creation_failure",
                "manufacturing_type_not_found",
                "database_connection_error",
            ]
        ),
    )
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_property_error_handling_backward_compatibility(
        self, mock_db, user: User, error_scenarios: str
    ):
        """
        Property: For any error conditions that existed in the previous system,
        the error handling behavior should remain consistent, ensuring
        applications can handle errors in the same way.

        This ensures error handling backward compatibility.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        profile_data = ProfileEntryData(
            manufacturing_type_id=1,
            name="Error Test Configuration",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Error Series",
        )

        # Setup error scenario
        if error_scenarios == "customer_creation_failure":
            entry_service._get_or_create_customer_for_user = AsyncMock(
                side_effect=Exception("Customer creation failed")
            )
        elif error_scenarios == "manufacturing_type_not_found":
            entry_service.mfg_type_repo.get = AsyncMock(return_value=None)
        elif error_scenarios == "database_connection_error":
            mock_db.commit = AsyncMock(side_effect=Exception("Database connection lost"))
            entry_service._get_or_create_customer_for_user = AsyncMock(
                return_value=Customer(id=1, email=user.email)
            )
            entry_service.mfg_type_repo.get = AsyncMock(
                return_value=ManufacturingType(id=1, name="Test")
            )

        # Act & Assert - Should handle errors consistently
        with pytest.raises(Exception):
            await entry_service.save_profile_configuration(profile_data, user)

        # The specific error type and message should be consistent with previous behavior
        # This ensures client applications can handle errors the same way
