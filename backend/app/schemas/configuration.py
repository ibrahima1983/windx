"""Configuration Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for Configuration data validation,
serialization, and API request/response handling.

Public Classes:
    ConfigurationBase: Base schema with common attributes
    ConfigurationCreate: Schema for creating configurations
    ConfigurationUpdate: Schema for updating configurations (partial)
    Configuration: Schema for API responses
    ConfigurationWithSelections: Configuration with full selection details

Features:
    - Composed schemas (not monolithic)
    - Semantic types (PositiveInt, Decimal validation)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

__all__ = [
    "ConfigurationBase",
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "Configuration",
    "ConfigurationWithSelections",
]


class ConfigurationBase(BaseModel):
    """Base configuration schema with common attributes.

    Attributes:
        name: Configuration name
        description: Customer notes and description
    """

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Configuration name",
            examples=["Living Room Window", "Front Entry Door", "Master Bedroom Bay Window"],
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Customer notes and description",
            examples=["Bay window facing south with triple pane glass"],
        ),
    ] = None


class ConfigurationCreate(ConfigurationBase):
    """Schema for creating a new configuration.

    Attributes:
        manufacturing_type_id: Manufacturing type ID
        customer_id: Optional customer ID
    """

    manufacturing_type_id: Annotated[
        PositiveInt,
        Field(
            description="Manufacturing type ID",
            examples=[1, 2, 3],
        ),
    ]
    customer_id: Annotated[
        PositiveInt | None,
        Field(
            default=None,
            description="Customer ID (optional)",
            examples=[42, 123],
        ),
    ] = None


class ConfigurationUpdate(BaseModel):
    """Schema for updating configuration information.

    All fields are optional for partial updates.

    Attributes:
        name: Optional new configuration name
        description: Optional new description
        status: Optional status update
    """

    name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=200,
            description="Configuration name",
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Customer notes and description",
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(
            default=None,
            description="Current state: draft, saved, quoted, ordered",
        ),
    ] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of the allowed values."""
        if v is None:
            return v
        allowed = {"draft", "saved", "quoted", "ordered"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v


class Configuration(ConfigurationBase):
    """Schema for configuration API response.

    Attributes:
        id: Configuration ID
        manufacturing_type_id: Manufacturing type ID
        customer_id: Optional customer ID
        status: Current state
        reference_code: Unique identifier
        base_price: Base price from manufacturing type
        total_price: Final calculated price
        calculated_weight: Total weight
        calculated_technical_data: Technical specifications
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Configuration ID"),
    ]
    manufacturing_type_id: Annotated[
        PositiveInt,
        Field(description="Manufacturing type ID"),
    ]
    customer_id: Annotated[
        PositiveInt | None,
        Field(default=None, description="Customer ID (optional)"),
    ]
    status: Annotated[
        str,
        Field(description="Current state: draft, saved, quoted, ordered"),
    ]
    reference_code: Annotated[
        str | None,
        Field(default=None, description="Unique identifier for easy reference"),
    ]
    base_price: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Base price from manufacturing type",
        ),
    ]
    total_price: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Final calculated price including all options",
        ),
    ]
    calculated_weight: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Total weight in kg",
        ),
    ]
    calculated_technical_data: Annotated[
        dict,
        Field(
            description="Product-specific technical specifications",
            examples=[{"u_value": 0.28, "shgc": 0.35, "vt": 0.65}],
        ),
    ]
    created_at: Annotated[
        datetime,
        Field(description="Record creation timestamp"),
    ]
    updated_at: Annotated[
        datetime,
        Field(description="Last update timestamp"),
    ]

    model_config = ConfigDict(from_attributes=True)


class ConfigurationWithSelections(Configuration):
    """Configuration with full selection details.

    Includes the configuration and all its attribute selections.
    """

    selections: Annotated[
        list[ConfigurationSelection],
        Field(
            default_factory=list,
            description="Configuration selections",
        ),
    ]

    model_config = ConfigDict(from_attributes=True)


# Forward reference resolution
from app.schemas.configuration_selection import ConfigurationSelection

ConfigurationWithSelections.model_rebuild()
