"""Integration tests for ASCII tree visualization in HierarchyBuilderService.

Tests the asciify() method and _generate_ascii_tree_recursive() helper
to ensure proper ASCII tree generation with box-drawing characters.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_asciify_simple_hierarchy(db_session: AsyncSession):
    """Test ASCII tree generation for a simple hierarchy."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
        base_weight=Decimal("10.00"),
    )

    # Create simple hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame Material",
        node_type="category",
    )

    child1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("50.00"),
    )

    child2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Vinyl",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("30.00"),
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify structure
    assert "Frame Material [category]" in tree_str
    assert "├── Aluminum [option] [+$50.00]" in tree_str
    assert "└── Vinyl [option] [+$30.00]" in tree_str

    # Verify box-drawing characters are used
    assert "├──" in tree_str
    assert "└──" in tree_str


@pytest.mark.asyncio
async def test_asciify_nested_hierarchy(db_session: AsyncSession):
    """Test ASCII tree generation for a nested hierarchy."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create nested hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )

    upvc = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="uPVC",
        node_type="category",
        parent_node_id=root.id,
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
        price_impact_value=Decimal("75.00"),
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify nested structure with proper indentation
    assert "Material [category]" in tree_str
    assert "└── uPVC [category]" in tree_str
    assert "    └── System [category]" in tree_str
    assert "        └── Aluplast [option] [+$75.00]" in tree_str

    # Verify vertical bars for continuation
    assert "│" in tree_str or "    " in tree_str  # Either vertical bar or spaces


@pytest.mark.asyncio
async def test_asciify_multiple_branches(db_session: AsyncSession):
    """Test ASCII tree with multiple branches at same level."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create hierarchy with multiple branches
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Options",
        node_type="category",
    )

    # First branch
    branch1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Frame",
        node_type="category",
        parent_node_id=root.id,
    )

    frame_child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Aluminum Frame",
        node_type="option",
        parent_node_id=branch1.id,
        price_impact_value=Decimal("50.00"),
    )

    # Second branch
    branch2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Glass",
        node_type="category",
        parent_node_id=root.id,
    )

    glass_child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Double Pane",
        node_type="option",
        parent_node_id=branch2.id,
        price_impact_value=Decimal("80.00"),
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify both branches are shown
    assert "Options [category]" in tree_str
    assert "Frame [category]" in tree_str
    assert "Glass [category]" in tree_str
    assert "Aluminum Frame [option] [+$50.00]" in tree_str
    assert "Double Pane [option] [+$80.00]" in tree_str

    # Verify proper connectors (├── for non-last, └── for last)
    assert "├──" in tree_str
    assert "└──" in tree_str


@pytest.mark.asyncio
async def test_asciify_with_zero_price(db_session: AsyncSession):
    """Test that nodes with zero price don't show price indicator."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create node with zero price
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Free Option",
        node_type="option",
        price_impact_value=Decimal("0.00"),
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify no price indicator for zero price
    assert "Free Option [option]" in tree_str
    assert "[+$0.00]" not in tree_str


@pytest.mark.asyncio
async def test_asciify_with_no_price(db_session: AsyncSession):
    """Test that nodes without price don't show price indicator."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create node without price
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Category Node",
        node_type="category",
        price_impact_value=None,
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify no price indicator
    assert "Category Node [category]" in tree_str
    assert "[+$" not in tree_str


@pytest.mark.asyncio
async def test_asciify_price_formatting(db_session: AsyncSession):
    """Test that prices are formatted with 2 decimal places."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create nodes with various price formats
    node1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Exact Price",
        node_type="option",
        price_impact_value=Decimal("50.00"),
    )

    node2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Decimal Price",
        node_type="option",
        price_impact_value=Decimal("75.50"),
    )

    node3 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Cents Price",
        node_type="option",
        price_impact_value=Decimal("99.99"),
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify all prices are formatted with 2 decimal places
    assert "[+$50.00]" in tree_str
    assert "[+$75.50]" in tree_str
    assert "[+$99.99]" in tree_str


@pytest.mark.asyncio
async def test_asciify_node_type_indicators(db_session: AsyncSession):
    """Test that all node types are shown with proper indicators."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create nodes of different types
    category = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Category Node",
        node_type="category",
    )

    attribute = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Attribute Node",
        node_type="attribute",
        parent_node_id=category.id,
    )

    option = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Option Node",
        node_type="option",
        parent_node_id=attribute.id,
    )

    component = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Component Node",
        node_type="component",
        parent_node_id=category.id,
    )

    technical = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Technical Node",
        node_type="technical_spec",
        parent_node_id=category.id,
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify all node types are shown
    assert "[category]" in tree_str
    assert "[attribute]" in tree_str
    assert "[option]" in tree_str
    assert "[component]" in tree_str
    assert "[technical_spec]" in tree_str


