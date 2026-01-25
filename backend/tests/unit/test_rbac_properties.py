"""Property-based tests for RBAC system.

This module contains property-based tests using Hypothesis to validate
RBAC system correctness properties across all valid inputs.

Property Tests:
    - Multiple decorator OR logic evaluation
    - Role assignment validity
    - Decorator authorization consistency
    - User-Customer mapping consistency
    - Customer auto-creation idempotency
"""

from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from app.core.rbac import Permission, Privilege, ResourceOwnership, Role, require
from app.models.user import User


class TestRBACProperties:
    """Property-based tests for RBAC system correctness."""

    @pytest.mark.asyncio
    @given(user_role=st.sampled_from([role.value for role in Role]))
    async def test_multiple_decorator_or_logic_property(self, user_role):
        """Property: Multiple decorator OR logic evaluation.

        For any user role, test that OR logic works correctly between decorators.
        A user with CUSTOMER role should be able to access a function that requires
        either CUSTOMER or SALESMAN role.

        Validates: Requirements 9.1, 9.2
        """
        # Create user with the given role
        user = User()
        user.id = 1
        user.email = f"test-{user_role}@example.com"  # Unique email per test
        user.role = user_role

        # Create function with multiple @require decorators (OR logic)
        # This should allow CUSTOMER or SALESMAN or SUPERADMIN
        @require(Role.CUSTOMER)  # First requirement
        @require(Role.SALESMAN)  # Second requirement (OR logic)
        async def test_function(user: User):
            return "success"

        # Determine expected result
        user_has_required_role = (
            user_role == Role.SUPERADMIN.value
            or user_role == Role.SALESMAN.value
            or user_role == Role.CUSTOMER.value
        )

        if user_has_required_role:
            # Should succeed
            result = await test_function(user)
            assert result == "success"
        else:
            # Should fail with 403
            with pytest.raises(Exception) as exc_info:
                await test_function(user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @given(role_value=st.sampled_from([role.value for role in Role]))
    async def test_role_assignment_validity_property(self, role_value):
        """Property: Role assignment validity.

        For any valid role value, a user should be able to be assigned that role
        and the role should be properly validated and stored.

        Validates: Requirements 3.3, 6.4
        """
        # Create user with the role
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = role_value

        # Validate role assignment
        assert user.role == role_value

        # Test has_role method
        role_enum = Role(role_value)
        assert user.has_role(role_value) is True

        # Superadmin should have all roles
        if role_value == Role.SUPERADMIN.value:
            for other_role in Role:
                assert user.has_role(other_role.value) is True
        else:
            # Non-superadmin should only have their own role
            for other_role in Role:
                if other_role.value != role_value:
                    expected = role_value == Role.SUPERADMIN.value
                    assert user.has_role(other_role.value) == expected

    @pytest.mark.asyncio
    @given(
        user_role=st.sampled_from([role.value for role in Role]),
        resource=st.text(
            min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))
        ),
        action=st.text(
            min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))
        ),
    )
    async def test_decorator_authorization_consistency_property(self, user_role, resource, action):
        """Property: Decorator authorization consistency.

        For any user role, resource, and action, the authorization result
        should be consistent regardless of how the decorator is applied
        (single vs multiple decorators with same requirements).

        Validates: Requirements 9.1, 9.2
        """
        assume(len(resource) > 0 and len(action) > 0)
        assume(resource.isalnum() and action.isalnum())

        # Create user
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = user_role

        # Create permission
        permission = Permission(resource, action)

        # Test single decorator
        @require(permission)
        async def single_decorator_function(user: User):
            return "success"

        # Test multiple decorators with same permission (should be equivalent)
        @require(permission)
        @require(permission)
        async def multiple_decorator_function(user: User):
            return "success"

        # Mock the permission check to return a consistent result
        with patch(
            "app.core.rbac.rbac_service.check_permission", new_callable=AsyncMock
        ) as mock_check:
            # Superadmin always has permission, others based on mock
            if user_role == Role.SUPERADMIN.value:
                mock_result = True
            else:
                # Use a deterministic result based on inputs
                mock_result = hash(f"{user_role}:{resource}:{action}") % 2 == 0

            mock_check.return_value = mock_result

            # Both functions should behave the same way
            if mock_result or user_role == Role.SUPERADMIN.value:
                result1 = await single_decorator_function(user)
                result2 = await multiple_decorator_function(user)
                assert result1 == result2 == "success"
            else:
                with pytest.raises(Exception) as exc1:
                    await single_decorator_function(user)
                with pytest.raises(Exception) as exc2:
                    await multiple_decorator_function(user)
                assert exc1.value.status_code == exc2.value.status_code == 403

    @pytest.mark.asyncio
    @given(
        roles=st.lists(
            st.sampled_from([role for role in Role]), min_size=1, max_size=3, unique=True
        )
    )
    async def test_privilege_composition_property(self, roles):
        """Property: Privilege composition consistency.

        For any list of roles, a Privilege object should correctly
        represent the role requirements and be evaluable consistently.

        Validates: Requirements 9.3, 9.5
        """
        # Create a test permission
        permission = Permission("test_resource", "test_action")

        # Create privilege with the roles
        privilege = Privilege(roles, permission)

        # Verify privilege contains all roles
        assert len(privilege.roles) == len(roles)
        for role in roles:
            assert role in privilege.roles

        # Test with users having different roles
        for test_role in Role:
            user = User()
            user.id = 1
            user.email = "test@example.com"
            user.role = test_role.value

            # Mock permission check
            with patch(
                "app.core.rbac.rbac_service.check_permission", new_callable=AsyncMock
            ) as mock_check:
                mock_check.return_value = True  # Assume permission is granted

                # Create function with privilege
                @require(privilege)
                async def test_function(user: User):
                    return "success"

                # Determine expected result
                user_has_role = test_role.value == Role.SUPERADMIN.value or any(
                    test_role == role for role in roles
                )

                if user_has_role:
                    result = await test_function(user)
                    assert result == "success"
                else:
                    with pytest.raises(Exception) as exc_info:
                        await test_function(user)
                    assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @given(
        resource_type=st.text(
            min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))
        ),
        resource_id=st.integers(min_value=1, max_value=1000),
    )
    async def test_resource_ownership_consistency_property(self, resource_type, resource_id):
        """Property: Resource ownership validation consistency.

        For any resource type and ID, ownership validation should be
        consistent regardless of how the resource ID is passed to the function.

        Validates: Requirements 9.5
        """
        assume(len(resource_type) > 0 and resource_type.isalpha())

        # Create user
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value

        # Create resource ownership requirement
        ownership = ResourceOwnership(resource_type)

        # Test with resource ID as keyword argument
        @require(ownership)
        async def test_function_kwargs(user: User, **kwargs):
            return "success"

        # Test with resource ID as positional argument
        @require(ResourceOwnership(resource_type, "resource_id"))
        async def test_function_args(resource_id: int, user: User):
            return "success"

        # Mock ownership check
        with patch(
            "app.core.rbac.rbac_service.check_resource_ownership", new_callable=AsyncMock
        ) as mock_check:
            # Use deterministic result based on inputs
            mock_result = hash(f"{resource_type}:{resource_id}") % 2 == 0
            mock_check.return_value = mock_result

            # Both functions should behave the same way
            if mock_result:
                result1 = await test_function_kwargs(user, **{f"{resource_type}_id": resource_id})
                result2 = await test_function_args(resource_id, user)
                assert result1 == result2 == "success"
            else:
                with pytest.raises(Exception) as exc1:
                    await test_function_kwargs(user, **{f"{resource_type}_id": resource_id})
                with pytest.raises(Exception) as exc2:
                    await test_function_args(resource_id, user)
                assert exc1.value.status_code == exc2.value.status_code == 403
