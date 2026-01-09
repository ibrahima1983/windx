"""Integration tests for admin template management endpoints.

Tests the admin template management interface including:
- Template dashboard rendering
- Template creation form
- Template saving functionality
- Template editing form
- Authentication and authorization
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration_template import ConfigurationTemplate
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User


@pytest.mark.asyncio
class TestAdminTemplateDashboard:
    """Tests for GET /api/v1/admin/templates/ endpoint."""

    async def test_template_dashboard_renders_for_superuser(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that template dashboard renders successfully for authenticated superuser."""
        response = await client.get(
            "/api/v1/admin/templates/",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"template" in response.content.lower()

    async def test_template_dashboard_redirects_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test template dashboard redirects unauthenticated users to login."""
        response = await client.get(
            "/api/v1/admin/templates/",
            follow_redirects=False,
        )

        # Should redirect to login
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_template_dashboard_redirects_non_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test template dashboard redirects non-superuser to login."""
        response = await client.get(
            "/api/v1/admin/templates/",
            headers=auth_headers,
            follow_redirects=False,
        )

        # Should redirect to login (non-superuser not allowed)
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_template_dashboard_shows_existing_templates(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """Test template dashboard displays existing templates."""
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window Type",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a template
        template = ConfigurationTemplate(
            name="Test Template",
            description="A test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/templates/",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        # Template name should appear in the response
        assert b"Test Template" in response.content

    async def test_template_dashboard_handles_database_error(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        monkeypatch,
    ):
        """Test template dashboard handles database errors gracefully."""
        from app.repositories.configuration_template import ConfigurationTemplateRepository

        # Mock the get_all method to raise a database error
        async def mock_get_all(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(ConfigurationTemplateRepository, "get_all", mock_get_all)

        response = await client.get(
            "/api/v1/admin/templates/",
            headers=superuser_auth_headers,
            follow_redirects=False,
        )

        # Should redirect to dashboard with error message
        assert response.status_code == 302
        assert "/api/v1/admin/dashboard" in response.headers["location"]


@pytest.mark.asyncio
class TestAdminTemplateNewForm:
    """Tests for GET /api/v1/admin/templates/new endpoint."""

    async def test_new_template_form_renders_for_superuser(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
    ):
        """Test that new template form renders successfully for authenticated superuser."""
        response = await client.get(
            "/api/v1/admin/templates/new",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"form" in response.content.lower()

    async def test_new_template_form_redirects_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test new template form redirects unauthenticated users to login."""
        response = await client.get(
            "/api/v1/admin/templates/new",
            follow_redirects=False,
        )

        # Should redirect to login
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_new_template_form_redirects_non_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test new template form redirects non-superuser to login."""
        response = await client.get(
            "/api/v1/admin/templates/new",
            headers=auth_headers,
            follow_redirects=False,
        )

        # Should redirect to login (non-superuser not allowed)
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_new_template_form_shows_manufacturing_types(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """Test new template form displays manufacturing types for selection."""
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window Type",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/templates/new",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        # Manufacturing type should appear in the form
        assert b"Test Window Type" in response.content

    async def test_new_template_form_handles_database_error(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        monkeypatch,
    ):
        """Test new template form handles database errors gracefully."""
        from app.repositories.manufacturing_type import ManufacturingTypeRepository

        # Mock the get_all method to raise a database error
        async def mock_get_all(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(ManufacturingTypeRepository, "get_all", mock_get_all)

        response = await client.get(
            "/api/v1/admin/templates/new",
            headers=superuser_auth_headers,
            follow_redirects=False,
        )

        # Should redirect to templates list with error message
        assert response.status_code == 302
        assert "/api/v1/admin/templates" in response.headers["location"]


@pytest.mark.asyncio
class TestAdminTemplateSave:
    """Tests for POST /api/v1/admin/templates/save endpoint."""

    async def test_save_template_success(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """Test successful template creation."""
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window Type",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        response = await client.post(
            "/api/v1/admin/templates/save",
            headers=superuser_auth_headers,
            data={
                "name": "New Test Template",
                "description": "A new test template",
                "manufacturing_type_id": mfg_type.id,
                "template_type": "standard",
                "is_public": True,
                "is_active": True,
            },
            follow_redirects=False,
        )

        # Should redirect to templates list with success message
        assert response.status_code == 302
        assert "/api/v1/admin/templates" in response.headers["location"]

        # Verify template was created in database
        from sqlalchemy import select

        stmt = select(ConfigurationTemplate).where(
            ConfigurationTemplate.name == "New Test Template"
        )
        result = await db_session.execute(stmt)
        template = result.scalar_one_or_none()

        assert template is not None
        assert template.name == "New Test Template"
        assert template.description == "A new test template"
        assert template.manufacturing_type_id == mfg_type.id

    async def test_save_template_redirects_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test save template redirects unauthenticated users to login."""
        response = await client.post(
            "/api/v1/admin/templates/save",
            data={
                "name": "Test Template",
                "description": "Test",
                "manufacturing_type_id": 1,
                "template_type": "standard",
            },
            follow_redirects=False,
        )

        # Should redirect to login
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_save_template_redirects_non_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test save template redirects non-superuser to login."""
        response = await client.post(
            "/api/v1/admin/templates/save",
            headers=auth_headers,
            data={
                "name": "Test Template",
                "description": "Test",
                "manufacturing_type_id": 1,
                "template_type": "standard",
            },
            follow_redirects=False,
        )

        # Should redirect to login (non-superuser not allowed)
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_save_template_handles_validation_error(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
    ):
        """Test save template handles validation errors gracefully."""
        response = await client.post(
            "/api/v1/admin/templates/save",
            headers=superuser_auth_headers,
            data={
                "name": "",  # Empty name should cause validation error
                "description": "Test",
                "manufacturing_type_id": 999,  # Non-existent manufacturing type
                "template_type": "standard",
            },
            follow_redirects=False,
        )

        # Should redirect to new form with error message
        assert response.status_code == 302
        assert "/api/v1/admin/templates/new" in response.headers["location"]

    async def test_save_template_handles_database_error(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        monkeypatch,
    ):
        """Test save template handles database errors gracefully."""
        from app.services.template import TemplateService

        # Mock the create_template method to raise a database error
        async def mock_create_template(*args, **kwargs):
            raise Exception("Database constraint violation")

        monkeypatch.setattr(TemplateService, "create_template", mock_create_template)

        response = await client.post(
            "/api/v1/admin/templates/save",
            headers=superuser_auth_headers,
            data={
                "name": "Test Template",
                "description": "Test",
                "manufacturing_type_id": 1,
                "template_type": "standard",
            },
            follow_redirects=False,
        )

        # Should redirect to new form with error message
        assert response.status_code == 302
        assert "/api/v1/admin/templates/new" in response.headers["location"]


@pytest.mark.asyncio
class TestAdminTemplateEditForm:
    """Tests for GET /api/v1/admin/templates/{template_id}/edit endpoint."""

    async def test_edit_template_form_renders_for_superuser(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """Test that edit template form renders successfully for authenticated superuser."""
        # Create a manufacturing type and template
        mfg_type = ManufacturingType(
            name="Test Window Type",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        template = ConfigurationTemplate(
            name="Test Template",
            description="A test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        response = await client.get(
            f"/api/v1/admin/templates/{template.id}/edit",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"form" in response.content.lower()
        assert b"Test Template" in response.content

    async def test_edit_template_form_redirects_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test edit template form redirects unauthenticated users to login."""
        response = await client.get(
            "/api/v1/admin/templates/1/edit",
            follow_redirects=False,
        )

        # Should redirect to login
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_edit_template_form_redirects_non_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test edit template form redirects non-superuser to login."""
        response = await client.get(
            "/api/v1/admin/templates/1/edit",
            headers=auth_headers,
            follow_redirects=False,
        )

        # Should redirect to login (non-superuser not allowed)
        assert response.status_code == 302
        assert "/api/v1/admin/login" in response.headers["location"]

    async def test_edit_template_form_handles_not_found(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
    ):
        """Test edit template form handles template not found."""
        response = await client.get(
            "/api/v1/admin/templates/999/edit",
            headers=superuser_auth_headers,
            follow_redirects=False,
        )

        # Should redirect to templates list with error message
        assert response.status_code == 302
        assert "/api/v1/admin/templates" in response.headers["location"]

    async def test_edit_template_form_handles_database_error(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict[str, str],
        monkeypatch,
    ):
        """Test edit template form handles database errors gracefully."""
        from app.repositories.configuration_template import ConfigurationTemplateRepository

        # Mock the get method to raise a database error
        async def mock_get(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(ConfigurationTemplateRepository, "get", mock_get)

        response = await client.get(
            "/api/v1/admin/templates/1/edit",
            headers=superuser_auth_headers,
            follow_redirects=False,
        )

        # Should redirect to templates list with error message
        assert response.status_code == 302
        assert "/api/v1/admin/templates" in response.headers["location"]


@pytest.mark.asyncio
class TestAdminTemplateAuthFlow:
    """Integration tests for complete admin template authentication flow."""

    async def test_complete_template_management_flow(
        self,
        client: AsyncClient,
        test_superuser: User,
        test_passwords: dict[str, str],
        db_session: AsyncSession,
    ):
        """Test complete flow: login -> view templates -> create template -> edit template."""
        # Step 1: Login
        login_response = await client.post(
            "/api/v1/admin/login",
            data={
                "username": test_superuser.username,
                "password": test_passwords["admin"],
            },
            follow_redirects=False,
        )

        assert login_response.status_code == 302
        assert "access_token" in login_response.cookies

        # Set cookie for subsequent requests
        cookie_value = login_response.cookies["access_token"]
        client.cookies.set("access_token", cookie_value)

        # Step 2: View template dashboard
        dashboard_response = await client.get("/api/v1/admin/templates/")
        assert dashboard_response.status_code == 200

        # Step 3: View new template form
        new_form_response = await client.get("/api/v1/admin/templates/new")
        assert new_form_response.status_code == 200

        # Step 4: Create a manufacturing type for the template
        mfg_type = ManufacturingType(
            name="Flow Test Window",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Step 5: Create template
        save_response = await client.post(
            "/api/v1/admin/templates/save",
            data={
                "name": "Flow Test Template",
                "description": "Created during flow test",
                "manufacturing_type_id": mfg_type.id,
                "template_type": "standard",
                "is_public": True,
                "is_active": True,
            },
            follow_redirects=False,
        )

        assert save_response.status_code == 302
        assert "/api/v1/admin/templates" in save_response.headers["location"]

        # Step 6: Find the created template
        from sqlalchemy import select

        stmt = select(ConfigurationTemplate).where(
            ConfigurationTemplate.name == "Flow Test Template"
        )
        result = await db_session.execute(stmt)
        template = result.scalar_one()

        # Step 7: Edit template form
        edit_form_response = await client.get(f"/api/v1/admin/templates/{template.id}/edit")
        assert edit_form_response.status_code == 200
        assert b"Flow Test Template" in edit_form_response.content

    async def test_unauthorized_access_redirects_consistently(
        self,
        client: AsyncClient,
    ):
        """Test that all template endpoints redirect unauthorized users consistently."""
        endpoints = [
            "/api/v1/admin/templates/",
            "/api/v1/admin/templates/new",
            "/api/v1/admin/templates/1/edit",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint, follow_redirects=False)
            assert response.status_code == 302
            assert "/api/v1/admin/login" in response.headers["location"]

        # Test POST endpoint
        post_response = await client.post(
            "/api/v1/admin/templates/save",
            data={"name": "test"},
            follow_redirects=False,
        )
        assert post_response.status_code == 302
        assert "/api/v1/admin/login" in post_response.headers["location"]
