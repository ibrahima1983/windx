"""Basic integration tests for HierarchyBuilderService.

Tests the core functionality of Task 1: Core HierarchyBuilderService Implementation.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_create_manufacturing_type(db_session: AsyncSession):
    """Test creating a manufacturing type."""
    service = HierarchyBuilderService(db_session)

    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        description="Test window type",
        base_category="window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )

    assert mfg_type.id is not None
    assert mfg_type.name == "Test Window"
    assert mfg_type.description == "Test window type"
    assert mfg_type.base_category == "window"
    assert mfg_type.base_price == Decimal("200.00")
    assert mfg_type.base_weight == Decimal("15.00")
    assert mfg_type.is_active is True


@pytest.mark.asyncio
async def test_create_root_node(db_session: AsyncSession):
    """Test creating a root node with automatic path and depth calculation."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type first
    mfg_type = await service.create_manufacturing_type(
        name="Window Type",
        base_price=Decimal("100.00"),
    )

    # Create root node
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Material",
        node_type="category",
    )

    assert root.id is not None
    assert root.name == "Frame Material"
    assert root.node_type == "category"
    assert root.parent_node_id is None
    assert root.ltree_path == "frame_material"
    assert root.depth == 0
    assert root.manufacturing_type_id == mfg_type.id


@pytest.mark.asyncio
async def test_create_child_node(db_session: AsyncSession):
    """Test creating a child node with correct path and depth."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Door Type",
        base_price=Decimal("150.00"),
    )

    # Create root node
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",
        node_type="category",
    )

    # Create child node
    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("50.00"),
        weight_impact=Decimal("2.00"),
    )

    assert child.id is not None
    assert child.name == "Aluminum"
    assert child.node_type == "option"
    assert child.parent_node_id == root.id
    assert child.ltree_path == "material_type.aluminum"
    assert child.depth == 1
    assert child.price_impact_value == Decimal("50.00")
    assert child.weight_impact == Decimal("2.00")


@pytest.mark.asyncio
async def test_create_nested_hierarchy(db_session: AsyncSession):
    """Test creating a multi-level hierarchy."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        base_price=Decimal("200.00"),
    )

    # Level 0: Root
    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )
    assert material.ltree_path == "material"
    assert material.depth == 0

    # Level 1: Child of root
    upvc = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="uPVC",
        node_type="category",
        parent_node_id=material.id,
    )
    assert upvc.ltree_path == "material.upvc"
    assert upvc.depth == 1

    # Level 2: Grandchild
    system = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="System",
        node_type="category",
        parent_node_id=upvc.id,
    )
    assert system.ltree_path == "material.upvc.system"
    assert system.depth == 2

    # Level 3: Great-grandchild
    aluplast = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluplast",
        node_type="option",
        parent_node_id=system.id,
    )
    assert aluplast.ltree_path == "material.upvc.system.aluplast"
    assert aluplast.depth == 3


@pytest.mark.asyncio
async def test_ltree_path_sanitization(db_session: AsyncSession):
    """Test that node names are properly sanitized for LTREE paths."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Type",
        base_price=Decimal("100.00"),
    )

    # Test space replacement
    node1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Material",
        node_type="category",
    )
    assert node1.ltree_path == "frame_material"

    # Test & replacement
    node2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum & Steel",
        node_type="option",
        parent_node_id=node1.id,
    )
    assert node2.ltree_path == "frame_material.aluminum_and_steel"

    # Test special character removal (hyphens become underscores, parentheses removed)
    node3 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Premium (High-End)",
        node_type="option",
        parent_node_id=node1.id,
    )
    assert node3.ltree_path == "frame_material.premium_high_end"


@pytest.mark.asyncio
async def test_create_node_with_invalid_parent_raises_exception(db_session: AsyncSession):
    """Test that creating a node with non-existent parent raises NotFoundException."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Type",
        base_price=Decimal("100.00"),
    )

    # Try to create node with invalid parent_node_id
    with pytest.raises(NotFoundException) as exc_info:
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="Test Node",
            node_type="option",
            parent_node_id=99999,  # Non-existent parent
        )

    assert "Parent node with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_node_with_all_parameters(db_session: AsyncSession):
    """Test creating a node with all optional parameters."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Full Test Type",
        base_price=Decimal("100.00"),
    )

    # Create node with all parameters
    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Complete Node",
        node_type="option",
        data_type="string",
        display_condition={"operator": "equals", "field": "parent.selected", "value": "custom"},
        validation_rules={"rule_type": "required", "message": "This field is required"},
        required=True,
        price_impact_type="fixed",
        price_impact_value=Decimal("75.50"),
        price_formula=None,
        weight_impact=Decimal("3.25"),
        weight_formula=None,
        technical_property_type="u_value",
        technical_impact_formula="base_u_value + 0.1",
        sort_order=5,
        ui_component="dropdown",
        description="Test description",
        help_text="Test help text",
    )

    assert node.id is not None
    assert node.name == "Complete Node"
    assert node.node_type == "option"
    assert node.data_type == "string"
    assert node.display_condition == {
        "operator": "equals",
        "field": "parent.selected",
        "value": "custom",
    }
    assert node.validation_rules == {"rule_type": "required", "message": "This field is required"}
    assert node.required is True
    assert node.price_impact_type == "fixed"
    assert node.price_impact_value == Decimal("75.50")
    assert node.weight_impact == Decimal("3.25")
    assert node.technical_property_type == "u_value"
    assert node.technical_impact_formula == "base_u_value + 0.1"
    assert node.sort_order == 5
    assert node.ui_component == "dropdown"
    assert node.description == "Test description"
    assert node.help_text == "Test help text"
