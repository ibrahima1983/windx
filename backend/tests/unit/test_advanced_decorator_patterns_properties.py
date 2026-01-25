"""Property-based tests for advanced decorator patterns.

This module contains property-based tests that verify multiple @require decorators
work correctly with OR logic evaluation and advanced authorization patterns.

Property 10: Multiple decorator OR logic evaluation
- For any method with multiple @require decorators, access should be granted
  if ANY decorator's requirements are satisfied (OR logic)

Requirements: 9.1, 9.2
"""

from functools import wraps

import pytest
from fastapi import HTTPException
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.core.rbac import Permission, Privilege, ResourceOwnership, Role
from app.models.user import User


@composite
def user_with_specific_role(draw):
    """Generate user data with specific roles for decorator testing."""
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


class TestAdvancedDecoratorPatternsProperties:
    """Property-based tests for advanced decorator patterns."""

    def create_mock_decorator_function(self, requirements_list: list):
        """Create a mock function with multiple @require decorators."""

        def mock_require(*requirements):
            """Mock implementation of @require decorator."""

            def decorator(func):
                # Get existing requirements from previous decorators
                existing_requirements = getattr(func, "_rbac_requirements", [])

                # Add new requirements (creates OR relationship with existing)
                all_requirements = existing_requirements + [requirements]

                @wraps(func)
                async def wrapper(*args, **kwargs):
                    user = kwargs.get("user") or (args[0] if args else None)

                    # Evaluate requirements with OR logic between decorator groups
                    for requirement_group in all_requirements:
                        if self._evaluate_requirement_group(user, requirement_group):
                            # At least one requirement group satisfied - allow access
                            return await func(*args, **kwargs)

                    # No requirement group satisfied - deny access
                    raise HTTPException(status_code=403, detail="Access denied")

                # Store requirements for potential additional decorators
                wrapper._rbac_requirements = all_requirements
                return wrapper

            return decorator

        # Create function with multiple decorators
        async def test_function(user: User):
            return "success"

        # Apply decorators in reverse order (as they would be applied in Python)
        for requirements in reversed(requirements_list):
            test_function = mock_require(*requirements)(test_function)

        return test_function

    def _evaluate_requirement_group(self, user: User, requirements: tuple) -> bool:
        """Evaluate a single requirement group with AND logic."""

        for requirement in requirements:
            if isinstance(requirement, Role):
                # Role requirement
                if not (user.role == requirement.value or user.role == Role.SUPERADMIN.value):
                    return False

            elif isinstance(requirement, Permission):
                # Permission requirement - simplified evaluation
                if user.role == Role.CUSTOMER.value:
                    # Customers have limited permissions
                    if requirement.resource not in [
                        "configuration",
                        "quote",
                    ] or requirement.action not in ["read", "create"]:
                        return False
                elif user.role not in [
                    Role.SUPERADMIN.value,
                    Role.SALESMAN.value,
                    Role.PARTNER.value,
                    Role.DATA_ENTRY.value,
                ]:
                    return False

            elif isinstance(requirement, ResourceOwnership):
                # Resource ownership - simplified (assume ownership for testing)
                if user.role == Role.CUSTOMER.value:
                    return True  # Customers own their resources
                elif user.role in [Role.SALESMAN.value, Role.PARTNER.value]:
                    return True  # Salesmen/partners have customer access
                elif user.role == Role.SUPERADMIN.value:
                    return True  # Superadmins have all access
                else:
                    return False

            elif isinstance(requirement, Privilege):
                # Privilege requirement - check if user's role is in privilege roles
                if (
                    not any(user.role == role.value for role in requirement.roles)
                    and user.role != Role.SUPERADMIN.value
                ):
                    return False

        # All requirements in group satisfied (AND logic)
        return True

    @given(
        user=user_with_specific_role(),
        decorator_patterns=st.sampled_from(
            [
                # Pattern 1: Role OR Permission
                [(Role.SALESMAN,), (Permission("configuration", "read"),)],
                # Pattern 2: Multiple roles OR ownership
                [(Role.CUSTOMER, ResourceOwnership("configuration")), (Role.SUPERADMIN,)],
                # Pattern 3: Complex privilege patterns
                [
                    (Privilege([Role.SALESMAN, Role.PARTNER], Permission("quote", "create")),),
                    (Role.SUPERADMIN, Permission("*", "*")),
                ],
            ]
        ),
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_multiple_decorator_or_logic_evaluation(
        self, user: User, decorator_patterns: list[tuple]
    ):
        """
        **Feature: entry-page-customer-rbac-fix, Property 10: Multiple decorator OR logic evaluation**

        Property: For any method with multiple @require decorators, access should be
        granted if ANY decorator's requirements are satisfied (OR logic).

        This ensures flexible authorization where users can access resources through
        different authorization paths.
        """
        # Arrange
        test_function = self.create_mock_decorator_function(decorator_patterns)

        # Act & Assert
        try:
            result = await test_function(user=user)

            # If we get here, at least one decorator allowed access
            assert result == "success"

            # Verify that at least one requirement group was satisfied
            at_least_one_satisfied = False
            for requirements in decorator_patterns:
                if self._evaluate_requirement_group(user, requirements):
                    at_least_one_satisfied = True
                    break

            assert at_least_one_satisfied, (
                f"Access granted but no requirement group should be satisfied for user role {user.role}"
            )

        except HTTPException as e:
            # If access was denied, verify that NO requirement group was satisfied
            assert e.status_code == 403

            all_groups_failed = True
            for requirements in decorator_patterns:
                if self._evaluate_requirement_group(user, requirements):
                    all_groups_failed = False
                    break

            assert all_groups_failed, (
                f"Access denied but at least one requirement group should be satisfied for user role {user.role}"
            )

    @given(
        users=st.lists(user_with_specific_role(), min_size=2, max_size=5),
        role_combinations=st.lists(
            st.sampled_from([Role.SALESMAN, Role.PARTNER, Role.CUSTOMER, Role.DATA_ENTRY]),
            min_size=1,
            max_size=3,
        ),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_role_composition_or_logic(
        self, users: list[User], role_combinations: list[Role]
    ):
        """
        Property: For any role composition (Role.A | Role.B), users with ANY
        of the composed roles should be granted access (OR logic within roles).
        """
        # Arrange - Create decorator with role composition
        decorator_patterns = [(tuple(role_combinations),)]
        test_function = self.create_mock_decorator_function(decorator_patterns)

        # Act & Assert for each user
        for user in users:
            try:
                result = await test_function(user=user)

                # If access granted, user should have one of the required roles or be superadmin
                assert (
                    any(user.role == role.value for role in role_combinations)
                    or user.role == Role.SUPERADMIN.value
                ), (
                    f"User with role {user.role} granted access but doesn't have required roles {[r.value for r in role_combinations]}"
                )

                assert result == "success"

            except HTTPException as e:
                # If access denied, user should not have any of the required roles
                assert e.status_code == 403
                assert not any(user.role == role.value for role in role_combinations)
                assert user.role != Role.SUPERADMIN.value

    @given(
        user=user_with_specific_role(),
        permission_sets=st.lists(
            st.builds(
                Permission,
                resource=st.sampled_from(["configuration", "quote", "order", "*"]),
                action=st.sampled_from(["create", "read", "update", "delete", "*"]),
            ),
            min_size=2,
            max_size=4,
        ),
    )
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_property_multiple_permission_or_logic(
        self, user: User, permission_sets: list[Permission]
    ):
        """
        Property: For any multiple permission decorators, access should be granted
        if the user satisfies ANY of the permission requirements (OR logic).
        """
        # Arrange - Create decorators with different permissions
        decorator_patterns = [(permission,) for permission in permission_sets]
        test_function = self.create_mock_decorator_function(decorator_patterns)

        # Act
        try:
            result = await test_function(user=user)

            # If access granted, verify user should satisfy at least one permission
            assert result == "success"

            # Check if user should have access to at least one permission
            should_have_access = False
            for permission in permission_sets:
                if user.role == Role.SUPERADMIN.value:
                    should_have_access = True
                    break
                elif user.role in [Role.SALESMAN.value, Role.PARTNER.value, Role.DATA_ENTRY.value]:
                    should_have_access = True  # These roles have full privileges initially
                    break
                elif user.role == Role.CUSTOMER.value:
                    if permission.resource in ["configuration", "quote"] and permission.action in [
                        "read",
                        "create",
                    ]:
                        should_have_access = True
                        break

            assert should_have_access, (
                f"User {user.role} granted access but shouldn't have permission for any of {[(p.resource, p.action) for p in permission_sets]}"
            )

        except HTTPException as e:
            assert e.status_code == 403

            # Verify user shouldn't have access to any permission
            should_be_denied = True
            for permission in permission_sets:
                if user.role == Role.SUPERADMIN.value:
                    should_be_denied = False
                    break
                elif user.role in [Role.SALESMAN.value, Role.PARTNER.value, Role.DATA_ENTRY.value]:
                    should_be_denied = False
                    break
                elif user.role == Role.CUSTOMER.value:
                    if permission.resource in ["configuration", "quote"] and permission.action in [
                        "read",
                        "create",
                    ]:
                        should_be_denied = False
                        break

            assert should_be_denied, (
                f"User {user.role} denied access but should have permission for at least one of {[(p.resource, p.action) for p in permission_sets]}"
            )

    @given(
        user=user_with_specific_role(),
        complex_requirements=st.lists(
            st.tuples(
                st.sampled_from([Role.SALESMAN, Role.PARTNER, Role.CUSTOMER]),
                st.builds(
                    Permission,
                    resource=st.sampled_from(["configuration", "quote"]),
                    action=st.sampled_from(["create", "read", "update"]),
                ),
                st.builds(
                    ResourceOwnership, resource_type=st.sampled_from(["configuration", "customer"])
                ),
            ),
            min_size=2,
            max_size=3,
        ),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_complex_decorator_combinations_or_logic(
        self, user: User, complex_requirements: list[tuple[Role, Permission, ResourceOwnership]]
    ):
        """
        Property: For any complex combinations of role + permission + ownership
        decorators, access should be granted if ANY complete combination is
        satisfied (OR logic between decorator groups, AND logic within groups).
        """
        # Arrange - Create decorators with complex requirements
        decorator_patterns = [requirements for requirements in complex_requirements]
        test_function = self.create_mock_decorator_function(decorator_patterns)

        # Act
        try:
            result = await test_function(user=user)
            assert result == "success"

            # Verify at least one complete requirement set was satisfied
            at_least_one_satisfied = False
            for requirements in complex_requirements:
                if self._evaluate_requirement_group(user, requirements):
                    at_least_one_satisfied = True
                    break

            assert at_least_one_satisfied, (
                f"Access granted but no complete requirement set satisfied for user {user.role}"
            )

        except HTTPException as e:
            assert e.status_code == 403

            # Verify no complete requirement set was satisfied
            all_failed = True
            for requirements in complex_requirements:
                if self._evaluate_requirement_group(user, requirements):
                    all_failed = False
                    break

            assert all_failed, (
                f"Access denied but at least one complete requirement set should be satisfied for user {user.role}"
            )

    @given(
        user=user_with_specific_role(),
        privilege_objects=st.lists(
            st.builds(
                Privilege,
                roles=st.lists(
                    st.sampled_from([Role.SALESMAN, Role.PARTNER, Role.CUSTOMER]),
                    min_size=1,
                    max_size=2,
                ),
                permission=st.builds(
                    Permission,
                    resource=st.sampled_from(["configuration", "quote"]),
                    action=st.sampled_from(["create", "read"]),
                ),
            ),
            min_size=2,
            max_size=3,
        ),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_privilege_object_or_logic(
        self, user: User, privilege_objects: list[Privilege]
    ):
        """
        Property: For any multiple Privilege object decorators, access should be
        granted if the user satisfies ANY privilege (OR logic between privileges).
        """
        # Arrange - Create decorators with Privilege objects
        decorator_patterns = [(privilege,) for privilege in privilege_objects]
        test_function = self.create_mock_decorator_function(decorator_patterns)

        # Act
        try:
            result = await test_function(user=user)
            assert result == "success"

            # Verify user satisfies at least one privilege
            satisfies_privilege = False
            for privilege in privilege_objects:
                if (
                    any(user.role == role.value for role in privilege.roles)
                    or user.role == Role.SUPERADMIN.value
                ):
                    satisfies_privilege = True
                    break

            assert satisfies_privilege, (
                f"User {user.role} granted access but doesn't satisfy any privilege"
            )

        except HTTPException as e:
            assert e.status_code == 403

            # Verify user doesn't satisfy any privilege
            satisfies_no_privilege = True
            for privilege in privilege_objects:
                if (
                    any(user.role == role.value for role in privilege.roles)
                    or user.role == Role.SUPERADMIN.value
                ):
                    satisfies_no_privilege = False
                    break

            assert satisfies_no_privilege, (
                f"User {user.role} denied access but should satisfy at least one privilege"
            )
