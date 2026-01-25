"""Unit tests for RBAC core functionality.

Tests the core RBAC classes including Role, Permission, ResourceOwnership,
Privilege, and the require decorator functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.core.rbac import (
    Permission,
    Privilege,
    ResourceOwnership,
    Role,
    RoleComposition,
    _check_ownership_requirement,
    _check_permission_requirement,
    _check_privilege_requirement,
    _check_role_requirement,
    _extract_resource_id,
    _extract_user_from_args,
    require,
)
from app.models.user import User


class TestRole:
    """Test Role enum and composition functionality."""

    def test_role_enum_values(self):
        """Test that Role enum has correct values."""
        assert Role.SUPERADMIN.value == "superadmin"
        assert Role.SALESMAN.value == "salesman"
        assert Role.DATA_ENTRY.value == "data_entry"
        assert Role.PARTNER.value == "partner"
        assert Role.CUSTOMER.value == "customer"

    def test_role_composition_or_operator(self):
        """Test role composition using bitwise OR operator."""
        # Test Role | Role
        composition = Role.SALESMAN | Role.PARTNER
        assert isinstance(composition, RoleComposition)
        assert Role.SALESMAN in composition.roles
        assert Role.PARTNER in composition.roles

        # Test Role | RoleComposition
        composition2 = Role.DATA_ENTRY | composition
        assert isinstance(composition2, RoleComposition)
        assert Role.DATA_ENTRY in composition2.roles
        assert Role.SALESMAN in composition2.roles
        assert Role.PARTNER in composition2.roles

    def test_role_composition_contains(self):
        """Test RoleComposition __contains__ method."""
        composition = Role.SALESMAN | Role.PARTNER
        assert Role.SALESMAN in composition
        assert Role.PARTNER in composition
        assert Role.CUSTOMER not in composition

    def test_role_composition_chaining(self):
        """Test chaining multiple role compositions."""
        composition = Role.SALESMAN | Role.PARTNER | Role.DATA_ENTRY
        assert len(composition.roles) == 3
        assert Role.SALESMAN in composition
        assert Role.PARTNER in composition
        assert Role.DATA_ENTRY in composition


class TestPermission:
    """Test Permission class functionality."""

    def test_permission_creation(self):
        """Test Permission object creation."""
        perm = Permission("configuration", "read")
        assert perm.resource == "configuration"
        assert perm.action == "read"
        assert perm.context == {}

    def test_permission_with_context(self):
        """Test Permission with context."""
        context = {"customer_id": 123}
        perm = Permission("configuration", "read", context)
        assert perm.context == context

    def test_permission_string_representation(self):
        """Test Permission string representation."""
        perm = Permission("configuration", "read")
        assert str(perm) == "configuration:read"


class TestResourceOwnership:
    """Test ResourceOwnership class functionality."""

    def test_resource_ownership_creation(self):
        """Test ResourceOwnership object creation."""
        ownership = ResourceOwnership("configuration")
        assert ownership.resource_type == "configuration"
        assert ownership.id_param == "configuration_id"

    def test_resource_ownership_custom_param(self):
        """Test ResourceOwnership with custom parameter name."""
        ownership = ResourceOwnership("customer", "cust_id")
        assert ownership.resource_type == "customer"
        assert ownership.id_param == "cust_id"

    def test_resource_ownership_string_representation(self):
        """Test ResourceOwnership string representation."""
        ownership = ResourceOwnership("configuration")
        assert str(ownership) == "ownership:configuration"


class TestPrivilege:
    """Test Privilege class functionality."""

    def test_privilege_with_single_role(self):
        """Test Privilege with single role."""
        perm = Permission("configuration", "read")
        privilege = Privilege(Role.CUSTOMER, perm)
        assert Role.CUSTOMER in privilege.roles
        assert privilege.permission == perm
        assert privilege.resource is None

    def test_privilege_with_role_composition(self):
        """Test Privilege with role composition."""
        perm = Permission("configuration", "read")
        roles = Role.SALESMAN | Role.PARTNER
        privilege = Privilege(roles, perm)
        assert Role.SALESMAN in privilege.roles
        assert Role.PARTNER in privilege.roles

    def test_privilege_with_resource_ownership(self):
        """Test Privilege with resource ownership."""
        perm = Permission("configuration", "read")
        ownership = ResourceOwnership("configuration")
        privilege = Privilege(Role.CUSTOMER, perm, ownership)
        assert privilege.resource == ownership

    def test_privilege_with_role_list(self):
        """Test Privilege with list of roles."""
        perm = Permission("configuration", "read")
        roles = [Role.SALESMAN, Role.PARTNER]
        privilege = Privilege(roles, perm)
        assert Role.SALESMAN in privilege.roles
        assert Role.PARTNER in privilege.roles


class TestRoleRequirementChecking:
    """Test role requirement checking functionality."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = "customer"
        return user

    @pytest.fixture
    def superadmin_user(self):
        """Create a superadmin test user."""
        user = User()
        user.id = 2
        user.email = "admin@example.com"
        user.role = "superadmin"
        return user

    @pytest.mark.asyncio
    async def test_check_role_requirement_single_role(self, user):
        """Test checking single role requirement."""
        # User has customer role
        result = await _check_role_requirement(user, Role.CUSTOMER)
        assert result is True

        # User doesn't have salesman role
        result = await _check_role_requirement(user, Role.SALESMAN)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_role_requirement_superadmin_bypass(self, superadmin_user):
        """Test that superadmin bypasses all role checks."""
        result = await _check_role_requirement(superadmin_user, Role.CUSTOMER)
        assert result is True

        result = await _check_role_requirement(superadmin_user, Role.SALESMAN)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_role_requirement_composition(self, user):
        """Test checking role composition requirement."""
        # User has customer role, composition includes customer
        composition = Role.CUSTOMER | Role.SALESMAN
        result = await _check_role_requirement(user, composition)
        assert result is True

        # User doesn't have any role in composition
        composition = Role.SALESMAN | Role.PARTNER
        result = await _check_role_requirement(user, composition)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_role_requirement_list(self, user):
        """Test checking role list requirement."""
        # User has customer role, list includes customer
        roles = [Role.CUSTOMER, Role.SALESMAN]
        result = await _check_role_requirement(user, roles)
        assert result is True

        # User doesn't have any role in list
        roles = [Role.SALESMAN, Role.PARTNER]
        result = await _check_role_requirement(user, roles)
        assert result is False


