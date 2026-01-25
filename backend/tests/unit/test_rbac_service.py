"""Unit tests for RBAC service functionality.

Tests the RBACService class including permission checking, resource ownership
validation, customer management, and policy operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Role
from app.models.customer import Customer
from app.models.user import User
from app.services.rbac import RBACService


class TestRBACService:
    """Test RBACService functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def rbac_service(self, mock_db):
        """Create RBACService instance with mocked dependencies."""
        with patch("casbin.Enforcer") as mock_enforcer:
            service = RBACService(mock_db)
            service.enforcer = mock_enforcer.return_value
            return service

    @pytest.fixture
    def user(self):
        """Create a test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.full_name = "Test User"
        user.role = "customer"
        return user

    @pytest.fixture
    def superadmin_user(self):
        """Create a superadmin test user."""
        user = User()
        user.id = 2
        user.email = "admin@example.com"
        user.username = "admin"
        user.full_name = "Admin User"
        user.role = "superadmin"
        return user

    @pytest.fixture
    def customer(self):
        """Create a test customer."""
        customer = Customer()
        customer.id = 1
        customer.email = "test@example.com"
        customer.contact_person = "Test User"
        customer.customer_type = "residential"
        customer.is_active = True
        return customer


class TestPermissionChecking(TestRBACService):
    """Test permission checking functionality."""

    @pytest.mark.asyncio
    async def test_check_permission_success(self, rbac_service, user):
        """Test successful permission check."""
        rbac_service.enforcer.enforce.return_value = True

        result = await rbac_service.check_permission(user, "configuration", "read")

        assert result is True
        rbac_service.enforcer.enforce.assert_called_once_with(user.email, "configuration", "read")

    @pytest.mark.asyncio
    async def test_check_permission_failure(self, rbac_service, user):
        """Test failed permission check."""
        rbac_service.enforcer.enforce.return_value = False

        result = await rbac_service.check_permission(user, "configuration", "write")

        assert result is False
        rbac_service.enforcer.enforce.assert_called_once_with(user.email, "configuration", "write")

    @pytest.mark.asyncio
    async def test_check_permission_caching(self, rbac_service, user):
        """Test permission check caching."""
        rbac_service.enforcer.enforce.return_value = True

        # First call
        result1 = await rbac_service.check_permission(user, "configuration", "read")
        # Second call should use cache
        result2 = await rbac_service.check_permission(user, "configuration", "read")

        assert result1 is True
        assert result2 is True
        # Enforcer should only be called once due to caching
        rbac_service.enforcer.enforce.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_permission_exception_handling(self, rbac_service, user):
        """Test permission check exception handling."""
        rbac_service.enforcer.enforce.side_effect = Exception("Casbin error")

        result = await rbac_service.check_permission(user, "configuration", "read")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_with_context(self, rbac_service, user):
        """Test permission check with context."""
        rbac_service.enforcer.enforce.return_value = True
        context = {"customer_id": 123}

        result = await rbac_service.check_permission(user, "configuration", "read", context)

        assert result is True
        # Context doesn't affect the basic Casbin call in this implementation
        rbac_service.enforcer.enforce.assert_called_once_with(user.email, "configuration", "read")


class TestResourceOwnership(TestRBACService):
    """Test resource ownership validation."""

    @pytest.mark.asyncio
    async def test_check_resource_ownership_superadmin(self, rbac_service, superadmin_user):
        """Test that superadmin has access to all resources."""
        result = await rbac_service.check_resource_ownership(superadmin_user, "configuration", 123)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_ownership_customer_direct(self, rbac_service, user):
        """Test direct customer resource ownership."""
        rbac_service.get_accessible_customers = AsyncMock(return_value=[1, 2, 3])

        result = await rbac_service.check_resource_ownership(user, "customer", 2)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_ownership_customer_denied(self, rbac_service, user):
        """Test denied customer resource ownership."""
        rbac_service.get_accessible_customers = AsyncMock(return_value=[1, 2, 3])

        result = await rbac_service.check_resource_ownership(user, "customer", 5)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_resource_ownership_configuration(self, rbac_service, user, mock_db):
        """Test configuration resource ownership through customer relationship."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # customer_id
        mock_db.execute.return_value = mock_result

        rbac_service.get_accessible_customers = AsyncMock(return_value=[1, 2, 3])

        result = await rbac_service.check_resource_ownership(user, "configuration", 123)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_resource_ownership_configuration_denied(self, rbac_service, user, mock_db):
        """Test denied configuration resource ownership."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 5  # customer_id not accessible
        mock_db.execute.return_value = mock_result

        rbac_service.get_accessible_customers = AsyncMock(return_value=[1, 2, 3])

        result = await rbac_service.check_resource_ownership(user, "configuration", 123)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_resource_ownership_configuration_not_found(
        self, rbac_service, user, mock_db
    ):
        """Test configuration resource ownership when configuration not found."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await rbac_service.check_resource_ownership(user, "configuration", 999)

        assert result is False


