"""Integration tests for Entry Page API endpoints.

This module contains integration tests that verify the entry page API endpoints
work correctly with the database and business logic.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User

pytestmark = pytest.mark.asyncio


class TestEntryAPIEndpoints:
    """Integration tests for Entry Page API endpoints."""

    @pytest.fixture
    async def test_customer(self, db_session: AsyncSession) -> Customer:
        """Create a test customer for configurations."""
        customer = Customer(
            company_name="Test Company",
            contact_person="Test User",
            email="test@example.com",
            phone="555-1234",
            customer_type="commercial",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)
        return customer

    @pytest.fixture
    async def manufacturing_type_with_attributes(
        self, db_session: AsyncSession
    ) -> ManufacturingType:
        """Create a manufacturing type with attribute hierarchy for testing."""
        import uuid

        unique_name = f"Test Window Profile {uuid.uuid4().hex[:8]}"

        # Create manufacturing type
        manufacturing_type = ManufacturingType(
            name=unique_name,
            description="Test window for profile entry",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        # Create attribute hierarchy
        # Basic Information category
        basic_info = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            name="Basic Information",
            node_type="category",
            ltree_path="basic_information",
            depth=0,
            sort_order=1,
        )
        db_session.add(basic_info)
        await db_session.commit()
        await db_session.refresh(basic_info)

        # Type attribute
        type_attr = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=basic_info.id,
            name="type",
            node_type="attribute",
            data_type="string",
            required=True,
            ui_component="dropdown",
            description="Profile Type",
            ltree_path="basic_information.type",
            depth=1,
            sort_order=1,
        )
        db_session.add(type_attr)

        # Material attribute
        material_attr = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=basic_info.id,
            name="material",
            node_type="attribute",
            data_type="string",
            required=True,
            ui_component="dropdown",
            description="Material Type",
            ltree_path="basic_information.material",
            depth=1,
            sort_order=2,
        )
        db_session.add(material_attr)

        # Opening system attribute
        opening_system_attr = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=basic_info.id,
            name="opening_system",
            node_type="attribute",
            data_type="string",
            required=True,
            ui_component="dropdown",
            description="Opening System",
            ltree_path="basic_information.opening_system",
            depth=1,
            sort_order=3,
        )
        db_session.add(opening_system_attr)

        # System series attribute
        system_series_attr = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=basic_info.id,
            name="system_series",
            node_type="attribute",
            data_type="string",
            required=True,
            ui_component="dropdown",
            description="System Series",
            ltree_path="basic_information.system_series",
            depth=1,
            sort_order=4,
        )
        db_session.add(system_series_attr)

        # Width attribute with conditional display
        width_attr = AttributeNode(
            manufacturing_type_id=manufacturing_type.id,
            parent_node_id=basic_info.id,
            name="width",
            node_type="attribute",
            data_type="number",
            required=False,
            ui_component="input",
            description="Width in mm",
            display_condition={"operator": "equals", "field": "type", "value": "Frame"},
            validation_rules={
                "min": 100,
                "max": 3000,
                "message": "Width must be between 100 and 3000 mm",
            },
            ltree_path="basic_information.width",
            depth=1,
            sort_order=5,
        )
        db_session.add(width_attr)

        await db_session.commit()
        return manufacturing_type

    async def test_get_profile_schema_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test successful profile schema retrieval."""
        response = await client.get(
            f"/api/v1/entry/profile/schema/{manufacturing_type_with_attributes.id}",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify schema structure
        assert "manufacturing_type_id" in data
        assert "sections" in data
        assert "conditional_logic" in data

        assert data["manufacturing_type_id"] == manufacturing_type_with_attributes.id
        assert len(data["sections"]) > 0

        # Verify section structure
        section = data["sections"][0]
        assert "title" in section
        assert "fields" in section
        assert "sort_order" in section
        assert section["title"] == "Basic Information"

        # Verify field structure
        fields = section["fields"]
        assert len(fields) >= 3  # type, material, width

        type_field = next(f for f in fields if f["name"] == "type")
        assert type_field["label"] == "Profile Type"
        assert type_field["data_type"] == "string"
        assert type_field["required"] is True
        assert type_field["ui_component"] == "dropdown"

        # Verify conditional logic
        assert "width" in data["conditional_logic"]
        width_condition = data["conditional_logic"]["width"]
        assert width_condition["operator"] == "equals"
        assert width_condition["field"] == "type"
        assert width_condition["value"] == "Frame"

    @pytest.mark.asyncio
    async def test_get_profile_schema_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test profile schema retrieval for non-existent manufacturing type."""
        response = await client.get(
            "/api/v1/entry/profile/schema/99999", headers=superuser_auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "Manufacturing type 99999 not found" in data["message"]

    @pytest.mark.asyncio
    async def test_get_profile_schema_unauthorized(
        self,
        client: AsyncClient,
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test profile schema retrieval without authentication."""
        response = await client.get(
            f"/api/v1/entry/profile/schema/{manufacturing_type_with_attributes.id}"
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_save_profile_data_success_with_customer_relationship(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test successful profile data saving with proper customer relationship."""
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Test Living Room Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "width": 1200,
        }

        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )

        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

        assert response.status_code == 201
        data = response.json()

        # Verify configuration structure
        assert "id" in data
        assert "manufacturing_type_id" in data
        assert "customer_id" in data
        assert "name" in data
        assert "status" in data
        assert "total_price" in data
        assert "calculated_weight" in data

        assert data["manufacturing_type_id"] == manufacturing_type_with_attributes.id
        assert data["name"] == "Test Living Room Window"
        assert data["status"] == "draft"

        # Verify customer relationship (should NOT be user.id)
        # The system should auto-create or find a customer record
        customer_id = data["customer_id"]
        assert customer_id is not None
        assert isinstance(customer_id, int)

        # Verify customer was created/found in database
        from sqlalchemy import select

        from app.models.customer import Customer

        result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        assert customer is not None
        assert customer.email == test_superuser.email

        # Verify pricing calculation (base price + any impacts)
        assert float(data["total_price"]) >= manufacturing_type_with_attributes.base_price

    @pytest.mark.ci_cd_issue
    @pytest.mark.asyncio
    async def test_save_profile_data_validation_error(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test profile data saving with validation errors."""
        # Missing required field 'type'
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Test Window",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "width": 1200,
        }

        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        # FastAPI's automatic validation returns 'detail' field, not 'message'
        assert "detail" in data
        # Check that the validation error mentions the missing field
        assert any("type" in str(error.get("loc", [])) for error in data["detail"])

    @pytest.mark.asyncio
    async def test_save_profile_data_invalid_manufacturing_type(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test profile data saving with invalid manufacturing type."""
        profile_data = {
            "manufacturing_type_id": 99999,
            "name": "Test Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
        }

        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "Invalid manufacturing type" in data["message"]

    @pytest.mark.asyncio
    async def test_load_profile_data_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test successful profile data loading."""
        # First create a configuration
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Test Load Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "width": 1400,
        }

        save_response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )

        if save_response.status_code != 201:
            print(f"Response status: {save_response.status_code}")
            print(f"Response body: {save_response.text}")

        assert save_response.status_code == 201
        configuration_id = save_response.json()["id"]

        # Now load the profile data
        response = await client.get(
            f"/api/v1/entry/profile/load/{configuration_id}", headers=superuser_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify loaded data structure matches ProfileEntryData schema
        assert "manufacturing_type_id" in data
        assert "name" in data
        assert "type" in data
        assert "material" in data
        assert "opening_system" in data
        assert "system_series" in data
        assert "width" in data

        # Verify data matches what was saved
        assert data["manufacturing_type_id"] == manufacturing_type_with_attributes.id
        assert data["name"] == "Test Load Window"
        assert data["type"] == "Frame"
        assert data["material"] == "Aluminum"
        assert data["opening_system"] == "Casement"
        assert data["system_series"] == "Kom800"
        assert data["width"] == 1400

    @pytest.mark.asyncio
    async def test_load_profile_data_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test profile data loading for non-existent configuration."""
        response = await client.get(
            "/api/v1/entry/profile/load/99999", headers=superuser_auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "Configuration 99999 not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_load_profile_data_unauthorized_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test profile data loading by unauthorized user."""
        # Create configuration as superuser
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Superuser Load Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
        }

        save_response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )
        assert save_response.status_code == 201
        configuration_id = save_response.json()["id"]

        # Try to load as regular user
        response = await client.get(
            f"/api/v1/entry/profile/load/{configuration_id}", headers=auth_headers
        )

        assert response.status_code == 403
        data = response.json()
        assert "Not authorized to access this configuration" in data["detail"]

    @pytest.mark.asyncio
    async def test_load_profile_data_unauthorized_no_auth(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test profile data loading without authentication."""
        # Create configuration first
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "No Auth Load Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
        }

        save_response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )
        assert save_response.status_code == 201
        configuration_id = save_response.json()["id"]

        # Try to load without authentication
        response = await client.get(f"/api/v1/entry/profile/load/{configuration_id}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_preview_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test successful profile preview retrieval."""
        # First create a configuration
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Test Preview Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "width": 1500,
        }

        save_response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )
        assert save_response.status_code == 201
        configuration_id = save_response.json()["id"]

        # Now get the preview
        response = await client.get(
            f"/api/v1/entry/profile/preview/{configuration_id}", headers=superuser_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify preview structure
        assert "configuration_id" in data
        assert "table" in data
        assert "last_updated" in data

        assert data["configuration_id"] == configuration_id

        # Verify table structure
        table = data["table"]
        assert "headers" in table
        assert "rows" in table

        # Verify CSV headers are present
        headers = table["headers"]
        expected_headers = [
            "Name",
            "Type",
            "Company",
            "Material",
            "Opening System",
            "System Series",
            "Code",
            "Length of beam",
            "Renovation",
            "Width",
        ]
        for header in expected_headers[:4]:  # Check first few headers
            assert header in headers

        # Verify row data
        rows = table["rows"]
        assert len(rows) > 0
        row = rows[0]
        assert row["Name"] == "Test Preview Window"
        assert row["Type"] == "Frame"
        assert row["Material"] == "Aluminum"

    @pytest.mark.asyncio
    async def test_get_profile_preview_not_found(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test profile preview retrieval for non-existent configuration."""
        response = await client.get(
            "/api/v1/entry/profile/preview/99999", headers=superuser_auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "Configuration 99999 not found" in data["message"]

    @pytest.mark.asyncio
    async def test_get_profile_preview_unauthorized_user(
        self,
        client: AsyncClient,
        test_user: User,
        user_auth_headers: dict[str, str],
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test profile preview retrieval by unauthorized user."""
        # Create configuration as superuser
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Superuser Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
        }

        save_response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )
        assert save_response.status_code == 201
        configuration_id = save_response.json()["id"]

        # Try to access as regular user
        response = await client.get(
            f"/api/v1/entry/profile/preview/{configuration_id}", headers=user_auth_headers
        )

        assert response.status_code == 403
        data = response.json()
        assert "Not authorized to access this configuration" in data["message"]

    @pytest.mark.asyncio
    async def test_evaluate_display_conditions_success(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test successful display condition evaluation."""
        form_data = {"type": "Frame", "material": "Aluminum"}

        response = await client.post(
            "/api/v1/entry/profile/evaluate-conditions",
            json={
                "manufacturing_type_id": manufacturing_type_with_attributes.id,
                "form_data": form_data,
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should be a dictionary of field visibility
        assert isinstance(data, dict)

        # Width field should be visible when type="Frame"
        if "width" in data:
            assert data["width"] is True

    @pytest.mark.asyncio
    async def test_evaluate_display_conditions_hidden_field(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test display condition evaluation with hidden field."""
        form_data = {
            "type": "Flying mullion",  # Different value should hide width
            "material": "Aluminum",
        }

        response = await client.post(
            "/api/v1/entry/profile/evaluate-conditions",
            json={
                "manufacturing_type_id": manufacturing_type_with_attributes.id,
                "form_data": form_data,
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Width field should be hidden when type != "Frame"
        if "width" in data:
            assert data["width"] is False

    @pytest.mark.asyncio
    async def test_evaluate_display_conditions_invalid_manufacturing_type(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
    ):
        """Test display condition evaluation with invalid manufacturing type."""
        response = await client.post(
            "/api/v1/entry/profile/evaluate-conditions",
            json={"manufacturing_type_id": 99999, "form_data": {"type": "Frame"}},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "Manufacturing type 99999 not found" in data["message"]

    @pytest.mark.asyncio
    async def test_customer_auto_creation_for_new_users(
        self,
        client: AsyncClient,
        test_user: User,
        user_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test that customer records are auto-created for new users."""
        # Arrange - Ensure no existing customer for this user
        from sqlalchemy import select

        from app.models.customer import Customer

        result = await db_session.execute(select(Customer).where(Customer.email == test_user.email))
        existing_customer = result.scalar_one_or_none()

        # Delete existing customer if any (for clean test)
        if existing_customer:
            await db_session.delete(existing_customer)
            await db_session.commit()

        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Auto-Created Customer Test",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Auto800",
        }

        # Act
        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=user_auth_headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()

        # Verify customer was auto-created
        customer_id = data["customer_id"]
        result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
        auto_created_customer = result.scalar_one_or_none()

        assert auto_created_customer is not None
        assert auto_created_customer.email == test_user.email
        assert auto_created_customer.contact_person == test_user.full_name or test_user.username
        assert auto_created_customer.customer_type == "residential"
        assert "Auto-created" in auto_created_customer.notes


class TestEntryAPICasbinRBAC:
    """Tests for Casbin RBAC functionality in Entry API."""

    @pytest.mark.asyncio
    async def test_casbin_decorator_authorization_on_save_profile(
        self,
        client: AsyncClient,
        test_user: User,
        user_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test Casbin decorator authorization on save_profile_configuration."""
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Casbin Auth Test",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Auth800",
        }

        # Act
        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=user_auth_headers
        )

        # Assert - Regular users should be able to create configurations
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Casbin Auth Test"

    @pytest.mark.asyncio
    async def test_casbin_decorator_authorization_on_preview(
        self,
        client: AsyncClient,
        test_user: User,
        user_auth_headers: dict[str, str],
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test Casbin decorator authorization on generate_preview_data."""
        # Arrange - Create configuration as regular user
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Preview Auth Test",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Preview800",
        }

        save_response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=user_auth_headers
        )
        assert save_response.status_code == 201
        configuration_id = save_response.json()["id"]

        # Test 1: User can access their own configuration preview
        response = await client.get(
            f"/api/v1/entry/profile/preview/{configuration_id}", headers=user_auth_headers
        )
        assert response.status_code == 200

        # Test 2: Superuser can access any configuration preview
        response = await client.get(
            f"/api/v1/entry/profile/preview/{configuration_id}", headers=superuser_auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_customer_relationship_consistency_across_operations(
        self,
        client: AsyncClient,
        test_user: User,
        user_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
        db_session: AsyncSession,
    ):
        """Test that customer relationships remain consistent across multiple operations."""
        # Create first configuration
        profile_data_1 = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Consistency Test 1",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Consist800",
        }

        response1 = await client.post(
            "/api/v1/entry/profile/save", json=profile_data_1, headers=user_auth_headers
        )
        assert response1.status_code == 201
        customer_id_1 = response1.json()["customer_id"]

        # Create second configuration
        profile_data_2 = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Consistency Test 2",
            "type": "Frame",
            "material": "Wood",
            "opening_system": "Sliding",
            "system_series": "Consist900",
        }

        response2 = await client.post(
            "/api/v1/entry/profile/save", json=profile_data_2, headers=user_auth_headers
        )
        assert response2.status_code == 201
        customer_id_2 = response2.json()["customer_id"]

        # Assert - Both configurations should use the same customer
        assert customer_id_1 == customer_id_2

        # Verify in database
        from sqlalchemy import select

        from app.models.customer import Customer

        result = await db_session.execute(select(Customer).where(Customer.id == customer_id_1))
        customer = result.scalar_one_or_none()
        assert customer is not None
        assert customer.email == test_user.email

    @pytest.mark.asyncio
    async def test_all_endpoints_require_authentication(
        self,
        client: AsyncClient,
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test that all entry API endpoints require authentication."""
        endpoints = [
            ("GET", f"/api/v1/entry/profile/schema/{manufacturing_type_with_attributes.id}"),
            ("POST", "/api/v1/entry/profile/save"),
            ("GET", "/api/v1/entry/profile/load/1"),
            ("GET", "/api/v1/entry/profile/preview/1"),
            ("POST", "/api/v1/entry/profile/evaluate-conditions"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json={})

            assert response.status_code == 401, f"Endpoint {method} {url} should require auth"

    @pytest.mark.asyncio
    async def test_profile_data_validation_rules(
        self,
        client: AsyncClient,
        test_superuser: User,
        superuser_auth_headers: dict[str, str],
        manufacturing_type_with_attributes: ManufacturingType,
    ):
        """Test profile data validation against attribute rules."""
        # Test width validation (should be between 100-3000)
        profile_data = {
            "manufacturing_type_id": manufacturing_type_with_attributes.id,
            "name": "Test Window",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "width": 50,  # Below minimum
        }

        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )

        assert response.status_code == 422
        data = response.json()
        assert "Validation failed" in data["message"]

        # Test with valid width
        profile_data["width"] = 1200
        response = await client.post(
            "/api/v1/entry/profile/save", json=profile_data, headers=superuser_auth_headers
        )

        assert response.status_code == 201
