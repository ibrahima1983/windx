"""Pydantic schemas for AttributeNode model."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CalculatedFieldMetadata(TypedDict, total=False):
    """Metadata for auto-calculated fields.
    
    Attributes:
        type: Calculation type (multiply, divide, add, subtract, formula)
        operands: List of field names to use in calculation (order matters for divide/subtract)
        trigger_on: List of field names that trigger recalculation when changed
        precision: Decimal places for rounding (default: 2)
    """
    type: Literal["multiply", "divide", "add", "subtract", "formula"]
    operands: list[str]
    trigger_on: list[str]
    precision: int


class DisplayCondition(BaseModel):
    """Conditional display logic for attribute nodes."""

    operator: Annotated[
        str,
        Field(
            description="Operator: equals, not_equals, greater_than, less_than, greater_equal, less_equal, contains, starts_with, ends_with, matches_pattern, in, not_in, any_of, all_of, exists, not_exists, is_empty, is_not_empty, and, or, not"
        ),
    ]
    field: Annotated[str | None, Field(default=None, description="Field to check")]
    value: Annotated[Any | None, Field(default=None, description="Value to compare")]
    conditions: Annotated[
        list[DisplayCondition] | None, Field(default=None, description="Nested conditions")
    ]

    model_config = ConfigDict(from_attributes=True)


class ValidationRule(BaseModel):
    """Validation rule definition for attribute inputs."""

    rule_type: Annotated[
        str, Field(description="Type: required, min, max, range, pattern, custom, length")
    ]
    value: Annotated[Any | None, Field(default=None, description="Rule value")]
    min: Annotated[float | None, Field(default=None, description="Minimum value for range")]
    max: Annotated[float | None, Field(default=None, description="Maximum value for range")]
    pattern: Annotated[str | None, Field(default=None, description="Regex pattern for validation")]
    message: Annotated[str, Field(description="Error message to display")]

    model_config = ConfigDict(from_attributes=True)


class AttributeNodeBase(BaseModel):
    """Base schema for AttributeNode with common fields."""

    name: Annotated[
        str, Field(min_length=1, max_length=200, description="Display name of the attribute")
    ]
    node_type: Annotated[
        str, Field(description="Node type: category, attribute, option, component, technical_spec")
    ]
    data_type: Annotated[
        str | None,
        Field(
            default=None,
            description="Data type: string, number, boolean, formula, dimension, selection",
        ),
    ]
    display_condition: Annotated[
        dict | None, Field(default=None, description="Conditional display logic (JSONB)")
    ]
    validation_rules: Annotated[
        dict | None, Field(default=None, description="Input validation rules (JSONB)")
    ]
    required: Annotated[
        bool, Field(default=False, description="Whether this attribute must be selected")
    ]
    price_impact_type: Annotated[
        str, Field(default="fixed", description="How it affects price: fixed, percentage, formula")
    ]
    price_impact_value: Annotated[
        Decimal | None,
        Field(default=None, ge=0, decimal_places=2, description="Fixed price adjustment amount"),
    ]
    price_formula: Annotated[
        str | None, Field(default=None, description="Dynamic price calculation formula")
    ]
    weight_impact: Annotated[
        Decimal,
        Field(
            default=Decimal("0"),
            ge=0,
            decimal_places=2,
            description="Fixed weight addition in grams",
        ),
    ]
    weight_formula: Annotated[
        str | None, Field(default=None, description="Dynamic weight calculation formula")
    ]
    technical_property_type: Annotated[
        str | None, Field(default=None, max_length=50, description="Type of technical property")
    ]
    technical_impact_formula: Annotated[
        str | None, Field(default=None, description="Technical calculation formula")
    ]
    calculated_field: Annotated[
        CalculatedFieldMetadata | None,
        Field(
            default=None,
            description="Calculation metadata for auto-calculated fields",
            examples=[{
                "type": "multiply",
                "operands": ["price_per_meter", "length_of_beam"],
                "trigger_on": ["price_per_meter", "length_of_beam"],
                "precision": 2
            }]
        )
    ] = None
    sort_order: Annotated[int, Field(default=0, description="Display order among siblings")]
    ui_component: Annotated[
        str | None, Field(default=None, max_length=50, description="UI control type")
    ]
    description: Annotated[str | None, Field(default=None, description="Help text for users")]
    help_text: Annotated[
        str | None, Field(default=None, description="Additional guidance for users")
    ]

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        """Validate node_type is one of the allowed values."""
        allowed = {"category", "attribute", "option", "component", "technical_spec"}
        if v not in allowed:
            raise ValueError(f"node_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str | None) -> str | None:
        """Validate data_type is one of the allowed values."""
        if v is None:
            return v
        allowed = {"string", "number", "boolean", "formula", "dimension", "selection"}
        if v not in allowed:
            raise ValueError(f"data_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("price_impact_type")
    @classmethod
    def validate_price_impact_type(cls, v: str) -> str:
        """Validate price_impact_type is one of the allowed values."""
        allowed = {"fixed", "percentage", "formula"}
        if v not in allowed:
            raise ValueError(f"price_impact_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("price_formula", "weight_formula", "technical_impact_formula")
    @classmethod
    def validate_formula_syntax(cls, v: str | None) -> str | None:
        """Validate formula syntax is safe and well-formed."""
        if v is None or v.strip() == "":
            return v

        # Check for dangerous operations
        dangerous_patterns = [
            r"__",  # Dunder methods
            r"import\s",  # Import statements
            r"exec\s*\(",  # Exec function
            r"eval\s*\(",  # Eval function
            r"compile\s*\(",  # Compile function
            r"open\s*\(",  # File operations
            r"os\.",  # OS module
            r"sys\.",  # Sys module
            r"subprocess",  # Subprocess module
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Formula contains forbidden operation: {pattern}")

        # Check for balanced parentheses
        if v.count("(") != v.count(")"):
            raise ValueError("Formula has unbalanced parentheses")

        # Check for valid characters (alphanumeric, operators, parentheses, dots, underscores)
        if not re.match(r"^[a-zA-Z0-9_\s\+\-\*\/\(\)\.\,\>\<\=\&\|\!]+$", v):
            raise ValueError("Formula contains invalid characters")

        return v


class AttributeNodeCreate(AttributeNodeBase):
    """Schema for creating a new AttributeNode."""

    manufacturing_type_id: Annotated[
        int | None,
        Field(default=None, gt=0, description="Manufacturing type ID (null for root nodes)"),
    ]
    parent_node_id: Annotated[
        int | None, Field(default=None, gt=0, description="Parent node ID (null for root nodes)")
    ]


class AttributeNodeUpdate(BaseModel):
    """Schema for updating an AttributeNode."""

    name: Annotated[str | None, Field(default=None, max_length=200)]
    node_type: Annotated[str | None, Field(default=None)]
    data_type: Annotated[str | None, Field(default=None)]
    display_condition: Annotated[dict | None, Field(default=None)]
    validation_rules: Annotated[dict | None, Field(default=None)]
    required: Annotated[bool | None, Field(default=None)]
    price_impact_type: Annotated[str | None, Field(default=None)]
    price_impact_value: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=2)]
    price_formula: Annotated[str | None, Field(default=None)]
    weight_impact: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=2)]
    weight_formula: Annotated[str | None, Field(default=None)]
    technical_property_type: Annotated[str | None, Field(default=None, max_length=50)]
    technical_impact_formula: Annotated[str | None, Field(default=None)]
    parent_node_id: Annotated[int | None, Field(default=None, gt=0)]
    sort_order: Annotated[int | None, Field(default=None)]
    ui_component: Annotated[str | None, Field(default=None, max_length=50)]
    description: Annotated[str | None, Field(default=None)]
    help_text: Annotated[str | None, Field(default=None)]

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, v: str | None) -> str | None:
        """Validate node_type is one of the allowed values."""
        if v is None:
            return v
        allowed = {"category", "attribute", "option", "component", "technical_spec"}
        if v not in allowed:
            raise ValueError(f"node_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str | None) -> str | None:
        """Validate data_type is one of the allowed values."""
        if v is None:
            return v
        allowed = {"string", "number", "boolean", "formula", "dimension", "selection"}
        if v not in allowed:
            raise ValueError(f"data_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("price_impact_type")
    @classmethod
    def validate_price_impact_type(cls, v: str | None) -> str | None:
        """Validate price_impact_type is one of the allowed values."""
        if v is None:
            return v
        allowed = {"fixed", "percentage", "formula"}
        if v not in allowed:
            raise ValueError(f"price_impact_type must be one of {allowed}, got '{v}'")
        return v


class AttributeNode(AttributeNodeBase):
    """Schema for AttributeNode response."""

    id: Annotated[int, Field(gt=0, description="Attribute node ID")]
    manufacturing_type_id: Annotated[
        int | None, Field(default=None, description="Manufacturing type ID")
    ]
    parent_node_id: Annotated[int | None, Field(default=None, description="Parent node ID")]
    ltree_path: Annotated[str, Field(description="Hierarchical path (LTREE)")]
    depth: Annotated[int, Field(ge=0, description="Nesting level in the tree")]
    created_at: Annotated[datetime, Field(description="Creation timestamp")]
    updated_at: Annotated[datetime, Field(description="Last update timestamp")]

    @field_validator("ltree_path")
    @classmethod
    def validate_ltree_path(cls, v: str) -> str:
        """Validate ltree_path format.

        LTREE paths must consist of labels separated by dots.
        Each label must be alphanumeric with underscores, max 256 chars per label.
        """
        if not v or v.strip() == "":
            raise ValueError("ltree_path cannot be empty")

        # Split by dots
        labels = v.split(".")

        # Validate each label
        for label in labels:
            if not label:
                raise ValueError("ltree_path cannot have empty labels")

            if len(label) > 256:
                raise ValueError(f"ltree_path label '{label}' exceeds 256 characters")

            # Labels must be alphanumeric with underscores
            if not re.match(r"^[a-zA-Z0-9_]+$", label):
                raise ValueError(
                    f"ltree_path label '{label}' contains invalid characters (only alphanumeric and underscore allowed)"
                )

        return v

    model_config = ConfigDict(from_attributes=True)


class AttributeNodeTree(AttributeNode):
    """Schema for AttributeNode with children for tree representation."""

    children: Annotated[
        list[AttributeNodeTree],
        Field(default_factory=list, description="Child nodes in the hierarchy"),
    ]

    model_config = ConfigDict(from_attributes=True)


class AttributeNodeWithParent(AttributeNode):
    """Schema for AttributeNode with parent information."""

    parent: Annotated[
        AttributeNode | None, Field(default=None, description="Parent node information")
    ]

    model_config = ConfigDict(from_attributes=True)