class TestAccessibleCustomers(TestRBACService):
    """Test accessible customers functionality."""

    @pytest.mark.asyncio
    async def test_get_accessible_customers_superadmin(
        self, rbac_service, superadmin_user, mock_db
    ):
        """Test that superadmin gets all customers."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (2,), (3,), (4,)]
        mock_db.execute.return_value = mock_result

        result = await rbac_service.get_accessible_customers(superadmin_user)

        assert result == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_get_accessible_customers_regular_user(self, rbac_service, user, mock_db):
        """Test that regular user gets their associated customer."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # customer_id
        mock_db.execute.return_value = mock_result

        result = await rbac_service.get_accessible_customers(user)

        assert result == [1]

    @pytest.mark.asyncio
    async def test_get_accessible_customers_no_customer(self, rbac_service, user, mock_db):
        """Test user with no associated customer."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await rbac_service.get_accessible_customers(user)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_accessible_customers_caching(self, rbac_service, user, mock_db):
        """Test accessible customers caching."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_db.execute.return_value = mock_result

        # First call
        result1 = await rbac_service.get_accessible_customers(user)
        # Second call should use cache
        result2 = await rbac_service.get_accessible_customers(user)

        assert result1 == [1]
        assert result2 == [1]
        # Database should only be queried once due to caching
        mock_db.execute.assert_called_once()


class TestCustomerManagement(TestRBACService):
    """Test customer management functionality."""

    @pytest.mark.asyncio
    async def test_get_or_create_customer_existing(self, rbac_service, user, customer, mock_db):
        """Test getting existing customer."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = customer
        mock_db.execute.return_value = mock_result

        result = await rbac_service.get_or_create_customer_for_user(user)

        assert result == customer
        # Should not add new customer to session
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_customer_new(self, rbac_service, user, mock_db):
        """Test creating new customer."""
        # Mock database query result - no existing customer
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock commit and refresh
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        result = await rbac_service.get_or_create_customer_for_user(user)

        # Should create new customer
        assert isinstance(result, Customer)
        assert result.email == user.email
        assert result.contact_person == user.full_name
        assert result.customer_type == "residential"
        assert result.is_active is True
        assert f"Auto-created from user: {user.username}" in result.notes

        # Should add to session and commit
        mock_db.add.assert_called_once()
        rbac_service.commit.assert_called_once()
        rbac_service.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_customer_fallback_username(self, rbac_service, mock_db):
        """Test creating customer with username fallback when no full_name."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.full_name = None  # No full name
        user.role = "customer"

        # Mock database query result - no existing customer
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock commit and refresh
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        result = await rbac_service.get_or_create_customer_for_user(user)

        # Should use username as contact_person
        assert result.contact_person == user.username

    @pytest.mark.asyncio
    async def test_get_or_create_customer_creation_failure(self, rbac_service, user, mock_db):
        """Test customer creation failure handling."""
        # Mock database query result - no existing customer
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock commit failure
        rbac_service.commit = AsyncMock(side_effect=Exception("Database error"))
        rbac_service.rollback = AsyncMock()

        # Mock finding customer after rollback (race condition scenario)
        rbac_service._find_customer_by_email = AsyncMock(return_value=None)

        with pytest.raises(Exception):  # Should raise DatabaseException
            await rbac_service.get_or_create_customer_for_user(user)

        rbac_service.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_customer_race_condition(
        self, rbac_service, user, customer, mock_db
    ):
        """Test customer creation race condition handling."""
        # Mock database query result - no existing customer initially
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock commit failure (race condition)
        rbac_service.commit = AsyncMock(side_effect=Exception("Unique constraint violation"))
        rbac_service.rollback = AsyncMock()

        # Mock finding customer after rollback (another process created it)
        rbac_service._find_customer_by_email = AsyncMock(return_value=customer)

        result = await rbac_service.get_or_create_customer_for_user(user)

        assert result == customer
        rbac_service.rollback.assert_called_once()


