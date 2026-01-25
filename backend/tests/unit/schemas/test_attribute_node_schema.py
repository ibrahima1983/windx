"""Unit tests for AttributeNode schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.attribute_node import (
    AttributeNode,
    AttributeNodeCreate,
    AttributeNodeTree,
    AttributeNodeUpdate,
    DisplayCondition,
    ValidationRule,
)


def test_attribute_node_create_valid():
    """Test creating a valid AttributeNodeCreate schema."""
    data = {
        "manufacturing_type_id": 1,
        "parent_node_id": None,
        "name": "Frame Material",
        "node_type": "attribute",
        "data_type": "string",
        "price_impact_type": "fixed",
        "price_impact_value": Decimal("50.00"),
        "weight_impact": Decimal("2.00"),
    }
    schema = AttributeNodeCreate(**data)

    assert schema.name == "Frame Material"
    assert schema.node_type == "attribute"
    assert schema.data_type == "string"
    assert schema.price_impact_type == "fixed"
    assert schema.price_impact_value == Decimal("50.00")
    assert schema.weight_impact == Decimal("2.00")


def test_attribute_node_create_invalid_node_type():
    """Test that invalid node_type raises ValidationError."""
    data = {
        "name": "Test Node",
        "node_type": "invalid_type",  # Invalid
    }

    with pytest.raises(ValidationError) as exc_info:
        AttributeNodeCreate(**data)

    errors = exc_info.value.errors()
    assert any("node_type" in str(error) for error in errors)


def test_attribute_node_create_invalid_data_type():
    """Test that invalid data_type raises ValidationError."""
    data = {
        "name": "Test Node",
        "node_type": "attribute",
        "data_type": "invalid_data_type",  # Invalid
    }

    with pytest.raises(ValidationError) as exc_info:
        AttributeNodeCreate(**data)

    errors = exc_info.value.errors()
    assert any("data_type" in str(error) for error in errors)


def test_attribute_node_create_invalid_price_impact_type():
    """Test that invalid price_impact_type raises ValidationError."""
    data = {
        "name": "Test Node",
        "node_type": "option",
        "price_impact_type": "invalid_type",  # Invalid
    }

    with pytest.raises(ValidationError) as exc_info:
        AttributeNodeCreate(**data)

    errors = exc_info.value.errors()
    assert any("price_impact_type" in str(error) for error in errors)


def test_attribute_node_create_with_defaults():
    """Test AttributeNodeCreate with default values."""
    data = {
        "name": "Test Node",
        "node_type": "category",
    }
    schema = AttributeNodeCreate(**data)

    assert schema.required is False
    assert schema.price_impact_type == "fixed"
    assert schema.weight_impact == Decimal("0")
    assert schema.sort_order == 0


def test_attribute_node_update_partial():
    """Test AttributeNodeUpdate with partial data."""
    data = {
        "name": "Updated Name",
        "price_impact_value": Decimal("75.00"),
    }
    schema = AttributeNodeUpdate(**data)

    assert schema.name == "Updated Name"
    assert schema.price_impact_value == Decimal("75.00")
    assert schema.node_type is None  # Not provided


def test_attribute_node_response():
    """Test AttributeNode response schema."""
    from datetime import datetime

    data = {
        "id": 1,
        "manufacturing_type_id": 1,
        "parent_node_id": None,
        "name": "Frame Material",
        "node_type": "attribute",
        "data_type": "string",
        "display_condition": None,
        "validation_rules": None,
        "required": False,
        "price_impact_type": "fixed",
        "price_impact_value": Decimal("50.00"),
        "price_formula": None,
        "weight_impact": Decimal("2.00"),
        "weight_formula": None,
        "technical_property_type": None,
        "technical_impact_formula": None,
        "ltree_path": "window.frame.material",
        "depth": 3,
        "sort_order": 0,
        "ui_component": "dropdown",
        "description": "Select frame material",
        "help_text": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    schema = AttributeNode(**data)

    assert schema.id == 1
    assert schema.name == "Frame Material"
    assert schema.ltree_path == "window.frame.material"
    assert schema.depth == 3


def test_attribute_node_tree():
    """Test AttributeNodeTree with children."""
    from datetime import datetime

    parent_data = {
        "id": 1,
        "manufacturing_type_id": 1,
        "parent_node_id": None,
        "name": "Hardware",
        "node_type": "category",
        "data_type": None,
        "display_condition": None,
        "validation_rules": None,
        "required": False,
        "price_impact_type": "fixed",
        "price_impact_value": None,
        "price_formula": None,
        "weight_impact": Decimal("0"),
        "weight_formula": None,
        "technical_property_type": None,
        "technical_impact_formula": None,
        "ltree_path": "door.hardware",
        "depth": 2,
        "sort_order": 0,
        "ui_component": None,
        "description": None,
        "help_text": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "children": [
            {
                "id": 2,
                "manufacturing_type_id": 1,
                "parent_node_id": 1,
                "name": "Lock Type",
                "node_type": "attribute",
                "data_type": "string",
                "display_condition": None,
                "validation_rules": None,
                "required": True,
                "price_impact_type": "fixed",
                "price_impact_value": None,
                "price_formula": None,
                "weight_impact": Decimal("0"),
                "weight_formula": None,
                "technical_property_type": None,
                "technical_impact_formula": None,
                "ltree_path": "door.hardware.lock",
                "depth": 3,
                "sort_order": 0,
                "ui_component": "dropdown",
                "description": None,
                "help_text": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "children": [],
            }
        ],
    }

    schema = AttributeNodeTree(**parent_data)

    assert schema.id == 1
    assert schema.name == "Hardware"
    assert len(schema.children) == 1
    assert schema.children[0].name == "Lock Type"
    assert schema.children[0].parent_node_id == 1


def test_display_condition_simple():
    """Test DisplayCondition schema with simple condition."""
    data = {
        "operator": "equals",
        "field": "material_type",
        "value": "Wood",
    }
    schema = DisplayCondition(**data)

    assert schema.operator == "equals"
    assert schema.field == "material_type"
    assert schema.value == "Wood"
    assert schema.conditions is None


def test_display_condition_nested():
    """Test DisplayCondition schema with nested conditions."""
    data = {
        "operator": "and",
        "conditions": [
            {
                "operator": "equals",
                "field": "material_type",
                "value": "Wood",
            },
            {
                "operator": "gt",
                "field": "pane_count",
                "value": 1,
            },
        ],
    }
    schema = DisplayCondition(**data)

    assert schema.operator == "and"
    assert schema.conditions is not None
    assert len(schema.conditions) == 2
    assert schema.conditions[0].operator == "equals"
    assert schema.conditions[1].operator == "gt"


def test_validation_rule_range():
    """Test ValidationRule schema with range validation."""
    data = {
        "rule_type": "range",
        "min": 24,
        "max": 96,
        "message": "Width must be between 24 and 96 inches",
    }
    schema = ValidationRule(**data)

    assert schema.rule_type == "range"
    assert schema.min == 24
    assert schema.max == 96
    assert schema.message == "Width must be between 24 and 96 inches"


def test_validation_rule_pattern():
    """Test ValidationRule schema with pattern validation."""
    data = {
        "rule_type": "pattern",
        "pattern": "^#[0-9A-Fa-f]{6}$",
        "message": "Must be a valid hex color code",
    }
    schema = ValidationRule(**data)

    assert schema.rule_type == "pattern"
    assert schema.pattern == "^#[0-9A-Fa-f]{6}$"
    assert schema.message == "Must be a valid hex color code"


def test_attribute_node_with_jsonb_fields():
    """Test AttributeNodeCreate with JSONB fields."""
    data = {
        "name": "Custom Color",
        "node_type": "option",
        "data_type": "string",
        "display_condition": {
            "operator": "equals",
            "field": "finish_type",
            "value": "custom",
        },
        "validation_rules": {
            "rule_type": "pattern",
            "pattern": "^#[0-9A-Fa-f]{6}$",
            "message": "Must be a valid hex color code",
        },
    }
    schema = AttributeNodeCreate(**data)

    assert schema.display_condition is not None
    assert schema.display_condition["operator"] == "equals"
    assert schema.validation_rules is not None
    assert schema.validation_rules["rule_type"] == "pattern"


def test_attribute_node_with_formulas():
    """Test AttributeNodeCreate with formula fields."""
    data = {
        "name": "Window Size",
        "node_type": "attribute",
        "data_type": "dimension",
        "price_impact_type": "formula",
        "price_formula": "width * height * 0.05",
        "weight_formula": "width * height * 0.002",
        "technical_property_type": "area",
        "technical_impact_formula": "width * height",
    }
    schema = AttributeNodeCreate(**data)

    assert schema.price_impact_type == "formula"
    assert schema.price_formula == "width * height * 0.05"
    assert schema.weight_formula == "width * height * 0.002"
    assert schema.technical_property_type == "area"
    assert schema.technical_impact_formula == "width * height"
