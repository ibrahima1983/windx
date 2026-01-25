"""Unit tests for Casbin policy evaluation in RBAC system.

This module tests the Casbin policy engine integration, policy loading,
and basic role-based permissions.

Test Classes:
    TestCasbinPolicyEvaluation: Tests for Casbin policy evaluation
    TestCasbinPolicyManagement: Tests for policy loading and saving
    TestCasbinCustomerContext: Tests for customer-context permissions
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.rbac import RBACService, Role
from app.models.user import User


class TestCasbinPolicyEvaluation:
    """Tests for basic Casbin policy evaluation.

    Validates: Requirements 3.1, 3.2, 6.1
    """

    @pytest.fixture
    def rbac_service(self):
        """Create RBAC service with mocked Casbin enforcer."""
        with patch("app.core.rbac.casbin.Enforcer") as mock_enforcer_class:
            mock_enforcer = MagicMock()
            mock_enforcer_class.return_value = mock_enforcer

            service = RBACService()
            service.enforcer = mock_enforcer
            return service, mock_enforcer

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.mark.asyncio
    async def test_check_permission_basic(self, rbac_service, user):
        """Test basic permission checking with Casbin."""
        service, mock_enforcer = rbac_service

        # Mock enforcer to return True
        mock_enforcer.enforce.return_value = True

        result = await service.check_permission(user, "configuration", "read")

        assert result is True
        mock_enforcer.enforce.assert_called_once_with(user.email, "configuration", "read")

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, rbac_service, user):
        """Test permission denial with Casbin."""
        service, mock_enforcer = rbac_service

        # Mock enforcer to return False
        mock_enforcer.enforce.return_value = False

        result = await service.check_permission(user, "admin", "access")

        assert result is False
        mock_enforcer.enforce.assert_called_once_with(user.email, "admin", "access")

    @pytest.mark.asyncio
    async def test_check_permission_caching(self, rbac_service, user):
        """Test that permission results are cached."""
        service, mock_enforcer = rbac_service

        # Mock enforcer to return True
        mock_enforcer.enforce.return_value = True

        # First call
        result1 = await service.check_permission(user, "configuration", "read")
        # Second call (should use cache)
        result2 = await service.check_permission(user, "configuration", "read")

        assert result1 is True
        assert result2 is True
        # Enforcer should only be called once due to caching
        mock_enforcer.enforce.assert_called_once_with(user.email, "configuration", "read")

    @pytest.mark.asyncio
    async def test_check_permission_with_context(self, rbac_service, user):
        """Test permission checking with additional context."""
        service, mock_enforcer = rbac_service

        # Mock enforcer to return True
        mock_enforcer.enforce.return_value = True

        context = {"customer_id": 123}
        result = await service.check_permission(user, "configuration", "read", context)

        assert result is True
        # Context doesn't affect basic Casbin call, but is stored for future use
        mock_enforcer.enforce.assert_called_once_with(user.email, "configuration", "read")

    @pytest.mark.asyncio
    async def test_check_permission_exception_handling(self, rbac_service, user):
        """Test that exceptions in Casbin evaluation are handled gracefully."""
        service, mock_enforcer = rbac_service

        # Mock enforcer to raise exception
        mock_enforcer.enforce.side_effect = Exception("Casbin error")

        result = await service.check_permission(user, "configuration", "read")

        assert result is False

    @pytest.mark.asyncio
    async def test_superadmin_resource_ownership(self, rbac_service):
        """Test that superadmin has access to all resources."""
        service, mock_enforcer = rbac_service

        # Create superadmin user
        superadmin = User()
        superadmin.id = 1
        superadmin.email = "admin@example.com"
        superadmin.role = Role.SUPERADMIN.value

        result = await service.check_resource_ownership(superadmin, "configuration", 123)

        assert result is True
        # Should not call enforcer for superadmin resource ownership

    @pytest.mark.asyncio
    async def test_regular_user_resource_ownership(self, rbac_service, user):
        """Test resource ownership for regular users."""
        service, mock_enforcer = rbac_service

        # Mock get_accessible_customers to return empty list
        with patch.object(
            service, "get_accessible_customers", new_callable=AsyncMock
        ) as mock_customers:
            mock_customers.return_value = []

            result = await service.check_resource_ownership(user, "customer", 123)

            assert result is False
            mock_customers.assert_called_once_with(user)


class TestCasbinPolicyManagement:
    """Tests for Casbin policy loading and saving.

    Validates: Requirements 3.1, 3.2, 6.1
    """

    def test_rbac_service_initialization(self):
        """Test that RBACService initializes Casbin enforcer correctly."""
        with patch("app.core.rbac.casbin.Enforcer") as mock_enforcer_class:
            mock_enforcer = MagicMock()
            mock_enforcer_class.return_value = mock_enforcer

            service = RBACService()

            # Verify enforcer was created with correct config files
            mock_enforcer_class.assert_called_once_with(
                "config/rbac_model.conf", "config/rbac_policy.csv"
            )
            assert service.enforcer == mock_enforcer

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        with patch("app.core.rbac.casbin.Enforcer"):
            service = RBACService()

            # Add some items to cache
            service._permission_cache["test"] = True
            service._customer_cache[1] = [1, 2, 3]

            # Clear cache
            service.clear_cache()

            assert len(service._permission_cache) == 0
            assert len(service._customer_cache) == 0

    @pytest.mark.asyncio
    async def test_policy_loading_error_handling(self):
        """Test handling of policy loading errors."""
        with patch("app.core.rbac.casbin.Enforcer") as mock_enforcer_class:
            # Mock enforcer creation to raise exception
            mock_enforcer_class.side_effect = Exception("Policy file not found")

            with pytest.raises(Exception):
                RBACService()


class TestCasbinCustomerContext:
    """Tests for customer-context permissions.

    Validates: Requirements 3.1, 3.2, 6.1
    """

    @pytest.fixture
    def rbac_service_with_db(self):
        """Create RBAC service with mocked database."""
        with patch("app.core.rbac.casbin.Enforcer") as mock_enforcer_class:
            mock_enforcer = MagicMock()
            mock_enforcer_class.return_value = mock_enforcer

            # Mock database session
            mock_db = AsyncMock()

            from app.services.rbac import RBACService as ServiceRBACService

            service = ServiceRBACService(mock_db)
            service.enforcer = mock_enforcer

            return service, mock_enforcer, mock_db

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.mark.asyncio
    async def test_get_accessible_customers_superadmin(self, rbac_service_with_db):
        """Test that superadmin gets access to all customers."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Create superadmin user
        superadmin = User()
        superadmin.id = 1
        superadmin.email = "admin@example.com"
        superadmin.role = Role.SUPERADMIN.value

        # Mock database to return customer IDs
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[(1,), (2,), (3,)])
        mock_db.execute = AsyncMock(return_value=mock_result)

        customers = await service.get_accessible_customers(superadmin)

        assert customers == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_accessible_customers_regular_user(self, rbac_service_with_db, user):
        """Test that regular users get access to their associated customer."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Mock database to return user's customer ID
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[(42,)])
        mock_db.execute = AsyncMock(return_value=mock_result)

        customers = await service.get_accessible_customers(user)

        assert customers == [42]

    @pytest.mark.asyncio
    async def test_get_accessible_customers_no_customer(self, rbac_service_with_db, user):
        """Test that users with no associated customer get empty list."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Mock database to return None (no customer found)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        customers = await service.get_accessible_customers(user)

        assert customers == []

    @pytest.mark.asyncio
    async def test_get_accessible_customers_caching(self, rbac_service_with_db, user):
        """Test that customer access results are cached."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Mock database to return customer ID
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[(42,)])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # First call
        customers1 = await service.get_accessible_customers(user)
        # Second call (should use cache)
        customers2 = await service.get_accessible_customers(user)

        assert customers1 == [42]
        assert customers2 == [42]
        # Database should only be called once due to caching
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_resource_ownership_configuration(self, rbac_service_with_db, user):
        """Test resource ownership checking for configurations."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Mock get_accessible_customers
        with patch.object(
            service, "get_accessible_customers", new_callable=AsyncMock
        ) as mock_customers:
            mock_customers.return_value = [42]

            # Mock database to return configuration's customer ID
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=42)
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await service.check_resource_ownership(user, "configuration", 123)

            assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_ownership_configuration_denied(self, rbac_service_with_db, user):
        """Test resource ownership denial for configurations."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Mock get_accessible_customers
        with patch.object(
            service, "get_accessible_customers", new_callable=AsyncMock
        ) as mock_customers:
            mock_customers.return_value = [42]

            # Mock database to return different customer ID
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=99)
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await service.check_resource_ownership(user, "configuration", 123)

            assert result is False

    @pytest.mark.asyncio
    async def test_check_resource_ownership_unknown_type(self, rbac_service_with_db, user):
        """Test resource ownership for unknown resource types."""
        service, mock_enforcer, mock_db = rbac_service_with_db

        # Mock get_accessible_customers to return empty list
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.check_resource_ownership(user, "unknown_resource", 123)

        assert result is False
