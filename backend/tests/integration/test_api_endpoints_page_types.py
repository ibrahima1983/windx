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

    def test_profile_schema_endpoint(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
        sample_attribute_nodes: dict[str, list[AttributeNode]],
        auth_headers: dict[str, str],
    ):
        """Test profile schema endpoint returns correct structure."""
        response = client.get(
            f"/api/v1/entry/profile/schema/{test_manufacturing_type.id}",
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

    def test_endpoints_without_authentication(
        self,
        client: TestClient,
        test_manufacturing_type: ManufacturingType,
    ):
        """Test that endpoints require authentication."""
        endpoints = [
            f"/api/v1/entry/profile/schema/{test_manufacturing_type.id}",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
            assert "Not authenticated" in response.json()["detail"]
