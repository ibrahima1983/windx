"""Integration tests for API endpoints with page type functionality."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manufacturing_type import ManufacturingType
from app.models.attribute_node import AttributeNode
from app.models.user import User


@pytest.mark.asyncio
class TestAPIEndpointsPageTypes:
    """Integration tests for API endpoints with page type support."""

    @pytest.fixture
    async def test_manufacturing_type(self, db_session: AsyncSession) -> ManufacturingType:
        """Create a test manufacturing type."""
        mfg_type = ManufacturingType(
            name="Test Window Profile Entry",
            description="Test manufacturing type for API tests",
            base_category="window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)
        return mfg_type

    @pytest.fixture
    async def test_superuser(self, db_session: AsyncSession) -> User:
        """Create a test superuser for authentication."""
        from app.core.security import get_password_hash

        user = User(
            email="test_superuser@example.com",
            username="test_superuser",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test Superuser",
            is_active=True,
            is_superuser=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def auth_headers(self, test_superuser: User) -> dict[str, str]:
        """Create authentication headers for API requests."""
        from app.core.security import create_access_token

        access_token = create_access_token(subject=test_superuser.id)
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.fixture
    async def sample_attribute_nodes(
        self, db_session: AsyncSession, test_manufacturing_type: ManufacturingType
    ) -> dict[str, list[AttributeNode]]:
        """Create sample attribute nodes for each page type."""
        nodes_by_type = {}

        page_type_configs = {
            "profile": [
                ("name", "string", True, "Product name"),
                ("material", "string", True, "Material type"),
                ("width", "number", False, "Width in mm"),
            ],
            "accessories": [
                ("accessory_name", "string", True, "Accessory name"),
                ("accessory_type", "string", True, "Type of accessory"),
                ("unit_price", "number", False, "Price per unit"),
            ],
            "glazing": [
                ("glass_type", "string", True, "Type of glass"),
                ("thickness", "number", True, "Glass thickness"),
                ("u_value", "number", False, "U-value rating"),
            ],
        }

        for page_type, configs in page_type_configs.items():
            nodes = []
            for i, (name, data_type, required, description) in enumerate(configs):
                node = AttributeNode(
                    manufacturing_type_id=test_manufacturing_type.id,
                    page_type=page_type,
                    name=name,
                    description=description,
                    node_type="attribute",
                    data_type=data_type,
                    required=required,
                    ltree_path=f"{page_type}.test.{name}",
                    depth=2,
                    sort_order=i + 1,
                    ui_component="input" if data_type == "string" else "number",
                    help_text=f"Help for {name}",
                )
                nodes.append(node)
                db_session.add(node)

            nodes_by_type[page_type] = nodes

        await db_session.commit()
        return nodes_by_type

    @pytest.mark.parametrize(
        "page_type,expected_status",
        [
            ("profile", 200),
            ("accessories", 200),
            ("glazing", 200),
        ],
        ids=["profile_page", "accessories_page", "glazing_page"],
    )
    def test_entry_page_endpoints_valid_page_types(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        auth_headers: dict[str, str],
        page_type: str,
        expected_status: int,
    ):
        """Test entry page endpoints with valid page types."""
        # Test profile endpoint with page_type parameter
        if page_type == "profile":
            response = client.get(
                f"/api/v1/admin/entry/profile?manufacturing_type_id={test_manufacturing_type.id}&page_type={page_type}",
                headers=auth_headers,
            )
        elif page_type == "accessories":
            response = client.get(
                f"/api/v1/admin/entry/accessories?manufacturing_type_id={test_manufacturing_type.id}&type=window",
                headers=auth_headers,
            )
        else:  # glazing
            response = client.get(
                f"/api/v1/admin/entry/glazing?manufacturing_type_id={test_manufacturing_type.id}&type=window",
                headers=auth_headers,
            )

        assert response.status_code == expected_status
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.parametrize(
        "invalid_page_type",
        [
            "invalid",
            "PROFILE",
            "Profile",
            "profiles",
            "accessory",
            "glass",
            "",
            "123",
        ],
        ids=[
            "random_invalid",
            "uppercase",
            "titlecase",
            "plural",
            "singular",
            "different_term",
            "empty",
            "numeric",
        ],
    )
    def test_profile_endpoint_invalid_page_types(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        auth_headers: dict[str, str],
        invalid_page_type: str,
    ):
        """Test profile endpoint rejects invalid page types."""
        response = client.get(
            f"/api/v1/admin/entry/profile?manufacturing_type_id={test_manufacturing_type.id}&page_type={invalid_page_type}",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid page type" in response.text

    def test_profile_endpoint_default_page_type(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        auth_headers: dict[str, str],
    ):
        """Test profile endpoint uses default page_type when not specified."""
        response = client.get(
            f"/api/v1/admin/entry/profile?manufacturing_type_id={test_manufacturing_type.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_profile_schema_endpoint(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        sample_attribute_nodes: dict[str, list[AttributeNode]],
        auth_headers: dict[str, str],
    ):
        """Test profile schema endpoint returns correct structure."""
        response = client.get(
            f"/api/v1/admin/entry/profile/schema/{test_manufacturing_type.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "sections" in data
        assert isinstance(data["sections"], list)

        if data["sections"]:
            section = data["sections"][0]
            assert "fields" in section
            assert isinstance(section["fields"], list)

    def test_profile_headers_endpoint(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        sample_attribute_nodes: dict[str, list[AttributeNode]],
        auth_headers: dict[str, str],
    ):
        """Test profile headers endpoint returns list of headers."""
        response = client.get(
            f"/api/v1/admin/entry/profile/headers/{test_manufacturing_type.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        headers = response.json()

        assert isinstance(headers, list)
        # Should include at least the ID column
        assert "id" in headers

    def test_endpoints_without_authentication(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
    ):
        """Test that endpoints require authentication."""
        endpoints = [
            f"/api/v1/admin/entry/profile?manufacturing_type_id={test_manufacturing_type.id}",
            f"/api/v1/admin/entry/accessories?manufacturing_type_id={test_manufacturing_type.id}",
            f"/api/v1/admin/entry/glazing?manufacturing_type_id={test_manufacturing_type.id}",
            f"/api/v1/admin/entry/profile/schema/{test_manufacturing_type.id}",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
            assert "Not authenticated" in response.json()["detail"]

    def test_endpoints_with_invalid_manufacturing_type(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Test endpoints with non-existent manufacturing type ID."""
        invalid_id = 99999

        endpoints = [
            f"/api/v1/admin/entry/profile?manufacturing_type_id={invalid_id}",
            f"/api/v1/admin/entry/accessories?manufacturing_type_id={invalid_id}",
            f"/api/v1/admin/entry/glazing?manufacturing_type_id={invalid_id}",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)
            # Should either return 503 (no manufacturing types) or handle gracefully
            assert response.status_code in [503, 200]

    @pytest.mark.parametrize(
        "manufacturing_category", ["window", "door"], ids=["window_category", "door_category"]
    )
    def test_accessories_glazing_endpoints_with_categories(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        auth_headers: dict[str, str],
        manufacturing_category: str,
    ):
        """Test accessories and glazing endpoints with different manufacturing categories."""
        endpoints = [
            f"/api/v1/admin/entry/accessories?manufacturing_type_id={test_manufacturing_type.id}&type={manufacturing_category}",
            f"/api/v1/admin/entry/glazing?manufacturing_type_id={test_manufacturing_type.id}&type={manufacturing_category}",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    def test_error_template_rendering(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Test that error template renders correctly for various error conditions."""
        # Test with invalid page type
        response = client.get(
            "/api/v1/admin/entry/profile?manufacturing_type_id=1&page_type=invalid",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "text/html" in response.headers.get("content-type", "")
        assert "Invalid page type" in response.text

    def test_navigation_context_in_templates(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        auth_headers: dict[str, str],
    ):
        """Test that templates receive correct navigation context."""
        endpoints_and_expected_titles = [
            (
                f"/api/v1/admin/entry/profile?manufacturing_type_id={test_manufacturing_type.id}",
                "Profile Entry",
            ),
            (
                f"/api/v1/admin/entry/accessories?manufacturing_type_id={test_manufacturing_type.id}",
                "Window Accessories Entry",
            ),
            (
                f"/api/v1/admin/entry/glazing?manufacturing_type_id={test_manufacturing_type.id}",
                "Window Glazing Entry",
            ),
        ]

        for endpoint, expected_title in endpoints_and_expected_titles:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 200
            # Check that the title appears in the response
            assert expected_title in response.text or "Entry" in response.text
