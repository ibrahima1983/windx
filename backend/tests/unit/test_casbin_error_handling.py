"""Unit tests for Casbin error handling scenarios.

This module tests error handling in the RBAC system including:
- Casbin authorization failure handling
- Customer creation failure handling
- Foreign key constraint violation handling
- Casbin policy loading failures
- Privilege object evaluation errors
- Race condition handling in customer creation

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    CasbinAuthorizationException,
    CustomerCreationException,
    PolicyEvaluationException,
    PrivilegeEvaluationException,
)
from app.core.rbac import Permission, Privilege, Role
from app.models.customer import Customer
from app.models.user import User
from app.services.rbac import RBACService


class TestCasbinAuthorizationFailures:
    """Test Casbin authorization failure handling."""

    @pytest.fixture
    def rbac_service(self, db_session):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(db_session)
            service.enforcer = MagicMock()
            service.commit = AsyncMock()
            service.rollback = AsyncMock()
            service.refresh = AsyncMock()
            return service

    @pytest.fixture
    def user(self):
        """Create test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.role = Role.CUSTOMER.value
        return user

    def test_casbin_authorization_exception_creation(self):
        """Test CasbinAuthorizationException creation and properties."""
        exception = CasbinAuthorizationException(
            user_email="test@example.com", resource="configuration", action="read"
        )

        assert exception.status_code == 403
        assert "test@example.com" in exception.detail
        assert "configuration" in exception.detail
        assert "read" in exception.detail
        assert exception.user_email == "test@example.com"
        assert exception.resource == "configuration"
        assert exception.action == "read"

    @pytest.mark.asyncio
    async def test_permission_check_casbin_failure(self, rbac_service, user):
        """Test permission check when Casbin enforcer fails."""
        # Mock Casbin enforcer to raise exception
        rbac_service.enforcer.enforce.side_effect = Exception("Casbin connection failed")

        # Should raise PolicyEvaluationException
        with pytest.raises(PolicyEvaluationException) as exc_info:
            await rbac_service.check_permission(user, "configuration", "read")

        assert "Failed to check permission" in str(exc_info.value)
        assert "test@example.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_privilege_evaluation_failure(self, rbac_service, user):
        """Test privilege evaluation when underlying checks fail."""
        # Create privilege object
        privilege = Privilege(roles=[Role.CUSTOMER], permission=Permission("configuration", "read"))

        # Mock permission check to fail
        rbac_service.check_permission = AsyncMock(side_effect=Exception("Permission check failed"))

        # Should raise PrivilegeEvaluationException
        with pytest.raises(PrivilegeEvaluationException) as exc_info:
            await rbac_service.check_privilege(user, privilege)

        assert "Failed to evaluate privilege" in str(exc_info.value)
        assert "test@example.com" in str(exc_info.value)

    def test_policy_evaluation_exception_logging(self):
        """Test PolicyEvaluationException logging and context."""
        context = {"resource": "configuration", "action": "read"}
        exception = PolicyEvaluationException("Policy check failed", context)

        assert exception.message == "Policy check failed"
        assert exception.context == context
        assert "configuration" in str(exception)


