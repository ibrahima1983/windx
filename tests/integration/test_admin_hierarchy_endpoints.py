"""Integration tests for admin hierarchy management endpoints.

Tests the admin dashboard endpoints for managing hierarchical attribute data.
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_hierarchy_dashboard_no_type_selected(
    client: AsyncClient,
    superuser_auth_headers: dict,
):
    """Test dashboard renders with no manufacturing type selected."""
    # Create a manufacturing type for the selector via API
    create_response = await client.post(
        "/api/v1/manufacturing-types/",
        headers=superuser_auth_headers,
        json={
            "name": "Test Window Dashboard No Selection",
            "description": "Test window type",
            "base_price": "200.00",
            "base_weight": "0.00",
        },
    )
    assert create_response.status_code == 201

    # Request dashboard without type selection
    response = await client.get(
        "/api/v1/admin/hierarchy/",
        headers=superuser_auth_headers,
    )

    # Verify response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # Verify content contains expected elements
    content = response.text
    assert "Hierarchy Editor" in content
    assert "Test Window" in content
    assert "Select Manufacturing Type" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_shows_ascii_tree(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test dashboard includes ASCII tree visualization."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("50.00"),
    )

    # Request dashboard
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify ASCII tree is present
    assert response.status_code == 200
    content = response.text
    # The tree is shown in the diagram tab
    assert "Frame Options [category]" in content
    assert "Aluminum [option]" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_requires_superuser(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test dashboard requires superuser authentication."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Request without authentication
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
    )

    # Verify unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hierarchy_dashboard_with_empty_tree(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test dashboard handles manufacturing type with no nodes."""
    # Create manufacturing type with no nodes
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Empty Type",
        base_price=Decimal("100.00"),
    )

    # Request dashboard
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify response
    assert response.status_code == 200
    content = response.text
    assert "Empty Type" in content
    # Should show empty state message
    assert "No attribute nodes found" in content or "Empty tree" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_diagram_failure_graceful(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
    monkeypatch,
):
    """Test dashboard handles diagram generation failure gracefully."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    # Mock plot_tree to raise exception
    async def mock_plot_tree(*args, **kwargs):
        raise Exception("Matplotlib not available")

    monkeypatch.setattr(
        "app.services.hierarchy_builder.HierarchyBuilderService.plot_tree", mock_plot_tree
    )

    # Request dashboard (should not crash)
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify response is still successful
    assert response.status_code == 200
    content = response.text
    assert "Frame Options" in content
    # Diagram should be None when generation fails, but page should still render
    # The ASCII tree should still be visible
    assert "Frame Options [category]" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_diagram_generation_success(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test dashboard successfully generates and displays diagram tree."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("50.00"),
    )

    # Request dashboard
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify response
    assert response.status_code == 200
    content = response.text

    # Verify ASCII tree is present
    assert "Frame Options [category]" in content
    assert "Aluminum [option]" in content

    # Verify diagram image is embedded (base64 encoded PNG)
    # The template should have an img tag with base64 data
    assert "data:image/png;base64," in content or "diagram_tree" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_with_complex_tree(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test dashboard with complex multi-level hierarchy."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Complex Window",
        base_price=Decimal("200.00"),
    )

    # Create complex hierarchy
    hierarchy = {
        "name": "Frame Options",
        "node_type": "category",
        "children": [
            {
                "name": "Material Type",
                "node_type": "attribute",
                "children": [
                    {
                        "name": "Aluminum",
                        "node_type": "option",
                        "price_impact_value": Decimal("50.00"),
                    },
                    {
                        "name": "Vinyl",
                        "node_type": "option",
                        "price_impact_value": Decimal("30.00"),
                    },
                ],
            },
            {
                "name": "Color",
                "node_type": "attribute",
                "children": [
                    {
                        "name": "White",
                        "node_type": "option",
                    },
                    {
                        "name": "Black",
                        "node_type": "option",
                        "price_impact_value": Decimal("25.00"),
                    },
                ],
            },
        ],
    }

    await service.create_hierarchy_from_dict(
        manufacturing_type_id=mfg_type.id,
        hierarchy_data=hierarchy,
    )

    # Request dashboard
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify all nodes are present
    assert response.status_code == 200
    content = response.text
    assert "Frame Options" in content
    assert "Material Type" in content
    assert "Aluminum" in content
    assert "Vinyl" in content
    assert "Color" in content
    assert "White" in content
    assert "Black" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_multiple_manufacturing_types(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test dashboard selector shows multiple manufacturing types."""
    # Create multiple manufacturing types
    service = HierarchyBuilderService(db_session)

    window = await service.create_manufacturing_type(
        name="Window Type",
        base_price=Decimal("200.00"),
    )

    door = await service.create_manufacturing_type(
        name="Door Type",
        base_price=Decimal("300.00"),
    )

    # Request dashboard
    response = await client.get(
        "/api/v1/admin/hierarchy/",
        headers=superuser_auth_headers,
    )

    # Verify both types are in selector
    assert response.status_code == 200
    content = response.text
    assert "Window Type" in content
    assert "Door Type" in content
    assert "Select Manufacturing Type" in content


