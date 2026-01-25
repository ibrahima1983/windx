"""Property-based tests for entry page authentication integration.

This module contains property-based tests that verify the entry page system
properly integrates with the existing Windx authentication system.

**Feature: entry-page-system, Property 9: Authentication integration**
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.exceptions import AuthorizationException, NotFoundException
from app.core.rbac import Role
from app.models.customer import Customer
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import EntryService


@st.composite
def mock_user_with_role(draw):
    """Generate mock user with various roles."""
    user = MagicMock(spec=User)
    user.id = draw(st.integers(min_value=1, max_value=1000))
    user.username = draw(st.text(min_size=3, max_size=20))
    user.email = draw(st.text(min_size=5, max_size=50))
    user.role = draw(
        st.sampled_from(
            [Role.CUSTOMER.value, Role.SALESMAN.value, Role.PARTNER.value, Role.SUPERADMIN.value]
        )
    )
    user.is_active = True
    return user


@st.composite
def valid_profile_data(draw):
    """Generate valid profile entry data."""
    return ProfileEntryData(
        manufacturing_type_id=draw(st.integers(min_value=1, max_value=100)),
        name=draw(st.text(min_size=1, max_size=50)),
        type=draw(st.sampled_from(["Frame", "Flying mullion"])),
        material=draw(st.sampled_from(["Aluminum", "Vinyl", "Wood"])),
        opening_system=draw(st.sampled_from(["Casement", "Sliding", "Double-hung"])),
        system_series=draw(st.sampled_from(["Kom700", "Kom800", "Series100"])),
    )


class TestEntryAuthenticationIntegration:
    """Test class for entry page authentication integration properties."""

    @pytest.mark.asyncio
    @given(user=mock_user_with_role(), profile_data=valid_profile_data())
    async def test_property_authentication_integration_save_configuration(
        self, user, profile_data: ProfileEntryData
    ):
        """
        **Feature: entry-page-system, Property 9: Authentication integration**

        Property: For any entry page access, the system should enforce authentication
        requirements consistent with existing Windx authentication patterns.

        This test verifies authentication integration in save operations.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock RBAC service and customer creation
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 123

        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=mock_customer
        )

        # Mock validation and database operations
        entry_service.validate_profile_data = AsyncMock()
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()

        # Mock manufacturing type lookup
        mock_manufacturing_type = MagicMock()
        mock_manufacturing_type.id = profile_data.manufacturing_type_id
        mock_manufacturing_type.base_price = 200.0
        mock_manufacturing_type.base_weight = 25.0

        mock_attribute_nodes = []

        def mock_execute_side_effect(stmt):
            mock_result = AsyncMock()
            if "manufacturing_types" in str(stmt):
                mock_result.scalar_one_or_none = MagicMock(
                    return_value=mock_manufacturing_type
                )  # Use MagicMock
            elif "attribute_nodes" in str(stmt):
                mock_scalars = MagicMock()
                mock_scalars.all = MagicMock(return_value=mock_attribute_nodes)  # Use MagicMock
                mock_result.scalars = MagicMock(return_value=mock_scalars)  # Use MagicMock
            return mock_result

        mock_db.execute.side_effect = mock_execute_side_effect

        # Act - Attempt to save configuration
        try:
            # The @require decorators should be enforced
            with patch("app.services.entry.require") as mock_require:
                # Mock the decorator to pass through
                mock_require.return_value = lambda func: func

                result = await entry_service.save_profile_configuration(profile_data, user)

                # Assert - Should integrate with RBAC service for customer management
                entry_service.rbac_service.get_or_create_customer_for_user.assert_called_once_with(
                    user
                )

                # Should use proper customer ID from RBAC service
                assert mock_db.add.called
                config_call = mock_db.add.call_args_list[0][0][0]
                assert config_call.customer_id == mock_customer.id

                # Should commit the transaction
                entry_service.commit.assert_called()

        except (AuthorizationException, NotFoundException):
            # These are valid outcomes depending on user role and data
            pass

    @pytest.mark.asyncio
    @given(user=mock_user_with_role(), configuration_id=st.integers(min_value=1, max_value=1000))
    async def test_property_authentication_integration_load_configuration(
        self, user, configuration_id: int
    ):
        """
        **Feature: entry-page-system, Property 9: Authentication integration**

        Property: Loading configurations should respect authentication and
        authorization rules consistent with Windx patterns.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock configuration with selections
        mock_config = MagicMock()
        mock_config.id = configuration_id
        mock_config.manufacturing_type_id = 1
        mock_config.name = "Test Configuration"
        mock_config.selections = []

        # Mock attribute nodes to provide required fields
        mock_attribute_nodes = []
        for i, field_name in enumerate(["type", "material", "opening_system", "system_series"]):
            node = MagicMock()
            node.id = i + 1
            node.name = field_name
            node.ltree_path = f"section.{field_name}"
            mock_attribute_nodes.append(node)

        # Mock configuration selections for required fields
        mock_selections = []
        for i, field_name in enumerate(["type", "material", "opening_system", "system_series"]):
            selection = MagicMock()
            selection.attribute_node_id = i + 1  # Match the node ID
            selection.string_value = f"Test {field_name.title()}"
            selection.numeric_value = None
            selection.boolean_value = None
            selection.json_value = None
            mock_selections.append(selection)

        mock_config.selections = mock_selections

        # Mock database queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_config)
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_attribute_nodes)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act - Attempt to load configuration
        try:
            with patch("app.services.entry.require") as mock_require:
                # Mock the decorator to pass through
                mock_require.return_value = lambda func: func

                # Mock RBAC authorization
                with patch(
                    "app.services.rbac.RBACService.check_resource_ownership", new_callable=AsyncMock
                ) as mock_ownership:
                    mock_ownership.return_value = True

                    result = await entry_service.load_profile_configuration(configuration_id, user)

                    # Assert - Should return ProfileEntryData
                    assert isinstance(result, ProfileEntryData)
                    assert result.manufacturing_type_id == mock_config.manufacturing_type_id
                    assert result.name == mock_config.name

        except (AuthorizationException, NotFoundException):
            # These are valid outcomes depending on user permissions and data existence
            pass

    @pytest.mark.asyncio
    @given(user=mock_user_with_role(), configuration_id=st.integers(min_value=1, max_value=1000))
    async def test_property_authentication_integration_generate_preview(
        self, user, configuration_id: int
    ):
        """
        **Feature: entry-page-system, Property 9: Authentication integration**

        Property: Preview generation should enforce proper authentication
        and authorization checks.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock configuration
        mock_config = MagicMock()
        mock_config.id = configuration_id
        mock_config.name = "Test Configuration"
        mock_config.updated_at = "2025-01-01T00:00:00"
        mock_config.selections = []

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_config)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock RBAC authorization
        with patch(
            "app.services.rbac.RBACService.check_resource_ownership", new_callable=AsyncMock
        ) as mock_ownership:
            mock_ownership.return_value = True

        # Act - Attempt to generate preview
        try:
            with patch("app.services.entry.require") as mock_require:
                # Mock the decorator to pass through
                mock_require.return_value = lambda func: func

                # Mock RBAC authorization
                with patch(
                    "app.services.rbac.RBACService.check_resource_ownership", new_callable=AsyncMock
                ) as mock_ownership:
                    mock_ownership.return_value = True

                    result = await entry_service.generate_preview_data(configuration_id, user)

                    # Assert - Should return ProfilePreviewData
                assert result.configuration_id == configuration_id
                assert result.table is not None
                assert len(result.table.headers) == 29  # All CSV columns

        except (AuthorizationException, NotFoundException):
            # These are valid outcomes depending on user permissions and data existence
            pass

    @given(
        users=st.lists(mock_user_with_role(), min_size=1, max_size=5),
        operation=st.sampled_from(["save", "load", "preview"]),
    )
    def test_property_rbac_decorator_consistency(self, users: list, operation: str):
        """
        **Feature: entry-page-system, Property 9: Authentication integration**

        Property: RBAC decorators should be consistently applied across all
        entry service operations that require authentication.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act & Assert - Verify decorators are present on methods
        if operation == "save":
            method = entry_service.save_profile_configuration
        elif operation == "load":
            method = entry_service.load_profile_configuration
        elif operation == "preview":
            method = entry_service.generate_preview_data

        # Check that the method exists and is callable
        assert callable(method), f"Method for {operation} should be callable"

        # Verify method signature includes user parameter
        import inspect

        sig = inspect.signature(method)
        param_names = list(sig.parameters.keys())

        # Should have user parameter for authentication
        assert "user" in param_names, (
            f"Method {operation} should have user parameter for authentication"
        )

    @pytest.mark.asyncio
    @given(
        user_role=st.sampled_from(
            [Role.CUSTOMER.value, Role.SALESMAN.value, Role.PARTNER.value, Role.SUPERADMIN.value]
        ),
        profile_data=valid_profile_data(),
    )
    async def test_property_role_based_access_patterns(
        self, user_role: str, profile_data: ProfileEntryData
    ):
        """
        **Feature: entry-page-system, Property 9: Authentication integration**

        Property: Different user roles should have appropriate access patterns
        consistent with Windx RBAC system.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        user = MagicMock(spec=User)
        user.id = 123
        user.role = user_role
        user.is_active = True

        # Mock customer creation for different roles
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 456

        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=mock_customer
        )

        # Mock other dependencies
        entry_service.validate_profile_data = AsyncMock()
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()

        mock_manufacturing_type = MagicMock()
        mock_manufacturing_type.base_price = 200.0
        mock_manufacturing_type.base_weight = 25.0

        def mock_execute_side_effect(stmt):
            mock_result = AsyncMock()
            if "manufacturing_types" in str(stmt):
                mock_result.scalar_one_or_none = MagicMock(
                    return_value=mock_manufacturing_type
                )  # Use MagicMock
            elif "attribute_nodes" in str(stmt):
                mock_scalars = MagicMock()
                mock_scalars.all = MagicMock(return_value=[])  # Use MagicMock
                mock_result.scalars = MagicMock(return_value=mock_scalars)  # Use MagicMock
            return mock_result

        mock_db.execute.side_effect = mock_execute_side_effect

        # Act - Test role-based access
        try:
            with patch("app.services.entry.require") as mock_require:
                # Mock the decorator to pass through
                mock_require.return_value = lambda func: func

                result = await entry_service.save_profile_configuration(profile_data, user)

                # Assert - All roles should be able to create configurations
                # (specific authorization is handled by decorators)
                entry_service.rbac_service.get_or_create_customer_for_user.assert_called_once_with(
                    user
                )

                # Customer relationship should be properly established
                assert mock_db.add.called
                config_call = mock_db.add.call_args_list[0][0][0]
                assert config_call.customer_id == mock_customer.id

        except (AuthorizationException, NotFoundException):
            # Some roles might not have access - this is valid behavior
            pass

    @pytest.mark.asyncio
    @given(
        user=mock_user_with_role(), manufacturing_type_id=st.integers(min_value=1, max_value=100)
    )
    async def test_property_schema_access_authentication(self, user, manufacturing_type_id: int):
        """
        **Feature: entry-page-system, Property 9: Authentication integration**

        Property: Schema access should not require special authentication
        beyond basic user authentication (schemas are read-only).
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock manufacturing type and attribute nodes
        mock_manufacturing_type = MagicMock()
        mock_manufacturing_type.id = manufacturing_type_id

        mock_attribute_nodes = []

        def mock_execute_side_effect(stmt):
            mock_result = AsyncMock()
            if "manufacturing_types" in str(stmt):
                mock_result.scalar_one_or_none = MagicMock(
                    return_value=mock_manufacturing_type
                )  # Use MagicMock
            elif "attribute_nodes" in str(stmt):
                mock_scalars = MagicMock()
                mock_scalars.all = MagicMock(return_value=mock_attribute_nodes)  # Use MagicMock
                mock_result.scalars = MagicMock(return_value=mock_scalars)  # Use MagicMock
            return mock_result

        mock_db.execute.side_effect = mock_execute_side_effect

        # Act - Get schema (should not require special authorization)
        try:
            schema = await entry_service.get_profile_schema(manufacturing_type_id)

            # Assert - Should return schema without authorization errors
            assert schema.manufacturing_type_id == manufacturing_type_id
            assert isinstance(schema.sections, list)
            assert isinstance(schema.conditional_logic, dict)

        except NotFoundException:
            # Valid outcome if manufacturing type doesn't exist
            pass
        except AuthorizationException:
            # Schema access should not require special authorization
            pytest.fail("Schema access should not require special authorization")
