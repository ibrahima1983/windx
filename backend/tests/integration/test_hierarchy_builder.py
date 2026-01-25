"""Integration tests for HierarchyBuilderService - Complete uPVC Hierarchy.

This test suite validates the complete functionality of the HierarchyBuilderService
by creating a real-world uPVC window hierarchy with multiple levels, price impacts,
and complex relationships.

Tests cover:
- Manufacturing type creation
- Root node creation
- Child node creation with proper path calculation
- Complete multi-level hierarchy creation
- Descendant queries using LTREE
- Batch creation from dictionary
- Transaction rollback on errors

Requirements: 10.1-10.12
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.repositories.attribute_node import AttributeNodeRepository
from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_create_manufacturing_type(db_session: AsyncSession):
    """Test creating a manufacturing type using HierarchyBuilderService.

    Verifies:
    - Manufacturing type is created successfully
    - Base price and base weight are set correctly
    - All fields are properly initialized

    Requirements: 10.1
    """
    service = HierarchyBuilderService(db_session)

    # Create "Casement Window" manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        description="Energy-efficient casement windows with superior ventilation",
        base_category="window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )

    # Verify manufacturing type was created
    assert mfg_type.id is not None
    assert mfg_type.name == "Casement Window"
    assert mfg_type.description == "Energy-efficient casement windows with superior ventilation"
    assert mfg_type.base_category == "window"
    assert mfg_type.base_price == Decimal("200.00")
    assert mfg_type.base_weight == Decimal("15.00")
    assert mfg_type.is_active is True


@pytest.mark.asyncio
async def test_create_root_node(db_session: AsyncSession):
    """Test creating a root category node.

    Verifies:
    - Root node is created with no parent
    - ltree_path is sanitized node name
    - Depth is 0
    - parent_node_id is None

    Requirements: 10.2, 10.9
    """
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )

    # Create root category node "Material"
    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )

    # Verify root node properties
    assert material.id is not None
    assert material.name == "Material"
    assert material.node_type == "category"
    assert material.parent_node_id is None
    assert material.ltree_path == "material"
    assert material.depth == 0
    assert material.manufacturing_type_id == mfg_type.id


@pytest.mark.asyncio
async def test_create_child_node(db_session: AsyncSession):
    """Test creating a child node under a parent.

    Verifies:
    - Child node is created with correct parent reference
    - ltree_path is "parent_path.child_name"
    - Depth is parent_depth + 1
    - parent_node_id is set correctly

    Requirements: 10.3, 10.9
    """
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        base_price=Decimal("200.00"),
    )

    # Create root node "Material"
    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )

    # Create child node "uPVC" under "Material"
    upvc = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="uPVC",
        node_type="category",
        parent_node_id=material.id,
    )

    # Verify child node properties
    assert upvc.id is not None
    assert upvc.name == "uPVC"
    assert upvc.node_type == "category"
    assert upvc.parent_node_id == material.id
    assert upvc.ltree_path == "material.upvc"
    assert upvc.depth == 1
    assert upvc.manufacturing_type_id == mfg_type.id


@pytest.mark.asyncio
async def test_create_complete_upvc_hierarchy(db_session: AsyncSession):
    """Test creating the complete uPVC window hierarchy.

    Creates the full hierarchy:
    Material → uPVC → System → Aluplast → Profile → IDEAL 4000 → Color & Decor

    Verifies:
    - All nodes are created with correct relationships
    - All ltree_paths are correct at each level
    - All depths are correct
    - Color options have price impacts

    Requirements: 10.4, 10.5, 10.6, 10.9
    """
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        description="uPVC casement window with multiple configuration options",
        base_category="window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )

    # Level 0: Material (root)
    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )
    assert material.ltree_path == "material"
    assert material.depth == 0

    # Level 1: uPVC
    upvc = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="uPVC",
        node_type="category",
        parent_node_id=material.id,
    )
    assert upvc.ltree_path == "material.upvc"
    assert upvc.depth == 1

    # Level 2: System
    system = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="System",
        node_type="category",
        parent_node_id=upvc.id,
    )
    assert system.ltree_path == "material.upvc.system"
    assert system.depth == 2

    # Level 3: Aluplast
    aluplast = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluplast",
        node_type="option",
        parent_node_id=system.id,
    )
    assert aluplast.ltree_path == "material.upvc.system.aluplast"
    assert aluplast.depth == 3

    # Level 4: Profile
    profile = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Profile",
        node_type="attribute",
        parent_node_id=aluplast.id,
    )
    assert profile.ltree_path == "material.upvc.system.aluplast.profile"
    assert profile.depth == 4

    # Level 5: IDEAL 4000 (with price impact)
    ideal_4000 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="IDEAL 4000",
        node_type="option",
        parent_node_id=profile.id,
        price_impact_type="fixed",
        price_impact_value=Decimal("50.00"),
    )
    assert ideal_4000.ltree_path == "material.upvc.system.aluplast.profile.ideal_4000"
    assert ideal_4000.depth == 5
    assert ideal_4000.price_impact_value == Decimal("50.00")

    # Level 6: Color & Decor
    color_decor = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Color & Decor",
        node_type="attribute",
        parent_node_id=ideal_4000.id,
    )
    assert (
        color_decor.ltree_path == "material.upvc.system.aluplast.profile.ideal_4000.color_and_decor"
    )
    assert color_decor.depth == 6

    # Level 7: Color options with price impacts
    standard_colors = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Standard colors",
        node_type="option",
        parent_node_id=color_decor.id,
        price_impact_type="fixed",
        price_impact_value=Decimal("0.00"),
    )
    assert (
        standard_colors.ltree_path
        == "material.upvc.system.aluplast.profile.ideal_4000.color_and_decor.standard_colors"
    )
    assert standard_colors.depth == 7
    assert standard_colors.price_impact_value == Decimal("0.00")

    special_colors = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Special colors",
        node_type="option",
        parent_node_id=color_decor.id,
        price_impact_type="fixed",
        price_impact_value=Decimal("25.00"),
    )
    assert (
        special_colors.ltree_path
        == "material.upvc.system.aluplast.profile.ideal_4000.color_and_decor.special_colors"
    )
    assert special_colors.depth == 7
    assert special_colors.price_impact_value == Decimal("25.00")

    aludec_collection = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aludec collection",
        node_type="option",
        parent_node_id=color_decor.id,
        price_impact_type="fixed",
        price_impact_value=Decimal("35.00"),
    )
    assert (
        aludec_collection.ltree_path
        == "material.upvc.system.aluplast.profile.ideal_4000.color_and_decor.aludec_collection"
    )
    assert aludec_collection.depth == 7
    assert aludec_collection.price_impact_value == Decimal("35.00")

    woodec_collection = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Woodec collection",
        node_type="option",
        parent_node_id=color_decor.id,
        price_impact_type="fixed",
        price_impact_value=Decimal("40.00"),
    )
    assert (
        woodec_collection.ltree_path
        == "material.upvc.system.aluplast.profile.ideal_4000.color_and_decor.woodec_collection"
    )
    assert woodec_collection.depth == 7
    assert woodec_collection.price_impact_value == Decimal("40.00")

    # Verify we can query all nodes
    repo = AttributeNodeRepository(db_session)
    all_nodes = await repo.get_by_manufacturing_type(mfg_type.id)
    # Count: Material(1) + uPVC(1) + System(1) + Aluplast(1) + Profile(1) +
    # IDEAL 4000(1) + Color & Decor(1) + 4 color options(4) = 11 nodes total
    assert len(all_nodes) == 11


@pytest.mark.asyncio
async def test_get_descendants(db_session: AsyncSession):
    """Test querying descendants using LTREE.

    Creates a multi-level hierarchy and verifies that get_descendants()
    returns all descendant nodes correctly.

    Requirements: 10.10
    """
    service = HierarchyBuilderService(db_session)
    repo = AttributeNodeRepository(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create hierarchy: Material → uPVC → System → Aluplast
    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )

    upvc = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="uPVC",
        node_type="category",
        parent_node_id=material.id,
    )

    system = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="System",
        node_type="category",
        parent_node_id=upvc.id,
    )

    aluplast = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluplast",
        node_type="option",
        parent_node_id=system.id,
    )

    # Also create a sibling branch to verify it's not included
    aluminum = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="category",
        parent_node_id=material.id,
    )

    # Get descendants of "Material" root node
    descendants = await repo.get_descendants(material.id)

    # Should include: uPVC, System, Aluplast, Aluminum (4 nodes)
    assert len(descendants) == 4
    descendant_names = {node.name for node in descendants}
    assert descendant_names == {"uPVC", "System", "Aluplast", "Aluminum"}

    # Get descendants of "uPVC" node
    upvc_descendants = await repo.get_descendants(upvc.id)

    # Should include: System, Aluplast (2 nodes)
    assert len(upvc_descendants) == 2
    upvc_descendant_names = {node.name for node in upvc_descendants}
    assert upvc_descendant_names == {"System", "Aluplast"}

    # Get descendants of "Aluplast" leaf node
    aluplast_descendants = await repo.get_descendants(aluplast.id)

    # Should be empty (leaf node has no descendants)
    assert len(aluplast_descendants) == 0


@pytest.mark.asyncio
async def test_create_hierarchy_from_dict(db_session: AsyncSession):
    """Test batch creation from nested dictionary structure.

    Creates a complete hierarchy from a nested dictionary and verifies
    all nodes are created with correct relationships.

    Requirements: 10.11
    """
    service = HierarchyBuilderService(db_session)
    repo = AttributeNodeRepository(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        base_price=Decimal("200.00"),
    )

    # Define nested hierarchy structure
    hierarchy_data = {
        "name": "Glass Type",
        "node_type": "category",
        "children": [
            {
                "name": "Glass Configuration",
                "node_type": "attribute",
                "data_type": "selection",
                "children": [
                    {
                        "name": "Single Pane",
                        "node_type": "option",
                        "price_impact_type": "fixed",
                        "price_impact_value": Decimal("0.00"),
                    },
                    {
                        "name": "Double Pane",
                        "node_type": "option",
                        "price_impact_type": "fixed",
                        "price_impact_value": Decimal("80.00"),
                    },
                    {
                        "name": "Triple Pane",
                        "node_type": "option",
                        "price_impact_type": "fixed",
                        "price_impact_value": Decimal("150.00"),
                    },
                ],
            },
            {
                "name": "Glass Coating",
                "node_type": "attribute",
                "data_type": "selection",
                "children": [
                    {
                        "name": "Low-E Coating",
                        "node_type": "option",
                        "price_impact_type": "fixed",
                        "price_impact_value": Decimal("40.00"),
                    },
                    {
                        "name": "Tinted",
                        "node_type": "option",
                        "price_impact_type": "fixed",
                        "price_impact_value": Decimal("30.00"),
                    },
                ],
            },
        ],
    }

    # Create hierarchy from dictionary
    root = await service.create_hierarchy_from_dict(
        manufacturing_type_id=mfg_type.id,
        hierarchy_data=hierarchy_data,
    )

    # Verify root node
    assert root.name == "Glass Type"
    assert root.node_type == "category"
    assert root.ltree_path == "glass_type"
    assert root.depth == 0

    # Get all nodes for this manufacturing type
    all_nodes = await repo.get_by_manufacturing_type(mfg_type.id)

    # Should have: 1 root + 2 attributes + 5 options = 8 nodes
    assert len(all_nodes) == 8

    # Verify structure by checking descendants
    descendants = await repo.get_descendants(root.id)
    assert len(descendants) == 7  # All nodes except root

    # Verify specific nodes exist with correct paths
    glass_config = next((n for n in all_nodes if n.name == "Glass Configuration"), None)
    assert glass_config is not None
    assert glass_config.ltree_path == "glass_type.glass_configuration"
    assert glass_config.depth == 1

    single_pane = next((n for n in all_nodes if n.name == "Single Pane"), None)
    assert single_pane is not None
    assert single_pane.ltree_path == "glass_type.glass_configuration.single_pane"
    assert single_pane.depth == 2
    assert single_pane.price_impact_value == Decimal("0.00")

    double_pane = next((n for n in all_nodes if n.name == "Double Pane"), None)
    assert double_pane is not None
    assert double_pane.price_impact_value == Decimal("80.00")

    low_e = next((n for n in all_nodes if n.name == "Low-E Coating"), None)
    assert low_e is not None
    assert low_e.ltree_path == "glass_type.glass_coating.low_e_coating"
    assert low_e.price_impact_value == Decimal("40.00")


@pytest.mark.asyncio
async def test_batch_creation_rollback(db_session: AsyncSession):
    """Test that batch creation rolls back on error.

    Creates a hierarchy with an invalid node in the middle and verifies
    that no nodes are created (transaction rollback).

    Requirements: 10.12
    """
    service = HierarchyBuilderService(db_session)
    repo = AttributeNodeRepository(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Store the ID before any potential rollback
    mfg_type_id = mfg_type.id

    # Define hierarchy with invalid node (missing required field)
    hierarchy_data = {
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
                        # Invalid: node_type is required but missing
                        "name": "Invalid Node",
                        "price_impact_value": Decimal("30.00"),
                    },
                ],
            },
        ],
    }

    # Attempt to create hierarchy - should fail
    try:
        await service.create_hierarchy_from_dict(
            manufacturing_type_id=mfg_type_id,
            hierarchy_data=hierarchy_data,
        )
        # If we get here, the test should fail
        assert False, "Expected exception was not raised"
    except (ValidationException, ValueError, KeyError):
        # Expected exception occurred
        pass

    # Verify no nodes were created (rollback occurred)
    # Refresh the session to ensure we see the rolled back state
    await db_session.rollback()
    all_nodes = await repo.get_by_manufacturing_type(mfg_type_id)
    assert len(all_nodes) == 0, "Transaction should have rolled back, no nodes should exist"


@pytest.mark.asyncio
async def test_batch_creation_with_invalid_parent_rollback(db_session: AsyncSession):
    """Test rollback when batch creation references non-existent parent.

    Verifies that if any node in the batch fails, the entire transaction
    is rolled back.

    Requirements: 10.12
    """
    service = HierarchyBuilderService(db_session)
    repo = AttributeNodeRepository(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # First, create a valid root node
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Root Node",
        node_type="category",
    )

    # Count nodes before failed batch operation
    nodes_before = await repo.get_by_manufacturing_type(mfg_type.id)
    count_before = len(nodes_before)

    # Try to create a node with invalid parent_node_id
    # This should fail and rollback
    with pytest.raises(NotFoundException):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="Invalid Child",
            node_type="option",
            parent_node_id=99999,  # Non-existent parent
        )

    # Verify node count hasn't changed (rollback occurred)
    nodes_after = await repo.get_by_manufacturing_type(mfg_type.id)
    count_after = len(nodes_after)

    assert count_after == count_before, "Failed node creation should not add any nodes"
    assert count_after == 1, "Should still have only the original root node"