class TestPermissionRequirementChecking:
    """Test permission requirement checking functionality."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = "customer"
        return user

    @pytest.mark.asyncio
    async def test_check_permission_requirement(self, user):
        """Test checking permission requirement."""
        permission = Permission("configuration", "read")

        with patch("app.core.rbac.rbac_service") as mock_rbac:
            mock_rbac.check_permission = AsyncMock(return_value=True)

            result = await _check_permission_requirement(user, permission)
            assert result is True

            mock_rbac.check_permission.assert_called_once_with(user, "configuration", "read", {})

    @pytest.mark.asyncio
    async def test_check_permission_requirement_with_context(self, user):
        """Test checking permission requirement with context."""
        context = {"customer_id": 123}
        permission = Permission("configuration", "read", context)

        with patch("app.core.rbac.rbac_service") as mock_rbac:
            mock_rbac.check_permission = AsyncMock(return_value=True)

            result = await _check_permission_requirement(user, permission)
            assert result is True

            mock_rbac.check_permission.assert_called_once_with(
                user, "configuration", "read", context
            )


class TestOwnershipRequirementChecking:
    """Test ownership requirement checking functionality."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = "customer"
        return user

    @pytest.mark.asyncio
    async def test_check_ownership_requirement(self, user):
        """Test checking ownership requirement."""
        ownership = ResourceOwnership("configuration")

        # Mock function that has configuration_id parameter
        def mock_func(configuration_id: int, user: User):
            pass

        args = (123, user)
        kwargs = {}

        with patch("app.core.rbac.rbac_service") as mock_rbac:
            mock_rbac.check_resource_ownership = AsyncMock(return_value=True)

            result = await _check_ownership_requirement(user, ownership, mock_func, args, kwargs)
            assert result is True

            mock_rbac.check_resource_ownership.assert_called_once_with(user, "configuration", 123)

    @pytest.mark.asyncio
    async def test_check_ownership_requirement_kwargs(self, user):
        """Test checking ownership requirement with kwargs."""
        ownership = ResourceOwnership("configuration")

        def mock_func(configuration_id: int, user: User):
            pass

        args = (user,)
        kwargs = {"configuration_id": 456}

        with patch("app.core.rbac.rbac_service") as mock_rbac:
            mock_rbac.check_resource_ownership = AsyncMock(return_value=True)

            result = await _check_ownership_requirement(user, ownership, mock_func, args, kwargs)
            assert result is True

            mock_rbac.check_resource_ownership.assert_called_once_with(user, "configuration", 456)