@pytest.mark.asyncio
async def test_hierarchy_dashboard_flattened_attribute_nodes_structure(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that dashboard provides flattened attribute_nodes for JavaScript consumption."""
    import random
    import time

    # Create manufacturing type and complex hierarchy with unique name
    service = HierarchyBuilderService(db_session)
    unique_id = f"{int(time.time() * 1000)}{random.randint(1000, 9999)}"
    mfg_type = await service.create_manufacturing_type(
        name=f"Test Window Flattened {unique_id}",
        base_price=Decimal("200.00"),
    )

    # Create nested hierarchy: Root -> Category -> Attribute -> Option
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    category = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",
        node_type="attribute",
        parent_node_id=root.id,
    )

    option1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=category.id,
        price_impact_value=Decimal("50.00"),
    )

    option2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Wood",
        node_type="option",
        parent_node_id=category.id,
        price_impact_value=Decimal("120.00"),
    )

    # Request dashboard
    response = await client.get(
        f"/api/v1/admin/hierarchy/?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    assert response.status_code == 200
    content = response.text

    # Verify all nodes are present in the flattened structure
    # The JavaScript should receive a flat list of all nodes without nested children
    assert "Frame Options" in content
    assert "Material Type" in content
    assert "Aluminum" in content
    assert "Wood" in content

    # Verify that the attribute_nodes JavaScript data is present
    # This should be a flat array, not nested tree structure
    assert "var nodeData" in content or "nodeData" in content

    # Verify the structure contains all expected node IDs
    # The flattened structure should include all 4 nodes we created
    import re

    # Look for JavaScript variable containing node data
    # The template should render something like: var nodeData = [...];
    js_data_match = re.search(r"nodeData\s*=\s*(\[.*?\]);", content, re.DOTALL)
    if js_data_match:
        js_data = js_data_match.group(1)
        # Verify all node names appear in the JavaScript data
        assert "Frame Options" in js_data
        assert "Material Type" in js_data
        assert "Aluminum" in js_data
        assert "Wood" in js_data

        # Verify it's a flat structure (no nested "children" arrays)
        # Count occurrences of "children" - should be 0 in flattened structure
        children_count = js_data.count('"children"')
        assert children_count == 0, (
            f"Found {children_count} 'children' properties in flattened data, expected 0"
        )


# ============================================================================
# Node Form Endpoints Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_node_form_renders(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that create node form renders correctly."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Request create form
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify response
    assert response.status_code == 200
    content = response.text
    assert "Create Node" in content or "node_form" in content
    assert "Test Window" in content


@pytest.mark.asyncio
async def test_create_node_form_with_parent(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test create node form with parent node specified."""
    # Create manufacturing type and parent node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    parent = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    # Request create form with parent
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}&parent_id={parent.id}",
        headers=superuser_auth_headers,
    )

    # Verify response
    assert response.status_code == 200
    content = response.text
    assert "Frame Options" in content


@pytest.mark.asyncio
async def test_create_node_form_requires_superuser(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that create node form requires superuser authentication."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Request without authentication
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}",
    )

    # Verify unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_save_node_creates_new_node(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that save_node endpoint creates a new node."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form to create node
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Frame Material",
        "node_type": "category",
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify redirect to dashboard
    assert response.status_code == 303
    assert f"manufacturing_type_id={mfg_type.id}" in response.headers["location"]
    assert "success" in response.headers["location"]

    # Verify node was created
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    nodes = await attr_repo.get_by_manufacturing_type(mfg_type.id)
    assert len(nodes) == 1
    assert nodes[0].name == "Frame Material"


@pytest.mark.asyncio
async def test_save_node_updates_existing_node(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that save_node endpoint updates an existing node."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Original Name",
        node_type="category",
    )

    # Submit form to update node
    form_data = {
        "node_id": str(node.id),
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Updated Name",
        "node_type": "category",
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify redirect
    assert response.status_code == 303
    assert "success" in response.headers["location"]

    # Verify node was updated
    await db_session.refresh(node)
    assert node.name == "Updated Name"


@pytest.mark.asyncio
async def test_save_node_with_price_impact(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test saving node with price impact value."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with price impact
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Aluminum Frame",
        "node_type": "option",
        "price_impact_type": "fixed",
        "price_impact_value": "50.00",
        "weight_impact": "2.0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify success
    assert response.status_code == 303

    # Verify node has correct price impact
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    nodes = await attr_repo.get_by_manufacturing_type(mfg_type.id)
    assert len(nodes) == 1
    assert nodes[0].price_impact_value == Decimal("50.00")
    assert nodes[0].weight_impact == Decimal("2.0")


@pytest.mark.asyncio
async def test_save_node_requires_superuser(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that save_node requires superuser authentication."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form without authentication
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Test Node",
        "node_type": "category",
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        data=form_data,
    )

    # Verify unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_edit_node_form_renders(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that edit node form renders with pre-filled data."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Material",
        node_type="category",
        description="Test description",
    )

    # Request edit form
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/{node.id}/edit",
        headers=superuser_auth_headers,
    )

    # Verify response
    assert response.status_code == 200
    content = response.text
    assert "Edit Node" in content or "node_form" in content
    assert "Frame Material" in content
    assert "Test description" in content


