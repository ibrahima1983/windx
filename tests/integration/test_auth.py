"""Integration tests for authentication endpoints.

This module tests the authentication API endpoints including:
- User registration
- User login
- User logout
- Get current user info

Features:
    - Full stack testing (HTTP → Service → Repository → Database)
    - Async testing with httpx
    - Authentication flow testing
    - Error case testing
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.user_factory import create_user_data

pytestmark = pytest.mark.asyncio


class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register endpoint."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        user_data = create_user_data()

        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
    ):
        """Test registration with duplicate email fails."""
        user_data = create_user_data(email=test_user_data["email"])

        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "conflict_error"
        assert "email" in data["message"].lower()

    async def test_register_duplicate_username(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
    ):
        """Test registration with duplicate username fails."""
        user_data = create_user_data(username=test_user_data["username"])

        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "conflict_error"
        assert "username" in data["message"].lower()

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        user_data = create_user_data(email="invalid-email")

        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password fails."""
        user_data = create_user_data(password="short")

        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 422

    async def test_register_short_username(self, client: AsyncClient):
        """Test registration with short username fails."""
        user_data = create_user_data(username="ab")

        response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        assert response.status_code == 422


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login endpoint."""

    async def test_login_with_username_success(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
    ):
        """Test successful login with username."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    async def test_login_with_email_success(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
    ):
        """Test successful login with email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
    ):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "authentication_error"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "Password123!",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "authentication_error"

    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
        db_session: AsyncSession,
    ):
        """Test login with inactive user fails."""
        # Store original state
        original_is_active = test_user.is_active

        try:
            # Deactivate user
            test_user.is_active = False
            await db_session.commit()

            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user_data["username"],
                    "password": test_user_data["password"],
                },
            )

            assert response.status_code == 401
            data = response.json()
            assert data["error"] == "authentication_error"
            assert "inactive" in data["message"].lower()
        finally:
            # Restore original state
            test_user.is_active = original_is_active
            await db_session.commit()


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout endpoint."""

    async def test_logout_success(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test successful logout."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )

        assert response.status_code == 204

    async def test_logout_without_auth(self, client: AsyncClient):
        """Test logout without authentication fails."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestGetCurrentUserEndpoint:
    """Tests for GET /api/v1/auth/me endpoint."""

    async def test_get_current_user_success(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
        auth_headers: dict,
    ):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_get_current_user_without_auth(self, client: AsyncClient):
        """Test getting current user without authentication fails."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


class TestAuthenticationFlow:
    """Tests for complete authentication flow."""

    async def test_complete_auth_flow(self, client: AsyncClient):
        """Test complete authentication flow: register → login → get user → logout."""
        # 1. Register
        user_data = create_user_data()
        register_response = await client.post(
            "/api/v1/auth/register",
            json=user_data,
        )
        assert register_response.status_code == 201

        # 2. Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": user_data["username"],
                "password": user_data["password"],
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get current user
        me_response = await client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == user_data["email"]

        # 4. Logout
        logout_response = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 204

    async def test_token_reuse_after_logout(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
        db_session: AsyncSession,
    ):
        """Test that token cannot be reused after logout."""
        # Ensure user is active before login (fix test isolation issue)
        await db_session.refresh(test_user)
        if not test_user.is_active:
            test_user.is_active = True
            await db_session.commit()
            await db_session.refresh(test_user)

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        assert login_response.status_code == 200, f"Login failed: {login_response.json()}"
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Logout
        await client.post("/api/v1/auth/logout", headers=headers)

        # Try to use token after logout
        me_response = await client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 401
