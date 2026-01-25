"""Unit tests for AttributeNode model."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType

# Tests now run with PostgreSQL (asyncpg) which supports LTREE and JSONB


@pytest.mark.asyncio
async def test_attribute_node_creation(db_session: AsyncSession):
    """Test creating an AttributeNode with all required fields."""
    # Create a manufacturing type first
    mfg_type = ManufacturingType(
        name="Test Window",
        description="Test window type",
        base_price=Decimal("200.00"),
        base_weight=Decimal("15.00"),
    )
    db_session.add(mfg_type)
    await db_session.flush()

    # Create an attribute node
    node = AttributeNode(
        manufacturing_type_id=mfg_type.id,
        name="Frame Material",
        node_type="attribute",
        data_type="string",
        ltree_path="window.frame.material",
        depth=3,
        price_impact_type="fixed",
        price_impact_value=Decimal("50.00"),
        weight_impact=Decimal("2.00"),
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    # Verify the node was created
    assert node.id is not None
    assert node.name == "Frame Material"
    assert node.node_type == "attribute"
    assert node.data_type == "string"
    assert node.ltree_path == "window.frame.material"
    assert node.depth == 3
    assert node.price_impact_type == "fixed"
    assert node.price_impact_value == Decimal("50.00")
    assert node.weight_impact == Decimal("2.00")
    assert node.manufacturing_type_id == mfg_type.id


@pytest.mark.asyncio
async def test_attribute_node_hierarchy(db_session: AsyncSession):
    """Test parent-child relationships in AttributeNode."""
    # Create a manufacturing type
    mfg_type = ManufacturingType(
        name="Test Door",
        base_price=Decimal("300.00"),
    )
    db_session.add(mfg_type)
    await db_session.flush()

    # Create parent node
    parent = AttributeNode(
        manufacturing_type_id=mfg_type.id,
        name="Hardware",
        node_type="category",
        ltree_path="door.hardware",
        depth=2,
    )
    db_session.add(parent)
    await db_session.flush()

    # Create child node
    child = AttributeNode(
        manufacturing_type_id=mfg_type.id,
        parent_node_id=parent.id,
        name="Lock Type",
        node_type="attribute",
        data_type="string",
        ltree_path="door.hardware.lock",
        depth=3,
    )
    db_session.add(child)
    await db_session.commit()
    await db_session.refresh(parent)
    await db_session.refresh(child)

    # Verify relationships
    assert child.parent_node_id == parent.id

    # Use selectinload or await to access relationships in async context
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Reload parent with children eagerly loaded
    # noinspection PyTypeChecker
    result = await db_session.execute(
        select(AttributeNode)
        .where(AttributeNode.id == parent.id)
        .options(selectinload(AttributeNode.children))
    )
    parent_with_children = result.scalar_one()

    assert len(parent_with_children.children) == 1
    assert parent_with_children.children[0].id == child.id

    # Reload child with parent eagerly loaded
    # noinspection PyTypeChecker
    result = await db_session.execute(
        select(AttributeNode)
        .where(AttributeNode.id == child.id)
        .options(selectinload(AttributeNode.parent))
    )
    child_with_parent = result.scalar_one()

    assert child_with_parent.parent.id == parent.id


@pytest.mark.asyncio
async def test_attribute_node_jsonb_fields(db_session: AsyncSession):
    """Test JSONB fields for display_condition and validation_rules."""
    mfg_type = ManufacturingType(
        name="Test Table",
        base_price=Decimal("500.00"),
    )
    db_session.add(mfg_type)
    await db_session.flush()

    # Create node with JSONB fields
    node = AttributeNode(
        manufacturing_type_id=mfg_type.id,
        name="Custom Color",
        node_type="option",
        data_type="string",
        ltree_path="table.finish.color",
        depth=3,
        display_condition={
            "operator": "equals",
            "field": "finish_type",
            "value": "custom",
        },
        validation_rules={
            "rule_type": "pattern",
            "pattern": "^#[0-9A-Fa-f]{6}$",
            "message": "Must be a valid hex color code",
        },
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    # Verify JSONB fields
    assert node.display_condition is not None
    assert node.display_condition["operator"] == "equals"
    assert node.display_condition["field"] == "finish_type"
    assert node.display_condition["value"] == "custom"

    assert node.validation_rules is not None
    assert node.validation_rules["rule_type"] == "pattern"
    assert node.validation_rules["pattern"] == "^#[0-9A-Fa-f]{6}$"


@pytest.mark.asyncio
async def test_attribute_node_formulas(db_session: AsyncSession):
    """Test formula fields for dynamic calculations."""
    mfg_type = ManufacturingType(
        name="Test Window Formula",
        base_price=Decimal("200.00"),
    )
    db_session.add(mfg_type)
    await db_session.flush()

    # Create node with formulas
    node = AttributeNode(
        manufacturing_type_id=mfg_type.id,
        name="Window Size",
        node_type="attribute",
        data_type="dimension",
        ltree_path="window.dimensions.size",
        depth=3,
        price_impact_type="formula",
        price_formula="width * height * 0.05",
        weight_formula="width * height * 0.002",
        technical_property_type="area",
        technical_impact_formula="width * height",
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    # Verify formulas
    assert node.price_impact_type == "formula"
    assert node.price_formula == "width * height * 0.05"
    assert node.weight_formula == "width * height * 0.002"
    assert node.technical_property_type == "area"
    assert node.technical_impact_formula == "width * height"


@pytest.mark.asyncio
async def test_attribute_node_cascade_delete(db_session: AsyncSession):
    """Test cascade delete when manufacturing type is deleted."""
    # Create manufacturing type with attribute nodes
    mfg_type = ManufacturingType(
        name="Test Delete",
        base_price=Decimal("100.00"),
    )
    db_session.add(mfg_type)
    await db_session.flush()

    node = AttributeNode(
        manufacturing_type_id=mfg_type.id,
        name="Test Node",
        node_type="attribute",
        ltree_path="test.node",
        depth=2,
    )
    db_session.add(node)
    await db_session.commit()

    node_id = node.id

    # Delete manufacturing type
    await db_session.delete(mfg_type)
    await db_session.commit()

    # Verify node was cascade deleted
    from sqlalchemy import select

    result = await db_session.execute(select(AttributeNode).where(AttributeNode.id == node_id))
    deleted_node = result.scalar_one_or_none()
    assert deleted_node is None
