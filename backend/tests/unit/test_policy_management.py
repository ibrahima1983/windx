"""Unit tests for policy management functionality.

This module tests policy management operations including:
- Dynamic customer assignment to salesmen
- Policy addition and removal
- Policy backup and restore
- Privilege object creation and management

Requirements: 6.1, 6.2, 6.3, 9.3
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import PolicyEvaluationException
from app.core.rbac import Role
from app.models.customer import Customer
from app.models.user import User
from app.services.policy_manager import PolicyManager


class TestPolicyManager:
    """Test PolicyManager functionality."""

    @pytest.fixture
    def policy_manager(self, db_session):
        """Create PolicyManager with mocked database."""
        with patch("casbin.Enforcer"):
            manager = PolicyManager(db_session)
            manager.enforcer = MagicMock()
            manager.enforcer.enable_auto_save = MagicMock()
            return manager

    @pytest.fixture
    def customer(self):
        """Create test customer."""
        customer = Customer()
        customer.id = 123
        customer.email = "customer@example.com"
        customer.company_name = "Test Company"
        customer.contact_person = "John Doe"
        return customer

    @pytest.fixture
    def user(self):
        """Create test user."""
        user = User()
        user.id = 1
        user.email = "salesman@example.com"
        user.username = "salesman"
        user.role = Role.SALESMAN.value
        return user


class TestPolicyAdditionAndRemoval(TestPolicyManager):
    """Test policy addition and removal operations."""

    @pytest.mark.asyncio
    async def test_add_policy_success(self, policy_manager):
        """Test successful policy addition."""
        # Mock enforcer to return True (policy added)
        policy_manager.enforcer.add_policy.return_value = True
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.add_policy(
            subject="test_role", resource="configuration", action="read", effect="allow"
        )

        assert result is True

        # Verify enforcer was called correctly
        policy_manager.enforcer.add_policy.assert_called_once_with(
            "test_role", "configuration", "read", "allow"
        )

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="add_policy",
            policy_data={
                "subject": "test_role",
                "resource": "configuration",
                "action": "read",
                "effect": "allow",
            },
        )

    @pytest.mark.asyncio
    async def test_add_policy_failure(self, policy_manager):
        """Test policy addition failure handling."""
        # Mock enforcer to raise exception
        policy_manager.enforcer.add_policy.side_effect = Exception("Casbin error")

        with pytest.raises(PolicyEvaluationException) as exc_info:
            await policy_manager.add_policy(
                subject="test_role", resource="configuration", action="read"
            )

        assert "Failed to add policy for test_role" in str(exc_info.value)
        assert exc_info.value.policy_context["subject"] == "test_role"

    @pytest.mark.asyncio
    async def test_remove_policy_success(self, policy_manager):
        """Test successful policy removal."""
        # Mock enforcer to return True (policy removed)
        policy_manager.enforcer.remove_policy.return_value = True
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.remove_policy(
            subject="test_role", resource="configuration", action="read", effect="allow"
        )

        assert result is True

        # Verify enforcer was called correctly
        policy_manager.enforcer.remove_policy.assert_called_once_with(
            "test_role", "configuration", "read", "allow"
        )

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="remove_policy",
            policy_data={
                "subject": "test_role",
                "resource": "configuration",
                "action": "read",
                "effect": "allow",
            },
        )

    @pytest.mark.asyncio
    async def test_remove_policy_not_exists(self, policy_manager):
        """Test removing non-existent policy."""
        # Mock enforcer to return False (policy doesn't exist)
        policy_manager.enforcer.remove_policy.return_value = False
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.remove_policy(
            subject="nonexistent_role", resource="configuration", action="read"
        )

        assert result is False

        # Verify no audit logging for non-existent policy
        policy_manager._log_policy_change.assert_not_called()


class TestCustomerAssignment(TestPolicyManager):
    """Test customer assignment functionality."""

    @pytest.mark.asyncio
    async def test_assign_customer_to_user_success(self, policy_manager, customer, user):
        """Test successful customer assignment to user."""
        # Mock database query to return customer
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = customer
        policy_manager.db.execute = AsyncMock(return_value=mock_result)

        # Mock enforcer to return True (assignment successful)
        policy_manager.enforcer.add_grouping_policy.return_value = True
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.assign_customer_to_user(
            user_email=user.email, customer_id=customer.id, assignment_type="assigned"
        )

        assert result is True

        # Verify enforcer was called correctly
        policy_manager.enforcer.add_grouping_policy.assert_called_once_with(
            user.email, "customer", str(customer.id)
        )

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="assign_customer",
            policy_data={
                "user_email": user.email,
                "customer_id": customer.id,
                "assignment_type": "assigned",
                "customer_name": customer.company_name,
            },
        )

    @pytest.mark.asyncio
    async def test_assign_customer_not_found(self, policy_manager, user):
        """Test customer assignment when customer doesn't exist."""
        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        policy_manager.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(PolicyEvaluationException) as exc_info:
            await policy_manager.assign_customer_to_user(
                user_email=user.email, customer_id=999, assignment_type="assigned"
            )

        assert "Customer 999 not found" in str(exc_info.value)
        assert exc_info.value.policy_context["customer_id"] == 999

    @pytest.mark.asyncio
    async def test_remove_customer_assignment_success(self, policy_manager, customer, user):
        """Test successful customer assignment removal."""
        # Mock enforcer to return True (assignment removed)
        policy_manager.enforcer.remove_grouping_policy.return_value = True
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.remove_customer_assignment(
            user_email=user.email, customer_id=customer.id
        )

        assert result is True

        # Verify enforcer was called correctly
        policy_manager.enforcer.remove_grouping_policy.assert_called_once_with(
            user.email, "customer", str(customer.id)
        )

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="remove_customer_assignment",
            policy_data={"user_email": user.email, "customer_id": customer.id},
        )

    @pytest.mark.asyncio
    async def test_get_user_customer_assignments(self, policy_manager, user):
        """Test getting user customer assignments."""
        # Mock enforcer to return grouping policies
        mock_groupings = [
            [user.email, "customer", "123"],
            [user.email, "customer", "456"],
            ["other@example.com", "customer", "789"],
            [user.email, "role", "salesman"],  # Non-customer grouping
        ]
        policy_manager.enforcer.get_grouping_policy.return_value = mock_groupings

        result = await policy_manager.get_user_customer_assignments(user.email)

        assert result == [123, 456]

    @pytest.mark.asyncio
    async def test_get_user_customer_assignments_empty(self, policy_manager, user):
        """Test getting customer assignments when user has none."""
        # Mock enforcer to return empty groupings
        policy_manager.enforcer.get_grouping_policy.return_value = []

        result = await policy_manager.get_user_customer_assignments(user.email)

        assert result == []