class TestPrivilegeRequirementChecking:
    """Test privilege requirement checking functionality."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = "customer"
        return user

    @pytest.mark.asyncio
    async def test_check_privilege_requirement(self, user):
        """Test checking privilege requirement."""
        permission = Permission("configuration", "read")
        privilege = Privilege(Role.CUSTOMER, permission)

        def mock_func(user: User):
            pass

        args = (user,)
        kwargs = {}

        with patch("app.core.rbac.rbac_service") as mock_rbac:
            mock_rbac.check_permission = AsyncMock(return_value=True)

            result = await _check_privilege_requirement(user, privilege, mock_func, args, kwargs)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_privilege_requirement_with_ownership(self, user):
        """Test checking privilege requirement with ownership."""
        permission = Permission("configuration", "read")
        ownership = ResourceOwnership("configuration")
        privilege = Privilege(Role.CUSTOMER, permission, ownership)

        def mock_func(configuration_id: int, user: User):
            pass

        args = (123, user)
        kwargs = {}

        with patch("app.core.rbac.rbac_service") as mock_rbac:
            mock_rbac.check_permission = AsyncMock(return_value=True)
            mock_rbac.check_resource_ownership = AsyncMock(return_value=True)

            result = await _check_privilege_requirement(user, privilege, mock_func, args, kwargs)
            assert result is True


class TestUserExtraction:
    """Test user extraction from function arguments."""

    def test_extract_user_from_kwargs(self):
        """Test extracting user from keyword arguments."""
        user = User()
        user.id = 1

        args = ()
        kwargs = {"user": user, "other_param": "value"}

        result = _extract_user_from_args(args, kwargs)
        assert result == user

    def test_extract_user_from_args(self):
        """Test extracting user from positional arguments."""
        user = User()
        user.id = 1

        args = ("other_param", user, "another_param")
        kwargs = {}

        result = _extract_user_from_args(args, kwargs)
        assert result == user

    def test_extract_user_not_found(self):
        """Test when user is not found in arguments."""
        args = ("param1", "param2")
        kwargs = {"other": "value"}

        result = _extract_user_from_args(args, kwargs)
        assert result is None


class TestResourceIdExtraction:
    """Test resource ID extraction from function parameters."""

    def test_extract_resource_id_from_kwargs(self):
        """Test extracting resource ID from keyword arguments."""

        def mock_func(configuration_id: int, user: User):
            pass

        args = ()
        kwargs = {"configuration_id": 123, "user": "user_obj"}

        result = _extract_resource_id("configuration_id", mock_func, args, kwargs)
        assert result == 123

    def test_extract_resource_id_from_args(self):
        """Test extracting resource ID from positional arguments."""

        def mock_func(configuration_id: int, user: User):
            pass

        args = (456, "user_obj")
        kwargs = {}

        result = _extract_resource_id("configuration_id", mock_func, args, kwargs)
        assert result == 456

    def test_extract_resource_id_not_found(self):
        """Test when resource ID is not found."""

        def mock_func(other_param: str, user: User):
            pass

        args = ("value", "user_obj")
        kwargs = {}

        result = _extract_resource_id("configuration_id", mock_func, args, kwargs)
        assert result is None


class TestRequireDecorator:
    """Test the require decorator functionality."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = "customer"
        return user

    @pytest.mark.asyncio
    async def test_require_decorator_success(self, user):
        """Test require decorator with successful authorization."""

        @require(Role.CUSTOMER)
        async def test_function(user: User):
            return "success"

        with patch("app.core.rbac._check_role_requirement", return_value=True):
            result = await test_function(user)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_require_decorator_failure(self, user):
        """Test require decorator with failed authorization."""

        @require(Role.SALESMAN)
        async def test_function(user: User):
            return "success"

        with patch("app.core.rbac._check_role_requirement", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await test_function(user)

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_decorator_no_user(self):
        """Test require decorator when no user is provided."""

        @require(Role.CUSTOMER)
        async def test_function():
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function()

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_multiple_require_decorators_or_logic(self, user):
        """Test multiple require decorators with OR logic."""

        # User has customer role, so this should succeed
        @require(Role.SALESMAN)  # User doesn't have this
        @require(Role.CUSTOMER)  # User has this
        async def test_function(user: User):
            return "success"

        # Since user.role is "customer", the CUSTOMER decorator should allow access
        result = await test_function(user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_decorator_with_permission(self, user):
        """Test require decorator with permission requirement."""
        permission = Permission("configuration", "read")

        @require(permission)
        async def test_function(user: User):
            return "success"

        with patch(
            "app.core.rbac._check_permission_requirement", new_callable=AsyncMock, return_value=True
        ):
            result = await test_function(user)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_require_decorator_with_ownership(self, user):
        """Test require decorator with ownership requirement."""
        ownership = ResourceOwnership("configuration")

        @require(ownership)
        async def test_function(configuration_id: int, user: User):
            return "success"

        with patch(
            "app.core.rbac._check_ownership_requirement", new_callable=AsyncMock, return_value=True
        ):
            result = await test_function(123, user)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_require_decorator_with_privilege(self, user):
        """Test require decorator with privilege requirement."""
        permission = Permission("configuration", "read")
        privilege = Privilege(Role.CUSTOMER, permission)

        @require(privilege)
        async def test_function(user: User):
            return "success"

        with patch("app.core.rbac._check_privilege_requirement", return_value=True):
            result = await test_function(user)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_require_decorator_and_logic(self, user):
        """Test require decorator with AND logic within single decorator."""
        permission = Permission("configuration", "read")

        @require(Role.CUSTOMER, permission)
        async def test_function(user: User):
            return "success"

        with (
            patch("app.core.rbac._check_role_requirement", return_value=True),
            patch("app.core.rbac._check_permission_requirement", return_value=True),
        ):
            result = await test_function(user)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_require_decorator_and_logic_failure(self, user):
        """Test require decorator AND logic with one requirement failing."""
        permission = Permission("configuration", "read")

        @require(Role.CUSTOMER, permission)
        async def test_function(user: User):
            return "success"

        with (
            patch("app.core.rbac._check_role_requirement", return_value=True),
            patch("app.core.rbac._check_permission_requirement", return_value=False),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await test_function(user)

            assert exc_info.value.status_code == 403
