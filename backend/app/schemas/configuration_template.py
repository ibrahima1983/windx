"""Configuration Template Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for ConfigurationTemplate data
validation, serialization, and API request/response handling.

Public Classes:
    ConfigurationTemplateBase: Base schema with common attributes
    ConfigurationTemplateCreate: Schema for creating templates
    ConfigurationTemplateUpdate: Schema for updating templates (partial)
    ConfigurationTemplate: Schema for API responses
    ConfigurationTemplateWithSelections: Template with full selection details

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

from app.schemas.template_selection import TemplateSelection

__all__ = [
    "ConfigurationTemplateBase",
    "ConfigurationTemplateCreate",
    "ConfigurationTemplateUpdate",
    "ConfigurationTemplate",
    "ConfigurationTemplateWithSelections",
]


class ConfigurationTemplateBase(BaseModel):
    """Base configuration template schema with common attributes.

    Attributes:
        name: Template name
        description: Template description
        template_type: Type classification
        is_public: Customer visibility flag
        estimated_price: Quick reference price
        estimated_weight: Quick reference weight
    """

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Template name",
            examples=["Standard Casement Window", "Premium Entry Door", "Economy Sliding Window"],
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Template description",
            examples=["Most popular configuration for residential use"],
        ),
    ] = None
    template_type: Annotated[
        str,
        Field(
            default="standard",
            max_length=50,
            description="Type: standard, premium, economy, custom",
            examples=["standard", "premium", "economy", "custom"],
        ),
    ] = "standard"
    is_public: Annotated[
        bool,
        Field(
            default=True,
            description="Customer visibility flag",
        ),
    ] = True
    estimated_price: Annotated[
        Decimal,
        Field(
            default=Decimal("0.00"),
            ge=0,
            decimal_places=2,
            description="Quick reference price",
        ),
    ] = Decimal("0.00")
    estimated_weight: Annotated[
        Decimal,
        Field(
            default=Decimal("0.00"),
            ge=0,
            decimal_places=2,
            description="Quick reference weight in kg",
        ),
    ] = Decimal("0.00")

    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v: str) -> str:
        """Validate template_type is one of the allowed values."""
        allowed = {"standard", "premium", "economy", "custom"}
        if v not in allowed:
            raise ValueError(f"template_type must be one of {allowed}, got '{v}'")
        return v


class ConfigurationTemplateCreate(ConfigurationTemplateBase):
    """Schema for creating a new configuration template.

    Attributes:
        manufacturing_type_id: Manufacturing type ID
        created_by: Optional creator user ID
    """

    manufacturing_type_id: Annotated[
        PositiveInt,
        Field(
            description="Manufacturing type ID",
            examples=[1, 2, 3],
        ),
    ]
    created_by: Annotated[
        PositiveInt | None,
        Field(
            default=None,
            description="Creator user ID (optional)",
            examples=[42, 123],
        ),
    ] = None


class ConfigurationTemplateUpdate(BaseModel):
    """Schema for updating configuration template information.

    All fields are optional for partial updates.

    Attributes:
        name: Optional new template name
        description: Optional new description
        template_type: Optional template type update
        is_public: Optional visibility update
        is_active: Optional active status update
        estimated_price: Optional estimated price update
        estimated_weight: Optional estimated weight update
    """

    name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=200,
            description="Template name",
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Template description",
        ),
    ] = None
    template_type: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Type: standard, premium, economy, custom",
        ),
    ] = None
    is_public: Annotated[
        bool | None,
        Field(
            default=None,
            description="Customer visibility flag",
        ),
    ] = None
    is_active: Annotated[
        bool | None,
        Field(
            default=None,
            description="Active status",
        ),
    ] = None
    estimated_price: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Quick reference price",
        ),
    ] = None
    estimated_weight: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Quick reference weight in kg",
        ),
    ] = None

    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v: str | None) -> str | None:
        """Validate template_type is one of the allowed values."""
        if v is None:
            return v
        allowed = {"standard", "premium", "economy", "custom"}
        if v not in allowed:
            raise ValueError(f"template_type must be one of {allowed}, got '{v}'")
        return v


class ConfigurationTemplate(ConfigurationTemplateBase):
    """Schema for configuration template API response.

    Attributes:
        id: Template ID
        manufacturing_type_id: Manufacturing type ID
        usage_count: Number of times template was used
        success_rate: Conversion rate to orders (percentage)
        created_by: Creator user ID
        is_active: Active status
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Template ID"),
    ]
    manufacturing_type_id: Annotated[
        PositiveInt,
        Field(description="Manufacturing type ID"),
    ]
    usage_count: Annotated[
        int,
        Field(
            ge=0,
            description="Number of times template was used",
        ),
    ]
    success_rate: Annotated[
        Decimal,
        Field(
            ge=0,
            le=100,
            decimal_places=2,
            description="Conversion rate to orders (percentage)",
        ),
    ]
    created_by: Annotated[
        PositiveInt | None,
        Field(default=None, description="Creator user ID"),
    ]
    is_active: Annotated[
        bool,
        Field(description="Active status"),
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


class ConfigurationTemplateWithSelections(ConfigurationTemplate):
    """Configuration template with full selection details.

    Includes the template and all its pre-selected attributes.
    """

    selections: Annotated[
        list[TemplateSelection],
        Field(
            default_factory=list,
            description="Template selections",
        ),
    ]

    model_config = ConfigDict(from_attributes=True)


ConfigurationTemplateWithSelections.model_rebuild()