class TestPolicyBackupRestore(TestPolicyManager):
    """Test policy backup and restore functionality."""

    @pytest.mark.asyncio
    async def test_backup_policies_success(self, policy_manager):
        """Test successful policy backup."""
        # Mock enforcer to return policies
        mock_policies = [
            ["salesman", "configuration", "read", "allow"],
            ["customer", "quote", "read", "allow"],
        ]
        mock_groupings = [["user@example.com", "salesman"], ["customer@example.com", "customer"]]

        policy_manager.enforcer.get_policy.return_value = mock_policies
        policy_manager.enforcer.get_grouping_policy.return_value = mock_groupings
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.backup_policies()

        assert "timestamp" in result
        assert result["policies"] == mock_policies
        assert result["grouping_policies"] == mock_groupings
        assert result["metadata"]["total_policies"] == 2
        assert result["metadata"]["total_groupings"] == 2

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="backup_policies", policy_data={"policy_count": 2, "grouping_count": 2}
        )

    @pytest.mark.asyncio
    async def test_restore_policies_success(self, policy_manager):
        """Test successful policy restore."""
        # Mock backup data
        backup_data = {
            "timestamp": "2024-01-01T00:00:00",
            "policies": [
                ["salesman", "configuration", "read", "allow"],
                ["customer", "quote", "read", "allow"],
            ],
            "grouping_policies": [
                ["user@example.com", "salesman"],
                ["customer@example.com", "customer"],
            ],
        }

        # Mock enforcer methods
        policy_manager.enforcer.clear_policy = MagicMock()
        policy_manager.enforcer.add_policy = MagicMock()
        policy_manager.enforcer.add_grouping_policy = MagicMock()
        policy_manager.enforcer.save_policy = MagicMock()
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.restore_policies(backup_data)

        assert result is True

        # Verify enforcer calls
        policy_manager.enforcer.clear_policy.assert_called_once()
        assert policy_manager.enforcer.add_policy.call_count == 2
        assert policy_manager.enforcer.add_grouping_policy.call_count == 2
        policy_manager.enforcer.save_policy.assert_called_once()

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="restore_policies",
            policy_data={
                "restored_policies": 2,
                "restored_groupings": 2,
                "backup_timestamp": "2024-01-01T00:00:00",
            },
        )

    @pytest.mark.asyncio
    async def test_restore_policies_invalid_data(self, policy_manager):
        """Test policy restore with invalid backup data."""
        # Invalid backup data (missing required keys)
        invalid_backup = {
            "timestamp": "2024-01-01T00:00:00",
            "policies": [],
            # Missing grouping_policies
        }

        with pytest.raises(PolicyEvaluationException) as exc_info:
            await policy_manager.restore_policies(invalid_backup)

        assert "Invalid backup data structure" in str(exc_info.value)
        assert "required_keys" in exc_info.value.policy_context


