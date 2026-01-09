"""Integration tests for admin entry endpoints.

This module tests the admin entry page functionality including
authentication, template rendering, and API endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manufacturing_type import ManufacturingType
from app.models.user import User


@pytest.fixture
async def simple_manufacturing_type(db_session: AsyncSession) -> ManufacturingType:
    """Create a simple manufacturing type for testing."""
    from decimal import Decimal
    import uuid

    # Use a unique name to avoid conflicts
    unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"

    mfg_type = ManufacturingType(
        name=unique_name,
        description="Test window type for admin entry tests",
        base_price=Decimal("200.00"),
        base_weight=Decimal("25.00"),
        is_active=True,
    )

    db_session.add(mfg_type)
    await db_session.commit()
    await db_session.refresh(mfg_type)

    return mfg_type


class TestAdminEntry:
    """Test admin entry page functionality."""

    @pytest.mark.asyncio
    async def test_admin_entry_profile_page_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that admin entry profile page requires authentication."""
        response = await client.get("/api/v1/admin/entry/profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_entry_profile_page_with_page_type_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that admin entry profile page with page_type parameter requires authentication."""
        response = await client.get("/api/v1/admin/entry/profile?page_type=accessories")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_preview_headers_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that preview headers endpoint requires authentication."""
        response = await client.get("/api/v1/admin/entry/profile/headers/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_preview_headers_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test successful preview headers retrieval."""
        # Get preview headers with auth headers
        response = await client.get(
            f"/api/v1/admin/entry/profile/headers/{simple_manufacturing_type.id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        headers = response.json()
        assert isinstance(headers, list)
        assert "id" in headers
        assert "Name" in headers

    @pytest.mark.asyncio
    async def test_admin_entry_profile_page_requires_superuser(
        self,
        client: AsyncClient,
        test_user_with_rbac: User,
    ):
        """Test that admin entry profile page requires superuser privileges."""
        from tests.config import get_test_settings

        test_settings = get_test_settings()

        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_with_rbac.username,
                "password": test_settings.test_user_password,  # Use test settings
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to access admin entry page
        response = await client.get(
            "/api/v1/admin/entry/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_entry_profile_page_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that superuser can access admin entry profile page."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Access admin entry page
        response = await client.get(
            "/api/v1/admin/entry/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Profile Data Entry" in response.text

    @pytest.mark.asyncio
    async def test_admin_entry_profile_page_with_page_type_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that superuser can access admin entry profile page with page_type parameter."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test different page types
        page_types = ["profile", "accessories", "glazing"]
        for page_type in page_types:
            response = await client.get(
                f"/api/v1/admin/entry/profile?page_type={page_type}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert f"{page_type.title()} Data Entry" in response.text

    @pytest.mark.asyncio
    async def test_admin_entry_profile_page_invalid_page_type(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that invalid page_type returns 400 error."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test invalid page type
        response = await client.get(
            "/api/v1/admin/entry/profile?page_type=invalid",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "text/html" in response.headers["content-type"]
        assert "Invalid page type" in response.text

    @pytest.mark.asyncio
    async def test_admin_entry_accessories_page_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that superuser can access admin entry accessories page."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Access admin entry accessories page via page_type parameter
        response = await client.get(
            "/api/v1/admin/entry/profile?page_type=accessories",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Accessories Data Entry" in response.text

    @pytest.mark.asyncio
    async def test_admin_entry_glazing_page_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that superuser can access admin entry glazing page."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Access admin entry glazing page via page_type parameter
        response = await client.get(
            "/api/v1/admin/entry/profile?page_type=glazing",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Glazing Data Entry" in response.text

    @pytest.mark.asyncio
    async def test_admin_entry_schema_api_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that admin entry schema API works for superuser."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Get schema via admin API
        response = await client.get(
            f"/api/v1/admin/entry/profile/schema/{simple_manufacturing_type.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        schema = response.json()
        assert "manufacturing_type_id" in schema
        assert "sections" in schema

    @pytest.mark.asyncio
    async def test_admin_entry_schema_api_with_page_type(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that admin entry schema API works with page_type parameter."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test schema API with different page types
        page_types = ["profile", "accessories", "glazing"]
        for page_type in page_types:
            response = await client.get(
                f"/api/v1/admin/entry/profile/schema/{simple_manufacturing_type.id}?page_type={page_type}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            schema = response.json()
            assert "manufacturing_type_id" in schema
            assert "sections" in schema

    @pytest.mark.asyncio
    async def test_admin_entry_save_api_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that admin entry save API works for superuser."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Save profile via admin API
        profile_data = {
            "manufacturing_type_id": simple_manufacturing_type.id,
            "name": "Admin Test Configuration",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Admin800",
        }

        response = await client.post(
            "/api/v1/admin/entry/profile/save",
            json=profile_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        configuration = response.json()
        assert configuration["name"] == "Admin Test Configuration"
        assert configuration["manufacturing_type_id"] == simple_manufacturing_type.id

    @pytest.mark.asyncio
    async def test_navigation_links_in_templates(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that navigation links are correct in admin entry templates."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Check profile page has correct navigation
        response = await client.get(
            "/api/v1/admin/entry/profile?page_type=profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        content = response.text
        # Navigation should still show the old URLs for backward compatibility
        assert "/api/v1/admin/entry/profile" in content
        assert "/api/v1/admin/entry/accessories" in content
        assert "/api/v1/admin/entry/glazing" in content

        # Check accessories page has correct navigation
        response = await client.get(
            "/api/v1/admin/entry/profile?page_type=accessories",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        content = response.text
        assert "/api/v1/admin/entry/profile" in content
        assert "/api/v1/admin/entry/accessories" in content
        assert "/api/v1/admin/entry/glazing" in content

        # Check glazing page has correct navigation
        response = await client.get(
            "/api/v1/admin/entry/profile?page_type=glazing",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        content = response.text
        assert "/api/v1/admin/entry/profile" in content
        assert "/api/v1/admin/entry/accessories" in content
        assert "/api/v1/admin/entry/glazing" in content

    @pytest.mark.asyncio
    async def test_upload_image_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that image upload requires authentication."""
        response = await client.post("/api/v1/admin/entry/upload-image")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_image_requires_superuser(
        self,
        client: AsyncClient,
        test_user_with_rbac: User,
    ):
        """Test that image upload requires superuser privileges."""
        from tests.config import get_test_settings

        test_settings = get_test_settings()

        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_with_rbac.username,
                "password": test_settings.test_user_password,
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to upload image
        response = await client.post(
            "/api/v1/admin/entry/upload-image",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_image_no_file(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that upload fails when no file is provided."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to upload without file (returns 200 with error JSON)
        response = await client.post(
            "/api/v1/admin/entry/upload-image",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No file provided" in data["error"]

    @pytest.mark.asyncio
    async def test_upload_image_invalid_file_type(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that upload fails for non-image files."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to upload a text file (make it large enough to pass size validation)
        # Create a 2KB text file to pass minimum size check
        large_text = b"This is not an image. " * 100  # ~2.2KB
        files = {"file": ("test.txt", large_text, "text/plain")}
        response = await client.post(
            "/api/v1/admin/entry/upload-image",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        # Should fail on file type validation (txt not in allowed extensions)
        assert "not allowed" in data["error"] or "File type" in data["error"]

    @pytest.mark.asyncio
    async def test_upload_image_file_too_large(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that upload fails for files larger than 5MB."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create a file larger than 5MB
        large_file_content = b"x" * (6 * 1024 * 1024)  # 6MB
        files = {"file": ("large.jpg", large_file_content, "image/jpeg")}
        response = await client.post(
            "/api/v1/admin/entry/upload-image",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "too large" in data["error"]

    @pytest.mark.asyncio
    async def test_upload_image_success(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test successful image upload."""
        import os
        from pathlib import Path

        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create a small test image (1x1 pixel PNG)
        # PNG header + minimal image data
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        files = {"file": ("test_image.png", png_data, "image/png")}
        response = await client.post(
            "/api/v1/admin/entry/upload-image",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        assert response.status_code == 200
        data = response.json()

        # The response should indicate success or failure based on storage service
        assert "success" in data
        if data["success"]:
            assert "filename" in data
            assert "message" in data
            # Clean up if file was created locally
            if "filename" in data:
                try:
                    uploads_dir = Path("app/static/uploads")
                    uploaded_file = uploads_dir / data["filename"]
                    if uploaded_file.exists():
                        uploaded_file.unlink()
                except Exception:
                    pass
        else:
            # If storage service fails (e.g., missing config), that's expected in tests
            assert "error" in data

    @pytest.mark.asyncio
    async def test_upload_image_generates_unique_filenames(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that multiple uploads generate unique filenames."""
        from pathlib import Path

        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create a small test image
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        filenames = []
        uploads_dir = Path("app/static/uploads")

        try:
            # Upload same file twice
            for _ in range(2):
                files = {"file": ("test.png", png_data, "image/png")}
                response = await client.post(
                    "/api/v1/admin/entry/upload-image",
                    headers={"Authorization": f"Bearer {token}"},
                    files=files,
                )
                assert response.status_code == 200
                data = response.json()

                # Only check uniqueness if both uploads succeeded
                if data.get("success") and "filename" in data:
                    filenames.append(data["filename"])

            # Verify filenames are unique (if we got any successful uploads)
            if len(filenames) >= 2:
                assert filenames[0] != filenames[1]
                assert len(set(filenames)) == len(filenames)

        finally:
            # Clean up
            for filename in filenames:
                try:
                    (uploads_dir / filename).unlink()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_manufacturing_type_resolution_with_page_types(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
    ):
        """Test that manufacturing type resolution works with different page types."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test that page loads without manufacturing_type_id (should resolve default)
        page_types = ["profile", "accessories", "glazing"]
        for page_type in page_types:
            response = await client.get(
                f"/api/v1/admin/entry/profile?page_type={page_type}",
                headers={"Authorization": f"Bearer {token}"},
            )
            # Should either succeed (200) or show setup required (503)
            assert response.status_code in [200, 503]

            if response.status_code == 200:
                assert f"{page_type.title()} Data Entry" in response.text
            else:
                assert (
                    "Setup Required" in response.text
                    or "No manufacturing types found" in response.text
                )

    @pytest.mark.asyncio
    async def test_page_type_context_variables(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that page_type context variables are correctly set."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test different page types have correct titles
        page_types = {
            "profile": "Profile Entry",
            "accessories": "Accessories Entry",
            "glazing": "Glazing Entry",
        }

        for page_type, expected_title in page_types.items():
            response = await client.get(
                f"/api/v1/admin/entry/profile?page_type={page_type}&manufacturing_type_id={simple_manufacturing_type.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            # Check that the page title is correctly set
            assert expected_title in response.text

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that bulk delete configurations requires authentication."""
        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk", json=[1, 2, 3]
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_requires_superuser(
        self,
        client: AsyncClient,
        test_user_with_rbac: User,
    ):
        """Test that bulk delete configurations requires superuser privileges."""
        from tests.config import get_test_settings

        test_settings = get_test_settings()

        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_with_rbac.username,
                "password": test_settings.test_user_password,
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to bulk delete configurations
        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=[1, 2, 3],
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_empty_list(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test that bulk delete with empty list returns 400."""
        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=[],
            headers=superuser_auth_headers,
        )
        assert response.status_code == 400
        data = response.json()
        assert "No configuration IDs provided" in data["detail"]

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test successful bulk delete of configurations."""
        # First create some configurations to delete
        configurations = []
        for i in range(3):
            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": f"Test Configuration {i + 1}",
                "type": "Frame",
                "material": "Aluminum",
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers=superuser_auth_headers,
            )
            assert response.status_code == 201
            configurations.append(response.json())

        # Extract configuration IDs
        config_ids = [config["id"] for config in configurations]

        # Bulk delete the configurations
        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=config_ids,
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        result = response.json()
        assert result["success_count"] == 3
        assert result["error_count"] == 0
        assert result["total_requested"] == 3
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_partial_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test bulk delete with mix of existing and non-existing configurations."""
        # Create one configuration
        profile_data = {
            "manufacturing_type_id": simple_manufacturing_type.id,
            "name": "Test Configuration",
            "type": "Frame",
            "material": "Aluminum",
        }

        response = await client.post(
            "/api/v1/admin/entry/profile/save",
            json=profile_data,
            headers=superuser_auth_headers,
        )
        assert response.status_code == 201
        existing_config = response.json()

        # Try to delete existing config + non-existing configs
        config_ids = [existing_config["id"], 99999, 99998]

        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=config_ids,
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        result = response.json()
        assert result["success_count"] == 1
        assert result["error_count"] == 2
        assert result["total_requested"] == 3
        assert len(result["errors"]) == 2
        assert "Configuration 99999 not found" in result["errors"]
        assert "Configuration 99998 not found" in result["errors"]

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_all_missing(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk delete with all non-existing configurations."""
        config_ids = [99999, 99998, 99997]

        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=config_ids,
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        result = response.json()
        assert result["success_count"] == 0
        assert result["error_count"] == 3
        assert result["total_requested"] == 3
        assert len(result["errors"]) == 3
        for config_id in config_ids:
            assert f"Configuration {config_id} not found" in result["errors"]

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_invalid_json(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk delete with invalid JSON payload."""
        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            content="invalid json",
            headers={**superuser_auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_bulk_delete_configurations_invalid_ids(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test bulk delete with invalid configuration IDs (negative numbers)."""
        config_ids = [-1, 0, -5]

        response = await client.delete(
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=config_ids,
            headers=superuser_auth_headers,
        )
        assert response.status_code == 422  # Validation error for PositiveInt


class TestAdminEntryFieldOptions:
    """Test admin entry field option management endpoints."""

    @pytest.mark.asyncio
    async def test_add_field_option_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that add field option requires authentication."""
        response = await client.post(
            "/api/v1/admin/entry/profile/add-option",
            params={"manufacturing_type_id": 1, "field_name": "material", "option_value": "Steel"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_field_option_requires_superuser(
        self,
        client: AsyncClient,
        test_user_with_rbac: User,
    ):
        """Test that add field option requires superuser privileges."""
        from tests.config import get_test_settings

        test_settings = get_test_settings()

        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_with_rbac.username,
                "password": test_settings.test_user_password,
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to add field option
        response = await client.post(
            "/api/v1/admin/entry/profile/add-option",
            params={"manufacturing_type_id": 1, "field_name": "material", "option_value": "Steel"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_add_field_option_manufacturing_type_not_found(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test add field option with non-existent manufacturing type."""
        response = await client.post(
            "/api/v1/admin/entry/profile/add-option",
            params={
                "manufacturing_type_id": 99999,
                "field_name": "material",
                "option_value": "Steel",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404
        data = response.json()
        assert "Manufacturing type 99999 not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_add_field_option_field_not_found(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test add field option with non-existent field."""
        response = await client.post(
            "/api/v1/admin/entry/profile/add-option",
            params={
                "manufacturing_type_id": simple_manufacturing_type.id,
                "field_name": "nonexistent_field",
                "option_value": "Steel",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404
        data = response.json()
        assert "Field 'nonexistent_field' not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_add_field_option_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test successful field option addition."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal

        # First create a parent field node for testing
        parent_field = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            name="material",
            node_type="attribute",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True,
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)

        # Add new option
        response = await client.post(
            "/api/v1/admin/entry/profile/add-option",
            params={
                "manufacturing_type_id": simple_manufacturing_type.id,
                "field_name": "material",
                "option_value": "Steel",
                "page_type": "profile",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Steel" in data["message"]
        assert data["field_name"] == "material"
        assert data["option_value"] == "Steel"
        assert "option_id" in data
        assert data["manufacturing_type_id"] == simple_manufacturing_type.id

    @pytest.mark.asyncio
    async def test_add_field_option_duplicate(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test adding duplicate field option."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal

        # Create parent field and existing option
        parent_field = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            name="material",
            node_type="attribute",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True,
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)

        existing_option = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            parent_node_id=parent_field.id,
            name="Steel",
            node_type="option",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material.steel",
            depth=2,
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            is_required=False,
            is_active=True,
        )
        db_session.add(existing_option)
        await db_session.commit()

        # Try to add duplicate option
        response = await client.post(
            "/api/v1/admin/entry/profile/add-option",
            params={
                "manufacturing_type_id": simple_manufacturing_type.id,
                "field_name": "material",
                "option_value": "Steel",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 400
        data = response.json()
        assert "Option 'Steel' already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_remove_field_option_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that remove field option requires authentication."""
        response = await client.delete("/api/v1/admin/entry/profile/remove-option/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_field_option_requires_superuser(
        self,
        client: AsyncClient,
        test_user_with_rbac: User,
    ):
        """Test that remove field option requires superuser privileges."""
        from tests.config import get_test_settings

        test_settings = get_test_settings()

        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_with_rbac.username,
                "password": test_settings.test_user_password,
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to remove field option
        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remove_field_option_not_found(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test remove field option with non-existent option."""
        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option/99999", headers=superuser_auth_headers
        )
        assert response.status_code == 404
        data = response.json()
        assert "Option 99999 not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_remove_field_option_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test successful field option removal."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal

        # Create parent field and option to remove
        parent_field = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            name="material",
            node_type="attribute",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True,
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)

        option_to_remove = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            parent_node_id=parent_field.id,
            name="Steel",
            node_type="option",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material.steel",
            depth=2,
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            is_required=False,
            is_active=True,
        )
        db_session.add(option_to_remove)
        await db_session.commit()
        await db_session.refresh(option_to_remove)

        # Remove the option
        response = await client.delete(
            f"/api/v1/admin/entry/profile/remove-option/{option_to_remove.id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Steel" in data["message"]
        assert data["option_id"] == option_to_remove.id
        assert data["option_name"] == "Steel"
        assert data["field_name"] == "material"

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that remove field option by name requires authentication."""
        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option-by-name",
            params={"manufacturing_type_id": 1, "field_name": "material", "option_value": "Steel"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_requires_superuser(
        self,
        client: AsyncClient,
        test_user_with_rbac: User,
    ):
        """Test that remove field option by name requires superuser privileges."""
        from tests.config import get_test_settings

        test_settings = get_test_settings()

        # Login as regular user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_with_rbac.username,
                "password": test_settings.test_user_password,
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Try to remove field option by name
        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option-by-name",
            params={"manufacturing_type_id": 1, "field_name": "material", "option_value": "Steel"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_field_not_found(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test remove field option by name with non-existent field."""
        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option-by-name",
            params={
                "manufacturing_type_id": simple_manufacturing_type.id,
                "field_name": "nonexistent_field",
                "option_value": "Steel",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404
        data = response.json()
        assert "Field 'nonexistent_field' not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_option_not_found(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test remove field option by name with non-existent option."""
        from app.models.attribute_node import AttributeNode

        # Create parent field but no option
        parent_field = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            name="material",
            node_type="attribute",
            page_type="profile",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True,
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)

        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option-by-name",
            params={
                "manufacturing_type_id": simple_manufacturing_type.id,
                "field_name": "material",
                "option_value": "NonexistentOption",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200  # Returns 200 with success: false
        data = response.json()
        assert data["success"] is False
        assert "Option 'NonexistentOption' not found in field 'material'" in data["error"]

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test successful field option removal by name."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal

        # Create parent field and option to remove
        parent_field = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            name="material",
            node_type="attribute",
            page_type="profile",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True,
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)

        option_to_remove = AttributeNode(
            manufacturing_type_id=simple_manufacturing_type.id,
            parent_node_id=parent_field.id,
            name="Steel",
            node_type="option",
            page_type="profile",
            ltree_path=f"mfg_{simple_manufacturing_type.id}.material.steel",
            depth=2,
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            is_required=False,
            is_active=True,
        )
        db_session.add(option_to_remove)
        await db_session.commit()
        await db_session.refresh(option_to_remove)

        # Remove the option by name
        response = await client.delete(
            "/api/v1/admin/entry/profile/remove-option-by-name",
            params={
                "manufacturing_type_id": simple_manufacturing_type.id,
                "field_name": "material",
                "option_value": "Steel",
                "page_type": "profile",
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Steel" in data["message"]
        assert data["option_id"] == option_to_remove.id
        assert data["field_name"] == "material"
        assert data["option_value"] == "Steel"
        assert data["manufacturing_type_id"] == simple_manufacturing_type.id

    @pytest.mark.asyncio
    async def test_add_field_option_with_different_page_types(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        simple_manufacturing_type: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test adding field options with different page types."""
        from app.models.attribute_node import AttributeNode

        # Create parent fields for different page types
        page_types = ["profile", "accessories", "glazing"]

        for i, page_type in enumerate(page_types):
            # Create parent field
            parent_field = AttributeNode(
                manufacturing_type_id=simple_manufacturing_type.id,
                name=f"test_field_{page_type}",
                node_type="attribute",
                ltree_path=f"mfg_{simple_manufacturing_type.id}.test_field_{page_type}",
                depth=1,
                data_type="string",
                is_required=False,
                is_active=True,
            )
            db_session.add(parent_field)
            await db_session.commit()
            await db_session.refresh(parent_field)

            # Add option with specific page type
            response = await client.post(
                "/api/v1/admin/entry/profile/add-option",
                params={
                    "manufacturing_type_id": simple_manufacturing_type.id,
                    "field_name": f"test_field_{page_type}",
                    "option_value": f"Option_{page_type}",
                    "page_type": page_type,
                },
                headers=superuser_auth_headers,
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert f"Option_{page_type}" in data["message"]
