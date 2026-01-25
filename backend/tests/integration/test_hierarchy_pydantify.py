"""Integration tests for HierarchyBuilderService.pydantify() method."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.schemas.attribute_node import AttributeNodeTree
from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_pydantify_full_tree(db_session: AsyncSession):
    """Test getting full tree as Pydantic models."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )

    # Create hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",
        node_type="attribute",
        parent_node_id=root.id,
    )

    aluminum = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=material.id,
        price_impact_value=Decimal("50.00"),
    )

    vinyl = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Vinyl",
        node_type="option",
        parent_node_id=material.id,
        price_impact_value=Decimal("30.00"),
    )

    # Get tree as Pydantic models
    tree = await service.pydantify(manufacturing_type_id=mfg_type.id)

    # Verify structure
    assert isinstance(tree, list)
    assert len(tree) == 1  # One root node

    root_node = tree[0]
    assert isinstance(root_node, AttributeNodeTree)
    assert root_node.name == "Frame Options"
    assert root_node.depth == 0
    assert root_node.ltree_path == "frame_options"

    # Verify children
    assert len(root_node.children) == 1
    material_node = root_node.children[0]
    assert material_node.name == "Material Type"
    assert material_node.depth == 1

    # Verify grandchildren
    assert len(material_node.children) == 2
    option_names = {child.name for child in material_node.children}
    assert option_names == {"Aluminum", "Vinyl"}

    # Verify price impacts
    for child in material_node.children:
        if child.name == "Aluminum":
            assert child.price_impact_value == Decimal("50.00")
        elif child.name == "Vinyl":
            assert child.price_impact_value == Decimal("30.00")


@pytest.mark.asyncio
async def test_pydantify_subtree(db_session: AsyncSession):
    """Test getting subtree starting from specific node."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",
        node_type="attribute",
        parent_node_id=root.id,
    )

    aluminum = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=material.id,
    )

    # Get subtree starting from material node
    subtree = await service.pydantify(
        manufacturing_type_id=mfg_type.id,
        root_node_id=material.id,
    )

    # Verify structure
    assert len(subtree) == 1
    material_node = subtree[0]
    assert material_node.name == "Material Type"
    assert material_node.depth == 1

    # Verify children
    assert len(material_node.children) == 1
    assert material_node.children[0].name == "Aluminum"


@pytest.mark.asyncio
async def test_pydantify_json_serialization(db_session: AsyncSession):
    """Test that Pydantic tree can be serialized to JSON."""
    import json

    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create simple hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Options",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material Type",
        node_type="attribute",
        parent_node_id=root.id,
    )

    # Get tree
    tree = await service.pydantify(manufacturing_type_id=mfg_type.id)

    # Serialize to JSON
    tree_dict = [node.model_dump() for node in tree]
    tree_json = json.dumps(tree_dict, default=str, indent=2)

    # Verify JSON is valid
    assert tree_json is not None
    assert len(tree_json) > 0

    # Parse back to verify structure
    parsed = json.loads(tree_json)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Frame Options"
    assert len(parsed[0]["children"]) == 1
    assert parsed[0]["children"][0]["name"] == "Material Type"


@pytest.mark.asyncio
async def test_pydantify_empty_tree(db_session: AsyncSession):
    """Test getting tree for manufacturing type with no nodes."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type with no nodes
    mfg_type = await service.create_manufacturing_type(
        name="Empty Type",
        base_price=Decimal("100.00"),
    )

    # Get tree
    tree = await service.pydantify(manufacturing_type_id=mfg_type.id)

    # Verify empty list
    assert isinstance(tree, list)
    assert len(tree) == 0


