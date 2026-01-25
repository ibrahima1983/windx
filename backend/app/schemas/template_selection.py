"""Template Selection Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for TemplateSelection data
validation, serialization, and API request/response handling.

Public Classes:
    TemplateSelectionBase: Base schema with common attributes
    TemplateSelectionCreate: Schema for creating template selections
    TemplateSelectionUpdate: Schema for updating template selections (partial)
    TemplateSelection: Schema for API responses

Features:
    - Composed schemas (not monolithic)
    - Semantic types (PositiveInt, Decimal validation)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
    - Flexible value storage
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

__all__ = [
    "TemplateSelectionBase",
    "TemplateSelectionCreate",
    "TemplateSelectionUpdate",
    "TemplateSelection",
]


class TemplateSelectionBase(BaseModel):
    """Base template selection schema with common attributes.

    Attributes:
        string_value: Text value for string attributes
        numeric_value: Numeric value for number attributes
        boolean_value: Boolean value for yes/no attributes
        json_value: Complex structured data for JSON attributes
        selection_path: Hierarchical path for context (LTREE)
    """

    string_value: Annotated[
        str | None,
        Field(
            default=None,
            description="Text value for string attributes",
            examples=["Aluminum", "White", "Double Pane"],
        ),
    ] = None
    numeric_value: Annotated[
        Decimal | None,
        Field(
            default=None,
            decimal_places=6,
            description="Numeric value for number attributes",
            examples=[48.5, 60.0, 1.5],
        ),
    ] = None
    boolean_value: Annotated[
        bool | None,
        Field(
            default=None,
            description="Boolean value for yes/no attributes",
            examples=[True, False],
        ),
    ] = None
    json_value: Annotated[
        dict | None,
        Field(
            default=None,
            description="Complex structured data for JSON attributes",
            examples=[{"color": "white", "finish": "matte"}],
        ),
    ] = None
    selection_path: Annotated[
        str,
        Field(
            description="Hierarchical path for context (LTREE)",
            examples=["window.frame.material.aluminum", "door.hardware.lock.premium"],
        ),
    ]

    @field_validator("selection_path")
    @classmethod
    def validate_selection_path(cls, v: str) -> str:
        """Validate selection_path is a valid LTREE path format."""
        if not v:
            raise ValueError("selection_path cannot be empty")
        # Basic LTREE validation: alphanumeric and underscores, separated by dots
        parts = v.split(".")
        if not parts:
            raise ValueError("selection_path must contain at least one label")
        for part in parts:
            if not part:
                raise ValueError("selection_path cannot have empty labels")
            if not all(c.isalnum() or c == "_" for c in part):
                raise ValueError(
                    f"selection_path label '{part}' contains invalid characters. "
                    "Only alphanumeric and underscores allowed."
                )
        return v


class TemplateSelectionCreate(TemplateSelectionBase):
    """Schema for creating a new template selection.

    Attributes:
        template_id: Template ID
        attribute_node_id: Attribute node ID
    """

    template_id: Annotated[
        PositiveInt,
        Field(
            description="Template ID",
            examples=[1, 2, 3],
        ),
    ]
    attribute_node_id: Annotated[
        PositiveInt,
        Field(
            description="Attribute node ID",
            examples=[42, 123, 456],
        ),
    ]


class TemplateSelectionUpdate(BaseModel):
    """Schema for updating template selection information.

    All fields are optional for partial updates.

    Attributes:
        string_value: Optional new text value
        numeric_value: Optional new numeric value
        boolean_value: Optional new boolean value
        json_value: Optional new JSON value
        selection_path: Optional new selection path
    """

    string_value: Annotated[
        str | None,
        Field(
            default=None,
            description="Text value for string attributes",
        ),
    ] = None
    numeric_value: Annotated[
        Decimal | None,
        Field(
            default=None,
            decimal_places=6,
            description="Numeric value for number attributes",
        ),
    ] = None
    boolean_value: Annotated[
        bool | None,
        Field(
            default=None,
            description="Boolean value for yes/no attributes",
        ),
    ] = None
    json_value: Annotated[
        dict | None,
        Field(
            default=None,
            description="Complex structured data for JSON attributes",
        ),
    ] = None
    selection_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Hierarchical path for context (LTREE)",
        ),
    ] = None

    @field_validator("selection_path")
    @classmethod
    def validate_selection_path(cls, v: str | None) -> str | None:
        """Validate selection_path is a valid LTREE path format."""
        if v is None:
            return v
        if not v:
            raise ValueError("selection_path cannot be empty")
        # Basic LTREE validation: alphanumeric and underscores, separated by dots
        parts = v.split(".")
        if not parts:
            raise ValueError("selection_path must contain at least one label")
        for part in parts:
            if not part:
                raise ValueError("selection_path cannot have empty labels")
            if not all(c.isalnum() or c == "_" for c in part):
                raise ValueError(
                    f"selection_path label '{part}' contains invalid characters. "
                    "Only alphanumeric and underscores allowed."
                )
        return v


class TemplateSelection(TemplateSelectionBase):
    """Schema for template selection API response.

    Attributes:
        id: Selection ID
        template_id: Template ID
        attribute_node_id: Attribute node ID
        created_at: Record creation timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Selection ID"),
    ]
    template_id: Annotated[
        PositiveInt,
        Field(description="Template ID"),
    ]
    attribute_node_id: Annotated[
        PositiveInt,
        Field(description="Attribute node ID"),
    ]
    created_at: Annotated[
        datetime,
        Field(description="Record creation timestamp"),
    ]

    model_config = ConfigDict(from_attributes=True)