class TestPrivilegeManagement(TestPolicyManager):
    """Test privilege object creation and management."""

    @pytest.mark.asyncio
    async def test_assign_role_to_user_success(self, policy_manager, user):
        """Test successful role assignment to user."""
        # Mock database query to return user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        policy_manager.db.execute = AsyncMock(return_value=mock_result)
        policy_manager.commit = AsyncMock()

        # Mock enforcer methods
        policy_manager.enforcer.remove_grouping_policy = MagicMock()
        policy_manager.enforcer.add_grouping_policy.return_value = True
        policy_manager._log_policy_change = AsyncMock()

        result = await policy_manager.assign_role_to_user(user_email=user.email, role=Role.SALESMAN)

        assert result is True

        # Verify enforcer calls
        policy_manager.enforcer.remove_grouping_policy.assert_called_once_with(user.email)
        policy_manager.enforcer.add_grouping_policy.assert_called_once_with(
            user.email, Role.SALESMAN.value
        )

        # Verify database update
        assert user.role == Role.SALESMAN.value
        policy_manager.commit.assert_called_once()

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once_with(
            action_type="assign_role",
            policy_data={"user_email": user.email, "role": Role.SALESMAN.value},
        )

    @pytest.mark.asyncio
    async def test_validate_policies_success(self, policy_manager):
        """Test policy validation with valid policies."""
        # Mock enforcer to return valid policies
        mock_policies = [
            ["salesman", "configuration", "read", "allow"],
            ["customer", "quote", "read", "allow"],
        ]
        mock_groupings = [["user@example.com", "salesman"], ["customer@example.com", "customer"]]

        policy_manager.enforcer.get_policy.return_value = mock_policies
        policy_manager.enforcer.get_grouping_policy.return_value = mock_groupings

        result = await policy_manager.validate_policies()

        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["statistics"]["total_policies"] == 2
        assert result["statistics"]["total_groupings"] == 2

    @pytest.mark.asyncio
    async def test_validate_policies_with_conflicts(self, policy_manager):
        """Test policy validation with conflicting policies."""
        # Mock enforcer to return conflicting policies
        mock_policies = [
            ["salesman", "configuration", "read", "allow"],
            ["salesman", "configuration", "read", "deny"],  # Conflict!
        ]
        mock_groupings = []

        policy_manager.enforcer.get_policy.return_value = mock_policies
        policy_manager.enforcer.get_grouping_policy.return_value = mock_groupings

        result = await policy_manager.validate_policies()

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "conflicting_policy"
        assert "salesman:configuration:read" in result["issues"][0]["description"]

    @pytest.mark.asyncio
    async def test_get_policy_summary(self, policy_manager):
        """Test getting policy summary."""
        # Mock enforcer to return policies and groupings
        mock_policies = [
            ["salesman", "configuration", "read", "allow"],
            ["salesman", "quote", "create", "allow"],
            ["customer", "quote", "read", "allow"],
        ]
        mock_groupings = [
            ["user1@example.com", "salesman"],
            ["user2@example.com", "customer"],
            ["user1@example.com", "customer", "123"],
        ]

        policy_manager.enforcer.get_policy.return_value = mock_policies
        policy_manager.enforcer.get_grouping_policy.return_value = mock_groupings

        result = await policy_manager.get_policy_summary()

        # Verify policies by role
        assert "salesman" in result["policies_by_role"]
        assert len(result["policies_by_role"]["salesman"]) == 2
        assert "customer" in result["policies_by_role"]
        assert len(result["policies_by_role"]["customer"]) == 1

        # Verify role assignments
        assert "user1@example.com" in result["role_assignments"]
        assert "salesman" in result["role_assignments"]["user1@example.com"]

        # Verify customer assignments
        assert "user1@example.com" in result["customer_assignments"]
        assert 123 in result["customer_assignments"]["user1@example.com"]

        # Verify statistics
        assert result["statistics"]["total_policies"] == 3
        assert result["statistics"]["total_role_assignments"] == 2
        assert result["statistics"]["total_customer_assignments"] == 1

    @pytest.mark.asyncio
    async def test_seed_initial_policies(self, policy_manager):
        """Test seeding initial policies."""
        # Mock enforcer methods
        policy_manager.enforcer.clear_policy = MagicMock()
        policy_manager.enforcer.add_policy = MagicMock()
        policy_manager.enforcer.save_policy = MagicMock()
        policy_manager._log_policy_change = AsyncMock()

        await policy_manager.seed_initial_policies()

        # Verify enforcer calls
        policy_manager.enforcer.clear_policy.assert_called_once()
        assert (
            policy_manager.enforcer.add_policy.call_count == 8
        )  # Expected number of initial policies
        policy_manager.enforcer.save_policy.assert_called_once()

        # Verify audit logging
        policy_manager._log_policy_change.assert_called_once()
        call_args = policy_manager._log_policy_change.call_args[1]
        assert call_args["action_type"] == "seed_initial_policies"
        assert call_args["policy_data"]["policies_created"] == 8


class TestPolicyManagerErrorHandling(TestPolicyManager):
    """Test error handling in PolicyManager."""

    @pytest.mark.asyncio
    async def test_backup_policies_failure(self, policy_manager):
        """Test policy backup failure handling."""
        # Mock enforcer to raise exception
        policy_manager.enforcer.get_policy.side_effect = Exception("Casbin error")

        with pytest.raises(PolicyEvaluationException) as exc_info:
            await policy_manager.backup_policies()

        assert "Failed to create policy backup" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_policies_failure(self, policy_manager):
        """Test policy validation failure handling."""
        # Mock enforcer to raise exception
        policy_manager.enforcer.get_policy.side_effect = Exception("Casbin error")

        with pytest.raises(PolicyEvaluationException) as exc_info:
            await policy_manager.validate_policies()

        assert "Failed to validate policies" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_policy_summary_failure(self, policy_manager):
        """Test policy summary failure handling."""
        # Mock enforcer to raise exception
        policy_manager.enforcer.get_policy.side_effect = Exception("Casbin error")

        with pytest.raises(PolicyEvaluationException) as exc_info:
            await policy_manager.get_policy_summary()

        assert "Failed to get policy summary" in str(exc_info.value)