@pytest.mark.asyncio
async def test_pydantify_invalid_manufacturing_type(db_session: AsyncSession):
    """Test error handling for invalid manufacturing type."""
    service = HierarchyBuilderService(db_session)

    # Try to get tree for non-existent manufacturing type
    with pytest.raises(NotFoundException) as exc_info:
        await service.pydantify(manufacturing_type_id=99999)

    assert "Manufacturing type with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pydantify_invalid_root_node(db_session: AsyncSession):
    """Test error handling for invalid root node."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Try to get subtree with non-existent root node
    with pytest.raises(NotFoundException) as exc_info:
        await service.pydantify(
            manufacturing_type_id=mfg_type.id,
            root_node_id=99999,
        )

    assert "Root node with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pydantify_root_node_wrong_type(db_session: AsyncSession):
    """Test error handling when root node belongs to different manufacturing type."""
    service = HierarchyBuilderService(db_session)

    # Create two manufacturing types
    mfg_type1 = await service.create_manufacturing_type(
        name="Type 1",
        base_price=Decimal("100.00"),
    )

    mfg_type2 = await service.create_manufacturing_type(
        name="Type 2",
        base_price=Decimal("200.00"),
    )

    # Create node in type 1
    node = await service.create_node(
        manufacturing_type_id=mfg_type1.id,
        name="Test Node",
        node_type="category",
    )

    # Try to get tree for type 2 with node from type 1
    with pytest.raises(ValueError) as exc_info:
        await service.pydantify(
            manufacturing_type_id=mfg_type2.id,
            root_node_id=node.id,
        )

    assert "belongs to manufacturing type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pydantify_complex_hierarchy(db_session: AsyncSession):
    """Test pydantify with complex multi-level hierarchy."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Complex Window",
        base_price=Decimal("200.00"),
    )

    # Create complex hierarchy
    # Level 0: Root
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Window Configuration",
        node_type="category",
    )

    # Level 1: Categories
    frame = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame",
        node_type="category",
        parent_node_id=root.id,
    )

    glass = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Glass",
        node_type="category",
        parent_node_id=root.id,
    )

    # Level 2: Attributes
    frame_material = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="attribute",
        parent_node_id=frame.id,
    )

    glass_type = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Type",
        node_type="attribute",
        parent_node_id=glass.id,
    )

    # Level 3: Options
    await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=frame_material.id,
        price_impact_value=Decimal("50.00"),
    )

    await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Double Pane",
        node_type="option",
        parent_node_id=glass_type.id,
        price_impact_value=Decimal("80.00"),
    )

    # Get tree
    tree = await service.pydantify(manufacturing_type_id=mfg_type.id)

    # Verify structure
    assert len(tree) == 1
    root_node = tree[0]
    assert root_node.name == "Window Configuration"
    assert len(root_node.children) == 2

    # Verify categories
    category_names = {child.name for child in root_node.children}
    assert category_names == {"Frame", "Glass"}

    # Verify attributes and options
    for category in root_node.children:
        assert len(category.children) == 1
        attribute = category.children[0]
        assert len(attribute.children) == 1
        option = attribute.children[0]

        if category.name == "Frame":
            assert attribute.name == "Material"
            assert option.name == "Aluminum"
            assert option.price_impact_value == Decimal("50.00")
        elif category.name == "Glass":
            assert attribute.name == "Type"
            assert option.name == "Double Pane"
            assert option.price_impact_value == Decimal("80.00")


@pytest.mark.asyncio
async def test_pydantify_preserves_all_fields(db_session: AsyncSession):
    """Test that pydantify preserves all node fields."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Create node with all fields populated
    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Test Node",
        node_type="option",
        data_type="string",
        display_condition={"operator": "equals", "field": "test", "value": "value"},
        validation_rules={"rule_type": "required", "message": "Required field"},
        required=True,
        price_impact_type="fixed",
        price_impact_value=Decimal("50.00"),
        price_formula="base * 1.5",
        weight_impact=Decimal("2.50"),
        weight_formula="width * height * 0.01",
        technical_property_type="u_value",
        technical_impact_formula="1 / r_value",
        sort_order=5,
        ui_component="dropdown",
        description="Test description",
        help_text="Test help text",
    )

    # Get tree
    tree = await service.pydantify(manufacturing_type_id=mfg_type.id)

    # Verify all fields are preserved
    assert len(tree) == 1
    pydantic_node = tree[0]

    assert pydantic_node.id == node.id
    assert pydantic_node.name == "Test Node"
    assert pydantic_node.node_type == "option"
    assert pydantic_node.data_type == "string"
    assert pydantic_node.display_condition == {
        "operator": "equals",
        "field": "test",
        "value": "value",
    }
    assert pydantic_node.validation_rules == {"rule_type": "required", "message": "Required field"}
    assert pydantic_node.required is True
    assert pydantic_node.price_impact_type == "fixed"
    assert pydantic_node.price_impact_value == Decimal("50.00")
    assert pydantic_node.price_formula == "base * 1.5"
    assert pydantic_node.weight_impact == Decimal("2.50")
    assert pydantic_node.weight_formula == "width * height * 0.01"
    assert pydantic_node.technical_property_type == "u_value"
    assert pydantic_node.technical_impact_formula == "1 / r_value"
    assert pydantic_node.sort_order == 5
    assert pydantic_node.ui_component == "dropdown"
    assert pydantic_node.description == "Test description"
    assert pydantic_node.help_text == "Test help text"
    assert pydantic_node.ltree_path == "test_node"
    assert pydantic_node.depth == 0
    assert pydantic_node.created_at is not None
    assert pydantic_node.updated_at is not None
