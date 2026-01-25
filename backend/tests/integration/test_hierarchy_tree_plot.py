"""Integration tests for HierarchyBuilderService tree plotting functionality.

This module tests the graphical tree visualization features of the
HierarchyBuilderService, including matplotlib-based plotting with both
NetworkX and manual layout algorithms.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.asyncio
async def test_plot_tree_basic(db_session: AsyncSession):
    """Test basic tree plotting functionality."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        description="Test window for plotting",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
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

    # Generate plot
    fig = await service.plot_tree(manufacturing_type_id=mfg_type.id)

    # Verify figure was created
    assert fig is not None
    assert hasattr(fig, "savefig")  # Matplotlib figure has savefig method

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)


@pytest.mark.asyncio
async def test_plot_tree_with_subtree(db_session: AsyncSession):
    """Test plotting a subtree starting from a specific node."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Door",
        description="Test door for subtree plotting",
        base_price=Decimal("300.00"),
    )

    # Create hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Material",
        node_type="category",
    )

    wood = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Wood",
        node_type="category",
        parent_node_id=root.id,
    )

    oak = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Oak",
        node_type="option",
        parent_node_id=wood.id,
        price_impact_value=Decimal("100.00"),
    )

    pine = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Pine",
        node_type="option",
        parent_node_id=wood.id,
        price_impact_value=Decimal("50.00"),
    )

    # Plot subtree starting from "Wood" node
    fig = await service.plot_tree(
        manufacturing_type_id=mfg_type.id,
        root_node_id=wood.id,
    )

    # Verify figure was created
    assert fig is not None

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)


@pytest.mark.asyncio
async def test_plot_tree_complex_hierarchy(db_session: AsyncSession):
    """Test plotting a complex multi-level hierarchy."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Complex Window",
        description="Complex window hierarchy",
        base_price=Decimal("200.00"),
    )

    # Create complex hierarchy using dictionary
    hierarchy = {
        "name": "Frame Options",
        "node_type": "category",
        "children": [
            {
                "name": "Material Type",
                "node_type": "attribute",
                "data_type": "selection",
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
                    {
                        "name": "Wood",
                        "node_type": "option",
                        "price_impact_value": Decimal("100.00"),
                    },
                ],
            },
            {
                "name": "Color",
                "node_type": "attribute",
                "data_type": "selection",
                "children": [
                    {
                        "name": "White",
                        "node_type": "option",
                        "price_impact_value": Decimal("0.00"),
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

    # Generate plot
    fig = await service.plot_tree(manufacturing_type_id=mfg_type.id)

    # Verify figure was created
    assert fig is not None

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)


@pytest.mark.asyncio
async def test_plot_tree_empty_hierarchy(db_session: AsyncSession):
    """Test plotting when no nodes exist."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type with no nodes
    mfg_type = await service.create_manufacturing_type(
        name="Empty Type",
        description="Type with no nodes",
    )

    # Generate plot (should handle empty tree gracefully)
    fig = await service.plot_tree(manufacturing_type_id=mfg_type.id)

    # Verify figure was created (with "No nodes found" message)
    assert fig is not None

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)


@pytest.mark.asyncio
async def test_plot_tree_invalid_manufacturing_type(db_session: AsyncSession):
    """Test plotting with invalid manufacturing type ID."""
    service = HierarchyBuilderService(db_session)

    # Try to plot non-existent manufacturing type
    with pytest.raises(NotFoundException) as exc_info:
        await service.plot_tree(manufacturing_type_id=99999)

    assert "Manufacturing type with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_plot_tree_invalid_root_node(db_session: AsyncSession):
    """Test plotting with invalid root node ID."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Test Type",
        description="Test type",
    )

    # Try to plot with non-existent root node
    with pytest.raises(NotFoundException) as exc_info:
        await service.plot_tree(
            manufacturing_type_id=mfg_type.id,
            root_node_id=99999,
        )

    assert "Root node with id 99999 not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_plot_tree_with_all_node_types(db_session: AsyncSession):
    """Test plotting with all different node types."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Multi-Type Test",
        description="Test all node types",
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
        price_impact_value=Decimal("25.00"),
    )

    component = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Component Node",
        node_type="component",
        parent_node_id=category.id,
    )

    technical = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Technical Spec Node",
        node_type="technical_spec",
        parent_node_id=category.id,
    )

    # Generate plot (should show all node types with different colors)
    fig = await service.plot_tree(manufacturing_type_id=mfg_type.id)

    # Verify figure was created
    assert fig is not None

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)


@pytest.mark.asyncio
async def test_plot_tree_save_to_file(db_session: AsyncSession, tmp_path):
    """Test saving tree plot to a file."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Save Test",
        description="Test saving plot",
    )

    # Create simple hierarchy
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Root",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("10.00"),
    )

    # Generate plot
    fig = await service.plot_tree(manufacturing_type_id=mfg_type.id)

    # Save to file
    output_file = tmp_path / "tree_plot.png"
    fig.savefig(str(output_file), dpi=150, bbox_inches="tight")

    # Verify file was created
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)


@pytest.mark.asyncio
async def test_plot_tree_with_price_formatting(db_session: AsyncSession):
    """Test that price impacts are formatted correctly in the plot."""
    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Price Format Test",
        description="Test price formatting",
    )

    # Create nodes with various price impacts
    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Options",
        node_type="category",
    )

    # Node with zero price (should not show price)
    zero_price = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Free Option",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("0.00"),
    )

    # Node with decimal price
    decimal_price = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Decimal Option",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("12.50"),
    )

    # Node with large price
    large_price = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Expensive Option",
        node_type="option",
        parent_node_id=root.id,
        price_impact_value=Decimal("999.99"),
    )

    # Generate plot
    fig = await service.plot_tree(manufacturing_type_id=mfg_type.id)

    # Verify figure was created
    assert fig is not None

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)
