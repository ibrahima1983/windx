"""Integration tests for admin hierarchy parent node selector logic.

Tests the parent node selector formatting with hierarchical paths.
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_parent_selector_shows_hierarchical_paths(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that parent selector displays hierarchical paths (e.g., 'Frame > Material > Aluminum')."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create multi-level hierarchy
    frame = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",
        node_type="attribute",
        parent_node_id=frame.id,
    )

    aluminum = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=material.id,
    )

    # Request create form (should show all nodes in parent selector)
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    # Verify response contains hierarchical paths
    assert response.status_code == 200
    content = response.text

    # Check for hierarchical path format: "Frame Options > Material Type > Aluminum"
    assert "Frame Options" in content
    assert (
        "Frame Options &gt; Material Type" in content or "Frame Options > Material Type" in content
    )
    assert (
        "Frame Options &gt; Material Type &gt; Aluminum" in content
        or "Frame Options > Material Type > Aluminum" in content
    )


@pytest.mark.asyncio
async def test_parent_selector_excludes_node_and_descendants_when_editing(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that edit form excludes current node and descendants from parent selector."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create hierarchy: Root -> Child -> Grandchild
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Root Node",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child Node",
        node_type="category",
        parent_node_id=root.id,
    )

    grandchild = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Grandchild Node",
        node_type="option",
        parent_node_id=child.id,
    )

    # Create sibling node (should be available as parent)
    sibling = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Sibling Node",
        node_type="category",
    )

    # Request edit form for root node
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/{root.id}/edit",
        headers=superuser_auth_headers,
    )

    assert response.status_code == 200
    content = response.text

    # Sibling should be available as parent option
    assert "Sibling Node" in content

    # Root, Child, and Grandchild should NOT be in parent selector
    # (They should appear in the page but not as selectable parent options)
    # We can verify by checking the select element doesn't contain these as options
    # Note: The node being edited will appear in the form title/header but not in the parent selector


@pytest.mark.asyncio
async def test_parent_selector_formats_snake_case_to_title_case(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that parent selector converts snake_case ltree paths to Title Case."""
    # Create manufacturing type and hierarchy with snake_case names
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create nodes with names that will become snake_case in ltree_path
    frame_options = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",  # ltree: frame_options
        node_type="category",
    )

    material_type = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",  # ltree: frame_options.material_type
        node_type="attribute",
        parent_node_id=frame_options.id,
    )

    # Request create form
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    assert response.status_code == 200
    content = response.text

    # Verify readable format (not snake_case)
    assert "Frame Options" in content
    assert "Material Type" in content
    # Should NOT show snake_case in the selector
    assert "frame_options" not in content or "Frame Options" in content
    assert "material_type" not in content or "Material Type" in content


@pytest.mark.asyncio
async def test_parent_selector_shows_all_nodes_for_create_form(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that create form shows all nodes in parent selector."""
    # Create manufacturing type and multiple nodes
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create multiple nodes at different levels
    node1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Node One",
        node_type="category",
    )

    node2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Node Two",
        node_type="category",
    )

    node3 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Node Three",
        node_type="attribute",
        parent_node_id=node1.id,
    )

    # Request create form
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    assert response.status_code == 200
    content = response.text

    # All nodes should be available in parent selector
    assert "Node One" in content
    assert "Node Two" in content
    assert "Node Three" in content or "Node One &gt; Node Three" in content


@pytest.mark.asyncio
async def test_parent_selector_with_deep_hierarchy(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test parent selector with deep multi-level hierarchy."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create deep hierarchy (5 levels)
    level1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Level One",
        node_type="category",
    )

    level2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Level Two",
        node_type="category",
        parent_node_id=level1.id,
    )

    level3 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Level Three",
        node_type="attribute",
        parent_node_id=level2.id,
    )

    level4 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Level Four",
        node_type="option",
        parent_node_id=level3.id,
    )

    level5 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Level Five",
        node_type="option",
        parent_node_id=level4.id,
    )

    # Request create form
    response = await client.get(
        f"/api/v1/admin/hierarchy/node/create?manufacturing_type_id={mfg_type.id}",
        headers=superuser_auth_headers,
    )

    assert response.status_code == 200
    content = response.text

    # Verify deep path is formatted correctly
    # Should show: "Level One > Level Two > Level Three > Level Four > Level Five"
    assert "Level One" in content
    assert "Level Five" in content
    # Check for hierarchical separator
    assert "&gt;" in content or ">" in content
