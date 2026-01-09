"""Integration tests for admin relations endpoints.

Tests the Relations management API for hierarchical option dependencies
(Company → Material → Opening System → System Series → Colors).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
class TestRelationsPage:
    """Tests for GET /api/v1/admin/relations endpoint."""

    async def test_relations_page_renders(self, client: AsyncClient):
        """Test that relations page renders successfully."""
        response = await client.get("/api/v1/admin/relations")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
class TestEntityCRUD:
    """Tests for entity CRUD endpoints."""

    async def test_create_company_entity(self, client: AsyncClient):
        """Test creating a company entity."""
        response = await client.post(
            "/api/v1/admin/relations/entities",
            json={
                "entity_type": "company",
                "name": "Test Company",
                "price_from": "100.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["entity"]["name"] == "Test Company"
        assert data["entity"]["node_type"] == "company"

    async def test_create_material_entity(self, client: AsyncClient):
        """Test creating a material entity with metadata."""
        response = await client.post(
            "/api/v1/admin/relations/entities",
            json={
                "entity_type": "material",
                "name": "UPVC",
                "price_from": "50.00",
                "metadata": {"density": 1.4},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["entity"]["name"] == "UPVC"
        assert data["entity"]["node_type"] == "material"

    async def test_create_entity_invalid_type(self, client: AsyncClient):
        """Test creating entity with invalid type returns error."""
        response = await client.post(
            "/api/v1/admin/relations/entities",
            json={
                "entity_type": "invalid_type",
                "name": "Test",
            },
        )

        assert response.status_code == 400

    async def test_get_entities_by_type(self, client: AsyncClient):
        """Test getting entities by type."""
        # First create an entity
        await client.post(
            "/api/v1/admin/relations/entities",
            json={
                "entity_type": "company",
                "name": "Test Company for List",
            },
        )

        # Then get all companies
        response = await client.get("/api/v1/admin/relations/entities/company")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["entities"], list)

    async def test_get_entities_invalid_type(self, client: AsyncClient):
        """Test getting entities with invalid type returns error."""
        response = await client.get("/api/v1/admin/relations/entities/invalid_type")

        assert response.status_code == 400

    async def test_update_entity(self, client: AsyncClient):
        """Test updating an entity."""
        # First create an entity
        create_response = await client.post(
            "/api/v1/admin/relations/entities",
            json={
                "entity_type": "company",
                "name": "Original Name",
            },
        )
        entity_id = create_response.json()["entity"]["id"]

        # Update the entity
        response = await client.put(
            f"/api/v1/admin/relations/entities/{entity_id}",
            json={
                "name": "Updated Name",
                "price_from": "200.00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["entity"]["name"] == "Updated Name"

    async def test_update_entity_not_found(self, client: AsyncClient):
        """Test updating non-existent entity returns 404."""
        response = await client.put(
            "/api/v1/admin/relations/entities/99999",
            json={"name": "New Name"},
        )

        assert response.status_code == 404

    async def test_delete_entity(self, client: AsyncClient):
        """Test deleting an entity."""
        # First create an entity
        create_response = await client.post(
            "/api/v1/admin/relations/entities",
            json={
                "entity_type": "company",
                "name": "To Delete",
            },
        )
        entity_id = create_response.json()["entity"]["id"]

        # Delete the entity
        response = await client.delete(f"/api/v1/admin/relations/entities/{entity_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_delete_entity_not_found(self, client: AsyncClient):
        """Test deleting non-existent entity returns 404."""
        response = await client.delete("/api/v1/admin/relations/entities/99999")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestPathManagement:
    """Tests for dependency path management endpoints."""

    async def test_get_all_paths_empty(self, client: AsyncClient):
        """Test getting all paths when none exist."""
        response = await client.get("/api/v1/admin/relations/paths")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["paths"], list)

    async def test_create_dependency_path(self, client: AsyncClient):
        """Test creating a complete dependency path."""
        # Create all required entities
        entities = {}
        for entity_type in ["company", "material", "opening_system", "system_series", "color"]:
            response = await client.post(
                "/api/v1/admin/relations/entities",
                json={
                    "entity_type": entity_type,
                    "name": f"Test {entity_type.replace('_', ' ').title()}",
                },
            )
            entities[entity_type] = response.json()["entity"]["id"]

        # Create the path
        response = await client.post(
            "/api/v1/admin/relations/paths",
            json={
                "company_id": entities["company"],
                "material_id": entities["material"],
                "opening_system_id": entities["opening_system"],
                "system_series_id": entities["system_series"],
                "color_id": entities["color"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "ltree_path" in data["path"]

    async def test_create_path_invalid_entity(self, client: AsyncClient):
        """Test creating path with non-existent entity returns error."""
        response = await client.post(
            "/api/v1/admin/relations/paths",
            json={
                "company_id": 99999,
                "material_id": 99998,
                "opening_system_id": 99997,
                "system_series_id": 99996,
                "color_id": 99995,
            },
        )

        assert response.status_code == 400


@pytest.mark.asyncio
class TestDependentOptions:
    """Tests for cascading options endpoint."""

    async def test_get_dependent_options_empty(self, client: AsyncClient):
        """Test getting dependent options with no selections."""
        response = await client.post(
            "/api/v1/admin/relations/options",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["options"], dict)