@pytest.mark.asyncio
async def test_asciify_empty_tree(db_session: AsyncSession):
    """Test ASCII tree generation for empty tree."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type with no nodes
    mfg_type = await service.create_manufacturing_type(
        name="Empty Window",
        base_price=Decimal("100.00"),
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify empty tree message
    assert tree_str == "(Empty tree)"


@pytest.mark.asyncio
async def test_asciify_subtree(db_session: AsyncSession):
    """Test ASCII tree generation for a subtree."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Create hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Root",
        node_type="category",
    )

    branch = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Branch",
        node_type="category",
        parent_node_id=root.id,
    )

    leaf1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Leaf 1",
        node_type="option",
        parent_node_id=branch.id,
    )

    leaf2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Leaf 2",
        node_type="option",
        parent_node_id=branch.id,
    )

    # Generate ASCII tree for subtree starting at branch
    tree_str = await service.asciify(
        manufacturing_type_id=mfg_type.id,
        root_node_id=branch.id,
    )

    # Verify only subtree is shown
    assert "Branch [category]" in tree_str
    assert "Leaf 1 [option]" in tree_str
    assert "Leaf 2 [option]" in tree_str
    assert "Root [category]" not in tree_str


@pytest.mark.asyncio
async def test_asciify_invalid_manufacturing_type(db_session: AsyncSession):
    """Test that asciify raises NotFoundException for invalid manufacturing type."""
    service = HierarchyBuilderService(db_session)

    # Try to generate tree for non-existent manufacturing type
    with pytest.raises(NotFoundException) as exc_info:
        await service.asciify(manufacturing_type_id=99999)

    assert "Manufacturing type with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_asciify_invalid_root_node(db_session: AsyncSession):
    """Test that asciify raises NotFoundException for invalid root node."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("100.00"),
    )

    # Try to generate tree for non-existent root node
    with pytest.raises(NotFoundException) as exc_info:
        await service.asciify(
            manufacturing_type_id=mfg_type.id,
            root_node_id=99999,
        )

    assert "Root node with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_asciify_complex_upvc_hierarchy(db_session: AsyncSession):
    """Test ASCII tree generation for complex uPVC hierarchy from requirements."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Casement Window",
        base_price=Decimal("200.00"),
    )

    # Create complex hierarchy from requirements example
    hierarchy = {
        "name": "Material",
        "node_type": "category",
        "children": [
            {
                "name": "uPVC",
                "node_type": "category",
                "children": [
                    {
                        "name": "System",
                        "node_type": "category",
                        "children": [
                            {
                                "name": "Aluplast",
                                "node_type": "option",
                                "children": [
                                    {
                                        "name": "Profile",
                                        "node_type": "attribute",
                                        "children": [
                                            {
                                                "name": "IDEAL 4000",
                                                "node_type": "option",
                                                "price_impact_value": Decimal("50.00"),
                                                "children": [
                                                    {
                                                        "name": "Color & Decor",
                                                        "node_type": "attribute",
                                                        "children": [
                                                            {
                                                                "name": "Standard colors",
                                                                "node_type": "option",
                                                                "price_impact_value": Decimal(
                                                                    "0.00"
                                                                ),
                                                            },
                                                            {
                                                                "name": "Special colors",
                                                                "node_type": "option",
                                                                "price_impact_value": Decimal(
                                                                    "25.00"
                                                                ),
                                                            },
                                                        ],
                                                    }
                                                ],
                                            },
                                            {
                                                "name": "IDEAL 5000",
                                                "node_type": "option",
                                                "price_impact_value": Decimal("75.00"),
                                            },
                                        ],
                                    }
                                ],
                            },
                            {
                                "name": "Kommerling",
                                "node_type": "option",
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Aluminium",
                "node_type": "category",
            },
        ],
    }

    await service.create_hierarchy_from_dict(
        manufacturing_type_id=mfg_type.id,
        hierarchy_data=hierarchy,
    )

    # Generate ASCII tree
    tree_str = await service.asciify(manufacturing_type_id=mfg_type.id)

    # Verify key elements are present
    assert "Material [category]" in tree_str
    assert "uPVC [category]" in tree_str
    assert "System [category]" in tree_str
    assert "Aluplast [option]" in tree_str
    assert "Profile [attribute]" in tree_str
    assert "IDEAL 4000 [option] [+$50.00]" in tree_str
    assert "Color & Decor [attribute]" in tree_str
    assert "Standard colors [option]" in tree_str
    assert "Special colors [option] [+$25.00]" in tree_str
    assert "IDEAL 5000 [option] [+$75.00]" in tree_str
    assert "Kommerling [option]" in tree_str
    assert "Aluminium [category]" in tree_str

    # Verify proper nesting with box-drawing characters
    assert "├──" in tree_str
    assert "└──" in tree_str
    assert "│" in tree_str

    # Print for visual inspection (optional)
    print("\n" + tree_str)
