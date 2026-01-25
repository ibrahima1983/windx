"""ConfigurationSelection Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for ConfigurationSelection data
validation, serialization, and API request/response handling.

Public Classes:
    ConfigurationSelectionValue: Flexible value container for selections
    ConfigurationSelectionBase: Base schema with common attributes
    ConfigurationSelectionCreate: Schema for creating selections
    ConfigurationSelectionUpdate: Schema for updating selections
    ConfigurationSelection: Schema for API responses

Features:
    - Flexible value storage (string, numeric, boolean, JSON)
    - Calculated impacts (price, weight, technical)
    - Type-safe with Annotated types
    - Automatic ORM conversion support
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

__all__ = [
    "ConfigurationSelectionValue",
    "ConfigurationSelectionBase",
    "ConfigurationSelectionCreate",
    "ConfigurationSelectionUpdate",
    "ConfigurationSelection",
]


class ConfigurationSelectionValue(BaseModel):
    """Flexible value container for selections.

    Only one value field should be populated based on the attribute's data type.

    Attributes:
        attribute_node_id: Attribute node ID
        string_value: Text selections (materials, colors)
        numeric_value: Numerical inputs (dimensions, quantities)
        boolean_value: True/false choices (features)
        json_value: Complex structured data
    """

    attribute_node_id: Annotated[
        PositiveInt,
        Field(
            description="Attribute node ID",
            examples=[42, 123],
        ),
    ]
    string_value: Annotated[
        str | None,
        Field(
            default=None,
            description="Text selections (materials, colors, etc.)",
            examples=["Aluminum", "White", "Premium"],
        ),
    ] = None
    numeric_value: Annotated[
        Decimal | None,
        Field(
            default=None,
            description="Numerical inputs (dimensions, quantities, etc.)",
            examples=[48.5, 60.0, 100.25],
        ),
    ] = None
    boolean_value: Annotated[
        bool | None,
        Field(
            default=None,
            description="True/false choices (features enabled/disabled)",
            examples=[True, False],
        ),
    ] = None
    json_value: Annotated[
        dict | None,
        Field(
            default=None,
            description="Complex structured data (multiple properties)",
            examples=[{"color": "white", "finish": "matte"}],
        ),
    ] = None


class ConfigurationSelectionBase(BaseModel):
    """Base configuration selection schema with common attributes.

    Attributes:
        string_value: Text selections
        numeric_value: Numerical inputs
        boolean_value: True/false choices
        json_value: Complex structured data
    """

    string_value: Annotated[
        str | None,
        Field(
            default=None,
            description="Text selections (materials, colors, etc.)",
        ),
    ] = None
    numeric_value: Annotated[
        Decimal | None,
        Field(
            default=None,
            description="Numerical inputs (dimensions, quantities, etc.)",
        ),
    ] = None
    boolean_value: Annotated[
        bool | None,
        Field(
            default=None,
            description="True/false choices (features enabled/disabled)",
        ),
    ] = None
    json_value: Annotated[
        dict | None,
        Field(
            default=None,
            description="Complex structured data (multiple properties)",
        ),
    ] = None


class ConfigurationSelectionCreate(ConfigurationSelectionBase):
    """Schema for creating a new configuration selection.

    Attributes:
        configuration_id: Configuration ID
        attribute_node_id: Attribute node ID
    """

    configuration_id: Annotated[
        PositiveInt,
        Field(
            description="Configuration ID",
            examples=[123, 456],
        ),
    ]
    attribute_node_id: Annotated[
        PositiveInt,
        Field(
            description="Attribute node ID",
            examples=[42, 789],
        ),
    ]


class ConfigurationSelectionUpdate(ConfigurationSelectionBase):
    """Schema for updating a configuration selection.

    All fields are optional for partial updates.
    """

    pass


class ConfigurationSelection(ConfigurationSelectionBase):
    """Schema for configuration selection API response.

    Attributes:
        id: Selection ID
        configuration_id: Configuration ID
        attribute_node_id: Attribute node ID
        calculated_price_impact: Price effect of this selection
        calculated_weight_impact: Weight effect of this selection
        calculated_technical_impact: Technical effects
        selection_path: Hierarchical path for context
        created_at: Record creation timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Selection ID"),
    ]
    configuration_id: Annotated[
        PositiveInt,
        Field(description="Configuration ID"),
    ]
    attribute_node_id: Annotated[
        PositiveInt,
        Field(description="Attribute node ID"),
    ]
    calculated_price_impact: Annotated[
        Decimal | None,
        Field(
            default=None,
            decimal_places=2,
            description="Price effect of this selection",
        ),
    ]
    calculated_weight_impact: Annotated[
        Decimal | None,
        Field(
            default=None,
            decimal_places=2,
            description="Weight effect of this selection",
        ),
    ]
    calculated_technical_impact: Annotated[
        dict | None,
        Field(
            default=None,
            description="Technical effects (JSONB)",
            examples=[{"u_value_impact": -0.05}],
        ),
    ]
    selection_path: Annotated[
        str,
        Field(
            description="Hierarchical path for context (LTREE)",
            examples=["window.frame.material.aluminum"],
        ),
    ]
    created_at: Annotated[
        datetime,
        Field(description="Record creation timestamp"),
    ]

    model_config = ConfigDict(from_attributes=True)