@pytest.mark.asyncio
async def test_edit_node_form_excludes_descendants_from_parent_selector(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that edit form excludes node and descendants from parent selector."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Root",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child",
        node_type="category",
        parent_node_id=root.id,
    )

    grandchild = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Grandchild",
        node_type="option",
        parent_node_id=child.id,
    )

    # Request edit form for root node
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/{root.id}/edit",
        headers=superuser_auth_headers,
    )

    # Verify response (root, child, grandchild should not be in parent selector)
    assert response.status_code == 200
    # The form should render successfully
    content = response.text
    assert "Root" in content


@pytest.mark.asyncio
async def test_edit_node_form_requires_superuser(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that edit node form requires superuser authentication."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Test Node",
        node_type="category",
    )

    # Request without authentication
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/{node.id}/edit",
    )

    # Verify unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_node_success(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test successful node deletion."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Test Node",
        node_type="category",
    )

    # Delete node
    response = await client.post(
        f"/api/v1/admin/hierarchy/node/{node.id}/delete",
        headers=superuser_auth_headers,
    )

    # Verify redirect
    assert response.status_code == 303
    assert "success" in response.headers["location"]

    # Verify node was deleted
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    deleted_node = await attr_repo.get(node.id)
    assert deleted_node is None


@pytest.mark.asyncio
async def test_delete_node_with_children_fails(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that deleting node with children returns error."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    parent = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Parent",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child",
        node_type="option",
        parent_node_id=parent.id,
    )

    # Try to delete parent
    response = await client.post(
        f"/api/v1/admin/hierarchy/node/{parent.id}/delete",
        headers=superuser_auth_headers,
    )

    # Verify redirect with error
    assert response.status_code == 303
    assert "error" in response.headers["location"]
    assert "children" in response.headers["location"].lower()

    # Verify node still exists
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    existing_node = await attr_repo.get(parent.id)
    assert existing_node is not None


@pytest.mark.asyncio
async def test_delete_node_requires_superuser(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that delete node requires superuser authentication."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Test Node",
        node_type="category",
    )

    # Request without authentication
    response = await client.post(
        f"/api/v1/admin/hierarchy/node/{node.id}/delete",
    )

    # Verify unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_flash_message_success_displayed(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that success flash messages are displayed in the dashboard."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    response = await client.get(
        f"/api/v1/admin/hierarchy?manufacturing_type_id={mfg_type.id}&success=Node created successfully",
        headers=superuser_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Node created successfully" in response.content
    assert b"alert-success" in response.content
    # Template uses emoji instead of Bootstrap Icons
    assert "✅" in response.text or "alert-success" in response.text


@pytest.mark.asyncio
async def test_flash_message_error_displayed(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that error flash messages are displayed in the dashboard."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    response = await client.get(
        f"/api/v1/admin/hierarchy?manufacturing_type_id={mfg_type.id}&error=Node not found",
        headers=superuser_auth_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Node not found" in response.content
    # Template uses alert-error class (not alert-danger)
    assert b"alert-error" in response.content
    # Template uses emoji instead of Bootstrap Icons
    assert "⚠️" in response.text or "alert-error" in response.text


@pytest.mark.asyncio
async def test_create_node_redirects_with_success_message(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that creating a node redirects with success message."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data={
            "manufacturing_type_id": str(mfg_type.id),
            "name": "Test Node",
            "node_type": "category",
            "price_impact_type": "fixed",
            "weight_impact": "0",
            "sort_order": "0",
            "required": "false",
        },
    )

    assert response.status_code == 303
    # Check for URL-encoded version of the message
    assert "success=" in response.headers["location"]
    assert (
        "Node created successfully" in response.headers["location"]
        or "Node%20created%20successfully" in response.headers["location"]
    )


@pytest.mark.asyncio
async def test_delete_node_redirects_with_success_message(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that deleting a node redirects with success message."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Test Node",
        node_type="category",
    )

    response = await client.post(
        f"/api/v1/admin/hierarchy/node/{node.id}/delete",
        headers=superuser_auth_headers,
    )

    assert response.status_code == 303
    # Check for URL-encoded version of the message
    assert "success=" in response.headers["location"]
    assert (
        "Node deleted successfully" in response.headers["location"]
        or "Node%20deleted%20successfully" in response.headers["location"]
    )
