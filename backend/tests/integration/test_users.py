"""Integration tests for user management endpoints.

This module tests the user management API endpoints including:
- List users (superuser only)
- Get user by ID
- Update user
- Delete user (superuser only)

Features:
    - Full stack testing
    - Permission testing
    - Pagination testing
    - Error case testing
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestListUsersEndpoint:
    """Tests for GET /api/v1/users/ endpoint."""

    async def test_list_users_as_superuser(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test listing users as superuser."""
        response = await client.get(
            "/api/v1/users/",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert isinstance(data["items"], list)

    async def test_list_users_as_regular_user(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test listing users as regular user fails."""
        response = await client.get(
            "/api/v1/users/",
            headers=auth_headers,
        )

        assert response.status_code == 403

    async def test_list_users_without_auth(self, client: AsyncClient):
        """Test listing users without authentication fails."""
        response = await client.get("/api/v1/users/")

        assert response.status_code == 401

    async def test_list_users_pagination(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test pagination parameters."""
        response = await client.get(
            "/api/v1/users/?page=1&size=10",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10


class TestGetUserEndpoint:
    """Tests for GET /api/v1/users/{user_id} endpoint."""

    async def test_get_own_user(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
        auth_headers: dict,
    ):
        """Test getting own user profile."""
        response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_get_other_user_as_regular_user(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        auth_headers: dict,
    ):
        """Test getting other user as regular user fails."""
        response = await client.get(
            f"/api/v1/users/{test_superuser.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "authorization_error"

    async def test_get_other_user_as_superuser(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test getting other user as superuser succeeds."""
        response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    async def test_get_nonexistent_user(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test getting nonexistent user fails."""
        response = await client.get(
            "/api/v1/users/99999",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found_error"

    async def test_get_user_without_auth(self, client: AsyncClient, test_user):
        """Test getting user without authentication fails."""
        response = await client.get(f"/api/v1/users/{test_user.id}")

        assert response.status_code == 401


class TestUpdateUserEndpoint:
    """Tests for PATCH /api/v1/users/{user_id} endpoint."""

    async def test_update_own_user(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test updating own user profile."""
        update_data = {
            "full_name": "Updated Name",
        }

        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    async def test_update_own_email(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test updating own email."""
        update_data = {
            "email": "newemail@example.com",
        }

        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    async def test_update_email_to_existing(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        auth_headers: dict,
    ):
        """Test updating email to existing email fails."""
        update_data = {
            "email": test_superuser.email,
        }

        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "conflict_error"

    async def test_update_other_user_as_regular_user(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        auth_headers: dict,
    ):
        """Test updating other user as regular user fails."""
        update_data = {
            "full_name": "Hacked Name",
        }

        response = await client.patch(
            f"/api/v1/users/{test_superuser.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "authorization_error"

    async def test_update_other_user_as_superuser(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test updating other user as superuser succeeds."""
        update_data = {
            "full_name": "Admin Updated Name",
        }

        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Admin Updated Name"

    async def test_update_password(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
        auth_headers: dict,
        db_session,
    ):
        """Test updating password."""
        new_password = "NewPassword123!"
        update_data = {
            "password": new_password,
        }

        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Logout to clear the session
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )
        assert logout_response.status_code == 204

        # Clean up any remaining sessions to avoid conflicts
        from sqlalchemy import delete

        from app.models.session import Session

        # noinspection PyTypeChecker
        await db_session.execute(delete(Session).where(Session.user_id == test_user.id))
        await db_session.commit()

        # Verify can login with new password
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": new_password,
            },
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    async def test_update_user_without_auth(self, client: AsyncClient, test_user):
        """Test updating user without authentication fails."""
        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json={"full_name": "Hacked"},
        )

        assert response.status_code == 401


class TestDeleteUserEndpoint:
    """Tests for DELETE /api/v1/users/{user_id} endpoint."""

    async def test_delete_user_as_superuser(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test deleting user as superuser."""
        response = await client.delete(
            f"/api/v1/users/{test_user.id}",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 204

        # Verify user is deleted
        get_response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=superuser_auth_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_user_as_regular_user(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        auth_headers: dict,
    ):
        """Test deleting user as regular user fails."""
        response = await client.delete(
            f"/api/v1/users/{test_superuser.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_delete_nonexistent_user(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test deleting nonexistent user fails."""
        response = await client.delete(
            "/api/v1/users/99999",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_user_without_auth(self, client: AsyncClient, test_user):
        """Test deleting user without authentication fails."""
        response = await client.delete(f"/api/v1/users/{test_user.id}")

        assert response.status_code == 401


class TestUserPermissions:
    """Tests for user permission scenarios."""

    async def test_regular_user_cannot_see_other_users(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        auth_headers: dict,
    ):
        """Test regular user cannot access other user's data."""
        # Cannot get other user
        response = await client.get(
            f"/api/v1/users/{test_superuser.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

        # Cannot update other user
        response = await client.patch(
            f"/api/v1/users/{test_superuser.id}",
            json={"full_name": "Hacked"},
            headers=auth_headers,
        )
        assert response.status_code == 403

        # Cannot delete other user
        response = await client.delete(
            f"/api/v1/users/{test_superuser.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_superuser_can_manage_all_users(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test superuser can manage all users."""
        # Can get other user
        response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        # Can update other user
        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json={"full_name": "Admin Updated"},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        # Can list all users
        response = await client.get(
            "/api/v1/users/",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
