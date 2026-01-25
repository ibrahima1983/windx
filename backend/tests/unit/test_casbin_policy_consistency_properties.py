"""Property-based tests for Casbin policy consistency.

This module contains property-based tests that verify Casbin policy evaluation
returns consistent results for user roles and resource access attempts.

Property 9: Casbin policy consistency
- For any user role and resource access attempt, Casbin policy evaluation
  should return consistent results

Requirements: 3.1, 8.1, 9.1
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.core.rbac import Permission, Privilege, ResourceOwnership, Role
from app.models.customer import Customer
from app.models.user import User
from app.services.rbac import RBACService


@composite
def user_with_role(draw):
    """Generate user data with specific roles for testing."""
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
def resource_action_pair(draw):
    """Generate resource and action pairs for testing."""
    resource = draw(
        st.sampled_from(
            ["configuration", "quote", "order", "customer", "manufacturing_type", "template", "*"]
        )
    )
    action = draw(st.sampled_from(["create", "read", "update", "delete", "*"]))
    return resource, action


@composite
def customer_data(draw):
    """Generate customer data for ownership testing."""
    return Customer(
        id=draw(st.integers(min_value=1, max_value=1000)),
        email=draw(st.emails()),
        contact_person=draw(st.text(min_size=1, max_size=100)),
        customer_type=draw(st.sampled_from(["residential", "commercial", "contractor"])),
        is_active=True,
    )


class TestCasbinPolicyConsistencyProperties:
    """Property-based tests for Casbin policy consistency."""

    @pytest.fixture
    def mock_casbin_enforcer(self):
        """Create mock Casbin enforcer."""
        enforcer = MagicMock()
        enforcer.enforce = MagicMock()
        return enforcer

    @given(user=user_with_role(), resource_action=resource_action_pair())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_casbin_policy_consistency(
        self, mock_casbin_enforcer, user: User, resource_action: tuple[str, str]
    ):
        """
        **Feature: entry-page-customer-rbac-fix, Property 9: Casbin policy consistency**

        Property: For any user role and resource access attempt, Casbin policy
        evaluation should return consistent results across multiple calls.

        This ensures policy evaluation is deterministic and reliable.
        """
        # Arrange
        resource, action = resource_action
        rbac_service = RBACService()
        rbac_service.enforcer = mock_casbin_enforcer

        # Mock consistent policy evaluation based on role
        def mock_enforce(user_email, resource_param, action_param):
            # Superadmin always has access
            if user.role == Role.SUPERADMIN.value:
                return True

            # Salesman, data_entry, partner have full privileges initially
            if user.role in [Role.SALESMAN.value, Role.DATA_ENTRY.value, Role.PARTNER.value]:
                return True

            # Customer has limited privileges
            if user.role == Role.CUSTOMER.value:
                if resource_param in ["configuration", "quote"] and action_param in [
                    "read",
                    "create",
                ]:
                    return True
                return False

            return False

        mock_casbin_enforcer.enforce.side_effect = mock_enforce

        # Act - Call policy evaluation multiple times
        results = []
        for _ in range(5):  # Test consistency across multiple calls
            result = await rbac_service.check_permission(user, resource, action)
            results.append(result)

        # Assert - All results should be identical (consistent)
        assert all(result == results[0] for result in results), (
            f"Policy evaluation inconsistent for user {user.role}, resource {resource}, action {action}"
        )

        # Verify the result matches expected policy
        expected_result = mock_enforce(user.email, resource, action)
        assert all(result == expected_result for result in results)

    @given(
        user=user_with_role(),
        customer=customer_data(),
        resource_type=st.sampled_from(["configuration", "quote", "order"]),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_resource_ownership_consistency(
        self, mock_casbin_enforcer, user: User, customer: Customer, resource_type: str
    ):
        """
        Property: For any user and resource ownership check, the result should
        be consistent across multiple evaluations and match the user-customer
        relationship rules.
        """
        # Arrange
        rbac_service = RBACService()
        rbac_service.enforcer = mock_casbin_enforcer

        # Mock customer lookup
        rbac_service.get_accessible_customers = AsyncMock(return_value=[customer.id])

        # Set user email to match customer for ownership
        user.email = customer.email

        # Act - Check ownership multiple times
        results = []
        for _ in range(3):
            result = await rbac_service.check_resource_ownership(user, resource_type, customer.id)
            results.append(result)

        # Assert - Results should be consistent
        assert all(result == results[0] for result in results)

        # For users with matching customer relationship, should have ownership
        if user.email == customer.email or user.role == Role.SUPERADMIN.value:
            assert all(result is True for result in results)

    @given(
        users=st.lists(user_with_role(), min_size=2, max_size=5),
        resource_action=resource_action_pair(),
    )
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_property_role_based_access_consistency(
        self, mock_casbin_enforcer, users: list[User], resource_action: tuple[str, str]
    ):
        """
        Property: For any users with the same role, policy evaluation should
        return consistent results for the same resource and action.
        """
        # Arrange
        resource, action = resource_action
        rbac_service = RBACService()
        rbac_service.enforcer = mock_casbin_enforcer

        # Group users by role
        users_by_role = {}
        for user in users:
            if user.role not in users_by_role:
                users_by_role[user.role] = []
            users_by_role[user.role].append(user)

        # Mock policy evaluation
        def mock_enforce(user_email, resource_param, action_param):
            # Extract role from user email (simplified for testing)
            for role, role_users in users_by_role.items():
                if any(u.email == user_email for u in role_users):
                    if role == Role.SUPERADMIN.value:
                        return True
                    elif role in [Role.SALESMAN.value, Role.DATA_ENTRY.value, Role.PARTNER.value]:
                        return True
                    elif role == Role.CUSTOMER.value:
                        return resource_param in ["configuration", "quote"] and action_param in [
                            "read",
                            "create",
                        ]
            return False

        mock_casbin_enforcer.enforce.side_effect = mock_enforce

        # Act & Assert - Users with same role should get same result
        for role, role_users in users_by_role.items():
            if len(role_users) > 1:  # Only test if we have multiple users with same role
                results = []
                for user in role_users:
                    result = await rbac_service.check_permission(user, resource, action)
                    results.append(result)

                # All users with same role should get same result
                assert all(result == results[0] for result in results), (
                    f"Inconsistent results for role {role}, resource {resource}, action {action}"
                )

    @given(
        user=user_with_role(),
        privilege_components=st.tuples(
            st.sampled_from([Role.SALESMAN, Role.PARTNER, Role.CUSTOMER]),
            st.builds(
                Permission,
                resource=st.sampled_from(["configuration", "quote", "order"]),
                action=st.sampled_from(["create", "read", "update"]),
            ),
            st.builds(
                ResourceOwnership, resource_type=st.sampled_from(["configuration", "customer"])
            ),
        ),
    )
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_property_privilege_evaluation_consistency(
        self, mock_casbin_enforcer, user: User, privilege_components: tuple
    ):
        """
        Property: For any Privilege object evaluation, the result should be
        consistent and match the combined evaluation of its component parts
        (role + permission + resource ownership).
        """
        # Arrange
        role, permission, resource_ownership = privilege_components
        privilege = Privilege(roles=[role], permission=permission, resource=resource_ownership)

        rbac_service = RBACService()
        rbac_service.enforcer = mock_casbin_enforcer

        # Mock individual component evaluations
        role_match = user.role == role.value or user.role == Role.SUPERADMIN.value

        def mock_enforce(user_email, resource_param, action_param):
            return role_match and (
                resource_param == permission.resource and action_param == permission.action
            )

        mock_casbin_enforcer.enforce.side_effect = mock_enforce

        # Mock resource ownership
        rbac_service.check_resource_ownership = AsyncMock(return_value=role_match)

        # Act - Evaluate privilege multiple times
        results = []
        for _ in range(3):
            result = await rbac_service.check_privilege(user, privilege)
            results.append(result)

        # Assert - Results should be consistent
        assert all(result == results[0] for result in results)

        # Result should match expected combination of components
        expected_result = role_match  # Simplified for testing
        assert all(result == expected_result for result in results)

    @given(
        user=user_with_role(),
        policy_changes=st.lists(
            st.tuples(
                st.sampled_from(["add", "remove"]),
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=20),
            ),
            min_size=1,
            max_size=3,
        ),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_policy_update_consistency(
        self, mock_casbin_enforcer, user: User, policy_changes: list[tuple[str, str, str, str]]
    ):
        """
        Property: For any policy updates (add/remove), the policy evaluation
        should reflect the changes consistently and immediately.
        """
        # Arrange
        rbac_service = RBACService()
        rbac_service.enforcer = mock_casbin_enforcer

        # Track policy state
        policies = set()

        def mock_add_policy(role, resource, action):
            policies.add((role, resource, action))
            return True

        def mock_remove_policy(role, resource, action):
            policies.discard((role, resource, action))
            return True

        def mock_enforce(user_email, resource, action):
            # Check if user's role has permission
            return (user.role, resource, action) in policies or user.role == Role.SUPERADMIN.value

        mock_casbin_enforcer.add_policy = mock_add_policy
        mock_casbin_enforcer.remove_policy = mock_remove_policy
        mock_casbin_enforcer.enforce.side_effect = mock_enforce

        # Act - Apply policy changes and test consistency
        for change_type, role, resource, action in policy_changes:
            if change_type == "add":
                await rbac_service.add_policy(role, resource, action)
            else:
                await rbac_service.remove_policy(role, resource, action)

            # Test consistency after each change
            results = []
            for _ in range(2):
                result = await rbac_service.check_permission(user, resource, action)
                results.append(result)

            # Assert - Results should be consistent after policy change
            assert all(result == results[0] for result in results)

    @given(user=user_with_role(), concurrent_requests=st.integers(min_value=2, max_value=5))
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_concurrent_evaluation_consistency(
        self, mock_casbin_enforcer, user: User, concurrent_requests: int
    ):
        """
        Property: For any concurrent policy evaluations for the same user and
        resource, all evaluations should return consistent results.
        """
        # Arrange
        rbac_service = RBACService()
        rbac_service.enforcer = mock_casbin_enforcer

        # Mock deterministic policy evaluation
        def mock_enforce(user_email, resource, action):
            return user.role in [Role.SUPERADMIN.value, Role.SALESMAN.value, Role.PARTNER.value]

        mock_casbin_enforcer.enforce.side_effect = mock_enforce

        # Act - Simulate concurrent evaluations
        import asyncio

        async def evaluate_permission():
            return await rbac_service.check_permission(user, "configuration", "read")

        # Run concurrent evaluations
        tasks = [evaluate_permission() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)

        # Assert - All concurrent evaluations should return same result
        assert all(result == results[0] for result in results), (
            f"Concurrent evaluations returned inconsistent results: {results}"
        )
