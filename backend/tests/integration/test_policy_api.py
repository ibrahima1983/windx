"""Integration tests for policy management API endpoints.

This module tests the policy management API endpoints including:
- Policy addition and removal
- Customer assignment management
- Role assignment operations
- Policy backup and restore
- Policy validation and summary

Requirements: 6.1, 6.2, 6.3, 9.3
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from tests.factories.customer_factory import CustomerFactory

# Base URL for policy API endpoints
POLICY_BASE_URL = "/api/v1/admin/policies"


class TestPolicyAPI:
    """Test policy management API endpoints."""

    @pytest.fixture
    async def test_customer(self, db_session: AsyncSession) -> Customer:
        """Create test customer."""
        return await CustomerFactory.create(
            db_session, email="customer@test.com", company_name="Test Company"
        )

    @pytest.fixture
    def mock_policy_manager(self):
        """Mock PolicyManager for testing."""
        with patch("app.api.v1.policy.PolicyManager") as mock:
            manager_instance = MagicMock()
            mock.return_value = manager_instance
            yield manager_instance


class TestAddPolicy(TestPolicyAPI):
    """Test policy addition endpoint."""

    @pytest.mark.asyncio
    async def test_add_policy_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        mock_policy_manager: MagicMock,
    ):
        """Test successful policy addition."""
        # Arrange
        mock_policy_manager.add_policy = AsyncMock(return_value=True)

        policy_data = {
            "subject": "test_role",
            "resource": "configuration",
            "action": "read",
            "effect": "allow",
        }

        # Act
        response = await client.post(
            f"{POLICY_BASE_URL}/", json=policy_data, headers=superuser_auth_headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Policy added successfully"
        assert data["policy"]["subject"] == "test_role"
        assert data["policy"]["resource"] == "configuration"
        assert data["policy"]["action"] == "read"
        assert data["policy"]["effect"] == "allow"

        # Verify service was called correctly
        mock_policy_manager.add_policy.assert_called_once_with(
            subject="test_role", resource="configuration", action="read", effect="allow"
        )

    @pytest.mark.asyncio
    async def test_add_policy_already_exists(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        mock_policy_manager: MagicMock,
    ):
        """Test adding policy that already exists."""
        # Arrange
        mock_policy_manager.add_policy = AsyncMock(return_value=False)

        policy_data = {"subject": "existing_role", "resource": "configuration", "action": "read"}

        # Act
        response = await client.post(
            f"{POLICY_BASE_URL}/", json=policy_data, headers=superuser_auth_headers
        )

        # Assert
        assert response.status_code == 409
        data = response.json()
        assert "Policy already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_add_policy_unauthorized(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Test policy addition without superadmin privileges."""
        # Arrange
        policy_data = {"subject": "test_role", "resource": "configuration", "action": "read"}

        # Act
        response = await client.post(f"{POLICY_BASE_URL}/", json=policy_data, headers=auth_headers)

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_add_policy_validation_error(
        self, client: AsyncClient, superuser_auth_headers: dict[str, str]
    ):
        """Test policy addition with invalid data."""
        # Arrange - missing required fields
        policy_data = {
            "subject": "test_role"
            # Missing resource and action
        }

        # Act
        response = await client.post(
            f"{POLICY_BASE_URL}/", json=policy_data, headers=superuser_auth_headers
        )

        # Assert
        assert response.status_code == 422
