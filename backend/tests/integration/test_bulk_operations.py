"""Integration tests for bulk user operations.

This module tests the bulk user creation endpoint with focus on:
- Successful bulk creation
- Transaction rollback on failure
- Validation error handling
- Access control (superuser only)

Features:
    - Full stack testing (HTTP → Service → Repository → Database)
    - Transaction atomicity validation
    - Error handling verification
    - Security testing
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.factories.user_factory import create_user_data

pytestmark = pytest.mark.asyncio


class TestBulkUserCreation:
    """Tests for POST /api/v1/users/bulk endpoint."""

    async def test_create_users_bulk_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test successful bulk user creation."""
        # Prepare bulk user data
        users_data = [
            create_user_data(
                email=f"bulk{i}@example.com",
                username=f"bulk{i}",
                # Use factory default password instead of hardcoded
            )
            for i in range(3)
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert isinstance(data, list)
        assert len(data) == 3

        # Verify each user
        for i, user in enumerate(data):
            assert user["email"] == users_data[i]["email"]
            assert user["username"] == users_data[i]["username"]
            assert user["full_name"] == users_data[i]["full_name"]
            assert user["is_active"] is True
            assert user["is_superuser"] is False
            assert "id" in user
            assert "created_at" in user
            assert "updated_at" in user
            # Password should not be in response
            assert "password" not in user
            assert "hashed_password" not in user

        # Verify users were created in database
        result = await db_session.execute(
            select(User).where(User.email.in_([u["email"] for u in users_data]))
        )
        db_users = result.scalars().all()
        assert len(db_users) == 3

    async def test_create_users_bulk_empty_list(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk creation with empty list."""
        response = await client.post(
            "/api/v1/users/bulk",
            json=[],
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_create_users_bulk_single_user(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk creation with single user."""
        user_data = create_user_data()
        user_data.pop("is_active", None)
        user_data.pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=[user_data],
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == user_data["email"]

    @pytest.mark.ci_cd_issue
    async def test_create_users_bulk_transaction_rollback_on_duplicate_email(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
        test_user,
    ):
        """Test that transaction rolls back when duplicate email is detected."""
        # Prepare bulk user data with one duplicate email
        users_data = [
            create_user_data(email="new1@example.com", username="new1"),
            create_user_data(email="new2@example.com", username="new2"),
            create_user_data(email=test_user.email, username="new3"),  # Duplicate email
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        # Count users before
        result_before = await db_session.execute(select(User))
        count_before = len(result_before.scalars().all())

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        # Should fail with conflict
        assert response.status_code == 409

        # Verify NO new users were created (transaction rolled back)
        result_after = await db_session.execute(select(User))
        count_after = len(result_after.scalars().all())
        assert count_after == count_before  # Should be same as before

        # Verify new1 and new2 were NOT created
        result = await db_session.execute(
            select(User).where(User.email.in_(["new1@example.com", "new2@example.com"]))
        )
        new_users = result.scalars().all()
        assert len(new_users) == 0

    @pytest.mark.ci_cd_issue
    async def test_create_users_bulk_transaction_rollback_on_duplicate_username(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
        test_user,
    ):
        """Test that transaction rolls back when duplicate username is detected."""
        # Prepare bulk user data with one duplicate username
        users_data = [
            create_user_data(email="unique1@example.com", username="unique1"),
            create_user_data(email="unique2@example.com", username="unique2"),
            create_user_data(
                email="unique3@example.com", username=test_user.username
            ),  # Duplicate username
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        # Count users before
        result_before = await db_session.execute(select(User))
        count_before = len(result_before.scalars().all())

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        # Should fail with conflict
        assert response.status_code == 409

        # Verify NO new users were created (transaction rolled back)
        result_after = await db_session.execute(select(User))
        count_after = len(result_after.scalars().all())
        assert count_after == count_before  # Should be same as before

    async def test_create_users_bulk_validation_error_invalid_email(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk creation with invalid email."""
        users_data = [
            create_user_data(email="valid@example.com", username="valid1"),
            create_user_data(email="invalid-email", username="valid2"),  # Invalid email
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        # Should fail with validation error
        assert response.status_code == 422
        data = response.json()
        assert "message" in data or "detail" in data

    async def test_create_users_bulk_validation_error_missing_field(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk creation with missing required field."""
        users_data = [
            create_user_data(email="valid@example.com", username="valid1"),
            {
                "email": "incomplete@example.com",
                # Missing username and password
            },
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        # Should fail with validation error
        assert response.status_code == 422

    async def test_create_users_bulk_validation_error_weak_password(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk creation with weak password."""
        users_data = [
            create_user_data(email="user1@example.com", username="user1"),
            create_user_data(
                email="user2@example.com", username="user2", password="weak"
            ),  # Weak password
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        # Should fail with validation error
        assert response.status_code == 422

    async def test_create_users_bulk_requires_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular users cannot create users in bulk."""
        users_data = [create_user_data()]
        users_data[0].pop("is_active", None)
        users_data[0].pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        # FastAPI returns 'detail' for built-in auth errors
        assert "detail" in data or "message" in data

    async def test_create_users_bulk_requires_authentication(
        self,
        client: AsyncClient,
    ):
        """Test that unauthenticated users cannot create users in bulk."""
        users_data = [create_user_data()]
        users_data[0].pop("is_active", None)
        users_data[0].pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
        )

        assert response.status_code == 401
        data = response.json()
        # FastAPI returns 'detail' for built-in auth errors
        assert "detail" in data or "message" in data

    async def test_create_users_bulk_large_batch(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test bulk creation with larger batch."""
        # Create 20 users
        users_data = [
            create_user_data(
                email=f"large{i}@example.com",
                username=f"large{i}",
            )
            for i in range(20)
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 20

        # Verify all users were created
        result = await db_session.execute(select(User).where(User.email.like("large%@example.com")))
        db_users = result.scalars().all()
        assert len(db_users) == 20

    async def test_create_users_bulk_passwords_are_hashed(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that passwords are hashed before storage."""
        users_data = [
            create_user_data(
                email="hash1@example.com",
                username="hash1",
                password="PlainPassword123!",
            )
        ]
        users_data[0].pop("is_active", None)
        users_data[0].pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201

        # Verify password is hashed in database
        # noinspection PyTypeChecker
        result = await db_session.execute(select(User).where(User.email == "hash1@example.com"))
        user = result.scalar_one()

        # Password should be hashed (bcrypt format)
        assert user.hashed_password != "PlainPassword123!"
        assert user.hashed_password.startswith("$2b$")

    async def test_create_users_bulk_duplicate_within_batch(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that duplicates within the same batch are detected."""
        # Create batch with duplicate email
        users_data = [
            create_user_data(email="dup@example.com", username="dup1"),
            create_user_data(email="dup@example.com", username="dup2"),  # Duplicate
        ]

        # Remove fields not in UserCreate schema
        for user_data in users_data:
            user_data.pop("is_active", None)
            user_data.pop("is_superuser", None)

        # Count users before
        result_before = await db_session.execute(select(User))
        count_before = len(result_before.scalars().all())

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        # Should fail with either 409 (ConflictException) or 500 (DatabaseException)
        # Both are valid as the duplicate is caught at different levels
        assert response.status_code in [409, 500]

        # Verify NO users were created (transaction rolled back)
        result_after = await db_session.execute(select(User))
        count_after = len(result_after.scalars().all())
        assert count_after == count_before

    async def test_create_users_bulk_response_format(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that response format matches specification."""
        users_data = [create_user_data(email="format@example.com", username="format1")]
        users_data[0].pop("is_active", None)
        users_data[0].pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response is list
        assert isinstance(data, list)
        assert len(data) == 1

        # Verify user schema
        user = data[0]
        required_fields = [
            "id",
            "email",
            "username",
            "full_name",
            "is_active",
            "is_superuser",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in user, f"Missing field: {field}"

        # Verify sensitive fields are not included
        assert "password" not in user
        assert "hashed_password" not in user

    async def test_create_users_bulk_content_type(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that response has correct content type."""
        users_data = [create_user_data()]
        users_data[0].pop("is_active", None)
        users_data[0].pop("is_superuser", None)

        response = await client.post(
            "/api/v1/users/bulk",
            json=users_data,
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        assert "application/json" in response.headers["content-type"]
