"""Property-based tests for template RBAC function consistency.

This module contains property-based tests that verify template RBAC functions
return results that match the corresponding backend Casbin policy evaluation.

Property 11: Template RBAC function consistency
- For any template RBAC function call, the result should match the corresponding
  backend Casbin policy evaluation

Requirements: 10.1, 10.2, 10.3
"""

from unittest.mock import AsyncMock

import pytest
from app.templates.rbac_context import RBACTemplateContext
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.core.rbac import Permission, Privilege, Role
from app.models.customer import Customer
from app.models.user import User
from app.services.rbac import RBACService


@composite
def user_with_role_for_templates(draw):
    """Generate user data for template RBAC testing."""
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
        role=draw(
            st.sampled_from(
                [
                    Role.SUPERADMIN.value,
                    Role.SALESMAN.value,
                    Role.DATA_ENTRY.value,
                    Role.PARTNER.value,
                    Role.CUSTOMER.value,
                ]
            )
        ),
        is_active=True,
        is_superuser=draw(st.booleans()),
    )


@composite
def resource_action_for_templates(draw):
    """Generate resource-action pairs for template testing."""
    resource = draw(
        st.sampled_from(
            ["configuration", "quote", "order", "customer", "manufacturing_type", "template"]
        )
    )
    action = draw(st.sampled_from(["create", "read", "update", "delete"]))
    return resource, action


@composite
def customer_for_ownership_testing(draw):
    """Generate customer data for ownership testing."""
    return Customer(
        id=draw(st.integers(min_value=1, max_value=1000)),
        email=draw(st.emails()),
        contact_person=draw(st.text(min_size=1, max_size=100)),
        customer_type=draw(st.sampled_from(["residential", "commercial", "contractor"])),
        is_active=True,
    )


