"""Integration tests for data export endpoints.

This module tests the data export API endpoints including:
- Export my data (GDPR compliance)
- Export all users as JSON (superuser only)
- Export all users as CSV (superuser only)

Features:
    - Full stack testing
    - Permission testing
    - File format testing
    - GDPR compliance testing
"""

import csv
import io

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestExportMyDataEndpoint:
    """Tests for GET /api/v1/export/my-data endpoint."""

    async def test_export_my_data_success(
        self,
        client: AsyncClient,
        test_user,
        test_user_data: dict,
        auth_headers: dict,
    ):
        """Test exporting own data."""
        response = await client.get(
            "/api/v1/export/my-data",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "hashed_password" not in data  # Should not expose password

    async def test_export_my_data_without_auth(self, client: AsyncClient):
        """Test exporting data without authentication fails."""
        response = await client.get("/api/v1/export/my-data")

        assert response.status_code == 401


class TestExportUsersJsonEndpoint:
    """Tests for GET /api/v1/export/users/json endpoint."""

    async def test_export_users_json_as_superuser(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test exporting all users as JSON (superuser)."""
        response = await client.get(
            "/api/v1/export/users/json",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "exported_at" in data
        assert "total_users" in data
        assert "users" in data
        assert isinstance(data["users"], list)
        assert data["total_users"] >= 2  # At least test_user and test_superuser

        # Verify user data structure
        user_data = data["users"][0]
        assert "id" in user_data
        assert "email" in user_data
        assert "username" in user_data
        assert "is_active" in user_data
        assert "created_at" in user_data

    async def test_export_users_json_as_regular_user(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test exporting all users as regular user fails."""
        response = await client.get(
            "/api/v1/export/users/json",
            headers=auth_headers,
        )

        assert response.status_code == 403

    async def test_export_users_json_without_auth(self, client: AsyncClient):
        """Test exporting users without authentication fails."""
        response = await client.get("/api/v1/export/users/json")

        assert response.status_code == 401


class TestExportUsersCsvEndpoint:
    """Tests for GET /api/v1/export/users/csv endpoint."""

    async def test_export_users_csv_as_superuser(
        self,
        client: AsyncClient,
        test_user,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test exporting all users as CSV (superuser)."""
        response = await client.get(
            "/api/v1/export/users/csv",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "users_export_" in response.headers["content-disposition"]

        # Parse CSV content
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) >= 2  # At least test_user and test_superuser

        # Verify CSV structure
        first_row = rows[0]
        assert "id" in first_row
        assert "email" in first_row
        assert "username" in first_row
        assert "is_active" in first_row
        assert "created_at" in first_row

    async def test_export_users_csv_as_regular_user(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test exporting users CSV as regular user fails."""
        response = await client.get(
            "/api/v1/export/users/csv",
            headers=auth_headers,
        )

        assert response.status_code == 403

    async def test_export_users_csv_without_auth(self, client: AsyncClient):
        """Test exporting users CSV without authentication fails."""
        response = await client.get("/api/v1/export/users/csv")

        assert response.status_code == 401


class TestExportPermissions:
    """Tests for export permission scenarios."""

    async def test_regular_user_can_export_own_data(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test regular user can export their own data."""
        response = await client.get(
            "/api/v1/export/my-data",
            headers=auth_headers,
        )

        assert response.status_code == 200

    async def test_regular_user_cannot_export_all_users(
        self,
        client: AsyncClient,
        test_user,
        auth_headers: dict,
    ):
        """Test regular user cannot export all users data."""
        # Cannot export JSON
        response = await client.get(
            "/api/v1/export/users/json",
            headers=auth_headers,
        )
        assert response.status_code == 403

        # Cannot export CSV
        response = await client.get(
            "/api/v1/export/users/csv",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_superuser_can_export_all_formats(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test superuser can export in all formats."""
        # Can export own data
        response = await client.get(
            "/api/v1/export/my-data",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        # Can export all users JSON
        response = await client.get(
            "/api/v1/export/users/json",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        # Can export all users CSV
        response = await client.get(
            "/api/v1/export/users/csv",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200


class TestExportDataFormats:
    """Tests for export data format validation."""

    async def test_json_export_format(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test JSON export has correct format."""
        response = await client.get(
            "/api/v1/export/users/json",
            headers=superuser_auth_headers,
        )

        data = response.json()

        # Verify top-level structure
        assert isinstance(data["exported_at"], str)
        assert isinstance(data["total_users"], int)
        assert isinstance(data["users"], list)

        # Verify user data structure
        if data["users"]:
            user = data["users"][0]
            assert isinstance(user["id"], int)
            assert isinstance(user["email"], str)
            assert isinstance(user["username"], str)
            assert isinstance(user["is_active"], bool)

    async def test_csv_export_format(
        self,
        client: AsyncClient,
        test_superuser,
        superuser_auth_headers: dict,
    ):
        """Test CSV export has correct format."""
        response = await client.get(
            "/api/v1/export/users/csv",
            headers=superuser_auth_headers,
        )

        # Verify CSV can be parsed
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        # Verify headers
        assert csv_reader.fieldnames == [
            "id",
            "email",
            "username",
            "full_name",
            "is_active",
            "is_superuser",
            "created_at",
            "updated_at",
        ]

        # Verify data types (as strings in CSV)
        if rows:
            row = rows[0]
            assert row["id"].isdigit()
            assert "@" in row["email"]
            assert row["is_active"] in ["True", "False"]