class TestRoleManagement(TestRBACService):
    """Test role management functionality."""

    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, rbac_service, user):
        """Test assigning role to user."""
        rbac_service.commit = AsyncMock()
        rbac_service.clear_cache = MagicMock()

        await rbac_service.assign_role_to_user(user, Role.SALESMAN)

        assert user.role == Role.SALESMAN.value
        rbac_service.commit.assert_called_once()
        rbac_service.enforcer.remove_grouping_policy.assert_called_once_with(user.email)
        rbac_service.enforcer.add_grouping_policy.assert_called_once_with(
            user.email, Role.SALESMAN.value
        )
        rbac_service.clear_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_customer_to_user(self, rbac_service, user):
        """Test assigning customer access to user."""
        customer_id = 123

        await rbac_service.assign_customer_to_user(user, customer_id)

        rbac_service.enforcer.add_grouping_policy.assert_called_once_with(
            user.email, "customer", str(customer_id)
        )
        # Should clear customer cache for this user
        assert user.id not in rbac_service._customer_cache

    @pytest.mark.asyncio
    async def test_initialize_user_policies_customer(self, rbac_service, user, customer):
        """Test initializing policies for customer user."""
        rbac_service.get_or_create_customer_for_user = AsyncMock(return_value=customer)

        await rbac_service.initialize_user_policies(user)

        rbac_service.enforcer.add_grouping_policy.assert_any_call(user.email, user.role)
        rbac_service.enforcer.add_grouping_policy.assert_any_call(
            user.email, "customer", str(customer.id)
        )

    @pytest.mark.asyncio
    async def test_initialize_user_policies_non_customer(self, rbac_service):
        """Test initializing policies for non-customer user."""
        user = User()
        user.email = "sales@example.com"
        user.role = "salesman"

        await rbac_service.initialize_user_policies(user)

        rbac_service.enforcer.add_grouping_policy.assert_called_once_with(user.email, user.role)


class TestCacheManagement(TestRBACService):
    """Test cache management functionality."""

    def test_clear_cache(self, rbac_service):
        """Test clearing all caches."""
        # Add some data to caches
        rbac_service._permission_cache["test"] = True
        rbac_service._customer_cache[1] = [1, 2, 3]

        rbac_service.clear_cache()

        assert len(rbac_service._permission_cache) == 0
        assert len(rbac_service._customer_cache) == 0


class TestPrivateHelperMethods(TestRBACService):
    """Test private helper methods."""

    @pytest.mark.asyncio
    async def test_find_customer_by_email_found(self, rbac_service, customer, mock_db):
        """Test finding customer by email when customer exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = customer
        mock_db.execute.return_value = mock_result

        result = await rbac_service._find_customer_by_email("test@example.com")

        assert result == customer

    @pytest.mark.asyncio
    async def test_find_customer_by_email_not_found(self, rbac_service, mock_db):
        """Test finding customer by email when customer doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await rbac_service._find_customer_by_email("notfound@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_customer_from_user(self, rbac_service, user, mock_db):
        """Test creating customer from user data."""
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        result = await rbac_service._create_customer_from_user(user)

        assert isinstance(result, Customer)
        assert result.email == user.email
        assert result.contact_person == user.full_name
        assert result.customer_type == "residential"
        assert result.is_active is True
        assert f"Auto-created from user: {user.username}" in result.notes

        mock_db.add.assert_called_once_with(result)
        rbac_service.commit.assert_called_once()
        rbac_service.refresh.assert_called_once_with(result)