class TestTemplateRBACFunctionConsistencyProperties:
    """Property-based tests for template RBAC function consistency."""

    @pytest.fixture
    def mock_rbac_service(self):
        """Create mock RBAC service for testing."""
        service = AsyncMock(spec=RBACService)
        return service

    @pytest.fixture
    def rbac_template_context(self, mock_rbac_service):
        """Create RBAC template context with mocked service."""
        return RBACTemplateContext(mock_rbac_service)

    @given(user=user_with_role_for_templates(), resource_action=resource_action_for_templates())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_can_function_consistency(
        self, mock_rbac_service, rbac_template_context, user: User, resource_action: tuple[str, str]
    ):
        """
        **Feature: entry-page-customer-rbac-fix, Property 11: Template RBAC function consistency**

        Property: For any template RBAC function call, the result should match
        the corresponding backend Casbin policy evaluation.

        This ensures template permission checks are consistent with backend authorization.
        """
        # Arrange
        resource, action = resource_action

        # Mock backend RBAC service behavior
        def mock_check_permission(user_param, resource_param, action_param):
            # Simulate Casbin policy evaluation
            if user_param.role == Role.SUPERADMIN.value:
                return True
            elif user_param.role in [
                Role.SALESMAN.value,
                Role.DATA_ENTRY.value,
                Role.PARTNER.value,
            ]:
                return True  # Full privileges initially
            elif user_param.role == Role.CUSTOMER.value:
                return resource_param in ["configuration", "quote"] and action_param in [
                    "read",
                    "create",
                ]
            return False

        mock_rbac_service.check_permission = AsyncMock(side_effect=mock_check_permission)

        # Act - Call both backend and template functions
        backend_result = await mock_rbac_service.check_permission(user, resource, action)
        template_result = await rbac_template_context.can(user, resource, action)

        # Assert - Results should be identical
        assert backend_result == template_result, (
            f"Template rbac.can({resource}, {action}) returned {template_result} but backend returned {backend_result} for user role {user.role}"
        )

        # Verify backend was called correctly
        mock_rbac_service.check_permission.assert_called_with(user, resource, action)

    @given(
        user=user_with_role_for_templates(),
        roles_to_check=st.lists(
            st.sampled_from(
                [Role.SUPERADMIN, Role.SALESMAN, Role.DATA_ENTRY, Role.PARTNER, Role.CUSTOMER]
            ),
            min_size=1,
            max_size=3,
        ),
    )
    @settings(
        max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_has_role_function_consistency(
        self, mock_rbac_service, rbac_template_context, user: User, roles_to_check: list[Role]
    ):
        """
        Property: For any role check in templates, the result should match
        the user's actual role assignment and superadmin privileges.
        """
        # Act & Assert for each role
        for role_to_check in roles_to_check:
            template_result = rbac_template_context.has_role(user, role_to_check.value)

            # Expected result based on user's actual role
            expected_result = user.role == role_to_check.value or user.role == Role.SUPERADMIN.value

            assert template_result == expected_result, (
                f"Template rbac.has_role({role_to_check.value}) returned {template_result} but expected {expected_result} for user role {user.role}"
            )

    @given(
        user=user_with_role_for_templates(),
        customer=customer_for_ownership_testing(),
        resource_types=st.lists(
            st.sampled_from(["configuration", "quote", "order", "customer"]), min_size=1, max_size=3
        ),
    )
    @settings(
        max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_owns_function_consistency(
        self,
        mock_rbac_service,
        rbac_template_context,
        user: User,
        customer: Customer,
        resource_types: list[str],
    ):
        """
        Property: For any ownership check in templates, the result should match
        the backend resource ownership evaluation.
        """

        # Arrange
        def mock_check_resource_ownership(user_param, resource_type, resource_id):
            # Simulate ownership logic
            if user_param.role == Role.SUPERADMIN.value:
                return True
            elif user_param.role in [Role.SALESMAN.value, Role.PARTNER.value]:
                return True  # Can access assigned customers
            elif user_param.role == Role.CUSTOMER.value:
                return user_param.email == customer.email  # Own resources only
            return False

        mock_rbac_service.check_resource_ownership = AsyncMock(
            side_effect=mock_check_resource_ownership
        )

        # Act & Assert for each resource type
        for resource_type in resource_types:
            backend_result = await mock_rbac_service.check_resource_ownership(
                user, resource_type, customer.id
            )
            template_result = await rbac_template_context.owns(user, resource_type, customer.id)

            assert backend_result == template_result, (
                f"Template rbac.owns({resource_type}, {customer.id}) returned {template_result} but backend returned {backend_result} for user role {user.role}"
            )

            # Verify backend was called correctly
            mock_rbac_service.check_resource_ownership.assert_called_with(
                user, resource_type, customer.id
            )

    @given(
        user=user_with_role_for_templates(),
        privilege_data=st.tuples(
            st.lists(
                st.sampled_from([Role.SALESMAN, Role.PARTNER, Role.CUSTOMER]),
                min_size=1,
                max_size=2,
            ),
            st.builds(
                Permission,
                resource=st.sampled_from(["configuration", "quote", "order"]),
                action=st.sampled_from(["create", "read", "update"]),
            ),
        ),
    )
    @settings(
        max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_has_privilege_function_consistency(
        self,
        mock_rbac_service,
        rbac_template_context,
        user: User,
        privilege_data: tuple[list[Role], Permission],
    ):
        """
        Property: For any privilege check in templates, the result should match
        the backend privilege evaluation.
        """
        # Arrange
        roles, permission = privilege_data
        privilege = Privilege(roles=roles, permission=permission)

        def mock_check_privilege(user_param, privilege_param):
            # Simulate privilege evaluation
            if user_param.role == Role.SUPERADMIN.value:
                return True

            # Check if user has one of the required roles
            has_role = any(user_param.role == role.value for role in privilege_param.roles)

            # Check permission (simplified)
            has_permission = True
            if user_param.role == Role.CUSTOMER.value:
                has_permission = privilege_param.permission.resource in [
                    "configuration",
                    "quote",
                ] and privilege_param.permission.action in ["read", "create"]

            return has_role and has_permission

        mock_rbac_service.check_privilege = AsyncMock(side_effect=mock_check_privilege)

        # Act
        backend_result = await mock_rbac_service.check_privilege(user, privilege)
        template_result = await rbac_template_context.has_privilege(user, privilege)

        # Assert
        assert backend_result == template_result, (
            f"Template rbac.has_privilege() returned {template_result} but backend returned {backend_result} for user role {user.role}"
        )

        # Verify backend was called correctly
        mock_rbac_service.check_privilege.assert_called_with(user, privilege)

    @given(
        user=user_with_role_for_templates(),
        multiple_checks=st.lists(
            st.tuples(
                st.sampled_from(["can", "has_role", "owns"]),
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=20),
            ),
            min_size=2,
            max_size=5,
        ),
    )
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_caching_consistency(
        self,
        mock_rbac_service,
        rbac_template_context,
        user: User,
        multiple_checks: list[tuple[str, str, str]],
    ):
        """
        Property: For any repeated template RBAC function calls within the same
        request scope, results should be consistent and cached appropriately.
        """
        # Arrange - Setup consistent backend responses
        mock_rbac_service.check_permission = AsyncMock(return_value=True)
        mock_rbac_service.check_resource_ownership = AsyncMock(return_value=True)

        # Act - Perform multiple checks and repeat them
        first_results = []
        second_results = []

        for check_type, param1, param2 in multiple_checks:
            if check_type == "can":
                result1 = await rbac_template_context.can(user, param1, param2)
                result2 = await rbac_template_context.can(user, param1, param2)  # Repeat
            elif check_type == "has_role":
                result1 = rbac_template_context.has_role(user, param1)
                result2 = rbac_template_context.has_role(user, param1)  # Repeat
            elif check_type == "owns":
                result1 = await rbac_template_context.owns(user, param1, 1)
                result2 = await rbac_template_context.owns(user, param1, 1)  # Repeat

            first_results.append(result1)
            second_results.append(result2)

        # Assert - Repeated calls should return identical results
        assert first_results == second_results, (
            f"Repeated template RBAC calls returned inconsistent results: {first_results} vs {second_results}"
        )

    @given(
        users=st.lists(user_with_role_for_templates(), min_size=2, max_size=5),
        resource_action=resource_action_for_templates(),
    )
    @settings(
        max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_cross_user_consistency(
        self,
        mock_rbac_service,
        rbac_template_context,
        users: list[User],
        resource_action: tuple[str, str],
    ):
        """
        Property: For any users with the same role, template RBAC functions
        should return consistent results for the same resource and action.
        """
        # Arrange
        resource, action = resource_action

        # Group users by role
        users_by_role = {}
        for user in users:
            if user.role not in users_by_role:
                users_by_role[user.role] = []
            users_by_role[user.role].append(user)

        # Mock consistent backend behavior
        def mock_check_permission(user_param, resource_param, action_param):
            if user_param.role == Role.SUPERADMIN.value:
                return True
            elif user_param.role in [
                Role.SALESMAN.value,
                Role.DATA_ENTRY.value,
                Role.PARTNER.value,
            ]:
                return True
            elif user_param.role == Role.CUSTOMER.value:
                return resource_param in ["configuration", "quote"] and action_param in [
                    "read",
                    "create",
                ]
            return False

        mock_rbac_service.check_permission = AsyncMock(side_effect=mock_check_permission)

        # Act & Assert - Users with same role should get same results
        for role, role_users in users_by_role.items():
            if len(role_users) > 1:  # Only test if multiple users with same role
                results = []
                for user in role_users:
                    result = await rbac_template_context.can(user, resource, action)
                    results.append(result)

                # All users with same role should get same result
                assert all(result == results[0] for result in results), (
                    f"Users with same role {role} got inconsistent template RBAC results: {results}"
                )

    @given(
        user=user_with_role_for_templates(),
        template_functions=st.lists(
            st.sampled_from(["can", "has_role", "owns", "has_privilege"]), min_size=3, max_size=5
        ),
    )
    @settings(
        max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_property_template_rbac_function_isolation(
        self, mock_rbac_service, rbac_template_context, user: User, template_functions: list[str]
    ):
        """
        Property: For any combination of template RBAC function calls, each
        function should operate independently and not affect others' results.
        """
        # Arrange - Setup backend mocks
        mock_rbac_service.check_permission = AsyncMock(return_value=True)
        mock_rbac_service.check_resource_ownership = AsyncMock(return_value=True)
        mock_rbac_service.check_privilege = AsyncMock(return_value=True)

        # Act - Call functions in different orders
        results_order1 = []
        results_order2 = []

        # First order
        for func_name in template_functions:
            if func_name == "can":
                result = await rbac_template_context.can(user, "configuration", "read")
            elif func_name == "has_role":
                result = rbac_template_context.has_role(user, Role.SALESMAN.value)
            elif func_name == "owns":
                result = await rbac_template_context.owns(user, "configuration", 1)
            elif func_name == "has_privilege":
                privilege = Privilege([Role.SALESMAN], Permission("configuration", "read"))
                result = await rbac_template_context.has_privilege(user, privilege)
            results_order1.append(result)

        # Second order (reversed)
        for func_name in reversed(template_functions):
            if func_name == "can":
                result = await rbac_template_context.can(user, "configuration", "read")
            elif func_name == "has_role":
                result = rbac_template_context.has_role(user, Role.SALESMAN.value)
            elif func_name == "owns":
                result = await rbac_template_context.owns(user, "configuration", 1)
            elif func_name == "has_privilege":
                privilege = Privilege([Role.SALESMAN], Permission("configuration", "read"))
                result = await rbac_template_context.has_privilege(user, privilege)
            results_order2.append(result)

        # Assert - Function call order shouldn't affect individual results
        # (Note: results_order2 is in reverse order, so we reverse it for comparison)
        results_order2.reverse()
        assert results_order1 == results_order2, (
            f"Template RBAC function call order affected results: {results_order1} vs {results_order2}"
        )