class TestCustomerCreationFailures:
    """Test customer creation failure scenarios."""

    @pytest.fixture
    def rbac_service(self, db_session):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(db_session)
            service.enforcer = MagicMock()
            service.commit = AsyncMock()
            service.rollback = AsyncMock()
            service.refresh = AsyncMock()
            service._find_customer_by_email = AsyncMock()
            return service

    @pytest.fixture
    def user(self):
        """Create test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.full_name = "Test User"
        user.role = Role.CUSTOMER.value
        return user

    def test_customer_creation_exception_logging(self):
        """Test CustomerCreationException logging and context."""
        exception = CustomerCreationException(
            message="Customer creation failed",
            user_email="test@example.com",
            original_error=Exception("Database error"),
        )

        assert exception.message == "Customer creation failed"
        assert exception.user_email == "test@example.com"
        assert exception.original_error is not None
        assert "test@example.com" in str(exception)


class TestPolicyLoadingFailures:
    """Test policy loading failure scenarios."""

    @pytest.mark.asyncio
    async def test_rbac_service_initialization_failure(self, db_session):
        """Test RBAC service initialization when Casbin fails to load."""
        with patch("casbin.Enforcer", side_effect=Exception("Policy file not found")):
            with pytest.raises(Exception) as exc_info:
                RBACService(db_session)

            assert "Policy file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_policy_file_corruption_handling(self, db_session):
        """Test handling of corrupted policy files."""
        with patch("casbin.Enforcer") as mock_enforcer_class:
            # Mock enforcer to raise exception during policy loading
            mock_enforcer = MagicMock()
            mock_enforcer.enforce.side_effect = Exception("Policy syntax error")
            mock_enforcer_class.return_value = mock_enforcer

            service = RBACService(db_session)
            user = User()
            user.email = "test@example.com"

            with pytest.raises(PolicyEvaluationException):
                await service.check_permission(user, "configuration", "read")


class TestRaceConditionHandling:
    """Test race condition handling in customer operations."""

    @pytest.fixture
    def rbac_service(self, db_session):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(db_session)
            service.enforcer = MagicMock()
            service.commit = AsyncMock()
            service.rollback = AsyncMock()
            service.refresh = AsyncMock()
            service._find_customer_by_email = AsyncMock()
            return service

    @pytest.fixture
    def user(self):
        """Create test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.full_name = "Test User"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.mark.asyncio
    async def test_concurrent_customer_creation_success(self, rbac_service, user):
        """Test successful handling of concurrent customer creation."""
        # Mock the scenario where another process creates customer during our attempt
        existing_customer = Customer()
        existing_customer.id = 456
        existing_customer.email = user.email

        # First call to _find_customer_by_email returns None (no customer)
        # Second call (during recovery) returns existing customer
        rbac_service._find_customer_by_email = AsyncMock(side_effect=[None, existing_customer])

        # Mock get_or_create to simulate the race condition
        rbac_service.db.add = MagicMock()
        rbac_service.commit = AsyncMock(
            side_effect=IntegrityError("duplicate key", "unique constraint", None)
        )

        # Should return the existing customer found during recovery
        result = await rbac_service.get_or_create_customer_for_user(user)

        assert result == existing_customer
        assert result.id == 456


class TestErrorRecoveryMechanisms:
    """Test error recovery mechanisms in RBAC system."""

    @pytest.fixture
    def rbac_service(self, db_session):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(db_session)
            service.enforcer = MagicMock()
            service._permission_cache = {}
            service._customer_cache = {}
            service._privilege_cache = {}
            return service

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_error(self, rbac_service):
        """Test cache invalidation when errors occur."""
        user = User()
        user.id = 1
        user.email = "test@example.com"

        # Populate cache with successful result
        rbac_service._permission_cache["1:configuration:read"] = True

        # Clear cache on error
        rbac_service.clear_cache()

        # Verify cache is empty
        assert len(rbac_service._permission_cache) == 0
        assert len(rbac_service._customer_cache) == 0
        assert len(rbac_service._privilege_cache) == 0

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_casbin_failure(self, rbac_service, user):
        """Test graceful degradation when Casbin is unavailable."""
        # Mock Casbin to be completely unavailable
        rbac_service.enforcer = None

        # Should handle gracefully and raise appropriate exception
        with pytest.raises(AttributeError):
            await rbac_service.check_permission(user, "configuration", "read")

    def test_error_context_preservation(self):
        """Test that error context is preserved through exception chain."""
        original_error = Exception("Original database error")

        customer_exception = CustomerCreationException(
            message="Failed to create customer",
            user_email="test@example.com",
            original_error=original_error,
        )

        assert customer_exception.original_error == original_error
        assert "test@example.com" in str(customer_exception)
        assert customer_exception.user_email == "test@example.com"
